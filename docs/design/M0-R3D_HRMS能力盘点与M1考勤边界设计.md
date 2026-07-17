# M0-R3D HRMS 能力盘点与 M1 考勤边界设计

项目名称：新乡海滨智能运营管理平台。

## 本轮目标

本轮只做 HRMS 原生能力盘点与 M1 考勤一期边界设计，为后续是否进入 M1、如何验证考勤一期、何时创建海滨自定义考勤 App 提供决策依据。

本轮不创建海滨自定义 Frappe App，不开发代码，不配置真实业务数据，不接飞书真实写入，不做 Vue / React 前端驾驶舱，不修改 Frappe / ERPNext / HRMS 核心源码。

## 本轮读取文件

- `README.md`
- `CLAUDE.md`
- `AGENTS.md`
- `docs/AI_CONTEXT.md`
- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/READING_GUIDE.md`
- `docs/milestones/README.md`
- `docs/milestones/M0.md`
- `docs/deployment/M0-R3A_Frappe_Docker最小环境落地记录.md`
- `docs/deployment/M0-R3B_Frappe_HR安装前评估.md`
- `docs/deployment/M0-R3C_Frappe_HR安装验证记录.md`
- `docker-compose.yml`
- `.env.example`
- `.gitignore`

## 官方参考来源

- Frappe HR Introduction：`https://docs.frappe.io/hr/introduction`
- Attendance：`https://docs.frappe.io/hr/attendance`
- Employee Checkin：`https://docs.frappe.io/hr/employee-checkin`
- Auto Attendance：`https://docs.frappe.io/hr/auto-attendance`
- Using Auto Attendance：`https://docs.frappe.io/hr/using-auto-attendance`
- Shift Type：`https://docs.frappe.io/hr/shift-type`
- Shift Assignment：`https://docs.frappe.io/hr/shift-assignment`
- Shift Schedule：`https://docs.frappe.io/hr/shift-schedule`
- Shift Schedule Assignment：`https://docs.frappe.io/hr/shift-schedule-assignment`
- Employee Attendance Tool：`https://docs.frappe.io/hr/employee-attendance-tool`
- Integrating Frappe HR With Biometric Attendance Devices：`https://docs.frappe.io/hr/integrating-frappe-hr-with-biometric-attendance-devices`
- Leave Application：`https://docs.frappe.io/hr/leave-application`
- Holiday List：`https://docs.frappe.io/hr/holiday-list`
- Payroll Entry：`https://docs.frappe.io/hr/payroll-entry`
- `frappe/hrms` 官方仓库：`https://github.com/frappe/hrms`

## 执行前只读检查

| 检查项 | 结果 |
| --- | --- |
| 工作目录 | `$PROJECT_ROOT` |
| 当前分支 | `main` |
| 本轮开始时真实 HEAD | `c1ca470c6dd1effeb5832c74025f6b1d75838842` |
| 附件中旧基线 | `9d7ade1eaa0e5eef86ced639b4e1efe7e04a858a`，这是 M0-R3C-FIX 前的旧 HEAD |
| git status | clean |
| Docker 容器状态 | `backend`、`db`、`frontend`、`queue-long`、`queue-short`、`redis-cache`、`redis-queue`、`scheduler`、`websocket` 均为 Up，`db` healthy |
| Desk 可访问性 | `http://localhost:8081/login` 返回 `HTTP 200` |
| site | `frontend` |
| Frappe | `16.25.0` |
| ERPNext | `16.26.2` |
| HRMS | `16.12.0 version-16 (666bf10)` |
| 已安装 App | `frappe`、`erpnext`、`hrms` |
| 自定义 App | 未创建 `hb_core_app`、`hb_attendance_app`、`hb_feishu_app` |
| 真实业务数据 | 未录入真实员工、打卡、班次、考勤、请假、假日等业务数据 |

当前关键业务表记录数只读检查：

| 对象 | 记录数 | 说明 |
| --- | ---: | --- |
| Employee | 0 | 未录入真实员工 |
| Attendance | 0 | 未生成真实考勤 |
| Employee Checkin | 0 | 未导入真实打卡 |
| Shift Type | 0 | 未配置真实早中夜班 |
| Shift Assignment | 0 | 未配置真实排班 |
| Shift Schedule | 0 | 未配置真实排班周期 |
| Leave Application | 0 | 未配置真实请假 |
| Holiday List | 0 | 未配置真实假日 |
| Department | 27 | ERPNext / HRMS 初始化数据 |
| Branch | 0 | 未配置真实分支 |
| Company | 2 | 初始化 / Demo 公司数据 |

