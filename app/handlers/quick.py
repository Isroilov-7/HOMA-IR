"""
⚡ Tezkor HOMA-IR: faqat ism-familiya, yosh, glukoza va insulin so'raladi.
Shifokor bir nechta bemorni ketma-ket kiritishi ham mumkin: har bemor
ismi bo'yicha alohida dinamikaga ega bo'ladi.
"""


from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app import db, ui
from app.analytics import verdict
from app.calculator import classify_glucose, glucose_from_input, quick_report
from app.utils import esc, parse_number

router = Router(name="quick")


class Quick(StatesGroup):
    name = State()
    age = State()
    glucose = State()
    insulin = State()


def same_patient(a: str | None, b: str | None) -> bool:
    return " ".join((a or "").lower().split()) == " ".join((b or "").lower().split())


async def previous_homa(user_id: int, patient_name: str, exclude_id: int) -> dict | None:
    for r in await db.user_screenings(user_id, limit=200):
        if r["id"] != exclude_id and r.get("homa_ir") is not None and same_patient(r.get("patient_name"), patient_name):
            return r
    return None


def compare_line(prev: dict | None, homa: float) -> str:
    if not prev:
        return ""
    pct = (homa - prev["homa_ir"]) / prev["homa_ir"] * 100 if prev["homa_ir"] else None
    icon, word = verdict(pct)
    pct_txt = f" ({pct:+.0f}%)".replace("-", "−") if pct is not None else ""
    return f"\n{icon} <b>Oldingi natija bilan:</b> {prev['homa_ir']:.2f} → {homa:.2f}{pct_txt}, {word}"


async def ask_glucose(target: Message, prefix: str = "") -> None:
    await target.answer(
        f"{prefix}🩸 Och qoringa <b>glukoza</b> qiymati?\n"
        "<i>mmol/L, masalan 5.4. mg/dL kiritsangiz (masalan 97), avtomatik o'giriladi.</i>",
        reply_markup=ui.with_cancel())


async def ask_insulin(target: Message, prefix: str = "") -> None:
    await target.answer(
        f"{prefix}💉 Och qoringa <b>insulin</b> qiymati?\n<i>μU/mL (mkME/ml), masalan 11.2</i>",
        reply_markup=ui.with_cancel())


def read_glucose(text: str | None) -> tuple[float | None, str]:
    v = parse_number(text)
    if v is None:
        return None, "Raqam kiriting, masalan 5.4"
    g, converted = glucose_from_input(v)
    if not 2.0 <= g <= 30.0:
        return None, "Glukoza 2–30 mmol/L (36–540 mg/dL) oralig'ida bo'lishi kerak."
    return g, (f"ℹ️ {v:g} mg/dL → {g:.2f} mmol/L" if converted else "")


def read_insulin(text: str | None) -> tuple[float | None, str]:
    v = parse_number(text)
    if v is None or not 0.5 <= v <= 300:
        return None, "Insulin 0.5–300 μU/mL oralig'ida bo'lishi kerak."
    return v, ""


@router.message(Command("quick"))
@router.callback_query(F.data == "quick:start")
async def quick_start(event: Message | CallbackQuery, state: FSMContext):
    msg = event.message if isinstance(event, CallbackQuery) else event
    if isinstance(event, CallbackQuery):
        await event.answer()
    user = await db.get_user(event.from_user.id)
    if not user:
        await msg.answer("Avval /start bosing va rozilik bering.")
        return
    await state.clear()
    rows = []
    if user.get("display_name") and not user.get("is_anonymous"):
        rows.append([(f"👤 {user['display_name'][:30]}", "qname:me")])
    rows.append([("🕶 Anonim", "qname:anon")])
    await msg.answer(
        "⚡ <b>Tezkor HOMA-IR</b> (4 ta savol)\n\n"
        "1/4. Bemorning <b>ism-familiyasini</b> yozing yoki tanlang:",
        reply_markup=ui.with_cancel(*rows))
    await state.set_state(Quick.name)


