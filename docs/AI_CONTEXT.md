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

> 状态校正（2026-09-21 本轮追加）：R8J 原有生产基线之外，本轮新增业务检验结果同步稳定性结果/趋势、审查缺陷修复及趋势摘要下拉控件宽度修复均已按 Owner 授权同步生产；生产发布脚本 pytest **342/342**、生产前端 `build:prod` 通过，生产路径 17 个页面/资源冒烟均返回 200，备份为 `【内部备份标识已省略】`，结果页已完成生产浏览器复测。

> 当前状态（2026-09-23）：M2-R8K「我的待办身份绑定」为 REVIEWING，真实 Frappe 冒烟已通过，待 Owner 测试路径验收。生产页面已可访问该功能，既有发布来源待核；本次仅将侧栏「最近访问」移除补丁 `fbb1aee` 同步生产，备份 `【内部备份标识已省略】`，未执行后端迁移或重启。LIMS 后端测试集 **395 passed**、前端单测 **7 passed**、生产构建通过。主文档 `docs/milestones/M2_R8K_我的待办身份绑定.md`。

> 守卫补齐（2026-09-24，分支 `m2-r8`，提交 `c8dcfcb`，**已部署**）：为 M2-R3/R6 检验流程 5 个 DocType 补齐 R7/R8 已有的系统字段守卫，堵住「`frappe.client.set_value` 直写状态 / 签署字段绕过服务层状态机与 SoD（伪造审批）」这一缺口。改动：`workflow_contract` 新增 5 个字段集（状态 + 签署 + 版本链，26 字段）、新增中性入口 `guards.py` 再导出 `stability_guards.guard_system_fields`、5 个控制器 `validate()` 接线、`lims_service` 23 个保存点补 `doc.flags.allow_system_fields = True`。验证：离线 **404 passed**（原 395 + 新增 9 项契约，含保存点放行标记的防回归扫描）；实机非特权用户 **9 passed**（正向全链多角色跑通 + 7 项直写负向全拦 + 1 项非系统字段对照可写）；验证数据已清理。部署：已重启 `backend` / `scheduler` / `queue-short` / `queue-long` 加载新代码（未动 `frontend` / `websocket`），部署后经 nginx → gunicorn 以非特权 LIMS Manager 真实发起伪造写返回 **HTTP 417** 被拦（对照组 200），HTTP 冒烟 17/18。**本轮为窄口径**，未纳入 M2-R3 缺失的删除拦截与运行期一致性扫描。主文档 `docs/milestones/M2_R3G_检验流程系统字段守卫.md`，详见 `docs/PROJECT_STATUS.md`。

前一子轮：M2-R8J（稳定性板块前后端审查与缺陷修复）**DEPLOYED / 待 Owner 测试路径验收**。两轮修复共 **3 + 8 项 P1** 与 **2 + 2 项 P2**（第一轮：报告链断裂 / 结果页缺「提交」/ `complete_testing` 越权 / 设备 status 无守卫 / 故障流水子表可改；第二轮：变更单伪造与审批 SoD、样品错配、库存流水对账、计划检验项目、趋势契约、取样日期政策与延期前置、月份过滤分页、变更条件输入路径）；离线契约 **321/321**、`pytest 329 passed`、前端类型检查与构建通过；**第二轮 10 项已补做实机逐项验证**并**负向回归 9/9 通过**。已提交 `e447f97` 并同步生产 `/hbos-lims`（备份 `【内部备份标识已省略】`）。上线后 Owner 验收发现的稳定性工作台「待 R8B~R8D」占位文案（KPI 卡 + 整块面板）已修复——后端补样品/时间点/结果真实计数与时间点执行结构，前端 KPI 6→8 张；侧边栏「取样与检测计划 / 结果录入与趋势」角标改接真实数据（原为原型遗留硬编码 4/3 且恒显红色，提交 `6e06155`）（提交 `b61f83d`，已同步生产）。趋势摘要产品/检验项目下拉控件宽度补丁已同步生产，生产发布脚本 pytest **342/342**、`build:prod` 和 17 条 HTTP 冒烟通过，并完成生产浏览器复测（备份 `【内部备份标识已省略】`）。主文档 `docs/milestones/M2_R8J_稳定性板块审查与修复.md`。

