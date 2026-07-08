# M1-R4：M1 Demo 技术方案与实施路线拆分

项目名称：新乡海滨智能运营管理平台。

状态：REVIEWING。

执行日期：2026-07-08。

审查记录：本轮为规划拆分轮，尚未提交 Codex 审查。

## 1. 文档定位

本文档是 M1-R4 的主文档。M1-R4 定位为 **M1 Demo 技术方案与实施路线拆分**。

注意：`docs/milestones/M1_START_GATE.md` 是 M1 阶段门禁文档，不是当前轮次主文档。本文件是当前轮次主文档。

## 2. 本轮定位

M1-R4 是**规划拆分轮**，不是执行轮。

本轮只做以下工作：

- 基于已补齐的 4 份设计文档，将 M1 Demo 后续实施拆分为明确的执行轮次（R5/R6/R7/可选 R8）
- 明确每轮的目标、输入、范围、禁止项、验收点和审查要求
- 重申并固化 M1 的技术边界、数据边界和运行边界

本轮**严格不做**：

- 不开发任何代码
- 不试运行任何功能
- 不创建任何 Frappe App（包括 `hb_hr_app`、`hb_attendance_app`、`hb_core_app`、`hb_feishu_app`）
- 不创建任何 DocType
- 不动数据库（不读写任何数据）
- 不接真实考勤机
- 不正式接飞书请假
- 不接飞书工作台
- 不部署公司内网或云服务器
- 不修改 Frappe / ERPNext / HRMS 核心源码
- 不清理或删除 TEST 数据

## 3. 输入文档

本轮依据以下 4 份已通过 Codex 审查的设计文档：

| 输入文档 | 用途 |
| --- | --- |
| `docs/milestones/M1_考勤一期真实需求确认.md` | 业务需求事实依据，5 轮 Owner 访谈结论 |
| `docs/milestones/M1_考勤一期产品需求说明书.md` | 产品设计，用户角色、场景、页面、流程图 |
| `docs/milestones/M1_考勤一期技术设计方案.md` | 技术路线，HRMS 对象复用、导入、飞书登录、权限设计 |
| `docs/milestones/M1_Demo实施路线图.md` | 实施拆分建议，R4/R5/R6/R7 轮次框架 |

这 4 份文档均为 M1-REQ-DESIGN-DRAFT 的组成部分，已通过 Codex 审查并收口为 COMPLETED。

## 4. M1 Demo 总目标

M1 Demo 总目标继承自 `M1_考勤一期真实需求确认.md` 第 12 项验收标准，共 12 条：

1. 人事能登录
2. 能看到考勤工作台
3. 能导入一份脱敏考勤 Excel
4. 能生成或展示月度考勤结果
5. 能识别迟到、早退、缺卡、缺勤
6. 员工能查看自己的记录
7. 员工能提交异常说明
8. 主管能确认异常
9. 人事能最终归档
10. 能导出 Excel 月报
11. 领导能看到汇总 Demo
12. 技术方案说明未来如何接真实考勤机

M1 不是正式生产上线，是内部可演示版本 + 可给人事试用的本地 Demo。M1 要求一周内要有东西可演示。

## 5. 后续轮次拆分

以下拆分基于 4 份设计文档中的路线建议，进一步明确每轮的目标、范围、禁止项和验收点。

后续 R5/R6/R7 均为 **PLANNED**，需用户逐轮明确授权后方可启动。不得在未经授权的情况下启动任何后续轮次。

### 5.1 M1-R5：HRMS 配置基线、考勤工作台与月度汇总 Demo

**状态**：PLANNED（待用户授权启动）。

**定位**：

基于 HRMS/Frappe 原生能力建立 M1 Demo 配置基线；建立考勤工作台入口；建立月度汇总展示与导出路径。本阶段仍优先复用 Frappe Desk / Workspace / Report，暂不启动大型 Vue 前端。

**目标**：

- 完成 HRMS 生产级配置基线：Company（基于真实组织架构）、Department（真实部门结构）、Employee（虚构员工姓名、真实组织架构）、Shift Type（白班/中班/夜班/行政班）、Holiday List、Leave Type、Leave Allocation（最小配置）
- 搭建 Frappe Desk 考勤工作台 Workspace 入口
- 实现月度汇总 Query Report（优先 Frappe 原生）
- 实现月度汇总 Excel 导出（优先 Frappe 原生 Excel Export 或 Script Report）
- 配置 Frappe Role 和 User Permission，实现角色权限隔离

