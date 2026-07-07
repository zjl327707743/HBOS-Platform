# M1-R3A 运行态阻断诊断与 TEST 数据隔离清理方案

项目名称：新乡海滨智能运营管理平台。

## M1-R3A 目标与边界

状态：COMPLETED。

收口记录：M1-R3A 已通过 Codex 审查，审查结果为 PASS。本次 M1-R3A-CLOSEOUT 仅做状态收口，不修复运行态，不清理或删除 TEST 数据，不继续创建测试数据。

本轮目标是诊断 M1-R3 的运行态阻断原因，并形成 `TEST-HBOS-M1R3-*` 虚构测试数据的隔离与清理方案。

本轮只做诊断和文档记录：

- 不继续创建测试数据。
- 不继续执行 HRMS 配置试运行。
- 不清理或删除 TEST 数据。
- 不修改数据库结构。
- 不创建自定义 App。
- 不创建 `hb_attendance_app`。
- 不新增 DocType。
- 不开发考勤业务代码。
- 不接飞书、SSO 或真实考勤机。
- 不修改 Frappe / ERPNext / HRMS 核心源码。
- 不提交 `.env`、备份、密钥、数据库、日志、缓存或运行时产物。

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
- `docs/milestones/M1_R3_HRMS原生考勤最小测试数据试运行记录.md`
- `docker-compose.yml`
- `.env.example`

说明：`docker-compose.yml` 与 `.env.example` 仅用于确认服务名称和 Redis 连接变量；本轮未读取、修改或提交真实 `.env`。

## 诊断命令清单

前置 Git 与仓库状态：

```bash
pwd
git branch --show-current
git rev-parse HEAD
git status --short
git remote -v
git rev-parse origin/main
git branch -vv
```

Docker / Frappe / HRMS 运行态：

```bash
docker compose ps
docker compose ps -a
docker inspect hbos-m0-r3a-redis-cache-1 hbos-m0-r3a-redis-queue-1 --format '{{.Name}} status={{.State.Status}} exit={{.State.ExitCode}} started={{.State.StartedAt}} finished={{.State.FinishedAt}} oom={{.State.OOMKilled}} error={{.State.Error}}'
docker compose logs --tail=80 redis-cache redis-queue
docker compose logs --tail=80 queue-short queue-long websocket
docker compose exec -T backend bash -lc "cd /home/frappe/frappe-bench && bench version"
docker compose exec -T backend bash -lc "cd /home/frappe/frappe-bench && bench --site frontend list-apps"
timeout 25s docker compose exec -T backend bash -lc "cd /home/frappe/frappe-bench && bench --site frontend doctor" || echo bench_doctor_timeout_or_failed
curl -s -o /dev/null -w 'login_http_code=%{http_code}\n' http://localhost:8081/login
docker compose config --services
```

MariaDB 只读诊断：

```bash
docker compose exec -T backend bash -lc "cd /home/frappe/frappe-bench && bench --site frontend mariadb -e 'SHOW FULL PROCESSLIST; SHOW OPEN TABLES WHERE In_use > 0;'"
docker compose exec -T backend bash -lc "cd /home/frappe/frappe-bench && bench --site frontend mariadb -e 'SHOW ENGINE INNODB STATUS\\G'"
```

TEST 数据范围与依赖查询：

```bash
docker compose exec -T backend bash -lc "cd /home/frappe/frappe-bench && bench --site frontend mariadb -e '<TEST-HBOS-M1R3 count and dependency queries>'"
docker compose exec -T backend bash -lc "cd /home/frappe/frappe-bench && bench --site frontend mariadb -e '<Shift Assignment and Employee Checkin detail queries>'"
```

## 当前运行态状态

Frappe / ERPNext / HRMS 版本仍可从 backend 容器读取：

| App | 版本 |
| --- | --- |
| Frappe | `16.25.0` |
| ERPNext | `16.26.2` |
| HRMS | `16.12.0 version-16 (666bf10)` |

Docker 容器状态诊断结论：

- `backend`、`db`、`frontend`、`scheduler` 处于运行状态。
- `redis-cache` 与 `redis-queue` 已退出，退出码为 `0`。
- Redis 日志显示收到 `SIGTERM` 后正常关闭，未显示 OOM 或 Redis 自身崩溃错误。
- `queue-short`、`queue-long` 处于反复重启状态。
- `websocket` 处于反复重启状态。

