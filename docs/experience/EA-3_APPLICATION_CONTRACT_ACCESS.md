# EA-3 — HBOS Application Contract & Access Model

> Status: **BASELINE**
>
> Scope: define the stable experience contract between HBOS Portal and business applications.
>
> Last updated: 2026-09-24

## 1. Goal

Portal must be able to compose Attendance, Inventory, LIMS, and future apps without knowing their internal DocTypes, workflow implementation, or database schema.

Portal should understand only a stable HBOS application contract.

```text
Portal
  │
  ├── does not know Employee Checkin
  ├── does not know Batch / Stock Entry
  ├── does not know HBOS Test Result
  └── does not know app-internal state machines
        ↓
HBOS Application Contract
        ↓
Business App Provider
        ↓
Domain / Application API
```

## 2. Two integration planes

### 2.1 Experience integration

Used for:

- app discovery;
- app visibility;
- summary cards;
- My Work;
- global search;
- deep links.

This is handled through the HBOS Application Contract.

### 2.2 Domain integration

Used for business-to-business facts and actions.

Example:

```text
LIMS release
  ↓
domain integration
  ↓
Inventory release projection
```

Portal is not an enterprise service bus and must not mediate domain truth between apps.

## 3. Contract capabilities

Contract v1 defines:

- Manifest;
- Access;
- Summary;
- Tasks;
- Search;
- Deep Link.

Future optional capabilities may include:

- notifications;
- commands / safe actions;
- activity;
- AI context.

An app implements only the capabilities it supports.

## 4. Provider discovery

Each business app registers a provider through a Frappe extension point / hook.

Conceptually:

```python
hbos_portal_provider = [
    "hb_lims_app.hbos_lims.portal.provider.get_provider"
]
```

Portal discovers providers dynamically.

Forbidden:

```python
import hb_lims_app
import hb_inventory_app
import hb_attendance_app
```

inside Portal orchestration.

The contract is the dependency; app internals are not.

## 5. Provider interface

Conceptual interface:

```text
manifest()
access_context()

summary()       optional
my_tasks()      optional
search()        optional
```

Portal invokes only explicitly supported, allowlisted experience capabilities.

## 6. Manifest contract

Example:

```json
{
  "contract_version": 1,
  "id": "lims",
  "title": "实验室质量管理",
  "short_title": "LIMS",
  "description": "检验、质量、留样与稳定性管理",
  "icon": "flask",
  "accent": "emerald",
  "order": 30,
  "migration_mode": "native",
  "route": "/hbos/lims",
  "capabilities": ["summary", "tasks", "search"]
}
```

### Stable app id

`id` is a permanent platform identifier.

Examples:

- `attendance`
- `inventory`
- `lims`
- `equipment`

Brand names may change. Stable IDs should not.

## 7. Migration mode

Supported values:

- `legacy`
- `hybrid`
- `native`

The stable HBOS route remains independent of implementation mode.

Example:

```text
/hbos/attendance
```

may resolve to a Desk workspace today and a Vue route later without changing Portal task links.

## 8. Manifest is not authorization

Manifest metadata must not become the final permission system.

Avoid relying on static declarations such as:

```json
{
  "requiredRoles": ["LIMS Manager"]
}
```

Complex applications may require role, data scope, workflow state, and segregation-of-duties checks.

Authorization is evaluated by the application.

## 9. Access Context

Each app answers:

> What can the current authenticated session user access?

Example:

```json
{
  "app_id": "lims",
  "can_enter": true,
  "capabilities": [
    "sample.read",
    "result.submit",
    "result.review",
    "coa.read"
  ],
  "scopes": {
    "company": ["HB"],
    "laboratory": ["QC"]
  }
}
```

### Portal usage

Portal normally consumes `can_enter` to decide app visibility and stable route access.

Portal should not need to understand LIMS role names.

### Business-app usage

The app frontend may consume capability and scope information to shape UX.

The backend must re-check authorization on every protected business operation.

## 10. Four authorization layers

```text
Layer 1 — Authentication
Who are you?

Layer 2 — Application access
Can you enter this app?

Layer 3 — Capability / scope
What functions and data can you access?

Layer 4 — Domain guard
Can this exact action be executed on this exact object now?
```

