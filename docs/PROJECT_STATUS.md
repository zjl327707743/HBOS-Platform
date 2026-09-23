# Project Status

项目名称：新乡海滨智能运营管理平台。

## 当前状态

- 当前阶段：M1-FIX 功能补漏阶段（IN_PROGRESS）；M1 产品交付尚未完成。M3 仓储库存数字化管理已由 Owner 授权新开（IN_PROGRESS，与 M1-FIX 并列）
- 当前轮次：M1-FIX-B5（REVIEWING）；M3-R0 至 M3-R5（REVIEWING，其中 M3-R2 至 M3-R5 已执行完毕）；M3-R6（IN_PROGRESS，已开工）
- 当前仓库定位：工程启动文档、AI 上下文、里程碑状态、计划、ADR、环境设计文档、最小 Docker 配置与 M1-FIX 轻量自定义 App
- 当前实现状态：M1-FIX-B2 已 COMPLETED；M1-FIX-B3 为 REVIEWING / Owner UI 验收未通过；M1-FIX-B4 为 REVIEWING / Claude PASS，但 Owner 数据链路验收发现后续问题；M1-FIX-B5 已核查导入数据链路，并收敛 HBOS 报表、月度汇总暂存和 HRMS 原生技术核查口径，当前 REVIEWING；M1-FIX-C/D/E 未启动。M3-R0 已完成仓储库存只读盘点、飞书参考文档只读拉取与需求确认，当前 REVIEWING；M3-R1 已建立货位主数据树（212 节点）并完成粒度验证，当前 REVIEWING；M3-R2 已执行完毕：已新建并安装 `hb_inventory_app`、落地主数据与 2 个报表、货位树改挂到 `3904`。M3-R3 已执行完毕：新增出库放行门禁、货位变更复验、`效期预警` 与 `库级盘点三对账` 报表、补建 `仓库工作台` 入口（原「仓储库存工作台」，2026-09-23 改名并换图标；**该入口两个缺陷已于 2026-09-23 修复**：图标曾与 ERPNext 原生 `Stock` 同名同图致点错，以及**桌面图标因 label 与侧边栏名不一致被 Frappe 静默丢弃**（父图标被丢弃还会连带子图标），现已三者同名）。M3-R4 已执行完毕：三个 Print Format（待检证 + 自产/外购货位卡）按批次数据生成（当时只支持手动打印）。M3-R5 已执行完毕：货位二维码标签 + 扫码页（全部字段、不脱敏）。均 REVIEWING。M3-R6 已开工（IN_PROGRESS）：服务骨架、约束校验层、Frappe 侧入口与校对界面均已交付并验证；**真实样本准确率实测已完成**（50 张 / 250 字段；末选 `small` 档：全字段 82%、单张均 8.1 s（7~9 s）；**分档实测**：大字全字段 `small` 82% / `medium` 86%，小字整串命中 `small` **83.5%** / `medium` 85.2%，**手写档无真值、给不出准确率**）；**入库提交后自动生成货位卡与待检证已交付**（详见下方第五批），并**顺带修复 M3-R4/R5 的打印纸型缺陷**。
- 当前远端：`origin` -> `https://github.com/zjl327707743/HBOS-Platform.git`，GitHub visibility = `PUBLIC`（公开协作仓库，范围见 `PUBLIC_REPOSITORY_SCOPE.md`）。另有内部私有归档库 `https://github.com/zjl327707743/HBOS.git`（`PRIVATE`，不接受普通成员开发），当前工作副本**未绑定**该私有库。历史记录中的 `HBOS.git` 为 M0-REMOTE 时期的绑定，已被当前的 `HBOS-Platform.git` 取代。
- 下一步路线：M1-FIX-C（异常三级流程）为 PLANNED / 待 Owner 授权；不自动启动 M1-FIX-C/D/E。M3-R6（入库拍照识别）为 IN_PROGRESS：准确率已实测（`small` 档 94.4%，**该数字主要衡量数字、不是汉字**；分档实测见下方第四批），**Owner 已决策（2026-09-16）**：效期只印到月时**按月末推定**、**不加粒度字段**；**外购暂缓**（外购到货时已有现成待检证与货位卡），本轮按自产收口。**耗时问题已解决**：改用 PaddleOCR `small` 档（免装依赖）→ 单张约 **7 s**（原 medium 35 s），已进 10 s 标准线。**仍待定：置信度类标准**（高置信度错误 ≤1% / 低置信度召回 ≥90%）C2 无逐字段置信度、**测不了**。M2 未启动。
- 飞书登录（M2-R0）：由 Owner 授权提前实现 M2 飞书集成首项，代码实现与本地真实验证已完成（REVIEWING）；同步完成 HRMS 界面汉化与「Frappe HR」→「海滨HR」改名（REVIEWING）。详见 `docs/milestones/M2_R0_飞书登录实现记录.md`；M2 整体仍 NOT STARTED。

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
28. M2：未启动 / 待 Owner 授权。

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

## M3 状态

状态：IN_PROGRESS。

M3 仓储库存数字化管理由 Owner 明确授权新开，与 M1（考勤）为并列里程碑，不替代、不阻塞 M1-FIX。

M3-R0：REVIEWING。本轮为仓储库存只读盘点与需求确认，已交付主文档 `docs/milestones/M3_R0_仓储库存只读盘点与需求确认.md`、门禁文档 `docs/milestones/M3_START_GATE.md` 和里程碑台账 `docs/milestones/M3.md`。

M3-R1：REVIEWING。本轮为货位主数据建模与粒度验证，已交付主文档 `docs/milestones/M3_R1_货位主数据建模与粒度验证.md` 与三个脚本（`scripts/M3R1_货位清单.json`、`scripts/M3R1_建立货位主数据.py`、`scripts/M3R1_粒度验证.py`）。

M3-R1 当前结果：

- 按方案 A1 建立货位树：`16号楼产品库 → 03区 → 五个层 → 203 个货位` + 2 个非货位区域，共 **212 个新节点**；`Warehouse` 总数由 5 增至 217。
- 层分布校验 **39 / 39 / 39 / 43 / 43 全部通过**；NestedSet（`lft`/`rgt`）完整性校验通过（无缺口、无重复、无非法区间、父子包含 0 违规、兄弟重叠 0）；脚本幂等验证通过（重复执行"新建 0 / 跳过 212"）。
- 用 `TEST-M3R1-` 虚构数据完成粒度验证：**"按批号查货位"与"货位→全部批号"双向通过**；同一批次散放多货位（B001 同时在两个货位）成立；移库后数量正确。
- **重要更正**：M3-R0 依据表结构推断"批次在 `Stock Ledger Entry.batch_no`"，**实测该列在 v16 中为空**。批次实际存放在 `Serial and Batch Bundle` / `Serial and Batch Entry`，通过 `SLE.serial_and_batch_bundle` 关联。正确的聚合 SQL 已实测通过，并已同步更正 M3-R0 §2.7、§4 映射表与门禁文档。
- 其他发现：`Stock Settings` 的批次开关默认关闭（已按 Owner 确认开启）；出库批次选取规则原生即为 **FIFO**（与需求一致）；`Batch.batch_qty` 是累计收货量而非结存；`UOM` 中**没有「件」**，M3-R2 需创建。

M3-R1 创建的虚构 TEST 数据（`TEST-M3R1-` 前缀）：`Item` 1、`Batch` 2、已提交 `Stock Entry` 3、`Stock Ledger Entry` 4、`Serial and Batch Bundle` 4、`Serial and Batch Entry` 4、`Bin` 3。仅影响 `16-03-221`/`222`/`223` 三个货位，无真实产品、批号或数量。

M3-R1 未做：未创建自定义 Frappe App、未创建 DocType、未实现任何业务功能、未创建真实产品数据、未创建「件」计量单位、未修改 Frappe/ERPNext/HRMS 核心源码（除 Owner 已确认的 `Stock Settings` 批次开关外未改其他全局设置）、未执行飞书写入、未启动外部服务与独立前端、未提交 `.env`/密钥/真实数据、未执行 `docker compose down -v`、未删除 volume、未重建 `frontend` site。

## M3-R2 状态

状态：REVIEWING（已执行完毕，等待 Owner 和 Claude 审查）。

本轮先出方案，Owner 授权后已执行完毕。已交付主文档 `docs/milestones/M3_R2_入库登记与批次货位台账方案与执行记录.md`。

Owner 已确认四项设计决策：

| 议题 | 决策 |
| --- | --- |
| 包装构成（件 / 听 / 瓶） | 自定义子表 `HBOS 包装明细`（容器类型 + 单件重量 + 件数），挂 `Batch`；「件」仅作计数单位不做换算；`kg` 为权威数量 |
| 「待检 → 放行 / 不放行」门禁 | `Batch` 自定义字段（放行状态 + 放行日期 + 合格证编号 + 附件），出库时校验 |
| 自定义字段 / UOM / 模板归属 | **Owner 授权新建 `hb_inventory_app`**（模块 `HBOS Inventory`），沿用 `hb_attendance_app` 的 `after_migrate` + `create_custom_fields` 代码化模式 |
| 产品分类 | 新建海滨分类树（挂 `Item Group` 下），与批号规则 / 有效期口径的产品种类对齐 |

