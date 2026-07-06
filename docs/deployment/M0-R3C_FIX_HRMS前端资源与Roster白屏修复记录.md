# M0-R3C-FIX HRMS 前端资源与 Roster 白屏修复记录

项目名称：新乡海滨智能运营管理平台。

## 本轮目标

本轮目标是诊断并修复 M0-R3C 后出现的 HRMS 前端资源问题，包括 Frappe HR 图标缺失、HRMS 子模块图标缺失和 `/hr/roster` 白屏。

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
- `docs/deployment/M0-R3C_Frappe_HR安装验证记录.md`
- `docs/deployment/M0-R3B_Frappe_HR安装前评估.md`
- `docs/deployment/M0-R3A_Frappe_Docker最小环境落地记录.md`
- `docker-compose.yml`
- `.env.example`
- `.gitignore`

## 当前环境事实

| 项目 | 状态 |
| --- | --- |
| 工作目录 | `/Users/zhaojiale/VS Projects/HBOS` |
| 分支 | `main` |
| 修复前 HEAD | `9d7ade1eaa0e5eef86ced639b4e1efe7e04a858a` |
| site | `frontend` |
| Desk 地址 | `http://localhost:8081/login` |
| Frappe | `16.25.0` |
| ERPNext | `16.26.2` |
| HRMS | `16.12.0 version-16 (666bf10)` |

## 问题复现

浏览器登录后复现到以下现象：

- `/app` 中 Frappe HR 图标缺失。
- HRMS 子模块图标缺失。
- `/hr/roster` 页面白屏。
- `/app/employee`、`/app/attendance`、`/app/employee-checkin`、`/app/shift-type` 等基础 HR 页面可进入，但存在 HRMS 静态资源缺失。

HTTP 与浏览器网络请求复现到以下资源异常：

```text
/assets/hrms/dist/js/hrms.bundle.QS2GRVNQ.js -> 404 text/html
/assets/hrms/dist/css/hrms.bundle.IAZMW4GW.css -> 404 text/html
/assets/hrms/images/frappe-hr-logo.svg -> 404 text/html
/assets/hrms/icons/desktop_icons/solid/shift_&_attendance.svg -> 404 text/html
/assets/hrms/roster/assets/index-btX0BJWy.js -> 404 text/html
/assets/hrms/roster/assets/index-D6rG5lUy.css -> 404 text/html
/assets/hrms/roster/favicon.png -> 404 text/html
```

浏览器控制台存在 HRMS bundle 加载失败和 `hrms is not defined` 相关错误。frontend 日志也显示 HRMS assets 404。

## 根因判断

当前 Docker 环境中，backend 容器通过 `bench get-app hrms --branch version-16` 获得 HRMS app 目录，并且 `bench build` 会将 `sites/assets/hrms` 链接到 backend 容器内的 app public 目录。

frontend 容器实际 Nginx 静态资源根目录为容器本地 `/home/frappe/frappe-bench/assets`。该容器内没有 backend 中安装得到的 `/home/frappe/frappe-bench/apps/hrms/hrms/public`，因此直接保留软链会在 frontend 中形成不可解析资源，导致 HRMS JS、CSS、图标和 Roster 资源返回 404。

执行 `bench build` 后，Frappe / ERPNext 核心 CSS hash 也会更新。如果只同步 HRMS 目录，页面 HTML 会引用新的 core bundle，但 frontend 仍保留旧 core assets，可能继续出现核心 CSS 404。因此最终采用解引用方式同步 backend 当前构建出的完整静态资源到 frontend 容器实际资源目录。

此外，`sites/apps.txt` 已包含 `hrms` 后，scheduler、queue 和 websocket 等非 backend 容器也需要能在 bench venv 中导入官方 HRMS app。否则后台服务可能出现 `ModuleNotFoundError: No module named 'hrms'`。本轮同步的是官方 `frappe/hrms` app 目录，没有创建海滨自定义 App。

## 修复命令摘要

清理缓存：

```text
docker compose exec -T backend bench --site frontend clear-cache
docker compose exec -T backend bench --site frontend clear-website-cache
```

重新构建资源：

```text
docker compose exec -T backend bench build
```

补正当前 site app 清单：

```text
printf "frappe\nerpnext\nhrms\n" > sites/apps.txt
```

用解引用方式导出 backend 构建后的真实静态资源，并同步到 frontend 容器实际 Nginx 资源目录：

```text
tar chf /tmp/hbos-assets-full.tar -C /home/frappe/frappe-bench/assets .
tar xf /tmp/hbos-assets-full.tar -C /tmp/assets.new
mv /home/frappe/frappe-bench/assets /home/frappe/frappe-bench/assets.old
mv /tmp/assets.new /home/frappe/frappe-bench/assets
```

