# R4 A 唯一开工单：身份关联、我的考勤与 Portal 接入

日期：2026-10-15。状态：`IAM_R4_IDENTITY_CONTRACT_AND_DELTA_REVIEW_READY`。本单是 B 阶段候选，B/C 均 `NOT_RUN / PENDING_OWNER`。用户本次直接授权“按这份 R4 任务书启动 A 阶段”；任务书中的 B/C 是后续范围，不是本轮实施授权。登录视觉认可也不等于 R3 全量签核。

## 1. 固定版本、目录与交付边界

| 项目 | 固定值 / 实际结果 |
|---|---|
| 仓库 / origin | `/Users/hb/Projects/HBOS-IAM-V1` / `https://github.com/zjl327707743/HBOS-Platform.git` |
| 产品基线 | `feature/hbos-portal-product@39366822a5b5d6041b9eea94da4f77255ad26761`；本轮重新 fetch，无漂移 |
| R3 原型基线 | `design/iam-v1-prototype-20261014@e7486a9cb3ded7a32a9ead17990e158562605d44`；Draft PR #50 保留 |
| R4 分支 | `design/iam-v1-r4-identity-attendance-20261015`，从 R3 基线新建；完整候选 HEAD 以本次 Draft PR 和随交付的冻结卡为准 |
| A 允许改动 | 仅 `prototypes/iam-v1/**`、`docs/design/iam-v1/**`；真实产品、schema、Site、Docker、调度与数据均未改 |
| A 预览 | `http://iam-prototype.localhost:5197/`，只绑定 `127.0.0.1`；5196 原有服务保留 |
| 隔离与旧成果 | 独立 IAM clone；未 reset/stash/clean，未覆盖旧分支、PR 或 R3 交付；未带入 #42/#49/#37 |

R4 增量以 `git diff e7486a9cb3ded7a32a9ead17990e158562605d44 <候选HEAD> -- prototypes/iam-v1 docs/design/iam-v1` 查看。由于提交不能包含自身 SHA，交付冻结卡在提交后记录完整 HEAD、base、PR 与差异指纹；Owner 应批准该冻结值。若产品基线漂移，先报告具体差异，不能自动更换批准对象。

Issue #41 最新记录和 #50 均已只读核对；#42/#49 仍是未合并的独立修复链。仓库根状态文档存在旧状态，本轮不越过 A 白名单修改；由集成线根据本单更新里程碑。

## 2. A 阶段交互：沿用、调整、延后

| 类别 | 本轮结果 |
|---|---|
| 沿用 | R3 登录布局、飞书优先/密码备用、三页视觉、部门普通预设、个人例外、调岗、停用与失败反馈；没有重画全站 |
| 调整 1 | Employee 中心列表包含未开户档案；员工数、已开通 User、待关联和非员工主体分开；详情显示稳定键、前导零字符串工号、企业/飞书/考勤来源关联；常用操作为已有员工开户/关联已有账号 |
| 调整 2 | 本企业首次核验后自动开户、预建账号证明后复用、冲突、待 Employee 关联、外企业拒绝；重复登录不重复创建或重置密码；待关联账号没有伪造 Employee |
| 调整 3 | 考勤实例：本人/指定部门读取、独立导出判定、他人参数拒绝；SELF∩部门按记录语义求交，限定 deny 只扣匹配对象，APP deny 全禁 |
| 安全主体 | 管理员选择的员工仅是配置目标；本人改密/换绑从当前会话主体执行，不跟随目标下拉框 |
| 延后 | 正式 Portal 路由和后端、真实 OAuth/MFA/密码、原生权限/副作用、真实部门历史报表与导出、真实来源映射/数据纠错，全部不是 A 阶段 PASS |

截图在 `screenshots-r4/`；原型验证见 `R4_A_验证记录.md`。全部为合成资料，没有原件行、真实姓名/工号/手机号进入截图或 PR。R4 使用独立 `hbos.iam-v1.r4.synthetic.v4`，不迁移或清除 R3 存储；此演示状态绝不能成为正式数据库。

## 3. 唯一身份链与来源选择

`考勤来源人员标识 → 已有 Employee.name ← Employee.user_id → 唯一 User.name ← 飞书 / 密码`

