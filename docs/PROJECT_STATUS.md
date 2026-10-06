# 项目状态

## 产品基线快照（核验日 2026-10-06）

> 本节记录**核验当日**事实，不是随分支自动前进的“当前 HEAD”。后续轮次须在当日重新 `git ls-remote` / GitHub API 核验后再引用。

- 产品分支 `feature/hbos-portal-product`；**核验日 2026-10-06** 的 HEAD = `72e5b1728981b7ef102a2c9ee033ce0452c400e7`。本机产品源码目录在该核验日已 fast-forward 到同一提交，工作区干净，与远端一致。
- 核验日合入顺序：`e4b16ee`（PR #21）→ `114a0cb`（#24 Portal 合并状态收口与库存 CI 门禁）→ `4d8e962`（#25 IAM-0 治理基线与只读盘点工具）→ `29220f4`（#26 考勤月度上传未授权写入）→ `0fc5c3a`（#27 LIMS 原生写绕过留样审批系统字段）→ `72e5b17`（#28 ESS 敏感数据批量导出与权限再生）。PR #26/#27/#28 均已 MERGED 到产品分支。
- **安全修复 #26/#27/#28 = 已合入源码、未部署**。本机 P1 运行版本仍为 `2d138f86a14883214f4963f5809550770a2bc3df`（`release.json` build ID `dcfcba32096a320a9981`，与本机 portal `build-info.json` 一致）。该版本因此是旧版本功能走查，不是新安全版本验收。
- **分叉原因与结论**：运行版本与产品分支历史不直接相连，主要原因是 PR #21 采用 **squash 合并**，两条历史不共享父提交（运行版本独有 23 commit、产品分支独有 6 commit）。这不代表旧账号/飞书功能遗漏——运行版本独有的提交内容已随 PR #21 进入产品分支，逐文件内容差仅 26 个文件。**无需也不得重新合并旧分支**；版本对齐只通过“构建新制品 + 备份 + 迁移”完成。
- X02 预期新增件 `apps/hbos_portal/hbos_portal/auth/export_policy.py`（含 `tests/test_export_policy.py`）在本机 P1 制品中**不存在**；#26/#27 对应文件的本机 P1 制品内容与安全修复版本不一致。升级计划单独保存于 Git 之外，本轮不执行任何迁移或制品切换。
- PR #15：仍 Open Draft（base `main`，head 产品分支）；描述停留在三应用 registry 阶段，未反映五应用、contract v1 与 #24–#28，属历史漂移，不作为当前功能状态依据。main 未变化。
- IAM-1 = PAUSED（本轮不设计、不实施权限变更，也不做 Site 盘点或隔离验收）。Owner 人工验收 = WAITING_OWNER。

以下 2026-10-01 各节为历史记录，保留原文。

## 并行权限治理 IAM-0 — 2026-10-01（历史）

Owner 已批准进入统一身份与权限治理。当前仅交付设计、角色—动作—范围矩阵、只读源码盘点工具与本机任务书；实际 Site 盘点和隔离验收仍为 NOT_RUN，不修改账号、角色或业务数据，不替代原账号收尾。入口：[IAM-0 治理资料](governance/iam/README.md)。

## PR #21 合并后收口 — 2026-10-01

状态：**FINAL_REVIEW_PASS / MERGED_TO_PORTAL_PRODUCT**。PR #21 已使用 expected-head squash 合入 `feature/hbos-portal-product`，产品 HEAD `e4b16ee80aaaf21aac2304246a4de1f9fe8995ea`；Owner 最新无破坏验收 PASS，团队合成浏览器 final-submit 3/3 PASS，新 squash 四项 CI SUCCESS。旧 #22 已关闭未合并，IAM-0 由 clean Draft PR #23 仅承接原 11 文件增量；PR #15 仍 Open Draft，main 未变化。

合并前发现并修复的原生 MFA Administrator proof P1 已完成回归；本次收口未修改 Owner 密码、MFA、飞书绑定、Secret、业务数据或 P1 卷。合并前 BLOCKED/WAITING 状态继续作为历史证据保留，但不再作为当前项目状态。

历史团队 Portal Authority（2026-10-01 收口点）：`feature/hbos-portal-product@e4b16ee80aaaf21aac2304246a4de1f9fe8995ea`。本轮起以本文件顶部“产品版本现状”的 HEAD 为准。

