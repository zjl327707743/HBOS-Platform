# Project Status

项目名称：新乡海滨智能运营管理平台。

## 当前状态

- 当前阶段：M2-LIMS 实验室信息管理系统板块（IN_PROGRESS）；M1-FIX 功能补漏为并行未决事项（IN_PROGRESS，B3/B4/B5 未 closeout）
- 当前轮次：M2-R7（留样管理板块开发方案，REVIEWING rev2，首轮审查 FAIL 8 项已修订，待复审）；M2-R6（Vue 前端原型与开发流程，REVIEWING，等待 Owner 审查）；M2-R5（验证收口）并行 REVIEWING，M2-LIMS MVP 全量交付完成。留样板块已按 Owner 授权纳入 R7 范围，R7A~D 子轮须方案审查通过后逐轮启动
- M2-R6A（样品登记动态表单设计，REVIEWING）：样品类型 / 检验优先级下拉决策条 + 9 类整表单切换，方案与交互原型已交付
- M2-R6B（检验结果台账双模式设计，REVIEWING / Owner 已确认原型与交互）：明细台账（受控记录）+ 样品表（每样品种类一张表、一行一个批次），后端 `HBOS Ledger Template` + `get_result_ledger` 落地设计已交付
- M2-R6C（检验结果台账 Vue 复刻与生产部署，DEPLOYED）：双模式已复刻进 Vue 并上线生产，Owner 已确认测试路径
- M2-R6D（合规审计日志 + 生产部署错配修复，DEPLOYED）：合规审计日志 DocType/全量捕获/前端页已上线生产，Owner 已确认测试路径；并修复生产部署旧 chunk 残留致部分页面进不去
- M2-R7（留样管理板块开发方案，REVIEWING rev2）：首轮审查 FAIL（8 项发现）已全部修订，待复审。rev2 定案：5 主 DocType + 1 子表（Retention Product / Retention Sample + Stock Log 通用库存流水 / Observation / Usage Apply / Disposal Apply）+ 标签 Print Format + 4 报表；数量字段 Float + UOM；reserved_qty 预占 + FOR UPDATE 原子扣减；观察计划字段挂留样主表；业务键单字段 unique；角色动作矩阵 + SoD 硬校验；状态机补驳回/转出/qm_approved_at；Sample→留样映射规则成节；R7A~C 验收含负向用例；Owner 已授权留样板块纳入 `hb_lims_app` 范围，R7A~D 须方案审查通过后启动；未创建 DocType、未写业务代码。方案文档 `docs/milestones/M2_R7_留样管理板块开发方案.md`
- 当前仓库定位：工程启动文档、AI 上下文、里程碑状态、计划、ADR、环境设计文档、最小 Docker 配置、M1-FIX 轻量自定义 App（hb_attendance_app）与 M2-LIMS 自定义 App（hb_lims_app）
- 当前实现状态：M1-FIX-B2 已 COMPLETED；M1-FIX-B3 为 REVIEWING / Owner UI 验收未通过；M1-FIX-B4 为 REVIEWING / Claude PASS，但 Owner 数据链路验收发现后续问题；M1-FIX-B5 为 REVIEWING；M1-FIX-C/D/E 未启动。M2-LIMS MVP 全量交付：M2-R1 骨架、M2-R2 主数据与判定引擎、M2-R3 检验流程闭环、M2-R4 COA 与报表、M2-R5 验证收口（全量演练 19/19 + 11 项验收 + 离线测试 109/109 + Workspace 全链接入口），M2-R5 为 REVIEWING 等待审查。
- M2-R6 Vue 前端原型与开发流程已交付（交互式 HTML 原型 + 开发流程文档），REVIEWING 等待 Owner 审查；未创建 Vue 工程、未接真实 API。
- 当前远端：`origin` -> `https://github.com/zjl327707743/HBOS.git`，GitHub visibility = `PRIVATE`
- 下一步路线：M2-R7 方案 rev2 复审，通过后按子轮启动 M2-R7A（主数据与留样登记）；M2-R6 原型 Owner 审查通过后进入 Vue 工程初始化与页面复刻；M2-R5 审查 closeout；M2-LIMS 其余扩展模块（仪器集成、稳定性、环测、微生物、试剂、OOS 调查等）另行规划，留样板块（M2-R7）已授权；M1-FIX-C（异常三级流程）为 PLANNED / 待 Owner 授权，不自动启动。

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
- M1-R5 已通过 Codex 审查并收口为 COMPLETED。Codex 审查 PASS。本轮已完成 HRMS 配置基线整理（14 类对象）、考勤工作台入口方案设计（方案 A/B）、月度汇总 Demo 展示路径设计（14 字段映射与覆盖分析）、Excel 导出路径说明（4 种导出方式）、R5 风险与后续 Gate 评估（9 项技术评估）。本轮未创建 App、未创建 DocType、未修改核心源码、未动数据库。主文档 `docs/milestones/M1_R5_HRMS配置基线工作台月报Demo.md` 已交付。

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
15. M1-R5：COMPLETED，HRMS 配置基线、考勤工作台与月度汇总 Demo 已通过 Codex 审查并收口。主文档 `docs/milestones/M1_R5_HRMS配置基线工作台月报Demo.md` 已交付。
16. M1-R6A：COMPLETED，Excel 导入与异常流程落地方案 / Gate 判定，主文档 `docs/milestones/M1_R6A_Excel导入与异常流程落地方案.md` 已交付，Codex 审查 PASS。
17. M1-R6B：COMPLETED，脱敏打卡流水导入最小验证，主文档 `docs/milestones/M1_R6B_脱敏打卡流水导入最小实现.md` 已交付并完成 closeout。
18. M1-R6C：COMPLETED，异常识别与异常说明流程最小实现已通过 Codex 审查并 closeout。
19. M1-R7：COMPLETED，飞书登录、领导 Demo 与 M1 收口准备，已通过 Codex 审查并 closeout。
20. M1-R8：PLANNED（可选缓冲轮，因 M1 closeout 完成可能跳过）。
21. M1 总收口：历史 closeout 已完成；Owner UI 验收发现功能缺口后，当前 M1 产品交付仍在 M1-FIX 中，尚未完成。
22. M1-FIX-A：REVIEWING，功能补漏差距盘点与实施方案已交付。
23. M1-FIX-B：REVIEWING，Excel 导入与真实本地数据闭环已实现。
24. M1-FIX-B2：COMPLETED，导入口径、安全与准确性修复已通过 Claude 审查并 closeout。
25. M1-FIX-B3：REVIEWING / Owner UI 验收未通过，考勤工作台入口、App 命名与 HRMS 数据一致性修复不能 closeout。
26. M1-FIX-B4：REVIEWING / Claude PASS，但 Owner 数据链路验收发现后续问题；B4 不 closeout。
27. M1-FIX-B5：REVIEWING，导入数据链路核查与报表口径收敛已交付，等待 Owner 和 Claude 审查。
28. M2-LIMS：IN_PROGRESS（实验室信息管理系统板块，Owner 已授权）。M2-R1 环境与骨架 COMPLETED；M2-R2 主数据与判定引擎 COMPLETED；M2-R3 检验流程闭环 COMPLETED；M2-R4 COA 与报表 COMPLETED；M2-R5 验证收口 REVIEWING（待审查 closeout）。

