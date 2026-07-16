# Docker 开发环境复现手册

本手册面向 HBOS 项目新成员，目标是：**从 Git 克隆代码后，能够从零构建完整的本地开发环境**，而不需要复制任何人的 Docker 目录或 Volume。

## 核心理念

> 新成员应该能通过 Git 中的源码、配置模板、版本清单和初始化步骤，在自己电脑上重新构建环境。不能依赖"复制 Owner 的 Docker 目录"。

## 1. 前置要求

### 1.1 硬件要求

| 项目 | 最低要求 | 建议 |
|------|----------|------|
| 内存 | 8GB | 16GB+ |
| 磁盘 | 20GB 可用 | 50GB+（Docker 镜像约 5GB） |
| CPU | 4 核 | 8 核 |

### 1.2 软件要求

| 软件 | 版本 | 说明 |
|------|------|------|
| Docker Desktop | 最新稳定版 | macOS/Windows 用 Docker Desktop，Linux 用 Docker Engine |
| Docker Compose | v2+ | 随 Docker Desktop 内置 |
| Git | 最新稳定版 | 用于代码克隆和版本管理 |

### 1.3 平台差异

| 平台 | 注意事项 |
|------|----------|
| macOS（Owner 当前使用） | 推荐 Docker Desktop for Mac，磁盘空间注意预留 |
| Windows | 必须使用 WSL2 + Docker Desktop，不要用旧版 Docker Toolbox |
| Linux | 使用 Docker Engine + Docker Compose 插件 |

## 2. 新成员从零开始（完整步骤）

### 2.1 克隆仓库

```bash
# 克隆 HBOS 主仓库
git clone https://github.com/zjl327707743/HBOS.git
cd HBOS
```

### 2.2 获取 Secret（.env 文件）

> ⚠️ `.env` 文件包含数据库密码、管理员密码等敏感信息，**不能**从 Git 获取。

**获取方式：**

1. Owner 通过安全渠道（飞书私聊、1Password、加密压缩包）发送 `.env` 文件
2. 将 `.env` 放在项目根目录（与 `docker-compose.yml` 同级）
3. 确认 `.env` 已被 `.gitignore` 忽略（当前已配置，不会误提交）

**如果需要自己创建 .env：**

```bash
# 从模板创建
cp .env.example .env

# 编辑 .env，将占位符替换为真实值
# 需要 Owner 提供以下值：
#   DB_ROOT_PASSWORD
#   MYSQL_ROOT_PASSWORD
#   ADMIN_PASSWORD
```

### 2.3 获取 HRMS 源码

HRMS 是 Frappe HR 官方的人力资源管理系统，通过 bind mount 挂载到 Docker 容器中。需要从 GitHub 克隆到 `runtime/apps/hrms`。

```bash
# 创建目录
mkdir -p runtime/apps

# 克隆 HRMS 官方仓库
git clone https://github.com/frappe/hrms.git runtime/apps/hrms

# 切换到 version-16 分支
cd runtime/apps/hrms
git checkout version-16

# 固定到 v16.12.0 版本（与当前环境一致）
git checkout v16.12.0

# 返回项目根目录
cd ../../..
```

> 说明：`runtime/` 目录已被 `.gitignore` 忽略，不会提交到 Git。HRMS 有自己的 `.git` 目录，是独立的 Git 仓库。

### 2.4 拉取 Docker 镜像

```bash
# 拉取所有需要的镜像（可能需要几分钟）
docker compose pull
```

镜像清单：

| 镜像 | 标签 | 用途 |
|------|------|------|
| `frappe/erpnext` | `v16.26.2` | Frappe + ERPNext 核心服务 |
| `mariadb` | `11.8` | 数据库 |
| `redis` | `6.2-alpine` | 缓存和队列 |

### 2.5 启动环境

```bash
# 启动所有服务（后台运行）
docker compose up -d

# 查看启动状态
docker compose ps
```

等待所有容器状态变为 `Up` 或 `healthy`（db 容器需要显示 `healthy`）。

