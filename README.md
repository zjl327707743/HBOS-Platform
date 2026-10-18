# 新乡海滨智能运营管理平台

## 2026-10-18 R3 集成记录 / 验证基线

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
