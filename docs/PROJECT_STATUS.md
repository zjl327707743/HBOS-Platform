# 项目状态

项目：新乡海滨智能运营管理平台。架构：Frappe/ERPNext 开源底座 + Frappe 多 App 模块化架构 + 外部独立服务扩展。

## 当前 Portal 轮次 — 2026-09-30

本轮 Portal：Mac 本地完整运行与 GitHub 最新功能同步，状态 LOCAL_RUNNING / FUNCTION_VERIFIED / REMOTE_PR_TRACKED / LIVE_OWNER_PENDING。Owner 已明确选择复用 P1 Site、Compose project、原卷和已批准知识/设备；不再寻找历史正式库。公司服务器、固定 IP 和正式 HTTPS 是后续工作，不是本轮门禁。沿用已实现统一账号和五应用，不重做 P0。主记录：`docs/milestones/M1_RP3_统一账号飞书绑定与正式发布.md`；运行说明：`docs/deployment/Mac本地运行与团队同步.md`。继续更新 PR #21，base `feature/hbos-portal-product`，head `codex/portal-unified-account-release`；不推 main/base、不强推、不自动合并。

| 项目 | 实际状态 |
| --- | --- |
| 唯一 User 与密码/飞书账号流程 | 统一账号代码已实现并测试；当前 P1 密码记录保留，本人登录/OAuth 未执行 |
| 五应用与已批准前端 | Administrator 五入口实际打开；普通用户按原角色仅开放知识/设备；未实现项明确标注 |
| 备份恢复/保留校验/production 制品 | 当前 P1 原卷已备份并迁移，账号/密码/角色/权限/业务/身份指纹保留；Portal 与 LIMS 编译资产已部署 |
| 通用 Gateway/团队依赖 | 版本化通用代码、Dockerfile、完整 lock 已提供；私有资料不进 Git |
| 真实 PR/CI | [PR #21](https://github.com/zjl327707743/HBOS-Platform/pull/21)，Draft，base 为 Portal 产品分支；CI 以该 PR 的实际 Checks 为准；未合并 |
| 固定 Mac 入口 | P1 的 loopback 同源入口 5188 已运行；本机隐藏设密工具已提供，未自动修改密码 |
| Owner 本人验收 | 本人 Administrator 密码登录与飞书授权尚未执行；受控验证会话不代替本人 |
| 公司服务器 | 未部署，固定 IP / 正式 HTTPS 后续；不影响已交付 Mac 状态 |

## 其他既有里程碑

M0 已完成并封板。考勤 M1 产品验收仍由 M1-FIX 主记录维护，不因本轮 Portal 代码测试而 closeout；M1-FIX-F 原状态为 REVIEWING。库存 M2-STOCK-R1 原状态为 IN_PROGRESS，其余独立轮次不由本任务推进。历史记录见 `docs/milestones/` 对应主文档，本公开状态摘要不携带人员、私有路径或内部运行报告。

本轮未回退或重建既有 Portal 开发分支，未重做 P0，未覆盖候选数据库，未重置原密码/角色。Owner 已选择 P1 作为固定本地使用环境；保留原 Site 和数据，未删除数据库、用户、文件或卷。公司生产首次部署另行授权。