```bash
# 查看日志（如果某个容器启动失败）
docker compose logs backend
docker compose logs db
```

### 2.6 初始化 Site

`create-site` 容器会在启动时自动创建 Frappe site。等待它完成：

```bash
# 查看 create-site 容器日志
docker compose logs create-site

# 如果看到 "sites/common_site_config.json found" 和 site 创建成功的信息，说明初始化完成
```

检查 site 是否创建成功：

```bash
# 进入 backend 容器（使用 Compose 服务名）
docker compose exec backend bash

# 查看 site 列表
bench list-sites

# 应该看到 frontend
```

### 2.7 安装 HRMS

HRMS 已通过 bind mount 挂载到容器中，但还需要在 Frappe site 中安装。

```bash
# 进入 backend 容器
docker compose exec backend bash

# 安装 HRMS 到 site
bench --site frontend install-app hrms

# 执行数据库迁移
bench --site frontend migrate

# 退出容器
exit
```

### 2.8 安装 hb_attendance_app

```bash
# 进入 backend 容器
docker compose exec backend bash

# 安装自定义 App
bench --site frontend install-app hb_attendance_app

# 执行数据库迁移
bench --site frontend migrate

# 退出容器
exit
```

### 2.9 修复 HRMS 前端资源

> ⚠️ **临时方案说明：** 以下 HRMS 前端资源同步步骤是当前环境的临时兼容措施。这是因为当前 Docker 镜像 `frappe/erpnext:v16.26.2` 不包含 HRMS 的静态资源，而 frontend 容器（Nginx）需要直接提供这些文件。
>
> **临时性限制：**
> - 容器重建（`docker compose down && docker compose up -d`）后可能需要重新执行这些步骤；
> - 以下命令中使用了 `docker cp`（需要实际容器实例名），不适合作为长期标准部署方案；
> - 实际容器名取决于 Compose 项目名，每次部署可能不同。
>
> **长期方向（本轮不实施）：** 通过自定义 Docker 镜像或挂载 HRMS public 目录到 frontend 容器，使静态资源在容器启动时自动可用。具体方案包括：
> - 构建包含 HRMS 的自定义 frontend 镜像；
> - 在 `docker-compose.yml` 中为 frontend 容器添加 HRMS public 目录的 bind mount；
> - 使用 Frappe 官方的 bench 前端构建流程。
>
> **当前步骤（仅在新环境首次搭建时需要）：**

```bash
# 进入 backend 容器，构建前端资源
docker compose exec backend bash
bench --site frontend clear-cache
bench build
exit

# 将构建后的 HRMS 资源同步到 frontend 容器
# 方法：动态获取容器名，避免硬编码
BACKEND_CONTAINER="$(docker compose ps -q backend)"
FRONTEND_CONTAINER="$(docker compose ps -q frontend)"
docker cp "${BACKEND_CONTAINER}:/home/frappe/frappe-bench/apps/hrms/hrms/public/." \
  /tmp/hrms_public_temp && \
docker cp /tmp/hrms_public_temp/. "${FRONTEND_CONTAINER}:/home/frappe/frappe-bench/apps/hrms/hrms/public/"
```

### 2.10 验证环境

```bash
# 1. 检查所有容器运行状态
docker compose ps
# 所有容器状态应为 Up

# 2. 检查版本
docker compose exec backend bench version
# 应显示：erpnext 16.26.2, frappe 16.25.0, hrms 16.12.0, hb_attendance_app 0.0.1

# 3. 检查已安装 App
docker compose exec backend bench --site frontend list-apps
# 应显示：frappe, erpnext, hrms, hb_attendance_app

# 4. 访问 Desk
# 浏览器打开 http://localhost:${HTTP_PORT:-8080}/login
# 使用 ADMIN_PASSWORD 登录
# 验证 Desk 可访问
# 验证 HR Workspace 可访问
# 验证 海滨考勤工作台 可访问
```

## 3. 日常操作

### 3.1 启动环境

