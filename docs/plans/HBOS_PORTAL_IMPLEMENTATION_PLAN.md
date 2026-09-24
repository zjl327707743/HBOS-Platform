# HBOS Portal Implementation Plan

**状态：AUTHORIZED / PARALLEL WORKSTREAM**  
**分支：** `feature/hbos-portal-product`  
**目标：** 在不打断 M1-FIX 主业务治理线的前提下，正式启动 HBOS Workspace / Portal 产品线。

## 1. Authority

- GitHub repository：`zjl327707743/HBOS-Platform`
- 正式源码与文档 Authority：GitHub
- Owner：最终产品与阶段 Gate
- Portal branch：`feature/hbos-portal-product`
- 平台集成目标：`integration/hbos-platform-v1`
- `main`：保护分支，不直接开发

## 2. 与 M1-FIX 的关系

Portal 是并行产品工作流，不替代：

- M1-FIX Attendance 修复；
- Inventory clean candidate；
- LIMS clean candidate；
- `integration/hbos-platform-v1` 的平台集成职责。

当前主里程碑仍由 `docs/CURRENT_MILESTONE.md` 管理。

Portal 通过独立 Experience Architecture / Product Gate 管理。

## 3. 实施阶段

### Phase A — Design Engineering

- EA-5.3 Interaction Review
- EA-5.4 Component & Interaction Specification
- EA-5.5 Interaction QA / Responsive / Accessibility — COMPLETE / OWNER APPROVED

输出：
- 设计冻结文档
- Visual Baseline
- Design Tokens
- Component Contract

### Phase B — Vue Portal Skeleton — COMPLETE / OWNER APPROVED

创建：

```text
frontend/hbos-portal-web/
```

技术栈固定：

- Vue 3
- Ant Design Vue
- Vue Router
- Pinia
- Axios
- ECharts（按需）

本阶段仅复刻已批准原型，不接真实业务 API。

### Phase C — Portal Platform App

P1 Platform App Architecture 已形成基线，P2 可开始创建：

```text
apps/hbos_portal/
```

职责仅限：

- current-user bootstrap
- app registry
- feature / preference
- provider discovery
- stable route resolver
- Portal access boundary

不得成为 Attendance / Inventory / LIMS 业务逻辑层。

### Phase D — App Registration

先接三项现有业务应用：

- Attendance
- Inventory
- LIMS

初始允许：

- legacy
- hybrid
- native

稳定 HBOS 路由不随实现方式变化。

### Phase E — Data Adaptation

每个 APP 分别实现：

```text
access_context()
summary()
my_tasks()
search()
deep_link()
```

Portal 只消费 DTO。

### Phase F — Native App Migration

建议顺序：

1. Attendance
2. LIMS experience refactor
3. Inventory hybrid evolution

## 4. Commit Strategy

Portal 分支至少分为：

1. `docs: 正式启动 HBOS Portal 产品工作台并固化 EA-5 设计基线`
2. `feat: 初始化 HBOS Portal Vue 3 前端工程骨架`
3. `feat: 完成 EA-5.5 交互与响应式基线`
4. `feat: 初始化 hbos_portal 平台 App`
5. Provider / Registry / Integration 独立提交

禁止把设计文档、前端工程、后端平台 App、三业务 APP 适配塞入一个巨型提交。

## 5. 当前禁止事项

在本计划当前状态下：

- 不修改 Frappe / ERPNext / HRMS 核心源码；
- 不让 Portal 直接读业务 DocType；
- 不创建第二套 User / JWT / Role；
- 不创建 Portal 业务事实副本；
- 不用 iframe / micro-frontend 作为第一阶段架构；
- 不把 LIMS Workspace 当企业 Portal；
- 不把飞书 SSO 放入 Inventory；
- 不直接在 `main` 开发。

## 6. Ready for Platform Integration

Portal 可进入 `integration/hbos-platform-v1` 的最低条件：

- Vue Portal Skeleton 可构建；
- EA-5.5 Gate 通过；
- Portal / App boundary 无回退；
- App Registry Contract 稳定；
- Frappe Session 作为唯一运行时身份；
- Provider 错误可以单 APP 隔离；
- 基础 403 / 404 / Loading / Empty / Error 可用；
- 至少一项真实 Business App registration 通过测试。


## 7. Phase B Current Result — 2026-09-24

`frontend/hbos-portal-web/` 已正式初始化。

当前仍只使用 Mock Provider / DTO。

