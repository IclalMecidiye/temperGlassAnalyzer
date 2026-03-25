"""
ui/canvas.py  -  Ana görüntü canvas: gösterim + fare ile ROI seçimi.
"""

import cv2
from PIL import Image, ImageTk
import ttkbootstrap as ttk
from tkinter import messagebox

from config import BG_MID, FG_DIM
from core.image_utils import draw_boxes, draw_preview_box


class ImageCanvas(ttk.Label):
    """Ana görüntüyü gösteren ve fare ile bölge seçimine izin veren widget."""

    MAX_BOXES = 2

    def __init__(self, parent, on_box_added=None, **kwargs):
        super().__init__(
            parent,
            anchor="center",
            background=BG_MID,
            text="Fotoğraf yükleyip analiz etmek istediğiniz bölgeyi seçin",
            foreground=FG_DIM,
            font=("Segoe UI", 12),
            **kwargs,
        )
        self._image    = None
        self._boxes    = []
        self._drawing  = False
        self._start_x  = 0
        self._start_y  = 0
        self._scale    = 1.0
        self._offset_x = 0
        self._offset_y = 0
        self.on_box_added = on_box_added

        self.bind("<ButtonPress-1>",   self._mouse_down)
        self.bind("<B1-Motion>",       self._mouse_move)
        self.bind("<ButtonRelease-1>", self._mouse_up)

    # ── Genel API ────────────────────────────────────────────────────────────

    def set_image(self, bgr_image) -> None:
        self._image = bgr_image
        self._redraw()

    def show_bgr(self, bgr_image) -> None:
        self._render(bgr_image)

    def clear_boxes(self) -> None:
        self._boxes = []
        self._redraw()

    # ── İç yardımcılar ───────────────────────────────────────────────────────

    def _canvas_to_img(self, ex, ey):
        rx = (ex - self._offset_x) / self._scale
        ry = (ey - self._offset_y) / self._scale
        h, w = self._image.shape[:2]
        return (
            max(0, min(int(rx), w - 1)),
            max(0, min(int(ry), h - 1)),
        )

    def _redraw(self) -> None:
        if self._image is None:
            return
        img = self._image.copy()
        draw_boxes(img, self._boxes)
        self._render(img)

    def _render(self, bgr_img) -> None:
        img_rgb = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)

        lw = max(self.winfo_width(),  800)
        lh = max(self.winfo_height(), 500)

        self._scale    = min(lw / pil_img.width, lh / pil_img.height, 1.0)
        nw             = max(1, int(pil_img.width  * self._scale))
        nh             = max(1, int(pil_img.height * self._scale))
        self._offset_x = (lw - nw) // 2
        self._offset_y = (lh - nh) // 2

        pil_img = pil_img.resize((nw, nh), Image.LANCZOS)
        imgtk   = ImageTk.PhotoImage(pil_img)
        self.config(image=imgtk, text="")
        self.image = imgtk

    # ── Fare olayları ────────────────────────────────────────────────────────

    def _mouse_down(self, event) -> None:
        if self._image is None:
            return
        self._drawing = True
        self._start_x, self._start_y = self._canvas_to_img(event.x, event.y)

    def _mouse_move(self, event) -> None:
        if not self._drawing or self._image is None:
            return
        cx, cy  = self._canvas_to_img(event.x, event.y)
        preview = self._image.copy()
        draw_boxes(preview, self._boxes)
        x1 = min(self._start_x, cx); y1 = min(self._start_y, cy)
        x2 = max(self._start_x, cx); y2 = max(self._start_y, cy)
        draw_preview_box(preview, x1, y1, x2, y2)
        self._render(preview)

    def _mouse_up(self, event) -> None:
        if not self._drawing or self._image is None:
            return
        self._drawing = False
        ex, ey = self._canvas_to_img(event.x, event.y)

        if abs(ex - self._start_x) < 5 or abs(ey - self._start_y) < 5:
            return

        if len(self._boxes) >= self.MAX_BOXES:
            messagebox.showwarning(
                "Uyarı",
                f"En fazla {self.MAX_BOXES} bölge seçebilirsiniz.\n"
                "Temizle butonuna basıp yeniden seçin.",
            )
            return

        box = (self._start_x, self._start_y, ex, ey)
        
        # Alan boyut kontrolü
        alan_w = abs(ex - self._start_x)
        alan_h = abs(ey - self._start_y)
        if alan_w < 110 or alan_h < 110:
            from tkinter import messagebox
            uyari = "Secilen alan " + str(alan_w) + "x" + str(alan_h) + " px - cok kucuk!\n\n"
            uyari += "En az 110x110 piksel secin."
            messagebox.showwarning("Alan Cok Kucuk", uyari)
            self._redraw()
            return
        if alan_w > 800 or alan_h > 800:
            from tkinter import messagebox
            uyari = "Secilen alan " + str(alan_w) + "x" + str(alan_h) + " px - cok buyuk!\n\n"
            uyari += "En fazla 800x800 piksel secin."
            messagebox.showwarning("Alan Cok Buyuk", uyari)
            self._redraw()
            return

        idx = len(self._boxes)
        self._boxes.append(box)
        self._redraw()

        if self.on_box_added:
            self.on_box_added(idx, box)