#!/usr/bin/env bash
# Har kuni 02:30 da Toshkent vaqti bilan (21:30 UTC): lokal zaxira (data/backups) +
# rclone sozlangan bo'lsa shifrlangan nusxa Google Drive'ga (scripts/backup_offsite.sh)
# Bir marta ishga tushiriladi: sudo bash scripts/install_backup_cron.sh
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"
cat > /etc/cron.d/homa-ir-backup <<CRON
30 21 * * * root /usr/bin/bash $DIR/scripts/backup_offsite.sh >> /var/log/homa-ir-backup.log 2>&1
CRON
chmod 644 /etc/cron.d/homa-ir-backup
echo "OK: /etc/cron.d/homa-ir-backup o'rnatildi"
