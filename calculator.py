"""
Klinik hisob-kitoblar. Adabiyot havolalari kod ichida.

Barcha shkalalar peer-reviewed manbalardan olingan.
Arbitrar ballardan qochish uchun bu modul alohida test qilinishi mumkin
(unit test qo'shish tavsiya etiladi).
"""

from typing import Optional


# ==================== BMI ====================

def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    """WHO klassik formulasi: BMI = kg / m²"""
    h_m = height_cm / 100.0
    return weight_kg / (h_m * h_m)


def classify_bmi(bmi: float) -> str:
    """WHO 2000 kategoriyalari (Osiyo populyatsiyasi uchun ozroq past chegara
    tavsiya etilgan: WHO Expert Consultation, Lancet 2004)."""
    if bmi < 18.5:
        return "kam vazn"
    if bmi < 23:
        return "normal"
    if bmi < 27.5:
        return "ortiqcha vazn"
    return "semizlik"


# ==================== Bel aylanasi ====================

def classify_waist(sex: str, waist_cm: float) -> str:
    """
    IDF Metabolik sindrom mezonlari (2006), Osiyo qiymatlari:
    Erkak >90 sm, Ayol >80 sm — abdominal semizlik.
    """
    thr = 90 if sex == "M" else 80
    high_thr = 102 if sex == "M" else 88  # NCEP ATP III (Yevropoid)
    if waist_cm < thr:
        return "normal"
    if waist_cm < high_thr:
        return "oshgan xavf"
    return "yuqori xavf"


# ==================== HOMA-IR ====================

def calculate_homa_ir(glucose_mmol: float, insulin_uiu: float) -> float:
    """
    Matthews DR, et al. Diabetologia 1985;28:412-419.
    HOMA-IR = (glukoza [mmol/L] × insulin [μU/mL]) / 22.5
    """
    return (glucose_mmol * insulin_uiu) / 22.5


def classify_homa_ir(homa_ir: float) -> str:
    """
    Klassik cutoff qiymatlari (Bonora et al. Diabetes Care 2000).
    Populyatsiyaga qarab moslashadi — o'zbek populyatsiyasi uchun
    o'zingizning tadqiqot ma'lumotlaringiz asosida qayta hisoblashingiz mumkin.
    """
    if homa_ir < 2.0:
        return "normal"
    if homa_ir < 2.5:
        return "chegara"
    if homa_ir < 3.8:
        return "insulin rezistentligi"
    return "yuqori insulin rezistentligi"


# ==================== FINDRISC ====================

# Lindström J, Tuomilehto J. Diabetes Care 2003;26(3):725-731.
# Xalqaro validatsiya qilingan, ADA va IDF tomonidan tavsiya etilgan.

def calculate_findrisc(
    *,
    age: int,
    bmi: float,
    waist: float,
    sex: str,
    activity_yes: bool,
    veg_daily: bool,
    bp_meds: bool,
    high_glucose_hist: bool,
    family_hx: str,  # 'none' | 'second' | 'first'
) -> tuple[int, str]:
    """
    Rasmiy FINDRISC ballari. Maksimal — 26.
    Qaytaradi: (jami ball, kategoriya).
    """
    score = 0

    # 1. Yosh
    if age < 45:
        score += 0
    elif age < 55:
        score += 2
    elif age < 65:
        score += 3
    else:
        score += 4

    # 2. BMI
    if bmi < 25:
        score += 0
    elif bmi < 30:
        score += 1
    else:
        score += 3

    # 3. Bel aylanasi (jinsga qarab)
    if sex == "M":
        if waist < 94:
            score += 0
        elif waist < 102:
            score += 3
        else:
            score += 4
    else:  # F
        if waist < 80:
            score += 0
        elif waist < 88:
            score += 3
        else:
            score += 4

    # 4. Jismoniy faollik (>=30 min/kun)
    score += 0 if activity_yes else 2

    # 5. Sabzavot/meva har kuni
    score += 0 if veg_daily else 1

    # 6. Bosim dorilari
    score += 2 if bp_meds else 0

    # 7. Ilgari yuqori qand aniqlanganmi
    score += 5 if high_glucose_hist else 0

    # 8. Oilaviy anamnez
    if family_hx == "first":
        score += 5
    elif family_hx == "second":
        score += 3
    else:
        score += 0

    return score, findrisc_band(score)


