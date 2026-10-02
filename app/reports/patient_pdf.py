"""
Bemor uchun PDF hisobot: natija, izoh, tavsiyalar va (bo'lsa) dinamika grafigi.
Chop etishga va shifokorga ko'rsatishga tayyor format.
"""

from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table

from app import __version__
from app.analytics import compute_changes, verdict
from app.calculator import (
    classify_bmi,
    classify_glucose,
    classify_homa_ir,
    classify_quicki,
    classify_waist,
    classify_whtr,
    combined_risk_report,
    quick_report,
    ten_year_risk,
)
from app.reports import styles, table_style
from app.utils import TASHKENT, esc, fmt_dt

BAND_COLORS = {
    "past": "#dcfce7", "ozgina yuqori": "#fef9c3", "o'rta": "#fed7aa",
    "yuqori": "#fecaca", "juda yuqori": "#fca5a5",
}
HOMA_COLORS = ["#dcfce7", "#fef9c3", "#fed7aa", "#fca5a5"]


def _kv_table(rows: list[list[str]], widths: list[float], highlight: tuple[int, str] | None = None):
    t = Table(rows, colWidths=widths)
    st = table_style(header=False)
    if highlight:
        row, color = highlight
        st.add("BACKGROUND", (0, row), (-1, row), colors.HexColor(color))
    st.add("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#52514e"))
    t.setStyle(st)
    return t


