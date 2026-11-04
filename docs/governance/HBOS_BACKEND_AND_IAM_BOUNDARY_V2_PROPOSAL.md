# HBOS V2 后端选型与统一身份权限边界（决策候选）

> 日期：2026-10-11；状态：**PROPOSED / Owner 确认与业务授权矩阵待定**。
> 本文件是当前团队 PR 集成工作的架构裁决输入，不代表启用新角色、迁移账号、调整真实 Site、发放员工权限或部署新应用。
> 继承：`docs/adr/0001-use-frappe-erpnext-as-platform-base.md`、`docs/experience/EA-1_SURFACE_RESPONSIBILITY.md`、`docs/experience/EA-3_APPLICATION_CONTRACT_ACCESS.md`、`docs/governance/iam/IAM-1_统一授权架构决策.md`。

## 1. 明确技术路线：不是两套互不相干的系统

**一个 HBOS 企业身份与授权治理体系，两类前端入口，两种可复用后端模式，多个领域数据所有者。**

| 层面 | 正式方向 |
|---|---|
| 登录身份 | 飞书登录与密码登录均映射**同一个 Frappe User**；保留既有 External Identity、密码/MFA、账号停用和交接机制，当前不另建账号表、JWT 密码库或 IAM 微服务 |
| 前台 Portal | Vue 3 + Ant Design Vue 企业入口，普通员工查看有权应用、事项、知识与业务操作。Portal 的卡片/导航**不是**权限执行器 |
| 后台 Management Console | 用户友好的管理页面可使用 Vue；原生 Frappe Desk 继续承担高级维护。二者复用上述 User，后台访问需**单独授权**，不因有 Portal 账号就自动获得 Desk 权限 |
| Frappe 业务引擎 | 考勤、仓库、LIMS 与强事务型生产业务沿用自研 Frappe App/DocType/ORM/服务/必要 ERPNext/HRMS 能力，默认同 Site MariaDB；Desk 和 Vue 都走相同领域规则 |
| 独立后端服务 | 知识检索/RAG、AI 工艺分析、实时遥测和高计算业务可采用 FastAPI/独立索引或存储；**不得另建员工账号和业务授权真相** |
| 数据治理 | 每个业务事实一个权威来源；平台整合通过版本化 API / 事件 / Provider，禁止前台或其他 App 绕过领域服务直接修改领域表 |

## 2. 一眼决定新 APP 后端怎么选

1. 主要是 Employee/HRMS/ERPNext/Stock/批次/质量单据/审批、需要同 Site 业务事务和记录权限：**Frappe 自研 APP + MariaDB**。可以仅建设 Vue 前端和 Frappe API，不强制新建 Desk Workspace。
2. 主要是模型推理、RAGFlow、视频处理、3D 模型计算、外部数据采集和高频时序：**独立后端服务**。可使用自己的数据库、索引和文件存储，但须申明资源 Owner 与数据权威，并通过 HBOS 受控 API 进入工作台。
3. 只是增加 Vue 展示、且没有新领域状态：复用既有 APP API，不额外创建 Frappe APP 或数据库。
4. 同一 APP 混合两类需要：Frappe 拥有事务事实和身份授权，独立服务只负责外部采集/计算；数据通过受控接口交互。**禁止为了统一而把 RAG/遥测搬进 MariaDB，也禁止为了独立部署重复开发库存、员工和质量主数据。**

新 APP PR 的必填字段：`app_id`、模式（Frappe/independent/hybrid）、稳定入口、数据 Authority、身份鉴权方式、action/scope 范围、所属数据库/资产、迁移/回滚、Provider 能力和隔离测试证据。

## 3. 前台 / 后台 / 业务角色如何区分

**不要创建两套用户，更不能使用“后台管理员即所有业务管理员”。**

- **主体层**：`Frappe User` 是唯一内部登录主体；`Employee` 关联员工；飞书目录可同步可核验的企业成员身份与组织字段，但**登录成功绝不等于获得全部业务授权**。
- **入口层**：`portal.enter`（企业员工门户）、`management.enter`（管理中心）、`desk.enter`（现有 Frappe Desk 受控访问）分别决定入口可达。现有 User Type / desk_access 的真实联动先在目标 Site 测试，不凭设计表批量切账号类型。
- **管理层**：`identity.manage`、`access.grant`、`portal.configure`、`audit.read` 等平台管理能力与业务角色分离；可委派管理员不得自批提权，不能自动执行 QA 审批或查看无限制 HR 明细。
- **领域层**：`lims.result.review`、`attendance.exception.read`、`inventory.stock.issue`、`production.board.read` 等能力按业务域提供，最终由**领域服务端**计算。
- **数据范围层**：能力与范围绑定为同一个授权单元：例如 `Reviewer@LAB-A` + `Analyst@LAB-B`，绝不能拆成角色集合和范围集合再笛卡儿积组合。公司/部门/仓库/实验室/知识空间/设备等按需定义，空范围不等于 ALL。
- **业务硬约束**：停用、撤权、字段保密、审批状态、签署资格、禁止本人自审、出库必须质量放行等在 Portal、Desk、REST、报表、导出、异步任务的服务端路径持续生效。

