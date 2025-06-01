from flask import Flask, render_template, request, redirect, url_for, flash, session
from config import Config
from datetime import datetime

class TiketKonserApp:
    def __init__(self):
        self.app = Flask(__name__)
        self.app.secret_key = "konser_secret_123"
        self.con = Config()
        self.routes()

    def routes(self):
        # Halaman Login & Register
        @self.app.route('/', methods=['GET', 'POST'])
        def home():
            if request.method == 'POST':
                action = request.form.get('action')
                username = request.form.get('username')
                password = request.form.get('password')

                cur = self.con.mysql.cursor()

                if action == 'login':
                    cur.execute("SELECT * FROM user WHERE user = %s AND password = %s", (username, password))
                    user = cur.fetchone()
                    if user:
                        session['user_id'] = user['id']
                        session['username'] = user['user']
                        flash('Login berhasil!', 'success')
                        return redirect(url_for('konser_list'))
                    else:
                        flash('Username atau password salah!', 'danger')
                        return redirect(url_for('home'))

                elif action == 'register':
                    cur.execute("SELECT * FROM user WHERE user = %s", (username,))
                    if cur.fetchone():
                        flash('Username sudah digunakan!', 'danger')
                        return redirect(url_for('home'))

                    cur.execute("INSERT INTO user (user, password) VALUES (%s, %s)", (username, password))
                    self.con.mysql.commit()
                    flash('Registrasi berhasil! Silakan login.', 'success')
                    return redirect(url_for('home'))

                cur.close()

            return render_template('home.html')

        # Daftar konser
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

        # Halaman konser per lokasi (lokasi1.html, lokasi2.html, dst.)
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

        # Form isi data diri dan booking
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

    def run(self):
        self.app.run(debug=True)

if __name__ == '__main__':
    app = TiketKonserApp()
    app.run()
