# M1-R3 HRMS 原生考勤最小测试数据试运行记录

项目名称：新乡海滨智能运营管理平台。

## M1-R3 目标与边界

状态：REVIEWING。

试运行结论：PARTIAL / BLOCKED。

本轮目标是按 `docs/milestones/M1_R2_HRMS原生考勤配置试运行方案.md`，在本地 `frontend` site 中使用 `TEST-HBOS-M1R3-` 前缀的虚构最小测试数据验证 HRMS 原生考勤配置链路。

本轮实际完成：

- 已启动本地 Docker / Frappe / ERPNext / HRMS 运行态。
- 已确认 `frontend` site 可进入 bench / Frappe 上下文。
- 已创建部分虚构 TEST 基础数据。
- 已记录 Company / User / Employee 创建阶段的运行态阻断。
- 已记录 14 个打卡场景的实际验证结果。

本轮未完成：

- 未完成 TEST Company 创建。
- 未完成 TEST User 创建。
- 未完成 TEST Employee 创建。
- 未完成 Shift Type / Shift Assignment / Employee Checkin / Leave Application / Attendance 闭环。
- 未完成 14 个打卡场景的 Auto Attendance 结果验证。

本轮仍严格未做：

- 未创建 `hb_attendance_app`。
- 未创建任何自定义 App。
- 未新增自定义 DocType。
- 未开发考勤业务代码。
- 未接真实考勤机。
- 未接真实飞书。
- 未实现 SSO。
- 未修改 Frappe / ERPNext / HRMS 核心源码。
- 未修改中文化源码。
- 未录入真实员工、真实部门、真实打卡或真实生产数据。

## 本轮读取文件

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
- `docs/milestones/M1_R1_HRMS原生考勤对象模型验证记录.md`

## 实际执行命令

前置检查与环境启动：

```bash
pwd
git rev-parse --show-toplevel
git branch --show-current
git rev-parse HEAD
git status --short
git remote -v
git rev-parse origin/main
git branch -vv
docker compose ps
```

Docker Desktop 未运行时执行：

```bash
open -a Docker
docker info
docker compose ps
```

Frappe / HRMS 元数据读取：

```bash
docker compose exec -T backend bash -lc "cd /home/frappe/frappe-bench && bench --site frontend console"
```

在 bench / Frappe 上下文中读取 `Company`、`Department`、`User`、`Employee`、`Holiday List`、`Shift Type`、`Shift Assignment`、`Employee Checkin`、`Leave Type`、`Leave Application`、`Attendance` 的必填字段、关键字段和是否可提交状态。

因 `bench console` 对长脚本输入不稳定，改用 Frappe Python 上下文执行：

```bash
docker compose exec -T backend bash -lc \
  'mkdir -p /home/frappe/logs /home/frappe/frappe-bench/frontend/logs /home/frappe/frappe-bench/sites/frontend/logs && cd /home/frappe/frappe-bench && ./env/bin/python -'
```

运行态锁与计数确认：

```bash
docker compose exec -T backend bash -lc "cd /home/frappe/frappe-bench && bench --site frontend mariadb -e 'SHOW FULL PROCESSLIST;'"
docker compose exec -T backend bash -lc "cd /home/frappe/frappe-bench && bench --site frontend mariadb -e 'KILL <sleeping_connection_id>;'"
docker compose exec -T backend bash -lc "cd /home/frappe/frappe-bench && bench --site frontend mariadb -e '<TEST object count queries>'"
```

未执行：

- 未执行 `docker compose down -v`。
- 未删除 volume。
- 未重建 `frontend` site。
- 未创建或提交脚本文件。

## 创建的 TEST 数据清单

本轮真实落库的虚构 TEST 数据如下：

| DocType | 数量 | 名称 / 说明 |
| --- | ---: | --- |
| Holiday List | 1 | `TEST-HBOS-M1R3-虚构节假日`，范围 `2026-06-01` 至 `2026-06-30`，包含 `2026-06-28` 虚构节假日 |
| Department | 2 | `TEST-HBOS-M1R3-生产一部 - 健D`、`TEST-HBOS-M1R3-生产二部 - 健D` |
| Leave Type | 1 | `TEST-HBOS-M1R3-虚构事假` |

本轮未能落库的数据如下：

| DocType | 目标 | 实际结果 |
| --- | --- | --- |
| Company | `TEST-HBOS-M1R3-虚构公司` | 标准 ORM 创建在 `tabCompany` insert 阶段触发 lock wait / 长时间阻塞，未创建 |
| User | `TEST-HBOS-M1R3-*` 虚构账号 | 第一个 User 创建长时间阻塞，未创建 |
| Employee | `TEST-HBOS-M1R3-E001` 至 `TEST-HBOS-M1R3-E008` | 起始 Employee 创建长时间阻塞，未创建 |
| Shift Type | 早班 / 中班 / 夜班 / 跨夜班 | 因 Employee 创建未完成，未继续创建 |
| Shift Assignment | 14 场景排班 | 未创建 |
| Employee Checkin | 14 场景虚构打卡 | 未创建 |
| Leave Application | 半天 / 全天虚构请假 | 未创建 |
| Attendance | Auto Attendance 结果 | 未生成 |

最终计数查询结果：

| DocType | TEST 计数 |
| --- | ---: |
| Company | 0 |
| Department | 2 |
| User | 0 |
| Employee | 0 |
| Holiday List | 1 |
| Shift Type | 0 |
| Shift Assignment | 0 |
| Employee Checkin | 0 |
| Leave Type | 1 |
| Leave Application | 0 |
| Attendance | 0 |

## 班次配置结果

计划验证的班次：

