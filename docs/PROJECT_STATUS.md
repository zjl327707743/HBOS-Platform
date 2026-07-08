# Project Status

项目名称：新乡海滨智能运营管理平台。

## 当前状态

- 当前阶段：M1 规划与验证阶段
- 当前轮次：M1-R5 HRMS 配置基线、考勤工作台与月度汇总 Demo（REVIEWING）
- 当前仓库定位：工程启动文档、AI 上下文、里程碑状态、计划、ADR、环境设计文档与最小 Docker 配置
- 当前实现状态：M0-R3A 已完成 Frappe / ERPNext / Docker 最小本地环境落地；M0-R3B 已完成 HRMS 安装前评估并通过 Codex 审查；M0-R3C 已完成 HRMS 安装验证；M0-R3C-FIX 已完成 HRMS 前端资源与 Roster 白屏诊断修复；M0-R3D 已完成 HRMS 能力盘点与 M1 考勤一期边界设计；M0-R3E 已完成 HRMS 环境可复现性收口并通过 Codex 审查；M0 整体状态为 COMPLETED；M0-REMOTE 已完成 GitHub Private remote 创建、`origin` 绑定和 `main` 首次 push；M1-R0 已通过 Codex 独立审查并收口为 COMPLETED；M1-R1 已通过 Codex 独立审查并收口为 COMPLETED；M1-R2 已通过 Codex 独立审查并收口为 COMPLETED；M1-R3 已执行 HRMS 原生考勤最小测试数据试运行并通过 Codex 审查，但实际结果为 PARTIAL / BLOCKED，最终状态收口为 BLOCKED；M1-R3A 已通过 Codex 审查并收口为 COMPLETED；M1-R3B 已通过 Codex 审查并收口为 COMPLETED；M1-R3B-FIX 已通过 Codex 审查并收口为 COMPLETED；M1-R3C 已通过 Codex 审查并收口为 COMPLETED，结论为 PARTIAL / GAP_IDENTIFIED；M1-R3D 已通过 Codex 审查并收口为 COMPLETED，结论为 Gap 四类分类、均不需要立即创建 hb_attendance_app；M1-R3E 已通过 Codex 审查并收口为 COMPLETED；M1-R3F 已通过 Codex 审查并收口为 COMPLETED；M1-REQ-DESIGN-DRAFT 已通过 Codex 审查并收口为 COMPLETED；M1-R4 已通过 Codex 审查并收口为 COMPLETED；M1-R5 已完成 HRMS 配置基线、考勤工作台与月度汇总 Demo 文档交付，当前为 REVIEWING；M1-R6/R7/R8 均为 PLANNED，待用户逐轮授权；当前未创建海滨自定义 App，未开发业务，未接真实飞书，未实现 SSO
- 当前远端：`origin` -> `https://github.com/zjl327707743/HBOS.git`，GitHub visibility = `PRIVATE`
- 下一步路线：M1-R5 当前为 REVIEWING，等待 Codex 审查或用户验收。M1-R6/R7 均为 PLANNED，待用户逐轮授权后启动。

## 状态更新制度

项目总状态必须在每轮任务收尾时同步更新。

- 如本轮改变项目状态，必须更新 `docs/PROJECT_STATUS.md`。
- 如本轮改变当前里程碑或轮次，必须更新 `docs/CURRENT_MILESTONE.md`。
- 如本轮属于某个里程碑，必须更新 `docs/milestones/M0.md` 或对应里程碑文件。
- 输出结果时必须说明状态文件是否已更新；如未更新，必须说明原因。

## M1-R3 状态

状态：BLOCKED。

执行结论：PARTIAL / BLOCKED。

收口记录：M1-R3 已通过 Codex 审查，审查结果为 PASS；由于本轮实际结果不是成功完成，而是 PARTIAL / BLOCKED，M1-R3 不标记为 COMPLETED，最终状态收口为 BLOCKED。

本轮目标：

- 在本地 `frontend` site 中使用 `TEST-HBOS-M1R3-` 前缀虚构最小测试数据试运行 HRMS 原生考勤配置链路。
- 覆盖早班、中班、夜班、跨夜班和 14 个打卡 / 请假 / 加班 / 节假日 / 调班场景。
- 记录 HRMS 原生可用项、需配置项和 Gap。

当前结果：

- 已创建 `TEST-HBOS-M1R3-虚构节假日`。
- 已创建 `TEST-HBOS-M1R3-生产一部 - 健D`、`TEST-HBOS-M1R3-生产二部 - 健D`。
- 已创建 `TEST-HBOS-M1R3-虚构事假`。
- `TEST-HBOS-M1R3-虚构公司` 标准创建在 `tabCompany` insert 阶段遇到 lock wait / 长时间阻塞，未创建。
- TEST User / Employee 创建未完成，导致 Shift Type、Shift Assignment、Employee Checkin、Leave Application 和 Attendance 闭环未执行完成。
- 14 个考勤场景未生成 Attendance，不能判定 HRMS 原生考勤链路通过。
- 本轮未越界，未继续创建测试数据，未清理 TEST 数据，未提交 `.env`、密钥、数据库、日志、缓存、备份或运行时产物。

本轮结论：

