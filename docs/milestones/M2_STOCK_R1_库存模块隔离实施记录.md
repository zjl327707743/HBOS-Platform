# M2-STOCK-R1 库存模块隔离实施记录

项目名称：新乡海滨智能运营管理平台。

轮次：M2-STOCK-R1（库存模块隔离）。
状态：IN_PROGRESS。Task 3 已交付（`stock` 站点建成）；**Task 4 已交付（PASS）**——首个回合因 fixture 顶层缺 `doctype` 字段导致 `install-app hb_stock_app` KeyError 失败（BLOCKED），该缺陷已由 Task 1 在 `014dc24` 修复；修复后重跑全部 Step 通过：App 安装成功、「海滨库存」工作台生成（72 / 1 / 3 / 8）、原生 `Stock` 工作台未被搬空（硬判据已在运行态重做）、`migrate` 幂等（连续两次退出码 0）、`frontend` 零回归 A / B / C 全 PASS。详见下方「Task 4」节。**Task 5 已交付（PASS）**——首个回合因原计划误设「`install-app erpnext` 会带来 ERPNext 建站主数据」而 `LinkValidationError: Could not find Warehouse Type: Transit` 失败（BLOCKED）；经裁定采用方案 A（建公司前先用 ERPNext 原生 `install_fixtures.install("China")` 补齐建站主数据）后，`stock` 建成 `Company HAIBIN`（abbr `H` / China / CNY）与 5 个默认仓库（逐字对齐 `frontend`）及 95 条科目 / 2 个成本中心，幂等复跑 `created=False`，`frontend` 零回归 A / B / C 全 PASS。详见下方「Task 5」节。Task 7 / 8 继续追加。

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

**状态：PASS（已交付）**。

首个回合：Step 1 `install-app` 因 fixture 顶层缺 `doctype` 而 KeyError 失败（**BLOCKED，未产生任何持久化变更，`frontend` 零回归**）；该缺陷已由 Task 1 在 `014dc24` 修复。修复后本回合重跑 Step 1–8 **全部通过**：App 安装成功、「海滨库存」工作台生成且计数与预期逐值一致、原生 `Stock` 工作台 72 / 1 / 3 未被搬空（硬判据已在运行态重做）、`migrate` 幂等、`frontend` 零回归 A / B / C 全 PASS。

> 下文 **Step 0 / Step 1 保留首回合 BLOCKED 的原始证据**（失败 traceback、根因定位、未产生持久化变更的核验表）作为历史记录；**Step 2 起**为修复后重跑回合的正文。首回合给出的「建议的最小修复方向」已由 Task 1 实施（`014dc24`），详见下方补记。

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

> **后续补记（2026-09-17）：该修复已由 Task 1 在 `014dc24` 实施。** 变更要点：
> 1. `workspace_builder.py` 的 `TOP_LEVEL_KEEP_FIELDS` 白名单重新推导，补上 `doctype` / `for_user` / `hide_custom`，并新增 `custom_blocks` / `quick_lists` 两张子表；
> 2. 生成的 fixture 顶层现已含 `"doctype": "Workspace"`（实测顶层键 21 个），Frappe 可正常导入；
> 3. 新增 `OracleSupersetTest`，以仓库内既有的「海滨考勤工作台」参考产物为 **oracle**，断言生成器输出与磁盘 fixture 的**顶层键集合都是该参考产物的超集**（排除 `creation` / `modified` 等审计字段），专门堵住本次「单测与实现共享盲点」——上一版 `_assert_no_drop_fields()` 只遍历 payload 的列表值（子表），而 `synthetic_source()` 自己也缺 `doctype`，于是测试全绿、产物却不可导入。
> 4. 修复提交同时改了 4 个文件：`setup.py`、`workspace/海滨库存/海滨库存.json`、`workspace_builder.py`、`test_workspace_builder.py`。

#### 失败未产生持久化变更（实测确认）

| 检查项 | 结果 |
| --- | --- |
| `bench --site stock list-apps` | 仍只有 `frappe` / `erpnext` |
| `sites/stock/site_config.json` 的 `installed_apps` | 仍为 `["frappe", "erpnext"]` |
| `Workspace 海滨库存` | 不存在 |
| `Module Def HBOS Stock` | 不存在（`add_module_defs` 的写入随事务回滚） |
| `Workspace` 总数 / `Module Def` 总数 / `stock` 库表数 | 19 / 32 / 736（与 Step 0 完全一致） |
| `grep -l hb_stock_app sites/*/site_config.json` | 无任何站点命中 |