- `TEST-HBOS-M1R3-早班-0800-1600`
- `TEST-HBOS-M1R3-中班-1600-0000`
- `TEST-HBOS-M1R3-夜班-0000-0800`
- `TEST-HBOS-M1R3-跨夜班-2000-0400`

实际结果：

- 未完成 Shift Type 创建。
- 未完成早 / 中 / 夜 / 跨夜班配置验证。
- 未完成 `enable_auto_attendance`、IN / OUT 识别策略、迟到早退宽限、跨夜时间窗的运行态验证。

阻断原因：

- Company 标准创建出现 lock wait / 长时间阻塞。
- User / Employee 创建阶段同样出现长时间阻塞。
- 在没有 Employee 和 Shift Type 的前提下，不继续伪造下游 Attendance 结果。

## 14 个打卡场景验证结果

M1-R2 设计的 14 个场景在本轮被转为过去日期区间 `2026-06-22` 至 `2026-06-29`，避免未来 Attendance 日期校验干扰。但由于 Employee / Shift Type / Employee Checkin 未能创建，场景验证未执行完成。

| 场景 | 目标 | 实际结果 | 结论 |
| --- | --- | --- | --- |
| M1R3-AT-001 | 正常早班 | 未生成 Attendance | 未验证 |
| M1R3-AT-002 | 正常中班 | 未生成 Attendance | 未验证 |
| M1R3-AT-003 | 正常夜班 | 未生成 Attendance | 未验证 |
| M1R3-AT-004 | 跨夜班正常上下班 | 未生成 Attendance | 未验证 |
| M1R3-AT-005 | 迟到 | 未生成 Attendance | 未验证 |
| M1R3-AT-006 | 早退 | 未生成 Attendance | 未验证 |
| M1R3-AT-007 | 上班缺卡 | 未生成 Attendance | 未验证 |
| M1R3-AT-008 | 下班缺卡 | 未生成 Attendance | 未验证 |
| M1R3-AT-009 | 全天缺勤 | 未生成 Attendance | 未验证 |
| M1R3-AT-010 | 半天请假 | 未生成 Attendance | 未验证 |
| M1R3-AT-011 | 全天请假 | 未生成 Attendance | 未验证 |
| M1R3-AT-012 | 加班候选 | 未生成 Attendance | 未验证 |
| M1R3-AT-013 | 节假日出勤 | 未生成 Attendance | 未验证 |
| M1R3-AT-014 | 临时调班 | 未生成 Attendance | 未验证 |

## 考勤能力结论

本轮不能把 HRMS 原生考勤链路判定为通过。

已确认：

- 本地 `frontend` site 中 HRMS DocType 元数据可读。
- `Holiday List`、`Department`、`Leave Type` 可创建虚构 TEST 数据。
- 运行态可以通过 bench / Frappe 上下文和 MariaDB 只读查询验证对象计数。

未确认：

- 早班、中班、夜班、跨夜班是否按 M1-R2 设计生成正确 Attendance。
- 迟到、早退、缺卡、请假、加班、节假日、调班场景是否被 HRMS 原生能力覆盖。
- Auto Attendance 在当前 site 的跨夜归属、缺卡表现、请假联动和节假日出勤口径。
- 原生报表是否满足 M1 初期月度汇总口径。

Gap：

- 当前运行态存在标准 ORM 写入长时间阻塞 / lock wait 问题，需要先处理。
- TEST Company 创建未完成，说明 Company 新建在当前 site 上不是本轮可依赖路径。
- TEST User / Employee 创建未完成，导致 HRMS 原生考勤链路无法进入 Shift / Checkin / Attendance 阶段。
- 账号体系验证仍需承接 M1-R0：飞书登录为主，HBOS User 自动映射 Employee；但本轮未创建真实 User，不影响该架构结论。

## 是否建议创建 hb_attendance_app

当前仍不建议创建 `hb_attendance_app`。

原因：

- 本轮阻断点是运行态写入 / 数据库连接或锁问题，不是 HRMS 原生对象模型已被证明无法覆盖海滨考勤。
- M1-R1 和 M1-R2 的结论仍成立：M1 初期应优先复用 HRMS 原生能力。
- 在完成 Employee / Shift Type / Employee Checkin / Auto Attendance 的真实闭环前，不能因为本轮运行态阻断而提前创建自定义 App。

## 测试数据清理与隔离建议

当前已落库 TEST 数据数量很少，建议暂时保留到 M1-R3 审查完成，便于复核：

- `TEST-HBOS-M1R3-虚构节假日`
- `TEST-HBOS-M1R3-生产一部 - 健D`
- `TEST-HBOS-M1R3-生产二部 - 健D`
- `TEST-HBOS-M1R3-虚构事假`

后续清理建议：

1. 审查确认不再需要后，再由用户授权清理 TEST 数据。
2. 清理顺序应从下游到上游：Attendance、Leave Application、Employee Checkin、Shift Assignment、Shift Type、Employee、User、Leave Type、Department、Holiday List、Company。
3. 本轮不执行清理，避免在写入阻断尚未定位前扩大数据库操作。

## 下一步建议

M1-R3 当前交付进入 REVIEWING，建议先交给 Codex 审查本记录。

审查通过后，不建议直接进入 M1-R4。应先由用户决定是否补做一个 M1-R3-FIX 或 M1-R3-RETRY：

- 先定位并解除当前 site 的 ORM 写入 / lock wait 问题。
- 再重新执行 Employee、Shift Type、Shift Assignment、Employee Checkin、Leave Application、Auto Attendance 的最小闭环。
- 仍不得接真实考勤机。
- 仍不得接真实飞书。
- 仍不得录入真实员工、真实打卡或真实生产数据。
- 仍不得创建自定义 App 或开发业务代码。

M1-R4 保持 PLANNED，只有 M1-R3 的真实 14 场景闭环完成并通过审查后，才建议进入。
