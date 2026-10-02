"""Botni ishga tushirish: DB migratsiyasi, buyruqlar menyusi, eslatmalar, polling."""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeChat, ErrorEvent

from app import __version__, db
from app.config import settings
from app.handlers import build_router
from app.reminders import reminder_loop

log = logging.getLogger("bot")

USER_COMMANDS = [
    BotCommand(command="start", description="Bosh menyu"),
    BotCommand(command="quick", description="Tezkor HOMA-IR"),
    BotCommand(command="screen", description="To'liq skrining (FINDRISC + HOMA-IR)"),
    BotCommand(command="dynamics", description="Natijalar dinamikasi"),
    BotCommand(command="history", description="Natijalarim va PDF"),
    BotCommand(command="about", description="Usullar va me'yorlar"),
    BotCommand(command="help", description="Yordam"),
    BotCommand(command="cancel", description="Bekor qilish"),
]


async def _set_commands(bot: Bot) -> None:
    await bot.set_my_commands(USER_COMMANDS)
    for admin_id in settings.admin_ids:
        try:
            await bot.set_my_commands(
                USER_COMMANDS + [BotCommand(command="admin", description="Admin panel")],
                scope=BotCommandScopeChat(chat_id=admin_id))
        except Exception:  # admin hali botga yozmagan bo'lsa
            log.warning("Admin %s uchun buyruqlar o'rnatilmadi", admin_id)


async def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    if not settings.bot_token:
        raise SystemExit("BOT_TOKEN yo'q: .env faylga yozing.")
    if not settings.admin_ids:
        log.warning("ADMIN_IDS bo'sh: admin panel hech kimga ochilmaydi.")

    await db.init_db()
    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(build_router())

    @dp.errors()
    async def on_error(event: ErrorEvent) -> bool:
        log.exception("Handler xatosi: %s", event.exception, exc_info=event.exception)
        upd = event.update
        target = (upd.message or (upd.callback_query.message if upd.callback_query else None))
        if target:
            try:
                await target.answer("⚠️ Kutilmagan xatolik. Qayta urinib ko'ring yoki /start bosing.")
            except Exception:
                pass
        return True

    await _set_commands(bot)
    if settings.health_port:
        from app.health import start_health_server

        await start_health_server(int(settings.health_port))
    tasks = [asyncio.create_task(reminder_loop(bot))]
    log.info("HOMA-IR bot v%s ishga tushdi (DB: %s)", __version__, settings.db_path)
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        for t in tasks:
            t.cancel()
        await bot.session.close()


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()
