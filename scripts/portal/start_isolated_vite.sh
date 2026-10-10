#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"

fail() {
  echo "HBOS isolated Portal Vite failed: $*" >&2
  exit 1
}

PROJECT="${HBOS_PREVIEW_PROJECT:-hbos-portal-preview}"
FRAPPE_PORT="${HBOS_PREVIEW_FRAPPE_PORT:-18091}"
PORTAL_PORT="${HBOS_PREVIEW_PORTAL_PORT:-5179}"
STATE_DIR="${HBOS_PREVIEW_STATE_DIR:-${TMPDIR:-/tmp}/hbos-portal-preview-${USER:-local}}"
ENV_FILE="$STATE_DIR/preview.env"

[[ -f "$ENV_FILE" ]] || fail "Preview state 不存在：$ENV_FILE；请先运行 start_isolated_preview.sh"
[[ -d frontend/hbos-portal-web ]] || fail "缺少 frontend/hbos-portal-web"

FRAPPE_URL="http://127.0.0.1:$FRAPPE_PORT"
PORTAL_URL="http://127.0.0.1:$PORTAL_PORT"

if ! docker ps   --filter "label=com.docker.compose.project=$PROJECT"   --filter "label=com.docker.compose.service=frontend"   --format '{{.Names}}' | grep -q .; then
  fail "Preview frontend 容器未运行；不要用 Vite-only 启动器替代完整 Preview 启动"
fi

command -v node >/dev/null 2>&1 || fail "未找到 Node.js"
command -v npm >/dev/null 2>&1 || fail "未找到 npm"

cd frontend/hbos-portal-web
if [[ ! -d node_modules ]]; then
  npm install --no-audit --no-fund --package-lock=false
fi

echo "HBOS Preview Vite-only"
echo "Portal API proxy:    $FRAPPE_URL"
echo "Business app origin: $FRAPPE_URL"
echo "Portal:              $PORTAL_URL"
echo "Docker Preview runtime 保持不变。"
echo

VITE_PORTAL_DATA_MODE=frappe \
VITE_FRAPPE_PROXY_TARGET="$FRAPPE_URL" \
VITE_FRAPPE_APP_ORIGIN="$FRAPPE_URL" \
exec npm run dev -- --host 127.0.0.1 --port "$PORTAL_PORT" --strictPort
