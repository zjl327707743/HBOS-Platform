# AI Context

## HBOS Knowledge N1 夜间候选 — 2026-10-10

状态：N1_PARTIAL_WITH_INDEPENDENT_WORK_COMPLETED / ACCOUNTING_PENDING / LOCAL_CANDIDATE_ONLY。原生 rerank 协议适配进入固定 RAGFlow 的实际模型注册入口；严格校验本请求的索引、分数、usage 和 request_id，其他模型保持原实现。生产参考装配缺原预算绑定时拒绝调用。旧 UNKNOWN 没有结清依据，普通模型调用、旧失败项解析和新资料在线发布继续关闭，不能以离线适配或此前单次成功宣称业务恢复。

本轮完成知识目录的服务端分页及筛选、本人反馈与处理状态、统一搜索/问答输入、一般反馈、历史/收藏上下文重放及多部门明确选择。修复同版本撤权后的旧活动标题泄漏、跨请求身份清理和数据库并发收藏幂等。新资料仅本地准入、身份去重、隔离及冻结计划；真实原文、问题、账号、运行配置和费用证据不进入公共 Git 或开发包。

领域106、本地准入18、独立服务162、前端141项合同已运行通过；层级有重叠，不相加，合成测试不代替真实来源/答案质量。最终原生数据库、HTTP、浏览器、远端 CI 和安装制品证据分别在联合交付中核对。PR #30 继续 Draft；只有全部业务、审查、CI、制品和部署边界门槛同时通过才可合入产品分支。此次不切 P1 或开放员工，其他 PR 和 main 不变。

本轮主记录：[M1-KB-N1 夜间连续候选](milestones/M1_KB_N1_夜间连续候选.md)。以下 R2.1 / R2 / R1 条目保留为历史事实。

## HBOS Knowledge R2.1 单次诊断 — 2026-10-10

PARTIAL / ACCOUNTING_PENDING / NOT_RELEASED。服务0.3.10增加维护入口专用的一次短合成rerank许可，绑定Owner指令、原预算/账本/配置、旧事件、原模型/空间/Key指纹、精确payload和有效期；同一锁中先消耗后发送，重放、并发、重启、SDK重试或重定向均不能形成第二次调用。许可/结果追加到原账本哈希链，旧calls与停止状态不改，新估算纳入原信封；成功不解锁普通调用或批次。嵌套/扁平结构计量包含查询在每篇文档中的重复贡献，并校验类型和长度。

本轮仅一次合成实测，结果 RERANK_SINGLE_PROBE_PASS；具体请求ID、用量、费用、操作与账本摘要仅在Owner层。核对现有客户端协议后，本次按该模型官方原生路径和嵌套结构精确诊断，provider/北京业务空间/Key/模型保持；普通检索配置未自动切换，旧403原因仍未知。单次成功不证明HBOS检索恢复、首组或整批质量通过。原12、原220、新成功4份、用户数据保持；224成功/78失败/0在途/新发布0，worker停止，无重解析、embedding/Flash调用、合并或P1切换。

必要新增8项一次性/两进程/重放/停止与计量反例通过，完整服务120项、原领域76与核心207项分别通过；既有前端和业务证据保留。后续需旧事件有依据对账，或Owner独立批准可核实上界的保守处置；再接入已验证原生协议，只重验失败的原固定检索及来源，补首组回归，之后按原累计预算有界推进。当前仍无新资料在线质量或精确子集发布的PASS。当前源码、安装wheel、联合锁和CI独立核对；不以它们代替业务验收。

## HBOS Knowledge R2.1 既有恢复记录 — 2026-10-09

状态：PARTIAL / STOPPED_UNVERIFIABLE_RERANK_USAGE / NOT_RELEASED。继续 Draft PR #30 与同一候选。Owner 已确认原模型额度恢复、允许按量付费并批准本轮累计预算；准确审批与费用记录仅在 Owner 层。优先原 embedding，Flash 仅备用，未探测或切换；原索引、provider、Key 与维度保持。

