"""
Ixtiyoriy HTTP health endpoint — faqat port talab qiladigan platformalar
(Koyeb, Render) uchun. Serverda HEALTH_PORT bo'sh qoldiriladi.
"""

from aiohttp import web


async def start_health_server(port: int) -> None:
    async def ok(_request):
        return web.Response(text="ok")

    app = web.Application()
    app.router.add_get("/", ok)
    app.router.add_get("/health", ok)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", port).start()
