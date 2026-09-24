# EA-1 — HBOS Surface Responsibility

> Status: **BASELINE**
>
> Scope: define the permanent responsibility boundary among HBOS Workspace / Portal, HBOS Business Applications, and HBOS Management Console.
>
> Last updated: 2026-09-24

## 1. Core model

HBOS has three product surfaces:

```text
                    HBOS
                     │
        ┌────────────┴────────────┐
        │                         │
 HBOS Workspace              Management Console
 Portal / user layer            Frappe Desk
        │                         │
        ├── Attendance            │
        ├── Inventory             │
        ├── LIMS                  │
        └── future apps           │
        │                         │
        └────────────┬────────────┘
                     │
              Application API
              Domain Services
                     │
        ERPNext / HRMS / Frappe
                     │
                  MariaDB
```

These surfaces are **not independent systems of record**. By default they use the same Frappe site, identity, domain services, permissions, and authoritative business data.

The difference is product responsibility, not database ownership.

## 2. Surface definitions

### 2.1 HBOS Workspace / Portal

Portal is the enterprise entry point and global experience shell.

Portal owns:

- enterprise home;
- global navigation;
- app discovery and App Center;
- current-user context;
- cross-app task aggregation;
- notifications entry;
- global search / command entry;
- recent items and shortcuts;
- user preferences;
- Portal feature flags;
- stable product routes;
- Portal-level access visibility.

Portal does **not** own:

- attendance calculation;
- stock ledger;
- inventory release logic;
- LIMS testing / review / approval rules;
- COA logic;
- scheduling algorithms;
- business-domain status machines.

### 2.2 HBOS Business Applications

Business applications own domain workflows and user-facing professional work.

Current applications:

- Attendance;
- Inventory;
- LIMS.

Future examples:

- Production;
- Equipment;
- Maintenance;
- EHS;
- Training;
- Procurement;
- AI;
- Digital Twin;
- Energy.

Business applications own:

- domain workflow;
- domain permissions;
- business operations;
- domain-specific dashboards;
- local navigation;
- task projection;
- summary projection;
- search projection;
- stable deep-link resolution;
- authoritative application APIs.

### 2.3 HBOS Management Console

HBOS Management Console is the product name for the administrative surface implemented primarily through Frappe Desk.

It owns or is the preferred surface for:

- master data administration;
- platform configuration;
- role / permission administration;
- implementation settings;
- integration settings;
- advanced diagnostics;
- technical audit;
- low-frequency expert administration;
- emergency / controlled operations where explicitly allowed.

Frappe Desk is retained. It is not the primary employee product surface.

## 3. Surface responsibility matrix

| Capability | Portal | Business App | Management Console |
|---|---|---|---|
| Login entry | Primary user entry | Reuse session | Available |
| Current user | Present / aggregate | Consume | Administer |
| Enterprise home | **Owner** | — | — |
| App Center | **Owner** | Register | — |
| Global search | Aggregate | Provide results | Back-office search |
| My Work | Aggregate | **Compute / project** | Inspect if needed |
| Notification center | Aggregate | Produce domain events/messages | Administer |
| Business dashboard | Overview only | **Owner** | Optional reporting |
| Domain operation | — | **Owner** | Advanced / controlled |
| Domain rules | — | **Authority** | Must not bypass |
| Workflow | — | **Authority** | Configure / administer |
| Data scope | App visibility only | **Authority** | Configure |
| Master data | — | Consume | **Preferred owner surface** |
| System config | — | — | **Owner** |
| Technical diagnostics | — | Produce telemetry | **Owner** |
| Portal preferences | **Owner** | Consume | Administer if required |

## 4. One data truth

A business fact must have one authoritative source.

Examples:

- Attendance status is owned by Attendance / HRMS facts.
- Batch quantity and stock movement are owned by Inventory / ERPNext stock facts.
- Test result and approval state are owned by LIMS.
- Portal cards and My Work items are projections of these facts.

Forbidden architecture:

```text
LIMS result
   ↓ copy
Portal result state
```

Required architecture:

```text
LIMS authoritative state
        ↓
   LIMS Provider
        ↓
Portal projection
```

## 5. Shared database does not mean direct access

Portal, Desk, and business apps may operate on the same underlying Frappe site and MariaDB database. This does **not** authorize Portal to query arbitrary business DocTypes.

User-facing access should follow:

```text
Vue / Portal
   ↓
Application API / Provider
   ↓
Domain Service
   ↓
Frappe ORM / DocType
   ↓
MariaDB
```

Portal must not become a generic `frappe.get_all()` client over all business data.

## 6. Business operation vs administrative operation

### Business operation

Examples:

- approve a test result;
- release a batch;
- close a maintenance order;
- regenerate attendance;
- confirm stock movement.

These operations must go through domain services / workflow guards.

Changing fields in Desk must not be a shortcut that bypasses the same rule.

### Administrative operation

Examples:

- maintain a category;
- edit configuration text;
- change integration mapping;
- maintain a master list;
- enable a feature flag.

These may appropriately remain Desk-first.

## 7. Desk-aware does not mean Desk-first

Every new HBOS app should consider the Management Console, but it does not need a Desk Workspace as its primary product.

A new app may be designed directly as:

```text
hb_training_app
├── Domain Models
├── Services / APIs
├── Permissions
├── Admin DocTypes / Desk
└── hbos-training-web
```

Frappe App creation and Frappe Workspace creation are separate decisions.

## 8. New application standard

A mature HBOS application should expose five conceptual layers:

```text
Domain
  ↓
Application / Domain API
  ↓
┌───────────────────┬─────────────────────┐
│ User Experience   │ Management Console  │
│ Vue + HBOS Design │ Frappe Desk         │
└───────────────────┴─────────────────────┘
  ↓
Portal Manifest / Provider
```

The business app may remain usable without Portal. Portal is an entry and experience layer, not the domain runtime.

## 9. Existing app migration modes

Existing applications may migrate progressively:

- `legacy` — Portal launches an existing Desk workspace / page.
- `hybrid` — common user journeys use HBOS Vue; advanced operations still use Desk.
- `native` — daily user workflows use HBOS App; Desk is administration only.

Recommended direction:

| App | Current direction | Target |
|---|---|---|
| Attendance | legacy | native |
| Inventory | legacy | hybrid → native |
| LIMS | native engineering base, UX redesign required | native |

## 10. Management Console transitions

For authorized users, HBOS may expose an explicit **Enter Management Console** action.

Requirements:

- ordinary users do not see it;
- entry is visually explicit;
- Management Console identifies itself as an administrative context;
- there is a clear **Return to HBOS** path;
- entering Desk does not create a second login;
- Desk permissions remain authoritative for Desk operations.

## 11. Surface laws

1. Portal is an experience shell, not a business owner.
2. Business apps own domain truth and operations.
3. Desk is administration, not the default employee product.
4. Same database does not imply unrestricted cross-surface access.
5. Critical business rules live on the server and cannot exist only in Vue.
6. A business fact has one source of truth.
7. New apps do not need to repeat the historical “Desk Workspace first” pattern.
8. Data ownership is reused; legacy UI is not automatically reused.

## 12. Review gate

A feature is not ready for implementation until the team can answer:

- Which surface owns it?
- Which domain owns its business truth?
- Is it a user operation or an administrative operation?
- Can Desk bypass its business rule?
- Does Portal need only a projection, or is business logic leaking into Portal?
- Can the same capability survive a future frontend replacement without data migration?

If ownership is unclear, resolve the surface boundary before coding.