Quality workflows may additionally enforce segregation of duties.

Having a review capability does not imply the user can review their own submitted result.

## 11. Session authority

Providers must derive identity from the authenticated Frappe session:

```python
frappe.session.user
```

Never trust client-supplied `user`, `roles`, or equivalent authority claims.

Login source is irrelevant to app authorization.

Whether a user authenticated by password or Feishu SSO, runtime authorization uses the same Frappe session.

## 12. Summary contract

Summary data is a projection for product experience, not a second business fact.

Example:

```json
{
  "app_id": "attendance",
  "generated_at": "2026-09-24T18:00:00+08:00",
  "status": "normal",
  "metrics": [
    {
      "id": "my_exceptions",
      "label": "我的异常",
      "value": 2,
      "tone": "warning",
      "deep_link": "/hbos/attendance/exceptions"
    }
  ]
}
```

Supported semantic tones should be platform-level values such as:

- `neutral`
- `info`
- `success`
- `warning`
- `critical`
- `processing`

Apps provide semantic meaning, not CSS values.

## 13. Task contract

HBOS adopts the principle already reflected by the LIMS todo design:

> A task is an actionable projection of existing business state, not a second state machine.

Forbidden:

```text
Business state
  ↓ copy
Portal Todo state
```

Preferred:

```text
Business state
  ↓
App task provider
  ↓
Portal My Work
```

Completing the business action removes or changes the projected task naturally.

## 14. Unified Task DTO

Example:

```json
{
  "task_id": "lims:review:RESULT-001",
  "app_id": "lims",
  "category": "testing",
  "title": "复核检验结果",
  "description": "样品 SAMPLE-001",
  "action": "review",
  "action_label": "立即复核",
  "priority": "high",
  "due_at": "2026-09-24T16:00:00+08:00",
  "overdue": true,
  "assignment_type": "role_pool",
  "deep_link": "/hbos/lims/results/RESULT-001/review",
  "modified_at": "2026-09-24T14:00:00+08:00"
}
```

Task IDs must be globally unique, preferably:

```text
<app_id>:<local_task_key>
```

Portal treats task IDs as opaque.

## 15. Task priority vocabulary

Use:

- `low`
- `normal`
- `high`
- `critical`

Do not let each app invent incompatible priority vocabularies.

Portal may sort tasks, but applications determine the semantic priority.

## 16. Portal v1 action rule

Portal v1 should route users into the business app for business execution.

Preferred:

```text
My Work
→ deep link
→ business app
→ protected operation
```

Avoid implementing high-risk cross-app inline approval from Portal in v1.

This keeps workflow, signature, SoD, audit, and domain validation inside the owning application.

## 17. Deep-link contract

Stable product paths:

```text
/hbos/<app>/<resource>/<id>/<action?>
```

Examples:

```text
/hbos/lims/results/RESULT-001/review
/hbos/inventory/batches/BATCH-001
/hbos/attendance/exceptions/2026-09-24/EMP001
```

Portal contracts must not expose:

- `/app/<doctype>/...` as the long-term product path;
- source-code paths;
- internal Vue component paths.

The app resolver may map a stable HBOS link to a legacy, hybrid, or native implementation.

## 18. Search contract

Global Search calls permission-aware app search providers.

Example result:

```json
{
  "app_id": "inventory",
  "entity_type": "batch",
  "entity_id": "26092401",
  "title": "批次 26092401",
  "subtitle": "3904-01",
  "status": "已放行",
  "deep_link": "/hbos/inventory/batches/26092401"
}
```

The provider performs its own access filtering.

Portal must not perform a global unrestricted `frappe.get_all()` across business DocTypes.

## 19. Bootstrap model

Portal bootstrap should return the minimum information needed to render the shell quickly:

- current user display context;
- visible applications;
- app metadata;
- supported capabilities;
- Portal feature flags;
- selected user preferences.

It should not return all Frappe roles and expect Vue to calculate authorization.

The backend should already determine visible apps.

## 20. Progressive provider loading

Avoid one giant request that depends on all apps.

Preferred model:

