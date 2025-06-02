from flask import Flask, render_template, request, redirect, url_for, flash, session
from config import Config
from datetime import datetime
import hashlib
import os, pdfkit, pymysql

user = None

class TiketKonserApp:    
    def __init__(self):
        self.app = Flask(__name__)
        self.app.secret_key = "konser_secret_123"
        self.con = Config()
        self.routes()

    def routes(self):
        @self.app.route('/Home')
        def home():
            return render_template("home.html", a=user)

        @self.app.route('/login/')
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
                cur.execute("SELECT * FROM user WHERE username = %s AND password = %s", (username, password))
                row = cur.fetchone()
                global user
                if row:
                    user = row[0]
                    cur.close()
                    return redirect(url_for('home'))
                else:
                    flash('Username atau password salah!', 'danger')
                    cur.close()
                    return redirect(url_for('login'))
        
        @self.app.route('/register/')
        def register():
            return render_template('register.html')
        
        @self.app.route('/register/process', methods=['POST'])
        def registerprocess():
            if request.method == 'POST':
                username = request.form['username']
                password = request.form['password']
                confirmpw = request.form["confirmpw"]
                phone = request.form["phone"]
                cur = self.con.mysql.cursor()
                if password == confirmpw:
                    # try:
                    cur.execute(
                        'INSERT INTO user (username, password, confirmpw, phone) VALUES (%s, md5(%s), md5(%s), %s)',
                        (username, password, confirmpw, phone)
                    )
                    self.con.mysql.commit()
                    cur.close()
                    return redirect(url_for('login'))
                    # except Exception as e:
                    user = None
                    flash('Registrasi Gagal!', 'danger')
                    cur.close()
                    return redirect(url_for('register'))
                else:
                    flash('Konfirmasi password salah!', 'danger')
                    return redirect(url_for('register'))
            
        @self.app.route('/konser')
        def konser_list():
            if 'user_id' not in session:
                flash('Silakan login terlebih dahulu.', 'warning')
                return redirect(url_for('home'))

            cur = self.con.mysql.cursor()
            cur.execute("SELECT * FROM konser")
            konser = cur.fetchall()
            cur.close()
            return render_template('lokasi.html', konser=konser)

        @self.app.route('/konser/<int:konser_id>')
        def konser_detail(konser_id):
            if 'user_id' not in session:
                flash('Silakan login terlebih dahulu.', 'warning')
                return redirect(url_for('home'))

            cur = self.con.mysql.cursor()
            cur.execute("SELECT * FROM section WHERE idkonser = %s", (konser_id,))
            sections = cur.fetchall()
            cur.close()
            return render_template(f'lokasi{konser_id}.html', sections=sections, konser_id=konser_id)

        @self.app.route('/pesan/<int:konser_id>/<int:section_id>', methods=['GET', 'POST'])
        def booking(konser_id, section_id):
            if 'user_id' not in session:
                flash('Silakan login terlebih dahulu.', 'warning')
                return redirect(url_for('home'))

            if request.method == 'POST':
                nama = request.form['nama']
                hp = request.form['hp']
                email = request.form['email']
                tanggal = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                action = request.form.get('action')

                cur = self.con.mysql.cursor(dictionary=True)
                cur.execute("SELECT quota, sold FROM section WHERE id = %s", (section_id,))
                section = cur.fetchone()

                festival = int(request.form.get('festival', 0))
                cat2 = int(request.form.get('cat2', 0))
                cat3 = int(request.form.get('cat3', 0))
                cat4 = int(request.form.get('cat4', 0))
                total_tiket = festival + cat2 + cat3 + cat4

                if total_tiket == 0:
                    flash('Jumlah tiket tidak boleh kurang dari 1!', 'danger')
                    cur.close()
                    return redirect(url_for('konser_detail', konser_id=konser_id))

                if section['sold'] + total_tiket > section['quota']:
                    flash('Section sudah penuh!', 'danger')
                    cur.close()
                    return redirect(url_for('konser_detail', konser_id=konser_id))

                harga_festival = 3220000
                harga_cat2 = 2702500
                harga_cat3 = 2242500
                harga_cat4 = 1552500

                if festival > 0:
                    cur.execute(
                        "INSERT INTO tiket (user_id, konser_id, section_id, nama, hp, email, tanggal, jumlah, harga) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                        (session['user_id'], konser_id, section_id, nama, hp, email, tanggal, festival, harga_festival)
                    )
                if cat2 > 0:
                    cur.execute(
                        "INSERT INTO tiket (user_id, konser_id, section_id, nama, hp, email, tanggal, jumlah, harga) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                        (session['user_id'], konser_id, section_id, nama, hp, email, tanggal, cat2, harga_cat2)
                    )
                if cat3 > 0:
                    cur.execute(
                        "INSERT INTO tiket (user_id, konser_id, section_id, nama, hp, email, tanggal, jumlah, harga) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                        (session['user_id'], konser_id, section_id, nama, hp, email, tanggal, cat3, harga_cat3)
                    )
                if cat4 > 0:
                    cur.execute(
                        "INSERT INTO tiket (user_id, konser_id, section_id, nama, hp, email, tanggal, jumlah, harga) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                        (session['user_id'], konser_id, section_id, nama, hp, email, tanggal, cat4, harga_cat4)
                    )

                cur.execute("UPDATE section SET sold = sold + %s WHERE id = %s", (total_tiket, section_id))
                self.con.mysql.commit()
                cur.close()

                session['tiket_data'] = {
                    'festival': {'jumlah': festival, 'harga': harga_festival},
                    'cat2': {'jumlah': cat2, 'harga': harga_cat2},
                    'cat3': {'jumlah': cat3, 'harga': harga_cat3},
                    'cat4': {'jumlah': cat4, 'harga': harga_cat4}
                }

                if action == 'Invoice':
                    return redirect(url_for('pdf'))

                flash("See you on the concert!", "success")
                return redirect(url_for('home'))

            return render_template('datadiri.html', konser_id=konser_id, section_id=section_id)

        @self.app.route('/purchase-report')
        def pdf():
            tiket_data = session.get('tiket_data', {})
            total_harga = sum(info['jumlah'] * info['harga'] for info in tiket_data.values())
            jumlah_tiket = sum(info['jumlah'] for info in tiket_data.values())

            rendered = render_template(
                'purchasereport.html',
                data=tiket_data,
                total_harga=total_harga,
                jumlah_tiket=jumlah_tiket
            )
            configpdf = pdfkit.configuration(wkhtmltopdf='C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe')
            filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            filepath = f"uasproject/static/pdf/{filename}"
            pdfkit.from_string(rendered, filepath, configuration=configpdf)
            flash('Success Download Invoice', 'success')
            return redirect(url_for('home'))

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
