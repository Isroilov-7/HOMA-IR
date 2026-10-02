"""
Kogorta statistikasi (dissertatsiya / doklad uchun).

Metodologik qoidalar:
- Kesma (cross-sectional) tahlilda har bir sub'ekt bir marta hisoblanadi —
  uning BIRINCHI laborator o'lchovi (baseline). Takroriy o'lchovlar faqat
  dinamika bo'limida ishlatiladi (psevdo-replikatsiyaning oldini olish).
- Sub'ekt = (Telegram foydalanuvchi, bemor ismi). Bitta shifokor bir nechta
  bemorni tezkor rejimda kiritsa, ular alohida sub'ekt bo'ladi.
- Taqsimot normal emasligi kutilgani uchun guruhlar Mann–Whitney U,
  bog'liqlik Spearman ρ, juft o'zgarish Wilcoxon signed-rank bilan tekshiriladi.
  Ulushlar uchun 95% CI — Wilson usuli; guruhlar orasidagi farq — χ² (yoki Fisher).
"""

import math
from collections import Counter, defaultdict
from collections.abc import Iterable
from typing import Any

from app.calculator import HOMA_IR_CUTOFF, classify_bmi, classify_homa_ir
from app.utils import esc

# Jadvalda ko'rsatiladigan o'zgaruvchilar: (ustun, nomi, birlik, kasr)
VARIABLES: list[tuple[str, str, str, int]] = [
    ("age", "Yosh", "yil", 1),
    ("bmi", "BMI", "kg/m²", 1),
    ("waist", "Bel aylanasi", "sm", 1),
    ("whtr", "Bel/bo'y nisbati", "", 2),
    ("fasting_glucose", "Och qoringa glukoza", "mmol/L", 2),
    ("fasting_insulin", "Och qoringa insulin", "μU/mL", 1),
    ("homa_ir", "HOMA-IR", "", 2),
    ("homa_beta", "HOMA-β", "%", 1),
    ("quicki", "QUICKI", "", 3),
    ("findrisc", "FINDRISC", "ball", 1),
]

CORR_VARS = ["age", "bmi", "waist", "whtr", "fasting_glucose", "fasting_insulin", "findrisc"]

AGE_GROUPS = [(0, 30, "<30"), (30, 45, "30–44"), (45, 60, "45–59"), (60, 200, "≥60")]
HOMA_CLASSES = ["normal", "chegara", "insulin rezistentligi", "yuqori insulin rezistentligi"]
FINDRISC_BANDS = ["past", "ozgina yuqori", "o'rta", "yuqori", "juda yuqori"]
BMI_CLASSES = ["kam vazn", "normal", "ortiqcha vazn", "semizlik"]


# ---------------- yordamchilar ----------------

def subject_key(row: dict) -> str:
    name = " ".join((row.get("patient_name") or "").lower().split())
    return f"{row.get('user_id')}|{name}"


def baseline_rows(rows: Iterable[dict], require_labs: bool = False) -> list[dict]:
    """Har sub'ektning birinchi yozuvi (require_labs bo'lsa — birinchi HOMA-IR li)."""
    seen: dict[str, dict] = {}
    for r in sorted(rows, key=lambda x: (str(x.get("created_at")), x.get("id", 0))):
        if require_labs and r.get("homa_ir") is None:
            continue
        seen.setdefault(subject_key(r), r)
    return list(seen.values())


def _vals(rows: Iterable[dict], key: str) -> list[float]:
    return [float(r[key]) for r in rows if r.get(key) is not None]


def fmt_p(p: float | None) -> str:
    if p is None or (isinstance(p, float) and math.isnan(p)):
        return "—"
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def p_text(p: float | None) -> str:
    """'p<0.001' yoki 'p=0.023' — matn ichida ishlatish uchun."""
    f = fmt_p(p)
    return f"p{f}" if f.startswith("<") else f"p={f}"


def describe(values: list[float]) -> dict:
    import numpy as np

    n = len(values)
    if n == 0:
        return {"n": 0}
    a = np.asarray(values, dtype=float)
    q1, med, q3 = np.percentile(a, [25, 50, 75])
    return {
        "n": n,
        "mean": float(a.mean()),
        "sd": float(a.std(ddof=1)) if n > 1 else 0.0,
        "median": float(med),
        "q1": float(q1),
        "q3": float(q3),
        "min": float(a.min()),
        "max": float(a.max()),
    }