### Step 1（重跑）：安装 App —— **PASS**

修复（`014dc24`）后重跑同一条命令（执行前再次逐字核对 `--site` 参数为 `stock`，不是 `frontend`）：

```bash
docker exec hbos-m0-r3a-backend-1 bash -lc \
  'cd /home/frappe/frappe-bench && bench --site stock install-app hb_stock_app'
```

结果：安装成功，`bench --site stock list-apps` 变为

```text
frappe       16.26.3 UNVERSIONED
erpnext      16.26.2 UNVERSIONED
hb_stock_app 0.0.1   UNVERSIONED
```

`sites/stock/site_config.json` 的 `installed_apps` 为 `["frappe", "erpnext", "hb_stock_app"]`——**只装这三个**，未装 `hrms` / `hb_attendance_app`；`stock` 站点库名为 `_f77d036c56d5d4af`（与 Task 3 一致，未新建库）。

### Step 2（重跑）：执行 migrate 触发 after_migrate —— **PASS（含幂等复跑）**

修复后 `hb_stock_app` 已登记进 `installed_apps`，其 `after_migrate` 钩子被加载。**只对 `stock` 站点**执行（执行前逐字核对 `--site` 为 `stock`）：

```bash
docker exec hbos-m0-r3a-backend-1 bash -lc \
  'cd /home/frappe/frappe-bench && bench --site stock migrate'
```

| 运行 | 开始时间（UTC / CST） | 退出码 | 输出尾部要点 |
| --- | --- | --- | --- |
| 第 1 次 | `2026-09-17T03:20:35Z` / `11:20:35 CST` | `0` | `Updating DocTypes for frappe/erpnext/hb_stock_app` → `Syncing jobs/fixtures/dashboards/customizations/languages` → `Removing orphan doctypes/Workspaces/...` → `Syncing portal menu` → `Updating installed applications` → `Executing \`after_migrate\` hooks...` → `Queued rebuilding of search index for stock` |
| 第 2 次 | `2026-09-17T03:27:35Z` / `11:27:35 CST` | `0` | 同上 |

两次输出均**无** `Traceback` / `Error` / `Exception` / `Warning` 行（关键字扫描计数为 0）。

**幂等性结论**：连续两次 `migrate` 均退出码 0；「海滨库存」工作台的 **docname（`海滨库存`）、顶层字段、三张子表计数（72 / 1 / 3）、`card_breaks`（8）在两次运行之间保持不变**（见 Step 3）。**唯一的运行态副作用**是工作台子表行的 docname 每次 `after_migrate` 保存时都会被重新生成（详见 Step 4 的「子表行名漂移」），属 Frappe 对「载荷不带 `name` 的子表行」删旧插新的常规语义，不影响计数与内容。

### Step 3（重跑）：确认工作台已生成 —— **PASS**

采集命令（brief 指定的只读解析器）：

```bash
docker exec hbos-m0-r3a-backend-1 bash -lc \
  'cd /home/frappe/frappe-bench && bench --site stock execute frappe.client.get \
     --kwargs '"'"'{"doctype":"Workspace","name":"海滨库存"}'"'"''
```

实测（`2026-09-17 11:35 CST`，即两次 `migrate` 之后）：

```text
name: 海滨库存 | label: 海滨库存 | module: HBOS Stock | app: hb_stock_app
links: 72 | charts: 1 | number_cards: 3
card_breaks: 8
```

与 brief 预期口径 `海滨库存 / HBOS Stock / hb_stock_app / 72 / 1 / 3 / 8` **逐值一致**。补充（同为只读查询）：`public = 1`、`type = Workspace`、`for_user` 空（公共工作台）、`owner = Administrator`、`shortcuts / quick_lists / custom_blocks` 均为 0。

### Step 4（重跑）：原生 Stock 工作台是否被搬空 —— **PASS（硬判据，已在运行态重做）**

fixture 修复并**真正跑通** `install-app` + `migrate` 之后，重新在运行态采集 `stock` 站点的原生 `Stock` 工作台（`2026-09-17 11:35 CST`）：

```text
name: Stock | label: Stock | module: Stock | app: erpnext
links: 72 | charts: 1 | number_cards: 3
card_breaks: 8
```

与 Step 0 基线（72 / 1 / 3 / 8）**逐值一致**，未被搬空。

