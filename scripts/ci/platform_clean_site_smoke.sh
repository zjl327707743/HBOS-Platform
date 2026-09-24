#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

test -d runtime/apps/hrms || {
  echo "::error:: runtime/apps/hrms missing"
  exit 1
}

PROJECT="${HBOS_SMOKE_PROJECT:-hbos-platform-smoke-${GITHUB_RUN_ID:-local}}"
export COMPOSE_PROJECT_NAME="$PROJECT"
export ERPNEXT_VERSION="${ERPNEXT_VERSION:-v16.26.2}"
export SITE_NAME="${SITE_NAME:-platform-smoke.localhost}"
export FRAPPE_SITE_NAME_HEADER="$SITE_NAME"
export HTTP_PORT="${HTTP_PORT:-18090}"
export MARIADB_HOST=db
export DB_PORT=3306
export DB_ROOT_PASSWORD="${DB_ROOT_PASSWORD:-hbos_smoke_root}"
export MYSQL_ROOT_PASSWORD="$DB_ROOT_PASSWORD"
export ADMIN_PASSWORD="${ADMIN_PASSWORD:-hbos_smoke_admin}"
export REDIS_CACHE=redis-cache:6379
export REDIS_QUEUE=redis-queue:6379
export SOCKETIO_PORT=9000
export UPSTREAM_REAL_IP_ADDRESS=127.0.0.1
export UPSTREAM_REAL_IP_HEADER=X-Forwarded-For
export UPSTREAM_REAL_IP_RECURSIVE=off
export PROXY_READ_TIMEOUT=120
export CLIENT_MAX_BODY_SIZE=50m

# All real outbound integrations are disabled in platform CI.
export HBOS_FEISHU_SYNC_ENABLED=0
export HBOS_DELICLOUD_SYNC_ENABLED=0
export HBOS_AI_ENABLED=0
export HBOS_AI_ALLOW_PII=0
export FEISHU_APP_ID=""
export FEISHU_APP_SECRET=""
export HBOS_FEISHU_LEAVE_APP_TOKEN=""
export HBOS_FEISHU_LEAVE_TABLE_ID=""
export HBOS_FEISHU_OVERTIME_APP_TOKEN=""
export HBOS_FEISHU_OVERTIME_TABLE_ID=""
export HBOS_FEISHU_REST_LEAVE_APP_TOKEN=""
export HBOS_FEISHU_REST_LEAVE_TABLE_ID=""
export HBOS_FEISHU_EXCEPTION_APP_TOKEN=""
export HBOS_FEISHU_EXCEPTION_TABLE_ID=""
export DELICLOUD_APP_KEY=""
export DELICLOUD_APP_SECRET=""
export HBOS_NOTIFY_WEBHOOK_URL=""
export HBOS_NOTIFY_DRY_RUN=1
export HBOS_AI_BASE_URL=""
export HBOS_AI_API_KEY=""
export HBOS_AI_MODEL=""
export HBOS_AI_TIMEOUT=60
export HBOS_OCR_URL="http://host.docker.internal:8100"
export HBOS_OCR_SHARED_TOKEN="platform-smoke-token"

