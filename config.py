RENK1_CV  = (52, 211, 153)   # BGR
RENK2_CV  = (251, 191, 36)

RENK1_HEX = "#34d399"
RENK2_HEX = "#fbbf24"

# ── Dark theme colours ────────────────────────────────────────────────────
BG_DARK  = "#0f172a"
BG_MID   = "#1e293b"
BG_CARD  = "#263248"
FG_MAIN  = "#e2e8f0"
FG_DIM   = "#64748b"
ACCENT   = "#38bdf8"

# ── Light theme colours ───────────────────────────────────────────────────
BG_DARK_LIGHT  = "#f1f5f9"
BG_MID_LIGHT   = "#e2e8f0"
BG_CARD_LIGHT  = "#ffffff"
FG_MAIN_LIGHT  = "#1e293b"
FG_DIM_LIGHT   = "#475569"
ACCENT_LIGHT   = "#0284c7"

# ── Theme palette lookup ──────────────────────────────────────────────────
THEMES = {
    "dark": {
        "bg_dark": BG_DARK,
        "bg_mid":  BG_MID,
        "bg_card": BG_CARD,
        "fg_main": FG_MAIN,
        "fg_dim":  FG_DIM,
        "accent":  ACCENT,
        "ttk_theme": "darkly",
    },
    "light": {
        "bg_dark": BG_DARK_LIGHT,
        "bg_mid":  BG_MID_LIGHT,
        "bg_card": BG_CARD_LIGHT,
        "fg_main": FG_MAIN_LIGHT,
        "fg_dim":  FG_DIM_LIGHT,
        "accent":  ACCENT_LIGHT,
        "ttk_theme": "cosmo",
    },
}

IMAGE_FILETYPES = [("Resimler", "*.jpg *.jpeg *.png *.bmp *.tif *.tiff")]
WINDOW_SIZE     = "1400x860"
WINDOW_MIN      = (1000, 650)
CROP_MAX_SIZE   = 700
