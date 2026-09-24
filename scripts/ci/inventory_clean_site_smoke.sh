#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if [[ ! -d runtime/apps/hrms ]]; then
  echo "::error:: runtime/apps/hrms 不存在；smoke 需要 compose 中既有 HRMS 挂载可导入"
  exit 1
fi

PROJECT="${HBOS_SMOKE_PROJECT:-hbos-inventory-smoke-${GITHUB_RUN_ID:-local}}"
export COMPOSE_PROJECT_NAME="$PROJECT"
export ERPNEXT_VERSION="${ERPNEXT_VERSION:-v16.26.2}"
export SITE_NAME="${SITE_NAME:-inventory-smoke.localhost}"
export FRAPPE_SITE_NAME_HEADER="$SITE_NAME"
export HTTP_PORT="${HTTP_PORT:-18081}"
export MARIADB_HOST=db
export DB_PORT=3306
export DB_ROOT_PASSWORD="${DB_ROOT_PASSWORD:-hbos_inventory_smoke_root}"
export MYSQL_ROOT_PASSWORD="$DB_ROOT_PASSWORD"
export ADMIN_PASSWORD="${ADMIN_PASSWORD:-hbos_inventory_smoke_admin}"
export REDIS_CACHE=redis-cache:6379
export REDIS_QUEUE=redis-queue:6379
export SOCKETIO_PORT=9000
export UPSTREAM_REAL_IP_ADDRESS=127.0.0.1
export UPSTREAM_REAL_IP_HEADER=X-Forwarded-For
export UPSTREAM_REAL_IP_RECURSIVE=off
export PROXY_READ_TIMEOUT=120
export CLIENT_MAX_BODY_SIZE=50m
export FEISHU_APP_ID=""
export FEISHU_APP_SECRET=""
export DELICLOUD_APP_KEY=""
export DELICLOUD_APP_SECRET=""
export HBOS_OCR_URL=http://host.docker.internal:8100
export HBOS_OCR_SHARED_TOKEN=inventory-smoke-only-token

cleanup() {
  docker compose -p "$PROJECT" down -v --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker compose -p "$PROJECT" up -d db redis-cache redis-queue
docker compose -p "$PROJECT" run --rm configurator
docker compose -p "$PROJECT" run --rm create-site
docker compose -p "$PROJECT" up -d backend

APPS="$(docker compose -p "$PROJECT" exec -T backend bench --site "$SITE_NAME" list-apps)"
printf '%s\n' "$APPS"
for app in frappe erpnext hb_inventory_app; do
  printf '%s\n' "$APPS" | awk '{print $1}' | grep -qx "$app" || {
    echo "::error:: clean site 缺少 app: $app"
    exit 1
  }
done

echo "[Inventory] migrate twice"
docker compose -p "$PROJECT" exec -T backend bench --site "$SITE_NAME" migrate
docker compose -p "$PROJECT" exec -T backend bench --site "$SITE_NAME" migrate

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

check_column "Item" "hbos_storage_condition"
check_column "Batch" "hbos_release_status"
check_column "Batch" "hbos_lims_reference"
check_column "Batch" "hbos_release_source"
check_column "Stock Entry" "hbos_intake_batch"

echo "[Inventory] clean-site smoke PASS"
