# Project Status

项目名称：新乡海滨智能运营管理平台。

## 当前状态

- 当前子轮：M2-R8K（我的待办身份绑定）**REVIEWING / 真实 Frappe 冒烟已通过，待 Owner 测试路径验收**。已完成基于 `frappe.session.user` 的检验 / 稳定性 / 留样跨模块聚合、角色待处理与指派归属区分、Administrator 特判、稳定性项目粒度收敛、六类深链定位、原业务 API 动作调度、个人摘要缓存与前台轮询控制；本轮补修 Frappe fullname / today API、父单权限读取、无读权限降级、稳定性业务覆盖误报、检验批准 SoD 字段、ISO 日期序列化、前端错误态 / 筛选 / 测试默认值与伪造时间。前端单测 7 项、LIMS 后端测试集 395 项、生产构建通过；真实 Frappe 冒烟 1 passed。生产页面已可访问「我的待办」，但该功能的既有生产发布来源未在本次侧栏发布中核定；本次仅同步侧栏前端资产。提交 `1c55a14` + `3fe0e05`（基线）。主文档 `docs/milestones/M2_R8K_我的待办身份绑定.md`。

> 守卫补齐（2026-09-24，分支 `m2-r8`，提交 `c8dcfcb`，**已部署**）：M2-R3/R6 检验流程 5 个 DocType（`HBOS Sample` / `HBOS Sample Task` / `HBOS Test Result` / `HBOS COA` / `HBOS Specification`）按方案 8.6 保留 DocType 层 create/write，但**缺 R7/R8 已有的系统字段守卫**——状态与签署字段可经 `frappe.client.set_value` / 通用 `frappe.client.insert` 直写，绕过 `lims_service` 的状态机、SoD、锁协议与电子签名写入（即伪造审批；实测 `HBOS Test Result` 的 `result_status` 不在 `RESULT_LOCKED_FIELDS` 内，控制器拦不住，而对 LIMS Analyst / Manager 有 write 权限）。本轮按 R8 既有机制补齐：`workflow_contract` 新增 5 个字段集（状态 + 签署 + 版本链，共 26 字段）、新增中性入口 `guards.py` 再导出 `stability_guards.guard_system_fields`（实现唯一，未动 R8 文件与契约测试）、5 个控制器在 `validate()` 接线、`lims_service` 的 23 个保存点补 `doc.flags.allow_system_fields = True`。验证：离线 **404 passed**（原 395 + 新增 9 项契约，含"受守卫 DocType 每个保存点必有放行标记"的防回归扫描）；实机非特权用户 **9 passed**（正向全链 建标准→生效→登记→生成任务→分配→开始检验→提交→复核→批准→生成 COA→QA 审核→发布→样品放行，角色 LIMS Manager / Analyst / Reviewer 真实切换；负向 7 项直写与伪造直插全部被拦；对照 1 项非系统字段仍可直写）。验证数据已清理（5 个 DocType 与 COA 附件 0 残留），审计留痕按 append-only 设计保留。**部署（2026-09-24）**：已重启 `backend` / `scheduler` / `queue-short` / `queue-long` 加载新代码（代码走 bind mount、无 DocType 变更故未执行 `bench migrate`；未动 `frontend` / `websocket`，规避 nginx SPA fallback 与容器内 assets 软链的重注入连带风险）；部署后经 **nginx → gunicorn** 以 `r7c-mgr@test.local`（LIMS Manager，非特权）持 API 凭据真实发起伪造写——改样品/标准 `status` 均返回 **HTTP 417**（`_exc_source: hb_lims_app`），对照组改 `remarks` 返回 200，事后核对数据未篡改，临时凭据已清空；部署后 HTTP 冒烟 17/18（唯一 403 为未认证调用 `get_csrf_token`，属预期）。本轮口径为窄口径，未纳入另两项相邻缺口：M2-R3 无删除拦截（受控检验记录可被真删）、无 8.6 运行期一致性扫描（低层直写无检出手段）。主文档 `docs/milestones/M2_R3G_检验流程系统字段守卫.md`。

> 发布记录（2026-09-23）：按 Owner 授权移除侧栏「最近访问」整块，代码提交 `fbb1aee`，仅同步前端静态资源；生产备份 `【内部备份标识已省略】`。发布后前端构建文件与生产逐项 SHA-256 校验 **87/87 一致**；生产浏览器复核该区块已消失、「我的待办」角标/列表和留样入口正常。未执行后端迁移或服务重启。

> 状态校正（2026-09-21 本轮追加）：上方 M2-R8J 的 DEPLOYED 现包含本轮已授权发布的“业务检验结果 → 稳定性结果与趋势”联动、审查缺陷修复及趋势摘要下拉控件宽度修复；生产发布脚本 pytest **342/342**、生产前端 `build:prod` 通过，生产路径 17 个页面/资源冒烟均返回 200，备份为 `【内部备份标识已省略】`，结果页产品/检验项目下拉已完成生产浏览器复测。

> 状态校正（2026-09-22）：Owner 已确认并授权侧栏「最近访问」关闭交互同步生产；提交 `934e36a`，前端构建与完整 pytest **342/342** 通过，`/hbos-lims/`、`/retention`、`/specs`、`/tasks` 及新构建主资源 HTTP 冒烟均返回 **200**，生产备份为 `【内部备份标识已省略】`。本次为纯前端资产同步，不涉及后端迁移。

