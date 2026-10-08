# Current Milestone

## M1-FIX：M1 考勤一期功能补漏阶段

项目名称：新乡海滨智能运营管理平台。

M1 已 closeout 为 COMPLETED，但 Owner 亲自验收后发现大量产品功能没有真正页面可体验——「方案完成」不等于「功能完成」。M1-FIX 阶段定位为功能补漏，补齐 M1 承诺但未实际可体验的产品功能。

## 当前轮次

M1-FIX-B2：导入口径、安全与准确性修复。当前状态：COMPLETED。已通过 Claude 审查（初审 FAIL → B2-FIX 复审 PASS），Codex closeout 已完成。

M1-FIX-B3：考勤工作台入口、App 命名与 HRMS 数据一致性修复。当前状态：REVIEWING，等待 Claude 审查。

M1-FIX-B4：考勤模块架构收敛与单一入口重整。当前状态：REVIEWING / Claude PASS，但 Owner 数据链路验收发现后续问题。B4 只收敛桌面入口、Workspace、Workspace Sidebar、导入页和 HBOS / HRMS 入口口径；M1-FIX-B3 不 closeout。

M1-FIX-B5：导入数据链路核查与报表口径收敛。当前状态：REVIEWING，等待 Owner 和 Claude 审查。B5 只核查真实 Employee / Checkin / Attendance / 月度暂存链路，收敛 HBOS 报表和 HRMS 技术核查入口；M1-FIX-B3 / B4 不 closeout。2026-08-21 后续修正：四车间 10 人行政班误判迟到修复、质量控制部四班次人员「满 8 小时算正常」口径收敛、配对上限 13h（见 B5 主文档「B5 后续修正」节）。2026-09-02 追加：班次管理页新增「规则看板」Tab，三类班次判定规则可视化（规则记录/内置班次/名单与配对参数）。2026-09-02 再追加：规则看板可导出班次人员维护表（5-sheet：部门-班次-人员主表 + 豁免/特殊班次/行政班名单/说明）。2026-09-03 追加：月度考勤汇总新增「AI复核」（enable_ai 隐藏临时列）——确认人次后逐人调 LLM 复核迟到/早退/缺勤，随导出透传，重新筛选自动复位。2026-09-08 追加：工作台新增「部门看板」（实时出勤快照 + 历史回顾；排班优先+规则推断，通用倒班计入应出勤，保守迟到判定回顾不判缺勤；60s 自动刷新 + 手动同步 120s 节流；+8 时区；接口角色门禁）——设计 spec 与实施计划已入库，运行态 migrate 注册待 Owner 授权。2026-09-11 追加：考勤提醒改发飞书卡片（只列异常部门+人名，正常部门汇总一行；渲染失败自动降级纯文本；判定口径与调度不变）。2026-09-15 追加：卡片运行态验证完成（Owner 授权）——实测裁定 interactive 报文外壳字段名为顶层 `card`（`code:0`）；原稿写的 `content` 会被拒（`code:19002`）且按设计不补发纯文本，等于提醒每天静默消失；干跑数字与看板同源一致、恒等式成立；已实发卡片到群（`sent: true`）；backend/scheduler 已 `restart` 加载新代码，次日 09:00 起自动发卡片。2026-09-24 追加：名单单一来源收敛（行政班 221→178 单一来源；无菌 48→59 改用 `pairing.SPECIAL_SHIFT_NUMS`；`EXCLUDE_NUMS` 冗余已标注、「无菌是否整批排除」待 Owner 裁定；旧引擎 `pair_checkins.py`/`shift_matcher.py`/`generate_attendance.py` 补废弃标记）与 PR 审查 5 项修复（去重窗口与配对下限对撞、`.env.example` 缺 9 变量、CI `.env` 门禁误伤模板、部门看板 XSS、月报 AI 复核 `list.index`）。行为变化：耿献磊失去周末双休豁免、3 名设备动力部人员获得豁免。全量测试 443→445 全绿。

