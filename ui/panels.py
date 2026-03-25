

import ttkbootstrap as ttk
from config import BG_CARD, BG_MID, FG_MAIN, FG_DIM, ACCENT, RENK1_HEX, RENK2_HEX

MAX_BOLGE = 2


def _section_header(parent, title: str) -> None:
    ttk.Label(
        parent, text=title,
        font=("Courier New", 9, "bold"),
        foreground=ACCENT, background=BG_CARD,
    ).pack(anchor="w", padx=14, pady=(16, 4))
    ttk.Frame(parent, height=1, style="Card.TFrame").pack(
        fill="x", padx=14, pady=(0, 8)
    )


class LeftPanel(ttk.Frame):

    def __init__(self, parent, **kwargs):
        super().__init__(parent, width=210, **kwargs)
        self.pack_propagate(False)
        self.configure(style="Card.TFrame")

        self.result_vars = [ttk.StringVar(value="—") for _ in range(MAX_BOLGE)]

        self.on_load    = None
        self.on_analyze = None
        self.on_save    = None
        self.on_pdf     = None
        self.on_kaydet  = None
        self.on_clear   = None

        self._build()

    def _build(self) -> None:
        self._build_results()
        self._build_actions()

    def _build_results(self) -> None:
        _section_header(self, "SONUÇLAR")
        colors = [RENK1_HEX, RENK2_HEX]
        for i in range(MAX_BOLGE):
            card = ttk.Frame(self, style="Card.TFrame")
            card.pack(fill="x", padx=10, pady=4)
            ttk.Label(card, text=f"  BÖLGE {i + 1}",
                      font=("Courier New", 8, "bold"),
                      foreground=colors[i], background=BG_CARD,
                      ).pack(anchor="w", padx=6, pady=(6, 0))
            ttk.Label(card, textvariable=self.result_vars[i],
                      font=("Courier New", 26, "bold"),
                      foreground=colors[i], background=BG_CARD,
                      ).pack(anchor="w", padx=10)
            ttk.Label(card, text="parça",
                      font=("Courier New", 8),
                      foreground=FG_DIM, background=BG_CARD,
                      ).pack(anchor="w", padx=10, pady=(0, 6))

    def _build_actions(self) -> None:
        _section_header(self, "İŞLEMLER")
        buttons = [
            ("Fotoğraf Yükle",  "info",      lambda: self.on_load    and self.on_load()),
            ("Analiz Et",       "success",   lambda: self.on_analyze and self.on_analyze()),
            ("Görüntü Kaydet",  "warning",   lambda: self.on_save    and self.on_save()),
            ("PDF Rapor",       "primary",   lambda: self.on_pdf     and self.on_pdf()),
            ("Sayimi Kaydet",   "danger",    lambda: self.on_kaydet  and self.on_kaydet()),
            ("Temizle",         "secondary", lambda: self.on_clear   and self.on_clear()),
        ]
        for txt, style_b, cmd in buttons:
            ttk.Button(self, text=txt, bootstyle=f"{style_b}-outline",
                       command=cmd, width=22).pack(padx=14, pady=3)

    def reset_results(self) -> None:
        for v in self.result_vars:
            v.set("—")


class CropTab(ttk.Frame):

    def __init__(self, parent, idx: int, **kwargs):
        super().__init__(parent, **kwargs)
        self.idx = idx
        renk_hex = [RENK1_HEX, RENK2_HEX][idx]

        top = ttk.Frame(self)
        top.pack(fill="x", padx=12, pady=8)
        ttk.Label(top,
                  text=f"BÖLGE {idx + 1}",
                  font=("Courier New", 11, "bold"),
                  foreground=renk_hex,
                  ).pack(side="left")

        self.image_label = ttk.Label(
            self, anchor="center", background=BG_MID,
            text="Henüz seçilmedi",
            foreground=FG_DIM, font=("Courier New", 11),
        )
        self.image_label.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def update_image(self, imgtk, width: int, height: int) -> None:
        self.image_label.config(image=imgtk, text="")
        self.image_label.image = imgtk

    def clear(self) -> None:
        self.image_label.config(image="", text="Henüz seçilmedi")
        self.image_label.image = None