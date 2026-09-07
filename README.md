# 新乡海滨智能运营管理平台

新乡海滨智能运营管理平台面向企业级智能运营管理，长期目标是在 Frappe/ERPNext 开源底座上建设海滨自定义业务 App、外部 AI/视频/算法服务、Vue/React 驾驶舱、飞书集成与 Docker 部署体系。

准确架构叫法：Frappe/ERPNext 开源底座 + Frappe 多 App 模块化架构 + 外部独立服务扩展。

## 当前阶段

当前 M0 已完成并封板。M1 产品交付仍在 M1-FIX 功能补漏中，尚未完成；M1-FIX-B5 为 REVIEWING（等待 Owner 和 Claude 审查），M1-FIX-B3 / B4 不 closeout，M1-FIX-C/D/E 未启动。M2-LIMS（实验室信息管理系统板块）已按 Owner 授权启动：M2-R1 至 M2-R4（环境与骨架、主数据与判定引擎、检验流程闭环、COA 与报表）已 COMPLETED，M2-R5（验证收口）为 REVIEWING；M2-R6（Vue 前端原型与开发流程）已交付交互式 HTML 原型与开发流程文档，进入 REVIEWING，未创建 Vue 工程。M1-FIX 为并行未决事项，不阻塞 M2-LIMS。
M2-R6A（样品登记动态表单设计）已交付下拉决策条 + 9 类样品类型完整表单切换方案，进入 REVIEWING，等待 Owner 审查。
M2-R6B（检验结果台账双模式设计）已交付明细台账 + 样品表（每样品种类一表）双模式方案，Owner 已确认原型与交互，进入 REVIEWING，设计文档待审查。
M2-R6C（检验结果台账 Vue 复刻与生产部署）已将双模式复刻进 Vue 并上线生产，Owner 已确认测试路径。
M2-R6D（合规审计日志）已交付：后端 HBOS Audit Log DocType（write-once 防篡改）+ 全量捕获 + 查询 API + 业务埋点，前端合规组新增合规审计日志入口与页面；已上线生产，Owner 已确认测试路径；并修复生产部署新旧 hash 错配致个别页面 404。
M2-R6C（检验结果台账 Vue 复刻与生产部署）双模式已复刻进 Vue 并上线生产，Owner 已确认测试路径效果，DEPLOYED。
M2-R7（留样管理板块开发方案）REVIEWING rev4：Owner 已授权留样板块纳入 `hb_lims_app` 范围，方案文档 `docs/milestones/M2_R7_留样管理板块开发方案.md` 经三轮审查修订（rev1 8 项 → rev2 → rev3 9 项 → rev4 9 项），待复审；未创建 DocType、未写业务代码；R7A~D 子轮须方案审查通过后逐轮启动。

当前真实进度以以下文件为准：

- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/milestones/README.md`
- `docs/milestones/M0.md`

当前状态摘要：

- M0-R1 工程骨架与 AI 上下文治理已完成
- M0-R2 环境设计、里程碑治理与 Skill 路由规范已完成
- M0-R2E 公共入口文件收尾规则补强已完成
- M0-R3A Frappe / Docker 最小环境落地已完成，Docker 镜像已拉取，容器已启动，测试 site 已初始化，Frappe Desk 登录页已验证
- M0-R3B Frappe HR / HRMS 安装前评估已完成并通过 Codex 审查
- M0-R3C Frappe HR / HRMS 安装验证已完成，HRMS 已安装到本地 `frontend` site，基础 HR 模块可访问
- M0-R3C-FIX HRMS 前端资源与 Roster 白屏诊断修复已完成，Frappe HR 图标、基础 HR 模块和 Roster 页面已验证可访问
- M0-R3D HRMS 能力盘点与 M1 考勤一期边界设计已完成
- M0-R3E HRMS 环境可复现性收口已完成，并已通过 Codex 审查
- M0 整体已完成并封板
- M0-REMOTE GitHub Private remote 创建、`origin` 绑定和 `main` 首次 push 已完成
- M1-R0 平台入口、账号体系、角色权限、飞书 SSO 可行性、中文化 / 本地化诊断方案已完成，并已通过 Codex 独立审查
- M1-R1 HRMS 原生考勤对象模型验证记录已完成，并已通过 Codex 独立审查，状态为 COMPLETED
- M1-R2 HRMS 原生考勤配置试运行方案已完成文档交付，并已通过 Codex 独立审查，状态为 COMPLETED
- M1-R3 HRMS 原生考勤最小测试数据试运行已执行并通过 Codex 审查，最终状态为 BLOCKED；本轮未完成 14 场景闭环
- M1-R3A 运行态阻断诊断与 TEST 数据隔离 / 清理方案已通过 Codex 审查并收口为 COMPLETED
- M1-R3B 运行态最小修复方案已通过 Codex 审查并收口为 COMPLETED；本轮未执行修复、未清理 TEST 数据、未继续试运行
- M1-R3B-FIX 已通过 Codex 审查并收口为 COMPLETED；该轮只执行 `docker compose up -d redis-cache redis-queue`，Redis / worker / scheduler / bench doctor / login 已恢复或改善
- M1-R3C HRMS 原生考勤最小试运行复测已通过 Codex 审查并收口为 COMPLETED，结论为 PARTIAL / GAP_IDENTIFIED；14 个场景中 8 个通过，6 个为 GAP / PARTIAL；Attendance 可由 HRMS 原生生成，但迟到 / 早退未置位、缺卡 / 缺勤口径、请假 Leave Allocation、加班业务口径仍需 M1-R3D 诊断
- M1-R3D HRMS 原生考勤异常口径与配置 Gap 诊断已通过 Codex 审查并收口为 COMPLETED；结论为 Gap 四类分类、均不需要立即创建 `hb_attendance_app`
- M1-R3E 配置复核清单与业务口径确认表已通过 Codex 审查并收口为 COMPLETED；配置清单已覆盖 8 类配置复核项，业务口径表已确认 8/10 项阻塞 M1-R4
- M1-R3F 业务口径确认包已通过 Codex 审查并收口为 COMPLETED；9 项确认主题中 7 项必须确认，2 项可先按默认值推进
- M1-REQ-DESIGN-DRAFT 已通过 Codex 审查并收口为 COMPLETED；四份设计文档交付完成
- M1-R4 Demo 技术方案与实施路线拆分已通过 Codex 审查并收口为 COMPLETED
- M1-R5 HRMS 配置基线、考勤工作台与月度汇总 Demo 已通过 Codex 审查并收口为 COMPLETED；本轮未创建 App / DocType，未写入站点数据库，未启动 R6/R7
- M1-R6A Excel 导入与异常流程落地方案 / Gate 判定已通过 Codex 审查并收口为 COMPLETED
- M1-R6B 脱敏打卡流水导入最小实现已通过 Codex 审查并收口为 COMPLETED；本轮未提交 Excel / CSV，未创建 App / DocType，未启动 R6C/R7
- M1-R6C 异常识别与异常说明流程最小实现当前为 COMPLETED；已通过 Codex 审查并 closeout
- M1-FIX-B 已按 Owner 授权创建轻量 `hb_attendance_app`、导入日志和 `海滨考勤工作台`，并使用 Owner 本地真实 Excel 完成导入闭环验证；M1-FIX-B-FIX 已补齐 `导入考勤机导出表` 浏览器入口、中文 `打卡流水` / `考勤结果` 报表、重复导入可读日志和默认白班/行政班 08:30-17:30；M1-FIX-B4 已收敛桌面入口、Workspace Sidebar、导入页归属和 HBOS / HRMS 入口口径；M1-FIX-B5 已核查真实 Employee / Checkin / Attendance / 月度暂存链路，并收敛 HBOS 报表和 HRMS 技术核查入口；真实 Excel、真实员工清单和导入产物不提交 Git
- M2-R1 已按 Owner 授权创建 `hb_lims_app`（实验室信息管理系统板块骨架），已安装到本地 `frontend` site，after_migrate 幂等同步 3 个 LIMS 角色、`海滨LIMS工作台` Workspace、Sidebar 与桌面图标，离线契约测试 8/8 全绿；本轮未创建 DocType / 业务方法（主数据与检验流程为 M2-R2 至 M2-R5）
- M2-R2 主数据与判定引擎、M2-R3 检验流程闭环、M2-R4 COA 与报表已 COMPLETED；M2-R5 验证收口为 REVIEWING（全量演练 19/19、11 项验收、离线测试 109/109）
- M2-R6 Vue 前端原型与开发流程已交付（`docs/frontend/M2_LIMS_Vue前端原型.html` + `docs/frontend/M2_LIMS_Vue前端开发流程.md`），REVIEWING 等待 Owner 审查；未创建 Vue 工程、未接真实 API

M0 阶段用于约束后续规划、执行、审查与验收。当前已完成 Frappe / ERPNext / Docker 最小环境启动验证、Frappe HR / HRMS 安装验证、HRMS 前端资源修复、M1 考勤一期边界设计、HRMS 环境可复现性收口、GitHub Private remote 首次同步、M1-R0 规划诊断收口、M1-R1 对象模型验证记录、M1-R2 配置试运行方案设计、M1-R3 局部试运行记录、M1-R3A 阻断诊断方案、M1-R3B 运行态最小修复方案、M1-R3B-FIX 运行态最小修复执行记录、M1-R3C 原生考勤最小试运行复测记录、M1-R3D 异常口径与 Gap 诊断、M1-R3E 配置复核与业务口径确认表、M1-R3F 业务口径确认包、M1 需求设计四份文档、M1-R4 Demo 技术方案与实施路线拆分、M1-R5 HRMS 配置基线、考勤工作台与月度汇总 Demo、M1-R6A Gate 判定和 M1-R6B 脱敏打卡流水导入最小验证；M1 仍未进入完整考勤业务开发。

## 仓库定位

当前仓库用于承载 M0 工程启动文档、AI 协作规则、里程碑状态、阅读指南、计划文档、架构决策记录、最小 Docker 环境配置和经 Owner 授权创建的自定义 Frappe App。

当前已包含 `apps/hb_attendance_app`（考勤导入入口、导入日志和 M1-FIX 必需扩展，不代表启动大而全 HR App）与 `apps/hb_lims_app`（M2-LIMS 实验室信息管理系统板块，MVP 覆盖样品管理、质量标准、检验流程与 COA 报告，演示数据一律 `TEST-HBOS-M2-*` 前缀）。

## 主技术栈

- Frappe Framework
- ERPNext
- Frappe HR
- Python
- JavaScript
- MariaDB/MySQL 兼容体系
- Redis
- Docker
- Docker Compose
- Vue/React
- ECharts
- FastAPI

## 长期仓库规划

长期建议按职责拆分仓库，当前仅记录规划，不在未批准轮次创建这些仓库：

- `haibin-hbos-infra`：基础设施、部署、环境编排与运维脚本
- `hb_core_app`：海滨核心主数据、权限、组织与平台扩展
- `hb_attendance_app`：考勤业务扩展
- `hb_feishu_app`：飞书集成扩展
- `hb_production_app`：生产运营扩展
- `hb_quality_app`：质量管理扩展
- `hb_safety_app`：安全管理扩展
- `hb_ai_ops_app`：AI 运营、视频、算法服务对接扩展
- `hbos-dashboard-web`：Vue/React 驾驶舱与大屏前端

## 当前禁止事项

当前 M1-FIX 仍处于功能补漏阶段，M2-LIMS 已按 Owner 授权启动。继续禁止：

- 未经 Owner 明确授权，不创建新的自定义 Frappe App（已授权：`hb_attendance_app`、`hb_lims_app`）
- 不创建 `hb_core_app`、`hb_feishu_app`
- 不把 `hb_attendance_app` 扩大为大而全 HR App
- 不把 `hb_lims_app` 扩大为 M2-LIMS MVP 之外的模块（仪器集成、稳定性、环测、微生物、试剂、OOS 调查等另行规划）。**例外（已授权）**：留样板块 M2-R7 已按 Owner 2026-09-04 授权纳入范围，R7A~D 子轮须在方案审查通过后逐轮启动
- 不把 HRMS 安装验证等同于考勤业务开发完成
- 不提交真实 `.env` 或真实密钥
- 不提交备份文件、数据库、Docker volume 或运行时数据
- 不开发业务
- 不接飞书真实写入
- 不在原型审查通过前实现前端驾驶舱
- 不浏览或搬运大量 Obsidian 长文
- 不执行 `docker compose down -v`
- 不删除 volume
- 不重建 `frontend` site

**独立前端开发规则**：凡涉及独立前端、驾驶舱、AI 工作台、复杂交互页面，必须先完成原型设计/视觉方案，经 Owner 人工审查通过后再进行前端复刻开发，最后接入真实页面功能和数据。详见 `docs/frontend/FRONTEND_IMPLEMENTATION_GUIDE.md`。

后续路线只记录，不代表已启动：

1. M1-R3C 已通过 Codex 审查并收口，试运行完成但业务闭环未完成。
2. M1-R3D 已通过 Codex 审查并收口，Gap 已四类分类，均不需要立即创建 App。
3. M1-R3E 已通过 Codex 审查并收口，配置复核清单与业务口径确认表已交付。
4. M1-R3F 已通过 Codex 审查并收口，业务口径确认包已交付。
5. M1-REQ-DESIGN-DRAFT 已通过 Codex 审查并收口，需求设计四份文档全部完成。
6. M1-R4 已通过 Codex 审查并收口为 COMPLETED；M1-R4 定位为 Demo 技术方案与实施路线拆分，后续 R5/R6/R7 按递进拆分。
7. M1-R5 已通过 Codex 审查并收口为 COMPLETED；本轮定位为 HRMS 配置基线、考勤工作台与月度汇总 Demo，未启动 R6/R7。
8. M1-R6A 已通过 Codex 审查并收口为 COMPLETED；本轮定位为 Excel 导入与异常流程落地方案 / Gate 判定，已 closeout。
9. M1-R6B 已通过 Codex 审查并收口为 COMPLETED；M1-R6C 为 COMPLETED。M1-R7 已通过 Codex 审查并 closeout 为 COMPLETED。
10. M1-FIX-B 已完成 Excel 导入与真实本地数据闭环实现，M1-FIX-B-FIX 已补齐浏览器导入与中文体验修复，M1-FIX-B2 为 COMPLETED，M1-FIX-B3 为 REVIEWING / Owner UI 验收未通过，M1-FIX-B4 为 REVIEWING / Claude PASS 但数据链路验收发现后续问题，M1-FIX-B5 为 REVIEWING。
11. M2-LIMS 已启动：M2-R1 至 M2-R4（环境与骨架、主数据与判定引擎、检验流程闭环、COA 与报表）COMPLETED；M2-R5 验证收口 REVIEWING；M2-R6 Vue 前端原型与开发流程 REVIEWING（待 Owner 审查，审查通过后才进入 Vue 工程初始化与页面复刻）。
M2-R6A 样品登记动态表单设计 REVIEWING（随 M2-R6 并行审查）。
M2-R6B 检验结果台账双模式设计 REVIEWING（Owner 已确认原型与交互，设计文档待审查）。
M2-R6C 检验结果台账 Vue 复刻与生产部署 DEPLOYED（双模式已上线生产）。
M2-R7 留样管理板块开发方案 REVIEWING rev6：Owner 已授权留样板块纳入 `hb_lims_app` 范围，方案经五轮审查修订（rev6 终审完成 1 P1 + 3 P2 修订与 P3 六项分轮实现注意事项）；Owner 2026-09-07 已确认角色方案 B+SoD 与分支策略 b（m2-r6 为 M2 延伸工作线），余 6 项待确认按节拍推进；未创建 DocType、未写业务代码，R7A~D 子轮须方案审查通过后逐轮启动，R7A 启动待 Owner 指令。

## AI 协作方式

- ChatGPT：负责规划、拆解、上下文整理与方案边界确认
- Claude：负责按计划执行文档或代码变更
- Codex：负责工程审查、边界检查、验证与交付复核
- 用户：负责最终验收、取舍确认与里程碑放行

每轮任务开始前，AI 必须说明本轮读取了哪些文档。默认只读 `CLAUDE.md`、`AGENTS.md`、`docs/AI_CONTEXT.md`、`docs/PROJECT_STATUS.md`、`docs/CURRENT_MILESTONE.md`，禁止默认递归读取整个 `docs/`。