```bash
# 在项目根目录执行
docker compose up -d

# 等待几秒后确认
docker compose ps
```

### 3.2 停止环境

```bash
# 停止所有容器（保留数据）
docker compose stop

# 注意：不要执行 docker compose down -v
# down -v 会删除数据卷，导致数据库丢失！
```

### 3.3 查看日志

```bash
# 查看所有服务日志
docker compose logs -f

# 查看特定服务日志
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f db
```

### 3.4 进入容器

```bash
# 进入 backend 容器（执行 bench 命令）
docker compose exec backend bash

# 进入数据库容器
docker compose exec db bash
```

### 3.5 更新代码

```bash
# 拉取最新代码
git pull

# 如果有迁移，执行 migrate
docker compose exec backend bench --site frontend migrate

# 如果 JS/CSS 有更新，重新构建
docker compose exec backend bench build

# 清除缓存
docker compose exec backend bench --site frontend clear-cache
```

### 3.6 更新依赖

```bash
# 拉取最新 Docker 镜像
docker compose pull

# 重新创建容器
docker compose up -d --force-recreate
```

## 4. 数据库备份和恢复

### 4.1 备份（推荐）

```bash
# 使用 bench backup 命令（推荐）
docker compose exec backend bench --site frontend backup

# 备份文件会存储在 sites/frontend/private/backups/ 目录
# 查看备份文件
docker compose exec backend ls /home/frappe/frappe-bench/sites/frontend/private/backups/
```

### 4.2 恢复

```bash
# 使用 bench restore 命令
# 注意：docker cp 需要使用实际容器名，通过 docker compose ps -q 动态获取
BACKEND_CONTAINER="$(docker compose ps -q backend)"
docker exec "${BACKEND_CONTAINER}" bench --site frontend restore \
  /home/frappe/frappe-bench/sites/frontend/private/backups/<备份文件名>

# 恢复后执行 migrate
docker compose exec backend bench --site frontend migrate
```

### 4.3 从 Docker Volume 直接备份

```bash
# 备份数据库 Volume（需要在宿主机执行）
docker run --rm -v hbos-m0-r3a_db-data:/data -v $(pwd)/backups:/backup alpine \
  tar czf /backup/db-data-backup-$(date +%Y%m%d).tar.gz -C /data .

# 备份 sites Volume
docker run --rm -v hbos-m0-r3a_sites:/data -v $(pwd)/backups:/backup alpine \
  tar czf /backup/sites-backup-$(date +%Y%m%d).tar.gz -C /data .
```

## 5. 环境重建

### 5.1 完全重建（保留数据）

```bash
# 停止容器（日常停止，推荐使用 stop）
docker compose stop

# 删除容器（保留 Volume 数据）
# ⚠️ docker compose down 会删除容器和网络，但 Volume 数据保留
# 🔴 禁止：docker compose down -v 会删除所有 Volume！
docker compose down

# 重新启动（Volume 数据保留）
docker compose up -d
```

### 5.2 完全重建（清除所有数据）

> ⚠️ 此操作会删除所有数据，包括数据库！执行前必须备份！

```bash
# 1. 备份数据库
docker compose exec backend bench --site frontend backup

# 2. 将备份文件复制到宿主机
#    使用 docker compose cp 或动态获取容器名
BACKEND_CONTAINER="$(docker compose ps -q backend)"
docker cp "${BACKEND_CONTAINER}:/home/frappe/frappe-bench/sites/frontend/private/backups/." ./backups/

# 3. 停止并删除容器和 Volume
docker compose down -v

# 4. 重新启动（会创建新的 Volume）
docker compose up -d

# 5. 重新安装 App
docker compose exec backend bash
bench --site frontend install-app hrms
bench --site frontend install-app hb_attendance_app
bench --site frontend migrate
exit

# 6. 恢复备份
BACKEND_CONTAINER="$(docker compose ps -q backend)"
docker cp ./backups/<备份文件> "${BACKEND_CONTAINER}:/home/frappe/frappe-bench/sites/frontend/private/backups/"
docker exec "${BACKEND_CONTAINER}" bench --site frontend restore <备份文件>
```