字段和锁定源码逐项证据在 `R4_A1_身份链与考勤来源证据.md`，属于本开工单附件。User.name/Employee.name 保持原键；username 复用既有拼音及冲突后缀，仅为登录别名。姓名、拼音、邮箱、手机号相同都不能证明员工归属；通讯录用户 ID 未经类型和企业/app 核验不能当 OAuth open_id。

映射选择：先复用已确认的 Employee.employee_number 与原生 attendance_device_id；二者语义分开，保留来源字符串与前导零。得力云当前同步真正使用 `check_data.employee_num`；`rec.user_id` 未建立当前归属契约。`rec.id` 是打卡事件，terminal_id/SN 是终端，均不是人员键。现有同步没有证明工号的企业/来源命名空间唯一性；真实映射保持待核对。

本次 B 候选**不新增考勤来源映射表**。若未来证据证明存在多来源/编号复用，再由考勤接入域申请最小 source/namespace/external_person_id/Employee/status/有效期/确认来源扩展；不在 IAM 内建第二员工库。缺可靠标识、冲突、多候选、姓名不一致均异常隔离，不能取第一条。

Employee Checkin.employee 与 Attendance.employee 复用原生 Employee 外键。月度对账暂存目前只有工号/姓名/部门文本及 JSON，不作为可信本人结果。本人历史按已确认同一 Employee 保留；调岗不重写历史外键。主管历史查询必须有事件时部门/有效任职证据，当前部门不能代替历史证据；无证据拒绝。

### 同步兼容补丁交考勤线，A/B 不擅改现行同步

源码 `api.py:242-255` 仍有姓名兜底；移除时须同时保留身份异常事件待处理/重试能力。现有未匹配仅 skipped，而 `:298-303` 在 write_failed=0 时推进游标，单删兜底会永久越过事件。建议严格解析器按批准命名空间查询唯一标识，0/多候选进持久待处理收据；没有收据能力时含异常批次不推进游标并幂等重拉，由考勤线评估积压。姓名仅差异提示，不认领。其他导入 `_match_or_create_employee` / `_find_employee` 同步收口，但不运行历史导入、清空、回填、重算。本单不授权部署这份兼容补丁或纠正真实历史。

## 4. B 接口、操作 ID 与范围契约（均须服务端执行）

已有：`attendance.read`（`portal/access.py` 注册），现阶段仍主要向 HR/管理角色开放；既有 `auth/onboarding.py` 已实现企业核验后 User 创建/拼音/锁/复用，**没有 Employee 关联，也没有新建用户初始本地密码**。

以下方法为明确新增候选，当前没有实现：

