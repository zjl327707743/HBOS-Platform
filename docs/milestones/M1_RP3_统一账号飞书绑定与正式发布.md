# M1-RP3：统一账号、飞书绑定与正式发布

轮次代号 RP3 表示 Owner 授权的 Portal 执行任务书 v3，并非考勤历史 M1-R3。

状态：**REVIEWING / OWNER_TARGET_REQUIRED / LIVE_AUTH_REQUIRED / NOT_RELEASED**。

目标：升级承载原账号的已确认 Site，唯一 Frappe User 接通密码和飞书，完成五应用真实展示、版本化部署与真实 GitHub PR。正式验收 Gate 没有关闭。

## 已交付通用实现

- 原账号密码重新认证后绑定本人飞书；首次飞书登录先选择绑定已有账号或永久普通开户。不按姓名/邮箱匹配，不创建独立密码表。
- 密码less User 经本人收件验证码及原 MFA 设置密码；改密、解绑、身份唯一性/tombstone、邮件短时恢复与管理员受控签发、中央停用和旧会话/票据撤销。
- Frappe 原生密码 API 和 User 文档路径均要求强验证；外部映射只信任服务端验证上下文，客户端 Document.flags 无法伪造。旧飞书 Social Login Key fail-closed；保留 Administrator 原生登录，不自动授权普通飞书用户。
- 飞书明确离职/停用状态同步每五分钟，可显式启用；网络/权限/范围异常不自动停用本地密码，具体边界已说明并测试。
- 同一 Site 托管 production SPA、deep routes 与 API/assets/Desk；六 App + 通用 Gateway v1.2.0 + 版本锁 + 保护备份/隔离恢复/目标匹配/保留校验工具。
- 前端真实能力矩阵、管理员诊断、安全页面、空状态/错误/未实现控件整理，清除生产通知示例和错误捷径。

## 已验证与证据范围

受控测试 Site 上：真实 Frappe ORM/SQL 唯一约束、原生密码、TOTP、一次性票据、冲突和停用；标准 HTTP 登录、CSRF/Origin、无强验证设密拒绝、旧接口旁路拒绝、真实多会话撤销及停用后拒绝；Vue typecheck/production build。隔离恢复工具已验证完整 SQL 导入、归档可读及密钥存在，强化的逐项账号指纹对比继续用于最终目标备份。

测试身份均为合成；没有把原用户迁到测试库，没有重置原账号或 Administrator 的密码、角色。Browser 曾展示测试 Site 的 Administrator 五应用及诊断，后续会话失效已识别；这不是正式目标的本人表单登录/五入口完整验收。Owner 的数据库候选明细、备份、账号与运行报告留在私下，不放入 Git。

## 仍需真实放行

| Gate | 当前状态 |
| --- | --- |
| 原账号唯一数据源 | 已只读定位多个候选，集中待 Owner 确认；P1 测试库不作为原库 |
| 正式服务器与 HTTPS 域名 | 未提供可核验目标；不伪造正式入口 |
| 目标完整备份/恢复/升级 | 未经确认不操作候选数据库；已有可执行工具 |
| 飞书真实企业 OAuth/本人收件验证码 | 目标 Secret、回调、应用权限/内部范围发布未完成实测；不以 configured 代替 |
| 原 Administrator 表单与五应用验收 | 待已确认正式目标及本人登录 |
| 原业务用户权限/关联不回归 | 保留校验和诊断已实现；原账号现场验收未执行 |
| GitHub 团队同步 | 独立净化发布分支，PR 状态由真实 GitHub 结果同步 |
| 正式发布 | 未放行，不标记 COMPLETED |

## 配套文档

- `docs/deployment/统一账号与Portal正式部署说明.md`
- `docs/frontend/统一账号发布与前端完整性矩阵.md`
- `scripts/release/依赖版本锁.json`

本轮接续既有 Portal 成果；保留原开发分支及个人工作，净化发布分支从 Portal 产品分支派生。允许安全扫描后 commit/push/真实 PR；禁止推 main、强推、自动合并。没有重新执行 P0、没有扩展考勤或库存独立里程碑。