- 当前仍不建议创建 `hb_attendance_app`。
- 阻断点是运行态 ORM 写入 / 数据库连接或锁问题，不是 HRMS 原生对象模型已被证明无法覆盖。
- M1-R3A 已完成运行态阻断诊断与 TEST 数据隔离 / 清理方案，并已通过 Codex 审查收口为 COMPLETED。
- M1-R3B 已完成运行态最小修复方案，并已通过 Codex 审查收口为 COMPLETED；本轮未执行修复、未清理 TEST 数据、未继续试运行。
- M1-R3B-FIX 已通过 Codex 审查，审查结果 PASS，状态已从 REVIEWING 收口为 COMPLETED。
- M1-R3B-FIX 只执行 `docker compose up -d redis-cache redis-queue`，未再执行额外服务启动 / 重启，未清理 TEST 数据，未继续试运行。
- M1-R3B-FIX 已确认 `redis-cache`、`redis-queue`、queue worker、scheduler、`bench doctor` 和 `/login` 已恢复或改善。
- M1-R3B-FIX 只读计数确认当前 TEST 数据包括 Employee 8、Shift Type 4、Shift Assignment 14、Employee Checkin 22、Leave Application 2、Attendance 12 等；本轮没有手工创建、删除或清理 TEST 数据，计数高于 M1-R3A / M1-R3B 旧记录，来源需在 M1-R3C 或清理授权前复核。
- M1-R3C 已按用户授权执行 HRMS 原生考勤最小试运行复测，使用新前缀 `TEST-HBOS-M1R3C-*` / `test-hbos-m1r3c-*`，未覆盖旧 `TEST-HBOS-M1R3-*` 数据。
- Company / User / Employee 写入阻断已解除：Company 1、User 8、Employee 8 已成功创建。
- M1-R3C 最终计数包括 Department 2、Holiday List 1、Shift Type 4、Shift Assignment 14、Employee Checkin 22、Leave Type 1、Attendance 13；Leave Application 因缺少 Leave Allocation 未创建。
- 14 个场景已完成复测记录：正常早班、中班、夜班、跨夜班、临时调班等基础链路可用；迟到 / 早退标记、缺卡、请假前置、全天缺勤、加班和节假日业务口径仍存在配置或业务 Gap。
- M1-R3C 已通过 Codex 审查并收口为 COMPLETED，结论为 PARTIAL / GAP_IDENTIFIED。M1-R3C 是试运行完成，不是考勤业务闭环完成。
- M1-R3D 已完成异常口径与 Gap 诊断文档交付，并已通过 Codex 审查收口为 COMPLETED；结论为 Gap 四类分类、均不需要立即创建 hb_attendance_app。
- M1-R3E 已形成配置复核清单与海滨业务口径确认表，并已通过 Codex 审查收口为 COMPLETED；8/10 项业务口径阻塞 M1-R4。
- M1-R3F 已形成面向业务负责人的确认包，并已通过 Codex 审查收口为 COMPLETED；9 项确认主题中 7 项必须确认，2 项可先按默认值推进。
- M1-REQ-DESIGN-DRAFT 已通过 Codex 审查并收口为 COMPLETED；初审员工姓名脱敏 blocker 已修复，复审 PASS。
- M1-R4 已通过 Codex 审查并收口为 COMPLETED。Codex 初审发现状态入口 blocker，修复后复审 PASS。主文档 `docs/milestones/M1_R4_Demo技术方案与实施路线拆分.md` 已交付。
- M1-R5 已完成 HRMS 配置基线、考勤工作台入口、月度汇总 Demo 展示路径和 Excel 月报导出路径文档交付，当前状态为 REVIEWING。主文档 `docs/milestones/M1_R5_HRMS配置基线工作台月报Demo.md` 已交付。本轮仅修改文档和配置说明，未创建 App，未创建 DocType，未修改核心源码，未写入 Frappe site 数据库，未启动 R6/R7。

## 已确认架构方向

准确叫法：Frappe/ERPNext 开源底座 + Frappe 多 App 模块化架构 + 外部独立服务扩展。

长期架构：Frappe/ERPNext 开源底座 + 海滨自定义 Frappe App + 外部 AI/视频/算法服务 + Vue/React 驾驶舱 + 飞书集成 + Docker 部署。

主技术栈：Frappe Framework、ERPNext、Frappe HR、Python、JavaScript、MariaDB/MySQL 兼容体系、Redis、Docker、Docker Compose、Vue/React、ECharts、FastAPI。

## M0-R1 状态

状态：已完成并封板。

本轮目标：

- 创建根目录说明文档
- 创建 AI 协作上下文文档
- 创建当前里程碑文档
- 创建 M0 工程启动计划
- 创建四个基础 ADR

本轮未做：

- 未安装 Frappe/ERPNext/Frappe HR
- 未创建 Frappe bench
- 未创建任何 Frappe App
- 未创建 `hb_core_app`、`hb_attendance_app`、`hb_feishu_app`
- 未写 Docker Compose
- 未开发考勤业务
- 未接入飞书
- 未开发前端驾驶舱

## M0-R2 状态

状态：已完成并通过 Codex 审查，已提交。

本轮目标：

- 设计 Frappe / ERPNext / Docker 最小本地开发环境方案
- 设计最小服务清单、目录规划、端口规划、数据卷规划和环境变量分组
- 明确 M0-R3 才允许真正落地 `docker-compose.yml` 与 Frappe 环境

本轮未做：

- 未安装 Frappe/ERPNext/Frappe HR
- 未创建 Frappe bench
- 未创建任何 Frappe App
- 未创建 `hb_core_app`、`hb_attendance_app`、`hb_feishu_app`
- 未写 Docker Compose
- 未创建 `.env`
- 未启动容器
- 未开发考勤业务
- 未接入飞书
- 未开发前端驾驶舱

## M0-R2B 状态

状态：已完成并通过 Codex 审查，已提交。

本轮目标：

- 建立里程碑规划和状态文件机制
- 固化每轮收尾必须更新状态的规则
- 新增 `docs/milestones/README.md` 和 `docs/milestones/M0.md`
- 更新协作规则、项目状态、当前里程碑、阅读指南和 M0-R2 计划

本轮未做：

- 未安装 Frappe/ERPNext/Frappe HR
- 未创建 Frappe bench
- 未创建任何 Frappe App
- 未写 Docker Compose
- 未创建 `.env`
- 未创建 `.gitignore`
- 未启动容器
- 未开发考勤业务
- 未接入飞书
- 未开发前端驾驶舱

## M0-R2C 状态

状态：已完成。

本轮目标：

- 收口 M0-R2 批次状态台账
- 确认 M0-R3 未开始
- 创建一次 Git 提交

本轮未做：

- 未安装任何 skill
- 未执行飞书真实写入
- 未安装 Frappe/ERPNext/Frappe HR
- 未创建 Frappe bench
- 未创建任何 Frappe App
- 未写 Docker Compose
- 未创建 `.env`
- 未启动容器
- 未开发业务代码
- 未开发前端驾驶舱

