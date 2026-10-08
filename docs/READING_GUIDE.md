# Reading Guide

## HBOS Knowledge R2.1 — 2026-10-08

状态：PARTIAL / BLOCKED_EMBEDDING_QUOTA / NOT_RELEASED。承接 Draft PR #30 与现有 R2 候选。事务性发布前进约束、独立 replace/restore 意图与不可变收据已落地，原生数据库反例和真实旧批次 12 项 NOOP 重放通过。

新冻结批次实际上传 302 份，220 份解析成功、82 份因获准 embedding provider 额度耗尽而失败，1 份同内容重复跳过，新发布 0 份。已成功内容和原 12 份资料、用户历史/收藏/反馈均保留。额度问题同时阻塞现有资料的在线检索，登录、目录与历史仍可读；不能将解析成功等同于召回、答案或发布验收通过。

稳定身份、精确部门 Dataset 映射、有界多部门计划/元数据分页、目录文本筛选与 12 项分页已实现。独立服务 0.3.4 本地提交及 wheel 单独固定。核心 207、领域 68、服务 39、前端 85 项分别通过，真实响应式浏览器 10 项通过；多部门在线检索、新资料问答/引用与相应 UI 流程 BLOCKED。真实资料、问题、截图、准确 ID、备份及恢复工具仅在 Owner 私有层。详情见 `docs/milestones/M1_KB_R2_1_增量入库与多部门验收.md`。不改变模型/付费策略，不合并、不切换 P1。以下 R2/R1 为历史记录。

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

## 默认读取文件

每轮任务默认只读：

