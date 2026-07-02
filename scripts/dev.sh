#!/usr/bin/env bash
# AutoBangumi one-command dev environment
#
#   ./scripts/dev.sh up      Start the full dev stack (qB + mock RSS + backend + webui) and seed it
#   ./scripts/dev.sh down    Stop everything and remove the containers
#   ./scripts/dev.sh seed    Re-run seeding (setup wizard + fixed qB password + one RSS refresh)
#   ./scripts/dev.sh status  Health of each service
#   ./scripts/dev.sh reset   down + wipe data/config, then up again (fresh database)
#   ./scripts/dev.sh shot <url-path> <out.png>   Headless-Chrome screenshot (1440x900)
#
# Ports:
#   7892  backend API (/docs = OpenAPI)     5173  webui Vite dev server
#   18080 qBittorrent WebUI                 18888 mock RSS (/rss/mikan.xml)
#
# Dev credentials: AB admin / adminpassword123; qB fixed to admin / adminadmin.
# The backend starts with AB_DEV_NO_AUTH=1, so the browser needs no login.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEV_DIR="$ROOT/.dev"
COMPOSE_FILE="$ROOT/backend/src/test/e2e/docker-compose.test.yml"
AB_URL="http://localhost:7892"
QB_URL="http://localhost:18080"
RSS_URL="http://localhost:18888/rss/mikan.xml"
AB_USER="admin"
AB_PASS="adminpassword123"
QB_USER="admin"
QB_PASS="adminadmin"

mkdir -p "$DEV_DIR"

log() { printf '\033[1;35m[dev]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[dev]\033[0m %s\n' "$*" >&2; exit 1; }

wait_for() { # wait_for <url> <name> [tries]
  local url=$1 name=$2 tries=${3:-30}
  for _ in $(seq 1 "$tries"); do
    if curl -sf -o /dev/null "$url"; then log "$name ready"; return 0; fi
    sleep 1
  done
  die "$name not ready: $url"
}

qb_fix_password() {
  # The linuxserver image generates a temporary password on each container
  # start; pin a fixed one so AB's stored credentials survive restarts.
  local tmp_pass cookie
  if curl -sf "$QB_URL/api/v2/auth/login" \
      --data-urlencode "username=$QB_USER" --data-urlencode "password=$QB_PASS" \
      -o /dev/null -w '%{http_code}' | grep -q "200\|204"; then
    log "qB password already pinned"
    return 0
  fi
  tmp_pass=$(docker logs ab-test-qbittorrent 2>&1 \
    | grep -o 'temporary password.*: *[A-Za-z0-9]*' | tail -1 | awk '{print $NF}')
  [ -n "$tmp_pass" ] || die "could not read qB temporary password from container logs"
  # Cookie name is QBT_SID_<port> on current qB, SID on older ones.
  cookie=$(curl -sf -i "$QB_URL/api/v2/auth/login" \
    --data-urlencode "username=$QB_USER" --data-urlencode "password=$tmp_pass" \
    | grep -io '^set-cookie: *[^=]*SID[^=]*=[^;]*' | sed 's/^[Ss]et-[Cc]ookie: *//')
  [ -n "$cookie" ] || die "qB login with temporary password failed"
  curl -sf "$QB_URL/api/v2/app/setPreferences" -H "Cookie: $cookie" \
    --data-urlencode "json={\"web_ui_username\":\"$QB_USER\",\"web_ui_password\":\"$QB_PASS\",\"bypass_local_auth\":true}" \
    -o /dev/null
  log "qB password pinned to $QB_USER / $QB_PASS"
}

seed() {
  local need_setup
  need_setup=$(curl -sf "$AB_URL/api/v1/setup/status" | grep -o '"need_setup": *[a-z]*' | awk -F: '{gsub(/ /,"",$2); print $2}')
  if [ "$need_setup" != "true" ]; then
    log "already seeded (need_setup=$need_setup)"
    return 0
  fi
  qb_fix_password
  curl -sf -X POST "$AB_URL/api/v1/setup/complete" -H 'Content-Type: application/json' -d "{
    \"username\": \"$AB_USER\", \"password\": \"$AB_PASS\",
    \"downloader_type\": \"qbittorrent\",
    \"downloader_host\": \"localhost:18080\",
    \"downloader_username\": \"$QB_USER\", \"downloader_password\": \"$QB_PASS\",
    \"downloader_path\": \"/downloads/Bangumi\", \"downloader_ssl\": false,
    \"rss_url\": \"$RSS_URL\", \"rss_name\": \"Mock Mikan Feed\"
  }" -o /dev/null
  log "setup complete: AB $AB_USER/$AB_PASS, mock RSS subscribed"
  curl -sf -X POST "$AB_URL/api/v1/rss/refresh/all" -o /dev/null \
    && log "triggered an RSS refresh" || true
}

