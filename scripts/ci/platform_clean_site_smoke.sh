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
for app in frappe erpnext hrms hb_attendance_app hb_inventory_app hb_lims_app; do
  printf '%s\n' "$APPS" | awk '{print $1}' | grep -qx "$app" || {
    echo "::error:: platform clean site missing app: $app"
    exit 1
  }
done

echo "[PLATFORM] double migrate"
docker compose -p "$PROJECT" exec -T backend bench --site "$SITE_NAME" migrate
docker compose -p "$PROJECT" exec -T backend bench --site "$SITE_NAME" migrate

echo "[PLATFORM] verify Chinese font inside backend"
docker compose -p "$PROJECT" exec -T backend bash -lc   'fc-list :lang=zh 2>/dev/null | grep -qi "Noto Serif SC\|NotoSerifSC"' || {
  echo "::error:: backend cannot see Noto Serif SC"
  exit 1
}

echo "[PLATFORM] Attendance G1 DB checks"
docker compose -p "$PROJECT" exec -T -e HBOS_G1_INTEGRATION_CHECKS=1 backend   bench --site "$SITE_NAME" execute hb_attendance_app.hbos_attendance.g1_integration_checks.run

echo "[PLATFORM] LIMS + Inventory release chain"
docker compose -p "$PROJECT" exec -T -e HBOS_G3_INTEGRATION_CHECKS=1 backend   bench --site "$SITE_NAME" execute hb_lims_app.hbos_lims.g3_integration_checks.verify_schema
docker compose -p "$PROJECT" exec -T -e HBOS_G3_INTEGRATION_CHECKS=1 backend   bench --site "$SITE_NAME" execute hb_lims_app.hbos_lims.g3_integration_checks.run

echo "HBOS PLATFORM clean-site integration PASS"