> **证据强度说明**：首回合该判据「必然通过但无证明力」——fixture 在 `import_file_by_path` 读取阶段就 KeyError 中断，从未进入 Frappe 的子表写入路径，也就从未有机会复用同名子文档。本回合是**真正进入运行态子表写入路径之后**的复测，具备证明力。

**数据库层面的独立佐证**（只读 SQL，按工作台子表行名前缀分组）：

```text
tbl         pfx   n   min_creation                parents
Link        0ge   72  2020-03-02 15:43:10.096528  Stock
Link        bds   72  2026-09-17 08:57:36.716531  海滨库存
Chart       0ge    1  2020-03-02 15:43:10.096528  Stock
Chart       bds    1  2026-09-17 08:57:36.716531  海滨库存
NumberCard  0ge    3  2020-03-02 15:43:10.096528  Stock
NumberCard  bds    3  2026-09-17 08:57:36.716531  海滨库存
```

说明：`Stock` 的子表行前缀恒为 `0ge`、`creation` 恒为 **2020-03-02 15:43:10.096528**（ERPNext 首次建库时间），说明其子表行**从未被本次安装 / 迁移触碰**；「海滨库存」拥有**独立前缀**（`bds`）与独立 `creation`（安装时刻）。两套子表各行其道，DocType 子表 docname 的全局唯一性未被违反——这正是「剥离身份字段」设计生效的直接证据。

#### 子表行名漂移（独立核实记录，结论：机制成立、具体归因不成立、非回归）

协调方转述了一项待核实的观察：「`stock` 站点在一次 `migrate` 中把工作台子表行名从 `si4*` 重排成了 `0ge*`，称这是 Frappe 对 Workspace 子表的常规行为、时间早于本次安装、非回归」。本任务独立核实结论如下：

1. **「`migrate` 会重排工作台子表行名」——机制成立，且已直接观测到。** 本任务第 1 次 `migrate` 之前，「海滨库存」的 `links` 行名为 `7b7*` / `7b8*`（`creation = 2026-09-17 08:50:37.734070`）；第 2 次 `migrate` 之后变为清一色 `bds*`（`creation = 2026-09-17 08:57:36.716531`）——**72 条旧行被删除、72 条新行被插入，计数不变**。成因是 Task 1 **有意**剥离子表行的 `name`（保证 docname 全局唯一、不窃取原生 `Stock` 的行），`Workspace.save()` 因此把每次载荷视为「全新子行」而删旧插新。
2. **「`si4*` → `0ge*`」这一具体归因——不成立，属误读。** 实测 `0ge*` 是**原生 `Stock` 工作台自己的**子表行前缀，`creation` 为 **2020-03-02 15:43:10.096528**（早于本轮一切操作），`parent` 为 `Stock`；它**不是**「海滨库存」行名的某个历史形态。当前库内**已不存在任何 `si4*` 行**（`SELECT COUNT(*) ... WHERE name LIKE 'si4%'` 实测 = 0），也不存在 `7b7*` / `7b8*` 行（均已被后续 `migrate` 重写）。
3. **判定：非回归。** 「海滨库存」每次 `after_migrate` 会重写自己的子表行（本次三张主要子表共 76 行 = links 72 + charts 1 + number_cards 3），计数稳定、内容不变、**不触碰 `Stock` 的任何一行**；`frontend` 站点未装 `hb_stock_app`、本任务未对其执行 `migrate`，完全不受影响。
4. **给后续轮次的提示**：**不要**用「工作台子表行名」（`si4*` / `0ge*` / `7b7*` / `bds*` 之类）做跨轮次不变量或证据锚点——它每次 `after_migrate` 都会变。稳定判据应使用**计数**（`links` / `charts` / `number_cards` / `card_breaks`）与**工作台 docname**。

### Step 5（重跑）：确认考勤站点未被装上 hb_stock_app —— **PASS**

```text
$ bench --site frontend list-apps

frappe            16.26.3 UNVERSIONED
erpnext           16.26.2 UNVERSIONED
hrms              16.13.0 version-16
hb_attendance_app 0.0.1   UNVERSIONED
```

**不含 `hb_stock_app`**，与 Task 3 登记的基线逐项一致，不多不少。旁证：`grep -l hb_stock_app sites/*/site_config.json` **只命中 `sites/stock/site_config.json`**（本次安装目标），`frontend` 未被命中。

