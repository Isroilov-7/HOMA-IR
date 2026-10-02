"""
Dissertatsiya / doklad uchun kogorta hisoboti (PDF).

Tuzilishi ilmiy maqola formatida: asosiy natijalar → material va metodlar →
jadvallar (1–5) → rasmlar → cheklovlar → adabiyotlar. Barcha raqamlar
app.stats.cohort_report() dan olinadi; shaxsiy ma'lumot (ism, Telegram ID) yo'q.
"""

from datetime import datetime
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
)

from app import __version__, charts
from app.calculator import HOMA_IR_CUTOFF
from app.reports import FONT, styles, table_style
from app.stats import _vals, baseline_rows, fmt_desc, fmt_p, p_text
from app.utils import TASHKENT, esc

REFERENCES = [
    "Matthews DR, Hosker JP, Rudenski AS, et al. Homeostasis model assessment: insulin "
    "resistance and β-cell function from fasting plasma glucose and insulin concentrations "
    "in man. Diabetologia. 1985;28(7):412–419.",
    "Lindström J, Tuomilehto J. The Diabetes Risk Score: a practical tool to predict type 2 "
    "diabetes risk. Diabetes Care. 2003;26(3):725–731.",
    "Katz A, Nambi SS, Mather K, et al. Quantitative insulin sensitivity check index. "
    "J Clin Endocrinol Metab. 2000;85(7):2402–2410.",
    "Bonora E, Targher G, Alberiche M, et al. Homeostasis model assessment closely mirrors "
    "the glucose clamp technique. Diabetes Care. 2000;23(1):57–63.",
    "Ascaso JF, Pardo S, Real JT, et al. Diagnosing insulin resistance by simple quantitative "
    "methods in subjects with normal glucose metabolism. Diabetes Care. 2003;26(12):3320–3325.",
    "WHO Expert Consultation. Appropriate body-mass index for Asian populations. "
    "Lancet. 2004;363(9403):157–163.",
    "Alberti KG, Zimmet P, Shaw J. Metabolic syndrome — a new world-wide definition (IDF). "
    "Diabet Med. 2006;23(5):469–480.",
    "Ashwell M, Gunn P, Gibson S. Waist-to-height ratio is a better screening tool than "
    "waist circumference and BMI. Obes Rev. 2012;13(3):275–286.",
    "American Diabetes Association. Classification and diagnosis of diabetes: Standards of "
    "Care in Diabetes—2024. Diabetes Care. 2024;47(Suppl 1):S20–S42.",
    "Wallace TM, Levy JC, Matthews DR. Use and abuse of HOMA modeling. Diabetes Care. "
    "2004;27(6):1487–1495.",
]


def _img(png: bytes | None, width: float):
    if not png:
        return None
    img = Image(BytesIO(png))
    img.drawWidth, img.drawHeight = width, width * img.imageHeight / img.imageWidth
    return img


