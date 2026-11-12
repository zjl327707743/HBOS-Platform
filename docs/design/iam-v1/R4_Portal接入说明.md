# R4 Portal 最小接入候选说明

状态：`DESIGN_CANDIDATE_NOT_IMPLEMENTED`。本说明及同目录 `R4_Portal接入候选.patch` 只供 R4 A 阶段审阅；未应用到正式源码，未注册正式路由，未接入后端，未获得 B 阶段实施授权。不得把该 patch 或 R3 原型整包合入产品。

## 固定来源及三个共享文件

产品基线：`39366822a5b5d6041b9eea94da4f77255ad26761`。patch 的旧内容逐字取自该提交的真实文件：

| 文件 | 旧代码位置 | 候选增量 |
|---|---|---|
| `frontend/hbos-portal-web/src/router/index.ts` | `:27-37` 现有 PortalLayout children；`:64-69` 标题处理 | 同一 Shell 下增加 `/hbos/admin` 四个子路由及独立 `/hbos/attendance/me`；管理页读取页级能力，本人考勤由领域服务判定；无权限与服务错误分开 |
| `frontend/hbos-portal-web/src/components/layout/PortalSidebar.vue` | `:3-14` 主导航和个人入口；`:23-37` 图标与 props | 只增加一个“管理中心”，四项页级能力任一允许时显示；不把四个子页堆入全局侧栏 |
| `frontend/hbos-portal-web/src/components/layout/PortalLayout.vue` | `:10-20` 现有 Header/Sidebar；`:21-31` 会话加载与内容；`:42-64` setup 生命周期 | 复用品牌/Shell/usePortalSession；bootstrap 后用 keyed FirstPasswordGate 包裹业务 RouterView，覆盖 OAuth 回调直接进入工作台；Gate ready 后才读取管理能力 |

`/hbos/profile`、`/hbos/login`、恢复和绑定路由保留现有职责。候选 AdminWorkspace 只能放局部页签、标题、内容与 RouterView，不再渲染 GlobalHeader、PortalSidebar 或另一套登录。绿色管理区域用共享 tokens 或局部样式，既有全局玻璃风不在此 patch 修改。

## 新 imports 的明确依赖

下列文件是 **B 阶段新增候选，当前尚不存在**。patch 不包含这些文件的实现，因此 `git apply --check` 通过也不意味着能够构建或运行。正式文件白名单由唯一开工单汇总。

| 候选文件 | 最小职责 |
|---|---|
| `frontend/hbos-portal-web/src/services/iamAccess.ts` | 导出 `fetchIamCapabilities()` 和 `IAM_ADMIN_PAGES`；走现有 frappeClient、当前会话、同源后端；无 caller-supplied user/actor；不读前端角色或原型存储兜底 |
| `frontend/hbos-portal-web/src/components/account/FirstPasswordGate.vue` | 与账号安全候选共用：读取当前 session 的 temporary_password_state/first_password_required，重新确认状态后决定 initial-password、identity、ready；ready 事件仅用于刷新 UI |
| `frontend/hbos-portal-web/src/components/account/InitialPasswordDelivery.vue` | 当前已验证本人一次安全领取及必要首次改密流程；一次口令仅内存展示，卸载清除；settled 后必须重读安全状态，不能直接放行业务 |
| `frontend/hbos-portal-web/src/components/account/EmployeeIdentityStatus.vue` | 通过当前 session 的 get_my_employee_status 展示最小关联状态，不接 caller user/employee；不伪造员工 |
| `frontend/hbos-portal-web/src/views/admin/AdminWorkspaceView.vue` | 仅局部页签及嵌套 RouterView，按服务端能力显示子页；无双顶栏/双侧栏；能力失败/撤销时清除原数据 |
| `frontend/hbos-portal-web/src/views/admin/PeopleAdminView.vue` | Employee 中心的受控人员投影与明确关联；本人 API 不被选中员工替换主体 |
| `frontend/hbos-portal-web/src/views/admin/DepartmentsAdminView.vue` | 受控部门及普通预设；范围、影响和保存结果来自后端 |
| `frontend/hbos-portal-web/src/views/admin/AccessAdminView.vue` | 成对的应用/动作/范围、明确禁止及来源；复用既有注册能力名称 |
| `frontend/hbos-portal-web/src/views/admin/AuditAdminView.vue` | 独立审计读取能力及目标/字段范围；管理其他三页不隐含审计读取 |
| `frontend/hbos-portal-web/src/views/admin/AdminAccessUnavailableView.vue` | 无私有数据的服务错误页；显示重试和返回 HBOS；重试目标须通过 accountRedirect 再限制为管理路由，错误不得显示原始异常 |
| `frontend/hbos-portal-web/src/views/attendance/MyAttendanceView.vue` | 复用现有 Portal Shell 的“我的考勤”；只调用当前 session 本人接口，无 caller user/employee/department 替换主体；未接入即明确拒绝，不回退旧 HR dashboard |
| `frontend/hbos-portal-web/src/services/attendancePersonal.ts` | 现有同源 frappeClient 的本人读取适配；由后端 attendance.read 与 self 范围判定，分页/数量/明细/汇总同范围；没有真实导出能力时不可生成下载 |
| `apps/hbos_portal/hbos_portal/api/iam_access.py` | 候选方法 `hbos_portal.api.iam_access.get_capabilities`；只判定当前服务端会话的管理页能力；不是客户端自传角色或 User 的代理查询 |

