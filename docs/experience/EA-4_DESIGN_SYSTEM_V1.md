# EA-4 — HBOS Design System v1

> Status: **BASELINE**
>
> Scope: define the shared visual and interaction language for HBOS Portal and user-facing business applications.
>
> Last updated: 2026-09-24

## 1. Design intent

HBOS should not look like:

- ERPNext with a new logo;
- default Ant Design;
- generic OA software;
- a passive KPI wall;
- several unrelated applications placed behind one launcher.

The target product language combines:

- modern enterprise operations;
- pharmaceutical / regulated-process precision;
- AI and digital-twin future readiness;
- strong information hierarchy;
- high operational efficiency.

Design keywords:

```text
Precise
Spatial
Intelligent
Operational
Premium
Human
```

## 2. Implementation foundation vs design language

Vue 3 + Ant Design Vue remain the preferred implementation foundation for user-facing HBOS applications.

Ant Design Vue is a **component engine**, not the HBOS visual identity.

HBOS owns:

- tokens;
- typography;
- layout;
- navigation;
- status semantics;
- cards;
- tables;
- empty states;
- motion;
- app identity;
- visual intensity rules.

The current LIMS frontend is an engineering reference for Vue / session / API patterns. It is not the visual master for HBOS.

## 3. Dual visual mode

HBOS deliberately supports two compatible modes:

### Expressive Experience

Used where product identity, orientation, or high-level context matters.

Examples:

- Portal Home;
- App Center;
- AI;
- Digital Twin;
- executive / operational overview.

### Operational Experience

Used where sustained professional work matters.

Examples:

- result entry;
- attendance exception handling;
- warehouse operations;
- schedule editing;
- review / approval work.

The same design system serves both. Visual intensity changes; product identity does not.

## 4. Visual Intensity Levels

### V3 — Hero / Immersive

Typical surfaces:

- Portal Home;
- App Center;
- Command Palette;
- AI;
- Digital Twin;
- selected executive views.

Allowed:

- gradient mesh;
- glassmorphism;
- ambient light;
- large metrics;
- animated backgrounds;
- app color accents;
- spatial depth;
- large-scale motion.

### V2 — Application Dashboard

Typical surfaces:

- Attendance dashboard;
- Inventory dashboard;
- LIMS dashboard;
- Production / Equipment dashboards.

Allowed:

- local gradient accents;
- lighter glass;
- KPI / charts;
- domain accent;
- moderate motion.

### V1 — Operational

Typical surfaces:

- result review / entry;
- inbound / outbound tasks;
- attendance exception handling;
- counting;
- scheduling.

Priority:

```text
efficiency > decoration
```

Use:

- strong hierarchy;
- restrained motion;
- subtle surfaces;
- clear states;
- dense but readable controls.

Avoid strong animated backgrounds and heavy blur.

### V0 — Management

Typical surface:

- Management Console / Frappe Desk;
- settings;
- master data;
- permissions;
- diagnostics.

Priority:

- function;
- stability;
- density.

Desk does not need to be visually cloned into the Portal.

## 5. Brand palette

### Core dark neutrals

```text
Graphite 950  #0A0D12
Graphite 900  #10141C
Graphite 800  #171C26
```

### Light neutrals

```text
Cloud 50      #F6F8FB
Cloud 100     #EEF2F7
Surface       #FFFFFF
```

### Platform brand accents

```text
HBOS Indigo   #6557FF
HBOS Blue     #3B82F6
HBOS Aqua     #37D6C5

Electric Cyan #35C8FF
Aurora Violet #8B5CFF
```

These values are v1 design baselines and may be tuned during EA-5 prototype validation while preserving semantic roles.

## 6. Signature gradient

HBOS V3 surfaces may use a multi-point gradient / mesh rather than a simple two-color background.

Conceptual palette:

```text
#584CFF
#3378FF
#20BCEB
#45D9BE
#8B5CF6
```

Guideline:

> strong color needs neutral breathing room.

Do not turn full pages into continuously saturated rainbow backgrounds.

## 7. Domain color identity

Each business application may have a stable accent family.

Suggested baseline:

