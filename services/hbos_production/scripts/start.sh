#!/usr/bin/env bash
#
# 启动生产看板取数服务（hbos_production）。
#
# 为什么要有这个脚本而不是在 plist 里直接写命令：
#
#   1. **凭据要从受限位置读**，不能写进 plist（plist 通常是 world-readable）。
#   2. **缺凭据时 fail-fast**：没有飞书 app_id/secret 时服务能起来，
#      但每个接口都返回 503「飞书凭据未配置」——页面上看到的是
#      「看板数据还没接通」，与「服务没跑」长得几乎一样。
#   3. **只挑需要的变量**，不 `source` 整个 .env。
#
# 2026-10-29 的由来：这个服务一直**没有自启配置**，靠手动起。有一次排查
# OCR 时用了 `pkill -f "port 8101"`，把正在跑的生产服务一起杀了（命令行里
# 就含 `--port 8101`）。加自启之后这类误伤能自动恢复。
#
# 用法：
#   services/hbos_production/scripts/start.sh          # 前台跑（Ctrl-C 停）
#   launchd 见 services/hbos_production/launchd/com.haibin.hbos.production.plist
#
# 退出码：
#   0  进程正常结束
#   2  配置不全（缺飞书凭据 / venv 不存在），未启动

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_DIR="$(cd "$HERE/.." && pwd)"
REPO_ROOT="$(cd "$SERVICE_DIR/../.." && pwd)"

# 默认读服务目录下的 .env；仓库根那份是 Compose 用的，两者内容不同。
ENV_FILE="${HBOS_PRODUCTION_ENV_FILE:-$SERVICE_DIR/.env}"

if [[ -f "$ENV_FILE" ]]; then
  while IFS= read -r line || [[ -n "$line" ]]; do
    case "$line" in
      HBOS_PRODUCTION_*=*|HBOS_FEISHU_APP_ID=*|HBOS_FEISHU_APP_SECRET=*|HBOS_FEISHU_BASE=*)
        key="${line%%=*}"
        # **外部已显式设置的变量优先**：launchd/容器/临时调端口时设的值
        # 不该被 .env 悄悄覆盖。早先无条件 export，导致
        # `HBOS_PRODUCTION_PORT=8121 ./start.sh` 仍然起在 8101
        # （两个实例抢同一端口，后来的那个直接 bind 失败）。
        if [[ -n "${!key:-}" ]]; then
          continue
        fi
        value="${line#*=}"
        value="${value%%#*}"
        value="$(printf '%s' "$value" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
        export "$key=$value"
        ;;
    esac
  done <"$ENV_FILE"
fi

# 绑定地址：服务只该给本机/容器网络用。**不要绑 0.0.0.0**——
# 这个服务目前零鉴权，暴露到局域网等于把生产数据公开（见部署文档）。
export HBOS_PRODUCTION_HOST="${HBOS_PRODUCTION_HOST:-127.0.0.1}"
export HBOS_PRODUCTION_PORT="${HBOS_PRODUCTION_PORT:-8101}"

if [[ -z "${HBOS_FEISHU_APP_ID:-}" || -z "${HBOS_FEISHU_APP_SECRET:-}" ]]; then
  echo "[hbos_production] 缺飞书凭据：服务能起来，但所有接口会返回 503。" >&2
  echo "[hbos_production] 请在 $ENV_FILE 配置 HBOS_FEISHU_APP_ID / HBOS_FEISHU_APP_SECRET。" >&2
  exit 2
fi

PYTHON="$SERVICE_DIR/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  echo "[hbos_production] 找不到虚拟环境解释器：$PYTHON" >&2
  echo "[hbos_production] 先建环境：cd services/hbos_production && uv sync" >&2
  exit 2
fi

cd "$SERVICE_DIR"

# 缓存目录是相对路径（默认 `.cache`）—— 必须 cd 到服务目录再起，
# 否则容器里/launchd 下的工作目录不同，缓存会落到别处，「重启秒开」失效。
echo "[hbos_production] host=$HBOS_PRODUCTION_HOST port=$HBOS_PRODUCTION_PORT" >&2
exec "$PYTHON" -m uvicorn app.main:app \
  --host "$HBOS_PRODUCTION_HOST" \
  --port "$HBOS_PRODUCTION_PORT"
