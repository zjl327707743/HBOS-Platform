# EA-2 — HBOS User Journey & Information Architecture

> Status: **BASELINE**
>
> Scope: define how employees, supervisors, professional users, business administrators, and system administrators navigate HBOS.
>
> Last updated: 2026-09-24

## 1. Experience objective

HBOS is moving from an object-driven ERP experience to a person-, task-, and journey-driven enterprise experience.

The product should answer:

1. What matters to me today?
2. What requires my action?
3. What should I do next?

Users should not need to understand DocTypes or internal module boundaries to complete routine work.

## 2. Primary personas

### 2.1 Employee

Primary questions:

- Is my attendance normal today?
- What is my schedule?
- Do I have exceptions?
- What tasks or notifications require attention?

Routine employees should normally remain inside HBOS Workspace and business apps, not Frappe Desk.

### 2.2 Supervisor

Primary questions:

- How is my team doing today?
- Who is absent or abnormal?
- Which actions require my approval or intervention?
- What operational risk needs attention?

Supervisors require both personal and team context.

### 2.3 HR professional

Repository roles currently include `HR User` and `HR Manager`.

Preferred user journeys:

- today's attendance;
- attendance exceptions;
- monthly attendance;
- scheduling;
- leave / adjustment workflows;
- import / controlled operations;
- team / company analytics.

Underlying objects such as Employee Checkin and Attendance remain domain facts, not primary IA labels.

### 2.4 Warehouse professional

Repository roles currently include `Stock User` and `Stock Manager`.

Preferred user journeys:

- inbound;
- put-away;
- outbound;
- picking;
- batch lookup;
- inventory lookup;
- expiry risk;
- counting;
- warehouse task execution.

Advanced ERP transactions may remain in Management Console during hybrid migration.

### 2.5 LIMS / Quality professional

Current LIMS role model includes:

- LIMS Analyst;
- LIMS Reviewer;
- LIMS QA;
- LIMS QA Manager;
- LIMS QP;
- LIMS Manager.

The same `/hbos/lims` application must adapt the visible work and capabilities to the current user.

Example focus:

| Role | Primary experience |
|---|---|
| Analyst | my tests, in-progress testing, result entry |
| Reviewer | review queue, exceptions requiring review |
| QA | QA review / approval, OOS, COA, retention, stability |
| QA Manager / QP | high-risk decisions, controlled approvals, release-related work |
| LIMS Manager | laboratory operations, workload, progress, configuration entry |

`System Manager` is a technical administration role and should not be treated as the normal business approver for quality decisions. Exceptional intervention should be controlled and audited.

## 3. Common entry journey

```text
Browser
  ↓
/hbos
  ↓
HBOS Login / existing Frappe session
  ↓
HBOS Bootstrap
  ↓
Current user + visible apps + tasks + preferences
  ↓
Personalized HBOS Workspace
```

Authentication source may include password login or future Feishu SSO, but runtime identity converges on Frappe User + Frappe Session.

## 4. Personalized home

Portal Home should not be identical for every user.

The shell remains consistent, but content emphasis is driven by responsibilities and tasks.

Examples:

### Employee

```text
Today
Attendance: Normal
Pending actions: 1
Messages: 1
Recent apps
```

### QA user

```text
9 MY ACTIONS
3 review
2 approval
1 OOS
3 stability
```

### Warehouse manager

```text
12 OPERATIONS
4 inbound
5 outbound
2 counting
1 expiry risk
```

The principle is:

```text
same shell
+ different responsibility context
```

## 5. Global information architecture

Keep Portal-level navigation small:

```text
/hbos
    Home

/hbos/work
    My Work

/hbos/apps
    App Center

/hbos/search
    Global Search

/hbos/messages
    Messages

/hbos/profile
    Profile / preferences
```

Do not turn every business app into a permanent first-level Portal navigation item.

Apps are primarily entered through:

- App Center;
- App Switcher;
- recent apps;
- pinned apps;
- My Work deep links;
- global search / command palette.

## 6. Global navigation vs local navigation

HBOS uses two navigation layers.

### Global layer

Owned by HBOS:

- brand;
- app switcher;
- global search / command;
- notifications;
- profile;
- Management Console entry for authorized users.

### Local application layer

Owned by the business app.

Example LIMS:

```text
HBOS Global Header
────────────────────────
LIMS Local Navigation
├── My Work
├── Testing
├── Quality
├── Retention
├── Stability
└── Compliance
```

Global navigation must not absorb every local business menu.

## 7. Stable routes

Stable product entry points:

```text
/hbos
/hbos/work
/hbos/apps
/hbos/search
/hbos/messages
/hbos/profile

/hbos/attendance
/hbos/inventory
/hbos/lims
```

These are product contracts. Internal implementations may change from Desk workspace to Vue SPA without changing the stable HBOS route.

## 8. My Work

My Work is a core HBOS surface.