### Step 6（重跑）：考勤站点零回归（A / B / C 三组）—— **PASS**

采集时间 **2026-09-17 13:44:13 CST**（容器内 `05:44:13Z`）。`frontend` 为活站，`Employee Checkin` 后台任务周期为 `*/10 * * * *`。**全部为只读查询 / 只读诊断，本任务全程未对 `frontend` 执行任何写操作。**

#### A. 结构不变量（逐值相等）

| 检查项 | 基线 | 实测 | 结论 |
| --- | --- | --- | --- |
| `common_site_config.json` 的 `default_site` | `frontend` | `frontend` | PASS |
| `sites/frontend/site_config.json` 的 `db_name` | `_7aecc840db82aaec` | `_7aecc840db82aaec` | PASS |
| `sites/frontend/site_config.json` 与 Task 3 备份逐字节比对 | `20260916_150559-frontend-site_config_backup.json` | `diff -q` **无输出**（相同）；双方 sha256 均 `1e623c874086fe79162e9ae8b41a4c00375ee49cf6c05a2535efa964cdfd7e55` | PASS |
| `bench --site frontend list-apps` | frappe 16.26.3 / erpnext 16.26.2 / hrms 16.13.0 version-16 / hb_attendance_app 0.0.1 | 同上，逐行一致 | PASS |
| 已装 App 中是否出现 `hb_stock_app` | 不应出现 | 未出现 | PASS |
| `information_schema.TABLES` 表数量 | `=` 896 | 896 | PASS |
| MariaDB 库名 | `_7aecc840db82aaec` | 同上，未新增/更名 | PASS |

#### B. 活表单调不减 + 上界

基线采集 2026-09-16 15:23:32 CST → 本次 2026-09-17 13:44:13 CST，经过 **22.345 小时**；上界口径 `1000 条/小时`（Task 3 实测小时峰值 317 × 3 倍余量），故 `Employee Checkin` 上界 = `47776 + 1000 × 22.345 = 70121`。

| 不变量 | Task 3 基线（09-16 15:23:32） | 本任务实测（09-17 13:44:13） | 判据 | 结论 |
| --- | --- | --- | --- | --- |
| `Employee` | `=` 710 | 710 | 相等 | PASS |
| `Employee Checkin` | `≥` 47776 | 48793 | 47776 ≤ 48793 ≤ 70121 | PASS |
| `Attendance` | `≥` 26535 | 27047 | ≥ 基线 | PASS |
| `Shift Assignment` | `≥` 623 | 623 | ≥ 基线 | PASS |
| `Shift Schedule` | `=` 0 | 0 | 相等 | PASS |
| `HBOS Employee Schedule` | `≥` 4440 | 4446 | ≥ 基线 | PASS |
| `HBOS Attendance Import Log` | `=` 0 | 0 | 相等 | PASS |
| `HBOS Shift Rule` | `=` 17 | 17 | 相等 | PASS |
| `HBOS Leave Record` | `≥` 10150 | 10597 | ≥ 基线 | PASS |
| `HBOS Overtime Record` | `≥` 516 | 518 | ≥ 基线 | PASS |
| `Data Import Log` | `=` 0 | 0 | 相等 | PASS |
| `File` | `≥` 45 | 45 | ≥ 基线 | PASS |
| `User` | `=` 3 | 3 | 相等 | PASS |

**B 组备注**：`Employee Checkin` 22.345 小时净增 1017 条（≈ 45.5 条/小时），远低于 1000 条/小时上界，符合 `*/10` 批量写入节奏，**未出现数据丢失或异常批量灌入**。库大小由基线 405.2 MB 增至 **433.7 MB**（活站持续写入的正常增长，非回归）；表数量 `896` 保持不变。

#### C. 健康存活

| 检查项 | 实测 | 结论 |
| --- | --- | --- |
| `curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/login`（宿主机） | `200` | PASS |
| `bench --site frontend doctor` | 退出码 `0`；`Workers online: 2`；`-----frontend Jobs-----`（无错误段） | PASS |

**C 组口径提示（重复强调）**：`http://localhost:8080/login` 在 **`backend-1` 容器内不可达**（实测 `curl` 退出码 7 / `000`），该端口由 `hbos-m0-r3a-frontend-1` 容器暴露。登录检查须在**宿主机**或 **`frontend-1` 容器内**执行，否则会得到假阴性。

**零回归总结论：A / B / C 三组全部 PASS，`frontend` 站点数据与入口无任何回归。**

