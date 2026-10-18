# HBOS 门户工作台集成实施记录

项目名称：新乡海滨智能运营管理平台。

轮次：**M3-PORTAL-R1**（HBOS 门户工作台集成，分支 `feature/hbos-portal-workbench`）。

状态：**REVIEWING**（**R1–R4 均已交付**）。

> **后续交付**：2026-09-29 在本轮基础上追加「考勤页原生化 + Desk 共享视觉层」——把考勤仪表盘 / 人员管理 / 部门看板三页从本文件所述的同域 iframe 内嵌改为**门户 SPA 原生页**（`migration_mode` 由 `legacy` 改 `native`），并给 Desk 侧 6 个考勤页接入共享视觉层。该交付**未认领新里程碑编号**，记录见 `docs/milestones/M3_考勤页原生化与Desk共享视觉层.md`。本文件所述 R1–R4 的内容与结论不变；iframe 通路（`BusinessEmbedView.vue`、Vite 12 条代理前缀、`businessRoutes.ts` 白名单）**保留未删**，其他 App 仍可能使用。

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
| **R4 生产形态** | 独立门户容器 + 生产构建参数固化 | 已授权 | **已交付** |

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

### R4 生产形态（已交付，Owner 2026-09-28 授权）

**未走原设计的「改生产 nginx」路径。** 侦察发现不可行：`/etc/nginx/conf.d/frappe.conf` 由 `nginx-entrypoint.sh:50` 在每次容器启动时从 `/templates/nginx/frappe.conf.template` 重新生成，故 `docker cp` 不持久；而往 `conf.d/` / `sites-enabled/` 另放文件无法向既有 server 块注入 `location`（同端口再起 server 块会因 `server_name` 不匹配而永远命不中）；要持久改只能接管上游 113 行模板，且改它需重建 `frontend` 容器＝**8080 短暂停机**，而该端口承载约 700 人在跑的真实考勤。

Owner 裁定改用**独立门户容器**：

- 新增 compose 服务 `portal`，端口 `${PORTAL_PORT:-8081}`；复用 `frappe/erpnext` 镜像（Docker Hub 不通，无法拉 nginx 镜像），**绕过其 entrypoint**（该 entrypoint 会 `rm -rf` 并重建 `sites/assets`，对本用途是有害写入）；并以 `tmpfs` 接管镜像声明的 `sites` / `logs` 两个 VOLUME，避免生成游离于项目命名空间外的匿名卷。
- 门户容器**不挂载 `sites` / `assets` 卷，也不挂载任何 Frappe App 目录**。
- `frontend/hbos-portal-web/deploy/portal.nginx.conf`：`/hbos/` 服务产物 + SPA 回退到 `index.html`；其余路径反代 `frontend:8080`；socket.io 单独一条转发 WebSocket 升级。
- 生产构建参数固化于 `frontend/hbos-portal-web/.env.production`（Vite 于 production 模式自动加载，故 `npm run build` 即生产构建）：`VITE_BASE=/hbos/` **与** `VITE_PORTAL_DATA_MODE=frappe`，**缺一不可**（只设前者会让生产走 mock 模式显示假数据）。

**生产形态暴露并修复的两个缺陷**（dev 下都看不到）：

1. **URL 被拼两次（首页变 `/hbos/hbos`）**：路由用 `createWebHistory(import.meta.env.BASE_URL)`，而路由表已写死 `/hbos` 前缀；dev 下 `BASE_URL='/'` 恰好正确，生产 `VITE_BASE='/hbos/'` 即叠加。已固定为 `createWebHistory('/')`——`VITE_BASE` 只负责资源路径，不兼任 history base。
2. **静态标题仍为 `HBOS Portal Prototype`**：已改为 `HBOS · 海滨智能运营工作台`。

**R4 验收（均已实测）**：产物前缀 `/hbos/assets/` 且裸 `/assets/` 引用为 0；数据模式固化为 `frappe` 字面量；8081 与 8080 **逐路径 11 条全部一致**（`/desk` 的 `Server: nginx/1.22.1` 证明穿透到 Frappe），重定向均为相对路径，`X-Frame-Options: SAMEORIGIN` 透传，socket.io 升级 101；**浏览器实测** URL 为 `/hbos/`、身份为真实 `Administrator`（非 mock `Carlo`）、点考勤后 iframe 来源同源且 `contentDocument` 可访问、frame 为真实仪表盘；**四指标逐值对账** 388/388、0/0、0/0、2210/2210（另出勤率 47.1%/47.1、总人数 696/696）；**生产栈未受影响**（`frontend` Up 8 days、`db` / redis 未动、`tabAttendance` 31541、`tabEmployee` 711 不变）。

**R4 遗留**：(i) 门户与 Frappe 分属 **8081 / 8080 两个端口**——同容器内是单一来源，但对外仍是第二个入口；收敛为 8080 单端口需接管上游 nginx 模板并接受一次 `frontend` 重建（8080 短暂停机）。(ii) 首次创建 portal 容器产生 **2 个匿名卷**，现以 tmpfs 接管、重建不再新增；那 2 个孤儿卷按「不删除 Docker volume」硬约束**未清理**，待 Owner 决定。

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

### (a) 曾发生并已修复的 migrate 副作用（已恢复）

> **当前状态：已恢复，不再是未决问题。** 保留本节是因为该机制（`remove_orphan_doctypes()` 删除取自其他工作线的 DocType 记录）在本分支上具有一般性，值得留档。

本分支执行 `migrate` 时，Frappe 的 `remove_orphan_doctypes()`（`frappe/migrate.py:188`）**移除了 DocType `HBOS Attendance Policy Assignment` 的元数据记录**。

- **数据完好**：表 `tabHBOS Attendance Policy Assignment` 与其 **422 行业务数据**（含 `employee` / `employee_number` / `employee_name` / `policy_type`）无损；仅 `tabDocType` 记录消失，导致这 422 行**经 app 暂不可达**。
- **根因**：本分支不含该 DocType 的源文件（源只存在于 `main`，3 个文件，`creation` 2026-09-24），而 `main` **不是**本分支基线的祖先。`remove_orphan_doctypes()` 以 `get_controller(doctype)` 是否抛 `ImportError` 判定孤儿，故被判为孤儿。
- **已修复**（2026-09-28，提交 `3897c59`）：从 `main` 取回 **4 个文件**——DocType 3 文件 **加上 `policy_registry.py`**（必需：controller 首行即 import 它，只取 3 文件仍会判孤儿、migrate 仍会再删）。`migrate` 后 `tabDocType` 记录重回 1、422 行仍在、`frappe.client.get_count` 与 ORM 实取均可达。**再次 `migrate` 后记录仍在，持久性已验证。** 判定核心仍零改动。

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
- **R4 门禁项已落实**：`VITE_PORTAL_DATA_MODE` 与 `VITE_BASE` 均已固化于 `.env.production`，`npm run build` 即生产构建。

## 未做

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