## M0-R2A 状态

状态：已完成并通过 Codex 审查，已提交。

本轮目标：

- 修复默认入口文档中的过期当前轮次描述
- 确保状态入口指向当前真实进度

## M0-R2D 状态

状态：已完成。

本轮目标：

- 新增并纳入 `docs/AI技能路由规范.md`
- 明确已确认可用 skill 与候选 skill 的边界
- 将 skill 路由规则接入 `CLAUDE.md`、`AGENTS.md`、`docs/AI_CONTEXT.md` 和 `docs/READING_GUIDE.md`
- 固化 Git 提交描述优先中文的规则
- 固化新增文档名称优先中文或中英混合的规则
- 将 M0-R2 批次新增英文文档改为中文或中英混合文件名

本轮未做：

- 未安装 Frappe/ERPNext/Frappe HR
- 未创建 Frappe bench
- 未创建任何 Frappe App
- 未写 Docker Compose
- 未创建 `.env`
- 未创建 `.gitignore`
- 未启动容器
- 未开发考勤业务
- 未执行飞书真实写入
- 未开发前端驾驶舱

## M0-R2E 状态

状态：已完成。

本轮目标：

- 修复 `README.md` 中过期的阶段描述
- 在协作规则中补强公共入口文件收尾检查规则
- 同步项目状态、当前里程碑和 M0 里程碑台账
- 创建一次 Git 提交

本轮未做：

- 未安装 Frappe/ERPNext/Frappe HR
- 未创建 Frappe bench
- 未创建任何 Frappe App
- 未写 Docker Compose
- 未创建 `.env`
- 未创建 `.gitignore`
- 未启动容器
- 未开发考勤业务
- 未执行飞书真实写入
- 未开发前端驾驶舱

## M0-R3A 状态

状态：COMPLETED。

本轮目标：

- 创建 Frappe / ERPNext / Docker 最小本地环境配置
- 创建 `.env.example`、`.gitignore` 和落地记录文档
- 基于官方 `frappe/frappe_docker` 资料确认版本和服务结构
- 拉取镜像、启动容器、初始化本地测试 site、验证 Frappe Desk

当前结果：

- 已创建最小 Docker 配置和落地记录
- 已基于官方 `pwd.yml` 确认服务结构与镜像 tag
- 原执行时本机执行 `docker --version && docker compose version` 返回 `zsh:1: command not found: docker`
- 本轮 M0-R3A-VERIFY 已获用户授权继续执行真实 Docker 本地启动验证
- 本轮确认 `docker --version` 和 `docker compose version` 已可用
- 已从 `.env.example` 生成本地 `.env`，`.env` 被 `.gitignore` 忽略且未被 Git 追踪
- 已执行 `docker compose pull`，但在拉取镜像时失败：Docker Hub token 获取返回 EOF
- M0-R3A-PULL-RETRY 已重试 `docker compose pull` 并成功拉取 `redis:6.2-alpine`、`mariadb:11.8`、`frappe/erpnext:v16.26.2`
- 首次 `docker compose up -d` 遇到宿主机 `8080` 端口占用，仅调整本地 `.env` 的 `HTTP_PORT=8081` 后启动成功；`.env` 未被 Git 追踪
- `create-site` 已成功完成，测试 site 为 `frontend`
- `bench version` 验证：ERPNext `16.26.2`，Frappe `16.25.0`
- Frappe Desk 登录页已通过 `http://localhost:8081/login` 验证，返回 `HTTP 200`

本轮未做：

- 未创建 `hb_core_app`
- 未创建 `hb_attendance_app`
- 未创建 `hb_feishu_app`
- 未安装自定义 Frappe App
- 未安装 Frappe HR / HRMS
- 未开发考勤业务
- 未执行飞书真实写入
- 未开发前端驾驶舱
- 未写 Python/JavaScript/TypeScript 业务代码
- 未引入第三方业务源码
- 未 push
- 未配置 remote
- 未提交真实密钥

## M0-R3B 状态

状态：COMPLETED。

本轮目标：

- 评估 Frappe HR / HRMS 官方信息、v16 分支 / tag 与当前环境的兼容性
- 比较现有容器 / bench 内安装与自定义镜像 / 扩展 Compose 流程两种候选方案
- 给出 M0-R3C 推荐安装方式、边界、风险和回滚建议
- 更新项目状态、当前里程碑和 M0 里程碑台账
- 根据 Codex 审查结论收口 M0-R3B 状态

当前结论：

- 当前环境为 ERPNext `16.26.2`、Frappe `16.25.0`，site 为 `frontend`，Desk 地址为 `http://localhost:8081/login`
- 当前仅安装 `frappe` 和 `erpnext`，未安装 HRMS
- 官方 `frappe/hrms` 存在 `version-16` 分支和 v16 tag；`version-16` 依赖声明要求 Frappe / ERPNext `>=16.0.0,<17.0.0`
- 从主版本范围看，HRMS `version-16` 与当前 Frappe / ERPNext v16 环境方向一致；具体 tag / branch 仍需 M0-R3C 实际安装验证
- 推荐 M0-R3C 在备份和可回滚前提下安装 HRMS，并只验证 HRMS App 和基础 HR 模块可访问
- M0-R3B 已通过 Codex 审查，状态已从 REVIEWING 收口为 COMPLETED

本轮未做：

- 未安装 Frappe HR / HRMS
- 未创建 `hb_core_app`
- 未创建 `hb_attendance_app`
- 未创建 `hb_feishu_app`
- 未安装自定义 Frappe App
- 未开发考勤业务
- 未执行飞书真实写入
- 未开发前端驾驶舱
- 未写 Python/JavaScript/TypeScript 业务代码
- 未修改 `docker-compose.yml`、`.env.example`、`.gitignore`
- 未提交真实密钥
- 未 push

## M0-R3C 状态

状态：COMPLETED。

本轮目标：

- 将 M0-R3B 从 REVIEWING 收口为 COMPLETED
- 备份当前 `frontend` site 并记录安装前环境状态
- 基于官方 `frappe/hrms` 的 `version-16` 分支安装 Frappe HR / HRMS
- 验证 HRMS App 已安装，基础 HR 模块可在 Desk 中访问
- 记录安装命令、日志摘要、版本、验证结果、风险与回滚方式