def fmt_desc(d: dict, digits: int) -> tuple[str, str]:
    """('M ± SD', 'Me [Q1; Q3]')"""
    if not d.get("n"):
        return "—", "—"
    f = f"{{:.{digits}f}}"
    return (f"{f.format(d['mean'])} ± {f.format(d['sd'])}",
            f"{f.format(d['median'])} [{f.format(d['q1'])}; {f.format(d['q3'])}]")


def wilson_ci(k: int, n: int, z: float = 1.959964) -> tuple[float, float, float]:
    """Ulush va 95% Wilson ishonch oralig'i (foizda)."""
    if n == 0:
        return 0.0, 0.0, 0.0
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    # Suzuvchi nuqta xatosi (k=0 yoki k=n) oraliqni p dan "o'tkazib" yubormasin
    lo = min(p, max(0.0, centre - half))
    hi = max(p, min(1.0, centre + half))
    return p * 100, lo * 100, hi * 100


def mann_whitney(a: list[float], b: list[float]) -> float | None:
    if len(a) < 3 or len(b) < 3:
        return None
    from scipy.stats import mannwhitneyu

    try:
        return float(mannwhitneyu(a, b, alternative="two-sided").pvalue)
    except ValueError:
        return None


def spearman(rows: list[dict], x: str, y: str) -> dict:
    pairs = [(float(r[x]), float(r[y])) for r in rows
             if r.get(x) is not None and r.get(y) is not None]
    n = len(pairs)
    if n < 5:
        return {"n": n, "rho": None, "p": None}
    from scipy.stats import spearmanr

    xs, ys = zip(*pairs)
    if len(set(xs)) < 2 or len(set(ys)) < 2:
        return {"n": n, "rho": None, "p": None}
    res = spearmanr(xs, ys)
    return {"n": n, "rho": float(res.statistic), "p": float(res.pvalue)}


def group_test(table: list[list[int]]) -> float | None:
    """Ulushlar farqi: 2×2 da kichik kutilgan qiymatlarda Fisher, aks holda χ²."""
    table = [row for row in table if sum(row) > 0]
    if len(table) < 2 or any(sum(col) == 0 for col in zip(*table)):
        return None
    from scipy.stats import chi2_contingency, fisher_exact

    try:
        chi2, p, _, expected = chi2_contingency(table)
        if len(table) == 2 and (expected < 5).any():
            return float(fisher_exact(table).pvalue)
        return float(p)
    except ValueError:
        return None


def age_group(age: float | None) -> str | None:
    if age is None:
        return None
    for lo, hi, label in AGE_GROUPS:
        if lo <= age < hi:
            return label
    return None


def is_ir(row: dict) -> bool:
    return row["homa_ir"] >= HOMA_IR_CUTOFF


# ---------------- asosiy hisobot ----------------