- 当前子轮：M2-R8J（稳定性板块前后端审查与缺陷修复），**DEPLOYED / 待 Owner 测试路径验收**。两轮修复共 **3 + 8 项 P1** 与 **2 + 2 项 P2**：第一轮（报告 `conclusion` 无写入路径致报告链断裂 / 结果页缺「提交」致工作流 UI 走不通 / `complete_testing` 角色门禁被绕过 / `Equipment.status` 无守卫 / 故障流水子表行可被 LIMS 角色增删改）；第二轮经 93 项回滚模拟复现的 10 项（① Analyst 通用 `insert` 伪造「已批准」变更单 ② 变更审批 SoD 缺失 ③ 样品可错配产品 ④ 受托转出流水无法对账 ⑤ 计划接口未返回 `test_items` 致录入下拉为空 ⑥ 趋势接口数据契约不一致 ⑦ 取样日晚于计划日无批准延期也可继续 ⑧ `complete_sampling` 缺政策硬上限校验 ⑨ 月份过滤在分页后执行 ⑩ 变更条件无完整输入路径）。离线契约 **321/321**、`pytest 329 passed`、`vue-tsc` 0 错误 + 构建通过；**第二轮 10 项已补做实机逐项验证**（非 Administrator 真实用户，含 SoD / 越权 / 错配 / 政策上限 / 流水对账 / 数据契约）并**负向回归 9/9 通过**。已提交 `e447f97` + `b61f83d` 并同步生产 `/hbos-lims`（备份 `【内部备份标识已省略】`；清理 58 个历史残留 chunk 后远端 85 文件与本地 `dist` 文件清单及 md5 逐条一致；生产路径浏览器读写全链走通）上线后 Owner 验收发现的稳定性工作台「待 R8B~R8D」占位文案（KPI 卡 + 整块面板）已修复——后端补样品/时间点/结果真实计数与时间点执行结构，前端 KPI 6→8 张；侧边栏「取样与检测计划 / 结果录入与趋势」角标改接真实数据（原为原型遗留硬编码 4/3 且恒显红色，提交 `6e06155`）（提交 `b61f83d`，已同步生产，备份 `【内部备份标识已省略】`）；**P3 加固项 7 条已识别未处置**。主文档 `docs/milestones/M2_R8J_稳定性板块审查与修复.md`
- 前一子轮：M2-R8I（稳定性前端接入：结果与趋势 + 报告与有效期 + 变更·稳定性室·设备），**DONE / 待 Owner 审查**。交付 Script Report ×5 物化（稳定性台账 / 检测进度跟踪 / 年度覆盖清单 / 温湿度记录查询 / 设备与校准到期清单——方案 6 张报表全部就位，有效截止日由服务层派生）；`api/stability.ts` +64 接口函数与 6.3.5~6.3.8 全量动作角色；重写 3 视图（结果三栏含录入/复核/批准/作废 + ECharts 趋势线与外推建议；报告三栏含 QA 判定有效期批准与外推助手；Ops 三标签含变更全链/温湿度/设备与故障）；3 视图横幅改 live、演示层 `stabilityDemo.ts` 356→21 行退役。实施处置 2 项（报表初版把 effective_*_due 当 DB 列→改服务层派生；浏览器首测 417 为 gunicorn 旧模块缓存→HUP 重载后判定一致）。验证：离线 311/311、5 张报表非 Administrator 实机渲染、浏览器真实会话写链（结果录入 v3 草稿/报告建档/温湿度写入/设备+故障全链）与角色显隐（Analyst 无设备建档、Reviewer 全链）、375px 三页无溢出。**稳定性板块 7 视图至此全部接入真实后端**。**未部署生产**。主文档 `docs/milestones/M2_R8I_稳定性剩余三视图前端接入.md`
- 前一子轮：M2-R8C（稳定性后端：结果、趋势评估与报告），**DONE / 待 Owner 审查**。交付 2 个 DocType（`HBOS Stability Result` / `HBOS Stability Report`）+ 2 条状态机 + `Timepoint Item.current_result`（兑现 R8B 前向兼容承诺）；服务方法：结果 9 动作（录入/提交/复核/退回/批准/修订/作废/被取代/趋势评估）+ 报告 8 动作（建档/提交/审核/批准/驳回/作废 + 2 只读）+ 只读 6 接口（结果台账/详情/趋势/报告台账/详情/外推助手）+ 客户存量扫描 + `scheduler_scan` 补趋势逾期项。核心口径：六步原子切换生效指针（Timepoint 行锁内）、修订不改旧版、作废按必检项目粒度重开、显著变化双套判定（基线按储存条件隔离选取）、趋势线**不含统计控制限**、报告防重键与 QA 判定有效期分离。新增 `SCOPED_ACTION_ROLES`——R3 检验流程与稳定性结果 4 个同名动作按 DocType 作用域分别授权（防互相放宽）。实机验证发现并修复 2 项自身缺陷：①六步切换第 (b) 步漏持久化 `is_current` 产生「已修订+current=1」第三态；②非专项报告填客户仅被 Link 校验拦截、真实合规客户可绕过（补 `check_report_scope` 范围校验）。证据：离线契约 **288/288** 全量、实机端到端 **34/34**、R8B 回归 **40/40**、验证残留已清理。前端「结果录入与趋势」「报告与有效期」仍为演示数据，接入另起一轮；**未部署生产**。主文档 `docs/milestones/M2_R8C_稳定性结果与报告后端.md`
- 前一子轮：M2-R8H（稳定性前端接入：样品入箱与台账 + 取样与检测计划），**DONE / 待 Owner 审查**。把 R8B 的后端接到 R8F 的两个视图：后端补 3 处（`get_stability_schedule` 增三层日期与延期状态、新增 `get_stability_delays` 跨时间点延期列表并注册角色、`_policy_latest_test` 入参由对象改值）；前端新增 22 个接口函数并重写两视图（样品台账 + 详情 + 动作弹窗；月度看板改整月日期列 + 日期链 + 计划台账三层日期 + 延期审批含批准/驳回）、新增登记入箱与申请延期抽屉、vite 补 `/printview` 代理、`stabilityDemo.ts` 删除这两节孤儿导出（630+ → 356 行）。实施中处置 2 个自身缺陷（无输入动作误弹空白确认框致动作不执行、入箱抽屉 `Promise.all` 解构不匹配）。验证：离线 246/246、`vue-tsc` 0 错误、build 成功、浏览器真实会话读写全链与角色门控、375px 三页无溢出。稳定性 7 视图中 4 个已接真实后端。**未部署生产**。主文档 `docs/milestones/M2_R8H_稳定性样品与计划前端接入.md`
- 前一子轮：M2-R8B（稳定性后端：样品、时间点与取样检测计划），**DONE / 待 Owner 审查**。交付 5 个 DocType（`HBOS Stability Sample` + `Sample Log`；`HBOS Stability Timepoint` + `Timepoint Item` + `Timepoint Delay`）+ 3 条状态机 + 21 个动作方法 + 4 个只读接口 + `scheduler_scan` + 标签 Print Format「HBOS 稳定性样品标签」+ Script Report「取样与检测计划看板」。核心口径：`current_qty` 单一写路径与四步锁（锁顺序固定 Sample → Timepoint）、时间点生成幂等可重跑、延期三段流程与四段日期链全链校验、逾期纯派生不改状态。Result（R8C）依赖处做前向兼容守卫。实施中发现并处置 4 项方案缺口（送样 3 周校验无承载字段 / 委外窗口无存放位置 / 「取样完成」事件不在受控枚举 / 标签目录名与 Frappe scrub 不符）。标签尺寸：读了附件一原件，**原件未给物理尺寸**，按内容宽 82.6mm 推定并集中在模板一处待确认。证据：离线契约 **244/244**、实机端到端 **40/40**、补充验证 **10/10**。本轮只做后端 + 标签 + 报表，前端接入另起一轮；**未部署生产**。主文档 `docs/milestones/M2_R8B_稳定性样品与时间点后端.md`
- 更早子轮：M2-R8G（稳定性前端接入真实 API：工作台 + 考察申请与方案），**DONE / 待 Owner 审查**。把 R8F 的演示数据前端接到 R8A 后端：后端补 5 个只读接口（`get_stability_products` / `get_stability_master`（doctype 白名单）/ `get_stability_protocols` / `get_stability_protocol_detail` / `get_stability_audit`，4 个新动作已注册角色）；前端新增 `src/api/stability.ts`（7 只读 + 14 写 + `ACTION_ROLES`/`canAction`），重写「稳定性工作台」与「考察申请与方案」两视图（读 + 写全接），按钮按会话角色显隐（后端仍为硬校验）；其余 5 视图保留演示数据但标注「演示数据 · 待 R8B~R8D」，并删除顶部**已过期**的「R8A 门禁 5 项未闭环」提示条。验证中修复 2 项 R8A 遗留缺陷：①`HBOS Stability Protocol` **漏建 `snapshot_frozen` 字段**致方案冻结快照守卫恒失效（方案 7.7）；②命名系列 `-####` 在本版 Frappe 下**非法**（`set_name_by_naming_series` 无条件追加 `.#####`），实际生成 `HBOS-STB-NOT-2026-####00009` 畸形单号——已改为不含 `#` 的既有约定写法，清理 4 条旧 Property Setter，并同步更正方案与门禁包 36 处写法。证据：离线 **203/203**、R8A 端到端 **28/28**、只读接口 **7/7**、浏览器真实会话走通读 + 写全链与角色门控、`vue-tsc` 0 错误、`npm run build` 成功、375px 三页无溢出。**未部署生产**（先给测试端链接，Owner 确认后再同步）。主文档 `docs/milestones/M2_R8G_稳定性前端接入真实API.md`
- 更早前：M2-R8A（稳定性主数据与通知单/方案：后端实现与实机验证），**DONE / 待 Owner 审查**。R8A 启动门禁 7/7 已闭环（Owner 2026-09-16）。在 `hb_lims_app` 落地 10 个 DocType（主数据 4：HBOS Stability Product / Condition / Room / Test Item；记录一 Notice；方案 Protocol；子表 4：Test Item Form / Batch / Study Condition / Protocol Item）+ `FLOW_STB_NOTICE` / `FLOW_STB_PROTOCOL` 两条状态机（并入 `workflow_contract`）+ 新增角色 `LIMS QA Manager` / `LIMS QP` + 批准后冻结快照与版本链；新增 `stability_contract.py`（纯契约）/ `stability_guards.py`（系统字段 + 冻结快照 + 删除拦截守卫）/ `stability_service.py`（唯一合法写路径 + SoD + 越权/非法转移审计）。DocType 层 6 个 LIMS 角色一律只读（方案 8.6）。实机 `bench --site frontend migrate` 已执行（10 DocType 与 6 角色全部落库）；端到端 + 负向用例 **28/28 通过**、离线契约 **199/199 全绿**（含稳定性 28 项）。验证中发现并修复 4 项缺陷：`test_method_ref` 字段类型/标签写反、`create_stability_notice` 缺 `extra_condition_reason` 致 >2 条件不可提交、审计 `log_type` 未登记受控枚举、越权/SoD/非法转移/删除尝试未留痕。本轮未接前端真实 API、未启动 R8B、未改动 R7。主文档 `docs/milestones/M2_R8A_后端实现与实机验证.md`
- 更早之前：M2-R8F（稳定性板块前端 Vue 复刻与生产部署），**DEPLOYED**，Owner 2026-09-16 已确认测试路径并授权同步生产。已按 `M2_R8E` 设计方案与 HTML 原型在 `frontend/hbos-lims-web` 复刻稳定性 7 视图（工作台 / 考察申请与方案 / 样品入箱与台账 / 取样与检测计划 / 结果录入与趋势 / 报告与有效期 / 变更·稳定性室·设备）+ 路由 + 侧栏「稳定性管理」分组 7 入口 + 演示数据层 `stabilityDemo.ts`（`TEST-HBOS-M2-STB-*`）；`vue-tsc` 0 错误、`npm run build` 通过、浏览器 7 路由与抽屉逐一回归通过、375px 无页面级横向溢出；`npm run build:prod` 后同步生产 `/hbos-lims`（备份 `【内部备份标识已省略】`，84 个文件与本地逐字节一致、全路由与 7 个稳定性 chunk 均 200、既有模块无回归）。本轮不创建稳定性 DocType、不改后端、不接真实 API（**该轮口径；其后 R8A 已完成后端、R8G 已接入其中两视图**）。主文档 `docs/milestones/M2_R8F_稳定性板块前端Vue复刻与生产部署.md`
- 更早之前：M2-R8E（稳定性板块前端设计方案与 HTML 原型），REVIEWING，已交付 7 视图交互式原型、工作台 PNG 设计图和设计方案文档；Owner 已确认原型，其 Vue 复刻阶段由 M2-R8F 承接。

