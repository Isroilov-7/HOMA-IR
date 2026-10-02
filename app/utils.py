"""Kichik yordamchilar: vaqt, raqam o'qish, HTML xavfsizligi."""

import html
from datetime import UTC, datetime, timedelta, timezone

# Toshkent: UTC+5, yozgi vaqt yo'q — tzdata kerak emas.
TASHKENT = timezone(timedelta(hours=5))


def parse_utc(value: str) -> datetime:
    """SQLite CURRENT_TIMESTAMP ('YYYY-MM-DD HH:MM:SS', UTC) → aware datetime."""
    return datetime.fromisoformat(str(value)[:19]).replace(tzinfo=UTC)


def fmt_dt(value: str | None, with_time: bool = False) -> str:
    if not value:
        return "—"
    local = parse_utc(value).astimezone(TASHKENT)
    return local.strftime("%d.%m.%Y %H:%M" if with_time else "%d.%m.%Y")


def parse_number(text: str | None) -> float | None:
    """'72,5' / ' 72.5 kg' → 72.5. O'qib bo'lmasa None."""
    if not text:
        return None
    cleaned = text.strip().lower().replace(",", ".")
    for unit in ("kg", "sm", "cm", "mmol/l", "mmol", "mg/dl", "mkme/ml", "μiu/ml", "uiu/ml", "yosh"):
        cleaned = cleaned.replace(unit, "")
    try:
        return float(cleaned.strip())
    except ValueError:
        return None


def esc(text: object) -> str:
    """Foydalanuvchi kiritgan matnni HTML xabarga xavfsiz qo'yish."""
    return html.escape(str(text), quote=False)


def fmt_num(value: float | None, digits: int = 2) -> str:
    return "—" if value is None else f"{value:.{digits}f}"