cleanup() {
  docker compose -p "$PROJECT" down -v --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[PLATFORM] prepare reproducible Chinese fonts"
scripts/setup_fonts.sh

echo "[PLATFORM] start isolated dependencies"
docker compose -p "$PROJECT" up -d db redis-cache redis-queue
docker compose -p "$PROJECT" run --rm configurator
docker compose -p "$PROJECT" run --rm create-site
docker compose -p "$PROJECT" up -d backend

echo "[PLATFORM] verify installed apps"
APPS="$(docker compose -p "$PROJECT" exec -T backend bench --site "$SITE_NAME" list-apps)"
printf '%s\n' "$APPS"
for app in frappe erpnext hrms hb_attendance_app hb_inventory_app hb_lims_app hbos_portal; do
  printf '%s\n' "$APPS" | awk '{print $1}' | grep -qx "$app" || {
    echo "::error:: platform clean site missing app: $app"
    exit 1
  }
done

echo "[PLATFORM] double migrate"
docker compose -p "$PROJECT" exec -T backend bench --site "$SITE_NAME" migrate
docker compose -p "$PROJECT" exec -T backend bench --site "$SITE_NAME" migrate

echo "[PLATFORM] Portal Registry + LIMS provider"
docker compose -p "$PROJECT" exec -T \
  -e HBOS_PORTAL_INTEGRATION_CHECKS=1 \
  backend bench --site "$SITE_NAME" execute hbos_portal.integration_checks.run

echo "[PLATFORM] LIMS stable deep-link projection"
docker compose -p "$PROJECT" exec -T \
  -e HBOS_PORTAL_INTEGRATION_CHECKS=1 \
  backend bench --site "$SITE_NAME" execute hb_lims_app.hbos_lims.portal.integration_checks.run

echo "[PLATFORM] Attendance Portal provider"
docker compose -p "$PROJECT" exec -T \
  -e HBOS_PORTAL_INTEGRATION_CHECKS=1 \
  backend bench --site "$SITE_NAME" execute hb_attendance_app.hbos_attendance.portal.integration_checks.run

echo "[PLATFORM] verify Chinese font inside backend"
docker compose -p "$PROJECT" exec -T backend bash -lc \
  'test -r /usr/share/fonts/truetype/hbos/NotoSerifSC-Regular.otf && test -r /usr/share/fonts/truetype/hbos/NotoSerifSC-Bold.otf' || {
  echo "::error:: Noto font files are not readable inside backend"
  docker compose -p "$PROJECT" exec -T backend bash -lc 'ls -la /usr/share/fonts/truetype/hbos || true'
  exit 1
}
docker compose -p "$PROJECT" exec -T backend bash -lc \
  'fc-cache -f /usr/share/fonts/truetype/hbos >/dev/null 2>&1 || fc-cache -f >/dev/null 2>&1'
docker compose -p "$PROJECT" exec -T backend bash -lc \
  'fc-list :lang=zh 2>/dev/null | grep -qiE "NotoSerifSC|Noto Serif SC"' || {
  echo "::error:: backend cannot see Noto Serif SC"
  exit 1
}

echo "[PLATFORM] Attendance G1 DB checks"
docker compose -p "$PROJECT" exec -T -e HBOS_G1_INTEGRATION_CHECKS=1 backend   bench --site "$SITE_NAME" execute hb_attendance_app.hbos_attendance.g1_integration_checks.run

echo "[PLATFORM] LIMS + Inventory release chain"
docker compose -p "$PROJECT" exec -T -e HBOS_G3_INTEGRATION_CHECKS=1 backend   bench --site "$SITE_NAME" execute hb_lims_app.hbos_lims.g3_integration_checks.verify_schema
docker compose -p "$PROJECT" exec -T -e HBOS_G3_INTEGRATION_CHECKS=1 backend   bench --site "$SITE_NAME" execute hb_lims_app.hbos_lims.g3_integration_checks.run

echo "[PLATFORM] prepare HBOS web assets + LIMS production bundle"
scripts/prepare_hbos_web.sh

echo "[PLATFORM] verify HBOS web assets + LIMS production entry"
docker compose -p "$PROJECT" up -d --no-deps websocket frontend

wait_http() {
  local path="$1"
  local output="$2"
  for _ in $(seq 1 60); do
    if curl -fsS -H "Host: $SITE_NAME" "http://127.0.0.1:$HTTP_PORT$path" > "$output"; then
      return 0
    fi
    sleep 2
  done
  echo "::error:: timed out waiting for $path"
  docker compose -p "$PROJECT" ps
  docker compose -p "$PROJECT" logs --no-color --tail=120 frontend backend hbos-web-prepare || true
  return 1
}

wait_http "/hbos-lims/dashboard" /tmp/hbos-lims-dashboard.html
grep -q 'lims_spa_loader.js' /tmp/hbos-lims-dashboard.html || {
  echo "::error:: /hbos-lims/dashboard did not render the HBOS LIMS SPA shell"
  exit 1
}
wait_http "/hbos-lims/tasks" /tmp/hbos-lims-tasks.html
grep -q 'lims_spa_loader.js' /tmp/hbos-lims-tasks.html || {
  echo "::error:: /hbos-lims/tasks did not resolve to the SPA shell"
  exit 1
}
wait_http "/hbos-lims/stability" /tmp/hbos-lims-stability.html
grep -q 'lims_spa_loader.js' /tmp/hbos-lims-stability.html || {
  echo "::error:: /hbos-lims/stability did not resolve to the SPA shell"
  exit 1
}

curl -fsS -H "Host: $SITE_NAME"   "http://127.0.0.1:$HTTP_PORT/assets/hb_attendance_app/hbos-attendance-logo.svg" >/dev/null
curl -fsS -H "Host: $SITE_NAME"   "http://127.0.0.1:$HTTP_PORT/assets/hb_lims_app/hbos-lims-logo.svg" >/dev/null
curl -fsS -H "Host: $SITE_NAME"   "http://127.0.0.1:$HTTP_PORT/assets/hb_lims_app/hbos-lims/.vite/manifest.json"   > /tmp/hbos-lims-manifest.json

ENTRY_FILE="$(python3 - <<'PY'
import json
with open("/tmp/hbos-lims-manifest.json", encoding="utf-8") as handle:
    manifest = json.load(handle)
entry = manifest.get("index.html") or next(
    (item for item in manifest.values() if item.get("isEntry")),
    None,
)
if not entry or not entry.get("file"):
    raise SystemExit("LIMS Vite manifest has no entry")
print(entry["file"])
PY
)"
curl -fsS -H "Host: $SITE_NAME"   "http://127.0.0.1:$HTTP_PORT/assets/hb_lims_app/hbos-lims/$ENTRY_FILE" >/dev/null

echo "[PLATFORM] frontend recreation must preserve LIMS production assets"
docker compose -p "$PROJECT" up -d --force-recreate --no-deps frontend
wait_http "/hbos-lims/dashboard" /tmp/hbos-lims-dashboard-after-recreate.html
grep -q 'lims_spa_loader.js' /tmp/hbos-lims-dashboard-after-recreate.html || {
  echo "::error:: LIMS SPA shell disappeared after frontend recreation"
  exit 1
}
curl -fsS -H "Host: $SITE_NAME"   "http://127.0.0.1:$HTTP_PORT/assets/hb_lims_app/hbos-lims/$ENTRY_FILE" >/dev/null

echo "HBOS PLATFORM clean-site integration PASS"
