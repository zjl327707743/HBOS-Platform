# M1-R3E 配置复核与业务口径确认表

项目名称：新乡海滨智能运营管理平台。

状态：REVIEWING。

执行日期：2026-07-08。

## 目标与边界

M1-R3E 承接 M1-R3C 的 `PARTIAL / GAP_IDENTIFIED` 试运行结论和 M1-R3D 的 Gap 分类结果，只形成 HRMS 配置复核清单与海滨业务口径确认表。

本轮只写文档，不继续试运行，不创建、删除或清理 TEST 数据，不创建 App / DocType / 代码，不接飞书 / SSO / 真实考勤机，不修改 Frappe / ERPNext / HRMS 核心源码，不提交数据库、日志、缓存、`.env`、密钥或备份。

## M1-R3C / M1-R3D 承接

M1-R3C 已证明 HRMS 原生链路可生成 Attendance，但不能把 Attendance 生成等同于海滨考勤业务闭环完成。M1-R3D 已将 Gap 分类为 HRMS 配置、原生 / 自定义报表、海滨业务规则定义和未来自定义 App 候选，结论是当前仍不建议创建 `hb_attendance_app`。

本轮复核和确认范围：

- 迟到 `late_entry` 未置位。
- 早退 `early_exit` 未置位。
- 上班缺卡 / 下班缺卡。
- 全天缺勤未生成 Attendance。
- 请假受 Leave Allocation 阻断。
- 加班仅体现 `working_hours`。
- 节假日出勤待遇、审批与报表口径。
- 临时调班申请、审批、追溯与权限口径。

## HRMS 配置复核清单

| 复核项 | 关联 DocType | 复核方式 | 预期结果 | 是否需再试运行 |
| --- | --- | --- | --- | --- |
| 迟到 `late_entry` 未置位 | Shift Type / Employee Checkin / Attendance | 复核 Shift Type 是否启用迟到标记、迟到宽限、自动考勤设置、`last_sync_of_checkin`、处理日期窗口；核对 Attendance 字段是否由原生逻辑写入 | 明确 late 标记未触发是配置缺失、处理窗口问题，还是 HRMS 原生口径限制 | 是。需要用虚构 TEST 数据复测同类迟到场景 |
| 早退 `early_exit` 未置位 | Shift Type / Employee Checkin / Attendance | 复核早退标记、早退宽限、跨日班次结束时间、自动考勤时间窗口和 `last_sync_of_checkin` | 明确 early 标记未触发原因，确认跨日中班是否需要特殊配置 | 是。需要用虚构 TEST 数据复测早退和跨日早退场景 |
| 全天缺勤未生成 Attendance | Shift Type / Shift Assignment / Employee / Attendance | 复核 Auto Attendance 是否支持无打卡员工生成 Absent；复核 Process Attendance After、Last Sync、Shift Assignment 有效期、Holiday List 排除规则 | 明确无打卡转 Absent 是否可由 HRMS 原生配置完成；若不能，则转报表候选识别 | 是。需要复测无打卡员工是否生成 Absent 或进入缺勤候选报表 |
| 请假 Leave Allocation 阻断 | Leave Type / Leave Period / Leave Allocation / Leave Application / Attendance | 复核最小 Leave Period、Leave Allocation、半天请假、全天请假和审批状态要求；不绕过 HRMS 原生校验 | Leave Application 能按原生规则提交或进入审批，并可与 Attendance / On Leave 口径形成闭环 | 是。需要在用户授权下用虚构 TEST 员工复测半天与全天请假 |
| 缺卡识别基础字段 | Attendance / Employee Checkin / Shift Type | 复核单边打卡生成的 `in_time`、`out_time`、`working_hours`、状态字段是否稳定可查 | 确认缺卡事实可由原生字段稳定识别，为报表候选提供字段基础 | 视情况。若仅做报表设计可先只读核对，若需验证字段稳定性则再试运行 |
| 加班候选基础字段 | Attendance / Shift Type / Shift Assignment | 复核标准班次工时、Attendance `working_hours`、跨日班次工时计算和 Holiday List 影响 | 确认 `working_hours > 标准工时` 可作为加班候选，不直接等同于加班成立 | 视情况。业务口径确认后再决定是否复测 |
| 节假日出勤基础配置 | Holiday List / Shift Type / Attendance | 复核 Holiday List 与 Shift Type 的关系，确认节假日出勤 Attendance 是否稳定生成 | 明确节假日出勤可作为候选事实记录，但待遇和审批仍由业务口径决定 | 视情况。若 M1-R4 做报表设计，优先只读核对 |
| 临时调班基础配置 | Shift Assignment / Shift Type / Attendance | 复核 Shift Assignment 对当日班次覆盖、提交权限、生效时间和追溯边界 | 确认 HRMS 原生 Shift Assignment 可承接调班结果记录 | 视情况。若后续定义调班审批，再决定是否复测 |

## 海滨业务口径确认表

