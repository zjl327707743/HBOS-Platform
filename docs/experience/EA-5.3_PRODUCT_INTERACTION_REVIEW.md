# HBOS EA-5.3 Product Interaction Review

## Review result

EA-5.2 is not approved as the final product interaction baseline.

The direction is correct, but the prototype had structural and visual-quality issues that must be corrected before backend implementation.

## P0 corrections

### P0-1 — LIMS must not be exposed as Portal outer navigation

LIMS is a standalone HBOS Business Application.

Portal fixed navigation contains only:
- 首页
- 我的工作
- 应用中心
- 我的 / 设置

LIMS is entered through App Center / App Switcher / Search / Deep Link.

Inside LIMS:
- Keep HBOS Global Header
- Use LIMS Local Navigation
- Do not keep Portal Sidebar

### P0-2 — Restore Digital Twin

Digital Twin is a core HBOS differentiator and cannot disappear during product expansion.

Home keeps:
- Digital Twin operational-status module
- M606B / M607B spatial preview
- 3D entry
- process / health / operation modes

App Center also reserves a Digital Twin app entry.

The module renders only when a real provider/capability exists in production.

### P0-3 — No emoji icon system

Production UI must use:
- Ant Design Vue icons for system/navigation/action icons
- HBOS custom app icons for application identity
- custom SVG / 3D assets for Digital Twin

Emoji may not be used as the primary product icon language.

### P0-4 — Chinese UI typography

Minimum recommended sizes:
- Page title: 32–40
- Section title: 18–22
- Card title: 14–16
- Body: 14
- Metadata: 11–12
- Micro technical label: 10–11

Do not use English SaaS sizing directly for dense Chinese text.

## My Work

My Work is an action inbox, not a universal activity feed.

Main scopes:
- 需要我处理
- 今天
- 本周
- 超期
- 等待别人
- 已完成

“等待别人” is not counted as “需要我处理”.

Portal does not execute high-risk business actions in v1. It deep-links into the owning application.

## App Center scalability

Home only shows:
- core/pinned/recent applications (about 5–7)
- Digital Twin
- More Applications

Full App Center supports:
- Featured
- Recent
- All
- search
- future category / pinning

Do not render 15–30 apps as a single phone-like icon grid.

## LIMS navigation

Portal:
- no LIMS fixed menu

LIMS app:
- 我的工作
- 我的待检
- 我的复核
- 我的审批
- 样品与检验
- 质量与报告
- 留样管理
- 稳定性管理
- 合规审计

The Global Header preserves HBOS identity.
The Local Sidebar owns LIMS information architecture.

## Drawer vs Page rules

Use Drawer for:
- quick read-only preview
- contextual supporting information
- light edit with <= ~8 fields
- recent item preview
- search-result preview
- batch/sample quick context

Use a full Page for:
- core workflow execution
- inspection/result entry
- approval/review requiring evidence
- e-signature / re-auth
- complex multi-section forms
- long tables / analytics
- anything that needs stable deep-link/bookmark/reload

Use Modal for:
- destructive confirmation
- single decision/reason input
- short acknowledgement

On mobile, complex drawers become full-screen page/drawer.

## Home density presets

Ordinary Employee:
- Hero
- App Center
- 0–3 personal work items
- personal status
- minimal business pulse
- Digital Twin only if relevant

Professional User:
- Hero
- App Center
- My Work
- Business Pulse
- Digital Twin
- Quick Actions

Manager:
- Professional layout
- team/risk summaries
- approval / operational pulse

The page is capability/role driven, not a single fixed dashboard for everyone.

## Chinese localization rules

- Chinese action labels first; English only as secondary brand/technical labels.
- Avoid excessive uppercase and letter spacing around Chinese.
- Buttons should use verbs: “立即处理 / 查看详情 / 返回工作台”.
- Use clear state terms rather than translated abstractions.
- Dates use Chinese-readable forms where appropriate: “今天 16:00 / 周五 14:00”.
- App product names may retain LIMS / HBOS / AI where they are established brands.

## Layout baseline

Desktop:
- 64–68 Global Header
- 216–224 Portal Sidebar
- 232–248 Application Local Sidebar
- max content 1440–1600
- 12-column grid
- 18–24 page gap
- 12–16 internal card gap

Business operation pages may use full width when tables require it.

## EA-5.3 gate

Do not proceed to real backend implementation until:
- Portal/App boundary is accepted
- My Work semantics are accepted
- App Center scaling is accepted
- Drawer/Page rules are accepted
- Chinese typography/icon baseline is accepted
- Digital Twin placement is accepted
- ordinary/professional/manager density model is accepted