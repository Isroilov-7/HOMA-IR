"""🩺 To'liq skrining: FINDRISC (8 savol) + ixtiyoriy glukoza/insulin (HOMA-IR)."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app import db, ui
from app.calculator import (
    calculate_bmi,
    calculate_findrisc,
    calculate_whtr,
    classify_bmi,
    classify_glucose,
    classify_waist,
    classify_whtr,
    combined_risk_report,
    quick_report,
)
from app.handlers.quick import ask_glucose, ask_insulin, compare_line, previous_homa, read_glucose, read_insulin
from app.utils import esc, parse_number

router = Router(name="screening")
TOTAL = 10


class Screen(StatesGroup):
    sex = State()
    age = State()
    weight = State()
    height = State()
    waist = State()
    activity = State()
    vegetables = State()
    bp_meds = State()
    high_glucose = State()
    family = State()
    glucose = State()
    insulin = State()


def step(n: int, text: str) -> str:
    return f"<b>{n}/{TOTAL}.</b> {text}"


YES_NO = lambda p: ui.with_cancel([("✅ Ha", f"{p}:1"), ("❌ Yo'q", f"{p}:0")])  # noqa: E731


@router.message(Command("screen"))
@router.callback_query(F.data == "screen:start")
async def screen_start(event: Message | CallbackQuery, state: FSMContext):
    msg = event.message if isinstance(event, CallbackQuery) else event
    if isinstance(event, CallbackQuery):
        await event.answer()
    if not await db.get_user(event.from_user.id):
        await msg.answer("Avval /start bosing va rozilik bering.")
        return
    await state.clear()
    await msg.answer(
        "🩺 <b>To'liq skrining</b>: 8 ta FINDRISC savoli + 2 ta ixtiyoriy laborator ko'rsatkich "
        "(~2 daqiqa)\n\n" + step(1, "Jinsingiz:"),
        reply_markup=ui.with_cancel([("👨 Erkak", "sex:M"), ("👩 Ayol", "sex:F")]))
    await state.set_state(Screen.sex)


@router.callback_query(F.data.startswith("sex:"), Screen.sex)
async def set_sex(c: CallbackQuery, state: FSMContext):
    await state.update_data(sex=c.data.split(":")[1])
    await c.message.edit_text(step(2, "Yoshingiz (yil)?"), reply_markup=ui.with_cancel())
    await state.set_state(Screen.age)
    await c.answer()


async def _number(m: Message, lo: float, hi: float, err: str):
    v = parse_number(m.text)
    if v is None or not lo <= v <= hi:
        await m.answer(err)
        return None
    return v


@router.message(Screen.age, F.text)
async def set_age(m: Message, state: FSMContext):
    v = await _number(m, 15, 100, "15–100 oralig'ida yosh kiriting:")
    if v is None:
        return
    await state.update_data(age=int(v))
    await m.answer(step(3, "Vazningiz (kg)? Masalan 72.5"), reply_markup=ui.with_cancel())
    await state.set_state(Screen.weight)


@router.message(Screen.weight, F.text)
async def set_weight(m: Message, state: FSMContext):
    v = await _number(m, 30, 300, "30–300 kg oralig'ida kiriting:")
    if v is None:
        return
    await state.update_data(weight=v)
    await m.answer(step(4, "Bo'yingiz (sm)? Masalan 170"), reply_markup=ui.with_cancel())
    await state.set_state(Screen.height)


@router.message(Screen.height, F.text)
async def set_height(m: Message, state: FSMContext):
    v = await _number(m, 120, 230, "120–230 sm oralig'ida kiriting:")
    if v is None:
        return
    await state.update_data(height=v)
    await m.answer(step(5, "Bel aylanasi (sm)?\n<i>Kindik sathida, nafas chiqargandan keyin o'lchang.</i>"),
                   reply_markup=ui.with_cancel())
    await state.set_state(Screen.waist)


@router.message(Screen.waist, F.text)
async def set_waist(m: Message, state: FSMContext):
    v = await _number(m, 50, 200, "50–200 sm oralig'ida kiriting:")
    if v is None:
        return
    await state.update_data(waist=v)
    await m.answer(step(6, "Har kuni kamida <b>30 daqiqa</b> jismoniy faollik (yurish, sport) bormi?"),
                   reply_markup=YES_NO("act"))
    await state.set_state(Screen.activity)


@router.callback_query(F.data.startswith("act:"), Screen.activity)
async def set_activity(c: CallbackQuery, state: FSMContext):
    await state.update_data(activity_yes=c.data.endswith("1"))
    await c.message.edit_text(step(7, "Har kuni sabzavot yoki meva iste'mol qilasizmi?"),
                              reply_markup=YES_NO("veg"))
    await state.set_state(Screen.vegetables)
    await c.answer()


@router.callback_query(F.data.startswith("veg:"), Screen.vegetables)
async def set_veg(c: CallbackQuery, state: FSMContext):
    await state.update_data(veg_daily=c.data.endswith("1"))
    await c.message.edit_text(step(8, "Qon bosimi uchun muntazam dori qabul qilasizmi (yoki qilganmisiz)?"),
                              reply_markup=YES_NO("bp"))
    await state.set_state(Screen.bp_meds)
    await c.answer()


@router.callback_query(F.data.startswith("bp:"), Screen.bp_meds)
async def set_bp(c: CallbackQuery, state: FSMContext):
    await state.update_data(bp_meds=c.data.endswith("1"))
    await c.message.edit_text(
        step(9, "Ilgari (tekshiruvda, kasallikda, homiladorlikda) qonda <b>yuqori qand</b> aniqlanganmi?"),
        reply_markup=YES_NO("hg"))
    await state.set_state(Screen.high_glucose)
    await c.answer()


@router.callback_query(F.data.startswith("hg:"), Screen.high_glucose)
async def set_hg(c: CallbackQuery, state: FSMContext):
    await state.update_data(high_glucose_hist=c.data.endswith("1"))
    await c.message.edit_text(
        step(10, "Qarindoshlaringizda <b>diabet</b> bormi?"),
        reply_markup=ui.with_cancel(
            [("Yo'q", "fam:none")],
            [("Bobo/buvi, amaki/tog'a, xola/amma", "fam:second")],
            [("Ota-ona, aka-uka, opa-singil, farzand", "fam:first")],
        ))
    await state.set_state(Screen.family)
    await c.answer()


@router.callback_query(F.data.startswith("fam:"), Screen.family)
async def set_family(c: CallbackQuery, state: FSMContext):
    await state.update_data(family_hx=c.data.split(":")[1])
    await c.answer()
    await c.message.edit_text(
        "✅ FINDRISC savollari tugadi.\n\n"
        "🧪 <b>Laborator ko'rsatkichlar (ixtiyoriy)</b>\n"
        "Och qoringa glukoza va insulin bo'lsa, HOMA-IR ham hisoblanadi.",
        reply_markup=ui.kb([("🧪 Kiritaman", "lab:yes")], [("⏭ O'tkazib yuborish", "lab:skip")]))
    await state.set_state(Screen.glucose)


@router.callback_query(F.data == "lab:yes", Screen.glucose)
async def lab_yes(c: CallbackQuery, state: FSMContext):
    await c.answer()
    await ask_glucose(c.message)


@router.callback_query(F.data == "lab:skip", Screen.glucose)
async def lab_skip(c: CallbackQuery, state: FSMContext):
    await c.answer()
    await finalize(c.message, state, c.from_user.id)


@router.message(Screen.glucose, F.text)
async def set_glucose(m: Message, state: FSMContext):
    g, note = read_glucose(m.text)
    if g is None:
        await m.answer(note)
        return
    if note:
        await m.answer(note)
    await state.update_data(fasting_glucose=round(g, 2))
    await ask_insulin(m)
    await state.set_state(Screen.insulin)


@router.message(Screen.insulin, F.text)
async def set_insulin(m: Message, state: FSMContext):
    ins, note = read_insulin(m.text)
    if ins is None:
        await m.answer(note)
        return
    await state.update_data(fasting_insulin=ins)
    await finalize(m, state, m.from_user.id)


async def finalize(msg: Message, state: FSMContext, user_id: int) -> None:
    data = await state.get_data()
    await state.clear()
    user = await db.get_user(user_id)
    bmi = calculate_bmi(data["weight"], data["height"])
    whtr = calculate_whtr(data["waist"], data["height"])
    g, ins = data.get("fasting_glucose"), data.get("fasting_insulin")
    lab = quick_report(glucose=g, insulin=ins) if g and ins else None

    score, band = calculate_findrisc(
        age=data["age"], bmi=bmi, waist=data["waist"], sex=data["sex"],
        activity_yes=data["activity_yes"], veg_daily=data["veg_daily"],
        bp_meds=data["bp_meds"], high_glucose_hist=data["high_glucose_hist"],
        family_hx=data["family_hx"],
    )
    report = combined_risk_report(findrisc=score, findrisc_band=band,
                                  homa_ir=lab["homa_ir"] if lab else None,
                                  bmi=bmi, waist=data["waist"], sex=data["sex"], glucose=g)
    name = (user or {}).get("display_name") or "—"
    sid = await db.save_screening({
        "user_id": user_id, "kind": "full", "patient_name": name,
        **{k: data.get(k) for k in ("sex", "age", "weight", "height", "waist", "activity_yes",
                                     "veg_daily", "bp_meds", "high_glucose_hist", "family_hx",
                                     "fasting_glucose", "fasting_insulin")},
        "bmi": bmi, "whtr": whtr,
        "homa_ir": lab["homa_ir"] if lab else None,
        "homa_beta": lab["homa_beta"] if lab else None,
        "quicki": lab["quicki"] if lab else None,
        "findrisc": score, "findrisc_band": band, "combined_band": report["combined_band"],
    })

    lines = [
        f"🏁 <b>To'liq skrining natijasi №{sid}</b>",
        f"👤 {esc(name)} • {data['age']} yosh • {'erkak' if data['sex'] == 'M' else 'ayol'}",
        "",
        f"{ui.BAND_ICONS.get(band, '⚪')} <b>FINDRISC: {score}/26</b>, {band}",
        f"    10 yil ichida 2-tur diabet ehtimoli: {report['ten_year_risk']}",
    ]
    if lab:
        lines += [
            f"{ui.LEVEL_ICONS[lab['level']]} <b>HOMA-IR: {lab['homa_ir']:.2f}</b>, {lab['homa_ir_class']}",
            f"    QUICKI {lab['quicki']:.3f} • glukoza {g:.2f} ({classify_glucose(g)})",
        ]
    elif g:
        lines.append(f"🩸 Glukoza: {g:.2f} mmol/L ({classify_glucose(g)})")
    lines += [
        f"⚖️ BMI: {bmi:.1f} ({classify_bmi(bmi)})",
        f"📏 Bel: {data['waist']:.0f} sm ({classify_waist(data['sex'], data['waist'])}) • "
        f"bel/bo'y {whtr:.2f} ({classify_whtr(whtr)})",
        "",
        f"<b>Umumiy xulosa:</b> {esc(report['combined_band'])}",
        "",
        "<b>Tavsiyalar:</b>",
    ]
    lines += [f"• {esc(r)}" for r in report["recommendations"]]
    if lab:
        prev = await previous_homa(user_id, name, sid)
        cmp = compare_line(prev, lab["homa_ir"])
        if cmp:
            lines.append(cmp)
    lines += ["", ui.DISCLAIMER]
    await msg.answer("\n".join(lines), reply_markup=ui.result_kb(sid))
