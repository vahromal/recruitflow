#!/usr/bin/env bash
# Local run WITHOUT Docker + optional public access via a localhost.run tunnel.
#
#   ./run-local.sh            # start db + API + frontend (local only)
#   ./run-local.sh tunnel     # start everything AND expose it on a public HTTPS URL
#   ./run-local.sh url        # print the current public URL (if tunnel is running)
#   ./run-local.sh status     # show what is running
#   ./run-local.sh stop       # stop app servers and tunnel (db keeps running)
#   ./run-local.sh stop-all   # stop everything including PostgreSQL
#
# The public tunnel needs no account: it is an SSH connection to localhost.run
# (deploy/tunnel-loop.sh reconnects by itself and keeps the URL file fresh).
#
# Data and binaries live in ~/.local (PERSISTENT — survives reboot; /tmp does not).
set -euo pipefail

cd "$(dirname "$0")"
HOME_DIR="$HOME"
PY="${PY:-$PWD/.venv/bin/python}"
VENV="$PWD/.venv"
DB_DIR="${DB_DIR:-$HOME_DIR/.local/pg16}"
PGDATA="${PGDATA:-$HOME_DIR/.local/pgdata}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
API_PORT=8000
WEB_PORT=5173

RUN_DIR="$HOME_DIR/.local/var/run"
LOG_DIR="$HOME_DIR/.local/var/log"
TUNNEL_URL="$RUN_DIR/tunnel.url"
TUNNEL_LOG="$LOG_DIR/tunnel.log"
TUNNEL_LOOP="$PWD/deploy/tunnel-loop.sh"
mkdir -p "$RUN_DIR" "$LOG_DIR"

# ---------------------------------------------------------------- helpers
alive() { pgrep -f "$1" >/dev/null 2>&1; }

wait_for() { # wait_for <url> <tries>
  local url="$1" n="${2:-30}"
  for _ in $(seq 1 "$n"); do
    curl -s -m 2 -o /dev/null "$url" && return 0
    sleep 1
  done
  return 1
}

# ---------------------------------------------------------------- postgres
start_postgres() {
  if "$DB_DIR/bin/pg_isready" -h 127.0.0.1 -p "$POSTGRES_PORT" >/dev/null 2>&1; then
    echo "==> PostgreSQL работает на :$POSTGRES_PORT"
    return
  fi
  if [ ! -x "$DB_DIR/bin/postgres" ]; then
    echo "!! PostgreSQL не установлен в $DB_DIR"
    echo "   Соберите его: bash ~/.local/src/build_pg.sh   (~4 минуты)"
    exit 1
  fi
  echo "==> Запуск PostgreSQL"
  [ -d "$PGDATA" ] || "$DB_DIR/bin/initdb" -D "$PGDATA" -U recruitflow --auth=trust --no-sync >/dev/null
  "$DB_DIR/bin/pg_ctl" -D "$PGDATA" -l "$LOG_DIR/postgres.log" \
    -o "-p $POSTGRES_PORT -k $RUN_DIR" start >/dev/null
  sleep 2
  PSQL="$DB_DIR/bin/psql"
  "$PSQL" -h 127.0.0.1 -p "$POSTGRES_PORT" -U recruitflow -d postgres \
    -c "ALTER USER recruitflow PASSWORD 'recruitflow_dev_password';" >/dev/null
  for db in recruitflow recruitflow_test; do
    "$PSQL" -h 127.0.0.1 -p "$POSTGRES_PORT" -U recruitflow -d postgres \
      -tc "SELECT 1 FROM pg_database WHERE datname='$db'" | grep -q 1 \
      || "$PSQL" -h 127.0.0.1 -p "$POSTGRES_PORT" -U recruitflow -d postgres \
           -c "CREATE DATABASE $db OWNER recruitflow;" >/dev/null
  done
}

# ---------------------------------------------------------------- app
start_app() {
  start_postgres

  echo "==> Миграции Alembic"
  (cd backend && "$PY" -m alembic upgrade head >/dev/null 2>&1) \
    || (cd backend && alembic upgrade head >/dev/null)

  echo "==> Демо-данные (пропускаются, если уже есть)"
  (cd backend && PYTHONPATH=. "$PY" -m app.seed)

  if ! curl -s -m 2 "http://127.0.0.1:$API_PORT/health" >/dev/null 2>&1; then
    echo "==> API на :$API_PORT"
    (cd backend && PYTHONPATH=. nohup "$PY" -m uvicorn app.main:app \
       --host 127.0.0.1 --port $API_PORT > "$LOG_DIR/api.log" 2>&1 &)
  fi

  if ! curl -s -m 2 -o /dev/null "http://127.0.0.1:$WEB_PORT/" 2>/dev/null; then
    echo "==> Frontend на :$WEB_PORT"
    (cd frontend && [ -d node_modules ] || npm install --no-audit --no-fund)
    (cd frontend && nohup npx vite --host 127.0.0.1 --port $WEB_PORT \
       > "$LOG_DIR/web.log" 2>&1 &)
  fi

  wait_for "http://127.0.0.1:$API_PORT/health" 40 || { echo "!! API не поднялся, лог: $LOG_DIR/api.log"; exit 1; }
  wait_for "http://127.0.0.1:$WEB_PORT/" 40 || { echo "!! Frontend не поднялся, лог: $LOG_DIR/web.log"; exit 1; }
}

