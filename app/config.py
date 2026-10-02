"""
Sozlamalar faqat muhit o'zgaruvchilaridan (.env) olinadi.
Token va admin ID'lari kodda hech qachon yozilmaydi.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
FONTS_DIR = ROOT / "assets" / "fonts"


def _int_set(raw: str) -> frozenset[int]:
    return frozenset(int(x) for x in raw.replace(" ", "").split(",") if x.strip().isdigit())


@dataclass(frozen=True)
class Settings:
    bot_token: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    admin_ids: frozenset[int] = field(default_factory=lambda: _int_set(os.getenv("ADMIN_IDS", "")))
    db_path: str = field(default_factory=lambda: os.getenv("DB_PATH", "health.db"))
    backup_dir: str = field(default_factory=lambda: os.getenv("BACKUP_DIR", "backups"))
    backup_keep_days: int = field(default_factory=lambda: int(os.getenv("BACKUP_KEEP_DAYS", "30")))
    support: str = field(default_factory=lambda: os.getenv("SUPPORT_USERNAME", "@muhammadali_77"))
    # Qayta tekshiruv eslatmasi (kun). 0 — o'chirilgan.
    reminder_days: int = field(default_factory=lambda: int(os.getenv("REMINDER_DAYS", "90")))
    # Insulin topshirilmagan natijadan keyin to'liq tahlilga eslatma (kun)
    insulin_reminder_days: int = field(default_factory=lambda: int(os.getenv("INSULIN_REMINDER_DAYS", "14")))
    # Faqat Koyeb/Render kabi platformalar uchun. Serverda bo'sh qoldiring.
    health_port: str = field(default_factory=lambda: os.getenv("HEALTH_PORT", ""))


settings = Settings()
