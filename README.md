> **仅用于隔离 CI/UAT 的组合分支**：前端 9d2d996 + 只读后端 ee7d3c0；未合并产品、无发布授权。产品仍为 22b47dc。

# 新乡海滨智能运营管理平台

> **2026-10-27 R6-B / G4_UAT_IN_PROGRESS**：#62 与 #61 已分别按 Owner 精确授权正常 Squash，实际产品基线为 `22b47dcdcc17e8dfd0f0640d2b9a04ec14303b0b`。实际提交四个 CI 作业通过。R6 从该 SHA 的 `feat/hbos-r6b-experience-v1` 实施，固定设计依据 R6-A2.2 / v1.3；G4 真实权限与浏览器验收、G5 独立审查及固定 SHA 合并、G6 统一构建/标签/团队发布尚未完成。`TEAM_PULL_READY=PENDING`，未生产上线。详见 [本轮主记录](docs/milestones/Portal_R6B_正式管理体验与稳定集成.md)。以下按日期保留的旧状态为历史。

> **2026-10-27 R6 只读 DTO / CODE_REVIEW_CANDIDATE**：#62/#61 已正常集成，实际产品基线 `22b47dcdcc17e8dfd0f0640d2b9a04ec14303b0b`。Owner 已授权独立补齐本人岗位、审计筛选和脱敏详情；本分支仅含三个后端文件、合同测试及文档，前端另在 PR #63。Python 3.11/3.12 各 261 测试 PASS；真实 Site/HTTP 联调与固定 SHA 合并仍待完成。未生产上线，`TEAM_PULL_READY=PENDING`。见 [本轮主记录](docs/milestones/Portal_R6_只读DTO合同补齐.md)。下列旧状态按日期保留历史含义。


## 历史集成状态 — 2026-10-19

**四个完整业务 PR 已实际合并：#42 考勤、#46 生产、#39 仓储、#43 LIMS。** 唯一目标为 `feature/hbos-portal-product`；业务合并基线为 `04e0bb033cb2e7156e407cf49a7b6966b0d2a022`，状态文档在其后维护。[#43](https://github.com/zjl327707743/HBOS-Platform/pull/43) 于 2026-10-19 03:28:29 UTC 正常 Squash Merge；来源、父提交与树见[项目状态](docs/PROJECT_STATUS.md)。

**合并前精确组合：PASS。** [R10 39184807396](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39184807396) 全部 10 jobs SUCCESS，五个原生域与离线／契约／构建在本次 #43 来源和产品基线的真实组合上通过；该组合树与实际 Squash 树相同。

**实际产品合并后回归：PASS。** [R11 39195037712](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39195037712) 全部 10 jobs SUCCESS；五个原生域均直接运行业务合并基线 `04e0bb033cb2e7156e407cf49a7b6966b0d2a022`，无额外 merge，实际单父与树一致，双 migrate 与清理均成功。LIMS 原有 32 项、新增审计 9 项、独立 Todo 1 项合计 42 项原生测试全部通过；Todo 只有 1 项，归属 LIMS。

四项完整业务 PR 已形成统一产品开发基线。IAM #52 保持独立，#37 不在任务范围；OCR、真实样本、实体打印和生产 UAT／部署未由本轮代码集成完成。库存单据取消与账务反转不等于 LIMS 质量放行撤回。本轮仅使用远端源码和云端合成 Site，未操作 Owner Mac 项目或真实业务库。 既有 Draft #15 自动质量门禁暴露的 Python 3.10 测试夹具兼容问题单独收口，两处仅测试修复须在固定候选 SHA 的 Python 3.10／3.12 检查通过后方可合并，实际结果以收尾 PR 最新 Owner 裁定及最终报告所列 SHA／Job 为准，见[项目状态](docs/PROJECT_STATUS.md)。

