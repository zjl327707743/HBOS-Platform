# M0-R3C Frappe HR 安装验证记录

项目名称：新乡海滨智能运营管理平台。

## 本轮目标

本轮目标是在已跑通的 Frappe / ERPNext Docker 最小环境中安装 Frappe HR / HRMS，并验证 HRMS App、Desk 登录页和基础 HR 模块可访问。

本轮不创建海滨自定义 Frappe App，不开发考勤业务规则，不配置飞书，不执行飞书真实写入，不做 Vue / React 前端驾驶舱，不修改 Frappe / ERPNext / HRMS 核心源码。

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
- `docs/deployment/M0-R3A_Frappe_Docker最小环境落地记录.md`
- `docs/deployment/M0-R3B_Frappe_HR安装前评估.md`
- `docker-compose.yml`
- `.env.example`
- `.gitignore`

## 安装前环境状态

| 项目 | 安装前状态 |
| --- | --- |
| 工作目录 | `/Users/zhaojiale/VS Projects/HBOS` |
| 分支 | `main` |
| 安装前 HEAD | `1fd252298dd145d1b5c9945e9123cd61f1025f81` |
| git status | clean |
| site | `frontend` |
| Desk 地址 | `http://localhost:8081/login` |
| HRMS | 未安装 |
| `.env` | 存在于本地，未被 Git 追踪 |

安装前 `docker compose ps` 显示核心服务运行中：

- `backend`
- `db`
- `frontend`
- `queue-long`
- `queue-short`
- `redis-cache`
- `redis-queue`
- `scheduler`
- `websocket`

## Docker / Compose 版本

```text
Docker version 29.6.1, build 8900f1d
Docker Compose version v5.3.0
```

## 安装前 bench version

```text
erpnext 16.26.2
frappe 16.25.0
```

## 安装前 list-apps

```text
frappe  16.25.0 UNVERSIONED
erpnext 16.26.2 UNVERSIONED
```

安装前 `hrms` 未出现在 `bench --site frontend list-apps` 中。

## 备份结果

安装前执行：

```text
docker compose exec -T backend bench --site frontend backup
```

执行结果：

```text
Backup Summary for frontend at 2026-07-06 11:27:08.207508
Config  : /home/frappe/frappe-bench/sites/frontend/private/backups/20260706_112705-frontend-site_config_backup.json 176.0B
Database: /home/frappe/frappe-bench/sites/frontend/private/backups/20260706_112705-frontend-database.sql.gz 849.0KiB
Backup for Site frontend has been successfully completed
```

备份文件位于 Docker volume 内的 site 私有备份目录，未提交到 Git。仓库 `.gitignore` 已忽略宿主机 `sites/`、`backups/` 等目录。

## HRMS 来源 / 分支 / 版本

官方来源：

- 官方仓库：`https://github.com/frappe/hrms`
- 官方文档：`https://docs.frappe.io/hr/introduction`
- 官方 v16 分支：`version-16`

安装前确认：

```text
666bf10a9271421abc361bded124d2d961a977e3 refs/heads/version-16
```

`version-16` 依赖范围：

```text
frappe = ">=16.0.0,<17.0.0"
erpnext = ">=16.0.0,<17.0.0"
```

安装后版本：

```text
hrms 16.12.0 version-16 (666bf10)
```

## 安装命令摘要

```text
docker compose exec -T backend bench get-app hrms --branch version-16
docker compose exec -T backend bench --site frontend install-app hrms
docker compose exec -T backend bench --site frontend migrate
docker compose restart
```

全量 `docker compose restart` 会重新运行一次性 `configurator` 和 `create-site` 服务；`create-site` 因 site 已存在退出，日志显示：

```text
Site frontend already exists, use `--force` to proceed anyway
```

该退出发生在已存在 site 的一次性初始化服务中；核心运行服务仍保持运行。

## 安装日志摘要

`bench get-app`：

- 已 clone `https://github.com/frappe/hrms.git --branch version-16`
- 已安装 Python 依赖
- 已执行 HRMS 前端、PWA、roster 资产构建
- 已编译 HRMS 翻译文件

`bench --site frontend install-app hrms`：

```text
Installing hrms...
Setting up Frappe HR...
Patching Existing Data...
Thank you for installing Frappe HR!
Creating Workspace Sidebars
Creating Desktop Icons
Updating Dashboard for hrms
```

安装日志中存在非阻塞提示：

```text
rename_field: kra_title not found in table for: Appraisal Template
rename_field: kra_template not found in table for: Appraisal
```

本轮未观察到安装命令失败。

## migrate / restart 结果

`bench --site frontend migrate` 成功完成，摘要如下：

