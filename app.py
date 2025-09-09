import os 
import pymysql.cursors
from flask import Flask, render_template, g, request, session
from functools import wraps
from datetime import datetime

# Impor Blueprint dari modul yang sudah dibuat
from auth import auth_bp, login_required
from tambah_gas import tambah_gas_bp
from transaksi import transaksi_bp
from kelola_pelanggan import kelola_pelanggan_bp
from laporan import laporan_bp
from cek_penjualan import cek_penjualan_bp  # Tambahkan baris ini

SECRET_KEY = os.urandom(24)

# Konfigurasi database MySQL
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "appgas",
    "cursorclass": pymysql.cursors.DictCursor
}

def create_app():
    app = Flask(__name__)
    app.config.from_mapping(SECRET_KEY=SECRET_KEY)

    def get_db():
        if 'db' not in g:
            g.db = pymysql.connect(**DB_CONFIG)
        return g.db

    def close_db(e=None):
        db = g.pop('db', None)
        if db is not None:
            db.close()

    app.teardown_appcontext(close_db)

    # Daftarkan Blueprint
    app.register_blueprint(auth_bp)
    app.register_blueprint(tambah_gas_bp)
    app.register_blueprint(transaksi_bp)
    app.register_blueprint(kelola_pelanggan_bp)
    app.register_blueprint(laporan_bp)
    app.register_blueprint(cek_penjualan_bp)

    @app.route('/')
    @login_required
    def index():
        return render_template('index.html')

    @app.before_request
    def before_request():
        user_id = session.get('user_id')
        if user_id is None:
            g.user = None
        else:
            db = get_db()
            with db.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                g.user = cursor.fetchone()

    # ✅ Tambahkan context processor untuk global variable di template
    @app.context_processor
    def inject_globals():
        return {
            'current_year': datetime.now().year
        }

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
