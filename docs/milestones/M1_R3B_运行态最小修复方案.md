# M1-R3B 运行态最小修复方案

项目名称：新乡海滨智能运营管理平台。

## M1-R3B 目标与边界

状态：COMPLETED。

收口记录：M1-R3B 已通过 Codex 审查，审查结果为 PASS，并已收口为 COMPLETED。后续 M1-R3B-FIX 已按本方案执行运行态最小修复，并已通过 Codex 审查收口为 COMPLETED；M1-R3C 已在用户授权下执行 HRMS 原生考勤最小试运行复测，并已通过 Codex 审查收口为 COMPLETED，结论为 PARTIAL / GAP_IDENTIFIED。

本轮目标是基于 M1-R3A 诊断结论，制定用于解除 M1-R3 运行态阻断的最小修复方案。方案覆盖 Redis、worker、scheduler、`bench doctor`、Desk login、Company / User / Employee 创建阻断复测，以及 TEST 数据隔离边界。

本轮只写方案，不执行修复：

- 不启动、重启或修复任何服务。
- 不清理、删除或修改 TEST 数据。
- 不继续创建测试数据。
- 不执行 HRMS 配置试运行。
- 不修改数据库结构。
- 不创建自定义 App。
- 不创建 `hb_attendance_app`。
- 不新增 DocType。
- 不新增业务代码或脚本文件。
- 不接飞书、SSO 或真实考勤机。
- 不提交 `.env`、备份、密钥、数据库、日志、缓存或运行时产物。

## 依据文件

- `docs/milestones/M1_R3A_运行态阻断诊断与TEST数据隔离清理方案.md`
- `docs/milestones/M1_R3_HRMS原生考勤最小测试数据试运行记录.md`

## 当前阻断摘要

M1-R3 的实际结论仍为 PARTIAL / BLOCKED。M1-R3A 已通过 Codex 审查并收口为 COMPLETED，确认阻断重点不是 HRMS 原生对象模型已失败，而是当前本地运行态不健康。

已确认的运行态异常：

- `redis-cache` 与 `redis-queue` 容器已退出，退出码为 `0`。
- Redis 日志显示收到 `SIGTERM` 后正常关闭，未显示 OOM 或 Redis 自身崩溃。
- `queue-short`、`queue-long` 反复重启。
- `websocket` 反复重启。
- `bench --site frontend doctor` 因 Redis Queue 连接失败无法完成。
- `bench --site frontend list-apps` 在 M1-R3A 诊断中长时间无返回。
- `http://localhost:8081/login` 在 M1-R3A 诊断中长时间无返回。
- MariaDB 可见进程列表未捕获活动阻塞 SQL，但当前账号缺少 `PROCESS` 权限，无法读取 InnoDB 事务和锁等待详情。

业务链路阻断现象：

- `TEST-HBOS-M1R3-虚构公司` 标准 ORM 创建在 `tabCompany` insert 阶段出现 lock wait / 长时间阻塞。
- TEST User 创建长时间阻塞，当前 TEST User 数量为 0。
- Employee 本体已有部分落库，但均未绑定 User。
- Auto Attendance 结果未生成，Attendance 数量为 0，14 个场景未完成闭环。

## 已落库 TEST 数据范围

当前必须把以下数据视为 M1-R3 残留 TEST 数据，后续修复、复测和清理都必须隔离处理：

