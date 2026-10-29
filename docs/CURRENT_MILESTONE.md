## 当前集成状态 — 2026-10-19

**四个完整业务 PR 已实际合并：#42 考勤、#46 生产、#39 仓储、#43 LIMS。** 唯一目标为 `feature/hbos-portal-product`；业务合并基线为 `04e0bb033cb2e7156e407cf49a7b6966b0d2a022`，状态文档在其后维护。[#43](https://github.com/zjl327707743/HBOS-Platform/pull/43) 于 2026-10-19 03:28:29 UTC 正常 Squash Merge；来源、父提交与树见[项目状态](PROJECT_STATUS.md)。

**合并前精确组合：PASS。** [R10 39184807396](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39184807396) 全部 10 jobs SUCCESS，五个原生域与离线／契约／构建在本次 #43 来源和产品基线的真实组合上通过；该组合树与实际 Squash 树相同。

**实际产品合并后回归：PASS。** [R11 39195037712](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39195037712) 全部 10 jobs SUCCESS；五个原生域均直接运行业务合并基线 `04e0bb033cb2e7156e407cf49a7b6966b0d2a022`，无额外 merge，实际单父与树一致，双 migrate 与清理均成功。LIMS 原有 32 项、新增审计 9 项、独立 Todo 1 项合计 42 项原生测试全部通过；Todo 只有 1 项，归属 LIMS。

当前轮次为四项完整业务 PR 的合并后验证与状态收口：#42 → #46 → #39 → #43 均已实际合入唯一产品分支，R11 五个原生域及 LIMS 独立 Todo 1 项补证均通过。当前收口包括状态文档与两处 Python 3.10 测试夹具兼容修复；本收尾 PR 必须在固定候选 SHA 的 Python 3.10／3.12 检查通过后方可合并，实际结果以本 PR 最新 Owner 裁定及最终报告所列 SHA／Job 为准，详见项目状态的独立 CI 事件记录。IAM #52、#37、OCR、真实样本、实体打印及生产 UAT／部署不由本次代码合并 closeout；质量放行撤回未在本轮实现。

