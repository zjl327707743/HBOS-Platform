# M1-R3B-FIX 运行态最小修复执行记录

项目名称：新乡海滨智能运营管理平台。

## 目标与边界

状态：COMPLETED。

收口记录：M1-R3B-FIX 已通过 Codex 审查，审查结果为 PASS。本次 M1-R3B-FIX-CLOSEOUT 仅做状态收口，将 M1-R3B-FIX 从 REVIEWING 改为 COMPLETED；未继续试运行，未创建、删除或清理 TEST 数据，未再启动或重启服务，未创建 App / DocType / 代码。

本轮目标是按 `docs/milestones/M1_R3B_运行态最小修复方案.md` 执行最小运行态修复，使本地 `frontend` site 的 Redis、worker、scheduler、`bench doctor` 和 `/login` 恢复到可继续判断 M1-R3C 的状态。

本轮不是 M1-R3C，不执行 HRMS 考勤重新试运行，不继续创建 TEST 数据，不清理或删除 TEST 数据，不创建 App / DocType / 代码，不接真实考勤机、真实飞书或 SSO。

M1-R3 仍为 BLOCKED。M1-R3B-FIX 已收口为 COMPLETED。M1-R3C 仍为 PLANNED，尚未启动，用户尚未授权进入 M1-R3C。

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
- `docs/milestones/M1_R3B_运行态最小修复方案.md`
- `docs/milestones/M1_R3A_运行态阻断诊断与TEST数据隔离清理方案.md`
- `docs/milestones/M1_R3_HRMS原生考勤最小测试数据试运行记录.md`

## 前置检查

- 工作目录：`/Users/zhaojiale/VS Projects/HBOS`。
- 分支：`main`。
- 基线 HEAD：`ea1d768beec114f6f1145e7904769d15414760a6`。
- 本地 `main` 与 `origin/main` 一致。
- 本轮开始前 `git status --short` clean。

## 执行命令与结果

### 基线 Git 检查

```bash
pwd
git branch --show-current
git rev-parse HEAD
git status --short
git rev-parse origin/main
git branch -vv
git remote -v
```

结果：目录、分支、HEAD 和远端符合基线；工作区 clean；`origin` 指向 `https://github.com/zjl327707743/HBOS.git`。

### 运行态检查

```bash
docker compose ps
docker compose ps -a
docker compose config --services
docker inspect hbos-m0-r3a-redis-cache-1 hbos-m0-r3a-redis-queue-1
docker compose logs --tail=80 redis-cache redis-queue
docker compose logs --tail=100 queue-short queue-long websocket
```

修复前结果：

- `redis-cache` 和 `redis-queue` 均为 `Exited (0)`。
- Redis 日志显示二者收到 `SIGTERM`，随后完成 RDB 保存并退出。
- `queue-short`、`queue-long` 日志反复出现 `Please make sure that Redis Queue runs @ redis://redis-queue:6379` 与 `Connection closed by server`。
- `websocket` 日志反复出现 `SocketClosedUnexpectedlyError: Socket closed unexpectedly`。

### 最小服务修复

```bash
docker compose up -d redis-cache redis-queue
docker compose ps redis-cache redis-queue
sleep 5; docker compose ps redis-cache redis-queue queue-short queue-long scheduler websocket
docker compose logs --tail=60 redis-cache redis-queue
docker compose logs --tail=80 queue-short queue-long scheduler websocket
```

修复结果：

- `redis-cache` 和 `redis-queue` 已启动，状态为 `Up`。
- Redis 日志显示 `Ready to accept connections`。
- `queue-long` 已启动 worker，并开始处理计划任务，日志出现 `Worker ... started`、`Listening on ...` 和 `Job OK`。
- `queue-short` 已启动 worker，日志出现 `Worker ... started` 与 `Listening on ...`。
- `websocket` 状态为 `Up`，日志显示 `Realtime service listening on: ws://0.0.0.0:9000`。
- `scheduler` 容器状态为 `Up`，后续 `bench --site frontend scheduler status` 显示 site scheduler 已启用。

本轮仅执行 `docker compose up -d redis-cache redis-queue` 以启动已退出的 Redis 服务；未执行 `docker compose down -v`，未删除 volume，未重建 `frontend` site。

### bench 与登录页验证

```bash
curl -s -o /dev/null -w 'login_http_code=%{http_code}\n' http://localhost:8081/login
docker compose exec -T backend bash -lc "cd /home/frappe/frappe-bench && bench version"
docker compose exec -T backend bash -lc "cd /home/frappe/frappe-bench && bench --site frontend list-apps"
docker compose exec -T backend bash -lc "cd /home/frappe/frappe-bench && bench --site frontend doctor"
docker compose exec -T backend bash -lc "cd /home/frappe/frappe-bench && bench --site frontend scheduler status"
docker compose exec -T backend bash -lc "cd /home/frappe/frappe-bench && bench --site frontend doctor"
```

结果：

- `/login` 返回 `login_http_code=200`。
- `bench version` 返回：
  - `erpnext 16.26.2`
  - `frappe 16.25.0`
  - `hrms 16.12.0 version-16`
- `bench --site frontend list-apps` 返回：
  - `frappe 16.25.0`
  - `erpnext 16.26.2`
  - `hrms 16.12.0 version-16`
- 首次 `bench doctor` 在 Redis 恢复后已可返回，不再卡在 Redis Queue 连接错误。
- 复跑 `bench doctor` 返回 `Workers online: 2`。
- `bench --site frontend scheduler status` 返回 `Scheduler is enabled for site frontend`。

