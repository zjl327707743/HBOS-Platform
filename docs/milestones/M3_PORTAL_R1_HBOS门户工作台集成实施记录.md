# HBOS 门户工作台集成实施记录

项目名称：新乡海滨智能运营管理平台。

轮次：**M3-PORTAL-R1**（HBOS 门户工作台集成，分支 `feature/hbos-portal-workbench`）。

状态：**REVIEWING**（R1–R3 已交付；**R4 未启动**，需 Owner 另行授权）。

## 编号说明

本工作线编号为 **M3-PORTAL-R1**（Owner 2026-09-28 裁定）。它不套用 `M1-FIX-*`——在性质上它是独立的门户 / 平台外壳工作流（新增 Vue 3 门户 SPA + `hbos_portal` 薄平台 App），不是 M1-FIX 考勤功能补漏轮次（`M1-FIX-C/D/E` 的既定含义仍为异常三级流程 / 考勤工作台月报 / 飞书 OAuth 验证）。

同一裁定一并消除了 `M2` 前缀冲突：

- **`M2` 归「飞书集成」**（回到最初定义）。
- **库存模块隔离由 `M2-STOCK-R1` 改号 `M4-STOCK-R1`**（文档改名 `M4_STOCK_R1_库存模块隔离实施记录.md`，分支改名 `m4-stock-r1`）。
- 本工作线取留出的 **`M3`**，与 `M2` 飞书集成、`M4` 库存隔离平行。

## 分支与基线

- 工作分支：`feature/hbos-portal-workbench`。
- 基线：`m1-fix-c-rest-leave` 的 HEAD `93ae18a`（`fix: 修复 CI 回归失败——test_rest_leave_verify 依赖 CI 未安装的 requests`）。
- 本轮提交数：19。
- 移植来源：长期分支 `origin/feature/hbos-portal-product`（**只做选择性移植，禁止 merge**）。
- 不合并的原因（实测）：两分支自 `2675411`（2026-08-14）后分别推进 100 / 164 提交，且**两边都改过** `pairing.py` / `api.py` / `rule_lists.py`——这三个文件承载 178 人行政班名单、调休豁免与配对判定。`apps/hb_attendance_app` 以 bind-mount 进入承载真实（约 700 名员工）数据的运行中容器，合并冲突处理失误会直接污染真实考勤。

## 轮次拆分与交付

| 轮次 | 内容 | 触碰运行态 | 状态 |
|---|---|---|---|
| **R1 移植** | 取入门户前端工程、`hbos_portal` 薄平台 App、考勤 portal 适配层与契约测试 | 否 | 已交付 |
| **R2 同域通路** | Vite dev 代理扩展、mock 业务路由映射、同域 iframe 承载视图、浏览器实测 | 否 | 已交付 |
| **R3 接真实数据** | compose 挂载 + PYTHONPATH、重建 5 个 app 容器、`install-app` + `migrate` | 是（已授权） | 已交付 |
| **R4 生产形态** | 门户构建产物交 nginx 分发、`VITE_BASE=/hbos/` | 需另授权 | **未启动** |

### R1 移植（Task 1–3，不触碰运行态）

从 `origin/feature/hbos-portal-product` 选择性取入三块产物：

- `frontend/hbos-portal-web`：Vue 3 + Ant Design Vue 4 + Vue Router 4 + Pinia + Vite 7 + TypeScript 的**门户 SPA（46 文件）**。
- `apps/hbos_portal`：**薄平台 App（37 文件）**——registry / bootstrap / provider dispatch / route resolver。该 App **从不 import 业务 App**，业务 App 经 `hbos_portal_provider` hook **自注册**。
- `apps/hb_attendance_app/hb_attendance_app/hbos_attendance/portal/`：**考勤对门户的只读适配层（7 文件）**，另加 `hooks.py` 末尾一行 `hbos_portal_provider` 注册，与 **12 用例契约测试** `apps/hb_attendance_app/tests/test_portal_provider_contract.py`。

移植只「新增文件 + 一行 hook」，不改考勤判定核心。

### R2 同域通路（Task 4–7，不触碰运行态）

