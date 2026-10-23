#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"

fail() {
  echo "HBOS isolated preview failed: $*" >&2
  exit 1
}

info() {
  echo
  echo "==> $*"
}

PROJECT="${HBOS_PREVIEW_PROJECT:-hbos-portal-preview}"
SITE_NAME="${HBOS_PREVIEW_SITE:-portal-preview.localhost}"
FRAPPE_PORT="${HBOS_PREVIEW_FRAPPE_PORT:-18091}"
PORTAL_PORT="${HBOS_PREVIEW_PORTAL_PORT:-5179}"
STATE_DIR="${HBOS_PREVIEW_STATE_DIR:-${TMPDIR:-/tmp}/hbos-portal-preview-${USER:-local}}"
ENV_FILE="$STATE_DIR/preview.env"
PREVIEW_COMPOSE="$ROOT_DIR/scripts/portal/docker-compose.isolated-preview.yml"

mkdir -p "$STATE_DIR"
chmod 700 "$STATE_DIR"

BASELINE_CONTAINERS="$STATE_DIR/baseline-containers.txt"
BASELINE_VOLUMES="$STATE_DIR/baseline-volumes.txt"
AFTER_CONTAINERS="$STATE_DIR/after-containers.txt"
AFTER_VOLUMES="$STATE_DIR/after-volumes.txt"

docker ps -a --format '{{.Names}}' | sort >"$BASELINE_CONTAINERS"
docker volume ls --format '{{.Name}}' | sort >"$BASELINE_VOLUMES"

[[ -d apps/hbos_portal ]] || fail "缺少 apps/hbos_portal；请在 Portal worktree / branch 中运行"
[[ -d apps/hb_attendance_app ]] || fail "缺少 apps/hb_attendance_app"
[[ -d apps/hb_inventory_app ]] || fail "缺少 apps/hb_inventory_app"
[[ -d apps/hb_lims_app ]] || fail "缺少 apps/hb_lims_app"
[[ -d frontend/hbos-portal-web ]] || fail "缺少 frontend/hbos-portal-web"
[[ -f "$PREVIEW_COMPOSE" ]] || fail "缺少 Preview Compose override: $PREVIEW_COMPOSE"
command -v docker >/dev/null 2>&1 || fail "未找到 docker"
docker compose version >/dev/null 2>&1 || fail "docker compose 不可用"
command -v node >/dev/null 2>&1 || fail "未找到 Node.js"
command -v npm >/dev/null 2>&1 || fail "未找到 npm"

if [[ ! -d runtime/apps/hrms/.git ]]; then
  info "准备隔离 worktree 的 HRMS v16 source"
  mkdir -p runtime/apps
  rm -rf runtime/apps/hrms
  git clone --depth 1 --branch version-16 https://github.com/frappe/hrms.git runtime/apps/hrms
fi

if [[ ! -f "$ENV_FILE" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    ADMIN_PASSWORD="$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(18))
PY
)"
    DB_ROOT_PASSWORD="$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(18))
PY
)"
  else
    ADMIN_PASSWORD="hbos-preview-admin-local"
    DB_ROOT_PASSWORD="hbos-preview-db-local"
  fi

  cat >"$ENV_FILE" <<EOF
