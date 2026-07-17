# M1-R1 HRMS 原生考勤对象模型验证记录

项目名称：新乡海滨智能运营管理平台。

## M1-R1 目标与边界

状态：COMPLETED。

收口记录：M1-R1 已通过 Codex 独立审查，并在 M1-R1-CLOSEOUT 中从待审查状态收口为 COMPLETED。

本轮目标：

- 只读验证 HRMS 原生考勤对象模型。
- 判断 Employee、Shift Type、Shift Assignment、Employee Checkin、Attendance、Attendance Request、Leave Application、Leave Type、Holiday List 等对象能否支撑新乡海滨考勤一期。
- 识别 HRMS 原生能力、配置验证项、导入 / 集成项、自定义报表项和后续海滨定制候选。

本轮不做：

- 不创建自定义 Frappe App。
- 不创建 `hb_attendance_app`。
- 不新增业务 DocType。
- 不开发考勤代码。
- 不接真实考勤机。
- 不接真实飞书。
- 不写入飞书。
- 不实现 SSO。
- 不修改 Frappe / ERPNext / HRMS 核心源码。
- 不修改中文翻译源码。
- 不录入真实员工、真实考勤或真实生产数据。
- 不创建测试员工、测试打卡或测试考勤结果。

## 当前环境基线

| 项目 | 当前结果 |
| --- | --- |
| site | `frontend` |
| Desk 地址 | `http://localhost:8081/login` |
| Desk 可访问性 | `HTTP 200` |
| Frappe | `16.25.0` |
| ERPNext | `16.26.2` |
| HRMS | `16.12.0 version-16 (666bf10)` |
| 已安装 App | `frappe`、`erpnext`、`hrms` |
| HR Workspace / HRMS 入口 | 可读取 `HR Setup`、`Leaves`、`Shift & Attendance` 等 Workspace |
| HRMS DocType 元数据 | 可通过只读 SQL 读取 DocType、字段、权限、Workspace 和报表元数据 |

运行态说明：

- 本轮只读查看当前已跑通的 Docker / Frappe / ERPNext / HRMS 环境。
- 未执行 `docker compose down -v`。
- 未删除 Docker volume。
- 未重建 `frontend` site。
- 未重新安装 HRMS。

## 本轮只读验证方法

本轮读取的文件：

- `CLAUDE.md`
- `AGENTS.md`
- `README.md`
- `docs/AI_CONTEXT.md`
- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/READING_GUIDE.md`
- `docs/milestones/README.md`
- `docs/milestones/M1_START_GATE.md`
- `docs/milestones/M1_R0_平台入口账号权限与本地化诊断方案.md`

本轮执行的只读命令或只读查询：

- `pwd`
- `git rev-parse --show-toplevel`
- `git branch --show-current`
- `git rev-parse HEAD`
- `git status --short`
- `git remote -v`
- `git rev-parse origin/main`
- `git branch -vv`
- `docker compose ps`
- `docker compose exec -T backend bench version`
- `docker compose exec -T backend bench --site frontend list-apps`
- `curl -s -o /dev/null -w 'login_http_code=%{http_code}\n' http://localhost:8081/login`
- 只读查询 `tabDocType`，确认重点 HRMS / ERPNext / Frappe DocType 存在性与是否可提交。
- 只读查询 `tabDocField`，确认重点 DocType 的关键字段。
- 只读查询 `tabDocPerm`，确认原生角色权限。
- 只读查询 `tabWorkspace`，确认 HRMS Workspace 入口。
- 只读查询 `tabReport`，确认考勤相关原生报表。

本轮未写入真实业务数据，未创建测试员工，未创建测试打卡，未创建测试考勤结果，未修改配置。

## HRMS 原生考勤对象清单