原 12 份曾完成实际召回、来源和一个代表问答，历史与收藏重新检索、跨用户打开拒绝通过。随后首组解析后的原资料回归遇到 rerank HTTP403，响应无可核实用量；计量器停止新增调用，worker 已安全停止，剩余组未入队。不能把较早的恢复成功写成当前持续可用，也不能把403统一断言为欠费：当前错误码、实际账单、账户余额均 UNKNOWN，准确请求ID在 Owner 收据中。

本次恢复起点220成功、82失败；原冻结批次首组4份已解析成功，物理ID、三字段metadata与原件hash均核对，但原资料在线回归阻塞，首组整体验收未通过。当前302上传=224成功+78失败+0在途，重复1另列，新发布0。224份离线文本/身份检查通过，逐份新资料在线召回和多部门答案质量仍 QUALITY_VERIFICATION_PENDING。敏感草稿继续排除，不阻塞其余批准资料。

只读索引全行hash对比确认原12份的159行、原220成功项的2994行、新成功4份的25行（含向量）完整保留；实际唯一索引行与后端chunk计数分开记录。原49条活动、7个用户指纹、文档/版本/绑定/空间逐字段保留。历史窗口只显示最近30项，不据窗口缺项断言删除。普通真实原批次重放仍12 NOOP、0写入。

服务0.3.9离线修复诊断覆盖：兼容嵌套/顶层code和type、Body/Header请求ID及冲突、Retry-After，非JSON403仍保存HTTP状态；token别名冲突或非整数值拒绝；非200合法usage只作观察，不能认定成功或实际账单。白名单、格式与长度限制隔离错误正文和凭据。旧停止守卫保留，SDK重试继续阻断；本次诊断修复不新增模型调用，也不能据合成输入推断实际403原因。原冻结清单、模型、维度与解析配置保持。

旧事件不改写；诊断补充、用量/金额对账、明确未执行不计费确认均绑定原请求、输入摘要、原行摘要与实际Owner证据，并在锁内追加哈希链事件。重复或并发相同对账只计一次；金额核实时token仍可UNKNOWN。账务结算与rerank恢复确认分别门禁，未知预留保持；禁止初始化覆盖旧ledger、直接READY或重开预算。恢复进程互斥，首组仅重验失败的原资料检索与来源，4份解析成功项不重做。剩余78项沿用原累计预算，最多20组、每组4份、并发1。

领域76、服务112、原核心207合成回归分别通过；前端89与原生合成发布10项既有证据保留；真实Chrome18项阻塞可用性检查通过（390/768/1440、目录/历史/收藏、状态读取、诊断权限、深链接仅预填、阻塞守卫，模型请求0）。配置与业务可用性分开，观察过期为UNKNOWN；当前费用收据未结算的阻断不会靠刷新清除。新资料来源、引用问答、发布和多部门前端仍未执行，不以这些回归或CI代替整批PASS。

普通发布不恢复下架或指回旧版；replace/restore需独立精确批准，首次发布冻结16字段、事务复核并写不可变收据。精确质量子集绑定原batch与质量摘要，冻结items不改。同内容改名复用身份；新内容经显式版本关系建立新版；同部门沿用确切Dataset。后续在本轮既有批准预算内有界连续推进，无需逐组批准，但必须先取得对应请求的诊断、用量/金额证据及独立rerank恢复确认，再完成失败回归。公共Git和开发包不含真实目录/题目/摘录/对象ID/账单/审批/凭据。不合并、不切换P1。

## HBOS Knowledge R2 — 2026-10-08

状态：REAL_CORPUS_SEARCH_AND_REFERENCE_ASK_CANDIDATE_PASS / NOT_RELEASED。承接 Draft PR #30 的 `codex/knowledge-autonomous-r1`，按最新 Owner 共享范围实现部门分类，无复杂部门 ACL。12 份已批准资料在固定本机 RAGFlow v0.27.0 完成解析，原始哈希、部门映射与实际解析证据仅保留 Owner 本机。

已完成原生登录/CSRF/启用状态、精确版本与下架再核验、真实检索、部门筛选、来源摘要、资料目录、按用户的历史/收藏和维护人反馈处理。受控来源保留 COMPANY_CONTROLLED，内部参考收录单独标记 CONTROLLED_REFERENCE_REVIEWED，不伪造 GMP 生效状态。gpt-6-luna 在获准的数据流下仅接收必要摘录，回答后再次核验来源，证据不足不调用模型。

