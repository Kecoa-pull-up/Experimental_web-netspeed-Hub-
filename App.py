from flask import Flask, render_template, request, redirect, url_for, session
from database import get_connection

app = Flask(__name__)
app.secret_key = "ganti-dengan-teks-rahasia-apapun"  # wajib ada untuk session

@app.context_processor
def inject_notifikasi():
    if "username" not in session:
        return {}

    conn = get_connection()
    cursor = conn.cursor()
    notif = 0

    if session.get("role") in ["admin", "teknisi"]:
        cursor.execute(
            "SELECT COUNT(*) FROM tiket_kendala WHERE status = 'Dilaporkan'"
        )
        notif = cursor.fetchone()[0]

    elif session.get("role") == "pelanggan":
        cursor.execute(
            "SELECT COUNT(*) FROM tiket_kendala WHERE pelanggan_id = ? AND status = 'Sedang Ditangani'",
            (session.get("pelanggan_id"),)
        )
        notif = cursor.fetchone()[0]

    conn.close()
    return {"jumlah_notifikasi": notif}

@app.route("/")
def login():
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def proses_login():
    username = request.form["username"]
    password = request.form["password"]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM admin WHERE username = ? AND password = ?",
        (username, password)
    )
    user_staf = cursor.fetchone()

    if user_staf:
        session["username"] = user_staf["username"]
        session["role"] = user_staf["role"]
        session["nama_lengkap"] = user_staf["nama_lengkap"]

        if user_staf["role"] == "teknisi":
            session["teknisi_id"] = user_staf["teknisi_id"]
            conn.close()
            return redirect(url_for("dashboard_teknisi"))
        else:
            conn.close()
            return redirect(url_for("dashboard"))

    cursor.execute(
        "SELECT * FROM user_pelanggan WHERE username = ? AND password = ?",
        (username, password)
    )
    user_pelanggan = cursor.fetchone()
    conn.close()

    if user_pelanggan:
        session["username"] = user_pelanggan["username"]
        session["role"] = "pelanggan"
        session["pelanggan_id"] = user_pelanggan["pelanggan_id"]
        return redirect(url_for("dashboard_pelanggan"))

    return render_template("login.html", error="Username atau password salah")

@app.route("/dashboard")
def dashboard():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM pelanggan")
    total_pelanggan = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM pelanggan WHERE status = 'Aktif'")
    pelanggan_aktif = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tagihan WHERE status_bayar = 'Belum Bayar'")
    tagihan_pending = cursor.fetchone()[0]

    cursor.execute("SELECT nama, paket, status FROM pelanggan ORDER BY id DESC LIMIT 5")
    aktivitas_terkini = cursor.fetchall()

    cursor.execute("""
        SELECT SUM(jumlah) FROM tagihan
        WHERE status_bayar = 'Lunas'
    """)
    pendapatan_bulan_ini = cursor.fetchone()[0]
    if pendapatan_bulan_ini is None:
        pendapatan_bulan_ini = 0

    paket_list = ["10 Mbps", "20 Mbps", "50 Mbps", "100 Mbps"]
    paket_count = []
    for paket in paket_list:
        cursor.execute("SELECT COUNT(*) FROM pelanggan WHERE paket = ?", (paket,))
        paket_count.append(cursor.fetchone()[0])
    conn.close()

    return render_template(
        "dashboard.html",
        username=session["username"],
        total_pelanggan=total_pelanggan,
        pelanggan_aktif=pelanggan_aktif,
        tagihan_pending=tagihan_pending,
        aktivitas_terkini=aktivitas_terkini,
        paket_count=paket_count,
        pendapatan_bulan_ini=pendapatan_bulan_ini
    )

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))

