"""
SQLite qatlami (aiosqlite).

Eski v2 bazasi ham ishlaydi: migrate() yetishmagan ustunlarni qo'shadi,
mavjud ma'lumotlarga tegmaydi. Vaqtlar UTC'da saqlanadi (CURRENT_TIMESTAMP),
ko'rsatishda Toshkent vaqtiga o'giriladi (app.utils.fmt_dt).
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import aiosqlite

from app.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    tg_username TEXT,
    display_name TEXT,
    birth_year INTEGER,
    is_anonymous INTEGER DEFAULT 0,
    consent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS screenings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    sex TEXT,
    age INTEGER,
    weight REAL,
    height REAL,
    waist REAL,
    activity_yes INTEGER,
    veg_daily INTEGER,
    bp_meds INTEGER,
    high_glucose_hist INTEGER,
    family_hx TEXT,
    fasting_glucose REAL,
    fasting_insulin REAL,
    bmi REAL,
    homa_ir REAL,
    findrisc INTEGER,
    findrisc_band TEXT,
    combined_band TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE INDEX IF NOT EXISTS idx_screen_user ON screenings(user_id);
CREATE INDEX IF NOT EXISTS idx_screen_created ON screenings(created_at);
"""

# v3 da qo'shilgan ustunlar: (jadval, ustun, tip)
MIGRATIONS: list[tuple[str, str, str]] = [
    ("users", "reminders", "INTEGER DEFAULT 1"),
    ("users", "last_reminded_at", "TIMESTAMP"),
    ("screenings", "kind", "TEXT DEFAULT 'full'"),      # 'full' | 'quick'
    ("screenings", "patient_name", "TEXT"),
    ("screenings", "homa_beta", "REAL"),
    ("screenings", "quicki", "REAL"),
    ("screenings", "whtr", "REAL"),
]

SCREENING_COLUMNS = (
    "user_id", "kind", "patient_name", "sex", "age", "weight", "height", "waist",
    "activity_yes", "veg_daily", "bp_meds", "high_glucose_hist", "family_hx",
    "fasting_glucose", "fasting_insulin", "bmi", "homa_ir", "homa_beta", "quicki",
    "whtr", "findrisc", "findrisc_band", "combined_band",
)


@asynccontextmanager
async def connect() -> AsyncIterator[aiosqlite.Connection]:
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")
        yield db


async def init_db() -> None:
    async with connect() as db:
        await db.execute("PRAGMA journal_mode = WAL")
        await db.executescript(SCHEMA)
        await migrate(db)
        await db.commit()


async def migrate(db: aiosqlite.Connection) -> list[str]:
    """Yetishmagan ustunlarni qo'shadi. Qo'shilganlar ro'yxatini qaytaradi."""
    added = []
    for table, column, ddl in MIGRATIONS:
        cur = await db.execute(f"PRAGMA table_info({table})")
        existing = {row[1] for row in await cur.fetchall()}
        if column not in existing:
            await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
            added.append(f"{table}.{column}")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_screen_kind ON screenings(kind)")
    return added


def _row(r: aiosqlite.Row | None) -> dict | None:
    return dict(r) if r is not None else None


# ---------------- users ----------------

async def get_user(user_id: int) -> dict | None:
    async with connect() as db:
        cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return _row(await cur.fetchone())


async def save_user(user_id: int, username: str, display_name: str,
                    birth_year: int | None, anonymous: bool) -> None:
    """Upsert: qayta ro'yxatdan o'tishda eslatma sozlamasi saqlanib qoladi."""
    async with connect() as db:
        await db.execute(
            """INSERT INTO users (user_id, tg_username, display_name, birth_year,
                                  is_anonymous, consent_at)
               VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(user_id) DO UPDATE SET
                   tg_username = excluded.tg_username,
                   display_name = excluded.display_name,
                   birth_year = excluded.birth_year,
                   is_anonymous = excluded.is_anonymous,
                   consent_at = excluded.consent_at""",
            (user_id, username or "", display_name, birth_year, int(anonymous)),
        )
        await db.commit()


async def set_reminders(user_id: int, enabled: bool) -> None:
    async with connect() as db:
        await db.execute("UPDATE users SET reminders = ? WHERE user_id = ?",
                         (int(enabled), user_id))
        await db.commit()


async def delete_user_data(user_id: int) -> None:
    async with connect() as db:
        await db.execute("DELETE FROM screenings WHERE user_id = ?", (user_id,))
        await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        await db.commit()


# ---------------- screenings ----------------

async def save_screening(record: dict[str, Any]) -> int:
    cols = [c for c in SCREENING_COLUMNS if c in record]
    values = [int(record[c]) if isinstance(record[c], bool) else record[c] for c in cols]
    async with connect() as db:
        cur = await db.execute(
            f"INSERT INTO screenings ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
            values,
        )
        await db.commit()
        return cur.lastrowid