```text
Bootstrap
  ↓
render shell
  ↓
parallel provider calls
  ├── Attendance summary
  ├── Inventory summary
  └── LIMS summary
```

One provider failure must not blank the whole Portal.

## 21. Provider error contract

Example:

```json
{
  "ok": false,
  "error": {
    "code": "PROVIDER_UNAVAILABLE",
    "message": "LIMS 数据暂时不可用",
    "retryable": true,
    "trace_id": "..."
  }
}
```

Recommended codes:

- `UNAUTHENTICATED`
- `FORBIDDEN`
- `APP_DISABLED`
- `APP_UNAVAILABLE`
- `CONTRACT_MISMATCH`
- `PROVIDER_ERROR`
- `INVALID_REQUEST`

User interfaces must not display raw Python tracebacks.

## 22. Freshness

Dynamic provider results should include `generated_at`.

Where useful, include `stale_after_seconds`.

The UI may show freshness explicitly for operational data.

## 23. Portal-owned state

Portal may own experience state such as:

- pinned apps;
- recent resources;
- shortcuts;
- layout preferences;
- sidebar state;
- visual preferences;
- Portal feature flags.

Portal must not own duplicate business truth such as:

- attendance state copy;
- stock balance copy;
- test result copy;
- quality release copy.

## 24. Application API vs Portal Provider

Do not combine them into one giant API surface.

Example LIMS application APIs:

- submit result;
- review result;
- approve result.

Portal provider APIs:

- access context;
- summary;
- My Work projection;
- search projection.

These have different responsibilities and security semantics.

## 25. Recommended app layout

Example:

```text
hb_lims_app/
└── hbos_lims/
    ├── application / domain services
    ├── workflow contracts
    └── portal/
        ├── provider.py
        ├── manifest.py
        ├── access.py
        ├── summary.py
        └── search.py
```

Attendance and Inventory should follow the same boundary when their Portal adapters are added.

## 26. Contract versioning

Every manifest includes:

```text
contract_version = 1
```

Portal should fail closed for unsupported contract versions at the app boundary, not fail the entire Portal.

Compatibility changes should allow staged migration where practical.

## 27. Current app gaps

### Attendance

Needs:

- Portal provider;
- Access Context;
- Summary DTO;
- task projection;
- search provider;
- stable deep-link resolver.

### Inventory

Needs:

- Portal provider;
- inventory summary;
- warehouse task projection;
- search provider;
- stable deep-link resolver.

Inventory permission cleanup must remain aligned with its clean-candidate governance.

### LIMS

Already has strong foundations:

- workflow / role contracts;
- todo service;
- session-derived identity;
- task projection concepts;
- Vue application APIs.

Needs standardization for:

- Portal manifest;
- Access Context;
- Summary contract;
- Search provider;
- stable HBOS deep links.

## 28. CI / review safety gates

Portal code should fail review if it directly queries protected business truth such as:

```python
frappe.get_all("HBOS Sample")
frappe.get_all("Batch")
frappe.get_all("Attendance")
frappe.get_all("Employee Checkin")
```

Portal may use its own Settings / Preferences / Registry DocTypes.

## 29. Contract laws

1. Portal knows Provider contracts, not business DocTypes.
2. Business apps decide application access.
3. Portal frontend does not use Frappe role names as final authorization logic.
4. Global tasks are projections, not duplicate workflow state.
5. Deep links use stable HBOS product routes.
6. One app failure must not take down the Portal.
7. Business-to-business integration does not route through Portal.
8. Runtime identity is the authenticated Frappe session.
9. Provider output is semantic data, not presentation markup.
10. Contract versions are explicit.

## 30. Acceptance tests

EA-3 implementation should eventually verify:

- installing a compliant demo provider makes a new app discoverable without editing Portal navigation source;
- unauthorized users do not see or invoke protected providers;
- one provider failure leaves other Portal cards usable;
- completing a business action changes My Work without synchronizing a second Portal task table;
- stable deep links survive legacy → native migration;
- forged user / role parameters cannot override `frappe.session.user`;
- unsupported contract versions fail at the app boundary;
- Portal does not directly query protected domain DocTypes.