业务合并基线与文档保存后的 HEAD 分开记录。Run1–9 的历史失败、未合并及 `NOT_PRODUCT_COMPOSITION` 均按各自日期、来源和作业保留，详见 [PR #56](https://github.com/zjl327707743/HBOS-Platform/pull/56)；最新业务与回归状态以本节和项目状态为准。

### 历史回归 — 2026-10-18 Run8（#39 合并后）

**合并后回归：PASS。** [Run8 39107944012](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39107944012) 全部 8 jobs SUCCESS；四个业务域直接检出实际产品 `a1cc65dde73cfad656faf290264f75fb1a25c32b`，记录 `post_merge_baseline`，源码树为 `43b59653ebbe61db530f523ea980163c88f1899e`、唯一父提交为 `4ddf9bebe5bd9f0d73cdb84bd4ddfa9b8615ad30`。仓储事务 8/8、报表22项HTTP与8项跨仓CSV、卡证权限74/74、考勤原生范围及生产28项检查均通过；所有原生Site双migrate与清理通过。完整来源与后续文档提交见 [PR #56](https://github.com/zjl327707743/HBOS-Platform/pull/56)，不以文档提交后的新HEAD冒充上述已运行提交。

## 验证历史 — 2026-10-18 Run6

[报表、扫码及附件验证](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39103298497/job/117603810152) **74 PASS / 0 FAIL**；[事务验证](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39103298497/job/117603810103) **6 PASS / 2 FAIL**。余两项失败为按单一 URL 误选 Batch File 的测试定位错误，LIMS 放行后两种外发 submit/cancel 仍 **NOT_REACHED**，完整仓储门禁未通过。

## 验证历史 — 2026-10-18 Run5

以下保留 Run5 当时的观察与判断，其中“当前”“尚未通过”“原因待定位”均指该次验证；后续状态以页首“当前集成状态”和实际 PR 记录为准。

完整 [#42 考勤](https://github.com/zjl327707743/HBOS-Platform/pull/42) 与 [#46 生产](https://github.com/zjl327707743/HBOS-Platform/pull/46) 已实际合并到唯一目标 `feature/hbos-portal-product`；本记录已核对产品为 `4ddf9bebe5bd9f0d73cdb84bd4ddfa9b8615ad30`。[#39 仓储](https://github.com/zjl327707743/HBOS-Platform/pull/39) 仍在技术门禁中，尚未合并；[#56](https://github.com/zjl327707743/HBOS-Platform/pull/56) 保存固定源码组合的隔离验证，不能以 CI 候选替代实际产品合并。

后续来源、CI、审批、合并与回归以 [项目状态](docs/PROJECT_STATUS.md)、[当前里程碑](docs/CURRENT_MILESTONE.md) 及上述 PR 最新记录为准。#43 LIMS 独立增量后置；本次仅使用远端源码与云端合成环境，未更新 Owner 的 Mac 项目、真实数据库或生产部署。IAM #52 保持独立，#37 不在本任务范围。

## 历史阶段记录

下方 PR #55、PR #21 的 SHA、账号验收与各阶段“本轮”描述保留其原日期的含义，不代表当前产品 HEAD 或本次部署。

> 2026-10-18 代码集成窗口：仓储物料只读浏览由 [PR #55](https://github.com/zjl327707743/HBOS-Platform/pull/55) 独立承接；当前代码来源以远端 `feature/hbos-portal-product` 与该 PR 实际合并 SHA 为准。下方 PR #21 的 SHA/账号验收是历史记录，不代表最新产品 HEAD。完整业务 #42/#43/#46/#39 和 IAM #52 各自保留独立门禁；本轮不安装或部署真实环境。

## 并行权限治理 IAM-0 — 2026-10-01

Owner 已批准进入统一身份与权限治理。当前仅交付设计、角色—动作—范围矩阵、只读源码盘点工具与本机任务书；实际 Site 盘点和隔离验收仍为 NOT_RUN，不修改账号、角色或业务数据，不替代原账号收尾。入口：[IAM-0 治理资料](docs/governance/iam/README.md)。

历史账号验收基线（2026-10-01）：PR #21 已在 FINAL_REVIEW_PASS 后 squash 合入 `feature/hbos-portal-product`，产品 HEAD `e4b16ee80aaaf21aac2304246a4de1f9fe8995ea`。Owner 最新无破坏验收 PASS、浏览器设密/改密/恢复 final-submit 3/3 PASS，新 squash 四项 CI SUCCESS。IAM-0 已由 clean Draft PR #23 承接，旧 #22 已关闭且未合并；PR #15 仍为 Draft，main 未变化。[当前 Gate](docs/milestones/M1_RP3_统一账号飞书绑定与正式发布.md) 记录本轮收口事实。

Frappe/ERPNext 开源底座 + Frappe 多 App 模块化架构 + 外部独立服务扩展。

## 历史交付 — 2026-10-01

本轮（2026-10-01）接续 PR #21，执行登录账号模块 UI 规范回归与全功能审修。Owner 已亲自确认 Administrator 能通过本人飞书验证并登录，记为 OWNER_CONFIRMED_SUCCESS；历史成员权限待审批或登录失败记录不再代表当前事实。保留真实绑定、密码、MFA、Secret、企业与回调；不要求重复配置。认证页沿用已有 Ant Design Vue / ConfigProvider / typography / tokens，修复表单、证明期限、错误状态、同路由目标与提交结果处理。破坏性、并发与交接只在独立合成 Site 验证。新版本真人 OAuth、本人收到验证码、第二位真人交接与移动软键盘结果单独记录，未执行不写 PASS。复用现有 P1 / Compose / 卷与常用入口，最终本机 SHA/build ID、远端提交、CI 和制品须一致。公司服务器为 NOT_DEPLOYED。主记录：`docs/milestones/M1_RP3_统一账号飞书绑定与正式发布.md`。PR #21 已 squash 合入 `feature/hbos-portal-product@e4b16ee80aaaf21aac2304246a4de1f9fe8995ea`；团队后续 Portal 代码以产品分支为准。PR #15 仍 Draft，不推 main；IAM 由 Draft PR #23 单独承接。

平台已包含考勤、仓储库存、LIMS、Portal、知识助理与设备/数字孪生自定义 App。密码和飞书使用同一 Frappe User；原有业务权限仍由原 App 约束。业务通知、生成式知识回答、现场遥测、工艺动画及偏好同步尚未实现，具体状态见前端完整性矩阵。安全变更通知单独记录真实发送状态，不能等同业务通知能力完成。

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

团队后续 Portal 代码来源：远端最新 `feature/hbos-portal-product`；固定 SHA 见本轮 PR 实际合并记录。PR #21 保留为已合并的审查与发布证据；Mac 本地运行与本人验收分开记录，公司生产尚未部署。
