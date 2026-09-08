# Current Milestone

## M2-LIMS：实验室信息管理系统板块（当前里程碑）

项目名称：新乡海滨智能运营管理平台。

M2-LIMS 在 HBOS 平台（Frappe/ERPNext 底座）上新增实验室信息管理系统（LIMS）板块，以《海滨药业LIMS系统开发方案》为业务口径（12 模块），参考开源 SENAITE LIMS 的功能结构（仅业务模型参考，不搬代码），自定义 Frappe App `hb_lims_app` 承载。第一版为核心闭环 MVP：样品管理 + 质量标准 + 检验流程 + COA 报告。

## 当前轮次

M2-R1（环境与骨架）：COMPLETED。`hb_lims_app` 已创建并安装到本地 `frontend` site，after_migrate 幂等同步 3 个 LIMS 角色、`海滨LIMS工作台` Workspace、Sidebar 与桌面图标，离线契约测试 8/8 全绿。主文档 `docs/milestones/M2_R1_环境与骨架.md`。

M2-R2（主数据与判定引擎）：COMPLETED。6 个主数据 DocType 已同步到 frontend site（规格命名 `format:{spec_code}-V{version}` 支持多版本）、`result_contract.py` 判定引擎、规格生效校验；离线测试 40/40 全绿；`TEST-HBOS-M2-*` 虚构主数据验证通过（含多版本/重复拒绝/限度校验/生效查询）。主文档 `docs/milestones/M2_R2_主数据与判定引擎.md`。

M2-R3（检验流程闭环）：COMPLETED。5 个事务 DocType（Sample+Item/Task/Test Result/Result Revision）、状态机、业务方法全链、待检任务看板报表已交付；离线测试 73/73 全绿；虚构数据闭环验证 29/29 通过（合格/OOS/修订/权限/报表）。主文档 `docs/milestones/M2_R3_检验流程闭环.md`。

M2-R4（COA 与报表）：COMPLETED。HBOS COA(+Item) + Print Format `HBOS COA` + create_coa / review_coa / publish_coa（PDF 附件归档 + 快照保护）、4 个报表（检验结果清单 / 样品台账 / 审计追踪查询 / COA 发布记录）已交付；离线测试 89/89 全绿；COA 发布链路验证 19/19 通过。主文档 `docs/milestones/M2_R4_COA与报表.md`。

M2-R5（验证收口）：REVIEWING，等待 Owner 和 Claude 审查。全量演练 19/19 通过、11 项验收全部通过、离线测试 109/109 全绿、Workspace 四卡片 13 链接 + 5 快捷入口已落库。审查期间增强：控制面板全面简体中文（Series→编号系列 + zh.csv DocType 名翻译）；侧边导航按业务模块下拉分组（原生 Section Break，样品管理/检验流程/报告管理/质量主数据/审计追踪 5 分组 17 子项）；定位并 workaround Frappe v16.26.3 侧边栏 DocType 项过滤核心 bug（boot_session hook 预置 user_perm_can_read 缓存，不改核心源码）；报表表格列宽拖拽修复（resize-handle 默认 opacity:0 不可见，CSS hover 表头显示手柄恢复原生拖拽与双击自适应，JS 单元格 hover 全文提示）；列表视图列宽拖拽（DocType 列表页 v16 原生不支持，monkey-patch apply_column_widths 注入表头手柄 + localStorage 持久化 + 双击复位，限定 HBOS LIMS 模块）；表单子表网格列宽拖拽（新建样品登记等表单子表列宽由 Bootstrap col-xs-N 固定无拖拽，monkey-patch ControlTable.make + MutationObserver 兜底，注入表头手柄 + localStorage 持久化 + 双击复位，限定 HBOS LIMS 模块）；样品登记默认报表视图（HBOS Sample 设 default_view=Report，打开自动进入报表视图，可切回列表）；表格字段文字居中（LIMS 标记容器内报表 datatable、列表视图、子表网格单元格 text-align:center，非 LIMS 页面不受影响）；列表视图表头/数据错位修复（文字居中下 Subject 列表头与数据行规则不一致致上下错位，数据行施同表头规则对齐）；结果修订记录列表行高异常修复（用户反馈编号与变更字段间出现独立 HBOS-TR-2026- 且行高异常；根因：字段名 result 命中 Frappe 原生 `.frappe-list .result { min-height:200px }` 被撑高至 200px，整行 211px，LIMS 列表行列重置 min-height/height 修复；CSS 资产 URL 无版本号致浏览器磁盘缓存旧版，hooks 资产 URL 加 ?v=2 版本参数强制刷新）。主文档 `docs/milestones/M2_R5_验证收口.md`。审查通过后 closeout，M2-LIMS MVP 整体收口。