**输入文档**：

- `M1_考勤一期真实需求确认.md`（需求依据）
- `M1_考勤一期产品需求说明书.md`（产品设计）
- `M1_考勤一期技术设计方案.md`（技术路线）
- `M1_R4_Demo技术方案与实施路线拆分.md`（本轮）

**允许的修改范围**：

- 在本地 Docker 环境中创建 HRMS 配置数据（Company、Department、Employee、Shift Type、Holiday List、Leave Type、Leave Allocation 等）
- 创建虚构 Demo 数据（Employee 使用虚构姓名、真实组织架构）
- 创建 Frappe Desk Workspace 自定义
- 创建 Query Report / Script Report
- 配置 Frappe Role 和 User Permission

**禁止项**：

- 不接真实考勤机
- 不接飞书登录
- 不正式接飞书请假
- 不接飞书工作台
- 不创建 `hb_hr_app`（除非自定义 Workspace / Report 确实无法在现有 site 中实现）
- 不创建复杂自定义 DocType（除非 R5 规划明确为后续评估项并获用户授权）
- 不启动大型 Vue 前端
- 不导入真实员工姓名
- 不使用未脱敏真实考勤数据
- 不部署公司内网或云服务器
- 不修改 Frappe / ERPNext / HRMS 核心源码
- 不执行 `docker compose down -v`
- 不删除 volume
- 不重建 `frontend` site

**验收点**：

1. 人事能登录（本地管理员账号）
2. 能在考勤工作台看到员工列表、班次配置、节假日配置
3. 能在页面看到月度汇总报表（含员工姓名、部门、应出勤天数、实际出勤天数、迟到次数、早退次数、缺卡次数、缺勤天数、请假、加班、最终状态等字段）
4. 能导出月度汇总 Excel
5. 角色权限隔离生效（员工只能看自己，主管只能看本部门，人事看全公司）
6. 配置基线可复现（有明确的配置步骤或脚本）

**Codex 审查**：需要。R5 完成后进入 REVIEWING，提交 Codex 审查。

**Closeout**：需要。Codex PASS 后执行 closeout 状态收口。

---

### 5.2 M1-R6：脱敏 Excel 导入、异常识别与异常说明流程

**状态**：PLANNED（待用户授权启动）。

**定位**：

实现两类 Excel 导入（原始打卡流水导入 + 月度汇总 Excel 导入）；实现迟到、早退、缺卡、缺勤的自动识别；实现员工→主管→人事三级异常处理流程。

**目标**：

- 实现原始打卡流水 Excel 导入（Employee Checkin → Auto Attendance → Attendance）
- 实现月度汇总 Excel 导入（独立展示或月度汇总 DocType，不触发 Auto Attendance）
- 保留导入批次记录（导入批次号、导入人、导入时间、来源文件名、总/成功/失败数、失败原因）
- 迟到识别（late_entry = 1，宽限期 0 分钟）
- 早退识别（early_exit = 1，宽限期 0 分钟）
- 缺卡识别（上班缺卡 or 下班缺卡，单边打卡判定）
- 缺勤识别（有排班、无请假、无打卡 → 缺勤；全天无打卡按判断顺序：先看请假 → 再看节假日 → 再看排班）
- 员工提交"考勤异常说明"（6 种类型：补卡/设备异常/公出会议/班次错误/请假未同步/其他）
- 部门主管确认异常事实（确认/驳回）
- 人事/考勤管理员最终处理并归档
- 所有修改留痕（谁、什么时候、改了什么、修改原因、处理状态）

**输入文档**：

- `M1_考勤一期真实需求确认.md`（需求依据）
- `M1_考勤一期产品需求说明书.md`（产品设计）
- `M1_考勤一期技术设计方案.md`（技术路线）
- `M1_R4_Demo技术方案与实施路线拆分.md`（本轮）
- M1-R5 的输出（配置基线与工作台）

**允许的修改范围**：