### Step 7 / 8（重跑）：本轮改动与提交

- 本轮**唯一**改动的仓库文件：本文档。
- 未改动 `apps/hb_stock_app/` 任何代码、未改动 fixture、未改动 `docker-compose.yml`、未改动 `.env`（fixture / 代码修复由 Task 1 在 `014dc24` 完成，不属于本任务改动）。
- 未对 `frontend` 执行任何写操作；未执行 `docker compose down -v`；未删除任何 Docker volume。
- 本任务完成后，Task 5 具备开工前置条件（`stock` 站点已含 `Module Def HBOS Stock` 与「海滨库存」工作台）。

## Task 5：初始化 stock 站点（Company HAIBIN + 默认仓库）

**状态：已交付（PASS）。** 首个回合以 `LinkValidationError: Could not find Warehouse Type: Transit` 失败（BLOCKED），根因为 `stock` 站点**从未跑过 ERPNext 的 setup wizard**，ERPNext 建站主数据（`Warehouse Type` / `UOM` / `Item Group` / `Party Type` …）一条都没有——这是原计划文本的一个错误假设（误以为 `install-app erpnext` 会带来这些主数据；实际只有 setup wizard 第 2 阶段 `install_fixtures.install()` 才会）。经协调人裁定采用方案 A：本脚本在建公司前，先用 ERPNext **原生装配器**补齐建站主数据。

### Step 0：交付物

- 新增脚本：`apps/hb_stock_app/hb_stock_app/hbos_stock/init_site.py`
- 调用方式：`bench --site stock execute hb_stock_app.hbos_stock.init_site.run`
- **未新建任何 DocType、未重写库存逻辑**；脚本内只调用 ERPNext 原生 DocType 与原生函数（`erpnext.setup.setup_wizard.operations.install_fixtures.install()`、`frappe.new_doc("Company")`）。

### Step 1：脚本要点（幂等设计）

1. **建站主数据补齐（新增，方案 A）**：以 `Warehouse Type` 为空作为建站主数据缺失的探针（该 Doctype 只由 setup wizard 装配器创建，且恰是 `Company.on_update -> create_default_warehouses()` 建默认仓库路径的硬依赖——它为「Goods In Transit」仓写死 `warehouse_type="Transit"`）。探针为空时调用 `install_fixtures.install("China")`（国家与 `frontend` 一致）。
2. **整体门控**：`install()` 整段包在 `if not frappe.db.count("Warehouse Type")` 之下，而非无条件执行——因为 `install()` 尾部还会无条件 `.save()` 一次 `Selling Settings` / `Buying Settings`；门控后重复执行不再触碰这些 Single，幂等在脚本层面显式成立（`install()` 自身经 `make_records()` → `doc.insert(ignore_permissions=True, ignore_if_duplicate=True)` 包在 savepoint 里，本身也已设计为幂等）。
3. **公司创建**：`frappe.new_doc("Company")` + `company_name="HAIBIN"` / `abbr="H"` / `country="China"` / `default_currency="CNY"`（逐字对齐 `frontend`），整段包在 `frappe.db.savepoint()` 中，异常即 `rollback(save_point=...)` 并 `raise`，**失败不留半成品**。
4. 脚本自带自检输出（公司名 / `created` / `master_data_created` / 仓库数 / 科目数 / 价目表数 / 仓库名列表），供执行后立即核对。

### Step 2：首次执行（`stock`）

```
$ bench --site stock execute hb_stock_app.hbos_stock.init_site.run
company=HAIBIN created=True master_data_created=True warehouses=5 accounts=95 price_lists=0
warehouses=['All Warehouses - H', 'Finished Goods - H', 'Goods In Transit - H', 'Stores - H', 'Work In Progress - H']
```

**公司字段核对（`stock` 实测）**：`abbr=H`、`country=China`、`default_currency=CNY` —— 与 `frontend` 逐字一致。

### Step 3：默认仓库与 `frontend` 逐字比对 —— PASS

`stock` 的 5 个仓库（含 `company` / `is_group` / `warehouse_type`）：

| 仓库名 | company | is_group | warehouse_type |
| --- | --- | --- | --- |
| `All Warehouses - H` | HAIBIN | 1 | — |
| `Finished Goods - H` | HAIBIN | 0 | — |
| `Goods In Transit - H` | HAIBIN | 0 | `Transit` |
| `Stores - H` | HAIBIN | 0 | — |
| `Work In Progress - H` | HAIBIN | 0 | — |