M2-R6（Vue 前端原型与开发流程）：REVIEWING，等待 Owner 审查。已交付交互式 HTML 原型（`docs/frontend/M2_LIMS_Vue前端原型.html`，7 个视图，桌面 / 移动端渲染验证通过）与开发流程文档（`docs/frontend/M2_LIMS_Vue前端开发流程.md`）；推荐 Vue 3 + Vite + TypeScript + Pinia + Vue Router + Element Plus + ECharts；API 复用 `lims_service.py` 现有 whitelist 方法与 5 个 Script Report；`frontend-design` skill 当前环境不可用，按项目规则等价人工设计。未创建 Vue 工程、未接真实 API。主文档 `docs/milestones/M2_R6_Vue前端原型与开发流程.md`。
M2-R6A（样品登记动态表单设计）：REVIEWING，等待 Owner 审查。结合 `/hbos-lims/samples` 实际需求，交付 `docs/frontend/M2_R6A_样品登记动态表单设计.md` 与原型 `#sample` 动态表单交互；样品类型 / 检验优先级为顶部 sticky 下拉决策条，每个样品类型各对应一张完整表单，切换下拉即整表单替换（成品 / 原料 / 中间体 / 包装材料 / 工艺用水 / 水 / 环境样品 / 稳定性样品 / 清洁验证样品），桌面 / 移动端渲染验证通过。

M2-R6B（检验结果台账双模式设计）：REVIEWING，Owner 已确认原型与交互。针对"每种样品登记信息类型不同、检验项目不同"与 GMP 数据完整性要求，交付双模式方案：明细台账（受控记录视角，样品卡片 + 检验项目逐行 + 下钻抽屉签名/修订/审计）+ 样品表（每样品种类一张表、一行一个批次、首列序号、次列样品批号，左侧按类型分组可收缩下拉列表）；后端落地设计为 `HBOS Ledger Template` DocType + `get_result_ledger` 聚合 API（只读投影，限度/结果/判定受控可溯源）。主文档 `docs/frontend/M2_R6B_检验结果台账设计方案.md`。

M2-R6C（检验结果台账 Vue 复刻与生产部署）：DEPLOYED，Owner 已确认测试路径效果。将 R6B 双模式复刻进 Vue 工程 `ResultLedgerView.vue`（明细台账 + 样品表，数据来自真实 Frappe API：HBOS Sample / Test Result / COA / Result Revision 聚合、只读投影、superseded 链过滤、修订/审计摘要）；新增判定列 + 记录状态列筛选、记录状态语义配色（放行/批准绿、检验完成/检验中蓝、登记/草稿灰、拒绝/OOS 红）；`vue-tsc` 类型检查 0 错误；生产构建 `npm run build:prod` 后同步至生产容器 `hbos-m0-r3a-frontend-1`（备份 `hbos-lims.bak-20260827a`），生产 URL `http://localhost:8080/hbos-lims/` HTTP 200 验证通过。后端同步：新增 `get_result_ledger` 聚合查询 whitelist（只读投影，返回 样品+受控记录+修订链+COA 报告日期+类型分组，对齐前端 ResultLedgerView，避免前端多路 get_list 拼接），`workflow_contract.py` ACTION_ROLES 注册 `get_result_ledger`（LIMS Analyst/Reviewer/Manager + System 可读）；离线契约测试 114/114 全绿（新增 6 项台账契约）；真实环境跑通（全量 7 样品/17 结果/2 修订/3 COA 日期/分组 + sample_type 与 material 筛选均验证）；backend 容器 gunicorn 已重启加载新代码（kill 误杀主进程后 `docker start` 恢复，容器健康、生产前端 200）。

