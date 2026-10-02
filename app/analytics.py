"""
Bemorning o'z natijalari dinamikasi: oldingi va birinchi o'lchov bilan solishtirish.

Barcha ko'rsatkichlarda "kamroq = yaxshiroq" (HOMA-IR, glukoza, insulin, BMI, bel,
FINDRISC). HOMA-IR ning biologik o'zgaruvchanligi ~10–25% (Wallace TM, Diabetes Care
2004), shuning uchun ±10% ichidagi farq "barqaror" deb talqin qilinadi.
"""

from dataclasses import dataclass

from app.calculator import classify_homa_ir
from app.utils import esc, fmt_dt

STABLE_PCT = 10.0

METRICS: list[tuple[str, str, str, int]] = [
    # (ustun, nomi, birlik, kasr)
    ("homa_ir", "HOMA-IR", "", 2),
    ("fasting_glucose", "Glukoza", " mmol/L", 1),
    ("fasting_insulin", "Insulin", " μU/mL", 1),
    ("bmi", "BMI", "", 1),
    ("waist", "Bel", " sm", 0),
    ("findrisc", "FINDRISC", "", 0),
]


@dataclass
class Change:
    key: str
    name: str
    unit: str
    digits: int
    first: float
    prev: float
    last: float
    n: int

    @property
    def delta_prev(self) -> float:
        return self.last - self.prev

    @property
    def pct_prev(self) -> float | None:
        return None if self.prev == 0 else (self.last - self.prev) / self.prev * 100

    @property
    def pct_first(self) -> float | None:
        return None if self.first == 0 else (self.last - self.first) / self.first * 100


def verdict(pct: float | None) -> tuple[str, str]:
    """(belgi, so'z). Kamayish — yaxshilanish."""
    if pct is None or abs(pct) < STABLE_PCT:
        return "⚪", "barqaror"
    return ("🟢", "yaxshilandi") if pct < 0 else ("🔴", "yomonlashdi")


def compute_changes(rows_newest_first: list[dict]) -> list[Change]:
    """Har ko'rsatkich uchun kamida 2 ta qiymat bo'lsa — o'zgarish."""
    chrono = list(reversed(rows_newest_first))
    out = []
    for key, name, unit, digits in METRICS:
        vals = [r[key] for r in chrono if r.get(key) is not None]
        if len(vals) >= 2:
            out.append(Change(key, name, unit, digits, vals[0], vals[-2], vals[-1], len(vals)))
    return out


def _sign(x: float, digits: int) -> str:
    return f"{x:+.{digits}f}".replace("-", "−")


def format_dynamics(rows_newest_first: list[dict]) -> str:
    """Telegram uchun HTML: so'nggi natijalar jadvali + solishtirish + xulosa."""
    if not rows_newest_first:
        return "📈 Hali natija yo'q. <b>🩺 Yangi baholash</b> yoki <b>⚡ Tezkor HOMA-IR</b> dan boshlang."

    lines = ["📈 <b>Mening dinamikam</b>", ""]
    lines.append("<b>So'nggi natijalar:</b>")
    lines.append("<pre>Sana        HOMA  Glyuk Insul FINDR")
    for r in rows_newest_first[:8]:
        homa = f"{r['homa_ir']:.2f}" if r.get("homa_ir") is not None else "  —"
        glu = f"{r['fasting_glucose']:.1f}" if r.get("fasting_glucose") is not None else "  —"
        ins = f"{r['fasting_insulin']:.1f}" if r.get("fasting_insulin") is not None else "  —"
        fr = str(r["findrisc"]) if r.get("findrisc") is not None else " —"
        lines.append(f"{fmt_dt(r['created_at']):<11} {homa:>5} {glu:>5} {ins:>5} {fr:>5}")
    lines.append("</pre>")

    changes = compute_changes(rows_newest_first)
    if not changes:
        lines.append("Solishtirish uchun kamida <b>2 ta</b> natija kerak. "
                     "3 oydan keyin qayta tekshirib, shu yerga kiriting.")
        return "\n".join(lines)

    lines.append("<b>Oldingi natijaga nisbatan:</b>")
    for c in changes:
        icon, word = verdict(c.pct_prev)
        pct = f" ({_sign(c.pct_prev, 0)}%)" if c.pct_prev is not None else ""
        lines.append(
            f"{icon} {c.name}: {c.prev:.{c.digits}f} → <b>{c.last:.{c.digits}f}</b>{c.unit}"
            f"{pct} — {word}"
        )

    homa = next((c for c in changes if c.key == "homa_ir"), None)
    if homa and homa.n >= 3 and homa.pct_first is not None:
        icon, word = verdict(homa.pct_first)
        lines += ["", f"<b>Birinchi o'lchovdan beri ({homa.n} ta):</b>",
                  f"{icon} HOMA-IR {homa.first:.2f} → {homa.last:.2f} "
                  f"({_sign(homa.pct_first, 0)}%) — {word}"]

    if homa:
        before, after = classify_homa_ir(homa.prev), classify_homa_ir(homa.last)
        lines.append("")
        if before != after:
            lines.append(f"📌 <b>Toifa o'zgardi:</b> {esc(before)} → <b>{esc(after)}</b>")
        else:
            lines.append(f"📌 Toifa o'zgarmadi: <b>{esc(after)}</b>")
    lines += ["", "<i>±10% ichidagi farq laborator o'zgaruvchanlik doirasida — barqaror deb olinadi.</i>"]
    return "\n".join(lines)
