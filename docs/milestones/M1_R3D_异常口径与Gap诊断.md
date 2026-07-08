# M1-R3D 异常口径与 Gap 诊断

项目名称：新乡海滨智能运营管理平台。

状态：COMPLETED。

审查记录：M1-R3D 已通过 Codex 审查，审查结果为 PASS。本次 M1-R3D-CLOSEOUT 仅做状态收口，将 M1-R3D 从 REVIEWING 改为 COMPLETED；未继续试运行，未创建、删除或清理 TEST 数据，未创建 App / DocType / 代码。

执行日期：2026-07-08。

## 目标与边界

M1-R3D 承接 M1-R3C 的 `PARTIAL / GAP_IDENTIFIED` 结论，只做异常口径与 Gap 诊断，不继续试运行，不创建、删除或清理 TEST 数据，不创建 App / DocType / 代码，不接飞书 / SSO / 真实考勤机，不修改 Frappe / ERPNext / HRMS 核心源码。

本轮目标是把 M1-R3C 暴露的 GAP / PARTIAL 分为四类：

1. HRMS 配置可解决。
2. 原生报表 / 自定义报表可解决。
3. 需要海滨业务规则定义。
4. 未来才考虑自定义 App。

## M1-R3C 结果承接

M1-R3C 已通过 Codex 审查并收口为 COMPLETED，结论为 `PARTIAL / GAP_IDENTIFIED`。该结论表示 HRMS 原生考勤最小试运行已完成，不表示海滨考勤业务闭环已完成。

M1-R3C 关键结果：

- Company / User / Employee 写入阻断已解除。
- Attendance 可由 HRMS 原生自动考勤生成。
- 14 个场景中 8 个通过，6 个为 GAP / PARTIAL。
- 13 条 Attendance 已生成。
- Leave Application 因缺少 Leave Allocation 未闭环。
- 当前仍不建议创建 `hb_attendance_app`。

M1-R3C 场景结果摘要：

| 类型 | 场景 | M1-R3C 结果 |
| --- | --- | --- |
| PASS | 正常早班、正常中班、正常夜班、跨夜班正常、临时调班 | HRMS 原生 Shift Type / Shift Assignment / Employee Checkin / Attendance 链路可用 |
| PASS / PARTIAL | 节假日出勤 | Attendance 可生成，但节假日工资、调休、审批或报表口径未定义 |
| PARTIAL | 加班候选 | `working_hours` 可记录长工时，但加班业务口径未定义 |
| GAP / PARTIAL | 上班缺卡、下班缺卡、半天请假、全天请假 | Attendance 或校验结果存在，但异常口径未闭环 |
| GAP | 迟到、早退、全天缺勤 | late / early 标记或缺勤生成未达预期 |

## Gap 分类总表

| Gap | 现象 | 主要分类 | 次级路径 | 是否需要立即创建 App |
| --- | --- | --- | --- | --- |
| 迟到 `late_entry` 未置位 | 08:12 上班打卡生成 Present，但 `late_entry=0` | HRMS 配置可解决 | 配置复核后用报表确认 | 否 |
| 早退 `early_exit` 未置位 | 23:40 下班打卡生成 Present，但 `early_exit=0` | HRMS 配置可解决 | 配置复核后用报表确认 | 否 |
| 上班缺卡 / 下班缺卡 | 单边打卡生成 Present 且工时为 0，缺卡未形成清晰异常 | 原生报表 / 自定义报表可解决 | 需海滨定义异常处理口径 | 否 |
| 全天缺勤未生成 Attendance | 无打卡场景未自动生成 Attendance | HRMS 配置可解决 | 可能需要报表补充 | 否 |
| 请假受 Leave Allocation 阻断 | Leave Application 因缺少 Leave Allocation 未通过 | HRMS 配置可解决 | 需定义请假类型、额度和审批口径 | 否 |
| 加班仅体现 `working_hours` | 长工时进入 Attendance，但不等于加班成立 | 需要海滨业务规则定义 | 可先用报表呈现候选 | 否 |
| 节假日出勤补充口径 | Holiday 出勤可生成 Attendance，但后续待遇口径未定义 | 需要海滨业务规则定义 | 原生 / 自定义报表呈现候选 | 否 |
| 临时调班补充口径 | Shift Assignment 可生效，但调班申请、审批、追溯口径未定义 | 需要海滨业务规则定义 | 可先复用 HRMS 原生 Shift Assignment | 否 |

## 逐项诊断

### 1. 迟到 late_entry 未置位

现象：

- M1-R3C 的迟到场景生成 `HR-ATT-2026-00014`。
- 状态为 Present，`working_hours=7.83`。
- 上班时间为 `2026-06-12 08:12:00`，但 `late_entry=0`。

可能原因：

- Shift Type 的迟到宽限、自动考勤或标记迟到字段未完全生效。
- HRMS 对 late entry 的触发可能依赖特定字段组合，而不是只依赖 `begin_check_in_before_shift_start_time` 和打卡时间。
- 自动考勤处理时点、`last_sync_of_checkin` 或处理日期窗口可能影响 late / early 标记。
- 当前试运行只证明 Attendance 生成，不足以证明异常标记配置已正确。

