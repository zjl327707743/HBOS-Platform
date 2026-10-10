# 权限管理：IAM 对齐与首批字段映射

2026-10-10 最新接续：[原站只读预检](../milestones/M2_人员权限原站只读预检记录.md)已完成，**S02_ORIGINAL_READONLY_PREFLIGHT_COMPLETED / PARTIAL / REVIEWING / 5178_REAL_READONLY**。实际frontend / DB摘要精确匹配，五来源InnoDB与24必需列PASS，COUNT18/0/1/14/31；八管理表全缺，正式预检在tables以STORAGE_PREFLIGHT_SCHEMA_INVALID停止。10诊断SELECT含正式预检2，零transaction_writes、rollback/destroy PASS，未初始化。只读诊断完成不等于结构或启用PASS；管理GET仍NOT_READY。原站备份工具release路径缺失，现已有镜像 / 权限 / 磁盘 / 备份总量仅元数据确认，原样stdin备份操作包已准备但未执行。下一段先确定停写一致性窗口 / 原服务恢复措施，再按同次私有备份与隔离SQL恢复范围执行；不建表 / 人员 / 政策 / pins或启GET。5178既有真实只读；本段未改代码 / 配置 / 服务 / 缓存 / schema，未备份 / 恢复或浏览器复验。前段14原生 / 428离线PASS为历史证据，本段未重跑。S01-B/S02 PARTIAL，C/S03—S06 NOT_STARTED，Grant NOT_RUN，P4-F6-5 REVIEWING；原Q1/Q2、Date、固定P1 / 完整恢复 / Owner及管理门禁保留。 以下为前序交付当时的记录。

2026-10-09 最新接续：[管理边界与受控接口实施规格](../milestones/M2_人员权限管理边界与受控接口实施规格.md)已形成，状态 **S02_MANAGEMENT_API_SPEC_DRAFT / REVIEWING**。明确独立具名管理政策、完整规则及人员 / 组织范围、固定操作与期限、写请求回滚 / 重启和同键重放；24 项新政策 / 接口验收全部 NOT_RUN。本轮仅文档变更，未创建政策表 / 接口 / 真实配置，前序 134 项离线及 19 项数据库场景通过不覆盖本规格。下一段仅实现纯管理政策协议与离线判定，不连接 Site、不开放写 API；S01-B / S02 PARTIAL、C / S03—S06 未开始、真实岗位授权 NOT_RUN。5178 真实只读；具名管理人、Q1 / Q2、Date 资格、固定 P1 / 恢复 / Owner 门禁保留。以下为前序交付与设计历史。

2026-10-09 最新接续：[实时来源与管理边界验收](../milestones/M2_人员权限S01B实时来源与管理边界验收记录.md)的 **3 项并发回归已按 Owner“继续”指令补验 PASS**，此前审批连接中断的执行缺口已补齐。本次未修改源码，前段 134 项离线、10 项真实来源 / 管理边界及 6 项存储回归结果沿用，摘要核对一致；累计 **19 项实际数据库场景 PASS**。合成数据已清理，原生指纹一致、六表归零。状态仍 **S01_B_NATIVE_SOURCE_VALIDATED / PARTIAL / REVIEWING**，S01-B / S02 PARTIAL、C / S03—S06 未开始，真实岗位授权 NOT_RUN。下一步细化真实管理边界配置与受控接口；5178 真实只读，Q1 / Q2、具名管理人、员工资格、固定 P1 / 恢复 / Owner 门禁保留。下方保留前序设计与历史证据。

2026-10-09 最新接续：[S02 隔离数据库验收](../milestones/M2_人员权限S02隔离数据库验收记录.md)已完成，状态 **S02_PREVIEW_STORAGE_VALIDATED / PARTIAL / REVIEWING**。既有空 Preview 完成备份和六类 DocType 定向同步，物理约束 / UTC 精度、6 项实际事务 / ORM 测试、3 项独立连接并发验证及 121 项离线测试 PASS（新保护 4 + 前序回归 117）；合成数据已清理，原生数据指纹保持。5178 未迁移，服务默认关闭，保持真实只读。S01-B / S02 仍 PARTIAL，下一步补可信实时来源与来源变更 / 管理边界验证；C 与 S03—S06 NOT_STARTED。下方保留前序设计和交付证据，未建表 / 未验证描述仅代表当时状态。