与 `frontend` 的 5 个仓库名**逐字相等**，别名后缀均为 ` - H`（对应 abbr），**不是** ` - HAIBIN`。ERPNext 自动生成的会计科目 `95` 条、成本中心 `2` 个，亦与 `frontend` 完全相等（见 Step 6 对照表）。

### Step 4：第二次执行（幂等复跑）—— PASS

```
$ bench --site stock execute hb_stock_app.hbos_stock.init_site.run   # EXITCODE=0
company=HAIBIN created=False master_data_created=False warehouses=5 accounts=95 price_lists=0
warehouses=['All Warehouses - H', 'Finished Goods - H', 'Goods In Transit - H', 'Stores - H', 'Work In Progress - H']
```

`created=False`、`master_data_created=False`，仓库仍为 `5`、科目仍为 `95`，**未重复建、未报错**。重复执行前后 `Warehouse Type` / `UOM` 等主数据计数不变（Step 6 对照表中为 `1` / `239`）。

### Step 5：`Item` 计数（打印式只读 SQL）—— PASS

口径提示：`bench execute` 对**假值返回值（`0` / `None`）不打印任何输出**，故 `frappe.client.get_count` 无法用于验证「应为 0」。本步改用会打印结果集的只读 SQL：

```
SELECT COUNT(*) FROM `tabItem`   →  0
```

`stock` 站点 `Item = 0`，`Customer = 0`，与 `frontend` 一致（`frontend` 的 `Item` 亦为 0 条，物料档案迁移不在本里程碑范围）。

### Step 6：建站主数据 / 双站点对照表（只读 SQL）

| 计数项 | `stock` | `frontend` | 结论 |
| --- | --- | --- | --- |
| `Company` | 1 | 1 | 相等 |
| `Warehouse` | 5 | 5 | 相等 |
| `Account` | 95 | 95 | 相等 |
| `Cost Center` | 2 | 2 | 相等 |
| `Warehouse Type` | 1 | 1 | 相等 |
| `UOM` | 239 | 239 | 相等 |
| `Item Group` | 6 | 6 | 相等 |
| `Party Type` | 4 | 4 | 相等 |
| `Price List` | **0** | **2** | **差异，见下** |
| `Item` | 0 | 0 | 相等 |
| `Customer` | 0 | 0 | 相等 |
| 限定 `company='HAIBIN'` 的 `Warehouse` / `Account` / `Cost Center` | 5 / 95 / 2 | 5 / 95 / 2 | 相等 |

**`Price List` 专项结论（协调人加问）**：`stock` 执行 `install_fixtures.install("China")` 后 `Price List` 仍为 `0`，`frontend` 为 `2`（`Standard Selling` / `Standard Buying`）。这是**预期内的**，原因：`Standard Selling` / `Standard Buying` 由 `erpnext/setup/setup_wizard/operations/defaults_setup.py:66 create_price_lists()` 创建，属 setup wizard 的 **defaults 阶段**（`setup_defaults`），**不在** `install_fixtures.install()`（fixtures 阶段）内，而本脚本按方案 A 只调用了后者。**`Price List` 不是创建 Company / 默认仓库 / 会计科目的前置依赖**——本任务在 `Price List = 0` 的条件下已完整创建公司、5 个默认仓库、95 条科目与 2 个成本中心（且 `install()` 自身的 `update_selling_defaults()` / `update_buying_defaults()` 只写 `cust_master_name` / `so_required` / `dn_required` 等字段，**不涉及** `price_list` 链接字段，实测 `stock` 的 `Selling Settings.selling_price_list` / `Buying Settings.buying_price_list` 均为空，**不存在悬空链接**）。若 Task 7 端到端验收需要价目表（如建销售/采购单据），再另行补建或补跑 setup wizard 的 defaults 阶段即可。

### Step 7：`System Settings.setup_complete` 依赖链调查（协调人加问，**仅报告，未置位**）

**结论：未置位时确有跳转，且发生在客户端；正确的置位途径是 ERPNext 原生机制，不是手写 `frappe.db.set_single_value`。**

实测两站点现状：

| 站点 | `Installed Application` 行（`is_setup_complete`） | `System Settings.setup_complete` | `frappe.is_setup_complete()` |
| --- | --- | --- | --- |
| `frontend` | `frappe=1`、`erpnext=1`（`hrms=0`、`hb_attendance_app=0`） | `1` | **True** |
| `stock` | `frappe=0`、`erpnext=0`（`hb_stock_app=0`） | 空 | **False** |