M1-FIX-B-FIX：Excel 导入与中文体验修复。历史轮次；当前后续修复由 M1-FIX-B2、M1-FIX-B3、M1-FIX-B4、M1-FIX-B5 管理。

M1-FIX-F：调休模块（**两个阶段均已上线**）。当前状态：**REVIEWING**。业务规则（Owner 2026-09-21）：调休日 = 飞书日期字段区间；加班日 = LLM 从「说明」自由文本提取；核实 = 加班日当天有完整上下班配对，全部通过才「已核实」——**这是调休与请假的判定差异所在**（请假审批通过即豁免，调休须先核实加班日）。

- **第一阶段**（同步 + LLM 解析加班日 + 打卡核实 + 落库）：交付 `rest_leave.py` 纯逻辑模块、DocType 4 个新字段、`sync_rest_leave.py` 三段（`*/30` 同一有序列表），并退休从未 migrate 的换班（`HBOS Shift Swap Record`）全部产物。**只产出结论、不改变任何考勤结果**。实测：119 条入库、103 条解析、41 已核实 / 53 核实不通过 / 14 解析失败。上线中修复三项阻断（模型下线、`HBOS_AI_*` 未注入队列容器、nginx 需 `reload` 而非 `restart`）。
- **第二阶段**（接入考勤判定豁免）：新建 `rest_leave_apply.verified_rest_dates()` 作为「已通过 + 已核实」的**唯一查询口径**（有测试防止第二份副本）；`api.py` 把已核实调休日并入豁免集合、并把记录班次标为 `调休`；看板**两条**标签路径（实时 + 回顾）均接入，显示「请假（调休）」；`sync_rest_leave.py` 重解析失效键补入 `employee`。
- 全量测试 311 → **437 全绿**。分支 `m1-fix-c-rest-leave`。
- **执行中造成并已修复的数据事故**：`regenerate_attendance` 的清理语句含第二条 DELETE，会删除 `attendance_date > range_end` 的全部记录，故窄窗口重算会静默摧毁后续数据。我按乱序执行窄窗口重算，一度删除 8/15–9/21 全部记录。已按**时间升序**逐段重建恢复。
- **整支复查**：功能正确；驳回并更正了我「8/14 属文档已记载遗留问题」的错误归因（8/14 的 223 条缺勤是本轮重算生成、从未验证的数据，机制为取数窗口跨过 8/15 时触发配对严格分支）。Owner 决定**暂不处理**，等专门轮次。复查另抓到我漏的月报 bug（调休被算成「正常出勤」）已修。
- 命名说明：原拟用 `M1-FIX-C`，因该编号已属「异常说明三级流程」，改用 `M1-FIX-F`，待 Owner 确认。
- 主文档 `docs/milestones/M1_FIX_F_调休模块第一阶段落地记录.md`。

**M3-PORTAL-R1**（HBOS 门户工作台集成，分支 `feature/hbos-portal-workbench`）：REVIEWING（R1–R4 均已交付）。基于 `m1-fix-c-rest-leave` HEAD `93ae18a`，19 提交。以长期分支 `origin/feature/hbos-portal-product` 为基准**选择性移植**（**非 merge**），新增 Vue 3 门户 SPA（`frontend/hbos-portal-web`）、`hbos_portal` 薄平台 App 与考勤 portal 适配层，并以**同域 iframe** 在门户内容区承载现有 Frappe 考勤页面（「导航不出门户」）。

