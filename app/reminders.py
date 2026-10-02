"""
Qayta tekshiruv eslatmasi: oxirgi natijadan REMINDER_DAYS kun o'tgach bir marta.
Dinamika ma'lumoti to'planishi (bemor uchun ham, tadqiqot uchun ham) shunga bog'liq.
"""

import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter

from app import db, ui
from app.config import settings

log = logging.getLogger(__name__)
CHECK_EVERY_SEC = 6 * 3600


def reminder_text(complete: bool) -> str:
    if complete:
        return ("🔔 <b>Qayta tekshiruv vaqti</b>\n\n"
                f"Oxirgi natijangizdan {settings.reminder_days} kun o'tdi. Och qoringa glukoza va "
                "insulinni qayta topshirib, natijani kiriting: bot avvalgisi bilan solishtirib, "
                "dinamikani ko'rsatadi.")
    return ("🧪 <b>Insulin natijangiz tayyormi?</b>\n\n"
            "Oxirgi safar faqat glukoza kiritilgan edi. Och qoringa <b>glukoza + insulin</b>ni "
            "birga topshirsangiz, HOMA-IR (insulin rezistentligi) hisoblanadi va diabet xavfini "
            "yillar oldin ko'rish mumkin bo'ladi. Natijani kiritish 1 daqiqa oladi.")


async def send_due(bot: Bot) -> int:
    sent = 0
    for u in await db.due_reminders(settings.reminder_days, settings.insulin_reminder_days):
        try:
            await bot.send_message(
                u["user_id"],
                reminder_text(bool(u["complete"])),
                reply_markup=ui.kb([("⚡ Tezkor HOMA-IR", "quick:start")],
                                   [("🔕 Eslatmani o'chirish", "remind:toggle")]),
            )
            sent += 1
        except TelegramForbiddenError:
            await db.set_reminders(u["user_id"], False)  # botni bloklagan
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
            continue
        except Exception:
            log.exception("Eslatma yuborilmadi: %s", u["user_id"])
            continue
        await db.mark_reminded(u["user_id"])
        await asyncio.sleep(0.05)  # Telegram limiti: ~30 xabar/soniya
    return sent


async def reminder_loop(bot: Bot) -> None:
    if settings.reminder_days <= 0:
        return
    await asyncio.sleep(60)
    while True:
        try:
            n = await send_due(bot)
            if n:
                log.info("Eslatma yuborildi: %d", n)
        except Exception:
            log.exception("Eslatma tsiklida xato")
        await asyncio.sleep(CHECK_EVERY_SEC)
