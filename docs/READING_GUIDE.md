> **2026-10-27 R6 独立安全修复 / G4_IMPLEMENTING**：请求前只读guard复用current_read，最多4次、回滚后全量重鉴权；拒绝及非读取错误不重试，业务命令不重放。基线实际产品22b47dcdcc17e8dfd0f0640d2b9a04ec14303b0b；Owner本轮明确授权独立安全修复与18191合成验证，提案补丁567d2f8fb2180db60edb72d1fb7acf798011dde0d251b165355ba9fa12bb6b7b。本分支未合并、真实UAT未部署、标签及团队发布未获授权，TEAM_PULL_READY=PENDING。详见 `docs/milestones/Portal_R6_请求前鉴权读取并发修复.md`。下列带日期的状态保留历史含义。

> **仅用于隔离 CI/UAT 的组合分支**：前端 9d2d996 + 只读后端 ee7d3c0；未合并产品、无发布授权。产品仍为 22b47dc。

# Reading Guide

> **2026-10-27 R6-B / G4_UAT_IN_PROGRESS**：#62 与 #61 已分别按 Owner 精确授权正常 Squash，实际产品基线为 `22b47dcdcc17e8dfd0f0640d2b9a04ec14303b0b`。实际提交四个 CI 作业通过。R6 从该 SHA 的 `feat/hbos-r6b-experience-v1` 实施，固定设计依据 R6-A2.2 / v1.3；G4 真实权限与浏览器验收、G5 独立审查及固定 SHA 合并、G6 统一构建/标签/团队发布尚未完成。`TEAM_PULL_READY=PENDING`，未生产上线。详见 [本轮主记录](milestones/Portal_R6B_正式管理体验与稳定集成.md)。以下按日期保留的旧状态为历史。

> **2026-10-27 R6 只读 DTO / CODE_REVIEW_CANDIDATE**：#62/#61 已正常集成，实际产品基线 `22b47dcdcc17e8dfd0f0640d2b9a04ec14303b0b`。Owner 已授权独立补齐本人岗位、审计筛选和脱敏详情；本分支仅含三个后端文件、合同测试及文档，前端另在 PR #63。Python 3.11/3.12 各 261 测试 PASS；真实 Site/HTTP 联调与固定 SHA 合并仍待完成。未生产上线，`TEAM_PULL_READY=PENDING`。见 [本轮主记录](milestones/Portal_R6_只读DTO合同补齐.md)。下列旧状态按日期保留历史含义。


## 历史集成状态 — 2026-10-19

**四个完整业务 PR 已实际合并：#42 考勤、#46 生产、#39 仓储、#43 LIMS。** 唯一目标为 `feature/hbos-portal-product`；业务合并基线为 `04e0bb033cb2e7156e407cf49a7b6966b0d2a022`，状态文档在其后维护。[#43](https://github.com/zjl327707743/HBOS-Platform/pull/43) 于 2026-10-19 03:28:29 UTC 正常 Squash Merge；来源、父提交与树见[项目状态](PROJECT_STATUS.md)。

**合并前精确组合：PASS。** [R10 39184807396](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39184807396) 全部 10 jobs SUCCESS，五个原生域与离线／契约／构建在本次 #43 来源和产品基线的真实组合上通过；该组合树与实际 Squash 树相同。

**实际产品合并后回归：PASS。** [R11 39195037712](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39195037712) 全部 10 jobs SUCCESS；五个原生域均直接运行业务合并基线 `04e0bb033cb2e7156e407cf49a7b6966b0d2a022`，无额外 merge，实际单父与树一致，双 migrate 与清理均成功。LIMS 原有 32 项、新增审计 9 项、独立 Todo 1 项合计 42 项原生测试全部通过；Todo 只有 1 项，归属 LIMS。

阅读顺序为页首当前状态 → [PROJECT_STATUS](PROJECT_STATUS.md) 的四项实际合并表、R10 与 R11 → M2／M3 当前门禁 → [审计兼容边界](experience/LIMS_审计指纹与锚定版本兼容边界.md) → 按需追溯旧 Run。后续工作读取远端最新产品 HEAD；AGENTS／CLAUDE 继续维护协作规则。旧 Mac、OCR、样本及打印记录不构成本轮操作或验收授权。