## 6. 常见故障排查

### 6.1 端口冲突

**症状：** `docker compose up -d` 报错 `port is already allocated`

**原因：** 宿主机 8080（或配置的 HTTP_PORT）端口被占用

**解决：**

```bash
# 查看端口占用
lsof -i :8080

# 修改 .env 中的 HTTP_PORT 为其他值（如 8081）
HTTP_PORT=8081

# 重新启动
docker compose up -d
```

### 6.2 容器无法启动

**症状：** 某个容器状态为 `Restarting` 或 `Exited`

**排查：**

```bash
# 查看容器日志
docker compose logs <容器名>

# 常见原因：
# - db 容器未 healthy（等待 db 启动完成）
# - Redis 容器未启动
# - 磁盘空间不足
```

### 6.3 Site 不存在

**症状：** `bench --site frontend` 报错 `site frontend does not exist`

**解决：**

```bash
# 检查 site 列表
docker compose exec backend bench list-sites

# 如果 site 不存在，检查 create-site 容器日志
docker compose logs create-site

# 可能需要重新运行 create-site
docker compose run --rm create-site
```

### 6.4 数据库连接失败

**症状：** 登录报错或 bench 命令无法连接数据库

**排查：**

```bash
# 检查 db 容器状态
docker compose ps db

# 查看 db 日志
docker compose logs db

# 检查 common_site_config.json
docker compose exec backend cat /home/frappe/frappe-bench/sites/common_site_config.json
```

### 6.5 Redis 连接失败

**症状：** `bench doctor` 报 Redis 连接错误

**排查：**

```bash
# 检查 Redis 容器
docker compose ps redis-cache redis-queue

# 重启 Redis
docker compose restart redis-cache redis-queue

# 重启 worker 和 scheduler
docker compose restart queue-short queue-long scheduler
```

### 6.6 前端资源 404

**症状：** 页面加载报 JS/CSS/PNG 404 错误

**解决：**

```bash
# 进入 backend 容器
docker compose exec backend bash

# 清除缓存
bench --site frontend clear-cache

# 重新构建
bench build

# 退出并重启 frontend
exit
docker compose restart frontend
```

### 6.7 bench doctor 报错

**症状：** `bench doctor` 有红色错误

**解决：**

```bash
# 查看具体错误
docker compose exec backend bench doctor

# 常见问题：
# - Redis 连接失败 → 重启 Redis 容器
# - Worker 未运行 → 重启 queue-short queue-long
# - Scheduler 未运行 → 重启 scheduler
```

### 6.8 登录页面无法访问

**症状：** 浏览器访问 `http://localhost:${HTTP_PORT:-8080}/login` 无响应

**排查：**

```bash
# 1. 检查 frontend 容器
docker compose ps frontend

# 2. 检查端口映射
docker compose port frontend 8080

# 3. 检查 frontend 日志
docker compose logs frontend

# 4. 直接从 backend 验证
docker compose exec backend curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/login
```

## 7. 环境验证清单

新环境搭建完成后，逐项检查以确认环境可复现：

| 检查项 | 验证方法 | 期望结果 |
|--------|----------|----------|
| 所有容器运行 | `docker compose ps` | 所有容器 Up |
| db 健康 | `docker compose ps db` | healthy |
| 版本正确 | `bench version` | erpnext 16.26.2, frappe 16.25.0 |
| App 已安装 | `bench --site frontend list-apps` | frappe, erpnext, hrms, hb_attendance_app |
| Desk 可访问 | 浏览器访问 `/login` | 显示登录页 |
| 可以登录 | 使用 ADMIN_PASSWORD 登录 | 进入 Desk |
| HR Workspace | 点击 HR 模块 | 可访问 |
| 海滨考勤 | 点击 海滨考勤 图标 | 可访问工作台 |
| bench doctor | `bench doctor` | 无红色错误 |

## 8. 资产分类表

明确区分什么在 Git 中、什么在 Docker 中：