def build_pdf_report(user: dict | None, screening: dict, history: list[dict] | None = None,
                     trend_png: bytes | None = None) -> bytes:
    """
    user, screening — DB qatorlari (dict). history — shu bemorning barcha
    natijalari (yangi → eski), dinamika bo'limi uchun ixtiyoriy.
    """
    s = styles()
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=1.8 * cm, rightMargin=1.8 * cm,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
        title=f"Metabolik skrining hisoboti #{screening['id']}",
        author="HOMA-IR Bot",
    )
    W = A4[0] - 3.6 * cm
    quick = screening.get("kind") == "quick"
    el = []

    el.append(Paragraph("Metabolik skrining hisoboti", s["h1"]))
    el.append(Paragraph(
        f"{'Tezkor HOMA-IR' if quick else 'HOMA-IR + FINDRISC'} • Hujjat №{screening['id']} • "
        f"{fmt_dt(screening['created_at'], with_time=True)}", s["small"]))
    el.append(Spacer(1, 0.3 * cm))

    # Bemor
    name = screening.get("patient_name") or (user or {}).get("display_name") or "—"
    rows = [["Bemor", name]]  # Table oddiy matn — HTML escape kerak emas
    if screening.get("age"):
        rows.append(["Yoshi", f"{screening['age']} yosh"])
    if screening.get("sex"):
        rows.append(["Jinsi", "Erkak" if screening["sex"] == "M" else "Ayol"])
    el.append(Paragraph("Bemor ma'lumotlari", s["h2"]))
    el.append(_kv_table(rows, [4.5 * cm, W - 4.5 * cm]))

    # Laboratoriya
    g, ins, homa = screening.get("fasting_glucose"), screening.get("fasting_insulin"), screening.get("homa_ir")
    if homa is not None:
        q = quick_report(glucose=g, insulin=ins)
        el.append(Paragraph("Laborator ko'rsatkichlar (och qoringa)", s["h2"]))
        lab = [
            ["Glukoza", f"{g:.2f} mmol/L ({g * 18.016:.0f} mg/dL)", classify_glucose(g)],
            ["Insulin", f"{ins:.1f} μU/mL", "ref. ~2–25 (laboratoriyaga qarab)"],
            ["HOMA-IR", f"{homa:.2f}", classify_homa_ir(homa)],
            ["HOMA-β", f"{q['homa_beta']:.0f}%" if q["homa_beta"] is not None else "—",
             "β-hujayra funksiyasi"],
            ["QUICKI", f"{q['quicki']:.3f}", classify_quicki(q["quicki"])],
        ]
        el.append(_kv_table(lab, [4.5 * cm, 5.5 * cm, W - 10 * cm],
                            highlight=(2, HOMA_COLORS[q["level"]])))

    if not quick and screening.get("bmi") is not None:
        el.append(Paragraph("Antropometriya", s["h2"]))
        whtr = screening.get("whtr") or (screening["waist"] / screening["height"])
        anth = [
            ["Vazn / bo'y", f"{screening['weight']:.1f} kg / {screening['height']:.0f} sm", ""],
            ["BMI", f"{screening['bmi']:.1f} kg/m²", classify_bmi(screening["bmi"])],
            ["Bel aylanasi", f"{screening['waist']:.0f} sm",
             classify_waist(screening["sex"], screening["waist"])],
            ["Bel/bo'y nisbati", f"{whtr:.2f}", classify_whtr(whtr)],
        ]
        el.append(_kv_table(anth, [4.5 * cm, 5.5 * cm, W - 10 * cm]))

        band = screening["findrisc_band"]
        el.append(Paragraph("FINDRISC: 10 yillik 2-tur diabet xavfi", s["h2"]))
        el.append(_kv_table([
            ["Ball", f"{screening['findrisc']} / 26"],
            ["Toifa", band.upper()],
            ["10 yillik xavf", ten_year_risk(band)],
            ["Umumiy xulosa", screening.get("combined_band") or band],
        ], [4.5 * cm, W - 4.5 * cm], highlight=(1, BAND_COLORS.get(band, "#f3f4f6"))))

    # Tavsiyalar
    if quick:
        recs = quick_report(glucose=g, insulin=ins)["recommendations"]
    else:
        recs = combined_risk_report(
            findrisc=screening["findrisc"], findrisc_band=screening["findrisc_band"],
            homa_ir=homa, bmi=screening["bmi"], waist=screening["waist"],
            sex=screening["sex"], glucose=g,
        )["recommendations"]
    el.append(Paragraph("Shaxsiy tavsiyalar", s["h2"]))
    for r in recs:
        el.append(Paragraph(f"•&nbsp;&nbsp;{esc(r)}", s["body"]))

    # Dinamika
    if history and len(history) >= 2:
        changes = compute_changes(history)
        if changes:
            el.append(Paragraph("Dinamika: oldingi natijaga nisbatan", s["h2"]))
            rows = [["Ko'rsatkich", "Oldingi", "Oxirgi", "O'zgarish", "Baho"]]
            for c in changes:
                _, word = verdict(c.pct_prev)
                pct = f"{c.pct_prev:+.0f}%" if c.pct_prev is not None else "—"
                rows.append([c.name, f"{c.prev:.{c.digits}f}", f"{c.last:.{c.digits}f}", pct, word])
            t = Table(rows, colWidths=[4 * cm, 3 * cm, 3 * cm, 3 * cm, W - 13 * cm])
            t.setStyle(table_style())
            el.append(t)
        if trend_png:
            el.append(Spacer(1, 0.2 * cm))
            img = Image(BytesIO(trend_png))
            ratio = img.imageHeight / img.imageWidth
            img.drawWidth, img.drawHeight = W, W * ratio
            el.append(img)

    el.append(Spacer(1, 0.4 * cm))
    el.append(Paragraph("Usullar va manbalar", s["h3"]))
    el.append(Paragraph(
        "HOMA-IR = glukoza (mmol/L) × insulin (μU/mL) / 22.5 — Matthews DR et al., "
        "<i>Diabetologia</i> 1985;28:412–419. HOMA-β = 20 × insulin / (glukoza − 3.5). "
        "QUICKI = 1 / (log insulin + log glukoza mg/dL) — Katz A et al., <i>JCEM</i> 2000. "
        "FINDRISC — Lindström J, Tuomilehto J, <i>Diabetes Care</i> 2003;26:725–731. "
        "BMI toifalari — WHO Expert Consultation, <i>Lancet</i> 2004 (Osiyo chegaralari).",
        s["small"]))
    el.append(Spacer(1, 0.25 * cm))
    el.append(Paragraph(
        "<b>MUHIM:</b> Bu hisobot skrining natijasi, tibbiy tashxis emas. Shubhali yoki yuqori "
        "natijada endokrinolog yoki oilaviy shifokor maslahati zarur. Dori vositalari faqat "
        "shifokor tavsiyasi bilan qabul qilinadi.", s["warn"]))
    el.append(Spacer(1, 0.2 * cm))
    el.append(Paragraph(
        f"Yaratildi: {datetime.now(TASHKENT).strftime('%d.%m.%Y %H:%M')} • HOMA-IR Bot v{__version__}",
        s["small"]))
    doc.build(el)
    return buf.getvalue()