M2-R6D（合规审计日志 + 生产部署错配修复）：DEPLOYED，Owner 已确认测试路径效果。新增合规审计日志（全量自动捕获 + write-once + 防篡改）：后端新增 `HBOS Audit Log` DocType（log_type/doctype_target/doc_name/action_text/field_changed/old_value/new_value/reason/user/created_at/checksum，permissions 仅 Reviewer/Manager/System 可读无 create/edit/delete 常规权限，写入仅系统钩子内部 insert），`hooks.py` 注册 doc_events 全量捕获创建/修改/删除（HBOS Sample/Task/Test Result/COA/Specification/Sample Type/Test Item），`lims_service.py` 新增 `audit_log` 写核心（sha1 指纹防篡改）与 `get_audit_log` 查询 whitelist（类型/对象/操作人/关键字/时间筛选）及各业务方法埋点（提交质检/复核/批准/修订/放行/拒绝/OOS/仪器使用/规格生效-废止），`workflow_contract.py` 注册 `get_audit_log`；离线契约测试 123/123 全绿（新增 9 项）；真实环境跑通（DocType 建表、事件流、register_sample 自动触发创建事件）。前端：合规组新增 合规审计日志 入口 + `/audit-log` 路由 + `AuditLogView.vue`（事件类型语义色 Pill/对象/操作人/时间/变更前后值/原因/指纹，下钻抽屉含数据完整性）+ getAuditLog。生产部署修复：Owner 反馈「海滨LIMS 已可进入但样品登记异常/审计追踪进不去」，根因为生产 `index.html` 引用旧 bundle `index-Ty0i1qY8.js` 与生产 assets 混 129 个历史旧 chunk（新旧哈希错配致 view chunk 懒加载 404/崩溃）；以 root 清空旧 assets 后重新部署最新干净 dist（主 bundle `index-BnAvve8_.js` + 39 资产与本地逐字节一致），全引用资产 200 + 正确 MIME 验证；注入 nginx SPA fallback（`location ^~ /hbos-lims/` try_files 命中 public/hbos-lims 并 fallback index.html）修 `/hbos-lims` history 404，备份 `frappe.conf.bak-20260903-spa`。生产部署机制：前端经 `docker cp dist/.` 覆盖至 `/home/frappe/frappe-bench/sites/frontend/public/hbos-lims/`（先 root 清 assets 防残留），后端经 bind mount 实时生效。

