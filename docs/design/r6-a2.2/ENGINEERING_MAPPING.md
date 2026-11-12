# R6-A2 工程映射与隔离边界

**设计样板，不是正式实施。** 原 R6-A 的 API、安全和角色映射完整保留于 `engineering/R6A_IMPLEMENTATION_PLAN_REFERENCE.md`；本文件补充新版界面与原能力之间的关系，不替换后端契约。

## 1. 实际接手基线

| 对象 | 本轮只读核对 |
|---|---|
| 统一入口 | `/Users/hb/Projects/HBOS/`，不是 Git 仓库；没有 git init / clone / 新产品分支 |
| 产品远端 | `feature/hbos-portal-product` @ `1a0d44de1399afca513855f3688eb06c1978429e`，ls-remote 与 PR base 一致 |
| product 工作位 | `fix/feishu-controlled-uat-login` @ `e1e3c9912913fbdd56706a0800e813d8d666626e`，clean，始终只读 |
| UAT 工作位 | detached @ 同一 `e1e3c9912913fbdd56706a0800e813d8d666626e`，clean，始终只读 |
| #61 / #62 | OPEN / Draft；head `5266651a5b82c4f2cf26792d1827cbc2194ae050` / `e1e3c9912913fbdd56706a0800e813d8d666626e`，未修改 |
| 18090 前端 | source `5266651a5b82c4f2cf26792d1827cbc2194ae050`；build `a55953cbc312ae85a4f2`；仍为双来源候选 |
| 原 R6-A | `design/r6-hbos-experience-v1/`；文件 hash 与开工快照比较，原成果保留 |
| 本轮写位 | `design/r6-experience-v2/`；设计资产、源码、构建、证据与评审材料 |

依赖版本由当前产品 `package-lock.json` 的实际解析值确定：Vue 3.5.43、Ant Design Vue 4.2.6、icons-vue 7.0.1、Vite 7.3.6、plugin-vue 6.0.9。独立 package.json 与锁文件均在设计目录。没有升级、复用写入产品 node_modules 或修改产品锁文件。

## 2. 新样板组件 → 已有组件 / 方法

以下真实路径均相对产品仓库 `frontend/hbos-portal-web/src/`。本轮界面通过 `src/mock/adapter.mjs` 驱动；**没有调用下表任何真实业务方法**。

| 样板 | 既有页面 / 组件 | 正式实施应复用的能力 |
|---|---|---|
| `App.vue` 外壳、个人头像入口 | PortalLayout / GlobalHeader / PortalSidebar / 现有 Router | capability 过滤、旧深链、账号上下文与会话协调器；不新增通用管理权限 |
| `ProfileView` 身份卡 | ProfileSettingsView / EmployeeIdentityStatus | `get_my_employee_status` + portal.user；明确 User / Employee 区分 |
| 密码、飞书、恢复 | AccountSecurity / OwnAccountVerification / FirstPasswordGate | `get_security`、`reauthenticate`、`set_password`、`get_recovery_channels`；飞书 `start_link` / `unlink_feishu` 及现有试点与管理员例外 |
| `PeopleView` 列表 | PeopleAdminView | `list_people` / `get_person` / `get_employee_metadata`；保留查询 category、view_group、department、account_status 和服务端 total |
| 新增员工 | 原 PeopleAdminView 表单 | `create_employee(fields, expected_version, request_id)`；元数据必填、公司与部门、本人验证 |
| 为已有员工开户 / 关联 | EmployeeDrawer account 分区 | `create_user`；`preview_link` → `link_user`；工号/公司/账号/归属依据，不按姓名自动认领 |
| `EmployeeDrawer` 应用角色 | AppUsageList / WorkSettings / RoleSettings | registered apps / effective access / assignment；`get_assignment` → `preview_assignment` → `save_assignment` |
| 单应用暂停 / 恢复 | WorkSettings / AppAccessAction | `preview_work` → `suspend_app` / `reenable_app`；与停用 User、撤销角色来源分开 |
| `DepartmentsView` | DepartmentsAdminView / department RoleSettings | `get_department_role` → `preview_department_role` → `save_department_role`；默认仅 staff 或不开通 |
| `RolesView` 分组阅读与编辑 | RolesAdminView | `list_roles` / `get_role` / `save_role_draft` / `preview_role_publish` / `publish_role` / `restore_role_release` |
| `AuditView` | AuditAdminView | `iam_audit.list_events` 脱敏分页；样板记录只描述内存中的模拟操作 |
| 更多管理工具 | 既有 access、账号协助、诊断与 Desk | 保留原能力过滤、专项流程与原生 href；本轮不重新实现这些低频高风险功能 |

## 3. 不能被美化改掉的合同

