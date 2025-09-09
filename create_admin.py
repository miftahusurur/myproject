import sqlite3
from werkzeug.security import generate_password_hash

# Nama file database Anda
DATABASE = 'appgas.db'

# Hubungkan ke database
db = sqlite3.connect(DATABASE)
cursor = db.cursor()

# Hashed password untuk 'admin'
hashed_password = generate_password_hash('admin123')

try:
    # Masukkan data pengguna admin ke tabel users
    cursor.execute("INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)",
                   ('admin', hashed_password, 1))
    db.commit()
    print("Pengguna admin 'admin' berhasil ditambahkan.")
except sqlite3.IntegrityError:
    print("Pengguna 'admin' sudah ada di database.")
finally:
    db.close()

