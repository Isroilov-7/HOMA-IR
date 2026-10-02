import sqlite3

import pytest

from app import backup, db

V2_SCHEMA = """
CREATE TABLE users (user_id INTEGER PRIMARY KEY, tg_username TEXT, display_name TEXT,
    birth_year INTEGER, is_anonymous INTEGER DEFAULT 0, consent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE screenings (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
    sex TEXT, age INTEGER, weight REAL, height REAL, waist REAL, activity_yes INTEGER,
    veg_daily INTEGER, bp_meds INTEGER, high_glucose_hist INTEGER, family_hx TEXT,
    fasting_glucose REAL, fasting_insulin REAL, bmi REAL, homa_ir REAL, findrisc INTEGER,
    findrisc_band TEXT, combined_band TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
"""


@pytest.mark.asyncio
async def test_v2_database_is_migrated_without_data_loss(tmp_db):
    con = sqlite3.connect(tmp_db)
    con.executescript(V2_SCHEMA)
    con.execute("INSERT INTO users (user_id, display_name) VALUES (5, 'Eski')")
    con.execute("INSERT INTO screenings (user_id, homa_ir, findrisc) VALUES (5, 3.1, 12)")
    con.commit()
    con.close()

    await db.init_db()
    await db.init_db()  # ikkinchi marta — idempotent
    user = await db.get_user(5)
    rows = await db.user_screenings(5)
    assert user["display_name"] == "Eski" and user["reminders"] == 1
    assert rows[0]["homa_ir"] == 3.1 and rows[0]["kind"] == "full"


@pytest.mark.asyncio
async def test_save_and_read_screenings(tmp_db):
    await db.init_db()
    await db.save_user(7, "u", "Ali", None, False)
    sid = await db.save_screening({"user_id": 7, "kind": "quick", "patient_name": "Ali",
                                   "fasting_glucose": 5.0, "fasting_insulin": 10.0,
                                   "homa_ir": 2.22, "activity_yes": True})
    assert (await db.get_screening(7))["id"] == sid
    assert await db.get_screening(8, sid) is None  # boshqa foydalanuvchi o'qiy olmaydi
    counts = await db.overview_counts()
    assert counts["users"] == 1 and counts["quick"] == 1 and counts["with_labs"] == 1


@pytest.mark.asyncio
async def test_save_user_upsert_keeps_reminder_setting(tmp_db):
    await db.init_db()
    await db.save_user(7, "u", "Ali", None, False)
    await db.set_reminders(7, False)
    await db.save_user(7, "u", "Ali Valiyev", None, False)
    user = await db.get_user(7)
    assert user["reminders"] == 0 and user["display_name"] == "Ali Valiyev"


@pytest.mark.asyncio
async def test_due_reminders_once_per_screening(tmp_db):
    await db.init_db()
    await db.save_user(7, "u", "Ali", None, False)
    await db.save_screening({"user_id": 7, "homa_ir": 3.0})
    con = sqlite3.connect(tmp_db)
    con.execute("UPDATE screenings SET created_at = datetime('now', '-100 days')")
    con.commit()
    con.close()
    assert [u["user_id"] for u in await db.due_reminders(90)] == [7]
    await db.mark_reminded(7)
    assert await db.due_reminders(90) == []
    await db.set_reminders(7, True)
    assert await db.due_reminders(90) == []


@pytest.mark.asyncio
async def test_delete_user_data(tmp_db):
    await db.init_db()
    await db.save_user(7, "u", "Ali", None, False)
    await db.save_screening({"user_id": 7, "homa_ir": 3.0})
    await db.delete_user_data(7)
    assert await db.get_user(7) is None and await db.user_screenings(7) == []


@pytest.mark.asyncio
async def test_backup_is_valid_copy(tmp_db):
    await db.init_db()
    await db.save_user(7, "u", "Ali", None, False)
    path = backup.make_backup()
    assert sqlite3.connect(path).execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
