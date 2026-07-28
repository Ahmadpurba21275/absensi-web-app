import csv

import sqlite3

from datetime import datetime

import pytz

import cv2

import numpy as np

import pandas as pd

import streamlit as st



# --- KONFIGURASI HALAMAN ---

st.set_page_config(

    page_title="Sistem Absensi Web Multi-Guru",

    page_icon="📋",

    layout="wide"

)



# Zona Waktu Indonesia Barat (WIB)

WIB = pytz.timezone('Asia/Jakarta')



# --- SETUP DATABASE ---

def init_db():

    conn = sqlite3.connect("absensi.db")

    c = conn.cursor()

    # Membuat tabel absensi dengan kolom nama_guru dan nama_kelas

    c.execute('''

        CREATE TABLE IF NOT EXISTS absensi (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            nama_guru TEXT,

            nama_kelas TEXT,

            nis_nip TEXT,

            nama TEXT,

            tanggal TEXT,

            jam TEXT

        )

    ''')

    conn.commit()

    conn.close()



init_db()



# --- FUNGSI ABSENSI ---

def proses_absensi(data_qr, nama_guru, nama_kelas):

    sekarang = datetime.now(WIB)

    tanggal_str = sekarang.strftime("%Y-%m-%d")

    jam_str = sekarang.strftime("%H:%M:%S")



    # Format QR Code diharapkan: NIS_NIP,Nama

    # Contoh isi QR: 12345,Ahmad Purba

    if "," in data_qr:

        nis_nip, nama = data_qr.split(",", 1)

    else:

        nis_nip = "N/A"

        nama = data_qr.strip()



    conn = sqlite3.connect("absensi.db")

    c = conn.cursor()



    # Cek apakah sudah absen hari ini untuk guru/kelas yang sama

    c.execute('''

        SELECT * FROM absensi 

        WHERE nis_nip = ? AND tanggal = ? AND nama_guru = ? AND nama_kelas = ?

    ''', (nis_nip, tanggal_str, nama_guru, nama_kelas))

    

    existing = c.fetchone()



    if existing:

        conn.close()

        return False, f"⚠️ **{nama}** ({nis_nip}) sudah melakukan absensi hari ini pada kelas {nama_kelas} ({nama_guru})!"

    else:

        c.execute('''

            INSERT INTO absensi (nama_guru, nama_kelas, nis_nip, nama, tanggal, jam)

            VALUES (?, ?, ?, ?, ?, ?)

        ''', (nama_guru, nama_kelas, nis_nip, nama, tanggal_str, jam_str))

        conn.commit()

        conn.close()

        return True, f"✅ Absensi berhasil dicatat! Nama: **{nama}** | Guru: **{nama_guru}** | Kelas: **{nama_kelas}**"



# --- TAMPILAN UTAMA STREAMLIT ---

st.title("📋 Sistem Absensi Harian Berbasis QR Code")

st.markdown("Aplikasi absensi terintegrasi untuk berbagai Guru & Kelas.")



tab1, tab2 = st.tabs(["📷 Scan / Input Absensi", "📊 Rekap Data Absensi"])



# --- TAB 1: SCAN ABSENSI ---

with tab1:

    st.header("Form Absensi Harian")

    

    col_opt1, col_opt2 = st.columns(2)

    with col_opt1:

        nama_guru = st.text_input("👨‍🏫 / 👩‍🏫 Nama Guru / Pengajar", value="Guru A", help="Masukkan nama guru yang mengampu kelas")

    with col_opt2:

        nama_kelas = st.text_input("🏫 Nama Kelas / Mata Pelajaran", value="Kelas 10-A", help="Contoh: Kelas 10-A / Matematika")



    st.subheader("Pilih Metode Input:")

    metode = st.radio("Metode Absensi", ["Kamera Web / HP (Scan QR)", "Input Manual NIS/Nama"], horizontal=True)



    if "Kamera" in metode:

        st.info("Arahkan QR Code ke kamera Anda. Pastikan pencahayaan cukup.")

        camera_image = st.camera_input("Kamera Absensi")



        if camera_image:

            bytes_data = camera_image.getvalue()

            cv_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)



            # Detector QR Code bawaan OpenCV

            detector = cv2.QRCodeDetector()

            data, bbox, _ = detector.detectAndDecode(cv_img)



            if data:

                sukses, pesan = proses_absensi(data, nama_guru, nama_kelas)

                if sukses:

                    st.success(pesan)

                else:

                    st.warning(pesan)

            else:

                st.error("❌ QR Code tidak terdeteksi. Silakan coba posisikan QR Code lebih jelas.")



    else:

        with st.form("form_manual", clear_on_submit=True):

            data_manual = st.text_input("Ketik 'NIS,Nama' atau 'Nama Saja' (Contoh: 1001,Ahmad Purba)")

            submitted = st.form_submit_button("Submit Absensi")



            if submitted and data_manual:

                sukses, pesan = proses_absensi(data_manual, nama_guru, nama_kelas)

                if sukses:

                    st.success(pesan)

                else:

                    st.warning(pesan)



# --- TAB 2: REKAP DATA ---

with tab2:

    st.header("📊 Rekapitulasi Data Absensi")



    conn = sqlite3.connect("absensi.db")

    df = pd.read_sql_query("SELECT * FROM absensi ORDER BY id DESC", conn)

    conn.close()



    if not df.empty:

        # Pilihan Filter Guru dan Kelas

        col_f1, col_f2 = st.columns(2)

        

        list_guru = ["Semua Guru"] + list(df["nama_guru"].unique())

        list_kelas = ["Semua Kelas"] + list(df["nama_kelas"].unique())



        with col_f1:

            filter_guru = st.selectbox("Filter Berdasarkan Guru:", list_guru)

        with col_f2:

            filter_kelas = st.selectbox("Filter Berdasarkan Kelas:", list_kelas)



        # Terapkan Filter

        df_filtered = df.copy()

        if filter_guru != "Semua Guru":

            df_filtered = df_filtered[df_filtered["nama_guru"] == filter_guru]

        if filter_kelas != "Semua Kelas":

            df_filtered = df_filtered[df_filtered["nama_kelas"] == filter_kelas]



        st.subheader(f"Total Data Terfilter: {len(df_filtered)} Absensi")

        

        # Tampilkan Tabel

        st.dataframe(df_filtered[["tanggal", "jam", "nama_guru", "nama_kelas", "nis_nip", "nama"]], use_container_width=True)



        # Download Excel khusus data yang sudah difilter

        buffer = pd.ExcelWriter("rekap_absensi.xlsx", engine="openpyxl")

        df_filtered.to_excel(buffer, index=False, sheet_name="Rekap Absensi")

        buffer.close()



        with open("rekap_absensi.xlsx", "rb") as f:

            st.download_button(

                label="📥 Download Rekap Excel (Sesuai Filter)",

                data=f,

                file_name=f"rekap_absensi_{filter_guru}_{filter_kelas}.xlsx",

                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

            )

    else:

        st.info("Belum ada data absensi yang tersimpan.")