- **Vite dev server（端口 5178）把 12 条 Frappe 路径前缀**（`/api`、`/app`、`/desk`、`/assets`、`/files`、`/private`、`/login`、`/logout`、`/method`、`/printview`、`/socket.io`、`/favicon.ico`）**代理到 `127.0.0.1:8080`**，使浏览器只看到 5178 单一来源。
- mock 模式补业务路由映射（`businessRoutes.ts`），使「考勤」解析到真实 Desk 页面而非不存在的门户路由。
- `BusinessEmbedView.vue` 以**相对路径**在同源 `<iframe>` 中承载 Frappe 页面（同源是前提：Frappe 发 `X-Frame-Options: SAMEORIGIN`，端口不同即不同源会被浏览器拦截）。
- 浏览器实测通过：登录后地址栏停在 5178；点击「考勤」在门户内容区加载真实 Desk 页面；`iframe.contentDocument` 可访问（同源的直接证据）。

### R3 接真实数据（Task 8–10，Owner 已授权）

- `docker-compose.yml` 新增 **8 处挂载 + 6 处 `PYTHONPATH`**（共 14 行）指向 `hbos_portal`。
- 重建 **5 个 app 容器**：`backend` / `scheduler` / `queue-long` / `queue-short` / `websocket`。**未重建 `frontend`(nginx)、未动 `db`。**
- `hbos_portal` 安装进运行中的 `frontend` site，并跑了 `migrate`；`list-apps` 由 4 App 变为 5 App（新增 `hbos_portal 0.1.0`）。

### R4 生产形态（未启动）

nginx 分发门户构建产物、生产构建须设 `VITE_BASE=/hbos/`（否则 Vite 的 `dist/assets/` 与 Frappe 的 `/assets/` 撞路径）。**本任务会改动 nginx 容器与 site 入口，必须取得 Owner 明确授权后才能开始；R4 未授权前，R1–R3 结论不得表述为「生产可用」。**

## 验证结果（均已独立复现）

- 考勤测试全量 **458 通过**（本轮前基线 445；+12 契约测试、修复波 +1）。
- `hbos_portal` 测试 **14 通过**。
- 前端 `npm run build`（`vue-tsc -b && vite build`）通过。
- **判定核心逐字节不变**：`pairing.py`、`api.py`、`rule_lists.py` 相对 `93ae18a` 由 `git diff --stat` 返回**空**，多轮不同审查者反复复核一致。这是本轮**最重要的约束**。
- **装 + migrate 后的零副作用断言**：
  - `tabAttendance` 31541 → 31541；`tabEmployee` 711 → 711。
  - `tabEmployee Checkin` 58863 → 58863（**活表**，`sync_delicloud_checkin` 每 10 分钟写入，判据为**单调不减 + 合理上界**，非逐值相等）。
  - `stopped=0` 的 `Scheduled Job Type` 104 → 104，**名称清单逐字节相同**（`hbos_portal` 未引入新定时任务）。
- **frappe 模式端到端对账**：门户摘要四项指标与后端权威 `dashboard_data.get_data()` **逐值一致**——异常人员 **388**、本周迟到 **0**、本周早退 **0**、本周缺勤 **2234**。门户只投影、不重算。
- iframe 来源为 **5178**（与门户同源），frame 标题为真实考勤仪表盘标题，且保持登录态。
- **普通员工门户准入按设计不开放**：仅 `HR User` / `HR Manager` / `System Manager` / `Administrator` 的 `can_enter` 为 true；`Employee` 角色用户与 `Guest` 均为 false。源自 portal 分支 P3-ATT-1（待个人考勤 native UX 与授权契约完成后才扩大），**不是缺陷**。

## 必须记录的三项

### (a) 对另一工作线的活副作用（必须记录在案）

本分支执行 `migrate` 时，Frappe 的 `remove_orphan_doctypes()`（`frappe/migrate.py:188`）**移除了 DocType `HBOS Attendance Policy Assignment` 的元数据记录**。

