import os, time, datetime
import cv2
import ttkbootstrap as ttk
from PIL import Image, ImageTk
from tkinter import filedialog, messagebox
from config import (ACCENT, BG_CARD, BG_DARK, BG_MID, FG_DIM,
                    IMAGE_FILETYPES, CROP_MAX_SIZE, WINDOW_SIZE, WINDOW_MIN)
from core.analysis import count_fragments
from core.image_utils import draw_analysis_result
from ui.canvas import ImageCanvas
from ui.panels import LeftPanel, CropTab
from ui.save_dialog import show_save_dialog


class App(ttk.Window):

    def __init__(self):
        super().__init__(themename="darkly")
        self.title("Temperli Cam Analizi")
        self.geometry(WINDOW_SIZE)
        self.minsize(*WINDOW_MIN)
        self.configure(bg=BG_DARK)
        self._image      = None
        self._image_path = ""
        self._result_img = None
        self._boxes      = []
        self._results    = []
        self._crop_tabs  = []
        self._status_var = ttk.StringVar(value="  Fotograf yukleyin.")
        self._apply_styles()
        self._build_ui()

    def _apply_styles(self):
        style = ttk.Style()
        style.configure("TFrame",      background=BG_DARK)
        style.configure("Card.TFrame", background=BG_CARD)

    def _build_ui(self):
        self._build_header()
        self._build_left_panel()
        self._build_right_area()
        self._build_status_bar()

    def _build_header(self):
        header = ttk.Frame(self, style="Card.TFrame")
        header.pack(fill="x")
        ttk.Label(header, text="  TEMPERLI CAM ANALIZI",
                  font=("Segoe UI", 16, "bold"),
                  foreground=ACCENT, background=BG_CARD).pack(side="left", padx=18, pady=12)

    def _build_left_panel(self):
        self._left = LeftPanel(self)
        self._left.pack(side="left", fill="y")
        self._left.on_load    = self._load_image
        self._left.on_analyze = self._analyze
        self._left.on_save    = self._save_image
        self._left.on_pdf     = self._save_pdf
        self._left.on_kaydet  = self._kaydet_dialog
        self._left.on_clear1  = self._clear_bolge1
        self._left.on_clear2  = self._clear_bolge2

    def _build_right_area(self):
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        self._notebook = ttk.Notebook(right, bootstyle="info")
        self._notebook.pack(fill="both", expand=True)
        tab_main = ttk.Frame(self._notebook)
        self._notebook.add(tab_main, text="  Ana Goruntu  ")
        self._canvas = ImageCanvas(tab_main, on_box_added=self._on_box_added)
        self._canvas.pack(fill="both", expand=True)
        for i in range(2):
            tab = CropTab(self._notebook, idx=i)
            self._notebook.add(tab, text=f"  Bolge {i + 1}  ")
            self._crop_tabs.append(tab)

    def _build_status_bar(self):
        bar = ttk.Frame(self, style="Card.TFrame")
        bar.pack(fill="x", side="bottom")
        ttk.Label(bar, textvariable=self._status_var, foreground=FG_DIM,
                  background=BG_CARD, font=("Segoe UI", 8)).pack(side="left", padx=12, pady=5)

    def _on_box_added(self, idx, box):
        self._boxes = self._canvas._boxes
        self._update_crop_tab(idx, box)
        self._notebook.select(idx + 1)
        self.update()

    def _update_crop_tab(self, idx, box):
        if self._image is None:
            return
        x1, x2 = sorted([box[0], box[2]])
        y1, y2 = sorted([box[1], box[3]])
        crop = self._image[y1:y2, x1:x2]
        if crop.size == 0:
            return
        pil_crop = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
        sc  = min(CROP_MAX_SIZE / pil_crop.width, CROP_MAX_SIZE / pil_crop.height, 1.0)
        nw  = max(1, int(pil_crop.width  * sc))
        nh  = max(1, int(pil_crop.height * sc))
        imgtk = ImageTk.PhotoImage(pil_crop.resize((nw, nh), Image.LANCZOS))
        self._crop_tabs[idx].update_image(imgtk, x2 - x1, y2 - y1)

    def _get_regions(self):
        regions = []
        for b in self._boxes:
            x1, x2 = sorted([b[0], b[2]])
            y1, y2 = sorted([b[1], b[3]])
            regions.append((self._image[y1:y2, x1:x2], x1, y1, x2, y2))
        return regions

    def _load_image(self):
        path = filedialog.askopenfilename(title="Goruntu Sec", filetypes=IMAGE_FILETYPES)
        if not path:
            return
        img = cv2.imread(path)
        if img is None:
            messagebox.showerror("Hata", f"Dosya acilamadi:\n{path}")
            return
        self._image = img
        self._image_path = path
        self._result_img = None
        self._results    = []
        self._boxes      = []
        self._canvas.set_image(img)
        self._canvas.clear_boxes()
        for tab in self._crop_tabs:
            tab.clear()
        self._left.reset_results()
        self._status_var.set(f"  {os.path.basename(path)}   —   {img.shape[1]} x {img.shape[0]} px")
        self._notebook.select(0)

    def _analyze(self):
        if self._image is None:
            messagebox.showwarning("Uyari", "Once bir fotograf yukleyin.")
            return None
        if not self._boxes:
            messagebox.showwarning("Uyari", "Analiz etmek istediginiz bolgeyi secin.")
            return None
        self._status_var.set("  Analiz ediliyor...")
        self.update()
        self._results = []
        for region, x1, y1, x2, y2 in self._get_regions():
            count, centers, _ = count_fragments(region)
            self._results.append((count, x1, y1, x2, y2, centers))
        self._result_img = self._image.copy()
        draw_analysis_result(self._result_img, self._results)
        self._canvas.show_bgr(self._result_img)
        for i, (count, *_) in enumerate(self._results[:2]):
            self._left.result_vars[i].set(str(count))
        counts = [r[0] for r in self._results]
        if len(counts) == 1:
            self._status_var.set(f"  Bolge 1: {counts[0]} parca")
        else:
            fark  = abs(counts[0] - counts[1])
            fazla = "Bolge 1" if counts[0] > counts[1] else "Bolge 2"
            self._status_var.set(f"  Bolge 1: {counts[0]}  |  Bolge 2: {counts[1]}  |  Fark: {fark}  |  Daha fazla: {fazla}")
        return self._result_img

    def _save_image(self):
        if not self._results:
            if self._analyze() is None:
                return
        folder = filedialog.askdirectory(title="Kayit Klasoru Sec")
        if not folder:
            return
        fname = f"Analiz_{int(time.time())}.jpg"
        cv2.imwrite(os.path.join(folder, fname), self._result_img)
        messagebox.showinfo("Kaydedildi", f"Goruntu kaydedildi:\n{os.path.join(folder, fname)}")

    def _save_pdf(self):
        if not self._results:
            if self._analyze() is None:
                return
        try:
            from core.pdf_report import save_pdf, REPORTLAB_OK
            if not REPORTLAB_OK:
                messagebox.showerror("Eksik Kutuphane",
                    "PDF olusturmak icin 'reportlab' gerekli.\n\npip install reportlab")
                return
        except Exception as e:
            messagebox.showerror("Hata", str(e))
            return
        tarih = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = filedialog.asksaveasfilename(title="PDF Kaydet",
            defaultextension=".pdf", filetypes=[("PDF", "*.pdf")],
            initialfile=f"Analiz_{tarih}.pdf")
        if not path:
            return
        self._status_var.set("  PDF olusturuluyor...")
        self.update()
        try:
            save_pdf(path=path, original_bgr=self._image, result_bgr=self._result_img,
                     results=self._results, filename=self._image_path)
            self._status_var.set(f"  PDF kaydedildi: {os.path.basename(path)}")
            messagebox.showinfo("PDF Kaydedildi", f"Rapor olusturuldu:\n{path}")
        except Exception as e:
            messagebox.showerror("PDF Hatasi", str(e))

    def _kaydet_dialog(self):
        if not self._results:
            if self._analyze() is None:
                return
        counts  = [r[0] for r in self._results]
        regions = []
        for r in self._results:
            _, x1, y1, x2, y2, _ = r
            x1s, x2s = sorted([x1, x2])
            y1s, y2s = sorted([y1, y2])
            crop = self._image[y1s:y2s, x1s:x2s]
            regions.append(crop if crop.size > 0 else None)
        while len(counts)  < 2: counts.append(None)
        while len(regions) < 2: regions.append(None)
        show_save_dialog(self, self._image_path, counts[:2], regions[:2])

    def _clear_bolge1(self):
        if self._canvas._boxes:
            self._canvas._boxes = self._canvas._boxes[1:]
        self._boxes = self._canvas._boxes
        if len(self._crop_tabs) > 0:
            self._crop_tabs[0].clear()
        self._left.result_vars[0].set("—")
        self._results = []
        self._result_img = None
        if self._image is not None:
            self._canvas._redraw()
        self._status_var.set("  Bolge 1 temizlendi.")
        self._notebook.select(0)

    def _clear_bolge2(self):
        if len(self._canvas._boxes) > 1:
            self._canvas._boxes = self._canvas._boxes[:1]
        self._boxes = self._canvas._boxes
        if len(self._crop_tabs) > 1:
            self._crop_tabs[1].clear()
        self._left.result_vars[1].set("—")
        self._results = []
        self._result_img = None
        if self._image is not None:
            self._canvas._redraw()
        self._status_var.set("  Bolge 2 temizlendi.")
        self._notebook.select(0)

    def _clear_all(self):
        self._boxes      = []
        self._results    = []
        self._result_img = None
        self._canvas.clear_boxes()
        if self._image is not None:
            self._canvas.set_image(self._image)
        for tab in self._crop_tabs:
            tab.clear()
        self._left.reset_results()
        self._status_var.set("  Temizlendi.")
        self._notebook.select(0)
