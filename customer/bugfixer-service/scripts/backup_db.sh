#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
set -a
. ./.env
set +a

BACKUP_DIR="${BACKUP_DIR:-./backups}"
mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
FILE="$BACKUP_DIR/db_${STAMP}.sql.gz"

docker compose exec -T db pg_dump -U "${POSTGRES_USER:-bugfixer}" "${POSTGRES_DB:-bugfixer}" | gzip > "$FILE"

ls -1t "$BACKUP_DIR"/db_*.sql.gz | tail -n +15 | xargs -r rm -f
echo "Backup written to $FILE"
