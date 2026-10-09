# M1 启动门禁

## HBOS Knowledge N1 夜间候选 — 2026-10-10

状态：N1_PARTIAL_WITH_INDEPENDENT_WORK_COMPLETED / ACCOUNTING_PENDING / LOCAL_CANDIDATE_ONLY。原生 rerank 协议适配进入固定 RAGFlow 的实际模型注册入口；严格校验本请求的索引、分数、usage 和 request_id，其他模型保持原实现。生产参考装配缺原预算绑定时拒绝调用。旧 UNKNOWN 没有结清依据，普通模型调用、旧失败项解析和新资料在线发布继续关闭，不能以离线适配或此前单次成功宣称业务恢复。

本轮完成知识目录的服务端分页及筛选、本人反馈与处理状态、统一搜索/问答输入、一般反馈、历史/收藏上下文重放及多部门明确选择。修复同版本撤权后的旧活动标题泄漏、跨请求身份清理和数据库并发收藏幂等。新资料仅本地准入、身份去重、隔离及冻结计划；真实原文、问题、账号、运行配置和费用证据不进入公共 Git 或开发包。

领域106、本地准入18、独立服务163（原冻结包162项，补充1项）、前端143项合同已运行通过；层级有重叠，不相加，合成测试不代替真实来源/答案质量。最终原生数据库、HTTP、浏览器、远端 CI 和安装制品证据分别在联合交付中核对。PR #30 继续 Draft；只有全部业务、审查、CI、制品和部署边界门槛同时通过才可合入产品分支。此次不切 P1 或开放员工，其他 PR 和 main 不变。


补充复核已完成：独立服务仅增加普通预算双 OS 进程锁入口握手回归，本地提交 `7485bae3073ce11511d7946578329a8090a8574e`；0.3.11 运行源码与原冻结 wheel 逐文件一致，删锁和子进程异常反例独立复核通过。两新目录发现703条路径；本地计划修订技术准入240条、200个新唯一内容，隔离463条。原238/198/465冻结及失败证据保留；修订未上传、入库、质量批准或发布，技术准入不宣称公司业务生效。补充原生 Chrome 键盘操作确认预算拦截，系统中文 IME 候选仍未核验，不能据此称完整在线验收通过。

本轮主记录：[M1-KB-N1 夜间连续候选](M1_KB_N1_夜间连续候选.md)。以下 R2.1 / R2 / R1 条目保留为历史事实。

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

## PR #21 最终 Gate — 2026-10-01

FINAL_REVIEW_BLOCKED：既有原生 MFA 跨请求证明 blocker 已最小修复；新 HEAD 的全部 CI/构建/历史扫描仍须最终核对。Browser final-submit 三项尚未实际完成，Owner 最新无破坏验收为 WAITING_OWNER_ACCEPTANCE。只有两项实际 PASS 且其余 Gate 全通过才 squash #21 到产品分支；#22 已冻结待安全承接，#15/main 不合并。真人验证码/新员工开户/高风险交接/实体手机软键盘未执行仍 NOT_RUN，按本轮授权不统一阻塞产品分支合入。

## 账号小范围收尾 — 2026-10-01

本轮接续交付基线 `eee1c5e22c57be3436244e77c65e189bd7eee242` 与 PR #21，仅做资料登录渠道、唯一个人导航、折叠偏好说明、飞书头像同步及 C03/C07/C09/F03 缺项补测；不重新全量审计、重画页面或新增账号功能。真实 Administrator 已成功飞书登录为 USER_CONFIRMED_SUCCESS，绑定、密码、MFA、Secret、企业与回调保留。本机沿用既有 P1 Site/Compose/入口，发布分支不合并、不强推、不推 main/base。 补测确认并修复参与页期限遗漏与 GET 回调未提交记录，原矩阵历史保持；最终浏览器新凭据步骤由工具要求人工接手，团队脚本与未执行状态单列。