| 资产类型 | 存储位置 | 在 Git 中？ | 删除容器后？ | 删除 Volume 后？ |
|----------|----------|-------------|-------------|-----------------|
| 源码（hb_attendance_app） | `apps/hb_attendance_app/` | ✅ 是 | 保留（宿主机） | 保留 |
| 源码（HRMS） | `runtime/apps/hrms/` | ❌ 否（Git 忽略） | 保留（宿主机） | 保留 |
| Frappe/ERPNext 源码 | Docker 镜像内 | ❌ 否 | 丢失（镜像还在） | 保留 |
| Docker 镜像 | Docker 镜像存储 | ❌ 否 | 保留 | 保留 |
| 数据库数据 | Volume `hbos-m0-r3a_db-data` | ❌ 否 | 保留 | ❌ 丢失 |
| Site 配置 | Volume `hbos-m0-r3a_sites` | ❌ 否 | 保留 | ❌ 丢失 |
| 上传附件 | Volume `hbos-m0-r3a_sites` | ❌ 否 | 保留 | ❌ 丢失 |
| 日志 | Volume `hbos-m0-r3a_logs` | ❌ 否 | 保留 | ❌ 丢失 |
| Redis 队列 | Volume `hbos-m0-r3a_redis-queue-data` | ❌ 否 | 保留 | ❌ 丢失 |
| 缓存 | 容器内 | ❌ 否 | ❌ 丢失 | N/A |
| .env | 项目根目录 | ❌ 否（Git 忽略） | 保留（宿主机） | 保留 |
| .env.example | 项目根目录 | ✅ 是 | 保留（宿主机） | 保留 |
| 真实数据 | 数据库 Volume | ❌ 否 | 保留 | ❌ 丢失 |
| Demo 数据 | 数据库 Volume | ❌ 否 | 保留 | ❌ 丢失 |
| Secret | .env + Volume | ❌ 否 | 保留 | 部分丢失 |

## 9. 快速命令参考

```bash
# 启动环境
docker compose up -d

# 停止环境
docker compose stop

# 查看状态
docker compose ps

# 进入 backend
docker compose exec backend bash

# 执行迁移
docker compose exec backend bench --site frontend migrate

# 构建前端
docker compose exec backend bench build

# 备份数据库
docker compose exec backend bench --site frontend backup

# 查看版本
docker compose exec backend bench version

# 健康检查
docker compose exec backend bench doctor
```

---

## 10. 长期服务健康检查与恢复

本章节记录 HBOS Docker 环境的长期服务健康检查、恢复顺序和故障排查 SOP，基于 G1B-A 和 G1B-B 的实际恢复经验。

### 10.1 服务角色

**长期运行服务（9 个）：**

| 服务 | 作用 | 关键依赖 |
|------|------|----------|
| db | MariaDB 数据库 | 无 |
| redis-cache | Redis 缓存 | 无 |
| redis-queue | Redis 队列 | 无 |
| backend | Gunicorn WSGI 应用服务器 | db, redis-cache, redis-queue |
| scheduler | Frappe 定时任务调度器 | db, redis-cache, redis-queue |
| queue-long | RQ Worker（long/default/short 队列） | db, redis-cache, redis-queue |
| queue-short | RQ Worker（short/default 队列） | db, redis-cache, redis-queue |
| websocket | Socket.IO 实时通信服务 | redis-cache, redis-queue |
| frontend | Nginx 反向代理 + 静态资源 | backend, websocket |

**一次性初始化服务（2 个）：**

| 服务 | 作用 | 预期状态 |
|------|------|----------|
| configurator | 一次性配置写入（common_site_config.json） | Exited (0) |
| create-site | 一次性 site 初始化 | Exited (0) 或 Exited (1)（site 已存在） |

### 10.2 恢复顺序

```
db
→ redis-cache / redis-queue
→ backend / scheduler / queue-long / queue-short
→ websocket
→ frontend
```

**原则：** 先启动无依赖的底层服务（db、Redis），再启动依赖它们的应用服务，最后启动依赖应用服务的前端代理。