- R1 移植（Task 1–3）/ R2 同域通路（Task 4–7：Vite 5178 代理 12 条 Frappe 前缀 + iframe 承载）/ R3 接真实数据（Task 8–10：compose 加 8 挂载 + 6 `PYTHONPATH` → 重建 5 个 app 容器；`hbos_portal` 装入 `frontend` site 并 `migrate`）均已完成。
- **R4 生产形态已于 2026-09-28 交付，必须 Owner 明确授权后才能开始**；R4 前不得表述为「生产可用」。
- 验收：考勤测试 458 通过（本轮前基线 445）、`hbos_portal` 测试 14 通过、前端构建通过；**判定核心 `pairing.py` / `api.py` / `rule_lists.py` 相对 `93ae18a` 逐字节不变**（多轮审查 `git diff --stat` 为空）；装 + migrate 零副作用（`tabAttendance` 31541→31541、`tabEmployee` 711→711、`tabEmployee Checkin` 58863→58863、`stopped=0` 调度任务 104→104 且名称清单逐字节相同）；frappe 模式四指标与后端 `dashboard_data.get_data()` 逐值一致（异常人员 388 / 本周迟到 0 / 本周早退 0 / 本周缺勤 2234）；iframe 来源为 5178（同源）。普通员工门户准入按设计未开放（非缺陷）。
- **本轮破例四项，均经 Owner 明确授权**（不写 Docker Compose → 写；不做前端驾驶舱 → 做；不启动大型 Vue/React 前端 → 启动；portal 分支实施计划 §5 不用 iframe → 选定同域 iframe）。**破例范围严格限于此四项**，其余禁令继续生效。
- 副作用与缺口（migrate 移除 `HBOS Attendance Policy Assignment` 元数据记录、422 行数据完好但暂不可达、Vite 代理覆盖缺口、3 个 CSS bundle 既有 404 等）详见 `docs/PROJECT_STATUS.md`「M3-PORTAL-R1 HBOS 门户工作台集成 状态」节与主文档 `docs/milestones/M3_PORTAL_R1_HBOS门户工作台集成实施记录.md`。
- 命名说明：编号 **M3-PORTAL-R1**（Owner 2026-09-28 裁定）。本工作线不是 M1-FIX 考勤功能补漏轮次，故不套用 `M1-FIX-*`；原 `M2` 前缀冲突（`docs/milestones/README.md` 既把 `M2` 定义为「飞书集成」、又让库存隔离用 `M2` 前缀）已一并裁定——`M2` 归飞书集成、库存改号 `M4-STOCK-R1`，本工作线取 `M3`。

**M3-PORTAL-R1 后续（2026-09-29，REVIEWING）**：考勤仪表盘 / 人员管理 / 部门看板三页由**同域 iframe 内嵌改为门户 SPA 原生页**，Desk 侧 6 个考勤页接入**共享视觉层**，并顺带修复班次管理写接口缺失的服务端角色门禁。

- 门户侧：新增 3 个视图 + 3 个 service（复用既有 `frappeClient`）；`migration_mode` 由 `legacy` 改 `native`；`resolve_stable_route` 改为**解析回自身**并新增稳定路由白名单（**未注册路径在解析阶段即落 403，不悄悄透传**）；契约测试 13 → 15。
- Desk 侧：新增 `hbos_attendance.bundle.css` + `app_include_css`，6 页挂 `.hbos-surface`；**全部规则限定该 class 内**（实测 `:root` 无 `--h*`、Desk 侧边栏字体不受影响）。
- 验收：考勤 **458 → 460 通过**；`npm run build` 通过；浏览器实测**门户页 / Desk 页 / 后端接口三方逐值一致**（仪表盘 3/0/1931/404/53.8%/696；部门看板 42.2%/505/213/0/20/0/3/53）；判定核心三文件零改动；未重建容器、未 `migrate`。
- 顺带修复（与前端无关，独立提交）：`shift_management_data.py` 13 个裸 `@frappe.whitelist()` 补读/写角色门禁。**只修了这半**——另有 9 处无守卫写接口未处理（含同等级爆炸半径的 `bind_shift` / `bulk_bind_shift`）。
- 遗留：两个原生子页**无导航入口**（属新前端开发活动，按 Gate 需先出原型，本轮不加）；`docs/experience/` 在本分支不存在但被代码引用（Owner 裁定保留引用、不移植）；`M3_START_GATE.md` 缺失（既有治理缺口）。
- 主文档 `docs/milestones/M3_考勤页原生化与Desk共享视觉层.md`。**本轮未认领新里程碑编号**（`R1`~`R4` 已被 M3-PORTAL-R1 用作内部阶段号），编号是否重排待 Owner 裁定。

