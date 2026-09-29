"""
HOMA-IR + FINDRISC Health Screening Bot v2
==========================================
Klinik jihatdan asosli diabet xavfi baholovchi Telegram bot.

Asosiy o'zgarishlar (v1 dan farqi):
- aiogram 3.x (2.x eskirgan)
- FINDRISC shkalasi (Lindström & Tuomilehto, 2003) - xalqaro validatsiya
- HOMA-IR - Matthews et al. (1985) formulasi va cutoff qiymatlari
- Informed consent (tadqiqot roziligi)
- Anonim rejim (research mode)
- PDF hisobot (reportlab)
- Inline keyboardlar (UX)
- .env orqali konfiguratsiya (token xavfsizligi)
- SQLite + migratsiyaga tayyor schema

Adabiyot:
- FINDRISC: Lindström J, Tuomilehto J. Diabetes Care. 2003;26(3):725-731
- HOMA-IR: Matthews DR, et al. Diabetologia. 1985;28(7):412-419
- Uzbek cutoff (tadqiqot): sizning ma'lumotlaringiz asosida keyinchalik
  moslashtirilishi mumkin (research_export.py orqali eksport qiling)
"""

import asyncio
import logging
import os
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Optional

import aiosqlite
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from dotenv import load_dotenv

from calculator import (
    calculate_bmi,
    calculate_findrisc,
    calculate_homa_ir,
    classify_bmi,
    classify_homa_ir,
    classify_waist,
    combined_risk_report,
)
from pdf_report import build_pdf_report
from health_server import start_health_server

# ==================== CONFIGURATION ====================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN yo'q. .env fayldan sozlang.")

ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()}
DB_PATH = os.getenv("DB_PATH", "health.db")
SUPPORT = os.getenv("SUPPORT_USERNAME", "@muhammadali_77")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("bot")

# ==================== STATES ====================


class Onboard(StatesGroup):
    consent = State()
    anonymous_choice = State()
    display_name = State()
    birth_year = State()


class Screen(StatesGroup):
    # FINDRISC savollari
    sex = State()
    age = State()
    bmi_weight = State()
    bmi_height = State()
    waist = State()
    activity = State()  # >=30 min/kun jismoniy faollik?
    vegetables = State()  # har kuni sabzavot/meva?
    bp_meds = State()  # bosim dorilari qabul qilasizmi?
    high_glucose = State()  # tekshiruvda yuqori qand aniqlanganmi?
    family = State()  # oilada diabet?
    # Klinik (ixtiyoriy)
    fasting_glucose = State()
    fasting_insulin = State()


# ==================== DATABASE ====================


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
    sex TEXT,             -- 'M' | 'F'
    age INTEGER,
    weight REAL,
    height REAL,
    waist REAL,
    activity_yes INTEGER, -- 1/0
    veg_daily INTEGER,    -- 1/0
    bp_meds INTEGER,      -- 1/0
    high_glucose_hist INTEGER, -- 1/0
    family_hx TEXT,       -- 'none' | 'second' | 'first'
    fasting_glucose REAL, -- mmol/L, nullable
    fasting_insulin REAL, -- uIU/mL, nullable
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


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()
    logger.info("DB ready: %s", DB_PATH)


async def get_user(user_id: int) -> Optional[aiosqlite.Row]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return await cur.fetchone()


async def save_user(user_id: int, username: str, display_name: str,
                    birth_year: int, anonymous: bool) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT OR REPLACE INTO users
               (user_id, tg_username, display_name, birth_year, is_anonymous, consent_at)
               VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            (user_id, username or "", display_name, birth_year, int(anonymous)),
        )
        await db.commit()


async def save_screening(user_id: int, data: dict, result: dict) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """INSERT INTO screenings
               (user_id, sex, age, weight, height, waist, activity_yes, veg_daily,
                bp_meds, high_glucose_hist, family_hx, fasting_glucose, fasting_insulin,
                bmi, homa_ir, findrisc, findrisc_band, combined_band)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                user_id,
                data["sex"], data["age"], data["weight"], data["height"], data["waist"],
                int(data["activity_yes"]), int(data["veg_daily"]),
                int(data["bp_meds"]), int(data["high_glucose_hist"]),
                data["family_hx"],
                data.get("fasting_glucose"), data.get("fasting_insulin"),
                result["bmi"], result.get("homa_ir"),
                result["findrisc"], result["findrisc_band"], result["combined_band"],
            ),
        )
        await db.commit()
        return cur.lastrowid


async def user_screenings(user_id: int, limit: int = 10) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM screenings WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        )
        return await cur.fetchall()


# ==================== UI HELPERS ====================


def kb(*rows: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    """Qulay inline keyboard konstruktori."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t, callback_data=c) for t, c in row]
        for row in rows
    ])


