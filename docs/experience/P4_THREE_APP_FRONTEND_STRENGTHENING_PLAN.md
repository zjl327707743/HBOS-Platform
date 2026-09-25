# HBOS P4 — Three-App Frontend Strengthening Plan

> Status: **P4-F3/F6 DONE — Inventory V2 概览页已实现（Owner 已审）**
>
> Date: 2026-09-25
>
> Branch: `p4/inventory-frontend-audit`（off `feature/hbos-portal-product`）
>
> Entry condition: **SATISFIED** — P3 remote runtime and Owner local isolated preview both passed.

## 1. Purpose

The next frontend phase is not a simultaneous visual rewrite of Attendance, Inventory, and LIMS.

The goal is to make the three user-facing business applications feel like one HBOS product while preserving their domain authority, permission boundaries, and efficient operational workflows.

The governing model remains:

```text
HBOS Portal                V3 expressive experience
        |
        +-- Attendance      V2 dashboard / V1 operations
        +-- Inventory       V2 dashboard / V1 operations
        +-- LIMS            V2 dashboard / V1 operations
        |
Frappe Desk                V0 management console
```

## 2. Entry gates

Frontend implementation must not start until all of the following are true:

1. three-app Portal Registry and stable entries pass remote clean-site runtime;
2. Owner local `p3_workspace_runtime_smoke.sh` passes;
3. current user journeys are captured from the real running system;
4. a visual / interaction proposal is produced for the target surface;
5. Owner approves that proposal;
6. only then may implementation begin.

This follows `docs/frontend/FRONTEND_IMPLEMENTATION_GUIDE.md`.

## 3. Current application modes

### LIMS

Current mode: **native / Vue**.

Strength:

- already has an independent Vue application;
- Frappe Session and API patterns are established;
- operational pages are already separated from Desk.

Gap:

- its current token system predates the HBOS EA-4 / EA-5.4 design language;
- its shell is an engineering reference, not the final HBOS visual master;
- shared header, app switching, typography, spacing, status semantics, responsive behavior, and interaction primitives need convergence.

Recommended direction:

```text
Native LIMS
    -> retain domain routes and workflows
    -> adopt HBOS shared shell / tokens / status semantics
    -> keep V1 operational density
    -> use V2 only for dashboard / orientation surfaces
```

### Inventory

Current mode: **legacy / Desk-first**.

Current stable route:

```text
/hbos/inventory
        ->
/app/hbos-photo-intake
```

The intake page is an operational surface. It contains label image upload, OCR, human correction, master-data gap handling, warehouse selection, and draft stock-entry creation.

Recommended direction:

```text
Inventory
    -> keep ERPNext documents and reports in Desk
    -> keep photo intake as a V1 operational workflow
    -> align typography / spacing / states inside the custom Desk page
    -> only create a separate V2 Inventory dashboard if the user journey proves it is useful
    -> migrate legacy -> hybrid progressively
```

Do not rebuild Stock Entry, Warehouse, Batch, Purchase Receipt, Delivery Note, or stock reports as a parallel frontend merely for visual consistency.

### Attendance

Current mode: **legacy / manager-oriented Desk surface**.

Current stable route:

```text
/hbos/attendance
        ->
/app/hbos-attendance-dashboard
```

The current Portal entry remains limited to HR User / HR Manager / System Manager / Administrator. Ordinary Employee access is intentionally gated.

Recommended direction:

```text
Attendance manager experience
    -> V2 dashboard + V1 exception operations

Attendance employee experience
    -> first define personal data scope and permission contract
    -> then design a focused personal attendance UX
    -> only after that consider hybrid/native implementation
```

The employee experience must not be created by exposing the existing HR dashboard to ordinary employees.

## 4. Shared HBOS visual contract

All three applications should converge on the same product language without forcing identical layouts.

Shared baseline:

- Chinese font stack: PingFang SC / Noto Sans SC / Microsoft YaHei / system-ui;
- Latin and numeric stack: Inter / SF Pro / system-ui;
- 4px spacing system;
- shared radius scale;
- shared status semantics: neutral / info / success / warning / critical / processing / disabled;
- shared accessibility rules;
- shared focus treatment;
- shared loading / empty / error presentation;
- shared app identity and domain accent;
- shared HBOS header behavior for native/hybrid user-facing surfaces.