说明：本地 shell 不存在 `timeout` 命令，三个带 `timeout` 包装的 bench 命令未进入容器执行；随后已改用普通 `docker compose exec -T` 完成验证。

## 当前服务状态

本轮修复后，关键容器状态如下：

- `backend`：Up。
- `frontend`：Up，`0.0.0.0:8081->8080/tcp`。
- `db`：Up，healthy。
- `redis-cache`：Up。
- `redis-queue`：Up。
- `queue-short`：Up，worker 已启动。
- `queue-long`：Up，worker 已启动并处理计划任务。
- `scheduler`：Up，`frontend` scheduler enabled。
- `websocket`：Up。

## TEST 数据只读计数

本轮执行了只读计数查询：

```bash
docker compose exec -T backend bash -lc 'cd /home/frappe/frappe-bench && bench --site frontend mariadb <<"...SQL..."'
```

当前 `TEST-HBOS-M1R3-*` 或 M1-R3 虚构员工相关数据计数如下：

| 对象 | 当前计数 |
| --- | ---: |
| Company | 0 |
| Department | 2 |
| User | 0 |
| Employee | 8 |
| Holiday List | 1 |
| Holiday child row | 1 |
| Shift Type | 4 |
| Shift Assignment | 14 |
| Employee Checkin | 22 |
| Leave Type | 1 |
| Leave Application | 2 |
| Attendance | 12 |

补充查询显示，当前存在的 Shift Assignment、Employee Checkin、Leave Application、Attendance 均关联 M1-R3 虚构员工或 `TEST-HBOS-M1R3-*` 班次 / 请假类型。

与 M1-R3A / M1-R3B 文档中记录的旧计数相比，当前只读计数范围更大。由于本轮未在修复前执行数据库计数，不能把差异精确归因到本轮 Redis / worker 恢复；但可以确认本轮没有手工执行创建、提交、删除或清理 TEST 数据的命令。该差异应作为 M1-R3C 或后续清理授权前的重点复核项。

## Company / User / Employee 阻断复测

本轮未执行 Company / User / Employee 写入复测。

原因：

- 用户明确禁止继续创建测试数据。
- Company / User / Employee 复测属于写入动作，会改变 TEST 数据范围。
- 本轮目标是运行态最小修复，不是 M1-R3C 重新试运行。

当前判断：

- Redis / worker / scheduler / `bench doctor` / `/login` 运行态阻断已经恢复或改善。
- Company / User / Employee 写入阻断尚未在本轮复测，需在用户明确授权的 M1-R3C 或独立复测轮次中验证。

## M1-R3C 进入条件判断

| 条件 | 当前判断 |
| --- | --- |
| Redis cache / queue 正常运行 | 满足 |
| queue worker 稳定在线 | 满足，`bench doctor` 显示 `Workers online: 2` |
| scheduler 可用 | 满足，`Scheduler is enabled for site frontend` |
| `/login` 可访问 | 满足，HTTP 200 |
| `bench --site frontend list-apps` 可返回 HRMS | 满足 |
| TEST 数据范围已重新只读确认 | 已确认，但当前计数高于 M1-R3A / M1-R3B 旧记录 |
| Company / User / Employee 写入阻断已复测 | 未满足，本轮禁止继续创建 TEST 数据 |
| 用户授权 M1-R3C | 未满足，M1-R3C 仍为 PLANNED |

结论：运行态层面的 Redis / worker / scheduler / bench / login 阻断已经最小修复；但 M1-R3C 仍不能自动启动。进入 M1-R3C 前，必须由用户确认是否接受当前 TEST 数据范围并授权继续虚构数据试运行，或先授权 TEST 数据隔离 / 清理。

## 本轮未做

- 未执行 `docker compose down -v`。
- 未删除 Docker volume。
- 未重建 `frontend` site。
- 未清理或删除 TEST 数据。
- 未继续创建 TEST 数据。
- 未执行 HRMS 考勤试运行。
- 未创建自定义 App。
- 未创建 `hb_attendance_app`。
- 未新增 DocType。
- 未开发业务代码。
- 未接真实考勤机。
- 未接真实飞书。
- 未实现 SSO。
- 未修改 Frappe / ERPNext / HRMS 核心源码。
- 未提交 `.env`、备份、密钥、数据库、日志、缓存或运行时产物。

## 架构结论

当前仍不建议创建 `hb_attendance_app`。

M1-R3 的阻断来自本地运行态和 TEST 数据链路不稳定，不是 HRMS 原生考勤能力已被证明无法覆盖海滨需求。M1 初期仍应优先复用 HRMS 原生能力；海滨特有规则继续进入 Gap List 或后续定制候选。

飞书登录沿用 M1-R0 结论：飞书作为员工侧主登录入口之一，HBOS 内部 User 自动映射 Employee。中文化问题仍只诊断，不直接修改 Frappe / ERPNext / HRMS 核心源码。

## 下一步建议

M1-R3B-FIX 已通过 Codex 审查并收口为 COMPLETED。

下一步由用户决定：

1. 授权进入 M1-R3C：在当前运行态恢复后，继续 HRMS 原生考勤虚构 TEST 数据重新试运行。
2. 或授权先做 TEST 数据隔离 / 清理，再进入重新试运行。
3. 或保持 M1-R3 BLOCKED，暂缓考勤链路试运行。

M1-R3C 仍为 PLANNED，尚未启动。M1-R4 未启动。
