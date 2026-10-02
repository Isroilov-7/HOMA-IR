"""Matnlar va klaviaturalar — bot ko'rinishi bir joyda."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.config import settings

LEVEL_ICONS = ["🟢", "🟡", "🟠", "🔴"]
BAND_ICONS = {"past": "🟢", "ozgina yuqori": "🟡", "o'rta": "🟠", "yuqori": "🔴", "juda yuqori": "🔴"}

BOT_LINK = f"https://t.me/{settings.bot_username}"

# /start'da chiqadigan va boshqalarga ulashiladigan asosiy post.
# Qoidasi: birinchi qator — ilmoq (hook), keyin muammo, keyin yechim, oxirida havola.
INTRO = (
    "🩸 <b>Qandingiz normal chiqdimi? Bu hali hammasi joyida degani emas.</b>\n\n"
    "2-tur diabet bir kunda paydo bo'lmaydi. Undan <b>5–10 yil oldin</b> organizm insulinga "
    "javob berishni susaytiradi: bu <b>insulin rezistentligi</b>. U og'rimaydi va oddiy qand "
    "tahlilida ko'pincha ko'rinmaydi.\n\n"
    "<b>HOMA-IR bot</b> uni 1 daqiqada hisoblab beradi 👇\n\n"
    "⚡ <b>Tezkor HOMA-IR</b>: glukoza + insulin → insulin rezistentligi bormi?\n"
    "🩺 <b>To'liq skrining</b>: FINDRISC, ya'ni 10 yil ichida diabet ehtimoli\n"
    "📈 <b>Dinamika</b>: har yangi tahlil oldingisi bilan solishtiriladi, grafik bilan\n"
    "📄 <b>PDF hisobot</b>: shifokorga ko'rsatishga tayyor\n"
    "🔔 <b>Eslatma</b>: qayta tekshiruv vaqtini o'zi eslatadi\n\n"
    "✅ Bepul  •  🔒 Maxfiy  •  🔬 Xalqaro usullar: HOMA-IR (Matthews, 1985), "
    "FINDRISC (Lindström &amp; Tuomilehto, 2003), ADA mezonlari\n"
    "<i>Natija skrining hisoblanadi, tashxis emas.</i>\n\n"
    "👨‍👩‍👧 Ota-onangiz va yaqinlaringizga ham yuboring: diabetni erta ko'rish uni "
    "oldini olishning eng oson yo'li.\n"
    f"👉 {BOT_LINK}"
)

# Ulashish tugmasi bosilganda tayyor matn (Telegram "share" oynasida chiqadi)
SHARE_TEXT = (
    "🩸 Qandingiz normal bo'lsa ham, insulin rezistentligi diabetdan 5–10 yil oldin boshlanadi. "
    "Bu bot glukoza va insulin bo'yicha HOMA-IR ni 1 daqiqada hisoblaydi, diabet xavfini "
    "baholaydi va natijalaringizni kuzatib boradi. Bepul va maxfiy 👇"
)

# Telegram qidiruvi va "Bu bot nima qila oladi?" oynasi uchun (BotFather o'rniga koddan o'rnatiladi)
BOT_NAME = "HOMA-IR: insulin rezistentligi va diabet testi"  # ≤ 64
BOT_SHORT_DESCRIPTION = (  # ≤ 120 — profil va ulashishda ko'rinadi
    "HOMA-IR kalkulyator: insulin rezistentligi, diabet xavfi (FINDRISC), natijalar dinamikasi. Bepul."
)
BOT_DESCRIPTION = (  # ≤ 512 — /start bosilmasdan oldin chiqadi
    "🩸 Qandingiz normal bo'lsa ham, insulin rezistentligi diabetdan 5–10 yil oldin boshlanadi.\n\n"
    "Bu bot:\n"
    "⚡ glukoza va insulin bo'yicha HOMA-IR, QUICKI va HOMA-β ni hisoblaydi\n"
    "🩺 FINDRISC bilan 10 yillik 2-tur diabet xavfini baholaydi\n"
    "📈 natijalaringizni solishtirib, grafik va PDF hisobot beradi\n\n"
    "Bepul • Maxfiy • Xalqaro usullar (Matthews 1985, FINDRISC, ADA).\n"
    "Skrining vositasi, tashxis emas.\n\n"
    "Boshlash uchun «Start» ni bosing 👇"
)


def share_url() -> str:
    from urllib.parse import quote

    return f"https://t.me/share/url?url={quote(BOT_LINK, safe='')}&text={quote(SHARE_TEXT, safe='')}"


PREP = (
    "📌 <b>Tahlilga to'g'ri tayyorgarlik</b> (natija aniq chiqishi uchun)\n"
    "• 8–12 soat och qoringa, ertalab 8:00–10:00 da qon topshiring\n"
    "• Glukoza va insulinni <b>bitta qon namunasidan</b>, birga topshiring\n"
    "• Oldingi kun og'ir jismoniy mashq va spirtli ichimlik bo'lmasin\n"
    "• Dori qabul qilsangiz, tahlildan keyin iching\n\n"
    "<i>«Boshlash» tugmasini bosish bilan natijalaringiz maxfiy saqlanishiga va ilmiy "
    "tadqiqotda umumlashgan holda ishlatilishiga rozilik bildirasiz.</i>"
)

ASK_NAME = "✍️ <b>Ism va familiyangizni</b> yozing (masalan: <i>Aliyev Vali</i>):"

NO_INSULIN_HOOK = (
    "🧪 <b>HOMA-IR hisoblanmadi: insulin tahlili kerak.</b>\n"
    "Glukoza normal bo'lsa ham, insulin rezistentligi yillar davomida sezilmasdan kechadi. "
    "HOMA-IR uni diabetdan <b>5–10 yil oldin</b> ko'rsatib beradi.\n\n"
    "👉 Keyingi safar laboratoriyada <b>och qoringa glukoza + insulin</b>ni birga topshiring "
    "(bitta qon namunasi yetadi). Natijani shu yerga kiritsangiz, to'liq xulosa va oldingi "
    "glukozangiz bilan solishtirishni beraman.\n"
    "🔔 {days} kundan keyin eslatib qo'yaman."
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


def _button(text: str, action: str) -> InlineKeyboardButton:
    """action 'https://...' bo'lsa — havola tugmasi, aks holda callback."""
    if action.startswith("https://"):
        return InlineKeyboardButton(text=text, url=action)
    return InlineKeyboardButton(text=text, callback_data=action)


