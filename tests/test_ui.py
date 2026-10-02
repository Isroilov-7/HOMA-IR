"""Start posti va Telegram profil matnlari: limitlar, HTML, havolalar."""

from urllib.parse import parse_qs, urlparse

from app import ui
from conftest import assert_telegram_html


def test_profile_texts_fit_telegram_limits():
    assert len(ui.BOT_NAME) <= 64
    assert len(ui.BOT_SHORT_DESCRIPTION) <= 120
    assert len(ui.BOT_DESCRIPTION) <= 512


def test_intro_is_hooky_valid_html_and_ends_with_bot_link():
    assert len(ui.INTRO) <= 4096
    assert_telegram_html(ui.INTRO)
    assert ui.INTRO.startswith("🩸 <b>Qandingiz normal")
    assert ui.INTRO.rstrip().endswith("https://t.me/HomaIR_bot")
    for key in ("insulin rezistentligi", "HOMA-IR", "FINDRISC", "diabet", "Bepul"):
        assert key in ui.INTRO


def test_share_url_carries_bot_link_and_text():
    q = parse_qs(urlparse(ui.share_url()).query)
    assert q["url"] == ["https://t.me/HomaIR_bot"]
    assert "HOMA-IR" in q["text"][0]


def test_menu_has_share_button():
    urls = [b.url for row in ui.main_menu(5).inline_keyboard for b in row if b.url]
    assert urls and urls[0].startswith("https://t.me/share/url")
