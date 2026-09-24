# HBOS Experience Architecture

> Authority scope: HBOS user-facing product experience, Portal / Business App / Management Console boundaries, cross-application experience contracts, and HBOS visual design baseline.
>
> Repository: `zjl327707743/HBOS-Platform`
>
> Status: **BASELINE**
>
> Last updated: 2026-09-24

## Purpose

HBOS is evolving from a Frappe / ERPNext based customized system into a unified enterprise product.

The Experience Architecture defines how employees, professional users, business administrators, and system administrators should use HBOS without forcing every user to understand Frappe Desk, ERPNext modules, DocTypes, or implementation details.

The governing model is:

```text
HBOS
├── HBOS Workspace / Portal       user product layer
├── HBOS Business Applications   Attendance / Inventory / LIMS / future apps
└── HBOS Management Console      Frappe Desk based administration layer
```

All three surfaces normally operate against the same Frappe site, business services, permissions, and authoritative business data. They are different product surfaces, not separate systems of record.

## Document set

| Stage | Document | Scope | Status |
|---|---|---|---|
| EA-1 | [Surface Responsibility](./EA-1_SURFACE_RESPONSIBILITY.md) | Portal / Business App / Desk responsibilities | BASELINE |
| EA-2 | [User Journey & Information Architecture](./EA-2_USER_JOURNEY_IA.md) | Personas, navigation, product map, migration journeys | BASELINE |
| EA-3 | [Application Contract & Access Model](./EA-3_APPLICATION_CONTRACT_ACCESS.md) | Provider contract, access, summary, tasks, search, deep links | BASELINE |
| EA-4 | [Design System v1](./EA-4_DESIGN_SYSTEM_V1.md) | HBOS visual language, visual intensity, layout, motion, tokens | BASELINE |
| EA-5 | [Portal Product Prototype](./EA-5_PORTAL_PRODUCT_PROTOTYPE.md) | High-fidelity prototype and interaction validation | IN_PROGRESS / OWNER VISUAL GATE APPROVED |\n| EA-5.3 | [Product Interaction Review](./EA-5.3_PRODUCT_INTERACTION_REVIEW.md) | Portal / App boundary, My Work, Digital Twin, Chinese UX | BASELINE |\n| EA-5.4 | [Component & Interaction Specification](./EA-5.4_COMPONENT_INTERACTION_SPEC.md) | Component geometry, glass, motion, typography, interaction | BASELINE |\n| EA-5.5 | [Interaction QA / Responsive / Accessibility](./EA-5.5_INTERACTION_QA_RESPONSIVE_ACCESSIBILITY.md) | Frontend reproduction, interaction, responsive and accessibility validation | COMPLETE / OWNER APPROVED |

## Relationship to other governance

These documents complement, rather than replace:

- `docs/governance/` — PR, data, merge, and domain governance.
- `docs/frontend/` — frontend implementation rules.
- `docs/adr/` — architecture decisions that should remain stable even when implementation details evolve.
- Business-app specific contracts — Attendance, Inventory, and LIMS remain the authorities for their own domain rules.

## Authority rules

1. **Portal is an experience shell, not a business-domain owner.**
2. **Business applications remain domain authorities.**
3. **Frappe Desk remains the management console and is not removed.**
4. **A business fact has one authoritative source.** Portal summaries and tasks are projections, not duplicate business state.
5. **User-facing HBOS applications share one product language but may have different domain colors and workflows.**
6. **Authentication converges on Frappe User + Frappe Session.** Login source does not define business authorization.
7. **Cross-app experience integration uses stable contracts.** Business-domain integration does not route through Portal.
8. **Existing apps may migrate progressively through legacy → hybrid → native modes.**

## Development gates

New or substantially redesigned HBOS user-facing applications should:

1. identify their surface responsibility;
2. define user journeys and local information architecture;
3. implement the HBOS application contract needed by Portal;
4. apply the HBOS Design System;
5. pass product / prototype review before large-scale frontend implementation.

## Current product direction

```text
                       HBOS
                        │
          ┌─────────────┴─────────────┐
          │                           │
   HBOS Workspace              Management Console
   employee product               admin surface
          │                           │
          │                       Frappe Desk
          │
   ┌──────┼────────┐
   │      │        │
Attendance Inventory LIMS
   │      │        │
   └──────┼────────┘
          │
   Application / Domain APIs
          │
 ERPNext / HRMS / Frappe
          │
       MariaDB
```

The long-term product identity is **HBOS**, while Frappe / ERPNext / HRMS remain foundational platform and management technologies.


## Current EA-5 workstream

The Owner has explicitly authorized the HBOS Portal product workstream.

Current branch:

```text
feature/hbos-portal-product
```

Current design authority:

- EA-5.3 visual baseline;
- EA-5.4 component / interaction specification;
- `docs/frontend/FRONTEND_IMPLEMENTATION_GUIDE.md`.

EA-5.5 has passed Owner review. The next workstream is **P1 — hbos_portal Frappe Platform App Architecture**.


### Frontend reproduction status

The approved Portal visual baseline has now been initialized as source code under:

```text
frontend/hbos-portal-web/
```

Status: **SOURCE INITIALIZED / BUILD VERIFICATION PENDING**.

The source includes Global Header, App Switcher, Notification Center, Command Palette, Portal routes, standalone LIMS shell, Digital Twin overview, EA-5.4 tokens, pointer atmosphere, responsive CSS, and reduced-motion fallback.

Real Frappe / business API integration has not started.


### EA-5.5 implementation started

EA-5.5 implementation now includes mobile navigation, skip links, keyboard Command Palette, Ant Design Vue theme mapping, and a LIMS V1 result-review operational route used to validate Full Page / Drawer / Modal rules.


EA-5.5 frontend implementation has passed both repository quality and Portal frontend build gates. Owner product review remains the final EA-5.5 closeout gate.


## P1 Platform Architecture

P1 authority: [`P1_HBOS_Portal平台App架构.md`](./P1_HBOS_Portal平台App架构.md).

Status: **ARCHITECTURE BASELINE / P2 READY**.


## P2 Runtime Status

```text
P1 = ARCHITECTURE BASELINE
P2 = SKELETON IMPLEMENTED / BACKEND GATE PASS
P2.1 = FRONTEND BOOTSTRAP ADAPTER PASS
P2.2 = RUNTIME SMOKE TEST NEXT
```