落地方式：Frappe Role/Role Profile/DocPerm/User Permission 保留其基础能力；对表达不了的“角色 × 数据范围 × 期限”，沿既有 IAM-1 设计拟实现受控 `HBOS Access Grant` 或等效授权记录。该模型**当前不是已全面运行的权限引擎**，严禁前端用角色名拼权限、严禁旧原生接口绕过新范围校验。单一授权写入口、权限变更审计和分阶段迁移必需。

## 4. 两种后端如何安全统一接入 Portal

```text
员工浏览器（飞书/密码 → Frappe 当前 Session）
       ↓
HBOS Portal（路由、导航、待办、搜索；只显示已授权入口）
       ↓
HBOS BFF / Provider（校验 User、App Access、Capability、Scope）
       ├── Frappe Domain Service → DocType / MariaDB（业务执行时重检）
       └── 受信服务到服务身份 → 独立 FastAPI / RAG/AI/遥测
                                  → 私有业务数据源/索引/模型
```

- 每个业务应用提供稳定 `app_id`，通过 Provider 的 `manifest/access/summary/tasks/search/deep_link` 发现与分发（不支持的能力显式关闭）。**路由是否由 Vue 渲染仅决定视图位置，绝不能决定是否跳过后台授权**。
- 独立 FastAPI 不应仅依靠 CORS、127.0.0.1 或前端传入的 `user`/`roles` 鉴权。受信服务间凭证短期/最小权限，后端传递用户与授权范围；具体签名、重放保护、失效和日志在实现设计中落地；敏感结果在独立服务或 BFF 双方按契约再次验权限。
- 生产 #40：保留现有采集与 AI FastAPI，不强行迁入 Frappe；修补 Vue 共享组件契约，但**只有增加后端用户/车间范围授权后**才能在正式 Portal 注册 `production`。质量合格率缺真实来源时标识为未接入，不显示似真“99.9%”实测数。
- 知识库 #30：继续独立开发，HBOS 后端中转检索与引用，禁止浏览器直连知识服务和代理原件下载/`get_source`；不随本 PR 改动知识资产与部署。
- Twin：模型查看、现场遥测、受限文档分别授权；浏览器能获取模型不代表有权控制设备。

## 5. #37 组织/IAM DocType 归属：最小改动方向

当前 `hbos_portal` 内已经包含飞书身份与账号安全代码，#37 在同一 Frappe App 内新增 `organization/`、`authorization/` 子域及组织/岗位 DocType。这是**平台核心能力**，不属于 Portal 的 UI 编排业务。

为了本轮尽量少改代码，允许将这部分**作为受控的 HBOS 平台 IAM 子域候选**继续保留在现有 `hbos_portal` 物理 App 内；必须清楚隔离 Python 命名空间、对外 API、DocType 拥有者及授权写入口，禁止 Portal bootstrap 直接掌控 LIMS/仓库领域状态。将来是否独立搬成 `hbos_identity_app` 另行 ADR，**现在不要为合并而立即迁移全部账号和表**。

旧 CI “Portal 只允许 4 个账号安全 DocType”是重要历史安全门禁。#37 要进入合并前，必须对**每个新 DocType**核实是否真正属于 IAM 子域、是否可被原生 Desk/REST 修改、迁移是否幂等且可回退，再将门禁改为**显式精确 allowlist + 权限负向测试**。禁止放开所有 `hbos_portal` DocType 或跳过 CI。

#37 还包含 LIMS 领域变更和全 Site 恢复工具；建议按“业务 LIMS、IAM/组织、恢复部署工具”分别评审。业务专用接口的领域授权由 LIMS 实现，Portal 只做适配器。

## 6. 最短集成验收顺序（不把 PR 合并误当成部署）

1. 合并低风险、已批准的开发规范 PR；#39 仓库在独立 Reviewer + 实际库存权限/过账隔离测试通过后 Squash 合入产品分支。
2. #37 在 IAM 子域所有权/DocType 精确白名单裁决后修 CI，拆分高风险恢复工具与 LIMS 领域，核验新 HEAD 后逐批合入。
3. #34 从最新产品 HEAD 新建考勤移植候选；保留已有日期范围删除和外部写入安全守卫，仅移植真实业务/页面增量。
4. #40 补平台授权接入、服务真实权限负向测试与正常质量口径；再作为员工应用合入。#30 本次不动。
5. 每次合并后下一 PR 以**新的远端 base SHA**重新运行全量相关 CI、评审与隔离回归；`main`、部署、数据库迁移与正式员工授权单独审批。

**架构批准 ≠ 真实权限已配置；源码合并 ≠ 数据库 migrate；CI PASS ≠ 现场业务 UAT PASS。**
