import ttkbootstrap as ttk
from config import BG_CARD, BG_MID, FG_MAIN, FG_DIM, ACCENT, RENK1_HEX, RENK2_HEX

MAX_BOLGE = 2
COUNT_MIN = 40
COUNT_MAX = 350

_UI = ("Segoe UI", 9)
_UI_BOLD = ("Segoe UI", 9, "bold")
_UI_SM   = ("Segoe UI", 8)
_UI_SM_B = ("Segoe UI", 8, "bold")
_UI_XS   = ("Segoe UI", 7)
_UI_NUM  = ("Segoe UI", 34, "bold")
_UI_HEAD = ("Segoe UI", 8, "bold")


def _section_label(parent, text):
    ttk.Label(parent, text=text, font=_UI_HEAD,
              foreground=FG_DIM, background=BG_CARD).pack(anchor="w", padx=14, pady=(14, 4))
    ttk.Frame(parent, height=1, style="Card.TFrame").pack(fill="x", padx=14, pady=(0, 6))


class LeftPanel(ttk.Frame):

    def __init__(self, parent, **kwargs):
        super().__init__(parent, width=250, **kwargs)
        self.pack_propagate(False)
        self.configure(style="Card.TFrame")
        self.result_vars  = [ttk.StringVar(value="—") for _ in range(MAX_BOLGE)]
        self._uyg_labels  = []
        self.on_load       = None
        self.on_analyze    = None
        self.on_save       = None
        self.on_pdf        = None
        self.on_kaydet     = None
        self.on_clear1     = None
        self.on_clear2     = None
        self.on_clear_all  = None
        self.on_poly_toggle = None
        self.poly_mode_var = ttk.BooleanVar(value=False)
        self._btn_analyze  = None
        self._build()

    def _build(self):
        self._build_results()
        self._build_actions()
        self._build_shortcuts()

    def _build_results(self):
        _section_label(self, "ANALIZ SONUCLARI")
        colors = [RENK1_HEX, RENK2_HEX]

        for i in range(MAX_BOLGE):
            row = ttk.Frame(self, style="Card.TFrame")
            row.pack(fill="x", padx=12, pady=4)

            # Sol renkli çubuk
            accent_bar = ttk.Frame(row, width=3, style="Card.TFrame")
            accent_bar.pack(side="left", fill="y")
            accent_bar.configure(style="Card.TFrame")
            # Arka plan rengi doğrudan widget'a ver
            try:
                accent_bar.configure(background=colors[i])
            except Exception:
                pass

            content = ttk.Frame(row, style="Card.TFrame")
            content.pack(side="left", fill="both", expand=True, padx=(8, 6))

            ttk.Label(content, text=f"BOLGE {i + 1}", font=_UI_SM_B,
                      foreground=colors[i], background=BG_CARD).pack(anchor="w", pady=(6, 0))

            ttk.Label(content, textvariable=self.result_vars[i],
                      font=_UI_NUM, foreground=colors[i],
                      background=BG_CARD).pack(anchor="w")

            ttk.Label(content, text="parca", font=_UI_SM,
                      foreground=FG_DIM, background=BG_CARD).pack(anchor="w")

            lbl = ttk.Label(content, text="", font=_UI_SM_B, background=BG_CARD)
            lbl.pack(anchor="w", pady=(2, 6))
            self._uyg_labels.append(lbl)

    def _build_actions(self):
        _section_label(self, "ISLEMLER")

        # Ana islemler
        ttk.Button(self, text="  Fotograf Yukle",
                   bootstyle="info", command=lambda: self.on_load and self.on_load(),
                   width=26).pack(padx=14, pady=(0, 3))

        ttk.Checkbutton(
            self, text="  4 Kose Modu",
            variable=self.poly_mode_var,
            bootstyle="warning-outline-toolbutton",
            command=lambda: self.on_poly_toggle and self.on_poly_toggle(self.poly_mode_var.get()),
            width=26,
        ).pack(padx=14, pady=(0, 6))

        self._btn_analyze = ttk.Button(self, text="  Analiz Et          F5",
                                       bootstyle="success",
                                       command=lambda: self.on_analyze and self.on_analyze(),
                                       width=26)
        self._btn_analyze.pack(padx=14, pady=(0, 10))

        # Kayit islemleri
        ttk.Frame(self, height=1, style="Card.TFrame").pack(fill="x", padx=14, pady=(0, 6))
        ttk.Label(self, text="KAYDET", font=_UI_HEAD, foreground=FG_DIM,
                  background=BG_CARD).pack(anchor="w", padx=14, pady=(0, 4))

        for txt, style_b, cb in [
            ("  Goruntu Kaydet", "warning-outline", lambda: self.on_save   and self.on_save()),
            ("  PDF Rapor",      "primary-outline", lambda: self.on_pdf    and self.on_pdf()),
            ("  Sayimi Kaydet",  "secondary-outline",lambda: self.on_kaydet and self.on_kaydet()),
        ]:
            ttk.Button(self, text=txt, bootstyle=style_b, command=cb,
                       width=26).pack(padx=14, pady=2)

        # Temizle
        ttk.Frame(self, height=1, style="Card.TFrame").pack(fill="x", padx=14, pady=(8, 6))
        ttk.Label(self, text="TEMIZLE", font=_UI_HEAD, foreground=FG_DIM,
                  background=BG_CARD).pack(anchor="w", padx=14, pady=(0, 4))

        for txt, cb in [
            ("  Bolge 1", lambda: self.on_clear1    and self.on_clear1()),
            ("  Bolge 2", lambda: self.on_clear2    and self.on_clear2()),
            ("  Tumu",    lambda: self.on_clear_all and self.on_clear_all()),
        ]:
            ttk.Button(self, text=txt, bootstyle="danger-outline", command=cb,
                       width=26).pack(padx=14, pady=2)

    def _build_shortcuts(self):
        ttk.Frame(self, height=1, style="Card.TFrame").pack(fill="x", padx=14, pady=(10, 6))
        hints = [
            ("Ctrl+O", "Yukle"),
            ("F5",     "Analiz"),
            ("Ctrl+S", "Kaydet"),
            ("Ctrl+P", "PDF"),
            ("Esc",    "Temizle"),
            ("Scroll", "Zoom"),
            ("Sag Tik","Pan"),
        ]
        grid = ttk.Frame(self, style="Card.TFrame")
        grid.pack(anchor="w", padx=14, pady=(0, 12))
        for row_i, (key, action) in enumerate(hints):
            ttk.Label(grid, text=key, font=_UI_XS, foreground=ACCENT,
                      background=BG_CARD, width=7).grid(row=row_i, column=0, sticky="w")
            ttk.Label(grid, text=action, font=_UI_XS, foreground=FG_DIM,
                      background=BG_CARD).grid(row=row_i, column=1, sticky="w", padx=(4, 0))

    def set_analyze_button_state(self, enabled: bool):
        if self._btn_analyze:
            self._btn_analyze.config(state="normal" if enabled else "disabled")

    def update_result(self, idx: int, count: int):
        self.result_vars[idx].set(str(count))
        if COUNT_MIN <= count <= COUNT_MAX:
            self._uyg_labels[idx].config(text="UYGUNDUR", foreground="#6CCB5F")
        else:
            self._uyg_labels[idx].config(text="UYGUN DEGIL", foreground="#D13438")

    def reset_results(self):
        for v in self.result_vars:
            v.set("—")
        for lbl in self._uyg_labels:
            lbl.config(text="")


class CropTab(ttk.Frame):

    def __init__(self, parent, idx, **kwargs):
        super().__init__(parent, **kwargs)
        self.idx = idx
        renk_hex = [RENK1_HEX, RENK2_HEX][idx]

        top = ttk.Frame(self)
        top.pack(fill="x", padx=14, pady=10)
        ttk.Label(top, text=f"BOLGE {idx + 1}", font=("Segoe UI", 11, "bold"),
                  foreground=renk_hex).pack(side="left")
        self._info_var = ttk.StringVar(value="")
        ttk.Label(top, textvariable=self._info_var,
                  font=("Segoe UI", 9), foreground=FG_DIM).pack(side="left", padx=12)

        self.image_label = ttk.Label(self, anchor="center", background=BG_MID,
                                      text="Henuz secilmedi", foreground=FG_DIM,
                                      font=("Segoe UI", 11))
        self.image_label.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    def update_image(self, imgtk, width, height):
        self.image_label.config(image=imgtk, text="")
        self.image_label.image = imgtk
        self._info_var.set(f"{width} x {height} px")

    def clear(self):
        self.image_label.config(image="", text="Henuz secilmedi")
        self.image_label.image = None
        self._info_var.set("")