Visual intensity remains contextual:

```text
Portal / App Center          V3
Application dashboard       V2
Daily operational workflow  V1
Frappe management console   V0
```

## 5. First audit deliverable

Before frontend coding, capture the real running system for the same representative scenarios.

Required surfaces:

### Portal

- Home;
- My Work;
- App Center;
- Command Palette;
- three app-entry transitions.

### LIMS

- dashboard;
- task list;
- result review / entry;
- one dense data table;
- empty / loading / error state.

### Inventory

- photo intake initial state;
- OCR available / unavailable;
- recognition review;
- manual correction;
- draft creation;
- representative inventory report.

### Attendance

- HR dashboard;
- exception overview;
- one exception-processing flow;
- monthly summary;
- representative employee-personal concept only after permission scope is approved.

Capture widths:

```text
1440px desktop
1280px desktop
768px tablet where supported
390px mobile for native/hybrid user-facing surfaces
```

Desk management pages do not need a mobile redesign unless a real user journey requires it.

## 6. Audit dimensions

Each surface is reviewed against:

1. information hierarchy;
2. typography scale;
3. spacing rhythm;
4. navigation continuity;
5. status semantics;
6. primary-action clarity;
7. density and scanning efficiency;
8. loading / empty / error states;
9. keyboard and focus behavior;
10. responsive degradation;
11. permission visibility;
12. cross-app consistency.

The audit reports facts and gaps. It does not immediately rewrite UI.

## 7. Proposed execution order

```text
P4-F0  Runtime screenshot / journey baseline
P4-F1  Shared HBOS token + typography contract verification
P4-F2  LIMS shell and dashboard visual proposal
P4-F3  Inventory V1 intake + optional V2 dashboard proposal
P4-F4  Attendance manager + employee information architecture proposal
P4-F5  Owner visual / interaction gate
P4-F6  Implement one app at a time
P4-F7  Cross-app visual regression and runtime acceptance
```

LIMS is the preferred first implementation target after Owner approval because it already has the native Vue foundation and therefore gives the cleanest place to validate shared HBOS components without disturbing ERPNext operational forms.

### 7.1 执行状态（2026-09-25 更新）

Owner 已将本轮范围收敛为**只做 Inventory**（LIMS 与 Attendance 由他人负责，不在本机）。因此上面 F2 / F4 本轮不启动。

```text
P4-F0  Inventory 自定义面盘点 + 运行态基线          = DONE
P4-F1  Token / Typography 契约核对                  = DONE（用于 Inventory）
P4-F2  LIMS 方案                                    = NOT STARTED（他人负责）
P4-F3  Inventory 概览页方案 + 实现                  = DONE
P4-F4  Attendance 方案                              = NOT STARTED（他人负责）
P4-F5  Owner 视觉门                                 = PASS（2026-09-25，三份方案均已过审）
P4-F6  Inventory 概览 / 拍照识别 / 草稿复核 / 批次   = DONE（入库流程整条前端化）
P4-F7  跨应用回归                                   = 待三应用前端齐备后再做
```

**Inventory 概览页（本轮交付）**

- 原型与方案：`docs/frontend/P4_Inventory_V2概览页原型.html`、`docs/frontend/P4_Inventory_V2概览页视觉方案与页面结构.md`
- 实现：`frontend/hbos-portal-web/src/views/InventoryOverviewView.vue` 等
- 路由：`/hbos/inventory` 留在 Portal SPA（后端 identity 解析）；`/hbos/inventory/intake` 仍映射 Desk 页
- `migration_mode`：`legacy` → `hybrid`
- 视觉强度：V2；数据仅用既有 4 项 summary，**未新增任何 Provider 能力**

**Owner 口径修正（本轮）**

