import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, g
import mysql.connector
from mysql.connector import cursor as mysql_cursor
from datetime import datetime
from werkzeug.utils import secure_filename
import sys
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from auth import login_required

transaksi_bp = Blueprint('transaksi', __name__)
UPLOAD_FOLDER = 'static/uploads'

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'appgas'
}

def get_db():
    if 'db' not in g:
        g.db = mysql.connector.connect(
            **DB_CONFIG,
            cursorclass=mysql_cursor.MySQLCursorDict
        )
    return g.db

@transaksi_bp.teardown_request
def teardown_request(exception):
    db = g.pop('db', None)
    if db is not None:
        try:
            db.close()
        except mysql.connector.errors.ProgrammingError:
            pass
        except Exception as e:
            print(f"Error closing database connection: {e}")

@transaksi_bp.route('/transaksi_barcode', methods=['GET'])
@login_required
def transaksi_barcode():
    barcode = request.args.get('barcode')
    if not barcode:
        flash("Kode barcode tidak valid.", "error")
        return redirect(url_for('transaksi.transaksi'))

    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id FROM gas WHERE barcode = %s", (barcode,))
        gas = cursor.fetchone()
        if gas:
            return redirect(url_for('transaksi.transaksi', produk_id=gas['id']))
        else:
            flash(f"Produk dengan barcode '{barcode}' tidak ditemukan.", "error")
            return redirect(url_for('transaksi.transaksi'))
    except Exception as e:
        flash(f"Gagal mencari produk: {e}", "error")
        return redirect(url_for('transaksi.transaksi'))

@transaksi_bp.route('/transaksi', methods=['GET', 'POST'])
@login_required
def transaksi():
    conn = get_db()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        try:
            nama_pelanggan = request.form.get('nama_pelanggan')
            alamat = request.form.get('alamat')
            tgl_kirim_raw = request.form.get('tgl_kirim')
            tgl_kirim = tgl_kirim_raw if tgl_kirim_raw else None
            tanggal_transaksi = datetime.now()
            keranjang_data = request.form.get('keranjang_data')
            
            if not keranjang_data:
                flash('Keranjang belanja kosong. Transaksi gagal.', 'error')
                return redirect(url_for('transaksi.transaksi'))

            items = json.loads(keranjang_data)
            
            if not items:
                flash('Keranjang belanja kosong. Transaksi gagal.', 'error')
                return redirect(url_for('transaksi.transaksi'))

            foto_file = request.files.get('foto')
            video_file = request.files.get('video')
            foto_path = None
            video_path = None

            if foto_file and foto_file.filename != '':
                filename = secure_filename(foto_file.filename)
                if not os.path.exists(UPLOAD_FOLDER):
                    os.makedirs(UPLOAD_FOLDER)
                foto_file.save(os.path.join(UPLOAD_FOLDER, filename))
                foto_path = f"uploads/{filename}"

            if video_file and video_file.filename != '':
                filename = secure_filename(video_file.filename)
                if not os.path.exists(UPLOAD_FOLDER):
                    os.makedirs(UPLOAD_FOLDER)
                video_file.save(os.path.join(UPLOAD_FOLDER, filename))
                video_path = f"uploads/{filename}"

            conn.begin()
            
            total_transaksi = 0
            
            # Memproses setiap item dalam keranjang sebagai transaksi terpisah
            for item in items:
                produk_id = item['id']
                jumlah_jual = item['jumlah']
                harga_satuan = item['harga']
                
                # Periksa stok setiap produk
                cursor.execute("SELECT stok, jenis_gas FROM gas WHERE id = %s", (produk_id,))
                gas_data = cursor.fetchone()
                
                if not gas_data or gas_data['stok'] < jumlah_jual:
                    conn.rollback()
                    flash(f"Stok {gas_data['jenis_gas']} tidak mencukupi.", "error")
                    return redirect(url_for('transaksi.transaksi'))
                    
                total_harga_item = jumlah_jual * harga_satuan
                total_transaksi += total_harga_item
                
                # Simpan setiap item sebagai baris transaksi baru
                # --- PERBAIKAN PENTING DI SINI ---
                # Menambahkan satu `%s` placeholder untuk `item_json`
                cursor.execute("""
                    INSERT INTO transaksi 
                    (nama_pelanggan, gas_id, jumlah_jual, harga_satuan, total_harga, tanggal_transaksi, tgl_kirim, alamat, foto, video, item_json)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (nama_pelanggan, produk_id, jumlah_jual, harga_satuan, total_harga_item, tanggal_transaksi, tgl_kirim, alamat, foto_path, video_path, json.dumps(item)))
                
                # Kurangi stok produk
                cursor.execute("UPDATE gas SET stok = stok - %s WHERE id = %s", (jumlah_jual, produk_id))
            
            conn.commit()
            flash(f'Transaksi berhasil dicatat! Total Keseluruhan: Rp {total_transaksi:,.0f}'.replace(',', '.'), 'success')

        except json.JSONDecodeError as e:
            conn.rollback()
            flash(f"Gagal memproses data keranjang: Data tidak valid. {e}", "error")
        except Exception as e:
            conn.rollback()
            flash(f"Terjadi kesalahan saat mencatat transaksi: {e}", "error")

        return redirect(url_for('transaksi.transaksi'))

    # Ambil riwayat transaksi
    gas_list = []
    transaksi_list = []
    try:
        cursor.execute("SELECT * FROM gas")
        gas_list = cursor.fetchall()
        
        # Ambil riwayat transaksi dengan JOIN ke tabel gas
        cursor.execute("""
            SELECT t.*, g.jenis_gas 
            FROM transaksi t
            JOIN gas g ON t.gas_id = g.id
            ORDER BY t.id DESC
        """)
        transaksi_list = cursor.fetchall()
        
    except Exception as e:
        flash(f"Gagal memuat data: {e}", "error")

    return render_template('transaksi.html', 
                            gas_list=gas_list, 
                            transaksi_list=transaksi_list)

@transaksi_bp.route('/hapus_transaksi/<int:transaksi_id>', methods=['POST'])
@login_required
def hapus_transaksi(transaksi_id):
    conn = get_db()
    cursor = conn.cursor()

    try:
        # 1. Ambil informasi transaksi yang akan dihapus untuk mengembalikan stok
        cursor.execute("SELECT gas_id, jumlah_jual FROM transaksi WHERE id = %s", (transaksi_id,))
        transaksi_to_delete = cursor.fetchone()

        if not transaksi_to_delete:
            flash("Transaksi tidak ditemukan.", "error")
            return redirect(url_for('transaksi.transaksi'))

        gas_id = transaksi_to_delete['gas_id']
        jumlah_jual = transaksi_to_delete['jumlah_jual']

        # Mulai transaksi database
        conn.begin()

        # 2. Hapus transaksi dari database
        cursor.execute("DELETE FROM transaksi WHERE id = %s", (transaksi_id,))
        
        # 3. Kembalikan stok gas yang terkait
        cursor.execute("UPDATE gas SET stok = stok + %s WHERE id = %s", (jumlah_jual, gas_id))

        conn.commit()
        flash("Transaksi berhasil dihapus dan stok telah dikembalikan!", "success")

    except Exception as e:
        conn.rollback()
        flash(f"Terjadi kesalahan saat menghapus transaksi: {e}", "error")

    return redirect(url_for('transaksi.transaksi'))