项目名称：新乡海滨智能运营管理平台。

## Portal 账号审修独立授权门禁 — 2026-10-01

本轮（2026-10-01）接续 PR #21，执行登录账号模块 UI 规范回归与全功能审修。Owner 已亲自确认 Administrator 能通过本人飞书验证并登录，记为 OWNER_CONFIRMED_SUCCESS；历史成员权限待审批或登录失败记录不再代表当前事实。保留真实绑定、密码、MFA、Secret、企业与回调；不要求重复配置。认证页沿用已有 Ant Design Vue / ConfigProvider / typography / tokens，修复表单、证明期限、错误状态、同路由目标与提交结果处理。破坏性、并发与交接只在独立合成 Site 验证。新版本真人 OAuth、本人收到验证码、第二位真人交接与移动软键盘结果单独记录，未执行不写 PASS。复用现有 P1 / Compose / 卷与常用入口，最终本机 SHA/build ID、远端提交、CI 和制品须一致。公司服务器为 NOT_DEPLOYED。主记录：`docs/milestones/M1_RP3_统一账号飞书绑定与正式发布.md`。PR #21 head `codex/portal-unified-account-release`、base `feature/hbos-portal-product`；不强推、不自动合并、不推 main/base。

本机验收顺序：已确定 P1 的保护备份 → 同库更新且保留账号/权限/关联 → 保留已成功的 Administrator 本人飞书路径 → 新版本正常登录复核 → 第二位获准企业身份首次开户及重复登录 → 可选本人验证码设密、恢复与拒绝边界。真实验收不能由 configured、许可标记或测试替身代替。公司服务器首次部署、固定 IP 和 HTTPS 为后续独立工作，不能阻塞本轮 Mac、PR 或制品。其他考勤/库存里程碑不由此 closeout。

