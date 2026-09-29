"""
PDF hisobot generatori (reportlab).
Chiroyli, chop etishga tayyor, klinik format.
"""

from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from calculator import (
    classify_bmi, classify_homa_ir, classify_waist,
    combined_risk_report, ten_year_risk,
)


def build_pdf_report(user: dict, screening: dict) -> bytes:
    """
    user, screening — DB dan bitta qator (dict).
    Qaytadi: PDF bytes.
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm,
        title=f"Skrining hisoboti #{screening['id']}",
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle(
        "H1", parent=styles["Heading1"], fontSize=18,
        textColor=colors.HexColor("#1f2937"), spaceAfter=6,
    )
    h2 = ParagraphStyle(
        "H2", parent=styles["Heading2"], fontSize=13,
        textColor=colors.HexColor("#374151"), spaceAfter=4,
    )
    body = ParagraphStyle(
        "Body", parent=styles["BodyText"], fontSize=10.5,
        textColor=colors.HexColor("#111827"), spaceAfter=4, leading=14,
    )
    small = ParagraphStyle(
        "Small", parent=styles["BodyText"], fontSize=9,
        textColor=colors.HexColor("#6b7280"), spaceAfter=2, leading=11,
    )
    disclaim = ParagraphStyle(
        "Disc", parent=body, fontSize=9,
        textColor=colors.HexColor("#991b1b"), leading=12,
    )

    elems = []

    # Sarlavha
    elems.append(Paragraph("Diabet xavfi skrining hisoboti", h1))
    elems.append(Paragraph(
        f"HOMA-IR + FINDRISC | Hujjat #{screening['id']} | "
        f"Sana: {screening['created_at'][:16]}",
        small,
    ))
    elems.append(Spacer(1, 0.4*cm))

    # Foydalanuvchi ma'lumoti
    name = user["display_name"] or "—"
    age = screening["age"]
    sex_txt = "Erkak" if screening["sex"] == "M" else "Ayol"
    elems.append(Paragraph("Foydalanuvchi", h2))
    user_tbl = Table([
        ["Ism / ID", name],
        ["Yoshi", f"{age} yosh"],
        ["Jinsi", sex_txt],
    ], colWidths=[4*cm, 12*cm])
    user_tbl.setStyle(_table_style())
    elems.append(user_tbl)
    elems.append(Spacer(1, 0.4*cm))

    # Antropometriya
    elems.append(Paragraph("Antropometrik ko'rsatkichlar", h2))
    bmi_cls = classify_bmi(screening["bmi"])
    waist_cls = classify_waist(screening["sex"], screening["waist"])
    anthro = Table([
        ["Vazn", f"{screening['weight']} kg", ""],
        ["Bo'y", f"{screening['height']} sm", ""],
        ["BMI", f"{screening['bmi']:.1f}", bmi_cls],
        ["Bel aylanasi", f"{screening['waist']:.0f} sm", waist_cls],
    ], colWidths=[4*cm, 4*cm, 8*cm])
    anthro.setStyle(_table_style())
    elems.append(anthro)
    elems.append(Spacer(1, 0.4*cm))

    # Klinik (agar mavjud bo'lsa)
    if screening["fasting_glucose"] and screening["fasting_insulin"]:
        elems.append(Paragraph("Klinik ko'rsatkichlar (och qoringa)", h2))
        homa_cls = classify_homa_ir(screening["homa_ir"])
        clin = Table([
            ["Glukoza", f"{screening['fasting_glucose']} mmol/L"],
            ["Insulin", f"{screening['fasting_insulin']} μIU/mL"],
            ["HOMA-IR", f"{screening['homa_ir']:.2f}  —  {homa_cls}"],
        ], colWidths=[4*cm, 12*cm])
        clin.setStyle(_table_style())
        elems.append(clin)
        elems.append(Spacer(1, 0.4*cm))

    # FINDRISC natija
    elems.append(Paragraph("FINDRISC natijasi", h2))
    fr_score = screening["findrisc"]
    fr_band = screening["findrisc_band"]
    ten_yr = ten_year_risk(fr_band)
    fr = Table([
        ["Umumiy ball", f"{fr_score} / 26"],
        ["Kategoriya", fr_band.upper()],
        ["10 yillik xavf", ten_yr],
    ], colWidths=[4*cm, 12*cm])
    fr.setStyle(_table_style(highlight_row=1, band=fr_band))
    elems.append(fr)
    elems.append(Spacer(1, 0.4*cm))

    # Tavsiyalar
    report = combined_risk_report(
        findrisc=fr_score, findrisc_band=fr_band,
        homa_ir=screening["homa_ir"], bmi=screening["bmi"],
        waist=screening["waist"], sex=screening["sex"],
    )
    elems.append(Paragraph("Shaxsiy tavsiyalar", h2))
    for r in report["recommendations"]:
        elems.append(Paragraph(f"•  {r}", body))
    elems.append(Spacer(1, 0.6*cm))

    # Manba
    elems.append(Paragraph("Adabiyot", h2))
    elems.append(Paragraph(
        "FINDRISC: Lindström J, Tuomilehto J. <i>Diabetes Care</i>. 2003;26(3):725-731.",
        small,
    ))
    elems.append(Paragraph(
        "HOMA-IR: Matthews DR et al. <i>Diabetologia</i>. 1985;28(7):412-419.",
        small,
    ))
    elems.append(Spacer(1, 0.3*cm))

    # Disclaimer
    elems.append(Paragraph(
        "<b>MUHIM:</b> Bu hisobot skrining hisoblanadi, tibbiy tashxis emas. "
        "Har qanday shubhali natija endokrinolog yoki oilaviy vrach maslahatini talab qiladi. "
        "Dorilar faqat shifokor tavsiyasi bilan qabul qilinadi.",
        disclaim,
    ))

    # Footer
    elems.append(Spacer(1, 0.4*cm))
    elems.append(Paragraph(
        f"Hisobot yaratildi: {datetime.now().strftime('%Y-%m-%d %H:%M')} | "
        "HOMA-IR Bot v2",
        small,
    ))

    doc.build(elems)
    return buf.getvalue()


def _table_style(highlight_row: int = None, band: str = None) -> TableStyle:
    style = [
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f3f4f6")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#111827")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5e7eb")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    if highlight_row is not None and band:
        color_map = {
            "past": "#dcfce7",
            "ozgina yuqori": "#fef9c3",
            "o'rta": "#fed7aa",
            "yuqori": "#fecaca",
            "juda yuqori": "#fca5a5",
        }
        c = color_map.get(band, "#f3f4f6")
        style.append(("BACKGROUND", (0, highlight_row), (-1, highlight_row),
                      colors.HexColor(c)))
        style.append(("FONTNAME", (0, highlight_row), (-1, highlight_row),
                      "Helvetica-Bold"))
    return TableStyle(style)