调研发现（只读查询，未改配置）：

- `Item.shelf_life_in_days`（Int）+ `has_expiry_date` 原生可承载"效期期限"（2 年 = 730 天），但"复检期 / 有效期"类型需自定义字段。
- `Item.uoms` = 原生 `UOM Conversion Detail`，是**固定换算系数**，装不下"整桶 5kg / 尾桶 4.33kg"，印证自定义子表方案。
- `Quality Inspection` 原生存在（`status` = Accepted / Rejected / Cancelled，`batch_no` Link），但要求挂具体单据且必填检验人，属"检验记录"语义，与 Owner 的"放行手续 + 合格证"凭证语义不匹配，故未采用；保留为未来可选。
- `Item Group` 仅有标准 6 类（Products / Raw Material / Sub Assemblies / Consumable / Services），无海滨产品种类。
- **更正此前一处误判**：自定义字段实际是**有版本化**的——`hb_attendance_app` 通过 `hooks.py` 注册 `after_migrate`，在 `setup.py` 中调用 `create_custom_fields(...)` 声明式创建（Employee Checkin 3 个、Attendance 6 个等），代码化、幂等、可复现。M3 沿用同一模式，这也是授权新建 `hb_inventory_app` 的意义。

M3-R2 唯一剩余缺口：~~产品主数据口径~~ → Owner 已提供；~~`16号楼产品库` 与 `3904` 是否同一处~~ → **Owner 已确认二者是同一处**（M3-R2 执行时把已建的 203 个货位改挂到 `3904` 之下）。

**执行前置（须 Owner 另行授权）**：新增 `hb_inventory_app` 需调整 `docker-compose.yml` 的挂载与 PYTHONPATH（涉及 backend / configurator / create-site / frontend / queue-long / queue-short / scheduler / websocket 共 8 个服务，另需补 frontend 的 assets 符号链接）。这属项目规则明列的"不写 Docker Compose"，须明确授权后方可执行；且改动生效需**重建容器**（非仅 restart）。备选方案（容器内建 App、不挂载）不可复现，已排除。详见方案 7.1。

**Owner 已提供的产品主数据口径**：

- 物料代码 8 位数字，SAP 创建、SAP 管理员维护；按前四位分大类：`1000` 原料药、`1100` 包材、`1200`/`1201`/`1202`/`1203` 非生产用物料 / 辅助用品、`1300` 中间体、`1400` 成品。
- 六车间 **8 个库位**（3902 退货库 / 3903 不合格品库 / 3904 中间库 / 3906 液体库 / 3907 冷藏库 / 3908 包材库 / 3914 物料库 / 3915 备品备库），Owner 已确认一并建入 `Warehouse`。
- 5 个库位有 08 月盘存表（3904/3907/3908/3914/3915），合计 **433 行、94 个物料代码**。
- **实测计量单位 11 种**（KG / 个 / 套 / 瓶 / 支 / 双 / 卷 / 张 / L / BT，另加「件」）。**修正早期设想**："双单位 KG/件"仅适用于原料药与中间体；包材与备品用件类单位。Owner 已确认按实际建全部 UOM。
- **盘存表为库级三对账**（ERP数量 / 货位卡数量 / 实物数量），**无货位号列**；Owner 已确认盘点按库级做三对账。
- 复检期 / 有效期至**合并为一列日期**；数据中未出现亚批。

数据安全：5 份盘存表与《库位区分》含真实物料名称、批号、数量，**未复制进仓库、未提交 Git**；文档只记录规则、结构与数量级。

M3-R2 执行结果（Owner 授权后已执行）：

- 新建并安装 `hb_inventory_app`（模块 `HBOS Inventory`），沿用 `hb_attendance_app` 的 `after_migrate` + `create_custom_fields` 代码化模式。
- `docker-compose.yml` 变更（Owner 已授权）：8 个服务补 volume 挂载、6 个服务补 `PYTHONPATH`、frontend 补 assets 符号链接；`docker compose up -d` 重建容器，`db-data` / `sites` / `logs` 三个 volume 全部保留，未重建 site。
- 主数据：新建 10 个 UOM（`UOM` 239→249）、六车间 7 个新库位（加改名的 3904 共 8 个）、5 个产品分类树节点、`Item` 5 个自定义字段、`Batch` 7 个自定义字段、子表 DocType `HBOS Packaging Detail`、2 个报表（`按批号查货位`、`货位明细表`）。
- 货位树改挂：`16号楼产品库 - HB` 经 `rename_doc` 改名为 `3904 六车间中间库 - HB`，子节点父级自动更新，NestedSet 完整性复验通过，203 个货位全部保留，层分布仍 39/39/39/43/43。
- 全链路验证通过（`TEST-M3R1-` 虚构数据）：批号→货位、货位→全部批号、包装构成（12件+1件尾桶+3听+1瓶）、放行字段（已放行 + 日期 + 合格证 + 原厂批号）并已带出到报表。
- 偏差两处：DocType 用英文名 `HBOS Packaging Detail`（与考勤 App 约定一致）；库级盘点三对账报表按交付边界留到 M3-R3。

**另修复一处既有缺陷（不在 M3 范围，但阻塞 migrate）**：`bench migrate` 全站失败 `KeyError: 'doctype'`，根因是 `hb_attendance_app/hb_attendance_app/hbos_attendance/page/hbos_monthly_upload/hbos_monthly_upload.json` 缺少 `doctype` / `name` / `module` / `owner` / `page_name` 必需字段（M1-FIX 期间产生）。按同目录 `hbos_attendance_import.json` 的标准结构补齐（`name` / `page_name` 取库中既有值 `hbos-monthly-upload`）后，migrate exit 0 无 Traceback。**此前 `bench migrate` 一直失败，任何依赖 migrate 的操作（含 `after_migrate` 钩子）都不会生效。**

M3-R2 未做：未创建真实产品主数据、未做库级盘点三对账报表（留 M3-R3）、未做出库核销 / 效期预警 / 盘点导出（M3-R3）、未做待检证与货位卡（M3-R4）、未做二维码扫码页（M3-R5）、未做拍照识别（M3-R6）、未修改 Frappe/ERPNext/HRMS 核心源码、未接飞书写入、未启动外部服务与独立前端、未执行 `docker compose down -v`、未删除 volume、未重建 site。

本轮已确认 Owner 三项决策：

- 里程碑归属：新开 M3 仓储里程碑。
- 入库拍照识别：外部 FastAPI + 视觉模型独立服务，返回结构化 JSON，人工校对后入台账。
- 货位二维码扫码页：Frappe 原生 Web 页，不启动独立 Vue/React 前端。

本轮只读盘点结论：

