# M1-R2 HRMS 原生考勤配置试运行方案

项目名称：新乡海滨智能运营管理平台。

## M1-R2 目标与边界

状态：REVIEWING。

本轮目标：

- 制定 HRMS 原生考勤配置试运行方案。
- 明确后续如何用最小虚构测试数据验证早班、中班、夜班、跨夜班、8 小时工作制、缺卡、迟到、早退、请假匹配、加班匹配、节假日出勤、调班和月度汇总。
- 形成 M1-R3 可执行前的配置步骤草案、打卡数据字段草案、验收用例和成功标准。

本轮只做方案和验收设计：

- 不执行配置试运行。
- 不创建测试数据。
- 不创建 Employee / Shift Type / Employee Checkin / Attendance / Leave Application。
- 不生成可直接导入的 CSV / Excel 测试数据文件。
- 不接真实考勤机。
- 不接真实飞书。
- 不写入飞书。
- 不创建自定义 App。
- 不创建 `hb_attendance_app`。
- 不新增业务 DocType。
- 不开发业务代码。
- 不修改 Frappe / ERPNext / HRMS 核心源码。
- 不修改中文化源码。

## M1-R1 结论承接

M1-R1 已完成 HRMS 原生考勤对象模型验证，并通过 Codex 独立审查收口为 COMPLETED。

承接结论：

- HRMS 原生能力是 M1 初期主路线。
- 当前不建议创建 `hb_attendance_app`。
- M1-R2 的目标是验证 HRMS 配置能力，而不是定制开发。
- 海滨特有规则只进入 Gap List、验收风险或后续定制候选。
- 飞书登录沿用 M1-R0 方向：飞书作为员工主登录入口，HBOS User 自动映射 Employee。
- 中文化问题仍只诊断，不改 Frappe / ERPNext / HRMS 核心源码，不改中文翻译源码。

## 试运行总体设计

试运行目的：

- 用最小虚构数据验证 HRMS 原生配置是否能覆盖考勤一期关键场景。
- 验证 Shift Type、Shift Assignment、Employee Checkin、Auto Attendance、Attendance、Leave Application 和原生报表之间的闭环。
- 识别哪些能力可以直接使用，哪些需要配置，哪些需要自定义报表，哪些才可能进入后续海滨定制。

试运行范围：

- 虚构测试公司、部门、员工和账号关系。
- 虚构早班、中班、夜班、跨夜班、休息日 / 节假日。
- 虚构打卡样例、请假样例、加班样例和调班样例。
- HRMS 原生 Attendance 生成、异常识别和报表导出验证。

试运行不覆盖范围：

- 不覆盖真实员工、真实考勤、真实生产数据。
- 不覆盖真实考勤机接入。
- 不覆盖真实飞书 OAuth、通讯录、审批、消息或写入。
- 不覆盖薪资核算、生产排产、前端驾驶舱和复杂移动端体验。
- 不覆盖自定义 App 开发。

试运行环境要求：

- 仅在已验证的本地 `frontend` site 上执行，且执行前再次确认 `git status` clean。
- 执行前需用户明确授权进入 M1-R3。
- 执行前需确认不提交数据库、日志、缓存、备份或运行时产物。
- 如需创建测试数据，命名必须带 `TEST` / `示例` / `虚构` 前缀。

数据隔离与清理策略：

- 所有测试公司、部门、员工、班次、打卡、请假、考勤结果均使用 `TEST-HBOS-M1R3-*` 命名。
- 测试数据不得混入真实公司、真实部门、真实员工或真实设备编号。
- M1-R3 执行前必须先写清理清单，记录每类测试对象的名称、数量和删除顺序。
- M1-R3 执行后必须记录是否保留、禁用、取消提交或删除测试数据；数据库不提交到 Git。

## 最小测试组织设计

以下仅为 Markdown 方案样例，不在本轮创建数据。