29. M2-R6：REVIEWING，Vue 前端原型与开发流程已交付（交互式 HTML 原型 + 开发流程文档），等待 Owner 审查；未创建 Vue 工程、未接真实 API。
30. M2-R6A：REVIEWING，样品登记动态表单设计已交付（`docs/frontend/M2_R6A_样品登记动态表单设计.md` + 原型 `#sample` 动态表单交互），样品类型 / 检验优先级为下拉决策条，9 类样品类型各对应一张完整表单，等待 Owner 审查。
31. M2-R6B：REVIEWING，检验结果台账双模式设计已交付（`docs/frontend/M2_R6B_检验结果台账设计方案.md` + 原型 `#ledger` 双模式交互）。Owner 已确认原型与交互：明细台账（受控记录视角，样品卡片 + 检验项目逐行 + 下钻抽屉签名/修订/审计）+ 样品表（每样品种类一张表、一行一个批次、首列序号、次列样品批号，左侧按类型分组可收缩下拉列表，数据区含判定/记录状态列，侧边栏与固定标签不含）；视觉规范已确认（表头 12px/600 统一、判定/状态徽章 12px）。后端落地设计为 `HBOS Ledger Template` DocType + `get_result_ledger` 聚合 API（只读投影，限度/结果/判定受控可溯源），待实现轮另行规划。
32. M2-R6C：DEPLOYED，检验结果台账双模式 Vue 复刻与生产部署完成。`ResultLedgerView.vue` 复刻双模式（明细台账 + 样品表），数据来自真实 Frappe API（HBOS Sample / Test Result / COA / Result Revision 聚合，只读投影，superseded 链过滤，修订/审计摘要）；新增判定列 + 记录状态列筛选、记录状态语义配色（放行/批准绿、检验完成/检验中蓝、登记/草稿灰、拒绝/OOS 红）；`vue-tsc` 0 错误；生产构建 `npm run build:prod` 同步至容器 `hbos-m0-r3a-frontend-1`（备份 `hbos-lims.bak-20260827a`），生产 URL `http://localhost:8080/hbos-lims/` HTTP 200 验证通过，Owner 已确认测试路径效果。后端同步：`lims_service.py` 新增 `get_result_ledger` 聚合查询 whitelist（只读投影，返回 samples / results / revisions / coas / groups / meta，服务端派生 limits_text/display/report_date，对齐前端 ResultLedgerView），`workflow_contract.py` ACTION_ROLES 注册 `get_result_ledger`（LIMS Analyst/Reviewer/Manager + System 可读）；离线契约测试 114/114 全绿（新增 6 项台账契约）；真实环境跑通（全量 7 样品/17 结果/2 修订/3 COA 日期/分组 + sample_type=成品 3 样品 + material=测试01 2 样品筛选均验证）；backend gunicorn 已重启加载新代码。
33. M2-R6D：DEPLOYED，合规审计日志已上线生产，Owner 已确认测试路径。后端新增 `HBOS Audit Log` DocType（write-once：log_type/doctype_target/doc_name/action_text/field_changed/old_value/new_value/reason/user/created_at/checksum，仅 Reviewer/Manager/System 可读、无常规 create/edit/delete）；`hooks.py` doc_events 全量捕获创建/修改/删除；`lims_service.py` 新增 `audit_log`（sha1 防篡改）与 `get_audit_log` 查询 whitelist 及业务埋点（提交/复核/批准/修订/放行/拒绝/OOS/仪器使用/规格生效-废止）；`workflow_contract.py` 注册 `get_audit_log`；离线契约 123/123 全绿（新增 9 项）；真实环境跑通。前端合规组新增 合规审计日志 入口 + `/audit-log` + `AuditLogView.vue` + `getAuditLog`。生产部署修复：Owner 反馈「海滨LIMS 已可进入但样品登记异常/审计追踪等个别页面进不去」，根因生产 `index.html` 引用旧 bundle 与 assets 混 129 个历史旧 chunk（新旧哈希错配致 view 懒加载 404/崩溃）；root 清旧 assets 后重新部署最新干净 dist（39 资产与本地逐字节一致，全引用 200+正确 MIME）；注入 nginx SPA fallback 修 `/hbos-lims` history 404（`frappe.conf.bak-20260903-spa`）。

## M2-LIMS 状态

状态：IN_PROGRESS。

M2-LIMS 是实验室信息管理系统板块（HB LIMS），以《海滨药业LIMS系统开发方案》为业务口径（12 模块），参考开源 SENAITE LIMS 功能结构（仅业务模型参考，不搬代码），自定义 Frappe App `hb_lims_app` 承载，技术承载为 HBOS 既有 Frappe 底座。