- ERPNext `Stock` 模块 44 个非子表 DocType 均可用，包括 `Item`、`Batch`、`Warehouse`、`Bin`、`Stock Ledger Entry`、`Stock Entry`、`Purchase Receipt`、`Delivery Note`、`Stock Reconciliation`、`Quality Inspection`、`Inventory Dimension`。
- 当前 site 无任何库存业务数据：`Item` 0、`Batch` 0、`Bin` 0、`Stock Ledger Entry` 0、`Stock Entry` 0；`Warehouse` 5（ERPNext 默认库位树）、`UOM` 239、`Item Group` 6、`Company` 1。
- `Batch` 原生具备 `batch_id`、`manufacturing_date`、`expiry_date`、`batch_qty`，可承载批号与效期。
- 结论：除拍照识别与扫码页外，其余需求应优先复用 ERPNext 原生 `Stock` 模块，不自建 DocType。`Bin` 粒度只到"物料 × 货位"（唯一索引 `unique_item_warehouse`，不含 `batch_no`），不可直接当作批次台账。**批次 × 货位的正确来源见下方 M3-R1 更正**。
- **M3-R1 实测更正**：本轮曾依据表结构判断"批次 × 货位 → 数量由 `Stock Ledger Entry` 聚合（SLE 含 `warehouse` + `batch_no`）"。M3-R1 实际写入后实测发现 **`SLE.batch_no` 在 v16 中为空列**；批次数据实际存放在 `Serial and Batch Bundle` / `Serial and Batch Entry`（含 `batch_no`、`warehouse`、`qty`），通过 `SLE.serial_and_batch_bundle` 关联。正确聚合路径已实测通过并写入 M3-R1 主文档第四节，M3-R0 正文相关段落已同步更正。
- 货位建模候选：`Warehouse` 树 / `Inventory Dimension` / 自定义 DocType 三方案；Owner 已定案走**方案 A（`Warehouse` = 货位）**、**方案 A1（层作为 `Warehouse` 树一级）**，"工作台""退回产品区"建成叶子 `Warehouse`，存放模式为**固定货位 + 随机存放**，试点范围**只做 16 号楼产品库**（203 个货位）。
- 只读分析确认"层"**不能由货位编码推导**（205–282 奇 = 第一层 / 偶 = 第二层；285 起不单调：316–359 第四层、360–368 又回第三层、369 起第五层），层必须显式录入；层分布 39 / 39 / 39 / 43 / 43。
- Owner 补充提供两份《自产物料/产品货位卡》实例，已解析字段与版式（含品名、物料代码、生产车间、生产批号、包装规格、件数、复检期/有效期勾选、入库经手人/复核人、入库数量与单位、货位号、待检日期、放行/不放行勾选、出入库流水表），作为 M3-R4 货位卡生成的直接依据。
- 货位卡暴露三处文档未明确的约束：① 存在"待检 → 放行 / 不放行"**状态门禁**，不只是生成待检证，Owner 明确**出库须有 QA 放行手续与合格证**；② "件数"是**件 / 听 / 瓶 混合构成**（件 = 5kg 一桶、尾桶 = 不足 5kg、听/瓶 = 取样小样），ERPNext 双 `UOM` 单一换算系数装不下；③ 卡片只有一个"货位号"字段，Owner 明确**一个批号只对应一张货位卡**，不论散放多少货位。
- 业务口径新增明确 5 项：**批号由车间生成、仓库按车间批号登记**（M3 不做批号生成）；双单位为 **KG / 件**；效期按**产品质量标准**逐产品设定（2 年 / 3 年不等，分**复检期**与**有效期**）；出库核销为 **FIFO + 客户指定先出**；货位卡模板已提供。
- Owner 提供批号编制规则（两张图片）：三类型结构——① 原料药/中间体 `生产线-年-月-流水号(3位，001–999)`，同月同品种递增、不随日期更改、换月重置；② 混粉 `生产线-主要两组份拼音首字母-年-月-流水号`；③ 亚批次 `主批号-1/-2/-3`（按生产时间顺序）。**生产日期 = 投料当天，有效期自投料当天起算**。已用两份货位卡批号验证类型一格式通过（批号原值不写入仓库）。
- 批号规则建模问题结论（三处均已收口）：① ~~撞号~~ → **Owner 明确不存在撞号，已排除**；`Batch.batch_id` 可直接承载业务批号，无需组合键，**"按批号查货位"以批号为唯一键成立**；② ~~混粉多来源承载~~ → **Owner 明确混粉与成品完全一样、登记流程完全相同，已解除**——仓库对所有产品种类走**同一套登记流程**，混配与来源批次追溯不在仓库范围；③ **亚批次**同样按统一流程登记，如需追溯 `Batch.parent_batch` 原生可选支持。
- 本轮重要简化：初稿一度为混粉引入"多来源批次追溯"特殊建模，经 Owner 澄清后确认多余；M3-R2 无需按产品种类分支。
- 有效期口径**按产品种类区分**（原料药/中间体与亚批次从投料当天起算；混粉从混料当天起算；相同原料不同批次混合取最短批次）。初稿曾登记为"口径不一致"，**属表述不当已修正**——规则表按产品种类组织，不同种类口径不同是设计如此。系统含义：产品主数据上维护"效期类型（复检期/有效期）+ 期限"，来源为产品质量标准。
- Owner 明确两项关键规则：**出库须有 QA 放行手续与合格证，缺任一项不可出库**（硬门禁）；**一个批号只对应一张货位卡**，不论该批散放多少个货位。
- Owner 提出需要"货位明细表"（一个货位上的全部批号）；该视图由 `Stock Ledger Entry` 按 `warehouse` 聚合即可，是"批号→货位"的反向视图，**无需新建数据表**。
- 澄清包装构成：货位卡"件数"（如 `34件3听1瓶`）是**同一批次的包装构成**——**件 = 5kg 一桶**（两桶一纸箱）、**尾桶** = 分装剩余不足 5kg 单独装桶、**听 / 瓶** = QC 或客户取样用小样，均同批次同货位存放；既非批次也非货位概念。ERPNext 双 `UOM` 单一换算系数装不下，M3-R2 需定承载方案。
- 更正：`Batch.manufacturing_date` 原生语义即"投料当天"，无需自定义；需自定义的是生产车间与效期类型（复检期 / 有效期）。

本轮飞书参考文档获取（Owner 授权）：

- 已安装 `lark-cli` 1.0.95（`~/.local/bin/lark-cli`）与 28 个 `lark-*` skill（`~/.claude/skills`）。
- 已新建专用飞书应用（App ID `cli_aa2debd5d3b85ce8`，与 M2-R0 登录应用相互独立）并完成 OAuth 登录。
- 已只读拉取 Owner 提供的两篇参考文档与两个附件；**未执行任何飞书写入**。
- 提取结论：批次 ↔ 货位为多对多；货位二维码存查询链接、扫码实时查库；货位编码格式 `16-03-NNN`（203 个，按第一层 ~ 第五层组织）；待检证字段为品名 / 物料代码 / 供货单位 / 生产单位 / 批号 / 数量 / 储存条件 / 操作人日期；试点为 16 号楼产品库。
- 含真实业务数据的附件仅下载到 `/tmp` 解析，未进仓库、未提交 Git。

M3-R0 待确认项：

1. 业务口径 20 项：已明确 12 项、已确认决策 3 项、部分明确 2 项、待确认 4 项（产品主数据、盘点口径、扫码可见信息、拍照校对责任，**均非阻塞**）。**已无高优先级待确认项**，M3-R0 具备收口条件。另有 2 项技术承载方式待 M3-R2 落定（包装构成、待检 / 放行联动实现）。
2. 飞书权限偏宽（观察项）：`--domain docs,wiki,drive` 实际授予了写入类 scope，本任务不需要；本轮未执行任何写入，建议后续收窄。

M3-R0 未做：未创建自定义 Frappe App、未创建 DocType、未写业务代码、未创建业务数据、未执行 `migrate`、未修改 Frappe/ERPNext/HRMS 核心源码、未执行任何飞书写入、未启动外部 FastAPI 服务、未调用视觉模型、未启动独立前端、未提交 `.env`/密钥/真实数据/Excel/CSV、未执行 `docker compose down -v`、未删除 volume、未重建 `frontend` site。

M3 后续轮次（仅规划，不自动启动）：

| 轮次 | 名称 | 优先级 | 状态 |
| --- | --- | --- | --- |
| M3-R0 | 仓储库存只读盘点与需求确认 | — | REVIEWING |
| M3-R1 | 货位与批次主数据建模 | P0 | REVIEWING |
| M3-R2 | 入库登记与"产品—批次—货位"台账 | P0 | REVIEWING |
| M3-R3 | 出库核销、货位变更、效期预警、盘点导出 | P0 | REVIEWING |
| M3-R4 | 待检证与货位卡自动生成 | P1 | REVIEWING |
| M3-R5 | 货位二维码与手机扫码页 | P1 | REVIEWING |
| M3-R6 | 入库拍照识别服务 | P1 | IN_PROGRESS |
| M3-R7 | 总审查与收口 | P2 | PLANNED |

M3 全程禁止：不修改 Frappe/ERPNext/HRMS 核心源码；未经 Owner 逐轮授权不创建自定义 Frappe App 与 DocType；不启动独立 Vue/React 前端；不接飞书真实写入；不提交 `.env`、密钥、token、真实产品清单、真实批次数据、Excel/CSV；不执行 `docker compose down -v`；不删除 Docker volume；不重建 `frontend` site；不启动 M1-FIX-C/D/E 与 M2。

## M3-R3 状态

状态：REVIEWING（已执行，等待 Owner 和 Claude 审查）。

主文档：`docs/milestones/M3_R3_出库核销效期预警与盘点导出.md`。

本轮交付四件事并补建一处入口：