业务合并基线与文档保存后的 HEAD 分开记录。Run1–9 的历史失败、未合并及 `NOT_PRODUCT_COMPOSITION` 均按各自日期、来源和作业保留，详见 [PR #56](https://github.com/zjl327707743/HBOS-Platform/pull/56)；最新业务与回归状态以本节和项目状态为准。

### 历史回归 — 2026-10-18 Run8（#39 合并后）

**合并后回归：PASS。** [Run8 39107944012](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39107944012) 全部 8 jobs SUCCESS；四个业务域直接检出实际产品 `a1cc65dde73cfad656faf290264f75fb1a25c32b`，记录 `post_merge_baseline`，源码树为 `43b59653ebbe61db530f523ea980163c88f1899e`、唯一父提交为 `4ddf9bebe5bd9f0d73cdb84bd4ddfa9b8615ad30`。仓储事务 8/8、报表22项HTTP与8项跨仓CSV、卡证权限74/74、考勤原生范围及生产28项检查均通过；所有原生Site双migrate与清理通过。完整来源与后续文档提交见 [PR #56](https://github.com/zjl327707743/HBOS-Platform/pull/56)，不以文档提交后的新HEAD冒充上述已运行提交。

## 验证历史 — 2026-10-18 Run6

[报表、扫码及附件验证](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39103298497/job/117603810152) **74 PASS / 0 FAIL**；[事务验证](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39103298497/job/117603810103) **6 PASS / 2 FAIL**。余两项失败为按单一 URL 误选 Batch File 的测试定位错误，LIMS 放行后两种外发 submit/cancel 仍 **NOT_REACHED**，完整仓储门禁未通过。

## 验证历史 — 2026-10-18 Run5

以下保留 Run5 当时的观察与判断，其中“当前”“尚未通过”“原因待定位”均指该次验证；后续状态以页首“当前集成状态”和实际 PR 记录为准。

当前业务集成先读 [项目状态](PROJECT_STATUS.md)、[当前里程碑](CURRENT_MILESTONE.md)、[多 App 集成规范](governance/HBOS_CONCURRENT_APP_INTEGRATION_V1.md) 与 [Owner 本批次裁定](governance/HBOS_Owner_业务集成批次裁定_20261018.md)。完整 #42、#46 已合并，已核对产品为 `4ddf9bebe5bd9f0d73cdb84bd4ddfa9b8615ad30`；[#39](https://github.com/zjl327707743/HBOS-Platform/pull/39) 仍在技术门禁中，未合并，验证证据见 [#56](https://github.com/zjl327707743/HBOS-Platform/pull/56)。#43 后置；独立 LIMS 契约结果不能替代产品组合。

仓储任务定向读取 [M3 门禁](milestones/M3_START_GATE.md) 和 M3-R4/R5/R6 页首 R3 补记；不因读取旧文档启动 Mac 服务或迁移真实 Site。最新来源和实际合并以 PR #39、PR #56 及远端产品 ref 为准。下方 PR #21、#55 与早期阶段的“本轮”“当前”均为历史背景，不覆盖此读取入口。

## 历史阶段记录

> 2026-10-18 代码集成窗口：仓储物料只读浏览由 [PR #55](https://github.com/zjl327707743/HBOS-Platform/pull/55) 独立承接；当前代码来源以远端 `feature/hbos-portal-product` 与该 PR 实际合并 SHA 为准。下方 PR #21 的 SHA/账号验收是历史记录，不代表最新产品 HEAD。完整业务 #42/#43/#46/#39 和 IAM #52 各自保留独立门禁；本轮不安装或部署真实环境。

PR #21 已完成 FINAL_REVIEW_PASS 并 squash 合入 `feature/hbos-portal-product@e4b16ee80aaaf21aac2304246a4de1f9fe8995ea`。Browser final-submit 3/3 与 Owner 最新无破坏验收均已 PASS；旧 #22 已关闭，IAM-0 由 clean Draft PR #23 承接。PR #15 仍 Draft，main 未放行。以 [本轮主记录](milestones/M1_RP3_统一账号飞书绑定与正式发布.md) 顶部的合并后收口状态为准；下方 BLOCKED/WAITING 文字均为历史。

本指南用于限制 AI 在新乡海滨智能运营管理平台中的默认阅读范围，避免上下文膨胀和误读旧资料。

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

该 PR #21 历史发布 Authority 为 `feature/hbos-portal-product@e4b16ee80aaaf21aac2304246a4de1f9fe8995ea`；原 `codex/portal-unified-account-release` 仅保留为已合并 PR #21 的历史来源。当前业务集成读取本页首 R3 入口。


## Portal 统一账号与正式发布

涉及该历史统一账号发布任务时，定向读取 `docs/milestones/M1_RP3_统一账号飞书绑定与正式发布.md`、`docs/deployment/统一账号与Portal正式部署说明.md`、`docs/frontend/统一账号发布与前端完整性矩阵.md`。旧预览/试点记录是历史背景，不能替代原账号或正式 Site 验收。真实目标清单、备份与内部报告私下保存。

团队通用交付已经通过 [PR #21](https://github.com/zjl327707743/HBOS-Platform/pull/21) 进入产品分支，该历史发布代码基线为 `feature/hbos-portal-product@e4b16ee80aaaf21aac2304246a4de1f9fe8995ea`；公司服务器/HTTPS 和尚未执行的真人高风险场景仍按独立后续 Gate 管理。当前后续代码以远端最新产品 ref 及本页首 R3 记录为准。

该历史 Portal 账号发布轮次门禁以 RP3 主记录和 `deployment/Mac本地运行与团队同步.md` 为准；原库选择、公司服务器和 HTTPS 不阻塞当时已授权 Mac 运行，不构成本次云端集成的 Mac 操作授权。

当前飞书成员拒绝、自动开户/拼音登录名与受控换绑/交接，定向阅读 `docs/deployment/飞书自动开户与受控账号变更.md`。2026-10-01 Owner 已确认 Administrator 本人飞书成功登录；旧成员权限待审批记录为历史，当前新版本真人回归及其他真人操作单独记录，不恢复旧的原库/服务器/HTTPS门禁。