**M3-PORTAL-R1 后续（2026-10-02，REVIEWING）**：Desk 四页视觉改造 + 门户考勤应用内导航。

- **Desk 四页**（补齐上一批只挂 class 未改版的部分）：人员管理 / 导入考勤机导出表 / 月度考勤上传 / 班次管理全部按 **V1 操作面**改版（实色面板、密集行、表头吸顶、无动效；玻璃只留工具条外壳）。硬编码色值与字号全部换成 `var(--h-*)` 与契约允许的 12/14/16/20/30 档；顺带补上部门名 / 姓名 / 规则名的 **XSS 转义**。
- **关键发现：Desk 页面缓存不会自愈**。Frappe 把标准 `Page` 脚本缓存进浏览器 localStorage，失效判据是 **`Page` 文档的 `modified`**，而改磁盘 `.js` 不动该字段 → 所有看过该页的浏览器**永远跑旧版本**；**F5 / Cmd+Shift+R 无效**，只有 Frappe 的 `Ctrl+Shift+R`（**Control** 键）才清。修复：一次性顶 6 个 `modified` + 长期工具 `bump_page_cache.py` + 写入前端规范 §1.1.1。**顶时间戳时发现仪表盘与部门看板的 `modified` 同样陈旧**（JS 改于 9-28 23:15/23:31，时间戳停在 16:29）。
- **我引入并修复的缺陷（留档）**：修「两页抢顶层 `renderPage`」时把函数收进 IIFE，**但 `on_page_load` 赋值留在闭包外** → `ReferenceError`、页面**整个空白**；症状从「旧界面」变「白页」一度误导排查，靠控制台报错才确认。已修 + 对六页做 IIFE 边界自检。
- **门户考勤导航**（按 Gate 先出原型，Owner 从三案选定 **B 顶部页签**）：新增 `AttendanceLayout.vue`（对齐 `LimsLayout`：GlobalHeader + aurora + 移动导航）；三条路由改为其**子路由**（原为并列顶层路由、**不带门户外壳**，玻璃卡浮在白底上）；页签精确匹配高亮；右侧「管理后台」链 `/app/海滨考勤工作台`（Workspace）**新开页签**。Owner 同时裁定**班次管理 / 导入 / 月度上传暂不搬进门户**（另开一轮）。
- **验收**：考勤 **467 通过**；`npm run build` 通过；浏览器实测 Desk 四页新结构齐备、**旧结构计数为 0**；门户三页签切换与高亮正确、管理后台 200→302→Desk、门户外壳 `.aurora` 计数 2（此前缺失）。
- **运行态影响**：动过数据库一次（6 个 `Page.modified`）；4 个页面 JS 经 bind-mount 即时生效；未重建容器、未 `migrate`、未 `bench build`。
- 主文档 `docs/milestones/M3_考勤Desk页视觉改造与门户导航.md`；原型 `docs/frontend/prototypes/2026-10-02-考勤应用内导航方案.html`。**未认领新里程碑编号**。



- **来源**：改动来自 2026-10-01 另一个中断的会话，本轮为**接管收口**（核对、实测、记录、提交）。落点由 Owner 2026-10-02 裁定为**另开分支承载**，以保住门户分支「判定核心零改动」的约束。
- **⚠ 运行态尚未生效**：bind-mount 目录已含新代码，但常驻进程内存里是旧代码、新起进程是新代码（已记录的「同一数据两个答案」模式）——**重启前不要用 `bench execute` 核对页面数字**。生效需重启容器 + 按**升序**定向重算（定时窗口覆盖不到 9 月），均待授权。
- 审查发现（记录不修）：`打卡流水` 报表是配对函数第二调用点、未传 `long_duty`（当前无可见影响，方向优先取设备 SN）；`audit_misjudgments.py` 会误报本修复**故意**产出的 24h Present（该脚本全仓库无引用）。



M1-FIX 后续规划轮次（仅规划，不自动启动）：