M2-R7（留样管理板块开发方案）：REVIEWING rev6（rev5 后 Claude 终审修订：P1 释放预占绑定本单预占状态、P2 待处理回退补全/审批流逃生口/受托转出落位，P3 六项分轮携带）。Owner 2026-09-07 已确认角色方案 B+SoD（清单第 1 项）与分支策略 b（第 8 项，`m2-r6` 为 M2 延伸工作线，门禁已同步）；余 6 项：第 2/5/6 为 R7A 前核对项，第 3/4/7 按默认值推进。R7 执行进度：R7A（主数据与留样登记 3 DocType + retention_service + 前端两页）已在 m2-r6 交付并测试路径验证；R7B（观察管理）/R7C（使用与处理审批）后端 PLANNED；R7D（Vue 前端 6 视图复刻与生产部署）DEPLOYED（见下方 M2-R7D 段）。以 JXH-SOP-LC-1-00-007-09《留样管理规程》全套文件（1 正文 + 4 记录 + 2 附件，Owner 2026-09-04 提供并授权）为第一业务依据，两份桌面方案评审为业务采纳、技术路线 Frappe 原生化。rev3 定案：5 主 DocType + 1 子表（Retention Product（default_uom Select 受控枚举为 UOM 唯一权威）/ Retention Sample + Stock Log 通用库存操作流水 / Observation / Usage Apply / Disposal Apply（qa_manager_required 4/5 级可配））+ 标签 Print Format + 4 报表；数量语义统一（available_qty=current_qty−reserved_qty 派生量不落库）+ 四步锁协议 + 各操作锁内复核；观察批数量校验（同产品同年度 ≤3 批 + 看板 N/3）；审计事件受控枚举 16 类；角色动作矩阵 + 两条 SoD 硬校验；状态机含驳回终态/已转出/qm_approved_at/4-5 级双路径；Sample→留样映射 6 规则成节；scheduler 扫描；R7A~C 验收含三组并发负向用例。rev4 三轮复审修订 9 项（5 P1 + 4 P2）：①confirm_stock 纳入四步锁协议与单一写路径（防并发确认超额预占）；②execute_usage 锁内复核条件修正——本单预占有效性（reserved_qty>=apply_qty）+ 总量守恒（current_qty>=reserved_qty），弃用 available_qty 判本单；③观察批选取并发防护——产品行 FOR UPDATE 锁内计数；④全检量 2 倍自动计算加 UOM 一致性闸（full_test_qty_uom≠default_uom 禁算）；⑤R7A 验收「调整低于预占」用例归位 R7C（预占由使用申请产生），R7A 改测负结存边界；⑥README/AI_CONTEXT/milestones README 补 R7 进度；⑦分支策略（m2-r6 vs m2-lims）列为待确认第 8 项并 M2_START_GATE 加注记；⑧scheduler 由 daily 改 cron（30 0 * * *）；⑨观察批 3 批口径定稿（上限硬校验、不足 3 批弹性允许 + 看板完整性提示）。主文档 `docs/milestones/M2_R7_留样管理板块开发方案.md`。

M2-R7D（留样板块前端 Vue 复刻与生产部署）：DEPLOYED，Owner 2026-09-08 已确认测试路径并授权同步生产。按 `docs/frontend/M2_R7_留样板块前端设计方案.md` 与交互式原型（`docs/frontend/M2_R7_留样板块前端原型.html`）在 `m2-r6` 分支落地 Vue 6 视图留样板块：路由 `/retention`（工作台总览）、`/retention/samples`、`/retention/products`、`/retention/observations`、`/retention/usage`、`/retention/disposal`，侧栏「留样管理」扩为 6 入口。新增 `RetentionDashboardView` / `RetentionObservationsView` / `RetentionUsageView` / `RetentionDisposalView` 四视图 + `styles/retention.scss` 共用样式 + `src/demo/retentionDemo.ts` 演示数据与角色矩阵 + `components/retention/DemoBar`（演示身份切换驱动角色动作矩阵显隐与 SoD 提示）。数据口径：登记台账/产品两页沿用真实 R7A API 并小幅对齐（可用量独立列、临期范围筛选、页头样式统一）；工作台/观察/使用/处理 4 视图因 R7B/C 后端未落地先以演示数据（TEST-HBOS-M2-RET-*）渲染完整 UI/交互并横幅标注。验证：`vue-tsc` 0 错误、六路由浏览器回归无控制台错误、生产构建成功；生产同步至 `/home/frappe/frappe-bench/sites/frontend/public/hbos-lims/`（备份 `hbos-lims.bak-20260908101325`），`http://localhost:8080/hbos-lims/` 全路由与 bundle HTTP 200。R7B（观察管理）/R7C（使用与处理审批）后端 PLANNED，落地后将 `src/demo/retentionDemo.ts` 演示数据源替换为 `retention_service` whitelist。

## 本轮补充（M2-R7D，已交付 DEPLOYED）

## 本轮范围（M2-R6，已交付 REVIEWING）

