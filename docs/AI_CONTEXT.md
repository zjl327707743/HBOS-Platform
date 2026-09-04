# AI Context

项目名称：新乡海滨智能运营管理平台。

## 架构定案

准确叫法：Frappe/ERPNext 开源底座 + Frappe 多 App 模块化架构 + 外部独立服务扩展。

长期架构包括：

- Frappe/ERPNext 开源底座
- 海滨自定义 Frappe App
- 外部 AI/视频/算法服务
- Vue/React 驾驶舱
- 飞书集成
- Docker 部署

主技术栈：Frappe Framework、ERPNext、Frappe HR、Python、JavaScript、MariaDB/MySQL 兼容体系、Redis、Docker、Docker Compose、Vue/React、ECharts、FastAPI。

## 当前上下文

当前阶段：M0 工程启动与上下文治理已完成并封板；M1 产品交付仍在 M1-FIX 功能补漏中，尚未完成（M1-FIX-B3 为 REVIEWING / Owner UI 验收未通过；M1-FIX-B4 为 REVIEWING / Claude PASS，但 Owner 数据链路验收发现后续问题；M1-FIX-B5 为 REVIEWING）；M2-LIMS（实验室信息管理系统板块）已按 Owner 授权启动。

当前目标：M2-R1 至 M2-R4 已 COMPLETED，M2-R5（验证收口）为 REVIEWING；M2-R6（Vue 前端原型与开发流程）已交付交互式 HTML 原型与开发流程文档，进入 REVIEWING，等待 Owner 审查。M1-FIX-B3 / B4 / B5 为并行未决事项，不 closeout，不阻塞 M2-LIMS。M1-FIX-C/D/E 未启动。
M2-R6A（样品登记动态表单设计）随 M2-R6 并行 REVIEWING，等待 Owner 审查。
M2-R6B（检验结果台账双模式设计）REVIEWING，Owner 已确认原型与交互（明细台账 + 样品表每样品种类一表），设计文档待审查。
M2-R6C（检验结果台账 Vue 复刻与生产部署）DEPLOYED，双模式已复刻进 Vue 并上线生产，Owner 已确认测试路径。

当前已在用户授权范围内安装 HRMS，并完成 Frappe HR 图标、基础 HR 模块和 Roster 页面的前端资源修复验证。M0-R3E HRMS 环境可复现性收口已完成并通过 Codex 审查，M0 整体状态为 COMPLETED。