def findrisc_band(score: int) -> str:
    """FINDRISC kategoriyalari (Lindström & Tuomilehto, 2003)."""
    if score < 7:
        return "past"
    if score < 12:
        return "ozgina yuqori"
    if score < 15:
        return "o'rta"
    if score < 21:
        return "yuqori"
    return "juda yuqori"


def ten_year_risk(band: str) -> str:
    """
    10 yil ichida 2-tur diabet rivojlanishi ehtimoli
    (asl maqola, Diabetes Care 2003).
    """
    return {
        "past": "~1% (100 kishidan 1 tasi)",
        "ozgina yuqori": "~4% (25 kishidan 1 tasi)",
        "o'rta": "~17% (6 kishidan 1 tasi)",
        "yuqori": "~33% (3 kishidan 1 tasi)",
        "juda yuqori": "~50% (2 kishidan 1 tasi)",
    }[band]


# ==================== Umumiy hisobot ====================

def combined_risk_report(
    *,
    findrisc: int,
    findrisc_band: str,
    homa_ir: Optional[float],
    bmi: float,
    waist: float,
    sex: str,
) -> dict:
    """
    FINDRISC + HOMA-IR birlashtirilgan xulosasi va tavsiyalar.
    Qoida: qaysi omil yuqori bo'lsa — o'shanga urg'u.
    """
    combined = findrisc_band
    # HOMA-IR mavjud bo'lsa va yuqori bo'lsa, umumiy bandni ko'taramiz
    if homa_ir is not None and homa_ir >= 3.8 and findrisc_band in {"past", "ozgina yuqori"}:
        combined = "o'rta (HOMA-IR sabab)"
    elif homa_ir is not None and homa_ir >= 2.5 and findrisc_band == "past":
        combined = "ozgina yuqori (HOMA-IR sabab)"

    recs: list[str] = []

    # Umumiy tavsiyalar (FINDRISC bandiga qarab)
    if findrisc_band == "past":
        recs.append("Ajoyib. Sog'lom turmush tarzini davom ettiring.")
    elif findrisc_band == "ozgina yuqori":
        recs.append("Yiliga 1 marta qonda glukoza tekshiring.")
    elif findrisc_band == "o'rta":
        recs.append("HbA1c va och qorin qandini tekshiring (6 oyda).")
        recs.append("Vazn 5-7% ga kamaytirish diabet rivojlanishini 50%+ kamaytiradi.")
    elif findrisc_band == "yuqori":
        recs.append("Endokrinolog maslahati va OGTT (glukoza-tolerantlik testi).")
        recs.append("Struktur ravishda ovqatlanish va harakat rejasi.")
    else:  # juda yuqori
        recs.append("⚠️ Zudlik bilan endokrinologga murojaat qiling.")
        recs.append("HbA1c, OGTT, lipid profil - to'liq tekshiruv.")

    # HOMA-IR bo'yicha
    if homa_ir is not None:
        if homa_ir >= 3.8:
            recs.append(f"HOMA-IR yuqori ({homa_ir:.2f}) — metformin muhokamasi shifokor bilan.")
        elif homa_ir >= 2.5:
            recs.append(f"HOMA-IR chegarada ({homa_ir:.2f}) — insulin rezistentligi belgilari.")

    # BMI bo'yicha
    if bmi >= 27.5:
        recs.append("Vazn kamaytirish (5-10%) — eng ta'sirchan aralashuv.")
    elif bmi >= 23:
        recs.append("Vazn nazorati — Osiyo populyatsiyasi uchun 23+ allaqachon xavf.")

    # Bel bo'yicha
    waist_cls = classify_waist(sex, waist)
    if waist_cls != "normal":
        recs.append(f"Bel aylanasi ({waist_cls}) — abdominal semizlik alohida xavf.")

    return {
        "combined_band": combined,
        "ten_year_risk": ten_year_risk(findrisc_band),
        "recommendations": recs,
    }
