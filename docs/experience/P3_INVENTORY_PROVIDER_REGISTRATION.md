# HBOS Portal P3 — Inventory Provider Registration

**状态：P3-INV-1 / P3-INV-2 COMPLETE / RUNTIME GATE PASS**  
**日期：** 2026-09-25  
**分支：** `feature/hbos-portal-product`

## 1. 当前定位

Inventory 当前主要仍依赖 Frappe / ERPNext Desk 工作流，因此保持：

```text
stable product route
/hbos/inventory
        ↓
Inventory-owned resolver
        ↓
current Desk operational page
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

Access Context 仍由 Inventory App 自己计算。Portal 不把 Frappe role 原样暴露给前端。

## 3. P3-INV-1 — Manifest / Access / Stable Entry

首轮只建立 Registry / Access / Stable Route：

```json
{
  "id": "inventory",
  "route": "/hbos/inventory",
  "migration_mode": "legacy"
}
```

该阶段没有为了首页 KPI 直接复用现有库存报表，因为海滨专有库存报表包含 raw SQL。

## 4. P3-INV-2 — Permission-aware Summary

最终 manifest：

```json
["summary"]
```

Inventory Provider 新增：

```text
hb_inventory_app.hbos_inventory.portal.summary
```

Summary 不调用：

- `货位明细表`
- `按批号查货位`
- `效期预警`
- `库级盘点三对账`

这些报表仍保持原业务用途，不作为 Portal 全局聚合 API。

### 权限边界

Summary 先使用当前 Frappe Session 的 `frappe.get_list("Warehouse")` 获取 permission-aware 的可见叶子货位，再把 `Bin` 查询显式限制在同一 Warehouse 集合内。

```text
Current Frappe Session
        ↓
permission-aware Warehouse list
        ↓
explicit Bin.warehouse IN visible warehouses
        ↓
Inventory-owned semantic projection
        ↓
Portal summary dispatcher
```

如果当前用户没有任何可见 Warehouse，Summary 返回零指标上下文，不继续查询 Bin。

### 指标语义

当前只投影四项计数：

- 可见货位；
- 有库存物料；
- 负库存项；
- 预计短缺项。

不跨物料累计 `actual_qty` / `projected_qty`，因为不同 Item 的 Stock UOM 可能不同，把它们直接相加会制造错误业务含义。

### Portal 边界

Portal 只通过标准 dispatcher 消费：

```text
dispatch_provider("inventory", "summary")
```

Portal 不直接 import Inventory，不读取 Warehouse / Bin，不拥有库存 KPI 算法。

## 5. Tests

Provider Contract 新增：

- manifest 只能开放 `summary`；
- 投影计数语义；
- Warehouse permission scope → Bin 显式 scope；
- 无可见 Warehouse 时不得查询 Bin；
- 不跨 UOM 汇总数量。

Portal clean-site Integration 进一步验证：

- Registry 中 Inventory manifest = `["summary"]`；
- Portal dispatcher 可调用 `inventory:summary`；
- Summary 返回 4 个稳定 metric；
- Stable Route 仍解析到 `/app/hbos-photo-intake`。

## 6. Runtime Authority

Inventory Provider 首次 real-site Summary Gate：

```text
Head = 3c6f1d5f54a5795d4a7b1ed486c8ce32c64ea7e4
Platform Integration run 36082817979
platform-clean-site = SUCCESS
```

关键输出：

```json
{
  "inventory_route": "/hbos/inventory",
  "inventory_mode": "legacy",
  "inventory_capabilities": ["summary"],
  "inventory_resolved_route": "/app/hbos-photo-intake",
  "inventory_summary_status": "normal",
  "inventory_summary_metrics": 4
}
```

Portal dispatcher + local-runtime-tooling strict Gate：

```text
Code authority = ea15676af42e14c2eb47bd65fa402481693b0cac
Platform Integration run 36083304003
Three-app clean-site integration step = SUCCESS
Portal Backend Gate = SUCCESS
```

该 code authority 同时包含三 APP PR 路径门禁修复、`p3_workspace_runtime_smoke.sh` 和 `start_local_workspace.sh`。

## 7. Definition of Done

```text
P3-INV-1 Registry / Access / Entry = PASS
P3-INV-2 Permission-aware Summary = PASS
Inventory Tasks = GATED
Inventory Search = GATED
Business Writes = NONE
Portal → Inventory static import = NONE
Raw-SQL reports exposed as Portal aggregate = NONE
```

下一阶段不是继续堆 Inventory KPI，而是先完成三 APP 本地工作台验收，再按 P4 前端强化 Gate 研究 Inventory V1/V2 用户体验。