`accountRedirect`、`FrappeRequestError`、`isUnauthenticatedError` 是上述固定产品已经存在的 exports，来源分别是 `services/accountNavigation.ts:2-11` 和 `services/frappeClient.ts:29-39,98-100`。本次不改它们。

## 候选页级能力契约

以下四个 ID 是本轮确定的**待注册候选**，不是当前产品已完成的能力：

| 页面 | 后端判定后返回的允许能力 ID |
|---|---|
| `/hbos/admin/people` | `iam.people.read` |
| `/hbos/admin/departments` | `iam.departments.read` |
| `/hbos/admin/access` | `iam.access.read` |
| `/hbos/admin/audit` | `iam.audit.read`（独立） |

`IAM_ADMIN_PAGES` 是固定的路径/能力 ID 映射和入口顺序（按上表），本身不产生权限。`fetchIamCapabilities()` 的前端返回类型至少为 `{ capabilities: readonly string[] }`，其中只包含当前服务端判定允许的能力。后端响应还需在唯一开工单冻结主体、授权修订、schema 版本及安全错误语义；适配器必须校验形状、白名单和当前会话绑定，缺失/未知/失败不能默认为全部允许。

服务依赖应使用现有同源 `callFrappeMethod` 与 Frappe Cookie/Session，不创建第二账号服务；不向方法传递选中员工替换会话主体。服务响应不持久化到 localStorage，不以模拟数据、硬编码管理员或 role 列表补齐；响应禁缓存或绑定正确的会话与授权修订，撤权后不能使用旧能力结果放行。

导航 guard 每次进入管理路由重新读取能力：

- `/hbos/admin` 跳到第一个可访问子页，避免只有审计能力的主体被固定跳到人员页。
- 没有对应能力或明确 403 → 现有 `/hbos/403`。
- 会话失效 → 现有 `/hbos/login`，保留经过 `accountRedirect` 过滤的站内返回路径。
- 网络/服务/载荷错误 → 新候选 `admin-unavailable` 安全状态页，禁止回退为允许或误称权限已生效。

guard 和入口隐藏只负责导航体验。列表、单条、写入、统计、导出及审计等每个后端请求仍须独立核验当前会话、管理动作、目标与范围；前端页级能力不能替代后端授权或成为 User/Role/Employee.user_id 的可编辑授权真相。管理页可见不隐含 `attendance.read`、`attendance.export` 或任何领域业务资格。

## OAuth 直接进入工作台与本人考勤接缝