@app.route("/pelanggan")
def pelanggan():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    filter_status = request.args.get("filter", "semua")
    kata_cari = request.args.get("cari", "")

    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM pelanggan WHERE nama LIKE ?"
    params = [f"%{kata_cari}%"]

    if filter_status == "aktif":
        query += " AND status = 'Aktif'"
    elif filter_status == "nonaktif":
        query += " AND status = 'Nonaktif'"

    cursor.execute(query, params)
    daftar_pelanggan = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM pelanggan")
    jumlah_semua = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM pelanggan WHERE status = 'Aktif'")
    jumlah_aktif = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM pelanggan WHERE status = 'Nonaktif'")
    jumlah_nonaktif = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "pelanggan.html",
        daftar_pelanggan=daftar_pelanggan,
        filter_status=filter_status,
        kata_cari=kata_cari,
        jumlah_semua=jumlah_semua,
        jumlah_aktif=jumlah_aktif,
        jumlah_nonaktif=jumlah_nonaktif
    )

@app.route("/pelanggan/tambah", methods=["GET", "POST"])
def tambah_pelanggan():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    if request.method == "POST":
        nama = request.form["nama"]
        no_hp = request.form["no_hp"]
        paket = request.form["paket"]
        status = request.form["status"]

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO pelanggan (nama, no_hp, paket, status) VALUES (?, ?, ?, ?)",
            (nama, no_hp, paket, status)
        )
        conn.commit()
        conn.close()

        return redirect(url_for("pelanggan"))

    return render_template("tambah_pelanggan.html")