M2-R1（环境与骨架）：COMPLETED。本轮目标为建立 M2-LIMS 启动门禁与总方案文档、将 `hb_lims_app` 挂载进 Docker Compose 环境（8 处 service + 6 处 PYTHONPATH）、创建 App 完整骨架（hooks / config / public logo / after_migrate 幂等同步）、安装到 `frontend` site 并验证入口对象与静态资源可达、搭建离线测试脚手架并跑通。执行结果：

- 已新建分支 `m2-lims`（自 `m1-fix-frontend-zh` 切出），M2-LIMS 全部工作在该分支进行。
- `docker compose config --quiet` 通过；`docker compose up -d` 重建容器成功（未执行 down -v，未删 volume）。
- `bench --site frontend install-app hb_lims_app` 成功；`migrate` 触发 after_migrate 成功；`list-apps` 显示 `hb_lims_app 0.0.1`。
- 3 个 LIMS 角色（LIMS Manager / LIMS Analyst / LIMS Reviewer）已创建；Workspace `海滨LIMS工作台`（4 卡片分区 + 4 角色）、Desktop Icon `海滨LIMS`、2 条 Workspace Sidebar 均已创建。
- `bench build --app hb_lims_app` 成功；frontend 容器 assets 软链接已补建（含恢复 hb_attendance_app 回归缺失）；`http://localhost:8080/login`（Host: frontend）200，LIMS / 考勤 logo 均 200。
- 离线契约测试 8/8 全绿（`python3 -m unittest discover -s apps/hb_lims_app/tests`）。
- 排障记录：业务包名由 `hb_lims` 重命名为 `hbos_lims`（对齐 Frappe 模块名 "HBOS LIMS" 的包名约定）；Desktop Icon `bg_color` 由 `green` 改为 `blue`（v16 仅允许 gray/blue）；端口口径为 `HTTP_PORT=8080`（8081 为本机 SENAITE 演示容器，勿混淆）。
- 主文档 `docs/milestones/M2_R1_环境与骨架.md`、门禁 `docs/milestones/M2_START_GATE.md`、总方案 `docs/milestones/M2_LIMS_总方案与轮次拆分.md` 已交付。

M2-LIMS 本轮未做：未创建 DocType；未创建业务方法（判定引擎 / 状态机 / lims_service）；未修改 Frappe / ERPNext / HRMS 核心源码；未录入任何样品 / 人员 / 检测数据；未提交 `.env`、密钥、Excel / CSV、数据库或运行时产物。

M2-R2（主数据与判定引擎）：COMPLETED。本轮交付 6 个主数据 DocType（HBOS Sample Type / HBOS Lab Department / HBOS Test Item / HBOS Calculation / HBOS Specification + Item 子表）、`result_contract.py` 判定引擎（judge_result / round_significant / apply_formula / verdict_to_label）、规格生效校验（同码同版本去重、限度一致性、is_spec_active / get_active_specifications）。离线测试 40/40 全绿。已同步到 frontend site，并用 `TEST-HBOS-M2-*` 虚构主数据验证：3 样品类型、3 检验组、3 检验项目、1 公式、规格 V1.0 已生效 + V2.0 草稿（同码多版本）、重复版本拒绝、区间缺上限拒绝、生效查询仅返回 V1.0。设计修正：规格 autoname 由 `field:spec_code` 改为 `format:{spec_code}-V{version}`（支持同规格多版本）。主文档 `docs/milestones/M2_R2_主数据与判定引擎.md` 已交付。

M2-R3（检验流程闭环）：COMPLETED。本轮交付 5 个事务 DocType（HBOS Sample + Item 子表 / Sample Task / Test Result / Result Revision）、`workflow_contract.py` 状态机（Sample/Task/Result 全状态转移表 + 角色矩阵）、`lims_service.py` 业务方法全链（register → generate_tasks → assign → start[自动创建检测记录] → submit[自动判定 + OOS 触发] → review → approve → revise[Revision + superseded 链] → release/reject）、待检任务看板 Script Report。离线测试 73/73 全绿。虚构数据闭环验证 29/29 通过（合格闭环 12 项 / OOS 6 项 / 修订 6 项 / 权限 3 项 / 报表 2 项）。排障并固化：子表 `istable: 1` 与 parent 列、Result 提交锁定基于提交前状态、任务 OOS 路径补全、PYTHONPATH 完整值、get_roles list 适配、修订自转移防护。主文档 `docs/milestones/M2_R3_检验流程闭环.md` 已交付。

M2-R4（COA 与报表）：COMPLETED。本轮交付 HBOS COA(+Item 子表) DocType、Print Format `HBOS COA`（中文 Jinja 模板 + 签名栏）、lims_service 扩展（create_coa / review_coa / publish_coa，PDF 附件归档 + 快照保护）、4 个 Script Report（检验结果清单 / 样品台账 / 审计追踪查询 / COA 发布记录）。HBOS LIMS 模块 13 个 DocType 全部就位。离线测试 89/89 全绿；COA 发布链路虚构数据验证 19/19 通过（创建/快照/重复拒绝/QA 审核/PDF 生成 17.8KB/发布人时间/快照锁定/4 报表）。排障并固化：publish 改为直接渲染 fixture 模板（绕开 frappe.get_print 的 website 管线，规避 hrms Job Opening 环境缺失）、记录型结果优先 result_text、fetch 字段防篡改还原语义、带空格报表名用 importlib 导入。主文档 `docs/milestones/M2_R4_COA与报表.md` 已交付。

