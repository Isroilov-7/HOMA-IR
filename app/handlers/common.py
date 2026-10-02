"""Start, rozilik, bosh menyu, ma'lumot va maxfiylik buyruqlari."""

import json

from aiogram import F, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from app import db, ui
from app.utils import esc

router = Router(name="common")


class Onboard(StatesGroup):
    consent = State()
    name_choice = State()
    name = State()


async def show_menu(target: Message, user_id: int, text: str | None = None) -> None:
    user = await db.get_user(user_id)
    name = esc(user["display_name"]) if user and user.get("display_name") else ""
    reminders = (user or {}).get("reminders") != 0
    await target.answer(
        text or (f"Assalomu alaykum, <b>{name}</b>! Kerakli bo'limni tanlang:" if name
                 else "Kerakli bo'limni tanlang:"),
        reply_markup=ui.main_menu(user_id, reminders),
    )


@router.message(CommandStart())
async def cmd_start(m: Message, state: FSMContext):
    await state.clear()
    if await db.get_user(m.from_user.id):
        await show_menu(m, m.from_user.id)
        return
    await m.answer(ui.INTRO)
    await m.answer(ui.CONSENT, reply_markup=ui.kb(
        [("✅ Roziman", "consent:yes"), ("❌ Yo'q", "consent:no")]))
    await state.set_state(Onboard.consent)


@router.callback_query(F.data == "consent:no")
async def consent_no(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await c.message.edit_text(
        "Tushunarli. Roziliksiz natijani saqlab bo'lmaydi. Fikringiz o'zgarsa /start bosing.")
    await c.answer()


@router.callback_query(F.data == "consent:yes")
async def consent_yes(c: CallbackQuery, state: FSMContext):
    await c.message.edit_text(
        "Rahmat! Hisobotlarda ismingiz qanday ko'rsatilsin?",
        reply_markup=ui.kb([("👤 Ism-familiyamni yozaman", "anon:no")],
                           [("🕶 Anonim qolaman", "anon:yes")]),
    )
    await state.set_state(Onboard.name_choice)
    await c.answer()


@router.callback_query(F.data.startswith("anon:"), Onboard.name_choice)
async def choose_anon(c: CallbackQuery, state: FSMContext):
    if c.data == "anon:yes":
        pseudo = f"Anonim-{c.from_user.id % 10000:04d}"
        await db.save_user(c.from_user.id, c.from_user.username or "", pseudo, None, True)
        await state.clear()
        await c.message.edit_text(f"✅ Ro'yxatdan o'tdingiz. Anonim ID: <code>{pseudo}</code>")
        await show_menu(c.message, c.from_user.id, "Boshlash uchun bo'limni tanlang:")
    else:
        await c.message.edit_text("Ism va familiyangizni yozing (masalan: <i>Aliyev Vali</i>):")
        await state.set_state(Onboard.name)
    await c.answer()


@router.message(Onboard.name, F.text)
async def set_name(m: Message, state: FSMContext):
    name = " ".join(m.text.split())
    if not 2 <= len(name) <= 60:
        await m.answer("Ism 2–60 belgi bo'lishi kerak. Qayta yozing:")
        return
    await db.save_user(m.from_user.id, m.from_user.username or "", name, None, False)
    await state.clear()
    await m.answer("✅ Ro'yxatdan o'tdingiz.")
    await show_menu(m, m.from_user.id, "Boshlash uchun bo'limni tanlang:")


# ---------------- umumiy ----------------

@router.message(Command("cancel"))
@router.callback_query(F.data == "cancel")
async def cancel(event: Message | CallbackQuery, state: FSMContext):
    await state.clear()
    msg = event.message if isinstance(event, CallbackQuery) else event
    if isinstance(event, CallbackQuery):
        await event.answer("Bekor qilindi")
    await show_menu(msg, event.from_user.id, "Bekor qilindi. Bosh menyu:")


@router.callback_query(F.data == "home")
async def go_home(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await show_menu(c.message, c.from_user.id)
    await c.answer()


@router.message(Command("help"))
async def cmd_help(m: Message):
    await m.answer(ui.HELP)


@router.message(Command("about"))
@router.callback_query(F.data == "about")
async def about(event: Message | CallbackQuery):
    msg = event.message if isinstance(event, CallbackQuery) else event
    await msg.answer(ui.ABOUT, reply_markup=ui.kb([("🏠 Bosh menyu", "home")]))
    if isinstance(event, CallbackQuery):
        await event.answer()


@router.callback_query(F.data == "privacy")
async def privacy(c: CallbackQuery):
    await c.message.answer(
        "🔒 <b>Maxfiylik</b>\n\n"
        "• Ma'lumotlar faqat shu bot serverida saqlanadi va har kuni zaxiralanadi.\n"
        "• Tadqiqot eksportida ism va Telegram ID bo'lmaydi, faqat anonim kod (S0001…).\n"
        "• /export: barcha ma'lumotlaringiz (JSON)\n"
        "• /delete: hammasini o'chirish (qaytarib bo'lmaydi)",
        reply_markup=ui.kb([("🏠 Bosh menyu", "home")]),
    )
    await c.answer()


@router.callback_query(F.data == "remind:toggle")
async def toggle_reminders(c: CallbackQuery):
    user = await db.get_user(c.from_user.id)
    if not user:
        await c.answer("Avval /start bosing.", show_alert=True)
        return
    new = user.get("reminders") == 0
    await db.set_reminders(c.from_user.id, new)
    await c.answer("Qayta tekshiruv eslatmasi yoqildi 🔔" if new else "Eslatma o'chirildi 🔕",
                   show_alert=True)
    await c.message.edit_reply_markup(reply_markup=ui.main_menu(c.from_user.id, new))


@router.message(Command("export"))
async def cmd_export(m: Message):
    user = await db.get_user(m.from_user.id)
    rows = await db.user_screenings(m.from_user.id, limit=10000)
    payload = json.dumps({"user": user, "screenings": rows}, ensure_ascii=False, indent=2, default=str)
    await m.answer_document(BufferedInputFile(payload.encode("utf-8"), filename="mening_malumotlarim.json"),
                            caption="🔒 Sizning barcha ma'lumotlaringiz")


@router.message(Command("delete"))
async def cmd_delete(m: Message):
    await m.answer("⚠️ Barcha natijalaringiz va profilingiz o'chiriladi. Qaytarib bo'lmaydi. Ishonchingiz komilmi?",
                   reply_markup=ui.kb([("🗑 Ha, o'chirilsin", "del:yes"), ("↩️ Yo'q", "home")]))


@router.callback_query(F.data == "del:yes")
async def do_delete(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await db.delete_user_data(c.from_user.id)
    await c.message.edit_text("✅ Ma'lumotlaringiz o'chirildi. Qayta boshlash: /start")
    await c.answer()


@router.message(StateFilter(None), F.text & ~F.text.startswith("/"))
async def fallback(m: Message):
    """So'rovnomadan tashqari matn: menyuni qayta ko'rsatamiz."""
    if not await db.get_user(m.from_user.id):
        await m.answer("Boshlash uchun /start bosing.")
        return
    await show_menu(m, m.from_user.id, "Kerakli bo'limni tanlang:")