COMPOSE_PROJECT_NAME=$PROJECT
ERPNEXT_VERSION=v16.26.2
SITE_NAME=$SITE_NAME
FRAPPE_SITE_NAME_HEADER=$SITE_NAME
HTTP_PORT=127.0.0.1:$FRAPPE_PORT
MARIADB_HOST=db
DB_PORT=3306
DB_ROOT_PASSWORD=$DB_ROOT_PASSWORD
MYSQL_ROOT_PASSWORD=$DB_ROOT_PASSWORD
REDIS_CACHE=redis-cache:6379
REDIS_QUEUE=redis-queue:6379
SOCKETIO_PORT=9000
ADMIN_PASSWORD=$ADMIN_PASSWORD
UPSTREAM_REAL_IP_ADDRESS=127.0.0.1
UPSTREAM_REAL_IP_HEADER=X-Forwarded-For
UPSTREAM_REAL_IP_RECURSIVE=off
PROXY_READ_TIMEOUT=120
CLIENT_MAX_BODY_SIZE=50m
HBOS_FEISHU_SYNC_ENABLED=0
HBOS_DELICLOUD_SYNC_ENABLED=0
HBOS_AI_ENABLED=0
HBOS_AI_ALLOW_PII=0
FEISHU_APP_ID=
FEISHU_APP_SECRET=
HBOS_FEISHU_LEAVE_APP_TOKEN=
HBOS_FEISHU_LEAVE_TABLE_ID=
HBOS_FEISHU_OVERTIME_APP_TOKEN=
HBOS_FEISHU_OVERTIME_TABLE_ID=
HBOS_FEISHU_REST_LEAVE_APP_TOKEN=
HBOS_FEISHU_REST_LEAVE_TABLE_ID=
HBOS_FEISHU_EXCEPTION_APP_TOKEN=
HBOS_FEISHU_EXCEPTION_TABLE_ID=
DELICLOUD_APP_KEY=
DELICLOUD_APP_SECRET=
HBOS_NOTIFY_WEBHOOK_URL=
HBOS_NOTIFY_DRY_RUN=1
HBOS_AI_BASE_URL=
HBOS_AI_API_KEY=
HBOS_AI_MODEL=
HBOS_AI_TIMEOUT=60
HBOS_OCR_URL=http://host.docker.internal:8100
HBOS_OCR_SHARED_TOKEN=preview-disabled
EOF
  chmod 600 "$ENV_FILE"
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

FRAPPE_URL="http://127.0.0.1:$FRAPPE_PORT"
PORTAL_URL="http://127.0.0.1:$PORTAL_PORT"

dc() {
  docker compose \
    --env-file "$ENV_FILE" \
    -p "$PROJECT" \
    -f docker-compose.yml \
    -f "$PREVIEW_COMPOSE" \
    "$@"
}

info "1/7 校验隔离 Compose"
dc config --quiet

ASSET_MOUNT_COUNT="$(
  dc config |
    grep -c '/home/frappe/frappe-bench/sites/assets' || true
)"
if [[ "$ASSET_MOUNT_COUNT" -lt 8 ]]; then
  fail "Preview Compose 未对所有 Frappe 服务显式命名 sites/assets 卷（当前命中 $ASSET_MOUNT_COUNT）"
fi

if docker ps --format '{{.Names}}' | grep -q '^hbos-m0-r3a-'; then
  echo "检测到原项目容器正在运行；本预览将使用独立 project '$PROJECT'，不会停止它们。"
fi

info "2/7 准备中文字体（仅当前 worktree runtime/；禁止扫描现有容器）"
scripts/setup_fonts.sh --no-container-check >/dev/null

info "3/7 启动隔离数据库 / Redis"
dc up -d db redis-cache redis-queue

info "4/7 配置 isolated site volume"
dc run --rm configurator >/dev/null

SITE_EXISTS=0
if dc run --rm --no-deps backend bash -lc "test -f sites/$SITE_NAME/site_config.json"; then
  SITE_EXISTS=1
fi

if [[ "$SITE_EXISTS" == "0" ]]; then
  info "5/7 创建隔离 preview Site，并安装三业务 App + Portal"
  dc run --rm create-site
else
  info "5/7 preview Site 已存在，跳过 new-site"
fi

info "6/7 启动隔离 HBOS runtime"
dc up -d backend queue-long queue-short scheduler websocket frontend

info "仅在 Preview backend 内刷新 / 验证字体缓存"
dc exec -T backend bash -lc \
  'fc-cache -f /usr/share/fonts/truetype/hbos >/dev/null 2>&1 || fc-cache -f >/dev/null 2>&1'
PREVIEW_ZH_FONTS="$(dc exec -T backend bash -lc 'fc-list :lang=zh 2>/dev/null || true')"
if ! grep -qiE 'NotoSerifSC|Noto Serif SC' <<< "$PREVIEW_ZH_FONTS"; then
  fail "Preview backend 未识别 Noto Serif SC；不会尝试修复或触碰其他容器"
