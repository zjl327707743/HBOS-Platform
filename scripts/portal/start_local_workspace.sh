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
# 走 `bench console`，不要裸调 python：镜像里的 `python` 是系统解释器（import frappe
# 直接 ModuleNotFoundError），而 `./env/bin/python` 虽能 import，但没经过 bench 的
# 环境准备，frappe.init 会因站点路径解析不到、日志目录落到 /home/frappe/logs 而失败。
# console 不会把异常转成非零退出码，所以用哨兵串判定，再由 grep 决定成败。
registry_out="$(docker compose exec -T backend bash -lc "bench --site \"$SITE_NAME\" console" <<'PY'
import frappe

frappe.set_user("Administrator")
from hbos_portal.services.registry import build_registry

registry = build_registry()
print("HBOS_REGISTRY_FAILURES=", registry.failures)
print("HBOS_REGISTRY_ENTRIES=", sorted(registry.entries))
PY
)"
grep -qF "HBOS_REGISTRY_FAILURES= []" <<<"$registry_out" || fail "Portal Registry 存在失败项：$registry_out"
grep -qF "HBOS_REGISTRY_ENTRIES= ['attendance', 'inventory', 'lims']" <<<"$registry_out" || fail "Portal Registry 条目不符合预期：$registry_out"
grep -F "HBOS_REGISTRY_" <<<"$registry_out"

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
VITE_FRAPPE_APP_ORIGIN="$BASE_URL" \
exec npm run dev -- --host 127.0.0.1 --port "$PORTAL_DEV_PORT" --strictPort