| 候选方法 / 操作 ID | 约束与结果 |
|---|---|
| `hbos_portal.api.iam_people.list_people` / `iam.people.read` | Employee 中心分页，未开户也返回；非员工 User 单独查询分类。敏感关联标识另核管理能力，普通本人页不下发 |
| `hbos_portal.api.iam_people.preview_link`、`link_user` / `iam.people.link` | 已有 Employee 与指定 User 的明确归属证明，先预览再事务提交；同号/同名不自动匹配，锁 Employee/User 防并发争用，重复关联幂等，审计版本 |
| `hbos_portal.api.iam_people.create_user` / `iam.people.provision` | 从已核验已有 Employee 受控开户，原键/部门/记录保留；已存在 User 进入归属证明，不再开户；临时密码一次受控交付 |
| `hbos_portal.api.iam_people.create_employee` / `iam.people.create` | 仅合成隔离场景验证；读取目标原生必填元数据，真实资料不全则拒绝；不填缺省生日/入职日，不另建 HR 模型 |
| `hbos_portal.api.iam_departments.list_departments` / `iam.departments.read` | 原生 Department 主键与组织，兼岗不自动叠加主部门预设；普通预设排除管理与高风险 |
| `hbos_portal.api.iam_access.get_capabilities`、`get_effective_access` / `iam.access.read` | 当前 session 解析能力、版本、来源、成对范围；前端只显示，服务端每请求重算/校验 |
| `hbos_portal.api.iam_access.preview_department_default`、`update_department_default` / `iam.departments.manage` | 管理范围内修改普通预设，拒绝自批/跨部门；保存带 expected_version，冲突不成功、不产成功审计 |
| `hbos_portal.api.iam_access.update_personal_exception` / `iam.access.manage` | 具名允许/限定禁止/删除恢复继承，动作与范围成对、资格/期限/审计，禁止通过 Role/DocShare/user_id 原生编辑绕过 |
| `hbos_portal.api.iam_audit.list_events` / `iam.audit.read` | 独立审计读取能力；不能仅有人员或权限管理即读取全部日志；仅最小脱敏字段 |
| 现有 `hbos_portal.auth.accounts.get_security` 扩展 | 只加 `temporary_password_state={pending,temporary,expires_at,generation,can_claim}` 与 `first_password_required`，均无明文。保留原 SecurityStatus 形状，前端 adapter 验证扩展；本人重新证明/首次改密仍复用 `reauthenticate` + `set_password` |
| 新 `hbos_portal.auth.accounts.claim_initial_password` | 仅当前已验证本人会话、POST/CSRF/禁缓存/用途证明。首次领取时随机生成并原生写哈希，状态锁内原子结算，一次响应内存显示；OAuth 只登记 pending，不把口令放重定向/header/日志/cache。重放不返回旧明文，丢失走受控重置 |
| 新 `hbos_portal.api.iam_people.get_my_employee_status` | 当前会话最小关联状态，不接受 user/employee 目标参数；只读，不按姓名或外部客户端值推断归属 |
| `hb_attendance_app.hbos_attendance.portal.personal.get_my_attendance` / 复用 `attendance.read` | 从 frappe.session.user 解析唯一有效 Employee；无 Employee、冲突、失效都拒绝。只接收 date_from/date_to/page/page_size 等明确白名单；employee/department/user/filter 等主体或任意查询参数拒绝，不替换 session |

我的考勤返回最小投影：记录 ID、日期/时间、打卡类型、已形成考勤状态及必要出处；不包含外部身份原值、定位、手机号、额外 HR 字段。列表、总数、分页、搜索和汇总共用同一 Employee 谓词，不用 owner 归属。只读取已有 Checkin/Attendance，不复制算法、不创建考勤记录库。权限撤回/停用在下一请求、后台任务执行与关键提交再判断，旧缓存/任务不得保留访问。

`get_capabilities` 响应冻结为 `{schema_version:1, subject_user:<当前session>, policy_revision:<服务端修订>, capabilities:[<允许且已注册ID>]}`。未知形状/版本/主体不符/网络失败均关闭入口，不缓存跨主体响应。只读当前本人接口不接受选中员工；管理员写接口目标是受控参数，须另核动作、目标部门及版本。

范围：`SELF` 由 session 得到 Employee，`DEPARTMENT` 是明确原生部门键集合、默认 `include_descendants=false`；APP 入口和每个 operation/scopes 必须同时满足。self∩部门需根据记录的 Employee/事件部门证据求交。限定动作 deny 只匹配对象；APP deny 才整 APP 拒绝；空/未知/冲突 fail closed。不把 read 与 export 的部门集合交叉放大。原生必要权限和领域规则仍要满足；不授予普通员工 HR Manager/System Manager 解锁旧仪表盘。

`attendance.export` 是新候选 ID，**未接入/不可正式授予**；本轮 B 首发不实现导出或部门历史业务报表，相关接口明确拒绝并展示未接入。部门模板仍须完成本人/应用权限变更的真实持久化闭环。合成设备模块使用 `iam_demo.read` 候选协议验证扩展，不能冒充真实业务接入；LIMS/仓储/知识/Twin 的演示动作不迁移为正式可用。

### 首发旁路清单与拒绝策略

B 需用合成 A/B 两名员工逐项验证 Employee Checkin、Attendance 的列表/单条、`/api/resource`、Desk/query_report、公开白名单/SQL/get_all、导出/打印/附件及后台生成、计数/搜索/联想。结果中没有 B 的字段和数量才算隔离通过，不能只看 HTTP 状态。query conditions 与 has_permission 保持列表/单条一致；raw SQL/get_all/ignore_permissions 逐入口显式限制。旧全量报表对普通员工与受限部门用户拒绝。#49 的临时拒绝不当作完整部门范围实现，不覆盖其分支；冲突交最小补丁。既有高权限 HR 的历史边界保留并单独回归。

