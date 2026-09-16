# M2-STOCK-R1 库存模块隔离实施记录

项目名称：新乡海滨智能运营管理平台。

轮次：M2-STOCK-R1（库存模块隔离）。
状态：IN_PROGRESS（本文档在 Task 3 建立骨架，Task 4 / 5 / 7 / 8 继续追加）。

## 目标与边界

本轮目标：在同一套 Frappe 栈内**新建独立站点 `stock`**（只装 `frappe` + `erpnext`），把「海滨库存」工作台与库存数据从考勤站点 `frontend` 中物理隔离出来，`frontend` 站点继续承载考勤一期业务且全程保持可用。

本轮明确的边界：

- 不修改 Frappe / ERPNext / HRMS 核心源码。
- 不执行 `docker compose down -v`，不删除 Docker volume，不重建 `frontend` site。
- `stock` 站点只装 `frappe`、`erpnext`；**不装** `hrms`、`hb_attendance_app`、`hb_stock_app`（`hb_stock_app` 属 Task 4）。
- 不提交 `.env`、App Secret、密钥、token。
- 每个任务结束必须让 `frontend` 站点保持可用（`http://localhost:8080/login` 返回 200）。

## 基线环境

- 工作目录：`/Users/xinxianghaibinzongheguanlizhongxin/Vibe Coding`。
- 分支：`m2-stock-r1`。
- 基线 HEAD：`4564164`（`chore: compose 挂载 hb_stock_app 卷与 PYTHONPATH（不改动现有站点）`）。
- 容器命名前缀：`hbos-m0-r3a-`（`backend-1`、`frontend-1`、`db-1`、`scheduler-1`、`queue-long-1`、`queue-short-1`、`websocket-1`、`redis-cache-1`、`redis-queue-1`）。
- 容器内 bench 路径：`/home/frappe/frappe-bench`；站点目录：`/home/frappe/frappe-bench/sites/`。
- `sites` 目录为 Docker named volume `hbos-m0-r3a_sites`（`/var/lib/docker/volumes/hbos-m0-r3a_sites/_data`）。

Task 2 已记录、本任务开工前复测确认的基线：

| 基线项 | 值 |
| --- | --- |
| `Employee Checkin` 计数 | 47770 |
| `http://localhost:8080/login` | 200 |
| `common_site_config.json` 的 `default_site` | `frontend` |
| MariaDB 中已有 Frappe 库 | `_7aecc840db82aaec`（frontend），无冲突库 |

## Task 3：备份 frontend 并创建 stock 站点

### Step 1：备份 frontend 站点（含文件）

命令：

```bash
docker exec hbos-m0-r3a-backend-1 bash -lc 'cd /home/frappe/frappe-bench && bench --site frontend backup --with-files'
```

实际输出：

```
Backup Summary for frontend at 2026-09-16 15:06:06.725887
Config  : /home/frappe/frappe-bench/sites/frontend/private/backups/20260916_150559-frontend-site_config_backup.json 296.0B
Database: /home/frappe/frappe-bench/sites/frontend/private/backups/20260916_150559-frontend-database.sql.gz 33.2MiB
Public  : /home/frappe/frappe-bench/sites/frontend/private/backups/20260916_150559-frontend-files.tar 1.5MiB
Private : /home/frappe/frappe-bench/sites/frontend/private/backups/20260916_150559-frontend-private-files.tar 300.0KiB
Backup for Site frontend has been successfully completed with files
```

**恢复点路径（本项目唯一恢复点，务必准确）**：

备份时间戳前缀：`20260916_150559`。

