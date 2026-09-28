#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# HBOS-Platform 本地部署脚本（精简版，已生成.env后的完成步骤）
# 新乡海滨智能运营管理平台
# ============================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[HBOS]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()  { echo -e "${RED}[ERROR]${NC} $1"; }

PROJECT_DIR="/Users/hbzl/Vibe Coding/HBOS-Platform"

cd "$PROJECT_DIR"

# ---------- Step 1: 验证 .env ----------
log "验证 .env 配置..."
if [ ! -f ".env" ]; then
    err ".env 文件不存在，请在 Claude Desktop 中重新生成。"
    exit 1
fi
log "  .env 已就绪"

# ---------- Step 2: 拉取 Docker 镜像并启动 ----------
log "拉取 Docker 镜像..."
docker compose pull

log "启动 Docker 服务..."
docker compose up -d

log "等待服务初始化（约 60-120 秒）..."
sleep 30

# 检查容器状态
log "检查容器状态..."
docker compose ps

# 等待 site 创建完成
log "等待 site 初始化..."
for i in $(seq 1 12); do
    if docker compose logs create-site 2>/dev/null | grep -q "set-default"; then
        log "Site 初始化完成!"
        break
    fi
    if [ $i -eq 12 ]; then
        warn "Site 初始化可能仍在进行中，查看: docker compose logs create-site"
    fi
    sleep 10
done

# ---------- 验证 ----------
HTTP_PORT=$(grep HTTP_PORT .env | cut -d= -f2)
ADMIN_PASS=$(grep ADMIN_PASSWORD .env | cut -d= -f2)

echo ""
log "============================================"
log "  HBOS-Platform 部署完成！"
log "============================================"
log "  Desk 地址: http://localhost:${HTTP_PORT}/login"
log "  管理员账号: Administrator"
log "  管理员密码: ${ADMIN_PASS}"
log ""
log "常用命令:"
log "  cd \"$PROJECT_DIR\""
log "  docker compose ps           # 查看容器状态"
log "  docker compose logs -f      # 查看日志"
log "  docker compose down         # 停止所有服务"
log "  docker compose up -d        # 重新启动"
log ""
warn "⚠️  重要提醒:"
warn "  - 不要执行 docker compose down -v（会删除数据）"
warn "  - 不要删除 frontend site"
log "============================================"
