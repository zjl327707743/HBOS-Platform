#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"

PROJECT="${HBOS_PREVIEW_PROJECT:-hbos-portal-preview}"
STATE_DIR="${HBOS_PREVIEW_STATE_DIR:-${TMPDIR:-/tmp}/hbos-portal-preview-${USER:-local}}"
ENV_FILE="$STATE_DIR/preview.env"
PREVIEW_COMPOSE="$ROOT_DIR/scripts/portal/docker-compose.isolated-preview.yml"
PURGE=0

if [[ "${1:-}" == "--purge" ]]; then
  PURGE=1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "没有找到 preview state: $ENV_FILE"
  echo "如使用了自定义 HBOS_PREVIEW_STATE_DIR，请带相同环境变量运行。"
  exit 0
fi

dc() {
  docker compose \
    --env-file "$ENV_FILE" \
    -p "$PROJECT" \
    -f docker-compose.yml \
    -f "$PREVIEW_COMPOSE" \
    "$@"
}

if [[ "$PURGE" == "1" ]]; then
  echo "停止并删除隔离 preview 容器 / network / volumes：$PROJECT"
  dc down -v --remove-orphans
  rm -rf "$STATE_DIR"
  echo "已删除 preview state。原项目资源不在 project '$PROJECT' 下，不会被删除。"
else
  echo "停止隔离 preview 容器 / network，保留 volumes：$PROJECT"
  dc down --remove-orphans
  echo "preview volumes 已保留，可再次快速启动。"
  echo "彻底删除时运行：bash scripts/portal/stop_isolated_preview.sh --purge"
fi