前一子轮：M2-R8I（稳定性前端接入：结果与趋势 + 报告与有效期 + 变更·稳定性室·设备）**DONE / 待 Owner 审查**。5 张 Script Report 物化（方案 6 张全部就位）、`api/stability.ts` +64 函数、3 视图重写接真实后端、演示层退役。验证：离线 311/311、报表实机渲染、浏览器读写全链与角色显隐、375px 无溢出。**稳定性板块 7 视图全部接入真实后端**。未部署生产。主文档 `docs/milestones/M2_R8I_稳定性剩余三视图前端接入.md`。

前一子轮：M2-R8C（稳定性后端：结果、趋势评估与报告）**DONE / 待 Owner 审查**。2 DocType（Result / Report）+ 2 状态机 + `Timepoint Item.current_result` 补建；结果 9 动作 + 报告 8 动作 + 只读 6 接口 + ICH Q1E 外推助手；六步原子切换生效指针、修订不改旧版、作废按必检项目粒度重开、显著变化双套判定（基线按储存条件隔离）、趋势线不含统计控制限；`SCOPED_ACTION_ROLES` 同名动作按 DocType 作用域授权。实机修复 2 项缺陷（六步切换漏持久化 `is_current` 致第三态；非专项报告填客户仅被 Link 校验拦截）。验证：离线 288/288、实机 34/34、R8B 回归 40/40。未部署生产。主文档 `docs/milestones/M2_R8C_稳定性结果与报告后端.md`。
前一子轮：M2-R8H（稳定性前端接入：样品入箱与台账 + 取样与检测计划）**DONE / 待 Owner 审查**。后端补 3 处（schedule 增三层日期与延期状态、新增跨时间点延期列表接口）；前端新增 22 个接口函数并重写两视图（样品台账 + 详情 + 动作弹窗；月度看板改整月日期列 + 日期链 + 计划台账三层日期 + 延期审批含批准/驳回），标签打印走 Frappe 打印视图（dev 补 `/printview` 代理）。验证：离线 246/246、`vue-tsc` 0 错误、build 成功、浏览器真实会话读写全链与角色门控、375px 三页无溢出。稳定性 7 视图中 4 个已接真实后端。**未部署生产**。主文档 `docs/milestones/M2_R8H_稳定性样品与计划前端接入.md`。

更早子轮：M2-R8G（稳定性前端接入真实 API：工作台 + 考察申请与方案）**DONE / 待 Owner 审查**。后端补 5 个只读接口（`get_stability_products`/`get_stability_master`（doctype 白名单）/`get_stability_protocols`/`get_stability_protocol_detail`/`get_stability_audit`）；前端新增 `src/api/stability.ts`（7 只读 + 14 写 + `ACTION_ROLES`/`canAction`），两视图读 + 写全接、按角色显隐；其余 5 视图标注「演示数据 · 待 R8B~R8D」。修复 2 项 R8A 遗留缺陷（Protocol 缺 `snapshot_frozen` 致冻结守卫失效、命名系列 `-####` 非法致畸形单号）。验证：离线 203/203、实机 28/28、只读 7/7、浏览器真实会话读写全链、`vue-tsc` 0 错误、build 成功、375px 无溢出。**未部署生产**。主文档 `docs/milestones/M2_R8G_稳定性前端接入真实API.md`。

更早前：M2-R8A（稳定性主数据与通知单/方案：后端实现与实机验证）**DONE / 待 Owner 审查**。R8A 启动门禁 7/7 已闭环（Owner 2026-09-16）。在 `hb_lims_app` 落地 10 个 DocType（主数据 4：Product/Condition/Room/Test Item；记录一 Notice；方案 Protocol；子表 4：Test Item Form/Batch/Study Condition/Protocol Item）+ `FLOW_STB_NOTICE`/`FLOW_STB_PROTOCOL` 两条状态机 + 新增 `LIMS QA Manager`/`LIMS QP` 两角色 + 批准后冻结快照与版本链；新增 `stability_contract.py`（纯契约）/`stability_guards.py`（系统字段 + 冻结快照 + 删除拦截守卫）/`stability_service.py`（唯一合法写路径 + SoD + 越权/非法转移审计），DocType 层 6 个 LIMS 角色一律只读（方案 8.6）。实机 `bench --site frontend migrate` 已执行；端到端 + 负向用例 **28/28 通过**、离线契约 **199/199 全绿**。验证中修复 4 项缺陷（非法 fieldtype、`extra_condition_reason` 缺失致 >2 条件不可提交、审计 `log_type` 未入受控枚举、越权/SoD/非法转移/删除未留痕）。本轮未接前端真实 API、未启动 R8B、未改动 R7。主文档 `docs/milestones/M2_R8A_后端实现与实机验证.md`。

