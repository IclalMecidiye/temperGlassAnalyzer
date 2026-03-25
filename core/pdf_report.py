

import os, datetime, tempfile
import cv2, numpy as np
from PIL import Image

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer,
        Image as RLImage, Table, TableStyle, HRFlowable,
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False

COUNT_MIN = 40
COUNT_MAX = 350

FN  = "Helvetica"
FNB = "Helvetica-Bold"


def _register_fonts():
    global FN, FNB
    pairs = [
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",      "DV",  False),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "DVB", True),
        ("C:/Windows/Fonts/arial.ttf",   "DV",  False),
        ("C:/Windows/Fonts/arialbd.ttf", "DVB", True),
    ]
    registered = {}
    for path, name, bold in pairs:
        if os.path.exists(path) and name not in registered:
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                registered[name] = True
                if not bold:
                    FN  = name
                else:
                    FNB = name
            except Exception:
                pass


def _ps(name, font=None, bold=False, size=10, color="#e2e8f0", align=TA_LEFT, **kw):
    """ParagraphStyle kısayolu."""
    return ParagraphStyle(
        name,
        fontName=FNB if bold else (font or FN),
        fontSize=size,
        textColor=colors.HexColor(color),
        alignment=align,
        leading=size * 1.4,
        **kw,
    )


def _uygunluk(count):
    if COUNT_MIN <= count <= COUNT_MAX:
        return "UYGUNDUR", "#34d399"
    return "UYGUN DEĞILDIR", "#ef4444"


def _bgr_pil(bgr):
    return Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))


def _rl_img(pil_img, max_w, max_h):
    ratio = min(max_w / pil_img.width, max_h / pil_img.height, 1.0)
    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    pil_img.save(tmp.name, "JPEG", quality=88)
    tmp.close()
    return RLImage(tmp.name,
                   width=pil_img.width * ratio,
                   height=pil_img.height * ratio)


