# Current Milestone

## HBOS Knowledge R2.1 — 2026-10-08

状态：PARTIAL / BLOCKED_EMBEDDING_QUOTA / NOT_RELEASED。承接 Draft PR #30 与现有 R2 候选。事务性发布前进约束、独立 replace/restore 意图与不可变收据已落地，原生数据库反例和真实旧批次 12 项 NOOP 重放通过。

新冻结批次实际上传 302 份，220 份解析成功、82 份因获准 embedding provider 额度耗尽而失败，1 份同内容重复跳过，新发布 0 份。已成功内容和原 12 份资料、用户历史/收藏/反馈均保留。额度问题同时阻塞现有资料的在线检索，登录、目录与历史仍可读；不能将解析成功等同于召回、答案或发布验收通过。

稳定身份、精确部门 Dataset 映射、有界多部门计划/元数据分页、目录文本筛选与 12 项分页已实现。独立服务 0.3.4 本地提交及 wheel 单独固定。核心 207、领域 74、服务 39、前端 85 项分别通过，真实响应式浏览器 10 项通过；多部门在线检索、新资料问答/引用与相应 UI 流程 BLOCKED。真实资料、问题、截图、准确 ID、备份及恢复工具仅在 Owner 私有层。详情见 `docs/milestones/M1_KB_R2_1_增量入库与多部门验收.md`。不改变模型/付费策略，不合并、不切换 P1。以下 R2/R1 为历史记录。

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