已包含平台级体验组件：

- Global Header
- App Switcher
- Notification Center
- Command Palette
- Portal Sidebar
- Home
- My Work
- App Center
- Profile / Settings
- 403 / 404
- LIMS App Shell
- Digital Twin Overview
- Pointer Atmosphere
- Reduced Motion

当前环境 `npm install` 因 npm registry 网络超时未完成，因此 build Gate 仍为 PENDING。不得将本轮状态描述为 production-ready 或 build-pass。


## 8. EA-5.5 Implementation

已进入交互与工程 QA：

- mobile Portal navigation；
- mobile LIMS navigation；
- keyboard Command Palette；
- skip links / focus；
- reduced motion；
- AntD theme mapping；
- LIMS V1 Result Review page；
- contextual Drawer；
- confirmation Modal。

EA-5.5 仍使用 Mock Provider，不连接真实业务 API。


## 9. EA-5.5 Build Gate Result

```text
HBOS Quality Gate: PASS
HBOS Portal Frontend Gate: PASS
EA-5.5 Engineering Gate: PASS
EA-5.5 Owner Gate: PENDING
```

Backend Phase C remains blocked until Owner closes EA-5.5.


## 10. P1 Platform Architecture Result — 2026-09-25

P1 架构基线已形成：

- `docs/experience/P1_HBOS_Portal平台App架构.md`

当前：

```text
EA-5.5 = COMPLETE / OWNER APPROVED
P1 = ARCHITECTURE BASELINE
P2 = READY TO IMPLEMENT
```

P2 只创建薄 `apps/hbos_portal` skeleton，不接 Attendance / Inventory / LIMS Provider。


## 11. P2 / P2.1 Implementation Result — 2026-09-25

P2 已创建 `apps/hbos_portal` 薄平台 App skeleton，并通过独立 Backend Gate。

Backend Gate PASS 项：Python compile、Contract/Registry unit tests、禁止业务 App 静态 import、禁止 Guest API、P2 禁止 DocType。

P2.1 已完成 Vue → Frappe Bootstrap Adapter：

```text
VITE_PORTAL_DATA_MODE=mock   → UI / Experience 开发
VITE_PORTAL_DATA_MODE=frappe → /api/method/hbos_portal.api.bootstrap.get_bootstrap
```

Frontend Gate 已真实通过 Node 22 / npm install / vue-tsc / Vite build / dist check。

P2.2 Runtime Smoke Test 已在真实 Frappe `frontend` site 通过。


## 12. P2.2 Runtime Smoke Result — 2026-09-25

真实本地 Worktree-safe Runtime Smoke 已完成：

```text
P2.2 = PASS
Guest Bootstrap = HTTP 403 / PASS
Authenticated Bootstrap = HTTP 200 / ok=true
Registry entries = 0
Registry failures = 0
Avatar = null / expected
Branding = PASS
Apps = [] / expected
Formal Attendance workspace = PRESERVED
Docker volumes = UNCHANGED
frontend site = PRESERVED
Business data = UNCHANGED
```

测试中临时安装 `hbos_portal`，验证结束后成功卸载并恢复原始 site app list。

Runtime Source HEAD：

```text
af8ca537bd77cffb714c4fbe2517c7108241d80b
```

已记录一个非阻断 Attendance hook import warning；P2.2 不越界修改 Attendance。

下一阶段：

```text
P3 — Business App Registration
```

PR #15 在至少一个真实 Business App Provider 完成注册和验证前保持 Draft。


## 13. P3-LIMS-1 First Real Provider — 2026-09-25

首个真实 Business App Provider 已完成：

```text
LIMS Manifest = PASS
LIMS Access Context = PASS
Frappe Hook Discovery = PASS
Portal Registry = ["lims"]
Registry failures = 0
Authenticated Bootstrap apps = ["lims"]
Stable App Entry = /hbos/lims
Provider data capabilities = []
Platform clean-site = PASS
```

Runtime authority：

- GitHub Actions Run `36036356941`
- `docs/experience/P3_LIMS_PROVIDER_REGISTRATION.md`

期间 clean-site 发现并修复 `hbos_portal` 缺 Frappe module package 的可复现性问题。

当前：

```text
P3 Business App Registration = IN_PROGRESS
P3-LIMS-1 = COMPLETE
P3-LIMS-2 Stable Deep-link Adapter = NEXT
```

本阶段仍不接 Summary / Tasks / Search。