上述命令均在本地 Docker 容器运行态执行，未修改仓库中的 `docker-compose.yml`、`.env.example` 或应用源码。

同步官方 HRMS app 到后台运行容器，并在 bench venv 中注册：

```text
tar chf /tmp/hbos-hrms-app.tar -C /home/frappe/frappe-bench/apps hrms
docker compose cp /tmp/hbos-hrms-app.tar scheduler:/tmp/hbos-hrms-app.tar
docker compose cp /tmp/hbos-hrms-app.tar queue-long:/tmp/hbos-hrms-app.tar
docker compose cp /tmp/hbos-hrms-app.tar queue-short:/tmp/hbos-hrms-app.tar
docker compose cp /tmp/hbos-hrms-app.tar websocket:/tmp/hbos-hrms-app.tar
tar xf /tmp/hbos-hrms-app.tar -C /home/frappe/frappe-bench/apps
./env/bin/pip install -e apps/hrms
docker compose restart scheduler queue-long queue-short websocket
```

修复后在 scheduler、queue 和 websocket 容器中使用 bench venv 验证：

```text
venv_import_hrms_ok /home/frappe/frappe-bench/apps/hrms/hrms/__init__.py
```

## 修复后 HTTP 验证

修复后关键资源均返回 `HTTP 200`：

```text
http://localhost:8081/assets/frappe/dist/css/desk.bundle.DFQF7NHJ.css -> 200 text/css
http://localhost:8081/assets/frappe/dist/css/report.bundle.DVOTNGKX.css -> 200 text/css
http://localhost:8081/assets/erpnext/dist/css/erpnext.bundle.CFEBJ623.css -> 200 text/css
http://localhost:8081/assets/hrms/dist/js/hrms.bundle.QS2GRVNQ.js -> 200 application/javascript
http://localhost:8081/assets/hrms/dist/css/hrms.bundle.VFT3PRVJ.css -> 200 text/css
http://localhost:8081/assets/hrms/images/frappe-hr-logo.svg -> 200 image/svg+xml
http://localhost:8081/assets/hrms/roster/assets/index-btX0BJWy.js -> 200 application/javascript
http://localhost:8081/assets/hrms/roster/assets/index-D6rG5lUy.css -> 200 text/css
http://localhost:8081/assets/hrms/roster/favicon.png -> 200 image/png
http://localhost:8081/hr/roster -> 200 text/html; charset=utf-8
```

## 修复后浏览器验证

使用本地 `.env` 中的 Administrator 本地开发密码完成登录态验证；未输出真实密码。

浏览器验证结果：

| 路由 | 验证结果 |
| --- | --- |
| `/app` | 可进入 Desk，显示 `Frappe HR系统`，图片数量 30，broken images 为 0 |
| `/app/employee` | 可进入员工列表，broken images 为 0 |
| `/app/employee-checkin` | 可进入员工签到列表，broken images 为 0 |
| `/app/attendance` | 可进入考勤列表，broken images 为 0 |
| `/app/shift-type` | 可进入班次类型列表，broken images 为 0 |
| `/hr/roster/` | 可渲染 Roster 页面，显示 `Roster`、`Month View`、`July, 2026` 和 `健康元新乡海滨 (Demo)` |

`/hr/roster/` 已不再白屏。

## 容器状态

修复后 `docker compose ps` 显示核心服务运行中：

- `backend`
- `db`
- `frontend`
- `queue-long`
- `queue-short`
- `redis-cache`
- `redis-queue`
- `scheduler`
- `websocket`

修复过程中曾观察到 scheduler 因 `No module named 'hrms'` 重启。同步官方 HRMS app 并在 bench venv 中注册后，scheduler、queue 和 websocket 均可导入 HRMS，容器状态恢复为 Up。

## 已知观察项

浏览器控制台仍可观察到 `socket.io` Invalid origin 相关提示。该提示未阻塞 Desk、基础 HR 页面和 Roster 页面渲染；本轮判断其不是 HRMS 前端资源缺失和 Roster 白屏的根因，留待后续环境治理。

当前修复是运行时容器资源同步和运行时 app 同步，适合 M0-R3C-FIX 诊断修复，不代表长期可复现部署方案已经完成。后续如果重建 frontend、scheduler、queue 或 websocket 容器，仍需治理 HRMS 自定义镜像、Compose assets 持久化或部署流程。

## 当前状态

状态：COMPLETED。

M0-R3C-FIX 已完成 HRMS 前端资源与 Roster 白屏诊断修复。Frappe HR 图标、HRMS 基础模块和 `/hr/roster/` Roster 月视图已验证可访问。

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

## 下一轮建议

下一步建议交给 Codex 做 M0-R3C-FIX 审查。审查通过后，再由用户决定是否恢复 M0-R3D：HRMS 能力盘点与 M1 考勤一期边界设计。
