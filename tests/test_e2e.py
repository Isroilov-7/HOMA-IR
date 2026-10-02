"""
Bot oqimlari boshidan oxirigacha: Telegram'ga ulanmasdan (soxta sessiya).
Har bir chaqiruv (sendMessage, sendDocument…) yozib olinadi va tekshiriladi.
"""

from datetime import datetime

import pytest
from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.methods import (
    AnswerCallbackQuery,
    EditMessageReplyMarkup,
    EditMessageText,
    SendDocument,
    SendMediaGroup,
    SendMessage,
    SendPhoto,
    TelegramMethod,
)
from aiogram.types import CallbackQuery, Chat, Message, Update, User

from app import db
from app.handlers import build_router
from conftest import assert_telegram_html

USER_ID = 1  # conftest: ADMIN_IDS=1
CHAT = Chat(id=USER_ID, type="private")
FROM = User(id=USER_ID, is_bot=False, first_name="Test")


class FakeSession(BaseSession):
    def __init__(self):
        super().__init__()
        self.calls: list[TelegramMethod] = []

    async def make_request(self, bot, method, timeout=None):
        self.calls.append(method)
        assert_telegram_html(getattr(method, "text", None))
        assert_telegram_html(getattr(method, "caption", None))
        msg = Message(message_id=len(self.calls), date=datetime.now(), chat=CHAT,
                      text=getattr(method, "text", None))
        if isinstance(method, SendMediaGroup):
            return [msg]
        if isinstance(method, (SendMessage, SendDocument, SendPhoto)):
            return msg
        if isinstance(method, (EditMessageText, EditMessageReplyMarkup)):
            return msg
        return True

    async def stream_content(self, *a, **k):  # pragma: no cover
        yield b""

    async def close(self):
        pass


_DP: Dispatcher | None = None


def dispatcher() -> Dispatcher:
    """Routerlar modul darajasida — bitta dispatcherga faqat bir marta ulanadi."""
    global _DP
    if _DP is None:
        _DP = Dispatcher(storage=MemoryStorage())
        _DP.include_router(build_router())
    _DP.fsm.storage = MemoryStorage()  # har test toza FSM holati bilan
    return _DP


class Harness:
    def __init__(self):
        self.session = FakeSession()
        self.bot = Bot("123:TEST", session=self.session)
        self.dp = dispatcher()
        self.uid = 0

    def _next(self):
        self.uid += 1
        return self.uid

    async def text(self, text: str):
        start = len(self.session.calls)
        msg = Message(message_id=self._next(), date=datetime.now(), chat=CHAT, from_user=FROM, text=text)
        await self.dp.feed_update(self.bot, Update(update_id=self._next(), message=msg))
        return self.session.calls[start:]

    async def click(self, data: str):
        start = len(self.session.calls)
        base = Message(message_id=self._next(), date=datetime.now(), chat=CHAT, text="x")
        cq = CallbackQuery(id=str(self._next()), from_user=FROM, chat_instance="c", data=data, message=base)
        await self.dp.feed_update(self.bot, Update(update_id=self._next(), callback_query=cq))
        return self.session.calls[start:]


def texts(calls):
    return "\n".join(c.text for c in calls if isinstance(c, (SendMessage, EditMessageText)))


def docs(calls):
    return [c for c in calls if isinstance(c, SendDocument)]


@pytest.fixture
async def h(tmp_db):
    await db.init_db()
    return Harness()


async def test_onboarding_intro_prep_and_mandatory_full_name(h):
    out = texts(await h.text("/start"))
    assert "Metabolik skrining" in out and "Tahlilga to'g'ri tayyorgarlik" in out
    assert "Rozimisiz" not in out and "Ma'lumotlaringiz" not in out  # eski rozilik bloki olib tashlangan
    assert "Ism va familiyangizni" in texts(await h.click("begin"))
    assert "to'liq yozing" in texts(await h.text("Vali"))       # bitta so'z — qabul qilinmaydi
    assert "to'liq yozing" in texts(await h.text("Ali 123"))    # raqam — qabul qilinmaydi
    assert "Ro'yxatdan o'tdingiz" in texts(await h.text("Aliyev Vali"))
    user = await db.get_user(USER_ID)
    assert user["display_name"] == "Aliyev Vali" and user["is_anonymous"] == 0


