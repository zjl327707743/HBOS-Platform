# Current Milestone

## M2-LIMS：实验室信息管理系统板块（当前里程碑）

项目名称：新乡海滨智能运营管理平台。

M2-LIMS 在 HBOS 平台（Frappe/ERPNext 底座）上新增实验室信息管理系统（LIMS）板块，以《海滨药业LIMS系统开发方案》为业务口径（12 模块），参考开源 SENAITE LIMS 的功能结构（仅业务模型参考，不搬代码），自定义 Frappe App `hb_lims_app` 承载。第一版为核心闭环 MVP：样品管理 + 质量标准 + 检验流程 + COA 报告。

## 当前轮次

> 状态校正（2026-09-21 本轮追加）：本轮在已部署 R8J 基线上新增稳定性取样绑定、业务检验结果同步、审查缺陷修复及趋势摘要下拉控件宽度修复，已按 Owner 授权同步生产；生产发布脚本 pytest **342/342**、生产前端 `build:prod` 通过，生产路径 17 个页面/资源冒烟均返回 200，备份为 `【内部备份标识已省略】`，结果页已完成生产浏览器复测。

> 状态校正（2026-09-22）：Owner 已确认并授权侧栏「最近访问」关闭交互同步生产；提交 `934e36a`，完整 pytest **342/342**、前端 `build:prod` 和生产路由/主资源 HTTP 200 冒烟通过，备份为 `【内部备份标识已省略】`。本次为纯前端资产同步，不涉及后端迁移。

> 状态校正（2026-09-24）：M2-R3G「检验流程系统字段守卫」DEPLOYED / 待 Owner 验收（M2-R3/R6 五个 DocType 补齐 R7/R8 已有的系统字段守卫，堵住 `frappe.client.set_value` 直写状态/签署字段绕过服务层状态机与 SoD 的「伪造审批」缺口）。提交 `c8dcfcb`；离线 **404 passed**、实机非特权用户 **9 passed**、部署后经 nginx → gunicorn 的伪造写 HTTP **417** 被拦；已重启 `backend` / `scheduler` / `queue-short` / `queue-long` 生效（未动 `frontend` / `websocket`，未执行迁移）。本轮为 M2-R3/R6 的补漏轮，**不改变**当前子轮 M2-R8K 与 M2-LIMS 里程碑口径；主文档 `docs/milestones/M2_R3G_检验流程系统字段守卫.md`。

当前子轮：M2-R8K（我的待办身份绑定）**REVIEWING / 真实 Frappe 冒烟已通过，待 Owner 测试路径验收**。已完成基于 `frappe.session.user` 的检验 / 稳定性 / 留样跨模块聚合、角色待处理与指派归属区分、Administrator 特判、稳定性项目粒度收敛、六类深链定位、原业务 API 动作调度、个人摘要缓存与前台轮询控制；本轮补修 Frappe fullname / today API、父单权限读取、无读权限降级、稳定性业务覆盖误报、检验批准 SoD 字段、ISO 日期序列化、前端错误态 / 筛选 / 测试默认值与伪造时间。前端单测 7 项、LIMS 后端测试集 395 项、生产构建通过；真实 Frappe 冒烟 1 passed。生产页面已可访问「我的待办」，既有发布来源待核；本次仅同步侧栏资源。提交 `1c55a14` + `3fe0e05`（基线）。主文档 `docs/milestones/M2_R8K_我的待办身份绑定.md`。

> 发布记录（2026-09-23）：侧栏「最近访问」整块移除，提交 `fbb1aee` 并同步生产前端；备份 `【内部备份标识已省略】`，构建文件 SHA-256 **87/87 一致**，生产浏览器已复核待办与留样入口，未执行后端迁移或重启。

当前子轮：M2-R8J（稳定性板块前后端审查与缺陷修复）**DEPLOYED / 待 Owner 测试路径验收**。2026-09-21 后续回滚模拟复现的 **8 项 P1 + 2 项 P2** 已完成修复；离线契约 **321/321**、前端类型检查与构建通过，测试路径浏览器冒烟覆盖变更条件、结果录入与趋势、取样计划及延期派生区域。**已提交 `e447f97` 并同步生产 `/hbos-lims`（备份 `【内部备份标识已省略】`）。上线后 Owner 验收发现的稳定性工作台「待 R8B~R8D」占位文案（KPI 卡 + 整块面板）已修复——后端补样品/时间点/结果真实计数与时间点执行结构，前端 KPI 6→8 张；侧边栏「取样与检测计划 / 结果录入与趋势」角标改接真实数据（原为原型遗留硬编码 4/3 且恒显红色，提交 `6e06155`）（提交 `b61f83d`，已同步生产，备份 `【内部备份标识已省略】`）。**主文档 `docs/milestones/M2_R8J_稳定性板块审查与修复.md`。

前一子轮：M2-R8I（稳定性前端接入：结果与趋势 + 报告与有效期 + 变更·稳定性室·设备）**DONE / 待 Owner 审查**。交付 Script Report ×5 物化（稳定性台账 / 检测进度跟踪 / 年度持续稳定性考察覆盖清单 / 稳定性室温湿度记录查询 / 设备与校准到期清单——**方案 6 张报表全部就位**，有效截止日由服务层派生而非 DB 列）；`api/stability.ts` +64 接口函数与 6.3.5~6.3.8 全量动作角色；重写 3 视图（结果三栏含录入/复核/批准/作废动作 + ECharts 趋势线含线性拟合与在途虚线 + 外推建议卡；报告三栏含 QA 判定有效期批准弹窗与外推助手；Ops 三标签含变更全链按钮/温湿度记录表/设备台账与故障工单动作链）；3 视图横幅改 live、演示层 `stabilityDemo.ts` 356→21 行退役（仅留语义色工具）。实施处置 2 项：报表初版把 `effective_*_due` 当 DB 列→改服务层派生；浏览器首测 417 为 gunicorn 旧模块缓存→HUP 重载后判定一致。证据：离线 311/311、5 张报表非 Administrator 实机渲染、浏览器真实会话写链（结果录入 v3 草稿与 v2 生效共存 / 报告建档含服务端外推建议 / 温湿度写入含上下限快照 / 设备建档→故障→关闭全链）与角色显隐（Analyst 无设备建档、Reviewer 全链）、375px 三页无溢出、残留已清理。**稳定性板块 7 视图至此全部接入真实后端**。**未部署生产**。主文档 `docs/milestones/M2_R8I_稳定性剩余三视图前端接入.md`。

