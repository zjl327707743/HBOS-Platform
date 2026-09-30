# 项目状态

项目：新乡海滨智能运营管理平台。架构：Frappe/ERPNext 开源底座 + Frappe 多 App 模块化架构 + 外部独立服务扩展。

## 当前 Portal 轮次 — 2026-09-30

本轮 Portal：统一账号与正式发布 v3，状态 REVIEWING / OWNER_TARGET_REQUIRED / LIVE_AUTH_REQUIRED / NOT_RELEASED。已接续既有 Knowledge/Twin 与五应用集成，实现账号双方验证、安全页面和 production 部署工具；尚未确认原账号正式 Site、正式 HTTPS 目标及本人飞书/原账号现场验收，不能标记正式交付完成。主记录：`docs/milestones/M1_RP3_统一账号飞书绑定与正式发布.md`。安全检查后允许功能分支 push 和真实 PR，PR base 明确为 `feature/hbos-portal-product`，不直接推 main、不强推、不自动合并。

| 项目 | 实际状态 |
| --- | --- |
| 唯一 User 与密码/飞书账号流程 | 代码已实现，受控 Site 验证；真实企业授权未通过现场 Gate |
| 五应用与已批准前端 | 既有成果继续使用；缺项与真实权限见完整性矩阵 |
| 备份恢复/保留校验/production 制品 | 工具与 clean 构建流程已交付；原数据库未升级 |
| 通用 Gateway/团队依赖 | 版本化通用代码、Dockerfile、完整 lock 已提供；私有资料不进 Git |
| 真实 PR/CI | 由真实 GitHub 返回结果同步；未合并 |
| 正式入口/原业务用户/Administrator 最终验收 | 待目标确认与本人登录；NOT_RELEASED |

## 其他既有里程碑

M0 已完成并封板。考勤 M1 产品验收仍由 M1-FIX 主记录维护，不因本轮 Portal 代码测试而 closeout；M1-FIX-F 原状态为 REVIEWING。库存 M2-STOCK-R1 原状态为 IN_PROGRESS，其余独立轮次不由本任务推进。历史记录见 `docs/milestones/` 对应主文档，本公开状态摘要不携带人员、私有路径或内部运行报告。

本轮未回退或重建既有 Portal 开发分支，未重做 P0，未覆盖候选数据库，未重置原密码/角色。Owner 数据源确认后继续目标备份/恢复/部署/真实验收；不存在将 P1 测试库改名为正式原库的放行路径。
