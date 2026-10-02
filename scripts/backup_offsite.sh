#!/usr/bin/env bash
# Kunlik zaxira: (1) lokal nusxa data/backups ga, (2) SHIFRLANGAN nusxa Google Drive'ga.
#
# Google Drive faqat shifrlangan faylni ko'radi (rclone crypt: mazmun ham, nom ham
# shifrlanadi). Sozlash: docs/GOOGLE_DRIVE_BACKUP.md. rclone sozlanmagan bo'lsa,
# faqat lokal zaxira olinadi. Xato bo'lsa adminga Telegram xabar keladi.
set -euo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR"
REMOTE="${HOMA_REMOTE:-homa-crypt:}"
REMOTE_KEEP_DAYS="${REMOTE_KEEP_DAYS:-90}"
STAMP="$(date '+%F %T')"

notify_fail() {
    local tok chat
    tok=$(grep '^BOT_TOKEN=' .env | cut -d= -f2- | tr -d "\"'")
    chat=$(grep '^ADMIN_IDS=' .env | cut -d= -f2- | tr -d "\"' " | cut -d, -f1)
    [ -n "$tok" ] && [ -n "$chat" ] && curl -s -X POST "https://api.telegram.org/bot${tok}/sendMessage" \
        --data-urlencode "chat_id=$chat" \
        --data-urlencode "text=❌ HOMA-IR zaxira XATO ($STAMP). Log: /var/log/homa-ir-backup.log" >/dev/null || true
}
trap notify_fail ERR

# 1) Lokal zaxira (konteyner ichida SQLite online backup + integrity_check)
OUT=$(docker compose exec -T bot python -m app.backup)
echo "[$STAMP] $OUT"
FILE="$DIR/data/backups/$(basename "$(echo "$OUT" | awk '{print $2}')")"
[ -s "$FILE" ]

# 2) Google Drive (shifrlangan)
if ! command -v rclone >/dev/null 2>&1 || ! rclone listremotes | grep -qx "${REMOTE%%:*}:"; then
    echo "[$STAMP] rclone/${REMOTE} sozlanmagan — faqat lokal zaxira"
    exit 0
fi
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
gzip -9 -c "$FILE" > "$TMP/$(basename "$FILE").gz"
rclone copy "$TMP/$(basename "$FILE").gz" "$REMOTE" --retries 3
rclone lsf "$REMOTE" | grep -qx "$(basename "$FILE").gz"
rclone delete "$REMOTE" --min-age "${REMOTE_KEEP_DAYS}d" --include "health_*.db.gz" || true
echo "[$STAMP] Google Drive'ga yuklandi (shifrlangan): $(basename "$FILE").gz"
