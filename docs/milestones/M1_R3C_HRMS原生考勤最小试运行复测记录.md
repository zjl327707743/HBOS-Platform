# M1-R3C HRMS 原生考勤最小试运行复测记录

项目名称：新乡海滨智能运营管理平台。

状态：COMPLETED。

审查记录：M1-R3C 已通过 Codex 审查，审查结果为 PASS。本次 M1-R3C-CLOSEOUT 仅做状态收口，将 M1-R3C 从 REVIEWING 改为 COMPLETED；未继续试运行，未创建、删除或清理 TEST 数据，未创建 App / DocType / 代码。

收口结论：PARTIAL / GAP_IDENTIFIED。M1-R3C 是 HRMS 原生考勤最小试运行完成，不是海滨考勤业务闭环完成。

执行日期：2026-07-08。

本轮前提：用户已明确授权创建 / 更新虚构 TEST 数据。本轮只使用 `TEST-HBOS-M1R3C-*` 与 `test-hbos-m1r3c-*` 前缀的虚构数据，避免覆盖旧 `TEST-HBOS-M1R3-*` 数据。

## 目标与边界

M1-R3C 目标是在 M1-R3B-FIX 恢复 Redis / worker / scheduler / bench doctor / login 后，重新执行 HRMS 原生考勤最小试运行，复测 Company / User / Employee 写入阻断，并验证 HRMS 原生 Auto Attendance / Attendance 在最小班次和 14 个虚构场景下的实际表现。

本轮不是业务开发，不创建 `hb_attendance_app`，不创建自定义 App / DocType，不接真实考勤机，不接真实飞书，不实现 SSO，不使用真实员工、真实部门、真实打卡或生产数据，不修改 Frappe / ERPNext / HRMS 核心源码。

## 读取文件

