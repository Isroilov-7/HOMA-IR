"""Matnlar va klaviaturalar — bot ko'rinishi bir joyda."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.config import settings

LEVEL_ICONS = ["🟢", "🟡", "🟠", "🔴"]
BAND_ICONS = {"past": "🟢", "ozgina yuqori": "🟡", "o'rta": "🟠", "yuqori": "🔴", "juda yuqori": "🔴"}

INTRO = (
    "🩺 <b>HOMA-IR • Metabolik skrining</b>\n\n"
    "Insulin rezistentligi va 2-tur diabet xavfini xalqaro tan olingan usullar bilan "
    "baholovchi ilmiy-amaliy bot.\n\n"
    "<b>Imkoniyatlar:</b>\n"
    "⚡ <b>Tezkor HOMA-IR</b>: glukoza va insulin bo'yicha 1 daqiqada natija\n"
    "🩺 <b>To'liq skrining</b>: FINDRISC (10 yillik diabet xavfi) + HOMA-IR\n"
    "📈 <b>Dinamika</b>: oldingi natijalar bilan solishtirish va grafik\n"
    "📄 <b>PDF hisobot</b>: shifokorga ko'rsatishga tayyor\n\n"
    "<b>Usullar:</b> Matthews (1985), Lindström &amp; Tuomilehto (2003), WHO, ADA.\n"
    "<i>Natija skrining hisoblanadi, tashxis emas.</i>"
)

CONSENT = (
    "🔒 <b>Ma'lumotlardan foydalanishga rozilik</b>\n\n"
    "• Kiritgan ma'lumotlaringiz natijani hisoblash va dinamikani ko'rsatish uchun saqlanadi.\n"
    "• Anonim ko'rinishda (ism va Telegram ID'siz) ilmiy tadqiqotda ishlatilishi mumkin: "
    "o'zbek populyatsiyasi uchun HOMA-IR chegaraviy qiymatini aniqlash.\n"
    "• Uchinchi shaxslarga berilmaydi. /export: ma'lumotlaringizni olish, "
    "/delete: to'liq o'chirish.\n\n"
    "Rozimisiz?"
)

ABOUT = (
    "ℹ️ <b>Bot haqida</b>\n\n"
    "<b>HOMA-IR</b> = glukoza (mmol/L) × insulin (μU/mL) / 22.5\n"
    "Matthews DR et al., <i>Diabetologia</i> 1985\n"
    "• &lt;2.0 normal • 2.0–2.49 chegara • 2.5–3.79 insulin rezistentligi • ≥3.8 yuqori\n\n"
    "<b>QUICKI</b>: &lt;0.339 insulin sezuvchanligi pasaygan (Katz, <i>JCEM</i> 2000)\n"
    "<b>HOMA-β</b>: β-hujayralar funksiyasi, %\n\n"
    "<b>FINDRISC</b>: 10 yillik 2-tur diabet xavfi (Lindström &amp; Tuomilehto, "
    "<i>Diabetes Care</i> 2003)\n"
    "• 0–6 past (~1%) • 7–11 ozgina (~4%) • 12–14 o'rta (~17%)\n"
    "• 15–20 yuqori (~33%) • 21–26 juda yuqori (~50%)\n\n"
    "<b>Tahlilga tayyorgarlik:</b> 8–12 soat och qoringa, ertalab, "
    "jismoniy zo'riqishsiz qon topshiring.\n\n"
    f"Aloqa: {settings.support}"
)

HELP = (
    "📖 <b>Buyruqlar</b>\n\n"
    "/quick: tezkor HOMA-IR (ism, yosh, glukoza, insulin)\n"
    "/screen: to'liq skrining (FINDRISC + HOMA-IR)\n"
    "/dynamics: natijalar dinamikasi va grafik\n"
    "/history: barcha natijalar va PDF\n"
    "/cancel: joriy so'rovnomani bekor qilish\n"
    "/export: ma'lumotlarim (JSON)\n"
    "/delete: ma'lumotlarimni o'chirish\n"
    "/about: usullar va me'yorlar"
)

DISCLAIMER = "⚠️ <i>Skrining natijasi, tashxis emas. Yuqori natijada endokrinologga murojaat qiling.</i>"


def kb(*rows: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t, callback_data=c) for t, c in row] for row in rows
    ])


def main_menu(user_id: int, reminders_on: bool = True) -> InlineKeyboardMarkup:
    rows = [
        [("⚡ Tezkor HOMA-IR", "quick:start"), ("🩺 To'liq skrining", "screen:start")],
        [("📈 Dinamikam", "dyn"), ("🗂 Natijalarim", "history")],
        [("📄 Oxirgi PDF", "pdf:last"),
         ("🔔 Eslatma: yoqilgan" if reminders_on else "🔕 Eslatma: o'chiq", "remind:toggle")],
        [("ℹ️ Bot haqida", "about"), ("🔒 Maxfiylik", "privacy")],
    ]
    if user_id in settings.admin_ids:
        rows.append([("👨‍💼 Admin panel", "adm:home")])
    return kb(*rows)


CANCEL_ROW = [("✖️ Bekor qilish", "cancel")]


def with_cancel(*rows: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    return kb(*rows, CANCEL_ROW)


def result_kb(screening_id: int) -> InlineKeyboardMarkup:
    return kb(
        [("📄 PDF hisobot", f"pdf:{screening_id}"), ("📈 Dinamika", "dyn")],
        [("🏠 Bosh menyu", "home")],
    )
