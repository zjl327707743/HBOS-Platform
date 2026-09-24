# Reading Guide

本指南用于限制 AI 在新乡海滨智能运营管理平台中的默认阅读范围，避免上下文膨胀和误读旧资料。

当前状态提示（2026-09-23）：M2-R8K「我的待办身份绑定」仍为 REVIEWING，真实 Frappe 冒烟已通过，待 Owner 测试路径验收；生产页面已可访问该功能，既有发布来源待核。本次仅将侧栏「最近访问」移除补丁 `fbb1aee` 同步生产，未执行后端迁移或重启。具体以 `docs/PROJECT_STATUS.md`、`docs/CURRENT_MILESTONE.md` 和 R8K 主文档为准。

## 默认读取文件

每轮任务默认只读：

- `CLAUDE.md`
- `AGENTS.md`
- `docs/AI_CONTEXT.md`
- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`

每轮任务开始前必须说明读取了哪些文档。

## 禁止默认递归读取

禁止默认递归读取整个 `docs/`。

默认不读取以下目录：

- `docs/archive`
- `docs/research`
- `docs/legacy`

除非用户明确要求，否则不要浏览或搬运大量 Obsidian 长文。

## 公共入口文件收尾检查规则

默认读取规则不变。

每轮收尾审查可读取以下公共入口文件：

- `README.md`
- `CLAUDE.md`
- `AGENTS.md`
- `docs/AI_CONTEXT.md`
- `docs/READING_GUIDE.md`
- `docs/frontend/FRONTEND_IMPLEMENTATION_GUIDE.md`（仅前端相关轮次）

此外，每轮收尾还必须检查：

- 当前阶段门禁文档：M1 阶段为 `docs/milestones/M1_START_GATE.md`，未来 M2/M3 阶段分别为 `docs/milestones/M2_START_GATE.md`、`docs/milestones/M3_START_GATE.md`。阶段门禁文档用于记录当前阶段的目标、边界、门禁、子轮次状态和下一步路线。
- 当前轮次主文档：指本轮实际交付的 `docs/milestones/Mx_Ry_*.md` 文档，例如 `docs/milestones/M1_R3F_业务口径确认包.md`。每轮进入 REVIEWING 或 closeout 时，必须同步更新该轮次主文档状态。

这些文件不一定每轮修改，但必须检查是否存在过期阶段描述。检查公共入口文件不等于允许递归读取整个 `docs/`。

## 条件读取规则

只有任务明确涉及当前里程碑时，才读取：

- `docs/plans/m0_engineering_bootstrap.md`

只有任务涉及独立前端开发、驾驶舱、AI 工作台或复杂交互页面时，才读取：

- `docs/frontend/FRONTEND_IMPLEMENTATION_GUIDE.md`

## 里程碑文件读取规则

- 默认不全量读取 `docs/milestones/`。
- 当前里程碑任务可读取对应文件，例如 M0 任务读取 `docs/milestones/M0.md`。
- `docs/milestones/README.md` 可作为里程碑索引读取。
- 每轮任务收尾时，如项目状态、当前轮次或里程碑状态发生变化，必须同步更新对应里程碑文件。

M0 历史任务曾允许读取：

- `docs/plans/M0-R2_Frappe_Docker最小环境方案设计.md`
- `docs/deployment/Frappe_Docker最小部署设计.md`
- `docs/deployment/本地开发环境变量说明.md`

## Skill 路由读取规则

- `docs/AI技能路由规范.md` 仅在涉及 Skill、Agent 调度、飞书 skill 选择或相关审查时读取。
- 不因存在 Skill 路由文档而默认全量读取 `docs/`。
- 不因存在飞书 skill 而默认执行飞书真实写入。

只有架构决策变更时，才读取：

- `docs/adr/`

## 当前里程碑提醒

当前 M0 已完成并封板，M0-REMOTE 已完成，M1-R0 已完成并通过 Codex 独立审查，M1-R1 已完成 HRMS 原生考勤对象模型验证记录并收口为 COMPLETED，M1-R2 已完成 HRMS 原生考勤配置试运行方案并通过 Codex 独立审查收口为 COMPLETED。M1-R3 已执行 HRMS 原生考勤最小测试数据试运行并通过 Codex 审查，实际结论为 PARTIAL / BLOCKED，最终状态收口为 BLOCKED：部分 TEST 数据已落库，14 个打卡场景未完成闭环验证。M1-R3A 已完成运行态阻断诊断与 TEST 数据隔离 / 清理方案，并已通过 Codex 审查收口为 COMPLETED。M1-R3B 已完成运行态最小修复方案，并已通过 Codex 审查收口为 COMPLETED。M1-R3B-FIX 已通过 Codex 审查并收口为 COMPLETED；该轮只执行 `docker compose up -d redis-cache redis-queue`。M1-R3C 已通过 Codex 审查并收口为 COMPLETED，结论为 PARTIAL / GAP_IDENTIFIED。M1-R3D 已通过 Codex 审查并收口为 COMPLETED，结论为 Gap 四类分类、均不需要立即创建 hb_attendance_app。M1-R3E 已通过 Codex 审查并收口为 COMPLETED。M1-R3F 已通过 Codex 审查并收口为 COMPLETED。M1-REQ-DESIGN-DRAFT 已通过 Codex 审查并收口为 COMPLETED。M1-R4 已通过 Codex 审查并收口为 COMPLETED，主文档 `docs/milestones/M1_R4_Demo技术方案与实施路线拆分.md` 已交付。M1-R5 已通过 Codex 审查并收口为 COMPLETED，主文档 `docs/milestones/M1_R5_HRMS配置基线工作台月报Demo.md` 已交付。M1-R6A 已通过 Codex 审查并收口为 COMPLETED，主文档 `docs/milestones/M1_R6A_Excel导入与异常流程落地方案.md` 已交付。M1-R6B 已通过 Codex 审查并收口为 COMPLETED，主文档 `docs/milestones/M1_R6B_脱敏打卡流水导入最小实现.md` 已交付。M1-R6C = COMPLETED，异常识别与异常说明流程最小实现已通过 Codex 审查并 closeout。M1-R7 = COMPLETED，飞书登录、领导 Demo 与 M1 收口准备已通过 Codex 审查并 closeout。M1 历史 closeout 已完成，但 Owner UI 验收发现功能缺口，当前 M1 产品交付仍在 M1-FIX 中，尚未完成。M0-R3A 已完成 Frappe / ERPNext / Docker 最小本地环境落地，M0-R3C 已完成 Frappe HR / HRMS 安装验证，M0-R3C-FIX 已完成 HRMS 前端资源与 Roster 白屏诊断修复，M0-R3D 已完成 HRMS 能力盘点与 M1 考勤一期边界设计，M0-R3E 已完成 HRMS 环境可复现性收口并通过 Codex 审查。

下一步路线只记录，不代表已启动：

1. M1-R5 已通过 Codex 审查并收口为 COMPLETED，已交付 HRMS 配置基线、考勤工作台入口、月度汇总 Demo 和 Excel 月报导出路径。
2. M1 已 closeout 为 COMPLETED，但 Owner 验收发现功能缺口。
3. M1-FIX 功能补漏阶段已启动，M1-FIX-A 为 REVIEWING。
4. M1-FIX-B Excel 导入与真实本地数据闭环已实现并进入 REVIEWING。
5. M1-FIX-B2 已 COMPLETED；M1-FIX-B3 为 REVIEWING / Owner UI 验收未通过；M1-FIX-B4 为 REVIEWING / Claude PASS，但 Owner 数据链路验收发现后续问题；当前 M1-FIX-B5 为 REVIEWING，核查导入数据链路并收敛 HBOS 报表、月度汇总暂存和 HRMS 原生技术核查口径。M1 产品交付未完成，M1-FIX-C/D/E 未启动。

后续涉及 HRMS 环境治理、前端资源复核、能力盘点或 M1 考勤一期边界时，可读取 M0-R3C 安装验证记录、M0-R3C-FIX 修复记录、M0-R3D 设计记录、M0-R3E 环境可复现性收口记录、官方 Frappe HR、`frappe/hrms`、`frappe/frappe_docker`、ERPNext / Frappe v16 资料。

不得因 HRMS 已安装而擅自创建新的海滨自定义 Frappe App；`hb_attendance_app` 仅限 M1-FIX-B 已授权的轻量导入能力，不得扩大范围；不得接飞书真实写入；不得在原型审查通过前实现前端驾驶舱；不得提交真实 `.env` 或真实密钥。
M2-LIMS 当前为 M2-R8K「我的待办身份绑定」REVIEWING：审查修复及真实 Frappe 冒烟已完成，待 Owner 测试路径验收；生产页面已可访问，既有发布来源待核。
M2-R6A（样品登记动态表单设计）随 M2-R6 并行 REVIEWING；样品登记动态表单方案见 `docs/frontend/M2_R6A_样品登记动态表单设计.md`。
M2-R6B（检验结果台账双模式设计）REVIEWING，Owner 已确认原型与交互；双模式（明细台账 + 样品表每样品种类一表）方案见 `docs/frontend/M2_R6B_检验结果台账设计方案.md`。
M2-R6C（检验结果台账 Vue 复刻与生产部署）DEPLOYED：双模式已复刻进 Vue 上线生产；M2-R6D（合规审计日志）DEPLOYED：合规审计日志 DocType/全量捕获/前端页已上线，并修复生产部署 hash 错配致个别页面 404。
M2-R7D（留样板块前端 Vue 复刻与生产部署）DEPLOYED：留样方案 rev6 口径定稿（Owner 2026-09-07 确认角色方案 B+SoD、分支策略 b）；R7A（主数据与留样登记 3 DocType+retention_service+前端两页）已在 m2-r6 交付并测试路径验证；6 视图 Vue 板块已同步生产 `/hbos-lims`（工作台/观察/使用/处理 4 视图已切换真实后端接入，登记台账/产品沿用 R7A API），Owner 2026-09-08 已确认测试路径；R7B（观察管理）/R7C（使用与处理审批）后端已实现并真实验证。方案主文档见 `docs/milestones/M2_R7_留样管理板块开发方案.md`，前端见 `docs/frontend/M2_R7_留样板块前端设计方案.md` 与 `docs/milestones/M2_R7D_留样板块前端设计.md`。
M2-R8F（稳定性板块前端 Vue 复刻与生产部署）DEPLOYED：Owner 2026-09-16 已确认测试路径并授权同步生产。在 `frontend/hbos-lims-web` 复刻稳定性 7 视图 + 7 条路由 + 侧栏「稳定性管理」分组 7 入口 + 演示数据层 `src/demo/stabilityDemo.ts`（`TEST-HBOS-M2-STB-*`）；`vue-tsc` 0 错误、`npm run build` 通过、浏览器与 375px 移动端回归通过；生产构建 `npm run build:prod` 后同步 `/hbos-lims`（备份 `【内部备份标识已省略】`，84 个文件与本地逐字节一致、全路由与 7 个稳定性 chunk 均 200）。本轮不创建稳定性 DocType、不改 `hb_lims_app`、不接真实 API（稳定性视图零 API 调用）、不启动 R8A（该轮口径；R8A 其后已由 M2-R8A 完成）。主文档 `docs/milestones/M2_R8F_稳定性板块前端Vue复刻与生产部署.md`。
M2-R8J（稳定性板块前后端审查与缺陷修复）**DEPLOYED / 待 Owner 测试路径验收**：2026-09-21 后续回滚模拟复现的 8 项 P1 与 2 项 P2 已完成修复；离线契约 321/321、前端类型检查与构建通过，测试路径浏览器冒烟覆盖变更条件、结果录入与趋势、取样计划及延期派生区域。已提交 `e447f97` 并同步生产 `/hbos-lims`（备份 `【内部备份标识已省略】`）。上线后 Owner 验收发现的稳定性工作台「待 R8B~R8D」占位文案（KPI 卡 + 整块面板）已修复——后端补样品/时间点/结果真实计数与时间点执行结构，前端 KPI 6→8 张；侧边栏「取样与检测计划 / 结果录入与趋势」角标改接真实数据（原为原型遗留硬编码 4/3 且恒显红色，提交 `6e06155`）（提交 `b61f83d`，已同步生产）。主文档 `docs/milestones/M2_R8J_稳定性板块审查与修复.md`。
M2-R8I（稳定性剩余三视图前端接入 + 5 张 Script Report 物化）DONE / 待 Owner 审查：5 张报表物化（方案 6 张全部就位）、`api/stability.ts` +64 函数、结果/报告/Ops 三视图接真实后端、演示层退役。验证：离线 311/311、报表实机渲染、浏览器读写全链与角色显隐、375px 无溢出。稳定性板块 7 视图全部接入真实后端。未部署生产。主文档 `docs/milestones/M2_R8I_稳定性剩余三视图前端接入.md`。
M2-R8H（稳定性前端接入：样品入箱与台账 + 取样与检测计划）DONE / 待 Owner 审查：把 R8B 后端接到两个视图（读 + 写全接、按角色显隐）；后端补跨时间点延期列表接口与 schedule 三层日期；月度看板改整月日期列；标签打印走 Frappe 打印视图。验证：离线 246/246、`vue-tsc` 0 错误、build 成功、浏览器读写全链与角色门控、375px 三页无溢出。稳定性 7 视图中 4 个已接真实后端。未部署生产。主文档 `docs/milestones/M2_R8H_稳定性样品与计划前端接入.md`。
M2-R8B（稳定性后端：样品、时间点与取样检测计划）DONE / 待 Owner 审查：交付 5 个 DocType（Sample+Log / Timepoint+Timepoint Item+Timepoint Delay）+ 3 条状态机 + 21 个动作 + 4 只读接口 + scheduler + 标签 Print Format + 「取样与检测计划看板」报表。核心口径：单一写路径与四步锁（Sample → Timepoint）、时间点生成幂等、延期日期链全段校验、逾期纯派生；Result（R8C）依赖处做前向兼容守卫。证据：离线 244/244、实机 40/40、补充 10/10。本轮只做后端 + 标签 + 报表，未部署生产。主文档 `docs/milestones/M2_R8B_稳定性样品与时间点后端.md`。
M2-R8G（稳定性前端接入真实 API：工作台 + 考察申请与方案）DONE / 待 Owner 审查：后端补 5 个只读接口（产品 / 主数据白名单 / 方案台账 / 方案详情 / 稳定性审计摘要）；前端新增 `src/api/stability.ts`，两视图读 + 写全接、按角色显隐；其余 5 视图标注「演示数据 · 待 R8B~R8D」。修复 2 项 R8A 遗留缺陷（Protocol 缺 `snapshot_frozen` 致冻结守卫失效；命名系列 `-####` 非法致畸形单号）。验证：离线 203/203、实机 28/28、只读 7/7、浏览器真实会话读写全链、`vue-tsc` 0 错误、build 成功。**未部署生产**。主文档 `docs/milestones/M2_R8G_稳定性前端接入真实API.md`。
M2-R8A（稳定性主数据与通知单/方案后端实现与实机验证）DONE / 待 Owner 审查：11.3 启动门禁 7/7 已闭环（Owner 2026-09-16）；在 `hb_lims_app` 落地 10 个 DocType（4 主数据 + Notice + Protocol + 4 子表）、`FLOW_STB_NOTICE`/`FLOW_STB_PROTOCOL` 两条状态机、新增 `LIMS QA Manager`/`LIMS QP` 两角色、批准后冻结快照与版本链；DocType 层 6 个 LIMS 角色一律只读（方案 8.6）。实机 migrate 已执行，端到端 + 负向用例 28/28 通过、离线契约 199/199 全绿；验证中修复 4 项缺陷。主文档 `docs/milestones/M2_R8A_后端实现与实机验证.md`。
M2-R8E（稳定性板块前端设计方案与 HTML 原型）REVIEWING / Owner 已确认原型：原型与设计图已交付（`docs/milestones/M2_R8E_稳定性板块前端设计方案.md`、`docs/frontend/M2_R8_稳定性板块前端原型.html`、`docs/frontend/assets/M2_R8_稳定性工作台设计图.png`），其 Vue 复刻阶段由 M2-R8F 承接。
M2-R8（稳定性管理板块开发方案）REVIEWING **rev15**（业务依据 v9.0 **已正式生效**，Owner 2026-09-16 确认 11.3-1）：Owner 2026-09-15 提供《稳定性管理》规程全套 5 份文件（新版 v9.0 `SOP-LC-1-00-019` 为主、旧版 05 版为差异基线）并授权方案设计；技术路线 Frappe 原生化（对齐 R7）。rev1 审核 FAIL（4 P0 + 6 P1）后 rev2 修订（Timepoint 提升为独立主 DocType、补 Result/Report 状态机、批准后冻结快照与版本链、电子签名能力边界更正、数据模型全量显式定义、时间单位统一、显著变化配置化、「控制图」改称「趋势图」、新增 Room/Test Item 主数据、角色身份先定后授权限、逾期纯派生）；复审"有条件通过"（5 必修 + 3 补强）后 rev3 修订、rev4 修订（结果版本键与生效指针、双延期模型、DocType 清单总表、按 DocType 删除拦截、0 月来源 Link、检测日期物理约束、一般变更审批收紧、有效期字段拆分，新增 11.3 节 R8A 启动前置门禁）；三轮复审后 rev4 修订（0 月免取样口径、时间点生成触发与中间条件、追加条件闭环、变更实施落点 7.9 节、`ROUND_HALF_UP`）；四轮复审 FAIL 后 rev5 修订（生效指针仅在新版批准后同事务切换、统一 `effective_due_date`、新增 `LIMS QA Manager`、动作矩阵全转移覆盖、Timepoint Item 防重复、年度类 Notice 快照链、并发锁协议）；五轮复审后 rev6 修订（`mark_for_disposal`/`cancel_disposal` 使「待处理」可达、入箱超期改强制评估四件套、`append_conditions` 入矩阵）；六轮复审 FAIL 后 rev7 修订（结果状态与生效指针冲突修正、期限三层模型与政策硬上限、`record_result` 收紧为 `Timepoint=检测中`、`pre_disposal_status` 快照、`approve_report` 三条硬前置、Report 补 `client`/`seq`/`source_ref`、补全驳回/作废/人日字段、延期历史单一口径，新增 8.6/8.7）；七轮复审 FAIL 后 rev8 修订（补 `apply_delay`/`reject_delay` 并统一字段名、补 `已批准→已作废` 出口与时间点重开、流水补「受托转出」、Notice 补驳回/取消字段、Report 改 Dynamic Link、8.3 按 DocType 列终止动作、期限审批口径入 11.3 第 7 项）；八轮复审 FAIL 后 rev9 修订（Timepoint 状态机矛盾消除 + `reopen_timepoint` 登记、重开判定按必检项目粒度、启动门禁口径统一为 11.3 的 5 项、Report 映射表移位、8.6 措辞更正）；九轮复审 FAIL 后 rev10 修订（`void_result` 行改按必检项目粒度重开、`report_period_key` 纳入 `source_doctype` 消歧并补 `seq` 并发锁）；十轮复审 FAIL 后 rev11 修订（`reopen_timepoint` 补"仅已完成才调用"守卫、延期日期全链校验、8.6 权限隔离更正、`seq` 锁指定产品行、`report_period_key` 改用 `client_code`、`mark_superseded` 语义界定）；十一轮复审 FAIL 后 rev12 修订（11.3 门禁维持"5 项未闭环、不得启动 R8A"；`apply_delay`/`approve_delay` 矩阵行补日期链、`reopen_timepoint` 矩阵行补状态守卫、映射规则与唯一性总表 `client` 统一为 `client_code`；`client_code` 定案五条规则、8.6 新增运行期一致性扫描同步 8.1/8.4/门禁 16）；十二轮复审 FAIL 后 rev13 修订（11.3 门禁维持"5 项未闭环、不得启动 R8A"；`client_code` 重定案——删名称回退、新增 `customer` Link 且 `client_code` 唯一来源为 `Customer` 文档名；台账修复；业务依据统一 v9.0 拟执行依据待生效确认、v8.0 仅作历史差异基线）；十三轮复审 FAIL 后 rev14 修订（11.3 门禁维持「5 项未闭环、不得启动 R8A」；`client_code` 收紧为始终只读派生 + 硬校验 `client_code == customer.name`、删「带出后可改」；格式约束落 ERPNext `Customer` 主数据命名规范、删运行时隐式规范化；`README` 旧待确认口径更正为 11.3-1/2/4/5/7、台账补 v9.0 拟执行标注；`report_period_key` 入键成分禁 `#`、非专项报告 `customer`/`client_code`/`seq` 必须为空）；十四轮复审 FAIL 后 rev15 修订（11.3 门禁维持「5 项未闭环、不得启动 R8A」；Customer 编码格式补两层可执行保障——validate 钩子强制校验 + R8A 前存量扫描；「规范化 `client_code`」旧措辞统一为 Customer 文档名原值；`client` 展示字段只读派生 `customer.customer_name`；文档头重复修订史清理）。定案 14 主 + 8 子 DocType（= 22）、8 条状态机、8 项强校验点、ICH Q1E 外推助手，拆 R8A~R8E，新增跨轮验收门禁 6 类；Owner 已确认两项范围边界（全量 12 模块、稳定性室手工记录纳入本板块）；**Owner 2026-09-15 决策两项**：电子签名走路线 ①（GMP 合规电子签名由平台后续统一专项、各板块统一接入）；R8 工作分支为新建 `m2-r8`。**R8A 已启动并完成**（11.3 启动门禁 7/7 已闭环；10 DocType + 2 状态机 + 2 角色 + 冻结快照/版本链；实机 28/28、离线 199/199）；R8B~R8E 待逐轮启动。方案主文档见 `docs/milestones/M2_R8_稳定性管理板块开发方案.md`。
