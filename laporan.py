import datetime
import pymysql
from flask import Blueprint, render_template, request, redirect, url_for, session, send_file
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO
from functools import wraps

laporan_bp = Blueprint('laporan', __name__, url_prefix='/laporan')

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'appgas',
    'cursorclass': pymysql.cursors.DictCursor
}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@laporan_bp.route('/', methods=['GET', 'POST'])
@login_required
def laporan():
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    laporan_harian = []
    
    query = """
        SELECT
            t.tanggal_transaksi,
            t.nama_pelanggan,
            t.jumlah_jual,
            t.harga_satuan,
            t.total_harga,
            g.jenis_gas
        FROM transaksi t
        JOIN gas g ON t.gas_id = g.id
        WHERE 1=1
    """
    params = []

    if start_date:
        query += " AND t.tanggal_transaksi >= %s"
        params.append(start_date)
    if end_date:
        query += " AND t.tanggal_transaksi <= %s"
        params.append(end_date)

    query += " ORDER BY t.tanggal_transaksi DESC"

    with pymysql.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            laporan_harian = cursor.fetchall()

    return render_template('laporan.html',
                           laporan_harian=laporan_harian,
                           start_date=start_date,
                           end_date=end_date)


@laporan_bp.route('/cetak', methods=['GET'])
@login_required
def cetak_laporan():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = """
        SELECT t.tanggal_transaksi,
               t.nama_pelanggan,
               g.jenis_gas,
               t.jumlah_jual,
               t.harga_satuan,
               t.total_harga
        FROM transaksi t
        JOIN gas g ON t.gas_id = g.id
        WHERE 1=1
    """
    params = []
    if start_date and start_date != 'None':
        query += " AND t.tanggal_transaksi >= %s"
        params.append(start_date)
    if end_date and end_date != 'None':
        query += " AND t.tanggal_transaksi <= %s"
        params.append(end_date)

    query += " ORDER BY t.tanggal_transaksi"

    with pymysql.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            data = cursor.fetchall()
    
    # Generate PDF
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Judul Laporan
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawCentredString(width/2, height - 30, "Laporan Penjualan Gas")
    
    # Rentang Tanggal
    date_range_str = ""
    if start_date and end_date and start_date != 'None' and end_date != 'None':
        date_range_str = f"Laporan Periode: {start_date} s.d. {end_date}"
    elif start_date and start_date != 'None':
        date_range_str = f"Laporan dari Tanggal: {start_date}"
    elif end_date and end_date != 'None':
        date_range_str = f"Laporan sampai Tanggal: {end_date}"

    if date_range_str:
        pdf.setFont("Helvetica", 10)
        pdf.drawCentredString(width/2, height - 45, date_range_str)

    # Posisi awal tabel
    x_start = 50
    y_start = height - 80
    col_widths = [100, 100, 80, 50, 90, 90]
    
    # Header tabel
    headers = ["Tanggal", "Pelanggan", "Jenis Gas", "Jumlah", "Harga Satuan", "Total"]
    pdf.setFont("Helvetica-Bold", 10)
    y = y_start
    x = x_start
    for i, header in enumerate(headers):
        pdf.drawString(x, y, header)
        x += col_widths[i]
    
    # Garis header (diturunkan sedikit biar ga nyilang)
    y -= 8
    pdf.line(x_start, y, x_start + sum(col_widths), y)
    y -= 10

    # Isi tabel
    pdf.setFont("Helvetica", 10)
    total_penjualan = 0
    
    for row in data:
        x = x_start
        tanggal_str = row['tanggal_transaksi'].strftime("%Y-%m-%d")
        pelanggan_str = row['nama_pelanggan']
        jenis_gas_str = row['jenis_gas']
        jumlah_str = str(row['jumlah_jual'])
        harga_satuan_str = f"Rp {row['harga_satuan']:,.0f}".replace(",", ".")
        total_harga_str = f"Rp {row['total_harga']:,.0f}".replace(",", ".")

        pdf.drawString(x, y, tanggal_str)
        x += col_widths[0]
        pdf.drawString(x, y, pelanggan_str)
        x += col_widths[1]
        pdf.drawString(x, y, jenis_gas_str)
        x += col_widths[2]
        pdf.drawString(x, y, jumlah_str)
        x += col_widths[3]
        pdf.drawRightString(x + col_widths[4], y, harga_satuan_str)
        x += col_widths[4]
        pdf.drawRightString(x + col_widths[5], y, total_harga_str)

        total_penjualan += row['total_harga']
        
        y -= 20
        if y < 50:  # Buat halaman baru
            pdf.showPage()
            y = height - 50
            pdf.setFont("Helvetica-Bold", 10)
            x = x_start
            for i, header in enumerate(headers):
                pdf.drawString(x, y, header)
                x += col_widths[i]
            y -= 8
            pdf.line(x_start, y, x_start + sum(col_widths), y)
            y -= 10
            pdf.setFont("Helvetica", 10)

    # Garis akhir tabel
    y -= 5
    pdf.line(x_start, y, x_start + sum(col_widths), y)
    
    # Total Penjualan
    y -= 20
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawRightString(x_start + sum(col_widths) - col_widths[-1] - 15, y, "TOTAL:")
    pdf.drawRightString(x_start + sum(col_widths) - 5, y, f"Rp {total_penjualan:,.0f}".replace(",", "."))
    
    pdf.save()
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name="laporan_penjualan.pdf", mimetype='application/pdf')
