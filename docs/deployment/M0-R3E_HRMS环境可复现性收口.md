# M0-R3E HRMS 环境可复现性收口

项目名称：新乡海滨智能运营管理平台。

## 本轮目标

本轮只做 HRMS 环境可复现性收口：确认当前运行态环境事实，识别 HRMS 运行态安装带来的复现风险，设计 M1 阶段环境保护规则，并给出未来可复现治理路线。

本轮不进入 M1-R1，不创建自定义 Frappe App，不开发考勤业务，不重构 Docker 环境，不重建容器或删除 volume，不接飞书，不做前端驾驶舱。

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
- `docs/deployment/M0-R3C_Frappe_HR安装验证记录.md`
- `docs/design/M0-R3D_HRMS能力盘点与M1考勤边界设计.md`
- `docker-compose.yml`
- `.env.example`
- `.gitignore`

## 当前环境事实

- site 名称：`frontend`
- Desk 地址：`http://localhost:8081/login`
- Desk 验证：`curl http://localhost:8081/login` 返回 `HTTP 200 text/html; charset=utf-8`
- Docker 服务状态：`backend`、`frontend`、`db`、`redis-cache`、`redis-queue`、`scheduler`、`queue-long`、`queue-short`、`websocket` 均处于运行状态，`db` 为 healthy。
- 当前版本：
  - Frappe：`16.25.0`
  - ERPNext：`16.26.2`
  - HRMS：`16.12.0 version-16 (666bf10)`
- 当前 apps 清单：
  - `frappe 16.25.0 UNVERSIONED`
  - `erpnext 16.26.2 UNVERSIONED`
  - `hrms 16.12.0 version-16`
- 当前 HRMS 安装方式：M0-R3C 中通过运行态 `bench get-app hrms --branch version-16`、`bench --site frontend install-app hrms`、`bench --site frontend migrate` 安装验证。
- 当前运行态落点：backend 容器内存在 `/home/frappe/frappe-bench/apps/hrms`，`/home/frappe/frappe-bench/sites/apps.txt` 包含 `frappe`、`erpnext`、`hrms`。

## 当前未做事项

- 未创建 `hb_core_app`
- 未创建 `hb_attendance_app`
- 未创建 `hb_feishu_app`
- 未创建任何海滨自定义 Frappe App
- 未开发考勤业务代码
- 未录入真实员工数据
- 未配置真实班次或真实考勤规则
- 未接飞书真实写入
- 未做 Vue / React 前端驾驶舱
- 未修改 Frappe / ERPNext / HRMS 核心源码
- 未修改 `docker-compose.yml`
- 未修改 `.env.example`
- 未修改 `.gitignore`
- 未提交 `.env`、备份文件或真实密钥

## 当前风险判断

当前 HRMS 已安装在本机当前运行环境中，但仓库没有固化包含 HRMS 的自定义镜像，也没有将 HRMS 安装流程固化为可执行脚本。

因此存在以下风险：

- 如果 Docker volume 被删除、site 被重建、换机器或重新部署，HRMS 可能需要重新安装。
- `docker-compose.yml` 目前仍是最小 ERPNext / Frappe 环境，不直接声明 HRMS 已内置。
- 当前 Compose 的配置流程仍以镜像内 app 和运行态 volume 为基础，不能等同于长期可复现交付方案。
- M0-R3C-FIX 中对 HRMS 前端资源和后台服务 app 的同步属于运行态修复，不是自定义镜像级固化。
- M1 期间如误执行 `docker compose down -v` 或删除 volume，可能破坏当前已验证的 HRMS 环境。
- M1 期间如确需重建环境，必须先备份 site，并确认 HRMS 恢复方案后再执行。

## 可复现策略比较

### A. 继续运行态安装 + 文档化恢复流程

优点：

- 不破坏当前已跑通的 Frappe / ERPNext / HRMS 环境。
- 不引入自定义镜像、构建流程和额外部署复杂度。
- 适合 M1 初期单机业务验证阶段。

风险：

- 依赖当前 Docker volume 和运行态容器状态。
- 换机器、删除 volume、重建 site 后需要人工恢复。
- 新成员复现环境时仍需要参考安装记录手动执行。

适用阶段：

- 适合 M1 初期业务验证尚未稳定前使用。

回滚 / 恢复方式：

- 保留当前 volume 和 site。
- 如 HRMS 丢失，先备份 site，再参考 M0-R3C 安装验证记录重新执行 HRMS 安装、migrate 和访问验证。

### B. 新增安装脚本或运维手册，用于重建后自动 get-app / install-app

优点：

- 比纯人工记录更容易复现。
- 可以保留当前最小 Compose 架构，同时降低重建后的恢复成本。
- 适合在 M1 过程中逐步形成可审查的运维手册。

风险：

- 仍然属于运行态安装，不能完全消除环境漂移。
- 脚本需要处理容器状态、site 状态、重复安装、失败回滚和敏感信息，过早实现可能引入新风险。
- 如果脚本未经充分验证，可能误伤当前可用环境。

适用阶段：

- 适合 M1 中后段或 M0 最终收口后，作为环境治理增强项设计。