M2-R5（验证收口）：REVIEWING。本轮交付 Workspace 四卡片 13 链接 + 5 快捷入口 + Sidebar 5 主项（after_migrate 幂等同步验证）、test_full_doctype_contract 全量契约测试（13 DocType 中文 label 全覆盖）、全量演练 19/19 通过（登记→任务→检验→判定→复核→批准→修订→COA→发布→放行 + 5 报表 + 数据盘点）、11 项验收全部通过、离线测试 100/100 全绿。排障并固化：状态机补「已批准→已提交」修订回退、submit_result 任务联动自转移防护。审查期间增强：①控制面板全面简体中文（Series 标签→编号系列 + translations/zh.csv 13 DocType 名中文化，契约测试强制中文 label 与翻译覆盖）；②侧边导航按业务模块下拉分组（原生 Section Break + collapsible + child，5 分组 17 子项，与工作台四卡片对应）；③定位并 workaround Frappe v16.26.3 核心 bug（`get_can_read_items` 缺 return 致非管理员侧边栏 DocType 项全被过滤，hb_lims_app 注册 boot_session hook 预置 `user_perm_can_read` 缓存，不改核心源码）；④报表表格列宽拖拽修复（datatable resize-handle 默认 opacity:0 无 hover 规则致手柄不可见，CSS hover 表头显示手柄 + 加宽命中区恢复原生拖拽与双击自适应，JS 注入单元格 hover 全文 title 提示）；⑤列表视图列宽拖拽（用户反馈 DocType 列表页无法拖宽列；v16 apply_column_widths 仅按内容自动算宽无拖拽交互，lims_list_resize.js monkey-patch 注入表头手柄 + localStorage 持久化 + 双击复位，限定 HBOS LIMS 模块；修复 patch 时机晚于首次渲染竞态，补扫已存在 LIMS 列表实例）；⑥表单子表网格列宽拖拽（用户反馈新建样品登记等表单子表无法拖宽列；Frappe v16 子表列宽由 Bootstrap col-xs-N 栅格类固定无拖拽，lims_grid_resize.js monkey-patch ControlTable.prototype.make + MutationObserver 兜底，wrap grid 实例 refresh 恢复持久化列宽并注入表头手柄 + localStorage 持久化 + 双击复位，限定 HBOS LIMS 模块）；⑦样品登记默认报表视图（用户需求：新建样品登记默认为报表视图；HBOS Sample DocType 设 default_view=Report，打开 /app/hbos-sample 自动进入报表视图，datatable 原生列宽拖拽，不设 force_re_route 故仍可切回列表视图，其他 LIMS DocType 不受影响）；⑧表格字段文字居中（用户需求：所有表格字段文字剧中；CSS 对 HBOS LIMS 标记容器 .hbos-lims-list / .hbos-lims-grid / .hbos-lims-report 内的报表 datatable、列表视图、子表网格单元格 text-align:center，JS 在 LIMS 列表/子表/Query Report 容器注入标记类，非 LIMS 页面不受影响）；⑨列表视图表头/数据错位修复（用户反馈结果修订记录页错位；文字居中断言下 Subject 列表头 checkbox 绝对定位+标题文字居中、数据行 checkbox+链接靠左，上下不对称；CSS 对数据行 Subject 列施加同表头规则——checkbox 置最左 + 文字居中，全 LIMS 列表页对齐）。离线测试 109/109 全绿。主文档 `docs/milestones/M2_R5_验证收口.md` 已交付，等待 Owner 和 Claude 审查后 closeout。

M2-R6（Vue 前端原型与开发流程）：REVIEWING。本轮结合《海滨药业LIMS系统开发方案》与 `hb_lims_app` 实际闭环，交付交互式 HTML 原型 `docs/frontend/M2_LIMS_Vue前端原型.html`（工作台总览 / 样品登记 / 待检任务看板 / 结果录入 / COA 报告 / 质量标准库 / 审计追踪查询，共 7 个视图，演示数据 `TEST-HBOS-M2-*`）与开发流程文档 `docs/frontend/M2_LIMS_Vue前端开发流程.md`（强制 Gate、Vue 3 + Vite + TypeScript + Pinia + Vue Router + Element Plus + ECharts 技术选型、页面信息架构、视觉方案、组件拆分、`lims_service.py` whitelist 方法映射）。桌面与移动端渲染验证通过；`frontend-design` skill 当前环境不可用，按项目规则等价人工设计。本轮只到原型 / 视觉方案阶段，未创建 Vue 工程、未接真实 API。主文档 `docs/milestones/M2_R6_Vue前端原型与开发流程.md` 已交付，等待 Owner 审查。
M2-R6A（样品登记动态表单设计）：REVIEWING。基于 `/hbos-lims/samples` 实际需求，交付方案文档 `docs/frontend/M2_R6A_样品登记动态表单设计.md` 并在交互式原型新增 `#sample` 动态表单页：样品类型与检验优先级固定为顶部下拉决策条（sticky），每个样品类型各对应一张完整表单，不拆分通用 / 专属信息区；切换下拉即整表单替换（成品 / 原料 / 中间体 / 包装材料 / 工艺用水 / 水 / 环境样品 / 稳定性样品 / 清洁验证样品，共 9 类），含字段映射、必填与联动规则、视觉与响应式策略、可直接复用中文设计提示词。桌面 / 移动端截图验证通过；本轮仍为原型 / 方案 REVIEWING，未创建 Vue 工程、未接真实 API。

M2-R6B（检验结果台账双模式设计）：REVIEWING / Owner 已确认原型与交互。针对"每种样品登记信息类型不同、检验项目不同"与 GMP 数据完整性（检验项目、限度、结果、判定均为受控记录、可审计追踪）需求，交付双模式方案 `docs/frontend/M2_R6B_检验结果台账设计方案.md` 并在交互式原型新增 `#ledger` 页：①明细台账（受控记录视角）——左侧样品列表（类型筛选 + 搜索 + 汇总判定角标），右侧样品卡片（登记信息按类型渲染 + 检验项目逐行展示 限度快照/结果/判定/检验人/状态），下钻抽屉含标准限度快照、三级电子签名、修订记录、审计摘要，OOS 完整链路展示；②样品表（每样品种类一张表）——左侧按类型分组可收缩下拉列表（每个样品种类一个条目，显示 N 批检验记录，不含判定），右侧每个样品种类单独一张表：首列序号、次列样品批号、登记信息字段、检验项目字段、判定、记录状态，一行一个批次按检测顺序填入。视觉规范已确认（表头 12px/600 统一、判定/状态徽章 12px、侧边栏与表头固定标签不含判定/状态）。桌面 / 移动端渲染验证通过、浏览器自动验证（侧边栏无判定徽章、表头纯净、字号统一、控制台无错误）。后端落地设计为 `HBOS Ledger Template` DocType + `get_result_ledger` 聚合 API（只读投影，模板缺失自动回退推导），待实现轮另行规划；本轮未创建 Vue 工程、未接真实 API。