验证证据：

- Attendance 已生成，说明 Employee Checkin 到 Attendance 的原生链路可用。
- late 标记未置位，说明异常标记口径未闭环。

解决路径：

- 优先进入 M1-R3E 做 Shift Type 自动考勤配置复核。
- 复核迟到宽限字段、是否启用迟到标记、自动考勤时间窗口、`last_sync_of_checkin`、处理日期。
- 复核后用同类虚构数据或只读方式验证 late 标记是否能由原生配置触发。

分类判断：HRMS 配置可解决优先。

### 2. 早退 early_exit 未置位

现象：

- M1-R3C 的早退场景生成 `HR-ATT-2026-00020`。
- 状态为 Present，`working_hours=7.7`。
- 下班时间为 `2026-06-12 23:40:00`，但 `early_exit=0`。

可能原因：

- Shift Type 的早退宽限或标记早退字段未完全生效。
- 跨日中班 `16:00-00:00` 的结束时间口径可能影响 early exit 判断。
- 自动考勤字段组合或处理时间窗口未覆盖该场景。

验证证据：

- Attendance 能生成，并能记录少于标准班次的工时。
- early 标记未置位，说明异常标记配置仍需复核。

解决路径：

- 与迟到一起进入 M1-R3E 配置复核。
- 重点复核跨日班次的结束时间、早退宽限、自动考勤处理窗口。
- 复核后通过 HRMS 原生 Attendance 字段和报表确认。

分类判断：HRMS 配置可解决优先。

### 3. 上班缺卡 / 下班缺卡

现象：

- 上班缺卡场景生成 `HR-ATT-2026-00023`，Present，`working_hours=0`，`in_time` 为空。
- 下班缺卡场景生成 `HR-ATT-2026-00025`，Present，`working_hours=0`，`out_time` 为空。

可能原因：

- HRMS 原生 Auto Attendance 能生成 Attendance，但不一定把单边打卡直接转为异常状态。
- 缺卡通常需要额外异常报表、补卡流程或人工审核口径。
- 海滨需要定义单边打卡的处理规则：算缺卡、算迟到 / 早退、算异常待处理，还是允许补卡后重算。

验证证据：

- Attendance 生成证明链路可用。
- `in_time` 或 `out_time` 为空证明缺卡事实可被报表识别。
- Present + 0 工时说明原生结果不等于业务异常闭环。

解决路径：

- 先用原生 Attendance 字段识别 `in_time is null` 或 `out_time is null`。
- 优先考虑原生报表或自定义报表列出缺卡候选。
- 海滨需定义补卡、审批、扣款、例外处理规则。
- 若未来缺卡处理需要复杂流程、批量重算、与考勤机或飞书审批深度联动，再考虑自定义 App。

分类判断：原生报表 / 自定义报表可解决，加上海滨业务规则定义。

### 4. 全天缺勤未生成 Attendance

现象：

- 全天缺勤场景没有生成 Attendance。
- 这意味着无打卡不一定自动产生 Absent 记录。

可能原因：

- HRMS 自动考勤可能只处理已有 Employee Checkin 的员工，或需要满足额外 Shift Assignment / Process Attendance After / Last Sync 条件。
- 无打卡转 Absent 可能需要调度、时间窗口或独立缺勤生成机制。
- 也可能需要通过报表识别“应出勤但无 Attendance”的候选缺勤。

验证证据：

- 有打卡的多数场景能生成 Attendance。
- 无打卡场景未生成 Attendance，说明缺勤生成口径未闭环。

解决路径：

- M1-R3E 先复核 HRMS 原生 Auto Attendance 是否支持对无打卡员工生成 Absent。
- 若原生配置可生成 Absent，则走配置复核。
- 若原生不生成，则用 Shift Assignment / Employee / Attendance 差异报表识别缺勤候选。
- 海滨需定义缺勤是否自动成立、是否需要排除请假 / 出差 / 调休 / 法定节假日。

分类判断：优先 HRMS 配置可解决；若配置不足，则原生报表 / 自定义报表补足。

### 5. 请假受 Leave Allocation 阻断

现象：

- 半天请假和全天请假的 Leave Application 因缺少 Leave Allocation 未通过。
- 半天请假场景仍生成 Present 和 4.03 小时。
- 全天请假场景生成 Absent，但不是 On Leave。

可能原因：

- HRMS 原生请假链路要求 Leave Allocation、Leave Period、Leave Type 等前置配置。
- 本轮只创建了 Leave Type，没有建立请假额度和分配，因此原生校验阻止申请。

验证证据：

- Leave Application 被原生校验拦截，说明 HRMS 请假前置配置机制在生效。
- Attendance 与 Leave 未完成联动，说明请假链路还没有配置闭环。

解决路径：

- 进入 M1-R3E 配置复核，补充最小 Leave Period / Leave Allocation 方案。
- 定义请假类型、额度、半天请假、全天请假、审批和与 Attendance 的联动口径。
- 配置完成前不应绕过校验，也不应通过自定义代码硬写请假结果。