- 当前阶段：M2-LIMS 实验室信息管理系统板块（IN_PROGRESS）；M1-FIX 功能补漏为并行未决事项（IN_PROGRESS，B3/B4/B5 未 closeout）
- 当前轮次：M2-R8（稳定性管理板块开发方案，REVIEWING **rev15**，Owner 2026-09-15 授权启动，业务依据为**v9.0 拟执行依据（生效待确认，11.3-1）**；rev1 审核 FAIL（4 P0 + 6 P1）→ rev2 已逐项修订（Timepoint 提升独立主 DocType、补 Result/Report 状态机、批准后冻结快照与版本链、电子签名能力边界更正、数据模型全量显式定义、时间单位统一、逾期纯派生等）；复审"有条件通过"（5 必修 + 3 补强）→ rev3 已逐项修订（结果版本键与生效指针、双延期模型、DocType 清单总表、按 DocType 删除拦截、0 月来源 Link、检测日期物理约束、一般变更审批收紧、有效期字段拆分，新增 11.3 节 R8A 启动前置门禁）；三轮复审 → rev4 修订 3 P1 + 8 P2 + 9 P3（0 月免取样口径、时间点生成触发与中间条件、`append_conditions` 追加闭环、变更实施落点 7.9 节、`ROUND_HALF_UP` 等）；**四轮复审 FAIL（2 P0 + 8 P1）→ rev5 修订（结果生效指针仅在新版批准后同事务切换、统一 `effective_due_date` 有效截止日、新增 `LIMS QA Manager` 角色、6.3 动作矩阵改全转移覆盖表、Timepoint Item 防重复、0 月基线补 `HBOS Stability Result`、年度类 Notice 快照链、`append_conditions` 原子化、统一并发锁协议）；五轮复审"有条件通过"（4 P1 + 5 P2 + 10 P3）→ rev6 修订（补 `mark_for_disposal`/`cancel_disposal` 使「待处理」可达、入箱超期改强制评估四件套、`append_conditions` 补入 6.3 动作矩阵、门禁 3 时序校正等）；六轮复审 FAIL（2 P0 + 6 P1 + 5 P2）→ rev7 修订（结果状态与生效指针冲突修正、期限三层模型与政策硬上限、`record_result` 收紧为检测中、`pre_disposal_status` 快照、`approve_report` 三条硬前置、Report 补 `client`/`seq`/`source_ref`、补全驳回/作废/人日字段、延期历史单一口径，新增 8.6/8.7）；七轮复审 FAIL（7 P1 + 5 P2）→ rev8 修订（延期申请/驳回动作补全并统一字段名、结果作废出口与时间点重开、流水补「受托转出」、Notice 补驳回/取消字段、Report 改 Dynamic Link、8.3 按 DocType 列终止动作、期限审批口径入启动门禁）；八轮复审 FAIL（3 P1 + 3 P2）→ rev9 修订（Timepoint 状态机矛盾消除 + 系统动作 `reopen_timepoint` 登记、重开判定改按必检项目粒度、启动门禁口径统一为 11.3 的 5 项、Report 映射表移位、8.6 措辞更正、台账 R7 版本恢复）；九轮复审 FAIL（1 P1 + 2 P2）→ rev10 修订（`void_result` 行改按必检项目粒度重开、`report_period_key` 纳入 `source_doctype` 消歧并补 `seq` 并发锁、里程碑摘要版本校正）；十轮复审 FAIL（4 P1 + 4 P2）→ rev11 修订（`reopen_timepoint` 补"仅已完成才调用"守卫、延期日期全链 `planned≤requested≤approved≤policy_latest`、8.6 权限隔离改为"DocType 保留 create/write 仅系统字段受控"+3 张流水表服务专用写入、`seq` 锁指定产品行 + 有上限重试、`report_period_key` 改用规范化 `client_code`、页脚与台账版本号校正）；十一轮复审 FAIL（1 P0 结论确认 + 3 P1 + 2 P2 补强）→ rev12 修订（**P0** 复核 11.3 门禁维持"5 项未闭环、不得启动 R8A"结论；`apply_delay`/`approve_delay` 动作矩阵行补日期链两段、`reopen_timepoint` 动作矩阵行补状态守卫、映射规则与唯一性总表 `client` 统一为 `client_code`；补强采纳：`client_code` 定案五条规则（来源/格式/规范化/禁 `#`/批准后锁定）、8.6 新增运行期一致性扫描（每日 scheduler 四类不变式 → 审计事件 `一致性异常` → QA 每日复核处置，同步 8.1/8.4/门禁 16））；十二轮复审 FAIL（1 P0 结论确认 + 2 P1 + 1 P2）→ rev13 修订（**P0** 复核 11.3 门禁维持"5 项未闭环、不得启动 R8A"结论；**P1** `client_code` 重定案——删除"临时用名称规范化"回退路径、运行态核实 ERPNext `Customer` 无 `customer_code` 字段后新增 `customer` Link 字段、`client_code` 唯一来源为 Customer 文档名并补唯一性与维护责任；台账修复 AI_CONTEXT rev11 残留与 PROJECT_STATUS "M2-R5 closeout"/"余第 2/3/4/5/10 项"旧口径（统一引用 11.3-1/2/4/5/7）；**P2** 业务依据统一为 v9.0 拟执行依据待生效确认、v8.0 仅作历史差异基线）；十三轮复审 FAIL（1 P0 结论确认 + 3 P1 + 1 P2）→ rev14 修订（11.3 门禁维持 5 项未闭环；`client_code` 收紧为**始终只读派生** + 硬校验 `client_code == customer.name`、删「带出后可改」；格式约束落 ERPNext `Customer` 主数据命名规范并**删运行时隐式规范化**；`README` 旧待确认口径更正为 11.3-1/2/4/5/7、四份台账补 v9.0 拟执行标注；`report_period_key` 入键成分禁 `#`、非专项报告 `customer`/`client_code`/`seq` 必须为空）；**十四轮复审 FAIL（1 P0 结论确认 + 2 P1 + 2 P2）→ rev15 修订（11.3 门禁维持 5 项未闭环；Customer 编码格式补两层可执行保障——validate 钩子强制校验 + R8A 前存量扫描；「规范化 client_code」旧措辞统一改为 Customer 文档名原值；`client` 展示字段定稿只读派生 `customer.customer_name`；清理文档头重复修订史）**）；方案定案 14 主 + 8 子 DocType（= 22）、8 条状态机、R8A~R8E 子轮拆分，含 6 项规程疑点与 13 项待 Owner/QC-QA 确认（第 1 项电子签名已定**路线 ①**、第 12 项工作分支已定**新建 `m2-r8`**，余 11 项待定）），前一交付轮 M2-R7D（留样板块前端 Vue 复刻与生产部署，DEPLOYED，Owner 2026-09-08 已确认测试路径并授权同步生产 `/hbos-lims`）；留样方案 rev6 口径定稿（Owner 已确认角色方案 B+SoD、分支策略 b）；R7A（主数据与留样登记：3 DocType + retention_service + 前端两页）已在 m2-r6 交付并测试路径验证；工作台/观察/使用/处理 4 视图已切换真实后端接入，登记台账/产品沿用 R7A API；R7B（观察管理）/R7C（使用与处理审批）后端已实现并真实验证；M2-R5（验证收口）并行 REVIEWING，M2-LIMS MVP 全量交付完成。留样板块已按 Owner 授权纳入 R7 范围，R7 子轮按节拍推进
- M2-R6A（样品登记动态表单设计，REVIEWING）：样品类型 / 检验优先级下拉决策条 + 9 类整表单切换，方案与交互原型已交付
- M2-R6B（检验结果台账双模式设计，REVIEWING / Owner 已确认原型与交互）：明细台账（受控记录）+ 样品表（每样品种类一张表、一行一个批次），后端 `HBOS Ledger Template` + `get_result_ledger` 落地设计已交付
- M2-R6C（检验结果台账 Vue 复刻与生产部署，DEPLOYED）：双模式已复刻进 Vue 并上线生产，Owner 已确认测试路径
- M2-R6D（合规审计日志 + 生产部署错配修复，DEPLOYED）：合规审计日志 DocType/全量捕获/前端页已上线生产，Owner 已确认测试路径；并修复生产部署旧 chunk 残留致部分页面进不去
- M2-R7（留样管理板块开发方案，REVIEWING rev6）：rev5 后 Claude 终审（全文 + 规程 OCR + 既有代码契约三方交叉核对）发现 1 项 P1（释放预占未绑定本单预占状态——未预占单驳回会误扣他单预占致账目错乱）与 3 项 P2（留样待处理回退路径不完整、已批准/待执行无取消逃生口、受托转出落位未定义），rev6 全部修订；P3 六项（初始状态定义、transfer_out 交付轮归属、其他原因绕过 3 批上限、next_obs_month 乱序回写、available_qty fetch 不可落库、日期月末溢出与时区）固化为分轮实现注意事项（R7A 携带 3 项 / R7B 2 项 / R7C 2 项）。Owner 已授权留样板块纳入 `hb_lims_app` 范围；R7A 已在 m2-r6 交付（3 DocType + retention_service + 前端两页），R7B/C 后端已实现并真实验证，R7D 已 DEPLOYED（见上）。方案文档 `docs/milestones/M2_R7_留样管理板块开发方案.md`
- M2-R8（稳定性管理板块开发方案，REVIEWING **rev15**，业务依据为 **v9.0 拟执行依据（生效待确认，11.3-1）**）：Owner 2026-09-15 提供公司现行《稳定性管理》规程全套 5 份文件（新版正文 v8.0/v9.0，编码系列 `SOP-LC-1-00-019`；旧版正文 `JXH-SOP-LC-1-00-008-05` 05 版差异基线；附件一标签、附件二通知单、旧版记录一）并授权设计稳定性板块开发方案，即启动 M2-R8。以新版 v9.0 为第一业务依据（旧版口径仅入差异对照），评审两份桌面方案（`【本地私有路径已省略】`、`【本地私有路径已省略】`）。Owner 确认两项范围边界：①**全量 12 模块**覆盖；②**稳定性室管理（温湿度手工记录 + 设备台账 + 故障处理）纳入本板块**，温湿度自动监测采集留「环境监测」扩展模块。rev1 审核结论 FAIL（4 项 P0 + 6 项 P1），rev2 逐项修订：**P0-1** Timepoint 由子表提升为独立主 DocType（子表无法承担跨事务唯一约束与并发防重），Result 直接 Link 时间点；**P0-2** 新增 `FLOW_STB_RESULT` / `FLOW_STB_REPORT` 两条状态机与提交/复核/批准签名字段；**P0-3** 新增批准后冻结快照与版本链（协议/标准/方法/条件/限度快照，批准后字段级只读）；**P0-4** 电子签名能力边界更正（`_signature` 为展示型操作签名，**不等同 21 CFR Part 11 / Annex 11 合规电子签名**，GMP 放行走纸质补签；并新增受控状态记录删除拦截）；**P1-5** 数据模型全量显式定义（删除所有「或」模糊写法）；**P1-6** 时间单位统一 `time_point_value + time_point_unit`，补计划检测日期、2/3 效期取整、月末、闰年、工作日历规则；**P1-7** 显著变化判定配置化到 `HBOS Stability Test Item`（基线/5% 公式/非数值/缺失/复测口径），「控制图」改称「趋势图」（统计控制限待 QA 确认）；**P1-8** 新增 `HBOS Stability Room` 主数据，房间温湿度改数值字段，产品身份统一规则（编码空间对齐 + 一致性校验，目标态 ERPNext Item）；**P1-9** 角色身份先定后授权限（`approve_change_general` 收紧至 QA 线 + Manager，`approve_change_major` 独占 QP），`已实施 → 已驳回` 改 `后评估不通过`；**P1-10** 逾期统一纯派生（不进状态枚举）、延期审批独立动作。方案定案 **14 主 + 8 子 DocType（= 22）**（Stability Product / Condition / Room / Test Item + Notice / Protocol / Sample(+Sample Log) / Timepoint(+Timepoint Item) / Result / Report / Change / Room Log / Equipment / Fault Ticket(+Fault Sample)，及 Batch / Study Condition / Protocol Item 共享子表）+ 标签 Print Format + 6 报表 + 8 条状态机 + 动作角色矩阵（沿用 R7 方案 B，建议新增 `LIMS QP` 角色）+ 8 项强校验点 + 显著变化双套判定 + ICH Q1E 外推助手 + 趋势图（规格限+折线+线性趋势线），拆 **R8A~R8E** 五个子轮。新增第十一节跨轮验收门禁 6 类（唯一性并发 / 批准后冻结与版本 / 结果报告状态与 SoD / 0 月可追溯 / 时间边界 / 审计不可绕过）。**rev3 按复审结论（有条件通过，5 必修 + 3 补强）修订**：**M1** 结果唯一键与修订链冲突——改 `result_version_key`（含 `revision_no`）唯一 + `is_current` 生效指针（Timepoint 行锁内维护）+ `Timepoint Item.current_result`；**M2** 取样延期与检测延期拆分——新增子表 `HBOS Stability Timepoint Delay`（`delay_type`/原始截止日/申请顺延日/批准截止日/审批链），废除共用扁平字段；**M3** DocType 计数口径统一——补全 `HBOS Stability Test Item Form`，新增 5.8 节 DocType 清单总表，全量口径 **14 主 + 8 子 = 22**；**M4** 删除拦截改为按 DocType / 状态机逐一定义（废止通用状态白名单），并补子表「仅追加、禁编辑、父单受控时禁删行」；**M5** 0 月可追溯补 `baseline_doctype` + `baseline_name`（Dynamic Link）；**S6** 补检测日期物理约束 `actual_test_date ≥ actual_sample_date` 并定检测截止日锚定口径；**S7** `approve_change_general` 删除 Manager 权限（QA 线专属）；**S8** 有效期字段由 `Data` 拆为 `_months`/`_date`/`_type`；新增 11.3 节 R8A 启动前置确认门禁。**rev4 按三轮复审意见修订 3 项 P1 + 8 项 P2 + 9 项 P3**：**P1-1** 0 月点（出厂全检/委外）专属口径——`import_zero_month_result` 免取样路径、`actual_sample_date` 取放行检测日快照、硬校验 #1/#2 豁免并审计留痕、Timepoint 流转补 0 月分支；**P1-2** 时间点生成定稿为"批准为前置资格 + 入箱登记触发按样品生成（可手动重跑）"，7.1 补**中间条件**生成规则（0/6/9/12、≥4 点、含全部重点项），新增**追加条件/时间点**动作 `append_conditions`（前置变更单"已实施"、锁内按 `sample_cond_point_key` 幂等仅新增）；**P1-3** 变更实施落点定稿（新增 7.9 节：涉方案→Protocol 新版本、涉通知单→新 Notice、涉条件→追加时间点、涉样品→新 Sample），Change 补 `supersedes`/`change_scope`，`后评估不通过` 定稿为终态（另立新单）；**P2** 交叉引用 6 处校正、矩阵补 7 行动作、审计补 5 类事件、委外窗口配置化、Protocol 补 `room_temp_recovery_days`、作废后 `is_current` 指针与 `revision_no` 分配定稿、`ROUND_HALF_UP`、取消/退回原因字段、Sample 评估四件套；**P3** 风险表去重、看板交付归属、Equipment 全名、强光 `exposure_days`、Notice 关闭前置校验、温湿度缺卡提醒、年度报告防重键。**rev5 按四轮复审结论（FAIL，2 P0 + 8 P1）修订**：**P0-1** 结果生效指针切换时机——修订件创建时旧版继续生效，**仅新版批准成功后**在 Timepoint 锁内同事务原子切换 `is_current`/`current_result`；**P0-2** 统一 `effective_due_date = approved_due_date or original_due_date`，实际日期超过有效截止日**一律拒绝**，scheduler 亦改用有效截止日；**P1-3** 同步方案首行版本号；**P1-4** 新增 `LIMS QA Manager` 角色（QA 经理与普通 QA 审核人分离）；**P1-5** 6.3 动作矩阵重写为**全转移覆盖表**（动作/转移/角色/前置/签名/审计六列，补 `close_notice`、`cancel_timepoint`、`revise_result`、`review_report`、`void_report`、后评估、故障处理等）；**P1-6** Timepoint Item 补父单级项目防重复与 `current_result` 归属一致性校验；**P1-7** 0 月基线 `baseline_doctype` 补 `HBOS Stability Result` 并明确与 `baseline_ref` 对应关系；**P1-8** 年度持续类补 Notice 快照机制与标准来源链（原 `Timepoint→Protocol` 链路对无方案单的年度类断裂）；**P1-9** `append_conditions` 前置循环解除——定为 `implement_change` 的**原子实施事务**；**P1-10** 统一并发锁协议与锁顺序（时间点生成锁 Sample、结果指针切换锁 Timepoint、固定 Sample→Timepoint 顺序）。11.2 门禁扩至 **14 条**。**rev6 按五轮复审结论（有条件通过，4 P1 + 5 P2 + 10 P3）修订**：**P1-1** 补 `mark_for_disposal` / `cancel_disposal` 两动作（原「待处理」状态不可达、处置流程断裂，与门禁 10 冲突）；**P1-2** 入箱超 1 个月由硬拦截改为**强制评估四件套 + 审计**（与 5.3.1 及规程 4.5/4.6 口径一致）；**P1-3** `append_conditions` 补入 6.3.4 动作矩阵（准入行 R/QAM/M）；**P1-4** 门禁 3 旧时序校正；**P2** `submit_notice` 角色收回 QA/QAM/M、`void_protocol`/`void_report` 纳入 QP 补理由、`cancel_timepoint` 补「待取样」并定稿"含已批准结果须先全部作废"、FAULT 补 `return_fault_handling` 与 `待处理→已关闭`、`report_period_key` 专项类型加客户与序号维度、`effective_due_date` 多条已批准取最新；**P3** 门禁行序重排、十四节标题、基线映射表移位并删非枚举行、11.1 补 `LIMS QA Manager`、`return_result` 补入 7.8 锁表、6.2 末尾措辞、8.4 补检测完成推荐期扫描、6.1 `在箱→在箱` 自环、7.1 生成失败语义、`complete_testing` 系统触发豁免。**rev7 按六轮复审结论（FAIL，2 P0 + 6 P1 + 5 P2）修订**（先做**自身检查逐项核实属实**再改）：**P0-1** 结果状态与生效指针冲突——`revise_result` 只创建新草稿、旧版保持「已批准 + `is_current=1`」，新版批准时**同事务六步切换**，`current_result` 约束为 `is_current=1 且 status=已批准`，同 `(时间点,项目)` 在途唯一；**P0-2** 期限三层模型——`planned_due_date` / `policy_latest_due_date`（**硬上限**）/ `approved_due_date ≤ 政策上限`，实际日期超过政策上限**无论有无审批一律拒绝**，超限归后续偏差模块；**P1-1** `record_result` 收紧为 `Timepoint=检测中`（仅 0 月导入豁免）；**P1-2** Sample 补 `pre_disposal_status` 快照，`cancel_disposal` 回退补「已取尽」；**P1-3** `approve_report` 三条硬前置（审核已填、审核人≠批准人、`review_report` 已完成）；**P1-4** Report 补 `client`/`seq`/`source_ref`/`period_*` 字段并重订防重键（纳入研究范围维度）；**P1-5** 补全动作所需字段（Sample 处置四件套、Protocol/Report `reject_reason`/`void_reason` 及人日、Change `reject_reason` 与实施/后评估人日）；**P1-6** 延期历史定稿单一口径（按审批时间取最后一条 + **禁止批准日期倒退**）；**P2** Sample/Change 的 Link 目标类型补全、`Condition.condition_code` 标 unique、`support_docs` 语义更正、新增 **8.6 禁止绕过业务服务** 与 **8.7 违规审计独立持久化**。门禁扩至 **17 条**。**rev8 按七轮复审结论（FAIL，7 P1 + 5 P2）修订**（先做**自身检查逐项核实属实**再改）：**P1-1** 延期流程补 `apply_delay`/`reject_delay` 动作并统一到子表 `status`（原引用未定义的 `delay_status`）；**P1-2** 补 `已批准 → 已作废` 出口，`void_result` 作废生效结果时**同事务**将 Timepoint 回退为「检测中」以支持重录；**P1-3** `Sample Log.transaction_type` 补「受托转出」，销毁监督人统一为子表既有 `reviewer`；**P1-4** Notice 补 `reject_reason`/`reject_by`/`reject_date` 与取消三字段；**P1-5** Report `source_ref` 改为 `source_doctype` + `source_name`（Dynamic Link）并补 `report_type` ↔ `source_doctype` 映射规则；**P1-6** 8.3 改为**按 DocType 逐一定义终止动作**（取消/关闭/销毁/转出/作废）及原因字段；**P1-7** 期限审批口径（区间内是否需审批、委外窗口可否不限制）**纳入 11.3 启动门禁第 7 项**；**P2** 7.3 双延期表字段名统一为 `planned_due_date`/`policy_latest_due_date`、`cancel_disposal` 注释与门禁 13 补「已取尽」、延期审批时间字段改 `approve_at`（Datetime）、8.6 强化 `frappe.db.set_value` 等低层写入防绕过与负向测试、入口摘要口径校正。门禁扩至 **19 条**。**rev9 按八轮复审结论（FAIL，3 P1 + 3 P2）修订**（先做**自身检查逐项核实属实**再改）：**P1-1** 删「已完成 → 终态」消除 Timepoint 状态机自相矛盾，**登记系统动作 `reopen_timepoint`**（跨 DocType 副作用，由 `void_result` 同事务调用）进 6.3.4 矩阵与 8.1 审计枚举，门禁 10 对系统触发动作按"角色豁免、动作名不豁免"；**P1-2** 重开判定由"整点已无生效结果"改为**按必检项目粒度**（任一必检项目无生效结果即回退「检测中」），补多项目用例；**P1-3** 启动门禁口径统一——台账"4 项"更正为 **11.3 的 5 项（1/2/4/5/7）**，§15 与页脚改直接引用 11.3、不再混用"第十五节 13 项"编号；**P2-4** Report 的 `report_type ↔ source_doctype` 映射表移到字段表之后；**P2-5** 8.6 末句更正为"低层直写后果检测与告警"；**P2-6** 修复公共台账中 `M2-R7` 被误改为 rev8 的残留（恢复 rev6）与 `PROJECT_STATUS` 重复摘要。门禁扩至 **20 条**；rev10 按九轮复审修订（`void_result` 行改按必检项目粒度重开、`report_period_key` 纳入 `source_doctype` 消歧并补 `seq` 并发锁，门禁扩至 21 条）；rev11 按十轮复审修订（`reopen_timepoint` 补"仅已完成才调用"守卫、延期日期全链校验、8.6 权限隔离更正、`seq` 锁指定产品行、`report_period_key` 改用 `client_code`、`mark_superseded` 语义界定）；rev12 按十一轮复审修订（11.3 门禁维持 5 项未闭环；`apply_delay`/`approve_delay` 矩阵行补日期链、`reopen_timepoint` 矩阵行补状态守卫、映射规则与唯一性总表 `client` 统一为 `client_code`；`client_code` 定案五条、8.6 新增运行期一致性扫描）；rev13 按十二轮复审修订（11.3 门禁维持 5 项未闭环；`client_code` 重定案——删名称回退、新增 `customer` Link 且 `client_code` 唯一来源为 `Customer` 文档名；台账修复；业务依据统一 v9.0 拟执行依据待生效确认、v8.0 仅作历史差异基线）。**Owner 2026-09-15 决策两项**：第 1 项电子签名走**路线 ①**（操作签名 + 审计追踪，明确定性不等同 GMP 合规电子签名、放行走纸质补签；GMP 合规电子签名由**平台后续统一专项**实施，届时各板块统一接入）；第 12 项工作分支为**新建 `m2-r8`**（自 `0948cf8` 切出，`m2-r6` 留作 R7 历史线，`dev-r7-20260910` 为同提交冗余别名不再使用，`M2_START_GATE` 已同步）。**11.3 启动门禁 7/7 已全部闭环（Owner 2026-09-16）**：11.3-1 v9.0 **已正式生效**（按 v9.0 实现）；11.3-2 角色采纳 §6.2 映射表并新增 `LIMS QA Manager`/`LIMS QP`（人员权限与身份群组管理后续统一设置，本轮只做角色结构性创建）；11.3-4 取样延期 10% **采甲**（该时间点值折算天数 × 10%，`ROUND_HALF_UP`，上限 15 天）；11.3-5 DocType 采纳 5.8（14 主 + 8 子 = 22）；11.3-7 期限口径 ①**需审批** ②委外窗口**允许留空 = 不限制**。逐项确认记录见 `docs/milestones/M2_R8A_启动门禁确认包.md`。**R8A 已启动并完成**（10 DocType + 2 状态机 + 2 角色 + 冻结快照/版本链；实机 28/28、离线 199/199，见本文件当前子轮与 `docs/milestones/M2_R8A_后端实现与实机验证.md`）；R8B~R8E 待逐轮启动。方案主文档 `docs/milestones/M2_R8_稳定性管理板块开发方案.md`。
- M2-R8H（稳定性样品入箱与台账 + 取样与检测计划前端接入真实 API，DONE / 待 Owner 审查）：后端补 3 处（schedule 增三层日期与延期状态、新增跨时间点延期列表接口），前端新增 22 个接口函数并重写两视图，月度看板按已确认口径改为整月日期列，标签打印走 Frappe 打印视图（dev 补 `/printview` 代理）。验证：离线 246/246、`vue-tsc` 0 错误、build 成功、浏览器真实会话走通读 + 写全链与角色门控、375px 三页无溢出。未部署生产。主文档 `docs/milestones/M2_R8H_稳定性样品与计划前端接入.md`
- M2-R8B（稳定性样品、时间点与取样检测计划后端，DONE / 待 Owner 审查）：新增 5 个 DocType 与 3 条状态机，21 个动作方法（入箱登记/取样/返还/处置四件套/结存调整/受托转出；时间点生成/取样完成/0 月免取样/检测开始与完成/重开/取消/追加条件/超方案取样/延期三段）+ 4 个只读接口 + scheduler_scan；四步锁与固定锁顺序、时间点生成幂等、延期日期链全段校验、逾期纯派生；标签 Print Format 与「取样与检测计划看板」报表。验证：离线 244/244、实机 40/40、补充 10/10（含门禁 16① 表单守卫、门禁 1 DB 唯一约束、门禁 16③ 低层直写可检出）。未部署生产；前端接入另起一轮。主文档 `docs/milestones/M2_R8B_稳定性样品与时间点后端.md`
- M2-R8G（稳定性前端接入真实 API：工作台 + 考察申请与方案，DONE / 待 Owner 审查）：把 R8F 的演示数据前端接到 R8A 后端。后端补 5 个只读接口（产品 / 主数据白名单 / 方案台账 / 方案详情 / 稳定性审计摘要，4 个新动作已注册角色）；前端新增 `src/api/stability.ts`、重写工作台与考察两视图（读 + 写全接）、新增方案起草/详情抽屉、审计抽屉改真实数据、顶部提示条改为「已接入真实后端 / 演示数据 · 待 R8B~R8D」两态并删除过期的门禁条；`src/demo/stabilityDemo.ts` 删除已接入视图的孤儿导出。修复 2 项 R8A 遗留缺陷（Protocol 缺 `snapshot_frozen` 致冻结守卫失效、命名系列 `-####` 非法致畸形单号）。验证：离线 203/203、R8A 端到端 28/28、只读接口 7/7、浏览器真实会话走通读 + 写全链与角色门控、`vue-tsc` 0 错误、build 成功、375px 三页无溢出。**未部署生产**。主文档 `docs/milestones/M2_R8G_稳定性前端接入真实API.md`
- M2-R8F（稳定性板块前端 Vue 复刻与生产部署，DEPLOYED）：Owner 2026-09-16 已确认测试路径并授权同步生产。在 `frontend/hbos-lims-web` 复刻稳定性 7 视图（`/stability` 工作台 + study/samples/schedule/results/reports/ops）、7 条路由、侧栏「稳定性管理」分组 7 入口；新增 `src/demo/stabilityDemo.ts` 演示数据层（`TEST-HBOS-M2-STB-*`）、`styles/stability.scss`（稳定性专属类统一 `stb-` 前缀，避免与留样板块全局类互相覆盖）与 3 个共享组件（门禁提示条 / 新建通知抽屉 / 审计摘要抽屉）。计划页含月度看板（月份切换 + 储存条件/执行状态双筛选）、计划台账（三层日期：计划检测日 / 有效截止日 / 政策硬上限）、延期审批三个标签页；结果页三栏（时间点 + 表单 + 趋势，当前生效实线 / 在途虚线）；报告页含外推助手（只给建议、QA 判定为独立动作）与版本链。`vue-tsc` 0 错误、`npm run build` 通过、浏览器 7 路由 + 12 抽屉 + 375px 移动端（无页面级横向溢出）回归通过。生产构建后同步 `/hbos-lims`（备份 `【内部备份标识已省略】`；root 清旧 assets 后重铺，84 个文件与本地逐字节一致、全路由与 7 个稳定性 chunk 均 200、既有模块无回归）；`deploy_lims_fix.sh` 冒烟清单已补 `/stability*` 路由。本轮不创建稳定性 DocType、不改 `hb_lims_app`、不接真实 API（零 API 调用）、不启动 R8A。侧栏分组按 Owner 2026-09-16 指示由设计方案 §3.1 的 4 分组统合为 1 个「稳定性管理」分组（差异已在主文档留档）。主文档 `docs/milestones/M2_R8F_稳定性板块前端Vue复刻与生产部署.md`
- M2-R7D（留样板块前端 Vue 复刻与生产部署，DEPLOYED）：按设计稿在 `m2-r6` Vue 工程落地 6 视图留样板块（`/retention` 工作台 + samples/products/observations/usage/disposal），侧栏「留样管理」扩为 6 入口；新增工作台/观察/使用/处理四视图 + `retention.scss` + `src/demo/retentionDemo.ts` 演示数据与角色矩阵 + `DemoBar`；登记台账/产品沿用真实 R7A API 并小幅对齐（可用量独立列、临期范围筛选、页头样式统一）；`vue-tsc` 0 错误、生产构建成功并同步生产 `/hbos-lims`（备份 `【内部备份标识已省略】`），全路由与 bundle HTTP 200，Owner 已确认测试路径
- M2-R7B/R7C（观察/使用/处理后端 + 前端真实接入）：新增 Observation / Usage Apply / Disposal Apply 3 DocType 与 retention_service 全链方法（观察 N/3+审核+回写；使用/处理审批链、四步锁、SoD、4/5 级跳过、逃生口与释放预占、双签/续留、scheduler cron），真实流程验证 R7B 13/13、R7C 19/19、并发库存确认恰一单成功、离线契约 179/179 全绿；观察/使用/处理/工作台前端已从演示数据切换为 retention_service whitelist（演示层 `retentionDemo` 移除），登记台账/产品沿用 R7A API
- （2026-09-09 复审修复轮）Owner 复审 FAIL 后完成修复并验证：写路径只读+库存/系统字段守卫、留样量>0、transfer_out 业务/状态边界、处理申请锁内唯一在途与状态机闭环（“其他”/续留）、SoD 补齐（QM 按链型、双签异人）、违规审计独立提交；复审新增 P1（建单唯一在途、待执行取消、转出边界补行锁）已修复并回归（生命周期+审计 10/10、边界用例 5/5、直写拦截）
- （2026-09-09 时区统一）HBOS 与 LIMS 服务时间已统一至 Asia/Shanghai，存量瞬时时间完成迁移，日期字段未变；审计一致性、页面和资源回归已验证。内部备份及恢复记录不进入公开仓库；P2-4 / P3-5 / P3-6 仍按后续轮次处理。
- 当前仓库定位：工程启动文档、AI 上下文、里程碑状态、计划、ADR、环境设计文档、最小 Docker 配置、M1-FIX 轻量自定义 App（hb_attendance_app）与 M2-LIMS 自定义 App（hb_lims_app）
- 当前实现状态：M1-FIX-B2 已 COMPLETED；M1-FIX-B3 为 REVIEWING / Owner UI 验收未通过；M1-FIX-B4 为 REVIEWING / Claude PASS，但 Owner 数据链路验收发现后续问题；M1-FIX-B5 为 REVIEWING；M1-FIX-C/D/E 未启动。M2-LIMS MVP 全量交付：M2-R1 骨架、M2-R2 主数据与判定引擎、M2-R3 检验流程闭环、M2-R4 COA 与报表、M2-R5 验证收口（全量演练 19/19 + 11 项验收 + 离线测试 109/109 + Workspace 全链接入口），M2-R5 为 REVIEWING 等待审查。
- M2-R6 Vue 前端原型与开发流程已交付（交互式 HTML 原型 + 开发流程文档），REVIEWING 等待 Owner 审查；未创建 Vue 工程、未接真实 API。
- 当前远端：`origin` -> `https://github.com/zjl327707743/HBOS.git`，GitHub visibility = `PRIVATE`
- 下一步路线：优先进行 M2-R8K「我的待办身份绑定」Owner 测试路径验收。生产页面已可访问该功能，但既有发布来源尚待核对；本次已授权发布仅涉及侧栏「最近访问」移除的前端资源，不据此认定 R8K 全功能验收或后端重新发布。
- 下一步路线：**M2-R8F 稳定性板块前端 Vue 复刻已 DEPLOYED**（生产 `/hbos-lims`，Owner 2026-09-16 已确认测试路径并授权同步生产）：7 视图 + 路由 + 侧栏稳定性管理分组 + 演示数据层，全部为 `TEST-HBOS-M2-STB-*` 演示数据、零 API 调用；生产验证 84 个文件与本地逐字节一致、全路由与 7 个 chunk 均 200、既有模块无回归，备份 `【内部备份标识已省略】` 可回滚；`deploy_lims_fix.sh` 冒烟清单已补 `/stability*` 路由。**M2-R8H 稳定性样品与计划前端已接入真实 API**（DONE / 待 Owner 审查）：稳定性 7 视图中 4 个已接真实后端（工作台 / 考察申请与方案 / 样品入箱与台账 / 取样与检测计划）。**M2-R8C 稳定性结果与报告后端已完成**（DONE / 待 Owner 审查）：R8B 的前向守卫（`complete_testing` 等）已自动打通，`HBOS Stability Result` / `HBOS Stability Report` 全链可用。**M2-R8D 变更、稳定性室与设备后端已完成**（DONE / 待 Owner 审查）：方案 8 条状态机全部落地。**M2-R8I 剩余 3 视图前端接入已完成**（DONE / 待 Owner 审查）：稳定性板块 7 视图全部接入真实后端、6 张报表全部物化。**未部署生产**——测试端链接 `http://localhost:5173/stability`。**M2-R8J 当前结论为两轮修复完成并已上线**：第一轮修复报告链断裂 / 结果页缺「提交」/ `complete_testing` 越权 / 设备 status 无守卫 / 故障流水子表可改；第二轮修复 2026-09-21 回滚模拟复现的 8 项 P1 + 2 项 P2；离线契约 321/321、`pytest 329 passed`、前端类型检查与构建通过，**第二轮 10 项已补做实机逐项验证并负向回归 9/9 通过**；已提交 `e447f97` + `b61f83d` 并同步生产 `/hbos-lims`（备份 `【内部备份标识已省略】`）。下一步：Owner 测试路径验收。留样板块前端 6 视图已 DEPLOYED（生产 /hbos-lims，Owner 2026-09-08 已确认），R7B（观察管理）/R7C（使用与处理审批）后端已实现并真实验证，前端已真实接入（演示数据源已移除）；M2-R5（验证收口）REVIEWING 等待 Owner 和 Claude 审查 closeout（离线测试 109/109、全量演练 19/19 已过，见本文件 M2-LIMS 状态节）；M2-LIMS 其余扩展模块（仪器集成、环测、微生物、试剂、OOS 调查等）另行规划——留样板块（M2-R7）与稳定性板块（M2-R8）均已 Owner 授权；M1-FIX-C（异常三级流程）为 PLANNED / 待 Owner 授权，不自动启动。

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

