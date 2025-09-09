import os
import pymysql
import qrcode
import barcode
from barcode.writer import ImageWriter
from flask import Blueprint, render_template, request, flash, redirect, url_for, g
from auth import login_required, admin_required  # Gunakan impor absolut
from datetime import datetime
from pymysql.cursors import DictCursor
from werkzeug.utils import secure_filename
import random

# Pastikan Anda telah mendefinisikan get_db() di file ini, atau impor dari file terpisah
def get_db():
    if 'db' not in g:
        g.db = pymysql.connect(
            host='localhost',
            user='root',
            password='',
            database='appgas',
            cursorclass=DictCursor
        )
    return g.db

tambah_gas_bp = Blueprint('tambah_gas', __name__)

UPLOAD_FOLDER = 'static/uploads'
QRCODE_FOLDER = 'static/qrcodes'
BARCODE_FOLDER = 'static/barcodes'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Pastikan folder ada
for folder in [UPLOAD_FOLDER, QRCODE_FOLDER, BARCODE_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

@tambah_gas_bp.teardown_request
def teardown_request(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@tambah_gas_bp.route('/')
@login_required
def dashboard():
    db = get_db()
    try:
        with db.cursor() as cursor:
            # Perbaiki nama tabel sesuai skema Anda.
            # Jika tabelnya bernama 'gas', maka tidak perlu diubah
            cursor.execute("SELECT * FROM gas ORDER BY id DESC")
            gas_list = cursor.fetchall()
    except Exception as e:
        print(f"Error fetching gas data: {e}")
        gas_list = []
        flash("Gagal memuat data produk.", "error")
        
    return render_template('index.html', gas_list=gas_list)

@tambah_gas_bp.route('/tambah_gas', methods=['GET', 'POST'])
@login_required
@admin_required  # Tambahkan dekorator admin_required
def tambah_gas():
    db = get_db()
    error = None

    if request.method == 'POST':
        jenis = request.form.get('jenis_gas')
        berat = request.form.get('berat')
        harga_str = request.form.get('harga')
        stok_str = request.form.get('stok')
        tanggal_str = request.form.get('tanggal_masuk')
        gambar_filename = None

        if not jenis or not berat or not harga_str or not stok_str or not tanggal_str:
            error = 'Semua field harus diisi.'
        else:
            if 'gambar' in request.files and request.files['gambar'].filename != '':
                file = request.files['gambar']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    gambar_filename = filename
                    file.save(os.path.join(UPLOAD_FOLDER, filename))
                else:
                    error = 'File tidak diizinkan. Hanya png, jpg, jpeg, atau gif.'

            if error is None:
                try:
                    berat = float(berat)
                except (ValueError, TypeError):
                    error = 'Berat harus berupa angka. Contoh: 3 atau 12.5.'
            
            if error is None:
                try:
                    harga = float(harga_str)
                    if harga < 0:
                        error = 'Harga tidak boleh < 0.'
                except ValueError:
                    error = 'Harga harus berupa angka.'

            if error is None:
                try:
                    stok = int(stok_str)
                    if stok < 0:
                        error = 'Stok tidak boleh < 0.'
                except ValueError:
                    error = 'Stok harus berupa angka.'

            if error is None:
                try:
                    tanggal_masuk = datetime.strptime(tanggal_str, '%Y-%m-%d').date()
                except ValueError:
                    error = 'Format tanggal salah. Gunakan YYYY-MM-DD.'

            if error is None:
                try:
                    with db.cursor() as cursor:
                        jenis_clean = jenis.upper().replace(' ', '')
                        year_code = datetime.now().year
                        random_number = random.randint(10000, 99999)
                        kode_unik = f"{jenis_clean}-IDN{year_code}-{random_number}"

                        qr_img = qrcode.make(kode_unik)
                        qr_filename = f"{kode_unik}.png"
                        qr_path = os.path.join(QRCODE_FOLDER, qr_filename)
                        qr_img.save(qr_path)

                        code128 = barcode.get('code128', kode_unik, writer=ImageWriter())
                        barcode_filename = f"{kode_unik}.png"
                        barcode_path = os.path.join(BARCODE_FOLDER, barcode_filename)
                        code128.save(os.path.splitext(barcode_path)[0])
                        
                        # Pastikan tabel 'gas' memiliki semua kolom yang Anda butuhkan
                        cursor.execute(
                            "INSERT INTO gas (jenis_gas, berat, harga, stok, tanggal_masuk, gambar, qrcode, barcode) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                            (jenis, berat, harga, stok, tanggal_masuk, gambar_filename, qr_filename, barcode_filename)
                        )
                        db.commit()

                    flash('Data gas berhasil ditambahkan dengan QR Code dan Barcode!', 'success')
                    return redirect(url_for('tambah_gas.tambah_gas'))
                except pymysql.MySQLError as err:
                    print("MySQL Error:", err)
                    error = f"Kesalahan DB: {err}"
                except Exception as e:
                    print("Error:", e)
                    error = f"Kesalahan tidak terduga: {e}"

    if error:
        flash(error, 'error')

    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM gas ORDER BY id DESC")
        gas_list = cursor.fetchall()

    return render_template('tambah_gas.html', gas_list=gas_list)

@tambah_gas_bp.route('/hapus_gas/<int:id>', methods=['POST'])
@login_required
@admin_required # Tambahkan dekorator admin_required
def hapus_gas(id):
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT gambar, qrcode, barcode FROM gas WHERE id = %s", (id,))
            result = cursor.fetchone()

            if result and result['gambar']:
                file_path = os.path.join(UPLOAD_FOLDER, result['gambar'])
                if os.path.exists(file_path):
                    os.remove(file_path)

            if result and result['qrcode']:
                qr_path = os.path.join(QRCODE_FOLDER, result['qrcode'])
                if os.path.exists(qr_path):
                    os.remove(qr_path)

            if result and result['barcode']:
                barcode_path = os.path.join(BARCODE_FOLDER, result['barcode'])
                if os.path.exists(barcode_path):
                    os.remove(barcode_path)

            cursor.execute("DELETE FROM gas WHERE id = %s", (id,))
        db.commit()
        flash('Data gas berhasil dihapus!', 'success')
    except Exception as e:
        flash(f'Kesalahan: {e}', 'error')

    return redirect(url_for('tambah_gas.tambah_gas'))


@tambah_gas_bp.route('/cetak_semua_barcode')
@login_required
@admin_required # Tambahkan dekorator admin_required
def cetak_semua_barcode():
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM gas WHERE barcode IS NOT NULL")
            gas_list = cursor.fetchall()

        return render_template('cetak_barcode.html', gas_list=gas_list)

    except Exception as e:
        flash(f'Gagal memuat data barcode untuk dicetak: {e}', 'error')
        return redirect(url_for('tambah_gas.tambah_gas'))