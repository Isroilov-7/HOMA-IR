# HOMA-IR • Metabolik skrining boti (v3)

Insulin rezistentligi va 2-tur diabet xavfini xalqaro validatsiyalangan usullar bilan
baholovchi Telegram bot. Dissertatsiya tadqiqoti uchun ma'lumot yig'adi va tahlil qiladi.

## Imkoniyatlar

| Bo'lim | Nima qiladi |
|---|---|
| ⚡ **Tezkor HOMA-IR** | Faqat ism-familiya, yosh, glukoza, insulin → HOMA-IR, QUICKI, HOMA-β, tavsiyalar. Shifokor bir nechta bemorni kiritishi mumkin |
| 🩺 **To'liq skrining** | FINDRISC (8 savol) + ixtiyoriy glukoza/insulin, BMI, bel/bo'y nisbati |
| 📈 **Dinamika** | Oldingi va birinchi natija bilan solishtirish (±10% chegara), toifa o'zgarishi, grafik |
| 📄 **PDF hisobot** | Shifokorga ko'rsatishga tayyor: natija, izoh, tavsiyalar, dinamika grafigi |
| 🔔 **Eslatma** | 90 kundan keyin qayta tekshiruvga eslatadi (o'chirsa bo'ladi) |
| 👨‍💼 **Admin panel** | Umumiy ko'rsatkichlar, tadqiqot statistikasi, dissertatsiya PDF, Excel, CSV, grafiklar, zaxira |

### Admin uchun dissertatsiya hisoboti

`/admin` → **📄 Dissertatsiya PDF** quyidagilarni beradi:

- asosiy natijalar va material-metodlar bo'limi (formulalar, statistik usullar);
- 1-jadval: ishtirokchilar tavsifi, M ± SD va Me [Q1; Q3], erkak va ayol uchun alohida, p (Mann–Whitney);
- HOMA-IR toifalari; IR prevalentligi 95% CI (Wilson) bilan, jins, yosh va BMI kesimida, p (χ²/Fisher);
- HOMA-IR ning yosh, BMI, bel, glukoza, insulin va FINDRISC bilan Spearman korrelyatsiyasi;
- **populyatsiyaga xos cutoff**: metabolik sog'lom guruhda HOMA-IR P75 (Ascaso 2003 yondashuvi);
- FINDRISC toifalari, takroriy o'lchovlar (Wilcoxon), rasmlar, cheklovlar, adabiyotlar.

**📗 Excel** fayli anonim ma'lumotlarni va tayyor jadvallarni o'z ichiga oladi. **🧾 CSV** SPSS, R va pandas uchun.
Eksportlarda ism ham, Telegram ID ham bo'lmaydi, faqat `S0001…` kodi qoladi.

**Metodologiya.** Kesma tahlilda har bir sub'ekt bir marta, o'zining birinchi laborator
o'lchovi bilan hisoblanadi. Takroriy o'lchovlar faqat dinamika bo'limiga kiradi.

## Serverga o'rnatish (Docker)

```bash
git clone https://github.com/Isroilov-7/homa-ir /opt/homa-ir && cd /opt/homa-ir
cp .env.example .env
read -s -p "BOT_TOKEN: " T && sed -i "s|^BOT_TOKEN=.*|BOT_TOKEN=$T|" .env && unset T; echo
mkdir -p data && chown 10001:10001 data
docker compose up -d --build
docker compose logs --tail 20 bot          # "HOMA-IR bot v3.0.0 ishga tushdi"
sudo bash scripts/install_backup_cron.sh   # har kuni zaxira: data/backups
```

Yangilash: `git pull && docker compose up -d --build`.
Eski v2 bazasi (`health.db`) bo'lsa, uni `data/health.db` ga ko'chiring. Bot ishga tushganda
uni avtomatik yangilaydi, ma'lumotlar saqlanib qoladi.

Resurslar: ~180 MB RAM, admin hisobotida ~330 MB gacha. Chegara 450 MB va 0.5 CPU.
Port ochilmaydi, konteyner faqat o'qish rejimida va root huquqisiz ishlaydi.

## Ishlab chiqish

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
ruff check . && pytest -q        # 50+ test: formulalar, statistika, migratsiya, bot oqimlari
BOT_TOKEN=... python bot.py
```

| Fayl | Vazifasi |
|---|---|
| `app/calculator.py` | Klinik formulalar (HOMA-IR, HOMA-β, QUICKI, FINDRISC, BMI, WHtR) |
| `app/analytics.py` | Bemor dinamikasi |
| `app/stats.py` | Kogorta statistikasi (dissertatsiya) |
| `app/charts.py` | Grafiklar |
| `app/reports/` | Bemor PDF, tadqiqot PDF, Excel/CSV |
| `app/handlers/` | Bot oqimlari: start, tezkor, to'liq, tarix, admin |
| `app/db.py` | SQLite + avtomatik migratsiya |

## Xavfsizlik

- Token faqat `.env` da turadi. `.env`, `data/` va `*.db` git'ga tushmaydi.
- Eski token git tarixida qolgan, lekin bekor qilingan. Har ehtimolga qarshi uni yana bir bor @BotFather'da tekshiring.
- Bazada tibbiy ma'lumot bor: zaxira nusxalarni boshqalarga yubormang.

## Manbalar

Matthews 1985 (HOMA), Katz 2000 (QUICKI), Lindström & Tuomilehto 2003 (FINDRISC),
Bonora 2000, Ascaso 2003, WHO 2004 (Osiyo BMI), IDF 2006, Ashwell 2012 (WHtR), ADA 2024.

> Bot skrining vositasi, tashxis qo'ymaydi. Yuqori natija chiqsa, endokrinologga murojaat qilish kerak.
