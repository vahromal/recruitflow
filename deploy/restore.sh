#!/usr/bin/env bash
# Restore database (and optionally resumes) from a backup created by backup.sh.
#
# Usage:
#   ./deploy/restore.sh backups/db_20261101_030000.sql.gz
#   ./deploy/restore.sh backups/db_20261101_030000.sql.gz --resumes backups/resumes_20261101_030000.tar.gz
#
# WARNING: restores OVERWRITE the current database. The script makes a safety
# dump of the current DB before restoring.
set -euo pipefail

cd "$(dirname "$0")/.."

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

: "${POSTGRES_USER:?POSTGRES_USER not set}"
: "${POSTGRES_DB:?POSTGRES_DB not set}"

DB_DUMP="${1:-}"
[ -n "$DB_DUMP" ] || { echo "Usage: $0 <db_dump.sql.gz> [--resumes <resumes.tar.gz>]"; exit 1; }
[ -f "$DB_DUMP" ] || { echo "File not found: $DB_DUMP"; exit 1; }

RESUMES_TAR=""
if [ "${2:-}" = "--resumes" ]; then
  RESUMES_TAR="${3:-}"
  [ -f "$RESUMES_TAR" ] || { echo "File not found: $RESUMES_TAR"; exit 1; }
fi

PROJECT_NAME="${PROJECT_NAME:-recruitflow}"
STAMP="$(date +%Y%m%d_%H%M%S)"

echo "==> [1/4] Safety dump of the current DB"
mkdir -p backups
docker compose -f docker-compose.prod.yml exec -T db \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists \
  | gzip > "backups/pre_restore_$STAMP.sql.gz" || true
echo "    backups/pre_restore_$STAMP.sql.gz"

echo "==> [2/4] Dropping all objects in $POSTGRES_DB"
docker compose -f docker-compose.prod.yml exec -T db \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 \
  -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

echo "==> [3/4] Restoring $DB_DUMP"
gunzip -c "$DB_DUMP" | docker compose -f docker-compose.prod.yml exec -T db \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -q

echo "    rows check:"
docker compose -f docker-compose.prod.yml exec -T db \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
  "SELECT (SELECT count(*) FROM users) AS users, (SELECT count(*) FROM candidates) AS candidates, (SELECT count(*) FROM vacancies) AS vacancies;"

if [ -n "$RESUMES_TAR" ]; then
  echo "==> [4/4] Restoring resumes to volume ${PROJECT_NAME}_uploads"
  docker run --rm \
    -v "${PROJECT_NAME}_uploads":/dest \
    -v "$(cd "$(dirname "$RESUMES_TAR")" && pwd)":/backups:ro \
    alpine sh -c "rm -rf /dest/* && tar xzf /backups/$(basename "$RESUMES_TAR") -C /dest"
else
  echo "==> [4/4] resumes restore skipped (pass --resumes <file>)"
fi

echo "DONE. Verify: docker compose -f docker-compose.prod.yml ps"
