"""
Grafiklar (matplotlib, Agg). PNG — Telegram uchun, PDF hisobotga ham qo'yiladi.

Dizayn qoidalari: bitta o'q (dual-axis yo'q — har o'lchov alohida panel),
ingichka chiziqlar, xira grid, rang faqat ma'no uchun; zonalar rang + yozuv bilan.
Ranglar validatsiyadan o'tgan palitradan (yorug' fon).
"""

from io import BytesIO

from app.calculator import HOMA_IR_CUTOFF
from app.utils import TASHKENT, parse_utc

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]  # 1–3 kategorial slotlar
ORDINAL = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"]  # tartibli (FINDRISC)
STATUS = {"good": "#0ca30c", "warning": "#fab219", "serious": "#ec835a", "critical": "#d03b3b"}

HOMA_ZONES = [  # (pastki, yuqori, rang, yozuv)
    (0.0, 2.0, STATUS["good"], "normal"),
    (2.0, 2.5, STATUS["warning"], "chegara"),
    (2.5, 3.8, STATUS["serious"], "IR"),
    (3.8, 99.0, STATUS["critical"], "yuqori IR"),
]


def _plt():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.edgecolor": GRID,
        "axes.labelcolor": INK_2,
        "axes.titlecolor": INK,
        "axes.titlesize": 11,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
    })
    return plt


def _png(fig) -> bytes:
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=160, bbox_inches="tight")
    import matplotlib.pyplot as plt

    plt.close(fig)
    return buf.getvalue()


def _shade_homa(ax, ymax: float) -> None:
    for lo, hi, color, label in HOMA_ZONES:
        if lo >= ymax:
            break
        ax.axhspan(lo, min(hi, ymax), color=color, alpha=0.10, lw=0)
        ax.text(1.005, (lo + min(hi, ymax)) / 2, label, transform=ax.get_yaxis_transform(),
                va="center", ha="left", fontsize=8, color=INK_2)


# ---------------- bemor dinamikasi ----------------

def patient_trend_png(rows_newest_first: list[dict], title: str = "") -> bytes | None:
    """HOMA-IR, glukoza, insulin — alohida panellar (umumiy vaqt o'qi)."""
    chrono = list(reversed(rows_newest_first))
    panels = []
    for key, name, unit in (("homa_ir", "HOMA-IR", ""), ("fasting_glucose", "Glukoza", "mmol/L"),
                            ("fasting_insulin", "Insulin", "μU/mL")):
        pts = [(parse_utc(r["created_at"]).astimezone(TASHKENT), r[key])
               for r in chrono if r.get(key) is not None]
        if len(pts) >= 2:
            panels.append((key, name, unit, pts))
    if not panels:
        return None

    plt = _plt()
    import matplotlib.dates as mdates

    fig, axes = plt.subplots(len(panels), 1, figsize=(7.2, 2.3 * len(panels) + 0.4),
                             sharex=True, squeeze=False)
    for ax, (key, name, unit, pts) in zip(axes[:, 0], panels):
        xs, ys = zip(*pts)
        ymax = max(max(ys) * 1.25, 3.0 if key == "homa_ir" else max(ys) * 1.25)
        if key == "homa_ir":
            _shade_homa(ax, ymax)
        elif key == "fasting_glucose":
            ax.axhline(5.6, color=MUTED, lw=1, ls="--")
            ax.text(1.005, 5.6, "5.6", transform=ax.get_yaxis_transform(),
                    va="center", fontsize=8, color=INK_2)
            ymax = max(ymax, 6.5)
        ax.plot(xs, ys, color=SERIES[0], lw=2, marker="o", ms=6,
                markeredgecolor=SURFACE, markeredgewidth=1.5, zorder=3)
        # faqat birinchi va oxirgi nuqtaga qiymat yoziladi
        for x, y in (pts[0], pts[-1]):
            ax.annotate(f"{y:.2f}" if key == "homa_ir" else f"{y:.1f}", (x, y),
                        textcoords="offset points", xytext=(0, 8), ha="center",
                        fontsize=9, color=INK)
        ax.set_ylim(0, ymax)
        ax.set_title(f"{name}" + (f", {unit}" if unit else ""))
    axes[-1, 0].xaxis.set_major_formatter(mdates.DateFormatter("%d.%m.%y"))
    fig.autofmt_xdate()
    if title:
        fig.suptitle(title, x=0.01, ha="left", fontsize=12, fontweight="bold", color=INK)
    fig.tight_layout()
    return _png(fig)


