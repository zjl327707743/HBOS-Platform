# IAM-1 统一授权架构决策

状态：设计候选。Owner 已批准治理方向和下一阶段；具体角色映射、数据迁移、生产启用未获本文件自动授权。

## ADR-IAM-001：一个身份与授权管理入口，多处服务端执行

Frappe User 是唯一内部账号；沿用既有 External Identity、账号安全与交接实现，不另造 JWT、密码库或第二套用户表。Employee、Company、Department 等沿用现有主数据。组织关系可由飞书同步，但需明确 HR/飞书字段主来源与冲突处理；飞书身份成功不等于业务授权。

Portal、Desk、管理中心是界面，不是三套账号。入口是否开放单独配置；同一账号从不同入口调用同一业务，须受同一记录级约束。普通员工优先 Portal；仍依赖 Desk 的考勤/仓库岗位保留最小必要 Desk 能力，不批量降为 Website User，不批量授予 System Manager。Role.desk_access 与 user_type 的实际联动以目标版本测试为准。

平台集中管理“谁获得什么授权、范围、期限与委派资格”，各 App 继续执行本领域动作、记录归属、流程状态、SoD 和敏感字段规则。Portal 不实现第二套判定器；前端能力用于体验，提交时后端重算。

## ADR-IAM-002：成对的角色—范围授权

拟建 `HBOS Access Grant`，但本轮不创建 DocType。概念字段：subject(User)、app、role/capability-template、scope_type、scope_reference、company、include_descendants、valid_from、valid_until、status、requestor、approver、reason、policy_revision。角色引用已有 Frappe Role 或受控的业务能力模板；不得复制一套任意角色表。与原生角色的投影关系在实现前形成逐项映射。

一条 Grant 是不可拆开的授权单元。例：甲在 A 组为 Reviewer，在 B 组为 Analyst。有效集合是 `(Reviewer,A) OR (Analyst,B)`，不是 `(Reviewer OR Analyst) AND (A OR B)`。一条授权内部多个限制取 AND；多条完整授权取 OR；账号停用、明确撤销、记录状态、本人自审等硬约束取 AND，不能被另一条角色绕过。

作用范围必须有明确类型：SELF、DEPARTMENT、LAB_GROUP、WAREHOUSE、KNOWLEDGE_SPACE、EQUIPMENT、COMPANY、显式 ALL。缺失/不支持/无法解析/过期范围都拒绝；不把空字符串或缺部门解释成 ALL。下级部门是否包含必须显式决定。跨公司、跨仓调拨校验每个相关对象，单侧授权不能默认授权另一侧。

数据归属必须可靠：本人考勤由 User→Employee 映射决定，不用 owner 代替；多任职关系保留有效期；历史记录按业务事件归属和经批准的历史查阅规则处理，不因人员调岗静默改写历史部门。旧数据缺归属进入待治理集合，不向所有人开放。

## ADR-IAM-003：原生权限与范围授权不双写失控

Role/Role Profile/DocPerm 继续提供通用权限；Role Profile 是岗位模板，不是部门范围。User Permission 可表达的简单范围优先复用；无法表达角色—范围配对时，领域服务/权限钩子必须执行 Grant。任何原生角色粗授权都不能成为绕开 Grant 的替代入口。

写授权只有受控服务入口。对原生 Role/User Permission/Custom DocPerm/DocShare 等直接变更规定受限运维通道、审批/审计与差异检查，不能同时存在两份可自由修改的真相。不是一上来禁止所有原生功能：先完成全部入口影响清单，再逐域切换；未覆盖路径保持 gated，不通过放宽全局配置修复兼容问题。

列表、详情、动作、统计、搜索、Link 下拉、Report、导入导出、打印、附件、异步任务均纳入范围检查。permission_query_conditions 管列表，has_permission/控制器/服务方法管记录与动作；原始 SQL、get_all、ignore_permissions 和 db.set_value 等例外由实际路径单独证明。后台任务在执行时重验有效授权，不借 Administrator 自动提升。

## ADR-IAM-004：委派管理不等于业务办理

拟定管理能力：identity.manage、access.grant、portal.configure、audit.read、domain.access.manage。拥有业务 role 不自动获得 grant 权。授予者只能给批准的应用/动作模板及自身被委派的范围内目标授权；子范围和期限不得扩大；不允许自批提权，不直接授予普通部门管理员完整 User/System Manager 编辑能力。

平台授权管理员不自动有质量签署、HR 明细、知识原件权限；应用管理员不自动有平台管理能力；技术运维不自动有业务批准能力。高风险角色、管理交接、跨部门例外由独立审批确认。保留当前已实现的账号换绑/具名管理权交接，不重复造流程，不把个人业务账号换绑成另一个人承继历史签署。

Administrator 保留受控应急入口，不日常办理业务。应急使用需要实名操作者、原因、时限、审批/双人复核及独立审计。应用代码不能承诺防住掌握主机/DB 最高权限的人；有超管实权的技术角色也不构成密码学隔离。

## ADR-IAM-005：身份生命周期、知识和 AI

公司成员必须正向核验；未映射 Employee 的新账号只进入最小基础体验，个人数据接口拒绝并提示待关联。不能删除当前 explicit_management_handover 的合法例外而造成交接用户失权。部门同步不自动授予 QA/QP、全公司HR、平台管理等高风险权限。

调岗撤销旧范围再按批准时间生效新范围；临时授权到期自动失效；停用/撤权后在后续请求与关键提交点重验，失效受影响会话/能力缓存/异步任务凭证。外部通讯录网络错误不能作为离职事实批量停用人员；新的高风险操作在无法确认资格时拒绝，原应急能力独立保留。

知识权限传播至文档、分块、检索、引用、生成式上下文和缓存；后端构造 subject/filters；网关凭证不等于员工拥有全库授权。空间管理员可管理发布与访问，不自动获得 HBOS 下载原件的入口；禁止浏览器直连、代理 get_source 和反复枚举还原全文。已显示的内容无法远程收回，系统不得承诺绝对防拷贝。

数字孪生的模型、现场遥测、告警、关联文档分开授权。AI 代表真实主体调用工具，使用其有效授权；不得使用全权服务账号替用户绕过。生成内容不能作为权限指令或质量批准结论。

## 实现次序

IAM-0 真站只读盘点 → IAM-1 矩阵/字段与迁移映射批准 → IAM-2 单域后端实现及隔离回归 → IAM-3 Portal 管理中心原型评审再实现 → IAM-4 试点/正式启用。

本文件不引入独立 IAM 微服务，不新建 App，不直接升级或修改开源核心。代码归属在 IAM-1 开发设计中明确，避免把各 App 业务规则搬进 Portal。