- `CLAUDE.md`
- `AGENTS.md`
- `docs/AI_CONTEXT.md`
- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`

每轮任务开始前必须说明读取了哪些文档。

## 禁止默认递归读取

禁止默认递归读取整个 `docs/`。

默认不读取以下目录：

- `docs/archive`
- `docs/research`
- `docs/legacy`

除非用户明确要求，否则不要浏览或搬运大量 Obsidian 长文。

## 公共入口文件收尾检查规则

默认读取规则不变。

每轮收尾审查可读取以下公共入口文件：

- `README.md`
- `CLAUDE.md`
- `AGENTS.md`
- `docs/AI_CONTEXT.md`
- `docs/READING_GUIDE.md`
- `docs/frontend/FRONTEND_IMPLEMENTATION_GUIDE.md`（仅前端相关轮次）

此外，每轮收尾还必须检查：

- 当前阶段门禁文档：M1 阶段为 `docs/milestones/M1_START_GATE.md`，未来 M2/M3 阶段分别为 `docs/milestones/M2_START_GATE.md`、`docs/milestones/M3_START_GATE.md`。阶段门禁文档用于记录当前阶段的目标、边界、门禁、子轮次状态和下一步路线。
- 当前轮次主文档：指本轮实际交付的 `docs/milestones/Mx_Ry_*.md` 文档，例如 `docs/milestones/M1_R3F_业务口径确认包.md`。每轮进入 REVIEWING 或 closeout 时，必须同步更新该轮次主文档状态。

这些文件不一定每轮修改，但必须检查是否存在过期阶段描述。检查公共入口文件不等于允许递归读取整个 `docs/`。

## 条件读取规则

只有任务明确涉及当前里程碑时，才读取：

- `docs/plans/m0_engineering_bootstrap.md`

只有任务涉及独立前端开发、驾驶舱、AI 工作台或复杂交互页面时，才读取：

- `docs/frontend/FRONTEND_IMPLEMENTATION_GUIDE.md`

## 里程碑文件读取规则

- 默认不全量读取 `docs/milestones/`。
- 当前里程碑任务可读取对应文件，例如 M0 任务读取 `docs/milestones/M0.md`。
- `docs/milestones/README.md` 可作为里程碑索引读取。
- 每轮任务收尾时，如项目状态、当前轮次或里程碑状态发生变化，必须同步更新对应里程碑文件。

M0 历史任务曾允许读取：

- `docs/plans/M0-R2_Frappe_Docker最小环境方案设计.md`
- `docs/deployment/Frappe_Docker最小部署设计.md`
- `docs/deployment/本地开发环境变量说明.md`

## Skill 路由读取规则

- `docs/AI技能路由规范.md` 仅在涉及 Skill、Agent 调度、飞书 skill 选择或相关审查时读取。
- 不因存在 Skill 路由文档而默认全量读取 `docs/`。
- 不因存在飞书 skill 而默认执行飞书真实写入。

只有架构决策变更时，才读取：

- `docs/adr/`

## 既有里程碑背景（不覆盖当前 RP3）

当前 M0 已完成并封板，M0-REMOTE 已完成，M1-R0 已完成并通过 Codex 独立审查，M1-R1 已完成 HRMS 原生考勤对象模型验证记录并收口为 COMPLETED，M1-R2 已完成 HRMS 原生考勤配置试运行方案并通过 Codex 独立审查收口为 COMPLETED。M1-R3 已执行 HRMS 原生考勤最小测试数据试运行并通过 Codex 审查，实际结论为 PARTIAL / BLOCKED，最终状态收口为 BLOCKED：部分 TEST 数据已落库，14 个打卡场景未完成闭环验证。M1-R3A 已完成运行态阻断诊断与 TEST 数据隔离 / 清理方案，并已通过 Codex 审查收口为 COMPLETED。M1-R3B 已完成运行态最小修复方案，并已通过 Codex 审查收口为 COMPLETED。M1-R3B-FIX 已通过 Codex 审查并收口为 COMPLETED；该轮只执行 `docker compose up -d redis-cache redis-queue`。M1-R3C 已通过 Codex 审查并收口为 COMPLETED，结论为 PARTIAL / GAP_IDENTIFIED。M1-R3D 已通过 Codex 审查并收口为 COMPLETED，结论为 Gap 四类分类、均不需要立即创建 hb_attendance_app。M1-R3E 已通过 Codex 审查并收口为 COMPLETED。M1-R3F 已通过 Codex 审查并收口为 COMPLETED。M1-REQ-DESIGN-DRAFT 已通过 Codex 审查并收口为 COMPLETED。M1-R4 已通过 Codex 审查并收口为 COMPLETED，主文档 `docs/milestones/M1_R4_Demo技术方案与实施路线拆分.md` 已交付。M1-R5 已通过 Codex 审查并收口为 COMPLETED，主文档 `docs/milestones/M1_R5_HRMS配置基线工作台月报Demo.md` 已交付。M1-R6A 已通过 Codex 审查并收口为 COMPLETED，主文档 `docs/milestones/M1_R6A_Excel导入与异常流程落地方案.md` 已交付。M1-R6B 已通过 Codex 审查并收口为 COMPLETED，主文档 `docs/milestones/M1_R6B_脱敏打卡流水导入最小实现.md` 已交付。M1-R6C = COMPLETED，异常识别与异常说明流程最小实现已通过 Codex 审查并 closeout。M1-R7 = COMPLETED，飞书登录、领导 Demo 与 M1 收口准备已通过 Codex 审查并 closeout。M1 历史 closeout 已完成，但 Owner UI 验收发现功能缺口，当前 M1 产品交付仍在 M1-FIX 中，尚未完成。M0-R3A 已完成 Frappe / ERPNext / Docker 最小本地环境落地，M0-R3C 已完成 Frappe HR / HRMS 安装验证，M0-R3C-FIX 已完成 HRMS 前端资源与 Roster 白屏诊断修复，M0-R3D 已完成 HRMS 能力盘点与 M1 考勤一期边界设计，M0-R3E 已完成 HRMS 环境可复现性收口并通过 Codex 审查。

下一步路线只记录，不代表已启动：

1. M1-R5 已通过 Codex 审查并收口为 COMPLETED，已交付 HRMS 配置基线、考勤工作台入口、月度汇总 Demo 和 Excel 月报导出路径。
2. M1 已 closeout 为 COMPLETED，但 Owner 验收发现功能缺口。
3. M1-FIX 功能补漏阶段已启动，M1-FIX-A 为 REVIEWING。
4. M1-FIX-B Excel 导入与真实本地数据闭环已实现并进入 REVIEWING。
5. M1-FIX-B2 已 COMPLETED；M1-FIX-B3 为 REVIEWING / Owner UI 验收未通过；M1-FIX-B4 为 REVIEWING / Claude PASS，但 Owner 数据链路验收发现后续问题；当前 M1-FIX-B5 为 REVIEWING，核查导入数据链路并收敛 HBOS 报表、月度汇总暂存和 HRMS 原生技术核查口径。M1 产品交付未完成，M1-FIX-C/D/E 未启动。

后续涉及 HRMS 环境治理、前端资源复核、能力盘点或 M1 考勤一期边界时，可读取 M0-R3C 安装验证记录、M0-R3C-FIX 修复记录、M0-R3D 设计记录、M0-R3E 环境可复现性收口记录、官方 Frappe HR、`frappe/hrms`、`frappe/frappe_docker`、ERPNext / Frappe v16 资料。

不得因 HRMS 已安装而擅自创建新的海滨自定义 Frappe App；`hb_attendance_app` 仅限 M1-FIX-B 已授权的轻量导入能力，不得扩大范围；不得接飞书真实写入；不得做前端驾驶舱；不得提交真实 `.env` 或真实密钥。


## HBOS Portal 并行工作流读取规则

当任务明确涉及 HBOS Portal / Workspace / Experience Architecture 时，可在默认入口文件之外读取：

- `docs/experience/README.md`
- 当前 EA 文档；
- `docs/frontend/FRONTEND_IMPLEMENTATION_GUIDE.md`
- `docs/plans/HBOS_PORTAL_IMPLEMENTATION_PLAN.md`

不得因此递归读取整个 `docs/`。

Portal 产品 Authority 为 `feature/hbos-portal-product@e4b16ee80aaaf21aac2304246a4de1f9fe8995ea`；原 `codex/portal-unified-account-release` 仅保留为已合并 PR #21 的历史来源。


## Portal 统一账号与正式发布

当前任务定向读取 `docs/milestones/M1_RP3_统一账号飞书绑定与正式发布.md`、`docs/deployment/统一账号与Portal正式部署说明.md`、`docs/frontend/统一账号发布与前端完整性矩阵.md`。旧预览/试点记录是历史背景，不能替代原账号或正式 Site 验收。真实目标清单、备份与内部报告私下保存。

团队通用交付已经通过 [PR #21](https://github.com/zjl327707743/HBOS-Platform/pull/21) 进入产品分支。当前后续代码以 `feature/hbos-portal-product@e4b16ee80aaaf21aac2304246a4de1f9fe8995ea` 为准；公司服务器/HTTPS 和尚未执行的真人高风险场景仍按独立后续 Gate 管理。

当前 Portal 本轮门禁以 RP3 主记录和 `deployment/Mac本地运行与团队同步.md` 为准；原库选择、公司服务器和 HTTPS 不阻塞已授权 Mac 运行。

当前飞书成员拒绝、自动开户/拼音登录名与受控换绑/交接，定向阅读 `docs/deployment/飞书自动开户与受控账号变更.md`。2026-10-01 Owner 已确认 Administrator 本人飞书成功登录；旧成员权限待审批记录为历史，当前新版本真人回归及其他真人操作单独记录，不恢复旧的原库/服务器/HTTPS门禁。