原核心 207 项、领域 58 项、独立服务 14 项、前端 85 项及类型/构建通过；最终真实验收 14 项全部通过，原失败原因与修复重测证据保留。真实浏览器流程、窄屏与最终源码/制品锁分别记录。v0.27 Word positions 仅为片段序号，参考装配将未核验页码留空，避免错误定位。测试范围重叠，不相加。CI 修复已提交 `b47c6afa`，该提交两条 PR 工作流均 SUCCESS；最终功能 head 的远端 CI 独立跟踪。

本轮仅独立本机候选，未合并或切换现行 P1，未升级/重建旧 RAGFlow 存储，旧 synthetic lease 不延长。服务 0.3.1 通过本地独立提交与 wheel 联合固定；未提供服务远端，不伪造远端服务 PR。员工 MCP、复杂 ACL、公司服务器与生产 TLS 留在后续范围。当前任务依据已收到的 R2 文件和 Owner 最新目录/模型授权，不依赖丢失的旧总任务书。

执行说明见 `docs/milestones/M1_KB_R2_真实部门知识候选.md`。以下 R1 记录为历史事实，不能当作当前 R2 阻塞清单。


## 知识候选连续执行 R1 — 2026-10-08

状态：PARTIAL_CANDIDATE_VERIFIED / NOT_RELEASED；整批总任务尚未完成。专用分支 `codex/knowledge-autonomous-r1`，Draft PR #30，固定产品基线 `72e5b1728981b7ef102a2c9ee033ce0452c400e7`。已核验 K1C2 归档与独立评审；恢复已审候选到独立源码副本，修复 Binding 列/JSON/关联身份一致性与写入守卫、搜索网格和局部字号，并实现授权空间列表、范围选择与当前文档数量。

核心/进程内 HTTP 与新增领域回归 241 PASS，候选/保留 P1 契约 56 PASS，前端 83 PASS、typecheck/frappe 构建 PASS；新 Site 的元数据/跨连接版本/空间 HTTP 14 PASS，原生 HTTP/共享状态完整重跑 19 PASS，真实 Chrome 12 项检查 PASS。前端复制遗漏已纠正，以新构建产物复跑空间筛选、隔离标识、桌面/移动/键盘/依据/撤权/切人；114 项安装源码哈希及 6 项原生框架文件一致，6 个新服务出站连接拒绝。测试存在范围重叠，不作为总验收数量相加。

本批新登记 9 容器已停止、4 卷保留，95 个既有容器身份/镜像/启停/重启/网络/挂载核验一致；这不等于数据内容备份或个人 MCP 健康验收。原环境与 lease 不改，未合并或切换正式部署。独立服务 0.2.1 本地提交 `d28c7e9a3219fc94db234302e2be14451fa10d2e`，尚无提供的远端，不声称已建立服务仓 PR。

后端 GitHub CI FAIL：当前 OAuth 凭据缺 `workflow` scope，GitHub 拒绝更新工作流；修复补丁单独交付，应用检查和全新依赖环境的本地等价复测通过。远端前端与普通 bundle 构建 PASS；普通 bundle 不包含联合 service，不能据此部署知识功能。主任务书 `HBOS_KNOWLEDGE_AUTONOMOUS_MASTER_TASK_R1.md` 未随已提供三附件出现，本机按名称检索未找到，时间/资源/完整依赖与分仓目标未核对。真实 RAGFlow、受控模型问答、员工 MCP、历史/收藏/反馈/资料维护、旧库恢复、生产 IAM/TLS 与发布仍未完成；模型与 MCP 路由保持关闭。执行事实见 `docs/milestones/M1_KB_AUTO_R1_知识候选连续执行.md`；以下旧轮次条目保留为历史与其他业务范围。

## 账号小范围收尾 — 2026-10-01