def cohort_report(rows: list[dict]) -> dict[str, Any]:
    subjects = baseline_rows(rows)
    labs = baseline_rows(rows, require_labs=True)
    men = [r for r in labs if r.get("sex") == "M"]
    women = [r for r in labs if r.get("sex") == "F"]
    all_subj_men = [r for r in subjects if r.get("sex") == "M"]
    all_subj_women = [r for r in subjects if r.get("sex") == "F"]

    rep: dict[str, Any] = {
        "n_records": len(rows),
        "n_subjects": len(subjects),
        "n_labs": len(labs),
        "n_full": sum(1 for r in subjects if (r.get("kind") or "full") == "full"),
        "n_quick": sum(1 for r in subjects if r.get("kind") == "quick"),
        "sex": {"M": len(all_subj_men), "F": len(all_subj_women),
                "unknown": len(subjects) - len(all_subj_men) - len(all_subj_women)},
    }

    # 1-jadval: umumiy, erkak, ayol (+ p). Antropometriya va FINDRISC — barcha
    # sub'ektlardan, laborator ko'rsatkichlar — laboratoriyasi borlardan.
    table1 = []
    lab_keys = {"fasting_glucose", "fasting_insulin", "homa_ir", "homa_beta", "quicki"}
    for key, name, unit, digits in VARIABLES:
        base = labs if key in lab_keys else subjects
        m = [r for r in base if r.get("sex") == "M"]
        f = [r for r in base if r.get("sex") == "F"]
        dv_all, dv_m, dv_f = describe(_vals(base, key)), describe(_vals(m, key)), describe(_vals(f, key))
        if not dv_all.get("n"):
            continue
        table1.append({
            "key": key, "name": name, "unit": unit, "digits": digits,
            "all": dv_all, "M": dv_m, "F": dv_f,
            "p": mann_whitney(_vals(m, key), _vals(f, key)),
        })
    rep["table1"] = table1

    # HOMA-IR toifalari
    cls_counts = Counter(classify_homa_ir(r["homa_ir"]) for r in labs)
    rep["homa_classes"] = [(c, cls_counts.get(c, 0)) for c in HOMA_CLASSES]

    # IR prevalentligi (HOMA-IR ≥ 2.5) — umumiy va kesimlar bo'yicha
    def prev_block(groups: dict[str, list[dict]]) -> dict:
        items = []
        table = []
        for label, grp in groups.items():
            k = sum(1 for r in grp if is_ir(r))
            n = len(grp)
            pct, lo, hi = wilson_ci(k, n)
            items.append({"label": label, "k": k, "n": n, "pct": pct, "lo": lo, "hi": hi})
            table.append([k, n - k])
        return {"items": items, "p": group_test(table) if len(groups) > 1 else None}

    k_all = sum(1 for r in labs if is_ir(r))
    pct, lo, hi = wilson_ci(k_all, len(labs))
    rep["ir_overall"] = {"k": k_all, "n": len(labs), "pct": pct, "lo": lo, "hi": hi}
    rep["ir_by_sex"] = prev_block({"Erkak": men, "Ayol": women})

    by_age: dict[str, list[dict]] = defaultdict(list)
    for r in labs:
        g = age_group(r.get("age"))
        if g:
            by_age[g].append(r)
    rep["ir_by_age"] = prev_block({lbl: by_age[lbl] for _, _, lbl in AGE_GROUPS if by_age.get(lbl)})

    by_bmi: dict[str, list[dict]] = defaultdict(list)
    for r in labs:
        if r.get("bmi") is not None:
            by_bmi[classify_bmi(r["bmi"])].append(r)
    rep["ir_by_bmi"] = prev_block({c: by_bmi[c] for c in BMI_CLASSES if by_bmi.get(c)})

    # FINDRISC toifalari (FINDRISC'i bor sub'ektlar)
    fr = [r for r in subjects if r.get("findrisc_band")]
    fr_counts = Counter(r["findrisc_band"] for r in fr)
    rep["findrisc_bands"] = [(b, fr_counts.get(b, 0)) for b in FINDRISC_BANDS]
    rep["n_findrisc"] = len(fr)

    # Spearman: HOMA-IR bilan bog'liqlik
    names = {k: n for k, n, _, _ in VARIABLES}
    rep["correlations"] = [
        {"key": v, "name": names[v], **spearman(labs, "homa_ir", v)} for v in CORR_VARS
    ]

    # HOMA-IR kvartillari va populyatsion cutoff
    homa_vals = _vals(labs, "homa_ir")
    rep["homa_desc"] = describe(homa_vals)
    rep["reference"] = reference_cutoff(labs)

    # Dinamika (≥2 HOMA-IR o'lchovi bor sub'ektlar)
    rep["longitudinal"] = longitudinal(rows)
    return rep


def reference_cutoff(labs: list[dict]) -> dict:
    """
    Metabolik sog'lom guruh: glukoza <5.6, BMI <25, ilgari yuqori qand yo'q,
    bosim dorisi yo'q (ma'lum bo'lsa). Cutoff = shu guruhdagi HOMA-IR ning
    75-persentili (Ascaso JF, Diabetes Care 2003 yondashuvi). n < 30 da
    natija taxminiy deb belgilanadi.
    """
    import numpy as np

    healthy = [
        r for r in labs
        if r.get("fasting_glucose") is not None and r["fasting_glucose"] < 5.6
        and r.get("bmi") is not None and r["bmi"] < 25
        and not r.get("high_glucose_hist") and not r.get("bp_meds")
    ]
    vals = _vals(healthy, "homa_ir")
    if len(vals) < 5:
        return {"n": len(vals), "p75": None, "p90": None, "reliable": False}
    p75, p90 = np.percentile(vals, [75, 90])
    return {"n": len(vals), "p75": float(p75), "p90": float(p90), "reliable": len(vals) >= 30}


