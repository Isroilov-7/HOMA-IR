"""
👨‍💼 Admin panel (faqat ADMIN_IDS): umumiy ko'rsatkichlar, tadqiqot statistikasi,
dissertatsiya PDF, Excel/CSV eksport, grafiklar va zaxira nusxa.

Og'ir hisob-kitoblar (scipy, matplotlib, reportlab) asyncio.to_thread da —
bot boshqa foydalanuvchilarga javob berishda davom etadi.
"""

import asyncio
import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, CallbackQuery, InputMediaPhoto, Message

from app import backup, charts, db, stats, ui
from app.config import settings
from app.reports.research_pdf import build_research_pdf
from app.reports.research_xlsx import build_csv, build_xlsx
from app.utils import TASHKENT

router = Router(name="admin")
router.message.filter(F.from_user.id.in_(settings.admin_ids))
router.callback_query.filter(F.from_user.id.in_(settings.admin_ids))
log = logging.getLogger(__name__)


def admin_kb():
    return ui.kb(
        [("🔬 Tadqiqot statistikasi", "adm:stats")],
        [("📄 Dissertatsiya PDF", "adm:pdf"), ("📗 Excel", "adm:xlsx")],
        [("🧾 CSV (SPSS/R)", "adm:csv"), ("📉 Grafiklar", "adm:charts")],
        [("💾 Zaxira nusxa", "adm:backup"), ("🔄 Yangilash", "adm:home")],
        [("🏠 Bosh menyu", "home")],
    )


async def overview_text() -> str:
    c = await db.overview_counts()
    return (
        "👨‍💼 <b>Admin panel</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{c['users']}</b> (7 kunda +{c['new_users_week']})\n"
        f"📋 Jami natijalar: <b>{c['screenings']}</b>\n"
        f"   🩺 to'liq: {c['full']} • ⚡ tezkor: {c['quick']}\n"
        f"   🧪 HOMA-IR bilan: {c['with_labs']}\n"
        f"🔁 Takroriy o'lchovli bemorlar: {c['repeat_patients']}\n"
        f"📅 24 soatda: {c['today']} • 7 kunda: {c['week']}\n\n"
        f"<i>{datetime.now(TASHKENT).strftime('%d.%m.%Y %H:%M')}</i>"
    )


@router.message(Command("admin"))
@router.callback_query(F.data == "adm:home")
async def admin_home(event: Message | CallbackQuery):
    msg = event.message if isinstance(event, CallbackQuery) else event
    if isinstance(event, CallbackQuery):
        await event.answer()
    await msg.answer(await overview_text(), reply_markup=admin_kb())


async def _report():
    rows = await db.all_screenings()
    rep = await asyncio.to_thread(stats.cohort_report, rows)
    return rows, rep


@router.callback_query(F.data == "adm:stats")
async def admin_stats(c: CallbackQuery):
    await c.answer("Hisoblanmoqda…")
    rows, rep = await _report()
    if not rows:
        await c.message.answer("Hali ma'lumot yo'q.")
        return
    await c.message.answer(stats.format_summary(rep), reply_markup=admin_kb())


@router.callback_query(F.data == "adm:pdf")
async def admin_pdf(c: CallbackQuery):
    await c.answer("Dissertatsiya hisoboti tayyorlanmoqda…")
    rows, rep = await _report()
    if not rows:
        await c.message.answer("Hali ma'lumot yo'q.")
        return
    pdf = await asyncio.to_thread(build_research_pdf, rows, rep)
    stamp = datetime.now(TASHKENT).strftime("%Y%m%d")
    await c.message.answer_document(
        BufferedInputFile(pdf, filename=f"HOMA-IR_kogorta_hisoboti_{stamp}.pdf"),
        caption="📄 Kogorta hisoboti: asosiy natijalar, metodlar, 7 ta jadval, rasmlar, adabiyotlar.")


@router.callback_query(F.data == "adm:xlsx")
async def admin_xlsx(c: CallbackQuery):
    await c.answer("Excel tayyorlanmoqda…")
    rows, rep = await _report()
    data = await asyncio.to_thread(build_xlsx, rows, rep)
    stamp = datetime.now(TASHKENT).strftime("%Y%m%d")
    await c.message.answer_document(
        BufferedInputFile(data, filename=f"HOMA-IR_tadqiqot_{stamp}.xlsx"),
        caption="📗 Anonim ma'lumotlar + 1-jadval, IR prevalentligi, korrelyatsiya, cutoff, dinamika, lug'at.")


@router.callback_query(F.data == "adm:csv")
async def admin_csv(c: CallbackQuery):
    await c.answer()
    rows = await db.all_screenings()
    data = build_csv(rows)
    stamp = datetime.now(TASHKENT).strftime("%Y%m%d")
    await c.message.answer_document(
        BufferedInputFile(data, filename=f"HOMA-IR_anonim_{stamp}.csv"),
        caption="🧾 Anonim CSV (UTF-8): SPSS, R, Python uchun. Ism va Telegram ID yo'q.")


@router.callback_query(F.data == "adm:charts")
async def admin_charts(c: CallbackQuery):
    await c.answer("Grafiklar chizilmoqda…")
    rows, rep = await _report()
    labs = stats.baseline_rows(rows, require_labs=True)
    corr = {x["key"]: x for x in rep["correlations"]}

    def build():
        return [p for p in (
            charts.homa_histogram_png(stats._vals(labs, "homa_ir"), rep["reference"].get("p75")),
            charts.prevalence_bars_png(rep["ir_by_bmi"]["items"], "IR ulushi: BMI toifalari"),
            charts.prevalence_bars_png(rep["ir_by_age"]["items"], "IR ulushi: yosh guruhlari"),
            charts.scatter_png(labs, "bmi", "BMI", corr["bmi"]["rho"], stats.fmt_p(corr["bmi"]["p"])),
            charts.findrisc_bars_png(rep["findrisc_bands"]),
        ) if p]

    pngs = await asyncio.to_thread(build)
    if not pngs:
        await c.message.answer("Grafik uchun ma'lumot yetarli emas (kamida 3–5 ta laborator natija kerak).")
        return
    await c.message.answer_media_group(
        [InputMediaPhoto(media=BufferedInputFile(p, f"grafik_{i}.png")) for i, p in enumerate(pngs, 1)])


@router.callback_query(F.data == "adm:backup")
async def admin_backup(c: CallbackQuery):
    await c.answer("Zaxira nusxa olinmoqda…")
    path = await asyncio.to_thread(backup.make_backup)
    await c.message.answer_document(
        BufferedInputFile(path.read_bytes(), filename=path.name),
        caption=f"💾 Baza zaxirasi ({path.stat().st_size / 1024:.0f} KB). Serverda ham saqlandi: "
                f"<code>{path}</code>\n⚠️ Tibbiy ma'lumot: faylni boshqalarga yubormang.")