async def _set_name_and_ask_age(msg: Message, state: FSMContext, name: str) -> None:
    await state.update_data(patient_name=name)
    await msg.answer(f"👤 {esc(name)}\n\n2/4. <b>Yoshi</b> (yil)?", reply_markup=ui.with_cancel())
    await state.set_state(Quick.age)


@router.callback_query(F.data.startswith("qname:"), Quick.name)
async def quick_name_btn(c: CallbackQuery, state: FSMContext):
    user = await db.get_user(c.from_user.id)
    name = user["display_name"] if c.data == "qname:me" else (user or {}).get("display_name") or "Anonim"
    if c.data == "qname:anon" and not (user or {}).get("is_anonymous"):
        name = f"Anonim-{c.from_user.id % 10000:04d}"
    await c.answer()
    await _set_name_and_ask_age(c.message, state, name)


@router.message(Quick.name, F.text)
async def quick_name(m: Message, state: FSMContext):
    name = " ".join(m.text.split())
    if not 2 <= len(name) <= 60 or name.startswith("/"):
        await m.answer("Ism-familiya 2–60 belgi bo'lishi kerak:")
        return
    await _set_name_and_ask_age(m, state, name)


@router.message(Quick.age, F.text)
async def quick_age(m: Message, state: FSMContext):
    v = parse_number(m.text)
    if v is None or not 1 <= v <= 110 or v != int(v):
        await m.answer("Yoshni butun son bilan kiriting (1–110):")
        return
    await state.update_data(age=int(v))
    await ask_glucose(m, "3/4. ")
    await state.set_state(Quick.glucose)


@router.message(Quick.glucose, F.text)
async def quick_glucose(m: Message, state: FSMContext):
    g, note = read_glucose(m.text)
    if g is None:
        await m.answer(note)
        return
    if note:
        await m.answer(note)
    await state.update_data(glucose=g)
    await ask_insulin(m, "4/4. ")
    await state.set_state(Quick.insulin)


@router.message(Quick.insulin, F.text)
async def quick_insulin(m: Message, state: FSMContext):
    ins, note = read_insulin(m.text)
    if ins is None:
        await m.answer(note)
        return
    data = await state.get_data()
    await state.clear()
    g = data["glucose"]
    rep = quick_report(glucose=g, insulin=ins, age=data["age"])
    sid = await db.save_screening({
        "user_id": m.from_user.id, "kind": "quick", "patient_name": data["patient_name"],
        "age": data["age"], "fasting_glucose": round(g, 2), "fasting_insulin": ins,
        "homa_ir": rep["homa_ir"], "homa_beta": rep["homa_beta"], "quicki": rep["quicki"],
    })
    prev = await previous_homa(m.from_user.id, data["patient_name"], sid)
    await m.answer(format_quick(sid, data["patient_name"], data["age"], g, ins, rep)
                   + compare_line(prev, rep["homa_ir"]) + "\n\n" + ui.DISCLAIMER,
                   reply_markup=ui.result_kb(sid))


def format_quick(sid: int, name: str, age: int, g: float, ins: float, rep: dict) -> str:
    beta = f"{rep['homa_beta']:.0f}%" if rep["homa_beta"] is not None else "—"
    lines = [
        f"⚡ <b>Tezkor HOMA-IR natijasi №{sid}</b>",
        f"👤 {esc(name)} • {age} yosh",
        "",
        f"🩸 Glukoza: <b>{g:.2f}</b> mmol/L ({classify_glucose(g)})",
        f"💉 Insulin: <b>{ins:.1f}</b> μU/mL",
        "",
        f"{ui.LEVEL_ICONS[rep['level']]} <b>HOMA-IR: {rep['homa_ir']:.2f}</b>, {rep['homa_ir_class']}",
        f"📐 QUICKI: {rep['quicki']:.3f} ({rep['quicki_class']}) • HOMA-β: {beta}",
        "",
        "<b>Tavsiyalar:</b>",
    ]
    lines += [f"• {esc(r)}" for r in rep["recommendations"]]
    return "\n".join(lines)