- 创建 Excel 导入流程（优先 HRMS Data Import；如不满足则建自定义导入入口）
- 如必要，创建自定义 DocType（需用户逐项授权）：`Attendance Exception`（异常说明）、`Attendance Correction`（修正记录）、`HBOS Import Log`（导入批次）
- 如必要且经用户授权，创建 `hb_hr_app` 承载自定义 DocType
- 创建 Client Script / Server Script 实现异常判定逻辑
- 配置 Workflow 或状态流转
- 创建操作留痕机制

**禁止项**：

- 不接真实考勤机
- 不接飞书请假（仅可做接口设计预留，不做真实接入）
- 不接飞书工作台
- 不创建 `hb_hr_app` 未经用户明确授权
- 不导入真实员工姓名
- 不使用未脱敏真实考勤数据
- 不把月度汇总 Excel 当成原始打卡流水（两类导入必须在代码和 UI 层面区分）
- 不部署公司内网或云服务器
- 不修改 Frappe / ERPNext / HRMS 核心源码
- 不执行 `docker compose down -v`
- 不删除 volume
- 不重建 `frontend` site

**验收点**：

1. 能导入脱敏打卡流水 Excel，生成 Employee Checkin 并触发 Auto Attendance 生成 Attendance
2. 能导入月度汇总 Excel，在对账/展示入口中呈现，且不错误触发 Auto Attendance
3. 导入批次日志可查（批次号、导入人、时间、文件、成功/失败数）
4. 迟到/早退自动识别（late_entry/early_exit 正确置位）
5. 缺卡自动识别（上班单边/下班单边可区分）
6. 缺勤自动识别（按判断顺序：请假→节假日→排班→缺勤）
7. 员工能查看自己的考勤结果和异常
8. 员工能提交考勤异常说明（6 种类型可选）
9. 部门主管能查看本部门异常并确认/驳回
10. 人事/考勤管理员能最终处理并归档
11. 所有异常处理操作留痕可查（谁、什么时候、改了什么、原因、状态）
12. 月度汇总报表正确反映迟到/早退/缺卡/缺勤/请假/加班/最终状态

**Codex 审查**：需要。R6 完成后进入 REVIEWING，提交 Codex 审查。

**Closeout**：需要。Codex PASS 后执行 closeout 状态收口。

**两类导入的关键区分**：

| 维度 | 原始打卡流水导入 | 月度汇总 Excel 导入 |
| --- | --- | --- |
| 数据内容 | 员工 + 日期 + 上班打卡时间 + 下班打卡时间 | 员工 + 月度统计字段 |
| 目标对象 | Employee Checkin → Attendance | 自定义汇总 DocType 或独立报表 |
| 是否触发 Auto Attendance | 触发 | 不触发 |
| 用途 | 生成考勤结果 | 对账、展示、历史迁移、演示报表 |

不得把月度汇总表错误当成原始打卡流水。

---

### 5.3 M1-R7：飞书登录、领导汇总 Demo 与 M1 收口

**状态**：PLANNED（待用户授权启动）。

**定位**：

实现飞书 OAuth 登录 + Employee 自动匹配；搭建领导汇总 Demo 视图；完成 M1 Demo 整体验收与收口。

**目标**：

- 实现或验证飞书 OAuth 登录（通过 Frappe Social Login Key 接入）
- 飞书登录成功后按手机号（优先）/ 邮箱 / 工号匹配 Employee
- 已匹配则进入对应角色页面
- 未匹配则提示"未找到匹配员工，请联系人事"
- 权限仍由 Frappe / HRMS User Role 控制（飞书身份只负责登录）
- 本地管理员账号作为管理兜底
- 搭建领导汇总 Demo 视图（本月异常人数、迟到总次数、缺卡总次数、部门排名）
- 领导可查看和导出月报
- 完成 M1 Demo 12 项验收标准的逐项确认
- 完成 M1 文档整理和 Demo 演示准备

**输入文档**：

- `M1_考勤一期真实需求确认.md`（需求依据）
- `M1_考勤一期产品需求说明书.md`（产品设计）
- `M1_考勤一期技术设计方案.md`（技术路线）
- `M1_R4_Demo技术方案与实施路线拆分.md`（本轮）
- M1-R5 的输出（配置基线与工作台）
- M1-R6 的输出（导入与异常处理）

