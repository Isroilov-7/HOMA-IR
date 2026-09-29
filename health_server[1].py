"""
Koyeb / Render kabi bepul web-service platformalari uchun
oddiy HTTP endpoint. Ular xizmatning "tirik" ekanini tekshirish uchun
port'ni ochiq talab qiladi.

Bot poll qiladi (asosiy vazifa), bu esa yon tarafda 8000-portda
GET / ga "ok" qaytaradi.
"""

import os
from aiohttp import web


async def health(_request):
    return web.Response(text="ok")


async def start_health_server():
    """Fon vazifasi sifatida ishga tushadi."""
    port = int(os.getenv("PORT", "8000"))
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
