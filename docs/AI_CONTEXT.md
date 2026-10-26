# AI Context

> **2026-10-26 R5-B 受控登录候选（实施中）**：产品基线为 `1a0d44de1399afca513855f3688eb06c1978429e`（PR #60 已合并）；视觉继续 Draft #61，认证策略独立候选修复。仅非生产 UAT、最多两个显式账号，自动开户关闭；Owner 追加明确授权本人飞书绑定 Administrator，须显式开关和试点名单同时允许并保留密码/MFA proof；真实 OAuth 仍待本人完成，不代表上线或合并。见 [本轮记录](milestones/Portal_R5B_受控飞书登录候选.md)。以下各日期记录保留历史含义。


## 当前集成状态 — 2026-10-19

**四个完整业务 PR 已实际合并：#42 考勤、#46 生产、#39 仓储、#43 LIMS。** 唯一目标为 `feature/hbos-portal-product`；业务合并基线为 `04e0bb033cb2e7156e407cf49a7b6966b0d2a022`，状态文档在其后维护。[#43](https://github.com/zjl327707743/HBOS-Platform/pull/43) 于 2026-10-19 03:28:29 UTC 正常 Squash Merge；来源、父提交与树见[项目状态](PROJECT_STATUS.md)。

**合并前精确组合：PASS。** [R10 39184807396](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39184807396) 全部 10 jobs SUCCESS，五个原生域与离线／契约／构建在本次 #43 来源和产品基线的真实组合上通过；该组合树与实际 Squash 树相同。

**实际产品合并后回归：PASS。** [R11 39195037712](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39195037712) 全部 10 jobs SUCCESS；五个原生域均直接运行业务合并基线 `04e0bb033cb2e7156e407cf49a7b6966b0d2a022`，无额外 merge，实际单父与树一致，双 migrate 与清理均成功。LIMS 原有 32 项、新增审计 9 项、独立 Todo 1 项合计 42 项原生测试全部通过；Todo 只有 1 项，归属 LIMS。

