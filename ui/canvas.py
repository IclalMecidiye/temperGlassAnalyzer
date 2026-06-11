"""
ui/canvas.py  -  Ana görüntü canvas: gösterim + fare ile ROI seçimi + zoom/pan.
"""

import cv2
from PIL import Image, ImageDraw, ImageTk
import ttkbootstrap as ttk
from tkinter import messagebox

from config import BG_MID, FG_DIM
from core.image_utils import draw_boxes

_BG_RGB = (30, 41, 59)   # BG_MID rengi RGB


class ImageCanvas(ttk.Label):
    """Ana görüntüyü gösteren, fare ile bölge seçimine ve zoom/pan'e izin veren widget."""

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

        self._fit_scale = 1.0   # widget'a sığdırma ölçeği
        self._zoom      = 1.0   # kullanıcı zoom katsayısı
        self._pan_x     = 0.0   # pan (image pixel cinsinden)
        self._pan_y     = 0.0
        self._offset_x  = 0     # ortalama ofseti (ekran px)
        self._offset_y  = 0

        self._base_pil         = None   # önbellek: son render (PIL RGB, widget boyutunda)
        self._preview_box      = None
        self._render_scheduled = False

        self._panning       = False
        self._pan_start_ev  = (0, 0)
        self._pan_start_pos = (0.0, 0.0)

        self._poly_mode   = False
        self._poly_points = []   # (x_img, y_img) — tamamlanmamış polygon noktaları

        self.on_box_added = on_box_added

        self.bind("<ButtonPress-1>",   self._mouse_down)
        self.bind("<B1-Motion>",       self._mouse_move)
        self.bind("<ButtonRelease-1>", self._mouse_up)
        self.bind("<MouseWheel>",      self._mouse_wheel)
        self.bind("<ButtonPress-2>",   self._pan_start)
        self.bind("<B2-Motion>",       self._pan_move)
        self.bind("<ButtonRelease-2>", self._pan_end)
        # Orta tuş (button-3 = sağ, button-2 = orta) alternatif
        self.bind("<ButtonPress-3>",   self._pan_start)
        self.bind("<B3-Motion>",       self._pan_move)
        self.bind("<ButtonRelease-3>", self._pan_end)
        self.bind("<Motion>",          self._update_cursor)

    # ── Genel API ────────────────────────────────────────────────────────────

    def set_image(self, bgr_image) -> None:
        self._image        = bgr_image
        self._zoom         = 1.0
        self._pan_x        = 0.0
        self._pan_y        = 0.0
        self._panning      = False
        self._poly_points  = []
        self._rebuild()
        self._update_cursor()

    def set_poly_mode(self, enabled: bool) -> None:
        self._poly_mode   = enabled
        self._poly_points = []
        self._redraw()

    def show_bgr(self, bgr_image) -> None:
        """Analiz sonucunu göster (cache güncellemeden)."""
        if bgr_image is None:
            return
        pil = self._build_pil(bgr_image)
        self._show_pil(pil)

    def clear_boxes(self) -> None:
        self._boxes       = []
        self._poly_points = []
        self._redraw()

    def reset_zoom(self) -> None:
        self._zoom  = 1.0
        self._pan_x = 0.0
        self._pan_y = 0.0
        self._redraw()

    # ── İç yardımcılar ───────────────────────────────────────────────────────

    @property
    def _scale(self):
        return self._fit_scale * self._zoom

    def _lw_lh(self):
        return max(self.winfo_width(), 800), max(self.winfo_height(), 500)

    def _canvas_to_img(self, ex, ey):
        rx = (ex - self._offset_x) / self._scale + self._pan_x
        ry = (ey - self._offset_y) / self._scale + self._pan_y
        h, w = self._image.shape[:2]
        return (max(0, min(int(rx), w - 1)), max(0, min(int(ry), h - 1)))

    def _img_to_canvas(self, ix, iy):
        cx = (ix - self._pan_x) * self._scale + self._offset_x
        cy = (iy - self._pan_y) * self._scale + self._offset_y
        return cx, cy

    def _build_pil(self, bgr_img) -> Image.Image:
        """BGR görüntüden widget boyutunda PIL görüntüsü üret; transform state günceller."""
        img_rgb = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)
        w, h    = pil_img.size
        lw, lh  = self._lw_lh()

        self._fit_scale = min(lw / w, lh / h, 1.0)
        disp_scale      = self._scale   # fit_scale * zoom

        # Pan sınırla
        max_px = max(0.0, w - lw / disp_scale)
        max_py = max(0.0, h - lh / disp_scale)
        self._pan_x = max(0.0, min(self._pan_x, max_px))
        self._pan_y = max(0.0, min(self._pan_y, max_py))

        # Görünür alan (image space)
        vis_w = lw / disp_scale
        vis_h = lh / disp_scale
        x1 = int(self._pan_x)
        y1 = int(self._pan_y)
        x2 = int(min(self._pan_x + vis_w, w))
        y2 = int(min(self._pan_y + vis_h, h))

        cropped = pil_img.crop((x1, y1, x2, y2))
        tw = max(1, int((x2 - x1) * disp_scale))
        th = max(1, int((y2 - y1) * disp_scale))
        scaled = cropped.resize((tw, th), Image.LANCZOS)

        self._offset_x = max(0, (lw - tw) // 2)
        self._offset_y = max(0, (lh - th) // 2)

        bg = Image.new('RGB', (lw, lh), _BG_RGB)
        bg.paste(scaled, (self._offset_x, self._offset_y))
        return bg

    def _rebuild(self) -> None:
        """Base PIL cache'ini yeniden oluştur ve göster."""
        if self._image is None:
            return
        img = self._image.copy()
        draw_boxes(img, self._boxes)
        self._base_pil = self._build_pil(img)
        if self._poly_mode and self._poly_points:
            self._draw_poly_progress()
        else:
            self._show_pil(self._base_pil)

    def _redraw(self) -> None:
        self._rebuild()

    def _show_pil(self, pil_img) -> None:
        imgtk = ImageTk.PhotoImage(pil_img)
        self.config(image=imgtk, text="")
        self.image = imgtk

    def _draw_poly_progress(self) -> None:
        """Tamamlanmamış polygon noktalarını base PIL üzerine çiz."""
        if self._base_pil is None:
            return
        pil  = self._base_pil.copy()
        draw = ImageDraw.Draw(pil)
        canvas_pts = [(int(cx), int(cy))
                      for (ix, iy) in self._poly_points
                      for cx, cy in [self._img_to_canvas(ix, iy)]]

        if len(canvas_pts) > 1:
            for i in range(len(canvas_pts) - 1):
                draw.line([canvas_pts[i], canvas_pts[i + 1]], fill=(255, 200, 0), width=2)

        for cx, cy in canvas_pts:
            r = 5
            draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                         fill=(255, 200, 0), outline=(255, 255, 255), width=1)

        remaining = 4 - len(self._poly_points)
        msg = f"  {remaining} nokta daha  "
        draw.rectangle([6, 6, 148, 28], fill=(30, 41, 59))
        draw.text((10, 10), msg, fill=(255, 200, 0))
        self._show_pil(pil)

    def _draw_preview_on_base(self, x1, y1, x2, y2) -> None:
        """Cache üzerine hızlıca preview kutu çiz (PIL ImageDraw — opencv kopyası yok)."""
        if self._base_pil is None:
            return

        px1, py1 = self._img_to_canvas(x1, y1)
        px2, py2 = self._img_to_canvas(x2, y2)
        bw, bh   = self._base_pil.size
        px1 = max(0, min(int(px1), bw - 1))
        py1 = max(0, min(int(py1), bh - 1))
        px2 = max(0, min(int(px2), bw - 1))
        py2 = max(0, min(int(py2), bh - 1))
        if px2 <= px1 or py2 <= py1:
            return

        # Yarı saydam dolgu (RGBA composite)
        overlay  = Image.new('RGBA', self._base_pil.size, (0, 0, 0, 0))
        draw_ov  = ImageDraw.Draw(overlay)
        draw_ov.rectangle([px1, py1, px2, py2], fill=(0, 160, 255, 45))
        pil      = Image.alpha_composite(self._base_pil.convert('RGBA'), overlay).convert('RGB')

        # Kenarlık + bilgi
        draw = ImageDraw.Draw(pil)
        draw.rectangle([px1, py1, px2, py2], outline=(0, 160, 255), width=2)
        info = f"{abs(x2 - x1)} x {abs(y2 - y1)} px"
        draw.text((px1 + 4, max(py1 + 4, py2 - 18)), info, fill=(255, 255, 255))

        self._show_pil(pil)

    # ── İmleç yönetimi ──────────────────────────────────────────────────────

    def _update_cursor(self, event=None) -> None:
        if self._image is None:
            self.config(cursor="")
            return
        if self._panning:
            self.config(cursor="fleur")
        else:
            self.config(cursor="crosshair")

    # ── Fare olayları ────────────────────────────────────────────────────────

    def _mouse_down(self, event) -> None:
        if self._image is None:
            return
        if self._poly_mode:
            pt = self._canvas_to_img(event.x, event.y)
            self._poly_points.append(pt)
            if len(self._poly_points) == 4:
                self._finalize_poly()
            else:
                self._rebuild()
            return
        self._drawing = True
        self._start_x, self._start_y = self._canvas_to_img(event.x, event.y)

    def _finalize_poly(self) -> None:
        pts = self._poly_points[:]
        self._poly_points = []
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        bw = max(xs) - min(xs)
        bh = max(ys) - min(ys)
        if bw < 110 or bh < 110:
            messagebox.showwarning("Alan Çok Küçük",
                f"Seçilen alan {bw}x{bh} px — çok küçük!\n\nEn az 110x110 piksel seçin.")
            self._rebuild()
            return
        if len(self._boxes) >= self.MAX_BOXES:
            messagebox.showwarning("Uyarı",
                f"En fazla {self.MAX_BOXES} bölge seçebilirsiniz.\n"
                "Temizle butonuna basıp yeniden seçin.")
            self._rebuild()
            return
        idx = len(self._boxes)
        self._boxes.append(pts)   # liste → polygon olduğunu belirtir
        self._rebuild()
        if self.on_box_added:
            self.on_box_added(idx, pts)

    def _mouse_move(self, event) -> None:
        if self._image is None:
            return
        if self._panning:
            dx = (event.x - self._pan_start_ev[0]) / self._scale
            dy = (event.y - self._pan_start_ev[1]) / self._scale
            self._pan_x = self._pan_start_pos[0] - dx
            self._pan_y = self._pan_start_pos[1] - dy
            self._redraw()
            return
        if not self._drawing:
            return
        cx, cy = self._canvas_to_img(event.x, event.y)
        x1 = min(self._start_x, cx); y1 = min(self._start_y, cy)
        x2 = max(self._start_x, cx); y2 = max(self._start_y, cy)
        self._preview_box = (x1, y1, x2, y2)
        if not self._render_scheduled:
            self._render_scheduled = True
            self.after_idle(self._flush_preview)

    def _flush_preview(self) -> None:
        self._render_scheduled = False
        if self._preview_box is not None:
            self._draw_preview_on_base(*self._preview_box)

    def _mouse_up(self, event) -> None:
        if self._image is None:
            return
        if not self._drawing:
            return
        self._drawing     = False
        self._preview_box = None
        ex, ey            = self._canvas_to_img(event.x, event.y)

        if abs(ex - self._start_x) < 5 or abs(ey - self._start_y) < 5:
            self._redraw()
            return

        if len(self._boxes) >= self.MAX_BOXES:
            messagebox.showwarning(
                "Uyarı",
                f"En fazla {self.MAX_BOXES} bölge seçebilirsiniz.\n"
                "Temizle butonuna basıp yeniden seçin.",
            )
            self._redraw()
            return

        alan_w = abs(ex - self._start_x)
        alan_h = abs(ey - self._start_y)
        if alan_w < 110 or alan_h < 110:
            messagebox.showwarning("Alan Çok Küçük",
                f"Seçilen alan {alan_w}x{alan_h} px — çok küçük!\n\nEn az 110x110 piksel seçin.")
            self._redraw()
            return
        if alan_w > 800 or alan_h > 800:
            messagebox.showwarning("Alan Çok Büyük",
                f"Seçilen alan {alan_w}x{alan_h} px — çok büyük!\n\nEn fazla 800x800 piksel seçin.")
            self._redraw()
            return

        box = (self._start_x, self._start_y, ex, ey)
        idx = len(self._boxes)
        self._boxes.append(box)
        self._redraw()

        if self.on_box_added:
            self.on_box_added(idx, box)

    def _mouse_wheel(self, event) -> None:
        if self._image is None:
            return
        old_scale = self._scale
        factor    = 1.15 if event.delta > 0 else 1 / 1.15
        self._zoom = max(1.0, min(self._zoom * factor, 8.0))
        new_scale  = self._scale

        # Fare imleci altındaki nokta sabit kalsın
        img_x = (event.x - self._offset_x) / old_scale + self._pan_x
        img_y = (event.y - self._offset_y) / old_scale + self._pan_y
        self._pan_x = img_x - (event.x - self._offset_x) / new_scale
        self._pan_y = img_y - (event.y - self._offset_y) / new_scale

        self._redraw()
        self._update_cursor()

    def _pan_start(self, event) -> None:
        if self._image is None:
            return
        self._panning       = True
        self._pan_start_ev  = (event.x, event.y)
        self._pan_start_pos = (self._pan_x, self._pan_y)

    def _pan_move(self, event) -> None:
        if not self._panning or self._image is None:
            return
        dx = (event.x - self._pan_start_ev[0]) / self._scale
        dy = (event.y - self._pan_start_ev[1]) / self._scale
        self._pan_x = self._pan_start_pos[0] - dx
        self._pan_y = self._pan_start_pos[1] - dy
        self._redraw()

    def _pan_end(self, event) -> None:
        self._panning = False
