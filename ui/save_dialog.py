"""
ui/save_dialog.py  -  Sayım düzeltme ve kayıt penceresi.
Seçilen bölgeyi crop edip kaydeder.
"""

import csv
import os
import datetime
import tkinter as tk
import ttkbootstrap as ttk
from tkinter import messagebox

import cv2

from config import BG_CARD, BG_DARK, BG_MID, FG_DIM, ACCENT, RENK1_HEX, RENK2_HEX

MASAUSTU = os.path.join(os.path.expanduser("~"), "Desktop")
KAYIT_DOSYASI = os.path.join(MASAUSTU, "cam_sayim_kayitlari.csv")
CROP_KLASOR   = os.path.join(MASAUSTU, "cam_crops")


def _ensure_csv():
    if not os.path.exists(KAYIT_DOSYASI):
        with open(KAYIT_DOSYASI, "w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerow([
                "Tarih", "Dosya", "Crop_Dosyasi",
                "Bolge1_Algoritma", "Bolge1_Gercek",
                "Bolge2_Algoritma", "Bolge2_Gercek",
            ])


def _sanitize_filename(name: str) -> str:
    """Remove characters that are unsafe for file names."""
    # Allow only alphanumerics, hyphens, underscores, and dots.
    import re
    sanitized = re.sub(r'[^\w.\-]', '_', name)
    # Prevent path traversal components.
    sanitized = sanitized.replace('..', '_')
    return sanitized[:200]  # limit length


def _save_crop(region_bgr, filename, count, idx):
    """Bölge görüntüsünü crop klasörüne kaydeder, dosya adını döndürür."""
    os.makedirs(CROP_KLASOR, exist_ok=True)
    base = os.path.splitext(os.path.basename(filename))[0] if filename else "goruntu"
    base = _sanitize_filename(base)
    tarih = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    crop_name = f"{base}_bolge{idx+1}_{count}_{tarih}.jpg"
    crop_path = os.path.join(CROP_KLASOR, crop_name)
    # Final safety check: ensure the resolved path stays inside CROP_KLASOR.
    real_dir = os.path.realpath(CROP_KLASOR)
    real_path = os.path.realpath(crop_path)
    if not real_path.startswith(real_dir + os.sep):
        raise ValueError("Invalid crop path — possible path traversal.")
    cv2.imwrite(crop_path, region_bgr)
    return crop_name


def show_save_dialog(parent, filename: str, counts: list, regions: list):
    """
    counts:  [bolge1_algo, bolge2_algo]  (None = seçilmemiş)
    regions: [bolge1_bgr,  bolge2_bgr]   (None = seçilmemiş)
    """
    win = tk.Toplevel(parent)
    win.title("Sayımı Kaydet")
    win.configure(bg=BG_DARK)
    win.resizable(False, False)
    win.grab_set()

    win.update_idletasks()
    pw, ph = 440, 340
    sx = parent.winfo_x() + (parent.winfo_width()  - pw) // 2
    sy = parent.winfo_y() + (parent.winfo_height() - ph) // 2
    win.geometry(f"{pw}x{ph}+{sx}+{sy}")

    RENK = [RENK1_HEX, RENK2_HEX]

    tk.Label(win, text="Sayımı Kaydet",
             font=("Segoe UI", 14, "bold"),
             fg=ACCENT, bg=BG_DARK).pack(pady=(18, 4))

    dosya_kisa = os.path.basename(filename) if filename else "—"
    tk.Label(win, text=dosya_kisa,
             font=("Segoe UI", 9), fg=FG_DIM, bg=BG_DARK).pack(pady=(0, 12))

    frame = tk.Frame(win, bg=BG_CARD, padx=20, pady=16)
    frame.pack(fill="x", padx=20)

    gercek_vars = []
    for i, algo in enumerate(counts):
        if algo is None:
            gercek_vars.append(None)
            continue

        row = tk.Frame(frame, bg=BG_CARD)
        row.pack(fill="x", pady=6)

        tk.Label(row, text=f"Bölge {i+1}",
                 font=("Segoe UI", 10, "bold"),
                 fg=RENK[i], bg=BG_CARD, width=8, anchor="w").pack(side="left")
        tk.Label(row, text=f"Algoritma: {algo}",
                 font=("Segoe UI", 10),
                 fg=FG_DIM, bg=BG_CARD, width=16).pack(side="left")
        tk.Label(row, text="Gerçek:",
                 font=("Segoe UI", 10),
                 fg="#e2e8f0", bg=BG_CARD).pack(side="left", padx=(8, 4))

        var = tk.StringVar(value=str(algo))
        entry = tk.Entry(row, textvariable=var,
                         font=("Segoe UI", 11, "bold"),
                         fg=RENK[i], bg=BG_MID,
                         insertbackground=RENK[i],
                         width=6, relief="flat", bd=4)
        entry.pack(side="left")
        entry.select_range(0, "end")
        gercek_vars.append(var)

    def _kaydet():
        satirlar = []
        for i, var in enumerate(gercek_vars):
            if var is None:
                continue
                gercek_txt = var.get().strip()
                if not gercek_txt.isdigit():
                    messagebox.showwarning("Hata",
                        f"Bölge {i+1} için geçerli bir sayı girin.", parent=win)
                    return
                gercek_val = int(gercek_txt)
                if gercek_val > 99999:
                    messagebox.showwarning("Hata",
                        f"Bölge {i+1}: değer çok büyük (maks 99999).", parent=win)
                    return
                satirlar.append((i, counts[i], gercek_val))

        _ensure_csv()
        tarih = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")

        # Crop kaydet
        crop_isimleri = []
        for i, algo, gercek in satirlar:
            if regions and i < len(regions) and regions[i] is not None:
                crop_isim = _save_crop(regions[i], filename, gercek, i)
                crop_isimleri.append(crop_isim)
            else:
                crop_isimleri.append("")

        row_data = [tarih, dosya_kisa, "|".join(crop_isimleri)]
        for i in range(2):
            match = [(a, g) for idx, a, g in satirlar if idx == i]
            if match:
                row_data += [match[0][0], match[0][1]]
            else:
                row_data += ["", ""]

        with open(KAYIT_DOSYASI, "a", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerow(row_data)

        messagebox.showinfo("Kaydedildi",
            f"Kayıt ve bölge görüntüsü kaydedildi!\n\n"
            f"CSV: {KAYIT_DOSYASI}\n"
            f"Görseller: {CROP_KLASOR}",
            parent=win)
        win.destroy()

    btn_frame = tk.Frame(win, bg=BG_DARK)
    btn_frame.pack(pady=16)

    ttk.Button(btn_frame, text="Kaydet", bootstyle="success",
               command=_kaydet, width=14).pack(side="left", padx=6)
    ttk.Button(btn_frame, text="İptal", bootstyle="secondary-outline",
               command=win.destroy, width=10).pack(side="left", padx=6)