# ---------------------------------------------------------------- tunnel
tunnel_url() { grep -E '^https://' "$TUNNEL_URL" 2>/dev/null | tail -1; }

tunnel_alive() {
  pgrep -f "[t]unnel-loop.sh" >/dev/null 2>&1 \
    || pgrep -f "[n]okey@localhost.run" >/dev/null 2>&1
}

start_tunnel() {
  start_app
  if tunnel_alive && [ -n "$(tunnel_url)" ]; then
    echo "==> Туннель уже работает"
    echo "    $(tunnel_url)"
    return
  fi
  echo "==> Запуск публичного туннеля (localhost.run, автопереподключение)"
  rm -f "$TUNNEL_URL"
  nohup bash "$TUNNEL_LOOP" "$WEB_PORT" "$TUNNEL_URL" "$TUNNEL_LOG" >/dev/null 2>&1 &
  echo $! > "$RUN_DIR/tunnel.pid"
  for _ in $(seq 1 90); do
    [ -n "$(tunnel_url)" ] && break
    sleep 1
  done
  if [ -z "$(tunnel_url)" ]; then
    echo "!! Не удалось получить URL, лог: $TUNNEL_LOG"
    tail -5 "$TUNNEL_LOG" 2>/dev/null
    exit 1
  fi
}

# ---------------------------------------------------------------- commands
case "${1:-start}" in
  stop)
    echo "==> Останавливаю приложения и туннель"
    alive "[u]vicorn app.main:app" && pkill -f "[u]vicorn app.main:app" || true
    alive "[n]px vite" && pkill -f "[n]px vite" || true
    alive "[v]ite --host 127.0.0.1" && pkill -f "[v]ite --host 127.0.0.1" || true
    alive "[t]unnel-loop.sh" && pkill -f "[t]unnel-loop.sh" || true
    alive "[n]okey@localhost.run" && pkill -f "[n]okey@localhost.run" || true
    sleep 1
    echo "Готово. PostgreSQL оставлен запущенным (данные в $PGDATA)."
    echo "Полная остановка: ./run-local.sh stop-all"
    ;;
  stop-all)
    pkill -f "[u]vicorn app.main:app" 2>/dev/null || true
    pkill -f "[n]px vite" 2>/dev/null || true
    pkill -f "[v]ite --host 127.0.0.1" 2>/dev/null || true
    pkill -f "[t]unnel-loop.sh" 2>/dev/null || true
    pkill -f "[n]okey@localhost.run" 2>/dev/null || true
    "$DB_DIR/bin/pg_ctl" -D "$PGDATA" stop 2>/dev/null || true
    echo "Всё остановлено."
    ;;
  tunnel)
    start_tunnel
    URL="$(tunnel_url)"
    echo
    echo "=============================================="
    echo "  ПУБЛИЧНЫЙ ДОСТУП (из любого города):"
    echo "  $URL"
    echo
    echo "  Локально:   http://localhost:$WEB_PORT"
    echo "  Вход: admin@recruitflow.local / Admin1234!"
    echo "  Пока ПК включён — сайт доступен."
    echo "  Адрес может смениться при переподключении: ./run-local.sh url"
    echo "  Стоп: ./run-local.sh stop"
    echo "=============================================="
    ;;
  url)
    URL="$(tunnel_url)"
    [ -n "$URL" ] && echo "$URL" || echo "туннель не запущен (./run-local.sh tunnel)"
    ;;
  status)
    echo "postgres: $("$DB_DIR/bin/pg_isready" -h 127.0.0.1 -p $POSTGRES_PORT 2>&1)"
    echo "api:      $(curl -s -m 2 http://127.0.0.1:$API_PORT/health 2>/dev/null || echo 'запущен — нет')"
    echo "frontend: HTTP $(curl -s -m 2 -o /dev/null -w '%{http_code}' http://127.0.0.1:$WEB_PORT/ 2>/dev/null || echo '—')"
    URL="$(tunnel_url)"
    if [ -n "$URL" ]; then echo "tunnel:   $URL"; else echo "tunnel:   не запущен"; fi
    ;;
  start|*)
    start_app
    echo
    echo "=============================================="
    echo "  RecruitFlow (локально): http://localhost:$WEB_PORT"
    echo "  API (Swagger):          http://localhost:$API_PORT/api/docs"
    echo "  Вход: admin@recruitflow.local / Admin1234!"
    echo
    echo "  Для доступа из другого города: ./run-local.sh tunnel"
    echo "  Стоп: ./run-local.sh stop"
    echo "=============================================="
    ;;
esac