- 结合《海滨药业LIMS系统开发方案》与 `hb_lims_app` 实际闭环，产出 HBOS LIMS Vue 前端原型与开发流程。
- 交付 `docs/frontend/M2_LIMS_Vue前端原型.html`（7 个视图，交互式，演示数据 `TEST-HBOS-M2-*`）与 `docs/frontend/M2_LIMS_Vue前端开发流程.md`。
- 推荐 Vue 3 + Vite + TypeScript + Pinia + Vue Router + Element Plus + ECharts；API 复用 `lims_service.py` 现有 whitelist 方法与 5 个 Script Report。
- 本轮只到原型 / 视觉方案阶段，未创建 Vue 工程、未接真实 API；`frontend-design` skill 当前环境不可用，按项目规则等价人工设计。
- 样品登记动态表单设计：样品类型与检验优先级为下拉决策条，每个样品类型各对应一张完整表单，切换下拉即整表单替换；交付 `docs/frontend/M2_R6A_样品登记动态表单设计.md` 与设计提示词。

## 并行未决事项（不阻塞 M2-LIMS）

M1 产品交付仍在 M1-FIX 功能补漏中，B3 / B4 / B5 为 REVIEWING，等待 Owner 和 Claude 审查，未 closeout；M1-FIX-C/D/E 为 PLANNED，未启动。M1-FIX 工作线在 `m1-fix-frontend-zh` 分支，M2-LIMS 工作线在 `m2-lims` 分支，互不干扰。

| 轮次 | 名称 | 优先级 | 状态 |
| --- | --- | --- | --- |
| M1-FIX-B3 | 考勤工作台入口、App 命名与 HRMS 数据一致性修复 | P0 | REVIEWING / Owner UI 验收未通过 |
| M1-FIX-B4 | 考勤模块架构收敛与单一入口重整 | P0 | REVIEWING / Claude PASS，Owner 数据链路验收发现后续问题 |
| M1-FIX-B5 | 导入数据链路核查与报表口径收敛 | P0 | REVIEWING |
| M1-FIX-C | 异常说明三级流程 | P1 | PLANNED |
| M1-FIX-D | 考勤工作台 + 月报 + 领导 Demo | P1 | PLANNED |
| M1-FIX-E | 飞书 OAuth 最小验证 + Owner 体验脚本 + 总审查 | P2 | PLANNED |

## M2-R1 范围（历史，已收口）

- 建立 M2-LIMS 启动门禁与总方案文档。
- 将 `hb_lims_app` 挂载进 Docker Compose 环境（8 处 service + 6 处 PYTHONPATH）。
- 创建 `hb_lims_app` 完整骨架（双层结构 + hooks + config + public logo + after_migrate 幂等同步）。
- 安装到 `frontend` site 并验证入口对象与静态资源可达。
- 搭建离线测试脚手架并跑通。

M2-R1 禁止事项：不创建 DocType；不创建业务方法；不修改 Frappe/ERPNext/HRMS 核心源码；不录入样品 / 人员 / 检测数据；不提交 `.env`、密钥、Excel/CSV、数据库或运行时产物；不执行 `docker compose down -v`；不删除 volume；不重建 `frontend` site。

## M2-LIMS 全阶段禁止事项

- 不创建 `hb_core_app`、`hb_feishu_app` 或其他未授权 App
- 不修改 Frappe/ERPNext/HRMS 核心源码
- 不把 `hb_lims_app` 扩大为 12 模块全量 LIMS（仪器集成、稳定性、环测、微生物、试剂、OOS 调查等另行规划）。**留样板块（M2-R7）已按 Owner 授权纳入 R7 范围**：2026-09-04 Owner 提供全套规程并授权设计，R7A~D 子轮须在方案审查通过后逐轮启动
- 不做大型 Vue/React 独立前端（须原型先行 + Owner 审查）
- 不接真实仪器、不录入真实样品 / 人员 / 检测数据；演示数据一律 `TEST-HBOS-M2-*` 前缀
- 不提交 `.env`、App Secret、密钥、token、真实数据、Excel/CSV
- 不执行 `docker compose down -v`，不删除 Docker volume，不重建 `frontend` site
- 不把「计划可行」写成「功能已实现」

## 当前状态口径

