import os
import random
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("BOT_TOKEN", "123:TEST")
os.environ.setdefault("ADMIN_IDS", "1")

from app.config import settings  # noqa: E402


@pytest.fixture
def tmp_db(tmp_path):
    """Har test o'z bazasi bilan (settings frozen — to'g'ridan-to'g'ri almashtiramiz)."""
    old_db, old_bk = settings.db_path, settings.backup_dir
    object.__setattr__(settings, "db_path", str(tmp_path / "test.db"))
    object.__setattr__(settings, "backup_dir", str(tmp_path / "backups"))
    yield tmp_path / "test.db"
    object.__setattr__(settings, "db_path", old_db)
    object.__setattr__(settings, "backup_dir", old_bk)


def make_rows(n: int = 80, seed: int = 7) -> list[dict]:
    """Sintetik kogorta: BMI va bel oshgani sari HOMA-IR oshadi; 15 kishi takroriy."""
    from app.calculator import (
        calculate_bmi,
        calculate_findrisc,
        calculate_homa_beta,
        calculate_homa_ir,
        calculate_quicki,
    )

    rnd = random.Random(seed)
    rows, rid = [], 0
    for i in range(n):
        sex = "M" if i % 2 else "F"
        age = rnd.randint(20, 70)
        h = rnd.uniform(155, 185)
        w = rnd.uniform(50, 110)
        waist = rnd.uniform(65, 120)
        bmi = calculate_bmi(w, h)
        g = round(rnd.uniform(4.2, 6.5) + (bmi - 25) * 0.03, 2)
        ins = round(max(2.0, rnd.uniform(3, 9) + (bmi - 20) * 0.9), 1)
        score, band = calculate_findrisc(age=age, bmi=bmi, waist=waist, sex=sex,
                                         activity_yes=rnd.random() > .5, veg_daily=rnd.random() > .5,
                                         bp_meds=rnd.random() > .8, high_glucose_hist=rnd.random() > .9,
                                         family_hx=rnd.choice(["none", "second", "first"]))
        visits = 2 if i < 15 else 1
        for v in range(visits):
            rid += 1
            ins_v = ins * (0.8 if v else 1.0)
            rows.append({
                "id": rid, "user_id": 1000 + i, "kind": "full", "patient_name": f"Bemor {i}",
                "sex": sex, "age": age, "weight": w, "height": h, "waist": waist,
                "activity_yes": 1, "veg_daily": 1, "bp_meds": 0, "high_glucose_hist": 0,
                "family_hx": "none", "fasting_glucose": g, "fasting_insulin": ins_v, "bmi": bmi,
                "whtr": waist / h, "homa_ir": calculate_homa_ir(g, ins_v),
                "homa_beta": calculate_homa_beta(g, ins_v), "quicki": calculate_quicki(g, ins_v),
                "findrisc": score, "findrisc_band": band, "combined_band": band,
                "created_at": f"2026-0{1 + v * 4}-{(i % 27) + 1:02d} 08:00:00", "is_anonymous": i % 3 == 0,
            })
    return rows


TAG = re.compile(r"</?(b|strong|i|em|u|ins|s|strike|del|code|pre|a|tg-spoiler|blockquote)(\s[^<>]*)?>")
AMP = re.compile(r"&(?!(lt|gt|amp|quot|#\d+);)")


def assert_telegram_html(text: str | None) -> None:
    """Telegram HTML qoidasi: '<' faqat ruxsat etilgan teg boshlashi, '&' faqat entity bo'lishi mumkin."""
    if not text:
        return
    for m in re.finditer("<", text):
        assert TAG.match(text, m.start()), f"Telegram rad etadi: ...{text[m.start():m.start() + 30]!r}"
    assert not AMP.search(text), f"Ekranlanmagan '&': {text!r}"