## 账号小范围收尾 — 2026-10-01

本轮接续交付基线 `eee1c5e22c57be3436244e77c65e189bd7eee242` 与 PR #21，仅做资料登录渠道、唯一个人导航、折叠偏好说明、飞书头像同步及 C03/C07/C09/F03 缺项补测；不重新全量审计、重画页面或新增账号功能。真实 Administrator 已成功飞书登录为 USER_CONFIRMED_SUCCESS，绑定、密码、MFA、Secret、企业与回调保留。本机沿用既有 P1 Site/Compose/入口，发布分支不合并、不强推、不推 main/base。 补测确认并修复参与页期限遗漏与 GET 回调未提交记录，原矩阵历史保持；最终浏览器新凭据步骤由工具要求人工接手，团队脚本与未执行状态单列。


项目：新乡海滨智能运营管理平台。架构：Frappe/ERPNext 开源底座 + Frappe 多 App 模块化架构 + 外部独立服务扩展。

## 当前 Portal 轮次 — 2026-10-01

本轮（2026-10-01）接续 PR #21，执行登录账号模块 UI 规范回归与全功能审修。Owner 已亲自确认 Administrator 能通过本人飞书验证并登录，记为 OWNER_CONFIRMED_SUCCESS；历史成员权限待审批或登录失败记录不再代表当前事实。保留真实绑定、密码、MFA、Secret、企业与回调；不要求重复配置。认证页沿用已有 Ant Design Vue / ConfigProvider / typography / tokens，修复表单、证明期限、错误状态、同路由目标与提交结果处理。破坏性、并发与交接只在独立合成 Site 验证。新版本真人 OAuth、本人收到验证码、第二位真人交接与移动软键盘结果单独记录，未执行不写 PASS。复用现有 P1 / Compose / 卷与常用入口，最终本机 SHA/build ID、远端提交、CI 和制品须一致。公司服务器为 NOT_DEPLOYED。主记录：`docs/milestones/M1_RP3_统一账号飞书绑定与正式发布.md`。PR #21 head `codex/portal-unified-account-release`、base `feature/hbos-portal-product`；不强推、不自动合并、不推 main/base。

| 项目 | 实际状态 |
| --- | --- |
| 唯一 User 与密码/飞书账号流程 | 统一账号与受控变更已实现并分层测试；密码记录保留；Owner 已确认本人飞书成功登录，新版本正常回归单列 |
| 五应用与已批准前端 | Administrator 五入口实际打开；普通用户按原角色仅开放知识/设备；未实现项明确标注 |
| 备份恢复/保留校验/production 制品 | 当前 P1 原卷已备份并迁移，账号/密码/角色/权限/业务/身份指纹保留；Portal 与 LIMS 编译资产已部署 |
| 通用 Gateway/团队依赖 | 版本化通用代码、Dockerfile、完整 lock 已提供；私有资料不进 Git |
| 真实 PR/CI | [PR #21](https://github.com/zjl327707743/HBOS-Platform/pull/21) 已合并到 Portal 产品分支；当前 CI/制品以产品 HEAD `e4b16ee80aaaf21aac2304246a4de1f9fe8995ea` 为准 |
| 固定 Mac 入口 | P1 的 loopback 同源入口 5188 已运行；本机隐藏设密工具已提供，未自动修改密码 |
| Owner 本人验收 | Owner 已确认 Administrator 本人飞书成功登录；第二位员工开户、本人验证码与交接另行记录，合成测试不替代真人 |
| 公司服务器 | 未部署，固定 IP / 正式 HTTPS 后续；不影响已交付 Mac 状态 |

## 其他既有里程碑

M0 已完成并封板。考勤 M1 产品验收仍由 M1-FIX 主记录维护，不因本轮 Portal 代码测试而 closeout；M1-FIX-F 原状态为 REVIEWING。库存 M2-STOCK-R1 原状态为 IN_PROGRESS，其余独立轮次不由本任务推进。历史记录见 `docs/milestones/` 对应主文档，本公开状态摘要不携带人员、私有路径或内部运行报告。

本轮未回退或重建既有 Portal 开发分支，未重做 P0，未覆盖候选数据库，未重置原密码/角色。Owner 已选择 P1 作为固定本地使用环境；保留原 Site 和数据，未删除数据库、用户、文件或卷。公司生产首次部署另行授权。