分类判断：HRMS 配置可解决，加上海滨业务规则定义。

### 6. 加班仅体现 working_hours

现象：

- 加班候选场景生成 `HR-ATT-2026-00016`。
- 状态为 Present，`working_hours=10.53`。
- 原生 Attendance 记录了长工时，但没有直接得出“加班成立”的业务结论。

可能原因：

- HRMS Attendance 主要记录出勤结果和工时，不负责自动定义海滨的加班审批、加班费、调休或无效加班规则。
- 加班是否成立通常依赖业务规则：是否提前申请、是否主管审批、是否超过阈值、是否节假日、是否与排班冲突。

验证证据：

- `working_hours` 可作为加班候选数据源。
- 没有加班审批 / 调休 / 薪资口径，不能认定加班业务闭环完成。

解决路径：

- 先定义海滨加班业务口径。
- 短期可用报表从 `working_hours > 标准工时` 识别加班候选。
- 中期可评估 HRMS 原生 Overtime / Additional Salary / Leave Allocation 等能力是否可承接。
- 只有当原生对象和报表无法覆盖海滨特有审批、补偿、重算规则时，才考虑自定义 App。

分类判断：需要海滨业务规则定义；原生报表 / 自定义报表可先解决候选识别。

### 7. 节假日出勤补充口径

现象：

- 节假日出勤场景可生成 Attendance。
- 但节假日出勤后的工资、调休、补贴或审批口径未定义。

可能原因：

- Holiday List 与 Shift Type 可支持考勤生成，但“节假日出勤算什么”属于企业制度口径。

验证证据：

- Attendance 可生成，说明 HRMS 原生链路可记录事实。
- 后续待遇没有定义，说明业务闭环未完成。

解决路径：

- 先定义节假日出勤是否自动转加班、是否必须审批、是否允许调休。
- 使用原生报表或自定义报表识别节假日出勤候选。
- 待业务口径稳定后再判断是否需要低代码定制或自定义 App。

分类判断：需要海滨业务规则定义；报表可先解决候选识别。

### 8. 临时调班补充口径

现象：

- 临时调班场景按中班生成 Attendance，说明 Shift Assignment 生效。
- 但调班申请、审批、追溯和权限口径未定义。

可能原因：

- HRMS 原生 Shift Assignment 能表达调班结果，但未必覆盖海滨的调班审批制度。

验证证据：

- 生成 `HR-ATT-2026-00021`，按中班处理。

解决路径：

- 短期复用 HRMS 原生 Shift Assignment。
- 定义谁能调班、是否需要审批、何时截止、是否允许补录。
- 若未来审批和外部系统联动复杂，再考虑自定义流程或 App。

分类判断：HRMS 原生能力可用，需海滨业务规则定义。

## 是否需要立即创建 hb_attendance_app

结论：仍不建议立即创建 `hb_attendance_app`。

理由：

- M1-R3C 已证明 Attendance 可由 HRMS 原生生成。
- 当前 6 个 GAP / PARTIAL 主要是配置复核、报表呈现和业务口径定义问题。
- 迟到 / 早退、全天缺勤、请假前置优先走 HRMS 配置复核。
- 缺卡、加班、节假日出勤、调班优先通过报表和业务口径定义收敛。
- 只有当海滨特有规则稳定后，且 HRMS 原生配置、角色权限、报表、导入、API 和低代码定制无法覆盖时，才考虑自定义 App。

## M1-R3E 建议

M1-R3E 已按本建议形成“配置复核清单与业务口径确认表”，不直接进入 App 创建。

M1-R3E 已拆为两类工作：

| 类别 | 建议动作 | 产出 |
| --- | --- | --- |
| 配置复核 | 复核 Shift Type late / early 字段、Auto Attendance 时间窗口、Absent 生成规则、Leave Allocation 最小配置 | 配置复核记录和最小可执行配置清单 |
| 业务口径确认 | 明确缺卡、缺勤、加班、节假日出勤、临时调班的海滨制度口径 | 业务口径确认表和报表字段需求 |

M1-R3E 仍不得接真实考勤机、不得接真实飞书、不得录入真实员工或生产数据、不得创建自定义 App、不得开发业务代码。若需要继续创建或调整虚构 TEST 数据，必须由用户另行明确授权。

## 状态与下一步

- M1-R3C：COMPLETED，结论为 PARTIAL / GAP_IDENTIFIED。
- M1-R3D：COMPLETED，已通过 Codex 审查并收口，结论为优先走 HRMS 配置复核、原生 / 自定义报表和海滨业务口径定义。
- M1-R3E：COMPLETED，已通过 Codex 审查并收口。
- M1-R4：未启动。

本轮未继续试运行，未创建、删除或清理 TEST 数据，未创建 App / DocType / 代码，未接飞书 / SSO / 真实考勤机，未修改核心源码，未提交数据库、日志、缓存、`.env`、密钥或备份。
