"""PDF / Excel / CSV hisobotlar."""

from functools import lru_cache

from app.config import FONTS_DIR

FONT = "DejaVu"
FONT_BOLD = "DejaVu-Bold"


@lru_cache(maxsize=1)
def register_fonts() -> None:
    """Helvetica o'zbek (ʻ), kirill va μ belgilarini ko'rsatmaydi — DejaVu ishlatamiz."""
    from reportlab.lib.fonts import addMapping
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    pdfmetrics.registerFont(TTFont(FONT, str(FONTS_DIR / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont(FONT_BOLD, str(FONTS_DIR / "DejaVuSans-Bold.ttf")))
    addMapping(FONT, 0, 0, FONT)
    addMapping(FONT, 1, 0, FONT_BOLD)
    addMapping(FONT, 0, 1, FONT)
    addMapping(FONT, 1, 1, FONT_BOLD)


def styles():
    """Umumiy paragraf uslublari (bemor va tadqiqot hisobotlari uchun bir xil)."""
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle

    register_fonts()
    ink = colors.HexColor("#111827")
    return {
        "h1": ParagraphStyle("H1", fontName=FONT_BOLD, fontSize=17, leading=21,
                             textColor=colors.HexColor("#0f172a"), spaceAfter=4),
        "h2": ParagraphStyle("H2", fontName=FONT_BOLD, fontSize=12.5, leading=16,
                             textColor=colors.HexColor("#1e3a8a"), spaceBefore=8, spaceAfter=4),
        "h3": ParagraphStyle("H3", fontName=FONT_BOLD, fontSize=10.5, leading=13,
                             textColor=ink, spaceBefore=4, spaceAfter=2),
        "body": ParagraphStyle("Body", fontName=FONT, fontSize=10, leading=13.5,
                               textColor=ink, spaceAfter=3),
        "small": ParagraphStyle("Small", fontName=FONT, fontSize=8.5, leading=11,
                                textColor=colors.HexColor("#52514e"), spaceAfter=2),
        "cell": ParagraphStyle("Cell", fontName=FONT, fontSize=8.5, leading=10.5, textColor=ink),
        "cellb": ParagraphStyle("CellB", fontName=FONT_BOLD, fontSize=8.5, leading=10.5,
                                textColor=ink),
        "warn": ParagraphStyle("Warn", fontName=FONT, fontSize=9, leading=12,
                               textColor=colors.HexColor("#991b1b")),
    }


def table_style(header: bool = True, zebra: bool = True):
    from reportlab.lib import colors
    from reportlab.platypus import TableStyle

    st = [
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 8.8),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#111827")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#e1e0d9")),
    ]
    if header:
        st += [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ]
    if zebra:
        st.append(("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1),
                   [colors.white, colors.HexColor("#f5f7fb")]))
    return TableStyle(st)
