# HBOS Portal P3-LIMS-1 — First Real Provider Registration

**状态：COMPLETE / RUNTIME GATE PASS**  
**日期：** 2026-09-25  
**分支：** `feature/hbos-portal-product`

## 1. 目标

P3-LIMS-1 只验证首个真实 Business App 能否通过 HBOS Application Contract 注册进 Portal。

本轮仅实现：

```text
Manifest
Access Context
Stable App Entry
```

明确不实现：

- Summary；
- My Work / Tasks；
- Search；
- LIMS 业务写操作；
- 第二套权限；
- Portal 对 LIMS DocType 的直接查询。

## 2. Provider Registration

LIMS 在自身 `hooks.py` 注册：

```python
hbos_portal_provider = [
    "hb_lims_app.hbos_lims.portal.provider.get_provider",
]
```

Portal 继续只调用：

```python
frappe.get_hooks("hbos_portal_provider")
```

因此：

- `hbos_portal` 没有静态 import LIMS；
- LIMS 自己拥有 Provider adapter；
- App 安装 / 卸载决定 Provider 是否存在；
- 一个业务 App 不存在时 Portal 仍可启动。

## 3. Manifest

当前 LIMS manifest：

```json
{
  "contract_version": 1,
  "id": "lims",
  "title": "实验室质量管理",
  "short_title": "LIMS",
  "description": "检验、质量、留样与稳定性管理",
  "icon": "ExperimentOutlined",
  "accent": "lims",
  "order": 30,
  "migration_mode": "native",
  "route": "/hbos/lims",
  "capabilities": []
}
```

`capabilities=[]` 是有意设计。

P3-LIMS-1 尚未放行：

- summary；
- tasks；
- search。

这些能力必须分别通过后续 Gate 才加入 manifest。

## 4. Access Context

LIMS Provider 从：

```text
frappe.session.user
frappe.get_roles(user)
```

推导当前身份。

Portal 不传 user / roles，也不解释 LIMS Role 名称。

LIMS Access Adapter 复用现有 LIMS Authority：

- `LIMS_BUSINESS_ROLES`；
- `workflow_contract.ROLE_SYSTEM`；
- Frappe built-in `Administrator` break-glass identity。

对 Portal 输出只包含语义信息：

```json
{
  "app_id": "lims",
  "can_enter": true,
  "capabilities": ["lims.read"],
  "scopes": {}
}
```

不会把：

```text
LIMS Analyst
LIMS Reviewer
LIMS QA
...
```

暴露给 Portal 作为授权逻辑。

## 5. Contract Gate

`HBOS Portal Backend Gate` 新增 LIMS Provider Contract Test，验证：

- Hook factory path；
- Manifest stable id / route / mode；
- 本阶段 capabilities 必须为空；
- Guest 不可进入；
- LIMS business role 可进入；
- System Manager 可获得 read entry；
- unrelated role 不可进入；
- Administrator break-glass entry；
- Access DTO 不暴露 raw LIMS role names；
- Provider identity 来自 Frappe session。

结果：

```text
Portal Backend Gate = PASS
HBOS Quality Gate   = PASS
Portal Frontend Gate = PASS
```

## 6. Clean-site Packaging Defect Found and Fixed

第一次 P3 runtime clean-site 暴露：

```text
ModuleNotFoundError:
No module named 'hbos_portal.hbos_portal'
```

原因：

`hbos_portal/modules.txt` 声明 `HBOS Portal`，
Frappe clean-site sync 需要对应 Python module package：

```text
hbos_portal/hbos_portal/
```

修复：

```text
apps/hbos_portal/hbos_portal/hbos_portal/__init__.py
```

并增加自动契约测试，保证每个 `modules.txt` 声明都存在对应 Python package。

该问题说明：

- P2.2 existing-site smoke 通过不等同于 clean-site 可复现；
- clean-site Gate 必须继续保留。

## 7. Real Frappe Runtime Gate

Platform clean-site Gate：

```text
GitHub Actions Run:
36036356941

Conclusion:
SUCCESS
```

真实 runtime 输出：

```json
{
  "registry_entries": ["lims"],
  "registry_failures": 0,
  "lims_route": "/hbos/lims",
  "lims_manifest_capabilities": [],
  "lims_access": true,
  "bootstrap_apps": ["lims"],
  "user": "Administrator"
}
```

同时同一 clean-site 中：

```text
Attendance G1 DB checks = PASS
LIMS + Inventory release chain = PASS
LIMS frontend = PASS
```

说明首个 Portal Provider 没有破坏既有三业务 App 集成。

## 8. Definition of Done

```text
P3-LIMS-1 Manifest             = PASS
P3-LIMS-1 Access Context       = PASS
P3-LIMS-1 Frappe Hook Discovery = PASS
P3-LIMS-1 Registry             = PASS
P3-LIMS-1 Bootstrap Visibility = PASS
P3-LIMS-1 Stable App Route     = /hbos/lims
P3-LIMS-1 Business Data Writes = NONE
P3-LIMS-1                      = COMPLETE
```

## 9. 下一步

下一步不是立刻打开 Tasks。

先进入：

```text
P3-LIMS-2 — Stable Deep-link Adapter
```

原因：

LIMS 现有 Todo projection 已经非常成熟，但它返回的是 App 内部 route / route_params。

Portal My Work 需要稳定：

```text
/hbos/lims/<resource>/<id>/<action?>
```

因此必须先建立：

```text
LIMS internal route
        ↓
LIMS-owned Portal deep-link adapter
        ↓
stable /hbos/lims/... URL
```

再进入：

```text
P3-LIMS-3 — My Work Projection
```

Portal 不得直接暴露 LIMS 内部 Vue route 或 Frappe DocType route。
