# HBOS Portal P3 — Inventory Provider Registration

**状态：P3-INV-1 COMPLETE / RUNTIME GATE PASS**  
**日期：** 2026-09-25  
**分支：** `feature/hbos-portal-product`

## 1. 当前定位

Inventory 当前主要仍依赖 Frappe / ERPNext Desk 工作流，因此首轮只注册受控入口和访问权限。

Stable route：

```text
/hbos/inventory
```

当前实现入口：

```text
/app/hbos-photo-intake
```

当前 migration mode：

```text
legacy
```

未来进入 hybrid/native 后只替换 resolver / capability，不改变 Portal 稳定地址。

## 2. Access

当前允许：

- Stock User
- Stock Manager
- System Manager
- Administrator break-glass

普通无库存角色用户不可进入。

## 3. Manifest

```json
{
  "id": "inventory",
  "route": "/hbos/inventory",
  "migration_mode": "legacy",
  "capabilities": []
}
```

本轮刻意不开放 Summary / Tasks / Search。

原因：

- 现有库存报表包含 raw SQL 统计；
- 在把它们作为 Portal Summary 前，需要先确认 User Permission / Warehouse Scope 不会被绕过；
- 当前没有统一的 Inventory action projection；
- 不为了首页好看而制造第二套库存任务或 KPI 口径。

## 4. Runtime Authority

Verified code authority：

```text
368265e4b2d6fac54dac756114cdde9063f8ff74
```

Platform Integration Gate：

```text
run 36048253825 = SUCCESS
```

clean-site 关键输出：

```json
{
  "registry_entries": ["attendance", "inventory", "lims"],
  "registry_failures": 0,
  "attendance_resolved_route": "/app/hbos-attendance-dashboard",
  "inventory_resolved_route": "/app/hbos-photo-intake",
  "bootstrap_apps": ["attendance", "inventory", "lims"]
}
```

Inventory-owned runtime：

```json
{
  "inventory_route": "/hbos/inventory",
  "inventory_mode": "legacy",
  "inventory_capabilities": [],
  "inventory_resolved_route": "/app/hbos-photo-intake"
}
```

## 5. Definition of Done

```text
P3-INV-1 Registry / Access / Entry = PASS
Inventory Summary = GATED
Inventory Tasks = GATED
Inventory Search = GATED
Business Writes = NONE
Portal → Inventory static import = NONE
```

下一阶段若开启 Inventory Summary，必须先建立 permission-aware projection，不直接把 raw SQL 报表当全局 Portal API。