## 当前环境事实

当前本地环境已完成 Frappe / ERPNext / Docker 最小环境、HRMS 安装验证和 HRMS 前端资源修复。HR Workspace 可访问，基础 HR DocType 存在，Roster 页面可访问。

本轮只读字段检查显示：

- `Employee` 已包含 `attendance_device_id`、`company`、`department`、`branch`、`holiday_list` 等字段。
- `Employee Checkin` 已包含 `employee`、`time`、`log_type`、`shift`、`device_id`、`skip_auto_attendance` 等字段。
- `Shift Type` 已包含 `start_time`、`end_time`、`enable_auto_attendance`、`determine_check_in_and_check_out`、`working_hours_calculation_based_on`、`process_attendance_after`、`last_sync_of_checkin`、`late_entry_grace_period`、`early_exit_grace_period`、`allow_overtime` 等字段。
- `Attendance` 已包含 `employee`、`attendance_date`、`status`、`shift`、`working_hours`、`in_time`、`out_time`、`late_entry`、`early_exit`、`overtime_type` 等字段。
- 本地已存在 `Monthly Attendance Sheet`、`Shift Attendance`、`Employees working on a holiday` 等 Attendance 相关报表。

## HRMS 原生能力盘点

| 能力 | 官方定位 / 作用 | 与新乡海滨考勤需求的关系 | 是否可直接复用 | 是否需要配置验证 | 是否需要后续自定义 | 风险或限制 |
| --- | --- | --- | --- | --- | --- | --- |
| Employee | 员工主数据，承载员工身份、组织、考勤设备 ID 等信息 | 需要把打卡机员工编号映射到 HRMS Employee；`attendance_device_id` 是关键字段 | 可复用 | 需要用测试员工验证编号映射 | 真实员工同步、字段映射、批量导入可能后续自定义 | 员工编号、打卡机编号、人事编号若不统一，会影响自动考勤 |
| Attendance | 员工每日考勤结果，包含 Present、Absent、On Leave、Half Day、Work From Home 等状态 | 是考勤一期的最终结果对象，可承载迟到、早退、工作时长、班次等结果 | 可复用 | 需要验证 Auto Attendance 生成结果 | 班次统计、异常解释、海滨特有状态可能后续扩展 | 原生状态不一定覆盖全部本地考勤口径 |
| Employee Checkin | 员工打卡日志，支持 IN / OUT、时间、设备、跳过自动考勤等字段 | 可承接打卡机导出的上下班时间，是自动考勤的输入 | 可复用 | 必须用测试 CSV 或手工测试数据验证导入 | 若打卡机字段复杂或无 IN/OUT，需要导入适配层 | 导出字段不标准、缺卡、多次打卡、跨天夜班会增加判断复杂度 |
| Auto Attendance | 基于 Employee Checkin 与 Shift Type 自动生成 Attendance | 对自动检测迟到、早退、缺勤有直接价值 | 可复用 | 必须验证早 / 中 / 夜班配置、Last Sync、Process Attendance After | 复杂班次识别、异常归因、跨天夜班可能需要自定义 | 配置项较多，Last Sync 未正确推进时不会处理打卡 |
| Shift Type | 定义班次开始 / 结束时间、自动考勤、迟到早退宽限、打卡窗口等 | 可建模早班 / 中班 / 夜班，是识别班次与迟到早退的核心 | 可复用 | 必须配置三类测试班次验证 | 若海滨班次规则含复杂轮班、跨班加班、休息扣除，可能后续自定义 | 夜班跨天、宽限时间、实际打卡窗口必须由人事确认 |
| Shift Assignment | 将某个员工在某段日期分配到某个 Shift Type | 可用于明确某员工当天应上早 / 中 / 夜班 | 可复用 | 需要测试员工排班验证 | 批量排班、导入排班、班组规则可能后续扩展 | 若仅靠打卡时间反推班次，而非预排班，原生能力可能不足 |
| Shift Schedule | 定义重复排班规则 | 对周期性轮班有帮助 | 可复用 | 需要在 M1 后段验证 | 复杂倒班规则或临时换班可能后续扩展 | 一期可先不做复杂排班优化 |
| Shift Schedule Assignment | 将 Shift Schedule 分配给员工并由 scheduler 创建重复 Shift Assignment | 可用于周期排班自动化 | 可复用 | 需要测试 scheduler 是否能按规则生成 | 多班组复杂轮转可能后续自定义 | 当前 HRMS 安装为运行态验证，长期 scheduler 可复现性仍需治理 |
| Leave Application | 员工请假申请与审批结果 | 可与 Attendance 的 On Leave 结果衔接；未来飞书请假可同步到该对象或中间对象 | 可复用 | 需要测试请假与考勤结果联动 | 飞书请假同步、审批映射可能后续自定义 | 不同来源请假数据口径需统一 |
| Holiday List | 假日清单，可影响 Auto Attendance 是否在假日标记缺勤 | 对法定节假日、工厂休息日、班次假日判断有价值 | 可复用 | 需要测试是否按公司 / 员工 / 班次应用 | 多厂区不同假日、临时调休可能后续扩展 | 假日与倒班制冲突时需人工确认 |
| Department / Branch / Company | 组织维度，用于员工归属、筛选、统计、权限和报表 | 一期可用于按部门 / 分支统计考勤 | 可复用 | 需要用测试组织验证统计维度 | 多厂区、多班组、复杂权限可能后续扩展 | 初始化数据不等于海滨真实组织，需要后续清洗 |
| Employee Attendance Tool | 按日期、部门、分支批量标记考勤 | 可作为人工补录或测试校验工具 | 可复用 | 可在测试数据中验证 | 批量异常处理可能后续扩展 | 不适合替代自动打卡导入主流程 |
| Attendance 报表 / Monthly Attendance Sheet | 查看月度考勤、班次考勤等报表 | 可作为 M1 一期最小验收报表候选 | 可复用 | 需要用测试数据验证报表输出 | 早 / 中 / 夜班次数统计可能需要自定义报表 | 原生报表可能不满足海滨验收格式 |
| Biometric / 外部考勤设备集成 | 官方建议可通过 Data Import Tool 或 API 将打卡日志写入 Employee Checkin | 与打卡机导出上下班打卡时间直接相关 | 部分可复用 | M1 先用测试 CSV 验证导入 | 自动同步、字段转换、错误重试需要后续开发 | 真实设备协议、字段、时区、员工编号都可能不稳定 |
| Payroll | 薪资批量处理、工资单等能力 | 与考勤结果可有关联，但不是考勤一期核心目标 | M1 不直接复用 | 不在 M1 验证 | 薪资核算阶段另行评估 | 过早进入薪资会显著扩大范围 |

