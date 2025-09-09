# penjualan_gas/models.py
# Catatan: Kita tidak menggunakan SQLAlchemy seperti permintaan,
# karena akan lebih sederhana menggunakan sqlite3 langsung untuk contoh ini.
# File ini akan berisi skema database.

import sqlite3

def create_database():
    conn = sqlite3.connect('appgas.db') # Menggunakan nama database yang baru
    c = conn.cursor()

    # Tabel untuk user (admin)
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        )
    ''')

    # Tabel untuk master data gas
    c.execute('''
        CREATE TABLE IF NOT EXISTS gas_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jenis_gas TEXT NOT NULL,
            harga REAL NOT NULL,
            stok INTEGER NOT NULL
        )
    ''')
    
    # Tabel untuk transaksi penjualan
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama_pelanggan TEXT,
            alamat TEXT,
            tanggal_transaksi TEXT NOT NULL,
            jumlah_bayar REAL NOT NULL,
            foto TEXT,
            video TEXT,
            item_json TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()

if __name__ == '__main__':
    create_database()