| DocType | 数量 | 说明 |
| --- | ---: | --- |
| Company | 0 | `TEST-HBOS-M1R3-虚构公司` 未创建成功 |
| Department | 2 | `TEST-HBOS-M1R3-生产一部 - 健D`、`TEST-HBOS-M1R3-生产二部 - 健D` |
| User | 0 | TEST User 未创建成功 |
| Employee | 8 | `HR-EMP-00001` 至 `HR-EMP-00008`，员工名为 `M1R3虚构员工E001` 至 `M1R3虚构员工E008` |
| Holiday List | 1 | `TEST-HBOS-M1R3-虚构节假日` |
| Holiday child row | 1 | `2026-06-28`，weekly off |
| Shift Type | 4 | 早班、中班、夜班、跨夜班 |
| Shift Assignment | 6 | 均为已提交记录，`docstatus = 1` |
| Employee Checkin | 12 | 覆盖早班、中班、夜班、跨夜班的部分 IN / OUT 记录 |
| Leave Type | 1 | `TEST-HBOS-M1R3-虚构事假` |
| Leave Application | 0 | 未创建 |
| Attendance | 0 | 未生成 |

## 最小修复目标

M1-R3B 后续若获得执行授权，最小修复目标应限制在恢复本地运行态健康，而不是重做考勤方案或开发新能力：

1. 恢复 Redis cache / queue 服务可用。
2. 恢复 queue worker 与 websocket 稳定运行。
3. 确认 scheduler 与后台任务链路可诊断。
4. 让 `bench --site frontend doctor` 可以完成或给出非 Redis 连接类错误。
5. 让 `bench --site frontend list-apps` 可以在合理时间内返回。
6. 让 `http://localhost:8081/login` 可以返回明确 HTTP 状态。
7. 明确 Company / User / Employee 创建阻断是否仍存在。
8. 在不清理现有 TEST 数据的前提下，判断是否具备进入 M1-R3C 重新试运行的条件。

非目标：

- 不修复业务规则。
- 不创建自定义 App。
- 不创建 `hb_attendance_app`。
- 不通过自定义代码绕过 HRMS 原生逻辑。
- 不连接真实考勤机、飞书或 SSO。
- 不录入真实员工、真实打卡或真实生产数据。

## 修复前备份与保护原则

M1-R3B 后续若进入执行，必须先执行保护性检查，再做任何服务级操作。

保护原则：

- 不执行 `docker compose down -v`。
- 不删除 Docker volume。
- 不重建 `frontend` site。
- 不重新初始化 ERPNext / HRMS。
- 不提交真实 `.env`。
- 不提交数据库、备份、日志、缓存或运行时产物。
- 不在未确认当前 TEST 数据范围前继续创建同名前缀数据。
- 不在未确认运行态健康前触发 Auto Attendance 或继续 HRMS 试运行。

修复前建议只读确认：

```bash
pwd
git branch --show-current
git rev-parse HEAD
git status --short
git remote -v
docker compose ps
docker compose ps -a
docker compose config --services
```

如用户要求备份，应优先明确备份路径、是否允许生成数据库 dump、是否允许保存到 Git 外目录；备份文件不得提交 Git。

## Redis 修复步骤草案

后续授权执行时，Redis 只做最小恢复，不做 volume 删除和重建：

1. 只读查看 Redis 服务状态：

```bash
docker compose ps redis-cache redis-queue
docker compose ps -a redis-cache redis-queue
docker compose logs --tail=120 redis-cache redis-queue
docker inspect hbos-m0-r3a-redis-cache-1 hbos-m0-r3a-redis-queue-1 --format '{{.Name}} status={{.State.Status}} exit={{.State.ExitCode}} oom={{.State.OOMKilled}} error={{.State.Error}}'
```

2. 若仍为 exited 且用户授权，可仅启动 Redis 服务：

```bash
docker compose up -d redis-cache redis-queue
```

3. 启动后确认：

```bash
docker compose ps redis-cache redis-queue
docker compose logs --tail=80 redis-cache redis-queue
```

成功标准：

- `redis-cache`、`redis-queue` 均为 running / healthy 或至少持续运行。
- 日志不再出现立即退出。
- 不执行 volume 删除，不重建 site。

## Worker / websocket 修复步骤草案

Redis 恢复后，再处理依赖 Redis 的 worker 与 websocket。

1. 只读确认重启状态和错误：

