# 项目状态

项目：新乡海滨智能运营管理平台。架构：Frappe/ERPNext 开源底座 + Frappe 多 App 模块化架构 + 外部独立服务扩展。

## 当前 Portal 轮次 — 2026-09-30

本轮 Portal 接续固定 Mac 环境，修复真实飞书成员拒绝，交付首次自动开户、拼音登录名及受控换绑/交接。状态 LOCAL_RUNNING / ACCOUNT_CHANGE_UPDATED / LIVE_MEMBER_PERMISSION_PENDING；Secret 与程序企业确认已完成，成员受雇信息权限已提交待审批。真人 OAuth、开户、查收验证码、恢复和交接独立验收。复用 P1 Site、Compose project、原卷、已批准知识/设备及 PR #21 最新代码；不重建、不清库、不重做模块。Owner 已批准当前 Site 的 Administrator 自助绑定许可与本人主动请求的收件验证码，仍须密码、已有 MFA、真实授权及明确确认。公司服务器与正式 HTTPS 继续留后续。主记录：`docs/milestones/M1_RP3_统一账号飞书绑定与正式发布.md`；常用说明：`docs/deployment/Mac本地运行与团队同步.md`。PR #21 的 base 为 `feature/hbos-portal-product`，head 为 `codex/portal-unified-account-release`；不强推、不合并、不推 main/base。

| 项目 | 实际状态 |
| --- | --- |
| 唯一 User 与密码/飞书账号流程 | 统一账号与受控变更已实现并分层测试；密码记录保留；本人新 OAuth 已诊断为成员字段缺失，尚未成功登录 |
| 五应用与已批准前端 | Administrator 五入口实际打开；普通用户按原角色仅开放知识/设备；未实现项明确标注 |
| 备份恢复/保留校验/production 制品 | 当前 P1 原卷已备份并迁移，账号/密码/角色/权限/业务/身份指纹保留；Portal 与 LIMS 编译资产已部署 |
| 通用 Gateway/团队依赖 | 版本化通用代码、Dockerfile、完整 lock 已提供；私有资料不进 Git |
| 真实 PR/CI | [PR #21](https://github.com/zjl327707743/HBOS-Platform/pull/21)，Draft，base 为 Portal 产品分支；CI 以该 PR 的实际 Checks 为准；未合并 |
| 固定 Mac 入口 | P1 的 loopback 同源入口 5188 已运行；本机隐藏设密工具已提供，未自动修改密码 |
| Owner 本人验收 | 本人新飞书授权已执行并定位拒绝；成功绑定/再登录、第二位员工开户与本人设密仍待操作；受控测试不替代本人 |
| 公司服务器 | 未部署，固定 IP / 正式 HTTPS 后续；不影响已交付 Mac 状态 |

## 其他既有里程碑

M0 已完成并封板。考勤 M1 产品验收仍由 M1-FIX 主记录维护，不因本轮 Portal 代码测试而 closeout；M1-FIX-F 原状态为 REVIEWING。库存 M2-STOCK-R1 原状态为 IN_PROGRESS，其余独立轮次不由本任务推进。历史记录见 `docs/milestones/` 对应主文档，本公开状态摘要不携带人员、私有路径或内部运行报告。

本轮未回退或重建既有 Portal 开发分支，未重做 P0，未覆盖候选数据库，未重置原密码/角色。Owner 已选择 P1 作为固定本地使用环境；保留原 Site 和数据，未删除数据库、用户、文件或卷。公司生产首次部署另行授权。
