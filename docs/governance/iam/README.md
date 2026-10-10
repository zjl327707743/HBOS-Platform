# HBOS 统一身份与权限治理

## 当前状态（2026-10-01）

Owner 已批准进入权限治理下一阶段。本分支只交付 IAM-0 设计与只读盘点准备，不启用新授权，不改变现有用户、角色、Site 或业务数据。

| 项目 | 状态 | 证据边界 |
| --- | --- | --- |
| 最新相关远端基线 | PINNED | PR #21 / `5ec35ec8510303a1c36475e80d33d57c9255d5d6`；不是生产运行证明 |
| 权限关键路径静态核对 | REVIEWED_SELECTED_PATHS | 见证据清单，不是全仓或运行时安全认证 |
| 授权架构和矩阵 | DRAFT_FOR_REVIEW | 延续 Owner 已认可方向，具体岗位授权尚未生效 |
| 源码盘点工具合成测试 | PASS 11/11 | 仅 Python 标准库单测，不连接 Frappe 或数据库 |
| 全仓源码工具执行 | NOT_RUN | 远端逐文件读取不冒充本地全仓扫描 |
| 固定本地 P1 Site 权限盘点 | NOT_RUN | 需要本机 Agent 按任务书只读采集 |
| 普通账号隔离测试 | NOT_RUN | 必须在隔离合成环境验证，不在原库试写 |
| 新权限实现 / 迁移 / 部署 | NOT_STARTED | 本 PR 无业务运行代码变更 |

## 阅读顺序

1. [IAM-0 权限现状与证据](IAM-0_权限现状与证据.md)
2. [IAM-1 统一授权架构决策](IAM-1_统一授权架构决策.md)
3. [IAM-1 角色动作范围矩阵](IAM-1_角色动作范围矩阵.md)
4. [IAM-0 本机只读盘点任务书](IAM-0_本机只读盘点任务书.md)
5. [IAM-2 隔离验收与迁移门禁](IAM-2_隔离验收与迁移门禁.md)

里程碑主记录：[M1-IAM0](../../milestones/M1_IAM0_统一身份与权限治理启动.md)。

## 不可突破的边界

统一 Frappe User / Session；Portal 与 Desk 分开入口能力；各 App 保留领域授权。知识库不提供原文下载，不开放浏览器直连网关或 get_source。保留已成功的飞书绑定、密码、MFA、企业/回调、原角色和身份交接机制。Owner 已选 P1 为固定本地环境，不能当临时库重建；公司服务器未部署。

不新建 App，不改 Frappe/ERPNext/HRMS 核心，不迁移、不建测试账号、不改角色、不清缓存/会话、不登录冒充用户、不触发业务同步。无真实人员/身份映射/内部范围名单/凭据/数据库/截图进入 GitHub。

## 分支与状态约定

权限治理使用独立 Draft PR，基于上述固定账号源码快照，目标为 `codex/portal-unified-account-release`；不直接推账号分支、Portal 产品分支或 main，不自动合并。上游继续推进时需另行比较差异，不能把旧快照称为始终最新。

本工作流是并行 IAM-0，不关闭或替换账号收尾、考勤和仓库里程碑。全局 CURRENT_MILESTONE 的既有账号轮次保持；本目录与独立主记录是 IAM 状态入口，PROJECT_STATUS 增加并行入口。合并时如上游状态冲突，只合并 IAM 增量，不覆盖其最新文字。

## 工具

`python3 -B -m unittest discover -s scripts/governance/tests -v`

源码盘点：`python3 -B scripts/governance/iam_source_inventory.py --repo <已核对的仓库> --source-commit <40位实际SHA>`。

输出包含相对代码路径、函数、行号、文件摘要和待复核标记；不导入业务模块、不连接 Site、不写文件。只能证明扫描发现了哪些词法入口，不能证明接口授权完整。源码版本由调用方独立核实，工具明确标记 EXTERNAL_REQUIRED。真实输出先保存在 Git 外私有目录，经审查后只共享脱敏结论。
