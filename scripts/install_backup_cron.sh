#!/usr/bin/env bash
# Har kuni 02:30 da Toshkent vaqti bilan (21:30 UTC) bazaning zaxira nusxasi: /opt/homa-ir/data/backups
# Bir marta ishga tushiriladi: sudo bash scripts/install_backup_cron.sh
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"
cat > /etc/cron.d/homa-ir-backup <<CRON
30 21 * * * root cd $DIR && /usr/bin/docker compose exec -T bot python -m app.backup >> /var/log/homa-ir-backup.log 2>&1
CRON
chmod 644 /etc/cron.d/homa-ir-backup
echo "OK: /etc/cron.d/homa-ir-backup o'rnatildi"