当前结果：

- 安装前已完成 site 备份，备份位于 Docker volume 内的 `/home/frappe/frappe-bench/sites/frontend/private/backups/`
- HRMS 来源为官方 `frappe/hrms` 仓库 `version-16` 分支，分支 commit 为 `666bf10a9271421abc361bded124d2d961a977e3`
- 已执行 `bench get-app hrms --branch version-16`
- 已执行 `bench --site frontend install-app hrms`
- 已执行 `bench --site frontend migrate`
- 已执行最小必要服务刷新
- 安装后 `bench version` 显示 `hrms 16.12.0 version-16 (666bf10)`
- 安装后 `bench --site frontend list-apps` 显示 `hrms 16.12.0 version-16`
- Desk 登录页 `http://localhost:8081/login` 返回 `HTTP 200`
- 登录后 `/app/hr`、`/app/hr-setup`、`/app/employee`、`/app/leave-application`、`/app/shift-and-attendance` 均可访问并返回 `HTTP 200`
- HR Workspace 已包含 `HR Setup`、`Leaves`、`Shift & Attendance`、`Recruitment` 等入口

已知风险：

- 本轮采用现有容器 / bench 内安装验证，适合 M0-R3C 验证，不代表长期可复现部署方案已经完成。
- 当前 Compose 的 `configurator` 会基于镜像内 `apps` 目录重写 `sites/apps.txt`；后续如要长期保留 HRMS，应治理自定义镜像或 Compose 持久化策略。

本轮未做：

- 未创建 `hb_core_app`
- 未创建 `hb_attendance_app`
- 未创建 `hb_feishu_app`
- 未创建任何海滨自定义 Frappe App
- 未开发考勤业务规则
- 未配置飞书
- 未执行飞书真实写入
- 未开发前端驾驶舱
- 未写 Python/JavaScript/TypeScript 业务代码
- 未修改 Frappe/ERPNext/HRMS 核心源码
- 未修改 `docker-compose.yml`
- 未修改 `.env.example`
- 未提交 `.env`
- 未提交真实密钥
- 未 push

## M0-R3C-FIX 状态

状态：COMPLETED。

本轮目标：

- 复现并诊断 Frappe HR 图标缺失、HRMS 子模块图标缺失和 `/hr/roster` 白屏问题。
- 修复 HRMS 前端资源 404 与 Roster 静态资源不可访问问题。
- 验证 Frappe HR 图标、基础 HR 模块和 Roster 页面可访问。
- 更新项目状态、当前里程碑、M0 里程碑台账和修复记录。

当前结果：

- 复现到 `/assets/hrms/...` JS、CSS、SVG、favicon 资源返回 `404 text/html`，Roster 页面因资源缺失呈现白屏。
- 诊断根因为当前容器内 `sites/assets` 指向容器本地 `/home/frappe/frappe-bench/assets`，而 frontend 容器没有 backend 中 `bench get-app hrms` 得到的 app public 目录，导致 HRMS assets 软链在 frontend 中不可解析。
- 已执行 `bench --site frontend clear-cache`、`clear-website-cache`、`bench build` 和最小必要服务刷新。
- 已用解引用方式将 backend 构建后的真实静态资源同步到 frontend 容器实际 Nginx 资源目录。
- 已将官方 HRMS app 同步到 scheduler、queue 和 websocket 容器，并在 bench venv 中注册，避免后台服务因 `No module named 'hrms'` 重启。
- HTTP 验证显示 Frappe、ERPNext、HRMS 和 Roster 关键静态资源均返回 `HTTP 200`。
- 浏览器验证显示 `/app` Frappe HR 图标不再 broken，`/app/employee`、`/app/employee-checkin`、`/app/attendance`、`/app/shift-type` 均可渲染，`/hr/roster/` 已显示 Roster 月视图。

已知风险：

- 当前修复是运行时容器资源同步和运行时 app 同步，适合 M0-R3C-FIX 诊断修复，不代表长期可复现部署方案已经完成。
- 后续如重建 frontend、scheduler、queue 或 websocket 容器，仍需治理 HRMS 自定义镜像、Compose assets 持久化或部署流程。
- 浏览器控制台仍存在 `socket.io` Invalid origin 相关提示，本轮判断为非 HRMS 资源白屏根因，留待后续环境治理。

本轮未做：

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

## M0-R3D 状态

状态：COMPLETED。

本轮目标：

- 只读盘点 HRMS 原生考勤能力。
- 结合新乡海滨考勤一期需求，设计 M1 最小边界。
- 设计 M1 分轮计划、自定义 App 决策建议、飞书边界和 M1 启动前待确认清单。
- 更新项目状态、当前里程碑和 M0 里程碑台账。
- 创建一次 Git 提交。

当前结果：

- 已确认当前环境为 Frappe `16.25.0`、ERPNext `16.26.2`、HRMS `16.12.0 version-16 (666bf10)`，site 为 `frontend`，Desk `http://localhost:8081/login` 返回 `HTTP 200`。
- 已确认本地核心容器均为 Up，`db` healthy。
- 已确认当前未创建 `hb_core_app`、`hb_attendance_app`、`hb_feishu_app`。
- 已确认当前未录入真实员工、打卡、班次、考勤、请假、假日等业务数据；`Employee`、`Attendance`、`Employee Checkin`、`Shift Type`、`Shift Assignment`、`Shift Schedule`、`Leave Application`、`Holiday List` 均为 0 条。
- 已盘点 HRMS 原生能力：Employee、Attendance、Employee Checkin、Auto Attendance、Shift Type、Shift Assignment、Shift Schedule、Leave Application、Holiday List、Department / Branch / Company、Employee Attendance Tool、Attendance 报表、Biometric / 外部考勤设备集成思路、Payroll 边界。
- 已形成 M1 一期推荐边界：优先用测试数据验证 HRMS 原生对象，覆盖测试员工、早 / 中 / 夜班、Employee Checkin 导入、Auto Attendance、迟到早退、请假联动和最小报表。
- 已明确 M1 初期不建议立即创建 `hb_attendance_app`；只有 HRMS 原生对象无法表达海滨特有规则或验收报表必须定制时，才进入自定义 App 决策。
- 已明确 M1 一期不做飞书真实写入；飞书请假 / 加班同步应另开飞书集成阶段，并需用户明确授权。

