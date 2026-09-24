# M2-LIMS 启动门禁

项目名称：新乡海滨智能运营管理平台。

## 文件定位

本文件记录 M2-LIMS（实验室信息管理系统板块）启动前必须满足的门禁条件，以及 M2-LIMS 的范围边界与并行事项记录。

## 当前子轮状态

- **M2-R8K（我的待办身份绑定）**：**REVIEWING / 真实 Frappe 冒烟已通过，待 Owner 测试路径验收**。完成基于当前 Frappe 会话身份的检验 / 稳定性 / 留样待办聚合，合并「指派给我」与「我的角色待处理」并明确区分；补齐 Administrator 特判、稳定性项目粒度跨模块收敛、六类深链定位、原业务 API 动作调度、个人摘要缓存和前台轮询控制；本轮修复 Frappe fullname / today API、子表父单权限读取、无读权限降级、业务覆盖误报、检验批准 SoD 字段、ISO 日期序列化，以及前端错误态 / 筛选 / 测试默认值问题。验证：前端单测 **7 passed**、LIMS 后端测试集 **395 passed**、生产构建通过、真实 Frappe 冒烟 **1 passed**。生产页面已可访问「我的待办」，其既有发布来源待核；本次仅同步侧栏资源。提交 `1c55a14` + `3fe0e05`（基线）。主文档：`docs/milestones/M2_R8K_我的待办身份绑定.md`。

> 侧栏发布（2026-09-23）：按 Owner 授权移除「最近访问」整块，提交 `fbb1aee`；生产备份 `【内部备份标识已省略】`，前端资源 SHA-256 **87/87 一致**，浏览器复核通过。未执行后端迁移或重启。

> 状态校正（2026-09-21 本轮追加）：R8J 既有修复及本轮新增稳定性取样绑定、业务检验结果同步、审查缺陷修复与趋势摘要下拉控件宽度修复均已按 Owner 授权同步生产；生产发布脚本 pytest **342/342**、生产前端 `build:prod` 通过，生产路径 17 个页面/资源冒烟均返回 200，备份为 `【内部备份标识已省略】`，结果页已完成生产浏览器复测。

> 状态校正（2026-09-22）：R8J 基线上的侧栏「最近访问」关闭交互已按 Owner 授权同步生产；提交 `934e36a`，完整 pytest **342/342**、`build:prod` 和生产路由/主资源 HTTP 200 冒烟通过，备份为 `【内部备份标识已省略】`。本次为纯前端资产同步，不涉及后端迁移。

