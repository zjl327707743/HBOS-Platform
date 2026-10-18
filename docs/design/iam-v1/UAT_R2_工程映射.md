# UAT-R2 工程映射与隔离开工记录

2026-10-18。Owner 已授权自身隔离站修复窗口、合成账号回归及三处独立设计。A 修复连续执行；B 的角色持久化、分配、迁移、部门/公司考勤和 LIMS 新授权停在设计确认。

- 目录 `/Users/hb/Projects/HBOS-IAM-R4-B`，分支 `feature/iam-v1`；开工本地/远端 HEAD 均为 `a6e175d653c46ef96973536a3f55296d8a809b06`，工作区干净。
- #52 OPEN/DRAFT，base `feature/hbos-portal-product@39366822a5b5d6041b9eea94da4f77255ad26761`；mergeable=CONFLICTING 仅记录，不调整 base、不处理他域冲突。
- R1 源码冻结 `134d76fbd6b34aef34e91b4636717db891a08d33`；历史报告保留。Owner 10 月 18 日 A1 与权限易用性未通过；A2 功能通过但提示重复。旧自动 PASS 不代表本次体验通过。
- Site `iam-r4-b.localhost`，compose `hbos-iam-r4-b-20261015`；回环 5198 Vite DEV、8198 backend、9198 socket。仅本项目服务/合成夹具进入修复窗口。5197 原型、#50/#51、其他 Site/卷保持保留。

已读 R2 任务书、AGENTS/CLAUDE、AI_CONTEXT、PROJECT_STATUS、CURRENT_MILESTONE、并行集成规范、技能路由、B0/B-C 与 UAT-R1 记录。当前任务授权优先于旧轮次禁止业务开发/要求换分支的默认条款。缺少 superpowers/frontend-design，按项目规则等价执行。设计参考现有代码/界面和 Product Design 指引。

## A：允许文件和最小接缝

现有文件：MyAttendanceView.vue、attendancePersonal.ts、types/iam.ts；portalSessionCoordinator.ts、iamAccess.ts；PortalLayout.vue（诊断接缝）；FeishuLoginView.vue（消费一次退出提示）；WorkSettings.vue、AttendanceAccessSummary.vue、DepartmentsAdminView.vue、iamWork.ts；policy.py、api/iam_access.py；Attendance portal/personal.py。相应 tests 增量，不整包替换源码。

新增 helper 确切名称：`frontend/hbos-portal-web/src/services/attendancePageState.ts`（仅日期/页码/位置的有界状态，Site/User/安全代次隔离，重新鉴权后才恢复）；`frontend/hbos-portal-web/src/services/attendanceObservation.ts`（仅 DEV 的日期/请求/生命周期计数，无业务行或认证材料）。如需要更多接缝，先在此追加映射。

选择受控最小 UI 状态缓存，保留普通 RouterView；不引入全站 KeepAlive。业务行仅留当前组件内存，路由返回重新按已应用条件读取。安全边界继续销毁旧数据/草稿；同主体安全旋转只允许在确认后迁移非敏感考勤条件。

后端只增加兼容日期/时区回显与按主体/App 收敛的版本摘要、已授权配置来源摘要；不改 Policy/Rule/Event 或四 User 状态 schema，不增加角色真相，不新增部门业务接口。

## A0 已确认现象

原生 Safari、固定开工源码：初次进入控件显示 2026/10/18，原生日期子项值均为 0；结果三条均属 10/14。源码 from/to 为空、省略参数；后端默认近 30 天。已确认空控件显示与查询默认范围表达不一致，不据此宣称 SQL 过滤失效。

同一文档 `e9264ce8-99d6-489b-8126-c1823e6cf7dc`，考勤→应用中心→考勤，Vue 实例 89→231，bootstrap 1→1，安全/能力读取 1→2。确认为路由重挂路径。它不是 Safari 系统应用切回的唯一根因证明。其余时序在本轮回归分别记录。

私有基线、备份、原生浏览器观测与源码摘要位于 `.local/iam-v1/uat-r2/`（0700，文件0600），不得提交口令、组织原件、真实部门名或认证材料。

## B：独立设计停点

仅在 `docs/design/iam-v1/role-scope-v1/` 增加自包含可点击设计与映射。正式 router/build 不引用；仅合成数据；保存只改演示内存，不发真实 API。三处局部页面承接现有 Vue3/Ant Design Vue 规范。新 Role/Profile/Policy 角色引用及迁移均 NOT_AUTHORIZED / NOT_RUN。

## 台账边界

本轮以新增 UAT-R2 主记录承载状态。交付时给共享 PROJECT_STATUS/CURRENT_MILESTONE/公共入口提供最小追加 hunk，由产品合并线接收；不以 IAM 修复覆盖其他业务里程碑。历史 UAT-R1 不改写。

## 补充：真实并行读取冲突

2b9678c 运行源码上，两独立 HTTP 主体各12次并行读取（本人考勤 / 本部门默认配置），员工12次200，管理员12次409；停止并行后同配置连续3次200。原生服务函数单独执行也通过。这证明并行路径事务冲突，不据此认定 Owner 原 Safari 问题的唯一根因。

追加最小文件 `apps/hbos_portal/hbos_portal/api/iam_people.py`：其四个固定 GET people 函数调用同一 `policy.current_read`；写入方法完全不重试。api/iam_access 的 load 查询与 personal 的纯读取使用最多3次事务重试，只捕获原生 QueryDeadlockError/QueryTimeoutError，回滚后重新执行原有身份/范围检查，25ms/125ms有界退避。最终仍冲突返回409，个人页显示中文重试原因；不重放任何保存、调岗、开户、proof或口令命令。

## 补充：部门列表同一只读接缝

4d4ed62 上补测员工本人读取与管理员 `iam_departments.list_departments` 并行，各12次；员工12次200，部门列表12次409。该列表仍调用未启用重试的 `_call(load)`。追加确切文件 `apps/hbos_portal/hbos_portal/api/iam_departments.py`，只将这一纯读取闭包接入同一 `read_only=True`；成员/数量仍在重试内重新鉴权，不重用上次行。测试补充“回滚后部门委托已撤销则403、不可返回旧成员”及有界失败；不改变任何写入命令。
