# UAT-R1 工程映射与修复窗口

日期：2026-10-17（Asia/Shanghai）。状态：`IAM_V1_OWNER_UAT_CHANGES_REQUIRED`。Owner已确认暂停5198人工写操作，允许进入修复窗口。本轮继续现有实现目录、分支、Site和Draft #52；不改写B0/BC历史验收结果。

## 来源与现场

- 本地/远端实现HEAD：`fa500b73e58fa595ad5425f869743135e8feb15f`，工作区起始干净；原源码冻结`8554b3b3485d5298030c2658cf21d2e51f018976`。
- 产品base仍为`39366822a5b5d6041b9eea94da4f77255ad26761`；设计R5仍为`35a778afa383a8f6d07531b8c048b79e4f6c2ba3`；#52 OPEN/DRAFT/未合并。
- `/Users/hb/Projects/HBOS-IAM-R4-B`、`feature/iam-v1`；自有Compose `hbos-iam-r4-b-20261015`、Site `iam-r4-b.localhost`、回环5198/8198/9198。5197及原目录保留。
- 已核Vite实际返回的组件/客户端、后端实际导入路径和源文件内容；私有基线、挂载、指纹及原生带文件备份记录在`.local/iam-v1/uat-r1/`。不能用URL代替运行源码证明。
- 已读适用AGENTS/CLAUDE、并行集成规范、AI_CONTEXT/PROJECT_STATUS/CURRENT_MILESTONE和本轮两份任务。superpowers/frontend-design当前不可用，按规范等价人工执行；组织工作使用已提供Spreadsheets skill只读核对来源。

## A：会话合同

原`accounts.get_request_security`继续是最小同源入口，Guest只返回匿名状态，不公开get_security、人员或能力。拟补`authenticated`和仅供内存比较、没有认证能力的`session_context`，与受保护get_security/能力响应一致；不返回sid或可用凭证，不写localStorage。get_security仍只允许当前已登录本人，补最小当前姓名/字符串工号/部门供页头使用。

新增单一`portalSessionCoordinator.ts`：首次加载、同主体后台重验、改密阻断、未知身份、已退出分开；同事件single-flight/去抖/新鲜度，同主体后台检查保留路由组件及导航位置。身份无法核实时遮蔽结果并禁写；确认主体/Session context变化清旧业务/能力/CSRF/proof/临时口令，迟到响应被代次拒绝。权限版本变化重查当前数据，不以快照授予业务权限。

frappeClient只在可靠会话事实下分类Guest，不以not-whitelisted文本单独认定；真正部署/注册错误保留服务错误和诊断编号。账号密码/OTP/proof/CSRF/限流/网络各自分类。只允许logout的受控一次CSRF重试，未知撤销结果不宣称已退出；不自动重放普通业务写请求。

## B：权限设置和调岗合同

复用三IAM模型和四User状态。新增有限`preview_app_settings`/`save_app_settings`：`subject_type/name`、`app_id`、`settings={access_state: normal|paused, permission_mode: department|personal, changes:[operation_id, enabled, scopes]}`；提交携带`expected_version/context_revision/request_id`。同一计划计算暂停、来源及普通功能的最终结果，单事务单审计，不串联多次HTTP写请求。受限普通范围、不授重要权限、不覆盖特殊期限。部门模式仅替换该应用可由普通面板处理的个人设置，暂停状态由独立访问状态字段明确决定。

旧save/restore/suspend/reenable端点的既有移除范围保持，兼容行为明确记录。新增组合端点不接受任意Policy JSON；注册/目标范围/可授范围/版本/期限仍由服务端重验。

新增`preview_transfer_employee`只返回原/新部门、失去/新增的普通权限及范围、个人设置保留和重新登录说明；不返回真实考勤内容/数量。`transfer_employee`提交绑定预览context及Employee版本，重验两部门管理范围和proof。缺失/过期预览拒绝，不更改原主键、工号、密码和历史外键。

## C/D：组织和体验

来源逐文件指纹、源行、公司/部门层级与原生对象映射只存私有计划。原件缺失或字段不完整只阻塞该数据项。真实人员档案最多5个明确完整候选、未开户；真实User创建数应为0。原件、真实部门和员工明细不进PR或截图。导入执行经过受控服务/原生文档，不直接SQL改纳管对象。

日常与技术夹具按明确原生ID清单分组，只控制列表体验，不成为授权来源；保留旧压力/MFA/故障夹具。原A的User/Employee/0001及10月14日历史优先保留，原生保存副作用另验。身份表私有、口令不进交付文档。

我的考勤区分每日结果与原始打卡，显示签到/签退/出勤，保留原值在详情；未知状态不猜。无权、未关联、无记录不同提示；同主体切回保留日期/分页，恢复后重新查同日期。

## 精确候选文件与共享职责