- **出库放行门禁（核心）**：新增 `hb_inventory_app/hbos_inventory/release_gate.py`，经 `hooks.py` 的 `doc_events` 挂在 `Delivery Note` 与 `Stock Entry`（`purpose = Material Issue`）的 **`before_submit`**（不挂 `validate`，使草稿仍可保存）。出库批次须 `Batch.hbos_release_status = 已放行` 且 `hbos_certificate_no` 非空，否则中止提交并给出明确提示。
- 门禁**有意收窄**：`Material Receipt`（入库）与 `Material Transfer`（库内移库，含移入不合格品库）不门禁；`Delivery Note` 的退货方向（`is_return`）不门禁。
- 批次取法：优先明细行 `batch_no`，回落 `serial_and_batch_bundle` 查 `tabSerial and Batch Entry`（依据 M3-R1 实测：v16 中 `SLE.batch_no` 为空列）。
- **实测**：待检批次出库被拦截（提示准确）；已放行批次出库通过；待检批次移库与入库均不受影响。
- **货位变更**：复用原生 `Stock Entry`（Material Transfer），无需新代码；复验 15 kg 移库成功、结存闭合。
- **效期预警报表**：按预警天数（默认 90）列出临近到期批次，含紧急度分级（已过期 / ≤30 天 / ≤90 天）、剩余天数、效期类型、放行状态。实测近效期虚构批次正确返回「紧急（≤30 天）」。
- **库级盘点三对账报表**：按库位出 ERP 数量，货位卡数量与实物数量**留空**供导出后现场填写（对齐纸质《物料及产品盘存记录》口径，该表本身无货位号列）。
- **补建操作入口**：M3-R2 遗漏的「入库登记入口」经核实后已在其主文档 9.5 补记为**偏差三**；本轮新建 `仓库工作台`（Workspace + 侧边栏 + 桌面图标，幂等，由 `after_migrate` 同步），入口指向原生表单与四个报表。
- ⚠ **入口缺陷更正（2026-09-23，Owner 验收发现）**：Owner 报「点进去会跑到库存模块，桌面又找不到仓库工作台、回不来」，核查属实，**两个独立缺陷** —— ① 顶层图标用了 `stock`，与 **ERPNext 原生 Stock 模块图标完全相同**，点错即进原生模块而那边没有本 App 侧边栏；② **桌面图标被 Frappe 静默丢弃**（主因）：`get_desktop_icons()` 要求图标 label 能在侧边栏映射里查到、且父图标在放行集合里，两条都不报错；本 App 图标 label 是 `仓储库存` 而侧边栏叫 `仓库工作台` → 查不到被丢弃；后补的工作台条目又挂在那个已被丢弃的父图标下 → **一起被过滤，桌面上一个入口都没有**。**已修**：三者同名（`DESKTOP_LABEL = WORKSPACE_TITLE`）、显式清空 `parent_icon`、清理陈旧图标、补 9 条契约测试。**验证方式也踩过坑**：直接调 `get_desktop_icons()` 不传 `bootinfo` 时恒返回空，第一次据此得了错误结论，必须走 `get_bootinfo()`。详见 M3-R3 主文档 6.2 节。
- ⚠ **改名后的页面版本戳补修（2026-09-23）**：改名时改了拍照识别页的 `.js`（返回按钮 → `Workspaces/仓库工作台`），**但没推该页 `.json` 的 `modified`** —— `pageview.js` 只要 `localStorage["_page:<name>"]` 存在就用缓存、根本不发请求，失效条件**只看 `Page.modified`**，所以服务端下发了新页、浏览器仍显示旧按钮（指向已不存在的旧路由）。已推版本戳 + `bench migrate` 修掉。详见 M3-R6 主文档第九批。

前置条件处理：

- 出库核销口径：Owner 早前已确认 FIFO + 客户指定先出；只读核对 `Stock Settings.pick_serial_and_batch_based_on = FIFO`，**原生即符合**。
- QA 放行校验方式：本轮定案为 `before_submit` 硬门禁。
- 负库存：采用 ERPNext 默认「不允许」（`allow_negative_stock = 0`、`allow_negative_stock_for_batch = 0`），未改配置。

实现过程中修复两个自身缺陷（已记录）：`Desktop Icon.link_to / sidebar` 必须指向已存在的 `Workspace Sidebar`；`Desktop Icon.bg_color` 与 `Workspace Shortcut.color` 取值受枚举限制。

M3-R3 未做：待检证与货位卡 `Print Format`（M3-R4）、货位二维码与扫码页（M3-R5）、入库拍照识别（M3-R6）、定制化录入页（当前走原生表单）、效期预警主动推送（当前仅查询报表）、盘点差异系统回写、未创建真实产品主数据、未修改核心源码、未接飞书写入、未执行 `docker compose down -v`、未删除 volume、未重建 site。

## M3-R4 状态

状态：REVIEWING（已执行，等待 Owner 和 Claude 审查）。

⚠ **2026-09-23 更正**：本轮三个 `Print Format` 此前「渲染与 PDF 验证通过」的结论**不成立**——
生成了 PDF、页型也对，但**里面一个汉字都没有**（后端容器无中文字体，wkhtmltopdf 静默丢弃汉字，
只留 ASCII/数字）。Owner 打开待检证看到的「乱码」即此。**已修**（容器挂载中文字体），
详见 M3-R6 主文档第九之十一节。

主文档：`docs/milestones/M3_R4_待检证与货位卡自动生成.md`。

本轮交付**按批次数据自动生成待检证与两种货位卡**：

- 新增三个 `Print Format`（`doc_type = Batch`、`standard = Yes`、`print_format_type = Jinja`、HTML 内嵌）：
  - `HBOS 待检证`：75mm × 110mm 小标签，10 行表格（标题+固定编码 / 品名 / 物料代码 / 供货单位 / 生产单位 / 批号 / 数量 / 储存条件 / 空行 / 操作人日期）。
  - `HBOS 自产货位卡`：A4，表头 4 行 + 入库/待检/放行 3 行（货位号垂直合并）+ 12 行流水表 + 备注。
  - `HBOS 外购货位卡`：A4，表头 6 行（含供货单位 / 生产单位 / 原厂批号 / 进厂批号）+ 状态 3 行 + 12 行流水表（含领料单位 / 用途）+ 备注。
  - 版式取自 Owner 提供的实物模板结构（`待检证/`、`自产/`、`新版货位卡外购/`），但 HTML/CSS 为**重新实现**，未复制真实文件内容。
- 新增 `hbos_inventory/print_utils.py`（打印辅助方法，全部只读），经 `hooks.py` 的 `jinja.methods` 注册为 Jinja 全局方法。
- 新增 `Batch` 自定义字段 `hbos_source_type`（自产 / 外购，默认自产），用于判别打印哪种货位卡；函数仍带推断兜底。
- **本轮定案**：一批散放多货位时，在「货位号」单元格内**逐行列出**全部货位，不改变原表结构（纸质卡该格本为单个合并单元格）。
- 其他口径：**件数按容器类型汇总**（依据实物卡写法 `42件5听10瓶` 反推：41+1=42、4+1=5、9+1=10）；流水表**按单据净减少**判断——库内移库一出一进净影响为 0，不计入「发出」；「Kg」统一显示为「kg」。
- 留空字段（系统无数据，供手写）：入库经手人 / 复核人、经手人 / 复核人、待检日期、去向、领料单位、用途、流水的件数列。已预填：入库日期、放行日期、放行勾选、复检期 / 有效期勾选。

验证结果（`TEST-M3R1-` 虚构数据）：

| 模板 | 渲染 | PDF |
| --- | --- | --- |
| `HBOS 待检证`（自产 B001） | 通过 | 通过（17.5 KB） |
| `HBOS 待检证`（外购 B002） | 通过 | — |
| `HBOS 自产货位卡`（B001） | 通过 | 通过（18.1 KB） |
| `HBOS 外购货位卡`（B002） | 通过 | 通过（18.2 KB） |

关键抽查：自产卡 B001 的件数 `13件3听1瓶`、货位号显示两行（`16-03-221` / `16-03-223`）、放行 ☑、流水表仅一条真实领用（发出 5.00 / 结存 95.00，移库未污染）。

实现中发现并修复 5 处问题：① `hbos_production_unit` 误从 `Batch` 读 `hbos_workshop`（该字段在 `Item` 上）；② 件数未按容器类型汇总；③ 单位显示 `Kg` 与纸质表 `kg` 不一致；④ 流水表把库内移库误记为「发出」；⑤ **Jinja 方法注册机制会连带注册 `import` 进来的函数**，可能覆盖 Frappe 同名全局（如 `flt` / `getdate`），故 `print_utils.py` 只 `import frappe`、改用全限定调用。

M3-R4 未做：批量打印（一次打印多个批次）、打印后流程联动、二维码字段（留 M3-R5）、货位扫码页（M3-R5）、入库拍照识别（M3-R6）、未创建真实产品主数据、未修改核心源码、未接飞书写入、未执行 `docker compose down -v`、未删除 volume、未重建 site、未提交真实模板文件。

## M3-R5 状态

状态：REVIEWING（已执行，等待 Owner 和 Claude 审查）。

⚠ **2026-09-23 更正**：`HBOS 货位二维码` Print Format 与 M3-R4 三个格式同一缺陷——
生成的 PDF 里汉字全被丢弃（容器无中文字体），标签上的货位名与提示行当时是空的。
**已随 M3-R4 一并修复**，详见 M3-R6 主文档第九之十一节。

主文档：`docs/milestones/M3_R5_货位二维码与手机扫码页.md`。

本轮交付**货位二维码与手机扫码查询页**：

- 二维码内容 = **货位查询链接**`{站点}/hbos_bin?bin={货位短码}`，**不含静态物料信息**，扫码后服务端实时查库（Owner 在 M3-R0 已定）。货位短码去掉 ` - HB` 后缀；含中文的短码入二维码前做 URL 编码。
- 扫码页 `/hbos_bin` 为 **Frappe 原生 www 页面**（服务端渲染，非独立前端工程）：
  - 传货位短码 → 展示该货位全部在库明细；
  - 传库位 / 层（分组节点）→ 展开其下全部叶子货位汇总，页首标注"库位汇总（含下级货位）"；
  - 未登录 → 跳登录页并**回跳本页**；货位不存在 / 缺参数 → 友好提示。