| App | Accent |
|---|---|
| Attendance | Indigo / Violet |
| Inventory | Amber / Orange |
| LIMS | Emerald / Cyan |
| Production | Electric Blue |
| Equipment | Cyan |
| Maintenance | Orange / Red |
| EHS | Green |
| Training | Violet |
| AI | Violet / Electric Blue |
| Digital Twin | Blue / Purple |
| Energy | Lime / Cyan |

Domain color is used for app identity, icons, selected accents, and important charts. It does not replace shared HBOS surfaces and typography.

## 8. App icon system

App icons should be identifiable and colorful while remaining systemized.

Preferred structure:

```text
rounded square
+ domain gradient
+ simple symbol
+ subtle highlight / depth at large sizes
```

Large presentation icons may include bloom / glass edge. Small icons use flatter variants for clarity.

Avoid assigning arbitrary unrelated colors to every menu item.

## 9. Typography

Recommended Chinese stack:

```text
PingFang SC
Noto Sans SC
Microsoft YaHei
system-ui
```

Recommended Latin / numeric stack:

```text
Inter
SF Pro
system-ui
```

Monospaced operational data where useful:

```text
SF Mono
JetBrains Mono
ui-monospace
```

### Type scale

| Role | Baseline |
|---|---|
| Display / Hero Metric | 64–88px, occasionally larger with review |
| H1 | 32–40px |
| H2 | 24–28px |
| H3 | 18–20px |
| Body | 14–16px |
| Dense Body | 13–14px |

Large metrics should normally use medium / semibold weight rather than extreme black weight.

## 10. Hero metrics

HBOS supports oversized metrics in V3 / selected V2 contexts.

Example:

```text
      11
  MY ACTIONS

3 Attendance
5 Quality
3 Inventory
```

Use oversized metrics sparingly:

- typically 1–3 per screen;
- preserve surrounding whitespace;
- do not make every dashboard metric oversized.

## 11. Glassmorphism levels

### Strong glass — V3 only

Concept:

```text
low-opacity translucent surface
24–36px blur
subtle bright border
ambient depth
```

### Medium glass — V2

Use lighter blur and more solid surfaces.

### Light glass — V1

Use minimal transparency / border separation. Strong blur is normally inappropriate for long operational sessions.

Glass is a hierarchy tool, not the default surface for every card.

## 12. Card hierarchy

HBOS distinguishes:

- **Hero Card** — orientation / identity / strong visual context;
- **Work Card** — actionable My Work item;
- **Data Card** — metric / visualization;
- **Operation Card** — form / professional workflow content.

Card types have different density and visual-intensity rules.

## 13. Shape and radius

Baseline radius scale:

```text
Small        8px
Control     10px
Card        14px
Large Card  18px
Hero        24px
Pill        999px
```

Avoid excessive “toy-like” rounding on dense operational surfaces.

## 14. Spacing

Use a 4px base unit.

Recommended token scale:

```text
4  8  12  16  20  24  32  40  48  64  80
```

Product principle:

> generous macro-spacing + precise component spacing.

## 15. Grid

Desktop uses a 12-column grid.

Guidance:

- Portal maximum content width around 1600px;
- typical business content around 1440px;
- data-table pages may use full available width.

Prototype validation may tune these values.

## 16. Global HBOS Shell

Native HBOS applications share a recognizable global shell.

```text
┌───────────────────────────────────────────────┐
│ HBOS  Context     Search / Command   Bell User│
├─────────────┬─────────────────────────────────┤
│ App Local   │ Application Content             │
│ Navigation  │                                 │
└─────────────┴─────────────────────────────────┘
```

Global Header responsibilities:

- HBOS brand;
- current app / context;
- App Switcher;
- global search / command;
- notifications;
- user profile;
- Management Console entry for authorized users.

## 17. Header behavior

Suggested desktop height: approximately 64px.

Header may be translucent / glass-like in V3 and progressively more solid in V1.

It should normally remain available through sticky positioning on desktop user-facing apps.

## 18. Local navigation

Recommended desktop width:

```text
220–248px
```

Collapsed:

```text
~64px
```

Mobile / narrow screens use a Drawer or equivalent responsive pattern.

Navigation should normally remain at two visible levels or fewer. Deeper structures should trigger IA review rather than indefinite nested menus.

## 19. Motion system

HBOS should feel alive without becoming distracting.

Baseline duration classes:

| Motion | Duration |
|---|---|
| Micro interaction | 120–180ms |
| Component / Drawer | 180–280ms |
| Page transition | 280–420ms |
| Ambient Hero motion | 4–12s slow cycle |

Suggested easing families:

```text
Standard  cubic-bezier(0.2, 0, 0, 1)
Enter     cubic-bezier(0, 0, 0, 1)
Exit      cubic-bezier(0.4, 0, 1, 1)
```

Avoid exaggerated bounce / spring behavior in enterprise workflows.

## 20. Large-area animation

V3 may use:

- aurora gradient movement;
- slow mesh movement;
- soft light orbs;
- restrained particles;
- subtle parallax.

Requirements:

- low frequency;
- low distraction;
- no continuous fast motion;
- no impairment of content readability.

Support `prefers-reduced-motion`.

When reduced motion is requested:

- disable ambient movement;
- reduce page transitions;
- disable number rolling / parallax where practical.

## 21. Shared status semantics

All apps use common status meaning:

- `neutral`
- `info`
- `success`
- `warning`
- `critical`
- `processing`
- `disabled`

Example mappings:

### Attendance

- normal → success;
- late → warning;
- absent → critical.

### Inventory

- released → success;
- pending inspection → warning / processing;
- rejected / blocked → critical.

### LIMS

- passed → success;
- pending review → processing;
- OOS → critical.

Color must not be the only status indicator. Text / iconography must reinforce meaning.

## 22. Data visualization

ECharts remains the preferred chart engine where charts are necessary.

HBOS chart principle:

> muted default series + saturated emphasis.

Risk colors such as warning / critical are reserved for risk meaning and should not be consumed as arbitrary chart-series colors.

## 23. Tables

Tables are a first-class HBOS component.

Design should support where relevant:

- sticky headers;
- comfortable / compact density;
- resizable columns;
- column visibility;
- saved views;
- filtering;
- quick search;
- bulk action;
- keyboard navigation.

Visual redesign must not reduce operational throughput.

## 24. Empty, loading, and error states

### Empty state

Do not stop at “No data”.

Preferred:

```text
暂无待检任务

当前没有需要你处理的检验任务。

[查看全部样品]
```

Explain context and useful next action.

### Loading

Prefer skeletons over page-level spinners.

Provider cards load independently.

### Error

Distinguish:

- user input;
- permission;
- business rule;
- provider unavailable;
- system failure;
- offline / connectivity.

Do not expose raw Python exceptions as user-facing product text.

## 25. My Work Card

My Work is a shared product primitive.

Recommended information:

- app identity;
- title;
- concise context;
- due time;
- priority;
- overdue state;
- primary deep-link action.

Example:

```text
[LIMS]

复核检验结果
SAMPLE-001 · RESULT-001

今天 16:00 · 高优先级

[立即处理]
```

## 26. App Center

App Center should support more than a mobile-style icon grid.

Recommended sections:

- Featured;
- Recently Used;
- Pinned;
- All Applications.

App cards may show:

- icon;
- title;
- short description;
- current pending count;
- limited status context.

## 27. App Switcher

Global Header should provide an app switcher supporting:

- pinned apps;
- recent apps;
- all accessible apps.

This scales better than placing every app permanently in Portal navigation.

## 28. Command Palette

Command Palette is a strategic HBOS interaction surface.

Shortcut:

```text
⌘ K
Ctrl K
```

Potential capabilities:

- global search;
- quick actions;
- recent resources;
- app switching.

It is an appropriate V3 surface for controlled glass, blur, and spatial motion.

## 29. Portal Home structure

Portal Home should function as a personal operating system, not a static KPI wall.

Recommended hierarchy:

```text
Hero / personal context
        ↓
My Work + Business Pulse
        ↓
Recent + Quick Actions
        ↓
Applications
```

The Hero may include a large `MY ACTIONS` count and role-relevant summary.

Recommended Hero height is a substantial section, not necessarily a 100vh takeover. Users should reach actionable content quickly.

## 30. Application dashboard pattern

Business app dashboards share a conceptual skeleton:

```text
App Identity
My Work
Operational Metrics
Risks
Recent / Context
```

The exact layout is domain-specific.

Do not force every app into an identical “four KPIs + line chart + table” template.