| 对象 | 原生用途 | 关键字段 / 机制 | 关系 | 复用判断 | 后续配置 | 海滨特有差距 |
| --- | --- | --- | --- | --- | --- | --- |
| User | 平台登录主体、权限主体、审计 owner | `name`、`email`、角色、启停状态 | 可由 Employee 的 `user_id` 关联 | 适合复用 | 需结合 M1-R0 飞书登录自动映射设计 | 飞书 open_id / union_id / user_id 映射字段或集成对象需后续设计 |
| Employee | 员工主数据 | `employee`、`employee_name`、`user_id`、`company`、`department`、`designation`、`branch`、`status`、`attendance_device_id`、`holiday_list` | 关联 User、Company、Department、Holiday List，作为考勤、请假、打卡主对象 | 适合直接复用 | 需配置公司、部门、岗位、员工编号、考勤设备 ID | 需要确认海滨工号、飞书身份、设备编号的稳定映射规则 |
| Department | 部门主数据 | `company` | 被 Employee、Attendance、Leave Application 等引用 | 适合复用 | 需配置海滨部门层级 | 部门主管可见范围和跨部门权限需后续验证 |
| Company | 公司主体 | 公司基础字段 | 被 Employee、Attendance、Shift Assignment、Leave Application 等引用 | 适合复用 | 需配置海滨公司主体 | 多法人或多厂区场景需后续确认 |
| Holiday List | 节假日规则 | `from_date`、`to_date`、holiday 明细 | 可关联 Employee、Shift Type | 适合复用 | 需配置法定节假日、厂区休息日 | 海滨特殊调休、生产班组休息日需验证 |
| Shift Type | 班次类型与自动考勤规则 | `start_time`、`end_time`、`holiday_list`、`enable_auto_attendance`、`determine_check_in_and_check_out`、`working_hours_calculation_based_on`、`begin_check_in_before_shift_start_time`、`allow_check_out_after_shift_end_time`、`process_attendance_after`、`last_sync_of_checkin`、`late_entry_grace_period`、`early_exit_grace_period` | 被 Shift Assignment、Employee Checkin、Attendance 引用，可驱动 Auto Attendance | 适合优先配置验证 | 需配置早 / 中 / 夜班、跨夜时间窗、迟到早退宽限、打卡识别方式 | 自动识别班次、复杂倒班和跨夜规则需测试数据验证 |
| Shift Assignment | 员工班次分配 | `employee`、`company`、`department`、`shift_type`、`status` | 将 Employee 与 Shift Type 绑定；该 DocType 为可提交单据 | 适合复用 | 需验证排班周期、批量分配、部门主管查看 | 自动排班、临时调班、倒班规则可能需要后续定制 |
| Employee Checkin | 打卡原始记录 | `employee`、`time`、`log_type`、`shift`、`device_id`、`skip_auto_attendance`、`attendance` | 关联 Employee、Shift Type、Attendance | 适合承接打卡导入 | 需验证打卡机导入格式、IN / OUT 识别、设备 ID 匹配 | 真实考勤机对接和异常打卡清洗需要导入 / 集成能力 |
| Attendance | 日考勤结果 | `employee`、`attendance_date`、`company`、`department`、`shift`、`status`、`working_hours`、`in_time`、`out_time`、`late_entry`、`early_exit`、`leave_type` | 可由 Auto Attendance 或人工流程生成；该 DocType 为可提交单据 | 适合复用 | 需验证自动生成、人工修正、提交 / 取消权限 | 月度核算口径、异常原因、海滨报表格式可能需要自定义报表 |
| Attendance Request | 出勤请求 / 外勤或居家等申请 | `employee`、`company`、`department`、`from_date`、`to_date`、`half_day`、`shift`、`reason`、`explanation` | 关联 Employee、Shift Type；该 DocType 为可提交单据 | 可作为补充能力复用 | 需确认海滨是否使用 On Duty / Work From Home 等类型 | 与海滨请假、外勤、补卡流程的适配需后续确认 |
| Leave Application | 请假申请 | `employee`、`leave_type`、`company`、`department`、`from_date`、`to_date`、`half_day`、`total_leave_days`、`status` | 关联 Employee、Leave Type，可影响 Attendance | 适合复用 | 需配置请假类型、审批流、假期额度 | 飞书请假数据同步、审批状态映射需后续集成 |
| Leave Type | 请假类型 | 请假类型基础字段 | 被 Leave Application 和 Attendance 引用 | 适合复用 | 需配置海滨请假类别 | 与飞书请假类型、加班调休规则映射需后续确认 |
| Auto Attendance / Mark Auto Attendance | 基于 Shift Type 和 Employee Checkin 自动生成 Attendance | 依赖 Shift Type 自动考勤字段、Employee Checkin、Shift Assignment、`last_sync_of_checkin` 等 | Shift Type / Employee Checkin -> Attendance | 适合 M1-R2 重点验证 | 需最小测试数据验证自动标记、迟到早退、缺卡和跨夜 | 复杂班次识别、异常修正、月度规则需要后续验证 |
| HR Workspace / Shift & Attendance | HRMS 模块入口 | `HR Setup`、`Leaves`、`Shift & Attendance` 等 Workspace | 提供 HRMS 后台入口和报表入口 | 适合短期入口复用 | 需结合角色权限治理菜单可见性 | 中文化、员工侧自助入口、主管入口体验需后续诊断 |

本轮只读查询还确认原生报表存在：

- `Monthly Attendance Sheet`
- `Shift Attendance`
- `Employees working on a holiday`