本轮未做：

- 未创建 `hb_core_app`
- 未创建 `hb_attendance_app`
- 未创建 `hb_feishu_app`
- 未创建任何自定义 Frappe App
- 未新增 Python / JavaScript / TypeScript 业务代码
- 未修改 Frappe / ERPNext / HRMS 核心源码
- 未录入真实员工数据
- 未配置真实班次
- 未配置真实考勤规则
- 未配置真实请假 / 审批流
- 未接飞书真实写入
- 未做 Vue / React 前端驾驶舱
- 未修改 `docker-compose.yml`
- 未修改 `.env.example`
- 未提交 `.env`
- 未提交真实密钥
- 未配置 remote
- 未 push

## M0-R3E 状态

状态：COMPLETED。

本轮目标：

- 只读确认当前 Frappe / ERPNext / HRMS 容器环境、版本、apps 清单和 Desk 可访问性。
- 识别当前 HRMS 运行态安装带来的可复现性风险。
- 比较运行态文档化恢复、安装脚本 / 运维手册、自定义镜像三种可复现策略。
- 设计 M1 环境保护规则和 HRMS 恢复手册草案。
- 明确本轮不修改 `docker-compose.yml`、`.env.example`、`.gitignore`，不重建容器，不删除 volume，不重新安装 HRMS。

当前结果：

- 当前容器均处于运行状态，`db` healthy。
- Desk 地址 `http://localhost:8081/login` 返回 `HTTP 200 text/html; charset=utf-8`。
- `bench version` 显示 ERPNext `16.26.2`、Frappe `16.25.0`、HRMS `16.12.0 version-16 (666bf10)`。
- `bench --site frontend list-apps` 显示 `frappe`、`erpnext`、`hrms`。
- 已确认 HRMS 仍属于运行态安装成果，仓库当前没有固化包含 HRMS 的自定义镜像。
- 已新增 `docs/deployment/M0-R3E_HRMS环境可复现性收口.md`，记录风险、策略、M1 环境保护规则和恢复手册草案。
- M0-R3E 已通过 Codex 审查，状态已从待审查收口为 COMPLETED。
- 当前推荐 M1-R1 至 M1-R5 期间优先保护当前已跑通环境，不急于重构镜像；如未来多人开发、服务器部署、长期交付或 CI/CD，再单独启动环境可复现阶段。

本轮未做：

- 未执行 `docker compose down -v`
- 未删除 Docker volume
- 未重建 site
- 未重新安装 HRMS
- 未修改 `docker-compose.yml`
- 未修改 `.env.example`
- 未修改 `.gitignore`
- 未创建 `hb_core_app`
- 未创建 `hb_attendance_app`
- 未创建 `hb_feishu_app`
- 未创建任何海滨自定义 Frappe App
- 未新增 Python / JavaScript / TypeScript 业务代码
- 未修改 Frappe / ERPNext / HRMS 核心源码
- 未录入真实员工数据
- 未配置真实班次或真实考勤规则
- 未接飞书真实写入
- 未做 Vue / React 前端驾驶舱
- 未提交 `.env`、备份文件或真实密钥
- 未配置 remote
- 未 push

## M0-FINAL 状态

状态：COMPLETED。

M0 最终边界：

- Docker / Frappe / ERPNext / HRMS 基线已跑通。
- HRMS 已安装并验证。
- HR Workspace 可访问。
- HR 基础 DocType 存在。
- HRMS 环境可复现性风险、保护规则和恢复手册草案已收口。
- 当前仍未创建自定义 App。
- 当前仍未开发考勤业务。
- 当前仍未接飞书。
- M0-FINAL 收口时仍无远端 remote；M0-REMOTE 已在后续轮次完成 GitHub Private remote 创建、`origin` 绑定和 `main` 首次 push。

后续架构原则：

- 不直接修改 Frappe / ERPNext / HRMS 核心源码。
- 优先使用原生配置、角色权限、DocType、报表、导入、API 和低代码定制。
- 自定义 App 只用于海滨特有规则，不用于重写 HRMS 已有功能。
- M1 初期不立即创建 `hb_attendance_app`。
- 飞书真实写入必须用户明确授权。
- 不得执行 `docker compose down -v`，不得删除 volume，不得重建 `frontend` site。
- `.env`、备份文件、密钥、数据库、Docker volume 和运行时数据不得提交。

## M0 后续路线记录

M0-FINAL 收口后的路线已执行到 M1-R5：

1. M0-REMOTE：已完成。
2. M1-R0：已通过 Codex 独立审查，状态 COMPLETED。
3. M1-R1：已通过 Codex 独立审查，状态 COMPLETED。
4. M1-R2：已通过 Codex 独立审查，状态 COMPLETED。
5. M1-R3：BLOCKED，已执行 HRMS 原生考勤最小测试数据试运行并通过 Codex 审查，实际结论为 PARTIAL / BLOCKED。
6. M1-R3A：COMPLETED，运行态阻断诊断与 TEST 数据隔离 / 清理方案，已通过 Codex 审查。
7. M1-R3B：COMPLETED，运行态最小修复方案，已通过 Codex 审查。
8. M1-R3B-FIX：COMPLETED，运行态最小修复已执行并通过 Codex 审查。
9. M1-R3C：COMPLETED，HRMS 原生考勤最小试运行复测，结论为 PARTIAL / GAP_IDENTIFIED。
10. M1-R3D：COMPLETED，HRMS 原生考勤异常口径与配置 Gap 诊断，已通过 Codex 审查。
11. M1-R3E：COMPLETED，配置复核清单与业务口径确认表已通过 Codex 审查。
12. M1-R3F：COMPLETED，业务口径确认包已通过 Codex 审查。
13. M1-REQ-DESIGN-DRAFT：COMPLETED，需求设计四份文档已通过 Codex 审查。
14. M1-R4：COMPLETED，Demo 技术方案与实施路线拆分已通过 Codex 审查并收口。
15. M1-R5：REVIEWING，HRMS 配置基线、考勤工作台与月度汇总 Demo 文档交付已完成，等待审查。
16. M1-R6：PLANNED，待用户授权启动。
17. M1-R7：PLANNED，待用户授权启动。
18. M1-R8：PLANNED（可选缓冲轮）。

