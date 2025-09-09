import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
from datetime import datetime
import pymysql

# Membuat Blueprint
cek_penjualan_bp = Blueprint("cek_penjualan", __name__, url_prefix="/cek_penjualan")

# Konfigurasi upload dan database
UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "mp4", "avi", "mov"}

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "appgas",
    "cursorclass": pymysql.cursors.DictCursor
}

def get_db_connection():
    return pymysql.connect(**DB_CONFIG)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ====== Route utama untuk tampilan halaman cek penjualan ======
@cek_penjualan_bp.route("/", methods=["GET"])
def cek_penjualan():
    transaksi_list = []
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Ambil semua data transaksi untuk riwayat
            cursor.execute("""
                SELECT t.*, g.jenis_gas, g.berat, g.harga AS harga_satuan,
                       (t.jumlah_jual * g.harga) AS total_harga
                FROM transaksi t
                JOIN gas g ON t.gas_id = g.id
                ORDER BY t.tanggal_transaksi DESC
            """)
            transaksi_list = cursor.fetchall()
    finally:
        conn.close()
    
    # Halaman ini hanya akan menampilkan tabel riwayat transaksi secara default
    return render_template("cek_penjualan.html", transaksi_list=transaksi_list)

# ====== Endpoint API untuk Mendapatkan Data Produk Berdasarkan Barcode ======
@cek_penjualan_bp.route("/api/gas_by_barcode/<string:barcode>", methods=["GET"])
def get_gas_by_barcode(barcode):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, jenis_gas, berat, harga, stok, barcode FROM gas WHERE barcode = %s", (barcode,))
            gas_info = cursor.fetchone()
        
        if gas_info:
            return jsonify({
                "success": True,
                "gas": gas_info
            })
        else:
            return jsonify({
                "success": False,
                "message": f"Gas dengan barcode '{barcode}' tidak ditemukan."
            }), 404
            
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()

# ====== Endpoint API untuk Mencatat Transaksi ======
@cek_penjualan_bp.route("/tambah_transaksi_manual", methods=["POST"])
def tambah_transaksi_manual():
    conn = get_db_connection()
    try:
        gas_id = request.form.get("gas_id", type=int)
        nama_pelanggan = request.form.get("nama_pelanggan")
        alamat = request.form.get("alamat")
        jumlah = request.form.get("jumlah", type=int)
        tgl_kirim = request.form.get("tgl_kirim") or None

        # Periksa ketersediaan stok
        with conn.cursor() as cursor:
            cursor.execute("SELECT stok, harga, jenis_gas, berat FROM gas WHERE id = %s", (gas_id,))
            gas_info = cursor.fetchone()
        
        if not gas_info:
            return jsonify({"success": False, "message": "Produk tidak ditemukan."}), 404
            
        if gas_info["stok"] < jumlah:
            return jsonify({"success": False, "message": "Stok tidak mencukupi."}), 400

        # Ambil nama file foto dan video, lalu simpan ke server
        foto_filename = None
        video_filename = None
        
        if "foto" in request.files and allowed_file(request.files["foto"].filename):
            foto = request.files["foto"]
            foto_filename = datetime.now().strftime("%Y%m%d%H%M%S_") + secure_filename(foto.filename)
            foto.save(os.path.join(UPLOAD_FOLDER, foto_filename))

        if "video" in request.files and allowed_file(request.files["video"].filename):
            video = request.files["video"]
            video_filename = datetime.now().strftime("%Y%m%d%H%M%S_") + secure_filename(video.filename)
            video.save(os.path.join(UPLOAD_FOLDER, video_filename))

        # Mulai transaksi database
        conn.begin()
        
        with conn.cursor() as cursor:
            # Kurangi stok gas
            cursor.execute("UPDATE gas SET stok = stok - %s WHERE id = %s", (jumlah, gas_id))
            
            # Tambahkan transaksi baru
            cursor.execute("""
                INSERT INTO transaksi (gas_id, nama_pelanggan, alamat, jumlah_jual, tgl_kirim, foto, video, tanggal_transaksi)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """, (gas_id, nama_pelanggan, alamat, jumlah, tgl_kirim, foto_filename, video_filename))
        
        conn.commit()
        
        return jsonify({"success": True, "message": "Transaksi berhasil disimpan!"})

    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "message": f"Kesalahan server: {e}"}), 500
    finally:
        conn.close()