- **M2-R8J（稳定性板块前后端审查与缺陷修复）**：**DEPLOYED / 待 Owner 测试路径验收**。两轮修复共 **3 + 8 项 P1** 与 **2 + 2 项 P2**：第一轮（报告链断裂 / 结果页缺「提交」/ `complete_testing` 越权 / 设备 status 无守卫 / 故障流水子表可改），第二轮经 93 项回滚模拟复现的 10 项（变更单伪造与审批 SoD、样品错配、库存流水对账、计划检验项目、趋势契约、取样日期政策与延期前置、月份过滤分页、变更条件输入路径）。离线契约 `321/321`、`pytest 329 passed`、前端 `vue-tsc` 与构建通过；**第二轮 10 项已补做实机逐项验证**（非 Administrator 真实用户）并**负向回归 9/9 通过**。已提交 `e447f97` 并同步生产 `/hbos-lims`（备份 `【内部备份标识已省略】`；清理 58 个历史残留 chunk 后远端 85 文件与本地 dist 文件清单及 md5 逐条一致；生产路径浏览器读写全链走通）。上线后 Owner 验收发现的稳定性工作台「待 R8B~R8D」占位文案（KPI 卡 + 整块面板）已修复——后端补样品/时间点/结果真实计数与时间点执行结构、前端 KPI 6→8 张，提交 `b61f83d` 并同步生产（备份 `【内部备份标识已省略】`，远端 86 文件与本地 dist md5 逐条一致）；侧边栏「取样与检测计划 / 结果录入与趋势」角标亦为原型遗留硬编码（4/3 且恒显红色），已改接真实数据并修正为 amber，提交 `6e06155` 并同步生产（备份 `【内部备份标识已省略】`，远端 86 文件 md5 逐条一致）。主文档：`docs/milestones/M2_R8J_稳定性板块审查与修复.md`。
- **M2-R8E（稳定性板块前端设计方案与 HTML 原型）**：REVIEWING / Owner 已确认原型。已交付 7 个原型视图、关键抽屉交互、PNG 设计图和移动端检查；本轮不创建 Vue 工程、不接真实 API、不创建稳定性 DocType，不改变 R8A 启动前置门禁。
- **M2-R8F（稳定性板块前端 Vue 复刻与生产部署）**：**DEPLOYED**，Owner 2026-09-16 已确认测试路径并授权同步生产。按 `M2-R8E` 设计方案与 HTML 原型，在 `frontend/hbos-lims-web` 复刻稳定性 **7 视图** + 7 条 `/stability*` 路由 + 侧栏「稳定性管理」分组 7 入口 + 演示数据层 `src/demo/stabilityDemo.ts`（`TEST-HBOS-M2-STB-*`）+ 样式 `stability.scss` + 3 个共享组件；`vue-tsc` 0 错误、`npm run build` 通过、浏览器 7 路由 / 12 抽屉 / 375px 移动端回归通过；生产构建 `npm run build:prod` 后同步 `/hbos-lims`（备份 `【内部备份标识已省略】`，84 个文件与本地逐字节一致、全路由与 7 个稳定性 chunk 均 200、既有模块无回归），`deploy_lims_fix.sh` 冒烟清单已补 `/stability*` 路由。本轮**不创建稳定性 DocType、不改 `hb_lims_app`、不接真实 API**（稳定性视图零 API 调用，全部为演示数据）；真实 API 接入待 R8B~R8C 落地后按设计方案 §8 顺序推进。主文档 `docs/milestones/M2_R8F_稳定性板块前端Vue复刻与生产部署.md`。
- **M2-R8H（稳定性前端接入：样品入箱与台账 + 取样与检测计划）**：**DONE / 待 Owner 审查**。后端补 3 处（`get_stability_schedule` 增三层日期与延期状态、新增跨时间点延期列表 `get_stability_delays` 并注册角色、`_policy_latest_test` 入参由对象改值）；前端新增 22 个接口函数并重写两视图（样品台账 + 详情 + 动作弹窗；月度看板改为**整月日期列** + 时间点日期链 + 计划台账三层日期 + 延期审批含批准/驳回），新增登记入箱与申请延期两个抽屉，vite 补 `/printview` 代理（标签打印走 Frappe 打印视图），`stabilityDemo.ts` 删除这两节孤儿导出。处置 2 个自身缺陷（无输入动作误弹空白确认框、入箱抽屉 `Promise.all` 解构不匹配）。验证：离线 **246/246**、`vue-tsc` 0 错误、build 成功、浏览器真实会话走通读 + 写全链与角色门控、375px 三页无溢出。至此稳定性 7 视图中 **4 个已接真实后端**。**未部署生产**。主文档 `docs/milestones/M2_R8H_稳定性样品与计划前端接入.md`。
- **M2-R8B（稳定性样品、时间点与取样检测计划后端）**：**DONE / 待 Owner 审查**。交付 5 个 DocType（`HBOS Stability Sample` + `Sample Log`；`HBOS Stability Timepoint` + `Timepoint Item` + `Timepoint Delay`）+ 3 条状态机 + 21 个动作 + 4 个只读接口 + `scheduler_scan` + 标签 Print Format「HBOS 稳定性样品标签」+ Script Report「取样与检测计划看板」。口径：`current_qty` 单一写路径与四步锁（锁顺序固定 Sample → Timepoint）、时间点生成幂等可重跑、延期三段流程与四段日期链全链校验、逾期纯派生。Result（R8C）依赖处做前向兼容守卫。处置 4 项方案缺口（送样 3 周校验无承载字段 / 委外窗口无存放位置 / 「取样完成」事件不在受控枚举 / 标签目录名与 Frappe scrub 不符）。证据：离线 **244/244**、实机端到端 **40/40**、补充 **10/10**（门禁 16① 表单守卫、门禁 1 DB 唯一约束、门禁 16③ 低层直写可检出）。标签尺寸：附件一原件未给物理尺寸，按内容宽 82.6mm 推定待确认。本轮只做后端 + 标签 + 报表，**未部署生产**。主文档 `docs/milestones/M2_R8B_稳定性样品与时间点后端.md`。
- **M2-R8G（稳定性前端接入真实 API）**：**DONE / 待 Owner 审查**。后端补 5 个只读接口（产品 / 主数据白名单 / 方案台账 / 方案详情 / 稳定性审计摘要）；前端新增 `src/api/stability.ts`，重写「稳定性工作台」与「考察申请与方案」两视图（读 + 写全接、按会话角色显隐按钮），其余 5 视图标注「演示数据 · 待 R8B~R8D」并删除已过期的 R8A 门禁提示条。修复 2 项 R8A 遗留缺陷：`HBOS Stability Protocol` 漏建 `snapshot_frozen` 致方案冻结快照守卫恒失效；命名系列 `-####` 在本版 Frappe 下非法致畸形单号 `HBOS-STB-NOT-2026-####00009`（已改为不含 `#` 的既有约定写法，并同步更正方案与门禁包 36 处）。验证：离线 203/203、R8A 端到端 28/28、只读接口 7/7、浏览器真实会话走通读 + 写全链与角色门控、`vue-tsc` 0 错误、build 成功、375px 三页无溢出。**未部署生产**（先给测试端链接，Owner 确认后再同步）。主文档 `docs/milestones/M2_R8G_稳定性前端接入真实API.md`。
- **M2-R8A（稳定性主数据与通知单/方案后端）**：**DONE / 待 Owner 审查**。11.3 启动门禁 7/7 已闭环（Owner 2026-09-16，记录见 `docs/milestones/M2_R8A_启动门禁确认包.md`）。在 `hb_lims_app` 落地 10 个 DocType（4 主数据 + Notice + Protocol + 4 子表）、`FLOW_STB_NOTICE`/`FLOW_STB_PROTOCOL` 两条状态机、新增 `LIMS QA Manager`/`LIMS QP` 两角色、批准后冻结快照与版本链；`stability_contract.py`/`stability_guards.py`/`stability_service.py` 三模块，DocType 层 6 个 LIMS 角色一律只读（方案 8.6）。实机 `migrate` 已执行，端到端 + 负向用例 **28/28 通过**、离线契约 **199/199 全绿**；验证中修复 4 项缺陷（非法 fieldtype、`extra_condition_reason` 缺失致 >2 条件不可提交、审计 `log_type` 未入受控枚举、越权/SoD/非法转移/删除未留痕）。本轮未接前端真实 API、未启动 R8B、未改动 R7。主文档 `docs/milestones/M2_R8A_后端实现与实机验证.md`。