| 问题 | 待确认口径 | 建议默认值 | 影响范围 | 确认人 / 部门 | 是否阻塞 M1-R4 |
| --- | --- | --- | --- | --- | --- |
| 迟到 | 超过上班时间多久算迟到；是否有宽限；迟到是否分级；迟到是否影响扣款或绩效 | 先按班次上班时间后 0 分钟即候选迟到，宽限分钟数由人事确认后再配置 | Attendance 标记、异常报表、工资 / 绩效候选、主管审核 | 人事行政部 / 生产部门主管 / 财务 | 是。影响 M1-R4 是否复测 late 标记 |
| 早退 | 提前下班多久算早退；跨日班次如何判断；是否允许主管豁免 | 先按班次结束时间前离岗即候选早退，宽限分钟数由人事确认 | Attendance 标记、异常报表、扣款 / 绩效候选 | 人事行政部 / 生产部门主管 | 是。影响 M1-R4 是否复测 early 标记 |
| 上班缺卡 | 只有下班卡时算缺卡、迟到、异常待补卡还是缺勤；补卡是否需要审批 | 默认列为缺卡异常待处理，不自动等同缺勤或迟到 | 缺卡报表、补卡流程、主管审批、工资扣款 | 人事行政部 / 部门主管 | 是。影响缺卡报表字段和异常流程 |
| 下班缺卡 | 只有上班卡时是否算早退、缺卡、异常待补卡；工时是否按 0、半天或人工确认 | 默认列为缺卡异常待处理，工时不自动用于工资结算 | 缺卡报表、补卡流程、工资结算 | 人事行政部 / 部门主管 / 财务 | 是。影响缺卡报表字段和工资口径 |
| 全天缺勤 | 无打卡且无请假 / 调休 / 出差时是否自动算旷工；是否需主管确认 | 默认进入缺勤候选，需排除请假、节假日和已审批外勤后再确认 | 缺勤报表、工资扣款、绩效、劳动纪律 | 人事行政部 / 部门主管 | 是。影响 M1-R4 缺勤候选或 Absent 复测 |
| 半天请假 | 半天请假的时间段、扣减额度、是否影响当天工时和 Attendance 状态 | 默认按 HRMS 半天请假能力优先配置，额度从 Leave Allocation 扣减 | Leave Application、Attendance、工资结算 | 人事行政部 / 财务 | 是。影响 Leave Allocation 最小配置复测 |
| 全天请假 | 全天请假是否必须提前审批；审批中是否影响出勤；是否允许事后补请 | 默认已批准请假才影响 Attendance / On Leave 口径 | Leave Application、Attendance、工资结算、异常排除 | 人事行政部 / 部门主管 | 是。影响请假闭环复测 |
| 加班 | 超过标准工时是否自动算加班；是否必须先审批；工作日、休息日、节假日是否不同 | 默认 `working_hours` 只作为加班候选，必须审批或人工确认后成立 | 加班报表、调休、加班费、财务结算 | 人事行政部 / 生产部门 / 财务 | 是。影响 M1-R4 报表或二次验证方向 |
| 节假日出勤 | 节假日出勤是否自动转加班、调休或补贴；是否必须审批 | 默认只记录节假日出勤候选，不自动结算待遇 | Attendance 报表、加班 / 调休、工资结算 | 人事行政部 / 财务 / 生产部门 | 否。可先做候选报表，但待遇口径会影响后续闭环 |
| 临时调班 | 谁能发起调班；是否需要审批；是否允许事后补录；变更截止时间 | 默认先由人事或授权主管维护 Shift Assignment，审批流程后置设计 | Shift Assignment、Attendance、权限、审计 | 人事行政部 / 部门主管 / 系统管理员 | 否。HRMS 原生 Shift Assignment 可先承接结果记录 |

## 报表候选

M1-R3E 不开发报表，只记录 M1-R4 可选方向。

| 报表候选 | 数据来源 | 目标 |
| --- | --- | --- |
| 缺卡异常候选表 | Attendance `in_time` / `out_time` / `working_hours`、Employee Checkin | 识别上班缺卡、下班缺卡、单边打卡和 0 工时异常 |
| 缺勤候选表 | Shift Assignment、Employee、Attendance、Leave Application、Holiday List | 识别应出勤但无有效 Attendance / Leave 的员工日期 |
| 加班候选表 | Attendance `working_hours`、Shift Type 标准工时、Holiday List | 识别长工时、节假日出勤、休息日出勤候选 |
| 调班追溯表 | Shift Assignment、Attendance、Employee、User | 记录调班结果、操作人、时间和影响的 Attendance |

## 结论

- 当前仍不建议创建 `hb_attendance_app`。
- 应先完成 HRMS 配置复核和海滨业务口径确认，再决定是否进入 M1-R4。
- M1-R4 才考虑二次最小验证或报表设计。
- Attendance 能生成，只说明 HRMS 原生链路可用，不等同于海滨考勤业务闭环完成。
- 只有当海滨特有规则稳定后，且 HRMS 原生配置、角色权限、DocType、报表、导入、API 和低代码定制无法覆盖时，才考虑自定义 App。

## 状态与下一步

- M1-R3D：COMPLETED。
- M1-R3E：REVIEWING，等待 Codex 审查。
- M1-R4：PLANNED，尚未启动。

下一步建议：先交给 Codex 审查 M1-R3E。审查通过后，再由用户决定是否进入 M1-R4：二次最小验证或报表设计。

本轮未继续试运行，未创建、删除或清理 TEST 数据，未创建 App / DocType / 代码，未接飞书 / SSO / 真实考勤机，未修改核心源码，未提交数据库、日志、缓存、`.env`、密钥或备份。
