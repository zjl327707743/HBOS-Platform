# 2026-09-09 时区统一 Asia/Shanghai（UTC+8）迁移留档

本文件记录把 HBOS 平台服务端与海滨 LIMS 时间统一为北京时间的一次性变更的**精确迁移范围**与**运维注意点**，供评审、回滚与后续重建时核对。变更落地与验证过程见 `docs/PROJECT_STATUS.md`（2026-09-09 时区统一条目）。

## 1. 变更内容

- `docker-compose.yml`：`backend / queue-long / queue-short / scheduler / websocket / frontend`（及一次性 `configurator/create-site`）增加 `TZ: Asia/Shanghai`，容器重建后 `date` 为 CST。`db`/redis 未设（时间戳由 Python 按 Frappe System Settings 写入，不依赖 DB 服务端时区；避免影响裸 SQL `NOW()`）。
- Frappe `System Settings.time_zone`：`Etc/UTC → Asia/Shanghai`。`now_datetime()/nowdate()/now()` 及 hb_lims_app 各服务（均调用 `frappe.utils.now_datetime()`）此后写入即北京 naive。
- 存量 UTC naive 时间戳一次性 +8h 迁为北京 naive。

## 2. 存量迁移范围（本次评审要求留档）

**迁移阈值**：`2026-09-09 15:34:47`（切换 System Settings 的时刻）。此前写入的为 UTC naive → 迁移；此后写入的已是北京 naive → 跳过（避免二次迁移）。

**迁移规则（两类，均已执行并核对计数）**：

1. **全表系统生成列**：遍历库中同时含 `creation` 与 `modified` 两列的所有 `tab*` 表，仅对这两列按阈值 +8h。二者永远是系统生成的瞬时列，故全局迁移安全。
   - 实际迁移 34,498 行 / 175 表（含 erpnext/hrms 元数据与业务表、HBOS* 各表）。
2. **业务「系统生成瞬时列」显式清单**（各 DocType 的一次性签署/审计时刻；Date 业务日历列一律不动）。清单与计数如下（合计 **891 行**）：

   | DocType | 列 | 迁移行数 |
   |---|---|---|
   | HBOS Audit Log | created_at | 774 |
   | HBOS COA | qa_reviewed_at | 6 |
   | HBOS COA | published_at | 6 |
   | HBOS Result Revision | changed_at | 3 |
   | HBOS Sample Task | assigned_date | 28 |
   | HBOS Test Result | submitted_at | 20 |
   | HBOS Test Result | reviewed_at | 20 |
   | HBOS Test Result | approved_at | 20 |
   | HBOS Retention Disposal Apply | qm_approved_at | 14 |

   `HBOS Sample.received_date`（DateTime）在清单内，但存量全为 NULL，实际迁移 0 行。

**明确未动的列**：所有 `Date` 业务日历列（样品/留样登记日、到期日、处理申请/执行日等）；**外部事实时刻列**——`Employee Checkin.time / shift_start / shift_end / shift_actual_start / shift_actual_end`（打卡机导入、按字符串原样落库，非 UTC 偏移生成）。`Employee Checkin / Attendance` 当前均为 0 行，即使未来有数据也不应纳入任何按 UTC 假设的时间迁移。

**迁移后采样核对**：审计最新事件 `06:38 UTC → 14:38 北京`；样品 creation `2026-09-04 02:06 → 10:06 北京`；Date 列（登记日/到期日）保持不变。

## 3. 备份（回滚）

- DB：容器内 `sites/frontend/private/backups/20260909_153642-frontend-database.sql.gz`（已拷宿主机 `runtime/backups/frappe_before_tz_20260909_153642/`）。
- 回滚：`bench --site frontend restore <备份>`。

## 4. 审计 checksum 口径（P2-3 记录 + 已处置）

`lims_service.py:61` `_checksum` 把 `created_at` 纳入 sha1。存量 `created_at` +8h 后，若按迁移后值重算会与旧 checksum 不一致、被误判篡改。**已处置**：2026-09-09 用同一算法对 774 行重算 `checksum`（复核 0 不一致），现 checksum 与迁移后的北京 naive `created_at` 自洽。今后若实现完整性重算校验，应全量通过；历史事件如需与迁移前对账，以第 3 节快照为准。

## 5. deadline 与迁移后批准日口径（P2-4 记录）

`HBOS Retention Disposal Apply.deadline`（Date，由批准时点 +3 个月派生）与 `qm_approved_at`（瞬时列）迁移后理论上存在跨日 ±1 天残留：UTC 16:00–24:00 批准的会由“UTC 日 +3 月”变成北京次日的批准时刻。实测当前含两者记录 **0 行不匹配**（存量批准均在不跨日时段）。属「瞬时列与日历列迁移不同步」固有残留，后续若出现边界窗口数据需以业务口径复核 deadline。

## 6. 前端展示层口径残留（P3 记录，待后续轮统一，不阻塞）

- P3-5：三处 `new Date().toISOString().slice(0,10)`（UTC 日）：`stores/dashboard.ts:15`（今日到期）、`RetentionView.vue:349/364`（登记默认留样日期）。北京每天 0:00–8:00 会把「今日」算成昨日。正确写法参照 `RetentionDisposalView.vue` 的 `localToday()`。
- P3-6：超期判定零点解析不一致：`RetentionDashboardView.vue:231` 用 `new Date('YYYY-MM-DD')`（UTC 零点），`RetentionDisposalView.vue:508` 用 `${dateStr}T00:00:00`（本地零点），同一 deadline 两处超期天数可差 8 小时；`RetentionView.vue:287-316` 临期过滤同口径。仅展示层，不影响落库。

## 7. 运维注意：frontend 容器重建后的恢复动作（P1-2 + 文档建议）

frontend 容器重建会同时丢失两类**容器本地、非 volume**的配置，需重建后恢复：

1. **nginx SPA fallback**（`/hbos-lims` history 深层路由）：运行时注入 `location ^~ /hbos-lims/` 到 `/etc/nginx/conf.d/frappe.conf` 并 reload。未注入时 `/hbos-lims/audit-log` 等深层路由 404（落到后端）。
2. **应用 assets 软链**：nginx `/assets/...` 解析到容器本地 `sites/assets → /home/frappe/frappe-bench/assets`，镜像仅内建 `erpnext/frappe` 软链；需重建 `hb_lims_app / hb_attendance_app / hrms → /home/frappe/frappe-bench/apps/<app>/<app>/public`（缺失时 Desk 的 LIMS/考勤 logo、`lims_report.css/js` 404）。

本次（2026-09-09）重建后两项均已恢复并验证 HTTP 200。**恢复动作已内置到 `deploy_lims_fix.sh`**（步骤 7b/7c），后续重建 frontend 或走该部署脚本时会自动补齐；`docker compose up -d` 重建后如需手工恢复，参照上两条命令。

（nginx conf 本次备份：容器内 `frappe.conf.bak-20260909-tz`。）