def main_menu_kb() -> InlineKeyboardMarkup:
    return kb(
        [("🩺 Yangi baholash", "screen:start")],
        [("📊 Mening tarixim", "history"), ("📄 Oxirgi PDF", "pdf:last")],
        [("ℹ️ Bot haqida", "about"), ("🔒 Ma'lumotlarim", "privacy")],
    )


CONSENT_TEXT = (
    "🔬 <b>Tadqiqot va roziligi</b>\n\n"
    "Bu bot <b>HOMA-IR + FINDRISC</b> shkalalari asosida diabet xavfini "
    "baholaydi. Natijalar tashxis emas — bu <b>skrining</b>.\n\n"
    "📋 <b>Ma'lumotlaringiz:</b>\n"
    "• Anonim tadqiqotda ishlatilishi mumkin (o'zbek populyatsiyasi uchun "
    "HOMA-IR chegaralarini aniqlash)\n"
    "• Uchinchi shaxslarga berilmaydi\n"
    "• Istalgan vaqtda o'chirishingiz mumkin (/delete)\n\n"
    "⚠️ <b>Muhim:</b> Har qanday shubhali natija — endokrinolog maslahati.\n\n"
    "Davom etishga rozimisiz?"
)


ABOUT_TEXT = (
    "🏥 <b>HOMA-IR + FINDRISC Skrining</b>\n\n"
    "<b>Shkala manbalari:</b>\n"
    "• FINDRISC — Lindström & Tuomilehto, <i>Diabetes Care</i> 2003\n"
    "• HOMA-IR — Matthews et al., <i>Diabetologia</i> 1985\n\n"
    "<b>Kategoriyalar:</b>\n"
    "• FINDRISC 0–6: past • 7–11: ozgina • 12–14: o'rta\n"
    "• 15–20: yuqori • &gt;20: juda yuqori (10 yil ichida ~50%)\n\n"
    "<b>HOMA-IR cutoff:</b>\n"
    "• &lt;2.0: normal • 2.0–2.5: chegara • &gt;2.5: rezistentlik\n\n"
    f"Aloqa: {SUPPORT}"
)


# ==================== ROUTER ====================

router = Router()


@router.message(CommandStart())
async def cmd_start(m: Message, state: FSMContext):
    await state.clear()
    user = await get_user(m.from_user.id)
    if user:
        name = user["display_name"] or "foydalanuvchi"
        await m.answer(
            f"Assalomu alaykum, <b>{name}</b>! 👋\n\nKerakli bo'limni tanlang:",
            reply_markup=main_menu_kb(),
        )
        return
    await m.answer(CONSENT_TEXT, reply_markup=kb(
        [("✅ Roziman", "consent:yes"), ("❌ Yo'q", "consent:no")],
    ))
    await state.set_state(Onboard.consent)


