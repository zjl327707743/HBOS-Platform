#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"

fail() {
  echo "HBOS Portal local start failed: $*" >&2
  exit 1
}

read_env() {
  grep -E "^$1=" .env | tail -n 1 | cut -d= -f2- | tr -d "\r" || true
}

[[ -f .env ]] || fail "缺少 .env"
[[ -d frontend/hbos-portal-web ]] || fail "缺少 frontend/hbos-portal-web"
[[ -d apps/hbos_portal ]] || fail "缺少 apps/hbos_portal"

SITE_NAME="$(read_env SITE_NAME)"
HTTP_PORT="$(read_env HTTP_PORT)"
PORTAL_DEV_PORT="${PORTAL_DEV_PORT:-5178}"

[[ -n "$SITE_NAME" ]] || fail ".env 中 SITE_NAME 为空"
[[ -n "$HTTP_PORT" ]] || fail ".env 中 HTTP_PORT 为空"

BASE_URL="http://127.0.0.1:$HTTP_PORT"
PORTAL_URL="http://127.0.0.1:$PORTAL_DEV_PORT"

echo "==> 启动 Frappe / ERPNext / HBOS 运行服务"
docker compose config --quiet
docker compose up -d backend frontend queue-long queue-short scheduler websocket

echo "==> 刷新 apps.txt"
docker compose run --rm configurator >/dev/null

echo "==> 确保 hbos_portal 已安装到 $SITE_NAME"
if ! docker compose exec -T backend bash -lc "bench --site \"$SITE_NAME\" list-apps" | awk '{print $1}' | grep -qx "hbos_portal"; then
  docker compose exec -T backend bash -lc "bench --site \"$SITE_NAME\" install-app hbos_portal"
fi

echo "==> 验证三业务 Provider 已注册"
docker compose exec -T backend bash -lc "SITE_NAME='$SITE_NAME' python - <<'PY'
import os
import frappe
from hbos_portal.services.registry import build_registry

site = os.environ['SITE_NAME']
frappe.init(site=site)
frappe.connect()
try:
    frappe.set_user('Administrator')
    registry = build_registry()
    assert not registry.failures, registry.failures
    assert sorted(registry.entries) == ['attendance', 'inventory', 'lims']
    print('Portal Registry:', sorted(registry.entries))
finally:
    frappe.destroy()
PY"

command -v node >/dev/null 2>&1 || fail "本机缺少 Node.js"
command -v npm >/dev/null 2>&1 || fail "本机缺少 npm"

cd frontend/hbos-portal-web
if [[ ! -d node_modules ]]; then
  echo "==> 安装 Portal 前端依赖（不生成 package-lock）"
  npm install --no-audit --no-fund --package-lock=false
fi

echo
echo "HBOS Portal 开发工作台"
echo "Frappe: $BASE_URL"
echo "Portal: $PORTAL_URL"
echo "数据模式: frappe"
echo "按 Ctrl+C 仅停止 Portal Vite；Docker 业务服务保持运行。"
echo

VITE_PORTAL_DATA_MODE=frappe \
VITE_FRAPPE_PROXY_TARGET="$BASE_URL" \
exec npm run dev -- --host 127.0.0.1 --port "$PORTAL_DEV_PORT" --strictPort
