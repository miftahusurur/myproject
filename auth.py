import pymysql.cursors
from flask import Blueprint, render_template, request, flash, redirect, url_for, session, g
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

# Blueprint untuk otentikasi
auth_bp = Blueprint('auth', __name__)

# Konfigurasi koneksi MySQL
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "appgas",
    "cursorclass": pymysql.cursors.DictCursor
}

def get_db():
    """Ambil koneksi database dari flask.g"""
    if 'db' not in g:
        g.db = pymysql.connect(**DB_CONFIG)
    return g.db

def create_default_admin():
    """Buat akun admin default jika belum ada"""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM users WHERE username = %s", ("admin",))
        user = cursor.fetchone()
        if not user:
            hashed_password = generate_password_hash("admin123")  # password sementara
            cursor.execute(
                "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                ("admin", hashed_password, "admin")  # Gunakan 'admin' (string)
            )
            db.commit()
            print("✅ Admin default dibuat: username='admin', password='admin123'")

@auth_bp.before_app_request
def before_app_request():
    """Pastikan admin default ada sebelum app berjalan"""
    if not hasattr(g, 'default_admin_created'):
        create_default_admin()
        g.default_admin_created = True

@auth_bp.before_request
def before_request():
    """Set user login di g.user sebelum setiap request"""
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            g.user = cursor.fetchone()

@auth_bp.teardown_request
def teardown_request(exception):
    """Tutup koneksi DB setelah request"""
    db = g.pop('db', None)
    if db is not None:
        db.close()

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    # Hanya admin yang bisa daftar pengguna baru
    if not g.user or g.user.get("role") != "admin":
        flash('Akses ditolak. Anda harus login sebagai admin.', 'error')
        return redirect(url_for('auth.login'))
        
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form.get('role', 'user')

        db = get_db()
        error = None
        
        if not username:
            error = 'Username dibutuhkan.'
        elif not password:
            error = 'Password dibutuhkan.'
        
        if error is None:
            try:
                hashed_password = generate_password_hash(password)
                with db.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                        (username, hashed_password, role)
                    )
                db.commit()
                flash('Pengguna berhasil didaftarkan!', 'success')
                return redirect(url_for('index'))
            except pymysql.err.IntegrityError:
                error = f"Username {username} sudah ada."
        
        flash(error, 'error')

    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
        
        if user is None:
            flash('Username atau password salah.', 'error')
        elif not check_password_hash(user["password"], password):
            flash('Username atau password salah.', 'error')
        else:
            session.clear()
            session['user_id'] = user["id"]
            session['role'] = user["role"]   # ⬅️ simpan role ke session
            flash('Login berhasil!', 'success')
            return redirect(url_for('index'))

    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Anda telah logout.', 'success')
    return redirect(url_for('auth.login'))

def login_required(view):
    """Dekorator: hanya boleh diakses setelah login"""
    @wraps(view)
    def decorated_function(*args, **kwargs):
        if session.get('user_id') is None:
            flash('Silakan login terlebih dahulu untuk mengakses halaman ini.', 'warning')
            return redirect(url_for('auth.login'))
        return view(*args, **kwargs)
    return decorated_function

def admin_required(view):
    """Dekorator: hanya bisa diakses oleh admin"""
    @wraps(view)
    def decorated_function(*args, **kwargs):
        if session.get('user_id') is None:
            flash('Silakan login terlebih dahulu.', 'warning')
            return redirect(url_for('auth.login'))
        elif not g.user or g.user.get("role") != "admin":
            flash('Akses ditolak. Hanya admin yang bisa mengakses halaman ini.', 'error')
            return redirect(url_for('index'))
        return view(*args, **kwargs)
    return decorated_function