async def test_old_anonymous_user_is_asked_for_name(h):
    await db.save_user(USER_ID, "u", "Anonim-0001", None, True)
    assert "Ism va familiyangizni" in texts(await h.text("/start"))
    await h.text("Karimov Olim")
    assert (await db.get_user(USER_ID))["is_anonymous"] == 0
    await db.save_user(USER_ID, "u", "Anonim-0001", None, True)
    assert "Ism va familiyangizni" in texts(await h.click("quick:start"))


async def _register(h):
    await h.text("/start")
    await h.click("begin")
    await h.text("Aliyev Vali")


async def test_questions_have_no_cancel_button(h):
    await _register(h)
    calls = await h.click("quick:start") + await h.click("qname:me") + await h.text("40") + await h.text("5")
    calls += await h.click("screen:start") + await h.click("sex:M")
    for c in calls:
        markup = getattr(c, "reply_markup", None)
        if markup:
            cbs = [b.callback_data for row in markup.inline_keyboard for b in row]
            assert "cancel" not in cbs


async def test_quick_without_insulin_saves_glucose_and_hooks(h):
    await _register(h)
    await h.click("quick:start")
    await h.click("qname:me")
    await h.text("40")
    await h.text("5.9")
    out = texts(await h.click("noins"))
    assert "Glukoza natijasi" in out and "prediabet" in out and "insulin tahlili kerak" in out
    assert "14 kundan keyin" in out
    row = await db.get_screening(USER_ID)
    assert row["fasting_glucose"] == 5.9 and row["homa_ir"] is None
    # ikkinchi marta — oldingi glukoza bilan solishtiriladi
    await h.click("quick:start")
    await h.click("qname:me")
    await h.text("40")
    await h.text("5.2")
    assert "Oldingi glukoza bilan" in texts(await h.click("noins"))
    pdf = docs(await h.click("pdf:last"))
    assert pdf  # insulinsiz natijaning PDF'i ham yaratiladi


async def test_full_screening_without_insulin(h):
    await _register(h)
    await h.click("screen:start")
    await h.click("sex:F")
    for v in ("35", "70", "165", "85"):
        await h.text(v)
    for cb in ("act:1", "veg:1", "bp:0", "hg:0", "fam:none", "lab:yes"):
        await h.click(cb)
    await h.text("5.0")
    out = texts(await h.click("noins"))
    assert "FINDRISC:" in out and "Glukoza: 5.00" in out and "insulin tahlili kerak" in out


async def test_quick_flow_twice_compares_with_previous(h):
    await _register(h)
    await h.click("quick:start")
    assert "to'liq yozing" in texts(await h.text("Nodira"))
    await h.text("Karimova Nodira")
    await h.text("45")
    await h.text("5,8")
    out = texts(await h.text("16"))
    assert "HOMA-IR: 4.12" in out and "Karimova Nodira" in out and "prediabet" in out
    assert "Oldingi natija" not in out

    await h.click("quick:start")
    await h.text("karimova  nodira")
    await h.text("45")
    out = texts(await h.text("95"))  # mg/dL → 5.27 mmol/L
    assert "mg/dL" in out
    out = texts(await h.text("9"))
    assert "Oldingi natija bilan" in out and "yaxshilandi" in out


async def test_quick_validation_messages(h):
    await _register(h)
    await h.click("quick:start")
    await h.text("Ali Valiyev")
    assert "butun son" in texts(await h.text("abc"))
    await h.text("30")
    assert "2–30" in texts(await h.text("1"))
    await h.text("5")
    assert "0.5–300" in texts(await h.text("0"))


async def test_full_screening_with_labs(h):
    await _register(h)
    await h.click("screen:start")
    await h.click("sex:M")
    for v in ("52", "92", "175", "104"):
        await h.text(v)
    for cb in ("act:0", "veg:1", "bp:1", "hg:0", "fam:first", "lab:yes"):
        await h.click(cb)
    await h.text("6.2")
    out = texts(await h.text("18"))
    # yosh 52 → 2, BMI 30.0 → 3, bel 104 → 4, faollik yo'q → 2, sabzavot → 0, bosim → 2, oila → 5
    assert "FINDRISC: 18/26" in out and "HOMA-IR: 4.96" in out
    row = await db.get_screening(USER_ID)
    assert row["kind"] == "full" and row["patient_name"] == "Aliyev Vali" and row["whtr"] > 0.5