M2-R6C（检验结果台账 Vue 复刻与生产部署）：DEPLOYED。将 R6B 双模式复刻进 Vue 工程 `frontend/hbos-lims-web/src/views/ResultLedgerView.vue`：①明细台账——左侧样品列表（类型筛选 + 搜索 + 汇总判定角标）、右侧样品卡片（登记信息 + 检验项目逐行 限度/结果/判定/检验人/记录状态）、下钻抽屉（标准限度快照 / 三级电子签名 / 修订记录 / 审计摘要，OOS 完整链路）；②样品表——左侧按类型分组可收缩列表（每个样品种类一个条目、不含判定），右侧每样品种类一张表（首列序号、次列样品批号、登记字段、项目列、判定、记录状态，一行一个批次）。数据来自真实 Frappe API：HBOS Sample / HBOS Test Result / HBOS COA / HBOS Result Revision 前端聚合，只读投影、superseded 链过滤、修订/审计摘要。增强：判定列 + 记录状态列筛选（下拉动态取当前表数据、可叠加、切换样品种类自动重置）、记录状态语义配色（放行/批准绿、检验完成/检验中蓝、登记/草稿灰、拒绝/OOS 红）。`vue-tsc` 类型检查 0 错误；生产构建 `npm run build:prod` 后经 `docker cp` 同步至容器 `hbos-m0-r3a-frontend-1` 生产路径 `/home/frappe/frappe-bench/sites/frontend/public/hbos-lims/`（部署前备份 `hbos-lims.bak-20260827a` 可回滚），生产 URL `http://localhost:8080/hbos-lims/` HTTP 200、静态资源全部 200 验证通过。Owner 已确认测试路径效果。后端同步：`lims_service.py` 新增 `get_result_ledger` 聚合查询 whitelist（只读投影，返回 samples / results / revisions / coas / groups / meta 六段，服务端派生 limits_text / display / report_date，支持 sample_type / material 筛选，对齐前端 ResultLedgerView 双模式数据需求，避免前端多路 get_list 拼接）；`workflow_contract.py` ACTION_ROLES 注册 `get_result_ledger`（LIMS Analyst / Reviewer / Manager + System Manager 可读）；离线契约测试 114/114 全绿（新增 TestLedgerContract 6 项：whitelist、角色注册、字段契约、派生字段、_ledger_groups）；真实环境跑通——全量返回 7 样品 / 17 结果 / 2 修订 / 3 个 COA 报告日期 / 类型分组（原材料→阿司匹林原料药 3 批等、成品→测试01 2 批等），`sample_type=成品` 3 样品、`material=测试01` 2 样品筛选均验证通过；backend 容器 gunicorn 已重启加载新代码（期间误杀主进程致容器退出，已 `docker start` 恢复，容器健康、生产前端 / 登录页 200）。

M2-R6D（合规审计日志 + 生产部署错配修复）：DEPLOYED。①合规审计日志：新增 `HBOS Audit Log` DocType（write-once，log_type/doctype_target/doc_name/action_text/field_changed/old_value/new_value/reason/user/created_at/checksum，仅 Reviewer/Manager/System 可读、无常规 create/edit/delete，写入仅系统钩子内部 insert）。`hooks.py` doc_events 全量捕获创建/修改/删除（HBOS Sample/Sample Task/Test Result/COA/Specification/Sample Type/Test Item）。`lims_service.py` 新增 `audit_log` 写核心（sha1 指纹防篡改）与 `get_audit_log` 查询 whitelist（类型/对象/操作人/关键字/时间筛选）及各业务方法埋点（提交含自动判定/复核/批准/修订/放行/拒绝/OOS/仪器使用/规格生效-废止）。`workflow_contract.py` 注册 `get_audit_log`；离线契约 123/123 全绿（新增 TestAuditLogContract 9 项）；真实环境跑通（建表、事件流、register_sample 自动触发创建）。前端合规组新增 合规审计日志 入口 + `/audit-log` 路由 + `AuditLogView.vue`（类型/对象/操作人/时间/前后值/原因/指纹 + 下钻含数据完整性）+ getAuditLog；生产构建 + docker cp 部署。②生产部署错配修复：Owner 反馈「海滨LIMS 已可进入但样品登记异常/审计追踪等个别页面进不去」，根因生产 index.html 引用旧 bundle 且 assets 混 129 个历史旧 chunk（新旧哈希错配致 view 懒加载 404/崩溃）；root 清旧 assets 后以干净 dist（39 资产与本地逐字节一致）重新部署，全引用 200+正确 MIME；注入 nginx SPA fallback 修 `/hbos-lims` history 404（备份 frappe.conf.bak-20260903-spa）。