1. 登录账号 User 与员工 Employee 分离。只有明确内置 Administrator 可判断员工档案不适用；人事管理员仍有员工资料。飞书绑定不创建 Employee 关联。
2. 管理域与后端 capability 校验保留。前端不根据角色名称推导管理权限；考勤管理员不获得平台管理能力。
3. 一个员工对考勤使用一个角色来源：FOLLOW_DEPARTMENT / DIRECT / NONE。单独设置替换部门默认，不叠加。
4. `operation_id` 与 `scope_binding` 成对。SELF 不额外选范围；部门必须为明确部门、`include_descendants=0`；COMPANY 恰好一个受支持公司。精确映射见 `engineering/operation-scope-map.json`，共有现有 registry 的 32 个 operation，按角色资格列出配对，不增加新权限。
5. 个人 deny、暂停、期限与有效性始终参与实际结果。恢复部门安排、改角色或改部门默认不顺带解除个人限制；未完整暴露逐条期限时不声称永久有效。
6. 草稿与不可变发布版本分离。保存草稿不影响员工；发布前重新请求真实服务端影响预览，再按当前上下文验证和发布。
7. 密码 proof、已有 MFA、CSRF、`expected_version` / `expected_draft_version` / `expected_release`、`context_revision`、`request_id`、事务、锁、审计、幂等与旧 proof 失效保留。界面的“核对最新内容”不是强制覆盖开关。
8. 401、撤权、退出与身份切换复用 `portalSessionCoordinator`、generation 隔离和已有清理；403 不登出。一次性口令、绑定信息、搜索结果和旧身份草稿不得串给新身份。
9. 调岗、临时密码交付、账号停用、职责交接、恢复、原生角色与旧 `/admin/access` 路径按原映射保留，不因导航整理被删除，也不混入本轮模拟普通动作。

## 4. 真实能力与提案

| 内容 | 本轮表达 | 能力边界 |
|---|---|---|
| 友好的跨分类账号候选搜索 | 只提供准确账号标识与合成候选说明 | **提案 / 需只读接口支持**；未画成已经存在的姓名自动匹配能力 |
| 逐条期限摘要 | 相关人员展示“需进一步核对” | **需 DTO 支持**；没有期限编辑器，没有永久有效承诺 |
| 非内置系统/服务账号识别 | 只明确识别 Administrator | **需核对分类契约**；不把所有管理员当作无 Employee |
| 仓库级授权 | 不提供已实现的仓库范围选择 | 既有原生角色公司包络合同保留；仓库级范围未实现 |
| 全员飞书 | 绑定状态明确为合成样例 | 不修改现有单人试点、OAuth、账号绑定或自动开户策略 |
| 概览数字与影响人数 | 28 位合成员工、实际内存筛选/配对的影响对象 | 不代表真实公司总人数；正式以 query total / publish preview 为准 |
| 密码与本人验证 | 固定占位与模拟核验 | 原型不收集密码；不能将模拟按钮复制为正式认证豁免 |

## 5. 隔离与服务交接

`src/mock/adapter.mjs` 是唯一模拟事务入口，错误发生时不执行 commit；Vue store 只维护内存。页面没有 fetch / Axios / WebSocket / OAuth 或真实业务链接调用。构建 CSP `connect-src 'none'`，只加载本机静态资源，无远程字体、头像或追踪。

50056 已确认原 PID 63929 的脚本、端口和原设计根后，才向该任务所有的旧预览进程发送 SIGTERM。原文件没有移动或覆盖。新服务只绑定 127.0.0.1，提供本轮 dist、评审材料、原 R6-A 的只读入口及本机截图；无代理，POST/PUT/DELETE 均拒绝。UAT 截图仅在本机私有评审中可见，未上传或公开部署。

启动、停止和回退见 README。`scripts/服务控制.py` 必须核对登记 PID 的完整脚本路径，归属改变则拒绝停止。回退模式使用本轮脚本只读服务旧 index，不执行会重写原登记的旧启动脚本。

## 6. 接手与停止点

已读取附件、START_HERE、NEXT_HANDOFF、WORKSPACES、AGENTS、CLAUDE、CONTRIBUTING、AI_CONTEXT、PROJECT_STATUS、CURRENT_MILESTONE、并行集成规则、既有主题/布局/相关页面与原 R6-A 文档、源码和截图。项目约定的 `frontend-design` / `superpowers` 未在本会话可用技能目录中提供，按项目要求等价人工执行；Product Design 用于截图审查，没有改变技术栈或写入边界。

本轮仅更新设计成果与既有本机交接登记。没有修改产品仓库的状态文件、里程碑、路由或源码，因为用户明确限制产品工作位只读；本轮状态在统一入口本任务登记和本目录维护。没有新 PR、标签、merge、push、部署、迁移、容器重启或身份写入。

停止在 **R6A2_DESIGN_REVIEW_READY**。Owner 设计确认之后，另行从届时已核对的产品集成完整 SHA 接手正式实施；#61/#62 的固定版本审查与合并是独立任务。
