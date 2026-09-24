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

当前阶段：M0 工程启动与上下文治理已完成并封板；M1 产品交付仍在 M1-FIX 功能补漏中，尚未完成。M1-FIX-B2 已 COMPLETED；M1-FIX-B3 为 REVIEWING / Owner UI 验收未通过；M1-FIX-B4 为 REVIEWING / Claude PASS，但 Owner 数据链路验收发现后续问题；M1-FIX-B5 为 REVIEWING；当前 **M1-FIX-F（调休模块）为 REVIEWING / 两阶段均已上线**。

当前目标：M1-FIX-F 两阶段均已上线，整支复查已完成并处置；2026-09-24 已完成名单单一来源收敛与 PR 审查 5 项修复（全量测试 445 全绿）。**建议下一轮优先处理「分机实施前数据修复」**（8/14 的 223 条错误缺勤 + `pairing.py` 设备方向判定按天改造）与台账 #10「重算幂等改造」。M1-FIX-B3 / B4 / B5 不 closeout。M1 产品交付仍未完成，M1-FIX-C/D/E 未启动。**M2-STOCK-R1（库存模块隔离）为 IN_PROGRESS**，分支 `m2-stock-r1`；M2 其余轮次未启动 / 待 Owner 授权。

当前已在用户授权范围内安装 HRMS，并完成 Frappe HR 图标、基础 HR 模块和 Roster 页面的前端资源修复验证。M0-R3E HRMS 环境可复现性收口已完成并通过 Codex 审查，M0 整体状态为 COMPLETED。

M0-REMOTE 已完成 GitHub Private remote 创建、`origin` 绑定和 `main` 首次 push。M1-R0 已完成方案和诊断并通过 Codex 独立审查；M1-R1 已完成只读对象模型验证记录，并已通过 Codex 独立审查，状态为 COMPLETED。M1-R2 已完成配置试运行方案设计，并已通过 Codex 独立审查，状态为 COMPLETED。M1-R3 已创建部分 `TEST-HBOS-M1R3-` 虚构测试数据；Codex 审查 PASS 后，M1-R3 最终状态收口为 BLOCKED。M1-R3A 已通过 Codex 审查并收口为 COMPLETED。M1-R3B 已通过 Codex 审查并收口为 COMPLETED。M1-R3B-FIX 已通过 Codex 审查并收口为 COMPLETED。M1-R3C 已新增 `TEST-HBOS-M1R3C-*` 虚构 TEST 数据；M1-R3C 已通过 Codex 审查并收口为 COMPLETED，结论为 PARTIAL / GAP_IDENTIFIED。M1-R3D 已通过 Codex 审查并收口为 COMPLETED。M1-R3E 已通过 Codex 审查并收口为 COMPLETED。M1-R3F 已通过 Codex 审查并收口为 COMPLETED。M1-REQ-DESIGN-DRAFT 为 COMPLETED。M1-R4 为 COMPLETED，已通过 Codex 审查并收口。M1-R5 为 COMPLETED，已通过 Codex 审查并收口。M1-R6A 已通过 Codex 审查并收口为 COMPLETED。M1-R6B 为 COMPLETED。M1-R6C 为 COMPLETED（已通过 Codex 审查并 closeout）。M1-R7 为 COMPLETED（已通过 Codex 审查并 closeout）。M1 历史 closeout 已完成，但 Owner UI 验收发现产品功能缺口，因此当前 M1 产品交付仍处于 M1-FIX IN_PROGRESS。M1-FIX-B 已创建轻量 `hb_attendance_app`、导入日志和 `海滨考勤工作台`，并使用 Owner 本地真实 Excel 完成导入闭环验证；M1-FIX-B-FIX 已补齐页面导入与中文体验；M1-FIX-B4 已收敛运行态入口主线；M1-FIX-B5 已核查真实 Employee / Employee Checkin / Attendance / 月度暂存数据链路，新增月度汇总暂存报表并增强 HBOS 报表过滤；2026-08-21 后续修正：四车间 10 人行政班误判迟到修复（ADMIN_NUMS 补回 + 名单短路规则表 + admin_shift_from_gap）、质量控制部四班次人员「满 8 小时算正常」口径收敛、配对上限 13h→14h（李明 8/19 无菌班 13.17h 案例）、分机孤立卡误判缺勤修复（陈雨欣 8/19 案例：方向不同的相邻卡不合并 + 当天已有完整上下班结构时孤立卡不判缺勤）、跨天夜班下班误刷上班机修复（吕玉升/庞冠军 8/16 案例）；2026-08-27 后续修正：配对上限 14h→16h、有卡就不判缺勤、连续无打卡 1-2 天不判缺勤 3 天起判（8/15-26 缺勤 489→134）、月度考勤汇总新增「导出异常考勤」按钮、2026 年度离职名单批量处理；2026-09-02 追加：班次管理页「规则看板」Tab 与班次人员维护表导出；2026-09-03 追加：月度考勤汇总「AI复核」（enable_ai 逐人 LLM 复核异常，随导出透传）；2026-09-08 追加：工作台「部门看板」（实时出勤快照 + 历史回顾；排班优先+规则推断、通用倒班计入应出勤、保守迟到判定、回顾不判缺勤、60s 轮询 + 手动同步 120s 节流、+8 时区、接口角色门禁）——设计与计划、代码与测试（全量 144 通过）已入库，运行态 migrate 注册待 Owner 授权；2026-09-11 追加：考勤提醒改发飞书卡片（只列异常部门+人名，正常部门汇总一行；渲染失败自动降级纯文本；判定口径与调度不变）；2026-09-24 追加：名单单一来源收敛（行政班 221→178 改为引用 `rule_lists.py`、无菌 48→59 改用 `pairing.SPECIAL_SHIFT_NUMS`、`EXCLUDE_NUMS` 冗余标注且「无菌是否整批排除」待 Owner 裁定、旧引擎补废弃标记）与 PR 审查 5 项修复（去重窗口与配对下限对撞导致恰好 2h 的上下班卡误判缺勤、`.env.example` 缺 9 个变量致 AI 与 9 点卡片静默失效、CI `.env` 门禁无 `$` 锚点误伤 `.env.example`、部门看板 XSS、月报 AI 复核 `list.index`），全量测试 443→445 全绿。真实 Excel、真实员工清单和导入产物不提交 Git。M2-STOCK-R1（库存模块隔离）为 IN_PROGRESS（分支 `m2-stock-r1`），M2 其余轮次未启动。当前不接飞书真实写入，不实现 SSO，不做前端驾驶舱，除非用户明确授权对应轮次。