M2-R7（留样管理板块开发方案）：REVIEWING rev2，首轮审查 FAIL（8 项发现：授权口径自相矛盾、数量字段不足、库存并发缺失、观察计划模型不完整、复合唯一不可落地、角色矩阵不足、状态机缺口、Sample 映射不足）已全部修订，待复审；未创建 DocType、未写业务代码。以 Owner 2026-09-04 提供的《留样管理规程》JXH-SOP-LC-1-00-007-09 全套文件（1 正文 + 4 记录 + 2 附件）为第一业务依据；两份桌面方案（《LIMS留样管理模块开发方案.md》《留样板块LIMS开发方案.md》）评审结论为业务采纳、技术路线修正（SQL 建表→Frappe DocType、自研/Activiti 工作流→workflow_contract 状态机、Node/PostgreSQL→既有 Frappe/MariaDB 底座、独立 12 周里程碑→R7A~D 四子轮）、条号修正（211.166→211.170，211.166 为稳定性考察）、补 0 月基线观察。方案定案：5 主 DocType + 1 子表（HBOS Retention Product 留样产品主数据（附件二电子化）/ HBOS Retention Sample 留样登记 + Usage Log 使用流水子表（记录一）/ HBOS Retention Observation 观察记录（记录二，unique(retention_sample, obs_period) 防重复）/ HBOS Retention Usage Apply 使用申请（记录三，四级审批链：资源管理员库存确认→QC 负责人→QA 负责人→质量管理负责人）/ HBOS Retention Disposal Apply 处理申请（记录四，五级审批链含销毁 3 个月时限与 QA 现场监督双签））；标签为 Print Format「HBOS 留样标签」；4 个 Script Report（留样台账 / 观察计划看板 / 季度到期处理清单 / 销毁超期清单）；三条状态机进 workflow_contract；审计与电子签名全部复用 M2-R6D 机制（doc_events 注册 + audit_log 埋点 + _signature 签名含义扩展）；与 HBOS Sample 检验闭环打通（检验完成批次一键创建留样，GMP 留样代表性），稳定性样品硬隔离；Vue 前端走原型先行流程（R7D）。发现规程疑点 3 项（正文 4.4.1 销毁签批 4 级 vs 记录四表单 5 签署位、08 版变更历史记录编号错位一格、标签尺寸 OCR 疑为 70.0×55.0mm 小数点丢失）与待 Owner 确认 7 项（角色方案 A 三角色映射 / B 新增 LIMS QA 分离（推荐）、标签尺寸原件确认、观察批手动/自动选取、历史在库数据是否迁移、法规条号核对、销毁签批层级定稿、到期提醒提前量）。子轮拆分：M2-R7A 主数据与留样登记 → R7B 观察管理 → R7C 使用与处理审批 → R7D Vue 原型与复刻。主文档 `docs/milestones/M2_R7_留样管理板块开发方案.md`。本轮未创建 DocType、未写业务代码、未动数据库、未建 Vue 工程、未录真实留样数据。

## M1-FIX 状态

状态：IN_PROGRESS。

M1 已 closeout 为 COMPLETED，但 Owner 亲自验收后发现「方案完成」不等于「功能完成」——大量产品功能没有真正页面可体验。M1-FIX 阶段定位为功能补漏，补齐 M1 承诺但未实际可体验的产品功能。

M1-FIX-A：REVIEWING。本轮为差距盘点与补漏实施方案，主文档 `docs/milestones/M1_FIX_功能补漏实施方案.md` 已交付。识别 20 项差距、给出自定义 App/DocType 初步判断、拆分 M1-FIX-B/C/D/E 推荐顺序。

M1-FIX-B：REVIEWING。本轮已创建轻量 `hb_attendance_app`、导入日志和 `海滨考勤工作台`，支持 Owner 本地真实 Excel 识别、员工匹配 / 创建、打卡流水适配生成、HRMS 自动考勤尝试、本地兜底生成标记和导入日志统计。主文档 `docs/milestones/M1_FIX_B_Excel导入与真实数据闭环.md` 已交付。

M1-FIX-B-FIX：REVIEWING。本轮补齐 `导入考勤机导出表` 浏览器入口、中文 `打卡流水` / `考勤结果` 报表、重复导入可读说明、兜底生成说明和默认白班/行政班 08:30-17:30。主文档 `docs/milestones/M1_FIX_B_FIX_Excel导入与中文体验修复.md` 已交付。

M1-FIX-B2：COMPLETED。导入口径、安全与准确性修复已通过 Claude 审查并 closeout。

M1-FIX-B3：REVIEWING / Owner UI 验收未通过。本轮不 closeout B3，Owner 真实浏览器发现桌面 icon、左侧导航、导入页归属和 HBOS / HRMS 入口口径仍混乱。

M1-FIX-B4：REVIEWING / Claude PASS，但 Owner 数据链路验收发现后续问题。本轮按 Owner 确认的方案 A 收敛运行态入口：`after_migrate` 幂等同步 Workspace、Workspace Sidebar、Desktop Icon；桌面入口显示为 `海滨考勤` 并使用实际可见 SVG；导入页增加 `海滨考勤工作台 / 导入考勤机导出表` 说明和返回入口；HBOS 报表与 HRMS 原生入口显示口径已区分。主文档 `docs/milestones/M1_FIX_B4_考勤模块架构收敛与单一入口重整.md` 已交付，B4 本轮不 closeout。

M1-FIX-B5：REVIEWING。本轮核查真实数据库中 Employee / Employee Checkin / Attendance / HBOS Attendance Import Log / 月度汇总暂存链路；确认 HRMS 原生月度考勤表空表主因是用户默认 Company 指向 Demo，正确 Company 下有 2026-07 Attendance；修复 HBOS 报表固定 500 行截断与缺少部门 / 批次过滤的问题；新增 `HBOS 月度汇总暂存（对账）` 报表；HRMS 原生入口降级为技术核查。主文档 `docs/milestones/M1_FIX_B5_导入数据链路核查与报表口径收敛.md` 已交付。

M1-FIX 后续规划（仅规划，不自动启动）：