PortalLayout 现有会话 bootstrap 成功后，在 RouterView 外增加 `FirstPasswordGate :key="portal.user?.id"`，与登录/profile 候选使用同一组组件。`initial-password` slot 接入 InitialPasswordDelivery，`identity` slot 展示 EmployeeIdentityStatus，只有 `ready` slot 挂载业务 RouterView。初始密码、临时状态、到期和会话变更均须重新读当前服务端状态；`onSettled` 和 ready 事件不是身份证明。

这里不新增平行 session、cookie 或登录实现。Gate 的 current-session adapter 遇到 session-required 应使用现有安全清理与同源登录跳转：复用 Portal store clearSession、accountRedirect 与既有 `/hbos/login`；PortalLayout 不再另写一套失效处理。InitialPasswordDelivery 的 session-required 在此接到 Gate 提供的 onSettled，含义是重新请求当前安全状态；401 必须由 Gate 安全跳登录，不能当作结算成功/ready。所有这些组件尚未实现，该契约是 B 待测项。

首次改密所需的既有 reauthenticate/set_password 操作必须在 Gate 阻断期间可达，不能等待 ready 后才挂载 profile 改密表单而形成死锁。待关联员工可获得批准的最低基础体验，考勤仍拒绝；服务/应急管理主体没有 Employee 时须显示“不适用”，不得为了通过 Gate 伪造员工或剥夺已批准的独立管理能力。

后端临时 request gate 仅放行最小 bootstrap 身份/品牌/apps 元数据和精确本人安全/证明/领取/改密方法；不能按路径前缀放行。现有 Store 在 bootstrap 后会另发 tasks/summary/twin 请求，这些请求仍由后端逐方法拒绝。只有状态重新确认并解除限制后才允许业务刷新；前端遮住 RouterView 不代替此服务端限制。本候选没有修改 bootstrap 服务。

新增 `/hbos/attendance/me` 是同一 PortalLayout 的普通子页，不挂 `iam.*` 管理 guard，也不因此获得数据权限。后端从当前 session 求唯一 Employee，以现有 `attendance.read` 和 self 范围判定；无关联、冲突、停用、未接入均拒绝。本人 resolver 只返回该路径，不落入旧全量 HR dashboard。

平台路径源码兼容已核对：`apps/hbos_portal/hbos_portal/services/routes.py:41-58,66-88` 接受 attendance 前缀稳定路径与同源绝对实现路径，`frontend/hbos-portal-web/src/services/businessNavigation.ts:13-14,47-49` 对 `/hbos/` 使用现有 SPA Router。不需要为这一新同源路径另改平台 resolver；provider 的具体新本人 resolver 及页面/API 仍尚未实现，运行 `NOT_RUN`。

## 已做检查与限制

- `git apply --check -- docs/design/iam-v1/R4_Portal接入候选.patch`：通过，仅语法与三个基线共享文件上下文匹配检查；没有应用 patch。
- 候选 Router TypeScript AST、两个候选 Vue 文件的 script/template 语法检查通过；新 imports 仍未实现，这不是正式构建或运行通过。
- 三个正式文件的工作区 diff 仍为空。本次只新增设计 patch 和本说明；不提交、不改原型、不改产品入口。
- 缺少的新 imports、候选后端服务、能力注册、页面数据/写入服务及隔离运行未实现，因此正式构建、OAuth 直接进入工作台、首次改密门禁/失效、本人考勤、浏览器路由、会话/撤权、API/SQL、旁路、审计和真实数据库验证均 `NOT_RUN`。
- 移动导航没有在本最小 patch 增加重复入口；B 阶段需在保留现有 Shell 的前提下确认小屏管理入口可达及键盘/焦点行为。正式接入前须完成直接刷新、无权限、会话失效、服务失败、只有审计能力、撤销能力及 1280/1440 视口验证。

本设计候选只能并入 R4 A 阶段的唯一开工单评审。正式源修改、后端实现、隔离 Site、迁移、合并和部署仍须各自适用授权。