```text
Migrating frontend
Syncing jobs...
Syncing fixtures...
Syncing dashboards...
Updating Dashboard for frappe
Updating Dashboard for erpnext
Updating Dashboard for hrms
Syncing customizations...
Syncing languages...
Updating installed applications...
Executing `after_migrate` hooks...
Queued rebuilding of search index for frontend
```

`docker compose restart` 后核心服务运行中。由于当前 Compose 中 `configurator` 会执行 `ls -1 apps > sites/apps.txt`，而 HRMS 是本轮在 backend 容器内通过 `bench get-app` 安装的临时验证 App，restart 后 `sites/apps.txt` 曾被重写为仅包含 `erpnext`、`frappe`。

本轮已在 Docker volume 内补正 `sites/apps.txt`：

```text
frappe
erpnext
hrms
```

补正后 `bench version` 可显示 HRMS。该现象说明当前 M0-R3C 方案适合安装验证，但后续如要形成可复现长期环境，应在后续轮次治理 HRMS 镜像 / Compose 持久化策略。

## 安装后 bench version

```text
erpnext 16.26.2
frappe 16.25.0
hrms 16.12.0 version-16 (666bf10)
```

## 安装后 list-apps

```text
frappe  16.25.0 UNVERSIONED
erpnext 16.26.2 UNVERSIONED
hrms    16.12.0 version-16
```

站点内应用清单验证：

```text
installed_apps = ['frappe', 'erpnext', 'hrms']
installed_app_versions = [
  {'app_name': 'hrms', 'app_version': '16.12.0'},
  {'app_name': 'erpnext', 'app_version': '16.26.2'},
  {'app_name': 'frappe', 'app_version': '16.25.0'}
]
```

## Desk 验证结果

Desk 登录页验证：

```text
http://localhost:8081/login
HTTP 200
```

使用本地 `.env` 中的 Administrator 本地开发密码完成登录态验证；未输出真实密码。

登录后 Desk 路由验证：

```text
/app/hr -> 200 http://localhost:8081/desk/hr
/app/hr-setup -> 200 http://localhost:8081/desk/hr-setup
/app/employee -> 200 http://localhost:8081/desk/employee
/app/leave-application -> 200 http://localhost:8081/desk/leave-application
/app/shift-and-attendance -> 200 http://localhost:8081/desk/shift-and-attendance
```

## HR 模块访问验证结果

站点内 HR Workspace 验证：

```text
Expenses
HR Setup
Leaves
Performance
Recruitment
Shift & Attendance
Tenure
```

基础 HR DocType 验证：

```text
Attendance        HR
Employee          Setup
Employee Checkin  HR
Leave Application HR
Shift Type        HR
```

本轮未创建员工、请假、考勤、班次等真实业务数据。

## 当前状态

状态：COMPLETED。

M0-R3C 已完成 HRMS 安装验证。HRMS App 已安装到 `frontend` site，Desk 与 HR 相关基础路由可访问。

## 未做事项

- 未创建 `hb_core_app`
- 未创建 `hb_attendance_app`
- 未创建 `hb_feishu_app`
- 未创建任何海滨自定义 Frappe App
- 未开发考勤业务规则
- 未配置飞书
- 未执行飞书真实写入
- 未做 Vue / React 前端驾驶舱
- 未新增 Python / JavaScript / TypeScript 业务代码
- 未修改 Frappe / ERPNext / HRMS 核心源码
- 未修改 `docker-compose.yml`
- 未修改 `.env.example`
- 未提交 `.env`
- 未提交真实密钥
- 未配置 remote
- 未 push

## 风险与回滚说明

已知风险：

- 当前 HRMS 是通过现有 backend 容器内 `bench get-app` 安装验证，不是通过自定义镜像固化。
- 当前 Compose 的 `configurator` 会基于镜像内 `apps` 目录重写 `sites/apps.txt`；全量 restart 后需要确认 `hrms` 是否仍在 `sites/apps.txt`。
- 当前方式验证了 HRMS 可安装和可访问，但不代表长期部署形态已经完成。

回滚方式：

- 优先使用安装前备份恢复 `frontend` site。
- 如可安全卸载，可评估执行 `bench --site frontend uninstall-app hrms`，但需另行授权并先备份。
- 如本地测试环境可丢弃，可停止容器、清理相关 volume，并按 M0-R3A 记录重建 site。
- Git 层面仅提交文档和状态记录；如文档需回退，可用 Git 回退本次提交。

## 下一轮建议

下一轮建议进入 M0-R3D：HRMS 能力盘点与 M1 考勤一期边界设计。

M0-R3D 仍不应开发海滨自定义 App，不应配置飞书真实写入，不应创建考勤业务规则。建议先盘点 HRMS 已提供的 Employee、Attendance、Employee Checkin、Shift Type、Leave Application 等能力，再定义 M1 的最小业务边界。