本轮接续交付基线 `eee1c5e22c57be3436244e77c65e189bd7eee242` 与 PR #21，仅做资料登录渠道、唯一个人导航、折叠偏好说明、飞书头像同步及 C03/C07/C09/F03 缺项补测；不重新全量审计、重画页面或新增账号功能。真实 Administrator 已成功飞书登录为 USER_CONFIRMED_SUCCESS，绑定、密码、MFA、Secret、企业与回调保留。本机沿用既有 P1 Site/Compose/入口，发布分支不合并、不强推、不推 main/base。 补测确认并修复参与页期限遗漏与 GET 回调未提交记录，原矩阵历史保持；最终浏览器新凭据步骤由工具要求人工接手，团队脚本与未执行状态单列。


项目名称：新乡海滨智能运营管理平台。

## 架构定案

准确叫法：Frappe/ERPNext 开源底座 + Frappe 多 App 模块化架构 + 外部独立服务扩展。

长期架构包括：

- Frappe/ERPNext 开源底座
- 海滨自定义 Frappe App
- 外部 AI/视频/算法服务
- Vue/React 驾驶舱
- 飞书集成
- Docker 部署

主技术栈：Frappe Framework、ERPNext、Frappe HR、Python、JavaScript、MariaDB/MySQL 兼容体系、Redis、Docker、Docker Compose、Vue/React、ECharts、FastAPI。

## 当前上下文

本轮账号 UI、统一账号、飞书、Knowledge/Twin 与发布收口已经通过 PR #21 完成并进入产品分支。当前产品 Authority 为 `feature/hbos-portal-product@e4b16ee80aaaf21aac2304246a4de1f9fe8995ea`；Owner 真人飞书基线和浏览器密码生命周期 3/3 均已通过，未执行的真人高风险交接/实体设备项目继续按历史记录保留。公司服务器仍 NOT_DEPLOYED。

其他业务里程碑以各自已登记主文档为准，本轮不扩大考勤/库存范围。新增代码通过独立净化发布分支交付；私有运行报告、账号、知识和模型不进入新可达对象。

## AI 默认读取规则

默认只读以下文件：

- `CLAUDE.md`
- `AGENTS.md`
- `docs/AI_CONTEXT.md`
- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`

禁止默认递归读取整个 `docs/`。

默认不读取：

- `docs/archive`
- `docs/research`
- `docs/legacy`

每轮任务开始前，必须说明本轮读取了哪些文档。

只有任务明确涉及当前里程碑时，才读取：

- `docs/plans/m0_engineering_bootstrap.md`

只有架构决策变更时，才读取：

- `docs/adr/`

## Skill 路由

本项目通过 `docs/AI技能路由规范.md` 管理不同任务类型对应的 AI skill 使用规则。

当前已确认拥有 / 可用的 skill：

- `superpowers`
- `frontend-design`
- `lark-cli`（飞书官方 CLI 工具，不是统一总 skill）
- `lark-shared`（飞书官方共享基础 skill）
- `lark-*` 官方领域 skills（详见 `docs/AI技能路由规范.md`）

未安装 skill 只能进入候选池，不得直接调用。任何 Agent 在执行开发、审查、前端设计、集成、文档维护前，必须先根据该文件判断本轮应使用的 skill。

## 提交与文档命名

本项目后续 Git 提交描述优先使用中文。可以保留 `docs`、`fix`、`feat`、`chore` 等 conventional commit 前缀，但冒号后的描述应使用中文。

新增文档名称优先使用中文或中英混合命名。技术专有名词可以保留英文，例如 Frappe、Docker、ERPNext、FastAPI、API、Skill。

Skill 路由规范文件为：

- `docs/AI技能路由规范.md`

## 后续路线

后续路线只记录，不代表已启动：

1. M1-R5 已通过 Codex 审查并收口为 COMPLETED，已交付 HRMS 配置基线、考勤工作台入口、月度汇总 Demo 和 Excel 月报导出路径。
2. M1 历史 closeout 已完成，但产品交付仍在 M1-FIX 中，尚未完成。M1-FIX-B3 为 REVIEWING / Owner UI 验收未通过；M1-FIX-B4 为 REVIEWING / Claude PASS，但 Owner 数据链路验收发现后续问题；M1-FIX-B5 为 REVIEWING。库存 M2-STOCK-R1 保持 IN_PROGRESS；其余 M2 轮次不由本任务推进。

## 前端实施流程规范

独立前端（Vue/React 驾驶舱、AI 工作台、复杂交互页面）开发必须遵循"原型先行 + Owner 审查 + 复刻实现 + 功能接入"流程。详见：

- `docs/frontend/FRONTEND_IMPLEMENTATION_GUIDE.md`

核心规则：凡涉及漂亮页面、驾驶舱、AI 工作台、复杂交互页面，必须先使用 `frontend-design` skill 产出原型/视觉方案，Owner 人工审查通过后再进入前端复刻和功能接入。Frappe Desk 后台页面不要强行重做成独立前端。

## 边界提醒

不直接修改 Frappe / ERPNext / HRMS 核心源码。优先使用原生配置、角色权限、DocType、报表、导入、API 和低代码定制。自定义 App 只用于海滨特有规则，不用于重写 HRMS 已有功能。`hb_attendance_app` 已在 M1-FIX-B 经 Owner 授权创建，后续不得擅自扩大为大而全 HR App。任何飞书真实写入必须由用户明确授权。

任何海滨自定义 App 生成、业务模型实现、真实业务数据配置、飞书真实写入、前端驾驶舱、AI 视频服务实现，以及 Docker volume 删除、site 重建或环境重构，都属于后续轮次或后续明确授权范围。


## HBOS Portal 并行工作流（Owner 已授权）

2026-09-24，Owner 已明确授权正式启动 HBOS Workspace / Portal 产品线。

该工作流与既有 Attendance / Inventory / LIMS 治理线并行；Portal 是 Experience Shell，不替代业务 App 的领域 Authority。

Authority：

- 分支：`feature/hbos-portal-product`
- Draft PR：#15
- 设计文档：`docs/experience/`
- 前端规范：`docs/frontend/FRONTEND_IMPLEMENTATION_GUIDE.md`
- Portal 前端：`frontend/hbos-portal-web/`
- Portal Platform App：`apps/hbos_portal/`

既有设计 / 实施基线（正式发布进度以 RP3 主记录为准）：

```text
EA-1～EA-4 = BASELINE
EA-5 Owner Visual Gate = APPROVED
EA-5.3 = BASELINE
EA-5.4 = DESIGN ENGINEERING BASELINE
EA-5.5 = COMPLETE / OWNER APPROVED