up() {
  command -v docker >/dev/null || die "Docker is required"
  command -v uv >/dev/null || die "uv is required"
  command -v pnpm >/dev/null || die "pnpm is required"

  log "starting qBittorrent + mock RSS containers..."
  docker compose -f "$COMPOSE_FILE" up -d --wait

  if ! curl -sf -o /dev/null "$AB_URL/health"; then
    log "starting backend (AB_DEV_NO_AUTH=1, :7892)..."
    (cd "$ROOT/backend/src" && mkdir -p config data \
      && AB_DEV_NO_AUTH=1 nohup uv run python main.py \
         > "$DEV_DIR/backend.log" 2>&1 & echo $! > "$DEV_DIR/backend.pid")
  else
    log "backend already running"
  fi
  wait_for "$AB_URL/health" "backend"

  if ! curl -sf -o /dev/null http://localhost:5173/; then
    log "starting webui (:5173)..."
    (cd "$ROOT/webui" && nohup pnpm dev \
       > "$DEV_DIR/webui.log" 2>&1 & echo $! > "$DEV_DIR/webui.pid")
  else
    log "webui already running"
  fi
  wait_for http://localhost:5173/ "webui"

  seed

  echo
  log "dev environment ready:"
  echo "    webui    http://localhost:5173        (AB_DEV_NO_AUTH=1, no login needed)"
  echo "    API docs $AB_URL/docs"
  echo "    qB WebUI $QB_URL              ($QB_USER / $QB_PASS)"
  echo "    mock RSS $RSS_URL"
  echo "    logs     $DEV_DIR/backend.log  $DEV_DIR/webui.log"
}

down() {
  for name in backend webui; do
    if [ -f "$DEV_DIR/$name.pid" ]; then
      pkill -P "$(cat "$DEV_DIR/$name.pid")" 2>/dev/null || true
      kill "$(cat "$DEV_DIR/$name.pid")" 2>/dev/null || true
      rm -f "$DEV_DIR/$name.pid"
      log "$name stopped"
    fi
  done
  docker compose -f "$COMPOSE_FILE" down 2>/dev/null || true
  log "containers removed"
}

status() {
  printf '%-10s' "backend:";  curl -sf "$AB_URL/health" && echo || echo "down"
  printf '%-10s' "webui:";    curl -sf -o /dev/null -w '%{http_code}\n' http://localhost:5173/ || echo "down"
  printf '%-10s' "qB:";       curl -sf -o /dev/null -w '%{http_code}\n' "$QB_URL" || echo "down"
  printf '%-10s' "mockRSS:";  curl -sf http://localhost:18888/health && echo || echo "down"
}

reset() {
  down
  rm -rf "$ROOT/backend/src/data" "$ROOT/backend/src/config"
  log "data/config wiped"
  up
}

shot() { # shot <url-path> <out.png> - fallback screenshot when agent-browser misbehaves
  local path=${1:?usage: dev.sh shot <url-path> <out.png>} out=${2:?}
  local chrome profile
  # Prefer system Chrome: the bundled Chrome-for-Testing hangs on
  # Page.captureScreenshot on macOS (July 2026 investigation).
  chrome="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
  [ -x "$chrome" ] || chrome=$(ls -d "$HOME/.agent-browser/browsers/"chrome-*/"Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing" 2>/dev/null | tail -1)
  profile=$(mktemp -d)
  "$chrome" --headless=new --no-first-run --user-data-dir="$profile" \
    --window-size=1440,900 --hide-scrollbars --virtual-time-budget=8000 \
    --screenshot="$out" "http://localhost:5173/#${path}" 2>/dev/null
  rm -rf "$profile"
  log "screenshot: $out"
}

case "${1:-}" in
  up) up ;;
  down) down ;;
  seed) seed ;;
  status) status ;;
  reset) reset ;;
  shot) shift; shot "$@" ;;
  *) sed -n '2,16p' "$0"; exit 1 ;;
esac