```
M2-LIMS   = IN_PROGRESS（MVP 交付完成，R5 待审查）
M2-R1     = COMPLETED
M2-R2     = COMPLETED
M2-R3     = COMPLETED
M2-R4     = COMPLETED
M2-R5     = REVIEWING（待 closeout）
M2-R6     = REVIEWING（Vue 前端原型待 Owner 审查）
M2-R6A    = REVIEWING（样品登记动态表单设计待 Owner 审查）
M2-R6B    = REVIEWING（检验结果台账双模式设计，Owner 已确认原型与交互，设计文档待审查）
M2-R6C    = DEPLOYED（检验结果台账 Vue 复刻已上线生产，Owner 已确认测试路径）
M2-R6D    = DEPLOYED（合规审计日志已上线生产，Owner 已确认测试路径；含生产部署错配修复）
M2-R7     = REVIEWING rev6（方案口径定稿：角色方案 B+SoD、分支策略 b 已 Owner 确认；R7A 已在 m2-r6 交付 3 DocType+retention_service+前端两页；R7B/C 后端 PLANNED）
M2-R7D    = DEPLOYED（Vue 前端 6 视图复刻并同步生产 /hbos-lims，工作台/观察/使用/处理以演示数据先行，Owner 2026-09-08 已确认测试路径）
M1-FIX    = IN_PROGRESS（并行未决，B3/B4/B5 REVIEWING）
M1-FIX-C/D/E = PLANNED / 待 Owner 授权
```

## 下一轮预告

M2-R5 审查 closeout 与 M2-R6 原型审查并行：M2-R5 等待 Owner 浏览器 UI 验收（海滨LIMS 桌面图标 → 工作台 → 样品登记 → 检验全流程 → COA 发布）与 Claude 审查，通过后 M2-LIMS MVP 整体收口；M2-R6 等待 Owner 审查交互式 HTML 原型与开发流程，通过后再进入 Vue 工程初始化与页面复刻。M2-LIMS 其余扩展模块（仪器集成、稳定性、环测、微生物、试剂、OOS 调查、审计追踪通用引擎、国密电子签名）另行规划，不自动启动；留样板块（M2-R7）已按 Owner 授权进入方案审查阶段。
M2-R6A 随 M2-R6 并行审查：Owner 审查动态表单方案与原型交互（含 9 类样品类型切换、必填联动、桌 / 移双端）通过后，将样品登记页纳入 Vue 页面复刻范围。
M2-R6B 随 M2-R6A 并行：Owner 已确认检验结果台账双模式原型（明细台账 + 样品表每样品种类一表）与视觉规范，设计文档待审查；通过后将检验结果台账页纳入 Vue 页面复刻范围，后端 `HBOS Ledger Template` / `get_result_ledger` 落地另行规划。
M2-R6C 已上线生产：检验结果台账双模式 Vue 复刻完成并同步至生产路径，Owner 已确认测试路径效果；`HBOS Ledger Template` DocType / `get_result_ledger` 聚合 API 为待实现规划项，本轮未新建 DocType、未改后端业务方法。
M2-R7D 已 DEPLOYED：留样板块 Vue 前端 6 视图已复刻并同步生产 `/hbos-lims`（备份 `hbos-lims.bak-20260908101325`），Owner 2026-09-08 已确认测试路径；工作台/观察/使用/处理 4 视图以演示数据先行，登记台账/产品接真实 R7A API。R7B（观察管理）/R7C（使用与处理审批）后端 PLANNED，待启动轮实现后把 `src/demo/retentionDemo.ts` 演示数据源替换为 `retention_service` whitelist（观察批 N/3 硬校验、使用/处理审批链与逃生口、SoD、四步锁协议按方案 rev6 落地）。留样板块（M2-R7）已按 Owner 2026-09-04 授权纳入 `hb_lims_app` 范围；R7A 与 R7D 落地状态已入台账。

权威状态文件：

- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/milestones/M2_START_GATE.md`
- `docs/milestones/M2_LIMS_总方案与轮次拆分.md`
- `docs/milestones/README.md`

权威方案文件：

- `docs/milestones/M2_LIMS_总方案与轮次拆分.md`
- `/Users/hbzl/Desktop/海滨药业LIMS系统开发方案.md`（私有，不入库，业务口径来源）