## 用户考勤一期需求适配判断

| 分类 | 内容 | M1 处理建议 |
| --- | --- | --- |
| A. HRMS 原生可覆盖 | Employee 主数据、Attendance 结果、Employee Checkin 日志、Shift Type、Shift Assignment、Leave Application、Holiday List、部门 / 分支 / 公司维度、基础 Attendance 报表 | M1 优先复用原生对象，不创建自定义 App |
| B. HRMS 需要配置后可覆盖 | 早 / 中 / 夜班建模、迟到 / 早退宽限、打卡窗口、自动考勤启用、请假与考勤状态联动、月度考勤报表 | M1 用测试数据配置验证，形成配置清单 |
| C. 需要导入 / 接口对接后可覆盖 | 打卡机导出数据进入 Employee Checkin、外部请假 / 加班数据进入 HRMS 或中间对象、员工编号映射 | M1 先用样例 CSV / 测试数据，不接真实生产设备和飞书 |
| D. 需要自定义 App 或后续开发 | 自动识别早 / 中 / 夜班的特有规则、班次次数统计专用报表、飞书请假 / 加班同步、异常解释、跨天夜班口径、批量导入校验 | M1 初期不做；M1-R5 以后根据验证结果决策是否创建 `hb_attendance_app` |
| E. M1 一期明确不做 | 复杂排班优化、完整薪资核算、真实飞书写入、审批流深度定制、复杂 UI 驾驶舱、多厂区复杂权限、自定义算法、生产级数据迁移 | 明确排除，避免一期失控 |

## M1 考勤一期推荐边界

M1 一期目标不是“开发完整考勤系统”，而是用 HRMS 原生对象验证新乡海滨考勤闭环是否能跑通。

