import csv
import sqlite3
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

# Cek library Excel & QR Scanner
try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

try:
    import cv2
    from pyzbar.pyzbar import decode
    HAS_CAMERA = True
except ImportError:
    HAS_CAMERA = False

# --- SETUP TEMA & WIDGET MODERN ---
ctk.set_appearance_mode("Dark")  # Pilihan: "Dark", "Light", "System"
ctk.set_default_color_theme("blue")  # Pilihan: "blue", "green", "dark-blue"

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

# --- FUNGSI ABSENSI ---
def proses_absensi_data(id_anggota, nama, status="Hadir"):
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
        pesan = f"Absen PULANG untuk {nama} berhasil dicatat ({waktu_sekarang})!"
    else:
        cursor.execute("""
            INSERT INTO absensi (nama, id_anggota, tanggal, jam_masuk, jam_keluar, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (nama, id_anggota, tanggal, waktu_sekarang, "-", status))
        conn.commit()
        pesan = f"Absen MASUK untuk {nama} berhasil dicatat ({waktu_sekarang})!"

    conn.close()
    muat_data()
    return pesan

def simpan_absensi():
    nama = entry_nama.get().strip()
    id_anggota = entry_id.get().strip()
    status = combo_status.get()

    if not nama or not id_anggota:
        messagebox.showwarning("Peringatan", "Nama dan ID tidak boleh kosong!")
        return

    pesan = proses_absensi_data(id_anggota, nama, status)
    messagebox.showinfo("Sukses", pesan)

    entry_nama.delete(0, tk.END)
    entry_id.delete(0, tk.END)

# --- FUNGSI SCANNER QR CODE ---
def mulai_scan_qr():
    if not HAS_CAMERA:
        messagebox.showerror("Error", "Library OpenCV / PyZBar belum terinstall!\nJalankan: pip install opencv-python pyzbar")
        return

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        messagebox.showerror("Error", "Kamera tidak terdeteksi!")
        return

    messagebox.showinfo("Info", "Arahkan QR Code ke kamera.\nTekan tombol 'q' pada keyboard untuk keluar dari kamera.")

    scanned_ids = set()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        for barcode in decode(frame):
            qr_data = barcode.data.decode("utf-8").strip()
            
            if qr_data and qr_data not in scanned_ids:
                scanned_ids.add(qr_data)
                if "," in qr_data:
                    id_anggota, nama = qr_data.split(",", 1)
                else:
                    id_anggota = qr_data
                    nama = f"Anggota-{id_anggota}"

                pesan = proses_absensi_data(id_anggota, nama, "Hadir")
                cv2.putText(frame, "SUCCESS!", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                messagebox.showinfo("Absensi Berhasil", pesan)

        cv2.imshow("Scanner QR Code Absensi (Tekan 'q' untuk Tutup)", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

def muat_data(query_search=""):
    for row in tree.get_children():
        tree.delete(row)

    conn = sqlite3.connect("absensi.db")
    cursor = conn.cursor()

    if query_search:
        cursor.execute("""
            SELECT id, id_anggota, nama, tanggal, jam_masuk, jam_keluar, status 
            FROM absensi 
            WHERE nama LIKE ? OR id_anggota LIKE ? 
            ORDER BY id DESC
        """, (f"%{query_search}%", f"%{query_search}%"))
    else:
        cursor.execute("SELECT id, id_anggota, nama, tanggal, jam_masuk, jam_keluar, status FROM absensi ORDER BY id DESC")

    rows = cursor.fetchall()
    conn.close()

    for row in rows:
        tree.insert("", tk.END, values=row)

# --- FUNGSI ADMIN & LOGIN ---
current_admin = ""

def buka_dialog_login():
    win_login = ctk.CTkToplevel(root)
    win_login.title("Login Admin")
    win_login.geometry("320x240")
    win_login.grab_set()

    ctk.CTkLabel(win_login, text="🔐 Login Admin", font=("Helvetica", 16, "bold")).pack(pady=15)

    e_user = ctk.CTkEntry(win_login, placeholder_text="Username", width=220)
    e_user.pack(pady=5)

    e_pass = ctk.CTkEntry(win_login, placeholder_text="Password", show="*", width=220)
    e_pass.pack(pady=5)

    def verifikasi_login():
        global current_admin
        u = e_user.get().strip()
        p = e_pass.get().strip()

        conn = sqlite3.connect("absensi.db")
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM admin WHERE username = ? AND password = ?", (u, p))
        admin = cursor.fetchone()
        conn.close()

        if admin:
            current_admin = admin[0]
            messagebox.showinfo("Sukses", f"Selamat datang, Admin {current_admin}!")
            win_login.destroy()
            aktifkan_mode_admin(True)
        else:
            messagebox.showerror("Gagal", "Username atau Password salah!")

    ctk.CTkButton(win_login, text="Login", fg_color="#1f538d", font=("Helvetica", 12, "bold"), command=verifikasi_login).pack(pady=15)

def kelola_admin():
    win_kelola = ctk.CTkToplevel(root)
    win_kelola.title("Kelola User Admin")
    win_kelola.geometry("480x420")
    win_kelola.grab_set()

    ctk.CTkLabel(win_kelola, text="👥 Kelola Akun Admin", font=("Helvetica", 16, "bold")).pack(pady=10)

    frame_add = ctk.CTkFrame(win_kelola)
    frame_add.pack(fill="x", padx=15, pady=5)

    e_new_user = ctk.CTkEntry(frame_add, placeholder_text="Username Baru", width=140)
    e_new_user.grid(row=0, column=0, padx=5, pady=10)

    e_new_pass = ctk.CTkEntry(frame_add, placeholder_text="Password Baru", show="*", width=140)
    e_new_pass.grid(row=0, column=1, padx=5, pady=10)

    def simpan_admin_baru():
        u = e_new_user.get().strip()
        p = e_new_pass.get().strip()

        if not u or not p:
            messagebox.showwarning("Peringatan", "Username & Password tidak boleh kosong!")
            return

        conn = sqlite3.connect("absensi.db")
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO admin (username, password) VALUES (?, ?)", (u, p))
            conn.commit()
            messagebox.showinfo("Sukses", f"Admin baru '{u}' berhasil ditambahkan!")
            e_new_user.delete(0, tk.END)
            e_new_pass.delete(0, tk.END)
            muat_list_admin()
        except sqlite3.IntegrityError:
            messagebox.showerror("Gagal", "Username tersebut sudah digunakan!")
        finally:
            conn.close()

    ctk.CTkButton(frame_add, text="➕ Tambah", width=100, fg_color="#2eb85c", command=simpan_admin_baru).grid(row=0, column=2, padx=5, pady=10)

    frame_list = ctk.CTkFrame(win_kelola)
    frame_list.pack(fill="both", expand=True, padx=15, pady=10)

    list_tree = ttk.Treeview(frame_list, columns=("id", "user"), show="headings", height=5)
    list_tree.heading("id", text="ID")
    list_tree.heading("user", text="Username Admin")
    list_tree.column("id", width=50, anchor="center")
    list_tree.column("user", width=250)
    list_tree.pack(fill="both", expand=True, padx=5, pady=5)

    def muat_list_admin():
        for r in list_tree.get_children():
            list_tree.delete(r)
        conn = sqlite3.connect("absensi.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, username FROM admin")
        for row in cursor.fetchall():
            list_tree.insert("", tk.END, values=row)
        conn.close()

    def hapus_admin_selected():
        selected = list_tree.selection()
        if not selected:
            messagebox.showwarning("Peringatan", "Pilih admin di daftar yang ingin dihapus!")
            return
        
        item = list_tree.item(selected)["values"]
        target_id, target_user = item[0], item[1]

        if target_user == current_admin:
            messagebox.showerror("Gagal", "Anda tidak dapat menghapus akun yang sedang digunakan!")
            return

        if messagebox.askyesno("Konfirmasi", f"Yakin ingin menghapus admin '{target_user}'?"):
            conn = sqlite3.connect("absensi.db")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM admin WHERE id = ?", (target_id,))
            conn.commit()
            conn.close()
            messagebox.showinfo("Sukses", f"Admin '{target_user}' berhasil dihapus!")
            muat_list_admin()

    ctk.CTkButton(win_kelola, text="🗑️ Hapus Admin Terpilih", fg_color="#e55353", command=hapus_admin_selected).pack(pady=10)
    muat_list_admin()

def ubah_password_admin():
    win_pass = ctk.CTkToplevel(root)
    win_pass.title("Ubah Password")
    win_pass.geometry("320x240")
    win_pass.grab_set()

    ctk.CTkLabel(win_pass, text=f"🔑 Ganti Password ({current_admin})", font=("Helvetica", 14, "bold")).pack(pady=15)

    e_old = ctk.CTkEntry(win_pass, placeholder_text="Password Lama", show="*", width=220)
    e_old.pack(pady=5)

    e_new = ctk.CTkEntry(win_pass, placeholder_text="Password Baru", show="*", width=220)
    e_new.pack(pady=5)

    def simpan_pass_baru():
        p_lama = e_old.get().strip()
        p_baru = e_new.get().strip()

        if not p_lama or not p_baru:
            messagebox.showwarning("Peringatan", "Semua kolom wajib diisi!")
            return

        conn = sqlite3.connect("absensi.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admin WHERE username = ? AND password = ?", (current_admin, p_lama))
        if not cursor.fetchone():
            messagebox.showerror("Gagal", "Password lama salah!")
            conn.close()
            return

        cursor.execute("UPDATE admin SET password = ? WHERE username = ?", (p_baru, current_admin))
        conn.commit()
        conn.close()

        messagebox.showinfo("Sukses", "Password berhasil diperbarui!")
        win_pass.destroy()

    ctk.CTkButton(win_pass, text="Simpan", fg_color="#2eb85c", command=simpan_pass_baru).pack(pady=15)

def aktifkan_mode_admin(status_admin):
    global current_admin
    if status_admin:
        frame_cari.pack(fill="x", padx=15, pady=5)
        frame_aksi.pack(pady=10)
        btn_ganti_pass.pack(side="right", padx=5)
        btn_kelola_admin.pack(side="right", padx=5)
        btn_login_admin.configure(text=f"🔒 Logout ({current_admin})", fg_color="#e55353", command=lambda: aktifkan_mode_admin(False))
        lbl_title.configure(text="Aplikasi Absensi Pro (Mode Admin)")
    else:
        current_admin = ""
        frame_cari.pack_forget()
        frame_aksi.pack_forget()
        btn_ganti_pass.pack_forget()
        btn_kelola_admin.pack_forget()
        btn_login_admin.configure(text="🔑 Login Admin", fg_color="#e5981d", command=buka_dialog_login)
        lbl_title.configure(text="Aplikasi Absensi Harian Pro")

def cari_data(event=None):
    keyword = entry_cari.get().strip()
    muat_data(keyword)

def hapus_data():
    selected_item = tree.selection()
    if not selected_item:
        messagebox.showwarning("Peringatan", "Pilih data di tabel yang ingin dihapus!")
        return

    if messagebox.askyesno("Konfirmasi Hapus", "Apakah Anda yakin ingin menghapus data ini?"):
        item_data = tree.item(selected_item)["values"]
        db_id = item_data[0]

        conn = sqlite3.connect("absensi.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM absensi WHERE id = ?", (db_id,))
        conn.commit()
        conn.close()

        messagebox.showinfo("Sukses", "Data berhasil dihapus!")
        muat_data()

def edit_data():
    selected_item = tree.selection()
    if not selected_item:
        messagebox.showwarning("Peringatan", "Pilih data di tabel yang ingin di-edit!")
        return

    item_data = tree.item(selected_item)["values"]
    db_id, id_anggota, nama_lama, tanggal, masuk, keluar, status_lama = item_data

    win_edit = ctk.CTkToplevel(root)
    win_edit.title("Edit Data Absensi")
    win_edit.geometry("350x260")

    ctk.CTkLabel(win_edit, text="✏️ Edit Data Absensi", font=("Helvetica", 15, "bold")).pack(pady=15)

    e_nama = ctk.CTkEntry(win_edit, width=220)
    e_nama.insert(0, nama_lama)
    e_nama.pack(pady=5)

    c_status = ctk.CTkOptionMenu(win_edit, values=["Hadir", "Izin", "Sakit"], width=220)
    c_status.set(status_lama)
    c_status.pack(pady=5)

    def simpan_perubahan():
        nama_baru = e_nama.get().strip()
        status_baru = c_status.get()

        if not nama_baru:
            messagebox.showwarning("Peringatan", "Nama tidak boleh kosong!")
            return

        conn = sqlite3.connect("absensi.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE absensi SET nama = ?, status = ? WHERE id = ?", (nama_baru, status_baru, db_id))
        conn.commit()
        conn.close()

        messagebox.showinfo("Sukses", "Data berhasil diperbarui!")
        win_edit.destroy()
        muat_data()

    ctk.CTkButton(win_edit, text="Simpan Perubahan", fg_color="#2eb85c", command=simpan_perubahan).pack(pady=15)

def ekspor_excel():
    conn = sqlite3.connect("absensi.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id_anggota, nama, tanggal, jam_masuk, jam_keluar, status FROM absensi ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        messagebox.showwarning("Peringatan", "Belum ada data absensi!")
        return

    if HAS_OPENPYXL:
        filetypes = [("Excel Workbook", "*.xlsx"), ("CSV File", "*.csv")]
        default_ext = ".xlsx"
    else:
        filetypes = [("CSV File", "*.csv")]
        default_ext = ".csv"

    filepath = filedialog.asksaveasfilename(defaultextension=default_ext, filetypes=filetypes, title="Simpan Laporan Absensi")

    if not filepath:
        return

    try:
        if filepath.endswith(".xlsx") and HAS_OPENPYXL:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Rekap Absensi"
            ws.append(["ID / NIK", "Nama Lengkap", "Tanggal", "Jam Masuk", "Jam Keluar", "Status"])
            for row in rows:
                ws.append(list(row))
            wb.save(filepath)
            messagebox.showinfo("Sukses", f"Data diekspor ke Excel:\n{filepath}")
        else:
            with open(filepath, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["ID / NIK", "Nama Lengkap", "Tanggal", "Jam Masuk", "Jam Keluar", "Status"])
                writer.writerows(rows)
            messagebox.showinfo("Sukses", f"Data diekspor ke CSV:\n{filepath}")
    except Exception as e:
        messagebox.showerror("Error", f"Gagal mengekspor:\n{str(e)}")

# --- GUI MAIN (CUSTOMTKINTER) ---
init_db()

root = ctk.CTk()
root.title("Sistem Absensi Modern")
root.geometry("820x720")

# Header Utama
frame_top = ctk.CTkFrame(root, fg_color="transparent")
frame_top.pack(fill="x", padx=20, pady=15)

lbl_title = ctk.CTkLabel(frame_top, text="Aplikasi Absensi Harian Pro", font=("Helvetica", 20, "bold"))
lbl_title.pack(side="left")

btn_login_admin = ctk.CTkButton(frame_top, text="🔑 Login Admin", fg_color="#e5981d", width=120, command=buka_dialog_login)
btn_login_admin.pack(side="right")

btn_kelola_admin = ctk.CTkButton(frame_top, text="👥 Kelola Admin", fg_color="#39f", width=120, command=kelola_admin)

btn_ganti_pass = ctk.CTkButton(frame_top, text="🔒 Ganti Pass", fg_color="#a832a4", width=100, command=ubah_password_admin)

# Card Form Input
frame_input = ctk.CTkFrame(root)
frame_input.pack(fill="x", padx=20, pady=10)

ctk.CTkLabel(frame_input, text="📋 Form Input Absensi", font=("Helvetica", 14, "bold")).pack(anchor="w", padx=15, pady=(10, 5))

f_in_grid = ctk.CTkFrame(frame_input, fg_color="transparent")
f_in_grid.pack(padx=15, pady=5, fill="x")

entry_id = ctk.CTkEntry(f_in_grid, placeholder_text="ID / NIK / NIM", width=220)
entry_id.grid(row=0, column=0, padx=5, pady=5)

entry_nama = ctk.CTkEntry(f_in_grid, placeholder_text="Nama Lengkap", width=250)
entry_nama.grid(row=0, column=1, padx=5, pady=5)

combo_status = ctk.CTkOptionMenu(f_in_grid, values=["Hadir", "Izin", "Sakit"], width=130)
combo_status.set("Hadir")
combo_status.grid(row=0, column=2, padx=5, pady=5)

f_in_btn = ctk.CTkFrame(frame_input, fg_color="transparent")
f_in_btn.pack(pady=(5, 15))

btn_simpan = ctk.CTkButton(f_in_btn, text="✅ Catat Absensi", fg_color="#2eb85c", hover_color="#249349", font=("Helvetica", 12, "bold"), command=simpan_absensi)
btn_simpan.pack(side="left", padx=10)

btn_scan = ctk.CTkButton(f_in_btn, text="📷 Scan QR Code", fg_color="#17a2b8", hover_color="#117a8b", font=("Helvetica", 12, "bold"), command=mulai_scan_qr)
btn_scan.pack(side="left", padx=10)

# Card Tabel
frame_tabel = ctk.CTkFrame(root)
frame_tabel.pack(fill="both", expand=True, padx=20, pady=10)

frame_cari = ctk.CTkFrame(frame_tabel, fg_color="transparent")

entry_cari = ctk.CTkEntry(frame_cari, placeholder_text="🔍 Cari Nama atau ID...", width=250)
entry_cari.pack(side="left", padx=5, pady=5)
entry_cari.bind("<KeyRelease>", cari_data)

# Styling Tabel Treeview agar selaras dengan Tema Gelap
style = ttk.Style()
style.theme_use("default")
style.configure("Treeview", background="#2a2d2e", foreground="white", fieldbackground="#2a2d2e", rowheight=28)
style.map("Treeview", background=[("selected", "#1f538d")])
style.configure("Treeview.Heading", background="#1a1c1e", foreground="white", font=("Helvetica", 10, "bold"))

columns = ("db_id", "id", "nama", "tanggal", "masuk", "keluar", "status")
tree = ttk.Treeview(frame_tabel, columns=columns, show="headings", height=8)

tree.heading("db_id", text="DB ID")
tree.heading("id", text="ID / NIK")
tree.heading("nama", text="Nama")
tree.heading("tanggal", text="Tanggal")
tree.heading("masuk", text="Jam Masuk")
tree.heading("keluar", text="Jam Keluar")
tree.heading("status", text="Status")

tree.column("db_id", width=0, stretch=tk.NO)
tree.column("id", width=90, anchor="center")
tree.column("nama", width=200)
tree.column("tanggal", width=100, anchor="center")
tree.column("masuk", width=90, anchor="center")
tree.column("keluar", width=90, anchor="center")
tree.column("status", width=80, anchor="center")

tree.pack(fill="both", expand=True, padx=15, pady=(5, 15))

# Frame Aksi Admin
frame_aksi = ctk.CTkFrame(root, fg_color="transparent")

btn_edit = ctk.CTkButton(frame_aksi, text="✏️ Edit Baris", fg_color="#e5981d", width=130, command=edit_data)
btn_edit.grid(row=0, column=0, padx=10)

btn_hapus = ctk.CTkButton(frame_aksi, text="🗑️ Hapus Baris", fg_color="#e55353", width=130, command=hapus_data)
btn_hapus.grid(row=0, column=1, padx=10)

btn_ekspor = ctk.CTkButton(frame_aksi, text="📥 Ekspor Excel/CSV", fg_color="#39f", width=150, command=ekspor_excel)
btn_ekspor.grid(row=0, column=2, padx=10)

aktifkan_mode_admin(False)
muat_data()

root.mainloop()