```bash
docker compose ps queue-short queue-long websocket
docker compose logs --tail=120 queue-short queue-long websocket
```

2. 若 worker / websocket 仍异常，用户授权后可最小重启依赖服务：

```bash
docker compose restart queue-short queue-long websocket
```

3. 复核：

```bash
docker compose ps queue-short queue-long websocket
docker compose logs --tail=120 queue-short queue-long websocket
```

成功标准：

- `queue-short`、`queue-long` 不再反复重启。
- `websocket` 不再反复重启。
- 日志不再持续出现 `redis.exceptions.ConnectionError: Connection closed by server` 或 `SocketClosedUnexpectedlyError`。

## Scheduler 诊断步骤草案

scheduler 在 M1-R3A 中仍显示运行，但 Redis 队列异常会影响后台链路判断。后续授权执行时，scheduler 只做诊断和必要的最小重启。

1. 只读确认：

```bash
docker compose ps scheduler
docker compose logs --tail=120 scheduler
```

2. Redis / worker 正常后再执行 Frappe 级诊断：

```bash
docker compose exec -T backend bash -lc "cd /home/frappe/frappe-bench && bench --site frontend doctor"
```

3. 如 scheduler 仍异常且用户授权，才考虑：

```bash
docker compose restart scheduler
```

成功标准：

- scheduler 不反复退出。
- `bench doctor` 不再因 Redis Queue 连接失败中断。
- 后续 Auto Attendance 可被诊断，但本步骤不触发试运行。

## bench doctor / list-apps / login 复核步骤草案

Redis、worker、websocket、scheduler 基本恢复后，按从低风险到用户入口的顺序复核：

```bash
docker compose exec -T backend bash -lc "cd /home/frappe/frappe-bench && bench version"
docker compose exec -T backend bash -lc "cd /home/frappe/frappe-bench && bench --site frontend list-apps"
docker compose exec -T backend bash -lc "cd /home/frappe/frappe-bench && bench --site frontend doctor"
curl -s -o /dev/null -w 'login_http_code=%{http_code}\n' http://localhost:8081/login
```

成功标准：

- `bench version` 返回 Frappe / ERPNext / HRMS 版本。
- `bench --site frontend list-apps` 在合理时间内返回 `frappe`、`erpnext`、`hrms`。
- `bench doctor` 可以完成或暴露新的非 Redis 阻断。
- `/login` 返回明确 HTTP 状态，理想状态为 `200` 或可解释的重定向 / 登录响应。

## Company / User / Employee 创建阻断复测路径

本轮不复测写入。后续授权执行时，必须先完成运行态恢复，再判断是否复测创建链路。

复测原则：

- 不使用真实员工、真实部门或真实公司数据。
- 不复用可能导致唯一键冲突的旧测试名称。
- 不在未确认 TEST 数据隔离前继续创建下游考勤数据。
- 优先做最小、可回滚、单对象复测，而不是直接恢复 14 场景试运行。

建议复测顺序：

1. 只读确认现有 TEST 数据范围仍与 M1-R3A 一致。
2. 只读确认 MariaDB processlist、open tables 和必要权限。
3. 若可获得具备权限的数据库账号，读取 InnoDB 锁等待 / 事务状态。
4. 先尝试最小 Company 创建复测，使用新的 M1-R3B 或 M1-R3C 前缀，避免与旧数据混淆。
5. Company 创建成功后，再尝试最小 User 创建复测。
6. User 创建成功后，再验证 Employee 与 User 绑定链路。
7. 任一复测出现阻塞，应停止下游操作，记录错误，不继续创建 Shift / Checkin / Attendance。

建议命名边界：

- M1-R3B 若仅做修复复测，使用 `TEST-HBOS-M1R3B-*`。
- M1-R3C 若进入重新试运行，使用 `TEST-HBOS-M1R3C-*` 或在清理旧数据后由用户确认是否复用 `TEST-HBOS-M1R3-*`。

