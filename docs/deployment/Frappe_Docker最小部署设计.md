# Frappe Docker Minimal Design

项目名称：新乡海滨智能运营管理平台。

## 设计目标

本文设计 M0-R2 阶段的 Frappe / ERPNext / Docker 最小本地开发环境。本文只描述方案，不生成 `docker-compose.yml`，不执行任何安装命令，不启动容器。

## 最小服务清单设计

- `frappe/erpnext`：承载 Frappe Framework、ERPNext 运行时和站点初始化能力。具体镜像名、版本标签和启动命令在 M0-R3 再确认。
- `mariadb`：作为 Frappe / ERPNext 主要数据库，遵循 MariaDB/MySQL 兼容路线。
- `redis-cache`：用于缓存。
- `redis-queue`：用于队列和后台任务协调。
- `scheduler/worker`：用于定时任务、短队列、长队列和后台作业执行。M0-R3 可根据官方镜像约定拆分为多个 worker 服务。
- `nginx` 或 `frontend proxy`：作为本地访问入口，代理 Frappe web 服务和静态资源。是否单独启用 nginx 在 M0-R3 根据镜像方案确认。

## 本地开发目录规划

建议后续 M0-R3 在正式仓库下规划环境文件，但不要把运行时数据和真实密钥提交到 Git。

- `deploy/`：未来放置本地 Docker 编排文件和部署说明。M0-R2 不创建。
- `deploy/env/`：未来放置 `.env.example` 等示例文件。M0-R2 不创建。
- `volumes/`：未来本地数据卷挂载目录候选。若使用 Docker named volumes，可不创建此目录。
- `sites/`：未来 Frappe site 数据目录候选。M0-R2 不创建。

上述目录均为后续方案候选，本轮不实际创建。

## 端口规划建议

- Frappe web：建议本地使用 `8080` 或 `8000`，避免占用系统常用端口。
- Nginx / frontend proxy：如启用代理，可使用 `8080` 对外暴露，内部转发到 Frappe web。
- MariaDB：建议仅容器网络内部访问；如必须暴露本机，可使用 `3307` 避免冲突。
- Redis cache / queue：建议仅容器网络内部访问，不暴露到宿主机。

M0-R3 执行前应先检查本机端口占用，再确定最终映射。

## 数据卷规划

- `mariadb-data`：保存数据库数据。
- `redis-cache-data`：保存缓存数据，可按需要设置为临时数据。
- `redis-queue-data`：保存队列相关数据。
- `frappe-sites`：保存 Frappe sites、站点配置、上传文件和私有文件。
- `frappe-logs`：保存运行日志，便于本地排查。

数据卷清理必须谨慎。M0-R3 应明确哪些卷可删除、哪些卷需要备份，不得用模糊命令清空全部运行数据。

## 环境变量分组

- 数据库变量：数据库主机、端口、库名、用户名、密码、root 密码。
- Redis 变量：cache 地址、queue 地址、socketio 或 realtime 相关 Redis 地址。
- Frappe site 变量：站点名、站点路径、安装应用列表、是否安装 ERPNext。
- 管理员账号变量：管理员用户名、管理员密码占位符。
- 域名和端口变量：本地域名、HTTP 端口、HTTPS 端口、代理端口。
- 密钥变量：加密密钥、secret key、数据库密码、管理员密码等，只允许使用占位符或本地未提交文件保存。

## 密钥与配置原则

- 不保存真实密钥。
- 不把真实 `.env` 提交到 Git。
- M0-R3 如需创建 `.env`，应同步加入 `.gitignore`，但 M0-R2 不创建 `.env`、不创建 `.gitignore`。
- 文档中只使用占位符，例如 `<DB_PASSWORD>`、`<ADMIN_PASSWORD>`、`<SECRET_KEY>`。

## 本轮禁止动作

- 不在本轮生成 `docker-compose.yml`。
- 不在本轮执行任何安装命令。
- 不拉取镜像。
- 不启动容器。
- 不初始化 Frappe site。
- 不安装 ERPNext 或 Frappe HR。
- 不创建任何 Frappe App。

## 后续 M0-R3 执行边界

M0-R3 在用户明确批准后，才可以把本文设计转化为实际最小环境落地步骤。M0-R3 应先锁定版本矩阵，再编写环境编排文件，并以可回滚方式验证 Frappe / ERPNext 最小本地访问链路。
