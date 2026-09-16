# M2-STOCK-R1 库存模块隔离实施记录

项目名称：新乡海滨智能运营管理平台。

轮次：M2-STOCK-R1（库存模块隔离）。
状态：IN_PROGRESS。Task 3 已交付（`stock` 站点建成）；**Task 4 BLOCKED**（`install-app hb_stock_app` 因 fixture 顶层缺 `doctype` 字段而 KeyError 失败，未产生持久化变更，`frontend` 零回归）——详见下方「Task 4」节。Task 5 / 7 / 8 继续追加。

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

**口径图例**：`≥` = 活表（可能增长，判据为**单调不减**，须另设上界，见下方「漂移说明」）；`=` = 冻结表（判据为**逐一相等**，不得增减）。

| 不变量（`frontend` 站点） | 采集值 / 口径 |
| --- | --- |
| `Employee` | `=` 710 |
| `Employee Checkin` | `≥` 47776（活表） |
| `Attendance` | `≥` 26535（由打卡派生，潜在增长） |
| `Shift Assignment` | `≥` 623（bitable 每 30 分钟同步，潜在增长） |
| `Shift Schedule` | `=` 0（该 doctype 在本栈存在但无数据） |
| `HBOS Employee Schedule` | `≥` 4440（bitable 同步，潜在增长） |
| `HBOS Attendance Import Log` | `=` 0（该 doctype 由 `hb_attendance_app` 使用，表存在、零行，属合法基线） |
| `HBOS Shift Rule` | `=` 17 |
| `HBOS Leave Record` | `≥` 10150（bitable 同步，潜在增长） |
| `HBOS Overtime Record` | `≥` 516（bitable 同步，潜在增长） |
| `Data Import Log` | `=` 0 |
| `File` | `≥` 45（导出/附件增长） |
| `User` | `=` 3 |
| `information_schema.TABLES` 表数量 / 库大小 | `=` 896 张 / 约 405.2 MB |
| MariaDB 库名 | `=` `_7aecc840db82aaec`（与基线一致） |
| `frontend` 已装 App | `=` frappe 16.26.3 / erpnext 16.26.2 / hrms 16.13.0（version-16）/ hb_attendance_app 0.0.1 |
| `curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/login` | `=` 200 |

标注依据（只读复测，非推测）：采集时刻 +16 分钟（15:39）复测，**上表仅 `Employee Checkin` 实际增长**（47776 → 47786，即 15:32 批次 10 条），其余全部不变；`hb_attendance_app/hooks.py` 中以 `*/30 * * * *` 挂载的 bitable 同步会在源数据变化时增长，故对这几张表取更保守的 `≥` 口径。

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

**漂移说明（重要）**：`frontend` 是本栈的**生产性试验活站**，`Employee Checkin` 由后台任务持续写入。写入周期为 **`*/10 * * * *`，即每 10 分钟触发一次**——依据 `apps/hb_attendance_app/hb_attendance_app/hooks.py` 中 `scheduler_events["cron"]` 将 `hb_attendance_app.hbos_attendance.api.sync_delicloud_checkin` 挂在 `*/10 * * * *` 上（**不是每小时**）。

**每批实际插入条数极不均一**（由外部 delicloud 增量驱动，源侧无新数据时该批次插入 0 条）：安静时段单批仅 **1–10 条**，而早班打卡峰单批可达 **113 条**（08:32 那个 10 分钟桶）。本日按**行创建时间**（`creation`，即实际入库时间）实测小时插入量：`00 时 117`、`06 时 11`、`07 时 103`、`08 时 317`（日内峰值，早班打卡峰）、`09 时 7`、`11/12 时各 1`、`14 时 4`、`15 时 32`（截至 15:39）。故该表计数在不同时刻**几乎没有可比性**：Step 7 建站时刻 47770 → 本表采集 47776 → 15:39 复测 47786——**这是活站正常增长，不是回归**（本任务全程未对 `frontend` 执行任何写操作）。

由此给出后续轮次（Task 4 / 6 / 7）的统一判定口径——**活表必须同时设下界与上界**，只设下界发现不了「异常灌入」（例如误连生产 API 造成暴增）：