## 必须满足的前置条件

- M0 状态必须为 COMPLETED（已满足）。
- M1 已 closeout 为 COMPLETED，产品交付仍在 M1-FIX 中（B3 / B4 / B5 为 REVIEWING，未 closeout）——M1-FIX 作为**并行未决事项**记录，不因 M2-LIMS 启动而关闭或合并。
- 当前 Frappe / ERPNext / HRMS 环境可访问：Frappe `16.26.3` / ERPNext `16.26.2` / HRMS `16.14.0`，site=`frontend`，Desk=`http://localhost:8080/login`（`.env` 中 `HTTP_PORT=8080`；`8081` 端口被本机 SENAITE 演示容器占用，勿混淆）。
- 不允许提交 `.env`、备份文件、密钥、数据库、Docker volume 或运行时数据。
- M2 自定义 App 已获 Owner 明确授权：`hb_lims_app`（业务模块包 `hbos_lims`）。

## M2-LIMS 范围

M2-LIMS 是实验室信息管理系统板块（HB LIMS）的开发里程碑，以《海滨药业LIMS系统开发方案》为业务口径（12 模块），参考开源 SENAITE LIMS 的功能结构（仅参考业务模型，不搬代码，遵守 ADR-0004），技术承载为 HBOS 既有 Frappe 底座。

第一版为**核心闭环 MVP**（M2-R2 至 M2-R5 交付）：

- 样品管理：样品登记 / 接收 / 状态流转（草稿 → 已登记 → 检验中 → 检验完成 → 已放行 / 已拒绝 / OOS 锁定）。
- 质量标准：规格 → 检验项目 → 方法 SOP → 限度 → 单位 → 有效位数 → 版本号 → 生效日期；版本控制为复制新版本人工流程。
- 检验流程：任务分配 → 检验执行 → 数据录入 → 自动判定（合格 / 不合格 / OOS 候选）→ 复核（第二人）→ 放行；计算公式（含量 % 内置模板）；结果修改留痕（修订表，修改原因必填）。
- COA 报告：自动提取已批准结果 → Print Format 渲染 → PDF 生成 → QA 审核 → 发布归档。
- 系统管理最小落地：三角色权限（LIMS Manager / LIMS Analyst / LIMS Reviewer）+ 审计追踪查询报表。

## M2-LIMS 不做（本轮及 MVP 边界）