- **展示全部字段、不脱敏（Owner 在 M3-R5 确认）**：批号 / 物料代码与名称 / 数量单位 / 包装规格 / 件数 / 放行状态（含合格证号与放行日期）/ 来源类型 / 生产日期 / 有效期（含效期类型）/ 生产车间 / 生产单位 / 供货单位 / 原厂批号；页首汇总批次数、物料数、合计数量。
- 新增 Print Format **`HBOS 货位二维码`**（60mm × 40mm 标签纸，挂 `Warehouse`），含短码大字、库位名、内联 SVG 二维码、提示语与完整链接。二维码由 Frappe 自带 `pyqrcode` 生成，**未新增第三方包**。
- 货位短码解析做三级匹配（完整名 → 短码精确 → **短码前缀**），手输 `3904` 可命中 `3904 六车间中间库`。
- 与 M3-R4 共用 `print_utils`，保证**扫码页与货位卡的包装规格、件数写法一致**。

**登录边界（需 Owner 知悉）**：扫码页要求登录。"不脱敏"指对已登录员工全部开放；**免登录扫码本轮未做**，如需请另行授权并界定可见范围。

验证（HTTP 实测）：匿名访问 301 跳登录且回跳参数正确编码；`?bin=16-03-221` 显示货位明细；`?bin=3904` 前缀命中并显示库位汇总；`?bin=第一层` 分组展开；不存在与无参数均为友好提示。二维码渲染与 PDF 通过。**M3-R4 三个模板回归通过**。

实现中发现并修复 6 处问题，两处值得注意：

1. **www 路由名含连字符会导致整页 500**——`www/hbos-bin.py` 无法作为 Python 模块 import，`get_context` 不执行，模板缺变量报错。改为下划线路由 `/hbos_bin`。
2. **`hooks.py` 中 `jinja` 被重复定义**（M3-R4 遗留缺陷）——Python 后定义覆盖前定义，当时 `print_utils` 仍注册成功故未暴露；本轮新增 `qr_utils` 时才显现，已合并为一个定义。

M3-R5 未做：免登录扫码、二维码批量打印（当前在 `Warehouse` 表单逐个打印）、货位平面图导航、扫码页库存变动历史、入库拍照识别（M3-R6）、未修改核心源码、未接飞书写入、未执行 `docker compose down -v`、未删除 volume、未重建 site。

## M3-R6 状态

状态：IN_PROGRESS（门禁已确认；Owner 已授权；**服务骨架、约束校验层、Frappe 侧入口与校对界面均已交付；真实跨进程端到端已验证通过**；准确率实测待仓库样本）。

主文档：`docs/milestones/M3_R6_入库拍照识别服务方案.md`（执行记录见其第九之二节）。

**最近一次修复（2026-09-23，Owner 指示「重启，并把该修的都修了」）**：
① **常驻识别服务跑的是旧代码**（进程 9/21 08:54 启动，启动命令无 `--reload`）→ `c2_ocr:small` 档位写法被 400 拒（文档却写着可用）、当天修好的品名抽取规则未生效；**已重启**，复测 `c2_ocr:small` 返回 200、品名恢复正确（`美罗培南` / 空 / 空）。
② **页面版本戳未推**：改名批改了拍照识别页 `.js` 但没推 `.json` 的 `modified`，浏览器 `localStorage` 缓存永不失效 → 页面返回按钮仍指向旧路由；已推版本戳 + `migrate`。详见主文档**第九批**。
③ **打印件汉字全丢**（Owner 报「打开全是乱码」）：后端容器**没有任何中文字体**（`fc-list :lang=zh` 为 0），wkhtmltopdf 渲染时**静默丢弃全部汉字、只留 ASCII 与数字**，四个打印格式全部中招。已由 Owner 授权改 `docker-compose.yml`，给 backend / queue-long / queue-short / scheduler 挂载 `./runtime/fonts`（中文字体，`runtime/` 已 gitignore、不入仓库），重建这四个容器（命名 volume 全保留）。复验四个格式均恢复中文、页型无回归。**已生成的 6 个 PDF 也已全部重出**（附件仍是 6 个，未堆积、未动手工附件；体积 34 KB → 约 73 KB，内嵌字体所致）。详见主文档**第九之十一节**。
④ **待检证版式对齐官方受控模板**（Owner 提供生成器参考工具后校对）：结构一直正确（模板与仓库样板同构、页型同为 75×110mm），但**版式差得多**——官方正文 12pt、内容占标签高 90%、只画横线无竖线无外框；我们当时 9pt、只占 63%、全格子。已按官方重写模板，9 条横线的位置与横向范围**逐条吻合**，内容占比 63% → **85%**。**货位卡两个格式本次未比对**（参考工具没随附货位卡模板）。已生成的 6 份 PDF 再次重出。详见主文档**第九之十二节**。
⑤ **修站点 502**（重建 backend 后漏了 frontend，nginx 启动时解析一次 upstream，backend 换 IP 后仍指旧 IP，而旧 IP 被 scheduler 复用）→ `--force-recreate frontend`。详见主文档**第九之十三节**。
⑥ **修 PDF 的 ToUnicode 被写成部首码位**（Owner 报「打开还是乱码」）：汉字渲染本身是好的，但 Qt 把 10 个常用字（人入手足日月生自行、车页）的**目标码位写成部首块**，导致复制/搜索得到部首、**按 Unicode 回查字体的阅读器显示错位小字形**——这解释了「我这边看是好的、Owner 说是乱码」。已在 `doc_gen.py` 写完 PDF 前修 CMap（`_fix_pdf_tounicode`）。同时把字体换成 **OFL 的 Noto Serif SC**（原 macOS 宋体不可再分发）。详见主文档**第九之十四节**。
⑦ **提交后给落点**（Owner 报「点提交就进到原生物料移动、跳出仓库工作台」）：新增 `Stock Entry.hbos_intake_batch`（Link→Batch）作为来源标记，拍照识别建的草稿**提交后弹框**给「打开该批次取货位卡/待检证」/「继续识别下一张」。落点必须是提交之后——批次在草稿阶段就建好了，但 PDF 提交后才生成。详见主文档**第九之十五节**。
⑧ **工作台瘦身 + 原生表单加返回**（Owner 问「为什么要单独做仓库工作台、不能集成在原生库存里」）：**保留工作台但瘦身**——侧边栏由 13 条减到 6 条，只留本 App 独有的（入库拍照识别 + 四个报表），撤掉与原生库存重复的 7 条（其中三个 Stock Entry 条目**指向同一处**、只是标签不同）；并在 `Stock Entry`、`Batch` 两个原生表单上加「返回仓库工作台」出口（重写原生表单等于改核心源码，故只补回路）。契约测试 9 → 12 条，且改为**按常量断言**而非按源码文本（注释里会提到撤掉的名字）。另记录一个隐患：工作台没有 `.json`，被 `migrate` 判为 orphan 后由 `after_migrate` 重建，**当前行为正确但理由是隐式的**。详见主文档**第九之十六节**。**⚠ 「撤掉重复条目」这一步于同日被纠正，见 ⑨。**
⑨ **纠正 ⑧ 的误撤，并修「点单据就跳走」的根因**（Owner 提供浏览器截图）：截图显示进单据后**左侧边栏整条换成原生「库存」**、面包屑第一项也是「库存」——说明「返回按钮能用」不等于「不跳」，而 ⑧ 撤掉的那几条其实是**承重的**。查框架源码确认这是**两层独立机制**：① **侧边栏** ← `Workspace Sidebar` 条目的 `link_to` 命中（`sidebar.js` 的 `resolve_sidebar` 规则 1：当前侧边栏已链接该单据则保持不变）；② **面包屑** ← `Workspace Shortcut`/`Link`（`link_type=DocType`）决定的 `__workspaces`。实测 `Batch` 只被原生 `Stock` 链接（必然切走）、`Stock Entry` 归 `Manufacturing`（完全无关）。**改法**：侧边栏加回 4 条原生入口（Stock Entry **只留一条**，原来那三条是假分类）；工作台加 3 条快捷方式（Stock Entry / Batch / Warehouse）；**`Item` 有意跳过**——原生 `Home` 已有 Item 快捷方式且 `load_workspaces()` 无 `order_by`，再加会结果不确定。验证：面包屑归属已改成 `仓库工作台`；侧边栏用真实 bootinfo + `sidebar.js` 原样逻辑在 Node 里跑，四个单据全部命中「保持不变」。契约测试 12 → 13 条，新增一条**专门防止这个错误再犯**。另**不建议** Owner 提的「合并进原生库存」方案（原生工作台是 erpnext 标准文档，每次升级会被静默覆盖）。详见主文档**第九之十七节**。
⑩ **补修面包屑**（Owner 截图当场推翻 ⑨ 里的「面包屑 ✓」——那是**假通过**：我只核了数据 `__workspaces`，没核它会渲染出来）：截图显示侧边栏 ✓ 已是「仓库工作台」，但面包屑只有 `🏠 / 物料移动`。机制：`breadcrumbs.js` 的 `set_workspace_breadcrumb` 拿不到 workspace 就直接 `return`，而 `set_workspace` 分两条互斥支路，**从工作台点进来那条要求 doctype 的 module 能映射到该工作台**（`Stock Entry` 的 module 是 `Stock`、仓库工作台属 `HBOS Inventory` → 永远匹配不上），Owner 走的正是这条。**改法**：新增全局脚本 `public/js/desk_context.js`，用 `$.extend(frappe.breadcrumbs.preferred, {...})` 把四个单据指到 `HBOS Inventory` —— **这是框架的正式扩展点，ERPNext 自己在 `erpnext/public/js/conf.js` 里就是这么用的**（我先前误判为 hack，已更正）；经 `hooks.py` 的 `app_include_js` 挂载（**路径必须写成 `/assets/<app>/...` 绝对形式**，非 bundle 文件写相对路径会 404；改 `hooks.py` 后必须 `bench clear-cache`）。验证：导出真实 `get_module_wise_workspaces()`，用 `set_workspace()` 原样逻辑在 Node 里跑五种来路，从工作台进四个单据全部命中。契约测试 13 → 14 条。详见主文档**第九之十七节**「五之三」。
⑪ **把仓库日常用到的原生内容都收进工作台**（Owner 确认面包屑已对后，按清单执行）：侧边栏 **6 → 24 条**，分五组——单据 5（库存单据 / 采购入库 / 销售出库 / 物料需求 / 拣货单）、盘点与质检 2、原生库存报表 7、海滨专有报表 4、主数据 4；工作台页面同步分五组并改写导语。**有意没收**原生 Stock 那 72 条里与仓库日常无关的（序列号、分包、定价关税、安装单保修等）。`desk_context.js` 的 `preferred` 由 4 个 doctype 扩到 11 个（报表不列——`query-report` 路由的面包屑本来不带工作台前缀）。**验证这次连渲染层一起跑**：把 `breadcrumbs.js` 的 `set_workspace` + `set_workspace_breadcrumb`（含 `visible_modules` 那道静默 return 的闸门）原样搬到 Node，喂真实 bootinfo，跑 11 单据 × 2 来路——打补丁后 22/22 全中；**对照列复现了 Owner 看到的现象**。契约测试 14 → 15 条，新增「`link_count` 必须等于该组实际链接数」。详见主文档**第九之十八节**。
⑫ **修「点打开草稿就跳走」——两个独立缺陷**（Owner 报仍会跳）：① **后端容器跑的是旧代码**：gunicorn 在容器启动（10:01:59）时导入一次 `api.py` 就缓存，而我 10:55 才加的 `hbos_intake_batch` 写入 —— 所以 Owner 15:24/15:25 建的两张草稿字段为空，**上一批的落点弹框因此按设计直接返回（这就是"没生效"的真正原因）**；已 `docker compose restart backend queue-long queue-short scheduler`，并**走真实 HTTP** 验证（返回键不含已删的 `route`、草稿带上了 `hbos_intake_batch`）。② **「打开草稿」是 `<a href>`，整页刷新** → 当前侧边栏为空 → `resolve_sidebar()` 落到规则 4 掉回原生；已改为 `frappe.set_route` 的 SPA 跳转。顺带补两处硬加载漏洞：`Workspace Sidebar.app` 原本留空（过滤用严格相等，留空谁都匹配不上）已设为 `hb_inventory_app`；前端种 `localStorage["sidebar_item_map"]` 让硬加载命中规则 2。验证：四级规则原样搬到 Node，11 单据 × 3 来路——SPA 11/11、硬加载（已种）11/11、**对照 11/11 掉回 Stock/Buying（复现现象）**；契约测试 15 → 18 条。详见主文档**第九之十九节**。