- 安装前已完成 site 备份，备份位于 Docker volume 内的 `【内部备份目录】`
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
32. M2-R6C：DEPLOYED，检验结果台账双模式 Vue 复刻与生产部署完成。`ResultLedgerView.vue` 复刻双模式（明细台账 + 样品表），数据来自真实 Frappe API（HBOS Sample / Test Result / COA / Result Revision 聚合，只读投影，superseded 链过滤，修订/审计摘要）；新增判定列 + 记录状态列筛选、记录状态语义配色（放行/批准绿、检验完成/检验中蓝、登记/草稿灰、拒绝/OOS 红）；`vue-tsc` 0 错误；生产构建 `npm run build:prod` 同步至容器 `hbos-m0-r3a-frontend-1`（备份 `【内部备份标识已省略】`），生产 URL `http://localhost:8080/hbos-lims/` HTTP 200 验证通过，Owner 已确认测试路径效果。后端同步：`lims_service.py` 新增 `get_result_ledger` 聚合查询 whitelist（只读投影，返回 samples / results / revisions / coas / groups / meta，服务端派生 limits_text/display/report_date，对齐前端 ResultLedgerView），`workflow_contract.py` ACTION_ROLES 注册 `get_result_ledger`（LIMS Analyst/Reviewer/Manager + System 可读）；离线契约测试 114/114 全绿（新增 6 项台账契约）；真实环境跑通（全量 7 样品/17 结果/2 修订/3 COA 日期/分组 + sample_type=成品 3 样品 + material=测试01 2 样品筛选均验证）；backend gunicorn 已重启加载新代码。
33. M2-R6D：DEPLOYED，合规审计日志已上线生产，Owner 已确认测试路径。后端新增 `HBOS Audit Log` DocType（write-once：log_type/doctype_target/doc_name/action_text/field_changed/old_value/new_value/reason/user/created_at/checksum，仅 Reviewer/Manager/System 可读、无常规 create/edit/delete）；`hooks.py` doc_events 全量捕获创建/修改/删除；`lims_service.py` 新增 `audit_log`（sha1 防篡改）与 `get_audit_log` 查询 whitelist 及业务埋点（提交/复核/批准/修订/放行/拒绝/OOS/仪器使用/规格生效-废止）；`workflow_contract.py` 注册 `get_audit_log`；离线契约 123/123 全绿（新增 9 项）；真实环境跑通。前端合规组新增 合规审计日志 入口 + `/audit-log` + `AuditLogView.vue` + `getAuditLog`。生产部署修复：Owner 反馈「海滨LIMS 已可进入但样品登记异常/审计追踪等个别页面进不去」，根因生产 `index.html` 引用旧 bundle 与 assets 混 129 个历史旧 chunk（新旧哈希错配致 view 懒加载 404/崩溃）；root 清旧 assets 后重新部署最新干净 dist（39 资产与本地逐字节一致，全引用 200+正确 MIME）；注入 nginx SPA fallback 修 `/hbos-lims` history 404（`frappe.conf.【内部备份标识已省略】`）。

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

