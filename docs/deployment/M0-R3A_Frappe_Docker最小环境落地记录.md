# M0-R3A Frappe Docker 最小环境落地记录

项目名称：新乡海滨智能运营管理平台。

## 本轮目标

完成 Frappe / ERPNext / Docker 的最小本地环境落地，创建最小 Compose 配置、环境变量示例、忽略规则和落地记录，并验证 Frappe Desk 登录页可访问。

## 本轮读取文件

- `README.md`
- `CLAUDE.md`
- `AGENTS.md`
- `docs/AI_CONTEXT.md`
- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/READING_GUIDE.md`
- `docs/milestones/README.md`
- `docs/milestones/M0.md`
- `docs/plans/M0-R2_Frappe_Docker最小环境方案设计.md`
- `docs/deployment/Frappe_Docker最小部署设计.md`
- `docs/deployment/本地开发环境变量说明.md`
- `docs/adr/0001-use-frappe-erpnext-as-platform-base.md`
- `docs/adr/0002-use-mariadb-compatible-database.md`

## 本轮创建文件

- `docker-compose.yml`
- `.env.example`
- `.gitignore`
- `docs/deployment/M0-R3A_Frappe_Docker最小环境落地记录.md`

## 官方参考来源

- `frappe/frappe_docker` 官方仓库 README：说明该仓库是 Frappe 应用的官方容器设置，并提供 Compose 配置。
- `frappe/frappe_docker` 官方 `pwd.yml`：作为本轮最小本地短期验证配置的主要结构参考。
- `frappe/frappe_docker` 官方 `docs/01-getting-started/01-choosing-a-deployment-method.md`：说明 `pwd.yml` 适用于快速探索、演示和短期测试，不用于生产或长期开发。
- `frappe/frappe_docker` 官方 `example.env`：作为环境变量命名与默认端口参考。

## 版本矩阵

| 组件 | 本轮采用版本或镜像 tag | 来源 |
| --- | --- | --- |
| Frappe / ERPNext 镜像 | `frappe/erpnext:v16.26.2` | 官方 `pwd.yml` |
| ERPNext 应用 | 随 `frappe/erpnext:v16.26.2` 镜像安装 | 官方 `pwd.yml` 的 `--install-app erpnext` |
| Frappe Framework | 随 `frappe/erpnext:v16.26.2` 镜像提供，待容器可运行后用 `bench version` 验证精确 app 版本 | 官方镜像 |
| MariaDB | `mariadb:11.8` | 官方 `pwd.yml` |
| Redis | `redis:6.2-alpine` | 官方 `pwd.yml` |

## 本地端口

- HTTP 访问端口：`${HTTP_PORT}`，`.env.example` 默认 `8080`
- 容器内 frontend 端口：`8080`
- MariaDB：仅 Compose 网络内部访问，不暴露宿主机端口
- Redis cache / queue：仅 Compose 网络内部访问，不暴露宿主机端口

## 容器服务清单

- `backend`
- `configurator`
- `create-site`
- `db`
- `frontend`
- `queue-long`
- `queue-short`
- `redis-cache`
- `redis-queue`
- `scheduler`
- `websocket`

## 数据卷说明

- `db-data`：MariaDB 数据
- `redis-queue-data`：Redis queue 数据
- `sites`：Frappe sites、站点配置、上传文件
- `logs`：Frappe / ERPNext 运行日志

## 执行步骤摘要

1. 已确认官方 `frappe/frappe_docker` 仓库、`pwd.yml`、`example.env` 和部署方式说明。
2. 已创建 `docker-compose.yml`，结构贴近官方 `pwd.yml`，仅做本地变量化。
3. 已创建 `.env.example`，只包含占位符和本地开发默认值，不含真实密钥。
4. 已创建 `.gitignore`，忽略 `.env`、运行目录和常见本地缓存。
5. 原执行 Docker 可用性检查时，当前机器返回 `zsh:1: command not found: docker`。
6. 本轮提交前只读复查时，`docker --version` 和 `docker compose version` 已可用，但本轮明确禁止启动 Docker / 容器，因此未继续执行启动验证。

## 验证结果

状态：BLOCKED。

原执行时本机未提供 `docker` 命令，无法继续执行镜像拉取、容器启动、site 初始化、ERPNext 安装和 Frappe Desk 访问验证。

本轮提交前只读复查结果：

```text
Docker version 29.6.1, build 8900f1d
Docker Compose version v5.3.0
```

由于本轮明确禁止启动 Docker / 容器，未继续执行 `docker compose up`、site 初始化或 Desk 访问验证。M0-R3A 仍保持 BLOCKED，等待下一轮用户明确授权继续。

已执行的检查：

```text
docker --version && docker compose version
```

错误摘要：

```text
zsh:1: command not found: docker
```

## 访问地址

计划访问地址：`http://localhost:${HTTP_PORT}`，按 `.env.example` 默认值为 `http://localhost:8080`。

实际访问验证：未完成，原因是原执行时 Docker 不可用；本轮提交前虽已能看到 Docker CLI，但禁止启动容器，未继续验证。

## 已知问题

- 原执行时本机缺少 Docker CLI 或 Docker Desktop 未安装 / 未加入当前 shell PATH。
- 本轮提交前只读复查显示 Docker CLI 已可见，但未获本轮启动授权。
- 尚不能确认 `frappe/erpnext:v16.26.2` 镜像实际拉取、容器健康状态、site 初始化和 Desk 登录页。
- `.env` 已删除，避免后续误用；待继续执行时再从 `.env.example` 复制并填写本地开发值。

## 未做事项

- 未创建 `hb_core_app`
- 未创建 `hb_attendance_app`
- 未创建 `hb_feishu_app`
- 未安装自定义 Frappe App
- 未安装 Frappe HR / HRMS
- 未开发考勤业务
- 未接飞书真实写入
- 未做前端驾驶舱
- 未写 Python / JavaScript / TypeScript 业务代码
- 未引入第三方业务源码
- 未 push
- 未配置 remote
- 未提交真实密钥

## 下一轮建议

下一轮由用户明确授权继续后，再执行：

```text
cp .env.example .env
docker compose pull
docker compose up -d
docker compose ps
docker compose logs create-site
```

如果 `create-site` 成功，再访问 `http://localhost:8080` 验证 Frappe Desk 登录页。