| 轮次 | 名称 | 优先级 | 状态 |
| --- | --- | --- | --- |
| M1-FIX-A | 差距盘点与实施方案 | — | REVIEWING |
| M1-FIX-B | Excel 导入与真实本地数据闭环 | P0 | REVIEWING |
| M1-FIX-B-FIX | Excel 导入与中文体验修复 | P0 | REVIEWING |
| M1-FIX-B2 | 导入口径、安全与准确性修复 | P0 | COMPLETED |
| M1-FIX-B3 | 考勤工作台入口、App 命名与 HRMS 数据一致性修复 | P0 | REVIEWING / Owner UI 验收未通过 |
| M1-FIX-B4 | 考勤模块架构收敛与单一入口重整 | P0 | REVIEWING / Claude PASS，Owner 数据链路验收发现后续问题 |
| M1-FIX-B5 | 导入数据链路核查与报表口径收敛 | P0 | REVIEWING |
| M1-FIX-C | 异常说明三级流程 | P1 | PLANNED |
| M1-FIX-D | 考勤工作台 + 月报 + 领导 Demo | P1 | PLANNED |
| M1-FIX-E | 飞书 OAuth 最小验证 + Owner 体验脚本 + 总审查 | P2 | PLANNED |

状态口径：
- M1 = IN_PROGRESS（产品交付仍在 M1-FIX 中）
- M1-FIX = IN_PROGRESS
- M1-FIX-A = REVIEWING
- M1-FIX-B = REVIEWING
- M1-FIX-B-FIX = REVIEWING
- M1-FIX-B2 = COMPLETED
- M1-FIX-B3 = REVIEWING / Owner UI 验收未通过
- M1-FIX-B4 = REVIEWING / Claude PASS，Owner 数据链路验收发现后续问题
- M1-FIX-B5 = REVIEWING
- M2 = NOT STARTED / WAITING OWNER AUTHORIZATION

M1-FIX 全程禁止：不创建 `hb_core_app`，不把 `hb_attendance_app` 扩大为大而全 HR App，不修改 Frappe/ERPNext/HRMS 核心源码，不提交 `.env`/App Secret/密钥/token/真实数据/Excel/CSV，不接真实考勤机，不部署公司内网/云服务器，不启动大型 Vue/React 前端，不启动 M2，不伪造飞书登录成功，不执行 `docker compose down -v`，不删除 Docker volume，不重建 `frontend` site。

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

状态：COMPLETED。

M1 考勤一期已 closeout。M1 全程为规划、验证与 Demo 准备阶段，不代表进入正式业务开发。

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
- M1-R5：COMPLETED。
- M1-R6A：COMPLETED。
- M1-R6B：COMPLETED。
- M1-R6C：COMPLETED，异常识别与异常说明流程最小实现已通过 Codex 审查并 closeout。
- M1-R7：COMPLETED，飞书登录、领导 Demo 与 M1 收口准备，已通过 Codex 审查并 closeout。
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

## M1-R6A 状态

状态：COMPLETED。

审查记录：Codex 初审 FAIL（R6A 文档未提交、工作区不 clean），已在 `330f320` 中修复并提交。Codex 复审 PASS。M1-R6A 已从 REVIEWING 收口为 COMPLETED。本次 closeout 仅做状态收口，未启动 R6B/R6C/R7，未修改方案结论。

本轮目标：

- 明确 R6 的最小实现路径。
- 核验 HRMS/Frappe 原生能力能否支撑原始打卡流水导入、月度汇总 Excel 导入、Attendance Request 异常说明流程、员工→主管→人事的三级处理流程。
- 判断 R6B 是否需要自定义导入入口、导入批次记录、Attendance Exception、Attendance Correction、`hb_hr_app`。
- 拆分 R6B / R6C 后续执行任务。

当前结果：

- 已明确两类 Excel 导入边界（原始打卡流水导入 ≠ 月度汇总 Excel 导入）。
- 已完成 Frappe Data Import 对 Employee Checkin 导入的能力评估：PASS，原生可覆盖；如需导入批次记录则需自定义 DocType `HBOS Import Log`。
- 已完成 Attendance Request 对异常说明三级流程的能力评估：CONDITIONAL PASS，优先方案 A（Custom Field 扩展原生 Attendance Request + Custom Workflow），方案 B 为备选。
- 已判定 R6B/R6C 不需要创建 `hb_hr_app`。
- 已判定 R6B 需要创建有限的自定义 DocType（`HBOS Import Log`、月度汇总 DocType）。
- 已拆分 R6B（Excel 导入与自动识别）和 R6C（异常流程与月度汇总整合）的详细边界和目标。
- 已完成 6 项 R6 相关 Gate 的逐项判定。
- 本轮未导入 Excel、未创建 App、未创建 DocType、未写代码、未动数据库。
- 本轮未接真实考勤机、未接飞书、未修改核心源码。

M1-R6A 未做：

- 未实现 Excel 导入功能。
- 未导入真实或脱敏 Excel。
- 未创建 App。
- 未创建 DocType。
- 未写正式导入代码。
- 未写异常流程正式代码。
- 未启动 M1-R7。
- 未接飞书登录。
- 未接真实考勤机。
- 未正式接飞书请假。
- 未接飞书工作台。
- 未部署公司内网/云服务器。
- 未修改 Frappe / ERPNext / HRMS 核心源码。
- 未提交 `.env`、备份、密钥、数据库、日志、缓存或运行时产物。

## M1-R6B 状态

状态：COMPLETED。

本轮目标：

- 识别 Owner 提供 Excel 的真实类型。
- 确认该 Excel 能否支撑原始打卡流水导入。
- 固定 Demo 脱敏原始打卡流水模板。
- 验证 Employee 匹配规则。
- 写入 HRMS 原生 `Employee Checkin`。
- 触发或记录 Auto Attendance 处理结果。
- 形成 R6B 主文档并同步状态。

当前结果：