前一子轮：M2-R8C（稳定性后端：结果、趋势评估与报告）**DONE / 待 Owner 审查**。交付 2 个 DocType（`HBOS Stability Result` / `HBOS Stability Report`）+ 2 条状态机（`FLOW_STB_RESULT` / `FLOW_STB_REPORT`）+ `Timepoint Item.current_result`（兑现 R8B 前向兼容承诺）；服务方法：结果 9 动作 + 报告 8 动作 + 只读 6 接口 + ICH Q1E 外推助手 + 客户存量扫描 + `scheduler_scan` 补趋势逾期项。核心口径：`result_version_key` 唯一 + `is_current` 生效指针、**六步原子切换**（Timepoint 行锁内，`mark_superseded` 系统内部子步骤幂等）、修订不改旧版（P0-1）、作废生效件同事务清指针并按**必检项目粒度**重开时间点（门禁 19）、显著变化双套判定（基线按储存条件隔离选取，方案 7.4）、趋势线**不含统计控制限**（QA 口径待确认）、报告防重键（专项 `seq` 服务端分配 + 冲突重试）与 QA 判定有效期分离。新增 `SCOPED_ACTION_ROLES`：R3 检验流程与稳定性结果 4 个**同名动作**（submit/review/approve/revise_result）按 DocType 作用域分别授权，防互相放宽。审计补 15 类新事件并全量入 §8.1 受控枚举；`Customer.validate` 注册命名规范校验（仅当已被稳定性专项报告引用时生效，不干扰非稳定性客户）。实机验证发现并修复 2 项自身缺陷：①六步切换第 (b) 步漏持久化 `is_current` 产生「已修订+current=1」第三态（违反门禁 11/15）；②非专项报告填客户仅被 Link 校验拦截、真实合规客户可绕过（补 `check_report_scope`）。证据：离线契约 **288/288** 全量、实机端到端 **34/34**（非 Administrator 全链 + SoD + 越权 + 删除拦截）、R8B 回归 **40/40**、验证残留已清理。前端「结果录入与趋势」「报告与有效期」仍为演示数据，接入另起一轮。**未部署生产**。主文档 `docs/milestones/M2_R8C_稳定性结果与报告后端.md`。

前一子轮：M2-R8B（稳定性后端：样品、时间点与取样检测计划）**DONE / 待 Owner 审查**。交付 5 个 DocType（`HBOS Stability Sample` + `Sample Log`；`HBOS Stability Timepoint` + `Timepoint Item` + `Timepoint Delay`）+ 3 条状态机（`FLOW_STB_SAMPLE` / `FLOW_STB_TIMEPOINT` / 延期子表机）+ 21 个动作方法 + 4 个只读接口 + `scheduler_scan` + 标签 Print Format「HBOS 稳定性样品标签」+ Script Report「取样与检测计划看板」。核心口径：`current_qty` 单一写路径与四步锁（锁顺序固定 Sample → Timepoint）、时间点生成幂等可重跑（登记先提交、生成失败只告警不回滚）、延期三段流程与**四段日期链全链校验**、逾期纯派生不改状态。Result（R8C）依赖处做**前向兼容守卫**（`complete_testing` 无已批准结果即拒绝、`Timepoint Item.current_result` 按 R8A 先例不建悬空 Link、`append_conditions` 待 R8D 变更单）。实施中发现并处置 4 项方案缺口：①「送样 ≤ 全检样 3 周」强校验**无承载字段**（补 `send_date`/`full_test_sample_date`）；②委外窗口 `outsourced_test_window_days` **未定义存放位置**（落 Product）；③`complete_sampling` 的审计事件「取样完成」**不在 §8.1 受控枚举内**（方案自身不一致，已全量对差补入）；④标签目录名与 Frappe 标准 Print Format 的 scrub 定位不符（改名）。标签尺寸：**读了附件一原件，原件未给物理尺寸**（A4 表格，内容宽 82.6mm），用 82.6×55mm 并集中在模板一处待 Owner 确认实物规格。证据：离线契约 **244/244**、实机端到端 **40/40**、补充验证 **10/10**（含门禁 16① 表单守卫、门禁 1 DB 唯一约束、门禁 16③ 低层直写可检出）。本轮**只做后端 + 标签 + 报表**，两个视图的前端接入另起一轮；**未部署生产**。主文档 `docs/milestones/M2_R8B_稳定性样品与时间点后端.md`。

更早子轮：M2-R8G（稳定性前端接入真实 API：工作台 + 考察申请与方案）**DONE / 待 Owner 审查**。把 R8F 的演示数据前端接到 R8A 后端：后端补 5 个只读接口（`get_stability_products` / `get_stability_master`（doctype 白名单）/ `get_stability_protocols` / `get_stability_protocol_detail` / `get_stability_audit`，4 个新动作已注册角色）；前端新增 `src/api/stability.ts`（7 只读 + 14 写 + `ACTION_ROLES`/`canAction`），重写「稳定性工作台」与「考察申请与方案」两视图（读 + 写全接：建档 / 提交 / QC 确认 / 批准 / 驳回 / 取消 / 关闭 + 方案起草 / 提交 / 审核 / 批准 / 驳回 / 作废），按钮按会话角色显隐（后端仍为硬校验）；其余 5 视图保留演示数据但明确标注「演示数据 · 待 R8B~R8D」，顶部原「R8A 门禁 5 项未闭环」的**过期**提示条删除。验证中修复 2 项 R8A 遗留缺陷：①`HBOS Stability Protocol` **漏建 `snapshot_frozen` 字段**致方案冻结快照守卫恒失效（方案 7.7）；②命名系列 `-####` 写法在本版 Frappe 下**非法**（`set_name_by_naming_series` 无条件追加 `.#####`），实际生成 `HBOS-STB-NOT-2026-####00009` 畸形单号——已改为不含 `#` 的既有约定写法，并清理 4 条钉住旧值的 Property Setter、同步更正方案与门禁包中共 36 处写法。证据：离线契约 **203/203**、R8A 端到端 **28/28**、只读接口 **7/7**、浏览器真实会话走通读 + 写全链与角色门控、`vue-tsc` 0 错误、`npm run build` 成功、375px 三页无溢出。**未部署生产**（先给测试端链接，Owner 确认后再同步）。主文档 `docs/milestones/M2_R8G_稳定性前端接入真实API.md`。