| 类型 | 容器内路径 | 大小 | sha256 |
| --- | --- | --- | --- |
| Site config | `/home/frappe/frappe-bench/sites/frontend/private/backups/20260916_150559-frontend-site_config_backup.json` | 296 B | `1e623c874086fe79162e9ae8b41a4c00375ee49cf6c05a2535efa964cdfd7e55` |
| Database | `/home/frappe/frappe-bench/sites/frontend/private/backups/20260916_150559-frontend-database.sql.gz` | 34827211 B | `ec00447160be163eddc96fa357643f6c62ef2702d8c80981a73cf5afaaa3aa51` |
| Public files | `/home/frappe/frappe-bench/sites/frontend/private/backups/20260916_150559-frontend-files.tar` | 1536000 B | `f34ee09c087850c319e2f457ae25a312d0a73de777d0132a1d045006d3eb3a75` |
| Private files | `/home/frappe/frappe-bench/sites/frontend/private/backups/20260916_150559-frontend-private-files.tar` | 307200 B | `93770c947735f502a3020b9ee4ee17e6b485582221ea55d6d86daf4b4712132d` |

备份位于 named volume `hbos-m0-r3a_sites` 内，不会因容器重启丢失；本项目禁止 `docker compose down -v`，因此该卷在轮次内视为安全。

额外的宿主机副本（仓库外、非 git 跟踪，仅作双保险，可随时删除）：

```
/Users/xinxianghaibinzongheguanlizhongxin/hbos-backups/m2-stock-r1/
```

宿主机副本 4 个文件的 sha256 与容器内**逐一致**，已核对。

恢复方式（如需）：

> **警告（务必先读）：`--force` 会覆盖现网数据。** 下文的 `bench restore --force` 会**直接覆盖 `frontend` 当前运行的数据库**，并覆盖站点内已存在的 public / private 文件。因此恢复前**必须先把「当前」的 `frontend` 再备份一次**（`bench --site frontend backup --with-files`），否则会用本次恢复点覆盖掉恢复点之后产生的新数据，且没有退路。**不要对 `frontend` 之外的站点执行 restore；不要用任何清理动作（`drop-site` / `down -v`）「重来一遍」。**

以本栈实测 `bench restore --help` 为准（**不凭记忆**），`--with-public-files` 与 `--with-private-files` 是**两个相互独立的开关**，各自接收对应的 tar 文件路径：

```text
Usage: bench  restore [OPTIONS] SQL_FILE_PATH

  --db-root-username, --mariadb-root-username TEXT
  --db-root-password, --mariadb-root-password TEXT
  --db-name TEXT
  --admin-password TEXT
  --install-app TEXT
  --with-public-files TEXT    Restores the public files of the site, given path to its tar file
  --with-private-files TEXT   Restores the private files of the site, given path to its tar file
  --force                     Ignore the validations and downgrade warnings. This action is not recommended
  --encryption-key TEXT
```

因此正确做法是**一次调用同时带上 4 件套**（数据库 + public 文件 + private 文件）。**只 restore 数据库那一个文件，会造成「数据库回来了、导出文件与附件全丢」的静默降级**——本次 `files.tar` 有 30 个条目（含 `HBOS异常考勤报表_*.xlsx`、`月度考勤汇总_*.xlsx`、`异常班次_*.xlsx` 等导出），`private-files.tar` 有 6 个条目（含 `四车间排班表.xlsx`、`月度汇总表_*.xlsx` 及 3 个 `.json.gz`），这些数据都在 tar 里，但只 restore 数据库时恢复程序根本不会去读它们。

```bash
docker exec hbos-m0-r3a-backend-1 bash -lc 'cd /home/frappe/frappe-bench && bench --site frontend --force restore \
  /home/frappe/frappe-bench/sites/frontend/private/backups/20260916_150559-frontend-database.sql.gz \
  --with-public-files /home/frappe/frappe-bench/sites/frontend/private/backups/20260916_150559-frontend-files.tar \
  --with-private-files /home/frappe/frappe-bench/sites/frontend/private/backups/20260916_150559-frontend-private-files.tar'
```

概念上的先后顺序（三者由上面**同一条命令**一次完成，`--help` 中并没有「只恢复文件」的独立子命令）：

