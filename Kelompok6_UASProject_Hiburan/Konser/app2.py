from flask import Flask, render_template, redirect, url_for, session, flash, request
from config import Config
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import os, traceback
import pdfkit
import pymysql

class TiketKonserApp:
    def __init__(self):
        self.app = Flask(__name__)
        self.app.secret_key = "konser_secret_123"
        self.con = Config()
        self.routes()

    def routes(self):
        @self.app.route('/Home')
        def home():
            cur = self.con.mysql.cursor(pymysql.cursors.DictCursor)
            
            # Ambil data lokasi
            cur.execute("SELECT * FROM lokasi")
            daftar_lokasi = cur.fetchall()

            # Ambil nama user dari session
            username = None
            if 'user_id' in session:
                cur.execute("SELECT username FROM users WHERE id = %s", (session['user_id'],))
                user = cur.fetchone()
                if user:
                    username = user['username']

            cur.close()
            return render_template("home.html", daftar_lokasi=daftar_lokasi, username=username)


        @self.app.route('/login/')
        def login():
            return render_template('login.html')

        @self.app.route('/login/process', methods=['POST'])
        def loginprocess():
            username = request.form.get('username')
            password = request.form.get('password')
            cur = self.con.mysql.cursor(pymysql.cursors.DictCursor)
            cur.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cur.fetchone()
            cur.close()
            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['role'] = user['role']
                
                if user['role'] == 'admin':
                    flash('Login berhasil sebagai admin.', 'success')
                    return redirect(url_for('admin_dashboard'))
                else:
                    return redirect(url_for('home'))

            else:
                flash('Username atau password salah!', 'danger')
                return redirect(url_for('login'))

        @self.app.route('/admin/dashboard')
        def admin_dashboard():
            if 'user_id' not in session or session.get('role') != 'admin':
                flash('Hanya admin yang bisa mengakses dashboard ini.', 'danger')
                return redirect(url_for('home'))

            cur = self.con.mysql.cursor(pymysql.cursors.DictCursor)
            cur.execute("SELECT SUM(total_harga) AS total_pendapatan FROM purchase_report")
            total_pendapatan = cur.fetchone()['total_pendapatan'] or 0
            cur.execute("SELECT nama_barang, SUM(jumlah) AS total FROM purchase_report GROUP BY nama_barang")
            penjualan = cur.fetchall()
            cur.execute("SELECT COUNT(*) AS jumlah FROM purchase_report WHERE tanggal_beli = CURDATE()")
            pembelian_hari_ini = cur.fetchone()['jumlah']
            cur.execute("SELECT id, username, email, role, created_at FROM users")
            users = cur.fetchall()
            cur.close()

            return render_template('admin_dashboard.html',
                                   total_pendapatan=total_pendapatan,
                                   pembelian_hari_ini=pembelian_hari_ini,
                                   penjualan=penjualan,
                                   users=users)
        
        @self.app.route('/admin/users/reset/<int:id>')
        def reset_password(id):
            default_pw = generate_password_hash("password123")
            cur = self.con.mysql.cursor()
            cur.execute("UPDATE users SET password = %s WHERE id = %s", (default_pw, id))
            self.con.mysql.commit()
            cur.close()
            flash("Password berhasil di-reset ke 'password123'.", "info")
            return redirect(url_for('admin_dashboard'))
        
        @self.app.route('/admin/users/delete/<int:id>')
        def delete_user(id):
            cur = self.con.mysql.cursor()

            # Hapus semua pembelian user ini
            cur.execute("DELETE FROM purchase_report WHERE user_id = %s", (id,))

            # Baru hapus user
            cur.execute("DELETE FROM users WHERE id = %s", (id,))
            
            self.con.mysql.commit()
            cur.close()

            flash("User dan data pembeliannya berhasil dihapus.", "info")
            return redirect(url_for('admin_dashboard'))


        @self.app.route('/register/')
        def register():
            return render_template('register.html')

        @self.app.route('/register/process', methods=['POST'])
        def registerprocess():
            username = request.form.get('username')
            password = request.form.get('password')
            email = request.form.get('email')
            hashed_pw = generate_password_hash(password)
            cur = self.con.mysql.cursor()
            try:
                cur.execute(
                    'INSERT INTO users (username, email, password) VALUES (%s, %s, %s)',
                    (username, email, hashed_pw)
                )
                self.con.mysql.commit()
                cur.close()
                return redirect(url_for('login'))
            except:
                flash('Registrasi Gagal!', 'danger')
                cur.close()
                return redirect(url_for('register'))

        @self.app.route('/konser<int:lokasi_id>')
        def konser_detail(lokasi_id):
            if 'user_id' not in session:
                flash('Silakan login terlebih dahulu.', 'warning')
                return redirect(url_for('login'))

            cur = self.con.mysql.cursor(pymysql.cursors.DictCursor)
            cur.execute("SELECT * FROM kategori_tempat_duduk WHERE lokasi_id = %s", (lokasi_id,))
            kategori = cur.fetchall()
            cur.execute("SELECT * FROM lokasi WHERE id = %s", (lokasi_id,))
            lokasi = cur.fetchone()
            cur.close()

            if not lokasi:
                flash('Lokasi tidak ditemukan.', 'danger')
                return redirect(url_for('home'))

            lokasi_nama = lokasi['nama_kota']
            lokasi_map = lokasi.get('link_maps') or 'https://maps.google.com'

            return render_template(
                "lokasi.html",
                kategori=kategori,
                lokasi_nama=lokasi_nama,
                lokasi_map=lokasi_map,
                lokasi_id=lokasi_id,
                lokasi=lokasi
            )

        @self.app.route('/pesan/<int:lokasi_id>', methods=['GET', 'POST'])
        def booking(lokasi_id):
            if 'user_id' not in session:
                flash('Silakan login terlebih dahulu.', 'warning')
                return redirect(url_for('home'))

            cur = self.con.mysql.cursor(pymysql.cursors.DictCursor)
            cur.execute("SELECT * FROM kategori_tempat_duduk WHERE lokasi_id = %s", (lokasi_id,))
            kategori_list = cur.fetchall()
            cur.execute("SELECT quota, sold FROM lokasi WHERE id = %s", (lokasi_id,))
            lokasi_data = cur.fetchone()
            quota = lokasi_data['quota']
            sold_sekarang = lokasi_data['sold'] or 0
            sisa_kuota = quota - sold_sekarang

            if request.method == 'POST':
                nama = request.form.get('nama')
                hp = request.form.get('hp')
                email = request.form.get('email')
                tanggal = datetime.now().strftime('%Y-%m-%d')

                if not nama or not hp or not email:
                    flash('Semua field data diri wajib diisi.', 'danger')
                    cur.close()
                    return redirect(url_for('konser_detail', lokasi_id=lokasi_id))

                total_tiket = 0
                total_harga = 0
                pembelian = []

                for kategori in kategori_list:
                    field_name = kategori['nama_kategori'].lower().replace(' ', '')
                    try:
                        jumlah = int(request.form.get(field_name, 0))
                    except ValueError:
                        jumlah = 0

                    if jumlah > 0:
                        if kategori['sold'] is None:
                            kategori['sold'] = 0
                        pembelian.append({
                            'nama_kategori': kategori['nama_kategori'],
                            'jumlah': jumlah,
                            'harga': kategori['harga']
                        })
                        total_tiket += jumlah
                        total_harga += jumlah * float(kategori['harga'])

                if total_tiket == 0:
                    flash('Pilih setidaknya 1 tiket untuk melanjutkan!', 'danger')
                    return redirect(request.url)

                if total_tiket > sisa_kuota:
                    flash(f'Sisa kuota hanya {sisa_kuota} tiket. Kurangi jumlah pembelian.', 'danger')
                    return redirect(request.url)

                for beli in pembelian:
                    cur.execute("""
                        INSERT INTO purchase_report (
                            user_id, nama_pembeli, no_hp, email,
                            nama_barang, jumlah, total_harga, tanggal_beli, lokasi_id
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        session['user_id'], nama, hp, email,
                        beli['nama_kategori'], beli['jumlah'],
                        beli['jumlah'] * beli['harga'], tanggal,
                        lokasi_id
                    ))

                    cur.execute("""
                        UPDATE kategori_tempat_duduk
                        SET sold = sold + %s
                        WHERE nama_kategori = %s AND lokasi_id = %s
                    """, (beli['jumlah'], beli['nama_kategori'], lokasi_id))

                cur.execute("""
                    UPDATE lokasi
                    SET sold = (
                        SELECT SUM(sold)
                        FROM kategori_tempat_duduk
                        WHERE lokasi_id = %s
                    )
                    WHERE id = %s
                """, (lokasi_id, lokasi_id))

                self.con.mysql.commit()
                cur.close()

                session['last_invoice_date'] = tanggal
                return redirect(url_for('pdf'))

            cur.close()
            return render_template('datadiri.html', lokasi_id=lokasi_id, kategori=kategori_list)

        @self.app.route('/purchase-report')
        def pdf():
            if 'user_id' not in session:
                flash('Silakan login terlebih dahulu.', 'warning')
                return redirect(url_for('login'))

            last_date = session.get('last_invoice_date')
            if not last_date:
                flash('Tidak ada data pembelian terbaru.', 'info')
                return redirect(url_for('home'))

            cur = self.con.mysql.cursor(pymysql.cursors.DictCursor)
            cur.execute("""
                SELECT p.nama_barang, p.jumlah, p.total_harga,
                    p.nama_pembeli, p.no_hp, p.email, l.nama_kota AS nama_lokasi
                FROM purchase_report p
                JOIN lokasi l ON p.lokasi_id = l.id
                WHERE p.user_id = %s AND p.tanggal_beli = %s
            """, (session['user_id'], last_date))
            pembelian = cur.fetchall()
            cur.close()

            if not pembelian:
                flash('Tidak ada data pembelian untuk dicetak.', 'info')
                return redirect(url_for('home'))

            total_harga = sum(item['total_harga'] for item in pembelian)
            jumlah_tiket = sum(item['jumlah'] for item in pembelian)
            user_info = pembelian[0]
            rendered = render_template(
                'purchasereport.html',
                data=pembelian,
                total_harga=total_harga,
                jumlah_tiket=jumlah_tiket,
                nama=user_info['nama_pembeli'],
                hp=user_info['no_hp'],
                email=user_info['email'],
                lokasi=user_info['nama_lokasi']
            )
            options = {
                'enable-local-file-access': '',
                'quiet': '',
                'page-size': 'A4',
                'encoding': 'UTF-8'
            }
            configpdf = pdfkit.configuration(wkhtmltopdf=r'C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe')

            output_dir = os.path.join(os.getcwd(), 'static', 'pdf')
            os.makedirs(output_dir, exist_ok=True)

            filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            filepath = os.path.join(output_dir, filename)

            try:
                with open("debug_rendered.html", "w", encoding="utf-8") as f:
                    f.write(rendered)
                pdfkit.from_string(rendered, filepath, configuration=configpdf, options=options)
                flash('Invoice berhasil dibuat.', 'success')
                return redirect(url_for('static', filename=f'pdf/{filename}'))
            except Exception as e:
                print("GAGAL BUAT PDF:")
                print(traceback.format_exc())
                flash(f'Gagal membuat PDF: {str(e)}', 'danger')
                return redirect(url_for('home'))

        @self.app.route('/admin/export-pdf')
        def export_admin_dashboard_pdf():
            if 'user_id' not in session or session.get('role') != 'admin':
                flash('Hanya admin yang bisa mencetak laporan.', 'danger')
                return redirect(url_for('home'))

            cur = self.con.mysql.cursor(pymysql.cursors.DictCursor)
            cur.execute("SELECT SUM(total_harga) AS total_pendapatan FROM purchase_report")
            total_pendapatan = cur.fetchone()['total_pendapatan'] or 0
            cur.execute("SELECT nama_barang, SUM(jumlah) AS total FROM purchase_report GROUP BY nama_barang")
            penjualan = cur.fetchall()
            cur.execute("SELECT COUNT(*) AS jumlah FROM purchase_report WHERE tanggal_beli = CURDATE()")
            pembelian_hari_ini = cur.fetchone()['jumlah']
            cur.execute("SELECT id, username, email, role, created_at FROM users")
            users = cur.fetchall()
            cur.close()

            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            rendered = render_template('admin_dashboard_pdf.html',
                                      total_pendapatan=total_pendapatan,
                                      pembelian_hari_ini=pembelian_hari_ini,
                                      penjualan=penjualan,
                                      users=users,
                                      now=now_str)
            options = {
                'enable-local-file-access': '',
                'quiet': '',
                'page-size': 'A4',
                'encoding': 'UTF-8'
            }
            configpdf = pdfkit.configuration(wkhtmltopdf=r'C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe')

            output_dir = os.path.join(os.getcwd(), 'static', 'pdf')
            os.makedirs(output_dir, exist_ok=True)

            filename = f"admin_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            filepath = os.path.join(output_dir, filename)

            try:
                pdfkit.from_string(rendered, filepath, configuration=configpdf, options=options)
                flash('Laporan PDF berhasil dibuat.', 'success')
                return redirect(url_for('static', filename=f'pdf/{filename}'))
            except Exception as e:
                print(traceback.format_exc())
                flash(f'Gagal membuat PDF: {str(e)}', 'danger')
                return redirect(url_for('admin_dashboard'))

        @self.app.route('/logout')
        def logout():
            session.clear()
            flash('Logout berhasil.', 'info')
            return redirect(url_for('home'))

        @self.app.route('/about')
        def about():
            return render_template('about.html')

        @self.app.route('/contact')
        def contact():
            return render_template('contactus.html')

    def run(self):
        self.app.run(debug=True, port=5000)

if __name__ == '__main__':
    app = TiketKonserApp()
    app.run()