## 31. Operational page pattern

Typical V1 structure:

```text
Page Header
Context / Breadcrumb
Primary Action
Filter / Search
Main Work Surface
Context Panel / Drawer
```

Use drawers for contextual detail where they reduce unnecessary page hopping.

Complex workflows should not be placed inside oversized modals.

## 32. Detail pages

Avoid raw long-form field dumps.

Prefer domain groupings such as:

- Overview;
- Activity;
- Related;
- History;
- Audit.

The data model can remain detailed while the product presentation is task-oriented.

## 33. Light / dark

EA-4 defines HBOS as dark-ready, but Portal MVP should not be blocked by implementing complete dark mode.

Recommended implementation order:

```text
Light = primary operational baseline
Dark = token-ready / later productized
```

V3 Hero surfaces may use dark or mixed visual treatments even when operational content is light.

## 34. Responsive baseline

Suggested breakpoints:

```text
Mobile   < 768
Tablet   768–1199
Desktop  1200–1599
Wide     >= 1600
```

Mobile should prioritize:

- My Work;
- Search;
- Notifications;
- Quick Actions.

Not every dense expert workflow must be forced into a compromised mobile UI.

## 35. Accessibility

HBOS should include:

- sufficient contrast;
- visible focus;
- keyboard support;
- screen-reader labels;
- reduced motion;
- non-color status cues.

Accessibility is part of product quality, not a post-launch visual patch.

## 36. Token architecture

Recommended future structure:

```text
tokens/
├── foundation
├── semantic
├── component
└── domain
```

Example semantic names:

```text
--hbos-bg-canvas
--hbos-bg-surface
--hbos-bg-elevated

--hbos-text-primary
--hbos-text-secondary
--hbos-text-muted

--hbos-border-default

--hbos-brand-primary

--hbos-status-success
--hbos-status-warning
--hbos-status-critical

--hbos-radius-card
--hbos-radius-hero

--hbos-motion-fast
--hbos-motion-page
```

Avoid app-local ambiguous names such as `--primary` becoming the long-term platform vocabulary.

## 37. Shared UI package timing

Do not create a large shared UI package before real cross-app reuse is demonstrated.

Recommended sequence:

1. implement and validate Portal design primitives;
2. begin a second native HBOS app;
3. identify proven reusable tokens / components;
4. extract a shared `hbos-ui` package if justified.

This prevents premature design-system abstraction.

## 38. Frappe Desk coexistence

Management Console does not need to visually match Portal pixel-for-pixel.

Minimum alignment:

- HBOS branding;
- clear Management Console identity;
- clear Return to HBOS action;
- restrained shared brand color / logo treatment where practical.

Avoid expensive core Frappe rewrites solely for visual parity.

## 39. Explicit design anti-patterns

Avoid:

- fully saturated gradient pages everywhere;
- glass on every card;
- oversized numbers on every metric;
- random per-menu colors;
- app-specific font systems;
- deep nested sidebars;
- rapid persistent background motion;
- decorative animation on repetitive operational actions;
- default Ant Design appearance presented as the HBOS design system.

## 40. EA-5 prototype set

EA-5 should validate this design system with a focused first batch:

1. **HBOS Portal Home** — V3
2. **My Work** — V2
3. **App Center** — V3 / V2
4. **Command Palette** — V3
5. **New LIMS Application Shell** — V2
6. **LIMS Operational Page** — V1

The purpose is to prove that a visually expressive Portal and a dense professional workflow still feel like one product.

Second-batch candidates after Owner review:

- Attendance dashboard;
- Inventory dashboard;
- Inventory hybrid-to-Desk transition;
- mobile Portal;
- Management Console transition.

## 41. Review gate

EA-4 is considered implemented correctly when:

- HBOS does not inherit the current LIMS visual language;
- Ant Design Vue is treated as implementation infrastructure;
- V3 / V2 / V1 / V0 intensity levels are visible in the product;
- gradient, glass, large KPI, colorful icons, and motion are allowed but governed;
- operational pages prioritize sustained productivity;
- domain color identity does not fragment the overall product;
- global shell and local navigation remain recognizable across apps;
- status semantics are consistent;
- responsive, accessibility, and reduced motion are designed from the start;
- Management Console remains clearly separate from the employee product surface.