推荐最小范围：

1. 基础组织 / 员工主数据验证：只创建测试公司 / 部门 / 员工，不录入真实员工。
2. 班次类型建模：用测试班次配置早班 / 中班 / 夜班，验证跨天夜班是否能表达。
3. Employee Checkin 打卡数据导入验证：使用测试 CSV 或手工测试打卡，不接真实考勤机生产数据。
4. Auto Attendance 自动生成 Attendance 验证：验证自动生成 Present / Absent / On Leave / Half Day 等结果。
5. 迟到 / 早退基础规则验证：验证 `late_entry`、`early_exit`、宽限分钟数和打卡窗口。
6. 请假 Leave Application 与 Attendance 基础联动验证：只用测试请假单，不接飞书。
7. 最小报表或导出验证：优先验证 Monthly Attendance Sheet、Shift Attendance；如无法统计早中夜班次数，记录为自定义报表候选。
8. 只使用测试数据，不接真实飞书，不接真实考勤机生产数据。

M1 一期明确不做：

- 不做复杂排班优化。
- 不做完整薪资核算。
- 不做真实飞书写入。
- 不做审批流深度定制。
- 不做复杂 UI 驾驶舱。
- 不做多厂区复杂组织权限。
- 不做自定义算法。
- 不做生产级数据迁移。
- 不修改 Frappe / ERPNext / HRMS 核心源码。

## M1 分轮建议

| 轮次 | 目标 | 允许做什么 | 禁止做什么 | 验收标准 | 是否需要 Codex 审查 |
| --- | --- | --- | --- | --- | --- |
| M1-R1 | HRMS 考勤对象模型验证 | 只读盘点 DocType、字段、权限、报表；设计测试数据结构；明确测试口径 | 不创建真实业务数据；不创建自定义 App；不接飞书 | 输出对象模型验证文档和测试数据模板 | 需要 |
| M1-R2 | 测试员工与班次配置 | 创建少量测试公司 / 部门 / 员工 / 早中夜班 / 假日；记录配置步骤 | 不录入真实员工；不接生产考勤机；不开发代码 | 测试员工、Shift Type、Shift Assignment 可复现 | 需要 |
| M1-R3 | Employee Checkin 导入与 Auto Attendance 验证 | 导入测试打卡 CSV；触发 / 等待 Auto Attendance；验证 Attendance 结果 | 不接真实考勤机；不写同步代码；不提交真实数据 | Attendance 能由测试 Employee Checkin 自动生成，迟到早退可观察 | 需要 |
| M1-R4 | 请假 / 加班 / 异常边界验证 | 用测试 Leave Application、缺卡、迟到、早退、夜班样例验证边界 | 不接飞书真实写入；不做完整审批流；不做薪资 | 形成异常边界矩阵和未覆盖清单 | 需要 |
| M1-R5 | 一期验收文档与自定义 App 决策 | 汇总验证结果、报表样例、是否需要 `hb_attendance_app` 的证据 | 不直接开始开发自定义 App，除非用户明确批准 | 输出 M1 一期验收报告和 M1 后续决策建议 | 需要 |

## 自定义 App 决策建议

M1 一期不建议立即创建 `hb_attendance_app`。

理由：

- HRMS 已原生提供 Employee、Employee Checkin、Shift Type、Shift Assignment、Auto Attendance、Attendance、Leave Application、Holiday List 和基础报表。
- 当前项目还没有用测试数据验证 HRMS 原生能力的上限，过早创建自定义 App 会增加维护成本和边界混乱。
- 新乡海滨的早 / 中 / 夜班、迟到早退、缺卡、请假、加班口径还需要人事确认，当前不宜直接固化为代码。
- 不修改 HRMS 核心源码是长期稳定原则；应先把原生对象跑通，再决定外接还是扩展。

什么时候才创建 `hb_attendance_app`：

- HRMS 原生 Shift Type / Auto Attendance 无法表达新乡海滨确认后的班次识别规则。
- 原生报表无法满足“一期验收报表”的早 / 中 / 夜班次数统计和异常统计格式。
- 飞书请假 / 加班、打卡机导入、异常处理需要稳定的中间对象和审计日志。
- 用户明确批准进入自定义 App 阶段，并允许创建 App / 写业务代码。

`hb_attendance_app` 未来可能承载：

