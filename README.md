# 新乡海滨智能运营管理平台

## HBOS Knowledge R2.1 — 2026-10-09

状态：PARTIAL / EXISTING_CORPUS_RETRIEVAL_RESTORED / NOT_RELEASED。继续 Draft PR #30 与同一候选。Owner 已确认额度恢复、允许按量付费并批准本轮累计预算；准确审批和费用只在 Owner 私有层留存。本轮优先恢复原 embedding，备用模型不作为前置测试，不自动切换模型、Key、provider 或混写旧索引。敏感草稿继续排除。

原 12 份资料已完成实际召回与来源核验；历史和收藏已重新检索，跨用户打开被拒绝。只读数据库逐字段对比确认原 49 条活动、7 个用户指纹及原文档、版本、绑定均保留。当前窗口只显示最近 30 条历史，不能据窗口缺项断言记录删除。另已完成一个原代表问答，分别记录检索、rerank 和生成的真实响应用量；不将该抽样写为整批问答验收。

303 个冻结项、302 份上传保持；本次恢复起点为成功 220、失败 82、重复跳过 1、新发布 0。220 份成功资料已建立只读索引哈希基线，保留既有物理身份。本轮先对最多 4 份失败项试跑，确认成功后在同一批准预算内按最多 4 份连续分组；无需每组重新批准。未知状态先 reconcile，硬额度、预算不足或无法核实用量停止新增调用并保留收据。

独立服务 0.3.8 增加显式请求收据和实际 provider usage 计量、在途费用预留、在线预留与费用估算上限；源字符只用于分组。账单金额和账户余额未获取时保持 UNKNOWN。固定 v0.27 的已关闭 Raptor/GraphRAG 会补充默认配置，恢复校验接受未使用的补充参数，仍拒绝重新启用或修改已批准字段；不改写冻结清单或实际解析设置。首组预检曾因此停止，已证明未入队、未调用模型后修复，不能把这次预检写为试跑成功。

领域 76、服务 81、前端 89、原核心 207 项分别通过，范围不相加。原生发布 10 项和此前 Chrome 阻塞期间可用性 18 项作为已验证历史保留；新资料逐项召回、必要问答、实际候选发布及恢复后的前端验收继续推进。只有质量通过的精确子集可发布，部分发布、CI 或解析成功均不能代替 R2.1 整批验收。普通发布不恢复下架或指回旧版本；replace/restore 继续独立批准。冻结 batch/items 与不可变收据保持。

配置状态与业务可用性分开，页面状态读取不调用模型，成功观察过期为 UNKNOWN；深链接仅预填。公共仓库和开发包不含真实目录、题目、摘录、账户、对象 ID、模型配置、账单或审批。详情见 `docs/milestones/M1_KB_R2_1_增量入库与多部门验收.md`。不合并、不切换 P1。以下 R2/R1 保留为历史记录。

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

## 并行权限治理 IAM-0 — 2026-10-01

Owner 已批准进入统一身份与权限治理。当前仅交付设计、角色—动作—范围矩阵、只读源码盘点工具与本机任务书；实际 Site 盘点和隔离验收仍为 NOT_RUN，不修改账号、角色或业务数据，不替代原账号收尾。入口：[IAM-0 治理资料](docs/governance/iam/README.md)。

最新产品基线：PR #21 已在 FINAL_REVIEW_PASS 后 squash 合入 `feature/hbos-portal-product`，产品 HEAD `e4b16ee80aaaf21aac2304246a4de1f9fe8995ea`。Owner 最新无破坏验收 PASS、浏览器设密/改密/恢复 final-submit 3/3 PASS，新 squash 四项 CI SUCCESS。IAM-0 已由 clean Draft PR #23 承接，旧 #22 已关闭且未合并；PR #15 仍为 Draft，main 未变化。[当前 Gate](docs/milestones/M1_RP3_统一账号飞书绑定与正式发布.md) 记录本轮收口事实。

Frappe/ERPNext 开源底座 + Frappe 多 App 模块化架构 + 外部独立服务扩展。

## 当前交付

本轮（2026-10-01）接续 PR #21，执行登录账号模块 UI 规范回归与全功能审修。Owner 已亲自确认 Administrator 能通过本人飞书验证并登录，记为 OWNER_CONFIRMED_SUCCESS；历史成员权限待审批或登录失败记录不再代表当前事实。保留真实绑定、密码、MFA、Secret、企业与回调；不要求重复配置。认证页沿用已有 Ant Design Vue / ConfigProvider / typography / tokens，修复表单、证明期限、错误状态、同路由目标与提交结果处理。破坏性、并发与交接只在独立合成 Site 验证。新版本真人 OAuth、本人收到验证码、第二位真人交接与移动软键盘结果单独记录，未执行不写 PASS。复用现有 P1 / Compose / 卷与常用入口，最终本机 SHA/build ID、远端提交、CI 和制品须一致。公司服务器为 NOT_DEPLOYED。主记录：`docs/milestones/M1_RP3_统一账号飞书绑定与正式发布.md`。PR #21 已 squash 合入 `feature/hbos-portal-product@e4b16ee80aaaf21aac2304246a4de1f9fe8995ea`；团队后续 Portal 代码以产品分支为准。PR #15 仍 Draft，不推 main；IAM 由 Draft PR #23 单独承接。

平台已包含考勤、仓储库存、LIMS、Portal、知识助理与设备/数字孪生自定义 App。密码和飞书使用同一 Frappe User；原有业务权限仍由原 App 约束。业务通知、现场遥测、工艺动画及偏好同步尚未实现；内部参考知识回答在 R2 独立候选实现，具体状态见前端完整性矩阵。安全变更通知单独记录真实发送状态，不能等同业务通知能力完成。

- [项目状态](docs/PROJECT_STATUS.md)
- [当前里程碑](docs/CURRENT_MILESTONE.md)
- [Mac 常用启动与团队同步](docs/deployment/Mac本地运行与团队同步.md)
- [团队部署、备份与回退](docs/deployment/统一账号与Portal正式部署说明.md)
- [前端完整性矩阵](docs/frontend/统一账号发布与前端完整性矩阵.md)

## 团队构建

在已审查的 clean checkout 使用 Node 22 执行 `bash scripts/release/build_bundle.sh`，生成同源 Portal 和 LIMS 编译资产及六 App 部署包。通用 Gateway 位于 `services/hbos_gateway`，依赖、基线与 HRMS commit 见 `scripts/release/依赖版本锁.json`。既有目标版本不得为了匹配基线而降级。

升级必须保留已确认原 Site/数据库，先备份并验证恢复，再迁移及核对原账号/角色/权限/业务关联。制品或 PR 不包含账号数据库、Secret、私有知识索引/原文或真实模型；这些经批准私下部署。

## 协作与边界

`AGENTS.md`、`CLAUDE.md` 为规则入口；进度以状态台账与对应里程碑为准。Portal 本轮不改变其他考勤/库存里程碑的 Owner 验收状态。禁止创建未知替代库、覆盖未知数据库、重置原密码/角色、发布凭据或私有资料。

团队后续 Portal 代码来源：`feature/hbos-portal-product@e4b16ee80aaaf21aac2304246a4de1f9fe8995ea`。PR #21 保留为已合并的审查与发布证据；Mac 本地运行与本人验收分开记录，公司生产尚未部署。