## 5. 模型、保护钩子、迁移与回滚候选

复用：原生 User/Session/密码哈希、Employee.user_id、Employee/Department/Company、既有 HBOS External Identity 与账号安全。没有独立 IAM 服务/数据库，没有改名 Employee/User 主键，没有把密文/哈希再存一份。

| 最小新增 / 修改候选 | 确切字段或责任 |
|---|---|
| `HBOS IAM Policy` + child `HBOS IAM Rule` | parent：subject_type(User/Department)、subject_name、version、enabled；child：app_id、operation_id、effect(allow/deny)、scope_type、scope_ref、include_descendants(false)、valid_from/until、qualification_ref。作用与范围成对保存，一处权限真相；读/写仅受控服务 |
| `HBOS IAM Change Event` | actor、request_id、subject、operation、before/after 的脱敏快照、版本、结果/原因、时间；服务端只追加，权限读独立，日志不存密码/token/原件标识 |
| User 自定义临时状态字段 | `hbos_initial_password_pending`(Check)、`hbos_temporary_password`(Check)、`hbos_temporary_password_expires_at`(Datetime)、`hbos_password_generation`(Int)。仅状态/期限/代次，不存明文；通过既有 Frappe 密码服务写哈希。独立随机值在已验证本人响应安全交付一次，Cache/日志/文件/localStorage 不留可读取旧明文 |
| 既有 External Identity | 不新增第二绑定表；沿用 provider/tenant/app/id_type/external_id、占用保护、tombstone、事务和并发锁。Employee 证明与身份绑定证明分开 |
| 考勤来源映射 | 本次无新表/字段；真实证据不足，按 A1 处理例外候选 |

钩子原则：扩展既有 `hooks.py` 的 on_login、on_session_creation、auth_hooks/before_request、User.before_validate/on_update 与既有 native password reset/update override；不另起平行登录链。覆盖原生密码/API 的临时状态失效/首次改密限制，同时保留 MFA/CSRF/state。OAuth 成功不重置旧密码，停用/tombstone 不复活。关联 Employee 采用完整受控文档验证，不能 set_value 跳过副作用。

密码备用和 OAuth 回调直接进入 workspace 都必须经同一服务端状态门禁。PortalLayout 候选在既有 Shell 内挂 FirstPasswordGate；仅允许最小无业务 bootstrap/profile、本人证明/交付/改密精确方法，业务读取在强制改密状态下拒绝，不能按 `/auth` 前缀宽松放行。候选 `_write_password` 的成功 flags 与 after_request 接缝尚未证明事务时序；B 必须将哈希与状态结算做到同一可回滚事务，拒绝部分成功，必要时只在已冻结的 `_write_password` hunk 内调整原有提交位置并回归全部原证明/会话逻辑，不以 UI 结算当服务端完成。

HRMS 锁定源仅有 CI 候选 `c0a04b80eeb721417b75cea758e831464d0da041`。它的 EmployeeMaster 继承 ERPNext Employee，User/Employee hooks 可能影响审批人 Role、self-service 资源；Frappe/ERPNext 精确 core SHA 和现场版本尚未知。B 在隔离镜像内记录完整 SHA 后实读对应 Employee/User/User Type 核心，再比较关联前后的 user_type、roles、User Permission、默认关联、导出能力；失败只阻塞关联相关实现，不能猜测或关闭全局权限。普通账号不自动拥有 HR Manager/System Manager/Desk 特权。

迁移：只安装上述 DocTypes/临时状态字段/必要索引，幂等双 migrate；存量 User 默认“非临时”、不批量改密、不猜测回填 Employee.user_id、不导入原件、不改历史业务外键。既有权限映射先列只读差异，未批准不得批量覆盖。迁移前后合成快照/回滚验证留证；回滚先撤入口/新能力，恢复隔离快照及代码，新增审计/策略数据保留导出，不对现场删字段、清表或回写数据。

## 6. B 正式文件白名单（候选，不是 A 已修改）

以下路径相对 repo root。每个新目录仅列出的文件可写；不能由 `/**` 扩大到其他域。若目标基线不存在/内容变动，先停该项报告最小差异，不动其他团队工作。

