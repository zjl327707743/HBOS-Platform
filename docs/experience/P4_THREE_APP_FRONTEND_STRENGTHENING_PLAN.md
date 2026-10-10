# HBOS P4 — Three-App Frontend Strengthening Plan

> Status: **P4-F0 READY / FRONTEND AUDIT & DESIGN AUTHORIZED**
>
> Date: 2026-09-25
>
> Branch: `feature/hbos-portal-product`
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