这些报表可作为 M1 初期验证基础，但是否满足海滨月度考勤核算格式，需要 M1-R2 结合样例数据和用户口径继续判断。

## 核心对象关系图

```text
飞书身份(open_id / union_id / user_id)
  -> Frappe User
  -> Employee.user_id

Employee
  -> Company
  -> Department
  -> Holiday List
  -> Shift Assignment
  -> Shift Type

Shift Type
  -> Auto Attendance 配置
  -> Holiday List
  -> Employee Checkin.shift
  -> Attendance.shift

Shift Assignment
  -> Employee
  -> Shift Type

Employee Checkin
  -> Employee
  -> Shift Type
  -> Attendance

Leave Type
  -> Leave Application

Leave Application
  -> Employee
  -> Leave Type
  -> Attendance / 请假状态联动

Attendance
  -> Employee
  -> Company / Department
  -> 月度统计
  -> Attendance 报表
  -> 后续考勤结果与薪资 / 运营统计
```

## 新乡海滨考勤一期需求映射

| 需求 | 初步分类 | 依据 / 说明 |
| --- | --- | --- |
| 员工基础信息 | HRMS 原生可覆盖 | Employee 已有姓名、公司、部门、岗位、状态、User 关联、设备 ID 等字段 |
| 部门与岗位 | HRMS 原生可覆盖 | Department、Designation、Branch、Company 可复用 |
| 早 / 中 / 夜班识别 | HRMS 配置后可覆盖 | Shift Type 可配置开始 / 结束时间，Shift Assignment 可分配班次；自动识别复杂场景需测试 |
| 8 小时工作制 | HRMS 配置后可覆盖 | Shift Type 可配置时间窗和工时计算方式 |
| 跨夜班 | 暂不确定，需测试数据验证 | Shift Type 有开始 / 结束时间和打卡前后时间窗，但跨夜自动考勤效果需 M1-R2 验证 |
| 打卡机数据导入 | 需要导入 / 集成 | Employee Checkin 可承接打卡记录；真实设备协议、文件格式和同步方式需后续设计 |
| 上下班打卡识别 | HRMS 配置后可覆盖 | Shift Type 支持交替 IN/OUT 或严格基于 Employee Checkin 的 `log_type` |
| 迟到 | HRMS 配置后可覆盖 | Shift Type 有 `late_entry_grace_period`，Attendance 有 `late_entry` |
| 早退 | HRMS 配置后可覆盖 | Shift Type 有 `early_exit_grace_period`，Attendance 有 `early_exit` |
| 缺卡 | 暂不确定，需测试数据验证 | Auto Attendance 可基于打卡生成结果，但缺卡异常形态和修正流程需 M1-R2 验证 |
| 请假匹配 | HRMS 原生可覆盖 | Leave Application、Leave Type、Attendance 的 `leave_type` 可复用 |
| 加班匹配 | 需要后续海滨定制 | 本轮未验证到考勤一期加班完整闭环；需结合 HRMS 现有加班对象、海滨口径和飞书审批后续判断 |
| 月度考勤结果汇总 | 需要自定义报表 | 原生有 Monthly Attendance Sheet，但海滨月度核算字段、异常口径、导出格式需验证 |
| 部门主管查看本部门 | HRMS 配置后可覆盖 / 需验证 | 原生权限有 HR Manager、HR User、Employee 等；部门范围权限需结合 Permission Query / User Permission 验证 |
| 人事查看和修正 | HRMS 原生可覆盖 | HR Manager / HR User 对 Attendance、Employee Checkin、Leave Application 有读写权限 |
| 普通员工查看自己的考勤 | HRMS 原生可覆盖 / 需验证 | Attendance、Shift Assignment、Leave Type 等有 Employee 读权限；自助范围需验证 if_owner / 用户权限 |
| 飞书登录后的员工身份映射 | 需要导入 / 集成 | 沿用 M1-R0 结论：飞书登录为主，HBOS User 自动映射 Employee |
| 后续飞书请假 / 加班数据接入 | 需要导入 / 集成 | 真实飞书读取 / 写入必须用户授权；本轮不接飞书 |

## 原生能力初步结论

应优先直接使用 HRMS 的能力：

- Employee 作为员工主数据。
- User 作为登录、权限和审计主体。
- Department、Company、Designation、Branch 作为组织与岗位基础。
- Holiday List 作为节假日和休息日基础。
- Employee Checkin 作为打卡原始记录承载对象。
- Attendance 作为日考勤结果对象。
- Leave Application / Leave Type 作为请假对象。
- HR Workspace / Shift & Attendance 作为短期后台入口。

应先通过配置验证的能力：

