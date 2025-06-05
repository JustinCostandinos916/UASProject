from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from config import Config
from datetime import datetime
from collections import OrderedDict
import hashlib
import os, pdfkit, pymysql

user = None
if user is None:
    user = 'Login'
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
                    try:
                        cur.execute(
                            'INSERT INTO user (username, password, confirmpw, phone) VALUES (%s, md5(%s), md5(%s), %s)',
                            (username, password, confirmpw, phone)
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
        
        @self.app.route('/konser<int:konser_id>/')
        def konser_detail(konser_id):
            if user == 'Login':
                flash('Silakan login terlebih dahulu.', 'danger')
                return redirect(url_for('login'))
            else:
                return render_template(f'lokasi{konser_id}.html')

        @self.app.route('/pesan/')
        def datadiri():
            konser_id = session.get('konser_id')
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
                tanggal = datetime.now().strftime('%Y-%m-%d')
                cur = self.con.mysql.cursor()
                cur.execute('SELECT harga FROM harga_per_kategori WHERE lokasi_id = %s', (lokasi_id,))
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
                    'totalsemuaharga' : session['totalsemuaharga'], 
                    'totalsemuatiket' :session['totalsemuatiket'],
                    'data' : data
                }
                data_tiket = []
                for i in range(len(price)):
                    data_tiket.append({
                        'kategori':kategoridibeli[i],
                        'totalharga':price[i],
                        'totaltiket': totaltiket[i],
                        'hargapertiket' : hargaperkategori[i]
                    })
                
                render = render_template('purchasereport.html', data_report = data_report, data_tiket = data_tiket)
                base_dir = os.path.abspath(os.path.dirname(__file__))  
                pdf_path = os.path.join(base_dir, 'purchasereport.pdf')
                configpdf = pdfkit.configuration(wkhtmltopdf=r'D:\wkhtmltopdf\bin\wkhtmltopdf.exe')
                pdfkit.from_string(render, pdf_path, configuration=configpdf)
                return send_file('purchasereport.pdf', as_attachment=False)
                # return render_template('home.html', b = session['totalsemuaharga'])
                

        # @self.app.route('/pesan/<int:konser_id>/<int:section_id>', methods=['GET', 'POST'])
        # def booking(konser_id, section_id):
        #     if 'user_id' not in session:
        #         flash('Silakan login terlebih dahulu.', 'warning')
        #         return redirect(url_for('home'))

        #     if request.method == 'POST':
        #         nama = request.form['nama']
        #         hp = request.form['hp']
        #         email = request.form['email']
        #         tanggal = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        #         action = request.form.get('action')

        #         cur = self.con.mysql.cursor(dictionary=True)
        #         cur.execute("SELECT quota, sold FROM section WHERE id = %s", (section_id,))
        #         section = cur.fetchone()

        #         festival = int(request.form.get('festival', 0))
        #         cat2 = int(request.form.get('cat2', 0))
        #         cat3 = int(request.form.get('cat3', 0))
        #         cat4 = int(request.form.get('cat4', 0))
        #         total_tiket = festival + cat2 + cat3 + cat4

        #         if total_tiket == 0:
        #             flash('Jumlah tiket tidak boleh kurang dari 1!', 'danger')
        #             cur.close()
        #             return redirect(url_for('konser_detail', konser_id=konser_id))

        #         if section['sold'] + total_tiket > section['quota']:
        #             flash('Section sudah penuh!', 'danger')
        #             cur.close()
        #             return redirect(url_for('konser_detail', konser_id=konser_id))

        #         harga_festival = 3220000
        #         harga_cat2 = 2702500
        #         harga_cat3 = 2242500
        #         harga_cat4 = 1552500

        #         if festival > 0:
        #             cur.execute(
        #                 "INSERT INTO tiket (user_id, konser_id, section_id, nama, hp, email, tanggal, jumlah, harga) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        #                 (session['user_id'], konser_id, section_id, nama, hp, email, tanggal, festival, harga_festival)
        #             )
        #         if cat2 > 0:
        #             cur.execute(
        #                 "INSERT INTO tiket (user_id, konser_id, section_id, nama, hp, email, tanggal, jumlah, harga) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        #                 (session['user_id'], konser_id, section_id, nama, hp, email, tanggal, cat2, harga_cat2)
        #             )
        #         if cat3 > 0:
        #             cur.execute(
        #                 "INSERT INTO tiket (user_id, konser_id, section_id, nama, hp, email, tanggal, jumlah, harga) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        #                 (session['user_id'], konser_id, section_id, nama, hp, email, tanggal, cat3, harga_cat3)
        #             )
        #         if cat4 > 0:
        #             cur.execute(
        #                 "INSERT INTO tiket (user_id, konser_id, section_id, nama, hp, email, tanggal, jumlah, harga) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        #                 (session['user_id'], konser_id, section_id, nama, hp, email, tanggal, cat4, harga_cat4)
        #             )

        #         cur.execute("UPDATE section SET sold = sold + %s WHERE id = %s", (total_tiket, section_id))
        #         self.con.mysql.commit()
        #         cur.close()

        #         session['tiket_data'] = {
        #             'festival': {'jumlah': festival, 'harga': harga_festival},
        #             'cat2': {'jumlah': cat2, 'harga': harga_cat2},
        #             'cat3': {'jumlah': cat3, 'harga': harga_cat3},
        #             'cat4': {'jumlah': cat4, 'harga': harga_cat4}
        #         }

        #         if action == 'Invoice':
        #             return redirect(url_for('pdf'))

        #         flash("See you on the concert!", "success")
        #         return redirect(url_for('home'))

        #     return render_template('datadiri.html', konser_id=konser_id, section_id=section_id)

        # @self.app.route('/purchase-report')
        # def pdf():
        #     tiket_data = session.get('tiket_data', {})
        #     total_harga = sum(info['jumlah'] * info['harga'] for info in tiket_data.values())
        #     jumlah_tiket = sum(info['jumlah'] for info in tiket_data.values())

        #     rendered = render_template(
        #         'purchasereport.html',
        #         data=tiket_data,
        #         total_harga=total_harga,
        #         jumlah_tiket=jumlah_tiket
        #     )
        #     configpdf = pdfkit.configuration(wkhtmltopdf='C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe')
        #     filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        #     filepath = f"uasproject/static/pdf/{filename}"
        #     pdfkit.from_string(rendered, filepath, configuration=configpdf)
        #     flash('Success Download Invoice', 'success')
        #     return redirect(url_for('home'))

        @self.app.route('/logout')
        def logout():
            session.clear()
            flash('Logout berhasil.', 'info')
            return redirect(url_for('home'))

        @self.app.route('/about')
        def about():
            return render_template('about.html', a=user)

        @self.app.route('/contact')
        def contact():
            return render_template('contactus.html')

    def run(self):
        self.app.run(debug=True, port=5000)

if __name__ == '__main__':
    app = TiketKonserApp()
    app.run()