async def test_full_screening_skip_labs(h):
    await _register(h)
    await h.click("screen:start")
    await h.click("sex:F")
    for v in ("30", "60", "165", "72"):
        await h.text(v)
    for cb in ("act:1", "veg:1", "bp:0", "hg:0", "fam:none"):
        await h.click(cb)
    out = texts(await h.click("lab:skip"))
    assert "FINDRISC: 0/26" in out and "HOMA-IR: " not in out and "insulin tahlili kerak" in out


async def test_cancel_mid_flow(h):
    await _register(h)
    await h.click("quick:start")
    await h.text("Ali Valiyev")
    out = texts(await h.text("/cancel"))
    assert "Bekor qilindi" in out
    # endi raqam yozilsa so'rovnoma davom etmaydi — menyu chiqadi
    assert "bo'limni tanlang" in texts(await h.text("45"))


async def test_dynamics_pdf_history_and_admin(h):
    await _register(h)
    for g, ins in (("5.6", "15"), ("5.2", "11"), ("5.0", "8")):
        await h.click("quick:start")
        await h.click("qname:me")
        await h.text("40")
        await h.text(g)
        await h.text(ins)

    calls = await h.click("dyn")
    assert "Dinamika" in texts(calls) and any(isinstance(c, SendPhoto) for c in calls)
    calls = await h.click("pdf:last")
    assert docs(calls) and docs(calls)[0].document.filename.endswith(".pdf")
    assert "№" in texts(await h.click("history"))

    assert "Admin panel" in texts(await h.text("/admin"))
    assert "Tadqiqot xulosasi" in texts(await h.click("adm:stats"))
    for cb, ext in (("adm:pdf", ".pdf"), ("adm:xlsx", ".xlsx"), ("adm:csv", ".csv"), ("adm:backup", ".db")):
        d = docs(await h.click(cb))
        assert d and d[0].document.filename.endswith(ext), cb


async def test_other_user_cannot_open_admin_or_foreign_pdf(h):
    await _register(h)
    await h.click("quick:start")
    await h.click("qname:me")
    await h.text("40")
    await h.text("5")
    await h.text("10")
    stranger = User(id=999, is_bot=False, first_name="X")
    msg = Message(message_id=500, date=datetime.now(), chat=Chat(id=999, type="private"),
                  from_user=stranger, text="/admin")
    start = len(h.session.calls)
    await h.dp.feed_update(h.bot, Update(update_id=900, message=msg))
    assert "Admin panel" not in texts(h.session.calls[start:])
    cq = CallbackQuery(id="z", from_user=stranger, chat_instance="c", data="pdf:1",
                       message=Message(message_id=501, date=datetime.now(), chat=Chat(id=999, type="private")))
    start = len(h.session.calls)
    await h.dp.feed_update(h.bot, Update(update_id=901, callback_query=cq))
    new = h.session.calls[start:]
    assert not docs(new) and any(isinstance(c, AnswerCallbackQuery) and c.show_alert for c in new)


async def test_delete_removes_everything(h):
    await _register(h)
    await h.text("/delete")
    assert "o'chirildi" in texts(await h.click("del:yes"))
    assert await db.get_user(USER_ID) is None


def test_html_validator_catches_raw_less_than():
    with pytest.raises(AssertionError):
        assert_telegram_html("p<0.001")
    assert_telegram_html("<b>ok</b> p&lt;0.001 &amp; <i>x</i>")


async def test_html_escaping_of_user_name(h):
    await h.text("/start")
    await h.click("begin")
    await h.text("<b>Ali</b> &Valiyev")  # validator FakeSession ichida tekshiradi
    await h.click("quick:start")
    await h.click("qname:me")
    await h.text("40")
    await h.text("5")
    await h.text("10")
    await h.click("history")
    await h.click("dyn")
