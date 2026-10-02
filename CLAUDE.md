# HOMA-IR bot — Claude uchun qisqa qo'llanma

- Til: javoblar o'zbekcha, qisqa. Kod izohlari o'zbekcha.
- Ishga tushirish: `python bot.py` → `app/main.py`. Server: `/opt/homa-ir`, `docker compose`.
- Har o'zgarishdan keyin: `ruff check . && pytest -q` (e2e testlar Telegram'siz ishlaydi).
- Klinik formula o'zgarsa: manbasini docstring'ga yozing va `tests/test_calculator.py` ga ma'lum qiymatli test qo'shing.
- Statistika: kesma tahlilda har sub'ekt bir marta (`stats.baseline_rows`). Sub'ekt = user_id + bemor ismi.
- DB: yangi ustun faqat `db.MIGRATIONS` orqali qo'shiladi (eski bazalar avtomatik yangilanadi).
- Sirlar faqat `.env` da; serverda `read -s` bilan yoziladi. Tibbiy ma'lumot git'ga tushmasin.
- Server buyruqlari bittadan, kutilgan natija bilan beriladi.
