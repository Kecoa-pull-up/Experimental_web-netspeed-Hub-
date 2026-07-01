import sqlite3

def get_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # ===== BAGIAN 1: BUAT SELURUH TABEL TERLEBIH DAHULU =====

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    try:
        cursor.execute("ALTER TABLE admin ADD COLUMN role TEXT DEFAULT 'admin'")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE admin ADD COLUMN nama_lengkap TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE admin ADD COLUMN teknisi_id INTEGER")
    except sqlite3.OperationalError:
        pass

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_pelanggan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            pelanggan_id INTEGER NOT NULL,
            FOREIGN KEY (pelanggan_id) REFERENCES pelanggan (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pelanggan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT NOT NULL,
            no_hp TEXT,
            paket TEXT,
            status TEXT DEFAULT 'Aktif'
        )
    """)
    try:
        cursor.execute("ALTER TABLE tagihan ADD COLUMN metode_bayar TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE tagihan ADD COLUMN tanggal_bayar TEXT")
    except sqlite3.OperationalError:
        pass

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tagihan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pelanggan_id INTEGER,
            jumlah INTEGER,
            jatuh_tempo TEXT,
            status_bayar TEXT DEFAULT 'Belum Bayar',
            FOREIGN KEY (pelanggan_id) REFERENCES pelanggan (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teknisi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT NOT NULL,
            spesialisasi TEXT,
            no_hp TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS absensi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teknisi_id INTEGER,
            tanggal TEXT NOT NULL,
            hadir INTEGER DEFAULT 0,
            FOREIGN KEY (teknisi_id) REFERENCES teknisi (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS barang (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT NOT NULL,
            kategori TEXT,
            stok INTEGER DEFAULT 0,
            stok_minimum INTEGER DEFAULT 5
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS riwayat_barang (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barang_id INTEGER,
            jenis_perubahan TEXT NOT NULL,
            jumlah INTEGER NOT NULL,
            tanggal TEXT NOT NULL,
            FOREIGN KEY (barang_id) REFERENCES barang (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS titik_jaringan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama_lokasi TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            status TEXT NOT NULL,
            keterangan TEXT,
            tanggal_input TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tiket_kendala (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pelanggan_id INTEGER NOT NULL,
            deskripsi TEXT NOT NULL,
            status TEXT DEFAULT 'Dilaporkan',
            tanggal_lapor TEXT NOT NULL,
            FOREIGN KEY (pelanggan_id) REFERENCES pelanggan (id)
        )
    """)

    # ===== BAGIAN 2: ISI DATA CONTOH (SETELAH SEMUA TABEL ADA) =====

    cursor.execute("SELECT * FROM admin WHERE username = 'admin'")
    if cursor.fetchone() is None:
        cursor.execute(
            "INSERT INTO admin (username, password) VALUES (?, ?)",
            ("admin", "admin123")
        )
    
    cursor.execute("SELECT id FROM teknisi LIMIT 1")
    teknisi_pertama = cursor.fetchone()

    if teknisi_pertama:
        cursor.execute("SELECT * FROM admin WHERE username = 'teknisi1'")
        if cursor.fetchone() is None:
            cursor.execute(
                "INSERT INTO admin (username, password, role, nama_lengkap, teknisi_id) VALUES (?, ?, ?, ?, ?)",
                ("teknisi1", "teknisi123", "teknisi", "Ahmad Fauzi", teknisi_pertama["id"])
            )

    cursor.execute("SELECT id FROM pelanggan LIMIT 1")
    pelanggan_pertama = cursor.fetchone()

    if pelanggan_pertama:
        cursor.execute("SELECT * FROM user_pelanggan WHERE username = 'user1'")
        if cursor.fetchone() is None:
            cursor.execute(
                "INSERT INTO user_pelanggan (username, password, pelanggan_id) VALUES (?, ?, ?)",
                ("user1", "user123", pelanggan_pertama["id"])
            )

    cursor.execute("SELECT COUNT(*) FROM pelanggan")
    jumlah_pelanggan = cursor.fetchone()[0]
    if jumlah_pelanggan == 0:
        data_pelanggan = [
            ("Budi Santoso", "0812-3456-7890", "50 Mbps", "Aktif"),
            ("Siti Rahayu", "0857-1234-5678", "20 Mbps", "Aktif"),
            ("Joko Widodo", "0821-9876-5432", "100 Mbps", "Nonaktif"),
        ]
        cursor.executemany(
            "INSERT INTO pelanggan (nama, no_hp, paket, status) VALUES (?, ?, ?, ?)",
            data_pelanggan
        )

    cursor.execute("SELECT COUNT(*) FROM teknisi")
    jumlah_teknisi = cursor.fetchone()[0]
    if jumlah_teknisi == 0:
        data_teknisi = [
            ("Ahmad Fauzi", "Instalasi", "0811-1111-1111"),
            ("Rizky Pratama", "Perbaikan", "0811-2222-2222"),
            ("Doni Saputra", "Jaringan", "0811-3333-3333"),
        ]
        cursor.executemany(
            "INSERT INTO teknisi (nama, spesialisasi, no_hp) VALUES (?, ?, ?)",
            data_teknisi
        )

    cursor.execute("SELECT COUNT(*) FROM barang")
    jumlah_barang = cursor.fetchone()[0]
    if jumlah_barang == 0:
        data_barang = [
            ("Router Mikrotik RB750", "Router", 23, 10),
            ("Kabel UTP Cat6", "Kabel", 8, 5),
            ("ODP 8 Port", "Optik", 3, 5),
            ("Konektor RJ45", "Aksesoris", 0, 20),
        ]
        cursor.executemany(
            "INSERT INTO barang (nama, kategori, stok, stok_minimum) VALUES (?, ?, ?, ?)",
            data_barang
        )

    cursor.execute("SELECT COUNT(*) FROM titik_jaringan")
    jumlah_titik = cursor.fetchone()[0]

    if jumlah_titik == 0:
        from datetime import date
        hari_ini = date.today().isoformat()
        data_titik = [
            ("Kantor Pusat NetSpeed", 5.1801, 97.1507, "Terpasang", "Server utama dan OLT pusat", hari_ini),
            ("ODP Jalan Merdeka", 5.1850, 97.1450, "Rusak", "ODP mengalami gangguan, menunggu perbaikan teknisi", hari_ini),
            ("Area Cunda", 5.1700, 97.1600, "Area Aktif", "Cakupan layanan internet aktif dan stabil", hari_ini),
            ("Tower Blang Pulo", 5.1900, 97.1300, "Terpasang", "Tower distribusi sinyal wilayah utara", hari_ini),
        ]
        cursor.executemany(
            "INSERT INTO titik_jaringan (nama_lokasi, latitude, longitude, status, keterangan, tanggal_input) VALUES (?, ?, ?, ?, ?, ?)",
            data_titik
        )
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tiket_kendala (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pelanggan_id INTEGER NOT NULL,
            deskripsi TEXT NOT NULL,
            status TEXT DEFAULT 'Dilaporkan',
            tanggal_lapor TEXT NOT NULL,
            FOREIGN KEY (pelanggan_id) REFERENCES pelanggan (id)
        )
    """)
    conn.commit()
    conn.close()
    print("Database berhasil dibuat!")

if __name__ == "__main__":
    init_db()