更早前：M2-R8A（稳定性主数据与通知单/方案：后端实现与实机验证）**DONE / 待 Owner 审查**。R8A 启动门禁 7/7 已闭环（Owner 2026-09-16，逐项记录见 `docs/milestones/M2_R8A_启动门禁确认包.md`）。本轮在 `hb_lims_app` 落地 **10 个 DocType**（主数据 4：Product / Condition / Room / Test Item；记录一 Notice；方案 Protocol；子表 4：Test Item Form / Batch / Study Condition / Protocol Item）+ `FLOW_STB_NOTICE` / `FLOW_STB_PROTOCOL` 两条状态机 + 新增 `LIMS QA Manager` / `LIMS QP` 两角色 + 批准后冻结快照与版本链；新增 `stability_contract.py`（纯契约，零 Frappe 依赖）/ `stability_guards.py`（系统字段 + 冻结快照 + 删除拦截守卫）/ `stability_service.py`（唯一合法写路径：通知单与方案全链、SoD、越权与非法转移审计），DocType 层 6 个 LIMS 角色一律只读（方案 8.6）。实机 `bench --site frontend migrate` 已执行（10 个 DocType 与 6 角色全部落库），端到端 + 负向用例 **28/28 通过**、离线契约 **199/199 全绿**（含稳定性 28 项）。验证中发现并修复 4 项缺陷：①`test_method_ref` 字段类型/标签写反（非法 fieldtype 落库）；②`create_stability_notice` 缺 `extra_condition_reason` 入参致 **>2 个条件的通知单无法提交**；③审计 `log_type` 未登记受控枚举致 `register_review` 等直接报错；④越权 / SoD / 非法转移 / 删除尝试**未留痕**（方案 8.7 / 8.3 / 门禁 6、17），已补 `_audit_commit` 独立提交与 `on_trash` 删除拦截。本轮**未接前端真实 API**（R8F 稳定性视图仍为演示数据）、**未启动 R8B**、未改动 R7 代码。主文档 `docs/milestones/M2_R8A_后端实现与实机验证.md`。

更早之前：M2-R8F（稳定性板块前端 Vue 复刻与生产部署）**DEPLOYED**，Owner 2026-09-16 已确认测试路径并授权同步生产。按设计方案与 HTML 原型在 `frontend/hbos-lims-web` 复刻稳定性 **7 视图**（工作台 / 考察申请与方案 / 样品入箱与台账 / 取样与检测计划 / 结果录入与趋势 / 报告与有效期 / 变更·稳定性室·设备）、7 条 `/stability*` 路由、侧栏「稳定性管理」分组 7 入口、演示数据层 `src/demo/stabilityDemo.ts`（`TEST-HBOS-M2-STB-*`）与样式 `stability.scss`；`vue-tsc` 0 错误、`npm run build` 通过、浏览器 7 路由 + 12 个抽屉 + 移动端 375px 回归通过；生产构建 `npm run build:prod` 后同步生产 `/hbos-lims`（备份 `【内部备份标识已省略】`；84 个文件与本地逐字节一致、全路由与 7 个稳定性 chunk 均 200、既有模块无回归）。本轮不创建稳定性 DocType、不改 `hb_lims_app`、不接真实 API（**该轮口径；其后 R8A 已完成后端、R8G 已把工作台与考察申请与方案两视图接入真实 API**）。主文档 `docs/milestones/M2_R8F_稳定性板块前端Vue复刻与生产部署.md`。

更早：M2-R8E（稳定性板块前端设计方案与 HTML 原型）REVIEWING / Owner 已确认原型。交付 `docs/milestones/M2_R8E_稳定性板块前端设计方案.md`、`docs/frontend/M2_R8_稳定性板块前端原型.html`（7 视图）与 `docs/frontend/assets/M2_R8_稳定性工作台设计图.png`；其 Vue 复刻阶段由 M2-R8F 承接。

M2-R1（环境与骨架）：COMPLETED。`hb_lims_app` 已创建并安装到本地 `frontend` site，after_migrate 幂等同步 3 个 LIMS 角色、`海滨LIMS工作台` Workspace、Sidebar 与桌面图标，离线契约测试 8/8 全绿。主文档 `docs/milestones/M2_R1_环境与骨架.md`。

M2-R2（主数据与判定引擎）：COMPLETED。6 个主数据 DocType 已同步到 frontend site（规格命名 `format:{spec_code}-V{version}` 支持多版本）、`result_contract.py` 判定引擎、规格生效校验；离线测试 40/40 全绿；`TEST-HBOS-M2-*` 虚构主数据验证通过（含多版本/重复拒绝/限度校验/生效查询）。主文档 `docs/milestones/M2_R2_主数据与判定引擎.md`。

M2-R3（检验流程闭环）：COMPLETED。5 个事务 DocType（Sample+Item/Task/Test Result/Result Revision）、状态机、业务方法全链、待检任务看板报表已交付；离线测试 73/73 全绿；虚构数据闭环验证 29/29 通过（合格/OOS/修订/权限/报表）。主文档 `docs/milestones/M2_R3_检验流程闭环.md`。

M2-R4（COA 与报表）：COMPLETED。HBOS COA(+Item) + Print Format `HBOS COA` + create_coa / review_coa / publish_coa（PDF 附件归档 + 快照保护）、4 个报表（检验结果清单 / 样品台账 / 审计追踪查询 / COA 发布记录）已交付；离线测试 89/89 全绿；COA 发布链路验证 19/19 通过。主文档 `docs/milestones/M2_R4_COA与报表.md`。

M2-R5（验证收口）：REVIEWING，等待 Owner 和 Claude 审查。全量演练 19/19 通过、11 项验收全部通过、离线测试 109/109 全绿、Workspace 四卡片 13 链接 + 5 快捷入口已落库。审查期间增强：控制面板全面简体中文（Series→编号系列 + zh.csv DocType 名翻译）；侧边导航按业务模块下拉分组（原生 Section Break，样品管理/检验流程/报告管理/质量主数据/审计追踪 5 分组 17 子项）；定位并 workaround Frappe v16.26.3 侧边栏 DocType 项过滤核心 bug（boot_session hook 预置 user_perm_can_read 缓存，不改核心源码）；报表表格列宽拖拽修复（resize-handle 默认 opacity:0 不可见，CSS hover 表头显示手柄恢复原生拖拽与双击自适应，JS 单元格 hover 全文提示）；列表视图列宽拖拽（DocType 列表页 v16 原生不支持，monkey-patch apply_column_widths 注入表头手柄 + localStorage 持久化 + 双击复位，限定 HBOS LIMS 模块）；表单子表网格列宽拖拽（新建样品登记等表单子表列宽由 Bootstrap col-xs-N 固定无拖拽，monkey-patch ControlTable.make + MutationObserver 兜底，注入表头手柄 + localStorage 持久化 + 双击复位，限定 HBOS LIMS 模块）；样品登记默认报表视图（HBOS Sample 设 default_view=Report，打开自动进入报表视图，可切回列表）；表格字段文字居中（LIMS 标记容器内报表 datatable、列表视图、子表网格单元格 text-align:center，非 LIMS 页面不受影响）；列表视图表头/数据错位修复（文字居中下 Subject 列表头与数据行规则不一致致上下错位，数据行施同表头规则对齐）；结果修订记录列表行高异常修复（用户反馈编号与变更字段间出现独立 HBOS-TR-2026- 且行高异常；根因：字段名 result 命中 Frappe 原生 `.frappe-list .result { min-height:200px }` 被撑高至 200px，整行 211px，LIMS 列表行列重置 min-height/height 修复；CSS 资产 URL 无版本号致浏览器磁盘缓存旧版，hooks 资产 URL 加 ?v=2 版本参数强制刷新）。主文档 `docs/milestones/M2_R5_验证收口.md`。审查通过后 closeout，M2-LIMS MVP 整体收口。