## M0-REMOTE 状态

状态：COMPLETED。

本轮目标：

- 创建 GitHub Private 仓库。
- 添加 `origin`。
- 首次 push `main`。
- 确认 `origin/main` 与本地 `main` 一致。
- 记录远端信息和下一步 M1-R0 路线。

当前结果：

- GitHub 仓库：`https://github.com/zjl327707743/HBOS`
- Git remote URL：`https://github.com/zjl327707743/HBOS.git`
- visibility：`PRIVATE`
- 首次 push 的本地 HEAD：`0a29ca526a417d7ec666234f9312dd3de47a687b`
- 首次 push 后本地 `main` 与 `origin/main` 一致。
- M0-REMOTE 本轮仅完成远端创建、绑定、push 和状态记录；当时 M1 尚未启动。当前 M1-R0 已收口为 COMPLETED。

本轮未做：

- 未创建自定义 Frappe App。
- 未创建 `hb_attendance_app`。
- 未开发考勤业务。
- 未开发飞书集成。
- 未实现 SSO。
- 未修改中文化源码。
- 未修改 Frappe / ERPNext / HRMS 核心源码。
- 未执行 `docker compose down -v`。
- 未删除 volume。
- 未重建 `frontend` site。
- 未提交 `.env`、备份、密钥、数据库、日志、缓存或运行时产物。

## M1 状态

状态：IN_PROGRESS。

M1 当前仅进入规划与诊断阶段，不代表进入业务开发。

当前轮次：

- M1-R0：COMPLETED。
- M1-R1：COMPLETED。
- M1-R2：COMPLETED。
- M1-R3：BLOCKED。
- M1-R3A：COMPLETED。
- M1-R3B：COMPLETED。
- M1-R3B-FIX：COMPLETED。
- M1-R3C：COMPLETED。
- M1-R3D：COMPLETED。
- M1-R3E：COMPLETED。
- M1-R3F：COMPLETED。
- M1-R4：COMPLETED。
- M1-R5：REVIEWING。
- M1-R6：PLANNED。
- M1-R7：PLANNED。
- M1-R8：PLANNED（可选缓冲轮）。

M1-R0 当前结果：

- 已新增 `docs/milestones/M1_R0_平台入口账号权限与本地化诊断方案.md`。
- 已通过 Codex 独立审查，并在 M1-R0-CLOSEOUT 中收口为 COMPLETED。
- 已明确 HBOS 账号目标：飞书登录为主，HBOS 内部账号自动映射，Frappe 权限体系承接系统权限和审计。
- 已规划平台入口、账号体系、角色权限、飞书 SSO 可行性和中文化 / 本地化诊断。
- 已明确 M1-R1 前置条件。

M1-R0 未做：

- 未创建自定义 Frappe App。
- 未创建 `hb_attendance_app`。
- 未开发考勤业务。
- 未接真实飞书。
- 未写入飞书。
- 未实现 SSO。
- 未修改 Frappe / ERPNext / HRMS 核心源码。
- 未修改中文翻译源码。
- 未执行 `docker compose down -v`。
- 未删除 volume。
- 未重建 `frontend` site。
- 未提交 `.env`、备份、密钥、数据库、日志、缓存或运行时产物。

M1-R1 当前结果：

- 已新增 `docs/milestones/M1_R1_HRMS原生考勤对象模型验证记录.md`。
- M1-R1 已通过 Codex 独立审查，并在 M1-R1-CLOSEOUT 中从待审查状态收口为 COMPLETED。
- 已通过只读命令确认当前运行态环境：Frappe `16.25.0`、ERPNext `16.26.2`、HRMS `16.12.0 version-16 (666bf10)`，site 为 `frontend`，Desk 登录页 `http://localhost:8081/login` 返回 `HTTP 200`。
- 已通过只读元数据查询确认 User、Employee、Department、Company、Holiday List、Shift Type、Shift Assignment、Employee Checkin、Attendance、Attendance Request、Leave Application、Leave Type 等 DocType 存在。
- 已确认 Shift Type 原生具备自动考勤、IN / OUT 判断、工时计算、迟到早退宽限、打卡时间窗等字段。
- 已确认 Employee Checkin 可承接打卡原始记录，Attendance 可承接日考勤结果，Leave Application / Leave Type 可承接请假对象。
- 已确认 `Shift & Attendance` 等 HR Workspace 入口存在，并确认 `Monthly Attendance Sheet`、`Shift Attendance`、`Employees working on a holiday` 等原生报表存在。
- 已形成需求映射和 Gap List，初步结论为 M1 初期优先复用 HRMS 原生能力，不建议现在创建 `hb_attendance_app`。
- 已建议下一轮为 M1-R2：HRMS 原生考勤配置试运行方案。

M1-R1 未做：

- 未创建自定义 Frappe App。
- 未创建 `hb_attendance_app`。
- 未新增业务 DocType。
- 未开发考勤业务。
- 未接真实考勤机。
- 未接真实飞书。
- 未写入飞书。
- 未实现 SSO。
- 未修改 Frappe / ERPNext / HRMS 核心源码。
- 未修改中文翻译源码。
- 未录入真实员工、真实考勤或真实生产数据。
- 未创建测试员工、测试打卡或测试考勤结果。
- 未执行 `docker compose down -v`。
- 未删除 volume。
- 未重建 `frontend` site。
- 未提交 `.env`、备份、密钥、数据库、日志、缓存或运行时产物。

M1-R2 当前结果：

