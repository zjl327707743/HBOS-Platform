# HBOS Portal P3 — LIMS Provider Registration

**状态：P3-LIMS-1 ~ P3-LIMS-5 COMPLETE / RUNTIME GATE PASS**  
**日期：** 2026-09-25  
**分支：** `feature/hbos-portal-product`

## 1. 当前阶段

LIMS 已成为 HBOS Portal 第一个真实 Business App Provider。

当前完成链路：

```text
P3-LIMS-1  Manifest / Access / Registration      COMPLETE
P3-LIMS-2  Stable Deep-link Adapter              COMPLETE
P3-LIMS-3  My Work Task Projection               COMPLETE
P3-LIMS-4  Summary Projection                    COMPLETE
P3-LIMS-5  Search Provider                       COMPLETE
```

当前 LIMS manifest capability：

```json
["summary", "tasks", "search"]
```

`summary`、`tasks`、`search` 三项 experience capability 均已通过独立 Gate。

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
- 一个业务 App 不存在时 Portal 仍可启动；
- Portal 只依赖 Application Contract，不依赖 LIMS DocType / workflow 实现。

## 3. P3-LIMS-1 — Manifest / Access / Registration

LIMS 稳定 manifest：

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
  "capabilities": ["tasks"]
}
```

说明：

- P3-LIMS-1 首次注册时 `capabilities=[]`；
- P3-LIMS-3 通过 Gate 后只开放 `tasks`；
- `summary` / `search` 必须分别通过后续 Gate 才能加入 manifest。

### Access Context

Provider 从：

```text
frappe.session.user
frappe.get_roles(user)
```

推导当前身份。

Portal 不传 user / roles，也不解释 LIMS Role 名称。

LIMS Access Adapter 继续复用现有 LIMS Authority：

- `LIMS_BUSINESS_ROLES`；
- `workflow_contract.ROLE_SYSTEM`；
- Frappe built-in `Administrator` break-glass identity。

输出为语义 Access DTO，不把原始 LIMS role names 暴露给 Portal 授权逻辑。

### P3-LIMS-1 Runtime

GitHub Actions Run：

```text
36036356941 = SUCCESS
```

首次真实 runtime：

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

## 4. Main / PR #20 同步

在 P3 继续开发前，Portal 分支已吸收最新 `main`，包含已合并 PR #20 的 LIMS production-entry 修复。

合并时显式保护三处交叉文件：

- `apps/hb_lims_app/hb_lims_app/hooks.py`
- `docker-compose.yml`
- `scripts/ci/platform_clean_site_smoke.sh`

最终同时保留：

- `/hbos-lims/*` production history-mode entry；
- LIMS Vite manifest / persistent assets；
- `hbos_portal_provider` Hook；
- `hbos_portal` Compose mount / PYTHONPATH；
- Portal Registry runtime checks；
- LIMS production-entry runtime checks。

同步 merge commit：

```text
411d550d6a61cb7b24c28004526d8fb5bc902e3a
```

对应 Platform Integration Gate 已 PASS。

## 5. P3-LIMS-2 — Stable Deep-link Adapter

Portal 的产品 URL 必须稳定：

```text
/hbos/lims/...
```

而当前 LIMS production implementation 仍部署在：

```text
/hbos-lims/...
```

因此建立 LIMS-owned 双向适配：

```text
LIMS Todo internal route + route_params
        ↓
build_stable_deep_link()
        ↓
/hbos/lims/...
        ↓
Portal Route Resolver
        ↓
LIMS resolve_stable_route()
        ↓
/hbos-lims/...
```

实现保证：

- 拒绝 scheme / netloc / fragment；
- 拒绝 `..` traversal；
- 拒绝 backslash；
- Stable URL 必须留在 `/hbos/lims` namespace；
- query params 统一编码；
- 当前所有 `TODO_RULES` route 有契约测试。

Runtime authority 保持正确依赖方向：

- LIMS 自己验证 internal → stable；
- Portal 只通过 Provider Contract 验证 stable → implementation；
- `hbos_portal` 不静态 import `hb_lims_app`。

P3-LIMS-2 Runtime Gate：

```text
HBOS Portal Backend Gate      = PASS
HBOS Portal Frontend Gate     = PASS
HBOS Quality Gate             = PASS
HBOS Platform Integration Gate run 36041405419 = PASS
```

## 6. P3-LIMS-3 — My Work Projection

P3-LIMS-3 不创建第二套 Todo。

数据链：

```text
LIMS authoritative business state
        ↓
existing todo_service.get_my_todos()
        ↓
LIMS Portal Task Adapter
        ↓
Unified Task DTO
        ↓
hbos_portal tasks dispatcher
        ↓
Portal /hbos/work
```

新增的 LIMS adapter 只做：

- semantic priority 映射；
- opaque global `task_id`；
- `assignment_type` 语义化；
- stable deep-link 生成；
- cursor / pagination adapter；
- 删除 Portal 不应依赖的 raw role / DocType 内部字段。

不会：

- 创建 Portal Todo DocType；
- 复制 LIMS workflow state；
- 在 Portal 中直接审批；
- 绕过 LIMS SoD / workflow / audit；
- 让 Portal 查询 LIMS DocType。

### Unified Task DTO

典型输出：

```json
{
  "task_id": "lims:<opaque-local-key>",
  "app_id": "lims",
  "category": "testing",
  "title": "检验任务",
  "description": "复核结果",
  "action": "review_result",
  "action_label": "复核结果",
  "priority": "high",
  "due_at": "2026-09-25",
  "overdue": false,
  "assignment_type": "role_pool",
  "deep_link": "/hbos/lims/tasks?scope=mine&task=TASK-001",
  "modified_at": "..."
}
```

Portal v1 点击任务后：

```text
stable deep_link
  ↓
hbos_portal.api.routes.resolve_route
  ↓
current implementation path
  ↓
business app executes protected action
```

业务动作继续由 LIMS 自己重新校验权限、状态、SoD 与审计。

### Frontend integration

真实 Frappe mode：

- Bootstrap 先渲染 Shell；
- 对声明 `tasks` capability 的 App 异步加载 Tasks；
- Provider failure 使用 `Promise.allSettled` 隔离；
- My Work / 首页待办数量随后更新；
- App Center / App Switcher / My Work 使用同一 Stable Route Resolver；
- Mock mode 继续保留原型本地路由。

## 7. P3-LIMS-3 Runtime Gate

最终代码 Head：

```text
67bee0fb44bd103fc6e3216aeb099957f6f4f71b
```

GitHub Actions：

```text
HBOS Portal Backend Gate  = PASS
HBOS Portal Frontend Gate = PASS
HBOS Quality Gate         = PASS
HBOS Platform Integration Gate
  run 36042393976         = SUCCESS
```

clean-site runtime 关键输出：

```json
{
  "registry_entries": ["lims"],
  "registry_failures": 0,
  "lims_route": "/hbos/lims",
  "lims_manifest_capabilities": ["tasks"],
  "lims_access": true,
  "lims_resolved_route": "/hbos-lims/tasks?scope=mine&task=TASK-001",
  "bootstrap_apps": ["lims"],
  "user": "Administrator"
}
```

LIMS-owned deep-link / tasks runtime：

```json
{
  "stable_link": "/hbos/lims/tasks?scope=mine&task=TASK-001",
  "resolved_path": "/hbos-lims/tasks?scope=mine&task=TASK-001",
  "task_count": 0,
  "next_cursor": null
}
```

`task_count=0` 是 clean-site Administrator 无当前 LIMS 业务待办的预期结果；本 Gate 验证真实 Provider 调用、序列化和路由链不会报错。非空 Task DTO 由契约测试覆盖。

同一 clean-site 继续通过：

```text
Attendance G1 DB checks
LIMS + Inventory release chain
LIMS frontend unit/build
LIMS production entry
frontend recreation asset persistence
```

最终：

```text
HBOS PLATFORM clean-site integration PASS
```

## 8. Definition of Done

```text
P3-LIMS-1 Manifest / Access / Hook / Bootstrap = PASS
P3-LIMS-2 Stable Deep-link Adapter             = PASS
P3-LIMS-2 Dependency Direction                 = PASS
P3-LIMS-3 Existing LIMS Todo Reuse             = PASS
P3-LIMS-3 Unified Task DTO                      = PASS
P3-LIMS-3 Stable My Work Link                   = PASS
P3-LIMS-3 Portal Frontend Consumption           = PASS
P3-LIMS-3 Business Data Writes                  = NONE
P3-LIMS-3 New Portal Todo State                 = NONE
P3-LIMS-1 / 2 / 3                               = COMPLETE
```

## 9. 下一阶段

下一阶段：

```text
P3-LIMS-4 — Summary Projection
```

目标是让 Portal Home 从“可进入 LIMS + 有真实 My Work”继续升级到“有真实 LIMS 业务摘要”。

仍保持：

- 只读 projection；
- LIMS 自己计算业务语义；
- Portal 不查 DocType；
- 不复制业务事实；
- `search` 继续保持关闭，待 P3-LIMS-5 单独 Gate。


## 10. P3-LIMS-4 — Summary Projection

Summary 没有复制 LIMS Dashboard 的全局统计逻辑，而是复用现有权限感知：

```text
todo_service.get_my_todo_summary()
```

由 LIMS 自己转换成 Portal semantic Summary DTO：

- 我的 LIMS 待办；
- LIMS 超期；
- 检验待办；
- 稳定性待办。

所有指标均针对当前 Frappe Session 用户，不让 Portal 重算业务事实，也不默认暴露全实验室范围数据。

Portal 真实模式按 manifest `summary` capability 异步加载；Provider failure 单卡隔离。

Runtime authority：

```text
Head 86496e5eeb8d2d585d5288a9fd6327308c2593de
Platform Integration Gate run 36044803594 = SUCCESS
```

clean-site 输出：

```text
lims_manifest_capabilities = ["summary", "tasks"]
summary_status = normal
summary_metrics = 4
HBOS PLATFORM clean-site integration PASS
```

## 11. P3-LIMS-5 — Search Provider

Search v1 只开放一个有明确业务落点的实体：

```text
HBOS Test Result
```

实现原则：

- 使用 permission-aware `frappe.get_list`；
- 不使用 unrestricted `frappe.get_all`；
- 当前支持按结果编号 / 样品编号 / 检验项目匹配；
- 返回 Stable Deep Link：`/hbos/lims/results/<id>`；
- Command Palette 点击后仍通过 Portal Route Resolver 进入当前 `/hbos-lims/results/<id>`；
- 空查询在前端不发请求；
- 样品 / COA 等没有稳定单记录 route 的对象本阶段不伪造 deep link。

最终 Runtime：

```text
Head 7cc1804e4d484feef221ba8b513ec07f036af281
HBOS Portal Backend Gate = PASS
HBOS Portal Frontend Gate = PASS
HBOS Quality Gate = PASS
HBOS Platform Integration Gate run 36045590049 = SUCCESS
```

clean-site 关键输出：

```json
{
  "registry_entries": ["lims"],
  "registry_failures": 0,
  "lims_manifest_capabilities": ["summary", "tasks", "search"],
  "bootstrap_apps": ["lims"]
}
```

LIMS-owned runtime：

```json
{
  "task_count": 0,
  "summary_status": "normal",
  "summary_metrics": 4,
  "search_results": 0
}
```

clean-site 无业务数据时 0 条 task/search 是预期；非空 DTO 映射由 contract tests 覆盖。

## 12. LIMS Provider Phase Complete

```text
Manifest / Access       PASS
Stable Entry            PASS
Stable Deep Link        PASS
My Work / Tasks         PASS
Summary                 PASS
Search                  PASS
Business Writes         NONE
Portal Todo State       NONE
Portal → LIMS Static Import NONE
```

LIMS 作为首个完整 HBOS Application Provider 的基础 experience contract 已收口。

下一步转入：

```text
P3-ATT-1 — Attendance Manifest / Access / Stable Entry
```