| 类型 | 示例名称 | 数量 | 用途 |
| --- | --- | --- | --- |
| 测试公司 | `TEST-HBOS-M1R3-虚构公司` | 1 | 承载测试部门、员工、班次和考勤 |
| 测试部门 | `TEST-HBOS-M1R3-生产一部`、`TEST-HBOS-M1R3-生产二部` | 2 | 验证部门维度、主管查看和报表过滤 |
| 人事管理员 | `TEST-HBOS-M1R3-HR-Admin` | 1 | 验证 HR Manager / HR User 维护能力 |
| 考勤管理员 | `TEST-HBOS-M1R3-Attendance-Admin` | 1 | 验证班次、打卡、考勤异常处理 |
| 部门主管 | `TEST-HBOS-M1R3-Dept-Lead-A`、`TEST-HBOS-M1R3-Dept-Lead-B` | 2 | 验证部门主管查看本部门场景 |
| 普通测试员工 | `TEST-HBOS-M1R3-E001` 至 `TEST-HBOS-M1R3-E008` | 8 | 覆盖早 / 中 / 夜 / 跨夜 / 请假 / 加班 / 缺卡 / 调班 |

测试身份分层：

- 员工体验层：后续仍以飞书登录为目标，但 M1-R3 不接真实飞书。
- 平台身份层：Frappe User 只作为内部权限和审计主体。
- 人事主数据层：Employee 作为员工主数据。
- 权限控制层：优先复用 HRMS / Frappe 原生角色。
- 飞书身份映射层：本轮仅保留字段映射方向，不保存真实 open_id / union_id / user_id。

## 最小班次设计

以下仅为配置候选方案，不在本轮创建 Shift Type。

| 班次 | 示例名称 | 上班 | 下班 | 是否跨天 | 是否 8 小时 | 迟到容差 | 早退容差 | HRMS `Shift Type` 候选字段 | 需验证问题 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 早班 | `TEST-早班-0800-1600` | 08:00 | 16:00 | 否 | 是 | 5 分钟 | 5 分钟 | `start_time`、`end_time`、`late_entry_grace_period`、`early_exit_grace_period`、`enable_auto_attendance` | 正常打卡、迟到、早退、缺卡 |
| 中班 | `TEST-中班-1600-0000` | 16:00 | 00:00 | 是 | 是 | 5 分钟 | 5 分钟 | `start_time`、`end_time`、`begin_check_in_before_shift_start_time`、`allow_check_out_after_shift_end_time` | 跨到次日 00:00 时的 Attendance 日期 |
| 夜班 | `TEST-夜班-0000-0800` | 00:00 | 08:00 | 否 | 是 | 5 分钟 | 5 分钟 | `start_time`、`end_time`、`determine_check_in_and_check_out` | 零点班次边界和缺卡识别 |
| 跨夜班 | `TEST-跨夜班-2000-0400` | 20:00 | 04:00 | 是 | 是 | 10 分钟 | 10 分钟 | `start_time`、`end_time`、`working_hours_calculation_based_on`、`process_attendance_after`、`last_sync_of_checkin` | 跨夜 Auto Attendance 归属日期 |
| 休息日 / 节假日 | `TEST-节假日出勤` | 按分配班次 | 按分配班次 | 取决于班次 | 取决于班次 | 按班次 | 按班次 | `holiday_list`、Attendance 报表 | 节假日出勤是否进入原生报表 |

统一候选设置：

- `enable_auto_attendance`：M1-R3 中开启验证。
- `determine_check_in_and_check_out`：分别验证“交替 IN/OUT”和“严格基于 Log Type”两种策略。
- `working_hours_calculation_based_on`：优先验证 First Check-in and Last Check-out。
- `begin_check_in_before_shift_start_time`：建议先设 60 分钟。
- `allow_check_out_after_shift_end_time`：建议先设 120 分钟，跨夜班可加大。

## 最小打卡场景设计

以下样例仅用于方案说明，不生成 CSV / Excel / JSON 文件，不在本轮创建数据。