**允许的修改范围**：

- 配置 Frappe Social Login Key（飞书 OAuth Provider）
- 实现飞书身份 → Employee 自动匹配逻辑
- 如必要且经用户授权，创建自定义 Script 实现匹配逻辑
- 创建领导汇总 Report / Dashboard Page
- M1 文档整理和状态台账同步

**禁止项**：

- 不接飞书工作台
- 不正式接入飞书请假（只确认接口设计预留）
- 不接飞书审批
- 不接飞书消息推送
- 不执行飞书真实写入
- 不部署公司内网或云服务器
- 不正式上线生产
- 不修改 Frappe / ERPNext / HRMS 核心源码
- 不执行 `docker compose down -v`
- 不删除 volume
- 不重建 `frontend` site

**验收点**：

1. 飞书扫码登录成功
2. 登录后根据手机号/邮箱/工号自动匹配 Employee，进入对应角色页面
3. 未匹配用户收到"联系人事"提示
4. 本地管理员账号可正常兜底登录
5. 领导能看到汇总 Demo（异常人数、迟到次数、缺卡次数、部门排名）
6. 领导能查看和导出月报
7. M1 Demo 12 项验收标准逐项确认通过
8. M1 文档完整、状态台账同步

**Codex 审查**：需要。R7 完成后进入 REVIEWING，提交 Codex 审查。

**Closeout**：需要。Codex PASS 后执行 closeout 状态收口。

**飞书请假本轮边界**：

- 飞书请假本轮只做接口设计或后续预留。
- 不作为 M1 一周内第一阻塞项。
- 不正式接入飞书请假（不包括在 M1 Demo 验收标准内）。
- 不接飞书工作台。

---

### 5.4 M1-R8：M1 Demo 验收修复与文档收口（可选缓冲轮）

**状态**：PLANNED（可选缓冲轮，不预先承诺一定执行）。

**定位**：

如果 R5/R6/R7 验收中发现需要修复的问题，且不适合在对应轮次内解决，则在 R8 集中修复。如果 R5/R6/R7 验收全部通过，R8 可跳过。

**目标**：

- 修复 R5/R6/R7 验收中发现的遗留问题
- M1 文档和状态台账最终梳理
- M1 整体 closeout

**输入文档**：

- R5/R6/R7 Codex 审查报告
- M1 Demo 验收发现的遗留问题清单

**是否执行**：由用户根据 R5/R6/R7 验收结果决定。如无需修复，直接跳过 R8 进入 M1 closeout。

---

## 6. 每轮输出物总结

| 轮次 | 目标 | 是否需要 Codex | 是否需要 closeout |
| --- | --- | --- | --- |
| M1-R5 | 配置基线 + 考勤工作台 + 月度汇总 Demo | 需要 | 需要 |
| M1-R6 | Excel 导入 + 异常识别 + 异常说明流程 | 需要 | 需要 |
| M1-R7 | 飞书登录 + 领导 Demo + M1 收口 | 需要 | 需要 |
| M1-R8 | 验收修复与文档收口（可选） | 按需 | 按需 |

## 7. 技术边界

以下技术边界在 M1 全阶段（含后续 R5/R6/R7）中保持：

### 7.1 复用优先

- 继续优先复用 Frappe / ERPNext / HRMS 原生对象和能力。
- 优先使用原生配置、角色权限、DocType、报表、导入、API 和低代码定制。

### 7.2 不修改核心源码

- 不修改 Frappe / ERPNext / HRMS 核心源码。
- 所有功能通过 Frappe Hook、Custom DocType、Client/Server Script、Query/Script Report、Frappe Page/Workspace、Frappe Role/User Permission、Frappe Data Import、Frappe Social Login Key、Frappe REST API 实现。

### 7.3 运行环境

- M1 只在本地 Mac / Docker 跑。
- M1 不部署公司内网。
- M1 不部署云服务器。

### 7.4 自定义 App 决策边界

- 允许评估轻量自定义 App，但 M1-R4 本轮不创建。
- 如未来需要自定义 App，倾向命名为 `hb_hr_app`。
- 仅在 HRMS 原生能力确实无法覆盖、且经用户明确授权时，才创建自定义 App。
- 自定义 App 只用于海滨特有规则，不用于重写 HRMS 已有功能。