Recommended views:

- Today;
- This week;
- Overdue;
- Waiting;
- Completed.

Task examples:

```text
LIMS
Review result RESULT-001
Due 16:00

Attendance
Resolve employee attendance exception

Inventory
Confirm outbound task
```

Portal aggregates tasks. Business apps own task calculation.

## 9. Deep-link principle

A task should open the work object or action directly.

Bad journey:

```text
Portal task
→ LIMS home
→ result menu
→ list
→ search
→ result
```

Preferred journey:

```text
Portal task
→ /hbos/lims/results/RESULT-001/review
```

The same principle applies to Attendance and Inventory.

## 10. Attendance IA v1

```text
Attendance

My Attendance
├── Today
├── Monthly
├── My Exceptions
└── My Schedule

Team
├── Today's Attendance
├── Exception Handling
└── Scheduling

Operations
├── Monthly Attendance
├── Leave / Adjustment
└── Data Import

Analytics
└── Attendance Analysis
```

Advanced data / rule administration remains in Management Console.

## 11. Inventory IA v1

```text
Inventory

My Work
├── Today's Tasks
└── Risks

Inbound
├── Pending Inbound
├── Capture / OCR
└── Put-away

Outbound
├── Pending Outbound
└── Picking

Inventory
├── Inventory Lookup
├── Batch Trace
├── Location
└── Expiry

Counting
├── Count Tasks
└── Variance Handling

Analytics
└── Warehouse Overview
```

Complex Stock Entry, Stock Reconciliation, Item / Warehouse administration, and advanced ERP reports may remain in Management Console during hybrid migration.

## 12. LIMS IA v1

```text
LIMS

My Work
├── My Testing
├── My Active Tests
├── My Review
└── My Approval

Testing
├── Samples
├── Test Tasks
└── Results

Quality
├── OOS / Exceptions
├── COA
└── Specifications

Retention
├── Retention Register
├── Observation Tasks
└── Use / Disposal

Stability
├── Protocols
├── Samples
├── Timepoints
├── Results
├── Reports
└── Changes

Compliance
├── Audit
└── Traceability
```

Navigation is capability-filtered. Users should not see actions they cannot perform.

## 13. Management Console transition

Ordinary employees should not see a Management Console entry.

Authorized users may access it through a deliberate action such as:

```text
Profile
→ Enter Management Console
```

Requirements:

- the change of context is explicit;
- Management Console is visually identified;
- the same Frappe session is reused;
- there is a clear Return to HBOS action.

## 14. Existing app migration journeys

### Attendance

```text
Current Desk workspace
→ Portal stable entry
→ new Attendance IA / UX
→ hbos-attendance-web
→ legacy workspace becomes admin / fallback
```

### Inventory

```text
Current warehouse workspace
→ Portal entry
→ hybrid Inventory
   ├── common tasks in Vue
   └── advanced ERP operations in Desk
→ progressive native migration
```

### LIMS

```text
Existing Vue engineering assets
→ keep domain / API investments
→ redesign IA and visual system
→ align with HBOS Design System
→ native HBOS LIMS
```

## 15. Future app journey

A new app should be able to start directly with HBOS standards:

```text
Install app
→ register Portal provider / manifest
→ Portal discovers app
→ access is evaluated
→ /hbos/<app>
→ app-local experience
```

It is not required to create a user-facing Frappe Workspace first.

## 16. Experience laws

1. User first — show work and decisions, not raw data objects.
2. One identity — applications reuse the same Frappe user / session.
3. One truth — one authoritative business state.
4. Deep-link work — users should reach the action, not repeat navigation.
5. Apps own business — Portal aggregates but does not calculate domain rules.
6. Desk is administration — routine users should not depend on Desk.
7. Backend enforces truth — business rules must survive any frontend.
8. Global navigation stays small — business complexity belongs inside apps.

## 17. Product map

```text
HBOS
│
├── Home
├── My Work
├── Apps
├── Search
├── Messages
├── Profile
│
├── Attendance
│   ├── My Attendance
│   ├── Exceptions
│   ├── Schedule
│   ├── Team
│   ├── Operations
│   └── Analytics
│
├── Inventory
│   ├── My Work
│   ├── Inbound
│   ├── Outbound
│   ├── Inventory
│   ├── Batch / Location
│   ├── Counting
│   └── Analytics
│
├── LIMS
│   ├── My Work
│   ├── Testing
│   ├── Quality
│   ├── Retention
│   ├── Stability
│   └── Compliance
│
└── Management Console
    └── Frappe Desk
```

## 18. Review gate

A user journey is not ready for frontend implementation until:

- the persona is known;
- the primary task is known;
- the authoritative domain operation is known;
- the stable HBOS route is defined;
- the user is not forced through unnecessary module / list / search steps;
- permission-dependent content is defined;
- the Desk fallback, if any, is explicit;
- the return path to HBOS is clear.
