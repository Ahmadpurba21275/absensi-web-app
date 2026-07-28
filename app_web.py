import io
import sqlite3
from datetime import datetime
import pytz
import cv2
import numpy as np
import pandas as pd
import streamlit as st

# --- KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Aplikasi Absensi Harian Pro",
    page_icon="📋",
    layout="wide"
)

# Zona Waktu WIB
WIB = pytz.timezone('Asia/Jakarta')

# --- SETUP DATABASE (SAMA DENGAN APP_ABSENSI.PY) ---
def init_db():
    with sqlite3.connect("absensi.db") as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS absensi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_anggota TEXT,
                nama TEXT,
                tanggal TEXT,
                jam_masuk TEXT,
                jam_keluar TEXT,
                status TEXT
            )
        ''')
        conn.commit()

init_db()

# --- FUNGSI PROSES ABSENSI ---
def simpan_absensi(id_anggota, nama, status_input):
    sekarang = datetime.now(WIB)
    tgl_str = sekarang.strftime("%Y-%m-%d")
    jam_str = sekarang.strftime("%H:%M:%S")

    with sqlite3.connect("absensi.db") as conn:
        c = conn.cursor()
        # Cek apakah ID sudah absen hari ini
        c.execute('''
            SELECT id, jam_masuk, jam_keluar FROM absensi 
            WHERE id_anggota = ? AND tanggal = ?
        ''', (id_anggota, tgl_str))
        existing = c.fetchone()

        if existing:
            # Jika sudah ada jam masuk tapi belum ada jam keluar -> Update Jam Keluar
            if existing[1] and not existing[2]:
                c.execute('''
                    UPDATE absensi SET jam_keluar = ? WHERE id = ?
                ''', (jam_str, existing[0]))
                conn.commit()
                return True, f"👋 **{nama}** ({id_anggota}) berhasil Absen Keluar pada {jam_str}!"
            else:
                return False, f"⚠️ **{nama}** ({id_anggota}) sudah melakukan absen masuk & keluar hari ini!"
        else:
            # Jika belum ada -> Catat Absen Masuk
            c.execute('''
                INSERT INTO absensi (id_anggota, nama, tanggal, jam_masuk, status)
                VALUES (?, ?, ?, ?, ?)
            ''', (id_anggota, nama, tgl_str, jam_str, status_input))
            conn.commit()
            return True, f"✅ **{nama}** ({id_anggota}) berhasil Absen Masuk ({status_input}) pada {jam_str}!"

# --- HEADER UTAMA ---
col_head1, col_head2 = st.columns([4, 1])
with col_head1:
    st.title("Aplikasi Absensi Harian Pro")
with col_head2:
    st.write("")
    if st.button("🔑 Login Admin", use_container_width=True):
        st.info("Area Login Admin")

# --- FORM INPUT ABSENSI ---
st.subheader("📋 Form Input Absensi")

with st.form("form_absensi_sync", clear_on_submit=True):
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        id_anggota = st.text_input("ID / NIK / NIM", placeholder="Masukkan ID/NIK...")
    with col2:
        nama = st.text_input("Nama Lengkap", placeholder="Masukkan Nama Lengkap...")
    with col3:
        status = st.selectbox("Status", ["Hadir", "Izin", "Sakit", "Alfa"])

    col_b1, col_b2 = st.columns(2)
    with col_b1:
        btn_catat = st.form_submit_button("✅ Catat Absensi", use_container_width=True)
    with col_b2:
        btn_scan = st.form_submit_button("📷 Scan QR Code", use_container_width=True)

    if btn_catat:
        if id_anggota and nama:
            sukses, pesan = simpan_absensi(id_anggota.strip(), nama.strip(), status)
            if sukses:
                st.success(pesan)
            else:
                st.warning(pesan)
        else:
            st.error("❌ Mohon isi ID/NIK dan Nama Lengkap!")

# Mode Kamera untuk Scan QR jika tombol Scan diklik / diaktifkan
if 'show_camera' not in st.session_state:
    st.session_state.show_camera = False

if btn_scan:
    st.session_state.show_camera = not st.session_state.show_camera

if st.session_state.show_camera:
    st.info("📷 Arahkan QR Code ke kamera:")
    img_file = st.camera_input("Kamera QR")
    if img_file:
        bytes_data = img_file.getvalue()
        cv_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
        detector = cv2.QRCodeDetector()
        data, bbox, _ = detector.detectAndDecode(cv_img)

        if data:
            if "," in data:
                id_qr, nama_qr = data.split(",", 1)
            else:
                id_qr, nama_qr = data, "Tanpa Nama"

            sukses, pesan = simpan_absensi(id_qr.strip(), nama_qr.strip(), "Hadir")
            if sukses:
                st.success(pesan)
            else:
                st.warning(pesan)
        else:
            st.error("❌ QR Code tidak terdeteksi. Silakan posisikan QR lebih jelas.")

# --- TABEL DATA ABSENSI ---
st.markdown("---")
st.subheader("📊 Rekapitulasi Data Absensi")

with sqlite3.connect("absensi.db") as conn:
    df = pd.read_sql_query('''
        SELECT 
            id_anggota AS 'ID / NIK', 
            nama AS 'Nama', 
            tanggal AS 'Tanggal', 
            jam_masuk AS 'Jam Masuk', 
            jam_keluar AS 'Jam Keluar', 
            status AS 'Status' 
        FROM absensi 
        ORDER BY id DESC
    ''', conn)

if not df.empty:
    st.dataframe(df, use_container_width=True)
    
    # Download Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Absensi")
    
    st.download_button(
        label="📥 Download Data (Excel)",
        data=output.getvalue(),
        file_name="rekap_absensi_pro.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("Belum ada data absensi tersimpan.")