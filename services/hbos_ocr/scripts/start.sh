#!/usr/bin/env bash
#
# 启动入库拍照识别服务（hbos_ocr）。
#
# 为什么要有这个脚本（而不是在 plist 里直接写一长串命令）：
#
#   1. **必须带上 HBOS_OCR_SHARED_TOKEN**，而且要与 Frappe 容器里那个是同一个值。
#      服务端没有令牌时 `/health` 依然是 200，但 `/api/v1/recognize` 返回
#      503「OCR 内部认证未配置」—— 页面上同样显示「识别服务当前不可用」，
#      和「服务没起」看起来完全一样，极难排查。
#   2. **只读 `.env` 里的 HBOS_OCR_* 行**，不 `source` 整个 .env ——
#      仓库根 .env 里有 DB 密码、飞书密钥，识别服务不需要，也不该拥有。
#   3. **必须绑 0.0.0.0**：Frappe 在容器里，经 `host.docker.internal` 进来；
#      绑 127.0.0.1 时容器连不上（README 踩过）。
#
# 用法：
#   services/hbos_ocr/scripts/start.sh          # 前台跑（Ctrl-C 停）
#   launchd 见 services/hbos_ocr/launchd/com.haibin.hbos.ocr.plist
#
# 退出码：
#   0  进程正常结束
#   2  配置不全（缺令牌 / venv 不存在），未启动

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_DIR="$(cd "$HERE/.." && pwd)"
REPO_ROOT="$(cd "$SERVICE_DIR/../.." && pwd)"
ENV_FILE="${HBOS_OCR_ENV_FILE:-$REPO_ROOT/.env}"

# --- 1) 只挑出 HBOS_OCR_* 行 ---
if [[ -f "$ENV_FILE" ]]; then
  while IFS= read -r line || [[ -n "$line" ]]; do
    case "$line" in
      HBOS_OCR_*=*)
        key="${line%%=*}"
        value="${line#*=}"
        # 去掉可能的行内注释与首尾空白（.env 里目前没有，防将来）
        value="${value%%#*}"
        value="$(printf '%s' "$value" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
        export "$key=$value"
        ;;
    esac
  done <"$ENV_FILE"
fi

# --- 2) 默认值 ---
export HBOS_OCR_BACKEND="${HBOS_OCR_BACKEND:-c2_ocr}"
export HBOS_OCR_HOST="${HBOS_OCR_HOST:-0.0.0.0}"
export HBOS_OCR_PORT="${HBOS_OCR_PORT:-8100}"

# --- 3) 前置检查：失败要**明确退出**，别让服务以「能起来但用不了」的状态跑 ---
if [[ -z "${HBOS_OCR_SHARED_TOKEN:-}" ]]; then
  echo "[hbos_ocr] 缺少 HBOS_OCR_SHARED_TOKEN：服务能起来，但 recognize 会一律 503。" >&2
  echo "[hbos_ocr] 请在 $ENV_FILE 里配置，且与 Frappe 容器使用同一个值。" >&2
  exit 2
fi

PYTHON="$SERVICE_DIR/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  echo "[hbos_ocr] 找不到虚拟环境解释器：$PYTHON" >&2
  echo "[hbos_ocr] 先建环境：cd services/hbos_ocr && uv sync" >&2
  exit 2
fi

# --- 4) 必须在这个目录里启动 ---
# 当前目录若有个叫 cv2.py 的文件，会盖住真正的 cv2 包（README 记载的坑）。
cd "$SERVICE_DIR"

echo "[hbos_ocr] backend=$HBOS_OCR_BACKEND host=$HBOS_OCR_HOST port=$HBOS_OCR_PORT" >&2
exec "$PYTHON" -m uvicorn app.main:app --host "$HBOS_OCR_HOST" --port "$HBOS_OCR_PORT"