团队通用交付已发布至 [PR #21](https://github.com/zjl327707743/HBOS-Platform/pull/21)（Draft、未合并），本轮复用 P1，不以原库/服务器/HTTPS 为前置条件；本人授权与公司生产分开验收。

## 文件定位

本文件记录 M1 启动前必须满足的门禁条件。M1 规划轮次已历史收口，但产品交付仍在 M1-FIX 中；M1-FIX-B2 已 COMPLETED，M1-FIX-B3 为 REVIEWING / Owner UI 验收未通过，M1-FIX-B4 为 REVIEWING / Claude PASS，但 Owner 数据链路验收发现后续问题，M1-FIX-B5 为 REVIEWING，当前 **M1-FIX-F（调休模块）为 REVIEWING / 两阶段均已上线**。M1-FIX-C/D/E 未启动。**M2-STOCK-R1（库存模块隔离）为 IN_PROGRESS**，分支 `m2-stock-r1`；M2 其余轮次未启动。

## 必须满足的前置条件

- M0 状态必须为 COMPLETED。
- M0-REMOTE 必须完成：创建 GitHub Private remote、添加 `origin`、首次 push `main`。（已完成，见 `docs/milestones/M0_REMOTE.md`。）
- `git status` 必须 clean。
- 不允许提交 `.env`、备份文件、密钥、数据库、Docker volume 或运行时数据。
- 当前 Frappe / ERPNext / HRMS 环境应保持可访问；如 HRMS 丢失，必须先恢复环境，再讨论 M1。

## M1 初期范围

M1-R0 只做：

- 平台入口治理。
- 账号体系。
- 角色权限。
- 飞书 SSO 可行性。
- 中文化 / 本地化诊断。

M1-R0 当前状态：COMPLETED，已通过 Codex 独立审查。方案文件见 `docs/milestones/M1_R0_平台入口账号权限与本地化诊断方案.md`。

M1-R0 不做：

- 不开发考勤业务。
- 不创建 `hb_attendance_app`。
- 不接飞书真实写入。
- 不实现 Vue / React 驾驶舱。
- 不修改 Frappe / ERPNext / HRMS 核心源码。

M1-R1 才验证 HRMS 原生考勤对象模型。M1-R1 当前状态：COMPLETED，已通过 Codex 独立审查，验证记录见 `docs/milestones/M1_R1_HRMS原生考勤对象模型验证记录.md`。

M1-R2 当前状态：COMPLETED，已通过 Codex 独立审查。M1-R2 只做 HRMS 原生考勤配置试运行方案，未执行配置，未创建测试数据，未创建 App，未接真实考勤机，未接真实飞书，未录入生产数据。方案文件见 `docs/milestones/M1_R2_HRMS原生考勤配置试运行方案.md`。

M1-R3 当前状态：BLOCKED。M1-R3 已使用 `TEST-HBOS-M1R3-` 前缀尝试虚构最小测试数据试运行 HRMS 原生考勤配置；部分 TEST 数据已落库，但 Attendance 闭环与 14 个场景验证未完成。Codex 审查 PASS，但该轮不是成功完成，不得标记为 COMPLETED。记录见 `docs/milestones/M1_R3_HRMS原生考勤最小测试数据试运行记录.md`。

M1-R3A 当前状态：COMPLETED。M1-R3A 已完成运行态阻断诊断与 TEST 数据隔离 / 清理方案，并已通过 Codex 审查，记录见 `docs/milestones/M1_R3A_运行态阻断诊断与TEST数据隔离清理方案.md`。本轮未继续创建测试数据，未执行配置试运行，未清理数据。

M1-R3B 当前状态：COMPLETED。M1-R3B 已完成运行态最小修复方案，并已通过 Codex 审查，记录见 `docs/milestones/M1_R3B_运行态最小修复方案.md`。本轮只是修复方案和状态收口，不是修复执行；未执行修复，未启动或重启服务，未清理 TEST 数据，未继续试运行。

M1-R3B-FIX 当前状态：COMPLETED。M1-R3B-FIX 已通过 Codex 审查，审查结果 PASS，并从 REVIEWING 收口为 COMPLETED；记录见 `docs/milestones/M1_R3B_FIX_运行态最小修复执行记录.md`。该轮只执行 `docker compose up -d redis-cache redis-queue`，`redis-cache`、`redis-queue`、queue worker、scheduler、`bench doctor` 和 `/login` 已恢复或改善；未清理 TEST 数据，未继续创建 TEST 数据，未执行 HRMS 考勤试运行。

M1-R3C 当前状态：COMPLETED。M1-R3C 已通过 Codex 审查，审查结果 PASS，并从 REVIEWING 收口为 COMPLETED；结论为 PARTIAL / GAP_IDENTIFIED。M1-R3C 已在用户授权下使用 `TEST-HBOS-M1R3C-*` / `test-hbos-m1r3c-*` 虚构 TEST 数据重新试运行；Company / User / Employee 写入阻断已解除，13 条 Attendance 已生成，14 个场景中 8 个通过、6 个为 GAP / PARTIAL。迟到 / 早退未置位、缺卡 / 缺勤口径、请假 Leave Allocation、加班业务口径仍是后续 Gap。记录见 `docs/milestones/M1_R3C_HRMS原生考勤最小试运行复测记录.md`。

M1-R3D 当前状态：COMPLETED。M1-R3D 已通过 Codex 审查，审查结果 PASS，并从 REVIEWING 收口为 COMPLETED；记录见 `docs/milestones/M1_R3D_异常口径与Gap诊断.md`。结论为 Gap 四类分类（HRMS 配置、原生 / 自定义报表、海滨业务规则定义、未来自定义 App 候选），8 个 Gap 均不需要立即创建 `hb_attendance_app`。本轮未继续试运行，未创建、删除或清理 TEST 数据，未创建 App / DocType / 代码，未接真实考勤机、真实飞书或 SSO。

M1-R3E 当前状态：COMPLETED。M1-R3E 已通过 Codex 审查，审查结果 PASS，并从 REVIEWING 收口为 COMPLETED；记录见 `docs/milestones/M1_R3E_配置复核与业务口径确认表.md`。本轮仅做文档交付，未试运行，未创建、删除或清理 TEST 数据，未创建 App / DocType / 代码。配置复核清单覆盖 8 类问题，业务口径确认表覆盖 10 项业务口径，8/10 项阻塞 M1-R4。

M1-R3F 当前状态：COMPLETED。M1-R3F 已通过 Codex 审查，审查结果 PASS，并从 REVIEWING 收口为 COMPLETED；记录见 `docs/milestones/M1_R3F_业务口径确认包.md`。本轮完成文档交付并已收口，未试运行，未创建、删除或清理 TEST 数据，未创建 App / DocType / 代码。确认包共 9 项确认主题，7 项必须业务负责人确认才能进入 M1-R4。

M1-REQ-DESIGN-DRAFT 当前状态：COMPLETED。M1-REQ-DESIGN-DRAFT 已通过 Codex 审查，审查结果 PASS（初审员工姓名脱敏 blocker 已修复，提交 `69aec6a`），并从 REVIEWING 收口为 COMPLETED；记录见 `docs/milestones/M1_考勤一期真实需求确认.md`、`docs/milestones/M1_考勤一期产品需求说明书.md`、`docs/milestones/M1_考勤一期技术设计方案.md`、`docs/milestones/M1_Demo实施路线图.md`。本轮只写文档，未试运行，未创建、删除或清理 TEST 数据，未创建 App / DocType / 代码，不修改核心源码。已补齐 M1 真实需求、PRD、技术设计、Demo 实施路线图四份文档。M1-R4 定位为 Demo 技术方案与实施路线拆分。

M1-R4 当前状态：COMPLETED。M1-R4 已完成 Demo 技术方案与实施路线拆分，主文档 `docs/milestones/M1_R4_Demo技术方案与实施路线拆分.md` 已交付。审查记录：Codex 初审 FAIL（发现 3 类 blocker：Git 同步门槛、公共入口 M1-R4 过期状态残留、阶段文字错误），已在 `2fbb6dc` 中修复；Codex 复审 PASS。M1-R4 定位为规划拆分轮，已完成 R5/R6/R7 后续轮次拆分，未开发、未试运行、未创建 App/DocType/代码。

M1-R5 当前状态：COMPLETED。M1-R5 已完成 HRMS 配置基线、考勤工作台入口、月度汇总 Demo 展示路径与 Excel 月报导出路径文档交付，主文档 `docs/milestones/M1_R5_HRMS配置基线工作台月报Demo.md` 已交付。审查记录：Codex 审查 PASS，已从 REVIEWING 收口为 COMPLETED。

M1-R6A 当前状态：COMPLETED。M1-R6A 已完成 Excel 导入与异常流程落地方案 / Gate 判定文档交付，主文档 `docs/milestones/M1_R6A_Excel导入与异常流程落地方案.md` 已交付。审查记录：Codex 初审 FAIL（未提交、工作区不 clean），复审 PASS（修复后 closeout 收口为 COMPLETED）。本轮未导入 Excel、未创建 App、未创建 DocType、未写代码。

M1-R6B 当前状态：COMPLETED。M1-R6B 已完成脱敏打卡流水导入最小实现，主文档 `docs/milestones/M1_R6B_脱敏打卡流水导入最小实现.md` 已交付并完成 closeout。审查记录：Codex 审查 PASS，closeout 已完成。本轮先将 Owner 提供 Excel 判定为混合表，未将其作为 Employee Checkin 导入源；使用脱敏 Demo 原始打卡流水写入 5 条 Employee Checkin，并通过 HRMS 原生 Auto Attendance 生成 3 条 Attendance。本轮未提交 Excel / CSV，未创建 App，未创建自定义 DocType，未启动 R6C/R7。

M1-R6C 当前状态：COMPLETED。M1-R6C 已完成异常识别与异常说明流程最小实现，主文档 `docs/milestones/M1_R6C_异常识别与异常说明流程最小实现.md` 已交付并完成 closeout。审查记录：执行审查 PASS，closeout 已完成。异常识别 7 个场景已验证通过；`late_entry`/`early_exit` 在 Shift Type 配置修复后正确置位；11 个 Custom Field 已在 HRMS 原生 Attendance Request 上扩展完成；HRMS 原生 `validate_no_attendance_to_create()` 在已有 Attendance 场景下阻止 Attendance Request 创建已记录为后续 Owner 授权点。本轮未创建 App、未创建 DocType、未修改核心源码、未提交 Excel / CSV。

M1-R7 当前状态：COMPLETED。M1-R7 已完成飞书 OAuth 登录方案设计、领导汇总 Demo 指标定义与实现路径、M1 Demo 演示路径整理和 M1 收口准备项清单。审查记录：Codex 初审 FAIL（3 类 blocker），已在 `e812e32` 中修复；复审 PASS，已 closeout 为 COMPLETED。

M1 总收口历史 closeout 已完成；Owner UI 验收发现功能缺口后，当前 M1 产品交付仍在 M1-FIX 中，尚未完成。

M1 规划收口已完成，但产品交付仍在 M1-FIX 中，尚未完成；M1-FIX-B2 为 COMPLETED，M1-FIX-B3 为 REVIEWING / Owner UI 验收未通过，M1-FIX-B4 为 REVIEWING / Claude PASS，但 Owner 数据链路验收发现后续问题，M1-FIX-B5 为 REVIEWING，当前 **M1-FIX-F（调休模块）为 REVIEWING / 两阶段均已上线**。M1-FIX-C/D/E 未启动。**M2-STOCK-R1（库存模块隔离）为 IN_PROGRESS**，分支 `m2-stock-r1`；M2 其余轮次未启动。
M1-R8 当前状态：PLANNED（可选缓冲轮，不预先承诺一定执行）。

## 中文化与核心源码边界

中文化问题只诊断，不改 Frappe / ERPNext / HRMS 核心源码。

优先使用：

- 原生配置。
- 角色权限。
- DocType。
- 报表。
- 导入。
- API。
- 低代码定制。

## 自定义 App 决策边界

M1 初期不创建 `hb_attendance_app`。M1-FIX-B 已经 Owner 明确授权创建轻量 `hb_attendance_app`，仅用于导入入口、导入日志和 M1-FIX 必需扩展。

优先复用 HRMS 原生考勤能力。只有 HRMS 原生能力无法覆盖新乡海滨特有规则，或用户明确批准进入自定义 App 阶段时，才考虑创建自定义 App。

自定义 App 只用于海滨特有规则，不用于重写 HRMS 已有功能。

## 飞书边界

飞书真实写入必须用户明确授权。

飞书真实写入包括但不限于：

- 群消息发送。
- 多维表格写入。
- 通讯录修改。
- 审批操作。
- 邮件发送。
- 云文档编辑。
- 任务创建或修改。

## 环境保护规则

- 不得执行 `docker compose down -v`。
- 不得删除 Docker volume。
- 不得删除或重建 `frontend` site。
- 不得重新初始化 ERPNext。
- 不得提交 `.env`、备份文件、密钥、数据库、Docker volume 或运行时数据。

## 启动顺序

1. M1-R0：平台入口治理、账号体系、角色权限、飞书 SSO 可行性、中文化 / 本地化诊断。
2. M1-R1：HRMS 原生考勤对象模型验证。
3. M1-R2：HRMS 原生考勤配置试运行方案。
4. M1-R3：HRMS 原生考勤最小测试数据试运行。
5. M1-R3A：运行态阻断诊断与 TEST 数据隔离 / 清理方案。
6. M1-R3B：运行态最小修复方案。
7. M1-R3B-FIX：运行态最小修复执行，当前为 COMPLETED。
8. M1-R3C：HRMS 原生考勤最小试运行复测，当前为 COMPLETED。
9. M1-R3D：HRMS 原生考勤异常口径与配置 Gap 诊断，当前为 COMPLETED。
10. M1-R3E：配置复核清单与业务口径确认表，当前为 COMPLETED。
11. M1-R3F：业务口径确认包，当前为 COMPLETED。
12. M1-REQ-DESIGN-DRAFT：M1 考勤一期需求设计草案，当前为 COMPLETED。
13. M1-R4：M1 Demo 技术方案与实施路线拆分，当前为 COMPLETED。
14. M1-R5：HRMS 配置基线、考勤工作台与月度汇总 Demo，当前为 COMPLETED。
15. M1-R6A：Excel 导入与异常流程落地方案 / Gate 判定，当前为 COMPLETED。
16. M1-R6B：脱敏打卡流水导入最小实现，当前为 COMPLETED。
17. M1-R6C：异常识别与异常说明流程最小实现，当前为 COMPLETED。
18. M1-R7：飞书登录、领导汇总 Demo 与 M1 收口准备，当前为 COMPLETED。
19. M1 总收口：M1 考勤一期历史 closeout 已完成；当前产品交付仍在 M1-FIX 中。
20. M1-R8：M1 Demo 验收修复与文档收口（可选缓冲轮），当前为 PLANNED。
21. M1-FIX-A：功能补漏差距盘点与实施方案，当前为 REVIEWING。
22. M1-FIX-B：Excel 导入与真实本地数据闭环，当前为 REVIEWING。
23. M1-FIX-B-FIX：Excel 导入与中文体验修复，当前为 REVIEWING。
24. M1-FIX-B2：导入口径、安全与准确性修复，当前为 COMPLETED。
25. M1-FIX-B3：考勤工作台入口、App 命名与 HRMS 数据一致性修复，当前为 REVIEWING / Owner UI 验收未通过。
26. M1-FIX-B4：考勤模块架构收敛与单一入口重整，当前为 REVIEWING / Claude PASS，Owner 数据链路验收发现后续问题。
27. M1-FIX-B5：导入数据链路核查与报表口径收敛，当前为 REVIEWING（2026-09-02 已追加：规则看板 Tab 三类规则可视化 + 班次人员维护表导出 5-sheet；2026-09-03 再追加：月度考勤汇总 AI复核 enable_ai 临时列）。
28. M1-FIX-C/D/E：后续补漏轮次，当前为 PLANNED。
29. M2：飞书集成（长期轮次）。M2-STOCK-R1（库存模块隔离）为 IN_PROGRESS，分支 `m2-stock-r1`；飞书集成等其余 M2 轮次为 NOT STARTED / 待 Owner 授权。

M0-REMOTE 已完成。M1-R0 已完成。M1-R1 已完成并通过 Codex 独立审查。M1-R2 已完成并通过 Codex 独立审查。M1-R3 已通过 Codex 审查并收口为 BLOCKED。M1-R3A 已通过 Codex 审查并收口为 COMPLETED。M1-R3B 已通过 Codex 审查并收口为 COMPLETED。M1-R3B-FIX 为 COMPLETED。M1-R3C 为 COMPLETED。M1-R3D 为 COMPLETED。M1-R3E 为 COMPLETED。M1-R3F 为 COMPLETED。M1-REQ-DESIGN-DRAFT 为 COMPLETED。M1-R4 为 COMPLETED，已通过 Codex 审查并收口。M1-R5 为 COMPLETED。M1-R6A 为 COMPLETED。M1-R6B 为 COMPLETED。M1-R6C 为 COMPLETED。M1-R7 当前为 COMPLETED。M1 总收口历史 closeout 已完成；当前产品交付仍在 M1-FIX 中。M1-R8 为 PLANNED（可选缓冲轮）。