| 场景 | 员工 | 日期 | 班次 | 打卡时间样例 | 请假 / 加班样例 | 预期 Attendance | 预期异常 | 原生预计覆盖 | 需验证问题 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 正常早班 | `TEST-E001` | 2026-08-03 | 早班 | 07:55 IN，16:03 OUT | 无 | Present，约 8 小时 | 无 | 是 | 工时是否按首入末出计算 |
| 正常中班 | `TEST-E002` | 2026-08-03 | 中班 | 15:55 IN，00:02 OUT | 无 | Present，约 8 小时 | 无 | 预计可覆盖 | Attendance 日期归属 |
| 正常夜班 | `TEST-E003` | 2026-08-04 | 夜班 | 23:55 IN，08:01 OUT | 无 | Present，约 8 小时 | 无 | 预计可覆盖 | 零点边界与班次归属 |
| 跨夜班正常上下班 | `TEST-E004` | 2026-08-04 | 跨夜班 | 19:55 IN，04:05 OUT | 无 | Present，约 8 小时 | 无 | 需验证 | 跨夜 Auto Attendance 是否稳定 |
| 迟到 | `TEST-E001` | 2026-08-05 | 早班 | 08:12 IN，16:02 OUT | 无 | Present | Late Entry | 预计可覆盖 | 宽限分钟是否准确 |
| 早退 | `TEST-E002` | 2026-08-05 | 中班 | 15:58 IN，23:40 OUT | 无 | Present | Early Exit | 预计可覆盖 | 跨日早退标记是否准确 |
| 上班缺卡 | `TEST-E003` | 2026-08-06 | 夜班 | 08:00 OUT | 无 | 需人工复核 | Missing IN | 需验证 | 原生缺卡表现是 Absent、Present 还是异常 |
| 下班缺卡 | `TEST-E004` | 2026-08-06 | 跨夜班 | 20:00 IN | 无 | 需人工复核 | Missing OUT | 需验证 | 是否需要 Attendance Request / 人工修正 |
| 全天缺勤 | `TEST-E005` | 2026-08-07 | 早班 | 无 | 无 | Absent | No Checkin | 需验证 | 无打卡是否自动生成 Absent |
| 请假覆盖部分时段 | `TEST-E006` | 2026-08-07 | 早班 | 07:58 IN，16:00 OUT | 13:00-16:00 请假 | Present / Half Day / On Leave 取决于配置 | 请假匹配 | 需验证 | 半天请假和 Attendance 状态关系 |
| 请假覆盖全天 | `TEST-E006` | 2026-08-08 | 早班 | 无 | 全天请假 | On Leave | 无打卡但有请假 | 预计可覆盖 | Leave Application 是否自动影响 Attendance |
| 加班场景 | `TEST-E007` | 2026-08-08 | 早班 | 07:58 IN，18:30 OUT | 下班后加班 2.5 小时 | Present，可能不自动形成加班 | Overtime Candidate | 不确定 | 加班是否需要海滨定制或报表 |
| 节假日出勤 | `TEST-E008` | 2026-08-09 | 早班 | 08:00 IN，16:00 OUT | 节假日出勤 | Present | Holiday Work | 预计报表支持 | 原生节假日出勤报表是否满足口径 |
| 员工调班或临时换班 | `TEST-E005` | 2026-08-10 | 原早班改中班 | 15:55 IN，00:01 OUT | 临时换班 | Present | Shift Changed | 需验证 | Shift Assignment 调整后 Auto Attendance 是否按新班次计算 |

## HRMS 配置步骤草案

以下仅为 M1-R3 可执行前草案，本轮不执行。

1. Company：创建 `TEST-HBOS-M1R3-虚构公司`。
2. Department：创建 `TEST-HBOS-M1R3-生产一部`、`TEST-HBOS-M1R3-生产二部`。
3. User：创建或准备虚构测试 User，区分 HR、Attendance Admin、Department Lead、Employee。
4. Employee：创建 6-9 名虚构 Employee，关联 Company、Department、Designation、User、Attendance Device ID。
5. User 与 Employee 关联：验证 Employee `user_id` 与 Frappe User 的稳定关联。
6. Holiday List：创建测试假日和休息日，覆盖普通工作日与节假日出勤。
7. Shift Type：创建早班、中班、夜班、跨夜班，配置自动考勤、IN/OUT 判断、工时计算、打卡时间窗、迟到早退容差。
8. Shift Assignment：为测试员工分配班次，覆盖固定班、跨夜班、临时调班。
9. Employee Checkin：在 M1-R3 用户授权后，用虚构打卡样例录入或导入，不使用真实考勤机数据。
10. Auto Attendance：按 Shift Type 触发或观察自动考勤生成，不修改核心源码。
11. Attendance：检查生成结果、状态、工时、迟到、早退、缺卡、请假关联。
12. Leave Type：创建虚构请假类型，避免混入真实请假制度。
13. Leave Application：创建虚构请假申请，覆盖半天、全天和跨班次请假。
14. Attendance Request：如适用，验证 On Duty / Work From Home / 补充出勤类场景。
15. 报表或导出验证：查看 `Monthly Attendance Sheet`、`Shift Attendance`、`Employees working on a holiday` 是否满足验收口径。