def build_research_pdf(rows: list[dict], rep: dict) -> bytes:
    s = styles()
    P = lambda text, st="cell": Paragraph(text, s[st])  # noqa: E731
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=1.7 * cm, rightMargin=1.7 * cm,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
        title="HOMA-IR va FINDRISC: kogorta tahlili", author="HOMA-IR Bot",
    )
    W = A4[0] - 3.4 * cm
    now = datetime.now(TASHKENT)
    labs = baseline_rows(rows, require_labs=True)
    el = []

    # ---------- sarlavha ----------
    el.append(Paragraph("Insulin rezistentligi va 2-tur diabet xavfi: kogorta tahlili", s["h1"]))
    el.append(Paragraph(
        f"HOMA-IR, QUICKI, HOMA-β va FINDRISC ko'rsatkichlari • Ma'lumotlar holati: "
        f"{now.strftime('%d.%m.%Y %H:%M')} (Toshkent) • HOMA-IR Bot v{__version__}", s["small"]))
    el.append(Spacer(1, 0.3 * cm))

    # ---------- asosiy natijalar ----------
    el.append(Paragraph("Asosiy natijalar", s["h2"]))
    bullets = [
        f"Tahlilga <b>{rep['n_subjects']}</b> sub'ekt kiritildi ({rep['n_records']} ta yozuv); "
        f"laborator ma'lumoti (glukoza + insulin) bor: <b>{rep['n_labs']}</b>.",
    ]
    if rep["n_labs"]:
        o = rep["ir_overall"]
        d = rep["homa_desc"]
        bullets.append(
            f"Insulin rezistentligi (HOMA-IR ≥ {HOMA_IR_CUTOFF}) prevalentligi: <b>{o['pct']:.1f}%</b> "
            f"(95% CI {o['lo']:.1f}–{o['hi']:.1f}; {o['k']}/{o['n']}).")
        bullets.append(
            f"HOMA-IR: Me {d['median']:.2f} [Q1 {d['q1']:.2f}; Q3 {d['q3']:.2f}], "
            f"M {d['mean']:.2f} ± {d['sd']:.2f}.")
        ref = rep["reference"]
        if ref.get("p75") is not None:
            bullets.append(
                f"Metabolik sog'lom guruhda (n={ref['n']}) HOMA-IR ning 75-persentili "
                f"<b>{ref['p75']:.2f}</b> — ushbu populyatsiya uchun taklif etilayotgan chegaraviy qiymat"
                + ("." if ref["reliable"] else " (n &lt; 30, taxminiy; namuna ko'paygach qayta hisoblanadi)."))
        strongest = sorted([c for c in rep["correlations"] if c["rho"] is not None],
                           key=lambda c: -abs(c["rho"]))[:2]
        for c in strongest:
            bullets.append(f"HOMA-IR va {c['name'].lower()} orasida Spearman ρ = {c['rho']:.2f} "
                           f"({esc(p_text(c['p']))}, n = {c['n']}).")
    lo = rep["longitudinal"]
    if lo.get("n"):
        bullets.append(
            f"Takroriy o'lchovli {lo['n']} sub'ektda HOMA-IR ning medianaviy o'zgarishi "
            f"{lo['delta']['median']:+.2f} (Wilcoxon {esc(p_text(lo['p']))}); "
            f"≥10% yaxshilanish: {lo['improved']}, yomonlashish: {lo['worsened']}.")
    for b in bullets:
        el.append(Paragraph(f"•&nbsp;&nbsp;{b}", s["body"]))

    # ---------- metodlar ----------
    el.append(Paragraph("Material va metodlar", s["h2"]))
    el.append(Paragraph(
        "<b>Dizayn va ishtirokchilar.</b> Kesma (cross-sectional) skrining tadqiqoti, takroriy "
        "o'lchovlar bo'yicha prospektiv kuzatuv elementi bilan. Ma'lumotlar Telegram-bot orqali "
        "xabardor qilingan rozilik (informed consent) olingandan keyin yig'ildi. Har bir sub'ekt "
        "kesma tahlilda bir marta — birinchi laborator o'lchovi bilan hisobga olindi "
        "(psevdo-replikatsiyaning oldini olish uchun).", s["body"]))
    el.append(Paragraph(
        "<b>O'lchovlar.</b> Och qoringa plazma glukozasi (mmol/L) va immunoreaktiv insulin "
        "(μU/mL); vazn, bo'y, bel aylanasi (kindik sathida). Hisoblangan indekslar: "
        "HOMA-IR = glukoza × insulin / 22.5; HOMA-β = 20 × insulin / (glukoza − 3.5); "
        "QUICKI = 1 / (log₁₀ insulin + log₁₀ glukoza [mg/dL]); BMI = kg/m²; bel/bo'y nisbati. "
        "FINDRISC — 8 savolli validatsiyalangan shkala (0–26 ball).", s["body"]))
    el.append(Paragraph(
        f"<b>Toifalar.</b> Insulin rezistentligi: HOMA-IR ≥ {HOMA_IR_CUTOFF} (asosiy), "
        "yuqori IR: ≥ 3.8; QUICKI &lt; 0.339. BMI — Osiyo populyatsiyasi uchun WHO (2004) "
        "chegaralari. Glukoza — ADA (2024): &lt;5.6 normal, 5.6–6.9 IFG, ≥7.0 diabet diapazoni. "
        "Populyatsion chegaraviy qiymat — metabolik sog'lom guruhda (glukoza &lt; 5.6, BMI &lt; 25, "
        "giperglikemiya anamnezi va antigipertenziv terapiya yo'q) HOMA-IR ning 75-persentili.",
        s["body"]))
    el.append(Paragraph(
        "<b>Statistik tahlil.</b> Miqdoriy o'zgaruvchilar M ± SD va Me [Q1; Q3] ko'rinishida. "
        "Guruhlar (erkak/ayol) Mann–Whitney U testi bilan, ulushlar χ² (kichik kutilgan "
        "chastotalarda Fisher aniq testi) bilan solishtirildi; ulushlar uchun 95% ishonch "
        "oralig'i — Wilson usuli. Bog'liqlik — Spearman ρ. Takroriy o'lchovlar — Wilcoxon "
        "signed-rank testi. Statistik ahamiyatlilik: ikki tomonlama p &lt; 0.05. "
        "Hisob-kitoblar Python (NumPy, SciPy) yordamida avtomatik bajarildi.", s["body"]))

    # ---------- 1-jadval ----------
    if rep["table1"]:
        el.append(Paragraph("1-jadval. Tadqiqot ishtirokchilarining tavsifi", s["h2"]))
        head = [P("Ko'rsatkich", "cellb"), P("Umumiy", "cellb"), P("Erkaklar", "cellb"),
                P("Ayollar", "cellb"), P("p", "cellb")]
        data = [head]
        for t in rep["table1"]:
            cells = []
            for grp in ("all", "M", "F"):
                d = t[grp]
                if d.get("n"):
                    msd, med = fmt_desc(d, t["digits"])
                    cells.append(P(f"{msd}<br/>{med}<br/><font size=7 color='#6b7280'>n={d['n']}</font>"))
                else:
                    cells.append(P("—"))
            unit = f", {t['unit']}" if t["unit"] else ""
            data.append([P(f"{t['name']}{unit}")] + cells + [P(esc(fmt_p(t["p"])))])
        tbl = Table(data, colWidths=[3.6 * cm, 3.9 * cm, 3.9 * cm, 3.9 * cm, W - 15.3 * cm],
                    repeatRows=1)
        tbl.setStyle(table_style())
        el.append(tbl)
        el.append(Paragraph("Qiymatlar: M ± SD (1-qator), Me [Q1; Q3] (2-qator). "
                            "p — Mann–Whitney U (erkak va ayol).", s["small"]))

    # ---------- 2-jadval: HOMA toifalari ----------
    if rep["n_labs"]:
        el.append(Paragraph("2-jadval. HOMA-IR toifalari bo'yicha taqsimot", s["h2"]))
        n = rep["n_labs"]
        data = [["Toifa", "Oraliq", "n", "%"]]
        ranges = ["< 2.0", "2.0–2.49", "2.5–3.79", "≥ 3.8"]
        for (cls, k), rng in zip(rep["homa_classes"], ranges):
            data.append([cls, rng, str(k), f"{k / n * 100:.1f}"])
        tbl = Table(data, colWidths=[6 * cm, 3.5 * cm, 2.5 * cm, 2.5 * cm])
        tbl.setStyle(table_style())
        el.append(tbl)

        # ---------- 3-jadval: prevalentlik ----------
        el.append(Paragraph(
            f"3-jadval. Insulin rezistentligi prevalentligi (HOMA-IR ≥ {HOMA_IR_CUTOFF})", s["h2"]))
        data = [["Guruh", "IR / n", "%", "95% CI", "p"]]
        o = rep["ir_overall"]
        data.append(["Umumiy", f"{o['k']}/{o['n']}", f"{o['pct']:.1f}",
                     f"{o['lo']:.1f}–{o['hi']:.1f}", ""])
        for title, block in (("Jins", rep["ir_by_sex"]), ("Yosh guruhi", rep["ir_by_age"]),
                             ("BMI toifasi", rep["ir_by_bmi"])):
            items = [i for i in block["items"] if i["n"]]
            for j, it in enumerate(items):
                data.append([f"{title}: {it['label']}", f"{it['k']}/{it['n']}", f"{it['pct']:.1f}",
                             f"{it['lo']:.1f}–{it['hi']:.1f}", fmt_p(block["p"]) if j == 0 else ""])
        tbl = Table(data, colWidths=[6 * cm, 2.6 * cm, 2 * cm, 3.2 * cm, W - 13.8 * cm], repeatRows=1)
        tbl.setStyle(table_style())
        el.append(tbl)
        el.append(Paragraph("95% CI — Wilson; p — χ² (2×2 da kichik chastotalarda Fisher).",
                            s["small"]))

        # ---------- 4-jadval: korrelyatsiya ----------
        el.append(Paragraph("4-jadval. HOMA-IR ning klinik ko'rsatkichlar bilan bog'liqligi", s["h2"]))
        data = [["Ko'rsatkich", "n", "Spearman ρ", "p", "Kuch"]]
        for c in rep["correlations"]:
            if c["rho"] is None:
                data.append([c["name"], str(c["n"]), "—", "—", "ma'lumot yetarli emas"])
                continue
            a = abs(c["rho"])
            strength = "kuchli" if a >= 0.7 else "o'rtacha" if a >= 0.4 else "kuchsiz" if a >= 0.2 else "juda kuchsiz"
            data.append([c["name"], str(c["n"]), f"{c['rho']:.2f}", fmt_p(c["p"]), strength])
        tbl = Table(data, colWidths=[5 * cm, 2 * cm, 3 * cm, 2.5 * cm, W - 12.5 * cm])
        tbl.setStyle(table_style())
        el.append(tbl)

        # ---------- populyatsion cutoff ----------
        el.append(Paragraph("5-jadval. Populyatsiyaga xos HOMA-IR chegaraviy qiymati", s["h2"]))
        ref = rep["reference"]
        d = rep["homa_desc"]
        data = [["Ko'rsatkich", "Qiymat"],
                ["Butun namuna: Q1 / Me / Q3", f"{d['q1']:.2f} / {d['median']:.2f} / {d['q3']:.2f}"],
                ["Metabolik sog'lom guruh, n", str(ref["n"])],
                ["Sog'lom guruh P75 (taklif etilgan cutoff)",
                 f"{ref['p75']:.2f}" if ref.get("p75") is not None else "n < 5 — hisoblanmadi"],
                ["Sog'lom guruh P90", f"{ref['p90']:.2f}" if ref.get("p90") is not None else "—"],
                ["Ishonchlilik", "yetarli (n ≥ 30)" if ref.get("reliable") else "taxminiy (n < 30)"]]
        tbl = Table(data, colWidths=[8 * cm, W - 8 * cm])
        tbl.setStyle(table_style())
        el.append(tbl)

    # ---------- FINDRISC ----------
    if rep["n_findrisc"]:
        el.append(Paragraph("6-jadval. FINDRISC xavf toifalari", s["h2"]))
        ten = {"past": "~1%", "ozgina yuqori": "~4%", "o'rta": "~17%", "yuqori": "~33%",
               "juda yuqori": "~50%"}
        rng = {"past": "0–6", "ozgina yuqori": "7–11", "o'rta": "12–14", "yuqori": "15–20",
               "juda yuqori": "21–26"}
        data = [["Toifa", "Ball", "10 yillik xavf", "n", "%"]]
        for band, k in rep["findrisc_bands"]:
            data.append([band, rng[band], ten[band], str(k), f"{k / rep['n_findrisc'] * 100:.1f}"])
        tbl = Table(data, colWidths=[4.5 * cm, 2.5 * cm, 3.5 * cm, 2 * cm, 2 * cm])
        tbl.setStyle(table_style())
        el.append(tbl)

    # ---------- dinamika ----------
    if lo.get("n"):
        el.append(Paragraph("7-jadval. Takroriy o'lchovlar: birinchi va oxirgi HOMA-IR", s["h2"]))
        f1, f2 = fmt_desc(lo["first"], 2), fmt_desc(lo["last"], 2)
        dd = fmt_desc(lo["delta"], 2)
        data = [["", "Birinchi", "Oxirgi", "Δ (oxirgi − birinchi)"],
                ["M ± SD", f1[0], f2[0], dd[0]],
                ["Me [Q1; Q3]", f1[1], f2[1], dd[1]],
                ["IR (≥ 2.5), n", str(lo["ir_first"]), str(lo["ir_last"]), ""],
                ["Wilcoxon p", "", "", fmt_p(lo["p"])]]
        tbl = Table(data, colWidths=[3.5 * cm, 4 * cm, 4 * cm, W - 11.5 * cm])
        tbl.setStyle(table_style())
        el.append(tbl)
        el.append(Paragraph(f"n = {lo['n']} sub'ekt (≥ 2 laborator o'lchov). "
                            f"≥10% kamayish: {lo['improved']}, ≥10% oshish: {lo['worsened']}.",
                            s["small"]))

    # ---------- rasmlar ----------
    figs = []
    if rep["n_labs"]:
        figs.append(("1-rasm. HOMA-IR taqsimoti; qizil chiziq — cutoff 2.5, nuqtali — sog'lom guruh P75.",
                     charts.homa_histogram_png(_vals(labs, "homa_ir"), rep["reference"].get("p75"))))
        figs.append(("2-rasm. BMI toifalari bo'yicha IR ulushi (95% CI).",
                     charts.prevalence_bars_png(rep["ir_by_bmi"]["items"], "IR ulushi: BMI toifalari")))
        figs.append(("3-rasm. Yosh guruhlari bo'yicha IR ulushi (95% CI).",
                     charts.prevalence_bars_png(rep["ir_by_age"]["items"], "IR ulushi: yosh guruhlari")))
        corr = {c["key"]: c for c in rep["correlations"]}
        for key, label in (("bmi", "BMI"), ("waist", "bel aylanasi")):
            c = corr.get(key, {})
            figs.append((f"{len(figs) + 1}-rasm. HOMA-IR va {label} (har nuqta — bitta sub'ekt).",
                         charts.scatter_png(labs, key, label, c.get("rho"), fmt_p(c.get("p")))))
    if rep["n_findrisc"]:
        figs.append((f"{len(figs) + 1}-rasm. FINDRISC toifalari bo'yicha taqsimot.",
                     charts.findrisc_bars_png(rep["findrisc_bands"])))
    figs = [(cap, png) for cap, png in figs if png]
    if figs:
        el.append(PageBreak())
        el.append(Paragraph("Rasmlar", s["h2"]))
        for i, (cap, png) in enumerate(figs, start=1):
            cap = f"{i}-rasm." + cap.split("rasm.", 1)[1]
            el.append(KeepTogether([_img(png, W * 0.92), Paragraph(cap, s["small"]), Spacer(1, 0.3 * cm)]))

    # ---------- cheklovlar va adabiyot ----------
    el.append(Paragraph("Cheklovlar", s["h2"]))
    for t in (
        "Ma'lumotlar o'z-o'zini hisobotga asoslangan (antropometriya, anamnez) va turli "
        "laboratoriyalarda o'lchangan; insulin tahlil usullari orasida farq bo'lishi mumkin.",
        "Namuna tasodifiy emas (bot foydalanuvchilari) — natijalarni umumiy populyatsiyaga "
        "ko'chirishda ehtiyot bo'lish kerak.",
        "HOMA-IR ning kunlik biologik o'zgaruvchanligi ~10–25%; yakka o'lchov asosida "
        "individual xulosa chiqarilmaydi.",
    ):
        el.append(Paragraph(f"•&nbsp;&nbsp;{t}", s["body"]))
    el.append(Paragraph("Adabiyotlar", s["h2"]))
    for i, r in enumerate(REFERENCES, start=1):
        el.append(Paragraph(f"{i}. {r}", s["small"]))

    def _footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont(FONT, 7.5)
        canvas.setFillColorRGB(0.42, 0.42, 0.42)
        canvas.drawString(1.7 * cm, 0.9 * cm, "HOMA-IR Bot — kogorta hisoboti (anonim ma'lumotlar)")
        canvas.drawRightString(A4[0] - 1.7 * cm, 0.9 * cm, f"{doc_.page}-bet")
        canvas.restoreState()

    doc.build(el, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