更早前：M2-R8F（稳定性板块前端 Vue 复刻与生产部署）**DEPLOYED**。Owner 2026-09-16 已确认测试路径并授权同步生产。在 `frontend/hbos-lims-web` 复刻稳定性 7 视图 + 7 条路由 + 侧栏「稳定性管理」分组 7 入口 + 演示数据层 `src/demo/stabilityDemo.ts`（`TEST-HBOS-M2-STB-*`）+ 样式 `stability.scss` + 3 个共享组件；`vue-tsc` 0 错误、`npm run build` 通过、浏览器 7 路由与 12 个抽屉及 375px 移动端回归通过；生产构建后同步 `/hbos-lims`（备份 `【内部备份标识已省略】`，84 个文件逐字节一致、路由与 chunk 全 200、既有模块无回归）。本轮不创建稳定性 DocType、不改 `hb_lims_app`、不接真实 API，不启动 R8A。主文档 `docs/milestones/M2_R8F_稳定性板块前端Vue复刻与生产部署.md`。

当前阶段：M0 工程启动与上下文治理已完成并封板；M1 产品交付仍在 M1-FIX 功能补漏中，尚未完成（M1-FIX-B3 为 REVIEWING / Owner UI 验收未通过；M1-FIX-B4 为 REVIEWING / Claude PASS，但 Owner 数据链路验收发现后续问题；M1-FIX-B5 为 REVIEWING）；M2-LIMS（实验室信息管理系统板块）已按 Owner 授权启动。