- 不做仪器数据集成（仅预留 `instrument_used` 字段）、环境监测、试剂与标准品、微生物检验、OOS/OOT 完整调查流程（仅保留触发与锁定接口）。**留样管理（M2-R7）已按 Owner 2026-09-04 授权纳入范围**：R7 子轮按 Owner 授权推进（R7A/R7D 前端已落地，R7B/C 后端已实现并真实验证、前端已真实接入）。**稳定性管理（M2-R8）已按 Owner 2026-09-15 授权纳入范围**：方案 `docs/milestones/M2_R8_稳定性管理板块开发方案.md` REVIEWING **rev15**（v9.0 为拟执行依据，生效待确认——11.3-1）（rev1 审核 FAIL 后 rev2 修订 4 P0 + 6 P1，复审"有条件通过"后 rev3 修订 5 必修 + 3 补强、rev4 修订 3 P1 + 8 P2 + 9 P3，四轮复审 FAIL 后 rev5 修订 2 P0 + 8 P1，五轮复审"有条件通过"后 rev6 修订 4 P1 + 5 P2 + 10 P3，六轮复审 FAIL 后 rev7 修订 2 P0 + 6 P1 + 5 P2，七轮复审 FAIL 后 rev8 修订 7 P1 + 5 P2，八轮复审 FAIL 后 rev9 修订 3 P1 + 3 P2（启动门禁 7 项已全部闭环 / 验收门禁 21 条），九轮复审 FAIL 后 rev10 修订 1 P1 + 2 P2，十轮复审 FAIL 后 rev11 修订 4 P1 + 4 P2（验收门禁保持 21 条），十一轮复审 FAIL 后 rev12 修订 1 P0 结论确认 + 3 P1 + 2 P2 补强，十二轮复审 FAIL 后 rev13 修订 1 P0 结论确认 + 2 P1 + 1 P2（`client_code` 重定案：删名称回退、新增 `customer` Link；台账修复；业务依据统一 v9.0 拟执行依据；验收门禁保持 21 条），十三轮复审 FAIL 后 rev14 修订 1 P0 结论确认 + 3 P1 + 1 P2（`client_code` 只读派生 + 硬校验 `client_code == customer.name`；Customer 主数据命名闭环、删隐式规范化；台账旧口径修复；`report_period_key` 入键成分禁 `#`、非专项报告三字段必须为空；验收门禁保持 21 条），十四轮复审 FAIL 后 rev15 修订 1 P0 结论确认 + 2 P1 + 2 P2（Customer 编码格式 validate 强制校验 + R8A 前存量扫描；「规范化 client_code」旧措辞统一为 Customer 文档名原值；`client` 只读派生 `customer.customer_name`；文档头重复修订史清理；验收门禁保持 21 条）；两项范围边界 Owner 已确认：全量 12 模块、稳定性室手工记录纳入本板块），11.3 启动门禁 7/7 已闭环（Owner 2026-09-16），R8A 已启动并完成（10 DocType + 2 状态机 + `LIMS QA Manager`/`LIMS QP` + 冻结快照与版本链；实机 28/28、离线 199/199），R8B~R8E 待逐轮启动。其余扩展仍另行规划。
- 不创建 `hb_core_app`、不创建 `hb_feishu_app`。
- 不修改 Frappe / ERPNext / HRMS 核心源码。
- 不做大型 Vue / React 独立前端（Frappe Desk 原生页面；独立前端须走原型先行 + Owner 审查流程）。
- 不接真实仪器、不录入真实样品 / 人员 / 检测数据；演示数据一律 `TEST-HBOS-M2-*` 前缀。
- 不执行 `docker compose down -v`，不删除 Docker volume，不重建 `frontend` site。
- 不提交 `.env`、密钥、Excel / CSV、数据库导出或运行时产物。

## 并行事项记录

- M1-FIX-B3 / B4 / B5 为 REVIEWING，等待 Owner 和 Claude 审查；M1-FIX-C/D/E 为 PLANNED，未启动。
- M1-FIX 未决事项不阻塞 M2-LIMS 开发；M2-LIMS 工作线在独立分支 `m2-lims` 上进行，与 M1-FIX 工作线互不干扰。

## Git 工作线

- M2-LIMS MVP（R1~R5）工作在分支 `m2-lims`（自 `m1-fix-frontend-zh` 切出）上进行。
- **M2-LIMS 延伸工作线（Owner 2026-09-07 拍板分支策略 b）**：自 R6C/R6D 起，M2 后续工作（R6 系列 Vue 复刻与生产部署、R7 留样板块及其子轮 R7A~D）在 `m2-r6` 分支上进行，作为 M2-LIMS 的延伸工作线，不回并 `m2-lims`；`m2-lims` 保留为 MVP 历史线。
- **M2-R8 稳定性板块工作分支（✅ Owner 2026-09-15 已指定）**：从当时 HEAD `0948cf8` 新建 **`m2-r8`**，R8 及其子轮（R8A~R8E）在 `m2-r8` 上进行，不回并 `m2-lims`；`m2-r6` 保留为 R7 历史线。**`dev-r7-20260910` 与 `m2-r6` 指向同一提交 `0948cf8`，为冗余别名，不再作为工作分支使用**（暂保留分支对象，未删除）。方案第十五节待确认第 12 项已闭环。
- 未跟踪文件（`start.sh`、`apps/hb_attendance_app/__init__.py`、`.claude/`）按 M1 既有处理原则，不误提交。