```text
frontend/hbos-portal-web/src/services/portalSessionCoordinator.ts
frontend/hbos-portal-web/src/services/frappeClient.ts
frontend/hbos-portal-web/src/services/iamAccount.ts
frontend/hbos-portal-web/src/services/iamAccess.ts
frontend/hbos-portal-web/src/services/iamWork.ts
frontend/hbos-portal-web/src/services/iamPeople.ts
frontend/hbos-portal-web/src/services/iamDepartments.ts
frontend/hbos-portal-web/src/services/accountErrors.ts
frontend/hbos-portal-web/src/composables/usePortalSession.ts
frontend/hbos-portal-web/src/composables/useAccountProof.ts
frontend/hbos-portal-web/src/stores/portal.ts
frontend/hbos-portal-web/src/contracts/portal.ts
frontend/hbos-portal-web/src/types/iam.ts
frontend/hbos-portal-web/src/router/index.ts
frontend/hbos-portal-web/src/components/layout/PortalLayout.vue
frontend/hbos-portal-web/src/components/layout/GlobalHeader.vue
frontend/hbos-portal-web/src/components/layout/PortalSidebar.vue
frontend/hbos-portal-web/src/components/account/FirstPasswordGate.vue
frontend/hbos-portal-web/src/views/FeishuLoginView.vue
frontend/hbos-portal-web/src/components/iam/EmployeeDrawer.vue
frontend/hbos-portal-web/src/components/iam/AppUsageList.vue
frontend/hbos-portal-web/src/components/iam/WorkSettings.vue
frontend/hbos-portal-web/src/components/iam/AttendanceAccessSummary.vue
frontend/hbos-portal-web/src/views/admin/AdminWorkspaceView.vue
frontend/hbos-portal-web/src/views/admin/PeopleAdminView.vue
frontend/hbos-portal-web/src/views/admin/DepartmentsAdminView.vue
frontend/hbos-portal-web/src/views/admin/AccessAdminView.vue
frontend/hbos-portal-web/src/views/admin/AdminAccessUnavailableView.vue
frontend/hbos-portal-web/src/views/attendance/MyAttendanceView.vue
apps/hbos_portal/hbos_portal/auth/accounts.py
apps/hbos_portal/hbos_portal/iam/temporary_passwords.py
apps/hbos_portal/hbos_portal/iam/people.py
apps/hbos_portal/hbos_portal/iam/policy.py
apps/hbos_portal/hbos_portal/iam/work_commands.py
apps/hbos_portal/hbos_portal/iam/organization.py
apps/hbos_portal/hbos_portal/api/iam_people.py
apps/hbos_portal/hbos_portal/api/iam_access.py
apps/hbos_portal/hbos_portal/api/iam_departments.py
apps/hbos_portal/tests/test_account_recovery.py
apps/hbos_portal/tests/test_iam_people.py
apps/hbos_portal/tests/test_iam_policy.py
apps/hbos_portal/tests/test_iam_work_commands.py
apps/hbos_portal/tests/test_iam_organization.py
frontend/hbos-portal-web/tests/portalSessionCoordinator.test.ts
frontend/hbos-portal-web/tests/portalSessionLifecycle.test.ts
frontend/hbos-portal-web/tests/frappeSessionErrors.test.ts
frontend/hbos-portal-web/tests/iamAccount.test.ts
frontend/hbos-portal-web/tests/iamAccess.test.ts
frontend/hbos-portal-web/tests/iamWork.test.ts
frontend/hbos-portal-web/tests/iamPeople.test.ts
frontend/hbos-portal-web/tests/iamManagement.test.ts
frontend/hbos-portal-web/tests/attendancePersonal.test.ts
frontend/hbos-portal-web/tests/sessionRegression.test.ts
frontend/hbos-portal-web/tests/sessionAccessRegression.test.ts
```

既有本人安全/登录测试仅因真实会话接缝追加对应回归，不删断言或关Gate。最终交付记录实际增量，未使用候选不改动。公共单写台账不覆盖其他团队历史；本轮当前状态集中于本映射和新增UAT_R1交付/复验单，历史B0/BC保持原样。

## 门禁与停点

实施补充：组合保存结果的幂等回放需在 `apps/hbos_portal/hbos_portal/iam/audit.py` 的配置快照白名单保留 `settings/access_state/permission_mode/changes`，不加入秘密或业务数据字段。组织分组复用 `iam/organization.py` 的明确原生ID清单，仅作列表筛选；对应人员、部门及应用目标列表接缝不改变授权。

先完成A真实会话/组件回归，再完成B/C/D与R01–R15。真OAuth/真200%按实际逐项记录；截图不代替无重挂/请求合并证据。最终运行源码、build及HEAD核对一致、#52保持Draft，交付后停止自动测试/夹具变化并保留服务。未具核心证据前不标READY_FOR_OWNER。

复验观测补充：CUA只读DOM不提供performance/hasFocus，因此开发运行在布局DOM公开无认证能力的文档实例标记、Vue实例、请求计数和恢复事件计数；生产构建不输出这些属性。不记录URL参数、主体、sid、token或proof，不参与组件key或授权；真实隐藏/恢复窗口后从只读DOM核对，不能用截图冒充生命周期证据。