当前目标：M2-R1 至 M2-R4 已 COMPLETED，M2-R5（验证收口）为 REVIEWING；M2-R6（Vue 前端原型与开发流程）已交付交互式 HTML 原型与开发流程文档，进入 REVIEWING，等待 Owner 审查。M2-R7D（留样板块前端 Vue 复刻与生产部署）DEPLOYED：留样方案 rev6 口径定稿（Owner 2026-09-07 确认角色方案 B+SoD、分支策略 b）；R7A（主数据与留样登记 3 DocType + retention_service + 前端两页）已在 m2-r6 交付并测试路径验证；6 视图 Vue 板块已同步生产 `/hbos-lims`（工作台/观察/使用/处理 4 视图已切换真实后端接入，登记台账/产品沿用 R7A API），Owner 2026-09-08 已确认测试路径；R7B（观察管理）/R7C（使用与处理审批）后端已实现并真实验证。M2-R8（稳定性管理板块开发方案）REVIEWING **rev15**（业务依据 v9.0 **已正式生效**，Owner 2026-09-16 确认 11.3-1）：Owner 2026-09-15 提供《稳定性管理》规程全套 5 份文件（新版 v9.0 `SOP-LC-1-00-019` 为主、旧版 05 版差异基线）并授权方案设计；rev1 审核 FAIL（4 P0 + 6 P1）后 rev2 修订（Timepoint 提升为独立主 DocType、补 `FLOW_STB_RESULT`/`FLOW_STB_REPORT` 状态机、批准后冻结快照与版本链、电子签名能力边界更正、数据模型全量显式定义、时间单位统一并补计划检测日期/取整/月末/工作日历、显著变化判定配置化、「控制图」改称「趋势图」、新增 Stability Room / Test Item 主数据、角色身份先定后授权限、逾期纯派生 + 延期审批独立动作）；复审"有条件通过"（5 必修 + 3 补强）后 rev3 修订（结果版本键 `result_version_key` + `is_current` 生效指针、双延期模型 `HBOS Stability Timepoint Delay`、补全 `HBOS Stability Test Item Form` + 5.8 节清单总表、按 DocType 逐一定义的删除拦截 + 子表仅追加、0 月来源 `baseline_doctype`/`baseline_name`、检测日期物理约束与锚定口径、`approve_change_general` 收紧为 QA 线专属、有效期字段拆分，新增 11.3 节 R8A 启动前置门禁）；三轮复审后 rev4 修订 3 P1 + 8 P2 + 9 P3（**P1-1** 0 月点免取样专属口径 `import_zero_month_result` + 校验豁免 + Timepoint 流转分支；**P1-2** 时间点生成触发定稿 + 中间条件生成规则 + `append_conditions` 追加闭环；**P1-3** 变更实施落点新增 7.9 节、Change 补 `supersedes`/`change_scope`、`后评估不通过` 定为终态；另含交叉引用校正、矩阵与审计补全、委外窗口配置化、`ROUND_HALF_UP`、作废后指针与 `revision_no` 定稿、Sample 评估四件套），四轮复审 FAIL 后 rev5 修订 2 P0 + 8 P1（生效指针仅在新版批准后同事务切换、统一 `effective_due_date` 有效截止日、新增 `LIMS QA Manager`、6.3 改全转移覆盖表、Timepoint Item 防重复、年度持续类 Notice 快照链、`append_conditions` 原子化、统一并发锁协议），五轮复审"有条件通过"后 rev6 修订 4 P1 + 5 P2 + 10 P3（补 `mark_for_disposal`/`cancel_disposal` 使「待处理」可达、入箱超期改强制评估四件套、`append_conditions` 补入动作矩阵准入行、门禁 3 时序校正等）；六轮复审 FAIL（2 P0 + 6 P1 + 5 P2）后 rev7 修订（先自身检查逐项核实）：结果状态与生效指针冲突修正（`revise_result` 只建草稿、旧版保持「已批准 + `is_current=1`」，新版批准时同事务六步切换）、期限三层模型与政策硬上限、`record_result` 收紧为 `Timepoint=检测中`、`pre_disposal_status` 快照、`approve_report` 三条硬前置、Report 补 `client`/`seq`/`source_ref`、补全驳回/作废/人日字段、延期历史单一口径，新增 8.6 禁止绕过业务服务与 8.7 违规审计独立持久化）；七轮复审 FAIL（7 P1 + 5 P2）后 rev8 修订（补 `apply_delay`/`reject_delay` 动作并统一到子表 `status`、补 `已批准→已作废` 出口与 `void_result` 触发的时间点重开、`Sample Log` 补「受托转出」并统一销毁监督人、Notice 补驳回/取消字段、Report 改 `source_doctype`+`source_name`、8.3 按 DocType 列出终止动作、期限审批口径纳入 11.3 门禁第 7 项）；八轮复审 FAIL 后 rev9 修订 3 P1 + 3 P2（删「已完成 → 终态」消除 Timepoint 状态机矛盾并登记系统动作 `reopen_timepoint`、重开判定改按必检项目粒度、启动门禁口径统一为 11.3 的 5 项、Report 映射表移位、8.6 措辞更正），九轮复审 FAIL 后 rev10 修订 1 P1 + 2 P2（`void_result` 行动作行改按必检项目粒度重开、`report_period_key` 纳入 `source_doctype` 消歧并补 `seq` 并发锁），十轮复审 FAIL 后 rev11 修订 4 P1 + 4 P2（`reopen_timepoint` 补"仅当 `Timepoint.status=已完成` 才调用"守卫、延期日期全链校验 `planned≤requested≤approved≤policy_latest`、8.6 权限隔离改为"DocType 保留 create/write 仅系统字段受控"、专项报告 `seq` 锁指定产品行 + 有上限重试、`report_period_key` 改用规范化 `client_code`、`mark_superseded` 补语义界定），十一轮复审 FAIL 后 rev12 修订 1 P0 结论确认 + 3 P1 + 2 P2（11.3 门禁维持"5 项未闭环、不得启动 R8A"；`apply_delay`/`approve_delay` 矩阵行补日期链、`reopen_timepoint` 矩阵行补状态守卫、映射规则与唯一性总表 `client` 统一为 `client_code`；`client_code` 定案五条规则、8.6 新增运行期一致性扫描同步 8.1/8.4/门禁 16），十二轮复审 FAIL 后 rev13 修订 1 P0 结论确认 + 2 P1 + 1 P2（11.3 门禁维持"5 项未闭环、不得启动 R8A"；`client_code` 重定案——删除"临时用名称规范化"回退路径、新增 `customer` Link 字段且 `client_code` 唯一来源为 ERPNext `Customer` 文档名；台账修复 PROJECT_STATUS "M2-R5 closeout"/旧编号口径；业务依据统一为 v9.0 拟执行依据待生效确认、v8.0 仅作历史差异基线）。定案 14 主 + 8 子 DocType（= 22）、8 条状态机、8 项强校验点、ICH Q1E 外推助手，拆 R8A~R8E，并新增跨轮验收门禁 6 类；Owner 已确认两项范围边界（全量 12 模块、稳定性室手工记录纳入本板块）；**Owner 2026-09-15 决策两项**：电子签名走路线 ①（操作签名 + 审计追踪，不等同 GMP 合规电子签名，GMP 合规电子签名由平台后续统一专项、各板块统一接入）；R8 工作分支为新建 `m2-r8`。**R8A 已启动并完成**（10 DocType + 2 状态机 + 2 角色 + 冻结快照/版本链；实机 28/28、离线 199/199）；R8B~R8E 待逐轮启动。M1-FIX-B3 / B4 / B5 为并行未决事项，不 closeout，不阻塞 M2-LIMS。M1-FIX-C/D/E 未启动。
M2-R6A（样品登记动态表单设计）随 M2-R6 并行 REVIEWING，等待 Owner 审查。
M2-R6B（检验结果台账双模式设计）REVIEWING，Owner 已确认原型与交互（明细台账 + 样品表每样品种类一表），设计文档待审查。
M2-R6C（检验结果台账 Vue 复刻与生产部署）DEPLOYED，双模式已复刻进 Vue 并上线生产，Owner 已确认测试路径。