M2-R6（Vue 前端原型与开发流程）：REVIEWING，等待 Owner 审查。已交付交互式 HTML 原型（`docs/frontend/M2_LIMS_Vue前端原型.html`，7 个视图，桌面 / 移动端渲染验证通过）与开发流程文档（`docs/frontend/M2_LIMS_Vue前端开发流程.md`）；推荐 Vue 3 + Vite + TypeScript + Pinia + Vue Router + Element Plus + ECharts；API 复用 `lims_service.py` 现有 whitelist 方法与 5 个 Script Report；`frontend-design` skill 当前环境不可用，按项目规则等价人工设计。未创建 Vue 工程、未接真实 API。主文档 `docs/milestones/M2_R6_Vue前端原型与开发流程.md`。
M2-R6A（样品登记动态表单设计）：REVIEWING，等待 Owner 审查。结合 `/hbos-lims/samples` 实际需求，交付 `docs/frontend/M2_R6A_样品登记动态表单设计.md` 与原型 `#sample` 动态表单交互；样品类型 / 检验优先级为顶部 sticky 下拉决策条，每个样品类型各对应一张完整表单，切换下拉即整表单替换（成品 / 原料 / 中间体 / 包装材料 / 工艺用水 / 水 / 环境样品 / 稳定性样品 / 清洁验证样品），桌面 / 移动端渲染验证通过。

M2-R6B（检验结果台账双模式设计）：REVIEWING，Owner 已确认原型与交互。针对"每种样品登记信息类型不同、检验项目不同"与 GMP 数据完整性要求，交付双模式方案：明细台账（受控记录视角，样品卡片 + 检验项目逐行 + 下钻抽屉签名/修订/审计）+ 样品表（每样品种类一张表、一行一个批次、首列序号、次列样品批号，左侧按类型分组可收缩下拉列表）；后端落地设计为 `HBOS Ledger Template` DocType + `get_result_ledger` 聚合 API（只读投影，限度/结果/判定受控可溯源）。主文档 `docs/frontend/M2_R6B_检验结果台账设计方案.md`。

M2-R6C（检验结果台账 Vue 复刻与生产部署）：DEPLOYED，Owner 已确认测试路径效果。将 R6B 双模式复刻进 Vue 工程 `ResultLedgerView.vue`（明细台账 + 样品表，数据来自真实 Frappe API：HBOS Sample / Test Result / COA / Result Revision 聚合、只读投影、superseded 链过滤、修订/审计摘要）；新增判定列 + 记录状态列筛选、记录状态语义配色（放行/批准绿、检验完成/检验中蓝、登记/草稿灰、拒绝/OOS 红）；`vue-tsc` 类型检查 0 错误；生产构建 `npm run build:prod` 后同步至生产容器 `hbos-m0-r3a-frontend-1`（备份 `【内部备份标识已省略】`），生产 URL `http://localhost:8080/hbos-lims/` HTTP 200 验证通过。后端同步：新增 `get_result_ledger` 聚合查询 whitelist（只读投影，返回 样品+受控记录+修订链+COA 报告日期+类型分组，对齐前端 ResultLedgerView，避免前端多路 get_list 拼接），`workflow_contract.py` ACTION_ROLES 注册 `get_result_ledger`（LIMS Analyst/Reviewer/Manager + System 可读）；离线契约测试 114/114 全绿（新增 6 项台账契约）；真实环境跑通（全量 7 样品/17 结果/2 修订/3 COA 日期/分组 + sample_type 与 material 筛选均验证）；backend 容器 gunicorn 已重启加载新代码（kill 误杀主进程后 `docker start` 恢复，容器健康、生产前端 200）。

M2-R6D（合规审计日志 + 生产部署错配修复）：DEPLOYED，Owner 已确认测试路径效果。新增合规审计日志（全量自动捕获 + write-once + 防篡改）：后端新增 `HBOS Audit Log` DocType（log_type/doctype_target/doc_name/action_text/field_changed/old_value/new_value/reason/user/created_at/checksum，permissions 仅 Reviewer/Manager/System 可读无 create/edit/delete 常规权限，写入仅系统钩子内部 insert），`hooks.py` 注册 doc_events 全量捕获创建/修改/删除（HBOS Sample/Task/Test Result/COA/Specification/Sample Type/Test Item），`lims_service.py` 新增 `audit_log` 写核心（sha1 指纹防篡改）与 `get_audit_log` 查询 whitelist（类型/对象/操作人/关键字/时间筛选）及各业务方法埋点（提交质检/复核/批准/修订/放行/拒绝/OOS/仪器使用/规格生效-废止），`workflow_contract.py` 注册 `get_audit_log`；离线契约测试 123/123 全绿（新增 9 项）；真实环境跑通（DocType 建表、事件流、register_sample 自动触发创建事件）。前端：合规组新增 合规审计日志 入口 + `/audit-log` 路由 + `AuditLogView.vue`（事件类型语义色 Pill/对象/操作人/时间/变更前后值/原因/指纹，下钻抽屉含数据完整性）+ getAuditLog。生产部署修复：Owner 反馈「海滨LIMS 已可进入但样品登记异常/审计追踪进不去」，根因为生产 `index.html` 引用旧 bundle `index-Ty0i1qY8.js` 与生产 assets 混 129 个历史旧 chunk（新旧哈希错配致 view chunk 懒加载 404/崩溃）；以 root 清空旧 assets 后重新部署最新干净 dist（主 bundle `index-BnAvve8_.js` + 39 资产与本地逐字节一致），全引用资产 200 + 正确 MIME 验证；注入 nginx SPA fallback（`location ^~ /hbos-lims/` try_files 命中 public/hbos-lims 并 fallback index.html）修 `/hbos-lims` history 404，备份 `frappe.conf.【内部备份标识已省略】`。生产部署机制：前端经 `docker cp dist/.` 覆盖至 `/home/frappe/frappe-bench/sites/frontend/public/hbos-lims/`（先 root 清 assets 防残留），后端经 bind mount 实时生效。

