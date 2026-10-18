# P4 生产看板 —— 权限接入与 IAM 需求

> 日期：2026-10-12
>
> 分支：`integration/hbos-production-clean-20261012`
>
> 依据：`docs/governance/HBOS_BACKEND_AND_IAM_BOUNDARY_V2_PROPOSAL.md`（#38，PROPOSED）、
> `docs/governance/HBOS_CONCURRENT_APP_INTEGRATION_V1.md`（#45）
>
> 状态：**默认拒绝已落地；正式角色与车间范围待 Owner 批准**。

## 1. 接入前后的访问链路（这是本轮的核心改动）

**接入前（#33 / #40 的形态）** —— 浏览器直连 FastAPI：

```text
员工浏览器 ──(VITE_PRODUCTION_SERVICE_ORIGIN)──> 生产 FastAPI ──> 飞书多维表格
```

问题：服务地址暴露在浏览器里，任何人不经 Portal 就能打它；FastAPI 只靠 CORS 判断来源，
而 **CORS 是浏览器行为，不是鉴权**；权限与数据范围无从谈起。

**接入后（本分支）** —— 经过 HBOS 受控后端：

```text
员工浏览器（Frappe Session）
   ↓  callFrappeMethod('hbos_portal.api.production.get_board')
HBOS 受控后端 API（hbos_portal/api/production.py）
   ├─ ① require_authenticated_user()   必须有有效 HBOS 会话
   ├─ ② get_entry('production')        应用必须已注册
   ├─ ③ require_app_access(entry)      必须有生产看板权限（默认拒绝）
   ↓  服务间令牌 X-HBOS-Service-Token
生产 FastAPI（services/hbos_production）
   ├─ ④ require_service_token          令牌未配置 → 503；不带/不对 → 401
   ↓
飞书多维表格（只读）
```

浏览器**不再知道** FastAPI 的地址，也不持有它的令牌。

## 2. 五条最低要求 vs 实现

| 要求 | 实现 | 位置 |
|---|---|---|
| ① 员工必须使用有效的 HBOS 登录会话 | `require_authenticated_user()`，Guest 一律拒 | `hbos_portal/services/access.py`（既有）+ `api/production.py` |
| ② 后端判断是否有生产看板访问权限 | `require_app_access()` → `build_access_context()` | `hbos_portal/production/access.py` |
| ③ 车间、部门范围由服务端确定 | access 契约的 `scopes` 由服务端产出（当前为空 = 暂无范围能力，**不等于 ALL**） | 同上 |
| ④ 未登录 / 无权限 / 越范围必须拒绝 | 分别返回 `UNAUTHENTICATED` / `FORBIDDEN`；FastAPI 侧 401 / 503 | `api/production.py` + `services/hbos_production/app/main.py` |
| ⑤ 不另建员工账号体系 | 沿用 Frappe User + Frappe Session，不新增账号表 / JWT / IAM 微服务 | 全链无账号代码 |

第六条的落地：生产角色名走 `PRODUCTION_ROLES` 常量（`production/access.py`），
**不在前端拼权限**，见 §3。

## 3. 默认拒绝（本轮的安全姿态）

Owner 尚未批准生产看板的正式角色，因此：

```python
# apps/hbos_portal/hbos_portal/production/access.py
PRODUCTION_ROLES: tuple[str, ...] = ()   # 空 = 默认拒绝
```

- 除内置 `Administrator`（本仓库既有的**审计 break-glass** 身份）外，**任何人都不放行**；
- 普通员工（哪怕有 Stock User / System Manager 等角色）**一律拒绝** ——
  平台管理角色 ≠ 生产业务角色（IAM 边界提案 §3）；
- 被拒的用户在 `bootstrap` 里看不到生产看板入口，直接调后端 API 也会拿到 `FORBIDDEN`；
- 服务端令牌未配置时，FastAPI **拒绝所有数据请求**（503），不允许「没配就跑匿名」。

**明确不做**（为了页面「能打开」而绕过授权）：不开 allow_guest、不在前端放角色名、
不用前端 CORS 当鉴权、不为演示临时放行。

## 4. 需要 Owner 决定的 IAM 事项（交付物之一）

| # | 事项 | 现状 | 需要 Owner 定 |
|---|---|---|---|
| 1 | **生产看板角色** | `PRODUCTION_ROLES` 为空 | 哪些 Frappe Role 可进？（建议按 IAM 提案 §3 的领域层能力命名，如 `production.board.read` 绑定的角色） |
| 2 | **车间 / 部门数据范围** | `scopes` 为空 | 生产管理岗是否只看本车间？还是全厂？范围从哪个字段取（Employee.department / 自定义字段）？ |
| 3 | **入口区分** | 未实现 | 是否要像 IAM 提案那样区分「企业员工门户 / 管理中心」两个入口？ |
| 4 | **服务间令牌的存放与轮换** | 静态共享令牌 | 是否接受静态令牌（最小形态），还是要签名 / 短时效？ |
| 5 | **质量合格率口径冲突** | 固定 99.9% | IAM 提案 §4 要求「缺真实来源标未接入」，与 Owner 10-10 的「沿用 99.9%」冲突 —— 以哪个为准？ |
| 6 | **生产看板 provider 的归属** | 暂放 `hbos_portal`（无独立 Frappe App） | 将来是否拆 `hbos_production_app`？本轮不拆（未授权新建 App） |

## 5. 负向测试（已跑）

`apps/hbos_portal/tests/test_production_contract.py`：

```text
test_guest_denied                        未登录 → 拒
test_ordinary_user_denied                普通员工（含其它业务角色）→ 拒
test_platform_roles_do_not_grant_production  System Manager / HR Manager → 拒
test_administrator_allowed_as_break_glass    Administrator → 放行（break-glass）
test_context_carries_no_raw_role_names       不把原始角色名透给前端
test_scope_is_empty_not_all                  空范围 ≠ ALL
```

`services/hbos_production/tests/test_service_auth.py`：

```text
test_data_endpoints_reject_without_token     不带令牌 → 401，响应体无数据
test_data_endpoints_reject_wrong_token       令牌不对 → 401
test_data_endpoints_refuse_when_token_not_configured  未配置 → 503（默认拒绝）
test_health_stays_open_but_leaks_nothing     /health 可探活但不含业务数据
test_correct_token_reaches_the_data_layer    带对令牌 → 进到取数层
```

结果：**12 例全部通过**（portal 7 + service 5）。

## 6. 部署前必须配置（不配就拒绝）

```text
site config（frappe.conf，不进仓库）：
  hbos_production_service_url    = http://127.0.0.1:8101
  hbos_production_service_token  = <与下面一致>

services/hbos_production/.env（不进仓库）：
  HBOS_PRODUCTION_SERVICE_TOKEN  = <同一个值>

services/hbos_production_ai/.env（不进仓库）：
  HBOS_AI_ENABLED=0     # 默认关
  HBOS_AI_DRY_RUN=1     # 默认干跑，不写飞书
```

**真实飞书写回默认关闭**：AI 分析服务要真写必须同时设 `HBOS_AI_ENABLED=1` 且 `HBOS_AI_DRY_RUN=0`，
两道开关叠加，避免「拉了个 .env 就悄悄写生产表」。
