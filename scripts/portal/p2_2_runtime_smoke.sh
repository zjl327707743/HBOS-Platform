#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"

fail() {
  echo "P2.2 FAIL: $*" >&2
  exit 1
}

info() {
  echo
  echo "==> $*"
}

read_env() {
  grep -E "^$1=" .env | tail -n 1 | cut -d= -f2- | tr -d "\r" || true
}

[[ -f .env ]] || fail "缺少 .env；不要从 .env.example 直接运行真实环境。"
[[ -d apps/hbos_portal ]] || fail "缺少 apps/hbos_portal；请先 git pull 当前 Portal 分支。"

SITE_NAME="$(read_env SITE_NAME)"
HTTP_PORT="$(read_env HTTP_PORT)"
ADMIN_PASSWORD="$(read_env ADMIN_PASSWORD)"

[[ -n "$SITE_NAME" ]] || fail ".env 中 SITE_NAME 为空"
[[ -n "$HTTP_PORT" ]] || fail ".env 中 HTTP_PORT 为空"

BASE_URL="http://127.0.0.1:$HTTP_PORT"

info "1/8 校验 Docker Compose"
docker compose config --quiet

info "2/8 检查当前容器状态"
docker compose ps

info "3/8 应用 hbos_portal bind mount（不删除 volume、不重建 site）"
docker compose up -d backend frontend queue-long queue-short scheduler websocket

info "4/8 刷新 sites/apps.txt"
docker compose run --rm configurator

info "5/8 安装 hbos_portal（已安装则跳过）"
if docker compose exec -T backend bash -lc "bench --site \"$SITE_NAME\" list-apps" | grep -qx "hbos_portal"; then
  echo "hbos_portal 已安装，跳过 install-app"
else
  docker compose exec -T backend bash -lc "bench --site \"$SITE_NAME\" install-app hbos_portal"
fi

info "6/8 验证 site app 清单与 Python import"
docker compose exec -T backend bash -lc "bench --site \"$SITE_NAME\" list-apps"
docker compose exec -T backend bash -lc "SITE_NAME='$SITE_NAME' python - <<'PY'
import os
import frappe
import hbos_portal
from hbos_portal.services.registry import build_registry

site = os.environ['SITE_NAME']
frappe.init(site=site)
frappe.connect()

try:
    print('hbos_portal version:', hbos_portal.__version__)
    snapshot = build_registry([])
    print('empty registry entries:', len(snapshot.entries))
    print('empty registry failures:', len(snapshot.failures))
    assert len(snapshot.entries) == 0
    assert len(snapshot.failures) == 0
finally:
    frappe.destroy()
PY"

info "7/8 验证 Guest 不能直接读取 Bootstrap"
GUEST_BODY="$(mktemp)"
COOKIE_FILE="$(mktemp)"
PASS_FILE="$(mktemp)"
LOGIN_BODY="$(mktemp)"
BOOTSTRAP_BODY="$(mktemp)"
trap 'rm -f "$GUEST_BODY" "$COOKIE_FILE" "$PASS_FILE" "$LOGIN_BODY" "$BOOTSTRAP_BODY"' EXIT
chmod 600 "$PASS_FILE"

GUEST_CODE="$(curl -sS -o "$GUEST_BODY" -w '%{http_code}' "$BASE_URL/api/method/hbos_portal.api.bootstrap.get_bootstrap" || true)"

if [[ "$GUEST_CODE" == "200" ]] && grep -Eq '"ok"[[:space:]]*:[[:space:]]*true' "$GUEST_BODY"; then
  fail "Guest bootstrap 意外返回成功"
fi
echo "Guest bootstrap HTTP: $GUEST_CODE (expected non-success)"

info "8/8 验证 Administrator Session Bootstrap"
if [[ -z "$ADMIN_PASSWORD" || "$ADMIN_PASSWORD" == "<LOCAL_ADMIN_PASSWORD>" ]]; then
  echo "SKIP authenticated HTTP smoke: .env 中 ADMIN_PASSWORD 未提供可用本地值"
  echo "其余安装 / Registry / Guest boundary 已通过。"
  exit 0
fi

printf '%s' "$ADMIN_PASSWORD" > "$PASS_FILE"

LOGIN_CODE="$(curl -sS -o "$LOGIN_BODY" -w '%{http_code}' -c "$COOKIE_FILE" -X POST --data-urlencode 'usr=Administrator' --data-urlencode "pwd@$PASS_FILE" "$BASE_URL/api/method/login" || true)"

[[ "$LOGIN_CODE" == "200" ]] || {
  cat "$LOGIN_BODY" >&2
  fail "Administrator 登录失败，HTTP $LOGIN_CODE"
}

BOOTSTRAP_CODE="$(curl -sS -o "$BOOTSTRAP_BODY" -w '%{http_code}' -b "$COOKIE_FILE" "$BASE_URL/api/method/hbos_portal.api.bootstrap.get_bootstrap" || true)"

[[ "$BOOTSTRAP_CODE" == "200" ]] || {
  cat "$BOOTSTRAP_BODY" >&2
  fail "Bootstrap HTTP 失败，HTTP $BOOTSTRAP_CODE"
}

grep -Eq '"ok"[[:space:]]*:[[:space:]]*true' "$BOOTSTRAP_BODY" || {
  cat "$BOOTSTRAP_BODY" >&2
  fail "Bootstrap 未返回 ok=true"
}

if ! grep -Eq '"apps"[[:space:]]*:[[:space:]]*\[[[:space:]]*\]' "$BOOTSTRAP_BODY"; then
  echo "提示：apps 当前不是空数组。若你已经注册 Provider，这是允许的；请人工核对。"
fi

echo
echo "P2.2 Runtime Smoke Test: PASS"
echo "Site: $SITE_NAME"
echo "URL:  $BASE_URL"
echo "说明：本脚本没有删除 volume、没有重建 site、没有写入任何业务事实。"