1. 仓管的操作全部在前端完成，**不跳 Frappe 后台**；后端是被调用的引擎。据此删除了方案中的 `Desk` 来源标签，并把入口区按**目标态**列全。
2. 侧边栏导航**由前端自己维护**，不再视为 Desk 工作台侧边栏的副本。
3. 尚未前端化的入口：可点，落到统一的「尚未实现」提示页（`/hbos/inventory/unavailable/:itemId`），不留死链接。

**本轮未做（有意）**

- 未把 Stock Entry / Purchase Receipt / Delivery Note / Batch / Warehouse / Item / 原生报表重做成前端页。后台能力原样保留，前端只做入口。
- 未新增 Provider 能力，概览页只用现有 4 项 summary。

**入库拍照识别 V1 页（已实现）**

- 原型与方案：`docs/frontend/P4_入库拍照识别V1原型.html`、`docs/frontend/P4_入库拍照识别V1视觉方案与页面结构.md`
- 实现：`frontend/hbos-portal-web/src/views/InventoryIntakeView.vue` + `src/services/intake.ts`
- 视觉强度 V1（无 aurora / 实底 / 布局稳定）；照片栏 sticky；底部动作条常驻，唯一 Primary
- 7 态：未上传 / 已上传待识别 / 服务不可用 / 识别中 / 待校对（有可疑） / 待校对（无可疑） / 已生成草稿
- 业务三条规则原样继承：不可用时如实提示不伪造、只生成草稿不直接入账、任何字段可人工改
- `/hbos/inventory/intake` 已原生进 Portal SPA —— Owner 报的「点入库拍照识别跳到后端」由此消除
- Desk 版页面里那个**失效且反口径**的「返回仓库工作台」按钮已删除（`data-route` 无人消费，实测点不动）

**草稿复核页 + 批次页（已实现，入库流程整条打通）**

- 原型与方案：`docs/frontend/P4_草稿复核与批次页原型.html`、`docs/frontend/P4_草稿复核与批次页视觉方案与页面结构.md`
- 实现：`InventoryDraftReviewView.vue`、`InventoryBatchView.vue`、`src/services/inventoryDocs.ts`
- 路由：`/hbos/inventory/draft/:draftName`、`/hbos/inventory/batch/:batchName`（后端按前缀 identity 解析，留在 SPA）
- **范围刻意收窄**：只服务「拍照识别建的草稿」（`Stock Entry.hbos_intake_batch` 非空）。
  通用 Stock Entry 表单前端化**另起一轮**，不在本轮。
- 入库流程三步现已全部在前端：拍照识别 → 草稿复核 + 提交 → 批次取货位卡 / 待检证

**入库流程三步（全部前端）**

```text
① 拍照识别 → 生成草稿          /hbos/inventory/intake
② 草稿复核 + 提交               /hbos/inventory/draft/:name
③ 取货位卡 / 待检证去贴货位      /hbos/inventory/batch/:name
```

**技术前提（已逐条查证）**：`frappe.client.submit` whitelisted；`release_gate.py` **不拦**
Material Receipt（待检物料本就该能入库）；`doc_gen` 在 `on_submit` 自动出 PDF 且**刻意吞异常**
（失败不能回滚入库），故「重新生成」按钮必须一并搬到前端，否则失败后无路可走；
`frappe.client.delete` 经 `check_permission_and_not_submitted` 天然只能删草稿。

**CSRF 令牌（已解决）**

上传照片与生成草稿都是 POST，Frappe 要求 `X-Frappe-CSRF-Token`；`frappe.sessions.get_csrf_token`
没有 `@frappe.whitelist()`，跨源前端取不到。**插一句事实澄清**：CSRF 校验是 Frappe 框架内置、
一直在跑，不是后加的限制；项目从未配置过 `ignore_csrf` / `allowed_referrers`。此前没暴露，
是因为 Portal 的接口调用**全是 GET**。

**已采用与 LIMS 同款做法**：`hb_inventory_app.hbos_inventory.api.get_csrf_token`
（`@frappe.whitelist()` + 转发 `frappe.sessions.get_csrf_token`），不发明新模式。

安全边界：不返回超出会话本身的信息——有 cookie 才有 token，没 cookie 拿不到 token，
拿不到就发不出合法 POST，故**未削弱 CSRF 防护**。实测访客调用返回 403。