## TEST 数据隔离策略

M1-R3B 不清理现有 TEST 数据，必须先隔离：

- 继续把 `TEST-HBOS-M1R3-*`、`M1R3虚构员工*`、`TEST-HBOS-M1R3-*` attendance device id 视为旧试运行数据。
- 修复验证不得修改旧 TEST Employee、Shift Type、Shift Assignment、Employee Checkin。
- 旧 Shift Assignment 已提交，禁止直接删除。
- 旧 Employee Checkin 不用于判断新复测是否成功。
- 新复测若获得授权，应使用新前缀，避免与旧残留混合。
- 所有复测结果都必须记录到后续文档，不提交数据库或导出文件。

## 不清理 TEST 数据的理由

本轮不清理 TEST 数据，原因如下：

- M1-R3A 已确认存在 8 个 Employee、4 个 Shift Type、6 个 Shift Assignment、12 条 Employee Checkin，且 6 条 Shift Assignment 为已提交记录。
- 清理需要取消提交单据并按依赖顺序删除，属于数据库写入操作。
- 当前 Redis / queue / scheduler / Desk 运行态不健康，清理动作可能因后台链路异常扩大风险。
- TEST 数据仍可用于复核阻断现场和清理方案正确性。
- 用户本轮明确要求只写方案，不执行清理。

后续若用户授权清理，应沿用 M1-R3A 的顺序：Attendance、Leave Application、Employee Checkin、Shift Assignment、Shift Type、Employee、User、Leave Type、Department、Holiday List、Company。

## M1-R3C 进入条件

只有同时满足以下条件，才建议进入 M1-R3C 重新试运行：

1. Redis cache / queue 均稳定运行。
2. queue worker 与 websocket 不再反复重启。
3. scheduler 状态可诊断，`bench doctor` 不再因 Redis Queue 连接失败中断。
4. `bench --site frontend list-apps` 能稳定返回 Frappe / ERPNext / HRMS。
5. `http://localhost:8081/login` 能返回明确可接受的 HTTP 状态。
6. Company / User / Employee 最小创建或绑定复测路径已明确，不再出现长时间阻塞。
7. 旧 `TEST-HBOS-M1R3-*` 数据已被隔离，或用户授权清理后确认清理完成。
8. 用户明确授权 M1-R3C 继续使用虚构 TEST 数据重新试运行。

M1-R3C 仍不得接真实考勤机、不得接真实飞书、不得实现 SSO、不得录入真实员工或真实考勤数据、不得创建自定义 App、不得开发业务代码。

## 是否建议创建 hb_attendance_app

当前仍不建议创建 `hb_attendance_app`。

原因：

- 当前阻断仍集中在 Redis / worker / websocket / scheduler / bench doctor / login 和数据库锁诊断路径。
- M1-R3 未能完成不是因为 HRMS 原生考勤模型已被证明不可覆盖。
- M1-R1、M1-R2、M1-R3A 的结论仍成立：M1 初期优先复用 HRMS 原生能力。
- 在完成运行态修复和 M1-R3C 重新试运行前，不应提前创建自定义 App。

## 下一步建议

M1-R3B 已通过 Codex 审查并收口为 COMPLETED。

M1-R3B-FIX 已按本方案执行运行态最小修复，并已通过 Codex 审查收口为 COMPLETED。执行记录见 `docs/milestones/M1_R3B_FIX_运行态最小修复执行记录.md`。

下一步由用户决定：

- 授权进入 M1-R3C：继续 HRMS 原生考勤虚构 TEST 数据重新试运行。
- 或授权 M1-R3B-CLEANUP：按 M1-R3A 清理顺序隔离 / 清理 TEST 数据。
- 或暂缓后续试运行，继续保持 M1-R3 BLOCKED。

M1-R3C 已在用户授权后进入并完成复测交付，当前状态为 COMPLETED。后续由用户决定是否进入 M1-R3D。