当前已在用户授权范围内安装 HRMS，并完成 Frappe HR 图标、基础 HR 模块和 Roster 页面的前端资源修复验证。M0-R3E HRMS 环境可复现性收口已完成并通过 Codex 审查，M0 整体状态为 COMPLETED。

M0-REMOTE 已完成 GitHub Private remote 创建、`origin` 绑定和 `main` 首次 push。M1-R0 已完成方案和诊断并通过 Codex 独立审查；M1-R1 已完成只读对象模型验证记录，并已通过 Codex 独立审查，状态为 COMPLETED。M1-R2 已完成配置试运行方案设计，并已通过 Codex 独立审查，状态为 COMPLETED。M1-R3 已创建部分 `TEST-HBOS-M1R3-` 虚构测试数据；Codex 审查 PASS 后，M1-R3 最终状态收口为 BLOCKED。M1-R3A 已通过 Codex 审查并收口为 COMPLETED。M1-R3B 已通过 Codex 审查并收口为 COMPLETED。M1-R3B-FIX 已通过 Codex 审查并收口为 COMPLETED。M1-R3C 已新增 `TEST-HBOS-M1R3C-*` 虚构 TEST 数据；M1-R3C 已通过 Codex 审查并收口为 COMPLETED，结论为 PARTIAL / GAP_IDENTIFIED。M1-R3D 已通过 Codex 审查并收口为 COMPLETED。M1-R3E 已通过 Codex 审查并收口为 COMPLETED。M1-R3F 已通过 Codex 审查并收口为 COMPLETED。M1-REQ-DESIGN-DRAFT 为 COMPLETED。M1-R4 为 COMPLETED，已通过 Codex 审查并收口。M1-R5 为 COMPLETED，已通过 Codex 审查并收口。M1-R6A 已通过 Codex 审查并收口为 COMPLETED。M1-R6B 为 COMPLETED。M1-R6C 为 COMPLETED（已通过 Codex 审查并 closeout）。M1-R7 为 COMPLETED（已通过 Codex 审查并 closeout）。M1 历史 closeout 已完成，但 Owner UI 验收发现产品功能缺口，因此当前 M1 产品交付仍处于 M1-FIX IN_PROGRESS。M1-FIX-B 已创建轻量 `hb_attendance_app`、导入日志和 `海滨考勤工作台`，并使用 Owner 本地真实 Excel 完成导入闭环验证；M1-FIX-B-FIX 已补齐页面导入与中文体验；M1-FIX-B4 已收敛运行态入口主线；M1-FIX-B5 已核查真实 Employee / Employee Checkin / Attendance / 月度暂存数据链路，新增月度汇总暂存报表并增强 HBOS 报表过滤；真实 Excel、真实员工清单和导入产物不提交 Git。M2-LIMS 已启动：M2-R1 已创建 `hb_lims_app` 骨架（hooks / config / public logo / after_migrate 幂等同步 3 个 LIMS 角色、`海滨LIMS工作台` Workspace、Sidebar 与桌面图标），已安装到本地 `frontend` site，离线契约测试 8/8 全绿；M2-R2 至 M2-R4 已收口为 COMPLETED，M2-R5 验证收口进入 REVIEWING（全量演练 19/19、11 项验收、离线测试 109/109）。M2-R6 已交付 Vue 前端原型与开发流程（`docs/frontend/M2_LIMS_Vue前端原型.html` + `docs/frontend/M2_LIMS_Vue前端开发流程.md`），进入 REVIEWING，未创建 Vue 工程、未接真实 API。当前不接飞书真实写入，不实现 SSO；不在原型审查通过前实现前端驾驶舱。
M2-R6A 已交付样品登记动态表单设计（`docs/frontend/M2_R6A_样品登记动态表单设计.md` + 原型 `#sample` 动态表单交互），样品类型 / 检验优先级为下拉决策条、9 类整表单切换，进入 REVIEWING，未创建 Vue 工程、未接真实 API。
M2-R6B 已交付检验结果台账双模式设计
M2-R6C 已交付检验结果台账双模式 Vue 复刻：`ResultLedgerView.vue` 明细台账 + 样品表（真实 Frappe API 聚合、只读投影、superseded 链过滤），判定/状态筛选；后端 `get_result_ledger` 聚合 API + `workflow_contract` 注册，离线 114/114 全绿；生产构建部署并验证，Owner 已确认测试路径。
M2-R6D 已交付合规审计日志：后端 `HBOS Audit Log` DocType（write-once+sha1 防篡改）+ hooks doc_events 全量捕获 + `get_audit_log` 查询 + 业务埋点，前端合规组新增 合规审计日志 入口 + /audit-log + `AuditLogView.vue`；离线契约 123/123 全绿；已上线生产，Owner 已确认测试路径。另修复生产部署错配（index.html 与 assets 新旧哈希错配致个别页面 404）——root 清旧 assets 后重新部署最新干净 dist（39 资产与本地一致、全引用 200+正确 MIME），nginx 加 SPA fallback 修 /hbos-lims history 404。（`docs/frontend/M2_R6B_检验结果台账设计方案.md` + 原型 `#ledger` 双模式交互）：明细台账（受控记录视角，样品卡片 + 检验项目逐行 + 下钻抽屉签名/修订/审计）+ 样品表（每样品种类一张表、一行一个批次、首列序号、次列样品批号，左侧按类型分组可收缩下拉列表）；Owner 已确认原型与交互，进入 REVIEWING，设计文档待审查；后端 `HBOS Ledger Template` / `get_result_ledger` 落地设计待实现轮另行规划，未创建 Vue 工程、未接真实 API。
M2-R6C 已交付检验结果台账 Vue 复刻与生产部署：`ResultLedgerView.vue` 复刻双模式（明细台账 + 样品表），数据来自真实 Frappe API（HBOS Sample / Test Result / COA / Result Revision 聚合、只读投影、superseded 链过滤、修订/审计摘要）；新增判定列 + 记录状态列筛选、记录状态语义配色；`vue-tsc` 0 错误；生产构建 `npm run build:prod` 已同步至容器 `hbos-m0-r3a-frontend-1`（备份 `【内部备份标识已省略】`），生产 URL `http://localhost:8080/hbos-lims/` HTTP 200 验证通过，Owner 已确认测试路径效果；本轮未新建 DocType、未改后端业务方法。

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
M2-R6D 合规审计日志 + 生产部署错配修复 DEPLOYED（write-once 审计日志已上线生产，Owner 已确认测试路径）。
M2-R7D 留样板块前端 Vue 复刻与生产部署 DEPLOYED（Owner 2026-09-08 已确认测试路径并授权同步生产 `/hbos-lims`）：留样方案 rev6 口径定稿（Owner 2026-09-07 确认角色方案 B+SoD、分支策略 b，m2-r6 为 M2 延伸工作线）；R7A（主数据与留样登记 3 DocType + retention_service + 前端两页）已在 m2-r6 交付并测试路径验证；按设计稿在 Vue 工程落地 6 视图（工作台/登记台账/产品/观察/使用/处理），工作台/观察/使用/处理 4 视图已切换真实后端接入，登记台账/产品沿用 R7A API；`vue-tsc` 0 错误、生产构建成功并同步 `/hbos-lims`（备份 【内部备份标识已省略】）。R7B（观察管理）/R7C（使用与处理审批）后端已实现并真实验证。方案主文档 `docs/milestones/M2_R7_留样管理板块开发方案.md`。
M2-R8 稳定性管理板块开发方案 REVIEWING **rev15**（业务依据 v9.0 **已正式生效**，Owner 2026-09-16 确认 11.3-1）（Owner 2026-09-15 授权并确认两项范围边界：全量 12 模块、稳定性室手工记录纳入本板块）：以《稳定性管理》v9.0 为第一业务依据（旧版 05 版为差异基线），技术路线 Frappe 原生化，rev1 审核 FAIL 后 rev2 修订 4 P0 + 6 P1，复审"有条件通过"后 rev3 修订 5 必修 + 3 补强、rev4 修订 3 P1 + 8 P2 + 9 P3，四轮复审 FAIL 后 rev5 修订 2 P0 + 8 P1，五轮复审"有条件通过"后 rev6 修订 4 P1 + 5 P2 + 10 P3（补 `mark_for_disposal`/`cancel_disposal` 使「待处理」可达、入箱超期改强制评估四件套、`append_conditions` 补入动作矩阵、门禁 3 时序校正），六轮复审 FAIL 后 rev7 修订 2 P0 + 6 P1 + 5 P2（结果状态与生效指针冲突修正、期限三层模型与政策硬上限、`record_result` 收紧为 `Timepoint=检测中`、`pre_disposal_status` 快照、`approve_report` 三条硬前置、Report 补 `client`/`seq`/`source_ref`、补全驳回/作废/人日字段、延期历史单一口径，新增 8.6/8.7），七轮复审 FAIL 后 rev8 修订 7 P1 + 5 P2，八轮复审 FAIL 后 rev9 修订 3 P1 + 3 P2（Timepoint 状态机矛盾消除 + `reopen_timepoint` 登记、重开判定按必检项目粒度、启动门禁口径统一为 11.3 的 5 项、Report 映射表移位、8.6 措辞更正），九轮复审 FAIL 后 rev10 修订 1 P1 + 2 P2（`void_result` 行改按必检项目粒度重开、`report_period_key` 纳入 `source_doctype` 消歧并补 `seq` 并发锁），十轮复审 FAIL 后 rev11 修订（`reopen_timepoint` 补"仅已完成才调用"守卫、延期日期全链校验、8.6 权限隔离更正、`seq` 锁指定产品行、`report_period_key` 改用 `client_code`、`mark_superseded` 语义界定），十一轮复审 FAIL 后 rev12 修订 1 P0 结论确认 + 3 P1 + 2 P2 补强（11.3 门禁维持"5 项未闭环、不得启动 R8A"；`apply_delay`/`approve_delay` 矩阵行补日期链、`reopen_timepoint` 矩阵行补状态守卫、映射规则与唯一性总表 `client` 统一为 `client_code`；`client_code` 定案五条规则、8.6 新增运行期一致性扫描同步 8.1/8.4/门禁 16），十二轮复审 FAIL 后 rev13 修订 1 P0 结论确认 + 2 P1 + 1 P2（11.3 门禁维持"5 项未闭环、不得启动 R8A"；`client_code` 重定案——删除"临时用名称规范化"回退路径、新增 `customer` Link 字段且 `client_code` 唯一来源为 ERPNext `Customer` 文档名；台账修复 AI_CONTEXT rev11 残留与 PROJECT_STATUS "M2-R5 closeout"/旧编号口径；业务依据统一为 v9.0 拟执行依据待生效确认、v8.0 仅作历史差异基线），十三轮复审 FAIL 后 rev14 修订 1 P0 结论确认 + 3 P1 + 1 P2（11.3 门禁维持「5 项未闭环、不得启动 R8A」；`client_code` 收紧为始终只读派生 + 硬校验 `client_code == customer.name`、删「带出后可改」；格式约束落 ERPNext `Customer` 主数据命名规范、删运行时隐式规范化；`README` 旧待确认口径更正为 11.3-1/2/4/5/7、台账补 v9.0 拟执行标注；`report_period_key` 入键成分禁 `#`、非专项报告 `customer`/`client_code`/`seq` 必须为空），十四轮复审 FAIL 后 rev15 修订 1 P0 结论确认 + 2 P1 + 2 P2（11.3 门禁维持「5 项未闭环、不得启动 R8A」；Customer 编码格式补两层可执行保障——validate 钩子强制校验 + R8A 前存量扫描；「规范化 `client_code`」旧措辞统一为 Customer 文档名原值；`client` 展示字段只读派生 `customer.customer_name`；文档头重复修订史清理），定案 14 主 + 8 子 DocType（= 22）、8 条状态机、动作角色矩阵（沿用 R7 方案 B，建议新增 `LIMS QP`）、8 项强校验点、显著变化配置化判定、ICH Q1E 有效期外推助手（只建议不定值）、趋势图（规格限+折线+趋势线）、批准后冻结快照与版本链，拆 R8A~R8E，新增跨轮验收门禁 6 类；电子签名明确定性为操作签名、不等同 GMP 合规电子签名（**Owner 2026-09-15 定路线 ①，GMP 合规电子签名由平台后续统一专项**）；R8 工作分支 **`m2-r8`**；**R8A 已启动并完成**（见本文件当前子轮）；R8B~R8E 待逐轮启动。方案主文档 `docs/milestones/M2_R8_稳定性管理板块开发方案.md`。