M0-REMOTE 已完成 GitHub Private remote 创建、`origin` 绑定和 `main` 首次 push。M1-R0 已完成方案和诊断并通过 Codex 独立审查；M1-R1 已完成只读对象模型验证记录，并已通过 Codex 独立审查，状态为 COMPLETED。M1-R2 已完成配置试运行方案设计，并已通过 Codex 独立审查，状态为 COMPLETED。M1-R3 已创建部分 `TEST-HBOS-M1R3-` 虚构测试数据；Codex 审查 PASS 后，M1-R3 最终状态收口为 BLOCKED。M1-R3A 已通过 Codex 审查并收口为 COMPLETED。M1-R3B 已通过 Codex 审查并收口为 COMPLETED。M1-R3B-FIX 已通过 Codex 审查并收口为 COMPLETED。M1-R3C 已新增 `TEST-HBOS-M1R3C-*` 虚构 TEST 数据；M1-R3C 已通过 Codex 审查并收口为 COMPLETED，结论为 PARTIAL / GAP_IDENTIFIED。M1-R3D 已通过 Codex 审查并收口为 COMPLETED。M1-R3E 已通过 Codex 审查并收口为 COMPLETED。M1-R3F 已通过 Codex 审查并收口为 COMPLETED。M1-REQ-DESIGN-DRAFT 为 COMPLETED。M1-R4 为 COMPLETED，已通过 Codex 审查并收口。M1-R5 为 COMPLETED，已通过 Codex 审查并收口。M1-R6A 已通过 Codex 审查并收口为 COMPLETED。M1-R6B 为 COMPLETED。M1-R6C 为 COMPLETED（已通过 Codex 审查并 closeout）。M1-R7 为 COMPLETED（已通过 Codex 审查并 closeout）。M1 历史 closeout 已完成，但 Owner UI 验收发现产品功能缺口，因此当前 M1 产品交付仍处于 M1-FIX IN_PROGRESS。M1-FIX-B 已创建轻量 `hb_attendance_app`、导入日志和 `海滨考勤工作台`，并使用 Owner 本地真实 Excel 完成导入闭环验证；M1-FIX-B-FIX 已补齐页面导入与中文体验；M1-FIX-B4 已收敛运行态入口主线；M1-FIX-B5 已核查真实 Employee / Employee Checkin / Attendance / 月度暂存数据链路，新增月度汇总暂存报表并增强 HBOS 报表过滤；真实 Excel、真实员工清单和导入产物不提交 Git。M2-LIMS 已启动：M2-R1 已创建 `hb_lims_app` 骨架（hooks / config / public logo / after_migrate 幂等同步 3 个 LIMS 角色、`海滨LIMS工作台` Workspace、Sidebar 与桌面图标），已安装到本地 `frontend` site，离线契约测试 8/8 全绿；M2-R2 至 M2-R4 已收口为 COMPLETED，M2-R5 验证收口进入 REVIEWING（全量演练 19/19、11 项验收、离线测试 109/109）。M2-R6 已交付 Vue 前端原型与开发流程（`docs/frontend/M2_LIMS_Vue前端原型.html` + `docs/frontend/M2_LIMS_Vue前端开发流程.md`），进入 REVIEWING，未创建 Vue 工程、未接真实 API。当前不接飞书真实写入，不实现 SSO；不在原型审查通过前实现前端驾驶舱。
M2-R6A 已交付样品登记动态表单设计（`docs/frontend/M2_R6A_样品登记动态表单设计.md` + 原型 `#sample` 动态表单交互），样品类型 / 检验优先级为下拉决策条、9 类整表单切换，进入 REVIEWING，未创建 Vue 工程、未接真实 API。
M2-R6B 已交付检验结果台账双模式设计
M2-R6C 已交付检验结果台账双模式 Vue 复刻：`ResultLedgerView.vue` 明细台账 + 样品表（真实 Frappe API 聚合、只读投影、superseded 链过滤），判定/状态筛选；后端 `get_result_ledger` 聚合 API + `workflow_contract` 注册，离线 114/114 全绿；生产构建部署并验证，Owner 已确认测试路径。
M2-R6D 已交付合规审计日志：后端 `HBOS Audit Log` DocType（write-once+sha1 防篡改）+ hooks doc_events 全量捕获 + `get_audit_log` 查询 + 业务埋点，前端合规组新增 合规审计日志 入口 + /audit-log + `AuditLogView.vue`；离线契约 123/123 全绿；已上线生产，Owner 已确认测试路径。另修复生产部署错配（index.html 与 assets 新旧哈希错配致个别页面 404）——root 清旧 assets 后重新部署最新干净 dist（39 资产与本地一致、全引用 200+正确 MIME），nginx 加 SPA fallback 修 /hbos-lims history 404。（`docs/frontend/M2_R6B_检验结果台账设计方案.md` + 原型 `#ledger` 双模式交互）：明细台账（受控记录视角，样品卡片 + 检验项目逐行 + 下钻抽屉签名/修订/审计）+ 样品表（每样品种类一张表、一行一个批次、首列序号、次列样品批号，左侧按类型分组可收缩下拉列表）；Owner 已确认原型与交互，进入 REVIEWING，设计文档待审查；后端 `HBOS Ledger Template` / `get_result_ledger` 落地设计待实现轮另行规划，未创建 Vue 工程、未接真实 API。
M2-R6C 已交付检验结果台账 Vue 复刻与生产部署：`ResultLedgerView.vue` 复刻双模式（明细台账 + 样品表），数据来自真实 Frappe API（HBOS Sample / Test Result / COA / Result Revision 聚合、只读投影、superseded 链过滤、修订/审计摘要）；新增判定列 + 记录状态列筛选、记录状态语义配色；`vue-tsc` 0 错误；生产构建 `npm run build:prod` 已同步至容器 `hbos-m0-r3a-frontend-1`（备份 `hbos-lims.bak-20260827a`），生产 URL `http://localhost:8080/hbos-lims/` HTTP 200 验证通过，Owner 已确认测试路径效果；本轮未新建 DocType、未改后端业务方法。

## AI 默认读取规则

默认只读以下文件：