2026-10-09 最新接续：[S01-B 来源适配基础](../milestones/M2_人员权限S01B来源适配实施记录.md)已实现并通过 37 项合成测试，A 的 28 项回归通过。来源按精确主键关联，保留 modified 原值、原生 Date 和组织证据；Position 的公司 / 代次通过新证据封装携带。完整性仍为注入声明，结果 runtime_verified=false，未创建对象或真实加载；B 保持 PARTIAL，固定 P1 来源待补独立保留。

2026-10-09 存储接续：[岗位任职存储与版本方案](../milestones/M2_人员权限岗位任职存储与版本方案.md)细化新关系字段与 S01-A 投影映射。source_modified 保留不透明原值，revision / authorization_generation 由受控关系记录产生；PositionProjection 当前缺少公司 / 代次，需额外来源证据，不能假称现有 A 已覆盖。下一段来源适配仅离线实现，B 仍 PARTIAL。

- 日期：2026-10-02
- 状态：SOURCE_MAPPING_DRAFT / 源码及设计对齐完成，P1 运行来源待补，未实施
- 工作分支与源码：m2-r11@27d3558；保留上一轮文档变更，未创建或切换分支。
- 上位规格：[可扩展授权契约与 LIMS 试点规格](权限管理_可扩展授权契约与LIMS试点规格.md)。
- 本轮只交付对齐、字段候选与试点边界，不创建对象、不更改配置、不查询替代 Site、不执行业务测试。

## 1. IAM-0 已核实的交付边界

