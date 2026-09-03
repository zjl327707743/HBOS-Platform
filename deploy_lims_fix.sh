#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/Users/hbzl/Vibe Coding/HBOS-Platform"
APP_DIR="$PROJECT_DIR/apps/hb_lims_app"
WEB_DIR="$PROJECT_DIR/frontend/hbos-lims-web"
DIST_DIR="$WEB_DIR/dist"
REMOTE_DIR="/home/frappe/frappe-bench/sites/frontend/public/hbos-lims"
DOCKER="/Applications/Docker.app/Contents/Resources/bin/docker"

log()  { printf '\n[HBOS-LIMS] %s\n' "$1"; }
fail() { printf '\n[HBOS-LIMS][ERROR] %s\n' "$1" >&2; exit 1; }

cd "$PROJECT_DIR"

log "1/8 Preflight: repository check"
git diff --check

log "2/8 Preflight: backend contract tests"
(
  cd "$APP_DIR"
  python3 -m pytest tests
)

log "3/8 Build production frontend"
(
  cd "$WEB_DIR"
  npm run build:prod
)

log "4/8 Docker service status"
"$DOCKER" compose ps

log "5/8 Apply Frappe migration and clear cache"
"$DOCKER" compose exec -T backend bash -lc \
  'cd /home/frappe/frappe-bench && bench --site frontend migrate'
"$DOCKER" compose exec -T backend bash -lc \
  'cd /home/frappe/frappe-bench && bench --site frontend clear-cache'

log "6/8 Backup and sync frontend production assets"
FRONTEND_ID="$("$DOCKER" compose ps -q frontend)"
[ -n "$FRONTEND_ID" ] || fail "frontend container is not running"
STAMP="$(date +%Y%m%d%H%M%S)"
if "$DOCKER" exec "$FRONTEND_ID" test -d "$REMOTE_DIR"; then
  "$DOCKER" exec "$FRONTEND_ID" cp -a "$REMOTE_DIR" "$REMOTE_DIR.bak-$STAMP"
  printf 'Backup: %s\n' "$REMOTE_DIR.bak-$STAMP"
fi
"$DOCKER" exec "$FRONTEND_ID" mkdir -p "$REMOTE_DIR"
"$DOCKER" cp "$DIST_DIR/." "$FRONTEND_ID:$REMOTE_DIR/"

log "7/8 Restart application services"
"$DOCKER" compose restart backend frontend scheduler queue-short queue-long websocket

log "8/8 HTTP smoke checks"
sleep 8
for path in /hbos-lims/ /hbos-lims/dashboard /hbos-lims/samples /hbos-lims/audit /hbos-lims/audit-log; do
  code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 "http://localhost:8080$path")"
  printf '%-28s %s\n' "$path" "$code"
  [ "$code" = "200" ] || fail "HTTP check failed for $path (status $code)"
done

printf '\n[HBOS-LIMS] Deployment completed successfully.\n'
printf 'URL: http://localhost:8080/hbos-lims/dashboard\n'
