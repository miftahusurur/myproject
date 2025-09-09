import mysql.connector
from flask import Blueprint, render_template, request, flash, redirect, url_for, g
from auth import login_required

# Membuat Blueprint untuk modul kelola pelanggan
kelola_pelanggan_bp = Blueprint('kelola_pelanggan', __name__)

def get_db():
    if 'db' not in g:
        g.db = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',
            database='appgas'
        )
    return g.db

@kelola_pelanggan_bp.teardown_request
def teardown_request(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@kelola_pelanggan_bp.route('/kelola_pelanggan', methods=['GET', 'POST'])
@login_required
def kelola_pelanggan():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'tambah_pelanggan' or action == 'edit_pelanggan':
            nama = request.form.get('nama')
            telepon = request.form.get('telepon')
            alamat = request.form.get('alamat')
            
            if not nama:
                flash('Nama pelanggan harus diisi.', 'error')
            else:
                try:
                    if action == 'tambah_pelanggan':
                        cursor.execute("INSERT INTO pelanggan (nama, telepon, alamat) VALUES (%s, %s, %s)", (nama, telepon, alamat))
                        flash('Pelanggan berhasil ditambahkan!', 'success')
                    elif action == 'edit_pelanggan':
                        pelanggan_id = request.form.get('id')
                        cursor.execute("UPDATE pelanggan SET nama = %s, telepon = %s, alamat = %s WHERE id = %s", (nama, telepon, alamat, pelanggan_id))
                        flash('Pelanggan berhasil diperbarui!', 'success')
                    db.commit()
                except mysql.connector.Error as err:
                    flash(f'Terjadi kesalahan saat menyimpan data: {err}', 'error')
            return redirect(url_for('kelola_pelanggan.kelola_pelanggan'))
        
        elif action == 'hapus_pelanggan':
            pelanggan_id = request.form.get('id')
            try:
                cursor.execute("DELETE FROM pelanggan WHERE id = %s", (pelanggan_id,))
                db.commit()
                flash('Pelanggan berhasil dihapus!', 'success')
            except mysql.connector.Error as err:
                flash(f'Terjadi kesalahan saat menghapus data: {err}', 'error')
            return redirect(url_for('kelola_pelanggan.kelola_pelanggan'))

    try:
        cursor.execute('SELECT * FROM pelanggan ORDER BY nama ASC')
        pelanggan_list = cursor.fetchall()
        return render_template('kelola_pelanggan.html', pelanggan_list=pelanggan_list)
    except mysql.connector.Error as err:
        flash(f'Terjadi kesalahan saat memuat data pelanggan: {err}', 'error')
        return render_template('kelola_pelanggan.html', pelanggan_list=[])