M2-R6C（检验结果台账 Vue 复刻与生产部署）：DEPLOYED。将 R6B 双模式复刻进 Vue 工程 `frontend/hbos-lims-web/src/views/ResultLedgerView.vue`：①明细台账——左侧样品列表（类型筛选 + 搜索 + 汇总判定角标）、右侧样品卡片（登记信息 + 检验项目逐行 限度/结果/判定/检验人/记录状态）、下钻抽屉（标准限度快照 / 三级电子签名 / 修订记录 / 审计摘要，OOS 完整链路）；②样品表——左侧按类型分组可收缩列表（每个样品种类一个条目、不含判定），右侧每样品种类一张表（首列序号、次列样品批号、登记字段、项目列、判定、记录状态，一行一个批次）。数据来自真实 Frappe API：HBOS Sample / HBOS Test Result / HBOS COA / HBOS Result Revision 前端聚合，只读投影、superseded 链过滤、修订/审计摘要。增强：判定列 + 记录状态列筛选（下拉动态取当前表数据、可叠加、切换样品种类自动重置）、记录状态语义配色（放行/批准绿、检验完成/检验中蓝、登记/草稿灰、拒绝/OOS 红）。`vue-tsc` 类型检查 0 错误；生产构建 `npm run build:prod` 后经 `docker cp` 同步至容器 `hbos-m0-r3a-frontend-1` 生产路径 `/home/frappe/frappe-bench/sites/frontend/public/hbos-lims/`（部署前备份 `【内部备份标识已省略】` 可回滚），生产 URL `http://localhost:8080/hbos-lims/` HTTP 200、静态资源全部 200 验证通过。Owner 已确认测试路径效果。后端同步：`lims_service.py` 新增 `get_result_ledger` 聚合查询 whitelist（只读投影，返回 samples / results / revisions / coas / groups / meta 六段，服务端派生 limits_text / display / report_date，支持 sample_type / material 筛选，对齐前端 ResultLedgerView 双模式数据需求，避免前端多路 get_list 拼接）；`workflow_contract.py` ACTION_ROLES 注册 `get_result_ledger`（LIMS Analyst / Reviewer / Manager + System Manager 可读）；离线契约测试 114/114 全绿（新增 TestLedgerContract 6 项：whitelist、角色注册、字段契约、派生字段、_ledger_groups）；真实环境跑通——全量返回 7 样品 / 17 结果 / 2 修订 / 3 个 COA 报告日期 / 类型分组（原材料→阿司匹林原料药 3 批等、成品→测试01 2 批等），`sample_type=成品` 3 样品、`material=测试01` 2 样品筛选均验证通过；backend 容器 gunicorn 已重启加载新代码（期间误杀主进程致容器退出，已 `docker start` 恢复，容器健康、生产前端 / 登录页 200）。

