#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"

fail() {
  echo "P3 WORKSPACE FAIL: $*" >&2
  exit 1
}

info() {
  echo
  echo "==> $*"
}

read_env() {
  grep -E "^$1=" .env | tail -n 1 | cut -d= -f2- | tr -d "\r" || true
}

[[ -f .env ]] || fail "缺少 .env；请使用本机现有私有配置，不要提交真实密钥。"
[[ -d apps/hbos_portal ]] || fail "缺少 apps/hbos_portal"
[[ -d apps/hb_attendance_app ]] || fail "缺少 apps/hb_attendance_app"
[[ -d apps/hb_inventory_app ]] || fail "缺少 apps/hb_inventory_app"
[[ -d apps/hb_lims_app ]] || fail "缺少 apps/hb_lims_app"
[[ -d frontend/hbos-portal-web ]] || fail "缺少 frontend/hbos-portal-web"

SITE_NAME="$(read_env SITE_NAME)"
HTTP_PORT="$(read_env HTTP_PORT)"
ADMIN_PASSWORD="$(read_env ADMIN_PASSWORD)"
PORTAL_DEV_PORT="${PORTAL_DEV_PORT:-5178}"

[[ -n "$SITE_NAME" ]] || fail ".env 中 SITE_NAME 为空"
[[ -n "$HTTP_PORT" ]] || fail ".env 中 HTTP_PORT 为空"
[[ -n "$ADMIN_PASSWORD" ]] || fail ".env 中 ADMIN_PASSWORD 为空"
[[ "$ADMIN_PASSWORD" != "<LOCAL_ADMIN_PASSWORD>" ]] || fail ".env 中 ADMIN_PASSWORD 仍是占位符"

BASE_URL="http://127.0.0.1:$HTTP_PORT"
PORTAL_URL="http://127.0.0.1:$PORTAL_DEV_PORT"

COOKIE_FILE="$(mktemp)"
PASS_FILE="$(mktemp)"
LOGIN_BODY="$(mktemp)"
BOOTSTRAP_BODY="$(mktemp)"
SUMMARY_BODY="$(mktemp)"
ROUTE_BODY="$(mktemp)"
VITE_BOOTSTRAP_BODY="$(mktemp)"
VITE_HTML="$(mktemp)"
VITE_LOG="$(mktemp)"
VITE_PID=""

cleanup() {
  if [[ -n "$VITE_PID" ]] && kill -0 "$VITE_PID" >/dev/null 2>&1; then
    kill "$VITE_PID" >/dev/null 2>&1 || true
    wait "$VITE_PID" >/dev/null 2>&1 || true
  fi
  rm -f \
    "$COOKIE_FILE" "$PASS_FILE" "$LOGIN_BODY" "$BOOTSTRAP_BODY" \
    "$SUMMARY_BODY" "$ROUTE_BODY" "$VITE_BOOTSTRAP_BODY" "$VITE_HTML" "$VITE_LOG"
}
trap cleanup EXIT
chmod 600 "$PASS_FILE"
printf '%s' "$ADMIN_PASSWORD" > "$PASS_FILE"

info "1/9 校验 Compose 配置与启动核心服务"
docker compose config --quiet
docker compose up -d backend frontend queue-long queue-short scheduler websocket

info "2/9 刷新 apps.txt，并确保 hbos_portal 已安装"
docker compose run --rm configurator >/dev/null
if ! docker compose exec -T backend bash -lc "bench --site \"$SITE_NAME\" list-apps" | awk '{print $1}' | grep -qx "hbos_portal"; then
  docker compose exec -T backend bash -lc "bench --site \"$SITE_NAME\" install-app hbos_portal"
fi

info "3/9 验证站点七个 App"
APPS="$(docker compose exec -T backend bash -lc "bench --site \"$SITE_NAME\" list-apps")"
printf '%s\n' "$APPS"
for app in frappe erpnext hrms hb_attendance_app hb_inventory_app hb_lims_app hbos_portal; do
  printf '%s\n' "$APPS" | awk '{print $1}' | grep -qx "$app" || fail "站点缺少 App: $app"