- `CLAUDE.md`
- `AGENTS.md`
- `docs/AI_CONTEXT.md`
- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`

禁止默认递归读取整个 `docs/`。

默认不读取：

- `docs/archive`
- `docs/research`
- `docs/legacy`

每轮任务开始前，必须说明本轮读取了哪些文档。

只有任务明确涉及当前里程碑时，才读取：

- `docs/plans/m0_engineering_bootstrap.md`

只有架构决策变更时，才读取：

- `docs/adr/`

## Skill 路由

本项目通过 `docs/AI技能路由规范.md` 管理不同任务类型对应的 AI skill 使用规则。

当前已确认拥有 / 可用的 skill：

- `superpowers`
- `frontend-design`
- `lark-cli`（飞书官方 CLI 工具，不是统一总 skill）
- `lark-shared`（飞书官方共享基础 skill）
- `lark-*` 官方领域 skills（详见 `docs/AI技能路由规范.md`）

未安装 skill 只能进入候选池，不得直接调用。任何 Agent 在执行开发、审查、前端设计、集成、文档维护前，必须先根据该文件判断本轮应使用的 skill。

## 提交与文档命名

本项目后续 Git 提交描述优先使用中文。可以保留 `docs`、`fix`、`feat`、`chore` 等 conventional commit 前缀，但冒号后的描述应使用中文。

新增文档名称优先使用中文或中英混合命名。技术专有名词可以保留英文，例如 Frappe、Docker、ERPNext、FastAPI、API、Skill。

Skill 路由规范文件为：

- `docs/AI技能路由规范.md`

## 后续路线

后续路线只记录，不代表已启动：

1. M1-R5 已通过 Codex 审查并收口为 COMPLETED，已交付 HRMS 配置基线、考勤工作台入口、月度汇总 Demo 和 Excel 月报导出路径。
2. M1 历史 closeout 已完成，但产品交付仍在 M1-FIX 中，尚未完成。M1-FIX-B3 为 REVIEWING / Owner UI 验收未通过；M1-FIX-B4 为 REVIEWING / Claude PASS，但 Owner 数据链路验收发现后续问题；M1-FIX-B5 为 REVIEWING。M1-FIX 为并行未决事项。
3. M2-LIMS 已启动：M2-R1 环境与骨架、M2-R2 主数据与判定引擎、M2-R3 检验流程闭环、M2-R4 COA 与报表已 COMPLETED；M2-R5 验证收口 REVIEWING；M2-R6 Vue 前端原型与开发流程 REVIEWING（待 Owner 审查，审查通过后才进入 Vue 工程初始化）。
M2-R6A 样品登记动态表单设计 REVIEWING（随 M2-R6 并行审查）。
M2-R6B 检验结果台账双模式设计 REVIEWING（Owner 已确认原型与交互，设计文档待审查；通过后纳入 Vue 页面复刻范围，后端 `HBOS Ledger Template` / `get_result_ledger` 落地另行规划）。
M2-R6C 检验结果台账 Vue 复刻与生产部署 DEPLOYED（双模式已上线生产，Owner 已确认测试路径；后端聚合 API 落地另行规划）。

## 前端实施流程规范

独立前端（Vue/React 驾驶舱、AI 工作台、复杂交互页面）开发必须遵循"原型先行 + Owner 审查 + 复刻实现 + 功能接入"流程。详见：

- `docs/frontend/FRONTEND_IMPLEMENTATION_GUIDE.md`

核心规则：凡涉及漂亮页面、驾驶舱、AI 工作台、复杂交互页面，必须先使用 `frontend-design` skill 产出原型/视觉方案，Owner 人工审查通过后再进入前端复刻和功能接入。Frappe Desk 后台页面不要强行重做成独立前端。

## 边界提醒

不直接修改 Frappe / ERPNext / HRMS 核心源码。优先使用原生配置、角色权限、DocType、报表、导入、API 和低代码定制。自定义 App 只用于海滨特有规则，不用于重写 HRMS 已有功能。`hb_attendance_app` 已在 M1-FIX-B 经 Owner 授权创建，后续不得擅自扩大为大而全 HR App。`hb_lims_app` 已在 M2-R1 经 Owner 授权创建，MVP 范围限定样品管理、质量标准、检验流程与 COA 报告，不擅自扩大为 12 模块全量 LIMS；**留样板块（M2-R7）已按 Owner 2026-09-04 授权纳入 `hb_lims_app` 范围**（R7A~D 子轮须方案审查通过后启动），其余扩展模块仍另行规划。任何飞书真实写入必须由用户明确授权。

任何海滨自定义 App 生成、业务模型实现、真实业务数据配置、飞书真实写入、前端驾驶舱、AI 视频服务实现，以及 Docker volume 删除、site 重建或环境重构，都属于后续轮次或后续明确授权范围。
