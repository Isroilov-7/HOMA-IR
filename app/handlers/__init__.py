from aiogram import Router

from app.handlers import admin, common, history, quick, screening


def build_router() -> Router:
    root = Router()
    # common birinchi: /cancel va "Bekor qilish" har qanday holatda ishlashi kerak
    for r in (common.router, quick.router, screening.router, history.router, admin.router):
        root.include_router(r)
    return root