- 已新增 `docs/milestones/M1_R2_HRMS原生考勤配置试运行方案.md`。
- M1-R2 已通过 Codex 独立审查，并在 M1-R2-CLOSEOUT 中从待审查状态收口为 COMPLETED。
- 已承接 M1-R1 结论：HRMS 原生能力是 M1 初期主路线，当前不建议创建 `hb_attendance_app`。
- 已设计最小测试组织、最小班次、最小打卡场景、HRMS 配置步骤草案、打卡数据导入字段草案、验收用例、成功标准、风险与待确认事项。
- 已明确 M1-R2 只是方案设计，不执行配置试运行，不创建测试数据，不生成可直接导入的 CSV / Excel 测试数据文件。
- 已建议下一轮为 M1-R3：HRMS 原生考勤最小测试数据试运行。

M1-R2 未做：

- 未执行配置试运行。
- 未创建测试 Employee / Shift Type / Employee Checkin / Attendance / Leave Application。
- 未创建可直接导入的 CSV / Excel / JSON 测试数据文件。
- 未创建自定义 Frappe App。
- 未创建 `hb_attendance_app`。
- 未新增业务 DocType。
- 未开发考勤业务。
- 未接真实考勤机。
- 未接真实飞书。
- 未写入飞书。
- 未实现 SSO。
- 未修改 Frappe / ERPNext / HRMS 核心源码。
- 未修改中文翻译源码。
- 未录入真实员工、真实打卡、真实考勤或真实生产数据。
- 未执行 `docker compose down -v`。
- 未删除 volume。
- 未重建 `frontend` site。
- 未提交 `.env`、备份、密钥、数据库、日志、缓存或运行时产物。

M1-R3 当前结果：

- 已新增 `docs/milestones/M1_R3_HRMS原生考勤最小测试数据试运行记录.md`。
- M1-R3 已通过 Codex 审查，审查结果 PASS。
- M1-R3 实际结论为 PARTIAL / BLOCKED，最终状态收口为 BLOCKED，不标记为 COMPLETED。
- 本轮曾创建部分 `TEST-HBOS-M1R3-*` 虚构测试数据。
- 当前只读诊断确认已落库范围包括 2 个 Department、1 个 Holiday List、1 个 Leave Type、8 个 Employee、4 个 Shift Type、6 个 Shift Assignment 和 12 条 Employee Checkin。
- Company 与 User 未创建成功，Attendance 与 Leave Application 为 0。
- 14 个打卡 / 请假 / 加班 / 节假日 / 调班场景未完成 Attendance 闭环验证。
- 当前仍不建议创建 `hb_attendance_app`。

M1-R3A 当前结果：

- 已新增 `docs/milestones/M1_R3A_运行态阻断诊断与TEST数据隔离清理方案.md`。
- M1-R3A 只做运行态阻断诊断和 TEST 数据隔离 / 清理方案，已通过 Codex 审查并收口为 COMPLETED。
- M1-R3A-CLOSEOUT 仅做状态收口，未修复服务、未清理 TEST 数据、未继续创建测试数据。
- 诊断发现 `redis-cache` 与 `redis-queue` 容器已退出，queue worker 和 websocket 反复重启。
- `bench doctor` 因 Redis Queue 连接失败无法完成；`bench --site frontend list-apps` 与 `http://localhost:8081/login` 在本轮检查中长时间无返回。
- MariaDB 可见进程列表未捕获活动阻塞 SQL，但当前账号缺少 `PROCESS` 权限，无法读取 InnoDB 事务与锁等待详情。
- 当前判断阻断更可能来自运行态 Redis / queue / websocket / site 请求路径异常和潜在数据库连接 / 锁状态，而不是 HRMS 原生对象模型已被证明不可用。
- 已形成清理顺序建议：Attendance、Leave Application、Employee Checkin、Shift Assignment、Shift Type、Employee、User、Leave Type、Department、Holiday List、Company。
- 清理和修复均需用户后续明确授权。

M1-R3A 未做：

- 未继续创建测试数据。
- 未继续执行配置试运行。
- 未清理或删除 TEST 数据。
- 未创建自定义 Frappe App。
- 未创建 `hb_attendance_app`。
- 未新增 DocType。
- 未开发考勤业务。
- 未接真实考勤机。
- 未接真实飞书。
- 未写入飞书。
- 未实现 SSO。
- 未修改 Frappe / ERPNext / HRMS 核心源码。
- 未修改中文翻译源码。
- 未提交 `.env`、备份、密钥、数据库、日志、缓存或运行时产物。

M1-R3B 当前结果：

- 已新增 `docs/milestones/M1_R3B_运行态最小修复方案.md`。
- M1-R3B 只制定运行态最小修复方案，已通过 Codex 审查并收口为 COMPLETED。
- 方案承接 M1-R3A 诊断结论：`redis-cache` 与 `redis-queue` 退出，queue worker 和 websocket 反复重启，`bench doctor` 因 Redis Queue 连接失败无法完成，`list-apps` 与 `/login` 存在长时间无返回症状。
- M1-R3B-FIX 已按方案执行运行态最小修复，并已通过 Codex 审查收口为 COMPLETED。
- M1-R3B-FIX 只读计数确认当前 TEST 数据范围包括 Employee 8、Shift Type 4、Shift Assignment 14、Employee Checkin 22、Leave Application 2、Attendance 12 等；该计数高于 M1-R3A / M1-R3B 旧记录，需在 M1-R3C 或清理授权前复核。
- 方案覆盖 Redis、worker、scheduler、`bench doctor`、`list-apps`、login 的最小诊断与修复步骤草案。
- 方案覆盖 Company / User / Employee 创建阻断的复测路径。
- 方案明确本轮不清理 TEST 数据，清理需用户另行授权。
- 方案明确 M1-R3C 进入条件：运行态稳定、TEST 数据隔离边界明确、用户授权重新试运行。
- 当前仍不建议创建 `hb_attendance_app`。

M1-R3B 未做：

- M1-R3B 方案轮本身未执行运行态修复；运行态修复执行已在 M1-R3B-FIX 中记录并收口为 COMPLETED。
- 未清理或删除 TEST 数据。
- 未继续创建测试数据。
- 未执行 HRMS 配置试运行。
- 未创建自定义 Frappe App。
- 未创建 `hb_attendance_app`。
- 未新增 DocType。
- 未开发考勤业务。
- 未接真实考勤机。
- 未接真实飞书。
- 未写入飞书。
- 未实现 SSO。
- 未修改 Frappe / ERPNext / HRMS 核心源码。
- 未提交 `.env`、备份、密钥、数据库、日志、缓存或运行时产物。

