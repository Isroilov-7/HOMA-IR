"""
SQLite zaxira nusxasi (online backup API — bot ishlab turganda ham xavfsiz).

Qo'lda yoki cron orqali:
    docker compose exec -T bot python -m app.backup
Eski nusxalar BACKUP_KEEP_DAYS kundan keyin o'chiriladi.
"""

import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

from app.config import settings
from app.utils import TASHKENT


def make_backup() -> Path:
    out_dir = Path(settings.backup_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(TASHKENT).strftime("%Y%m%d_%H%M%S")
    dest = out_dir / f"health_{stamp}.db"
    src = sqlite3.connect(settings.db_path)
    try:
        dst = sqlite3.connect(dest)
        with dst:
            src.backup(dst)
        dst.close()
    finally:
        src.close()
    ok = sqlite3.connect(dest).execute("PRAGMA integrity_check").fetchone()[0]
    if ok != "ok":
        raise RuntimeError(f"Zaxira butunligi buzilgan: {ok}")
    prune(out_dir)
    return dest


def prune(out_dir: Path) -> int:
    cutoff = time.time() - settings.backup_keep_days * 86400
    removed = 0
    for f in out_dir.glob("health_*.db"):
        if f.stat().st_mtime < cutoff:
            f.unlink()
            removed += 1
    return removed


if __name__ == "__main__":
    path = make_backup()
    print(f"OK {path} {path.stat().st_size} bayt")
    sys.exit(0)