def longitudinal(rows: list[dict]) -> dict:
    by_subj: dict[str, list[dict]] = defaultdict(list)
    for r in sorted(rows, key=lambda x: (str(x.get("created_at")), x.get("id", 0))):
        if r.get("homa_ir") is not None:
            by_subj[subject_key(r)].append(r)
    pairs = [(v[0]["homa_ir"], v[-1]["homa_ir"]) for v in by_subj.values() if len(v) >= 2]
    n = len(pairs)
    out: dict[str, Any] = {"n": n}
    if n == 0:
        return out
    first = [a for a, _ in pairs]
    last = [b for _, b in pairs]
    deltas = [b - a for a, b in pairs]
    out.update({
        "first": describe(first),
        "last": describe(last),
        "delta": describe(deltas),
        "improved": sum(1 for a, b in pairs if a > 0 and (b - a) / a <= -0.10),
        "worsened": sum(1 for a, b in pairs if a > 0 and (b - a) / a >= 0.10),
        "ir_first": sum(1 for a in first if a >= HOMA_IR_CUTOFF),
        "ir_last": sum(1 for b in last if b >= HOMA_IR_CUTOFF),
        "p": None,
    })
    if n >= 5 and any(d != 0 for d in deltas):
        from scipy.stats import wilcoxon

        try:
            out["p"] = float(wilcoxon(first, last).pvalue)
        except ValueError:
            pass
    return out


def format_summary(rep: dict) -> str:
    """Telegram uchun qisqa HTML xulosa (to'liq versiya — PDF/Excel'da)."""
    lines = ["🔬 <b>Tadqiqot xulosasi</b>", ""]
    lines.append(f"Sub'ektlar: <b>{rep['n_subjects']}</b> (yozuvlar: {rep['n_records']})")
    lines.append(f"Laboratoriyasi bor: <b>{rep['n_labs']}</b> • "
                 f"Erkak/ayol: {rep['sex']['M']}/{rep['sex']['F']}")
    if rep["n_labs"]:
        o = rep["ir_overall"]
        lines += ["", f"<b>Insulin rezistentligi</b> (HOMA-IR ≥ {HOMA_IR_CUTOFF}):",
                  f"{o['k']}/{o['n']} = <b>{o['pct']:.1f}%</b> (95% CI {o['lo']:.1f}–{o['hi']:.1f})"]
        for it in rep["ir_by_sex"]["items"]:
            if it["n"]:
                lines.append(f"• {it['label']}: {it['pct']:.1f}% ({it['k']}/{it['n']})")
        if rep["ir_by_sex"]["p"] is not None:
            lines.append(f"  {esc(p_text(rep['ir_by_sex']['p']))}")
        d = rep["homa_desc"]
        lines += ["", f"<b>HOMA-IR:</b> Me {d['median']:.2f} [{d['q1']:.2f}; {d['q3']:.2f}], "
                      f"M {d['mean']:.2f} ± {d['sd']:.2f}"]
        ref = rep["reference"]
        if ref.get("p75") is not None:
            note = "" if ref["reliable"] else " ⚠️ n&lt;30, taxminiy"
            lines.append(f"Populyatsion cutoff (sog'lom guruh P75): <b>{ref['p75']:.2f}</b> "
                         f"(n={ref['n']}){note}")
        sig = [c for c in rep["correlations"] if c["rho"] is not None]
        if sig:
            lines += ["", "<b>Spearman ρ (HOMA-IR bilan):</b>"]
            for c in sig:
                star = " *" if c["p"] is not None and c["p"] < 0.05 else ""
                lines.append(f"• {c['name']}: ρ={c['rho']:.2f}, {esc(p_text(c['p']))}{star}")
    lo = rep["longitudinal"]
    if lo.get("n"):
        lines += ["", f"<b>Dinamika</b> ({lo['n']} sub'ekt, ≥2 o'lchov):",
                  f"Yaxshilangan: {lo['improved']} • Yomonlashgan: {lo['worsened']}",
                  f"ΔHOMA-IR Me {lo['delta']['median']:+.2f}, Wilcoxon {esc(p_text(lo['p']))}"]
    lines += ["", "<i>To'liq jadvallar, grafiklar va metodika — PDF hisobotda.</i>"]
    return "\n".join(lines)
