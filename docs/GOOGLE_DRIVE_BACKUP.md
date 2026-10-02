# Zaxirani Google Drive'ga shifrlangan holda yuborish

Har kecha 02:30 da `scripts/backup_offsite.sh` ishga tushadi:

1. Bazaning lokal nusxasini `data/backups/` ga oladi va butunligini tekshiradi.
2. Nusxani siqib, **shifrlab** Google Drive'ga yuboradi (rclone crypt).
   Google faqat ma'nosiz baytlarni ko'radi: faylning mazmuni ham, nomi ham shifrlangan.
3. Drive'da 90 kundan eski nusxalarni o'chiradi. Xato bo'lsa adminga Telegram xabar keladi.

rclone `drive.file` ruxsati bilan ulanadi. Bu ruxsat bilan u Drive'dagi boshqa
fayllaringizni ko'rmaydi, faqat o'zi yaratgan fayllar bilan ishlaydi.

## Bir martalik sozlash

**1. Kompyuteringizda (Windows) ruxsat olish.**
https://rclone.org/downloads/ dan Windows uchun zip'ni yuklab oching. Papkada `cmd` oching:
```
rclone authorize "drive" "eyJzY29wZSI6ImRyaXZlLmZpbGUifQ"
```
Brauzer ochiladi, Google akkauntingiz bilan kiring va ruxsat bering. Terminalda
`--->` va `<---` orasida `{"access_token":...}` ko'rinishidagi matn chiqadi.
Uni nusxalang. **Bu token, chatga yubormang.**

**2. Serverda rclone o'rnatish.**
```
apt install -y rclone && rclone version | head -1
```

**3. Google Drive ulanishi** (token yashirin kiritiladi):
```
read -s -p "Token: " TOK && rclone config create gdrive drive scope=drive.file token="$TOK" --non-interactive >/dev/null && unset TOK && echo && rclone listremotes
```
Kutilgan natija: `gdrive:`

**4. Shifrlash qatlami.** Ikkita tasodifiy parol yaratiladi va faqat root o'qiy oladigan faylga yoziladi:
```
umask 077 && P1=$(openssl rand -base64 24) && P2=$(openssl rand -base64 24) && rclone config create homa-crypt crypt remote=gdrive:homa-ir-backup password="$P1" password2="$P2" --obscure --non-interactive >/dev/null && printf 'HOMA-IR zaxira parollari (rclone crypt)\npassword=%s\npassword2=%s\n' "$P1" "$P2" > /root/homa-ir-crypt-parollar.txt && unset P1 P2 && rclone listremotes
```
Kutilgan natija: `gdrive:` va `homa-crypt:`

⚠️ `/root/homa-ir-crypt-parollar.txt` dagi ikki parolni parol menejeriga yoki qog'ozga ko'chirib qo'ying.
Server butunlay yo'qolsa, Drive'dagi zaxirani **faqat shu parollar bilan** ochish mumkin. Ularni chatga yubormang.

**5. Sinash.**
```
cd /opt/homa-ir && bash scripts/backup_offsite.sh
```
Kutilgan natija: `Google Drive'ga yuklandi (shifrlangan): health_....db.gz`.
Drive'da `homa-ir-backup` papkasi paydo bo'ladi, ichidagi fayl nomlari ma'nosiz harflardan iborat bo'ladi.

## Tiklash

```
rclone lsf homa-crypt:                         # nusxalar ro'yxati (shifrdan ochilgan nomlar)
rclone copy homa-crypt:health_YYYYMMDD_HHMMSS.db.gz /tmp/ && gunzip /tmp/health_*.db.gz
cd /opt/homa-ir && docker compose stop bot && cp /tmp/health_*.db data/health.db && chown 10001:10001 data/health.db && docker compose start bot
```
Yangi serverda tiklash uchun avval 3-qadamni bajaring. 4-qadamda yangi parol yaratmang:
saqlab qo'ygan parollaringizni `password=` va `password2=` ga yozing.