async def user_screenings(user_id: int, limit: int = 50) -> list[dict]:
    """Yangi → eski tartibda."""
    async with connect() as db:
        cur = await db.execute(
            "SELECT * FROM screenings WHERE user_id = ? "
            "ORDER BY created_at DESC, id DESC LIMIT ?",
            (user_id, limit),
        )
        return [dict(r) for r in await cur.fetchall()]


async def get_screening(user_id: int, screening_id: int | None = None) -> dict | None:
    """Faqat egasining yozuvi qaytadi (boshqa foydalanuvchi ID taxmin qila olmaydi)."""
    async with connect() as db:
        if screening_id is None:
            cur = await db.execute(
                "SELECT * FROM screenings WHERE user_id = ? ORDER BY id DESC LIMIT 1",
                (user_id,),
            )
        else:
            cur = await db.execute(
                "SELECT * FROM screenings WHERE id = ? AND user_id = ?",
                (screening_id, user_id),
            )
        return _row(await cur.fetchone())


# ---------------- admin / tadqiqot ----------------

async def all_screenings() -> list[dict]:
    """Tadqiqot tahlili uchun: har yozuv + foydalanuvchi ma'lumoti."""
    async with connect() as db:
        cur = await db.execute(
            """SELECT s.*, u.is_anonymous, u.birth_year, u.tg_username
               FROM screenings s LEFT JOIN users u ON u.user_id = s.user_id
               ORDER BY s.created_at, s.id"""
        )
        return [dict(r) for r in await cur.fetchall()]


async def overview_counts() -> dict:
    async with connect() as db:
        async def one(sql: str) -> Any:
            cur = await db.execute(sql)
            row = await cur.fetchone()
            return row[0] if row else 0

        return {
            "users": await one("SELECT COUNT(*) FROM users"),
            "screenings": await one("SELECT COUNT(*) FROM screenings"),
            "full": await one("SELECT COUNT(*) FROM screenings WHERE COALESCE(kind,'full')='full'"),
            "quick": await one("SELECT COUNT(*) FROM screenings WHERE kind='quick'"),
            "with_labs": await one("SELECT COUNT(*) FROM screenings WHERE homa_ir IS NOT NULL"),
            "today": await one(
                "SELECT COUNT(*) FROM screenings WHERE created_at >= datetime('now','-1 day')"),
            "week": await one(
                "SELECT COUNT(*) FROM screenings WHERE created_at >= datetime('now','-7 days')"),
            "new_users_week": await one(
                "SELECT COUNT(*) FROM users WHERE created_at >= datetime('now','-7 days')"),
            "no_insulin": await one(
                "SELECT COUNT(*) FROM screenings WHERE fasting_glucose IS NOT NULL AND homa_ir IS NULL"),
            "repeat_patients": await one(
                "SELECT COUNT(*) FROM (SELECT user_id FROM screenings "
                "WHERE homa_ir IS NOT NULL GROUP BY user_id HAVING COUNT(*) >= 2)"),
        }


async def due_reminders(days: int, incomplete_days: int | None = None) -> list[dict]:
    """
    Eslatma yoqilgan va oxirgi natijasidan keyin hali eslatilmagan foydalanuvchilar:
    - oxirgi natijada HOMA-IR bor bo'lsa — `days` kundan keyin (qayta tekshiruv);
    - HOMA-IR yo'q (insulin topshirilmagan) bo'lsa — `incomplete_days` kundan keyin.
    Qaytaradi: user_id, display_name, last_at, complete (1/0).
    """
    incomplete_days = days if incomplete_days is None else incomplete_days
    async with connect() as db:
        cur = await db.execute(
            """SELECT u.user_id, u.display_name, s.created_at AS last_at,
                      (s.homa_ir IS NOT NULL) AS complete
               FROM users u
               JOIN screenings s ON s.id = (
                   SELECT id FROM screenings WHERE user_id = u.user_id
                   ORDER BY created_at DESC, id DESC LIMIT 1)
               WHERE COALESCE(u.reminders, 1) = 1
                 AND (u.last_reminded_at IS NULL OR u.last_reminded_at < s.created_at)
                 AND s.created_at <= datetime('now',
                       CASE WHEN s.homa_ir IS NULL THEN ? ELSE ? END)""",
            (f"-{int(incomplete_days)} days", f"-{int(days)} days"),
        )
        return [dict(r) for r in await cur.fetchall()]


async def mark_reminded(user_id: int) -> None:
    async with connect() as db:
        await db.execute(
            "UPDATE users SET last_reminded_at = CURRENT_TIMESTAMP WHERE user_id = ?",
            (user_id,),
        )
        await db.commit()