@app.route("/pelanggan/edit/<int:id>", methods=["GET", "POST"])
def edit_pelanggan(id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        nama = request.form["nama"]
        no_hp = request.form["no_hp"]
        paket = request.form["paket"]
        status = request.form["status"]

        cursor.execute(
            "UPDATE pelanggan SET nama = ?, no_hp = ?, paket = ?, status = ? WHERE id = ?",
            (nama, no_hp, paket, status, id)
        )
        conn.commit()
        conn.close()
        return redirect(url_for("pelanggan"))

    cursor.execute("SELECT * FROM pelanggan WHERE id = ?", (id,))
    data_pelanggan = cursor.fetchone()
    conn.close()

    return render_template("edit_pelanggan.html", p=data_pelanggan)

@app.route("/pelanggan/hapus/<int:id>")
def hapus_pelanggan(id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM tiket_kendala WHERE pelanggan_id = ?", (id,))
    cursor.execute("DELETE FROM tagihan WHERE pelanggan_id = ?", (id,))
    cursor.execute("DELETE FROM user_pelanggan WHERE pelanggan_id = ?", (id,))
    cursor.execute("DELETE FROM pelanggan WHERE id = ?", (id,))

    conn.commit()
    conn.close()

    return redirect(url_for("pelanggan"))

@app.route("/tagihan")
def tagihan():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    filter_status = request.args.get("filter", "semua")
    kata_cari = request.args.get("cari", "")

    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT tagihan.id, pelanggan.nama, tagihan.jumlah,
               tagihan.jatuh_tempo, tagihan.status_bayar
        FROM tagihan
        JOIN pelanggan ON tagihan.pelanggan_id = pelanggan.id
        WHERE pelanggan.nama LIKE ?
    """
    params = [f"%{kata_cari}%"]

    if filter_status == "lunas":
        query += " AND tagihan.status_bayar = 'Lunas'"
    elif filter_status == "belum_bayar":
        query += " AND tagihan.status_bayar = 'Belum Bayar'"

    cursor.execute(query, params)
    daftar_tagihan = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM tagihan")
    jumlah_semua = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tagihan WHERE status_bayar = 'Lunas'")
    jumlah_lunas = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tagihan WHERE status_bayar = 'Belum Bayar'")
    jumlah_belum_bayar = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "tagihan.html",
        daftar_tagihan=daftar_tagihan,
        filter_status=filter_status,
        kata_cari=kata_cari,
        jumlah_semua=jumlah_semua,
        jumlah_lunas=jumlah_lunas,
        jumlah_belum_bayar=jumlah_belum_bayar
    )

@app.route("/tagihan/tambah", methods=["GET", "POST"])
def tambah_tagihan():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        pelanggan_id = request.form["pelanggan_id"]
        jumlah = request.form["jumlah"]
        jatuh_tempo = request.form["jatuh_tempo"]

        cursor.execute(
            "INSERT INTO tagihan (pelanggan_id, jumlah, jatuh_tempo) VALUES (?, ?, ?)",
            (pelanggan_id, jumlah, jatuh_tempo)
        )
        conn.commit()
        conn.close()
        return redirect(url_for("tagihan"))

    cursor.execute("SELECT * FROM pelanggan")
    daftar_pelanggan = cursor.fetchall()
    conn.close()

    return render_template("tambah_tagihan.html", daftar_pelanggan=daftar_pelanggan)

@app.route("/tagihan/bayar/<int:id>", methods=["GET", "POST"])
def bayar_tagihan(id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    from datetime import date
    hari_ini = date.today().isoformat()

    conn = get_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        metode_bayar = request.form["metode_bayar"]

        cursor.execute(
            "UPDATE tagihan SET status_bayar = 'Lunas', metode_bayar = ?, tanggal_bayar = ? WHERE id = ?",
            (metode_bayar, hari_ini, id)
        )
        conn.commit()
        conn.close()
        return redirect(url_for("tagihan"))

    cursor.execute("""
        SELECT tagihan.id, pelanggan.nama, tagihan.jumlah
        FROM tagihan JOIN pelanggan ON tagihan.pelanggan_id = pelanggan.id
        WHERE tagihan.id = ?
    """, (id,))
    data_tagihan = cursor.fetchone()
    conn.close()

    return render_template("bayar_tagihan.html", t=data_tagihan)

@app.route("/jaringan")
def jaringan():
    if session.get("role") not in ["admin", "teknisi"]:
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM titik_jaringan")
    daftar_titik = cursor.fetchall()
    conn.close()

    titik_json = [dict(t) for t in daftar_titik]

    return render_template("jaringan.html", titik_json=titik_json)


@app.route("/jaringan/tambah", methods=["POST"])
def tambah_titik():
    if session.get("role") not in ["admin", "teknisi"]:
        return redirect(url_for("login"))

    from datetime import date
    hari_ini = date.today().isoformat()

    nama_lokasi = request.form["nama_lokasi"]
    latitude = request.form["latitude"]
    longitude = request.form["longitude"]
    status = request.form["status"]
    keterangan = request.form["keterangan"]

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO titik_jaringan (nama_lokasi, latitude, longitude, status, keterangan, tanggal_input) VALUES (?, ?, ?, ?, ?, ?)",
        (nama_lokasi, latitude, longitude, status, keterangan, hari_ini)
    )
    conn.commit()
    conn.close()

    return redirect(url_for("jaringan"))


@app.route("/jaringan/hapus/<int:id>")
def hapus_titik(id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM titik_jaringan WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    return redirect(url_for("jaringan"))

@app.route("/inventaris")
def inventaris():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM barang")
    daftar_barang = cursor.fetchall()
    conn.close()

    return render_template("inventaris.html", daftar_barang=daftar_barang)


@app.route("/inventaris/ubah/<int:id>", methods=["POST"])
def ubah_stok(id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    from datetime import date
    hari_ini = date.today().isoformat()

    jenis = request.form["jenis"]
    jumlah = int(request.form["jumlah"])

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT stok FROM barang WHERE id = ?", (id,))
    barang = cursor.fetchone()
    stok_sekarang = barang["stok"]

    if jenis == "tambah":
        stok_baru = stok_sekarang + jumlah
    else:
        stok_baru = max(0, stok_sekarang - jumlah)

    cursor.execute("UPDATE barang SET stok = ? WHERE id = ?", (stok_baru, id))

    cursor.execute(
        "INSERT INTO riwayat_barang (barang_id, jenis_perubahan, jumlah, tanggal) VALUES (?, ?, ?, ?)",
        (id, "Tambah" if jenis == "tambah" else "Kurang", jumlah, hari_ini)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("inventaris"))


@app.route("/inventaris/riwayat/<int:id>")
def riwayat_barang(id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM barang WHERE id = ?", (id,))
    barang = cursor.fetchone()

    cursor.execute(
        "SELECT * FROM riwayat_barang WHERE barang_id = ? ORDER BY id DESC",
        (id,)
    )
    daftar_riwayat = cursor.fetchall()

    conn.close()

    return render_template(
        "riwayat_barang.html",
        barang=barang,
        daftar_riwayat=daftar_riwayat
    )

@app.route("/teknisi")
def teknisi():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    from datetime import date
    hari_ini = date.today().isoformat()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM teknisi")
    daftar_teknisi = cursor.fetchall()

    cursor.execute(
        "SELECT teknisi_id, hadir FROM absensi WHERE tanggal = ?", (hari_ini,)
    )
    absensi_rows = cursor.fetchall()
    status_absensi = {row["teknisi_id"]: row["hadir"] for row in absensi_rows}

    conn.close()

    return render_template(
        "teknisi.html",
        daftar_teknisi=daftar_teknisi,
        status_absensi=status_absensi,
        hari_ini=hari_ini
    )


@app.route("/teknisi/absen/<int:id>")
def toggle_absen(id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    from datetime import date
    hari_ini = date.today().isoformat()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM absensi WHERE teknisi_id = ? AND tanggal = ?",
        (id, hari_ini)
    )
    data_absen = cursor.fetchone()

    if data_absen:
        status_baru = 0 if data_absen["hadir"] == 1 else 1
        cursor.execute(
            "UPDATE absensi SET hadir = ? WHERE id = ?",
            (status_baru, data_absen["id"])
        )
    else:
        cursor.execute(
            "INSERT INTO absensi (teknisi_id, tanggal, hadir) VALUES (?, ?, 1)",
            (id, hari_ini)
        )

    conn.commit()
    conn.close()

    return redirect(url_for("teknisi"))


@app.route("/teknisi/tambah", methods=["GET", "POST"])
def tambah_teknisi():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    if request.method == "POST":
        nama = request.form["nama"]
        spesialisasi = request.form["spesialisasi"]
        no_hp = request.form["no_hp"]

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO teknisi (nama, spesialisasi, no_hp) VALUES (?, ?, ?)",
            (nama, spesialisasi, no_hp)
        )
        conn.commit()
        conn.close()
        return redirect(url_for("teknisi"))

    return render_template("tambah_teknisi.html")


@app.route("/teknisi/hapus/<int:id>")
def hapus_teknisi(id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM teknisi WHERE id = ?", (id,))
    cursor.execute("DELETE FROM absensi WHERE teknisi_id = ?", (id,))
    conn.commit()
    conn.close()

    return redirect(url_for("teknisi"))

@app.route("/laporan")
def laporan():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT SUM(jumlah) FROM tagihan WHERE status_bayar = 'Lunas'")
    total_pemasukan = cursor.fetchone()[0]
    if total_pemasukan is None:
        total_pemasukan = 0

    bulan_list = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
    nama_bulan = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
    pemasukan_per_bulan = []

    for bulan in bulan_list:
        cursor.execute("""
            SELECT SUM(jumlah) FROM tagihan
            WHERE status_bayar = 'Lunas' AND jatuh_tempo LIKE ?
        """, (f"2026-{bulan}%",))
        hasil = cursor.fetchone()[0]
        pemasukan_per_bulan.append(hasil if hasil else 0)

    conn.close()

    pengeluaran_tetap = 31200000
    laba_bersih = total_pemasukan - pengeluaran_tetap

    cursor2 = get_connection().cursor()
    cursor2.execute("SELECT nama, spesialisasi FROM teknisi")
    daftar_teknisi_gaji = cursor2.fetchall()

    gaji_total = 16000000
    jumlah_teknisi_aktif = len(daftar_teknisi_gaji) if len(daftar_teknisi_gaji) > 0 else 1
    gaji_per_orang = gaji_total // jumlah_teknisi_aktif

    rincian_gaji_html = ""
    for t in daftar_teknisi_gaji:
        rincian_gaji_html += f"{t['nama']} ({t['spesialisasi']}): Rp {gaji_per_orang:,}<br>"

    rincian_pengeluaran = [
        {"kategori": "Gaji Teknisi", "jumlah": 16000000, "persen": 51,
         "detail": f"Dibagi rata ke {jumlah_teknisi_aktif} teknisi aktif, masing-masing menerima Rp {gaji_per_orang:,}.<br><br>" + rincian_gaji_html},
        {"kategori": "Pembelian Alat", "jumlah": 9000000, "persen": 29,
         "detail": (
             "Router Mikrotik RB750 (2 unit) — estimasi Rp 1.200.000/unit: Rp 2.400.000<br>"
             "Kabel UTP Cat6 (10 roll) — estimasi Rp 450.000/roll: Rp 4.500.000<br>"
             "ODP 8 Port (4 unit) — estimasi Rp 350.000/unit: Rp 1.400.000<br>"
             "Konektor RJ45 (100 pcs) — estimasi Rp 1.000/pcs hingga Rp 700.000<br>"
             "<br><em>Estimasi berdasarkan harga pasaran umum, dapat bervariasi tergantung toko/wilayah.</em>"
         )},
        {"kategori": "Sewa Server", "jumlah": 3500000, "persen": 11,
         "detail": "Biaya sewa server dan hosting sistem bulanan, termasuk biaya domain dan backup data."},
        {"kategori": "Lain-lain", "jumlah": 2700000, "persen": 9,
         "detail": "Biaya operasional tambahan, termasuk transportasi teknisi dan alat tulis kantor (ATK)."},
    ]

    return render_template(
        "laporan.html",
        total_pemasukan=total_pemasukan,
        pengeluaran_tetap=pengeluaran_tetap,
        laba_bersih=laba_bersih,
        nama_bulan=nama_bulan,
        pemasukan_per_bulan=pemasukan_per_bulan,
        rincian_pengeluaran=rincian_pengeluaran
    )
@app.route("/teknisi-area/dashboard")
def dashboard_teknisi():
    if session.get("role") != "teknisi":
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()

    from datetime import date
    hari_ini = date.today().isoformat()

    cursor.execute(
        "SELECT * FROM absensi WHERE teknisi_id = ? AND tanggal = ?",
        (session["teknisi_id"], hari_ini)
    )
    absen_hari_ini = cursor.fetchone()
    sudah_absen = absen_hari_ini["hadir"] == 1 if absen_hari_ini else False

    cursor.execute("SELECT COUNT(*) FROM titik_jaringan WHERE status = 'Rusak'")
    jumlah_gangguan = cursor.fetchone()[0]

    cursor.execute(
        "SELECT tanggal, hadir FROM absensi WHERE teknisi_id = ?",
        (session["teknisi_id"],)
    )
    riwayat_absen_rows = cursor.fetchall()
    riwayat_absen_json = {row["tanggal"]: row["hadir"] for row in riwayat_absen_rows}

    conn.close()

    return render_template(
        "dashboard_teknisi.html",
        nama_lengkap=session.get("nama_lengkap"),
        sudah_absen=sudah_absen,
        jumlah_gangguan=jumlah_gangguan,
        hari_ini=hari_ini,
        riwayat_absen_json=riwayat_absen_json
    )

@app.route("/teknisi-area/absen")
def absen_diri_sendiri():
    if session.get("role") != "teknisi":
        return redirect(url_for("login"))

    from datetime import date
    hari_ini = date.today().isoformat()
    teknisi_id = session["teknisi_id"]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM absensi WHERE teknisi_id = ? AND tanggal = ?",
        (teknisi_id, hari_ini)
    )
    data_absen = cursor.fetchone()

    if data_absen:
        cursor.execute("UPDATE absensi SET hadir = 1 WHERE id = ?", (data_absen["id"],))
    else:
        cursor.execute(
            "INSERT INTO absensi (teknisi_id, tanggal, hadir) VALUES (?, ?, 1)",
            (teknisi_id, hari_ini)
        )

    conn.commit()
    conn.close()

    return redirect(url_for("dashboard_teknisi"))
@app.route("/daftar", methods=["GET", "POST"])
def daftar_pelanggan_mandiri():
    if request.method == "POST":
        nama = request.form["nama"]
        no_hp = request.form["no_hp"]
        paket = request.form["paket"]
        username = request.form["username"]
        password = request.form["password"]

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO pelanggan (nama, no_hp, paket, status) VALUES (?, ?, ?, ?)",
            (nama, no_hp, paket, "Aktif")
        )
        pelanggan_id_baru = cursor.lastrowid

        try:
            cursor.execute(
                "INSERT INTO user_pelanggan (username, password, pelanggan_id) VALUES (?, ?, ?)",
                (username, password, pelanggan_id_baru)
            )
            conn.commit()
            conn.close()
            return render_template("login.html", error="Pendaftaran berhasil! Silakan login.")
        except sqlite3.IntegrityError:
            conn.close()
            return render_template("daftar.html", error="Username sudah digunakan, mohon pilih username lain.")

    return render_template("daftar.html")


@app.route("/pelanggan-area/dashboard")
def dashboard_pelanggan():
    if session.get("role") != "pelanggan":
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM pelanggan WHERE id = ?", (session["pelanggan_id"],))
    data_diri = cursor.fetchone()

    cursor.execute(
        "SELECT * FROM tagihan WHERE pelanggan_id = ? ORDER BY id DESC",
        (session["pelanggan_id"],)
    )
    daftar_tagihan_saya = cursor.fetchall()

    conn.close()

    return render_template(
        "dashboard_pelanggan.html",
        data_diri=data_diri,
        daftar_tagihan_saya=daftar_tagihan_saya
    )

@app.route("/pelanggan-area/lapor", methods=["GET", "POST"])
def lapor_kendala():
    if session.get("role") != "pelanggan":
        return redirect(url_for("login"))

    from datetime import date

    if request.method == "POST":
        deskripsi = request.form["deskripsi"]

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tiket_kendala (pelanggan_id, deskripsi, tanggal_lapor) VALUES (?, ?, ?)",
            (session["pelanggan_id"], deskripsi, date.today().isoformat())
        )
        conn.commit()
        conn.close()
        return redirect(url_for("dashboard_pelanggan"))

    return render_template("lapor_kendala.html")
@app.route("/tiket")
def tiket():
    if session.get("role") not in ["admin", "teknisi"]:
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT tiket_kendala.id, pelanggan.nama, tiket_kendala.deskripsi,
               tiket_kendala.status, tiket_kendala.tanggal_lapor
        FROM tiket_kendala
        JOIN pelanggan ON tiket_kendala.pelanggan_id = pelanggan.id
        ORDER BY tiket_kendala.id DESC
    """)
    daftar_tiket = cursor.fetchall()
    conn.close()

    return render_template("tiket.html", daftar_tiket=daftar_tiket)

@app.route("/tiket/update/<int:id>", methods=["POST"])
def update_status_tiket(id):
    if session.get("role") not in ["admin", "teknisi"]:
        return redirect(url_for("login"))

    status_baru = request.form["status"]

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE tiket_kendala SET status = ? WHERE id = ?",
        (status_baru, id)
    )
    conn.commit()
    conn.close()

    return redirect(url_for("tiket"))

@app.route("/jaringan/update-status/<int:id>", methods=["POST"])
def update_status_titik(id):
    if session.get("role") not in ["admin", "teknisi"]:
        return redirect(url_for("login"))

    status_baru = request.form["status"]

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE titik_jaringan SET status = ? WHERE id = ?",
        (status_baru, id)
    )
    conn.commit()
    conn.close()

    return redirect(url_for("jaringan"))

if __name__ == "__main__":
    app.run(debug=True)