- Owner 提供的 `docs/data/月度汇总表_20260701_20260703.xlsx` 位于仓库目录内，但未被 Git 跟踪。
- 本轮已补充 `.gitignore`：`docs/data/*.xlsx`、`docs/data/*.xls`、`docs/data/*.csv`，防止真实导出文件误提交。
- 该 Excel 被判定为混合表：包含姓名、工号、部门、应出勤、实际出勤、迟到、早退、旷工等汇总字段，也包含 2026-07-01 至 2026-07-03 每日时间列。
- 该 Excel 含真实人员身份列，不可直接作为 R6B `Employee Checkin` 导入源，不提交，不导入。
- R6B 使用脱敏 Demo 原始打卡流水在本地 `frontend` site 验证。
- 已创建 3 名虚构员工、1 个 R6B Shift Type、3 条 Shift Assignment、5 条 Employee Checkin。
- 已调用 HRMS 原生 `process_auto_attendance()`，生成 3 条 Attendance。
- `Employee Checkin -> Auto Attendance -> Attendance` 最小链路通过。
- 迟到 / 早退候选 Attendance 已生成，但 `late_entry` / `early_exit` 未置位；该限制留给 R6C 或后续配置复核。
- Codex 审查 PASS 后，本轮已完成 closeout，状态收口为 COMPLETED。

M1-R6B 未做：

- 未提交 Owner Excel。
- 未提交任何 Excel / CSV。
- 未实现月度汇总 Excel 导入。
- 未把月度汇总 / 混合 Excel 当作原始打卡流水。
- 未创建 App。
- 未创建自定义 DocType。
- 未写正式导入模块。
- 未写正式异常流程代码。
- 未启动 R6C。
- 未启动 R7。
- 未接飞书登录、飞书请假、飞书工作台。
- 未接真实考勤机自动同步。
- 未修改 Frappe / ERPNext / HRMS 核心源码。
- 未部署公司内网或云服务器。
- 未提交真实员工姓名、真实工号或未脱敏数据。

## 前端实施流程规范（M1-R6B 后补充）

在 M1-R6B closeout 后，Owner 确认新增前端实施流程规范，本轮执行记录：

- 已新增 `docs/frontend/FRONTEND_IMPLEMENTATION_GUIDE.md`：定义前端分层（Frappe Desk vs Vue/React 独立前端）、独立前端启动 Gate（原型先行 → Owner 审查 → 前端复刻 → 功能接入）、组件库选择原则、Agent Skill 使用要求。
- 已更新 `docs/AI_CONTEXT.md`：加入前端实施流程规范摘要和链接。
- 已更新 `docs/READING_GUIDE.md`：加入前端规范的读取条件和公共入口文件检查清单。
- 已更新入口文件 `README.md`、`CLAUDE.md`、`AGENTS.md`：补充独立前端开发规则摘要。
- 已更新 `docs/adr/0003-use-dual-layer-frontend.md`：补充前端实施流程规范引用。
- 本轮未启动实际前端开发、不引入 npm 包、不创建 Vue/React 工程、不修改业务代码、不改变 M1 当前范围。

## M0 后续路线记录
34. M2-R7：REVIEWING，留样管理板块开发方案已交付，等待 Owner 审查。业务依据为 Owner 2026-09-04 提供的《留样管理规程》JXH-SOP-LC-1-00-007-09 全套文件（1 正文 + 4 记录 + 2 附件）；两份桌面方案（《LIMS留样管理模块开发方案.md》《留样板块LIMS开发方案.md》）评审结论为业务采纳、技术路线修正（SQL 建表→Frappe DocType、自研/Activiti→workflow_contract 状态机、Node/PostgreSQL→既有 Frappe/MariaDB 底座、独立 12 周→R7A~D 四子轮），并修正 211.166→211.170 条号引用、补充 0 月基线观察。方案定案：HBOS Retention Product / Retention Sample(+Usage Log) / Observation / Usage Apply / Disposal Apply 共 5 主 + 1 子表；标签为 Print Format；4 个 Script Report（留样台账/观察计划看板/季度到期清单/销毁超期清单）；三条状态机（留样在库生命周期、使用四级审批链、处理五级审批链含销毁 3 个月时限）；审计与电子签名全部复用 M2-R6D 机制；与 HBOS Sample 检验闭环打通（检验完成批次一键创建留样）、稳定性样品硬隔离；子轮 M2-R7A 主数据与登记 → R7B 观察管理 → R7C 使用与处理审批 → R7D Vue 原型与复刻。发现规程疑点 3 项（正文 4 级销毁签批 vs 记录四 5 签署位、08 版变更历史记录编号错位、标签尺寸 OCR 疑为 70.0×55.0mm）与待 Owner 确认 7 项（角色方案 A/B、标签尺寸原件确认、观察批手动/自动、历史在库数据是否迁移、法规条号核对、销毁签批层级、提醒提前量）。主文档 `docs/milestones/M2_R7_留样管理板块开发方案.md`。本轮未创建 DocType、未写业务代码、未动数据库、未建 Vue 工程。rev2 修订（首轮审查 FAIL 8 项全改）：8 个状态文件授权口径统一（Owner 已授权 R7 设计，R7A~D 须方案审查通过后启动）；数量字段全部 Float + UOM + package_count；库存 reserved_qty 预占 + FOR UPDATE 原子扣减 + Stock Log 通用库存操作流水（transaction_type/source_doctype/source_name/qty_delta/remaining_qty，覆盖使用/销毁/转出/调整全部来源）；观察计划字段（obs_year/obs_selected_by/obs_selected_date/obs_selected_reason/next_obs_month/next_obs_due_date）挂留样主表；复合唯一改业务键单字段 unique（product_batch_container_key / sample_period_key，validate 生成、用户只读）；角色动作矩阵 + 两条 SoD 硬校验（同人连续签署拦截、申请人自批拦截）；状态机补驳回终态/已转出入口/qm_approved_at 独立字段/deadline 计算基准；Sample→留样映射规则成节（类型白名单/状态白名单/防递归/产品匹配/同批唯一/液体拦截）；R7A~C 验收补并发扣减、重复登记、越权审批、超期销毁、续留改期、单位不匹配、审计字段变更等负向用例；R7C 验收措辞修正为「两类审批链」。
