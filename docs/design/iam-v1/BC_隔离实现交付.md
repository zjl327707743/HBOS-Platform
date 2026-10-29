# BC 隔离实现交付

本轮已将已有员工开户、部门与个人工作安排、单人单应用停用及本人考勤接入真实隔离 Frappe Site。管理页的设置持久化、版本冲突、撤权与审计由服务端执行。状态为 `IAM_V1_BC_ISOLATED_REVIEW_READY`：供隔离审查和 Owner 体验，未合并、未部署生产。真实企业 OAuth、真实浏览器 200% 缩放与远端 CI 的结论分别列在下文，不能解释为 ALL PASS。

## 固定来源与实现位置

| 项目 | 交付值 |
| --- | --- |
| 实现目录 / 分支 | `/Users/hb/Projects/HBOS-IAM-R4-B` / `feature/iam-v1` |
| origin | `https://github.com/zjl327707743/HBOS-Platform.git` |
| 产品 base | `39366822a5b5d6041b9eea94da4f77255ad26761` |
| 产品目标 | `feature/hbos-portal-product`，不修改其引用 |
| R5 界面基线 | `35a778afa383a8f6d07531b8c048b79e4f6c2ba3` |
| 实现源码冻结 HEAD | 8554b3b3485d5298030c2658cf21d2e51f018976 |
| 新实现 Draft PR | [#52](https://github.com/zjl327707743/HBOS-Platform/pull/52)，base 为产品分支 |
| 原型保留 | `/Users/hb/Projects/HBOS-IAM-V1`，5197，原 HEAD 与工作区未改 |
| 详细工程映射 | `B0_实施冻结.md`，含模型字段、索引、命令与必要共享 hunk |
| 精确增量 | `BC_修改文件.json`；最终交付记录 commit 由 PR head 与本机交付版本记录给出 |

R3 `e7486a9cb3ded7a32a9ead17990e158562605d44`、R4 `d1573ddbe05a0bd09120918e7dd4b00a5aa639b5`、R5 固定提交与历史交付未改写。最终 fetch 产品与设计来源仍为上述固定值。#42 OPEN/DRAFT、#49 OPEN、#50/#51 OPEN/DRAFT，均未合并；没有吸收这些 PR 或接管合并线。

实现按身份与账号、策略及原生守卫、受控工作命令、考勤执行、Portal 和验收分提交。没有整包应用 R4 patch，没有复制原型 model.js、演示身份、localStorage 或合成密码实现。

## 打开与实际操作

- [正式隔离 Portal](http://iam-r4-b.localhost:5198/hbos/admin/people)，[登录](http://iam-r4-b.localhost:5198/hbos/login)。Site 为 `iam-r4-b.localhost`；后端回环 8198，socket 回环 9198。
- [保留的 5197 原型](http://127.0.0.1:5197)。正式 Site 与原型独立。
- 管理身份为合成 `iam_manager1`，仅 D1 的人员、部门和普通工作管理，没有他人考勤读取权；`iam_a` 为合成 A 本人员工。另有仅应用管理者、独立审计员、未纳管旧 HR、待关联/停用/冲突夹具。
- 私有凭据由本机 Owner 在实现目录 `.local/iam-v1/fixture-credentials.json` 领取，账号 ID 见同目录 `fixture.json`。管理员恢复凭据在 `credentials.json`。目录0700、凭据0600且被本 clone `.git/info/exclude` 排除。口令、sid、proof、token、原生哈希和备份不进报告或 PR。
- 给已有员工开户：员工管理搜索 `OWNER-TRY-001` → `开户 / 关联` → 账号管理 → `为已有员工开户`。该员工保留未开户状态供体验；输入明确归属记录并验证负责人。缺原生必填资料时要求补齐；不会复制已有 Employee。
- 本人考勤范围：员工抽屉 → 应用安排 → 考勤管理 → `查看与修改`，显示“本人、部门安排”等来源；配置不返回目标员工的时间、结果、数量或样例。A 用自己的密码登录 → 首页考勤应用 → `/hbos/attendance/me` 才读取真实合成记录。
- 修改/停用：同一员工抽屉可从员工管理或应用权限打开；`修改工作与对象` → 预览 → `确认保存一次`；`其他安排` 可停用、重新启用或恢复部门安排。失败保留草稿，成功仅一次短提示。
- 部门安排：部门管理 → 默认应用安排 → 考勤管理；预览由服务端列受影响人员及个人安排保留结果。调岗在员工账号管理中单独核验，历史考勤仍按原 Employee 外键保留。
- “只查询 A 仓”已作为隔离合成成对范围验收，**库存未正式接入此管理功能**，当前正式页面不会给出虚假授权成功。库存、LIMS、知识、孪生保持原有合法业务授权，本轮不能在新 IAM 中调整。

已在正式 Portal 实际点击登录、员工、部门、应用权限、已有员工开户表单、部门影响预览及 A 本人考勤。已实际保存单应用停用，核对一次成功提示后恢复；实际制造第二管理员版本变化，旧页面收到409并保持未选草稿。截图在本机聊天交付目录 `outputs/BC/`，仅含合成数据。

## 模型、迁移与执行边界

仅新增 `HBOS IAM Policy`、child `HBOS IAM Rule`、`HBOS IAM Change Event` 和 User 四个临时密码状态字段。复用 User/Session、Employee、Company/Department 和 External Identity。Policy 主体唯一、Event request_id 唯一；Rule 查询索引，以及 Employee.user_id/department 两个非唯一查询索引。不清理原数据、不增加现场唯一约束、不批量修改旧账号/角色，不重写历史外键。

控制器无普通角色直接写权；正式命令按管理能力、具名目标范围及可授业务范围分别验证。普通工作按动作与对象成对求值；未改不写，有限禁止不扩大为全对象禁止。停用只加本人的本应用入口 deny，重新启用按当前部门/期限/资格重算，不恢复过期快照。资格执行器尚未接入，非空资格引用拒绝，不宣称已核验相应业务资格。重要管理能力不随部门普通安排继承。

原生 Employee.save 完整执行后，针对本轮关联的 Website User 保持网站类型；原生 Employee 角色/User Permission 等副作用实际核验，不给 HR Manager/System Manager，不改核心或原生角色定义。已纳管用户/员工的原生删除、改名、关联和范围修改由精确守卫拒绝，包含 User.on_trash 内部会话 commit 之前的请求预检。

真实首个业务只有 `hb_attendance_app.hbos_attendance.portal.personal.get_my_attendance`：从当前 Session 唯一有效 Employee 取数据；白名单日期和有界分页；拒绝 user/employee/department/filters 注入。列表、总数和汇总使用相同 Employee 查询条件。受限管理者的业务读取另行拒绝；未纳管旧 HR 保留原边界，残留 HR 粗角色不作为已纳管撤权后的后备许可。

初始密码只用原生哈希，状态同事务结算；可信企业会话一次交付，响应内存显示，重放不返旧明文；领取旋转 Session 后重新取 CSRF。首次密码使用要求改密，保留既有 proof/MFA/限流/恢复链。原生关联可能撤销原会话，验收保留此副作用；停用/重置/改密撤销目标会话和旧票据。真实飞书交换未运行，受控服务适配只在私有测试进程，无公开身份注入端点。

隔离 Compose project 为 `hbos-iam-r4-b-20261015`，从零 Site，四个独有数据卷；DB/Redis不对宿主发布。全部发布端口只127.0.0.1。Docker地址池耗尽后仅创建两条经重叠核对的本项目网络；未删除旧网络。外部同步/飞书/邮件等开关关闭，scheduler暂停，常规worker未启动。仅针对本项目专用合成队列运行一次性 burst worker。此配置不声称物理断网。

固定镜像、Frappe/ERPNext/HRMS完整SHA及内容匹配证据见B0。双 migrate 前后表/角色/字段快照一致；原生 backup带文件 → 自有Site探针变更 → 停自有backend → 原生restore同DB/files → 恢复服务，探针消失且快照相同。C15时为22 User/10 Employee/12 Policy/41 Rule/49 Event；之后增加了 Owner待开户、长名/分页/停用专用合成夹具及受控审计，**这不是最终当前总数**。

## C01–C16 验收结论

逐项命令、执行主体、预期/实际HTTP、数据库最小前后、证据层级及私有证据SHA256详见 `BC_C01-C16_验收证据.json`。私有原始日志、凭据和数据库备份没有复制到公开证据。

| 编号 | 当前结论 | 证据重点 |
| --- | --- | --- |
| C01 | PASS | 固定产品来源、精确文件/共享hunk、41个既有容器元数据未变/旧卷未丢；5197与5198均200；原型clean |
| C02 | PASS | 实际原Employee开户/关联、前导零、占用/同号/并发拒绝；真实原生副作用 |
| C03 | PARTIAL | 密码/可信企业服务适配同User，新/旧/未关联/停用分支通过；真人企业OAuth NOT_RUN |
| C04 | PASS | 一次交付、可信会话资格、旋转CSRF、首次改密/原生密码、MFA、过期/重置/重放及事务失败；恢复RR当前锁读 |
| C05 | PASS | A真实本人3条；主体注入及64项原生/报表/导出/文件/RQ旁路；受信任SQL边界单列 |
| C06 | PASS | 仅管理权可配置、不能读考勤；独立应用委派不强绑people.read；配置无目标业务数据 |
| C07 | PASS | 动作/对象成对、有限禁止/新对象；真实空/未知范围400、未知操作403；合成仓不冒充业务接入 |
| C08 | PASS | 无改保存version/rules/event不变；取消与恢复、显式个人范围及其他工作保留 |
| C09 | PASS | 单人单应用stop gate；停用期间来源到期，旧预览409，新启用仍不授过期权限 |
| C10 | PASS | 管理能力/具名范围/自批/CSRF拒绝；审计员D1两页52条同范围总数，D2/普通A403 |
| C11 | PASS | 部门真实写库、个人例外非零保留、调岗/旧会话及历史外键；故障事务回滚 |
| C12 | PASS | 原有会话撤权/调岗/重置下一请求拒绝，真实disable命令后同旧sid403、Sessions1→0，旧RQ重验 |
| C13 | PASS | 三轮实际并发[200,409]，仅一次版本/审计增长；幂等、SQL故障回滚、真实浏览器冲突草稿 |
| C14 | PASS | 合成新模块由注册表识别，无权后端拒绝；两隔离演示开关交付恢复0 |
| C15 | PASS | 双migrate、原生副作用、原生备份/恢复和旧功能回归；不等同生产灾备 |
| C16 | PARTIAL | 正式三页/登录/本人实际点击、空态/分页/长名/键盘、多宽度、构建与回归；真实200% NOT_RUN；CI单列 |

本地最终前端19文件157项、typecheck/build通过；Portal后端 154 项、Attendance后端498项通过。它们是回归证据，不能替代上表中的真实HTTP、MariaDB、并发、RQ与恢复证据。可复验只读入口：在实现目录执行 `scripts/ci/iam_r4_isolated_smoke.sh`，只读本机私有凭据，先核验 clone路径和容器标签；最近10项通过。避免多个测试同时登录同一合成账号，干扰原生会话配额。

## CI、修复历史与剩余边界

远端CI以实现源码 `8554b3b3485d5298030c2658cf21d2e51f018976` 的实际记录为准：

| Check | 实际状态 |
| --- | --- |
| [Portal 后端骨架](https://github.com/zjl327707743/HBOS-Platform/actions/runs/38765149971/job/116526315283) | SUCCESS |
| [Portal 前端构建](https://github.com/zjl327707743/HBOS-Platform/actions/runs/38765149529/job/116526312849) | SUCCESS |
| [lims-frontend](https://github.com/zjl327707743/HBOS-Platform/actions/runs/38765149500/job/116526312204) | SUCCESS |
| [production-bundle](https://github.com/zjl327707743/HBOS-Platform/actions/runs/38765149553/job/116526313827) | SUCCESS |
| [platform-clean-site](https://github.com/zjl327707743/HBOS-Platform/actions/runs/38765149500/job/116526312670) | SUCCESS |
| [contracts](https://github.com/zjl327707743/HBOS-Platform/actions/runs/38765149553/job/116526313018) | SUCCESS |

最终文档提交不改实现代码；其HEAD和CI当前快照另随本机`BC_最终版本.json`交付。未完成/失败的Check不视为通过。

第一次远端clean-site在账号交接集成时拒绝新增auth_hooks。已保留原`accounts.check_request`唯一认证Hook，在其原账号/撤权/临时状态检查后固定调用两个只拒绝的IAM守卫；业务App按已安装状态解析唯一常量路径，加载失败拒绝。没有修改`operations.py`、放宽认证清单或CI。原before_request及后台守卫保留；已以真实原生API token复验5项通过：四入口守卫403、目标会话/主键保持且原sid仍200；临时合成token已清除。远端clean-site交接回归结果见上表。

首次并发曾出现[500,200]，现将明确数据库锁/1020冲突回滚并映射409，补索引后连续三轮[200,409]；不把历史失败改成通过。首次恢复测试的测试驱动初始化/预期姓名错误留在私有历史，修正驱动后完整原生备份恢复重跑通过。合成域初次夹具含未来对象gate污染基线，改为独立合成基线再按真实命令复验通过。

首次领密收紧会话资格后发现hook以尚未建立的资格作前提，已改为从未交付状态及可信OAuth标记建立资格，再通过真实标准Session/HTTP领取、旋转CSRF、原生密码proof复验。恢复密码经锁内当前key/epoch/期限复核，已在两个真实OS进程的MariaDB RR旧快照场景中验证不能覆盖后来的重置。

一次并行只读冒烟出现A登录200后CSRF401，已保留失败历史，随后复验10项通过。当时另一测试也在登录同一A；实查A原生同时会话配额为2。可能受并行会话清理影响，但未追溯确证该次撤销原因，不把推测当作根因结论。

真实200%：IAB快捷键未改变viewport/DPR，未使用CSS zoom冒充。1280/1440/1920/900视口验证与16px正文属响应式证据；200%请Owner使用真实浏览器人工补验。真实企业OAuth：未用真实租户凭据/控制台/真人回调，NOT_RUN；普通密码登录可用，飞书按钮如实不可用。

仍需集成线审查混合User/Employee锁顺序与生产并发性能、旧HR纳管清单、历史物理public文件及真实来源映射。任意受信任服务器Python/SQL不是IAM权限沙箱；既有公开物理文件不能靠应用hook追溯保护。未实现部门历史报表/导出、真实员工导入、其他App全面IAM接入或生产上线。

交付后停在本实现Draft PR和独立Site，保留5197、#50/#51以及其他所有运行环境。Owner人工体验、真人OAuth、200%补验和集成合并由原项目合并线安排，本轮不自行合并或部署。