- **下界（单调不减）**：`当前值 ≥ 基线值`（上表标注 `≥` 的项）。用途是发现数据丢失。
- **上界（异常灌入告警）**：按 `基线值 + 周期数 × 单批条数 × 余量` 估算。以实测**小时峰值 317 条**、余量 3× 计，取 **约 1000 条/小时** 为告警上界，判定式为：

  ```
  基线值 ≤ 复测值 ≤ 基线值 + 1000 × 距基线经过小时数
  ```

  任一计数**超过上界即须人工解释**（首要怀疑误连生产 API、源侧重复推送），不得直接判通过。两条说明：

  - **未采用**「实测约 6 条/批 × 6 批/小时 ≈ 36 条/小时」这一估算：6 条/批 只是**安静时段**的批均，早班峰单批可达 113 条、小时合计 317 条，**固定批均假设不成立**（若照该公式代入峰值单批 113 条，得 `6 × 113 × 3 ≈ 2000 条/小时`）。本表取更直接的实测小时峰值 `317 × 3 ≈ 1000 条/小时`。
  - 该上界针对**万级量级的暴增**（误连生产库之类）；数百条/小时的**持续小量**异常单点看不出来，须靠多时刻累计比对。
- **冻结表（上表标注 `=` 的项）**：`当前值 == 基线值`；并保持 `库名 / 库大小 / 表数量 / App 列表 / 登录码` 不变。

**跨文档一致性提示**：`docs/superpowers/plans/2026-09-16-库存模块隔离实施计划.md` 的零回归判据组目前仍写「实测一批约 6 条，即约 36 条/小时」，与本表口径不一致。该文件不属本任务改动范围，故此处仅登记差异——请协调方裁定后，由该文件负责人在 Task 6 / 7 之前统一，避免下游按 36 条/小时 设界产生正常早班峰即误报。

同样地，这也意味着**任何 restore 恢复点都是活站的某一时刻切片**——一旦 `--force` 覆盖，恢复点之后新产生的打卡会被回滚。这正是上文恢复步骤要求「先备份当前 `frontend` 再 restore」的原因。

## Task 4：安装 hb_stock_app 并生成海滨库存工作台

**状态：BLOCKED**（Step 1 `install-app` 失败，**未完成安装，未生成工作台**；未产生任何持久化变更，`frontend` 零回归）。

### Step 0：开工前只读基线

采集时间 **2026-09-16 17:02:38 CST**（容器内 `09:02:38Z`）。

`stock` 站点（写入前）：

| 项 | 值 |
| --- | --- |
| `list-apps` | `frappe 16.26.3` / `erpnext 16.26.2`（只有这两个） |
| 站点库名 | `_f77d036c56d5d4af` |
| 原生 `Stock` 工作台 | links 72 / charts 1 / number_cards 3 / card_breaks 8 |
| `Workspace 海滨库存` | 不存在（`frappe.db.exists` 返回空 + `DoesNotExistError`） |
| `Workspace` 总数 / `Module Def` 总数 / 库表数 | 19 / 32 / 736 |

### Step 1：安装 App —— **失败**

命令（执行前已逐字核对 `--site` 参数为 `stock`，不是 `frontend`）：

```bash
docker exec hbos-m0-r3a-backend-1 bash -lc \
  'cd /home/frappe/frappe-bench && bench --site stock install-app hb_stock_app'
```

实际输出（完整，仅省略 frappe traceback 的局部变量转储）：

```text
=== start: 2026-09-16T09:02:58Z ===
App frappe already installed
App erpnext already installed

Installing hb_stock_app...
An error occurred while installing hb_stock_app: 'doctype'
Traceback (most recent call last):
  File "apps/frappe/frappe/commands/site.py", line 522, in install_app
    _install_app(app, verbose=context.verbose, force=force)
  File "apps/frappe/frappe/installer.py", line 323, in install_app
    sync_for(name, force=force, reset_permissions=True)
  File "apps/frappe/frappe/model/sync.py", line 131, in sync_for
    imported = import_file_by_path(
  File "apps/frappe/frappe/modules/import_file.py", line 123, in import_file_by_path
    db_modified_timestamp = frappe.db.get_value(doc["doctype"], doc["name"], "modified")
builtins.KeyError: 'doctype'
=== exit code: 1 ===
=== end: 2026-09-16T09:02:59Z ===
```

