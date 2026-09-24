# HBOS Portal

HBOS Workspace / Portal 的薄 Frappe Platform App。

当前阶段：P2 Skeleton。

职责仅限：
- Frappe Session current-user bootstrap
- HBOS branding / identity presentation
- app registry
- provider discovery
- access aggregation
- summary / task / search dispatch
- stable route boundary
- provider failure isolation

明确不包含：
- Attendance / Inventory / LIMS 业务逻辑
- 第二套用户 / JWT / Role
- 业务事实副本
- 飞书 OAuth 实现
- Portal Settings / Preference DocType
- 任意业务写 API

Architecture authority:
- docs/experience/P1_HBOS_Portal平台App架构.md
