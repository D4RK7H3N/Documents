#!/bin/sh
# Daily database backup with 14-day retention. Schedule with cron:
#   0 2 * * * /opt/grade-monitoring/deploy/backup.sh >> /var/log/grade-backup.log 2>&1
set -eu

BACKUP_DIR="${BACKUP_DIR:-/var/backups/grade-monitoring}"
KEEP_DAYS="${KEEP_DAYS:-14}"
COMPOSE_FILE="$(dirname "$0")/docker-compose.yml"

mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="$BACKUP_DIR/grade_monitoring_$STAMP.sql.gz"

docker compose -f "$COMPOSE_FILE" exec -T db \
  sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' | gzip > "$OUT"

if [ -s "$OUT" ]; then
  echo "$(date '+%F %T') backup written to $OUT ($(du -h "$OUT" | cut -f1))"
  find "$BACKUP_DIR" -name 'grade_monitoring_*.sql.gz' -mtime +"$KEEP_DAYS" -delete
else
  echo "$(date '+%F %T') ERROR: backup file is empty" >&2
  rm -f "$OUT"
  exit 1
fi