M2-R7（留样管理板块开发方案）：REVIEWING rev6（rev5 后 Claude 终审修订：P1 释放预占绑定本单预占状态、P2 待处理回退补全/审批流逃生口/受托转出落位，P3 六项分轮携带）。Owner 2026-09-07 已确认角色方案 B+SoD（清单第 1 项）与分支策略 b（第 8 项，`m2-r6` 为 M2 延伸工作线，门禁已同步）；余 6 项：第 2/5/6 为 R7A 前核对项，第 3/4/7 按默认值推进。R7 执行进度：R7A（主数据与留样登记 3 DocType + retention_service + 前端两页）已在 m2-r6 交付并测试路径验证；R7B（观察管理）/R7C（使用与处理审批）后端已实现并真实验证；R7D（Vue 前端 6 视图复刻与生产部署）DEPLOYED（见下方 M2-R7D 段）。以 JXH-SOP-LC-1-00-007-09《留样管理规程》全套文件（1 正文 + 4 记录 + 2 附件，Owner 2026-09-04 提供并授权）为第一业务依据，两份桌面方案评审为业务采纳、技术路线 Frappe 原生化。rev3 定案：5 主 DocType + 1 子表（Retention Product（default_uom Select 受控枚举为 UOM 唯一权威）/ Retention Sample + Stock Log 通用库存操作流水 / Observation / Usage Apply / Disposal Apply（qa_manager_required 4/5 级可配））+ 标签 Print Format + 4 报表；数量语义统一（available_qty=current_qty−reserved_qty 派生量不落库）+ 四步锁协议 + 各操作锁内复核；观察批数量校验（同产品同年度 ≤3 批 + 看板 N/3）；审计事件受控枚举 16 类；角色动作矩阵 + 两条 SoD 硬校验；状态机含驳回终态/已转出/qm_approved_at/4-5 级双路径；Sample→留样映射 6 规则成节；scheduler 扫描；R7A~C 验收含三组并发负向用例。rev4 三轮复审修订 9 项（5 P1 + 4 P2）：①confirm_stock 纳入四步锁协议与单一写路径（防并发确认超额预占）；②execute_usage 锁内复核条件修正——本单预占有效性（reserved_qty>=apply_qty）+ 总量守恒（current_qty>=reserved_qty），弃用 available_qty 判本单；③观察批选取并发防护——产品行 FOR UPDATE 锁内计数；④全检量 2 倍自动计算加 UOM 一致性闸（full_test_qty_uom≠default_uom 禁算）；⑤R7A 验收「调整低于预占」用例归位 R7C（预占由使用申请产生），R7A 改测负结存边界；⑥README/AI_CONTEXT/milestones README 补 R7 进度；⑦分支策略（m2-r6 vs m2-lims）列为待确认第 8 项并 M2_START_GATE 加注记；⑧scheduler 由 daily 改 cron（30 0 * * *）；⑨观察批 3 批口径定稿（上限硬校验、不足 3 批弹性允许 + 看板完整性提示）。主文档 `docs/milestones/M2_R7_留样管理板块开发方案.md`。

M2-R7D（留样板块前端 Vue 复刻与生产部署）：DEPLOYED，Owner 2026-09-08 已确认测试路径并授权同步生产。在 `m2-r6` Vue 工程落地 6 视图留样板块（/retention 工作台 + samples/products/observations/usage/disposal），侧栏「留样管理」6 入口；后端 R7A~C（登记/观察/使用/处理 DocType 与 retention_service 全链方法：观察 N/3、审批链、四步锁、SoD、4/5 级、双签/续留、scheduler、审计）已实现并真实库验证（R7B 13/13、R7C 19/19、并发库存确认恰一单成功、合规审计连通核验通过）；工作台/观察/使用/处理四页已切换真实 API（`src/api/retention.ts` + 会话角色 canAction + SoD 提示），演示数据层 `retentionDemo`/`DemoBar` 已移除；`vue-tsc` 0 错误、生产构建并同步 `/hbos-lims`（备份 `【内部备份标识已省略】`），全路由与 bundle HTTP 200。