通过 GitHub 只读连接器核对 [PR #23](https://github.com/zjl327707743/HBOS-Platform/pull/23)：当前为 open / Draft / 未合并，head 为 dc75ffb554d4467f3a5ae3330f2f217b31fed012，base 为 feature/hbos-portal-product@e4b16ee80aaaf21aac2304246a4de1f9fe8995ea。

差异为 11 文件、612 行新增、0 删除：7 份治理 / 里程碑文档，2 个离线工具及合成测试文件，README / PROJECT_STATUS 入口各 4 行。差异没有 apps/、frontend/、DocType、业务 Hook 或部署配置。因此 IAM-0 已有的是治理设计和盘点准备，没有已经可以复用的 Access Grant、角色版本对象或范围判定实现。

远端已有设计延续统一 User、成对角色范围、委派管理、业务守卫、原生与自定义路径覆盖及撤权原则。本机可扩展目录、模板版本和试点规格是在这些设计上补充，不新起一套身份体系，也不将候选对象说成远端已经实现。

PR 描述中的工具合成测试 PASS 11/11 属于远端既有记录。本轮没有导入或执行该工具，没有重跑该测试，没有修改、合并或推送 PR。本机分支未包含该 head 对象，连接器读取不能视为 PR 已合入当前分支。

## 2. 设计对齐结果

| 对齐项 | IAM 基线与当前规格 | 本轮处理 |
| --- | --- | --- |
| 身份与会话 | 都复用 Frappe User / Session 和既有账号模块 | 保持；不创建 Portal User 或密码库 |
| 角色与范围 | 都要求完整 Grant 内取 AND、完整 Grant 间取 OR | 保持；明确动作先匹配，再应用本条范围 |
| 角色定义 | IAM 允许既有 Role 或受控能力模板 | 模板版本是能力组合的受控扩展，须有原生 Role 兼容映射；不复制任意角色体系 |
| 范围类型 | IAM 列出本人、部门、检验组、仓库等候选 | 这些是初始类型示例；新增类型由 App 注册结构、归属解析与过滤适配 |
| 新功能与旧授权 | IAM 未完整定义动态目录及模板升级 | 补充定义修订、模板固定版本、动作退役及旧授权不自动增权 |
| Portal 能力输出 | IAM S01 按冻结快照写为仅 can_enter | 当前 bootstrap 已输出 capabilities 和 scopes；登记为基线差异，不复制过期结论 |
| 固定环境 | IAM 任务书与本机部署主文档都已选 P1 | 修正上一轮“目标待选择”：目标已定，实际配置和运行来源待定位 |
| 测试规范 | IAM-2 有 36 条跨域用例；本机规格有 16 条 LIMS/契约用例 | 后者是细化与补充，不替代前者；均不因文档形成而标 PASS |
| 治理轮次 | IAM-0 准备 → IAM-1 映射批准 → IAM-2 隔离实现 | 目前仅形成 IAM-1 范围的映射草案；实际 P1 盘点与实施门禁仍待办 |

固定证据：[IAM-1 架构](https://github.com/zjl327707743/HBOS-Platform/blob/dc75ffb554d4467f3a5ae3330f2f217b31fed012/docs/governance/iam/IAM-1_统一授权架构决策.md)、[角色动作范围矩阵](https://github.com/zjl327707743/HBOS-Platform/blob/dc75ffb554d4467f3a5ae3330f2f217b31fed012/docs/governance/iam/IAM-1_角色动作范围矩阵.md)、[IAM-2 门禁](https://github.com/zjl327707743/HBOS-Platform/blob/dc75ffb554d4467f3a5ae3330f2f217b31fed012/docs/governance/iam/IAM-2_隔离验收与迁移门禁.md)。远端旧源码、分支或运行状态文字不覆盖本机当前台账。

## 3. 固定 P1 来源核对

拟盘点目标沿用既有固定环境：Site 为 p1-knowledge-twin.localhost，Compose project 为 hbos-p1-knowledge-twin，常用入口为本机 5188 的 /hbos。此选择来源于已有部署主文档及 IAM-0 任务书，本轮不重新选择 frontend 或 preview，也不修改该目标。

| 检查 | 本轮结果 | 证据边界 |
| --- | --- | --- |
| Docker 当前上下文 | desktop-linux | 仅本机当前上下文，不推定其他主机或配置不存在 |
| 当前及停止容器 | 未发现 hbos-p1-knowledge-twin 项目；有 m0-r3a、portal-preview 等既有项目 | 不启动、停止或切换任何项目 |
| 启动器约定默认配置 | 未发现 ~/Library/Application Support/HBOS/local/config.json | 可能使用自定义 --config 或其他已安装位置，需明确路径 |
| 薄启动器位置（2026-10-07 纠正） | 源码安装到配置的 runtime_root/hbos；实际 runtime_root 待定位 | ~/.local/bin/hbos 不是约定默认位置，其缺失不能说明启动器未安装；不重新安装 |
| 仓库配置示例 | project/site 与 P1 一致，但包含占位路径 | 示例不是实际部署配置，不能据此连接数据库 |
| P1 Site / DB / 制品来源对应 | NOT_RUN | 无已核实配置，未建立 P1 数据库连接，未读取 source_commit / build_id |

已向 Owner 请求实际自定义配置路径；路径属于缺失信息，不是重新确认固定环境选择。未收到路径时，只完成源码映射，不凭猜测扫描其他私有目录或连接候选库。frontend 的既有只读快照不转记为 P1 盘点结果。

2026-10-07 已按 Owner 指令进入第一步并复核来源，详见[P1 环境只读盘点记录](权限管理_P1环境只读盘点记录.md)。来源检查已执行，实际配置 / Site 尚未定位，状态为 PARTIAL；实际权限与 schema 盘点仍 NOT_RUN。

依据：[Mac 本地运行与团队同步](../deployment/Mac本地运行与团队同步.md)、[启动器源码](../../scripts/local/manage.py)、[配置示例](../../scripts/local/config.example.json)、[IAM-0 本机任务书](https://github.com/zjl327707743/HBOS-Platform/blob/dc75ffb554d4467f3a5ae3330f2f217b31fed012/docs/governance/iam/IAM-0_本机只读盘点任务书.md)。后续先核对安全摘要和配置 / Compose / Site / DB / 制品对应，不输出配置全文或凭据。

## 4. 已有字段与对象映射

本机自定义对象来自当前仓库 JSON / Python。原生字段来自已运行 frontend 容器的 Frappe / ERPNext JSON，只读取源码文件，没有连接该 Site 数据库。P1 的版本、Custom Field、唯一约束与实际关联仍未验证；下表是 SOURCE_MAPPED，不是 P1_SCHEMA_VERIFIED。

| 需求 | 已有对象或字段 | 复用与限制 |
| --- | --- | --- |
| 唯一人员账号 | User.name、enabled | 授权 subject 引用 User；状态检查复用账号服务 |
| 用户类型及原生角色 | User.user_type → User Type；User.roles → Has Role | user_type 是 Link；原生角色不是完整范围授权 |
| 原生角色配置组合（兼容投影） | User.role_profile_name → Role Profile；role_profiles → User Role Profile | 当前参考版本两种字段均存在；须连同 Has Role 核对，不代表具体部门岗位、任职或带范围的完整授权 |
| 身份与员工关联 | Employee.user_id → User | 复用该关联；源码字段未声明 unique，不能假定天然一对一 |
| 员工状态与组织 | Employee.status、company、department、date_of_joining、relieving_date | 参考状态为 Active / Inactive / Suspended / Left；多关联或任职日期需明确口径 |
| 部门树 | Department.company、parent_department、is_group | 下级范围明确配置；不能把组织树直接当 LIMS 检验组 |
| 飞书外部身份 | HBOS External Identity.user、provider、enabled 等 | 保留现有复合身份键与校验，不复制外部身份表 |
| 账号安全状态 | HBOS Account Security.user、security_version、blocked、custody_mode | 保留认证与票据失效；security_version 不能直接充当授权目录 / 范围版本 |
| 账号交接 | HBOS Account Operation、HBOS Account Change Event | 复用账号变更审计关联；角色移交不等于带范围的任职授权迁移 |
| 检验组 | HBOS Lab Department.name、head_user | scope 目标引用稳定组 ID；head_user 不自动取得授权；源码没有 Company Link |
| 检验任务归属 | HBOS Sample Task.lab_department、sample、assignee | 解析真实检验组及经办人；不接受客户端组号作为权限依据 |
| 检验结果归属 | HBOS Test Result.task、analyst、reviewer、approver | 范围沿 task.lab_department；保留检验人 / 复核人 / 批准人职责分离 |
| 关联样品及稳定性 | HBOS Sample.stability_timepoint | 识别跨记录影响；普通检验试点不能假称涵盖关联稳定性授权 |

当前账号角色交接服务将选定的既有 Role 从原用户移交接任者，并有受控管理交接例外。它没有本轮拟定的角色版本、检验组范围与授予审批语义。受管 Role 的交接未来必须与 Grant 撤销 / 新授予保持一致，不能复用原生 add_roles 作为范围授权旁路；本轮不更改原合法交接流程。

来源：[账号对象目录](../../apps/hbos_portal/hbos_portal/hbos_portal/doctype/)、[账号服务](../../apps/hbos_portal/hbos_portal/auth/accounts.py)、[交接服务](../../apps/hbos_portal/hbos_portal/auth/operations.py)、[检验组](../../apps/hb_lims_app/hb_lims_app/hbos_lims/doctype/hbos_lab_department/hbos_lab_department.json)、[任务](../../apps/hb_lims_app/hb_lims_app/hbos_lims/doctype/hbos_sample_task/hbos_sample_task.json)、[结果](../../apps/hb_lims_app/hb_lims_app/hbos_lims/doctype/hbos_test_result/hbos_test_result.json)。

2026-10-08 接续：[岗位任职与角色关联契约](权限管理_岗位任职与角色关联后端契约.md)细化具体部门岗位、任职来源、跨 App 页面角色版本及 Grant 来源字段。Employee / Department 继续复用；Designation 仅为目标 Site 核实后可采用的岗位类别来源，不等于具体部门岗位。没有创建对象或完成 P1 schema 验证。

## 5. 首批存储字段候选

IAM-0 没有这些对象的运行实现。以下只是存储映射候选，不表示已定案或本轮创建 DocType。App 权限目录可以直接来自代码注册与只读投影，不要求先新增一张可编辑权限真相表。

### 5.1 受控角色模板版本

| 字段候选 | 类型候选 | 服务端约束 |
| --- | --- | --- |
| app_id / template_key | Data / Data | 稳定应用及模板 ID，属于注册命名空间 |
| version | Int | 与 app_id + template_key 形成唯一版本键 |
| title | Data | 中文显示名，改名不改变稳定 ID |
| definition_revision | Data | 绑定经校验的动作及范围定义修订，兼容规则明确 |
| actions | Table | 子行引用稳定 action_id，不能存通配符或任意方法路径 |
| scope_constraints | 经注册结构校验的条件 | 选择 App 支持的类型；不能放宽领域硬约束 |
| status / approved_by / approved_at / basis | Select / Link User / Datetime / Text | 新增或增权形成新版本；批准后内容不可原地改写 |

模板不是复制原生 Role 名单。其作用是将 App 已有动作形成可审计的能力版本，并有受控的 Role / Role Profile 投影。是否与已有原生对象共享主记录或单独存修订，实施前依据目标版本约束确定。

### 5.2 完整人员授权

| 字段候选 | 类型候选 | 服务端约束 |
| --- | --- | --- |
| subject_user | Link User | 必须引用现有 User，账号及身份状态有效 |
| app_id | Data | 与引用模板所属应用一致 |
| role_template_version | Link 受控模板版本 | 引用具体批准版本，不只存角色显示名 |
| scope_terms | Table | 在同一授权内保存全部条件，不能拆成全局用户范围列表 |
| valid_from / valid_until | Datetime / Datetime | 服务器时间；没有截止时需明确批准长期授权 |
| status / revision | Select / Int | 审批、撤销和并发修订受控；有效状态结合时间派生 |
| requestor / approver / reason | Link User / Link User / Text | 必须来自受控审批流程，不信任客户端自填审批人 |
| delegation_ref | 受控委派引用 | 委派功能启用前不可绕过；人员、角色、范围和期限受上限限制 |
| revoked_by / revoked_at / revoke_reason | Link User / Datetime / Text | 留存撤权历史，不硬删除授权冒充未发生 |

授权修订与认证 security_version 语义分开。授权、动作启停、模板停用和范围归属的改变均有可核验修订；具体落点待实现设计，不直接给 User 新增任意业务字段或修改认证票据逻辑。

### 5.3 首批范围子行

| 字段候选 | 首批取值与语义 |
| --- | --- |
| scope_type | 拟为 lims.lab_group，由 LIMS 注册；未来类型另行注册，不新增中央业务枚举 |
| schema_version | 拟为 1；不兼容版本拒绝，不解析为全量 |
| dimension | 首批为 lab_group，属于同一完整 Grant |
| reference_type / reference_id | 引用 HBOS Lab Department 及真实稳定 ID；由注册适配限定对象类型 |
| include_descendants | 首批检验组不启用继承；未来树形范围需显式声明和批准 |

初期不预建通用表达式引擎，不把自由 JSON、任意 DocType 或 SQL 作为范围。多组可通过多条完整授权或同一维度明确对象集合表达，仍逐条检查角色与范围配对。当前检验组没有公司关联，首批不得凭员工 company 推定检验组公司隔离已完成。

## 6. 首批资源与操作边界

首批字段映射限于普通检验任务、普通检验结果，以及从 User / Employee 获取主体资格所需的字段。实验组 A / B、人员代号及角色组合只是隔离测试设计，不在固定 P1 创建这些对象。

| 语义动作候选 | 现有代码映射 | 首批实施建议 |
| --- | --- | --- |
| lims.tasks.read | tasks Provider 与任务投影 | 优先验证，查询前按 lab_department 过滤 |
| lims.results.read | results / ledger 投影、get_result_ledger | 优先验证，沿 result.task 解析组，统计和详情一致 |
| lims.results.submit | submit_result | 读取隔离完成后进入受控写入验证，保留经办人及代填规则 |
| lims.results.review | review_result | 与提交配对验证 A 复核 / B 检验，保留不得自审与状态规则 |
| lims.tasks.assign / execute | assign_task / start_task | 后续单独覆盖目标人员、双侧归属及状态，不先用全权 Manager 兜底 |
| lims.results.approve | approve_result | 后续覆盖第三人批准、OOS 和关联影响，不随复核模板自动授予 |

操作名是权限目录候选，不是本轮新增 API。现有任务 / 结果动作、原生 Role 和批准业务事实保持；不能把某动作不在首批 enforced 误写为原功能已经被删除。已有 get_all、SQL、ignore_permissions 路径须逐条接入，不能靠新增声明自动保护。

首批顺序是“登记及模板版本 → 任务 / 结果读取隔离 → 提交 / 复核及撤权”，每段均有允许与拒绝用例。读取试点不等于写入或全 LIMS 验收通过。带 stability_timepoint 的关联样品、无检验组或无 task 的历史记录、跨组父单完整导出以及配置 / 留样 / QA / QP 等功能不进入首批实际切换；对应检查完善后再扩充目录及试点。

## 7. 验收编号对齐

本机规格中的 A01—A16 为文档内编号。进入实现测试时采用 LIMS-PILOT-Axx 命名空间，避免与 IAM-2 的 A01—A04 管理授权用例混淆。以下映射不声明已执行任何测试：

| 本机编号 | IAM-2 相关编号 | 补充重点 |
| --- | --- | --- |
| A01 / A15 | L02 / X01 / X02 | 各读取面一致、分页与聚合前过滤 |
| A02 / A03 | G01 / L01 | 角色范围不串权、禁止自审 |
| A04 | I02 / G04 | 身份及记录关联缺失不能兜底全量 |
| A05 / A06 | P01 / G04，并补充目录版本案例 | 新动作不自动授予、未知版本及未启用能力拒绝 |
| A07 / A08 | P01 / P02 / L03 / X02 | 直接接口、原生路径、子表及共享 |
| A09 / A13 | I03 / G06 / X03 及并发证据要求 | 缓存、任务、事务和撤权边界 |
| A10 / A16 | A01 / A02 / A03 | 委派越界与原生投影漂移 |
| A11 / A12 | L02 / X01 / X02 | 父单跨范围、归属变化和关联稳定性写入 |
| A14 | G04 及回退门禁，并补充版本案例 | 回退不复活授权、动作 ID 不扩大语义 |

原 IAM-2 的 36 条跨域用例仍全部保留。本机 16 条为试点和扩展细化，不代替考勤、库存、知识、孪生及账号生命周期验收。双方运行态验收均 NOT_RUN。

## 8. 进入实现前的具体缺口

后续[后端详细设计与实施拆分](权限管理_后端详细设计与实施拆分.md)只细化候选存储和接入位置，不将下列缺口写为已解决或实施已放行。

2026-10-07 后续业务设计见[权限矩阵与授权流程草案](权限管理_业务权限矩阵与授权流程草案.md)；角色范围及审批建议未作为 Owner 已批准口径，下面缺口仍保留。

| 编号 | 缺口 | 影响 |
| --- | --- | --- |
| E01 | P1 实际自定义启动配置 / 来源未定位 | 无法核对 Site、DB、制品、Custom Field 和实际人员映射；不连接替代库 |
| E02 | 实际旧权限与候选 Grant 映射未批准 | 不可批量转换或启用 enforced |
| E03 | 首批人员资格、检验组和审批责任人未完成业务确认 | 不创建真实授权；源码字段映射不能替代批准 |
| E04 | 原生详情 / 分享 / 交接投影及关联写入影响尚未运行验证 | 不能宣称原生路径与全部 LIMS 隔离通过 |

当前可以交付的结果是 IAM 设计对齐、已存在字段复用表和新字段候选。后续取得 P1 配置后先完成只读来源与 schema 核对；编码、隔离环境建立及启用仍服从 Owner 的后续明确授权，不把本轮“进入下一步”解释为撤销“先不动代码”。