#### 根因（只读定位，未改动任何 App / 核心代码）

失败点是 **Task 1 产出的 fixture 文件本身**，不是环境问题：

1. `frappe/installer.py::install_app` 的顺序是 `add_module_defs()` → **`sync_for(name)`** → 才 `add_to_installed_apps(name)`。异常发生在 `sync_for` 内，所以 App 从未被登记进 `installed_apps`。
2. `sync_for` 经 `get_doc_files()` 收 `<module>/workspace/<docname>/<docname>.json`，本次 `files` 恰为 1 个：`apps/hb_stock_app/hb_stock_app/hbos_stock/workspace/海滨库存/海滨库存.json`（traceback 中 `i = 0, l = 1`，即**第一个文件就失败**）。
3. `import_file_by_path()` 第 123 行无条件读 `doc["doctype"]`；而该 fixture 顶层**没有** `doctype` 键。实测顶层键集合：

   ```text
   ['app', 'charts', 'content', 'icon', 'is_hidden', 'label', 'links', 'module',
    'name', 'number_cards', 'public', 'roles', 'sequence_id', 'shortcuts', 'title', 'type']
   ```

   对照 ERPNext 原生 `apps/erpnext/erpnext/stock/workspace/stock/stock.json`，其顶层**含** `"doctype": "Workspace"`。
4. 成因在 `apps/hb_stock_app/hb_stock_app/hbos_stock/workspace_builder.py`：
   - `ROW_DROP_FIELDS` 把 `doctype` 列为「必须剥离」（本意**只针对子表行**，剥离子表 docname 身份）；
   - 但 `TOP_LEVEL_KEEP_FIELDS` 白名单里**也没有** `doctype`，于是顶层 `doctype` 既没被保留、也没被保留列表断言拦住；
   - `_assert_no_drop_fields()` 只遍历 payload 的**列表**值（子表），**不检查顶层标量**，因此这个缺失是静默的。
5. 单测为什么没拦住：`apps/hb_stock_app/tests/test_workspace_builder.py` 的 `synthetic_source()` 顶层同样没有 `doctype`，`test_link_rows_drop_child_identity` 也只对 `p["links"]` 的行断言。**单测全绿，但产物不是 Frappe 可导入的文档。** 这正是 Task 1 审查时要求「必须在运行态验证」的那类问题。

**建议的最小修复方向（本任务未实施，等 Owner / 协调方裁定）**：让 fixture 顶层带上 `"doctype": "Workspace"`（例如把 `doctype` 加入 `TOP_LEVEL_KEEP_FIELDS` 并在 `build_workspace_payload` 里显式置为 `"Workspace"`），同时**保持**子表行继续剥离 `doctype` / `name` / `parent` 等身份字段；并给 `test_workspace_builder.py` 补一条「顶层必须含 `doctype == "Workspace"`」的断言。按本任务纪律（「不要自行修改 fixture 或 App 代码绕过」），**未执行此修复**。

#### 失败未产生持久化变更（实测确认）

| 检查项 | 结果 |
| --- | --- |
| `bench --site stock list-apps` | 仍只有 `frappe` / `erpnext` |
| `sites/stock/site_config.json` 的 `installed_apps` | 仍为 `["frappe", "erpnext"]` |
| `Workspace 海滨库存` | 不存在 |
| `Module Def HBOS Stock` | 不存在（`add_module_defs` 的写入随事务回滚） |
| `Workspace` 总数 / `Module Def` 总数 / `stock` 库表数 | 19 / 32 / 736（与 Step 0 完全一致） |
| `grep -l hb_stock_app sites/*/site_config.json` | 无任何站点命中 |

### Step 2：执行 migrate 触发 after_migrate —— **未执行（无意义）**

App 未安装成功，`hb_stock_app` 不在 `installed_apps` 中，其 `after_migrate` 钩子不会被加载；此时对 `stock` 跑 `migrate` 只会跑 frappe/erpnext 自身的 patch，无法触及本任务目标，故跳过，不做无意义的写入。