M2-R6D（合规审计日志 + 生产部署错配修复）：DEPLOYED。①合规审计日志：新增 `HBOS Audit Log` DocType（write-once，log_type/doctype_target/doc_name/action_text/field_changed/old_value/new_value/reason/user/created_at/checksum，仅 Reviewer/Manager/System 可读、无常规 create/edit/delete，写入仅系统钩子内部 insert）。`hooks.py` doc_events 全量捕获创建/修改/删除（HBOS Sample/Sample Task/Test Result/COA/Specification/Sample Type/Test Item）。`lims_service.py` 新增 `audit_log` 写核心（sha1 指纹防篡改）与 `get_audit_log` 查询 whitelist（类型/对象/操作人/关键字/时间筛选）及各业务方法埋点（提交含自动判定/复核/批准/修订/放行/拒绝/OOS/仪器使用/规格生效-废止）。`workflow_contract.py` 注册 `get_audit_log`；离线契约 123/123 全绿（新增 TestAuditLogContract 9 项）；真实环境跑通（建表、事件流、register_sample 自动触发创建）。前端合规组新增 合规审计日志 入口 + `/audit-log` 路由 + `AuditLogView.vue`（类型/对象/操作人/时间/前后值/原因/指纹 + 下钻含数据完整性）+ getAuditLog；生产构建 + docker cp 部署。②生产部署错配修复：Owner 反馈「海滨LIMS 已可进入但样品登记异常/审计追踪等个别页面进不去」，根因生产 index.html 引用旧 bundle 且 assets 混 129 个历史旧 chunk（新旧哈希错配致 view 懒加载 404/崩溃）；root 清旧 assets 后以干净 dist（39 资产与本地逐字节一致）重新部署，全引用 200+正确 MIME；注入 nginx SPA fallback 修 `/hbos-lims` history 404（备份 frappe.conf.【内部备份标识已省略】）。