- Shift Type 的早 / 中 / 夜班、跨夜班、8 小时工作制、迟到早退宽限。
- Shift Assignment 的班次分配和部门范围查看。
- Auto Attendance 的 IN / OUT 识别、缺卡、迟到、早退、请假联动。
- Employee 自助查看和 Department Manager 查看本部门的权限范围。

可能需要自定义报表的能力：

- 海滨月度考勤汇总表。
- 部门考勤异常汇总。
- 班次维度统计。
- 缺卡、迟到、早退、请假、加班组合口径报表。

可能需要后续自定义 App 或独立集成的能力：

- 真实考勤机导入适配器。
- 飞书请假 / 加班 / 通讯录同步 connector。
- 海滨特有复杂倒班、自动识别班次、异常审批流。
- 飞书身份与 HBOS User / Employee 的稳定映射对象。

当前不建议创建 `hb_attendance_app`。

理由：

- HRMS 已提供 Employee、Shift Type、Shift Assignment、Employee Checkin、Attendance、Leave Application 等核心对象。
- M1-R1 尚未通过最小测试数据验证原生 Auto Attendance 的行为边界。
- 过早创建 App 容易重写 HRMS 已有能力，增加升级和维护风险。
- 更稳妥的路径是 M1-R2 先做 HRMS 原生考勤配置试运行方案。

## Gap List：海滨特有差距清单

| 分类 | 差距 | 后续处理建议 |
| --- | --- | --- |
| 班次规则差距 | 早 / 中 / 夜班、跨夜班、8 小时制、迟到早退宽限可配置，但海滨真实班次和异常口径尚未验证 | M1-R2 用最小测试班次验证 |
| 打卡数据导入差距 | Employee Checkin 可承接记录，但真实考勤机协议、文件字段、设备 ID 与员工匹配规则未确定 | 后续设计导入方案，不接真实机器前先用样例格式 |
| 自动排班 / 自动识别班次差距 | Shift Assignment 可分配班次，但自动识别员工当日班次、倒班规律和临时调班未验证 | M1-R2 验证原生排班；复杂规则列为定制候选 |
| 请假 / 加班与飞书集成差距 | Leave Application 可承接请假，但飞书请假、加班审批、调休和同步权限未接入 | 需要用户授权后另开飞书集成轮次 |
| 月度核算报表差距 | 原生有 Monthly Attendance Sheet，但是否符合海滨工资 / 管理口径未知 | 先验证原生报表，再决定自定义报表 |
| 部门权限差距 | 原生角色能区分 HR / Employee，但部门主管只看本部门需权限规则验证 | M1-R2 或后续权限轮次验证 User Permission / Permission Query |
| 员工自助查看差距 | Employee 可读部分考勤对象，但员工端入口体验和可见范围需确认 | 短期用 Frappe Desk / Workspace，后续再考虑员工侧入口优化 |
| 中文化 / 本地化体验差距 | HRMS 原生中文覆盖、Workspace、Report、按钮和字段文案可能不完整 | 继续诊断，不改核心源码；优先 Custom Translation / 配置 / 后续自定义 App 承载 |

## M1-R2 承接

M1-R2 已形成 `HRMS 原生考勤配置试运行方案`，并已通过 Codex 独立审查收口为 COMPLETED。

M1-R2 仍然遵守：

- 不创建 App。
- 不创建 `hb_attendance_app`。
- 不接真实考勤机。
- 不接真实飞书。
- 不写入飞书。
- 不录入生产数据。
- 使用最小测试数据或配置方案验证 HRMS 原生考勤流程。
- 明确测试数据命名规则、清理方案和不提交数据库。
- 重点验证 Shift Type、Shift Assignment、Employee Checkin、Auto Attendance、Attendance、Leave Application 的实际闭环。

## 结论

M1-R1 是对象模型验证，不是业务实现。

HRMS 原生能力是 M1 初期主路线。当前应优先复用 HRMS 的 Employee、Shift Type、Shift Assignment、Employee Checkin、Attendance、Attendance Request、Leave Application、Leave Type、Holiday List、Workspace 和原生报表能力。

`hb_attendance_app` 不是当前动作。只有在 M1-R2 或后续轮次用最小数据验证后，确认 HRMS 原生配置、导入、报表、权限无法覆盖新乡海滨特有规则时，才考虑进入自定义 App 决策。

飞书登录方向沿用 M1-R0 结论：飞书作为员工主登录入口，HBOS User 自动映射 Employee，Frappe 权限体系承接系统权限和审计。

中文化问题仍只诊断，不改 Frappe / ERPNext / HRMS 核心源码，不改中文翻译源码。
