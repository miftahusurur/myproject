# penjualan_gas/init_db.py
import sqlite3
import os

DATABASE = 'appgas.db'

def init_db():
    if os.path.exists(DATABASE):
        os.remove(DATABASE) # Hapus database lama jika ada
    conn = sqlite3.connect(DATABASE)
    with open('schema.sql', 'r') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    print("Database berhasil diinisialisasi.")

if __name__ == '__main__':
    init_db()