1. **先 restore database**：`...-database.sql.gz`（位置参数 `SQL_FILE_PATH`），恢复主数据。
2. **再 restore public files**：`--with-public-files ...-files.tar`，恢复公开附件与导出文件。
3. **最后 restore private files**：`--with-private-files ...-private-files.tar`，恢复私有附件。

> 本任务**不执行**任何 restore（含演练）——「备份能否真恢复」属后续验证项，本次仅登记正确用法与已知风险。

### Step 2：改动前 `common_site_config.json` 全文（基线）

```json
{
 "db_host": "db",
 "db_port": 3306,
 "default_lang": "zh",
 "default_site": "frontend",
 "redis_cache": "redis://redis-cache:6379",
 "redis_queue": "redis://redis-queue:6379",
 "redis_socketio": "redis://redis-queue:6379",
 "socketio_port": 9000
}
```

### Step 3：确认 hosts 中尚无 stock 站点

命令：

```bash
docker exec hbos-m0-r3a-backend-1 bash -lc 'ls /home/frappe/frappe-bench/sites/'
```

结论：站点目录中只有 `frontend`，**不含 `stock`**。MariaDB 侧 `SHOW DATABASES` 也只有 Frontend 一个 Frappe 库，无同名库冲突。

### Step 4：创建 stock 站点

先在宿主机 `.env` 末尾追加一行（`.env` 未被 Git 跟踪，已确认；`STOCK_SITE_NAME` / `STOCK_HTTP_PORT` 属 Task 6 范围，本任务未加）：

```
STOCK_ADMIN_PASSWORD=$STOCK_ADMIN_PASSWORD
```

（真实值以 `python3 -c "import secrets; print(secrets.token_urlsafe(24))"` 生成的强随机值写入，本文档不记录明文。）

实际执行的命令：

```bash
docker exec -e STOCK_ADMIN_PASSWORD hbos-m0-r3a-backend-1 bash -lc \
  'cd /home/frappe/frappe-bench && bench new-site stock \
     --mariadb-user-host-login-scope="%" \
     --admin-password="$STOCK_ADMIN_PASSWORD" \
     --db-root-username=root \
     --db-root-password="$MARIADB_ROOT_PASSWORD" \
     --install-app erpnext'
```

要点：

- **未传 `--set-default`**（该参数是布尔开关，不是键值对；带上会抢走 `frontend` 的默认站点身份）。
- 密码通过 `docker exec -e`（**不带 `=值`**）从宿主机 shell 环境传入，**宿主机侧不再进入 argv**；但容器内 `bash -lc '... --admin-password="$STOCK_ADMIN_PASSWORD" ...'` 会展开该变量，`bench new-site` 进程的 argv 仍含明文（容器内 `ps` 可见）。这与本栈既有做法一致，不是本任务引入的回归。容器内 root 密码直接引用已注入的 `MARIADB_ROOT_PASSWORD`。
- 先用 `bench new-site --help` 核对过 `--mariadb-user-host-login-scope` / `--admin-password` / `--db-root-password` / `--install-app` 均存在。

实际输出（进度条已省略）：

```
=== start: 2026-09-16T07:07:02Z ===

Installing frappe...
Updating DocTypes for frappe        : [========================================] 100%
Creating Workspace Sidebars
Creating Desktop Icons
Installing erpnext...
Updating DocTypes for erpnext       : [========================================] 100%
Creating Workspace Sidebars
Creating Desktop Icons
*** Scheduler is disabled ***
=== exit code: 0 ===
=== end: 2026-09-16T07:07:39Z ===
```

结论：**exit code 0，无 traceback、无 error**。该 bench 版本不打印字面量 `Site stock created`，成功判据为退出码 0 + `sites/stock/` 目录生成 + 后续 `list-apps` 正常返回。

### Step 5：确认 `default_site` 未被抢走

命令：

