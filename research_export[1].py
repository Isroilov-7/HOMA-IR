"""
Tadqiqot uchun anonim CSV eksporti.
SPSS/R/Python (pandas) da tahlil qilishga tayyor.

Foydalanish:
    python research_export.py           # barcha ma'lumot
    python research_export.py --anon    # faqat anonim rozilik berganlar
    python research_export.py --after 2026-01-01
"""

import argparse
import csv
import os
import sqlite3
import sys
from pathlib import Path

DB_PATH = os.getenv("DB_PATH", "health.db")


def export(anon_only: bool = False, after: str = None, out: str = "research.csv") -> None:
    if not Path(DB_PATH).exists():
        print(f"DB topilmadi: {DB_PATH}", file=sys.stderr)
        sys.exit(1)

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    query = """
        SELECT
            s.id AS screening_id,
            u.user_id,
            u.is_anonymous,
            (strftime('%Y', 'now') - u.birth_year) AS age_calc,
            s.sex, s.age, s.weight, s.height, s.waist,
            s.activity_yes, s.veg_daily, s.bp_meds,
            s.high_glucose_hist, s.family_hx,
            s.fasting_glucose, s.fasting_insulin,
            s.bmi, s.homa_ir,
            s.findrisc, s.findrisc_band, s.combined_band,
            s.created_at
        FROM screenings s
        JOIN users u ON s.user_id = u.user_id
        WHERE 1=1
    """
    params = []
    if anon_only:
        query += " AND u.is_anonymous = 1"
    if after:
        query += " AND s.created_at >= ?"
        params.append(after)
    query += " ORDER BY s.created_at"

    cur = con.execute(query, params)
    rows = cur.fetchall()

    if not rows:
        print("Ma'lumot yo'q.")
        return

    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        # Anonim id — hech qanday tg identifikatori chiqmasin
        writer.writerow([
            "subject_id", "sex", "age", "weight_kg", "height_cm", "waist_cm",
            "activity_daily", "vegetables_daily", "bp_medication",
            "history_high_glucose", "family_diabetes",
            "fasting_glucose_mmol", "fasting_insulin_uiu",
            "bmi", "homa_ir",
            "findrisc_score", "findrisc_band", "combined_band",
            "date",
        ])
        for i, r in enumerate(rows, start=1):
            writer.writerow([
                f"S{i:05d}",
                r["sex"], r["age"], r["weight"], r["height"], r["waist"],
                r["activity_yes"], r["veg_daily"], r["bp_meds"],
                r["high_glucose_hist"], r["family_hx"],
                r["fasting_glucose"] or "", r["fasting_insulin"] or "",
                f"{r['bmi']:.2f}" if r["bmi"] else "",
                f"{r['homa_ir']:.3f}" if r["homa_ir"] else "",
                r["findrisc"], r["findrisc_band"], r["combined_band"],
                r["created_at"],
            ])

    print(f"✅ {len(rows)} ta yozuv → {out}")
    print("   TG ID va ism yo'q, faqat anonim subject_id.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--anon", action="store_true", help="faqat anonim rozilik berganlar")
    ap.add_argument("--after", help="sanadan keyingilar (YYYY-MM-DD)")
    ap.add_argument("--out", default="research.csv")
    args = ap.parse_args()
    export(anon_only=args.anon, after=args.after, out=args.out)