## 打卡数据导入方案草案

本轮不生成 CSV 文件，不生成 Excel 文件，不创建导入模板。

Employee Checkin 建议字段草案：

| 字段 | 示例 | 用途 |
| --- | --- | --- |
| `employee` | `TEST-HBOS-M1R3-E001` | 关联虚构 Employee |
| `time` | `2026-08-03 07:55:00` | 打卡时间 |
| `log_type` | `IN` / `OUT` | 上班 / 下班识别 |
| `device_id` | `TEST-DEVICE-01` | 虚构设备编号 |
| `shift` | `TEST-早班-0800-1600` | 辅助班次归属 |
| `skip_auto_attendance` | `0` | 是否跳过自动考勤 |

真实考勤机后续需要字段映射：

- 设备人员编号 -> Employee `attendance_device_id` 或后续映射对象。
- 设备打卡时间 -> Employee Checkin `time`。
- 设备进出方向 -> Employee Checkin `log_type`。
- 设备编号 / 门禁点 -> Employee Checkin `device_id`。
- 时区、夏令时、重复打卡、离线补传、跨日时间归属。

约束：

- M1-R3 前不得使用真实考勤机数据。
- 后续如需要导入模板，必须另行授权并明确不包含真实数据。
- 导入方案必须先验证去重、字段缺失、无员工匹配和错班次归属的处理方式。

## 验收用例设计

| 用例编号 | 场景名称 | 前置配置 | 输入数据 | 预期 HRMS 输出 | 通过标准 | 风险点 | 人工复核 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| M1R3-AT-001 | 正常早班 | 早班、员工、班次分配 | 07:55 IN，16:03 OUT | Attendance Present，约 8 小时 | 无迟到早退，工时合理 | 工时四舍五入 | 是 |
| M1R3-AT-002 | 正常中班 | 中班、员工、班次分配 | 15:55 IN，00:02 OUT | Attendance Present | 日期归属正确 | 跨日边界 | 是 |
| M1R3-AT-003 | 正常夜班 | 夜班、员工、班次分配 | 23:55 IN，08:01 OUT | Attendance Present | 班次归属正确 | 零点边界 | 是 |
| M1R3-AT-004 | 跨夜班 | 跨夜班、打卡时间窗 | 19:55 IN，04:05 OUT | Attendance Present | 跨夜归属稳定 | Auto Attendance 日期 | 是 |
| M1R3-AT-005 | 迟到 | 迟到容差 5 分钟 | 08:12 IN，16:02 OUT | Late Entry | 超过容差被标记 | 容差配置 | 是 |
| M1R3-AT-006 | 早退 | 早退容差 5 分钟 | 15:58 IN，23:40 OUT | Early Exit | 提前下班被标记 | 跨日早退 | 是 |
| M1R3-AT-007 | 上班缺卡 | Employee Checkin 仅 OUT | 08:00 OUT | 缺卡或需人工修正 | 原生表现可解释 | HRMS 缺卡口径 | 是 |
| M1R3-AT-008 | 下班缺卡 | Employee Checkin 仅 IN | 20:00 IN | 缺卡或需人工修正 | 原生表现可解释 | 是否自动 Absent | 是 |
| M1R3-AT-009 | 全天缺勤 | 有 Shift Assignment，无 Checkin | 无 | Absent 或未生成需处理 | 能定义后续流程 | 原生是否自动生成 | 是 |
| M1R3-AT-010 | 半天请假 | Leave Type、Leave Application | 半天请假 + 正常打卡 | Half Day / On Leave 口径明确 | 请假与考勤能关联 | 状态组合 | 是 |
| M1R3-AT-011 | 全天请假 | Leave Application Approved | 无打卡 + 全天请假 | On Leave | 不误判旷工 | 审批状态影响 | 是 |
| M1R3-AT-012 | 加班 | 正常早班 + 延后 OUT | 07:58 IN，18:30 OUT | Present，可能需报表判断加班 | 明确原生是否足够 | 加班对象模型不足 | 是 |
| M1R3-AT-013 | 节假日出勤 | Holiday List | 节假日打卡 | Present / Holiday Work 报表可见 | 报表能识别 | 月度口径 | 是 |
| M1R3-AT-014 | 临时调班 | Shift Assignment 调整 | 中班打卡 | 按新班次生成 Attendance | 调班后计算正确 | 生效日期 | 是 |
| M1R3-AT-015 | 部门主管查看 | 部门、主管、权限 | 查看本部门员工考勤 | 只看本部门 | 不越权 | 原生权限不足 | 是 |
| M1R3-AT-016 | 月度汇总 | 多天 Attendance | 原生报表 | 月度表可导出 | 字段满足或记录差距 | 自定义报表需求 | 是 |