done

info "4/9 验证三业务 Provider + Portal dispatcher"
docker compose exec -T backend bash -lc "SITE_NAME='$SITE_NAME' python - <<'PY'
import os
import frappe

from hbos_portal.services.bootstrap import build_bootstrap
from hbos_portal.services.dispatcher import dispatch_provider
from hbos_portal.services.registry import build_registry
from hbos_portal.services.routes import resolve_stable_route

site = os.environ['SITE_NAME']
frappe.init(site=site)
frappe.connect()

try:
    frappe.set_user('Administrator')

    registry = build_registry()
    assert not registry.failures, registry.failures
    assert sorted(registry.entries) == ['attendance', 'inventory', 'lims']

    expected_caps = {
        'attendance': ['summary'],
        'inventory': ['summary'],
        'lims': ['summary', 'tasks', 'search'],
    }
    for app_id, caps in expected_caps.items():
        assert registry.entries[app_id].manifest.to_dict()['capabilities'] == caps

    bootstrap = build_bootstrap()
    app_ids = sorted(app['manifest']['id'] for app in bootstrap['apps'])
    assert app_ids == ['attendance', 'inventory', 'lims']

    inventory = dispatch_provider('inventory', 'summary')['data']
    assert inventory['app_id'] == 'inventory'
    assert len(inventory['metrics']) == 4

    assert resolve_stable_route('attendance', '/hbos/attendance')['resolved_path'] == '/app/hbos-attendance-dashboard'
    assert resolve_stable_route('inventory', '/hbos/inventory')['resolved_path'] == '/app/hbos-photo-intake'
    assert resolve_stable_route('lims', '/hbos/lims')['resolved_path'] == '/hbos-lims/dashboard'

    print('registry_entries =', sorted(registry.entries))
    print('bootstrap_apps =', app_ids)
    print('inventory_summary_metrics =', len(inventory['metrics']))
finally:
    frappe.destroy()
PY"

info "5/9 验证 Frappe HTTP 与 Administrator Session"
LOGIN_CODE="$(curl -sS -o "$LOGIN_BODY" -w '%{http_code}' -c "$COOKIE_FILE" \
  -X POST \
  --data-urlencode 'usr=Administrator' \
  --data-urlencode "pwd@$PASS_FILE" \
  "$BASE_URL/api/method/login" || true)"
[[ "$LOGIN_CODE" == "200" ]] || {
  cat "$LOGIN_BODY" >&2
  fail "Administrator 登录失败，HTTP $LOGIN_CODE"
}

BOOTSTRAP_CODE="$(curl -sS -o "$BOOTSTRAP_BODY" -w '%{http_code}' -b "$COOKIE_FILE" \
  "$BASE_URL/api/method/hbos_portal.api.bootstrap.get_bootstrap" || true)"
[[ "$BOOTSTRAP_CODE" == "200" ]] || fail "Portal Bootstrap HTTP $BOOTSTRAP_CODE"

python3 - "$BOOTSTRAP_BODY" <<'PY'
import json
import sys

with open(sys.argv[1], encoding='utf-8') as handle:
    payload = json.load(handle)
message = payload.get('message') or {}
assert message.get('ok') is True, payload
data = message.get('data') or {}
apps = sorted(app['manifest']['id'] for app in data.get('apps') or [])
assert apps == ['attendance', 'inventory', 'lims'], apps
print('HTTP bootstrap apps =', apps)
PY

info "6/9 验证三 APP Stable Route HTTP"
for spec in \
  "attendance|/hbos/attendance|/app/hbos-attendance-dashboard" \
  "inventory|/hbos/inventory|/app/hbos-photo-intake" \
  "lims|/hbos/lims|/hbos-lims/dashboard"; do
  IFS='|' read -r app_id stable_path expected_path <<<"$spec"
  curl -sS -o "$ROUTE_BODY" -b "$COOKIE_FILE" --get \
    --data-urlencode "app_id=$app_id" \
    --data-urlencode "stable_path=$stable_path" \
    "$BASE_URL/api/method/hbos_portal.api.routes.resolve_route"
  python3 - "$ROUTE_BODY" "$expected_path" <<'PY'
