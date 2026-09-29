# HOMA-IR + FINDRISC Skrining Bot v2

Diabet xavfini klinik jihatdan asosli baholovchi Telegram bot.

## Nima o'zgardi (v1 → v2)

| | v1 (eski) | v2 (yangi) |
|---|---|---|
| Framework | aiogram 2.25 (eskirgan) | aiogram 3.13 |
| Xavf shkalasi | O'z-o'zicha ballar | **FINDRISC** (Diabetes Care, 2003) |
| HOMA-IR | Bor, lekin arbitrar cutoff | Matthews (1985) + Bonora (2000) |
| Konfiguratsiya | Token kodda ochiq | `.env` |
| Rozilik | Yo'q | Bor (informed consent) |
| Anonim rejim | Yo'q | Bor |
| PDF hisobot | Yo'q | Bor (reportlab) |
| UI | Reply keyboard | Inline (zamonaviyroq) |
| Tadqiqot eksport | Aralash Excel | Anonim CSV (SPSS/R-ga) |
| Foydalanuvchi huquqlari | Yo'q | `/export`, `/delete` (GDPR-mos) |

## O'rnatish

```bash
# 1. Loyihani ko'chiring
cd homa-ir-bot

# 2. Virtual environment
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Kutubxonalar
pip install -r requirements.txt

# 4. Token va sozlamalar
cp .env.example .env
# .env ni tahrirlang: BOT_TOKEN qo'ying (BotFader'dan yangisi!)

# 5. Ishga tushirish
python bot.py
```

## Muhim: Token xavfsizligi

Sizning eski tokeningiz (`8446153026:AAFx2kM-kgBn9soI6KSp14Fjp9-MuMgeJYA`)
chatga qo'yilgan va bir necha kodda ochiq bor edi.

**Hoziroq bajaring:**
1. `@BotFather` → `/mybots` → botingizni tanlang → API Token → **Revoke current token**
2. Yangi tokenni faqat `.env` fayliga qo'ying
3. `.env` faylni **hech qachon** git'ga qo'shmang (`.gitignore` qo'shing)

## Fayllar

```
homa-ir-bot/
├── bot.py               # Asosiy bot (routing, handlers)
├── calculator.py        # Klinik hisob-kitoblar (FINDRISC, HOMA-IR, BMI)
├── pdf_report.py        # PDF generator
├── research_export.py   # Anonim CSV eksport (tadqiqot uchun)
├── .env.example         # Konfiguratsiya namunasi
├── requirements.txt     # Python bog'lanishlar
└── README.md            # Bu fayl
```

## Tadqiqot uchun ma'lumot eksport

```bash
# Barcha ma'lumot
python research_export.py --out barcha.csv

# Faqat anonim rozilik berganlar (etika komissiyasi uchun ma'qulroq)
python research_export.py --anon --out anonim.csv

# Ma'lum sanadan keyin
python research_export.py --after 2026-01-01 --out yangi.csv
```

CSV `subject_id` (S00001, S00002…) bilan chiqadi — Telegram ID yo'q,
ism yo'q. To'g'ridan-to'g'ri SPSS/R/pandas'ga import qilinadi.

### O'zbek populyatsiyasi uchun HOMA-IR cutoff

Yetarli ma'lumot yig'ilgach (masalan, N=200+), CSV'ni R'ga import qiling
va sog'lom guruhning 75-persentilini hisoblang. Bu — sizning populyatsiyangiz
uchun aniq cutoff bo'ladi va nashrga tayyor ma'lumot beradi.

```r
library(dplyr)
data <- read.csv("anonim.csv")
healthy <- data %>% filter(findrisc_band == "past" & is.na(fasting_glucose) | fasting_glucose < 5.6)
cutoff <- quantile(healthy$homa_ir, 0.75, na.rm = TRUE)
cat("Uzbek cutoff (P75):", cutoff, "\n")
```

## Deploy

### VPS (tavsiya etilgan)
- **Railway** (7$/oy) — GitHub push → auto deploy
- **Hetzner CPX11** (~4€/oy) — sizniki nazorat
- **PythonAnywhere** — bepul, cheklangan

### systemd unit misoli

```ini
# /etc/systemd/system/homa-bot.service
[Unit]
Description=HOMA-IR Bot
After=network.target

[Service]
Type=simple
User=botuser
WorkingDirectory=/home/botuser/homa-ir-bot
EnvironmentFile=/home/botuser/homa-ir-bot/.env
ExecStart=/home/botuser/homa-ir-bot/venv/bin/python bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## Klinik izohlar

Bu bot **skrining** vositasi, tashxis emas. Real klinikada:

1. **FINDRISC** — WHO va IDF tomonidan tavsiya etilgan
2. **HOMA-IR > 2.5** — insulin rezistentligi (yevropoid populyatsiyasi;
   sizning tadqiqotingiz o'zbek populyatsiyasi uchun aniq raqam beradi)
3. Har qanday **YUQORI** yoki **JUDA YUQORI** natija → endokrinolog

## Keyingi qadamlar

- [ ] Prometheus metrikalari (foydalanish statistikasi)
- [ ] `/reminder` — 3 oyda qayta baholash eslatmasi
- [ ] Ko'p tillilik (rus/ingliz)
- [ ] HbA1c qo'shish (agar mavjud bo'lsa, aniqroq)
- [ ] Endokrinolog ro'yxati (viloyatlar bo'yicha)
- [ ] Docker-compose

## Litsenziya

MIT (yoki o'zingiz tanlagan). Klinik shkalalar ochiq nashrlarda.