def kb(*rows: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[_button(t, a) for t, a in row] for row in rows])


def main_menu(user_id: int, reminders_on: bool = True) -> InlineKeyboardMarkup:
    rows = [
        [("⚡ Tezkor HOMA-IR", "quick:start"), ("🩺 To'liq skrining", "screen:start")],
        [("📈 Dinamikam", "dyn"), ("🗂 Natijalarim", "history")],
        [("📄 Oxirgi PDF", "pdf:last"),
         ("🔔 Eslatma: yoqilgan" if reminders_on else "🔕 Eslatma: o'chiq", "remind:toggle")],
        [("ℹ️ Bot haqida", "about"), ("🔒 Maxfiylik", "privacy")],
        [("📤 Do'stlarga ulashish", share_url())],
    ]
    if user_id in settings.admin_ids:
        rows.append([("👨‍💼 Admin panel", "adm:home")])
    return kb(*rows)


def opt_kb(*rows: list[tuple[str, str]]) -> InlineKeyboardMarkup | None:
    """Savol tugmalari (bo'sh bo'lsa klaviaturasiz). Bekor qilish tugmasi yo'q: /cancel bor."""
    return kb(*rows) if rows else None


def result_kb(screening_id: int) -> InlineKeyboardMarkup:
    return kb(
        [("📄 PDF hisobot", f"pdf:{screening_id}"), ("📈 Dinamika", "dyn")],
        [("🏠 Bosh menyu", "home")],
    )