运行态错误特征：

- `queue-short`、`queue-long` 日志出现 `redis.exceptions.ConnectionError: Connection closed by server`。
- `websocket` 日志出现 `SocketClosedUnexpectedlyError: Socket closed unexpectedly`。
- `bench --site frontend doctor` 因 Redis Queue 连接失败退出。
- `bench --site frontend list-apps` 在本轮诊断中长时间无返回，已中断，记录为运行态异常症状。
- `http://localhost:8081/login` 本轮 `curl` 检查长时间无返回，已中断，记录为 Desk / web 请求路径异常症状。

MariaDB 只读诊断结论：

- `SHOW FULL PROCESSLIST` 可执行，能看到站点连接中存在较长时间 `Sleep` 连接。
- 可见进程列表中未观察到正在执行的阻塞 SQL。
- `SHOW ENGINE INNODB STATUS\G` 因当前数据库账号缺少 `PROCESS` 权限失败，错误为需要 `PROCESS` privilege。
- 因缺少 InnoDB 事务 / 锁详情权限，本轮不能最终排除未提交事务、行锁或元数据锁。

## TEST 数据计数与依赖关系

本轮只读查询确认，`TEST-HBOS-M1R3-*` 或 M1-R3 虚构员工相关数据范围如下：

| DocType | 数量 | 说明 |
| --- | ---: | --- |
| Company | 0 | `TEST-HBOS-M1R3-虚构公司` 未创建成功 |
| Department | 2 | `TEST-HBOS-M1R3-生产一部 - 健D`、`TEST-HBOS-M1R3-生产二部 - 健D` |
| User | 0 | 未创建 TEST User |
| Employee | 8 | `HR-EMP-00001` 至 `HR-EMP-00008`，员工名为 `M1R3虚构员工E001` 至 `M1R3虚构员工E008` |
| Holiday List | 1 | `TEST-HBOS-M1R3-虚构节假日` |
| Holiday child row | 1 | `2026-06-28`，weekly off |
| Shift Type | 4 | 早班、中班、夜班、跨夜班 |
| Shift Assignment | 6 | 均为已提交记录，`docstatus = 1` |
| Employee Checkin | 12 | 覆盖早班、中班、夜班、跨夜班的部分 IN / OUT 记录 |
| Leave Type | 1 | `TEST-HBOS-M1R3-虚构事假` |
| Leave Application | 0 | 未创建 |
| Attendance | 0 | 未生成 |

已确认的依赖关系：

- 8 个 Employee 引用了 TEST Department。
- 8 个 Employee 引用了 TEST Holiday List。
- 4 个 Shift Type 引用了 TEST Holiday List。
- 6 个 Shift Assignment 引用了 TEST Employee 与 TEST Shift Type，且均已提交。
- 12 个 Employee Checkin 引用了 TEST Employee 与 TEST Shift Type。
- Leave Application 为 0，因此当前没有请假申请引用 TEST Leave Type。
- Attendance 为 0，因此当前没有考勤结果引用 TEST Employee。

## 关键 TEST 数据明细

Shift Assignment：

| Name | Employee | Shift Type | Start Date | End Date | Docstatus |
| --- | --- | --- | --- | --- | ---: |
| `HR-SHA-26-07-00001` | `HR-EMP-00001` | `TEST-HBOS-M1R3-早班-0800-1600` | `2026-06-22` | `2026-06-22` | 1 |
| `HR-SHA-26-07-00005` | `HR-EMP-00001` | `TEST-HBOS-M1R3-早班-0800-1600` | `2026-06-24` | `2026-06-24` | 1 |
| `HR-SHA-26-07-00002` | `HR-EMP-00002` | `TEST-HBOS-M1R3-中班-1600-0000` | `2026-06-22` | `2026-06-22` | 1 |
| `HR-SHA-26-07-00006` | `HR-EMP-00002` | `TEST-HBOS-M1R3-中班-1600-0000` | `2026-06-24` | `2026-06-24` | 1 |
| `HR-SHA-26-07-00003` | `HR-EMP-00003` | `TEST-HBOS-M1R3-夜班-0000-0800` | `2026-06-23` | `2026-06-23` | 1 |
| `HR-SHA-26-07-00004` | `HR-EMP-00004` | `TEST-HBOS-M1R3-跨夜班-2000-0400` | `2026-06-23` | `2026-06-23` | 1 |

