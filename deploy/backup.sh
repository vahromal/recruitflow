#!/usr/bin/env bash
# Daily backup: PostgreSQL dump + resume files. Keeps 14 days.
# Run manually: ./deploy/backup.sh
# Cron example:  0 3 * * * cd /opt/RecruitFlow && ./deploy/backup.sh >> /var/log/recruitflow-backup.log 2>&1
set -euo pipefail

cd "$(dirname "$0")/.."

# Load .env if present
if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

: "${POSTGRES_USER:?POSTGRES_USER not set}"
: "${POSTGRES_DB:?POSTGRES_DB not set}"
BACKUP_DIR="${BACKUP_DIR:-$PWD/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
STAMP="$(date +%Y%m%d_%H%M%S)"

mkdir -p "$BACKUP_DIR"

echo "[$(date -Is)] backup started"

# 1. Database dump (inside the db container)
docker compose -f docker-compose.prod.yml exec -T db \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists \
  | gzip > "$BACKUP_DIR/db_$STAMP.sql.gz"

echo "[$(date -Is)] db dump: $(du -h "$BACKUP_DIR/db_$STAMP.sql.gz" | cut -f1)"

# Production stack name is fixed below (top-level `name:`), so volume names are stable.
PROJECT_NAME="${PROJECT_NAME:-recruitflow}"

# 2. Resume files (named volume "uploads" of the prod stack)
TMP_UPLOADS="$(mktemp -d)"
if docker run --rm \
    -v "${PROJECT_NAME}_uploads":/source:ro \
    -v "$TMP_UPLOADS":/dest \
    alpine tar czf /dest/resumes.tar.gz -C /source .; then
  mv "$TMP_UPLOADS/resumes.tar.gz" "$BACKUP_DIR/resumes_$STAMP.tar.gz"
  echo "[$(date -Is)] resumes: $(du -h "$BACKUP_DIR/resumes_$STAMP.tar.gz" | cut -f1)"
else
  echo "WARN: uploads volume copy failed (is the stack running?)"
fi
rm -rf "$TMP_UPLOADS"

# 3. manifest (for restore verification)
{
  echo "created=$(date -Is)"
  echo "db_file=db_$STAMP.sql.gz"
  echo "resumes_file=resumes_$STAMP.tar.gz"
} > "$BACKUP_DIR/manifest_$STAMP.txt"

# 4. retention: delete older than RETENTION_DAYS
find "$BACKUP_DIR" -name "db_*.sql.gz"   -mtime +"$RETENTION_DAYS" -delete
find "$BACKUP_DIR" -name "resumes_*.tar.gz" -mtime +"$RETENTION_DAYS" -delete
find "$BACKUP_DIR" -name "manifest_*.txt"   -mtime +"$RETENTION_DAYS" -delete

echo "[$(date -Is)] backup finished; files in $BACKUP_DIR:"
ls -lh "$BACKUP_DIR" | tail -n +2
