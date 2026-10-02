"""
Tadqiqot uchun anonim CSV eksporti (serverda, botsiz).
SPSS / R / Python (pandas) da tahlil qilishga tayyor; ism va Telegram ID yo'q.

    python research_export.py                 # barcha ma'lumot
    python research_export.py --anon          # faqat anonim rozilik berganlar
    python research_export.py --after 2026-01-01 --out yangi.csv

Docker'da:
    docker compose exec -T bot python research_export.py --out /data/research.csv
"""

import argparse
import asyncio
import sys
from pathlib import Path

from app import db
from app.config import settings
from app.reports.research_xlsx import build_csv


async def _rows(after: str | None) -> list[dict]:
    rows = await db.all_screenings()
    return [r for r in rows if not after or str(r["created_at"]) >= after]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--anon", action="store_true", help="faqat anonim rozilik berganlar")
    ap.add_argument("--after", help="shu sanadan keyingilar (YYYY-MM-DD)")
    ap.add_argument("--out", default="research.csv")
    args = ap.parse_args()
    if not Path(settings.db_path).exists():
        sys.exit(f"DB topilmadi: {settings.db_path}")
    rows = asyncio.run(_rows(args.after))
    Path(args.out).write_bytes(build_csv(rows, anon_only=args.anon))
    print(f"OK {len(rows)} ta yozuv -> {args.out} (faqat anonim subject_id)")


if __name__ == "__main__":
    main()