P2 Portal Skeleton / Bootstrap / Runtime = PASS
P3 Three-App Registry = PASS

LIMS       = entry + summary + tasks + search
Attendance = entry + HR summary
Inventory  = entry + permission-aware summary
```

Inventory Summary 不直接消费现有 raw-SQL 库存报表。Inventory App 先使用当前 Frappe Session 的 permission-aware Warehouse 可见范围，再显式限制 Bin 查询，并只向 Portal 投影计数型指标；不同 UOM 的库存数量不跨物料求和。

Attendance 普通员工个人入口、Attendance / Inventory Tasks 与 Search 仍未开放。

真实 Frappe 模式禁止用 Mock 数据补齐缺失业务能力。Mock 仅用于 UI / Experience 开发。

本地工作台：

```bash
bash scripts/portal/start_local_workspace.sh
```

完整本地运行态验收：

```bash
bash scripts/portal/p3_workspace_runtime_smoke.sh
```

本地 smoke 会验证七个 Site App、三 Provider、Bootstrap、Inventory Summary、三 Stable Route、Administrator Frappe Session 以及 Vite → Frappe API proxy；它不删除 volume、不重建 Site、不写三业务 App 的业务事实。

当前推进 RP3 的原账号 Site 确认、部署与真实统一账号验收；其他前端研究不自动启动。必须继续遵守 `docs/frontend/FRONTEND_IMPLEMENTATION_GUIDE.md`：独立前端先做原型 / 视觉方案与 Owner Gate，再实施；Desk 后台页面不得为了“好看”被整体重写成独立前端。

Portal 技术栈：Vue 3 + Ant Design Vue + Vue Router + Pinia + Axios；ECharts 按需使用。

团队通用交付已通过 [PR #21](https://github.com/zjl327707743/HBOS-Platform/pull/21) 合入产品分支；后续团队基线为 `feature/hbos-portal-product@e4b16ee80aaaf21aac2304246a4de1f9fe8995ea`。PR #15/main 仍需独立 Gate。