## 前端实施流程规范

独立前端（Vue/React 驾驶舱、AI 工作台、复杂交互页面）开发必须遵循"原型先行 + Owner 审查 + 复刻实现 + 功能接入"流程。详见：

- `docs/frontend/FRONTEND_IMPLEMENTATION_GUIDE.md`

核心规则：凡涉及漂亮页面、驾驶舱、AI 工作台、复杂交互页面，必须先使用 `frontend-design` skill 产出原型/视觉方案，Owner 人工审查通过后再进入前端复刻和功能接入。Frappe Desk 后台页面不要强行重做成独立前端。

## 边界提醒

不直接修改 Frappe / ERPNext / HRMS 核心源码。优先使用原生配置、角色权限、DocType、报表、导入、API 和低代码定制。自定义 App 只用于海滨特有规则，不用于重写 HRMS 已有功能。`hb_attendance_app` 已在 M1-FIX-B 经 Owner 授权创建，后续不得擅自扩大为大而全 HR App。`hb_lims_app` 已在 M2-R1 经 Owner 授权创建，MVP 范围限定样品管理、质量标准、检验流程与 COA 报告，不擅自扩大为 12 模块全量 LIMS；**留样板块（M2-R7）已按 Owner 2026-09-04 授权纳入 `hb_lims_app` 范围**（R7 子轮按 Owner 授权推进：R7A/R7D 前端已落地，R7B/C 后端已实现并真实验证、前端已真实接入）；**稳定性板块（M2-R8）已按 Owner 2026-09-15 授权纳入 `hb_lims_app` 范围**（11.3 启动门禁 7/7 已闭环，R8A~R8J 已推进；R8J 联动与审查修复已按 Owner 2026-09-21 授权同步生产，当前待生产路径验收），其余扩展模块仍另行规划。任何飞书真实写入必须由用户明确授权。

任何海滨自定义 App 生成、业务模型实现、真实业务数据配置、飞书真实写入、前端驾驶舱、AI 视频服务实现，以及 Docker volume 删除、site 重建或环境重构，都属于后续轮次或后续明确授权范围。