@router.callback_query(F.data == "consent:no", Onboard.consent)
async def consent_no(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await c.message.edit_text(
        "Tushunarli. Rozilik bo'lmasa bot ishlamaydi. Fikringiz o'zgarsa /start bosing."
    )
    await c.answer()


@router.callback_query(F.data == "consent:yes", Onboard.consent)
async def consent_yes(c: CallbackQuery, state: FSMContext):
    await c.message.edit_text(
        "Rahmat! 🔒 Ismingiz qanday saqlansin?",
        reply_markup=kb(
            [("👤 Haqiqiy ism", "anon:no")],
            [("🕶 Anonim (tavsiya)", "anon:yes")],
        ),
    )
    await state.set_state(Onboard.anonymous_choice)
    await c.answer()


@router.callback_query(F.data.startswith("anon:"), Onboard.anonymous_choice)
async def choose_anon(c: CallbackQuery, state: FSMContext):
    anonymous = c.data.endswith("yes")
    await state.update_data(is_anonymous=anonymous)
    if anonymous:
        # Ism o'rniga random ID
        pseudo = f"User-{c.from_user.id % 10000:04d}"
        await state.update_data(display_name=pseudo)
        await c.message.edit_text(
            f"Sizning anonim ID'ingiz: <code>{pseudo}</code>\n\n"
            "Tug'ilgan yilingizni kiriting (masalan: 1990):"
        )
        await state.set_state(Onboard.birth_year)
    else:
        await c.message.edit_text("Ism va familiyangizni yozing:")
        await state.set_state(Onboard.display_name)
    await c.answer()


@router.message(Onboard.display_name)
async def set_name(m: Message, state: FSMContext):
    name = m.text.strip()
    if len(name) < 2 or len(name) > 60:
        await m.answer("2–60 belgi orasida ism kiriting:")
        return
    await state.update_data(display_name=name)
    await m.answer("Tug'ilgan yilingiz (masalan: 1990):")
    await state.set_state(Onboard.birth_year)


@router.message(Onboard.birth_year)
async def set_year(m: Message, state: FSMContext):
    try:
        year = int(m.text.strip())
    except ValueError:
        await m.answer("Faqat 4 xonali yil kiriting:")
        return
    current = datetime.now().year
    if year < 1920 or year > current - 5:
        await m.answer(f"Yil {1920}–{current-5} orasida bo'lishi kerak:")
        return
    data = await state.get_data()
    await save_user(
        m.from_user.id, m.from_user.username or "",
        data["display_name"], year, data["is_anonymous"],
    )
    await state.clear()
    await m.answer(
        f"✅ Ro'yxatdan o'tildi.\n\nEndi <b>Yangi baholash</b>ni boshlashingiz mumkin.",
        reply_markup=main_menu_kb(),
    )


# ---- SCREENING ----

@router.callback_query(F.data == "screen:start")
async def screen_start(c: CallbackQuery, state: FSMContext):
    user = await get_user(c.from_user.id)
    if not user:
        await c.answer("Avval /start bosing.", show_alert=True)
        return
    await state.clear()
    await c.message.edit_text(
        "🩺 <b>Baholash (8 asosiy + 2 ixtiyoriy savol)</b>\n\n"
        "Jinsingiz:",
        reply_markup=kb([("👨 Erkak", "sex:M"), ("👩 Ayol", "sex:F")]),
    )
    await state.set_state(Screen.sex)
    await c.answer()


@router.callback_query(F.data.startswith("sex:"), Screen.sex)
async def set_sex(c: CallbackQuery, state: FSMContext):
    await state.update_data(sex=c.data.split(":")[1])
    await c.message.edit_text("Yoshingiz (yil):")
    await state.set_state(Screen.age)
    await c.answer()


@router.message(Screen.age)
async def set_age(m: Message, state: FSMContext):
    try:
        age = int(m.text.strip())
        assert 15 <= age <= 100
    except (ValueError, AssertionError):
        await m.answer("15–100 orasida yosh kiriting:")
        return
    await state.update_data(age=age)
    await m.answer("Vazningiz (kg, masalan 72 yoki 72.5):")
    await state.set_state(Screen.bmi_weight)


@router.message(Screen.bmi_weight)
async def set_weight(m: Message, state: FSMContext):
    try:
        w = float(m.text.strip().replace(",", "."))
        assert 30 <= w <= 300
    except (ValueError, AssertionError):
        await m.answer("30–300 kg orasida kiriting:")
        return
    await state.update_data(weight=w)
    await m.answer("Bo'yingiz (sm):")
    await state.set_state(Screen.bmi_height)


@router.message(Screen.bmi_height)
async def set_height(m: Message, state: FSMContext):
    try:
        h = float(m.text.strip().replace(",", "."))
        assert 120 <= h <= 230
    except (ValueError, AssertionError):
        await m.answer("120–230 sm orasida kiriting:")
        return
    await state.update_data(height=h)
    await m.answer("Bel aylanasi (sm, kindik chizig'idan o'lchang):")
    await state.set_state(Screen.waist)


@router.message(Screen.waist)
async def set_waist(m: Message, state: FSMContext):
    try:
        b = float(m.text.strip().replace(",", "."))
        assert 50 <= b <= 200
    except (ValueError, AssertionError):
        await m.answer("50–200 sm orasida kiriting:")
        return
    await state.update_data(waist=b)
    await m.answer(
        "Har kuni kamida <b>30 daqiqa</b> jismoniy faollik (yurish, sport) bormi?",
        reply_markup=kb([("✅ Ha", "act:1"), ("❌ Yo'q", "act:0")]),
    )
    await state.set_state(Screen.activity)


@router.callback_query(F.data.startswith("act:"), Screen.activity)
async def set_activity(c: CallbackQuery, state: FSMContext):
    await state.update_data(activity_yes=c.data.endswith("1"))
    await c.message.edit_text(
        "Har kuni sabzavot yoki meva iste'mol qilasizmi?",
        reply_markup=kb([("✅ Ha", "veg:1"), ("❌ Yo'q", "veg:0")]),
    )
    await state.set_state(Screen.vegetables)
    await c.answer()


@router.callback_query(F.data.startswith("veg:"), Screen.vegetables)
async def set_veg(c: CallbackQuery, state: FSMContext):
    await state.update_data(veg_daily=c.data.endswith("1"))
    await c.message.edit_text(
        "Qon bosimi uchun dori qabul qilasizmi (yoki qilganmisiz)?",
        reply_markup=kb([("✅ Ha", "bp:1"), ("❌ Yo'q", "bp:0")]),
    )
    await state.set_state(Screen.bp_meds)
    await c.answer()


@router.callback_query(F.data.startswith("bp:"), Screen.bp_meds)
async def set_bp(c: CallbackQuery, state: FSMContext):
    await state.update_data(bp_meds=c.data.endswith("1"))
    await c.message.edit_text(
        "Ilgari (tekshiruv, homiladorlik, kasallikda) qonda yuqori qand aniqlanganmi?",
        reply_markup=kb([("✅ Ha", "hg:1"), ("❌ Yo'q", "hg:0")]),
    )
    await state.set_state(Screen.high_glucose)
    await c.answer()


@router.callback_query(F.data.startswith("hg:"), Screen.high_glucose)
async def set_hg(c: CallbackQuery, state: FSMContext):
    await state.update_data(high_glucose_hist=c.data.endswith("1"))
    await c.message.edit_text(
        "Oilangizda diabet bormi?",
        reply_markup=kb(
            [("👤 Yo'q", "fam:none")],
            [("👴 Bobo/buvi, amaki/xola", "fam:second")],
            [("👨‍👩‍👧 Ota-ona, aka-uka, opa-singil, farzand", "fam:first")],
        ),
    )
    await state.set_state(Screen.family)
    await c.answer()


@router.callback_query(F.data.startswith("fam:"), Screen.family)
async def set_family(c: CallbackQuery, state: FSMContext):
    await state.update_data(family_hx=c.data.split(":")[1])
    await c.message.edit_text(
        "Och qoringa qon <b>glukoza</b>si (mmol/L)?\n"
        "<i>Bilmasangiz — 'O'tkazib yuborish'.</i>",
        reply_markup=kb([("⏭ O'tkazib yuborish", "skip:glucose")]),
    )
    await state.set_state(Screen.fasting_glucose)
    await c.answer()


@router.callback_query(F.data == "skip:glucose", Screen.fasting_glucose)
async def skip_glucose(c: CallbackQuery, state: FSMContext):
    await state.update_data(fasting_glucose=None, fasting_insulin=None)
    await c.answer()
    await _finalize(c.message, state, c.from_user.id)


@router.message(Screen.fasting_glucose)
async def set_glucose(m: Message, state: FSMContext):
    try:
        g = float(m.text.strip().replace(",", "."))
        assert 2 <= g <= 30
    except (ValueError, AssertionError):
        await m.answer("2–30 mmol/L kiriting yoki tugma bilan o'tkazib yuboring:")
        return
    await state.update_data(fasting_glucose=g)
    await m.answer(
        "Och qoringa <b>insulin</b> (μIU/mL yoki mkED/ml)?\n"
        "<i>Bilmasangiz — 'O'tkazib yuborish'.</i>",
        reply_markup=kb([("⏭ O'tkazib yuborish", "skip:insulin")]),
    )
    await state.set_state(Screen.fasting_insulin)


@router.callback_query(F.data == "skip:insulin", Screen.fasting_insulin)
async def skip_insulin(c: CallbackQuery, state: FSMContext):
    await state.update_data(fasting_insulin=None)
    await c.answer()
    await _finalize(c.message, state, c.from_user.id)


@router.message(Screen.fasting_insulin)
async def set_insulin(m: Message, state: FSMContext):
    try:
        ins = float(m.text.strip().replace(",", "."))
        assert 0.5 <= ins <= 300
    except (ValueError, AssertionError):
        await m.answer("0.5–300 orasida kiriting yoki o'tkazib yuboring:")
        return
    await state.update_data(fasting_insulin=ins)
    await _finalize(m, state, m.from_user.id)


async def _finalize(msg: Message, state: FSMContext, user_id: int) -> None:
    data = await state.get_data()
    bmi = calculate_bmi(data["weight"], data["height"])
    homa = None
    if data.get("fasting_glucose") and data.get("fasting_insulin"):
        homa = calculate_homa_ir(data["fasting_glucose"], data["fasting_insulin"])

    findrisc_score, findrisc_band = calculate_findrisc(
        age=data["age"], bmi=bmi, waist=data["waist"], sex=data["sex"],
        activity_yes=data["activity_yes"], veg_daily=data["veg_daily"],
        bp_meds=data["bp_meds"], high_glucose_hist=data["high_glucose_hist"],
        family_hx=data["family_hx"],
    )

    report = combined_risk_report(
        findrisc=findrisc_score, findrisc_band=findrisc_band,
        homa_ir=homa, bmi=bmi, waist=data["waist"], sex=data["sex"],
    )
    result = {
        "bmi": bmi, "homa_ir": homa,
        "findrisc": findrisc_score, "findrisc_band": findrisc_band,
        "combined_band": report["combined_band"],
    }
    diag_id = await save_screening(user_id, data, result)

    # Foydalanuvchiga xabar
    text = _format_result(diag_id, data, result, report)
    await msg.answer(text, reply_markup=kb(
        [("📄 PDF yuklab olish", f"pdf:{diag_id}")],
        [("🏠 Bosh menyu", "home")],
    ))
    await state.clear()


def _format_result(diag_id: int, data: dict, result: dict, report: dict) -> str:
    lines = [
        f"🏁 <b>Baholash natijasi #{diag_id}</b>",
        "",
        f"📊 <b>FINDRISC:</b> {result['findrisc']}/26 — <b>{result['findrisc_band']}</b>",
        f"    10 yil ichida 2-tur diabet ehtimoli: {report['ten_year_risk']}",
    ]
    if result["homa_ir"] is not None:
        cls = classify_homa_ir(result["homa_ir"])
        lines.append(f"🧬 <b>HOMA-IR:</b> {result['homa_ir']:.2f} — {cls}")
    lines += [
        f"⚖️  <b>BMI:</b> {result['bmi']:.1f} ({classify_bmi(result['bmi'])})",
        f"📏 <b>Bel:</b> {data['waist']:.0f} sm ({classify_waist(data['sex'], data['waist'])})",
        "",
        f"<b>Umumiy xulosa:</b> {report['combined_band']}",
        "",
        "<b>Tavsiyalar:</b>",
    ]
    for r in report["recommendations"]:
        lines.append(f"• {r}")
    lines += [
        "",
        "⚠️ <i>Bu skrining, tashxis emas. Yuqori xavf — endokrinologga murojaat.</i>",
    ]
    return "\n".join(lines)


# ---- HISTORY / PDF ----

@router.callback_query(F.data == "home")
async def go_home(c: CallbackQuery):
    await c.message.answer("Bosh menyu:", reply_markup=main_menu_kb())
    await c.answer()


@router.callback_query(F.data == "history")
async def history(c: CallbackQuery):
    rows = await user_screenings(c.from_user.id, limit=10)
    if not rows:
        await c.answer("Hozircha baholash yo'q.", show_alert=True)
        return
    lines = ["📊 <b>Oxirgi 10 ta baholash:</b>\n"]
    for r in rows:
        homa = f"HOMA {r['homa_ir']:.2f}" if r["homa_ir"] else "HOMA —"
        lines.append(
            f"#{r['id']} • {r['created_at'][:10]} • "
            f"FINDRISC {r['findrisc']} ({r['findrisc_band']}) • {homa}"
        )
    await c.message.answer("\n".join(lines), reply_markup=main_menu_kb())
    await c.answer()


@router.callback_query(F.data == "about")
async def about(c: CallbackQuery):
    await c.message.answer(ABOUT_TEXT, reply_markup=main_menu_kb())
    await c.answer()


@router.callback_query(F.data == "privacy")
async def privacy(c: CallbackQuery):
    await c.message.answer(
        "🔒 <b>Ma'lumotlaringiz</b>\n\n"
        "• <code>/export</code> — o'z ma'lumotlaringizni JSON'da olish\n"
        "• <code>/delete</code> — hammasini o'chirish (qaytarib bo'lmaydi)\n"
        f"\nSavollar: {SUPPORT}",
        reply_markup=main_menu_kb(),
    )
    await c.answer()


@router.callback_query(F.data.startswith("pdf:"))
async def send_pdf(c: CallbackQuery):
    target = c.data.split(":")[1]
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if target == "last":
            cur = await db.execute(
                "SELECT * FROM screenings WHERE user_id=? ORDER BY id DESC LIMIT 1",
                (c.from_user.id,),
            )
        else:
            cur = await db.execute(
                "SELECT * FROM screenings WHERE id=? AND user_id=?",
                (int(target), c.from_user.id),
            )
        row = await cur.fetchone()
        u_cur = await db.execute("SELECT * FROM users WHERE user_id=?", (c.from_user.id,))
        user = await u_cur.fetchone()
    if not row:
        await c.answer("Baholash topilmadi.", show_alert=True)
        return
    pdf_bytes = build_pdf_report(user=dict(user), screening=dict(row))
    await c.message.answer_document(
        BufferedInputFile(pdf_bytes, filename=f"skrining_{row['id']}.pdf"),
        caption=f"📄 Baholash #{row['id']} — PDF hisobot",
    )
    await c.answer()


# ---- USER-DATA COMMANDS ----

@router.message(Command("delete"))
async def cmd_delete(m: Message):
    await m.answer(
        "⚠️ Barcha ma'lumotlaringiz o'chiriladi. Ishonchingiz komilmi?",
        reply_markup=kb(
            [("🗑 Ha, o'chir", "del:yes"), ("↩️ Bekor", "home")],
        ),
    )


@router.callback_query(F.data == "del:yes")
async def do_delete(c: CallbackQuery):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM screenings WHERE user_id=?", (c.from_user.id,))
        await db.execute("DELETE FROM users WHERE user_id=?", (c.from_user.id,))
        await db.commit()
    await c.message.edit_text("✅ Barcha ma'lumotlaringiz o'chirildi. /start")
    await c.answer()


@router.message(Command("export"))
async def cmd_export(m: Message):
    import json
    rows = await user_screenings(m.from_user.id, limit=1000)
    payload = json.dumps([dict(r) for r in rows], ensure_ascii=False, indent=2, default=str)
    await m.answer_document(
        BufferedInputFile(payload.encode("utf-8"), filename="mening_malumotlarim.json")
    )


# ---- ADMIN ----

@router.message(Command("admin"))
async def cmd_admin(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        (users,) = await (await db.execute("SELECT COUNT(*) FROM users")).fetchone()
        (screens,) = await (await db.execute("SELECT COUNT(*) FROM screenings")).fetchone()
        (avg_fr,) = await (await db.execute("SELECT AVG(findrisc) FROM screenings")).fetchone()
    await m.answer(
        f"👨‍💼 <b>Admin</b>\n\n"
        f"Foydalanuvchi: {users}\n"
        f"Baholash: {screens}\n"
        f"O'rt. FINDRISC: {avg_fr:.1f}" if avg_fr else "O'rtacha: —",
    )


# ==================== MAIN ====================

async def main():
    await init_db()
    # Koyeb/Render uchun kichik HTTP endpoint (fon vazifasi)
    await start_health_server()
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    logger.info("Bot ishga tushdi.")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
