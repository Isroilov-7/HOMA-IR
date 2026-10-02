"""Start (tanishuv + ism-familiya), bosh menyu, ma'lumot va maxfiylik buyruqlari."""

import json

from aiogram import F, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from app import db, ui
from app.utils import esc, valid_full_name

router = Router(name="common")


class Onboard(StatesGroup):
    name = State()


def needs_name(user: dict | None) -> bool:
    """Tadqiqot uchun har foydalanuvchining ism-familiyasi kerak (eski anonimlar ham so'raladi)."""
    return not user or bool(user.get("is_anonymous")) or not user.get("display_name")


async def ask_name(msg: Message, state: FSMContext) -> None:
    await msg.answer(ui.ASK_NAME)
    await state.set_state(Onboard.name)


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
    user = await db.get_user(m.from_user.id)
    if user and not needs_name(user):
        await show_menu(m, m.from_user.id)
        return
    if user:  # oldin anonim bo'lgan — faqat ism so'raladi
        await ask_name(m, state)
        return
    await m.answer(ui.INTRO)
    await m.answer(ui.PREP, reply_markup=ui.kb([("▶️ Boshlash", "begin")]))


@router.callback_query(F.data == "begin")
async def begin(c: CallbackQuery, state: FSMContext):
    await c.answer()
    await ask_name(c.message, state)


@router.message(Onboard.name, F.text)
async def set_name(m: Message, state: FSMContext):
    name = " ".join(m.text.split())
    if not valid_full_name(name):
        await m.answer("Iltimos, <b>ism va familiyani</b> to'liq yozing (kamida 2 so'z, masalan: <i>Aliyev Vali</i>):")
        return
    await db.save_user(m.from_user.id, m.from_user.username or "", name, None, False)
    await state.clear()
    await m.answer(f"✅ Rahmat, <b>{esc(name)}</b>! Ro'yxatdan o'tdingiz.")
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