接续时先读本节、[项目状态](PROJECT_STATUS.md)及远端产品 ref。[#43 Owner Approve 5566593947](https://github.com/zjl327707743/HBOS-Platform/pull/43#pullrequestreview-5566593947) 对应最终来源 `06e4639fe8efeda9d1874b0eb5d5d33706be98d2`；#39 的 Owner 裁定及旧 Review 闭环继续保留。R11 实际产品回归及 LIMS 独立 Todo 1 项补证已经通过，不再将 #43 记为 source-only；后续收口只另行记录两处 Python 3.10 测试夹具兼容修复，本收尾 PR 必须在固定候选 SHA 的 Python 3.10／3.12 检查通过后方可合并，实际结果以本 PR 最新 Owner 裁定及最终报告所列 SHA／Job 为准。IAM #52、OCR、实体样本／打印和生产 UAT 保留各自门禁。

业务合并基线与文档保存后的 HEAD 分开记录。Run1–9 的历史失败、未合并及 `NOT_PRODUCT_COMPOSITION` 均按各自日期、来源和作业保留，详见 [PR #56](https://github.com/zjl327707743/HBOS-Platform/pull/56)；最新业务与回归状态以本节和项目状态为准。

### 历史回归 — 2026-10-18 Run8（#39 合并后）

**合并后回归：PASS。** [Run8 39107944012](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39107944012) 全部 8 jobs SUCCESS；四个业务域直接检出实际产品 `a1cc65dde73cfad656faf290264f75fb1a25c32b`，记录 `post_merge_baseline`，源码树为 `43b59653ebbe61db530f523ea980163c88f1899e`、唯一父提交为 `4ddf9bebe5bd9f0d73cdb84bd4ddfa9b8615ad30`。仓储事务 8/8、报表22项HTTP与8项跨仓CSV、卡证权限74/74、考勤原生范围及生产28项检查均通过；所有原生Site双migrate与清理通过。完整来源与后续文档提交见 [PR #56](https://github.com/zjl327707743/HBOS-Platform/pull/56)，不以文档提交后的新HEAD冒充上述已运行提交。

## 验证历史 — 2026-10-18 Run6

[报表、扫码及附件验证](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39103298497/job/117603810152) **74 PASS / 0 FAIL**；[事务验证](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39103298497/job/117603810103) **6 PASS / 2 FAIL**。余两项失败为按单一 URL 误选 Batch File 的测试定位错误，LIMS 放行后两种外发 submit/cancel 仍 **NOT_REACHED**，完整仓储门禁未通过。

## 验证历史 — 2026-10-18 Run5

以下保留 Run5 当时的观察与判断，其中“当前”“尚未通过”“原因待定位”均指该次验证；后续状态以页首“当前集成状态”和实际 PR 记录为准。

当前工作是 Owner 授权的远端业务 PR 集成：完整 #42 考勤、#46 生产已实际合并，已核对产品基线为 `feature/hbos-portal-product@4ddf9bebe5bd9f0d73cdb84bd4ddfa9b8615ad30`。[#39 仓储](https://github.com/zjl327707743/HBOS-Platform/pull/39) 尚未合并，继续技术门禁；[#56](https://github.com/zjl327707743/HBOS-Platform/pull/56) 是固定组合验证入口。#43 LIMS 独立增量后置，独立契约通过不代表产品组合通过。

按 [项目状态](PROJECT_STATUS.md)、[当前里程碑](CURRENT_MILESTONE.md)、[Owner 本批次裁定](governance/HBOS_Owner_业务集成批次裁定_20261018.md) 与 [M3 门禁](milestones/M3_START_GATE.md) 接续工作，每次合并后重读远端 HEAD。#39 候选扫码仅展示原生 Warehouse 授权范围；全批次卡证读取要求全仓范围，受控收货自动制证不授予读取或手动再生权限。本轮使用云端合成环境，不操作 Mac、真实业务库或生产；#37 排除，IAM #52 独立。

## 历史阶段记录

下方账号、M1 与 Portal 阶段记录保留其原日期的背景和验收结果；旧“当前”“本轮”“Authority”不覆盖本页首 R3 记录。#55 已合入的物料只读范围不能代表完整 #39 完成。

> 2026-10-18 代码集成窗口：仓储物料只读浏览由 [PR #55](https://github.com/zjl327707743/HBOS-Platform/pull/55) 独立承接；当前代码来源以远端 `feature/hbos-portal-product` 与该 PR 实际合并 SHA 为准。下方 PR #21 的 SHA/账号验收是历史记录，不代表最新产品 HEAD。完整业务 #42/#43/#46/#39 和 IAM #52 各自保留独立门禁；本轮不安装或部署真实环境。

历史账号验收事实（2026-10-01）：PR #21 已完成 FINAL_REVIEW_PASS，并 squash 合入 `feature/hbos-portal-product@e4b16ee80aaaf21aac2304246a4de1f9fe8995ea`。Owner 最新无破坏验收 PASS，团队合成浏览器 final-submit 3/3 PASS，新 squash 四项 CI SUCCESS。旧 #22 已关闭未合并，IAM-0 由 clean Draft PR #23 承接；PR #15 仍 Draft，main 未变化。真实 Owner 凭据、绑定、MFA 与 P1 原卷保持不变。下方 BLOCKED/WAITING 记录仅为合并前历史，不再代表当前 Gate。

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

## 历史账号上下文 — 2026-10-01

本轮账号 UI、统一账号、飞书、Knowledge/Twin 与发布收口已经通过 PR #21 完成并进入产品分支。该账号轮次历史 Authority 为 `feature/hbos-portal-product@e4b16ee80aaaf21aac2304246a4de1f9fe8995ea`；Owner 真人飞书基线和浏览器密码生命周期 3/3 均已通过，未执行的真人高风险交接/实体设备项目继续按历史记录保留。公司服务器仍 NOT_DEPLOYED。

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

## 历史路线背景（不覆盖 R3 集成队列）

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

该历史 Portal 阶段 Authority：

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
