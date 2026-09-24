#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if [[ ! -d runtime/apps/hrms ]]; then
  echo "::error:: runtime/apps/hrms 不存在；clean-site smoke 需要与 ERPNext v16 匹配的 HRMS 源码"
  exit 1
fi

PROJECT="${HBOS_SMOKE_PROJECT:-hbos-attendance-smoke-${GITHUB_RUN_ID:-local}}"
export COMPOSE_PROJECT_NAME="$PROJECT"
export ERPNEXT_VERSION="${ERPNEXT_VERSION:-v16.26.2}"
export SITE_NAME="${SITE_NAME:-attendance-smoke.localhost}"
export FRAPPE_SITE_NAME_HEADER="$SITE_NAME"
export HTTP_PORT="${HTTP_PORT:-18080}"
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

# All real outbound integrations remain disabled in the smoke environment.
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
export HBOS_AI_BASE_URL=""
export HBOS_AI_API_KEY=""
export HBOS_AI_MODEL=""
export HBOS_AI_TIMEOUT=60
export HBOS_NOTIFY_WEBHOOK_URL=""
export HBOS_NOTIFY_DRY_RUN=1

cleanup() {
  docker compose -p "$PROJECT" down -v --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[G1] start isolated dependencies: $PROJECT"
docker compose -p "$PROJECT" up -d db redis-cache redis-queue
docker compose -p "$PROJECT" run --rm configurator
docker compose -p "$PROJECT" run --rm create-site

docker compose -p "$PROJECT" up -d backend

echo "[G1] verify required apps"
APPS="$(docker compose -p "$PROJECT" exec -T backend bench --site "$SITE_NAME" list-apps)"
printf '%s\n' "$APPS"
for app in frappe erpnext hrms hb_attendance_app; do
  printf '%s\n' "$APPS" | awk '{print $1}' | grep -qx "$app" || {
    echo "::error:: clean site 缺少 app: $app"
    exit 1
  }
done

echo "[G1] migrate twice to prove idempotency"
docker compose -p "$PROJECT" exec -T backend bench --site "$SITE_NAME" migrate
docker compose -p "$PROJECT" exec -T backend bench --site "$SITE_NAME" migrate

echo "[G1] verify critical custom fields"
check_column() {
  local doctype="$1"
  local field="$2"
  local out
  out="$(docker compose -p "$PROJECT" exec -T backend bench --site "$SITE_NAME" execute frappe.db.has_column --args "[\"$doctype\",\"$field\"]")"
  printf '%s\n' "$out"
  printf '%s\n' "$out" | grep -qiE '^true$' || {
    echo "::error:: missing custom field: $doctype.$field"
    exit 1
  }
}
check_column "Employee" "hbos_fixed_shift_code"
check_column "Employee Checkin" "hbos_terminal_sn"
check_column "Employee Checkin" "hbos_check_type"
check_column "Attendance" "hbos_missing_out"

echo "[G1] run DB rollback/idempotency + policy seed rehearsal"
CHECKS="$(docker compose -p "$PROJECT" exec -T -e HBOS_G1_INTEGRATION_CHECKS=1 backend \
  bench --site "$SITE_NAME" execute hb_attendance_app.hbos_attendance.g1_integration_checks.run)"
printf '%s\n' "$CHECKS"
printf '%s\n' "$CHECKS" | grep -q "'ok': True" || {
  echo "::error:: G1 DB integration checks did not report success"
  exit 1
}

echo "[G1] clean-site smoke PASS"