业务合并基线与文档保存后的 HEAD 分开记录。Run1–9 的历史失败、未合并及 `NOT_PRODUCT_COMPOSITION` 均按各自日期、来源和作业保留，详见 [PR #56](https://github.com/zjl327707743/HBOS-Platform/pull/56)；最新业务与回归状态以本节和项目状态为准。

### 历史回归 — 2026-10-18 Run8（#39 合并后）

**合并后回归：PASS。** [Run8 39107944012](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39107944012) 全部 8 jobs SUCCESS；四个业务域直接检出实际产品 `a1cc65dde73cfad656faf290264f75fb1a25c32b`，记录 `post_merge_baseline`，源码树为 `43b59653ebbe61db530f523ea980163c88f1899e`、唯一父提交为 `4ddf9bebe5bd9f0d73cdb84bd4ddfa9b8615ad30`。仓储事务 8/8、报表22项HTTP与8项跨仓CSV、卡证权限74/74、考勤原生范围及生产28项检查均通过；所有原生Site双migrate与清理通过。完整来源与后续文档提交见 [PR #56](https://github.com/zjl327707743/HBOS-Platform/pull/56)，不以文档提交后的新HEAD冒充上述已运行提交。

## 验证历史 — 2026-10-18 Run6

[报表、扫码及附件验证](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39103298497/job/117603810152) **74 PASS / 0 FAIL**；[事务验证](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39103298497/job/117603810103) **6 PASS / 2 FAIL**。余两项失败为按单一 URL 误选 Batch File 的测试定位错误，LIMS 放行后两种外发 submit/cancel 仍 **NOT_REACHED**，完整仓储门禁未通过。

## 验证历史 — 2026-10-18 Run5

以下保留 Run5 当时的观察与判断，其中“当前”“尚未通过”“原因待定位”均指该次验证；后续状态以页首“当前集成状态”和实际 PR 记录为准。

当前继续完成 Owner 授权的业务 PR 合并。完整 #42 考勤与 #46 生产已合并，已核对产品为 `4ddf9bebe5bd9f0d73cdb84bd4ddfa9b8615ad30`。[#39 仓储](https://github.com/zjl327707743/HBOS-Platform/pull/39) **尚未合并／技术门禁 FAIL**：Run 5 的扫码与附件权限域 73/74 通过、真实事务域 3/8 场景通过；PDF 正文、注册外协目标放行旁路及完整 LIMS 放行链仍需收口。具体失败、`NOT_REACHED` 和固定 SHA 见 [项目状态](PROJECT_STATUS.md) 与 [#56](https://github.com/zjl327707743/HBOS-Platform/pull/56)，不能用来源分支提交替代产品合并。

下一步在最新仓储来源修复并重跑其真实组合，满足门禁后才 Squash、重读产品 HEAD 并做合并后回归。#43 后置；其独立 39/39 契约与 4 项 mutation 检查通过只记为 `NOT_PRODUCT_COMPOSITION`。本轮不据此完成 M3-R6 的 OCR／实体打印验收，不推进 IAM #52、#37 或生产部署。

## 历史阶段记录

下方较早合并、账号、M1 与 Portal 阶段的“当前”“本轮”和允许范围保留原日期含义，不覆盖页首 R3 授权与验证记录；实际最新来源、验证及合并以 PR #39、PR #56 和远端产品 ref 为准。

> 2026-10-18 生产已完成集成：完整 #42 考勤、#46 生产均已实际合并。最新核对产品为 `4ddf9bebe5bd9f0d73cdb84bd4ddfa9b8615ad30`，来源、审批与原生验证见 [项目状态](PROJECT_STATUS.md)。继续推进 #39 仓储，#43 后置；以下较早产品 SHA 为各阶段历史记录，不替代远端最新 ref。

> 2026-10-18 最新代码集成：**首个完整业务 #42 考勤已实际合并**。产品基线 `374e2bd8633d4127fabcc4659c2314e4a7ca7cd8`，实际父提交 `45658fe4b84d8fb7dd4433c459aa30572e0d13d3`。来源与审批、CI、归档证据见 [PR #42](https://github.com/zjl327707743/HBOS-Platform/pull/42) 和 [项目状态](PROJECT_STATUS.md)。下一顺序为 #46 生产、#39 仓储，#43 LIMS 后置；每项仍以当前 SHA 的权限、运行与审查门禁为准。Owner 承担本批次最终审批，具体方式见 [正式裁定](governance/HBOS_Owner_业务集成批次裁定_20261018.md)。本轮不代表真实环境部署或 IAM #52 完成。

> 历史记录：2026-10-18 物料只读集成窗口：仓储物料只读浏览由 [PR #55](https://github.com/zjl327707743/HBOS-Platform/pull/55) 独立承接；当前代码来源以远端 `feature/hbos-portal-product` 与该 PR 实际合并 SHA 为准。下方 PR #21 的 SHA/账号验收是历史记录，不代表最新产品 HEAD。完整业务 #42/#43/#46/#39 和 IAM #52 各自保留独立门禁；本轮不安装或部署真实环境。

> 知识专项（PR #30，分支 `codex/knowledge-autonomous-r1`）：以下为知识轮次自己的状态记录，保留其原日期含义；是否合入、验收与部署以 [PR #30](https://github.com/zjl327707743/HBOS-Platform/pull/30) 的实际记录为准。

## 2026-10-27 Knowledge RC14 V2

当前为隔离员工体验候选的 REVIEWING / LOCAL_UAT / OWNER_NOT_RUN。采用 Codex Main + 三个真实外部应用执行入口，D 安全后端由 Main 负责；外部完成、失败、超时和 Main 修正如实分列。当前轮次见 [RC14 员工体验候选](milestones/M1_KB_RC14_员工体验候选.md)。真实分数、资料净增、运行版本、费用未知项与 CI 仅认 Owner 私有 RC14 交付，不继承旧 PASS。

受控下载独立授权，默认拒绝；只有精确候选测试范围可开启。PDF 原版式与 Office 派生预览均经原件哈希、当前版本、撤回和当前账号复核。仅本机候选，PR #30 保持 Draft，不合并、不切 P1、不开放正式员工。产品生成仍为批准 DeepSeek，千问 1024 维与 rerank 关闭保持。

## 2026-10-26 RC1.1 执行

承接 RC1。围绕已命中资料的正文证据补足、有限同源章节检索、原目录缓存复用与质量发布、目录返回保留以及隔离恢复副本验证继续收敛。原20题及目标身份保持，首次结果保留；最终实际问答完成率、140项优先资料处理和净新增、时延、CI及回退回执仅认Owner本机 `OWNER_RC1_1_RESULT.md` 与联合锁。新版本仍为待验候选，不据代码测试宣称业务通过。

自动生成仅 deepseek-flash，原千问/1024维与零rerank保持；不合并PR #30、不切P1、不开放员工、正式目录只读。RC1既有两次切换收据保留；RC1.1保留一次计划切换及目录滚动、实际chunk DTO契约两次有据修复，只有Main Agent操作。

## 2026-10-26 Knowledge UAT6 RC1 当前候选

Owner 已授权在现有隔离 UAT6 上收敛 RC1。保留模型配置、原千问 1024 维、零 rerank、融合后排序修复、MCP 负向和页面软复核；本轮补充真实 ID/版本评测、普通资料实际处理、原目录浏览及不可变制品/可执行回退。最终实际版本、质量、时延、资料净增与远端 CI 只认 Owner 私有 `RELEASE_LOCK.json` 与 `OWNER_RC1_RESULT.md`，不继承旧报告的 PASS。

PR #30 继续 Draft；正式 HBOS 目录只读，不合并、不切 P1、不自动开放员工。自动生成仅 deepseek-flash；不用其他生成模型或付费子 Agent。独立服务源码不向公开仓上传完整历史。当前入口：[UAT6 RC1 可用候选](milestones/M1_KB_UAT6_RC1_可用候选.md)。

## 2026-10-19 UAT5 执行补充当前检查点

**运行补充（2026-10-19）：** Owner已授权整体Docker资源调整，现为10 GiB内存／4 GiB Swap，Docker Desktop界面恢复可操作。原44个运行容器及原ES恢复，其他原停止容器保持停止；原数据卷、索引UUID和应用配置语义保留。首轮有限计划已收束为359份完成、1份已知阅读器异常，跳过此前260份成功项；扩展255份全文技术版本已全部完成首次解析，有限工作进程已结束；各组按最多4份及至少1 GiB内存余量保护执行。当前无写入、Docker连接或必要模型网络权限拒绝。带时间戳的发布总量、15个Dataset数量和逐份收据在Owner本机闭合台账，解析完成不代表允许共享。

**UAT5_PARTIAL / LOCAL_UAT / OWNER_NOT_RUN / ROLLOUT_PENDING。** 当前隔离候选安装独立服务 **0.6.22**；原知识领域与独立前端保留。安装包逐文件核对一致，服务505项、知识前端154项检查通过；这些不代替真实业务及Owner验收。PR #30 保持Draft，不合并、不切P1、不开放正式员工。

已定位并修复完整原句仍遭拒绝的实际原因：提取结构标签与正文混合、条件在义务词规范化前提取、全角标点规范化后与片段边界不一致。数字、单位大小写、否定、真实条件、主宾关系、完整单元、生成后来源及权限复核继续保留。同源索引修复采用新版本与原件哈希、父绑定和当前发布比较校验，原件、原发布历史不删除。

新增封闭证据单元选择契约，由服务端按完整原文要点分别组织并引用，明确显示“按所引原文整理”。四个旧自然语言失败问题的最新逐题收据均获得可核验原文整理回答，8/8个来源重新打开；其中前三题在0.6.21、剩余一题在0.6.22完成，不能写成0.6.22全量基准通过。0.6.20原四题自由措辞仍0/4通过；原文整理不能计作模型自由归纳通过。原73题未重新大批重放。 Docker资源恢复后新增1个工程清单业务题使用deepseek-flash实测，回答及预期引用1/1通过、来源复开1/1；仍为原文整理模式，不能据单题证明全库自然归纳通过。

全目录闭合台账保持每个唯一内容一个去向，别名另列；不覆盖初始盘点。已发布、原件上传、原生解析、完整索引验证、OCR提取及最终共享质量分别计数。通过原件、身份、全文、向量和授权质量的具体资料继续发布；OCR、表格/图示、隐私及保密疑点继续逐份核对。既有成功项跳过，失败和不确定请求不自动重放。原OCR318份补齐2个缺失页后形成13695页结构记录，两处具体敏感线索经原页核对，1处为真实供应商联系方式待共享／脱敏判断，1处为表格数字拼接误报；另对0页阅读器异常资料完成25页离线OCR，单独保留冻结计划。工程3表的15工作表、1070非空单元格已逐页预览与独立值对照，明确保留作废／未签批／未生效及合并行关系；其中2份已用保留完整行关系的新文本版本索引并作为参考发布，原件及旧版本保留；另1份图例关联待明确。CAD112份已完成本地有界导出尝试，104份DXF仍待几何核验、5份达到输出上限、3份读取错误，未自动发布。

本机两次Docker虚拟机整体内存耗尽终止ES的内核global_oom证据已保存。此前批次在完整组末停止；最新Owner授权资源维护已恢复原容器、挂载和索引，现按有限批次续跑。整体Docker受控重启前已备份数据库与容器清单，P1路由、应用版本和既有数据不变。一个原PDF在原生阅读器读成0页的问题已完成保留原件的结构修复，尚不据此宣告完整质量通过。

三名获批候选测试账号的定向换密和旧会话撤销已完成；Owner已登录现有RAGFlow管理页，现有15个Dataset文件页面均有真实访问证据。收藏保存/重开/跨用户拒绝、既有历史重开、维护员允许与员工拒绝，以及既有隔离MCP连接的真实检索/来源链已复验；原UAT4隔离MCP令牌已按既有TTL到期；另用临时候选连接完成真实协议检索和来源展开并立即撤销，未更改个人配置或旧连接。

自动生成测试只用deepseek-flash；禁止Claude-opus-5及其他未批准模型、付费子Agent。员工默认gpt-6-luna、个人偏好、千问Embedding/1024维和默认零rerank保持。真实题目、原文、凭据、完整计数、批次及调用收据均只保存在Owner本机私有交付；当前剩余门槛仍包括自然归纳、更多资料质量及Owner人工验收。

## 当前知识专项：HBOS Knowledge UAT5 — 2026-10-15

**UAT5_PARTIAL / LOCAL_UAT / OWNER_NOT_RUN / ROLLOUT_PENDING。** 本轮以真实检索、回答和来源质量为验收依据。已修复跨部门候选汇总、单个异常片段拖垮检索、在线来源/会话续租及问答错误跨页面显示；增加公共法规分类和独立原文下载决策点，原件下载仍关闭。真实回答的自然归纳支持率、更多资料的逐份质量与授权仍有缺口，不能据 CI 或 HTTP200 宣布 READY。

全目录已完成递归哈希盘点、历史身份对账和分阶段质量检查；解析完成与已发布分别计数。仅精确获准且质量通过的子集可发布，个人/保密和授权冲突资料维持待核。测试仅 DeepSeek-Flash，员工默认 GPT-6-luna、原千问 Embedding/维度和默认零 rerank 保持。PR #30 保持 Draft，不合并，不切 P1。

本轮证据范围与剩余门槛见 [UAT5质量候选](milestones/M1_KB_UAT5_检索可靠性与全目录质量候选.md)；详细真实问题、原文、账号、目录和完整漏斗仅留 Owner 本机交付。

## 历史：HBOS Knowledge UAT4 — 2026-10-11

**LOCAL_UAT / REVIEWING / OWNER_NOT_RUN / ROLLOUT_PENDING。** 个人助手入口简化为客户端选择、一次私密安装和最近真实知识使用。状态只在本人连接实际检索并打开同一检索来源后更新；个人 Token 与无凭据使用规则分开存储。已批准的成功资料按精确子集分批发布，完整性未过关的资料保持待核；解析许可不能代替共享许可。原 15 份、UAT2 样式、四回答模型、千问 Embedding 和默认零外部 rerank 保留。

本轮事实、最终统计及制品边界见 [UAT4 验收候选](milestones/M1_KB_UAT4_极简接入与真实资料发布候选.md)；Owner 私有联合锁为数量、运行源码、CI 和 wheel 的最终依据。PR #30 保持 Draft，不合并、不切 P1、不开放正式员工。公司 HTTPS 入口待部署，本机地址仅用于本机 Owner 验收。

## 历史：HBOS Knowledge UAT2 — 2026-10-10

**UAT2_IMPLEMENTATION_CANDIDATE / PROTOTYPE_APPROVED / OWNER_NOT_RUN / ROLLOUT_PENDING。** Owner 已正式批准知识库交互设计 V1，本轮原型审批门禁已满足。知识模块按批准原型完成独立首页、资料目录、本人收藏/记录、六步 MCP 向导和维护员资料/上传/版本/反馈页面；接入原生 Frappe/API，保留 15 份真实共享资料、GPT-6-luna、千问 Embedding、用户权限及关闭原件下载。按两轮截图与实际操作复验，最终运行源码、构建资产和 CI 以本机 Owner 交付联合锁为准。人工产品验收与真实服务器上线是独立 Gate；PR #30 保持 Draft，不合并、不切 P1、不开放全员。

当前记录：[M1-KB-UAT2 完整业务与迁移候选](milestones/M1_KB_UAT2_完整业务与迁移候选.md)。下文 UAT1/N1 的财务阻断和旧终态仅为历史记录，不能覆盖本轮最新要求。PR #30 保持 Draft，P1 与员工开放范围不变。

## HBOS Knowledge UAT-1 当前候选 — 2026-10-10

**PARTIAL / ACCOUNTING_PENDING / LOCAL_UAT / COMPANY_ROLLOUT_PENDING。** 本轮直接实现并装配个人 MCP、页面维护、默认标准检索、有限会话和反馈闭环；未达到完整人工验收放行。旧事件的 Owner 风险例外已按原信封追加，但新增生成未知和在途 embedding 未结算使付费查询、问答、解析暂停，不扩大旧例外。

生产发布 13（原 12 + 本轮 1），人事/安全发布 0；旧 224 解析成功、78 失败保留。MCP 认证/发现/撤销可用；停止前 Hermes 的真实检索/来源通过，OpenClaw 完整问答未通过。维护 UI 的去重、质量、发布、下架/恢复及反馈处理通过，新资料完整解析和换版查询链待补。原生 API/索引不重建，批量 worker 和自动付费测试停止，Owner 1.5 元控制预留留在原两个信封内但当前受对账门槛阻断。

最终标准领域入口 132 项（114 领域 + 18 本地准入）、服务 185 项、前端 148 项分别通过，不能代替功能验收。PR #30 保持 Draft、人工验收前不合并；P1、main、其他 PR 和真实员工范围不改。

当前主记录：[M1-KB-UAT1 完整功能人工验收候选](milestones/M1_KB_UAT1_完整功能人工验收候选.md)；两轮审查和真实缺口在主记录中，以下 N1 / R2 条目为历史记录。

## 历史：HBOS Knowledge N1 夜间候选 — 2026-10-10

状态：N1_PARTIAL_WITH_INDEPENDENT_WORK_COMPLETED / ACCOUNTING_PENDING / LOCAL_CANDIDATE_ONLY。原生 rerank 协议适配进入固定 RAGFlow 的实际模型注册入口；严格校验本请求的索引、分数、usage 和 request_id，其他模型保持原实现。生产参考装配缺原预算绑定时拒绝调用。旧 UNKNOWN 没有结清依据，普通模型调用、旧失败项解析和新资料在线发布继续关闭，不能以离线适配或此前单次成功宣称业务恢复。

本轮完成知识目录的服务端分页及筛选、本人反馈与处理状态、统一搜索/问答输入、一般反馈、历史/收藏上下文重放及多部门明确选择。修复同版本撤权后的旧活动标题泄漏、跨请求身份清理和数据库并发收藏幂等。新资料仅本地准入、身份去重、隔离及冻结计划；真实原文、问题、账号、运行配置和费用证据不进入公共 Git 或开发包。

领域106、本地准入18、独立服务163（原冻结包162项，补充1项）、前端143项合同已运行通过；层级有重叠，不相加，合成测试不代替真实来源/答案质量。最终原生数据库、HTTP、浏览器、远端 CI 和安装制品证据分别在联合交付中核对。PR #30 继续 Draft；只有全部业务、审查、CI、制品和部署边界门槛同时通过才可合入产品分支。此次不切 P1 或开放员工，其他 PR 和 main 不变。


补充复核已完成：独立服务仅增加普通预算双 OS 进程锁入口握手回归，本地提交 `7485bae3073ce11511d7946578329a8090a8574e`；0.3.11 运行源码与原冻结 wheel 逐文件一致，删锁和子进程异常反例独立复核通过。两新目录发现703条路径；本地计划修订技术准入240条、200个新唯一内容，隔离463条。原238/198/465冻结及失败证据保留；修订未上传、入库、质量批准或发布，技术准入不宣称公司业务生效。补充原生 Chrome 键盘操作确认预算拦截，系统中文 IME 候选仍未核验，不能据此称完整在线验收通过。

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

## Portal 产品分支合并后 Gate — 2026-10-01

当前：**PR21_FINAL_REVIEW_PASS / PRODUCT_BRANCH_ACTIVE**。PR #21 已 squash 合入 `feature/hbos-portal-product@e4b16ee80aaaf21aac2304246a4de1f9fe8995ea`；Owner 最新无破坏验收与 Browser final-submit 3/3 已通过，新 squash 四项 CI SUCCESS。旧 #22 已关闭且未合并，IAM-0 由 clean Draft PR #23 单独承接；#15 仍 Open Draft，main 未变化。

下一阶段不再重复 PR #21 的 Owner OAuth、设密/改密/恢复验收。Portal 进入 main 仍需单独 Gate；IAM-0/后续 IAM 实施不因 #21 合并自动完成。

## 账号小范围收尾 — 2026-10-01

本轮接续交付基线 `eee1c5e22c57be3436244e77c65e189bd7eee242` 与 PR #21，仅做资料登录渠道、唯一个人导航、折叠偏好说明、飞书头像同步及 C03/C07/C09/F03 缺项补测；不重新全量审计、重画页面或新增账号功能。真实 Administrator 已成功飞书登录为 USER_CONFIRMED_SUCCESS，绑定、密码、MFA、Secret、企业与回调保留。本机沿用既有 P1 Site/Compose/入口，发布分支不合并、不强推、不推 main/base。 补测确认并修复参与页期限遗漏与 GET 回调未提交记录，原矩阵历史保持；最终浏览器新凭据步骤由工具要求人工接手，团队脚本与未执行状态单列。

## Portal 本轮独立授权

本轮（2026-10-01）接续 PR #21，执行登录账号模块 UI 规范回归与全功能审修。Owner 已亲自确认 Administrator 能通过本人飞书验证并登录，记为 OWNER_CONFIRMED_SUCCESS；历史成员权限待审批或登录失败记录不再代表当前事实。保留真实绑定、密码、MFA、Secret、企业与回调；不要求重复配置。认证页沿用已有 Ant Design Vue / ConfigProvider / typography / tokens，修复表单、证明期限、错误状态、同路由目标与提交结果处理。破坏性、并发与交接只在独立合成 Site 验证。新版本真人 OAuth、本人收到验证码、第二位真人交接与移动软键盘结果单独记录，未执行不写 PASS。复用现有 P1 / Compose / 卷与常用入口，最终本机 SHA/build ID、远端提交、CI 和制品须一致。公司服务器为 NOT_DEPLOYED。主记录：`docs/milestones/M1_RP3_统一账号飞书绑定与正式发布.md`。PR #21 head `codex/portal-unified-account-release`、base `feature/hbos-portal-product`；不强推、不自动合并、不推 main/base。

下述考勤历史轮次的范围不约束已明确授权的 Portal v3；Portal 不替其他业务轮次 closeout。

团队代码已通过 [PR #21](https://github.com/zjl327707743/HBOS-Platform/pull/21) squash 合入 `feature/hbos-portal-product@e4b16ee80aaaf21aac2304246a4de1f9fe8995ea`。P1 继续作为固定本地运行环境；PR #15/main 仍按后续独立 Gate 管理。

## M1-FIX：M1 考勤一期功能补漏阶段

项目名称：新乡海滨智能运营管理平台。

M1 已 closeout 为 COMPLETED，但 Owner 亲自验收后发现大量产品功能没有真正页面可体验——「方案完成」不等于「功能完成」。M1-FIX 阶段定位为功能补漏，补齐 M1 承诺但未实际可体验的产品功能。

## 考勤既有轮次记录

M1-FIX-B2：导入口径、安全与准确性修复。当前状态：COMPLETED。已通过 Claude 审查（初审 FAIL → B2-FIX 复审 PASS），Codex closeout 已完成。

M1-FIX-B3：考勤工作台入口、App 命名与 HRMS 数据一致性修复。当前状态：REVIEWING，等待 Claude 审查。

M1-FIX-B4：考勤模块架构收敛与单一入口重整。当前状态：REVIEWING / Claude PASS，但 Owner 数据链路验收发现后续问题。B4 只收敛桌面入口、Workspace、Workspace Sidebar、导入页和 HBOS / HRMS 入口口径；M1-FIX-B3 不 closeout。

M1-FIX-B5：导入数据链路核查与报表口径收敛。当前状态：REVIEWING，等待 Owner 和 Claude 审查。B5 只核查真实 Employee / Checkin / Attendance / 月度暂存链路，收敛 HBOS 报表和 HRMS 技术核查入口；M1-FIX-B3 / B4 不 closeout。

M1-FIX-B-FIX：Excel 导入与中文体验修复。历史轮次；当前后续修复由 M1-FIX-B2、M1-FIX-B3、M1-FIX-B4、M1-FIX-B5 管理。

M1-FIX 后续规划轮次（仅规划，不自动启动）：

| 轮次 | 名称 | 优先级 | 状态 |
| --- | --- | --- | --- |
| M1-FIX-A | 差距盘点与实施方案 | — | REVIEWING |
| M1-FIX-B | Excel 导入与真实本地数据闭环 | P0 | REVIEWING |
| M1-FIX-B-FIX | Excel 导入与中文体验修复 | P0 | REVIEWING |
| M1-FIX-B2 | 导入口径、安全与准确性修复 | P0 | COMPLETED |
| M1-FIX-B3 | 考勤工作台入口、App 命名与 HRMS 数据一致性修复 | P0 | REVIEWING / Owner UI 验收未通过 |
| M1-FIX-B4 | 考勤模块架构收敛与单一入口重整 | P0 | REVIEWING / Claude PASS，Owner 数据链路验收发现后续问题 |
| M1-FIX-B5 | 导入数据链路核查与报表口径收敛 | P0 | REVIEWING |
| M1-FIX-C | 异常说明三级流程 | P1 | PLANNED |
| M1-FIX-D | 考勤工作台 + 月报 + 领导 Demo | P1 | PLANNED |
| M1-FIX-E | 飞书 OAuth 最小验证 + Owner 体验脚本 + 总审查 | P2 | PLANNED |

## M1 历史轮次（已完成）

M1 规划收口已完成；产品交付仍在 M1-FIX 中，尚未完成。全部 19 个历史轮次状态见里程碑索引。

M0 已完成并封板。M0-REMOTE 已完成。

权威状态文件：

- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/milestones/M0.md`

权威方案文件：

- `docs/milestones/M1_FIX_功能补漏实施方案.md`

## 本轮范围

M1-FIX-B / M1-FIX-B-FIX 只做 Excel 导入与真实本地数据闭环修复：

- 创建轻量 `hb_attendance_app`
- 创建导入日志
- 支持 Owner 在 Frappe Desk 页面上传考勤机月度导出表、识别预览、确认导入、查看导入日志与中文结果
- 创建 / 匹配 Employee
- 生成打卡流水
- 尝试 HRMS 原生自动考勤，并在必要时记录本地兜底生成
- 生成考勤结果并展示导入统计、重复跳过说明和失败摘要
- 默认白班/行政班为 08:30-17:30
- 不提交真实 Excel、真实员工清单或导入产物

## 本轮禁止事项

-- 不创建 `hb_core_app`
-- 不创建 `hb_feishu_app`
-- 不创建月度汇总 DocType
-- 不创建异常三级流程 DocType
- 不创建/删除/清理 TEST 数据
- 不接真实考勤机
- 不配置真实飞书密钥
- 不要求 Owner 在聊天中粘贴 App Secret
- 不提交 `.env`、密钥、token、数据库、日志、缓存、运行产物
- 不修改 Frappe/ERPNext/HRMS 核心源码
- 不启动大型 Vue/React 前端
- 不启动 M2
- 不把「计划可行」写成「功能已实现」

## M1-FIX 全阶段禁止事项

- 不创建 `hb_core_app`
- 不修改 Frappe/ERPNext/HRMS 核心源码
- 不提交 `.env`、App Secret、密钥、token
- 不提交真实员工姓名、真实工号、真实数据
- 不提交 Excel/CSV 数据文件
- 不接真实考勤机
- 不部署公司内网/云服务器
- 不启动大型 Vue/React 前端
- 不启动 M2
- 不伪造飞书登录成功
- 不执行 `docker compose down -v`
- 不删除 Docker volume
- 不重建 `frontend` site

## 当前状态口径

```
M1     = IN_PROGRESS（产品交付，M1-FIX 中）
M1-FIX = IN_PROGRESS
M1-FIX-A = REVIEWING
M1-FIX-B = REVIEWING
M1-FIX-B-FIX = REVIEWING
M1-FIX-B2 = COMPLETED
M1-FIX-B3 = REVIEWING / Owner UI 验收未通过
M1-FIX-B4 = REVIEWING / Claude PASS，Owner 数据链路验收发现后续问题
M1-FIX-B5 = REVIEWING
M2     = NOT STARTED / WAITING OWNER AUTHORIZATION
```

## 下一轮预告

M1-FIX-B5 已进入 REVIEWING，等待 Owner 和 Claude 审查。M1-FIX-B3 / B4 不 closeout。M1-FIX-C（异常说明三级流程）为 PLANNED / 待 Owner 授权。M1-FIX-D/E 与 M2 均未启动。

## 并行产品工作流：HBOS Portal

Owner 已于 2026-09-24 明确授权 HBOS Portal 独立并行启动。

该授权不改变本文件顶部的 M1-FIX 主里程碑。

Portal 当前状态：

```text
EA-1 ~ EA-4 = BASELINE
EA-5 Owner Visual Gate = APPROVED
EA-5.3 = BASELINE
EA-5.4 = DESIGN ENGINEERING BASELINE
EA-5.5 = NEXT
```

正式工作分支：`feature/hbos-portal-product`。

允许范围：
- Portal Experience Architecture 文档；
- 已批准原型复刻；
- Vue 3 + Ant Design Vue Portal Skeleton；
- EA-5.5 响应式 / 可访问性 / 交互 QA。

在后续 Gate 前暂不创建 `apps/hbos_portal`，不接真实业务 Provider。


### Portal Phase B 更新

```text
Phase B — Vue Portal Skeleton
= SOURCE INITIALIZED / BUILD VERIFICATION PENDING
```

已在 `frontend/hbos-portal-web/` 初始化经 Owner 批准视觉母版的 Vue 3 + Ant Design Vue 工程骨架。

本轮仍属于“前端复刻”，没有进入“真实功能接入”。

下一 Gate 保持：

```text
EA-5.5 Interaction QA + Responsive + Accessibility
```

在 build Gate 和 EA-5.5 通过前，不创建 `apps/hbos_portal`。


### EA-5.5 已启动

Portal 并行工作流当前更新为：

```text
EA-5.4 = DESIGN ENGINEERING BASELINE
Vue Portal Skeleton = BUILD PASS
EA-5.5 = IN_PROGRESS
```

EA-5.5 当前只做交互、响应式、可访问性和 LIMS V1 Operational Page 验证，不进入真实 API 功能接入。


### Portal EA-5.5 Gate

```text
EA-5.5 Implementation = PASS
HBOS Quality Gate = PASS
Portal Frontend Build Gate = PASS
Owner Product Review = PENDING
```

在 Owner Review 前，EA-5.5 不标记 COMPLETE，不进入真实 Provider / backend implementation。


### Portal Gate Update — 2026-09-25

EA-5.5 已通过 Owner 验收并收口。

下一允许范围：

- P1 `hbos_portal` Platform App Architecture；
- App Registry / Bootstrap / Session / Access / Provider Discovery 设计；
- 不改变 Attendance / Inventory / LIMS 领域 Authority；
- P1 架构收口前不引入业务事实副本。


### Portal P1 Architecture Gate — 2026-09-25

`docs/experience/P1_HBOS_Portal平台App架构.md` 已形成架构基线。

下一允许范围：P2 `apps/hbos_portal` skeleton；不接三业务 APP Provider，不创建业务事实 DocType。


### Portal P2 Gate Update — 2026-09-25

- `apps/hbos_portal` skeleton 已创建；
- Portal Backend Gate = PASS；
- Vue Frappe Bootstrap Adapter = PASS；
- 下一 Gate = P2.2 Runtime Smoke Test；
- 尚未接三业务 APP Provider。


### Portal P2.2 Runtime Gate — 2026-09-25

```text
P2.2 Runtime Smoke Test = PASS
P3 Business App Registration = NEXT
```

Runtime 使用独立 Portal worktree + 临时 Compose override，正式 `main` Attendance 工作区未 switch / stash / reset / clean。

验证完成后：

- `hbos_portal` 已安全卸载；
- site app list 恢复 baseline；
- 28 个 Docker volume 名称保持一致；
- Attendance bind mount 恢复正式工作区；
- 业务数据未改变。

Attendance hook import warning 为非阻断观察项，留在 Attendance Authority 下后续处理。


### Portal P3-LIMS-1 Gate — 2026-09-25

```text
P3 Business App Registration = IN_PROGRESS
P3-LIMS-1 First Real Provider = COMPLETE
P3-LIMS-2 Stable Deep-link Adapter = NEXT
```

Runtime clean-site 已真实验证 Frappe Hook → Portal Registry → LIMS Access → Bootstrap，且没有开启业务数据 capability。

同轮 Attendance G1 与 LIMS → Inventory release integration 继续 PASS。


### Portal P3-LIMS-2 / P3-LIMS-3 Closeout — 2026-09-25

Portal 分支已先同步最新 `main`（含已合并 PR #20 的 LIMS production-entry 修复），同步后保持：

- LIMS `/hbos-lims/*` 正式入口与持久静态资源能力；
- `hbos_portal_provider` 动态 Provider discovery；
- `hbos_portal` Runtime mount / Registry；
- 三业务 App 原有联合门禁。

P3 当前状态：

```text
P3 Business App Registration = IN_PROGRESS
P3-LIMS-1 Manifest / Access / Registration = COMPLETE
P3-LIMS-2 Stable Deep-link Adapter = COMPLETE / RUNTIME PASS
P3-LIMS-3 My Work Projection = COMPLETE / RUNTIME PASS
P3-LIMS-4 Summary Projection = NEXT
P3-LIMS-5 Search Provider = PLANNED
```

LIMS manifest 当前只开放：

```json
["tasks"]
```

Summary / Search 仍未开放。

P3-LIMS-2 已建立 LIMS internal route → stable `/hbos/lims/...` → current `/hbos-lims/...` 的双向适配，并保持 `hbos_portal` 不静态 import LIMS。

P3-LIMS-3 已复用现有 `todo_service.get_my_todos()` 输出 Unified Task DTO，Portal 不创建第二套 Todo，不持有业务状态，不执行 LIMS 业务动作。

最终 Runtime：

```text
Portal Backend Gate = PASS
Portal Frontend Gate = PASS
HBOS Quality Gate = PASS
Platform Integration Gate run 36042393976 = SUCCESS
HBOS PLATFORM clean-site integration = PASS
```

clean-site 已验证 `lims_manifest_capabilities=["tasks"]`、Stable Route、LIMS task provider 调用、LIMS + Inventory release chain 与 LIMS production entry 共存。


### Portal P3-LIMS-4 / P3-LIMS-5 Closeout — 2026-09-25

LIMS 首个完整 Application Provider experience contract 已完成：

```text
P3-LIMS-1 Manifest / Access / Registration = COMPLETE
P3-LIMS-2 Stable Deep-link Adapter = COMPLETE / RUNTIME PASS
P3-LIMS-3 My Work Projection = COMPLETE / RUNTIME PASS
P3-LIMS-4 Summary Projection = COMPLETE / RUNTIME PASS
P3-LIMS-5 Search Provider = COMPLETE / RUNTIME PASS
```

最终 LIMS manifest：

```json
["summary", "tasks", "search"]
```

最新 clean-site authority：

```text
Head = 7cc1804e4d484feef221ba8b513ec07f036af281
Platform Integration Gate run 36045590049 = SUCCESS
HBOS PLATFORM clean-site integration = PASS
```

Portal 当前下一 Gate：

```text
P3-ATT-1 — Attendance Manifest / Access / Stable Entry
```


### Portal P3 — Three-App Registry Baseline — 2026-09-25

三大业务 APP 已同时进入 Portal Registry：

```text
LIMS
  Manifest / Access / Stable Route = COMPLETE
  Tasks = COMPLETE
  Summary = COMPLETE
  Search = COMPLETE

Attendance
  Manifest / Access / Stable Route = COMPLETE
  HR Summary = COMPLETE
  Tasks / Search = GATED
  Ordinary Employee Portal Access = GATED

Inventory
  Manifest / Access / Stable Route = COMPLETE
  Permission-aware Summary = COMPLETE / RUNTIME PASS
  Tasks / Search = GATED
```

三 APP clean-site Registry authority：

```text
registry_entries = ["attendance", "inventory", "lims"]
registry_failures = 0
bootstrap_apps = ["attendance", "inventory", "lims"]
```

Inventory registration Gate：

```text
run 36048253825 = SUCCESS
```

最新真实数据硬化 HEAD：

```text
f6267baf44813c5b89f83adfe744d8f0192d03bb
```

该版本：
- Frappe mode 不再展示原型期 12/12、7 apps、SAMPLE-001、Digital Twin LIVE 等演示数据；
- 没有 Provider 的模块直接隐藏；
- 多 APP Summary 采用 round-robin 选择，避免一个 APP 独占 Hero 四个指标。

最新 Platform Integration Gate `36048726221` = SUCCESS。

P3 下一阶段从“注册 APP”转为“逐 App 数据能力深化”。


### Portal P3-INV-2 — Inventory Permission-aware Summary — 2026-09-25

状态：**COMPLETE / RUNTIME PASS**。

```text
Inventory manifest = ["summary"]
Inventory Summary metrics = 4
Stable Route = /hbos/inventory -> /app/hbos-photo-intake
Raw-SQL report reuse = NONE
Cross-UOM quantity aggregation = NONE
```

权限链：

```text
Frappe Session
  -> permission-aware visible Warehouse
  -> Bin explicitly scoped to visible Warehouse
  -> Inventory semantic projection
  -> Portal dispatcher
```

Runtime authority：

```text
Inventory real-site first pass:
  Head 3c6f1d5f54a5795d4a7b1ed486c8ce32c64ea7e4
  Platform run 36082817979 = SUCCESS

Portal dispatcher / strict three-app code authority:
  Head ea15676af42e14c2eb47bd65fa402481693b0cac
  Platform run 36083304003
  Three-app clean-site integration step = SUCCESS
```

本地运行工具已加入：

```text
scripts/portal/start_local_workspace.sh
scripts/portal/p3_workspace_runtime_smoke.sh
```

下一 Gate：

```text
Owner local P3 workspace smoke
    ->
P4-F0 real runtime screenshot / journey baseline
    ->
three-app frontend strengthening audit / prototype
```


### Portal P3 Local Isolated Preview Closeout — 2026-09-25

状态：**PASS / P3 RUNTIME CLOSEOUT / P4-F0 READY**。

Owner 本机隔离预览最终通过：

```text
Runtime authority = a6411fadaeccf644a47ffbf93595d00ce9e5b04b
Docker project    = hbos-portal-preview
Preview Site      = portal-preview.localhost
Portal            = http://127.0.0.1:5179
Frappe            = http://127.0.0.1:18091
```

验证完成：

```text
Portal Home                       PASS
App Center                        PASS
My Work                           PASS
Attendance Portal Navigation      PASS
Inventory Portal Navigation       PASS
LIMS Portal Navigation            PASS
Portal native /hbos routes        PASS
Frappe Session across navigation  PASS
Inventory Summary                 PASS
Three-App Registry                PASS
New anonymous volumes             0
Formal workspace                  PRESERVED
Formal Docker runtime             PRESERVED
Formal volumes                    PRESERVED
Formal frontend Site              PRESERVED
```

最终实际落地点：

```text
Attendance -> http://127.0.0.1:18091/desk/hbos-attendance-dashboard
Inventory  -> http://127.0.0.1:18091/desk/hbos-photo-intake
LIMS       -> http://127.0.0.1:18091/hbos-lims/dashboard
```

因此：

```text
P3 Three-App Workspace Integration = COMPLETE / LOCAL + REMOTE RUNTIME PASS
P4-F0 Runtime Screenshot / Journey Baseline = READY
```

P4 开始后仍执行前端 Gate：真实页面审计 → 原型 / 视觉方案 → Owner 审查 → 单 App 实施，不允许三个 App 同时直接大规模改代码。


### UAT5 执行补充：长文档书签校验修复（2026-10-16）

同一真实候选中，一份 PDF 已 DONE 且 39 个片段存在，三个保护身份一致；551 条原生合法书签触发旧 512 条上限，导致误隔离。修复只接纳有界、闭合结构的原生书签（最多4096条、标题总计131072字符），身份差异、未知元数据字段及无效结构继续拒绝。领域检查258项通过；原生已完成任务按状态读取恢复，不重复embedding。

无关资料发布引起进行中查询 SCOPE_REJECTED 的真实前后对照已通过：原授权与来源保持一致，新版为 ALLOWED。Owner 批准的三个非管理员候选账号已定向换密、清除旧会话并更新私有访问文件，偏好/MCP连接/知识历史ID未变。RAGFlow管理窗口已由Owner登录，实际Dataset及文件界面正在核对。整体仍为 UAT5_PARTIAL；PR30保持Draft，不切P1。


### UAT5 执行补充：同源完整索引修复候选（2026-10-16）

5个原失败案例的完整原件与当前索引逐一对照，均证实旧解析分隔配置删除句末标点；只有在诊断中剥离同一组标点后才覆盖100%，该诊断不作质量通过。原件SHA与保护身份均一致。新增同源完整文本索引的封闭校验：父版本、原件SHA、业务版次、文号、标题、权限空间和原Dataset保持一致，原物理索引保留，通过质量检查后由既有replace事务原子更新逻辑文档索引。不得用此路径恢复已撤回资料、改变业务事实或取得新授权。

领域检查263项、独立服务检查438项通过；5个来源的本机实际解析/引用/回答验证仍须完成。当时安装0.6.14的三原失败问答实测：3/3包含原预期来源、11/11来源可重新打开；1/3形成受支持自然回答、2/3仅来源可核验，零系统请求错误。该小样本不替代原73题命中率，也不能宣布UAT5_READY_FOR_OWNER。继续UAT5_PARTIAL、PR30 Draft与本机候选，不切P1。
> **2026-10-29 R6 部门应用权限解释与原型保真 / REVIEWING**：按《HBOS R6 部门应用权限解释与原型保真》单 Agent 任务书，在 #63 定向整改“部门按应用设置默认权限”和“员工按应用单独设置”的页面语义，并对个人中心、员工管理、部门页面、角色与权限、变更记录逐页核对 R6-A2.2 / v1.3 原型。部门页新增固定应用标题与紧凑应用选择、把 LEGACY 兼容状态从第三个灰色单选改为独立状态说明、无修改时不显示取消修改并统一禁用主按钮样式、影响摘要区分服务端可见成员/跟随者/个人安排/实际变化；员工抽屉新增按应用权限总览，考勤兼岗显示“本人考勤”与“明确负责（不含下级）”两个独立范围，未接入应用不绘制为可生效开关。前端 50 文件/466 测试、TypeScript、构建与改动文件 ESLint 通过；未改后端权限合同、未新增授予、不把知识库/LIMS/仓储/生产写成已接入。合成 18191 固定候选、多视口同尺寸对照与 Owner 两条理解回执仍待完成；未合并、未转 Ready、无标签、main 与团队发布。详见统一入口 `R6_DEPARTMENT_SEMANTICS_AND_FIDELITY_20261029.md`。以下按日期保留历史。

> **2026-10-27 · 原型整改代码候选**：员工/部门/个人中心/草稿发布完整流程已重做并完成离线复核：44文件409测试、TypeScript及18个改动文件lint通过。浏览器工具在Owner启用后仍返回禁用，同状态原型复核与新构建真实UAT未通过。TEAM_PULL_READY=BLOCKED，不提交整体验收、不发布。详见本轮主记录末节。

> **2026-10-27 · G3/G4 原型完整性重新实施**：Owner否决753候选的员工应用角色、部门安排、个人中心和角色发布理解体验。按固定R6-A2.2/v1.3补齐完整正式流程，旧接口/权限分项结果不代表整体验收。原生200%仅Owner确认753版本；新候选待测。本地DeepSeek按文件执行A/B/C，总实施Codex统一复核、Git及运行验收。浏览器工具当前禁用，新视觉证据待补；TEAM_PULL_READY=BLOCKED_G3_G4_FIDELITY，未生产上线。

> **G4 分页边界修复（2026-10-27）**：真实浏览器在初次读取前点击分页曾发出page=0并进入400；人员/审计分页现仅接受已加载范围内的正整数页，加载及空态禁用。40文件326测试、typecheck及改动lint通过，须新组合复测。Owner已批准的两项独立后端修复在#65/#66实施，当前测试7a的HR开户/首次改密/关联14项及副作用核验PASS，未合并。TEAM_PULL_READY=PENDING。下列按日期保留历史。

> **G4 抽屉键盘修复待新构建（2026-10-27）**：332的界面建档、20次往返、动效、暂停/deny/停用已有真实证据；Shift+Tab曾跳到背景，局部焦点循环已修并通过325项离线测试，须真实复测。并发鉴权与HR开户两个独立安全修复仍待Owner授权，未应用。

> **G4 继续验收（2026-10-27）**：af0434e 的20项读取/拒绝、38项角色联调及39个CSS视口通过；323前端测试通过。T08草稿切换和T04表单修复待新构建复测；并发鉴权500独立补丁待Owner授权。`TEAM_PULL_READY=PENDING`。

> **G4 隔离联调修复中（2026-10-27）**：旧测试组合 97e0272 实际发现岗位为空、个人中心卡片 top 偏移重叠；前后端各自修复后须新 SHA 构建复测。旧组合不计 G4 PASS，产品仍为 22b47dc，未发布。

# Current Milestone

> **2026-10-27 R6-B / G4_UAT_IN_PROGRESS**：#62 与 #61 已分别按 Owner 精确授权正常 Squash，实际产品基线为 `22b47dcdcc17e8dfd0f0640d2b9a04ec14303b0b`。实际提交四个 CI 作业通过。R6 从该 SHA 的 `feat/hbos-r6b-experience-v1` 实施，固定设计依据 R6-A2.2 / v1.3；G4 真实权限与浏览器验收、G5 独立审查及固定 SHA 合并、G6 统一构建/标签/团队发布尚未完成。`TEAM_PULL_READY=PENDING`，未生产上线。详见 [本轮主记录](milestones/Portal_R6B_正式管理体验与稳定集成.md)。以下按日期保留的旧状态为历史。


> **2026-10-27 #62 旧站点登录兼容修复 / REVIEWING**：Owner 已授权修复旧站点在非试点且关闭自动开户时可能重新开放飞书登录的问题。修复保留该旧关闭语义，并仅在显式试点名单有效时允许关闭自动开户的受控登录；原身份、权限和 proof 合同不变。新增入口及旧回调拒绝负例，Python 3.11/3.12 各 248 项本地测试通过。当前候选尚未部署，最终 GitHub HEAD 的 CI、非作者身份安全审查和固定 HEAD/base 的独立合并授权仍须核对；#61/#62 均未合并，未批准标签或生产发布。历史首通证据见下文。

> **2026-10-26 R5-B 真实首通已核验 / REVIEWING**：产品基线 `1a0d44de1399afca513855f3688eb06c1978429e`。Owner 已本人完成 Administrator 绑定并确认飞书登录；官方回调、企业和在职成员校验成功，真实飞书签发会话的同 User、工作台/IAM/库存/LIMS 读取、原生退出与旧会话重放拒绝已核验，密码登录仍有效，未复制 User/Employee 或新增角色。仅本人 Administrator 试点，自动开户关闭。视觉 Draft #61、认证 Draft #62 均暂缓合并；最终页面/管理员使用验收和专门审查门禁分别记录，不代表生产发布。见 [本轮记录](milestones/Portal_R5B_受控飞书登录候选.md)。以下各日期内容保留历史含义。


## 历史集成状态 — 2026-10-19

**四个完整业务 PR 已实际合并：#42 考勤、#46 生产、#39 仓储、#43 LIMS。** 唯一目标为 `feature/hbos-portal-product`；业务合并基线为 `04e0bb033cb2e7156e407cf49a7b6966b0d2a022`，状态文档在其后维护。[#43](https://github.com/zjl327707743/HBOS-Platform/pull/43) 于 2026-10-19 03:28:29 UTC 正常 Squash Merge；来源、父提交与树见[项目状态](PROJECT_STATUS.md)。

**合并前精确组合：PASS。** [R10 39184807396](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39184807396) 全部 10 jobs SUCCESS，五个原生域与离线／契约／构建在本次 #43 来源和产品基线的真实组合上通过；该组合树与实际 Squash 树相同。

**实际产品合并后回归：PASS。** [R11 39195037712](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39195037712) 全部 10 jobs SUCCESS；五个原生域均直接运行业务合并基线 `04e0bb033cb2e7156e407cf49a7b6966b0d2a022`，无额外 merge，实际单父与树一致，双 migrate 与清理均成功。LIMS 原有 32 项、新增审计 9 项、独立 Todo 1 项合计 42 项原生测试全部通过；Todo 只有 1 项，归属 LIMS。

当前轮次为四项完整业务 PR 的合并后验证与状态收口：#42 → #46 → #39 → #43 均已实际合入唯一产品分支，R11 五个原生域及 LIMS 独立 Todo 1 项补证均通过。当前收口包括状态文档与两处 Python 3.10 测试夹具兼容修复；本收尾 PR 必须在固定候选 SHA 的 Python 3.10／3.12 检查通过后方可合并，实际结果以本 PR 最新 Owner 裁定及最终报告所列 SHA／Job 为准，详见项目状态的独立 CI 事件记录。IAM #52、#37、OCR、真实样本、实体打印及生产 UAT／部署不由本次代码合并 closeout；质量放行撤回未在本轮实现。

业务合并基线与文档保存后的 HEAD 分开记录。Run1–9 的历史失败、未合并及 `NOT_PRODUCT_COMPOSITION` 均按各自日期、来源和作业保留，详见 [PR #56](https://github.com/zjl327707743/HBOS-Platform/pull/56)；最新业务与回归状态以本节和项目状态为准。

### 历史回归 — 2026-10-18 Run8（#39 合并后）

**合并后回归：PASS。** [Run8 39107944012](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39107944012) 全部 8 jobs SUCCESS；四个业务域直接检出实际产品 `a1cc65dde73cfad656faf290264f75fb1a25c32b`，记录 `post_merge_baseline`，源码树为 `43b59653ebbe61db530f523ea980163c88f1899e`、唯一父提交为 `4ddf9bebe5bd9f0d73cdb84bd4ddfa9b8615ad30`。仓储事务 8/8、报表22项HTTP与8项跨仓CSV、卡证权限74/74、考勤原生范围及生产28项检查均通过；所有原生Site双migrate与清理通过。完整来源与后续文档提交见 [PR #56](https://github.com/zjl327707743/HBOS-Platform/pull/56)，不以文档提交后的新HEAD冒充上述已运行提交。

## 验证历史 — 2026-10-18 Run6

[报表、扫码及附件验证](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39103298497/job/117603810152) **74 PASS / 0 FAIL**；[事务验证](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39103298497/job/117603810103) **6 PASS / 2 FAIL**。余两项失败为按单一 URL 误选 Batch File 的测试定位错误，LIMS 放行后两种外发 submit/cancel 仍 **NOT_REACHED**，完整仓储门禁未通过。

## 验证历史 — 2026-10-18 Run5

以下保留 Run5 当时的观察与判断，其中“当前”“尚未通过”“原因待定位”均指该次验证；后续状态以页首“当前集成状态”和实际 PR 记录为准。

当前继续完成 Owner 授权的业务 PR 合并。完整 #42 考勤与 #46 生产已合并，已核对产品为 `4ddf9bebe5bd9f0d73cdb84bd4ddfa9b8615ad30`。[#39 仓储](https://github.com/zjl327707743/HBOS-Platform/pull/39) **尚未合并／技术门禁 FAIL**：Run 5 的扫码与附件权限域 73/74 通过、真实事务域 3/8 场景通过；PDF 正文、注册外协目标放行旁路及完整 LIMS 放行链仍需收口。具体失败、`NOT_REACHED` 和固定 SHA 见 [项目状态](PROJECT_STATUS.md) 与 [#56](https://github.com/zjl327707743/HBOS-Platform/pull/56)，不能用来源分支提交替代产品合并。

下一步在最新仓储来源修复并重跑其真实组合，满足门禁后才 Squash、重读产品 HEAD 并做合并后回归。#43 后置；其独立 39/39 契约与 4 项 mutation 检查通过只记为 `NOT_PRODUCT_COMPOSITION`。本轮不据此完成 M3-R6 的 OCR／实体打印验收，不推进 IAM #52、#37 或生产部署。

## 历史阶段记录

下方较早合并、账号、M1 与 Portal 阶段的“当前”“本轮”和允许范围保留原日期含义，不覆盖页首 R3 授权与验证记录；实际最新来源、验证及合并以 PR #39、PR #56 和远端产品 ref 为准。

> 2026-10-18 生产已完成集成：完整 #42 考勤、#46 生产均已实际合并。最新核对产品为 `4ddf9bebe5bd9f0d73cdb84bd4ddfa9b8615ad30`，来源、审批与原生验证见 [项目状态](PROJECT_STATUS.md)。继续推进 #39 仓储，#43 后置；以下较早产品 SHA 为各阶段历史记录，不替代远端最新 ref。

> 2026-10-18 最新代码集成：**首个完整业务 #42 考勤已实际合并**。产品基线 `374e2bd8633d4127fabcc4659c2314e4a7ca7cd8`，实际父提交 `45658fe4b84d8fb7dd4433c459aa30572e0d13d3`。来源与审批、CI、归档证据见 [PR #42](https://github.com/zjl327707743/HBOS-Platform/pull/42) 和 [项目状态](PROJECT_STATUS.md)。下一顺序为 #46 生产、#39 仓储，#43 LIMS 后置；每项仍以当前 SHA 的权限、运行与审查门禁为准。Owner 承担本批次最终审批，具体方式见 [正式裁定](governance/HBOS_Owner_业务集成批次裁定_20261018.md)。本轮不代表真实环境部署或 IAM #52 完成。

> 历史记录：2026-10-18 物料只读集成窗口：仓储物料只读浏览由 [PR #55](https://github.com/zjl327707743/HBOS-Platform/pull/55) 独立承接；当前代码来源以远端 `feature/hbos-portal-product` 与该 PR 实际合并 SHA 为准。下方 PR #21 的 SHA/账号验收是历史记录，不代表最新产品 HEAD。完整业务 #42/#43/#46/#39 和 IAM #52 各自保留独立门禁；本轮不安装或部署真实环境。

## Portal 产品分支合并后 Gate — 2026-10-01

当前：**PR21_FINAL_REVIEW_PASS / PRODUCT_BRANCH_ACTIVE**。PR #21 已 squash 合入 `feature/hbos-portal-product@e4b16ee80aaaf21aac2304246a4de1f9fe8995ea`；Owner 最新无破坏验收与 Browser final-submit 3/3 已通过，新 squash 四项 CI SUCCESS。旧 #22 已关闭且未合并，IAM-0 由 clean Draft PR #23 单独承接；#15 仍 Open Draft，main 未变化。

下一阶段不再重复 PR #21 的 Owner OAuth、设密/改密/恢复验收。Portal 进入 main 仍需单独 Gate；IAM-0/后续 IAM 实施不因 #21 合并自动完成。

## 账号小范围收尾 — 2026-10-01

本轮接续交付基线 `eee1c5e22c57be3436244e77c65e189bd7eee242` 与 PR #21，仅做资料登录渠道、唯一个人导航、折叠偏好说明、飞书头像同步及 C03/C07/C09/F03 缺项补测；不重新全量审计、重画页面或新增账号功能。真实 Administrator 已成功飞书登录为 USER_CONFIRMED_SUCCESS，绑定、密码、MFA、Secret、企业与回调保留。本机沿用既有 P1 Site/Compose/入口，发布分支不合并、不强推、不推 main/base。 补测确认并修复参与页期限遗漏与 GET 回调未提交记录，原矩阵历史保持；最终浏览器新凭据步骤由工具要求人工接手，团队脚本与未执行状态单列。


## Portal 本轮独立授权

本轮（2026-10-01）接续 PR #21，执行登录账号模块 UI 规范回归与全功能审修。Owner 已亲自确认 Administrator 能通过本人飞书验证并登录，记为 OWNER_CONFIRMED_SUCCESS；历史成员权限待审批或登录失败记录不再代表当前事实。保留真实绑定、密码、MFA、Secret、企业与回调；不要求重复配置。认证页沿用已有 Ant Design Vue / ConfigProvider / typography / tokens，修复表单、证明期限、错误状态、同路由目标与提交结果处理。破坏性、并发与交接只在独立合成 Site 验证。新版本真人 OAuth、本人收到验证码、第二位真人交接与移动软键盘结果单独记录，未执行不写 PASS。复用现有 P1 / Compose / 卷与常用入口，最终本机 SHA/build ID、远端提交、CI 和制品须一致。公司服务器为 NOT_DEPLOYED。主记录：`docs/milestones/M1_RP3_统一账号飞书绑定与正式发布.md`。PR #21 head `codex/portal-unified-account-release`、base `feature/hbos-portal-product`；不强推、不自动合并、不推 main/base。

下述考勤历史轮次的范围不约束已明确授权的 Portal v3；Portal 不替其他业务轮次 closeout。

团队代码已通过 [PR #21](https://github.com/zjl327707743/HBOS-Platform/pull/21) squash 合入 `feature/hbos-portal-product@e4b16ee80aaaf21aac2304246a4de1f9fe8995ea`。P1 继续作为固定本地运行环境；PR #15/main 仍按后续独立 Gate 管理。

## M1-FIX：M1 考勤一期功能补漏阶段

项目名称：新乡海滨智能运营管理平台。

M1 已 closeout 为 COMPLETED，但 Owner 亲自验收后发现大量产品功能没有真正页面可体验——「方案完成」不等于「功能完成」。M1-FIX 阶段定位为功能补漏，补齐 M1 承诺但未实际可体验的产品功能。

## 考勤既有轮次记录

M1-FIX-B2：导入口径、安全与准确性修复。当前状态：COMPLETED。已通过 Claude 审查（初审 FAIL → B2-FIX 复审 PASS），Codex closeout 已完成。

M1-FIX-B3：考勤工作台入口、App 命名与 HRMS 数据一致性修复。当前状态：REVIEWING，等待 Claude 审查。

M1-FIX-B4：考勤模块架构收敛与单一入口重整。当前状态：REVIEWING / Claude PASS，但 Owner 数据链路验收发现后续问题。B4 只收敛桌面入口、Workspace、Workspace Sidebar、导入页和 HBOS / HRMS 入口口径；M1-FIX-B3 不 closeout。

M1-FIX-B5：导入数据链路核查与报表口径收敛。当前状态：REVIEWING，等待 Owner 和 Claude 审查。B5 只核查真实 Employee / Checkin / Attendance / 月度暂存链路，收敛 HBOS 报表和 HRMS 技术核查入口；M1-FIX-B3 / B4 不 closeout。

M1-FIX-B-FIX：Excel 导入与中文体验修复。历史轮次；当前后续修复由 M1-FIX-B2、M1-FIX-B3、M1-FIX-B4、M1-FIX-B5 管理。

M1-FIX 后续规划轮次（仅规划，不自动启动）：

| 轮次 | 名称 | 优先级 | 状态 |
| --- | --- | --- | --- |
| M1-FIX-A | 差距盘点与实施方案 | — | REVIEWING |
| M1-FIX-B | Excel 导入与真实本地数据闭环 | P0 | REVIEWING |
| M1-FIX-B-FIX | Excel 导入与中文体验修复 | P0 | REVIEWING |
| M1-FIX-B2 | 导入口径、安全与准确性修复 | P0 | COMPLETED |
| M1-FIX-B3 | 考勤工作台入口、App 命名与 HRMS 数据一致性修复 | P0 | REVIEWING / Owner UI 验收未通过 |
| M1-FIX-B4 | 考勤模块架构收敛与单一入口重整 | P0 | REVIEWING / Claude PASS，Owner 数据链路验收发现后续问题 |
| M1-FIX-B5 | 导入数据链路核查与报表口径收敛 | P0 | REVIEWING |
| M1-FIX-C | 异常说明三级流程 | P1 | PLANNED |
| M1-FIX-D | 考勤工作台 + 月报 + 领导 Demo | P1 | PLANNED |
| M1-FIX-E | 飞书 OAuth 最小验证 + Owner 体验脚本 + 总审查 | P2 | PLANNED |

## M1 历史轮次（已完成）

M1 规划收口已完成；产品交付仍在 M1-FIX 中，尚未完成。全部 19 个历史轮次状态见里程碑索引。

M0 已完成并封板。M0-REMOTE 已完成。

权威状态文件：

- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/milestones/M0.md`

权威方案文件：

- `docs/milestones/M1_FIX_功能补漏实施方案.md`

## 本轮范围

M1-FIX-B / M1-FIX-B-FIX 只做 Excel 导入与真实本地数据闭环修复：

- 创建轻量 `hb_attendance_app`
- 创建导入日志
- 支持 Owner 在 Frappe Desk 页面上传考勤机月度导出表、识别预览、确认导入、查看导入日志与中文结果
- 创建 / 匹配 Employee
- 生成打卡流水
- 尝试 HRMS 原生自动考勤，并在必要时记录本地兜底生成
- 生成考勤结果并展示导入统计、重复跳过说明和失败摘要
- 默认白班/行政班为 08:30-17:30
- 不提交真实 Excel、真实员工清单或导入产物

## 本轮禁止事项

-- 不创建 `hb_core_app`
-- 不创建 `hb_feishu_app`
-- 不创建月度汇总 DocType
-- 不创建异常三级流程 DocType
- 不创建/删除/清理 TEST 数据
- 不接真实考勤机
- 不配置真实飞书密钥
- 不要求 Owner 在聊天中粘贴 App Secret
- 不提交 `.env`、密钥、token、数据库、日志、缓存、运行产物
- 不修改 Frappe/ERPNext/HRMS 核心源码
- 不启动大型 Vue/React 前端
- 不启动 M2
- 不把「计划可行」写成「功能已实现」

## M1-FIX 全阶段禁止事项

- 不创建 `hb_core_app`
- 不修改 Frappe/ERPNext/HRMS 核心源码
- 不提交 `.env`、App Secret、密钥、token
- 不提交真实员工姓名、真实工号、真实数据
- 不提交 Excel/CSV 数据文件
- 不接真实考勤机
- 不部署公司内网/云服务器
- 不启动大型 Vue/React 前端
- 不启动 M2
- 不伪造飞书登录成功
- 不执行 `docker compose down -v`
- 不删除 Docker volume
- 不重建 `frontend` site

## 当前状态口径

```
M1     = IN_PROGRESS（产品交付，M1-FIX 中）
M1-FIX = IN_PROGRESS
M1-FIX-A = REVIEWING
M1-FIX-B = REVIEWING
M1-FIX-B-FIX = REVIEWING
M1-FIX-B2 = COMPLETED
M1-FIX-B3 = REVIEWING / Owner UI 验收未通过
M1-FIX-B4 = REVIEWING / Claude PASS，Owner 数据链路验收发现后续问题
M1-FIX-B5 = REVIEWING
M2     = NOT STARTED / WAITING OWNER AUTHORIZATION
```

## 下一轮预告

M1-FIX-B5 已进入 REVIEWING，等待 Owner 和 Claude 审查。M1-FIX-B3 / B4 不 closeout。M1-FIX-C（异常说明三级流程）为 PLANNED / 待 Owner 授权。M1-FIX-D/E 与 M2 均未启动。


## 并行产品工作流：HBOS Portal

Owner 已于 2026-09-24 明确授权 HBOS Portal 独立并行启动。

该授权不改变本文件顶部的 M1-FIX 主里程碑。

Portal 当前状态：

```text
EA-1 ~ EA-4 = BASELINE
EA-5 Owner Visual Gate = APPROVED
EA-5.3 = BASELINE
EA-5.4 = DESIGN ENGINEERING BASELINE
EA-5.5 = NEXT
```

正式工作分支：`feature/hbos-portal-product`。

允许范围：
- Portal Experience Architecture 文档；
- 已批准原型复刻；
- Vue 3 + Ant Design Vue Portal Skeleton；
- EA-5.5 响应式 / 可访问性 / 交互 QA。

在后续 Gate 前暂不创建 `apps/hbos_portal`，不接真实业务 Provider。


### Portal Phase B 更新

```text
Phase B — Vue Portal Skeleton
= SOURCE INITIALIZED / BUILD VERIFICATION PENDING
```

已在 `frontend/hbos-portal-web/` 初始化经 Owner 批准视觉母版的 Vue 3 + Ant Design Vue 工程骨架。

本轮仍属于“前端复刻”，没有进入“真实功能接入”。

下一 Gate 保持：

```text
EA-5.5 Interaction QA + Responsive + Accessibility
```

在 build Gate 和 EA-5.5 通过前，不创建 `apps/hbos_portal`。


### EA-5.5 已启动

Portal 并行工作流当前更新为：

```text
EA-5.4 = DESIGN ENGINEERING BASELINE
Vue Portal Skeleton = BUILD PASS
EA-5.5 = IN_PROGRESS
```

EA-5.5 当前只做交互、响应式、可访问性和 LIMS V1 Operational Page 验证，不进入真实 API 功能接入。


### Portal EA-5.5 Gate

```text
EA-5.5 Implementation = PASS
HBOS Quality Gate = PASS
Portal Frontend Build Gate = PASS
Owner Product Review = PENDING
```

在 Owner Review 前，EA-5.5 不标记 COMPLETE，不进入真实 Provider / backend implementation。


### Portal Gate Update — 2026-09-25

EA-5.5 已通过 Owner 验收并收口。

下一允许范围：

- P1 `hbos_portal` Platform App Architecture；
- App Registry / Bootstrap / Session / Access / Provider Discovery 设计；
- 不改变 Attendance / Inventory / LIMS 领域 Authority；
- P1 架构收口前不引入业务事实副本。


### Portal P1 Architecture Gate — 2026-09-25

`docs/experience/P1_HBOS_Portal平台App架构.md` 已形成架构基线。

下一允许范围：P2 `apps/hbos_portal` skeleton；不接三业务 APP Provider，不创建业务事实 DocType。


### Portal P2 Gate Update — 2026-09-25

- `apps/hbos_portal` skeleton 已创建；
- Portal Backend Gate = PASS；
- Vue Frappe Bootstrap Adapter = PASS；
- 下一 Gate = P2.2 Runtime Smoke Test；
- 尚未接三业务 APP Provider。


### Portal P2.2 Runtime Gate — 2026-09-25

```text
P2.2 Runtime Smoke Test = PASS
P3 Business App Registration = NEXT
```

Runtime 使用独立 Portal worktree + 临时 Compose override，正式 `main` Attendance 工作区未 switch / stash / reset / clean。

验证完成后：

- `hbos_portal` 已安全卸载；
- site app list 恢复 baseline；
- 28 个 Docker volume 名称保持一致；
- Attendance bind mount 恢复正式工作区；
- 业务数据未改变。

Attendance hook import warning 为非阻断观察项，留在 Attendance Authority 下后续处理。


### Portal P3-LIMS-1 Gate — 2026-09-25

```text
P3 Business App Registration = IN_PROGRESS
P3-LIMS-1 First Real Provider = COMPLETE
P3-LIMS-2 Stable Deep-link Adapter = NEXT
```

Runtime clean-site 已真实验证 Frappe Hook → Portal Registry → LIMS Access → Bootstrap，且没有开启业务数据 capability。

同轮 Attendance G1 与 LIMS → Inventory release integration 继续 PASS。


### Portal P3-LIMS-2 / P3-LIMS-3 Closeout — 2026-09-25

Portal 分支已先同步最新 `main`（含已合并 PR #20 的 LIMS production-entry 修复），同步后保持：

- LIMS `/hbos-lims/*` 正式入口与持久静态资源能力；
- `hbos_portal_provider` 动态 Provider discovery；
- `hbos_portal` Runtime mount / Registry；
- 三业务 App 原有联合门禁。

P3 当前状态：

```text
P3 Business App Registration = IN_PROGRESS
P3-LIMS-1 Manifest / Access / Registration = COMPLETE
P3-LIMS-2 Stable Deep-link Adapter = COMPLETE / RUNTIME PASS
P3-LIMS-3 My Work Projection = COMPLETE / RUNTIME PASS
P3-LIMS-4 Summary Projection = NEXT
P3-LIMS-5 Search Provider = PLANNED
```

LIMS manifest 当前只开放：

```json
["tasks"]
```

Summary / Search 仍未开放。

P3-LIMS-2 已建立 LIMS internal route → stable `/hbos/lims/...` → current `/hbos-lims/...` 的双向适配，并保持 `hbos_portal` 不静态 import LIMS。

P3-LIMS-3 已复用现有 `todo_service.get_my_todos()` 输出 Unified Task DTO，Portal 不创建第二套 Todo，不持有业务状态，不执行 LIMS 业务动作。

最终 Runtime：

```text
Portal Backend Gate = PASS
Portal Frontend Gate = PASS
HBOS Quality Gate = PASS
Platform Integration Gate run 36042393976 = SUCCESS
HBOS PLATFORM clean-site integration = PASS
```

clean-site 已验证 `lims_manifest_capabilities=["tasks"]`、Stable Route、LIMS task provider 调用、LIMS + Inventory release chain 与 LIMS production entry 共存。


### Portal P3-LIMS-4 / P3-LIMS-5 Closeout — 2026-09-25

LIMS 首个完整 Application Provider experience contract 已完成：

```text
P3-LIMS-1 Manifest / Access / Registration = COMPLETE
P3-LIMS-2 Stable Deep-link Adapter = COMPLETE / RUNTIME PASS
P3-LIMS-3 My Work Projection = COMPLETE / RUNTIME PASS
P3-LIMS-4 Summary Projection = COMPLETE / RUNTIME PASS
P3-LIMS-5 Search Provider = COMPLETE / RUNTIME PASS
```

最终 LIMS manifest：

```json
["summary", "tasks", "search"]
```

最新 clean-site authority：

```text
Head = 7cc1804e4d484feef221ba8b513ec07f036af281
Platform Integration Gate run 36045590049 = SUCCESS
HBOS PLATFORM clean-site integration = PASS
```

Portal 当前下一 Gate：

```text
P3-ATT-1 — Attendance Manifest / Access / Stable Entry
```


### Portal P3 — Three-App Registry Baseline — 2026-09-25

三大业务 APP 已同时进入 Portal Registry：

```text
LIMS
  Manifest / Access / Stable Route = COMPLETE
  Tasks = COMPLETE
  Summary = COMPLETE
  Search = COMPLETE

Attendance
  Manifest / Access / Stable Route = COMPLETE
  HR Summary = COMPLETE
  Tasks / Search = GATED
  Ordinary Employee Portal Access = GATED

Inventory
  Manifest / Access / Stable Route = COMPLETE
  Permission-aware Summary = COMPLETE / RUNTIME PASS
  Tasks / Search = GATED
```

三 APP clean-site Registry authority：

```text
registry_entries = ["attendance", "inventory", "lims"]
registry_failures = 0
bootstrap_apps = ["attendance", "inventory", "lims"]
```

Inventory registration Gate：

```text
run 36048253825 = SUCCESS
```

最新真实数据硬化 HEAD：

```text
f6267baf44813c5b89f83adfe744d8f0192d03bb
```

该版本：
- Frappe mode 不再展示原型期 12/12、7 apps、SAMPLE-001、Digital Twin LIVE 等演示数据；
- 没有 Provider 的模块直接隐藏；
- 多 APP Summary 采用 round-robin 选择，避免一个 APP 独占 Hero 四个指标。

最新 Platform Integration Gate `36048726221` = SUCCESS。

P3 下一阶段从“注册 APP”转为“逐 App 数据能力深化”。


### Portal P3-INV-2 — Inventory Permission-aware Summary — 2026-09-25

状态：**COMPLETE / RUNTIME PASS**。

```text
Inventory manifest = ["summary"]
Inventory Summary metrics = 4
Stable Route = /hbos/inventory -> /app/hbos-photo-intake
Raw-SQL report reuse = NONE
Cross-UOM quantity aggregation = NONE
```

权限链：

```text
Frappe Session
  -> permission-aware visible Warehouse
  -> Bin explicitly scoped to visible Warehouse
  -> Inventory semantic projection
  -> Portal dispatcher
```

Runtime authority：

```text
Inventory real-site first pass:
  Head 3c6f1d5f54a5795d4a7b1ed486c8ce32c64ea7e4
  Platform run 36082817979 = SUCCESS

Portal dispatcher / strict three-app code authority:
  Head ea15676af42e14c2eb47bd65fa402481693b0cac
  Platform run 36083304003
  Three-app clean-site integration step = SUCCESS
```

本地运行工具已加入：

```text
scripts/portal/start_local_workspace.sh
scripts/portal/p3_workspace_runtime_smoke.sh
```

下一 Gate：

```text
Owner local P3 workspace smoke
    ->
P4-F0 real runtime screenshot / journey baseline
    ->
three-app frontend strengthening audit / prototype
```


### Portal P3 Local Isolated Preview Closeout — 2026-09-25

状态：**PASS / P3 RUNTIME CLOSEOUT / P4-F0 READY**。

Owner 本机隔离预览最终通过：

```text
Runtime authority = a6411fadaeccf644a47ffbf93595d00ce9e5b04b
Docker project    = hbos-portal-preview
Preview Site      = portal-preview.localhost
Portal            = http://127.0.0.1:5179
Frappe            = http://127.0.0.1:18091
```

验证完成：

```text
Portal Home                       PASS
App Center                        PASS
My Work                           PASS
Attendance Portal Navigation      PASS
Inventory Portal Navigation       PASS
LIMS Portal Navigation            PASS
Portal native /hbos routes        PASS
Frappe Session across navigation  PASS
Inventory Summary                 PASS
Three-App Registry                PASS
New anonymous volumes             0
Formal workspace                  PRESERVED
Formal Docker runtime             PRESERVED
Formal volumes                    PRESERVED
Formal frontend Site              PRESERVED
```

最终实际落地点：

```text
Attendance -> http://127.0.0.1:18091/desk/hbos-attendance-dashboard
Inventory  -> http://127.0.0.1:18091/desk/hbos-photo-intake
LIMS       -> http://127.0.0.1:18091/hbos-lims/dashboard
```

因此：

```text
P3 Three-App Workspace Integration = COMPLETE / LOCAL + REMOTE RUNTIME PASS
P4-F0 Runtime Screenshot / Journey Baseline = READY
```

P4 开始后仍执行前端 Gate：真实页面审计 → 原型 / 视觉方案 → Owner 审查 → 单 App 实施，不允许三个 App 同时直接大规模改代码。
