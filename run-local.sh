#!/usr/bin/env bash
# Local run WITHOUT Docker (fallback for machines where Docker is unavailable).
#
#   ./run-local.sh          # start everything
#   ./run-local.sh stop     # stop everything
#
# Requires: a PostgreSQL 16+ reachable on localhost:5432 (see POSTGRES_* vars).
# In the project where this was developed PostgreSQL runs from /tmp/opencode/pg16.
set -euo pipefail

cd "$(dirname "$0")"

PY="${PY:-$PWD/.venv/bin/python}"
VENV="$PWD/.venv"
DB_DIR="${DB_DIR:-/tmp/opencode/pg16}"
PGDATA="${PGDATA:-/tmp/opencode/pgdata}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
API_PORT=8000
WEB_PORT=5173

if [ ! -x "$PY" ]; then
  echo "==> Creating Python venv + installing backend deps"
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q --upgrade pip
  "$VENV/bin/pip" install -q -r backend/requirements.txt
  PY="$VENV/bin/python"
fi

start_postgres() {
  if "$DB_DIR/bin/pg_isready" -h 127.0.0.1 -p "$POSTGRES_PORT" >/dev/null 2>&1; then
    echo "==> PostgreSQL already running on :$POSTGRES_PORT"
    return
  fi
  echo "==> Starting PostgreSQL"
  if [ ! -d "$PGDATA" ]; then
    "$DB_DIR/bin/initdb" -D "$PGDATA" -U recruitflow --auth=trust --no-sync >/dev/null
  fi
  "$DB_DIR/bin/pg_ctl" -D "$PGDATA" -l /tmp/opencode/pg.log \
    -o "-p $POSTGRES_PORT -k /tmp/opencode" start >/dev/null
  sleep 2
  psql -h 127.0.0.1 -p "$POSTGRES_PORT" -U recruitflow -d postgres \
    -c "ALTER USER recruitflow PASSWORD 'recruitflow_dev_password';" >/dev/null
  for db in recruitflow recruitflow_test; do
    psql -h 127.0.0.1 -p "$POSTGRES_PORT" -U recruitflow -d postgres \
      -tc "SELECT 1 FROM pg_database WHERE datname='$db'" | grep -q 1 \
      || psql -h 127.0.0.1 -p "$POSTGRES_PORT" -U recruitflow -d postgres \
           -c "CREATE DATABASE $db OWNER recruitflow;" >/dev/null
  done
}

stop_all() {
  echo "==> Stopping app servers"
  pkill -f "[u]vicorn app.main:app" 2>/dev/null || true
  pkill -f "[n]px vite" 2>/dev/null || true
  pkill -f "[v]ite --host 127.0.0.1" 2>/dev/null || true
  echo "==> PostgreSQL left running (data in $PGDATA). Stop with:"
  echo "    $DB_DIR/bin/pg_ctl -D $PGDATA stop"
}

if [ "${1:-}" = "stop" ]; then
  stop_all
  exit 0
fi

start_postgres

echo "==> Applying migrations"
(cd backend && alembic upgrade head >/dev/null 2>&1 || "$PY" -m alembic upgrade head)

echo "==> Seeding demo data (skipped if users already exist)"
(cd backend && PYTHONPATH=. "$PY" -m app.seed)

if ! curl -s -m 2 "http://127.0.0.1:$API_PORT/health" >/dev/null 2>&1; then
  echo "==> Starting API on :$API_PORT"
  (cd backend && PYTHONPATH=. nohup "$PY" -m uvicorn app.main:app \
     --host 127.0.0.1 --port $API_PORT > /tmp/opencode/uvicorn.log 2>&1 &)
fi

if ! curl -s -m 2 -o /dev/null "http://127.0.0.1:$WEB_PORT/" 2>/dev/null; then
  echo "==> Starting frontend on :$WEB_PORT"
  (cd frontend && [ -d node_modules ] || npm install --no-audit --no-fund)
  (cd frontend && nohup npx vite --host 127.0.0.1 --port $WEB_PORT \
     > /tmp/opencode/vite.log 2>&1 &)
fi

sleep 3
echo
echo "=============================================="
echo "  RecruitFlow запущен:  http://localhost:$WEB_PORT"
echo "  API (Swagger):        http://localhost:$API_PORT/api/docs"
echo "  Вход: admin@recruitflow.local / Admin1234!"
echo "  Стоп: ./run-local.sh stop"
echo "=============================================="