**M1-FIX-F 调休模块（2026-09-22~24，两阶段均已上线）**：调休按「模板同请假、判定独立」实现——调休日取飞书日期字段区间；加班日由 LLM 从「说明」自由文本提取；核实加班日当天是否有完整上下班配对，全部通过才「已核实」。**这是与请假的关键差异**（请假审批通过即豁免，调休须先核实）。

- **一阶段**（只出结论、不改考勤）：交付 `rest_leave.py` 纯标准库模块、DocType `HBOS Rest Leave Record` 的 4 个新字段、`sync_rest_leave.py` 三段（同步 → LLM 解析 → 核实，同一 `*/30` 有序列表），并退休从未 migrate 的换班全部产物。实测 119 条入库、103 条解析、41 已核实 / 53 核实不通过 / 14 解析失败。
- **二阶段**（接入判定）：新建 `rest_leave_apply.verified_rest_dates()` 作为「已通过 + 已核实」的**唯一查询口径**（有测试防止第二份副本）；`api.py` 并入豁免集合、记录班次标 `调休`；看板**两条**标签路径均接入（显示「请假（调休）」）。
- 全量测试 311 → **437 全绿**。分支 `m1-fix-c-rest-leave`。
- **关键约束**：LLM 结果落库，**判定热路径永不调用 LLM**（考勤每 10 分钟重算）。
- 上线中修复三项阻断：模型下线（`deepseek-v4-flash` 已不可用，实测 4 候选后改 `deepseek-flash`）、**`HBOS_AI_*` 只注入 backend 而 scheduler/queue 全缺**（定时任务 0.35 秒「成功」实则未调 LLM，且 `bench execute` 手动跑正常、永远测不出）、**nginx 502 的正解是 `nginx -s reload` 而非 `restart`**（已更正 `docs/HBOS考勤判定规则.md` §13.9）。
- **执行中造成并已修复的数据事故**：`regenerate_attendance` 的清理语句含第二条 DELETE（删 `attendance_date > range_end` 的全部记录），故窄窗口重算会静默摧毁后续数据。按乱序执行一度删除 8/15–9/21 全部记录，已按**时间升序**逐段重建恢复。
- **整支复查**：功能正确；驳回并更正了我「8/14 属文档已记载遗留问题」的错误归因——8/14 的 223 条缺勤是本轮重算生成、从未验证的数据（机制：取数窗口跨过 8/15 时触发配对严格分支）。Owner 决定暂不处理。复查另抓到我漏的月报 bug（调休被算成「正常出勤」）已修。
- 主文档 `docs/milestones/M1_FIX_F_调休模块第一阶段落地记录.md`。命名说明：原拟用 `M1-FIX-C`，因该编号已属「异常说明三级流程」，改用 `M1-FIX-F`，待 Owner 确认。

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
2. M1 历史 closeout 已完成，但产品交付仍在 M1-FIX 中，尚未完成。M1-FIX-B3 为 REVIEWING / Owner UI 验收未通过；M1-FIX-B4 为 REVIEWING / Claude PASS，但 Owner 数据链路验收发现后续问题；M1-FIX-B5 为 REVIEWING；**M1-FIX-F 为 REVIEWING / 两阶段均已上线**。M2-STOCK-R1（库存模块隔离）为 IN_PROGRESS（分支 `m2-stock-r1`）；M2 其余轮次未启动 / 待 Owner 授权。

## 前端实施流程规范

独立前端（Vue/React 驾驶舱、AI 工作台、复杂交互页面）开发必须遵循"原型先行 + Owner 审查 + 复刻实现 + 功能接入"流程。详见：

- `docs/frontend/FRONTEND_IMPLEMENTATION_GUIDE.md`

核心规则：凡涉及漂亮页面、驾驶舱、AI 工作台、复杂交互页面，必须先使用 `frontend-design` skill 产出原型/视觉方案，Owner 人工审查通过后再进入前端复刻和功能接入。Frappe Desk 后台页面不要强行重做成独立前端。

## 边界提醒

不直接修改 Frappe / ERPNext / HRMS 核心源码。优先使用原生配置、角色权限、DocType、报表、导入、API 和低代码定制。自定义 App 只用于海滨特有规则，不用于重写 HRMS 已有功能。`hb_attendance_app` 已在 M1-FIX-B 经 Owner 授权创建，后续不得擅自扩大为大而全 HR App。任何飞书真实写入必须由用户明确授权。

任何海滨自定义 App 生成、业务模型实现、真实业务数据配置、飞书真实写入、前端驾驶舱、AI 视频服务实现，以及 Docker volume 删除、site 重建或环境重构，都属于后续轮次或后续明确授权范围。
