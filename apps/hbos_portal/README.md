# HBOS Portal

HBOS Workspace / Portal 的薄 Frappe Platform App。

当前阶段：**P3 THREE-APP WORKSPACE INTEGRATION / CAPABILITY DEEPENING**。

职责仅限：

- Frappe Session current-user bootstrap；
- HBOS branding / identity presentation；
- Application Provider Registry / discovery；
- business-app access aggregation；
- permission-aware summary / task / search dispatch；
- stable route boundary；
- provider failure isolation。

当前 Registry 业务 App：

```text
attendance
inventory
lims
```

当前 Provider capability：

```text
Attendance  summary
Inventory   summary
LIMS        summary / tasks / search
```

Inventory Summary 由 Inventory App 自己提供 permission-aware projection；Portal 不读取库存表、不复制库存口径。

明确不包含：

- Attendance / Inventory / LIMS 业务逻辑；
- 第二套用户 / JWT / Role；
- 业务事实副本；
- 飞书 OAuth 实现；
- Portal Settings / Preference DocType；
- 任意业务写 API。

本地工作台：

```bash
bash scripts/portal/start_local_workspace.sh
```

完整本地运行态验收：

```bash
bash scripts/portal/p3_workspace_runtime_smoke.sh
```

Architecture authority：

- `docs/experience/P1_HBOS_Portal平台App架构.md`
- `docs/experience/EA-3_APPLICATION_CONTRACT_ACCESS.md`
- `docs/experience/EA-4_DESIGN_SYSTEM_V1.md`
