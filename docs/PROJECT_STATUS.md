# 2026-10-18 Owner 业务集成：考勤和生产已实际合并

最新已核对产品基线为 `4ddf9bebe5bd9f0d73cdb84bd4ddfa9b8615ad30`，实际父提交为考勤基线 `374e2bd8633d4127fabcc4659c2314e4a7ca7cd8`，代码树为 `dabf7846817f096434949bc38a48c7cc4ec958bd`。

完整 [#46 生产 PR](https://github.com/zjl327707743/HBOS-Platform/pull/46) 已普通 Squash Merge，来源 `3f0e8847f2769025d764214ae56950fe97693808` 保存于 `archive/owner-r3-pr46-3f0e884-20261018`；[Owner 正式审批](https://github.com/zjl327707743/HBOS-Platform/pull/46#pullrequestreview-5561524421) 与当前树的五项 CI、[28项真实服务链验证](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39098816237/job/117590685169) 均已核对。服务/AI 41+26项、Portal前端146项通过，AI模型调用与上游写入均为0。普通生产角色仍默认拒绝，Administrator 例外明确；代码集成不代表启用真实服务或完成车间范围授权。

#39 仓储正在新基线上继续真实库存、账务、外协放行、二维码与打印附件权限门禁；#43 LIMS 独立增量后置。当前远端产品 ref 与各 PR 的实际合并记录是后续更新的权威；下面保留每阶段的历史证据。

# 2026-10-18 Owner 业务集成：首个完整业务已合并

**#42 考勤已实际 Squash Merge** 到唯一产品分支 `feature/hbos-portal-product`。新产品提交为 `374e2bd8633d4127fabcc4659c2314e4a7ca7cd8`，父提交为 `45658fe4b84d8fb7dd4433c459aa30572e0d13d3`，树为 `31097c5f9e6f245ecbaca779643c421a4458bee8`；与已审批、已测试的真实组合相符。来源 `5780924fb000c869ddf7e23afa76e2f95fe15ea8` 保存在 `archive/owner-r3-pr42-5780924-20261018`。

证据：[实际 PR #42](https://github.com/zjl327707743/HBOS-Platform/pull/42)、[当前来源 Owner 审批](https://github.com/zjl327707743/HBOS-Platform/pull/42#pullrequestreview-5561462238)、[原生权限与导出补充验证](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39097688048/job/117587422856)。批次最终审批由 Owner 承担，依据 [本批次正式裁定](governance/HBOS_Owner_业务集成批次裁定_20261018.md) 执行，不伪造另一位人工审批，也不减免技术门禁。

后续以每次合并后的真实产品 HEAD 顺序验证 #46 生产、#39 仓储，#43 LIMS 独立增量后置。#55 物料只读子范围此前已合并；完整仓储不能据此算作完成。生产原生服务链、仓储库存账务和质检放行各以当前来源 SHA 的实际运行结果为准。历史环境验收不等于本轮部署；本轮仅使用远端源码与新建的云端合成 Site。

## 历史记录：2026-10-18 仓储物料只读候选

本轮从 #39 固定 HEAD `136e90dc102cc40d294650b8f463ac2e709c92cb` 单独提取物料浏览，使用已有 Portal Shell、原批准主从页面和 Frappe Item 原生 ACL。候选新增列表/搜索/详情与深链，保留库存原 Desk 默认入口；不携带 SQL 报表、二维码、附件导出、库存写入、调账、放行、角色或 Schema 修改。

本增量仅供非生产产品开发分支使用；实际合并与 CI 以 [PR #55](https://github.com/zjl327707743/HBOS-Platform/pull/55) 固定 HEAD 及最终 squash 为准。完整 #42/#43/#46/#39 均仍受各自高风险人工审查及运行门禁约束，不因本子范围进入代码基线而完成。真实 Site、IAM #52、main、Owner 本机项目均未操作。物料可见范围是既有 Item ACL，不等于仓库范围；无可见记录与服务失败明确区分。

# 项目状态

## 2026-10-10 HBOS 多 APP 集成治理（产品分支）

制定 `docs/governance/HBOS_CONCURRENT_APP_INTEGRATION_V1.md` 作为并行开发、PR 粒度与分批合并协作规范：Portal 任务以当前产品分支为基线，领域增量与共享入口分离，拉代码不自动 migrate。此项仅为治理文档，不代表 #33/#34/#37 的高风险代码或 #30 知识库已合并、不代表原本本机运行版本已更新。正式合并/验收按各 PR 最新 SHA 独立记录。


## 并行权限治理 IAM-0 — 2026-10-01

Owner 已批准进入统一身份与权限治理。当前仅交付设计、角色—动作—范围矩阵、只读源码盘点工具与本机任务书；实际 Site 盘点和隔离验收仍为 NOT_RUN，不修改账号、角色或业务数据，不替代原账号收尾。入口：[IAM-0 治理资料](governance/iam/README.md)。

## PR #21 合并后收口 — 2026-10-01

状态：**FINAL_REVIEW_PASS / MERGED_TO_PORTAL_PRODUCT**。PR #21 已使用 expected-head squash 合入 `feature/hbos-portal-product`，产品 HEAD `e4b16ee80aaaf21aac2304246a4de1f9fe8995ea`；Owner 最新无破坏验收 PASS，团队合成浏览器 final-submit 3/3 PASS，新 squash 四项 CI SUCCESS。旧 #22 已关闭未合并，IAM-0 由 clean Draft PR #23 仅承接原 11 文件增量；PR #15 仍 Open Draft，main 未变化。

合并前发现并修复的原生 MFA Administrator proof P1 已完成回归；本次收口未修改 Owner 密码、MFA、飞书绑定、Secret、业务数据或 P1 卷。合并前 BLOCKED/WAITING 状态继续作为历史证据保留，但不再作为当前项目状态。

团队后续 Portal Authority：`feature/hbos-portal-product@e4b16ee80aaaf21aac2304246a4de1f9fe8995ea`。

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