```bash
docker exec hbos-m0-r3a-backend-1 bash -lc 'cat /home/frappe/frappe-bench/sites/common_site_config.json'
```

实际输出（建站后）：

```json
{
 "db_host": "db",
 "db_port": 3306,
 "default_lang": "zh",
 "default_site": "frontend",
 "redis_cache": "redis://redis-cache:6379",
 "redis_queue": "redis://redis-queue:6379",
 "redis_socketio": "redis://redis-queue:6379",
 "socketio_port": 9000
}
```

**与 Step 2 逐字段对比结论：全文 8 个字段完全一致（键、值、顺序均相同），`default_site` 仍为 `frontend`，未被 `stock` 抢走。**

补充核对：`stock` 站点的 `sites/stock/site_config.json` 独立生成，`installed_apps` 为 `["frappe", "erpnext"]`；`sites/frontend/site_config.json` 与备份中的 `20260916_150559-frontend-site_config_backup.json` **逐字节相同**（`diff` 无输出），证明建站未触碰 `frontend` 的站点配置。

### Step 6：确认新站点已装 erpnext，且未装考勤类 App

命令：

```bash
docker exec hbos-m0-r3a-backend-1 bash -lc 'cd /home/frappe/frappe-bench && bench --site stock list-apps'
```

实际输出：

```
frappe  16.26.3 UNVERSIONED
erpnext 16.26.2 UNVERSIONED
```

结论：只有 `frappe` 与 `erpnext`；**不含 `hrms`、`hb_attendance_app`、`hb_stock_app`**，符合本轮隔离要求。

### Step 7：frontend 站点回归验证

| 检查项 | 基线 | 建站后实测 | 结论 |
| --- | --- | --- | --- |
| `curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/login` | 200 | 200 | PASS |
| `bench --site frontend execute frappe.db.count --args '["Employee Checkin"]'` | 47770 | 47770 | PASS |
| `common_site_config.json` 的 `default_site` | `frontend` | `frontend` | PASS |
| MariaDB 中 frontend 库 | `_7aecc840db82aaec` | `_7aecc840db82aaec` 仍存在 | PASS |

结论：**`frontend` 站点完全可用，数据与入口无任何回归。** 新建的 `stock` 站点使用独立数据库 `_f77d036c56d5d4af`。

### Step 7 补充：frontend 更宽回归不变量快照（只读采集）

单看 `Employee Checkin = 47770` 太弱（该表在本栈是**持续写入**的活表，见下方「漂移说明」）。因此额外采集一组更宽的不变量作为回归判定依据。**全部为只读查询，未执行任何写操作或 restore。**

采集时间：**2026-09-16 15:23:32 CST**（宿主机 `TZ=Asia/Shanghai date`；容器内同时刻为 `07:23 UTC`）。

| 不变量（`frontend` 站点） | 采集值 |
| --- | --- |
| `Employee` | 710 |
| `Employee Checkin` | 47776 |
| `Attendance` | 26535 |
| `Shift Assignment` | 623 |
| `Shift Schedule` | 0（该 doctype 在本栈存在但无数据） |
| `HBOS Employee Schedule` | 4440 |
| `HBOS Attendance Import Log` | 0（该 doctype 由 `hb_attendance_app` 使用，表存在、零行，属合法基线） |
| `HBOS Shift Rule` | 17 |
| `HBOS Leave Record` | 10150 |
| `HBOS Overtime Record` | 516 |
| `Data Import Log` | 0 |
| `File` | 45 |
| `User` | 3 |
| `information_schema.TABLES` 表数量 / 库大小 | 896 张 / 约 405.2 MB |
| MariaDB 库名 | `_7aecc840db82aaec`（与基线一致） |
| `frontend` 已装 App | frappe 16.26.3 / erpnext 16.26.2 / hrms 16.13.0（version-16）/ hb_attendance_app 0.0.1 |
| `curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/login` | 200 |

`bench --site frontend doctor` 摘要（退出码 0）：