Employee Checkin：

| Name | Employee | Time | Log Type | Shift |
| --- | --- | --- | --- | --- |
| `EMP-CKIN-07-2026-000001` | `HR-EMP-00001` | `2026-06-22 07:55:00` | IN | `TEST-HBOS-M1R3-早班-0800-1600` |
| `EMP-CKIN-07-2026-000002` | `HR-EMP-00001` | `2026-06-22 16:03:00` | OUT | `TEST-HBOS-M1R3-早班-0800-1600` |
| `EMP-CKIN-07-2026-000003` | `HR-EMP-00002` | `2026-06-22 15:55:00` | IN | `TEST-HBOS-M1R3-中班-1600-0000` |
| `EMP-CKIN-07-2026-000004` | `HR-EMP-00002` | `2026-06-23 00:02:00` | OUT | `TEST-HBOS-M1R3-中班-1600-0000` |
| `EMP-CKIN-07-2026-000005` | `HR-EMP-00003` | `2026-06-22 23:55:00` | IN | `TEST-HBOS-M1R3-夜班-0000-0800` |
| `EMP-CKIN-07-2026-000006` | `HR-EMP-00003` | `2026-06-23 08:01:00` | OUT | `TEST-HBOS-M1R3-夜班-0000-0800` |
| `EMP-CKIN-07-2026-000007` | `HR-EMP-00004` | `2026-06-23 19:55:00` | IN | `TEST-HBOS-M1R3-跨夜班-2000-0400` |
| `EMP-CKIN-07-2026-000008` | `HR-EMP-00004` | `2026-06-24 04:05:00` | OUT | `TEST-HBOS-M1R3-跨夜班-2000-0400` |
| `EMP-CKIN-07-2026-000009` | `HR-EMP-00001` | `2026-06-24 08:12:00` | IN | `TEST-HBOS-M1R3-早班-0800-1600` |
| `EMP-CKIN-07-2026-000010` | `HR-EMP-00001` | `2026-06-24 16:02:00` | OUT | `TEST-HBOS-M1R3-早班-0800-1600` |
| `EMP-CKIN-07-2026-000011` | `HR-EMP-00002` | `2026-06-24 15:58:00` | IN | `TEST-HBOS-M1R3-中班-1600-0000` |
| `EMP-CKIN-07-2026-000012` | `HR-EMP-00002` | `2026-06-24 23:40:00` | OUT | `TEST-HBOS-M1R3-中班-1600-0000` |

## 阻断原因判断

Company 创建阻断：

- M1-R3 中 `TEST-HBOS-M1R3-虚构公司` 标准 ORM 创建在 `tabCompany` insert 阶段发生 lock wait / 长时间阻塞。
- 本轮可见 MariaDB 进程列表没有捕获到活动阻塞 SQL，但存在较长时间 Sleep 连接。
- 因缺少 `PROCESS` 权限，未能读取 InnoDB 事务和锁等待详情。
- 当前判断：Company 创建阻断更像运行态数据库连接 / 事务 / 锁等待问题，不是 HRMS 原生对象模型缺失。

User 创建阻断：

- TEST User 计数为 0。
- M1-R3 中 User 创建链路曾发生长时间阻塞。
- Redis Queue 与 Redis Cache 当前已退出，queue worker 和 websocket 重启，说明后台任务、通知、缓存和请求路径不健康。
- 当前判断：User 创建阻断可能与整体运行态不健康、后台队列 / Redis 不可用、数据库连接状态异常共同相关；本轮不做写入复测，因此不把原因定死为字段缺失或权限配置错误。

Employee 创建链路：

- 本轮只读查询确认 Employee 已有 8 条虚构记录，且均未绑定 User。
- 这说明 M1-R3 的部分 Employee 写入最终已经落库，但 User 与 Employee 绑定链路没有完成。
- Employee、Shift Type、Shift Assignment、Employee Checkin 已部分落库，而 Attendance 为 0，说明链路停在 Auto Attendance 结果生成之前。
- 当前判断：Employee 本体不是完全无法创建；真正阻断是运行态不稳定导致链路不完整，以及 Auto Attendance 所需后台队列不可用。

后台与 scheduler：