- `CLAUDE.md`
- `AGENTS.md`
- `README.md`
- `docs/AI_CONTEXT.md`
- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/READING_GUIDE.md`
- `docs/milestones/README.md`
- `docs/milestones/M1_START_GATE.md`
- `docs/milestones/M1_R2_HRMS原生考勤配置试运行方案.md`
- `docs/milestones/M1_R3_HRMS原生考勤最小测试数据试运行记录.md`
- `docs/milestones/M1_R3A_运行态阻断诊断与TEST数据隔离清理方案.md`
- `docs/milestones/M1_R3B_运行态最小修复方案.md`
- `docs/milestones/M1_R3B_FIX_运行态最小修复执行记录.md`

## 执行命令摘要

前置状态：

```bash
pwd
git branch --show-current
git rev-parse HEAD
git rev-parse origin/main
git status --short
git branch -vv
git remote -v
```

运行态复核：

```bash
docker compose ps redis-cache redis-queue queue-short queue-long scheduler websocket backend frontend db
curl -s -o /dev/null -w 'login_http_code=%{http_code}\n' http://localhost:8081/login
docker compose exec -T backend bash -lc 'cd /home/frappe/frappe-bench && bench version && bench --site frontend list-apps && bench --site frontend doctor && bench --site frontend scheduler status'
```

元数据与数据复核：

```bash
docker compose exec -T backend bash -lc 'cd /home/frappe/frappe-bench && ./env/bin/python - << "PY" ... PY'
```

该类 Python 命令仅在容器内通过 Frappe ORM / DB API 执行，用于读取 DocType 元数据、复核旧 TEST 数据计数、创建 M1-R3C 虚构 TEST 数据、调用 Shift Type 原生 `process_auto_attendance`、复核 Attendance 结果。未写入仓库脚本文件。

提交前自检命令：

```bash
git status --short
git diff --check
git diff --name-only
git branch -vv
git remote -v
```

## 运行态复核结果

- `main` 与 `origin/main` 起始一致，起始 HEAD 为 `9f92823aae41e4cecc50512230a2e99f1b36ed4b`。
- `redis-cache`、`redis-queue`、`queue-short`、`queue-long`、`scheduler`、`websocket`、`backend`、`frontend`、`db` 均为 Up，其中 `db` 为 healthy。
- `/login` 返回 `HTTP 200`。
- `bench doctor` 显示 `Workers online: 1`。
- `bench --site frontend scheduler status` 显示 `Scheduler is enabled for site frontend`。
- `bench --site frontend list-apps` 返回 `frappe`、`erpnext`、`hrms`。

## TEST 数据计数对比

旧 `TEST-HBOS-M1R3-*` 数据本轮未清理、未删除、未覆盖。由于旧轮次存在命名字段不完全一致的问题，本轮对旧数据只做只读复核，不以本轮结果改写旧轮次结论。

M1-R3C 新前缀数据最终计数如下：

| 对象 | M1-R3C 新数据计数 |
| --- | ---: |
| Company | 1 |
| Department | 2 |
| User | 8 |
| Employee | 8 |
| Holiday List | 1 |
| Holiday child row | 1 |
| Shift Type | 4 |
| Shift Assignment | 14 |
| Employee Checkin | 22 |
| Leave Type | 1 |
| Leave Application | 0 |
| Attendance | 13 |

## 创建 / 更新的 TEST 数据摘要

本轮创建并提交的虚构数据包括：

- Company：`TEST-HBOS-M1R3C-虚构公司`
- Department：`TEST-HBOS-M1R3C-生产一部 - R3C`、`TEST-HBOS-M1R3C-生产二部 - R3C`
- User：`test-hbos-m1r3c-e001@example.test` 至 `test-hbos-m1r3c-e008@example.test`
- Employee：`HR-EMP-00009` 至 `HR-EMP-00016`，均绑定上述虚构 User
- Holiday List：`TEST-HBOS-M1R3C-虚构节假日`
- Holiday：`2026-06-21`
- Shift Type：
  - `TEST-HBOS-M1R3C-早班-0800-1600`
  - `TEST-HBOS-M1R3C-中班-1600-0000`
  - `TEST-HBOS-M1R3C-夜班-0000-0800`
  - `TEST-HBOS-M1R3C-跨夜班-2000-0400`
- Shift Assignment：14 条，均已提交
- Employee Checkin：22 条
- Leave Type：`TEST-HBOS-M1R3C-虚构事假`
- Attendance：13 条，均为 HRMS 原生自动考勤处理后生成或确认

Company 创建期间仍出现 ERPNext 初始化默认部门树的非阻断性报错日志：`Could not find Parent Department: All Departments`。本轮 Company 最终已成功落库，因此该问题不再阻断 M1-R3C，但建议在 M1-R3D 继续确认公司 / 部门默认结构是否会影响后续组织治理。

## Company / User / Employee 阻断复测

结论：M1-R3 的 Company / User / Employee 写入阻断在 M1-R3C 新前缀复测中已解除。

- Company：成功创建 1 个。
- User：成功创建 8 个。
- Employee：成功创建 8 个，并通过 `user_id` 与虚构 User 建立关联。
- 后续 Shift Assignment、Employee Checkin 和 Attendance 均能关联这些 Employee。

## 班次配置结果

| 班次 | 时间 | 复测结果 |
| --- | --- | --- |
| 早班 | 08:00-16:00 | 可创建 Shift Type，可提交 Shift Assignment，可生成 Attendance |
| 中班 | 16:00-00:00 | 可处理跨日下班打卡，可生成 Attendance |
| 夜班 | 00:00-08:00 | 可生成 Attendance |
| 跨夜班 | 20:00-04:00 | 可处理跨日班次，可生成 Attendance |

## 14 个场景验证结果

Codex PASS 口径：14 个场景中 8 个通过，6 个为 GAP / PARTIAL。Attendance 可由 HRMS 原生生成，但异常口径和业务口径仍需 M1-R3D 继续诊断。

| 编号 | 场景 | 结果 | 结论 |
| --- | --- | --- | --- |
| AT-001 | 正常早班 | 生成 `HR-ATT-2026-00013`，Present，8.13 小时 | PASS |
| AT-002 | 正常中班 | 生成 `HR-ATT-2026-00019`，Present，8.12 小时，跨日下班正常 | PASS |
| AT-003 | 正常夜班 | 生成 `HR-ATT-2026-00022`，Present，8.0 小时 | PASS |
| AT-004 | 跨夜班正常 | 生成 `HR-ATT-2026-00024`，Present，8.17 小时，跨日班次正常 | PASS |
| AT-005 | 迟到 | 生成 `HR-ATT-2026-00014`，Present，7.83 小时，但 `late_entry=0` | GAP |
| AT-006 | 早退 | 生成 `HR-ATT-2026-00020`，Present，7.7 小时，但 `early_exit=0` | GAP |
| AT-007 | 上班缺卡 | 生成 `HR-ATT-2026-00023`，Present，0 小时，`in_time` 为空 | PARTIAL / GAP |
| AT-008 | 下班缺卡 | 生成 `HR-ATT-2026-00025`，Present，0 小时，`out_time` 为空 | PARTIAL / GAP |
| AT-009 | 全天缺勤 | 未生成 Attendance | GAP |
| AT-010 | 半天请假 | Leave Application 因缺少 Leave Allocation 未通过；生成 Present，4.03 小时 | PARTIAL / GAP |
| AT-011 | 全天请假 | Leave Application 因缺少 Leave Allocation 未通过；生成 Absent，0 小时 | PARTIAL / GAP |
| AT-012 | 加班候选 | 生成 `HR-ATT-2026-00016`，Present，10.53 小时 | PARTIAL |
| AT-013 | 节假日出勤 | 生成 `HR-ATT-2026-00017`，Present，8.0 小时 | PASS / PARTIAL |
| AT-014 | 临时调班 | 生成 `HR-ATT-2026-00021`，Present，8.1 小时，按中班处理 | PASS |

收口解释：

- 通过项表示 HRMS 原生对象链路能生成或记录对应最小验证证据，不代表海滨业务口径已闭环。
- GAP / PARTIAL 项集中在迟到 / 早退标记、缺卡 / 缺勤口径、请假 Leave Allocation、加班业务口径。
- 加班场景仅证明 Attendance `working_hours` 可记录长工时，不代表加班审批、调休、薪资或报表口径已定义。

## 迟到、早退、缺卡、请假、加班、节假日、调班结论

- 迟到：Attendance 可生成，但本轮配置下 `late_entry` 未按预期置位，需要 M1-R3D 诊断 Shift Type 宽限、自动考勤字段、处理时点或 HRMS 原生规则口径。
- 早退：Attendance 可生成，但本轮配置下 `early_exit` 未按预期置位，需要 M1-R3D 继续诊断。
- 上班缺卡 / 下班缺卡：Attendance 可生成，但 HRMS 原生结果仍为 Present 且工时为 0，缺卡异常需要后续通过原生报表、异常处理流程或受控定制补足。
- 全天缺勤：无打卡场景未自动生成 Absent，需要继续验证 HRMS 是否要求额外配置、调度时点或独立补勤 / 缺勤生成机制。
- 半天请假 / 全天请假：Leave Application 因缺少 Leave Allocation 被原生校验阻止。本轮不绕过校验，结论为需要先建立 Leave Allocation 或最小请假前置配置。
- 加班：长工时可体现在 Attendance `working_hours`，但不等同于加班审批、加班费或调休规则完成。
- 节假日出勤：在 Holiday List 与 Shift Type 配置允许后可生成 Attendance，但节假日出勤的薪资、调休或报表口径仍需后续验证。
- 临时调班：Shift Assignment 可覆盖员工当日班次，HRMS 原生能力可用。

## HRMS 原生能力结论

本轮证明 HRMS 原生链路已能覆盖以下能力：

- Company / Department / User / Employee 基础写入。
- Employee 与 User 稳定关联。
- 早班、中班、夜班、跨夜班 Shift Type 创建。
- Shift Assignment 提交。
- Employee Checkin 写入。
- Auto Attendance 处理并生成 Attendance。
- 跨日下班、跨夜班、节假日出勤、临时调班的基础 Attendance 生成。

本轮仍需要配置或后续验证的能力：

- 迟到 / 早退标记触发条件。
- 上班缺卡 / 下班缺卡异常识别和处理流程。
- 全天缺勤自动生成口径。
- Leave Allocation 与 Leave Application 的最小请假链路。
- 加班审批、调休、薪资或报表口径。
- 节假日出勤的业务口径和报表口径。

本轮 Gap：

- 不能把 Attendance 生成等同于海滨考勤业务闭环完成。
- 不能仅凭 HRMS 原生对象完成而跳过异常口径、审批口径和报表口径验证。
- 不能在 M1-R3C 阶段创建 `hb_attendance_app` 来提前重写 HRMS 原生能力。

## 是否建议创建 hb_attendance_app

当前仍不建议创建 `hb_attendance_app`。

理由：

- M1-R3C 已证明 HRMS 原生链路可以生成大部分最小 Attendance 结果。
- 当前问题主要集中在配置、异常口径、请假前置、加班与报表解释，不是原生对象模型完全不可用。
- 自定义 App 应只用于 HRMS 原生能力无法覆盖的新乡海滨特有规则，不应用于提前重写 HRMS 已有考勤对象。

## 数据隔离与清理建议

- 旧 `TEST-HBOS-M1R3-*` 数据本轮不清理、不覆盖。
- 新 `TEST-HBOS-M1R3C-*` / `test-hbos-m1r3c-*` 数据已完成 M1-R3C 审查收口，后续仍应隔离保留，除非用户另行授权清理。
- 若用户后续授权清理，应按依赖顺序执行：Attendance、Leave Application、Employee Checkin、Shift Assignment、Shift Type、Leave Type、Employee、User、Department、Holiday List、Company。
- 清理必须另开授权轮次，不应在 M1-R3C 文档收口中顺手执行。

## 状态与下一步

- M1-R3 保持 `BLOCKED`，因为原 M1-R3 不是成功完成。
- M1-R3C 标记为 `COMPLETED`，结论为 `PARTIAL / GAP_IDENTIFIED`。
- M1-R3D 已通过 Codex 审查并收口为 `COMPLETED`，结论为 Gap 四类分类、均不需要立即创建 hb_attendance_app。
- M1-R3E 标记为 `PLANNED`，不得直接启动。
- M1-R4 未启动。

M1-R3D 已聚焦 HRMS 原生考勤异常口径与配置 Gap 诊断，覆盖迟到 / 早退标记、缺卡异常、全天缺勤生成、Leave Allocation 请假前置、加班和节假日出勤报表口径，全部归入 HRMS 配置、原生 / 自定义报表、海滨业务规则定义和未来自定义 App 候选四类。下一步 M1-R3E 建议做配置复核或业务口径确认，仍不得接真实考勤机、不得接真实飞书、不得录入真实生产数据、不得创建自定义 App、不得开发业务代码。