## 成功标准

M1-R2 方案通过后，后续 M1-R3 或下一轮试运行应判断：

- HRMS 能否识别早班、中班、夜班。
- HRMS 能否处理跨夜班。
- HRMS 能否根据 Employee Checkin 的 IN / OUT 生成 Attendance。
- HRMS 能否识别迟到、早退、上班缺卡、下班缺卡和全天缺勤。
- HRMS 能否匹配半天请假和全天请假。
- 加班是否原生足够，还是需要海滨定制或自定义报表。
- 月度汇总是否可以直接使用原生报表，还是需要自定义报表。
- 部门主管权限是否可以通过原生角色、User Permission 或权限规则解决。
- 是否仍不需要创建 `hb_attendance_app`。

判定原则：

- 原生可覆盖：优先配置和使用 HRMS 原生对象。
- 配置后可覆盖：记录配置步骤和验收条件。
- 原生报表不足：优先考虑自定义报表，不直接创建业务 App。
- 原生对象无法表达：才进入后续海滨定制候选。

## 风险与待确认事项

| 风险 | 说明 | M1-R3 前待确认 |
| --- | --- | --- |
| 跨夜班配置风险 | 跨日班次的 Attendance 日期、打卡时间窗和 Auto Attendance 归属可能不符合海滨口径 | 确认跨夜班按上班日还是下班日归属 |
| 缺卡判定风险 | 原生缺卡表现可能不是海滨期望的异常类型 | 确认缺卡是否需要独立异常状态或人工修正流程 |
| 加班匹配风险 | 原生 Attendance 未必能完整表达加班申请、审批和调休 | 确认加班一期是否只做统计，还是要闭环审批 |
| 月度汇总报表不足风险 | 原生 Monthly Attendance Sheet 未必满足工资或管理口径 | 确认月度表字段、异常口径和导出格式 |
| 部门主管权限风险 | 原生角色可能无法直接做到只看本部门 | 确认是否接受 User Permission / 权限规则验证 |
| 测试数据污染风险 | 测试数据可能混入真实数据或难以清理 | 使用 `TEST-HBOS-M1R3-*` 命名并先写清理方案 |
| 真实考勤机字段不一致风险 | 设备字段、人员编号、时间格式和进出方向可能不一致 | M1-R3 不接真实设备；后续先做字段样例评审 |
| 中文化体验风险 | HRMS 页面、报表、按钮仍可能有英文 | 继续诊断，优先 Custom Translation / 配置，不改核心源码 |

## M1-R3 建议

建议下一轮为：`M1-R3：HRMS 原生考勤最小测试数据试运行`。

M1-R3 必须在用户明确授权后才可创建虚构测试数据。

M1-R3 仍不得：

- 接真实考勤机。
- 接真实飞书。
- 写入飞书。
- 实现 SSO。
- 录入真实员工。
- 录入真实考勤。
- 录入真实生产数据。
- 创建自定义 App。
- 创建 `hb_attendance_app`。
- 开发业务代码。
- 修改 Frappe / ERPNext / HRMS 核心源码。
- 提交数据库、日志、缓存、备份、密钥或运行时产物。

M1-R3 执行前建议补充：

- 测试数据创建清单。
- 测试数据清理清单。
- 用户授权记录。
- 试运行验收表。
- 失败时停止条件和回滚策略。

## 最终结论

M1-R2 是方案设计，不是配置执行。

当前仍不建议创建 `hb_attendance_app`。M1 初期应继续优先复用 HRMS 原生对象和配置能力，用 M1-R3 的最小虚构测试数据验证 HRMS 原生考勤流程。

下一步应在用户授权后，用虚构最小测试数据验证 HRMS 原生配置。只有 HRMS 原生能力经试运行无法覆盖新乡海滨特有规则时，才考虑后续定制、自定义报表或自定义 App。