# ---------------- kogorta grafiklari (admin / dissertatsiya) ----------------

def homa_histogram_png(values: list[float], p75: float | None = None) -> bytes | None:
    if len(values) < 3:
        return None
    import numpy as np

    plt = _plt()
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    hi = float(np.percentile(values, 99)) * 1.1
    bins = np.linspace(0, max(hi, 4.0), 25)
    ax.hist([min(v, bins[-1]) for v in values], bins=bins, color=SERIES[0],
            edgecolor=SURFACE, linewidth=1.5)
    # Yozuvlar ustunlar ustiga tushmasligi uchun — legenda
    ax.axvline(HOMA_IR_CUTOFF, color=STATUS["critical"], lw=1.5, ls="--",
               label=f"cutoff {HOMA_IR_CUTOFF}")
    if p75 is not None:
        ax.axvline(p75, color=INK_2, lw=1.2, ls=":", label=f"P75 sog'lom guruh = {p75:.2f}")
    ax.legend(frameon=False, loc="upper right", fontsize=8, labelcolor=INK)
    ax.set_title(f"HOMA-IR taqsimoti (n={len(values)})")
    ax.set_xlabel("HOMA-IR")
    ax.set_ylabel("Sub'ektlar soni")
    fig.tight_layout()
    return _png(fig)


def prevalence_bars_png(items: list[dict], title: str) -> bytes | None:
    items = [i for i in items if i["n"] > 0]
    if not items:
        return None
    plt = _plt()
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    labels = [f"{i['label']}\n(n={i['n']})" for i in items]
    pcts = [i["pct"] for i in items]
    err = [[max(0.0, i["pct"] - i["lo"]) for i in items], [max(0.0, i["hi"] - i["pct"]) for i in items]]
    ax.bar(labels, pcts, color=SERIES[0], width=0.55, edgecolor=SURFACE, linewidth=2)
    ax.errorbar(labels, pcts, yerr=err, fmt="none", ecolor=INK_2, elinewidth=1, capsize=4)
    for x, (p, i) in enumerate(zip(pcts, items)):
        ax.text(x, i["hi"] + 2, f"{p:.0f}%", ha="center", fontsize=9, color=INK)
    ax.set_ylim(0, min(110, max(i["hi"] for i in items) + 14))
    ax.set_ylabel("IR ulushi, % (95% CI)")
    ax.set_title(title)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    return _png(fig)


def scatter_png(rows: list[dict], x: str, xlabel: str, rho: float | None,
                p_text: str) -> bytes | None:
    pts = [(r[x], r["homa_ir"]) for r in rows if r.get(x) is not None and r.get("homa_ir") is not None]
    if len(pts) < 5:
        return None
    plt = _plt()
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    xs, ys = zip(*pts)
    ax.scatter(xs, ys, s=28, color=SERIES[0], alpha=0.75, edgecolors=SURFACE, linewidths=1)
    ax.axhline(HOMA_IR_CUTOFF, color=STATUS["critical"], lw=1.2, ls="--")
    ax.set_xlabel(xlabel)
    ax.set_ylabel("HOMA-IR")
    p_part = f"p {p_text}" if p_text.startswith("<") else f"p = {p_text}"
    stat = f"Spearman ρ = {rho:.2f}, {p_part}" if rho is not None else ""
    ax.set_title(f"HOMA-IR va {xlabel}   {stat}")
    fig.tight_layout()
    return _png(fig)


def findrisc_bars_png(bands: list[tuple[str, int]]) -> bytes | None:
    total = sum(n for _, n in bands)
    if total == 0:
        return None
    plt = _plt()
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    labels = [b for b, _ in bands]
    counts = [n for _, n in bands]
    ax.bar(labels, counts, color=ORDINAL[:len(labels)], width=0.6, edgecolor=SURFACE, linewidth=2)
    for x, n in enumerate(counts):
        ax.text(x, n + total * 0.01, f"{n} ({n / total * 100:.0f}%)", ha="center",
                va="bottom", fontsize=9, color=INK)
    ax.set_ylabel("Sub'ektlar soni")
    ax.set_title(f"FINDRISC xavf toifalari (n={total})")
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    return _png(fig)
