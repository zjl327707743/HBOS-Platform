# 新乡海滨智能运营管理平台

Frappe/ERPNext 开源底座 + Frappe 多 App 模块化架构 + 外部独立服务扩展。

## 当前交付

本轮 Portal：统一账号与正式发布 v3，状态 REVIEWING / OWNER_TARGET_REQUIRED / LIVE_AUTH_REQUIRED / NOT_RELEASED。已接续既有 Knowledge/Twin 与五应用集成，实现账号双方验证、安全页面和 production 部署工具；尚未确认原账号正式 Site、正式 HTTPS 目标及本人飞书/原账号现场验收，不能标记正式交付完成。主记录：`docs/milestones/M1_RP3_统一账号飞书绑定与正式发布.md`。安全检查后允许功能分支 push 和真实 PR，PR base 明确为 `feature/hbos-portal-product`，不直接推 main、不强推、不自动合并。

平台已包含考勤、仓储库存、LIMS、Portal、知识助理与设备/数字孪生自定义 App。密码和飞书使用同一 Frappe User；原有业务权限仍由原 App 约束。通知、生成式知识回答、现场遥测、工艺动画及偏好同步尚未实现，具体状态见前端完整性矩阵。

- [项目状态](docs/PROJECT_STATUS.md)
- [当前里程碑](docs/CURRENT_MILESTONE.md)
- [团队部署、备份与回退](docs/deployment/统一账号与Portal正式部署说明.md)
- [前端完整性矩阵](docs/frontend/统一账号发布与前端完整性矩阵.md)

## 团队构建

在已审查的 clean checkout 使用 Node 22 执行 `bash scripts/release/build_bundle.sh`，生成同源 Portal 和 LIMS 编译资产及六 App 部署包。通用 Gateway 位于 `services/hbos_gateway`，依赖、基线与 HRMS commit 见 `scripts/release/依赖版本锁.json`。既有目标版本不得为了匹配基线而降级。

升级必须保留已确认原 Site/数据库，先备份并验证恢复，再迁移及核对原账号/角色/权限/业务关联。制品或 PR 不包含账号数据库、Secret、私有知识索引/原文或真实模型；这些经批准私下部署。

## 协作与边界

`AGENTS.md`、`CLAUDE.md` 为规则入口；进度以状态台账与对应里程碑为准。Portal 本轮不改变其他考勤/库存里程碑的 Owner 验收状态。禁止创建未知替代库、覆盖未知数据库、重置原密码/角色、发布凭据或私有资料。

团队取得代码与部署制品：[PR #21](https://github.com/zjl327707743/HBOS-Platform/pull/21)。正式发布 Gate 尚未关闭，详情见本轮主记录。