```text
-----Checking scheduler status-----
Workers online: 2
-----frontend Jobs-----
```

采集命令（只读）：

```bash
# 行数：把 SQL 写成 JSON 参数文件后 docker cp 进容器，避免 shell 反引号转义问题
docker exec hbos-m0-r3a-backend-1 bash -lc \
  'cd /home/frappe/frappe-bench && bench --site frontend execute frappe.db.sql --args "$(cat /tmp/task3-inv.json)"'

# 库大小 / 表数量
docker exec hbos-m0-r3a-backend-1 bash -lc \
  'cd /home/frappe/frappe-bench && bench --site frontend execute frappe.db.sql --args "$(cat /tmp/task3-q2.json)"'

# 健康检查
docker exec hbos-m0-r3a-backend-1 bash -lc 'cd /home/frappe/frappe-bench && bench --site frontend doctor'
```

**漂移说明（重要）**：`frontend` 是本栈的**生产性试验活站**，`Employee Checkin` 由后台任务按小时持续写入（最近批次 `2026-09-16 15:20:01`，`EMP-CKIN-09-2026-015209` 起）。故本表采集时该计数为 **47776**，较 Step 7 建站时刻的 47770 多 6 条——**这是活站正常增长，不是回归**（本任务全程未对 `frontend` 执行任何写操作）。因此 `Employee Checkin` 的正确不变量是**「单调不减 + 站点可读可登录」**，而非与某个固定数字严格相等；后续轮次复测时请以「不小于上表采集值、且库名 / 库大小 / 表数量 / App 列表 / 登录码不变」为判定口径。

同样地，这也意味着**任何 restore 恢复点都是活站的某一时刻切片**——一旦 `--force` 覆盖，恢复点之后新产生的打卡会被回滚。这正是上文恢复步骤要求「先备份当前 `frontend` 再 restore」的原因。

## Task 4：安装 hb_stock_app 并生成海滨库存工作台

（由 Task 4 追加）

## Task 5：初始化 stock 站点（Company HAIBIN + 默认仓库）

（由 Task 5 追加）

## Task 6：暴露 stock 站点（frontend-stock 服务 + 8082）

（由 Task 6 追加）

## Task 7：端到端验收

（由 Task 7 追加）

## 回滚方法

Task 3 之后（尚未安装 `hb_stock_app`，`stock` 站点内无业务数据）：

| 阶段 | 回滚动作 |
| --- | --- |
| Task 1–2 之后 | `git revert` 对应提交；`docker compose up -d` 恢复 |
| Task 3 之后（未装 App） | `bench drop-site stock`；Git 侧 `git revert` Task 2 提交 |
| Task 4–7 之后（已有数据） | 导出 `stock` 数据 → `bench drop-site stock` → 移除 `frontend-stock` 服务与 `STOCK_HTTP_PORT` → 恢复 Task 3 备份的 `frontend` |

`frontend` 恢复点见本文档 Step 1；**严禁**使用 `docker compose down -v` 或删除 Docker volume。

## 明确不做

- 不复制 ERPNext 库存 DocType 定义（75 个），不 fork ERPNext。
- 不做物料档案迁移（`frontend` 的 `Item` 为 0 条）。
- 不新增库存业务逻辑、不自建库存报表。
- 不动 M1-FIX 各轮既有状态（B3 / B4 / B5 保持原状）。

## 遗留事项

- `stock` 站点目前尚无定期备份习惯，待 Task 8 或后续轮次纳入（不得删除本次 `frontend` 恢复点）。
- `stock` 站点物料档案为空，待后续业务轮次录入。
- 状态台账（`docs/PROJECT_STATUS.md`、`docs/CURRENT_MILESTONE.md`）、`docs/milestones/README.md`（其中 `M2` 仍标为 `NOT STARTED`）与公共入口文件的更新不在 Task 3 范围，统一由 Task 8 收口。