| 领域 | 允许的候选文件与边界 |
|---|---|
| Portal 共享 hunk | `frontend/hbos-portal-web/src/router/index.ts`、`frontend/hbos-portal-web/src/components/layout/PortalSidebar.vue`、`frontend/hbos-portal-web/src/components/layout/PortalLayout.vue`，仅附件 `R4_Portal接入候选.patch` 的导航/会话能力加载/路由 guard hunk，不另改全站壳 |
| Portal IAM 新局部组件 | `frontend/hbos-portal-web/src/views/admin/` 下仅 `AdminWorkspaceView.vue`、`PeopleAdminView.vue`、`DepartmentsAdminView.vue`、`AccessAdminView.vue`、`AuditAdminView.vue`、`AdminAccessUnavailableView.vue`；`frontend/hbos-portal-web/src/services/` 下仅 `iamAccess.ts`、`iamPeople.ts`、`iamDepartments.ts`、`iamAudit.ts`；`frontend/hbos-portal-web/src/types/iam.ts`；本人考勤仅新增 `frontend/hbos-portal-web/src/views/attendance/MyAttendanceView.vue`、`frontend/hbos-portal-web/src/services/attendancePersonal.ts` |
| 现有登录/本人安全 | `frontend/hbos-portal-web/src/views/FeishuLoginView.vue`、`frontend/hbos-portal-web/src/views/ProfileSettingsView.vue` 只移植已认可视觉/一次交付/首次改密与既有恢复绑定衔接；不得新增一套密码/OAuth后端或替换全站布局。仅 `R4_前端账号安全接缝候选.patch` 的逐 hunk；新组件仅 `frontend/hbos-portal-web/src/components/account/{FirstPasswordGate.vue,InitialPasswordDelivery.vue,EmployeeIdentityStatus.vue}`，新适配器仅 `frontend/hbos-portal-web/src/services/iamAccount.ts` |
| Portal 后端新服务 | `apps/hbos_portal/hbos_portal/api/iam_people.py`、`iam_departments.py`、`iam_access.py`、`iam_audit.py`；`apps/hbos_portal/hbos_portal/iam/__init__.py`、`policy.py`、`people.py`、`audit.py`、`temporary_passwords.py`、`demo_provider.py`、`migration.py`、`guards.py`、`onboarding.py` |
| Portal 后端共享 hunk | `apps/hbos_portal/hbos_portal/auth/onboarding.py` 仅开户后受控关联/独立临时状态交付；`auth/accounts.py` 仅复用本人安全/临时状态验证；`hooks.py` 仅既有钩子追加及迁移入口；不改 bootstrap，能力使用独立候选接口。共享改动限 `R4_后端共享接缝候选.patch` 的接缝 |
| IAM DocType 新文件 | `apps/hbos_portal/hbos_portal/hbos_portal/doctype/hbos_iam_policy/{__init__.py,hbos_iam_policy.json,hbos_iam_policy.py}`、`apps/hbos_portal/hbos_portal/hbos_portal/doctype/hbos_iam_rule/{__init__.py,hbos_iam_rule.json,hbos_iam_rule.py}`、`apps/hbos_portal/hbos_portal/hbos_portal/doctype/hbos_iam_change_event/{__init__.py,hbos_iam_change_event.json,hbos_iam_change_event.py}`；按既有 HBOS Portal module 与 External Identity 所在真实层级放置 |
| 考勤本人服务/守卫 | `apps/hb_attendance_app/hb_attendance_app/hbos_attendance/portal/personal.py`、`portal/permissions.py` 新增；`portal/access.py` / `portal/provider.py` 仅 attendance.read 的本人注册/可用性；`apps/hb_attendance_app/hb_attendance_app/hooks.py` 仅 Checkin/Attendance query/has_permission 入口；旧报表/导出未受控时用入口拒绝，不扩大为全量报表重构 |
| 回归/隔离脚本/文档 | 新增 `apps/hbos_portal/tests/test_iam_people.py`、`apps/hbos_portal/tests/test_iam_policy.py`、`apps/hbos_portal/tests/test_iam_temporary_password.py`，`apps/hb_attendance_app/tests/test_iam_personal.py`、`apps/hb_attendance_app/tests/test_iam_bypass.py`；`scripts/ci/iam_r4_isolated_smoke.sh`、`docs/design/iam-v1/` B 验证记录。只读源码清单不等于允许写该清单全部文件 |