import json
import sys

with open(sys.argv[1], encoding='utf-8') as handle:
    payload = json.load(handle)
message = payload.get('message') or {}
assert message.get('ok') is True, payload
resolved = (message.get('data') or {}).get('resolved_path')
assert resolved == sys.argv[2], (resolved, sys.argv[2])
PY
done

info "7/9 验证 Inventory Summary HTTP"
curl -sS -o "$SUMMARY_BODY" -b "$COOKIE_FILE" --get \
  --data-urlencode "app_id=inventory" \
  "$BASE_URL/api/method/hbos_portal.api.summary.get_summary"
python3 - "$SUMMARY_BODY" <<'PY'
import json
import sys

with open(sys.argv[1], encoding='utf-8') as handle:
    payload = json.load(handle)
message = payload.get('message') or {}
assert message.get('ok') is True, payload
dispatch = message.get('data') or {}
summary = dispatch.get('data') or {}
assert summary.get('app_id') == 'inventory', summary
metrics = summary.get('metrics') or []
assert len(metrics) == 4, metrics
print('Inventory summary metric ids =', [item.get('id') for item in metrics])
PY

info "8/9 启动 Portal Vue（真实 Frappe 模式）并验证页面"
command -v node >/dev/null 2>&1 || fail "本机缺少 Node.js"
command -v npm >/dev/null 2>&1 || fail "本机缺少 npm"

(
  cd frontend/hbos-portal-web
  npm install --no-audit --no-fund --package-lock=false >/dev/null
  VITE_PORTAL_DATA_MODE=frappe \
  VITE_FRAPPE_PROXY_TARGET="$BASE_URL" \
  npm run dev -- --host 127.0.0.1 --port "$PORTAL_DEV_PORT" --strictPort
) >"$VITE_LOG" 2>&1 &
VITE_PID="$!"

VITE_READY=0
for _ in $(seq 1 30); do
  if curl -fsS "$PORTAL_URL/" > "$VITE_HTML"; then
    VITE_READY=1
    break
  fi
  if ! kill -0 "$VITE_PID" >/dev/null 2>&1; then
    cat "$VITE_LOG" >&2
    fail "Portal Vite 提前退出"
  fi
  sleep 1
done
[[ "$VITE_READY" == "1" ]] || {
  cat "$VITE_LOG" >&2
  fail "Portal Vite 未就绪"
}
grep -q 'id="app"' "$VITE_HTML" || fail "Portal HTML 未包含 Vue mount 节点"

info "9/9 验证 Vite 代理携带同一 Frappe Session"
VITE_BOOTSTRAP_CODE="$(curl -sS -o "$VITE_BOOTSTRAP_BODY" -w '%{http_code}' -b "$COOKIE_FILE" \
  "$PORTAL_URL/api/method/hbos_portal.api.bootstrap.get_bootstrap" || true)"
[[ "$VITE_BOOTSTRAP_CODE" == "200" ]] || {
  cat "$VITE_LOG" >&2
  fail "Vite -> Frappe Bootstrap 代理失败，HTTP $VITE_BOOTSTRAP_CODE"
}

python3 - "$VITE_BOOTSTRAP_BODY" <<'PY'
import json
import sys

with open(sys.argv[1], encoding='utf-8') as handle:
    payload = json.load(handle)
message = payload.get('message') or {}
assert message.get('ok') is True, payload
apps = sorted(
    app['manifest']['id']
    for app in (message.get('data') or {}).get('apps') or []
)
assert apps == ['attendance', 'inventory', 'lims'], apps
print('Vite proxy bootstrap apps =', apps)
PY

echo
echo "P3 Workspace Runtime Smoke: PASS"
echo "Frappe: $BASE_URL"
echo "Portal: $PORTAL_URL"
echo "说明：本脚本不会删除 volume、不会重建 site、不会写入 Attendance / Inventory / LIMS 业务事实。"
echo "脚本退出时会关闭本次临时 Vite smoke 进程；正式开发可按 README 的 Frappe 模式命令启动。"
