"""Matnlar va klaviaturalar — bot ko'rinishi bir joyda."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.config import settings

LEVEL_ICONS = ["🟢", "🟡", "🟠", "🔴"]
BAND_ICONS = {"past": "🟢", "ozgina yuqori": "🟡", "o'rta": "🟠", "yuqori": "🔴", "juda yuqori": "🔴"}

BOT_LINK = f"https://t.me/{settings.bot_username}"

# /start'da chiqadigan va boshqalarga ulashiladigan asosiy post (2026-10-13, egasi: oddiy xalq tilida,
# ko'p tugma chalg'itadi — 3 ta tugma). Glukoza majburiy, insulin tavsiya: hamma ham insulin topshirmaydi,
# lekin insulin bo'lsa natija ancha aniq — shu taklif qilinadi.
INTRO = (
    "🩸 <b>Qandingiz normal chiqdimi? Bu hali hammasi joyida degani emas.</b>\n\n"
    "Qandli diabet bir kunda paydo bo'lmaydi. Undan <b>5–10 yil oldin</b> organizm qandni yomon "
    "o'zlashtira boshlaydi — bu <b>insulin rezistentligi</b>. U og'rimaydi, oddiy qand tahlilida esa "
    "ko'pincha ko'rinmaydi.\n\n"
    "<b>Bu bot uni 1 daqiqada tekshiradi.</b> Laboratoriya qog'ozingizdan raqamlarni kiritasiz:\n"
    "🩸 <b>Glukoza (qand)</b> — kerak\n"
    "💉 <b>Insulin</b> — tavsiya etiladi ⭐\n\n"
    "💡 <b>Insulin raqami bo'lsa, natija ancha aniq chiqadi:</b> bot <b>HOMA-IR</b> ko'rsatkichini "
    "hisoblaydi va muammoni qand hali normal bo'lganda ham ko'rsatadi. Faqat qand bo'lsa ham "
    "boshlashingiz mumkin — dastlabki baho beraman.\n\n"
    "📊 Har safar natijangiz saqlanadi — keyingi tahlil bilan solishtirasiz.\n\n"
    "✅ Bepul  •  🔒 Maxfiy  •  🔬 Xalqaro usul (Matthews, 1985)\n"
    "<i>Bu tashxis emas. Natija yuqori chiqsa, shifokorga ko'rining.</i>\n\n"
    "👇 Boshlash uchun «🧪 Testni boshlash» ni bosing\n"
    f"👉 {BOT_LINK}"
)

# Ulashish tugmasi bosilganda tayyor matn (Telegram "share" oynasida chiqadi)
SHARE_TEXT = (
    "🩸 Qandingiz normal bo'lsa ham, insulin rezistentligi diabetdan 5–10 yil oldin boshlanadi. "
    "Bu bot qand va insulin tahlilingizdan uni (HOMA-IR) 1 daqiqada hisoblaydi va natijalaringizni saqlab boradi. "
    "Bepul va maxfiy 👇"
)

# Telegram qidiruvi va "Bu bot nima qila oladi?" oynasi uchun (BotFather o'rniga koddan o'rnatiladi).
# Odamlar "qand", "insulin", "diabet" deb qidiradi — shu so'zlar nomning boshida.
BOT_NAME = "Qand va insulin testi | Diabet xavfi | HOMA-IR"  # ≤ 64
BOT_SHORT_DESCRIPTION = (  # ≤ 120 — profil va ulashishda ko'rinadi
    "Qand va insulin tahlilingizdan insulin rezistentligi va diabet xavfini 1 daqiqada aniqlaydi. Bepul."
)
BOT_DESCRIPTION = (  # ≤ 512 — /start bosilmasdan oldin chiqadi
    "🩸 Qandingiz normal bo'lsa ham, insulin rezistentligi diabetdan 5–10 yil oldin boshlanadi.\n\n"
    "Bu bot laboratoriya tahlilingizdan:\n"
    "🧪 insulin rezistentligini (HOMA-IR) hisoblaydi\n"
    "📊 natijalaringizni saqlab, oldingisi bilan solishtiradi\n"
    "📄 shifokorga ko'rsatish uchun PDF beradi\n\n"
    "Kerak: qand (glukoza). Insulin bo'lsa — natija ancha aniq.\n"
    "Bepul • Maxfiy • Tashxis emas, skrining.\n\n"
    "Boshlash uchun «Start» ni bosing 👇"
)

def share_url() -> str:
    from urllib.parse import quote

    return f"https://t.me/share/url?url={quote(BOT_LINK, safe='')}&text={quote(SHARE_TEXT, safe='')}"


PREP = (
    "📌 <b>Boshlashdan oldin</b> — tahlilga to'g'ri tayyorgarlik (natija aniq chiqishi uchun)\n"
    "• 8–12 soat och qoringa, ertalab 8:00–10:00 da qon topshiring\n"
    "• Glukoza va insulinni <b>bitta qon namunasidan</b>, birga topshiring\n"
    "• Oldingi kun og'ir jismoniy mashq va spirtli ichimlik bo'lmasin\n"
    "• Dori qabul qilsangiz, tahlildan keyin iching\n\n"
    "<i>«Boshlash» tugmasini bosish bilan natijalaringiz maxfiy saqlanishiga va ilmiy "
    "tadqiqotda umumlashgan holda ishlatilishiga rozilik bildirasiz.</i>"
)

ASK_NAME = "✍️ <b>Ism va familiyangizni</b> yozing (masalan: <i>Aliyev Vali</i>):"

ABOUT_SIMPLE = (
    "❓ <b>Bu nima?</b>\n\n"
    "<b>Insulin</b> — qonimizdagi qandni hujayralarga kiritadigan gormon. Ba'zan organizm insulinga "
    "yomon javob bera boshlaydi: qandni hazm qilish uchun insulin ko'proq kerak bo'ladi. Bu "
    "<b>insulin rezistentligi</b>. Yillar o'tib u qandli diabetga, ortiqcha vaznga va bosimga olib keladi.\n\n"
    "<b>HOMA-IR</b> — shu holatni och qoringa topshirilgan <b>qand va insulin</b> tahlilidan hisoblaydigan "
    "xalqaro ko'rsatkich. Raqam qancha past bo'lsa, shuncha yaxshi.\n\n"
    "🟢 2.0 dan past — normal\n"
    "🟡 2.0–2.49 — chegara\n"
    "🟠 2.5–3.79 — insulin rezistentligi\n"
    "🔴 3.8 va yuqori — yuqori\n\n"
    "<b>Faqat qand bo'lsa:</b> dastlabki baho olasiz, lekin insulin rezistentligini aniqlab bo'lmaydi. "
    "Shuning uchun keyingi safar qand bilan birga <b>insulin</b>ni ham topshiring.\n\n"
    "<i>Bot tashxis qo'ymaydi. Natija yuqori chiqsa, endokrinologga murojaat qiling.</i>"
)

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
    "/quick: testni boshlash (ism, yosh, qand, insulin)\n"
    "/screen: to'liq skrining (FINDRISC + HOMA-IR)\n"
    "/dynamics: natijalar dinamikasi va grafik\n"
    "/history: barcha natijalar va PDF\n"
    "/cancel: joriy so'rovnomani bekor qilish\n"
    "/export: ma'lumotlarim (JSON)\n"
    "/delete: ma'lumotlarimni o'chirish\n"
    "/about: bu nima? (oddiy tilda)\n"
    "/methods: ilmiy usullar va me'yorlar"
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
    """Bosh menyu — faqat 3 ta tugma (2026-10-13, egasi: ko'p tugma odamni chalg'itadi). Qolgan bo'limlar
    (to'liq skrining, dinamika, eslatma, maxfiylik, ulashish) «❓ Bu nima?» va natija ekranlarida."""
    rows = [
        [("🧪 Testni boshlash", "quick:start")],
        [("📊 Natijalarim", "history"), ("❓ Bu nima?", "about")],
    ]
    if user_id in settings.admin_ids:
        rows.append([("👨‍💼 Admin panel", "adm:home")])
    return kb(*rows)


def about_kb(reminders_on: bool = True) -> InlineKeyboardMarkup:
    """«❓ Bu nima?» ekrani: qo'shimcha bo'limlar shu yerda (bosh menyuni yuklamaslik uchun)."""
    return kb(
        [("🧪 Testni boshlash", "quick:start")],
        [("🩺 To'liq skrining (diabet xavfi)", "screen:start")],
        [("🔔 Eslatma: yoqilgan" if reminders_on else "🔕 Eslatma: o'chiq", "remind:toggle"),
         ("🔒 Maxfiylik", "privacy")],
        [("📚 Usullar va me'yorlar", "methods"), ("📤 Ulashish", share_url())],
        [("🏠 Bosh menyu", "home")],
    )


def opt_kb(*rows: list[tuple[str, str]]) -> InlineKeyboardMarkup | None:
    """Savol tugmalari (bo'sh bo'lsa klaviaturasiz). Bekor qilish tugmasi yo'q: /cancel bor."""
    return kb(*rows) if rows else None


def result_kb(screening_id: int) -> InlineKeyboardMarkup:
    return kb(
        [("📄 PDF hisobot", f"pdf:{screening_id}"), ("📈 Dinamika", "dyn")],
        [("🏠 Bosh menyu", "home")],
    )