def save_pdf(path, original_bgr, result_bgr, results, filename=""):
    if not REPORTLAB_OK:
        raise ImportError("pip install reportlab")

    _register_fonts()

    W, H = A4
    doc = SimpleDocTemplate(path, pagesize=A4,
                             leftMargin=2*cm, rightMargin=2*cm,
                             topMargin=2*cm,  bottomMargin=2*cm)
    cw = W - 4*cm        
    BOLGE_RENK = ["#34d399", "#fbbf24"]

    def HR():
        return HRFlowable(width="100%", thickness=1,
                          color=colors.HexColor("#263248"), spaceAfter=4)

    def P(txt, sty): return Paragraph(txt, sty)

    story = []

    story.append(P("TEMPERLI CAM ANALIZI",
                   _ps("tit", bold=True, size=20, color="#38bdf8", spaceAfter=3)))
    tarih = datetime.datetime.now().strftime("%d.%m.%Y  %H:%M")
    dosya = os.path.basename(filename) if filename else "—"
    story.append(P(f"Tarih: {tarih}     Dosya: {dosya}",
                   _ps("sub", size=9, color="#64748b", spaceAfter=10)))
    story.append(HR())
    story.append(Spacer(1, 0.35*cm))

    story.append(P("ANALIZ SONUCLARI",
                   _ps("h1", bold=True, size=11, color="#38bdf8",
                       spaceBefore=6, spaceAfter=6)))

    th = _ps("th", bold=True, size=10, color="#38bdf8", align=TA_CENTER)
    rows = [[P("Bolge", th), P("Parca Sayisi", th), P("Uygunluk (40-350)", th)]]

    for i, (count, *_ ) in enumerate(results):
        uygun_txt, uygun_renk = _uygunluk(count)
        rows.append([
            P(f"Bolge {i+1}",
              _ps(f"tc{i}", bold=True, size=11,
                  color=BOLGE_RENK[i], align=TA_CENTER)),
            P(str(count),
              _ps(f"tv{i}", bold=True, size=18,
                  color=BOLGE_RENK[i], align=TA_CENTER)),
            P(uygun_txt,
              _ps(f"tu{i}", bold=True, size=12,
                  color=uygun_renk, align=TA_CENTER)),
        ])

    if len(results) == 2:
        fark  = abs(results[0][0] - results[1][0])
        fazla = "Bolge 1" if results[0][0] > results[1][0] else "Bolge 2"
        td = _ps("tdf", size=9, color="#94a3b8", align=TA_CENTER)
        rows.append([P("Fark", td), P(str(fark), td), P(f"Daha fazla: {fazla}", td)])

    tbl = Table(rows, colWidths=[cw*0.22, cw*0.28, cw*0.50])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",     (0,0),(-1,0),  colors.HexColor("#1e293b")),
        ("ROWBACKGROUNDS", (0,1),(-1,-1),
         [colors.HexColor("#263248"), colors.HexColor("#1e2a3a")]),
        ("GRID",           (0,0),(-1,-1), 0.5, colors.HexColor("#38bdf8")),
        ("VALIGN",         (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",     (0,0),(-1,-1), 10),
        ("BOTTOMPADDING",  (0,0),(-1,-1), 10),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 0.5*cm))

    story.append(P("ANALIZ GORUNTULERI",
                   _ps("h2", bold=True, size=11, color="#38bdf8",
                       spaceBefore=6, spaceAfter=6)))

    half = cw / 2 - 0.3*cm
    rl_orig   = _rl_img(_bgr_pil(original_bgr), half, 8*cm)
    rl_result = _rl_img(_bgr_pil(result_bgr),   half, 8*cm)

    sc = _ps("sc", size=8, color="#64748b", align=TA_CENTER)
    img_tbl = Table(
        [[P("Orijinal", sc), P("Analiz Sonucu", sc)],
         [rl_orig, rl_result]],
        colWidths=[cw/2, cw/2],
    )
    img_tbl.setStyle(TableStyle([
        ("ALIGN",         (0,0),(-1,-1), "CENTER"),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0),(-1,-1), 3),
        ("BOTTOMPADDING", (0,0),(-1,-1), 3),
    ]))
    story.append(img_tbl)
    story.append(Spacer(1, 0.4*cm))

    crop_cells = []
    for i, (count, x1, y1, x2, y2, _) in enumerate(results):
        xs1,xs2 = sorted([x1,x2]); ys1,ys2 = sorted([y1,y2])
        crop = original_bgr[ys1:ys2, xs1:xs2]
        if crop.size == 0:
            continue
        rl = _rl_img(_bgr_pil(crop), cw/2 - 0.4*cm, 6*cm)
        ut, ur = _uygunluk(count)
        lbl = P(
            f"<b>Bolge {i+1}</b> — {count} parca<br/>"
            f'<font color="{ur}">{ut}</font>',
            _ps(f"cl{i}", bold=False, size=9,
                color=BOLGE_RENK[i], align=TA_CENTER)
        )
        crop_cells.append((lbl, rl))

    if crop_cells:
        story.append(P("SECILEN BOLGELER",
                       _ps("h3", bold=True, size=11, color="#38bdf8",
                           spaceBefore=6, spaceAfter=6)))
        if len(crop_cells) == 1:
            ct = Table([[crop_cells[0][0]], [crop_cells[0][1]]],
                       colWidths=[cw])
        else:
            ct = Table(
                [[crop_cells[0][0], crop_cells[1][0]],
                 [crop_cells[0][1], crop_cells[1][1]]],
                colWidths=[cw/2, cw/2],
            )
        ct.setStyle(TableStyle([
            ("ALIGN",         (0,0),(-1,-1), "CENTER"),
            ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
            ("TOPPADDING",    (0,0),(-1,-1), 4),
            ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ]))
        story.append(ct)

    story.append(Spacer(1, 0.5*cm))
    story.append(HR())
    story.append(P("Temperli Cam Analizi  —  Otomatik Kirik Sayim Sistemi",
                   _ps("ft", size=7, color="#64748b", align=TA_CENTER)))

    doc.build(story)
