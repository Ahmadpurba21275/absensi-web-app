import csv
import sqlite3
from datetime import datetime
import cv2
import numpy as np
import pandas as pd
import streamlit as st

# --- KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Sistem Absensi Web",
    page_icon="📋",
    layout="wide"
)

# --- SETUP DATABASE ---
def init_db():
    conn = sqlite3.connect("absensi.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS absensi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT NOT NULL,
            id_anggota TEXT NOT NULL,
            tanggal TEXT NOT NULL,
            jam_masuk TEXT NOT NULL,
            jam_keluar TEXT,
            status TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    cursor.execute("INSERT OR IGNORE INTO admin (id, username, password) VALUES (1, 'admin', 'admin123')")
    conn.commit()
    conn.close()

init_db()

# --- FUNGSI UTAMA ABSENSI ---
def proses_absensi(id_anggota, nama, status="Hadir"):
    sekarang = datetime.now()
    tanggal = sekarang.strftime("%Y-%m-%d")
    waktu_sekarang = sekarang.strftime("%H:%M:%S")

    conn = sqlite3.connect("absensi.db")
    cursor = conn.cursor()

    cursor.execute("SELECT id, jam_keluar FROM absensi WHERE id_anggota = ? AND tanggal = ?", (id_anggota, tanggal))
    data_hari_ini = cursor.fetchone()

    if data_hari_ini:
        record_id, jam_keluar = data_hari_ini
        cursor.execute("UPDATE absensi SET jam_keluar = ?, status = ? WHERE id = ?", (waktu_sekarang, status, record_id))
        conn.commit()
        pesan = f"✅ Absen PULANG untuk {nama} ({id_anggota}) berhasil dicatat ({waktu_sekarang})!"
    else:
        cursor.execute("""
            INSERT INTO absensi (nama, id_anggota, tanggal, jam_masuk, jam_keluar, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (nama, id_anggota, tanggal, waktu_sekarang, "-", status))
        conn.commit()
        pesan = f"✅ Absen MASUK untuk {nama} ({id_anggota}) berhasil dicatat ({waktu_sekarang})!"

    conn.close()
    return pesan

# --- SIDEBAR (NAVIGASI & LOGIN) ---
st.sidebar.title("📌 Navigasi Menu")

if "is_admin" not in st.session_state:
    st.session_state["is_admin"] = False
if "admin_user" not in st.session_state:
    st.session_state["admin_user"] = ""

# Form Login Admin di Sidebar
st.sidebar.markdown("---")
if not st.session_state["is_admin"]:
    st.sidebar.subheader("🔑 Login Admin")
    username_input = st.sidebar.text_input("Username")
    password_input = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        conn = sqlite3.connect("absensi.db")
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM admin WHERE username = ? AND password = ?", (username_input, password_input))
        admin = cursor.fetchone()
        conn.close()
        if admin:
            st.session_state["is_admin"] = True
            st.session_state["admin_user"] = admin[0]
            st.sidebar.success(f"Login berhasil sebagai {admin[0]}")
            st.rerun()
        else:
            st.sidebar.error("Username/Password salah!")
else:
    st.sidebar.success(f"👤 Login sebagai: **{st.session_state['admin_user']}**")
    if st.sidebar.button("Logout Admin"):
        st.session_state["is_admin"] = False
        st.session_state["admin_user"] = ""
        st.rerun()

# --- HALAMAN UTAMA ---
st.title("📋 Aplikasi Absensi Harian Web")

# Tab Layar (Sudah Ditambahkan Tab QR Code)
tab1, tab2, tab3 = st.tabs(["✍️ Input Manual", "📷 Scan QR Code", "📊 Rekap Data"])

with tab1:
    st.subheader("Catat Kehadiran Manual")
    col1, col2 = st.columns(2)
    with col1:
        id_anggota = st.text_input("ID / NIK / NIM")
        nama = st.text_input("Nama Lengkap")
    with col2:
        status = st.selectbox("Status Kehadiran", ["Hadir", "Izin", "Sakit"])

    if st.button("Submit Absensi", type="primary"):
        if not id_anggota or not nama:
            st.warning("Mohon isi ID dan Nama Lengkap!")
        else:
            msg = proses_absensi(id_anggota, nama, status)
            st.success(msg)

with tab2:
    st.subheader("📷 Scan QR Code lewat Kamera Browser")
    st.info("Arahkan kartu/gambar QR Code ke kamera di bawah ini.")
    
    img_file_buffer = st.camera_input("Ambil Foto QR Code")

    if img_file_buffer is not None:
        # Convert foto dari browser ke OpenCV format
        bytes_data = img_file_buffer.getvalue()
        cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)

        # Deteksi QR Code
        detector = cv2.QRCodeDetector()
        data, bbox, _ = detector.detectAndDecode(cv2_img)

        if data:
            st.success(f"QR Code Terdeteksi: **{data}**")
            # Format QR: "ID" atau "ID,Nama"
            if "," in data:
                qr_id, qr_nama = data.split(",", 1)
            else:
                qr_id = data
                qr_nama = f"Anggota-{qr_id}"

            msg = proses_absensi(qr_id, qr_nama, "Hadir")
            st.balloons()
            st.success(msg)
        else:
            st.error("QR Code tidak terbaca / tidak jelas. Silakan coba arahkan ulang ke kamera.")

with tab3:
    st.subheader("Data Rekap Absensi")
    
    conn = sqlite3.connect("absensi.db")
    df = pd.read_sql_query("SELECT id, id_anggota, nama, tanggal, jam_masuk, jam_keluar, status FROM absensi ORDER BY id DESC", conn)
    conn.close()

    # Filter Pencarian
    search = st.text_input("🔍 Cari Data (Nama / ID)...")
    if search:
        df = df[df['nama'].str.contains(search, case=False, na=False) | df['id_anggota'].str.contains(search, case=False, na=False)]

    # Tampilkan Tabel
    st.dataframe(df, use_container_width=True)

    # --- FITUR KHUSUS ADMIN ---
    if st.session_state["is_admin"]:
        st.markdown("---")
        st.subheader("🛠️ Panel Kontrol Admin")
        
        col_admin1, col_admin2 = st.columns(2)
        
        with col_admin1:
            st.markdown("### 📥 Ekspor Laporan")
            csv_data = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Laporan (CSV)",
                data=csv_data,
                file_name=f"rekap_absensi_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

        with col_admin2:
            st.markdown("### 🗑️ Hapus Baris Data")
            id_to_delete = st.number_input("Masukkan DB ID yang ingin dihapus", min_value=1, step=1)
            if st.button("Hapus Data", type="primary"):
                conn = sqlite3.connect("absensi.db")
                cursor = conn.cursor()
                cursor.execute("DELETE FROM absensi WHERE id = ?", (id_to_delete,))
                conn.commit()
                conn.close()
                st.success(f"Data dengan DB ID {id_to_delete} berhasil dihapus!")
                st.rerun()