M1-R3C 当前结果：

- 已新增 `docs/milestones/M1_R3C_HRMS原生考勤最小试运行复测记录.md`。
- M1-R3C 已在用户明确授权下使用虚构 TEST 数据重新试运行，并已通过 Codex 审查收口为 COMPLETED。
- M1-R3C 结论为 PARTIAL / GAP_IDENTIFIED；这是试运行完成，不是考勤业务闭环完成。
- 本轮使用新前缀 `TEST-HBOS-M1R3C-*` / `test-hbos-m1r3c-*`，未覆盖旧 `TEST-HBOS-M1R3-*` 数据。
- 运行态复核显示 `/login` 返回 HTTP 200，scheduler enabled，`bench doctor` 显示 worker online，Redis / queue / scheduler / frontend / backend / db 容器可用。
- Company / User / Employee 写入阻断已解除：Company 1、User 8、Employee 8 已成功创建。
- M1-R3C 最终虚构数据计数包括 Department 2、Holiday List 1、Shift Type 4、Shift Assignment 14、Employee Checkin 22、Leave Type 1、Attendance 13；Leave Application 因缺少 Leave Allocation 未创建。
- 14 个场景已完成复测记录：8 个通过，6 个为 GAP / PARTIAL。Attendance 可由 HRMS 原生生成；迟到 / 早退未置位是 Gap，缺卡 / 缺勤口径是 Gap，请假因 Leave Allocation 未闭环是 Gap，加班仅体现 `working_hours`，业务口径待定义。
- 当前仍不建议创建 `hb_attendance_app`。
- M1-R3D 已通过 Codex 审查并收口为 COMPLETED；M1-R3E 已通过 Codex 审查并收口为 COMPLETED；M1-R4 未启动。

M1-R3C 未做：

- 未使用真实员工、真实部门、真实考勤机、真实飞书或生产数据。
- 未清理、删除或覆盖旧 TEST 数据。
- 未创建自定义 Frappe App。
- 未创建 `hb_attendance_app`。
- 未新增 DocType。
- 未开发考勤业务代码。
- 未接真实考勤机。
- 未接真实飞书。
- 未写入飞书。
- 未实现 SSO。
- 未修改 Frappe / ERPNext / HRMS 核心源码。
- 未提交 `.env`、备份、密钥、数据库、日志、缓存或运行时产物。

M1-R3D 当前结果：

- 已新增 `docs/milestones/M1_R3D_异常口径与Gap诊断.md`。
- M1-R3D 只做异常口径与 Gap 诊断，并已通过 Codex 审查收口为 COMPLETED。
- M1-R3D-CLOSEOUT 仅做状态收口，未继续试运行，未创建、删除或清理 TEST 数据，未创建 App / DocType / 代码。
- 已承接 M1-R3C 结论：14 个场景中 8 个通过，6 个为 GAP / PARTIAL；Attendance 可由 HRMS 原生生成。
- 已将迟到 `late_entry` 未置位、早退 `early_exit` 未置位归入 HRMS 配置复核优先。
- 已将上班缺卡 / 下班缺卡归入原生报表 / 自定义报表和海滨业务规则定义。
- 已将全天缺勤未生成 Attendance 归入 HRMS 配置复核优先，必要时用报表补足候选识别。
- 已将请假受 Leave Allocation 阻断归入 HRMS 请假配置和海滨请假口径定义。
- 已将加班仅体现 `working_hours` 归入海滨业务规则定义，报表可先识别候选。
- 已补充节假日出勤、临时调班需要待遇、审批、追溯等业务口径。
- 当前仍不建议创建 `hb_attendance_app`。8 个 Gap 均不需要立即创建自定义 App。
- M1-R3E 已通过 Codex 审查并收口为 COMPLETED；M1-R4 未启动。

M1-R3D 未做：

- 未继续试运行。
- 未创建、删除或清理 TEST 数据。
- 未创建自定义 Frappe App。
- 未创建 `hb_attendance_app`。
- 未新增 DocType。
- 未开发考勤业务代码。
- 未接真实考勤机。
- 未接真实飞书。
- 未写入飞书。
- 未实现 SSO。
- 未修改 Frappe / ERPNext / HRMS 核心源码。
- 未提交 `.env`、备份、密钥、数据库、日志、缓存或运行时产物。

M1-R3E 当前结果：

- 已新增 `docs/milestones/M1_R3E_配置复核与业务口径确认表.md`。
- M1-R3E 只做文档交付，不做试运行、不清理 TEST 数据、不开发业务。
- HRMS 配置复核清单覆盖迟到 `late_entry`、早退 `early_exit`、全天缺勤、Leave Allocation、缺卡基础字段、加班候选字段、节假日出勤基础配置和临时调班基础配置。
- 海滨业务口径确认表覆盖迟到、早退、上班缺卡、下班缺卡、全天缺勤、半天请假、全天请假、加班、节假日出勤和临时调班。
- 已记录缺卡异常候选表、缺勤候选表、加班候选表和调班追溯表为 M1-R4 报表候选；本轮未实现报表。
- 已明确 Attendance 生成不等同于海滨考勤业务闭环完成。
- 当前仍不建议创建 `hb_attendance_app`。
- M1-R3E 已通过 Codex 审查并收口为 COMPLETED；M1-R4 未启动。

M1-R3E 未做：

- 未继续试运行。
- 未创建、删除或清理 TEST 数据。
- 未创建自定义 Frappe App。
- 未创建 `hb_attendance_app`。
- 未新增 DocType。
- 未开发考勤业务代码。
- 未接真实考勤机。
- 未接真实飞书。
- 未写入飞书。
- 未实现 SSO。
- 未修改 Frappe / ERPNext / HRMS 核心源码。
- 未提交 `.env`、备份、密钥、数据库、日志、缓存或运行时产物。