fi

# Ensure the existing isolated site is aligned with the current worktree.
dc exec -T backend bench --site "$SITE_NAME" migrate >/dev/null

APPS="$(dc exec -T backend bench --site "$SITE_NAME" list-apps)"
printf '%s\n' "$APPS"
for app in frappe erpnext hrms hb_attendance_app hb_inventory_app hb_lims_app hbos_portal; do
  printf '%s\n' "$APPS" | awk '{print $1}' | grep -qx "$app" || fail "preview Site 缺少 App: $app"
done

info "验证三业务 Provider / Portal dispatcher"
dc exec -T -e HBOS_PORTAL_INTEGRATION_CHECKS=1   backend bench --site "$SITE_NAME" execute hbos_portal.integration_checks.run
dc exec -T -e HBOS_PORTAL_INTEGRATION_CHECKS=1   backend bench --site "$SITE_NAME" execute hb_inventory_app.hbos_inventory.portal.integration_checks.run

info "验证隔离资源边界"
docker ps -a --format '{{.Names}}' | sort >"$AFTER_CONTAINERS"
docker volume ls --format '{{.Name}}' | sort >"$AFTER_VOLUMES"

UNEXPECTED_CONTAINERS="$(
  comm -13 "$BASELINE_CONTAINERS" "$AFTER_CONTAINERS" |
    grep -Ev "^(${PROJECT}[-_])" || true
)"
UNEXPECTED_VOLUMES="$(
  comm -13 "$BASELINE_VOLUMES" "$AFTER_VOLUMES" |
    grep -Ev "^(${PROJECT}[-_])" || true
)"

if [[ -n "$UNEXPECTED_CONTAINERS" || -n "$UNEXPECTED_VOLUMES" ]]; then
  echo "检测到预览启动期间出现非 '$PROJECT' 命名空间的新 Docker 资源：" >&2
  [[ -z "$UNEXPECTED_CONTAINERS" ]] || {
    echo "Containers:" >&2
    printf '%s\n' "$UNEXPECTED_CONTAINERS" >&2
  }
  [[ -z "$UNEXPECTED_VOLUMES" ]] || {
    echo "Volumes:" >&2
    printf '%s\n' "$UNEXPECTED_VOLUMES" >&2
  }
  fail "隔离资源边界检查失败；请人工审查，不自动清理原项目资源"
fi

info "7/7 启动 Portal Vite（真实 preview Frappe 模式）"
cd frontend/hbos-portal-web
if [[ ! -d node_modules ]]; then
  npm install --no-audit --no-fund --package-lock=false
fi

echo
echo "=============================================================="
echo "HBOS 隔离预览已准备完成"
echo
echo "Portal:  $PORTAL_URL"
echo "Frappe:  $FRAPPE_URL"
echo "Site:    $SITE_NAME"
echo "User:    Administrator"
echo "Password: $ADMIN_PASSWORD"
echo
echo "Docker project: $PROJECT"
echo "State file:     $ENV_FILE"
echo
echo "隔离检查：启动期间新增的 Docker container / volume 均受 '$PROJECT' 命名空间约束。"
echo "原项目 8080 / frontend Site / 原 Docker volumes 未被停止或复用。"
echo "按 Ctrl+C 只会停止 Vite；隔离 Docker 环境继续保留。"
echo "完全停止预览：bash scripts/portal/stop_isolated_preview.sh"
echo "彻底删除预览 volumes：bash scripts/portal/stop_isolated_preview.sh --purge"
echo "=============================================================="
echo

VITE_PORTAL_DATA_MODE=frappe \
VITE_FRAPPE_PROXY_TARGET="$FRAPPE_URL" \
VITE_FRAPPE_APP_ORIGIN="$FRAPPE_URL" \
exec npm run dev -- --host 127.0.0.1 --port "$PORTAL_PORT" --strictPort