方案要点：

- **门禁三项已由 Owner 确认**：① **照片不能出内网** → 排除方案 A / B（云端），走**本地部署**；③ 服务器未采购，**暂部署在这台 Mac**（Mac mini M4 / 16GB）；⑥ 使用范围**全部产品**；⑤ 准确率标准**由本轮制定**。
- **识别范围收敛**：AI 只负责 5 个字段（产品名称 / 批号 / 产品代码 / 生产日期 / 有效期至）；入库时间由系统记录，货位号扫码录入（M3-R5 已落地），数量与操作人由系统或人工提供。
- **关键技术判断**：这不是"固定版式表单识别"，而是"版式多样、需语义理解的标签识别"——实测 **94 个物料、自产/外购两套版式、中英混排、11 种单位**。故 **OCR + 规则（方案 B）维护成本随产品数增长**，多模态模型（方案 A）对版式变化更鲁棒。
- **推荐路径（已按 Owner 决定修订）**：因照片不出内网，云端方案 A/B 出局。改为在**方案 C 内部比较两条路线**：**C1**（本地量化大模型，走 MLX/Metal）与 **C2**（PaddleOCR + 规则 + **主数据约束匹配**），**两条都实现、用同一测试集对比后选定**——都在本地，成本低，后端本就可插拔。
- **核心工程价值**：**识别后端可插拔**。A / B / C 实现同一契约，切换不需重写服务，把"数据出不出内网"变成配置问题。
- **部署环境（实测）**：识别服务**原生跑在 Mac 上**，不塞进 Frappe 容器（容器是 Linux arm64，拿不到 Metal）。`host.docker.internal` **实测可达**。Docker VM 上限 7.7 GB、宿主机 16 GB、无 NVIDIA GPU。**风险已记录**：Mac 是开发机、内存偏紧，作临时验证可行，**不适合长期生产**。
- **沿用项目既有规范**：`docs/team/05_开源代码二次开发与升级规范.md` 的**优先级 5（外部服务）**，FastAPI 为既定技术栈。接口契约含幂等键、超时重试、失败日志、权限边界（**服务不直连数据库**，只收图片返结果）。
- **人工校对为强制环节**：返回每字段置信度，界面高亮低置信度，**识别结果不直接入账**，须操作人确认。照片归档到 Frappe `Attach`，**服务端不长期留存**；服务日志不记照片内容与批号。
- **脱敏不适用**：批号与代码正是识别目标，**脱敏即失去意义**，故"是否出内网"是二选一，不能靠脱敏折中。
- **物料代码全数字（Owner 补充）**：这一条极大简化了 C2——OCR 常把数字认成形近字母（`O`/`0`、`l`/`1`、`S`/`5`），既然代码只可能是数字，**无条件把字母映射回形近数字即可纠错，不需要任何主数据清单**。

**第 4 项已答复（Owner）**：④ **样本只能去仓库实地获取**。

由此产生**时序结论**：除「用真实样本测准确率」外，其余工作**都不被样本阻塞**（服务骨架、C1/C2 后端、约束校验层、Frappe 侧上传与校对界面、合成标签冒烟测试均可现在做）。

方案已补 **7.8 仓库实地取样清单**：≥50 张覆盖矩阵、同一标签多拍 4 种条件、按现场真实方式拍、命名约定、**现场同步填真值**、存储安全，以及 C2 所需的合法物料代码清单依赖（ERPNext 尚无真实 Item 主数据）。

**本批执行记录（Owner 授权「先做不被样本阻塞的部分」）**：

已交付 `services/hbos_ocr/`：FastAPI 服务骨架（`/health` + `POST /api/v1/recognize`，含幂等 / 超时 / 大小上限 / 失败日志，**日志不记照片内容与批号**）；**约束校验层**（物料代码**形近字母纠错**、批号结构提示、日期多格式解析、有效期异常检测）；后端抽象 + 3 实现（`stub` 冒烟用 / `c1_local_vlm` / `c2_ocr`），注册表**缺依赖不崩**；契约、配置、端到端冒烟脚本、约束层单测。

验证：**约束层单测 26/26 通过**、**端到端冒烟 18/18 通过**（覆盖形近纠正、`needs_review`、幂等命中、未知后端 / 空图 / 未装依赖后端均返回 400 而非 500）。**关键：均在进程内完成（FastAPI TestClient），未启动任何常驻服务。**

三处实现取舍已记录：① mlx-vlm / PaddleOCR 只收文件路径，为满足"不落盘"改为临时文件 + `finally` 立即删除；② 幂等为**进程内非持久**缓存；③ `stub` 不得用于生产。新增 `services/` 目录约定（独立服务，不放 `apps/`）。

**第二批（Frappe 侧）已交付**：`ocr_client.py`、`api.py`（`get_intake_context` / `recognize_label` / `create_intake_draft`）、Desk 页面 `hbos-photo-intake`（四步：选照片 → 识别 → 人工校对 → 生成草稿；需复核字段橙色高亮）、工作台入口。