- **数据完好**：表 `tabHBOS Attendance Policy Assignment` 与其 **422 行业务数据**（含 `employee` / `employee_number` / `employee_name` / `policy_type`）无损；仅 `tabDocType` 记录消失，导致这 422 行**经 app 暂不可达**。
- **根因**：本分支不含该 DocType 的源文件（源只存在于 `main`，3 个文件，`creation` 2026-09-24），而 `main` **不是**本分支基线的祖先。`remove_orphan_doctypes()` 以 `get_controller(doctype)` 是否抛 `ImportError` 判定孤儿，故被判为孤儿。
- **可复现**：**只要在本分支再跑一次 `bench migrate`，该记录会被再次移除。**
- **恢复方式**：从 `main` 取回那 3 个文件 → `migrate` → 记录重建并指向现有表 → 422 行恢复可达。
- **Owner 裁定（2026-09-28）**：**暂不处理**。数据完好、可恢复，预期随两条工作线合并自然回归。

### (b) 四项门禁破例（均经 Owner 明确授权）

本轮触及以下既有禁令，**均经 Owner 明确授权**（记录于设计文档 §7）：

| 禁令来源 | 条文 | 处置 |
|---|---|---|
| `CLAUDE.md` | 不写 Docker Compose | 破例：新增挂载 + `PYTHONPATH` |
| `CLAUDE.md` | 不做前端驾驶舱 | 破例：本工作流即驾驶舱形态 |
| `docs/CURRENT_MILESTONE.md` | 不启动大型 Vue/React 前端 | 破例：启动 portal 前端工程 |
| portal 分支实施计划 §5 | 不用 iframe 作为第一阶段架构 | 破例：Owner 选定同域 iframe |

**破例范围严格限于上述四项。** 其余禁令继续生效，特别是：不修改 Frappe / ERPNext / HRMS 核心源码、不提交 `.env` / 密钥 / 真实数据、不执行 `docker compose down -v`、不删除 volume、不重建 `frontend` site。

### (c) 结转的已知缺口（记录，不修）

- **Vite 代理覆盖缺口**：`/robots.txt`、`/sitemap.xml`、`/backups`、`/website_script.js` 在 Frappe（8080）有真实响应，但未被 Vite 代理，在 5178 被 Vite 的 SPA 兜底吞成 `200 text/html`。四者均**不阻断** iframe 内嵌考勤仪表盘（`/website_script.js` 实际为空，仅控制台报错）。如需覆盖应在后续轮次统一评估。
- **既有资源陈旧问题（非本轮引入）**：内嵌页面引用的 3 个 CSS bundle（`desk.bundle.VALCFTBN.css`、`erpnext.bundle.WTSCA2XE.css`、`report.bundle.CO7WV5RO.css`）在 5178 与 **8080 直连时同样 404**——页面引用了过期的构建哈希，与已记录的 hrms 前端无法重建问题**同根**。四条均不阻断仪表盘渲染。
- frappe 模式下 `resolve_route` 每次导航被调用两次（**刻意为之**：保持 iframe `src` 由后端解析而非 URL 派生）。
- 普通员工入口**按设计未开放**（见上，非缺陷）。
- **R4 前置项**：`VITE_PORTAL_DATA_MODE` 默认 `mock`；任何生产构建前必须设 `VITE_BASE=/hbos/`。两者列入 R4 门禁清单。

## 未做

- **R4 未启动**（nginx 分发 + `VITE_BASE=/hbos/` 需 Owner 另行授权）。
- 未 merge `origin/feature/hbos-portal-product`。
- 未修改 `pairing.py` / `api.py` / `rule_lists.py` 及任何考勤判定核心。
- 未新增 Inventory / LIMS 业务前端，未引入 `services/hbos_ocr`。
- 未在门户内以 Vue 重写考勤页面（native 模式）。
- 未开放普通员工门户入口（按设计）。
- 未修改 Frappe / ERPNext / HRMS 核心源码。
- 未提交 `.env`、密钥、token、真实员工数据、Excel / CSV。
- 未执行 `docker compose down -v`，未删除 volume，未重建 `frontend` site。
- 未重建 `frontend`(nginx) 与 `db` 容器。

## 主文档与关联文档

- 主文档（本轮交付记录）：本文件 `docs/milestones/M3_PORTAL_R1_HBOS门户工作台集成实施记录.md`。
- 设计文档：`docs/superpowers/specs/2026-09-28-HBOS门户工作台集成设计.md`。
- 实施计划：`docs/superpowers/plans/2026-09-28-HBOS门户工作台集成.md`。