### Step 3：确认工作台已生成 —— **未达成**

`Workspace 海滨库存` 从未被创建。实测（与 Step 1 失败输出一致）：

```text
frappe.exceptions.DoesNotExistError: Workspace 海滨库存 not found
```

故 **name / label / module / app、links / charts / number_cards / card_breaks 的实测计数全部无从产生**——预期口径 `海滨库存 / HBOS Stock / hb_stock_app / 72 / 1 / 3 / 8` 未验证。

### Step 4：原生 Stock 工作台是否被搬空 —— **运行态未验证（这是本任务的遗留风险）**

失败后（**2026-09-16 17:04 CST**）复测 `stock` 站点原生 `Stock`：

```text
name: Stock | label: Stock | module: Stock | app: erpnext
links: 72 | charts: 1 | number_cards: 3
card_breaks: 8
```

与 Step 0 逐值一致，**表面上 72 / 1 未被破坏**。但必须明确标注证据强度：

> **这不是子表身份字段剥离正确的证据。** fixture 在 `import_file_by_path` 读取阶段就 KeyError 中断，**从未进入 frappe 的子表写入路径**，也就从未有机会复用同名子文档，因此「Stock 仍是 72 条」是**必然结果**，不能用来证明剥离逻辑正确。
>
> 作为旁证（**静态**，非运行态）：对 fixture 文件做只读检查，`links` / `charts` / `number_cards` 三张子表**没有任何一行**携带 `name`、`parent`、`parentfield`、`parenttype`、`doctype` 等身份字段（72 / 1 / 3 行，携带 `name` 的行数为 0）。这只说明**产物文件**是干净的，不能替代运行态验证。
>
> **结论：Step 4 的核验（原生 Stock 在安装后仍为 72 links / 1 chart）必须在 fixture 修好、`install-app` + `migrate` 真正跑通之后重做。**

### Step 5：确认考勤站点未被装上 hb_stock_app —— **PASS**

```text
$ bench --site frontend list-apps

frappe            16.26.3 UNVERSIONED
erpnext           16.26.2 UNVERSIONED
hrms              16.13.0 version-16
hb_attendance_app 0.0.1   UNVERSIONED
```

**不含 `hb_stock_app`**，与 Task 3 登记的基线逐项一致，不多不少。

### Step 6：考勤站点零回归（A / B / C 三组）—— **PASS**

采集时间 **2026-09-16 17:04:01 CST**。`frontend` 为活站，`Employee Checkin` 后台任务周期为 `*/10 * * * *`。

#### A. 结构不变量（逐值相等）

| 检查项 | 基线 | 实测 | 结论 |
| --- | --- | --- | --- |
| `common_site_config.json` 的 `default_site` | `frontend` | `frontend`（全文 8 字段与 Task 3 Step 2 逐字段一致） | PASS |
| `sites/frontend/site_config.json` 的 `db_name` | `_7aecc840db82aaec` | `_7aecc840db82aaec` | PASS |
| `bench --site frontend list-apps` | frappe 16.26.3 / erpnext 16.26.2 / hrms 16.13.0 version-16 / hb_attendance_app 0.0.1 | 同上，逐行一致 | PASS |
| MariaDB 库列表 | `_7aecc840db82aaec`、`_f77d036c56d5d4af` | 同上，未新增库 | PASS |

#### B. 活表单调不减 + 上界