- scheduler 容器仍运行，但 Redis 队列服务退出后，后台任务链路不可用。
- `bench doctor` 因 Redis Queue 连接失败无法完成。
- Auto Attendance 依赖的后台执行与队列健康度需要在 M1-R3B 先恢复再判断。

权限 / 必填字段 / HRMS 依赖配置：

- 本轮确认 `Gender Other`、`Currency CNY`、`Country China`、`Employee`、`HR Manager`、`HR User` 等基础对象或角色存在。
- 未发现可直接证明阻断来自缺少基础主数据或必填字段的只读证据。
- 仍需在运行态恢复后，通过受控写入或错误日志复核字段级校验。

## 最小修复建议

以下建议仅作为 M1-R3B 候选动作，必须获得用户授权后执行：

1. 先恢复 Redis 运行态，不使用 `docker compose down -v`，不删除 volume，不重建 `frontend` site。
2. 使用非破坏性方式启动或重启 `redis-cache`、`redis-queue` 及依赖的 queue / websocket 服务。
3. 恢复后重新执行 `docker compose ps`、`bench --site frontend doctor`、`bench --site frontend list-apps` 和 `curl http://localhost:8081/login`。
4. 若仍存在数据库阻塞，使用具备足够权限的数据库账号读取 InnoDB 事务和锁等待信息。
5. 在运行态健康前，不继续创建 TEST 数据，不触发 Auto Attendance，不清理已有 TEST 数据。
6. 运行态恢复后，先决定清理 TEST 数据还是继续补齐试运行，避免在半残留数据上叠加新数据。

## TEST 数据隔离与清理顺序建议

清理必须由用户明确授权后执行。本轮不清理。

建议清理前先导出或记录当前 TEST 数据清单，保证可追溯。清理顺序应从下游到上游：

1. `Attendance`：当前 0。
2. `Leave Application`：当前 0。
3. `Employee Checkin`：当前 12。
4. `Shift Assignment`：当前 6，均为 `docstatus = 1`，应先 cancel 再 delete。
5. `Shift Type`：当前 4。
6. `Employee`：当前 8。
7. `User`：当前 0。
8. `Leave Type`：当前 1。
9. `Department`：当前 2。
10. `Holiday List` 子表记录与 `Holiday List`：当前 1 个 Holiday List、1 条 Holiday。
11. `Company`：当前 0。

隔离建议：

- 在清理或继续试运行前，所有后续查询都应继续使用 `TEST-HBOS-M1R3-` 前缀、`M1R3虚构员工` 员工名和 `TEST-HBOS-M1R3-*` attendance device id 作为边界。
- 不混用真实员工、真实部门、真实打卡或真实生产数据。
- 不在未清理或未确认依赖前重复创建同名前缀数据。
- 对已提交的 Shift Assignment，必须按 Frappe / HRMS 文档状态规则先取消再删除。

## 是否需要用户授权后清理

需要。

原因：

- 当前已有 8 个 Employee、6 个已提交 Shift Assignment、12 条 Employee Checkin 等下游数据。
- 清理涉及提交单据取消、依赖顺序和可能的后台状态影响。
- 清理动作属于数据库写入，不在 M1-R3A 的只读诊断范围内。

## 是否建议创建 hb_attendance_app

当前仍不建议创建 `hb_attendance_app`。

原因：

- 本轮阻断点集中在 Redis / queue / websocket / site 请求路径和数据库锁诊断能力，不是 HRMS 原生考勤模型已被证明无法覆盖。
- M1-R1 和 M1-R2 结论仍成立：M1 初期主路线是优先复用 HRMS 原生考勤能力。
- M1-R3 的失败不能作为提前重写 HRMS 考勤能力的依据。

## 下一步建议

M1-R3A 已通过 Codex 审查并收口为 COMPLETED。

下一步已进入 M1-R3B：运行态最小修复方案，状态为 REVIEWING；本轮只写方案，不执行修复、不清理 TEST 数据。

M1-R3B 方案建议后续只在授权后选择其一：

- 先恢复 Redis / queue / websocket / site 运行态，再判断是否继续 M1-R3 试运行。
- 或按本文档顺序清理已有 TEST 数据，恢复干净边界后再决定是否重跑。

M1-R4 不启动。不得在 M1-R3A 或未授权的 M1-R3B 中接真实考勤机、接真实飞书、实现 SSO、录入真实业务数据、创建自定义 App 或开发业务代码。