- 打卡机导入适配器、字段映射、导入批次、错误重试和审计日志。
- 早 / 中 / 夜班识别规则、跨天夜班规则、缺卡规则和特殊班次规则。
- 海滨专用考勤汇总报表和导出模板。
- 飞书请假 / 加班数据同步中间对象。
- HRMS 原生 Attendance / Employee Checkin 的补充校验和异常解释。

应继续留在 HRMS 原生对象里的内容：

- 员工主数据：Employee。
- 原始打卡日志：Employee Checkin。
- 班次配置：Shift Type、Shift Assignment、Shift Schedule。
- 标准考勤结果：Attendance。
- 请假记录：Leave Application。
- 假日配置：Holiday List。

## 飞书边界

M1 一期不做飞书真实写入，不发送群消息，不写多维表格，不创建任务，不提交审批，不修改通讯录，不创建日程，不写文档。

M1 可以设计未来飞书集成边界：

- 飞书请假 / 加班数据未来可作为外部数据源，同步到 HRMS Leave Application、Attendance 相关对象，或同步到 `hb_attendance_app` 中间对象。
- 飞书审批状态与 HRMS 请假 / 加班状态需要字段映射和冲突处理规则。
- 真正接飞书前必须另开 Mx 飞书集成阶段。
- 任何飞书真实写入必须由用户明确授权。

## 风险清单

| 风险 | 说明 | M1 应对 |
| --- | --- | --- |
| HRMS 原生考勤模型与本地班次规则不完全匹配 | 早中夜班、跨天夜班、临时调班可能超出原生配置 | 先用测试数据验证，再决定是否自定义 |
| 打卡机数据字段不标准 | 可能缺少员工编号、IN/OUT、设备 ID 或时间格式不统一 | M1 启动前索取导出样例 |
| 早中夜班识别规则需要人事确认 | 如果没有预排班，靠打卡时间反推班次需要明确规则 | M1-R1 先形成规则问题清单 |
| 请假 / 加班来源不统一 | HRMS、飞书、线下表格可能同时存在 | M1 不接真实飞书，只设计映射 |
| Auto Attendance 配置复杂 | Process Attendance After、Last Sync、打卡窗口、假日都会影响结果 | M1-R3 专门验证配置闭环 |
| 测试数据与真实数据差异 | 测试样例少可能无法覆盖缺卡、跨天、加班 | M1-R4 补充异常样例 |
| 自定义 App 与 HRMS 原生对象边界不清 | 过早自定义会造成重复数据源 | M1-R5 以验证证据决策 |
| 当前 HRMS 运行态安装可复现性不足 | M0-R3C-FIX 已记录运行态同步风险 | 后续环境治理时固化自定义镜像或 Compose 策略 |

## M1 启动前待确认清单

需要用户或人事确认：

- 早班 / 中班 / 夜班具体时间范围。
- 夜班是否跨天，跨天夜班归属到哪一天。
- 迟到 / 早退容忍分钟数。
- 上班缺卡、下班缺卡、全天缺卡如何处理。
- 请假和加班数据来源：HRMS 手工、飞书审批、线下表格，还是混合。
- 打卡机导出字段样例：员工编号、姓名、打卡时间、设备 ID、IN/OUT、部门等。
- 员工编号是否能与 HRMS Employee 的 `attendance_device_id` 对应。
- 是否需要按部门 / 班组 / 岗位 / 分支统计。
- 一期验收报表长什么样：按人、按天、按班次、按部门、按月汇总哪些字段。
- 早 / 中 / 夜班次数统计是否按 Attendance 的 `shift` 字段即可满足。
- 加班是否只记录，还是要参与薪资核算。
- 是否存在临时调班、换班、连班、倒班、休息日上班等特殊场景。

## 本轮结论

状态：REVIEWING。

M0-R3D 已完成 HRMS 能力盘点与 M1 考勤一期边界设计，等待 Codex 审查。建议 M1 初期优先验证 HRMS 原生能力，不急于创建 `hb_attendance_app`。只有当测试数据证明 HRMS 原生对象无法表达新乡海滨特有规则，或一期验收报表必须定制时，才进入自定义 App 决策。

## 未做事项

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

## 下一步建议

下一步建议交给 Codex 做 M0-R3D 审查。审查通过后，由用户决定是进入 M1 启动前决策，还是先做 M0-R3E 环境可复现性收口。
