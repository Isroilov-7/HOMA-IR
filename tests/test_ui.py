"""Start posti va Telegram profil matnlari: limitlar, HTML, havolalar."""

from urllib.parse import parse_qs, urlparse

from app import ui
from conftest import assert_telegram_html


def test_profile_texts_fit_telegram_limits():
    assert len(ui.BOT_NAME) <= 64
    assert len(ui.BOT_SHORT_DESCRIPTION) <= 120
    assert len(ui.BOT_DESCRIPTION) <= 512


def test_intro_is_hooky_valid_html_and_ends_with_bot_link():
    """2026-10-13 (egasi): start posti oddiy xalq tilida; glukoza kerak, insulin tavsiya — "insulin bo'lsa
    natija ancha aniq" taklifi bilan (hamma ham insulin topshirmaydi)."""
    assert len(ui.INTRO) <= 4096
    assert_telegram_html(ui.INTRO)
    assert ui.INTRO.startswith("🩸 <b>Qandingiz normal")
    assert ui.INTRO.rstrip().endswith("https://t.me/HomaIR_bot")
    for key in ("insulin rezistentligi", "HOMA-IR", "diabet", "Bepul", "Glukoza (qand)", "Insulin",
                "natija ancha aniq", "Faqat qand bo'lsa ham", "tashxis emas"):
        assert key in ui.INTRO, key
    assert_telegram_html(ui.ABOUT_SIMPLE)
    assert "HOMA-IR" in ui.ABOUT_SIMPLE and "Faqat qand bo'lsa" in ui.ABOUT_SIMPLE


def test_search_name_has_common_keywords():
    """Telegram qidiruvi nom va tavsifdagi so'zlarni topadi — odamlar "qand", "insulin", "diabet" deb qidiradi."""
    for w in ("Qand", "insulin", "Diabet", "HOMA-IR"):
        assert w.lower() in ui.BOT_NAME.lower()


def test_share_url_carries_bot_link_and_text():
    q = parse_qs(urlparse(ui.share_url()).query)
    assert q["url"] == ["https://t.me/HomaIR_bot"]
    assert "HOMA-IR" in q["text"][0]


def test_main_menu_has_only_three_buttons_and_share_moved_to_about():
    """2026-10-13 (egasi): ko'p tugma odamni chalg'itadi — bosh menyuda 3 ta: test, natijalar, bu nima.
    Qolganlari (to'liq skrining, eslatma, maxfiylik, ulashish, usullar) «❓ Bu nima?» ekranida."""
    cbs = [b.callback_data or b.url for row in ui.main_menu(5).inline_keyboard for b in row]
    assert cbs == ["quick:start", "history", "about"]
    admin = [b.callback_data for row in ui.main_menu(1).inline_keyboard for b in row]   # conftest: ADMIN_IDS=1
    assert admin[-1] == "adm:home" and len(admin) == 4
    about = [b.callback_data or b.url for row in ui.about_kb(admin=True).inline_keyboard for b in row]
    assert {"screen:start", "remind:toggle", "privacy", "methods", "home"} <= set(about)
    assert any(u.startswith("https://t.me/share/url") for u in about if u)
    # oddiy foydalanuvchiga qo'shimcha bo'limlar ko'rinmaydi (faqat admin profilida)
    plain = [b.callback_data or b.url for row in ui.about_kb().inline_keyboard for b in row]
    assert plain == ["quick:start", "home"]