M2-R7（留样管理板块开发方案）：REVIEWING rev6（rev5 后终审修订 1 P1 + 3 P2 + P3 六项分轮注意事项）。Owner 2026-09-07 两项决策落定：角色方案 B+SoD（第 1 项）、分支策略 b（第 8 项，m2-r6 为 M2-LIMS 延伸工作线，M2_START_GATE Git 工作线节已同步）；余 6 项——标签尺寸/法规条号/销毁层级为 R7A 前核对项，观察批先手动/历史不迁移/提醒提前量 30 天按默认值推进；R7A（主数据与留样登记 3 DocType + retention_service + 前端两页）已在 m2-r6 交付并测试路径验证，R7B/C 后端已实现并真实验证，R7D（Vue 前端 6 视图复刻）DEPLOYED（见下段）。以 Owner 2026-09-04 提供并授权的《留样管理规程》JXH-SOP-LC-1-00-007-09 全套文件（1 正文 + 4 记录 + 2 附件）为第一业务依据；两份桌面方案评审为业务采纳、技术路线 Frappe 原生化（SQL→DocType、Activiti→workflow_contract、Node/PostgreSQL→既有底座、12 周瀑布→四子轮；211.166→211.170 条号修正；补 0 月基线）。rev3 定案：5 主 DocType + 1 子表（HBOS Retention Product（附件二电子化，default_uom Select 受控枚举为全板块 UOM 唯一权威）/ Retention Sample + Stock Log 通用库存操作流水（transaction_type 入库/使用出库/销毁出库/受托转出/手动调整，source_doctype/source_name/qty_delta/remaining_qty）/ Observation（记录二，sample_period_key 单字段 unique）/ Usage Apply（记录三，四级审批）/ Disposal Apply（记录四，qa_manager_required 4/5 级可配 + qm_approved_at + deadline））+ 标签 Print Format + 4 报表；数量语义统一（available_qty = current_qty − reserved_qty 派生量不落库，全系统唯一口径）+ 四步锁协议（无锁校验→FOR UPDATE 锁行→锁内复核→写入提交）+ 各操作锁内复核（销毁须 qty==available_qty 且无预占、转出须无预占、调整不得低于预占量）；观察批数量校验（同产品同 obs_year ≤3 批 + 看板已选 N/3）；审计事件受控枚举 16 类（预占/释放/转出/调整/续留改期/审批层跳过/SoD 拦截等，get_audit_log 筛选受控）；角色动作矩阵 + 两条 SoD 硬校验；Sample→留样映射 6 规则成节；scheduler daily hook（销毁超期 + 到期 30 天临期扫描，纯报表派生）；R7A~C 验收含并发扣减（使用vs使用/使用vs处理/使用vs转出三组）、重复登记、越权审批、超期销毁、续留改期、单位不匹配、第4观察批、销毁数量不等于可用量等负向用例。发现规程疑点 3 项与待 Owner 确认 7 项不变（角色方案、标签尺寸、观察批选取、历史迁移、法规条号、销毁层级 4/5 级可配、提醒提前量）。子轮拆分：M2-R7A 主数据与留样登记 → R7B 观察管理 → R7C 使用与处理审批 → R7D Vue 原型与复刻。主文档 `docs/milestones/M2_R7_留样管理板块开发方案.md`。