| 不变量 | Task 3 基线（15:23:32） | 本任务实测（17:04:01） | 判据 | 结论 |
| --- | --- | --- | --- | --- |
| `Employee` | `=` 710 | 710 | 相等 | PASS |
| `Employee Checkin` | `≥` 47776 | 47933 | 47776 ≤ 47933 ≤ 47776 + 1000×1.675 = 49451 | PASS |
| `Attendance` | `≥` 26535 | 26535 | ≥ 基线 | PASS |
| `Shift Assignment` | `≥` 623 | 623 | ≥ 基线 | PASS |
| `Shift Schedule` | `=` 0 | 0 | 相等 | PASS |
| `HBOS Employee Schedule` | `≥` 4440 | 4440 | ≥ 基线 | PASS |
| `HBOS Attendance Import Log` | `=` 0 | 0 | 相等 | PASS |
| `HBOS Shift Rule` | `=` 17 | 17 | 相等 | PASS |
| `HBOS Leave Record` | `≥` 10150 | 10190 | ≥ 基线 | PASS |
| `HBOS Overtime Record` | `≥` 516 | 516 | ≥ 基线 | PASS |
| `Data Import Log` | `=` 0 | 0 | 相等 | PASS |
| `File` | `≥` 45 | 45 | ≥ 基线 | PASS |
| `User` | `=` 3 | 3 | 相等 | PASS |
| `information_schema.TABLES` 表数 / 库大小 | `=` 896 / 405.2 MB | 896 / 405.2 MB | 相等 | PASS |

上界口径说明：`1000 条/小时` 取自 Task 3 文档「漂移说明」的实测小时峰值 317 条 × 3 倍余量。基线到复测经过 `1.6747` 小时，故上界 `47776 + 1675 = 49451`。`Employee Checkin` 实测 47933，落在区间内。另：开工前 17:02:38 与收工后 17:04:01 两次读数**相同**（47933），与 `*/10` 的 10 分钟批次节奏一致，不是异常。

#### C. 健康存活

| 检查项 | 实测 | 结论 |
| --- | --- | --- |
| `curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/login`（宿主机） | `200` | PASS |
| 同一 URL 从 `hbos-m0-r3a-frontend-1` 容器内 | `200` | PASS |
| `bench --site frontend doctor` | 退出码 0；`Workers online: 2`；`-----frontend Jobs-----`（无错误段） | PASS |
| `hbos-m0-r3a-backend-1` 容器日志尾部 | 无新增 error（仅 whoosh SyntaxWarning，为既有） | PASS |

**C 组口径提示**：`http://localhost:8080/login` 在 **`backend-1` 容器内不可达**（实测 `curl` 退出码 7 / `000`），该端口由 `hbos-m0-r3a-frontend-1` 容器暴露。本任务的登录检查在**宿主机**与 **`frontend-1` 容器内**执行，两处均为 200。后续轮次做该检查时不要误在 `backend-1` 内执行，否则会得到假阴性。

**零回归总结论：A / B / C 三组全部 PASS，`frontend` 站点数据与入口无任何回归。本任务全程未对 `frontend` 执行任何写操作（仅 `list-apps` / `doctor` / `execute frappe.db.sql` 只读查询）。**

### Step 7 / 8：本轮改动与提交

- 本轮**唯一**改动的仓库文件：本文档。
- 未改动 `apps/hb_stock_app/` 任何代码、未改动 fixture、未改动 `docker-compose.yml`、未改动 `.env`。
- Task 4 的 `hb_stock_app` 安装与「海滨库存」工作台生成**尚未完成**，Task 5 无法在其之上开工（缺少 `Module Def HBOS Stock` 与 `海滨库存` 工作台），需先修 fixture 后重跑 Task 4。

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
- **Task 4 阻塞项（P0，阻断 Task 5）**：`hb_stock_app` 的 fixture（`apps/hb_stock_app/hb_stock_app/hbos_stock/workspace/海滨库存/海滨库存.json`）顶层缺 `doctype` 字段，`bench --site stock install-app hb_stock_app` 必然 KeyError 失败。需在 Task 1 的 `workspace_builder.py` / fixture 生成器侧修复（并补单测断言），再重跑 Task 4 全部 Step。**修好重跑时，Step 4「原生 Stock 工作台仍为 72 links / 1 chart」必须作为硬判据重做**——本次因 fixture 未真正导入，该判据未被有效验证。
- `stock` 站点物料档案为空，待后续业务轮次录入。
- 状态台账（`docs/PROJECT_STATUS.md`、`docs/CURRENT_MILESTONE.md`）、`docs/milestones/README.md`（其中 `M2` 仍标为 `NOT STARTED`）与公共入口文件的更新不在 Task 3 范围，统一由 Task 8 收口。