### 7.5 异常流程技术路线

- 优先用 HRMS 原生 Attendance Request / Leave Application 等对象凑流程。
- 如果不能满足海滨 6 种异常说明类型和设备异常等特有场景，再评估自定义 DocType：
  - `Attendance Exception`：考勤异常说明记录
  - `Attendance Correction`：考勤修正记录（留痕）
- 本轮（R4）不得写成已经创建 App 或 DocType。

### 7.6 飞书边界

- 飞书登录在 M1-R7 做。
- 飞书请假本轮只做接口设计预留，不正式接入。
- 飞书工作台 M1 不做。
- 所有飞书真实写入必须用户明确授权。
- 飞书身份只负责登录，权限由 Frappe Role 控制。

### 7.7 月度汇总报表

- 优先 Frappe Query Report。
- 如不足则 Script Report。
- 月度汇总字段包含：员工姓名、部门、应出勤天数、实际出勤天数、迟到次数、早退次数、缺卡次数、缺勤天数、请假天数/小时、加班小时、节假日出勤、异常待确认数、最终考勤状态、备注。

### 7.8 前端策略

- 第一优先：Frappe Desk / Workspace 聚合入口。
- 第二优先：可导出月报和异常处理流。
- 第三优先：轻量领导 Demo 视图。
- 暂不单独启动大型 Vue 前端。

## 8. 数据与脱敏边界

### 8.1 M1 数据策略

- M1 使用真实导出的考勤机 Excel，但必须脱敏。
- M1 使用真实组织架构（部门结构）。
- Demo 使用虚构员工姓名。
- 不得使用真实员工姓名。
- 不得使用未脱敏真实考勤数据。

### 8.2 两类导入不得混淆

- 原始打卡流水导入 → Employee Checkin → Attendance（生成考勤结果）。
- 月度汇总 Excel 导入 → 独立展示或汇总 DocType（对账、演示报表、历史迁移）。
- 不得把月度汇总表错误当成原始打卡流水。
- 不得让月度汇总导入触发 Auto Attendance。

### 8.3 导入批次

- M1 技术方案必须设计导入批次结构。
- M1 实现上可以先不做复杂批次管理。
- 如果使用自定义导入入口，则必须保留导入批次记录。
- 导入批次字段包括：导入批次号、导入人、导入时间、导入类型、来源文件名、总记录数、成功数、失败数、失败原因。

### 8.4 操作留痕

M1 至少记录：
- 谁
- 什么时候
- 改了什么
- 修改原因
- 处理状态

## 9. 风险与 Gate 检查点

以下 Gate 为技术评估项或待验证项。**标注「技术评估」或「待验证」的内容不是已确认要做的事，也不代表 Owner 已确认**。这些是后续执行轮次中需要关注和验证的风险点。