M2-R7D（留样板块前端 Vue 复刻与生产部署）：DEPLOYED，Owner 2026-09-08 已确认测试路径并授权同步生产。按 `docs/frontend/M2_R7_留样板块前端设计方案.md` 与交互式原型（`M2_R7_留样板块前端原型.html`）在 `m2-r6` Vue 工程落地 6 视图留样板块：路由 `/retention`（工作台总览）+ `/retention/samples` `/products` `/observations` `/usage` `/disposal`，侧栏「留样管理」扩为 6 入口；新增工作台/观察/使用/处理四视图 + `styles/retention.scss` + `src/demo/retentionDemo.ts`（演示数据与演示角色矩阵）+ `components/retention/DemoBar`（演示身份切换驱动角色动作矩阵显隐与 SoD 提示）；登记台账/产品沿用真实 R7A API 并小幅对齐（可用量独立列、临期范围筛选、页头样式统一），工作台/观察/使用/处理 4 视图已切换真实后端接入（演示数据源已移除）；`vue-tsc` 0 错误、六路由浏览器回归无控制台错误、生产构建 `npm run build:prod` 成功；同步生产容器 `hbos-m0-r3a-frontend-1` `/home/frappe/frappe-bench/sites/frontend/public/hbos-lims/`（备份 `【内部备份标识已省略】`，root 清旧 assets），`http://localhost:8080/hbos-lims/` 全路由与主/视图 bundle HTTP 200。R7B（观察管理）/R7C（使用与处理审批）后端已实现并真实验证，落地后将 `retentionDemo` 演示数据源替换为 `retention_service` whitelist。

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
34. M2-R7：REVIEWING rev6（rev1 首轮审查 FAIL 8 项 → rev2 → rev3 二轮 9 项 → rev4 三轮复审 9 项 → rev5 复审 PASS WITH WARN 后 2 项 P2 修正 → rev6 终审修订 1 P1 + 3 P2 + P3 六项分轮实现注意事项）。Owner 2026-09-07 已确认角色方案 B+SoD（清单第 1 项）与分支策略 b（第 8 项）；余 6 项按节拍推进，R7A 启动待 Owner 指令。业务依据为 Owner 2026-09-04 提供并授权的《留样管理规程》JXH-SOP-LC-1-00-007-09 全套文件（1 正文 + 4 记录 + 2 附件）；两份桌面方案（《LIMS留样管理模块开发方案.md》《留样板块LIMS开发方案.md》）评审结论为业务采纳、技术路线修正（SQL 建表→Frappe DocType、自研/Activiti 工作流→workflow_contract 状态机、Node/PostgreSQL→既有 Frappe/MariaDB 底座、独立 12 周里程碑→R7A~D 四子轮），并修正 211.166→211.170 条号引用、补充 0 月基线观察。方案 rev3 定案：HBOS Retention Product（default_uom Select 受控枚举）/ Retention Sample + Stock Log 通用库存操作流水 / Observation（sample_period_key unique）/ Usage Apply（四级审批链）/ Disposal Apply（qa_manager_required 4/5 级可配 + qm_approved_at + deadline）共 5 主 + 1 子表；标签为 Print Format；4 个 Script Report（留样台账/观察计划看板含已选 N/3/季度到期清单/销毁超期清单）；三条状态机（留样在库生命周期、使用四级审批链、处理 4/5 级可配审批链含销毁 3 个月时限）；数量语义 available_qty=current_qty−reserved_qty 派生量不落库 + 四步锁协议 + 各操作锁内复核；审计事件受控枚举 16 类；角色动作矩阵 + SoD 硬校验；与 HBOS Sample 检验闭环打通（检验完成批次一键创建留样）、稳定性样品硬隔离；Sample→留样映射 6 规则成节；scheduler daily 扫描；R7A~C 验收含三组并发与多项负向用例。发现规程疑点 3 项（正文 4 级销毁签批 vs 记录四 5 签署位、08 版变更历史记录编号错位、标签尺寸 OCR 疑为 70.0×55.0mm）与待 Owner 确认 7 项（角色方案 A/B、标签尺寸原件确认、观察批手动/自动、历史在库数据是否迁移、法规条号核对、销毁签批层级 4/5 级可配、提醒提前量）。子轮 M2-R7A 主数据与留样登记 → R7B 观察管理 → R7C 使用与处理审批 → R7D Vue 原型与复刻。主文档 `docs/milestones/M2_R7_留样管理板块开发方案.md`。本轮未创建 DocType、未写业务代码、未动数据库、未建 Vue 工程。rev2 修订（首轮审查 FAIL 8 项全改）：8 个状态文件授权口径统一（Owner 已授权 R7 设计，R7A~D 须方案审查通过后启动）；数量字段全部 Float + UOM + package_count；库存 reserved_qty 预占 + FOR UPDATE 原子扣减 + Stock Log 通用库存操作流水（transaction_type/source_doctype/source_name/qty_delta/remaining_qty，覆盖使用/销毁/转出/调整全部来源）；观察计划字段（obs_year/obs_selected_by/obs_selected_date/obs_selected_reason/next_obs_month/next_obs_due_date）挂留样主表；复合唯一改业务键单字段 unique（product_batch_container_key / sample_period_key，validate 生成、用户只读）；角色动作矩阵 + 两条 SoD 硬校验（同人连续签署拦截、申请人自批拦截）；状态机补驳回终态/已转出入口/qm_approved_at 独立字段/deadline 计算基准；Sample→留样映射规则成节（类型白名单/状态白名单/防递归/产品匹配/同批唯一/液体拦截）；R7A~C 验收补并发扣减、重复登记、越权审批、超期销毁、续留改期、单位不匹配、审计字段变更等负向用例；R7C 验收措辞修正为「两类审批链」。rev3 修订（二轮 9 项）：①可用量与锁模型统一——available_qty=current_qty−reserved_qty 派生量不落库为全系统唯一口径，四步锁协议（无锁校验→FOR UPDATE→锁内复核→写入提交），各操作锁内复核（销毁 qty==available_qty 且 reserved_qty==0、转出 reserved_qty==0、调整后 current_qty>=reserved_qty、释放防重复）；②观察批数量校验——同产品同 obs_year ≤3 批，第 4 批 validate 拒绝，看板展示已选 N/3，换批先取消再选留痕；③审计事件受控枚举 16 类（新增预占/释放/受托转出/手动调整/续留改期/观察异常/审批层跳过/SoD 拦截），get_audit_log 筛选下拉同步受控；④rev1 残留清理——本文件 M2-LIMS 章节旧 Usage Log/复合 unique 描述重写，全部状态文件 rev2→rev3；⑤数量语义表成节（retention_qty/current_qty/reserved_qty/available_qty/qty_delta/remaining_qty/package_count 语义定义）；⑥UOM 受控来源——Retention Product.default_uom Select 受控枚举（g/kg/mg/mL/L/瓶/支/袋/桶/盒/其他）为全板块唯一权威，下游全部只读带出，扩充仅 Manager；⑦4/5 级审批跳过机制——qa_manager_required Check 默认 5 级，状态机双路径（待QA审核→待QA负责人审核 或 直达待QM批准），跳过写审计事件，定稿后 one-time patch 全局切换、在途单按创建时快照执行；⑧scheduler hook 明确——hooks.py 注册 scheduler_events.daily（00:30）扫描销毁超期与到期 30 天临期，纯报表派生不改状态，不做推送；⑨R7C 验收新增 6 用例：使用vs处理并发、使用vs转出并发、手动调整低于预占量拒、第4观察批拒、审计新事件枚举可查、销毁数量不等于可用量拒。rev4 修订（三轮复审 5 P1 + 4 P2）：①confirm_stock 纳入四步锁协议与单一写路径（7.2/7.4，防并发确认超额预占）；②execute_usage 锁内复核条件修正——本单预占有效性（reserved_qty>=apply_qty）+ 总量守恒（current_qty>=reserved_qty），弃用 available_qty 判本单（7.3）；③观察批选取并发防护——产品行 FOR UPDATE 锁内计数（5.3）；④全检量 2 倍自动计算加 UOM 一致性闸（4.1，full_test_qty_uom≠default_uom 时禁算）；⑤R7A 验收「调整低于预占」用例归位 R7C（预占由使用申请产生），R7A 改测负结存边界；⑥README/AI_CONTEXT/milestones README 补 R7 进度；⑦分支策略（m2-r6 vs m2-lims）列为待确认第 8 项并 M2_START_GATE 加注记；⑧scheduler 由 daily 改 cron（30 0 * * *，daily 不提供精确时刻参数）；⑨观察批 3 批口径定稿——上限 3 批硬校验、不足 3 批弹性允许 + 看板完整性提示（5.3）。rev5 修订（复审 PASS WITH WARN 后 2 项 P2）：①7.1 可用量口径与 7.3 消歧——available_qty 用于展示与无预占语境的可用量判断（库存确认前置校验、台账/报表展示、前端 fetch），库存写操作锁内复核按 7.3 操作级规则直接校验 current_qty / reserved_qty，消除「唯一口径」表述与操作级特例的冲突；②README / AI_CONTEXT / milestones README 的「后续路线」摘要段补 R7。分支策略维持待 Owner 拍板第 8 项（R7A 启动前必须收口，M2_START_GATE 已加注记）。rev6 修订（终审 1 P1 + 3 P2）：①P1——释放预占绑定本单预占状态（7.3：仅已过库存确认的单驳回/取消才释放，聚合守卫仅防重复；修 B 单确认前驳回误扣 A 单预占 5 的账目错乱场景）；②P2——FLOW_RETENTION 待处理回退补全（待处理→{已销毁,在库,部分使用}，按进入前快照恢复，覆盖处理驳回退出与部分使用续留回写）、两条审批流逃生口（使用申请已批准→已取消（Manager、原因必填、释放预占留审计，防预占永久占用阻塞销毁/转出）、处理申请待执行→已取消）、受托转出落位定义（受托产品登记直接以已转出状态创建，不经在库，current_qty=0，0 量审计事件）；③P3 六项固化为分轮实现注意事项（十四节末表）：FLOW_RETENTION 初始状态=在库与审核栏签名承载（R7A）、transfer_out R7A 交付/R7C 验收、obs「其他」原因限 Manager 防绕过 3 批上限（R7B）、next_obs_month 按 max(已审核)+12 推导防乱序（R7B）、available_qty 派生量不可 fetch 需 virtual/聚合查询（R7C）、relativedelta 月末溢出与容器时区（R7A/R7C）；R7A/R7C 验收各补 2 用例（受托登记直接已转出、确认前驳回不释放预占、已批准取消后留样恢复销毁/转出）。
35. M2-R7D（留样板块前端 Vue 复刻与生产部署）：DEPLOYED。按 `docs/frontend/M2_R7_留样板块前端设计方案.md` 与交互式原型（`M2_R7_留样板块前端原型.html`）在 `m2-r6` Vue 工程落地 6 视图留样板块：路由 `/retention`（工作台总览）+ `/retention/samples` `/products` `/observations` `/usage` `/disposal`，侧栏「留样管理」扩为 6 入口；新增工作台/观察/使用/处理四视图 + `styles/retention.scss` + `src/demo/retentionDemo.ts`（演示数据与演示角色矩阵）+ `components/retention/DemoBar`；登记台账/产品沿用真实 R7A API 并小幅对齐（可用量独立列、临期范围筛选、页头样式统一），工作台/观察/使用/处理 4 视图已切换真实后端接入（演示数据源已移除）；`vue-tsc` 0 错误、六路由浏览器回归无控制台错误、生产构建成功；同步生产容器 `hbos-m0-r3a-frontend-1` `/home/frappe/frappe-bench/sites/frontend/public/hbos-lims/`（备份 `【内部备份标识已省略】`，root 清旧 assets），`http://localhost:8080/hbos-lims/` 全路由与 bundle HTTP 200；Owner 2026-09-08 已确认测试路径并授权同步生产。R7B（观察管理）/R7C（使用与处理审批）后端已实现并真实验证，落地后将 `retentionDemo` 演示数据源替换为 `retention_service` whitelist。