依赖链（逐层已核对源码）：

1. `frappe/frappe/__init__.py:1537 is_setup_complete()` —— 读取 `Installed Application` 中 `app_name in ("frappe","erpnext")` 两行的 `is_setup_complete`，`all(...)` 为真才算完成；**不直接读 `System Settings.setup_complete`**。
2. `frappe/frappe/boot.py:48` —— `bootinfo.sysdefaults["setup_complete"] = frappe.is_setup_complete()`。
3. `frappe/frappe/public/js/frappe/desk.js:293` —— `frappe.boot.setup_complete = frappe.boot.sysdefaults["setup_complete"]`（前端取的是 sysdefaults 这一路）。
4. **跳转点（客户端，非服务端）**：`frappe/frappe/public/js/frappe/router.js:137`——
   `if (frappe.boot.setup_complete) { ... } else if (!sub_path.startsWith("setup-wizard")) { frappe.set_route(["setup-wizard"]); }`
   即：`setup_complete` 为假时，用户访问 `/app` 下**任何非 `setup-wizard` 路由都会被强制改道到 setup wizard 页面**。另有 `desk.js:63`（`startup_setup_dialog` 弹窗）与 `frappe/boot.py:246`（`bootinfo.setup_wizard_requires = frappe.get_hooks("setup_wizard_requires")` → `erpnext/hooks.py:63 = assets/erpnext/js/setup_wizard.js`）同源受此标志驱动。
   补充：`frappe/www/`、`frappe/website/` 下 **grep 不到** `setup-wizard` 相关服务端跳转，`www/desk.py` 只处理 Guest 跳登录，**服务端不跳**——所以这是纯前端路由行为。
5. **唯一的原生置位者**：`frappe/frappe/core/doctype/installed_applications/installed_applications.py:31 update_versions()` —— 对 `frappe` 行取 `has_non_admin_user()`（存在**非 `Administrator`/`Guest` 的 System User**），对 `erpnext` 行取 `has_company()`（**存在任一 `Company`**），随后 `frappe.db.set_single_value("System Settings","setup_complete", frappe.is_setup_complete())`。该函数由 `frappe/frappe/migrate.py:198` 与 `frappe/frappe/installer.py:360/374/432` 调用，即**由 `bench migrate` / `install-app` 触发**。

**建议（供裁定）**：

- 本任务完成后 `stock` 已有 `Company HAIBIN`，故 `erpnext` 行在下次 `update_versions()` 时会置 `1`；但 `frappe` 行依赖 `has_non_admin_user()`，`stock` 当前只有 `Administrator`（System User）+ `Guest`（Website User），**为 False**。因此**单独跑 `bench --site stock migrate` 仍不足以让 `is_setup_complete()` 为真**（`frontend` 之所以为真，正因为它有 `isstascha121@gmail.com` 这个非管理员 System User）。
- 推荐路径（原生、可持续）：在 Task 6/7 为 `stock` 建一个**非 Administrator 的 System User**（真实登录本来也需要），再跑 `bench --site stock migrate` 触发 `update_versions()` 重算两行。**不建议**手写 `frappe.db.set_single_value("System Settings","setup_complete",1)`——它既不改变 `Installed Application` 两行（`is_setup_complete()` 仍为假、跳转依旧），又会被下一次 `migrate` 立即覆盖回去。
- 该项**未阻塞本任务**：公司、仓库、科目均已建成，`stock` 站点后端完全可用。

### Step 8：`frontend` 零回归（A / B / C）—— 全 PASS

| 组 | 检查项 | 实测 | 结论 |
| --- | --- | --- | --- |
| A | `common_site_config.json` 的 `default_site` | `frontend` | PASS |
| A | `bench --site frontend list-apps`（逐行） | `frappe 16.26.3` / `erpnext 16.26.2` / `hrms 16.13.0 version-16` / `hb_attendance_app 0.0.1`，不多不少 | PASS |
| A | `bench --site frontend doctor` | 退出码 `0` | PASS |
| A | `sites/frontend/site_config.json` 的 `db_name` | `_7aecc840db82aaec`（与 Task 3 基线一致） | PASS |
| B | `Employee Checkin` 计数 | 基线 `47776`（2026-09-16 15:23:32 CST）；本次实测 `48796`（2026-09-17 06:54:23 UTC，历时 23.514 h） | PASS |
| B | 上界 `47776 + 1000 × 23.514 = 71290` | `48796 ≤ 71290`，且 `48796 ≥ 47776`（净增 1020 条 ≈ 43.4 条/小时，符合 `*/10` 批量写入节奏） | PASS |
| C | `curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/login`（**宿主机**执行） | `200` | PASS |

