"""🗂 Natijalar tarixi, 📈 dinamika (grafik bilan) va 📄 PDF."""

import asyncio
import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from app import charts, db, ui
from app.analytics import format_dynamics
from app.handlers.quick import same_patient
from app.reports.patient_pdf import build_pdf_report
from app.utils import esc, fmt_dt

router = Router(name="history")
log = logging.getLogger(__name__)


def patients(rows: list[dict]) -> list[str]:
    """Foydalanuvchi kiritgan bemorlar (yangi → eski), takrorlarsiz."""
    seen: list[str] = []
    for r in rows:
        name = r.get("patient_name") or "—"
        if not any(same_patient(name, s) for s in seen):
            seen.append(name)
    return seen


def rows_for(rows: list[dict], name: str) -> list[dict]:
    return [r for r in rows if same_patient(r.get("patient_name") or "—", name)]


@router.message(Command("history"))
@router.callback_query(F.data == "history")
async def history(event: Message | CallbackQuery):
    msg = event.message if isinstance(event, CallbackQuery) else event
    if isinstance(event, CallbackQuery):
        await event.answer()
    rows = await db.user_screenings(event.from_user.id, limit=10)
    if not rows:
        await msg.answer("Hozircha natija yo'q.", reply_markup=ui.main_menu(event.from_user.id))
        return
    lines = ["🗂 <b>So'nggi natijalar</b> (PDF uchun tugmani bosing)\n"]
    buttons = []
    for r in rows:
        kind = "⚡" if r.get("kind") == "quick" else "🩺"
        homa = f"HOMA {r['homa_ir']:.2f}" if r.get("homa_ir") is not None else "HOMA —"
        fr = f" • FINDRISC {r['findrisc']}" if r.get("findrisc") is not None else ""
        lines.append(f"{kind} №{r['id']} • {fmt_dt(r['created_at'])} • {esc(r.get('patient_name') or '—')}"
                     f" • {homa}{fr}")
        buttons.append((f"📄 №{r['id']}", f"pdf:{r['id']}"))
    rows_kb = [buttons[i:i + 3] for i in range(0, len(buttons), 3)] + [[("🏠 Bosh menyu", "home")]]
    await msg.answer("\n".join(lines), reply_markup=ui.kb(*rows_kb))


@router.message(Command("dynamics"))
@router.callback_query(F.data == "dyn")
async def dynamics(event: Message | CallbackQuery):
    msg = event.message if isinstance(event, CallbackQuery) else event
    if isinstance(event, CallbackQuery):
        await event.answer()
    rows = await db.user_screenings(event.from_user.id, limit=500)
    names = patients(rows)
    if len(names) > 1:
        await msg.answer(
            "📈 Bir nechta bemor kiritilgan. Kimning dinamikasini ko'ramiz?",
            reply_markup=ui.kb(*[[(n[:40], f"dyn:{i}")] for i, n in enumerate(names[:12])],
                               [("🏠 Bosh menyu", "home")]))
        return
    await send_dynamics(msg, rows, names[0] if names else "")


@router.callback_query(F.data.startswith("dyn:"))
async def dynamics_for(c: CallbackQuery):
    await c.answer()
    rows = await db.user_screenings(c.from_user.id, limit=500)
    names = patients(rows)
    idx = int(c.data.split(":")[1])
    if idx >= len(names):
        await c.message.answer("Ro'yxat yangilandi, qaytadan tanlang.")
        return
    await send_dynamics(c.message, rows_for(rows, names[idx]), names[idx])


async def send_dynamics(msg: Message, rows: list[dict], name: str) -> None:
    text = format_dynamics(rows)
    if name and len(rows) > 0:
        text = text.replace("📈 <b>Mening dinamikam</b>", f"📈 <b>Dinamika: {esc(name)}</b>", 1)
    pdf_cb = f"pdf:{rows[0]['id']}" if rows else "pdf:last"
    await msg.answer(text, reply_markup=ui.kb([("📄 PDF (grafik bilan)", pdf_cb), ("🏠 Bosh menyu", "home")]))
    png = await asyncio.to_thread(charts.patient_trend_png, rows, name)
    if png:
        await msg.answer_photo(BufferedInputFile(png, "dinamika.png"),
                               caption="Rangli zonalar: yashil — normal, sariq — chegara, "
                                       "to'q sariq — insulin rezistentligi, qizil — yuqori.")


@router.callback_query(F.data.startswith("pdf:"))
async def send_pdf(c: CallbackQuery):
    target = c.data.split(":")[1]
    sid = None if target == "last" else int(target)
    row = await db.get_screening(c.from_user.id, sid)
    if not row:
        await c.answer("Natija topilmadi.", show_alert=True)
        return
    await c.answer("PDF tayyorlanmoqda…")
    user = await db.get_user(c.from_user.id)
    all_rows = await db.user_screenings(c.from_user.id, limit=500)
    # Dinamika — shu bemorning shu natijagacha bo'lgan yozuvlari
    hist = [r for r in rows_for(all_rows, row.get("patient_name") or "—") if r["id"] <= row["id"]]
    trend = await asyncio.to_thread(charts.patient_trend_png, hist) if len(hist) >= 2 else None
    pdf = await asyncio.to_thread(build_pdf_report, user, row, hist, trend)
    await c.message.answer_document(
        BufferedInputFile(pdf, filename=f"HOMA-IR_hisobot_{row['id']}.pdf"),
        caption=f"📄 Hisobot №{row['id']} • {fmt_dt(row['created_at'])}")
