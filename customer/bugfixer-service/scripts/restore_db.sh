#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
set -a
. ./.env
set +a

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 backups/db_YYYYmmdd_HHMMSS.sql.gz"
  exit 1
fi

FILE="$1"
if [ ! -f "$FILE" ]; then
  echo "File not found: $FILE"
  exit 1
fi

read -r -p "This replaces the current database contents. Type 'yes' to continue: " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
  echo "Cancelled."
  exit 1
fi

docker compose exec -T db psql -U "${POSTGRES_USER:-bugfixer}" -d "${POSTGRES_DB:-bugfixer}" \
  -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
gunzip -c "$FILE" | docker compose exec -T db psql -U "${POSTGRES_USER:-bugfixer}" \
  -d "${POSTGRES_DB:-bugfixer}" --set ON_ERROR_STOP=on

echo "Restore complete from $FILE"