三条边界落实：**识别不可用不伪造结果**（页面照常打开、如实提示、指路人工录入）；**不自动创建物料主数据**（未知代码拦截）；**只生成草稿不入账**（`docstatus = 0`，不绕过既有校验）。实测：服务未启动时上下文接口正常返回并提示；草稿 `MAT-STE-2026-00007` 生成正确（批次、附件齐备）；未知物料 / 分组货位 / 数量为 0 / 空批号全部拦截。识别层编排经 mock 验证。

技术发现：Desk 页面的 `.js` / `.css` 由 `Page.load_assets()` 服务端读入后随页面元数据下发，**无独立资源 URL**，无需加进 `build.json`。

**第三批（真实跨进程端到端）已通过**：Owner 授权临时启动服务，实测容器 → 宿主机连通性（`host.docker.internal:8100/health` 200）、Frappe → HTTP → FastAPI 真实识别、真实 HTTP 幂等命中、未知后端 400、草稿生成（批次与附件正确）；停止服务后降级正确（`available: false` + 原因，货位清单仍返回 216 条）。**服务已停止，无残留进程。**

**验证中发现并修复一个真实缺陷**：`_attach_photo` 原先只用 `file_url` 定位 `File`；而同内容两次上传会产生两条 `File` 共用同一 `file_url`，按 url 取有歧义、可能抢走别人已挂的附件（E2E 中复现）。已改为优先用 **File docname** 精确定位，`file_url` 降为兜底。

**安全提示**：服务绑 `0.0.0.0` 才能被容器访问，意味着同局域网可访问 8100；临时验证风险小，**正式部署须缩小暴露面**。已写入服务 README。

**第四批（真实样本准确率实测）已完成**——主文档见第九之五节。Owner 提供仓库实地样本（50 张，均在仓库外）后执行。

- **选型**：先上 **C2**（PaddleOCR 3.7.0 + PaddlePaddle 3.3.1，CPU）；C1（`mlx-vlm`，需下 ~2.5 GB 权重）**本轮未装**。
- **实测（50 张真实标签，250 个字段，`small` 档）**：批号 **100%**、物料代码 **98%**、生产日期 **94%**、有效期至 **90%**、品名 **90%**；**整体 94.4%（236/250）**、全字段正确 80%。判定口径：日期按**真值印刷粒度**比对。
  - ⚠ **2026-09-21 Owner 核对后更正口径**：**这一组数字不能读成「汉字识别准确率」**。5 个字段里 **4 个是数字**（批号/代码/两个日期），只有「品名」是汉字——所以 94.4% **主要衡量的是数字**。标签上大量汉字（公司名、生产车间、储存条件、操作人、注意事项）**从未进入该指标**，而这些恰恰**错得最多**（实测：「操作人/日期」只读到「作」、`六车间B线车间` 读成「过果线」、英文公司名读错、手写人名日期读错）。数字的高分还被**多处重复印刷**撑高（读对任一遍即记命中）。**换 medium 档同一张图小字一样错**，瓶颈是**小字成像质量**而非模型。详见 R6 主文档第九之五节的⚠小节。
- **分档实测（2026-09-21 补测）**：三档 `tiny`/`small`/`medium` 共用同一批 50 张样本、同一套口径，用归档识别原文测，**未重跑 OCR**。
  - **大字**（5 个结构化字段）全字段：`tiny` 72% / `small` **82%** / `medium` 86%。
  - **小字**（16 个模板恒定串 × 50 张 = 800 次）整串命中：`tiny` 560/800 = 70.0% / `small` **668/800 = 83.5%** / `medium` 682/800 = 85.2%。
  - **均值掩盖短板**（`small` 档）：执行标准 50/50，但**运输注意事项整句仅 25/50**、`【贮藏】：` 34/50、公司名(英) 35/50——**串越长、字越小，命中越低**。
  - **换 `medium` 不划算**：总量只多 1.7 个点，耗时 8 s → 35 s，**每提 1 个点付 4 倍时间**，维持 `small`。
  - **手写档给不出准确率**：无真值来源，标签内容逐张不同；人工转写在可获分辨率下同样辨认不出。只如实记录可观测事实——`操作人/日期` 标签后为空 **34/50**、`复核人/日期` 20/50、两行皆空 12/50、**姓名 50 张无一读出**；读到的日期多为相邻印刷字段串入，无真值无法区分。**结论：手写只能靠人工，不计入 OCR 成绩。** 详见 R6 主文档第九之五·二节。
- **品名抽取规则修复（2026-09-21）**——Owner 报「识别汉字的正确率太低」（例：品名读成「名」、`美罗培南` 读成 `美罗第南`）后逐张核对。**先分清两件事**：原始识别读错字是**模型上限、改规则救不了**（但标签上品名印 2~3 遍，锚定规则取到的是读对的那一遍，实测该样本最终品名是**对的**）；**抽取规则自己造出来的错能修，而且确实错了**。查出三个真缺陷：
  - ① **值里含 ASCII 就把整条丢掉**——真值 `美罗培南 (B)`、OCR 读出 `美罗培南（B）`，因含字母 `B` 被判无效，**把读对的答案扔了**；
  - ② **标签与值被切成两行时取不到**——`1.txt` 是「`品`」「`名：`」「`美罗培南`」三个独立的框，旧正则要求冒号后至少一字符，这种标签**根本不被识别成标签**；
  - ③ **频次法没有长度下限**——标签上没读到品名时，它从残渣里挑 2~5 字碎片交差（`避免硫碰。`、`存新件`、`合证`），**把「没读到」谎报成「读到了」**。③ 最有害：前两条只是没取到，③ 是**编一个答案**。
  - **修法**：① 改看汉字占比 ≥50%（容忍「（B）」）；② 值允许为空 + 往后回看最多 3 行、**撞上带冒号的行就停**；③ 频次法加汉字长度下限 4，**宁返回 None 也不给错的**（主数据那层会补上）。
  - **效果**（`small` 档）：品名 90% → **92%**，**错答 4 → 0**（3 处转为诚实的「空」，由 `_enrich_from_master` 用物料主数据补上）。单测 89 → **93 条全通过**。对 `tiny`/`medium` 无帮助——那两档是真读错字（`美罗信网混粉`/`携件人中期`/`美罗培南湿粉`），再次印证**瓶颈在成像、不在规则**。详见 R6 主文档第九之五·三节。
- **发现并修复三个真实缺陷**：① **只到月的日期被整条丢弃**（实测 39/50 张标签的有效期只印到月，原校验层直接返回 None → 三分之二效期会丢），已改为补**当月最后一天** + 明确提示；② **签核日期顶掉生产日期**（操作人/复核人日期混入"取最早作生产日期"判断），已排除签核行；③ **C2 后端按 2.x 写的，在 3.x 上完全失效**，已按 3.x 重写。
- **剩余 10 处未命中已逐张核对识别原文**：**8 处是 OCR 读错/漏读**（能力上限），2 处规则误配（已修）。结论：继续提高只能换更强模型，或接受现状 + 人工校对。
- **性能实测**：原图 **约 35 s/张**；**不可用降分辨率提速**（有效期是小字，降到 2000 px 会读错）。对仓库现场偏慢，选型须正视。
- **识别范围**：**只做自产**。外购物料到货时已有现成的待检证与货位卡，**不经过本识别流程**，故外购标签无需测试（50 张全自产是符合预期的）。
- **样本的一处局限**：**「拍法」列全空**（测不出"理想 vs 现实"的落差）。
- **单测**：约束层 33 条 + C2 抽取规则 37 条，**共 70 条全通过**。
- **数据安全**：真实照片、真值表、比对结果**全部在仓库外**（`~/Documents/M3R6样本/`），未提交、未入库；仓库内脚本与单测**只含方法与虚构数据**。

**第五批（入库后自动生成货位卡与待检证）已交付并验证**：新建 `hbos_inventory/doc_gen.py`，挂 `Stock Entry.on_submit`——**入库单提交后**按批次自动生成「待检证(75×110mm) + 货位卡(A4)」**合并 PDF**，挂到 `Batch` 附件；`Batch` 表单加「重新生成」按钮。

- **为什么挂提交后**：货位卡的货位明细/数量/入库日期/流水表都取自真实库存流水，草稿阶段还不存在；且 Frappe 的 `compose()` 先跑控制器、再跑钩子，故 ERPNext 建完 SLE 才轮到本模块。
- **失败不阻断入库**：`on_submit` 抛错会回滚整个提交，故整段吞异常、记 `Error Log`、界面如实提示可手动补生成。
- **实测（TEST 数据，全通过）**：2 批次 **1.55s**；同一批次拆 3 行 → 只出 1 张卡；重复生成不堆附件；`Material Transfer` 不误触发；**渲染失败时提交仍成功**；自产/外购分流正确。
- **顺带修复 M3-R4/R5 的纸型缺陷（当时未发现）**：三个打印格式与货位二维码**手动点打印时全都按 A4 出**（`@page size` 被 wkhtmltopdf 忽略），且 Frappe 打印框架注入的 `.print-format { min-height: 11.69in }` 会让小标签**溢出成多页**。已修——纸型改声明在 `.print-format` 上。修复后待检证 **1 页 75×110mm**、货位卡 **1 页 A4 无回归**。**货位二维码同样已修**（`hbos_bin_qr_svg` 带 `size_mm`，尺寸写进 SVG 属性；去掉冗余 URL 行）——两个打印格式与二维码现在**手动打印纸型全部正确**。**该批中断于二维码验证之前**，收尾见下。
- **操作坑（已记录）**：改 `hooks.py` 后**必须清缓存**，新钩子才生效（首次跑验证时钩子完全没触发）。