### 10.3 现有容器恢复（最小操作）

适用于容器已存在但部分 Exited 的场景：

```bash
# 第一步：启动 Redis（底层依赖）
docker compose start redis-cache redis-queue

# 第二步：启动 Worker（依赖 Redis）
docker compose start queue-long queue-short

# websocket 通常会在 Redis 恢复后通过 restart policy 自动恢复
# 如果未自动恢复，执行：
docker compose start websocket
```

### 10.4 恢复后验证

```bash
# 1. 全服务状态检查
docker compose ps -a
# 所有长期运行服务应为 Up，configurator 应为 Exited (0)

# 2. bench doctor 健康检查
docker compose exec -T backend bash -lc \
  'cd /home/frappe/frappe-bench && bench doctor'
# 应显示 Workers online: 2，无 Redis 连接错误

# 3. HTTP 验证（使用环境变量口径，不硬编码端口）
curl -I "http://localhost:${HTTP_PORT:-8080}"
# 应返回 HTTP 200

# 4. Socket.IO 握手验证
curl -s -o /dev/null -w "%{http_code}" "http://localhost:${HTTP_PORT:-8080}/api/method/frappe.realtime.get_user_info"
# 应返回 200
```

### 10.5 完整启动（容器已停止）

```bash
# 启动所有服务
docker compose up -d

# 等待 db 健康检查通过
docker compose ps db
# 应显示 healthy

# 查看各服务状态
docker compose ps
```

### 10.6 Nginx 运行态重载（仅限紧急恢复）

**⚠️ 此操作仅在以下条件**全部同时满足**时才能执行：**

1. backend 正常运行（`docker compose ps backend` 显示 Up）
2. Redis 和 Worker 正常运行
3. frontend 仍返回 502 Bad Gateway
4. frontend 日志明确指向旧 backend 上游地址或连接拒绝
5. 确认没有 Nginx 配置文件错误

**执行命令：**

```bash
# 在 frontend 容器内执行运行态重载
docker compose exec frontend nginx -s reload
```

**执行后必须记录：**

| 记录项 | 内容 |
|--------|------|
| 执行命令 | `nginx -s reload` |
| 执行原因 | 日志证据（如 DNS 缓存旧 IP 导致 502） |
| 执行前 HTTP 状态 | 502 |
| 执行后 HTTP 状态 | 200 |

**禁止将 `nginx -s reload` 写为每次启动的固定步骤。** 这是运行态紧急恢复操作，不是正常启动流程的一部分。

### 10.7 常见故障恢复速查

| 故障 | 症状 | 恢复操作 |
|------|------|----------|
| Redis 退出 | websocket Restarting，Worker Exited，bench doctor 报 Redis 连接错误 | `docker compose start redis-cache redis-queue` → 等待 30s → 验证 websocket 自动恢复 → `docker compose start queue-long queue-short` |
| Worker 退出 | bench doctor 显示 Workers=0 | `docker compose start queue-long queue-short` |
| websocket 重启循环 | websocket 状态 Restarting，RestartCount 持续增加 | 先恢复 Redis，websocket 会自动恢复 |
| frontend 502 | HTTP 返回 502，backend 正常 | 先检查 backend 是否正常 → 检查 frontend 日志 → 如确认 DNS 缓存问题，执行 `nginx -s reload` |
| db 不健康 | `docker compose ps db` 不显示 healthy | 检查 db 日志：`docker compose logs db` → 确认 Volume 存在 → 可能需要 `docker compose restart db` |

### 10.8 禁止操作

- ❌ `docker compose down -v` — 删除所有 Volume，数据永久丢失
- ❌ 在未备份的情况下手动 `DROP DATABASE`
- ❌ 将 `nginx -s reload` 加入自动启动脚本或固定步骤
- ❌ 在 Redis 未恢复时强制重启 websocket（会继续 crash）

```

---

> ⚠️ 禁止操作：`docker compose down -v`（会删除数据库 Volume！）