所有正式路径已按固定产品树校准；本表花括号只展开指定文件，不授权整个目录。三个设计候选 patch 仅说明共享接缝、未应用；新 imports 尚未实现，不能将上下文检查当作真实构建通过。B 按本单边界实现具体逻辑并供集成线审阅；不能整包 cherry-pick 原型、#42 或 #49。不改 Frappe/ERPNext/HRMS 核心、全站首页、现行同步 api.py/导入脚本、生产 compose/env/挂载、真实数据或其他团队业务。

## 7. B 隔离环境和 source 计划（尚未创建）

| 项目 | 本次唯一候选 |
|---|---|
| 新功能 checkout / branch | 新独立 `/Users/hb/Projects/HBOS-IAM-R4-B`；`feature/iam-v1` 从批准 product SHA 建立，若已有先核对归属、另报告，不覆盖；Draft PR 目标 product，保留设计 PR |
| Compose project / Site | `hbos-iam-r4-b-20261015` / `iam-r4-b.localhost`；从零合成 Site，无现场备份导入 |
| 端口计划 | 前端 5198、后端 8198、socket 9198；实施前核对未占用，均 bind 127.0.0.1。占用时不 kill、不抢占，报告最小替代端口 |
| 新 volumes | `hbos-iam-r4-b-20261015-db`、`-sites`、`-redis-cache`、`-redis-queue`；不引用现有 P1/考勤/产品卷，不复用 Owner sites/logs/env 挂载 |
| 产品 source | `39366822a5b5d6041b9eea94da4f77255ad26761`；禁止混入未合并 PR 或从移动产品 HEAD 偷换 |
| image / HRMS source | `frappe/erpnext:v16.26.2@sha256:d349cceb89693d54525ef9696c29af772c05ad4f42af723742cbee4e62420583`；HRMS `c0a04b80eeb721417b75cea758e831464d0da041`。B 前置记录镜像平台与内部 Frappe/ERPNext 完整 SHA；不换成移动标签掩盖不匹配 |
| 数据 / 外部服务 | 仅合成 User/Employee/Department/考勤记录；不用原件/现场库；真实飞书、得力云、AI 出站及外部定时同步关闭，密钥不写入 repo/PR/日志；缺真实 OAuth 只将该项 NOT_RUN |
| 生命周期 / 回滚 | 只管理新项目自有容器/端口/卷；记录创建前清单和合成快照，验证双 migrate/停用旧 sid/并发/回滚。回滚仅停本项目并恢复其快照，不能 docker down 其他项目或删共享卷 |

A 没有创建这些 Site、volume、容器，没有碰已有运行挂载或连接真实数据库。5197 仍只是交互原型，不是正式接入证明。

## 8. 未知项、验收门槛与唯一授权

真实 Employee/User 关联率、同号/孤立记录数、来源 namespace、姓名兜底历史影响、现场核心版本、Employee.user_id 副作用均 `NOT_RUN`。最小只读统计请求只返回指定公司/来源的总量、空/重复/孤立计数和解析0/1/多候选数，不返回人员值、不触及 __Auth/token/sid；不得用会读取凭据的 site_inventory.inspect 代替。此请求留待单独指定 Site 的许可，不阻塞合成 A 交付。

B/C 应逐条执行 R4 任务书 C 的 13 项并输出 PASS/FAIL/NOT_RUN、脱敏请求响应、持久化刷新/重登、构建/后端回归、双 migrate/最小副作用/旁路/回滚证据。设计测试 PASS 不能变成真实验收 PASS。部门历史报表/导出首发未接入则明确拒绝；真实 OAuth 未许可则只测试服务端合成身份适配。

唯一待 Owner 确认：**是否批准冻结卡列出的 R4 设计候选完整 HEAD，以固定产品 SHA `39366822a5b5d6041b9eea94da4f77255ad26761` 为基础，按本单接口/模型/确切白名单及隔离环境进入 B，并连续完成 C 的合成隔离验收？** 不包含真实库访问/全员导入、外部 OAuth UAT、合并或正式部署。授权前停在 A。
