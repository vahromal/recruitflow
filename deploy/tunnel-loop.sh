#!/usr/bin/env bash
# Persistent public tunnel to a local port via localhost.run (anonymous, no account).
#
#   tunnel-loop.sh <local_port> <url_file> <log_file>
#
# - reconnects automatically when the session drops or expires;
# - pings the tunnel every 60 s so the provider does not drop it as idle;
# - rewrites <url_file> whenever the public URL changes (anonymous URLs rotate).
set -u

PORT="${1:?local port required}"
URL_FILE="${2:?url file required}"
LOG="${3:?log file required}"

mkdir -p "$(dirname "$URL_FILE")" "$(dirname "$LOG")"

url_regex='https://[a-z0-9]+\.lhr\.life'

while true; do
  tmp="$(mktemp)"
  ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 \
      -o ServerAliveInterval=30 -o ServerAliveCountMax=4 \
      -R 80:127.0.0.1:"$PORT" nokey@localhost.run < /dev/null > "$tmp" 2>&1 &
  ssh_pid=$!

  # --- wait for the public URL (usually <5 s) ---
  url=""
  for _ in $(seq 1 60); do
    url="$(grep -oE "$url_regex" "$tmp" 2>/dev/null | head -1)"
    [ -n "$url" ] && break
    kill -0 "$ssh_pid" 2>/dev/null || break
    sleep 1
  done

  if [ -n "$url" ]; then
    printf '%s\n' "$url" > "$URL_FILE"
    printf '%s [%s] connected: %s\n' "$(date '+%F %T')" "$$" "$url" >> "$LOG"
    # --- keepalive + dead-URL detection ---
    # Anonymous forwards expire in ~11 minutes even while ssh stays up,
    # so a failing URL forces a reconnect (fresh URL follows).
    fails=0
    while kill -0 "$ssh_pid" 2>/dev/null; do
      code=$(curl -s -m 10 -o /dev/null -w '%{http_code}' "$url/health" 2>/dev/null || echo 000)
      if [ "$code" = "200" ]; then
        fails=0
      else
        fails=$((fails + 1))
        if [ "$fails" -ge 2 ]; then
          printf '%s [%s] URL dead (code=%s), forcing reconnect\n' "$(date '+%F %T')" "$$" "$code" >> "$LOG"
          kill "$ssh_pid" 2>/dev/null
          break
        fi
      fi
      sleep 30
    done
  else
    printf '%s [%s] no URL received, ssh exited\n' "$(date '+%F %T')" "$$" >> "$LOG"
  fi

  wait "$ssh_pid" 2>/dev/null
  rc=$?
  cat "$tmp" >> "$LOG"
  rm -f "$tmp"
  printf '%s [%s] disconnected (rc=%s), reconnecting in 5 s\n' "$(date '+%F %T')" "$$" "$rc" >> "$LOG"

  # keep the log from growing forever
  if [ -f "$LOG" ] && [ "$(wc -c < "$LOG")" -gt 500000 ]; then
    tail -c 200000 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
  fi

  sleep 5
done