是否现在需要实现：

- 本轮不实现脚本，只保留恢复手册草案和触发条件。

回滚 / 恢复方式：

- 脚本化前必须保留手动步骤和 site 备份。
- 脚本执行失败时停止业务开发，回到备份和手动恢复路径。

### C. 构建包含 HRMS 的自定义镜像或扩展 frappe_docker 流程

优点：

- 可复现性最好，适合多人开发、服务器部署、长期交付和 CI/CD。
- HRMS app、依赖、前端资源和后台服务环境可以随镜像固化。
- 能降低运行态容器差异导致的白屏、后台服务缺 app 等问题。

风险：

- 会引入镜像构建、版本锁定、构建缓存、镜像发布和升级维护成本。
- 可能扰动当前已跑通的最小环境。
- 在 M1 业务验证尚未稳定前，过早重构镜像可能让问题定位变复杂。

适用阶段：

- 适合 M1 验证完成后准备长期交付、多人协作或服务器部署时启动。

是否现在需要实现：

- 本轮不实现自定义镜像，也不修改 `docker-compose.yml`。

回滚 / 恢复方式：

- 保留当前最小 Compose 和当前 volume 作为可用基线。
- 自定义镜像方案应在独立轮次验证，失败时回退到当前已验证环境。

## 当前推荐结论

M1 初期优先保留当前运行态环境，不急于重构镜像。

在 M1 业务验证未稳定前，不创建自定义 Docker 镜像，不重构 Compose 流程，避免把环境治理复杂度提前混入业务验证。

必须将“禁止删除 volume / 重建 site”写入 M1 开发约束。若未来准备多人开发、服务器部署、长期交付或 CI/CD，再启动单独的环境可复现阶段，构建包含 HRMS 的可复现镜像或安装流程。

## M1 环境保护规则

M1 期间必须遵守：

- 不得无用户明确授权执行 `docker compose down -v`。
- 不得删除 Docker volume。
- 不得删除 site。
- 不得重建 `frontend` site。
- 不得重新初始化 ERPNext。
- 每轮 M1 开始前检查 `bench --site frontend list-apps` 是否仍包含 `frappe`、`erpnext`、`hrms`。
- 每轮 M1 收尾检查 Desk 是否仍可访问。
- 如 HRMS 丢失，必须停止业务开发，先恢复环境。
- `.env` 不得提交。
- 备份文件不得提交。
- 不得将真实员工数据、真实班次、真实考勤规则或真实密钥写入仓库。

## HRMS 恢复手册草案

本节只记录草案，本轮不执行恢复、不重建环境、不重新安装 HRMS。

建议恢复流程：

1. 检查 Docker 与 Compose 是否可用。
2. 执行 `docker compose ps`，确认关键服务状态。
3. 执行 `docker compose exec -T backend bench version`，确认 Frappe / ERPNext / HRMS 版本。
4. 执行 `docker compose exec -T backend bench --site frontend list-apps`，确认 apps 清单。
5. 如果 HRMS 不存在，先备份 `frontend` site。
6. 参考 `docs/deployment/M0-R3C_Frappe_HR安装验证记录.md` 重新执行 HRMS 安装。
7. 执行 `bench --site frontend migrate`。
8. 验证 Desk 登录页、HR Workspace、Employee、Attendance、Employee Checkin、Shift Type。
9. 不在日志或文档中输出真实管理员密码、数据库密码或 token。

## 是否需要现在修改 docker-compose.yml

本轮不修改 `docker-compose.yml`。

原因：

- M1 业务验证前，优先稳定使用当前已跑通环境。
- 当前 Compose 已能承载 M0-R3A 的最小 Frappe / ERPNext 环境和当前运行态 HRMS 验证。
- 过早引入自定义镜像会增加构建、部署和排障复杂度。

已知风险：

- 运行态安装不如自定义镜像可复现。
- 当前环境依赖本机 volume 和运行态修复成果。

后续触发条件：

- 换机器部署。
- 新成员需要复现环境。
- 准备服务器部署。
- M1 验证完成后准备交付。
- 需要 CI/CD。
- 当前容器重建导致 HRMS 丢失。

## M1 启动门禁参考

建议 M1 启动前必须满足：

- 当前 Desk 可访问。
- `bench --site frontend list-apps` 包含 `frappe`、`erpnext`、`hrms`。
- HR Workspace 可访问。
- 当前无海滨自定义 App。
- `git status` clean。
- M0 状态已封板。
- M0-REMOTE 已完成 GitHub Private remote、`origin` 和首次 push `main`。
- 用户明确确认进入 M1。

M0-FINAL 后的启动顺序为：先 M0-REMOTE，再 M1-R0；M1-R1 才验证 HRMS 原生考勤对象模型。

## 本轮结论

状态：COMPLETED。

M0-R3E 已完成 HRMS 环境可复现性风险识别、策略比较、M1 环境保护规则和恢复手册草案，并已通过 Codex 审查。当前推荐继续保护已跑通的运行态环境，M1 初期不重构镜像，不删除 volume，不重建 site，不提前进入业务开发。
