from flask import Flask, render_template, request, redirect, url_for, flash, session
from config import Config
from datetime import datetime
import hashlib
import os, pdfkit

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
            return render_template('loginregister.html', form="login")
        
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
            return render_template('loginregister.html', form="register")
        
        @self.app.route('/register/process', methods=['POST'])
        def registerprocess():
            if request.method == 'POST':
                username = request.form['username']
                password = request.form['password']
                confirmpw = request.form["confirmpw"]
                phone = request.form["phone"]
                cur = self.con.mysql.cursor()
                if password == confirmpw:
                    try:
                        cur.execute('INSERT INTO user (username, password, confirmpw, phone) VALUES (%s, md5(%s), md5(%s), %s)', (username, password, confirmpw, phone))
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

                cur = self.con.mysql.cursor()
                cur.execute("SELECT quota, sold FROM section WHERE id = %s", (section_id,))
                section = cur.fetchone()

                if section['sold'] >= section['quota']:
                    flash('Section sudah penuh!', 'danger')
                    return redirect(url_for('konser_detail', konser_id=konser_id))

                cur.execute("""
                    INSERT INTO bookiong (userid, idkonser, idsection, nama, hp, email, tanggalbooking)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (session['user_id'], konser_id, section_id, nama, hp, email, tanggal))

                cur.execute("UPDATE section SET sold = sold + 1 WHERE id = %s", (section_id,))
                self.con.mysql.commit()
                cur.close()

                flash("See you on the concert!", "success")
                return redirect(url_for('home'))

            return render_template('datadiri.html', konser_id=konser_id, section_id=section_id)

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
        
        @self.app.route('/invoice')
        def pdf():
            cur         = self.con.mysql.cursor()
            cur.execute('SELECT * FROM booking')
            data        = cur.fetchall()
            cur.close()
            rendered = render_template('Invoice.html', data=data)
            configpdf = pdfkit.configuration(wkhtmltopdf = 'C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe')
            pdfkit.from_string(rendered, 'uasproject/static/pdf/report.pdf',configuration= configpdf)
            flash('Success Download Invoice', 'success')
            return redirect(url_for('home'))

    def run(self):
        self.app.run(debug=True)

if __name__ == '__main__':
    app = TiketKonserApp()
    app.run()