**第六批（收尾修复 + 物料建档守卫）**：把第五批的中断处补完，并修掉一处会误导读数的守卫。

- **二维码标签收尾+全量验证**：确认改动已随 `bench migrate` 落库（库里 `modified` 与 app 文件一致）；**手动打印路径全量回归 224 个货位 / 库位**——全部 **1 页 60×40mm**，渲染出的 SVG 带 `width="20mm" height="20mm"`；另三个格式同期回归 **待检证 1 页 75×110mm、自产/外购货位卡各 1 页 A4**，无回归。**这四项验的都是「手动点打印」那条路**（不注入覆盖 CSS，纸型完全由模板自己声明决定），与自动生成那条路（`doc_gen.py` 显式传参）是两条不同的路。验证方式：取 HTML → `get_pdf()` → 用 `pypdf` 读每页 `mediabox` 的**实际物理尺寸**，不是看模板里写了什么。
- **物料建档守卫**：`create_intake_draft` 原来只查 `frappe.db.exists("Item", ...)`——**不够**：物料存在但没勾批次管理时，会一路走到 `_ensure_batch` 才炸在 ERPNext 的 `Batch.validate()` 上，报英文 `The selected item cannot have Batch`，操作员看不出该改哪个字段。已改为 `_require_item_ready()`，一次查清 **未停用 / `is_stock_item` / `has_batch_no`** 三个开关，缺什么说什么。**仍不自动创建物料主数据**（第八节边界不变）。
- **建档需要什么**：原生必填只有「代码 / 名称 / 物料组 / 计量单位」四项，但走通本流程还需 `is_stock_item`、**`has_batch_no`**、海滨分类（`item_group` + `hbos_product_kind`）、`hbos_shelf_life_type` 与期限、`hbos_storage_condition`（缺了**待检证的储存条件会印成空白**）、`hbos_workshop`。完整清单见 R6 主文档**第九之七节**。
- **未做**：未替 Owner 修改任何真实物料的主数据（勾 `has_batch_no` 等属业务数据变更，须 Owner 授权）。

**第七批（按 Owner 提供的样本批量建档）**：Owner 授权后，扫描 `待检证/`、`自产/`、`新版货位卡外购/` 三个目录共 **312 个文件**（跳过 34 个 Word 锁文件 / 快捷方式），抽出 **128 个不重复物料并全部建档**（另有 1 条已存在，跳过）。完整记录见 R6 主文档**第九之八节**。

- **字段来源**：代码与品名取「物料代码」「品名」单元格；分类按**代码前四位**（M3-R2 6.1 的 Owner 口径）；单位取「数量/件数」单元格（**不是**包装规格——`30%过氧化氢` 规格 500ml/瓶 但实际按**瓶**存）；生产车间 31 个、储存条件 28 个来自样本；`is_stock_item` / `has_batch_no` 一律置 1。
- **抽不准的两类已如实处理**：① 待检证正文无表格边界时品名会被切碎（`CN1）` 这类），**6 个品名人工订正**，其余 122 个是单元格原文；② 待检证上的 `20251201` 这类**日期**曾被误当代码抽出 12 个假物料，已按 SAP 口径用 `^1\d{7}$` 过滤，挡下的日期逐条留痕、**没有静默丢弃**。
- **顺带修掉 M3-R2 一处缺陷**：海滨分类树 5 个节点当初全建成 `is_group = 1`（分组节点），**物料根本放不进去**，树形同虚设（已有那条物料用的是原生 `Products`，绕开了所以一直没暴露）。已按 Owner 2026-09-18 的选定改为叶子节点，并给 `sync_item_groups` 补**纠偏逻辑**（`sync_*` 一律「存在即跳过」，光改常量对库里已有节点无效）。
- **仍未建档**：**37 个文件**上的 **19 个物料**（多为培养基与部分洁净鞋 / 滤芯），其「物料代码」栏印的是 `/`——**须先由 SAP 管理员分配 8 位代码**，本平台做不了。按大类分布见 R6 主文档第九之八节（**具体品名属真实业务数据，仓库是 PUBLIC，不入库**）。
- **仍为空**：`hbos_shelf_life_type`（复检期 / 有效期）与 `hbos_shelf_life_months`——样本上那两个勾选框**全部是 `□`**（140 处无一勾选），是空白模板，**须质量 / 仓库提供口径**。
- **数据安全**：真实代码与品名**只在数据库**，抽取产物全部在 `/tmp`，已 `grep` 全仓库确认无泄漏。
- **未做**：未勾现有那条已建档物料的「启用批号管理」（它仍 `has_batch_no = 0`，入库到它仍会被拦）、未把它从原生 `Products` 挪到「中间体」、未替 SAP 分配代码。

**第八批（补充信息手工录入）**：Owner 要求「拍照后获取信息生成文件，**没获取到的信息可以手工加入**」。OCR 只读 5 个字段，而待检证 / 货位卡要印的远不止这些，缺的那些此前**在页面上无从录入**。完整记录见 R6 主文档**第九之九节**。

- **已交付**：`Batch.hbos_supplier_name` 新字段（供货单位用自由文本，因标准 `Batch.supplier` 是**只读 Supplier 链接**，塞自由文本会让批次日后保存不了）；`print_utils.hbos_supplier_name` 优先取新字段；`create_intake_draft` 增 7 个可选参数 + `_fill_item_master_gaps` / `_parse_packaging` / `_replace_packaging`；**校对区改为「标签上要印的信息全部列在一处」**（识别到的 + 手工补的 + 包装构成），并把 **OCR 识别原文按行拆成可编辑行**供逐字校对——校对后的文本存进 `Batch.hbos_label_text`（照片是原始凭证、**不可搜**；这段是可检索的转录件，**不参与打印**）。
- **两层落地**：**物料级**（储存条件 / 生产车间 / 效期类型）写回 `Item` 主数据但**仅补空**——已有值绝不覆盖；**批次级**写进本批次。
- **权限是有意绕开默认矩阵的**：实测 `Item` 只有 `Item Manager` 有写权限，`Stock Manager`/`Stock User`/连 `System Manager` 都只有读。若用 `frappe.has_permission("Item","write")`，页面允许的三个角色**会被自己的权限门全挡死**。故沿用页面既有 `_require_permission()` + `ignore_permissions`，风险由「仅补空」+「Comment 留痕」承担。
- **验证（全通过）**：仅补空（已有值不被覆盖 / 空值写入并留痕）、**并发保先到者**、包装构成**替换式不翻倍**、自产与外购货位卡及待检证逐字段印出、**回归**（不传新参数行为不变）、**Stock User 身份能补**（此时 `has_permission('Item','write')` 为 False，正是要绕开的门）、页面资源加载。OCR 服务 83 条单测无回归。
- **顺带修掉一个误导性控件**：页面上那个可编辑的「产品名称」**从未传给后端**，改了不生效（打印取 `Item.item_name`，`Batch.item_name` 又是 `fetch_from` 快照）。已改为只读对照展示。**另发现 `Item.item_name` 非必填，为空时两个货位卡的品名会印成空白。**
- **未做**：**未在真实浏览器里点过该界面**（本 install 的预览只支持 attach URL 形式，当前不可用——界面是**经后端验证**的，未见浏览器渲染），建议 Owner 亲自走一遍。

M3-R6 未做（累计）：**未装 C1**、未按第七节标准正式验收与定选型、未做批量拍照、**未覆盖 `Purchase Receipt`**（采购收货是另一个 DocType）、未做批量打印入口、未做「建档引导页」、未做物料导入模板、**未在真实浏览器验证拍照识别页新界面**、未修改核心源码、未接飞书写入、未执行 `docker compose down -v`、未删除 volume、未重建 site。

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

后续变更（M3-R0 记录）：

- 上述记录描述的是 M0-REMOTE 当时的真实状态，保留不改。
- 当前工作副本的 `origin` 已变为 `https://github.com/zjl327707743/HBOS-Platform.git`（**PUBLIC** 公开协作仓库）。`HBOS.git`（PRIVATE）现作为内部归档库存在，当前未绑定。
- 因此**本仓库的提交会进入公开仓库**，`PUBLIC_REPOSITORY_SCOPE.md` 的公开范围声明对每轮提交都有约束力。

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