**未采用**：配置 `allowed_referrers`（命中即跳过 CSRF 校验，是真正放宽防护）；前端自造 token
（不可行，token 由服务端生成存于 session）。

测试见 `apps/hb_inventory_app/tests/test_governance.py`（3 条）。前端侧接入
（`frappeClient.ts` 非 GET 前取 token 并缓存）将在入库页进入复刻阶段时一并做。

### 7.2 审计发现的既有缺陷（记录，未代为修改）

`FRONTEND_IMPLEMENTATION_GUIDE` 与 CLAUDE.md 均要求不扩大范围。以下为审计中确认、但**不属于本轮 Inventory 前端实现**的问题，仅记录：

1. `scripts/portal/p2_2_runtime_smoke.sh` 与 `p3_workspace_runtime_smoke.sh` 在容器内裸调 `python`（系统解释器无 `frappe`），**必然失败**，与 P4 §2 的入场 Gate 和 §10 的 PASS 记录相矛盾。`start_local_workspace.sh` 的同款缺陷本轮已修（改用 `bench console`）。
2. `.back-workspace span` 在 `<=1199px` 折叠断点未被隐藏，76px 宽栏里文字被挤成竖排。**LIMS 与 Inventory 侧边栏都存在**；本轮只对 `.inventory-sidebar` 加了限定修复，LIMS 处未动。
3. `.global-search` 在 `<768px` 未隐藏，390px 下被压到 89px 宽，占位文字逐字换行。属全局 `GlobalHeader`，影响所有应用，未修。
4. `ForbiddenView` 曾已实现并注册但无任何跳转接线，权限失败时用户看到的是 axios 原始英文报错。本轮已接线。

### 7.3 本轮附带修复（受限范围）

- `ForbiddenView` 接线：`frappeClient.ts` 保留 HTTP 状态码（`FrappeHttpError`），`portal.ts` 按成因归一化（Frappe 对「访客」与「无权限」都返回 403，须用 `frappe.auth.get_logged_user` 分辨），`PortalLayout.vue` 渲染 403 视图。
- `businessNavigation.ts` 回环主机名对齐：Frappe 的 `sid` 是 host-only Cookie，`localhost` 与 `127.0.0.1` 登录态互不相通，会导致点业务入口变成访客。仅在双方都是回环地址时对齐。
- `MobileAppNav.vue` 参数化：原为 LIMS 硬编码，改为 props 驱动并保留原默认值，LIMS 渲染不变。

Inventory and Attendance should follow only after the shared design language has been proven.

## 8. What must remain unchanged during visual work

Unless a separately approved domain change requires otherwise:

- authentication remains Frappe User + Frappe Session;
- business authorization remains in the business application;
- Portal does not own business facts;
- Attendance calculations remain Attendance-owned;
- Inventory stock facts remain ERPNext / Inventory-owned;
- LIMS quality facts remain LIMS-owned;
- stable `/hbos/<app>` product routes remain the Portal contract;
- no direct browser access to MariaDB;
- no business write operation is moved into Portal.

## 9. Definition of Ready for implementation

Frontend implementation for an app is ready only when:

```text
Real runtime baseline captured
+ target user journey named
+ V-level selected
+ page IA defined
+ token / component mapping defined
+ permission boundary documented
+ responsive behavior defined
+ Owner visual gate approved
= READY FOR IMPLEMENTATION
```

Until then, work remains in audit / design, not frontend coding.


## 10. P3 entry gate closeout

The P4 entry condition is now satisfied.

Owner local isolated preview authority:

```text
a6411fadaeccf644a47ffbf93595d00ce9e5b04b
```

Verified:

- Portal Home / App Center / My Work;
- Attendance / Inventory / LIMS navigation;
- Frappe Session continuity;
- Portal native route continuity;
- Inventory Summary;
- zero new anonymous volumes;
- preserved formal workspace / Docker runtime / volumes / Site.

Therefore P4-F0 may start immediately.

This authorizes **audit and design work** for all three app teams. It does not waive the per-app Owner Visual Gate before substantial implementation.