**零回归总结论：A / B / C 三组全部 PASS，`frontend` 活站数据与入口无任何回归。**

### Step 9：本轮改动与提交

- 本轮改动的仓库文件：`apps/hb_stock_app/hb_stock_app/hbos_stock/init_site.py`（新增）与本文档。
- **仅对 `stock` 站点执行写操作**；`--site` 参数逐字确认为 `stock`。**未对 `frontend` 执行任何写操作**（全程只读查询）。
- 未改动 `docker-compose.yml`、`.env`；未改动 `workspace_builder.py` / `setup.py` / fixture / 既有 tests；未改动 Frappe / ERPNext / HRMS 核心源码；未新建 DocType。
- 未执行 `docker compose down -v`；未删除任何 Docker volume；未重建 `frontend` 站点。
- 首回合失败后**未自行删公司/删仓库重来**：失败后实测 `stock` 的 `Company` / `Warehouse` / `Account` 仍为 `0/0/0`，全事务已回滚、无残留，故无需清理。

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
- **工作台子表行名每次 `after_migrate` 都会重新生成**（本次实测 `7b7*` / `7b8*` → `bds*`，见 Task 4 Step 4「子表行名漂移」）。这是 Task 1 有意剥离子表行 `name` 以保全 docname 全局唯一性的副作用，**计数与内容稳定、非回归**。后续轮次做证据采集或回归判据时，**不要**用子表行名做锚点，请用计数与工作台 docname。若后续希望消除该 churn，可在 `_apply_payload` 侧改为「按顺序复用既有子行 docname」，但与「不得窃取原生 `Stock` 行」的设计约束需一并评估。
- ~~**Task 4 阻塞项（P0，阻断 Task 5）**：`hb_stock_app` 的 fixture 顶层缺 `doctype` 字段，`bench --site stock install-app hb_stock_app` 必然 KeyError 失败。~~ **已解除（2026-09-17）**：Task 1 已在 `014dc24` 修复 fixture 顶层缺 `doctype`（`TOP_LEVEL_KEEP_FIELDS` 补 `doctype` / `for_user` / `hide_custom` 并新增 `custom_blocks` / `quick_lists`，新增以参考产物为 oracle 的 `OracleSupersetTest` 补上「顶层键集合须为参考产物超集」的防线），并在 `setup.py` / fixture / `workspace_builder.py` / 单测四处同步。修复后本任务重跑 Step 1–8 全部通过。**首回合遗留的硬判据已按承诺重做**：Step 4「原生 `Stock` 工作台在安装 + migrate 后仍为 72 links / 1 chart / 3 number_cards」已在真正进入运行态子表写入路径后复测通过（见 Step 4），并有 `tabWorkspace *` 按行名前缀分组的数据库级佐证。
- `stock` 站点物料档案为空，待后续业务轮次录入。
- **Task 5 遗留（转 Task 6/7，非阻塞）**：
  - `stock` 的 `System Settings.setup_complete` 仍为空、`frappe.is_setup_complete()` 为 `False`，浏览器访问 `/app` 会被**前端路由**改道到 setup wizard（详见 Task 5 Step 7）。原生解法是「建一个非 `Administrator` 的 System User → `bench --site stock migrate`」触发 `Installed Applications.update_versions()` 重算；**不要**手写 `frappe.db.set_single_value("System Settings","setup_complete",1)`。
  - `stock` 的 `Price List` 为 `0`（`frontend` 为 `2`）：`Standard Selling` / `Standard Buying` 属 setup wizard 的 **defaults 阶段**，本任务的 `install_fixtures.install()` 不覆盖。**不影响** Company / 仓库 / 科目的创建与本任务验收；若 Task 7 需要价目表再补建。
- 状态台账（`docs/PROJECT_STATUS.md`、`docs/CURRENT_MILESTONE.md`）、`docs/milestones/README.md`（其中 `M2` 仍标为 `NOT STARTED`）与公共入口文件的更新不在 Task 3 范围，统一由 Task 8 收口。
