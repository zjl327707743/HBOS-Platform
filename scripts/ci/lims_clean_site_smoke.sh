#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

test -d runtime/apps/hrms || {
  echo "::error:: runtime/apps/hrms missing"
  exit 1
}

PROJECT="${HBOS_SMOKE_PROJECT:-hbos-lims-smoke-${GITHUB_RUN_ID:-local}}"
export COMPOSE_PROJECT_NAME="$PROJECT"
export ERPNEXT_VERSION="${ERPNEXT_VERSION:-v16.26.2}"
export SITE_NAME="${SITE_NAME:-lims-smoke.localhost}"
export FRAPPE_SITE_NAME_HEADER="$SITE_NAME"
export HTTP_PORT="${HTTP_PORT:-18082}"
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

DC=(docker compose -f docker-compose.yml -f scripts/ci/docker-compose.lims-ci.yml -p "$PROJECT")

cleanup() {
  "${DC[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT

"${DC[@]}" up -d db redis-cache redis-queue
"${DC[@]}" run --rm configurator
"${DC[@]}" run --rm create-site
"${DC[@]}" up -d backend

APPS="$("${DC[@]}" exec -T backend bench --site "$SITE_NAME" list-apps)"
printf '%s\n' "$APPS"
for app in frappe erpnext hrms hb_attendance_app hb_inventory_app hb_lims_app; do
  printf '%s\n' "$APPS" | awk '{print $1}' | grep -qx "$app" || {
    echo "::error:: clean site missing app: $app"
    exit 1
  }
done

"${DC[@]}" exec -T backend bench --site "$SITE_NAME" migrate
"${DC[@]}" exec -T backend bench --site "$SITE_NAME" migrate

check_column() {
  local doctype="$1" field="$2"
  local out
  out="$("${DC[@]}" exec -T backend bench --site "$SITE_NAME" execute frappe.db.has_column --args "[\"$doctype\",\"$field\"]")"
  printf '%s\n' "$out" | grep -q "True" || {
    echo "::error:: missing column $doctype.$field"
    exit 1
  }
}
check_column "HBOS Sample" "item_ref"
check_column "HBOS Sample" "batch_ref"
check_column "HBOS Test Result" "approved_signature"
check_column "Batch" "hbos_lims_reference"
check_column "Batch" "hbos_release_source"

"${DC[@]}" exec -T -e HBOS_G3_INTEGRATION_CHECKS=1 backend   bench --site "$SITE_NAME" execute hb_lims_app.hbos_lims.g3_integration_checks.run

echo "HBOS LIMS clean-site integration PASS"