| Gate | 说明 | 类型 | 验证轮次 |
| --- | --- | --- | --- |
| Gate-1：HRMS Data Import 对打卡流水导入的支持 | 验证 HRMS 原生 Data Import 是否满足 Employee Checkin 批量导入、字段映射和错误处理需求。如不满足，评估自定义导入入口 | 技术评估/待验证 | M1-R6 |
| Gate-2：Attendance Request 是否足够支撑异常说明流程 | 验证 HRMS 原生 Attendance Request 是否支持海滨 6 种异常说明类型。如不满足，评估自定义 Attendance Exception DocType | 技术评估/待验证 | M1-R6 |
| Gate-3：月度汇总 Excel 与原始打卡流水字段混淆 | 确保两类导入在代码和 UI 层面严格区分。月度汇总导入不得错误触发 Auto Attendance | 技术评估/待验证 | M1-R6 |
| Gate-4：夜班跨日期 Attendance 归属 | 验证 Shift Type 跨夜配置 + Auto Attendance 的 Attendance Date 归属是否与人工理解一致 | 技术评估/待验证 | M1-R5 |
| Gate-5：迟到/早退标记置位 | 已在 M1-R3C 中确认 `late_entry`/`early_exit` 配置存在但未生效。需在 M1-R5 中按 0 宽限配置复测 | 技术评估/待验证 | M1-R5 |
| Gate-6：缺席判断逻辑完整性 | 全天无打卡的判断顺序（请假 → 节假日 → 排班 → 缺勤）需在 M1-R6 中完整实现并验证 | 技术评估/待验证 | M1-R6 |
| Gate-7：飞书登录 Employee 匹配字段稳定性 | 手机号 / 邮箱 / 工号作为匹配字段是否足够稳定。如飞书不返回手机号或 Employee 未维护手机号，需兜底方案 | 技术评估/待验证 | M1-R7 |
| Gate-8：是否需要创建 `hb_hr_app` | 仅在自定义 DocType/Workspace/Report 无法在现有 site 中实现时考虑。不得为"可能需要的自定义"提前创建空 App | 技术评估/决策 Gate | M1-R5/R6 |
| Gate-9：是否需要自定义 DocType | `Attendance Exception` / `Attendance Correction` 等自定义 DocType 仅在 HRMS 原生确实无法满足时创建，需逐项经用户授权 | 技术评估/决策 Gate | M1-R6 |
| Gate-10：是否需要大型 Vue 前端 | M1 优先 Frappe Desk / Workspace。仅当原生 UI 无法满足领导 Demo 或员工视图时才考虑轻量前端。M1 暂不启动大型 Vue 前端 | 技术评估/决策 Gate | M1-R5/R7 |
| Gate-11：Leave Allocation 对请假流程的阻断 | 已在 M1-R3C 中确认 leave_application 因缺少 Leave Allocation 无法创建。M1-R5 需配置 Leave Allocation 解除阻断 | 已知风险 | M1-R5 |
| Gate-12：TEST 数据清理 | 当前环境存在历史 `TEST-HBOS-M1R3-*` 和 `TEST-HBOS-M1R3C-*` 数据。M1 Demo 开始前需用户授权清理或确认保留 | 决策 Gate | M1-R5 前置 |

注意：以上 Gate 是技术评估或待验证项，**不得写成 Owner 已确认要做**。各 Gate 的状态将在对应执行轮次中更新。

## 10. 环境保护规则

M1 全阶段（含后续 R5/R6/R7）保持以下环境保护规则：

- 不得执行 `docker compose down -v`
- 不得删除 Docker volume
- 不得删除或重建 `frontend` site
- 不得重新初始化 ERPNext
- 不得重新安装 HRMS（除非可复现性方案授权）
- 不得提交 `.env`、备份文件、密钥、数据库、Docker volume 或运行时数据

## 11. 状态总结

| 轮次 | 状态 | 说明 |
| --- | --- | --- |
| M1-REQ-DESIGN-DRAFT | COMPLETED | 4 份设计文档已通过 Codex 审查 |
| M1-R4 | REVIEWING | 本轮：Demo 技术方案与实施路线拆分，等待 Codex 审查 |
| M1-R5 | PLANNED | 待用户授权启动 |
| M1-R6 | PLANNED | 待用户授权启动 |
| M1-R7 | PLANNED | 待用户授权启动 |
| M1-R8 | PLANNED | 可选缓冲轮，不预先承诺一定执行 |

M1-R5/R6/R7 均为 PLANNED，未启动。不得在未经用户逐轮授权的情况下启动后续轮次。

## 12. 本轮完成确认

本轮只做规划拆分文档交付，不做任何开发、试运行或数据操作：

- [x] 已拆出 M1-R5/R6/R7/可选 R8 的详细路线
- [x] 每轮有明确的目标、输入、范围、禁止项、验收点、审查和 closeout 要求
- [x] 已重申 M1 技术边界（复用优先、不修改核心源码、本地 Docker 运行）
- [x] 已明确数据与脱敏边界（虚构员工姓名、两类导入区分、导入批次、操作留痕）
- [x] 已列出 12 项 Gate 检查点（技术评估/待验证，非已确认需求）
- [x] 已重申环境保护规则
- [x] 本轮未开发、未试运行、未动数据库、未创建 App、未创建 DocType
- [x] 本轮未接真实考勤机、未接飞书工作台、未正式接飞书请假
- [x] 本轮未部署内网/云服务器、未修改核心源码