| 轮次 | 名称 | 优先级 | 状态 |
| --- | --- | --- | --- |
| M1-FIX-A | 差距盘点与实施方案 | — | REVIEWING |
| M1-FIX-B | Excel 导入与真实本地数据闭环 | P0 | REVIEWING |
| M1-FIX-B-FIX | Excel 导入与中文体验修复 | P0 | REVIEWING |
| M1-FIX-B2 | 导入口径、安全与准确性修复 | P0 | COMPLETED |
| M1-FIX-B3 | 考勤工作台入口、App 命名与 HRMS 数据一致性修复 | P0 | REVIEWING / Owner UI 验收未通过 |
| M1-FIX-B4 | 考勤模块架构收敛与单一入口重整 | P0 | REVIEWING / Claude PASS，Owner 数据链路验收发现后续问题 |
| M1-FIX-B5 | 导入数据链路核查与报表口径收敛 | P0 | REVIEWING |
| M1-FIX-F | 调休模块（一阶段：同步+解析+核实；二阶段：接入判定豁免） | P1 | REVIEWING / 两阶段均已上线 |
| M1-FIX-C | 异常说明三级流程 | P1 | PLANNED |
| M1-FIX-D | 考勤工作台 + 月报 + 领导 Demo | P1 | PLANNED |
| M1-FIX-E | 飞书 OAuth 最小验证 + Owner 体验脚本 + 总审查 | P2 | PLANNED |

## M1 历史轮次（已完成）

M1 规划收口已完成；产品交付仍在 M1-FIX 中，尚未完成。全部 19 个历史轮次状态见里程碑索引。

M0 已完成并封板。M0-REMOTE 已完成。

权威状态文件：

- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/milestones/M0.md`

权威方案文件：

- `docs/milestones/M1_FIX_功能补漏实施方案.md`

## M1-FIX-B 范围（历史轮次）

M1-FIX-B / M1-FIX-B-FIX 只做 Excel 导入与真实本地数据闭环修复：

- 创建轻量 `hb_attendance_app`
- 创建导入日志
- 支持 Owner 在 Frappe Desk 页面上传考勤机月度导出表、识别预览、确认导入、查看导入日志与中文结果
- 创建 / 匹配 Employee
- 生成打卡流水
- 尝试 HRMS 原生自动考勤，并在必要时记录本地兜底生成
- 生成考勤结果并展示导入统计、重复跳过说明和失败摘要
- 默认白班/行政班为 08:30-17:30
- 不提交真实 Excel、真实员工清单或导入产物

## M1-FIX-F 范围

调休模块：
- 一阶段：同步 → LLM 解析加班日 → 打卡核实 → 落库（只出结论）
- 二阶段：把已核实的调休日接入考勤判定与看板（真正豁免）

- 飞书调休表 → `HBOS Rest Leave Record`（同步）
- 「说明」自由文本 → LLM 提取加班日并**落库**（解析）
- 加班日当天是否有完整上下班配对 → 写核实结论（核实）
- 三段挂 `*/30` 同一有序列表；退休从未 migrate 的换班全部产物

M1-FIX-F **不做**：

- 不做终态重新核实（F4，Owner 决定先观察）
- 不做加班模块本体（加班审批、加班余额、抵扣核对）、不做额度校验
- 不做半天/小时级调休（飞书表无时段字段）
- 不改 `pairing.py`（二阶段靠并入既有豁免集合实现，判定核心零改动）

## 本轮禁止事项

-- 不创建 `hb_core_app`
-- 不创建 `hb_feishu_app`
-- 不创建月度汇总 DocType
-- 不创建异常三级流程 DocType
- 不创建/删除/清理 TEST 数据
- 不接真实考勤机
- 不配置真实飞书密钥
- 不要求 Owner 在聊天中粘贴 App Secret
- 不提交 `.env`、密钥、token、数据库、日志、缓存、运行产物
- 不修改 Frappe/ERPNext/HRMS 核心源码
- 不启动大型 Vue/React 前端
- 不在 M1-FIX 轮次内做 M2 工作（M4-STOCK-R1 已在独立分支 `m4-stock-r1` 进行）
- 不把「计划可行」写成「功能已实现」

## M1-FIX 全阶段禁止事项

- 不创建 `hb_core_app`
- 不修改 Frappe/ERPNext/HRMS 核心源码
- 不提交 `.env`、App Secret、密钥、token
- 不提交真实员工姓名、真实工号、真实数据
- 不提交 Excel/CSV 数据文件
- 不接真实考勤机
- 不部署公司内网/云服务器
- 不启动大型 Vue/React 前端
- 不在 M1-FIX 轮次内做 M2 工作（M4-STOCK-R1 已在独立分支 `m4-stock-r1` 进行）
- 不伪造飞书登录成功
- 不执行 `docker compose down -v`
- 不删除 Docker volume
- 不重建 `frontend` site

## 当前状态口径

```
M1     = IN_PROGRESS（产品交付，M1-FIX 中）
M1-FIX = IN_PROGRESS
M1-FIX-A = REVIEWING
M1-FIX-B = REVIEWING
M1-FIX-B-FIX = REVIEWING
M1-FIX-B2 = COMPLETED
M1-FIX-B3 = REVIEWING / Owner UI 验收未通过
M1-FIX-B4 = REVIEWING / Claude PASS，Owner 数据链路验收发现后续问题
M1-FIX-B5 = REVIEWING
M1-FIX-F = REVIEWING / 两阶段均已上线
M4-STOCK-R1 = IN_PROGRESS（库存模块隔离，分支 `m4-stock-r1`）
M2 其余轮次 = NOT STARTED / WAITING OWNER AUTHORIZATION
M3-PORTAL-R1 = REVIEWING（HBOS 门户工作台集成，分支 `feature/hbos-portal-workbench`；R1–R4 均已交付；2026-09-29「考勤页原生化 + Desk 共享视觉层」、2026-10-02「Desk 四页视觉改造 + 门户应用内导航」两批后续交付同为 REVIEWING）
```

## 下一轮预告

M1-FIX-F 两阶段均已上线：一阶段产出核实结论（119 条入库、41 已核实 / 53 核实不通过 / 14 解析失败），二阶段已把已核实调休日接入考勤豁免与看板（看板显示「请假（调休）」），全量测试 437 全绿。整支复查已完成并处置。2026-09-24 追加：完成名单单一来源收敛（行政班 221→178、无菌 48→59 改用 `SPECIAL_SHIFT_NUMS`）与 PR 审查 5 项修复，全量测试 445 全绿。M1-FIX-B3 / B4 / B5 不 closeout。M1-FIX-C（异常说明三级流程）为 PLANNED / 待 Owner 授权。M1-FIX-D/E 未启动。**M4-STOCK-R1（库存模块隔离）为 IN_PROGRESS**，分支 `m4-stock-r1`，主文档 `docs/milestones/M4_STOCK_R1_库存模块隔离实施记录.md`；M2 其余轮次未启动。**M3-PORTAL-R1**（HBOS 门户工作台集成，分支 `feature/hbos-portal-workbench`）R1–R4 均已交付**——R4（nginx 分发门户产物 + `VITE_BASE=/hbos/`）**必须 Owner 明确授权后才能开始**，R4 前不得表述为「生产可用」；本工作线编号已裁定为 **M3-PORTAL-R1**。**2026-09-29 后续交付**：考勤三页原生化（`migration_mode` `legacy`→`native`）+ Desk 共享视觉层。**2026-10-02 后续交付**：Desk 四页视觉改造 + 页面缓存失效机制 + 门户考勤应用内导航（`AttendanceLayout.vue`，页签 + 管理后台入口）。两批均为 REVIEWING，主文档分别为 `docs/milestones/M3_考勤页原生化与Desk共享视觉层.md`、`docs/milestones/M3_考勤Desk页视觉改造与门户导航.md`；**均未认领新编号**，是否重排待 Owner 裁定。
