from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, make_response
from config import Config
from datetime import datetime
from werkzeug.security import generate_password_hash
import hashlib
import os, pdfkit, pymysql

class TiketKonserApp:    
    def __init__(self):
        self.app = Flask(__name__)
        self.app.secret_key = "konser_secret_123"
        self.con = Config()
        self.routes()
    
    def routes(self):
        @self.app.route('/Home')
        def home():
            if 'user_id' in session:
                return render_template("home.html", username=session['username'], role=session['role'])
            else:
                return render_template("home.html", username='Login', role=None)
                
        @self.app.route('/login')
        def login():
            return render_template('login.html')
        
        @self.app.route('/login/process', methods=['POST'])
        def loginprocess():
            if request.method == 'POST':
                username = request.form.get('username')
                password = request.form.get('password')
                cur = self.con.mysql.cursor()
                pw = hashlib.md5(password.encode()).hexdigest()
                password = pw[:30]
                cur.execute("SELECT * FROM user WHERE (username = %s OR email = %s OR phone = %s) AND password = %s", (username, username, username, password))
                row = cur.fetchone()
                if row:
                    # row: (id, username, password, confirmpw, phone, role)
                    session['user_id'] = row[0]      # id
                    session['username'] = row[1]     # username
                    session['role'] = row[5]         # role

                    print("DEBUG LOGIN:", session)   # bantu debug

                    cur.close()
                    if session['role'] == 'admin':
                        return redirect(url_for('admin_dashboard'))
                    else:
                        return redirect(url_for('home'))
                else:
                    flash('Username atau password salah!', 'danger')
                    cur.close()
                    return redirect(url_for('login'))
            flash('Akses tidak valid.', 'danger')
            return redirect(url_for('login'))

            
        @self.app.route('/admin/dashboard', endpoint='admin_dashboard')
        def admin_dashboard():
            if 'user_id' not in session or session.get('role') != 'admin':
                flash('Hanya admin yang bisa mengakses dashboard ini.', 'danger')
                return redirect(url_for('home'))
            cur = self.con.mysql.cursor(pymysql.cursors.DictCursor)
            cur.execute("SELECT SUM(totalharga) AS total_pendapatan FROM booking")
            total_pendapatan = cur.fetchone()['total_pendapatan'] or 0
            cur.execute("SELECT kategori AS nama_barang, SUM(totaltiket) AS total FROM booking GROUP BY kategori")
            penjualan = cur.fetchall()
            cur.execute("SELECT COUNT(*) AS jumlah FROM booking WHERE DATE(tanggal) = CURDATE()")
            pembelian_hari_ini = cur.fetchone()['jumlah']
            cur.execute("SELECT id, username, email, phone, role FROM user")
            users = cur.fetchall()
            cur.close()
            return render_template('admin_dashboard.html',
                                total_pendapatan=total_pendapatan,
                                pembelian_hari_ini=pembelian_hari_ini,
                                penjualan=penjualan,
                                users=users)

        @self.app.route('/admin/users/reset/<int:id>')
        def reset_password(id):
            password = 'password123'
            pw = hashlib.md5(password.encode()).hexdigest()
            
            cur = self.con.mysql.cursor()
            
            cur.execute("""
                UPDATE user 
                SET password = %s  
                WHERE id = %s
            """, (pw, id))
            
            self.con.mysql.commit()
            cur.close()

            flash("Password berhasil di-reset ke 'password123'.", "info")
            return redirect(url_for('admin_dashboard'))
        
        @self.app.route('/admin/users/delete/<int:id>')
        def delete_user(id):
            cur = self.con.mysql.cursor()

            cur.execute("SELECT username, phone FROM user WHERE id = %s", (id,))
            user_data = cur.fetchone()

            if user_data:
                username, phone = user_data

                
                cur.execute("DELETE FROM booking WHERE nama = %s AND phone = %s", (username, str(phone)))

                cur.execute("DELETE FROM user WHERE id = %s", (id,))

                self.con.mysql.commit()
                flash("User dan data pemesanannya berhasil dihapus.", "info")
            else:
                flash("User tidak ditemukan.", "warning")

            cur.close()
            return redirect(url_for('admin_dashboard'))

        @self.app.route('/register')
        def register():
            return render_template('register.html')
        
        @self.app.route('/register/process', methods=['POST'])
        def registerprocess():
            if request.method == 'POST':
                username = request.form['username']
                email = request.form['email']
                password = request.form['password']
                confirmpw = request.form["confirmpw"]
                phone = request.form["phone"]
                role = 'user'
                cur = self.con.mysql.cursor()
                cur.execute('SELECT username FROM user WHERE username = %s', (username,))
                if cur.fetchone():
                    session['warning'] = 'Username Sudah Dipakai!'
                    return redirect(url_for('register'))
                elif password == confirmpw:
                    try:
                        cur.execute(
                            'INSERT INTO user (username, email, password, phone, role) VALUES (%s, %s, md5(%s), %s, %s)',
                            (username, email, password, phone, role)
                        )
                        self.con.mysql.commit()
                        cur.close()
                        return redirect(url_for('login'))
                    except Exception as e:
                        user = None
                        flash('Registrasi Gagal!', 'danger')
                        cur.close()
                        return redirect(url_for('register'))
                else:
                    flash('Konfirmasi password salah!', 'danger')
                    return redirect(url_for('register'))
                
        @self.app.route('/konser<int:konser_id>')
        def konser_detail(konser_id):
            if not 'user_id' in session:
                flash('Silakan login terlebih dahulu.', 'danger')
                return redirect(url_for('login'))
            else:
                return render_template(f'lokasi{konser_id}.html', username=session['username'])

        @self.app.route('/pesan/')
        def datadiri():
            if not 'pesan' in session:
                return 'Not Allowed'
            konser_id = session.get('konser_id')
            session.pop('pesan', None)
            return render_template('datadiri.html', konser_id=konser_id)
        
        @self.app.route('/konser<int:konser_id>/process', methods=['GET','POST'])
        def jumlahtiket(konser_id):
            if request.method == 'POST':
                if request.form['total_tiket'] != '0':
                    session['tmptduduk'] = {
                        'festival' : int(request.form['festival']),  
                        'cat2' : int(request.form["cat2"]), 
                        'cat3' : int(request.form["cat3"]), 
                        'cat4' : int(request.form["cat4"])
                    }
                    session['totalsemuaharga'] = request.form['total_harga']
                    session['totalsemuatiket'] = request.form['total_tiket']
                    jumlahtiket = []
                    tmptduduk = session['tmptduduk']
                    for i in tmptduduk:
                        if tmptduduk[i] != 0:
                            jumlahtiket.append(tmptduduk[i])
                    session['konser_id']=konser_id
                    session['pesan'] = True
                    return redirect(url_for('datadiri'))
                else:
                    flash('Anda Belum Memilih Jumlah Tiket!', 'danger')
                    return redirect(url_for('jumlahtiket', konser_id=konser_id))
            return render_template(f'lokasi{konser_id}.html')

        
        @self.app.route('/purchase-report', methods=['POST'])
        def purchase_report():
            lokasi_id = request.form.get('lokasi_id')
            if lokasi_id == '1':
                lokasi = 'Jakarta'
            elif lokasi_id == '2':
                lokasi = 'Bandung'
            elif lokasi_id == '3':
                lokasi = 'Surabaya'
            if request.method == 'POST':
                nama = request.form['nama']
                email = request.form['email']
                phone = request.form['phone']
                tanggal = datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
                cur = self.con.mysql.cursor()
                cur.execute('SELECT harga FROM kategori_tempat_duduk WHERE lokasi_id = %s', (lokasi_id,))
                harga = cur.fetchall()
                price = []
                kategori = list(session['tmptduduk'].keys())
                totaltiket = []
                kategoridibeli = []
                hargaperkategori = []
                key = ['festival', 'cat2', 'cat3', 'cat4']
                for i in range(len(harga)):
                    if int(session['tmptduduk'][key[i]]) != 0:
                        hargaperkategori.append(harga[i][0])
                        prc = harga[i][0]*int(session['tmptduduk'][key[i]])
                        if prc != 0:
                            price.append(prc)
                a = 0
                for i in range(len(harga)):
                    if int(session['tmptduduk'][key[i]]) != 0:
                        totaltiket.append(int(session['tmptduduk'][key[i]]))
                        totalharga = price[a]
                        kategoridibeli.append(key[i])
                        cur.execute('INSERT INTO booking (nama, email, phone, tanggal, totaltiket, totalharga, kategori, lokasi) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)', (nama, email, phone, tanggal, totaltiket[a], totalharga, key[i], lokasi))
                        a += 1
                self.con.mysql.commit()
                cur.execute ('SELECT * FROM booking WHERE nama=%s', (nama,))
                data = cur.fetchone()
                data_report = {
                    'nama': nama,
                    'email': email,
                    'phone': phone,
                    'tanggal': tanggal,
                    'lokasi':lokasi,
                    'totalsemuaharga' : f"{int(session['totalsemuaharga']):,}".replace(',', '.'), 
                    'totalsemuatiket' :session['totalsemuatiket'],
                    'data' : data
                }
                data_tiket = []
                for i in range(len(price)):
                    data_tiket.append({
                        'kategori':kategoridibeli[i],
                        'totalharga':f'{price[i]:,}'.replace(',', '.'),
                        'totaltiket': totaltiket[i],
                        'hargapertiket' : f'{hargaperkategori[i]:,}'.replace(',', '.')
                    })
                
                render = render_template('purchasereport.html', data_report = data_report, data_tiket = data_tiket)
                base_dir = os.path.abspath(os.path.dirname(__file__))  
                pdf_path = os.path.join(base_dir, 'purchasereport.pdf')
                configpdf = pdfkit.configuration(wkhtmltopdf=r'D:\wkhtmltopdf\bin\wkhtmltopdf.exe')
                pdfkit.from_string(render, False, configuration=configpdf)
                pdf_bytes = pdfkit.from_string(render, False, configuration=configpdf)  # Hasil langsung bytes
                response = make_response(pdf_bytes)
                response.headers['Content-Type'] = 'application/pdf'
                response.headers['Content-Disposition'] = 'inline; filename=purchasereport.pdf'
                return response
                
        @self.app.route('/admin/export-pdf', endpoint='export_admin_dashboard_pdf')
        def export_admin_dashboard_pdf():
            if 'user_id' not in session or session.get('role') != 'admin':
                flash('Hanya admin yang bisa mencetak laporan.', 'danger')
                return redirect(url_for('home'))

            cur = self.con.mysql.cursor(pymysql.cursors.DictCursor)

            
            cur.execute("SELECT SUM(totalharga) AS total_pendapatan FROM booking")
            total_pendapatan = cur.fetchone()['total_pendapatan'] or 0

            
            cur.execute("SELECT kategori AS nama_barang, SUM(totaltiket) AS total FROM booking GROUP BY kategori")
            penjualan = cur.fetchall()

        
            cur.execute("SELECT COUNT(*) AS jumlah FROM booking WHERE DATE(tanggal) = CURDATE()")
            pembelian_hari_ini = cur.fetchone()['jumlah']

            
            cur.execute("SELECT id, username, email, phone, role FROM user")
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
            base_dir = os.path.abspath(os.path.dirname(__file__))
            output_dir = os.path.join(base_dir, 'static', 'pdf')
            os.makedirs(output_dir, exist_ok=True)

            filename = f"admin_report_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.pdf"
            filepath = os.path.join(output_dir, filename)

            try:
                pdfkit.from_string(rendered, filepath, configuration=configpdf, options=options)
                flash('Laporan PDF berhasil dibuat.', 'success')
                return send_file(filepath, as_attachment=False)
            except Exception as e:
                import traceback
                print("ERROR saat buat PDF:")
                print(traceback.format_exc())
                flash(f'Gagal membuat PDF: {str(e)}', 'danger')
                return redirect(url_for('admin_dashboard'))

        @self.app.route('/logout')
        def logout():
            session.clear()
            flash('Logout berhasil.', 'info')
            return redirect(url_for('login'))
            # return render_template('home.html', b=logout)

        @self.app.route('/about')
        def about():
            if 'user_id' in session:
                return render_template("about.html", username=session['username'], role=session['role'])
            else:
                return render_template("about.html", username='Login', role=None)

        @self.app.route('/contactus')
        def contact():
            if 'user_id' in session:
                return render_template("contactus.html", username=session['username'], role=session['role'])
            else:
                return render_template("contactus.html", username='Login', role=None)
        
        @self.app.route('/change-password')
        def change_password():
            return render_template('changepassword.html')

        @self.app.route('/change-password/process', methods=['POST'])
        def change_password_process():
            username = request.form.get('username')
            old_password = request.form.get('oldpassword')
            new_password = request.form.get('newpassword')
            pw = hashlib.md5(old_password.encode()).hexdigest()
            password = pw[:30]
            cur = self.con.mysql.cursor(pymysql.cursors.DictCursor)
            cur.execute('SELECT password FROM user WHERE (username = %s OR email = %s OR phone = %s) AND password = %s', (username, username, username, password))
            select = cur.fetchone()
            if select:
                cur.execute("UPDATE user SET password = md5(%s) WHERE (username = %s OR email = %s OR phone = %s) AND password = %s", (new_password, username, username, username, password))
                self.con.mysql.commit()
                return redirect(url_for('login'))
            else:
                flash('Username atau Password Salah!')
                return redirect(url_for('change_password'))

    def run(self):
        self.app.run(debug=True, port=5000)

if __name__ == '__main__':
    app = TiketKonserApp()
    app.run()