M2-R8（稳定性管理板块开发方案）：REVIEWING **rev15**，等待 Owner 复审（业务依据为 **v9.0 拟执行依据，生效待确认——11.3-1**；v8.0 仅作历史差异基线）。Owner 2026-09-15 提供公司现行《稳定性管理》规程全套 5 份文件（新版正文 v8.0/v9.0，编码系列 `SOP-LC-1-00-019`；旧版正文 `JXH-SOP-LC-1-00-008-05` 05 版为差异基线；附件一标签、附件二通知单、旧版记录一）并授权稳定性板块方案设计。以新版 v9.0 为第一业务依据，评审两份桌面方案（`【本地私有路径已省略】`、`【本地私有路径已省略】`），技术路线 Frappe 原生化（对齐 R7）。Owner 已确认两项范围边界：①**全量 12 模块**；②**稳定性室管理（温湿度手工记录 + 设备台账 + 故障处理）纳入本板块**，自动监测采集留环境监测模块。rev1 审核 FAIL（4 P0 + 6 P1），rev2 逐项修订：Timepoint 提升为独立主 DocType（唯一键与并发可靠）、新增 `FLOW_STB_RESULT`/`FLOW_STB_REPORT` 状态机、批准后冻结快照与版本链、电子签名能力边界更正（不等同 GMP 合规电子签名）、数据模型全量显式定义、时间单位统一 `time_point_value+unit`、显著变化判定配置化、「控制图」改称「趋势图」、新增 `HBOS Stability Room`/`HBOS Stability Test Item` 主数据、角色身份先定后授权限、逾期纯派生 + 延期审批独立动作。方案定案 **14 主 + 8 子 DocType（= 22）**（Product / Condition / Room / Test Item + Notice / Protocol / Sample(+Sample Log) / Timepoint(+Timepoint Item) / Result / Report / Change / Room Log / Equipment / Fault Ticket(+Fault Sample) + Batch / Study Condition / Protocol Item 共享子表）+ 标签 Print Format + 6 报表 + 8 条状态机 + 动作角色矩阵（沿用 R7 方案 B，建议新增 `LIMS QP`）+ 8 项强校验点 + 显著变化双套判定 + ICH Q1E 外推助手 + 趋势图，拆 R8A~R8E 五子轮；新增第十一节跨轮验收门禁 6 类。**复审结论为"有条件通过"（5 必修 + 3 补强），rev3 已逐项修订**：结果唯一键与修订链冲突改为 `result_version_key`（含版本号）+ `is_current` 生效指针；取样/检测延期拆分为 `HBOS Stability Timepoint Delay` 子表（`delay_type` 区分）；补全 `HBOS Stability Test Item Form` 并新增 5.8 节 DocType 清单总表（全量 **14 主 + 8 子 = 22**）；删除拦截改为按 DocType 逐一定义 + 子表仅追加/禁编辑/禁删行；0 月数据补 `baseline_doctype`+`baseline_name` 追溯到具体 `HBOS Test Result`/COA；补 `actual_test_date ≥ actual_sample_date` 物理约束并定检测 30 天窗口锚定计划检测日期；`approve_change_general` 收紧为 QA 线专属（删 Manager）；有效期字段拆为月数/日期/类型；新增 11.3 节 R8A 启动前置确认门禁。**复审明确暂不建议直接进入完整 R8A~R8E 实施**，须先闭环 11.3 启动门禁。**rev4 按三轮复审意见修订 3 项 P1 + 8 项 P2 + 9 项 P3**：0 月点免取样专属口径（`import_zero_month_result` + 硬校验豁免 + Timepoint 流转分支）；时间点生成定稿为"批准为前置资格 + 入箱登记触发"并补中间条件生成规则与 `append_conditions` 追加闭环；变更实施落点新增 7.9 节（涉方案→Protocol 新版本 / 涉通知单→新 Notice / 涉条件→追加时间点 / 涉样品→新 Sample），`后评估不通过` 定为终态；另含交叉引用校正、矩阵与审计补全、委外窗口配置化、`ROUND_HALF_UP`、作废后指针与 `revision_no` 定稿、Sample 评估四件套等。**四轮复审结论 FAIL（2 P0 + 8 P1），rev5 已逐项修订**：结果生效指针**仅在新版批准后**同事务原子切换（防草稿/待复核结果被报表读到）；统一 `effective_due_date` 有效截止日口径（超过一律拒绝，scheduler 同步）；新增 `LIMS QA Manager` 角色；6.3 动作矩阵重写为全转移覆盖表（六列：动作/转移/角色/前置/签名/审计）；Timepoint Item 补项目防重复与指针归属校验；0 月基线补 `HBOS Stability Result`；年度持续类补 Notice 快照机制与来源链；`append_conditions` 循环解除为变更实施原子事务；统一并发锁协议与锁顺序。11.2 门禁扩至 12 条。**五轮复审结论"有条件通过"（4 P1 + 5 P2 + 10 P3），rev6 已逐项修订**：补 `mark_for_disposal`/`cancel_disposal` 使「待处理」可达（原处置流程断裂）；入箱超 1 个月改**强制评估四件套 + 审计**（原硬拦截严于 SOP）；`append_conditions` 补入 6.3 动作矩阵准入行；门禁 3 时序校正；另修 `submit_notice` 角色、QP 作废权限理由、`cancel_timepoint` 范围与已批准结果处置、FAULT 两处转移、报告防重键专项维度、多条已批准延期取最新等 P2，以及门禁行序、章节标题、基线映射表移位、锁表补 `return_result`、scheduler 补推荐期扫描等 P3。门禁扩至 14 条。**六轮复审结论 FAIL（2 P0 + 6 P1 + 5 P2），rev7 已逐项修订**（先做自身检查逐项核实属实）：**P0-1** 结果状态与生效指针冲突——`revise_result` 只建新草稿、旧版保持「已批准 + `is_current=1`」，新版批准时**同事务六步切换**，`current_result` 约束为 `is_current=1 且 status=已批准`，同 `(时间点,项目)` 在途唯一；**P0-2** 期限三层模型（`planned_due_date` / `policy_latest_due_date` **硬上限** / `approved_due_date ≤ 上限`），超过政策上限**无论有无审批一律拒绝**；**P1-1** `record_result` 收紧为 `Timepoint=检测中`；**P1-2** 补 `pre_disposal_status` 快照、`cancel_disposal` 回退含「已取尽」；**P1-3** `approve_report` 三条硬前置；**P1-4** Report 补 `client`/`seq`/`source_ref`/`period_*` 并重订防重键；**P1-5** 补全 Sample 处置与 Protocol/Report/Change 的驳回/作废/人日字段；**P1-6** 延期历史单一口径 + 禁止批准日期倒退；**P2** 补 Link 目标类型、`Condition.condition_code` unique、`support_docs` 语义更正，新增 **8.6 禁止绕过业务服务** 与 **8.7 违规审计独立持久化**。门禁扩至 17 条。**七轮复审结论 FAIL（7 P1 + 5 P2），rev8 已逐项修订**（先做自身检查逐项核实属实）：**P1-1** 补 `apply_delay`/`reject_delay` 动作并统一到子表 `status`（原引用未定义的 `delay_status`）；**P1-2** 补 `已批准 → 已作废` 出口，`void_result` 作废生效结果时同事务将 Timepoint 回退为「检测中」以支持重录；**P1-3** `Sample Log` 补「受托转出」枚举，销毁监督人统一用 `reviewer`；**P1-4** Notice 补驳回/取消六字段；**P1-5** Report 改 `source_doctype` + `source_name`（Dynamic Link）并补类型映射；**P1-6** 8.3 改为按 DocType 列出各自终止动作；**P1-7** 期限审批口径纳入 11.3 门禁第 7 项；**P2** 双延期表字段名统一、`cancel_disposal` 与门禁 13 补「已取尽」、`approve_at` 改 Datetime、8.6 强化低层写入防绕过、两处入口摘要校正。门禁扩至 19 条。**八轮复审 FAIL（3 P1 + 3 P2）后 rev9 修订**（先自身检查逐项核实）：删「已完成 → 终态」消除 Timepoint 状态机自相矛盾并登记系统动作 `reopen_timepoint`（矩阵／审计／门禁 10 豁免同步）；重开判定改**按必检项目粒度**并补多项目用例；启动门禁口径统一为 11.3 的 5 项（1、2、4、5、7）；Report 映射表移至字段表之后；8.6 末句改"低层直写后果检测与告警"；修复台账中 `M2-R7` 被误改 rev8 的残留与重复摘要。门禁扩至 20 条。**九轮复审 FAIL（1 P1 + 2 P2）后 rev10 修订**：`void_result` 动作行改**按必检项目粒度**重开（原留"整点若无其他生效结果"旧口径，与状态机及门禁 19 冲突）；`report_period_key` **纳入 `source_doctype`** 消歧并补 `seq` 并发锁与冲突重试；里程碑摘要版本校正。门禁扩至 21 条。**十轮复审 FAIL（4 P1 + 4 P2）后 rev11 修订**：`reopen_timepoint` 补"仅当 `Timepoint.status=已完成` 才调用"守卫（部分项目有结果时原写法会产生非法转移）；延期日期补全链校验 `planned ≤ requested ≤ approved ≤ policy_latest`；8.6 权限隔离改为"DocType 保留 create/write、仅系统字段受控"并逐张列明 3 张流水表服务专用写入；专项报告 `seq` 锁指定为产品行 + 有上限循环重试（≤3 次）；`report_period_key` 客户改用规范化 `client_code`；`mark_superseded` 补语义界定（`approve_result` 唯一公开入口、幂等、每次生效切换仅一条审计）。门禁保持 21 条。**十一轮复审 FAIL（1 P0 结论确认 + 3 P1 + 2 P2 补强）后 rev12 修订**（先自身检查逐项核实属实）：**P0** 复核 11.3 门禁维持"5 项（11.3-1/2/4/5/7）未闭环、不得启动 R8A"结论；**P1** `apply_delay`/`approve_delay` 动作矩阵行补日期链两段（`planned≤requested`、`requested≤approved`）、`reopen_timepoint` 动作矩阵行补状态守卫（仅 `已完成` 时调用、已是「检测中」不调用）、5.4.2 映射规则与 5.6 唯一性总表 `client` 统一更正为 `client_code`；**P2 补强**：`client_code` 定案五条（来源 ERPNext `Customer` 或 QA 指定代号 / 格式 ≤40 仅大写字母数字连下划线 / 自动规范化 / 禁 `#` / 批准后锁定）、8.6 新增**运行期一致性扫描**（每日 scheduler 四类不变式 → 审计事件 `一致性异常` → 「一致性扫描异常」清单 → QA 每日复核处置、不自动修复；同步 8.1/8.4/门禁 16）。门禁保持 21 条。**十二轮复审 FAIL（1 P0 结论确认 + 2 P1 + 1 P2）后 rev13 修订**（先自身检查逐项核实属实）：**P0** 复核 11.3 门禁维持"5 项（11.3-1/2/4/5/7）未闭环、不得启动 R8A"结论；**P1-1** `client_code` 规则矛盾重定案——删除 `client` 字段"临时用名称规范化后写入"回退路径（与禁自由文本自相矛盾）、运行态核实 ERPNext `Customer` **无 `customer_code` 字段**（主键即文档名）后**新增 `customer` Link 字段**，`client_code` 唯一来源为 Link 带出的 Customer 文档名（受控主数据、QA 维护、本板块只读引用，补唯一性与维护责任）；**P1-2** 公共台账修复——`AI_CONTEXT` 第 24 行 rev11 残留更正、`PROJECT_STATUS` "下一步路线"行 "M2-R5 审查 closeout" 更正为 REVIEWING、"余第 2/3/4/5/10 项" 旧编号统一引用 **11.3-1/2/4/5/7**；**P2** 业务依据表述统一为"**v9.0 为拟执行依据（生效待确认，11.3-1）**、v8.0 仅作历史差异基线"（文档头 + 2.1 表）。门禁保持 21 条。**十三轮复审 FAIL（1 P0 结论确认 + 3 P1 + 1 P2）后 rev14 修订**（先自身检查逐项核实属实）：**P0** 复核 11.3 门禁维持"5 项（11.3-1/2/4/5/7）未闭环、不得启动 R8A"；**P1-1** 删 `customer` 字段「带出后可改」，定稿 `client_code` **始终只读派生**（草稿期亦不可手改）+ 控制器硬校验 **`client_code == customer.name`**，更正走草稿改选 Link / 提交后作废重录；**P1-2** 格式约束落在 **ERPNext `Customer` 主数据命名规范**（大写字母/数字/`-`/`_`、≤40、禁 `#`）、**删除运行时隐式规范化**（防派生值与主数据不一致及规范化键碰撞）；**P1-3** `README` 「第 1/2/3/5/12 项需优先定案」更正（第 1、12 项已决策，统一引用 11.3-1/2/4/5/7），`PROJECT_STATUS`/`CURRENT_MILESTONE`/`milestones/README` 状态描述补「v9.0 拟执行依据、生效待确认」；**P2** `report_period_key` 入键成分 `product_code`/`source_name`/`client_code` 禁含 `#`、**非专项报告 `customer`/`client_code`/`seq` 必须为空**。门禁保持 21 条。**十四轮复审 FAIL（1 P0 结论确认 + 2 P1 + 2 P2）后 rev15 修订**（先自身检查逐项核实属实）：**P0** 复核 11.3 门禁维持「5 项（11.3-1/2/4/5/7）未闭环、不得启动 R8A」；**P1-1** Customer 编码格式补**两层可执行保障**——本板块 validate 钩子对稳定性客户 Customer 创建/修改按命名正则（大写字母/数字/`-`/`_`、≤40、禁 `#`）强制校验（不改核心源码、不干扰非稳定性客户）+ **R8A 启动前存量扫描**（不合规清单交 QA 处置后专项报告方可引用）；**P1-2** 5.4.2 映射表与 5.6 唯一性总表「规范化 `client_code`」旧措辞统一改为「**Customer 文档名原值**」；**P2-1** `client` 展示字段定稿**只读派生** `customer.customer_name`（任何阶段不可编辑，防档案漂移）；**P2-2** 清理文档头 rev14 时误复制的整段 rev1~rev13 重复修订史（含过时 rev13 口径）。门禁保持 21 条。**Owner 2026-09-15 决策两项**：第 1 项电子签名走**路线 ①**（操作签名 + 审计追踪，不等同 GMP 合规电子签名；GMP 合规电子签名由**平台后续统一专项**、各板块统一接入）；第 12 项 R8 工作分支为**新建 `m2-r8`**。**11.3 启动门禁 7/7 已闭环**（Owner 2026-09-16 逐项确认：v9.0 已正式生效按 v9.0 实现、角色采纳 §6.2 + 新增 `LIMS QA Manager`/`LIMS QP`、取样延期 10% 采甲（该时间点值折算天数 × 10%，`ROUND_HALF_UP`，上限 15 天）、DocType 采纳 5.8（14 主 + 8 子 = 22）、期限口径①需审批②委外窗口可留空）。**R8A 已启动并完成**（见本文件当前子轮）；R8B~R8E 待逐轮启动。主文档 `docs/milestones/M2_R8_稳定性管理板块开发方案.md`。

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
M2-R8E    = REVIEWING（稳定性板块前端设计方案 + HTML 原型，Owner 已确认原型）
M2-R8F    = DEPLOYED（稳定性板块前端 Vue 复刻与生产部署，Owner 2026-09-16 已确认测试路径并授权同步生产 /hbos-lims，备份 【内部备份标识已省略】）
M2-R8     = REVIEWING rev15（方案口径；11.3 启动门禁 7/7 已闭环，R8A 已启动并完成，R8B~R8E 待逐轮启动）
M2-R8A    = DONE / 待 Owner 审查（稳定性主数据 4 + 通知单 + 方案 + 子表 4 后端；实机 28/28、离线 199/199）
M2-R8G    = DONE / 待 Owner 审查（稳定性前端接入真实 API：工作台 + 考察申请与方案；后端 +5 只读接口；修 2 项 R8A 遗留缺陷；未部署生产）
M2-R8B    = DONE / 待 Owner 审查（稳定性样品 + 时间点 + 取样检测计划后端；5 DocType + 3 状态机 + 21 动作 + 标签 + 看板报表 + scheduler；离线 244/244、实机 40/40、补充 10/10）
M2-R8H    = DONE / 待 Owner 审查（样品入箱与台账 + 取样与检测计划接入真实 API；后端 +1 只读接口与 schedule 增列；稳定性 7 视图中 4 个已接真实后端）
M2-R8C    = DONE / 待 Owner 审查（稳定性结果 + 报告后端；2 DocType + 2 状态机 + 六步原子切换 + 外推助手；离线 288/288、实机 34/34、R8B 回归 40/40；R8B 前向守卫已打通）
M2-R8D    = DONE / 待 Owner 审查（稳定性变更 + 稳定性室 + 设备后端；4 DocType + 1 子表 + 2 状态机（方案 8 条全部落地）+ 7.9 原子事务实施 + 一致性扫描；离线 311/311、实机 39/39、R8B/C 回归 40+34）
M2-R8I    = DONE / 待 Owner 审查（稳定性剩余 3 视图前端接入 + 5 张 Script Report 物化；7 视图全部接真实后端；vue-tsc 0 错误、浏览器读写全链与角色显隐、375px 无溢出）
M2-R8D    = DONE / 待 Owner 审查（稳定性变更 + 稳定性室 + 设备后端；4 DocType + 1 子表 + 2 状态机（方案 8 条全部落地）+ 7.9 原子事务实施 + 一致性扫描；离线 311/311、实机 39/39、R8B/C 回归 40+34）
M2-R8I    = DONE / 待 Owner 审查（稳定性剩余 3 视图前端接入 + 5 张 Script Report 物化；7 视图全部接真实后端；vue-tsc 0 错误、浏览器读写全链与角色显隐、375px 无溢出）
M2-R8J    = DEPLOYED / 待 Owner 测试路径验收（2026-09-21 后续回滚模拟复现的 8 项 P1 + 2 项 P2 已修复；离线 321/321、前端类型检查与构建通过；已提交 e447f97 + b61f83d 并同步生产 /hbos-lims）
M2-R7     = REVIEWING rev6（方案口径定稿：角色方案 B+SoD、分支策略 b 已 Owner 确认；R7A 已在 m2-r6 交付 3 DocType+retention_service+前端两页；R7B/C 后端已实现并真实验证）
M2-R7D    = DEPLOYED（Vue 前端 6 视图复刻并同步生产 /hbos-lims，工作台/观察/使用/处理已切换真实后端接入，Owner 2026-09-08 已确认测试路径）
M2-R7B/R7C = 后端已实现并真实验证（Observation / Usage Apply / Disposal Apply DocType + retention_service 全链方法：四步锁 / SoD / 4-5 级 / scheduler / 审计；真实流程 R7B 13/13、R7C 19/19、并发库存确认恰一单成功），R7D 前端已切换真实 API
M1-FIX    = IN_PROGRESS（并行未决，B3/B4/B5 REVIEWING）
M1-FIX-C/D/E = PLANNED / 待 Owner 授权
```

## 下一轮预告

M2-R5 审查 closeout 与 M2-R6 原型审查并行：M2-R5 等待 Owner 浏览器 UI 验收（海滨LIMS 桌面图标 → 工作台 → 样品登记 → 检验全流程 → COA 发布）与 Claude 审查，通过后 M2-LIMS MVP 整体收口；M2-R6 等待 Owner 审查交互式 HTML 原型与开发流程，通过后再进入 Vue 工程初始化与页面复刻。M2-LIMS 其余扩展模块（仪器集成、稳定性、环测、微生物、试剂、OOS 调查、审计追踪通用引擎、国密电子签名）另行规划，不自动启动；留样板块（M2-R7）已按 Owner 授权进入方案审查阶段。
M2-R6A 随 M2-R6 并行审查：Owner 审查动态表单方案与原型交互（含 9 类样品类型切换、必填联动、桌 / 移双端）通过后，将样品登记页纳入 Vue 页面复刻范围。
M2-R6B 随 M2-R6A 并行：Owner 已确认检验结果台账双模式原型（明细台账 + 样品表每样品种类一表）与视觉规范，设计文档待审查；通过后将检验结果台账页纳入 Vue 页面复刻范围，后端 `HBOS Ledger Template` / `get_result_ledger` 落地另行规划。
M2-R6C 已上线生产：检验结果台账双模式 Vue 复刻完成并同步至生产路径，Owner 已确认测试路径效果；`HBOS Ledger Template` DocType / `get_result_ledger` 聚合 API 为待实现规划项，本轮未新建 DocType、未改后端业务方法。
M2-R7D 已 DEPLOYED：留样板块 Vue 前端 6 视图已复刻并同步生产 `/hbos-lims`（备份 `【内部备份标识已省略】`），Owner 2026-09-08 已确认测试路径；工作台/观察/使用/处理 4 视图已切换真实后端接入，登记台账/产品沿用 R7A API。R7B（观察管理）/R7C（使用与处理审批）后端已实现并真实验证（含并发与审计连通）；前端四页已切换真实 API，演示数据源 `retentionDemo` 已移除；观察批 N/3、审批链与逃生口、SoD、四步锁协议均按方案 rev6 落地。留样板块（M2-R7）已按 Owner 2026-09-04 授权纳入 `hb_lims_app` 范围；R7A/R7B/R7C/R7D 落地状态已入台账。

M2-R8H 已 DONE（待 Owner 审查）：「样品入箱与台账」「取样与检测计划」两视图已接入真实后端，稳定性 7 视图中 **4 个已接真实后端**（工作台 / 考察申请与方案 / 样品入箱与台账 / 取样与检测计划）。M2-R8C / M2-R8D / M2-R8I 已 DONE（待 Owner 审查）：**稳定性板块整体交付完成**——后端（22 DocType、8 状态机、6 报表）与前端（7 视图全部接真实 API）全部就位。M2-R8J 联动与审查修复已按 Owner 授权同步生产 `/hbos-lims`：完整 pytest 341/341、生产路径 17 个页面/资源冒烟均返回 200，备份 `【内部备份标识已省略】`。下一步：Owner 生产路径验收。

权威状态文件：

- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/milestones/M2_START_GATE.md`
- `docs/milestones/M2_LIMS_总方案与轮次拆分.md`
- `docs/milestones/README.md`

权威方案文件：

- `docs/milestones/M2_LIMS_总方案与轮次拆分.md`
- `【本地私有路径已省略】`（私有，不入库，业务口径来源）
