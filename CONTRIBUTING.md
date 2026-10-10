# 贡献指南

> 新乡海滨智能运营管理平台（HBOS）团队协作规范

## 核心规则

### 禁止直接在 `main` 分支开发

`main` 是受保护的生产就绪分支。**所有变更必须通过 Pull Request 合并。**

### 分支策略

- 从最新的 `origin/main` 创建功能分支
- 分支命名规范：

| 类型 | 格式 | 示例 |
|------|------|------|
| 功能 | `feat/<scope>-<description>` | `feat/attendance-monthly-report` |
| 修复 | `fix/<scope>-<description>` | `fix/import-duplicate-check` |
| 文档 | `docs/<description>` | `docs/api-guide` |
| 杂项 | `chore/<description>` | `chore/update-dependencies` |

- 禁止长期存在的个人分支；功能分支应在合并后尽快删除

### 提交前检查清单

- [ ] `git fetch origin` 拉取最新远程状态
- [ ] `git diff origin/main...HEAD` 检查与 `main` 的差异
- [ ] 执行本地测试：`docker compose exec backend python3 -m unittest discover -s apps/hb_attendance_app/tests -v`
- [ ] 检查是否误提交了敏感文件（见下方禁止项）
- [ ] 提交信息遵循约定式提交格式：`<type>: <description>`
- [ ] 将分支推送到个人远端：`git push -u origin <branch-name>`
- [ ] 在 GitHub 上创建 Pull Request

### 禁止提交的文件

| 禁止内容 | 原因 |
|----------|------|
| `.env` 及 `.env.*` | 包含数据库密码、API 密钥等敏感信息 |
| 数据库 dump、备份文件（`*.sql`、`*.sql.gz`） | 数据安全与体积 |
| 真实 Excel 考勤文件（`*.xlsx`、`*.xls`） | 员工隐私 |
| 真实数据 CSV | 员工隐私 |
| 私钥、证书（`*.pem`、`*.key`、`*.crt`） | 安全 |
| 日志文件（`*.log`） | 体积 |
| Site 配置文件 | 环境特定 |
| 上游 Frappe/ERPNext/HRMS 核心源码的修改 | 维护性 |

## Pull Request 规范

### PR 描述必须包含

1. **任务目标**：这个 PR 要达成什么
2. **变更范围**：改了什么文件、为什么改
3. **未做范围**：明确说明哪些不在本次变更中
4. **测试与验证**：测试命令、测试结果
5. **数据库或迁移影响**：是否有 schema 变更、是否需要 migrate
6. **配置资产影响**：是否修改了 docker-compose、环境变量、CI 配置
7. **安全与敏感数据检查**：确认无敏感文件提交
8. **Docker 影响**：是否需要重建容器或镜像
9. **文档更新**：是否同步更新了相关文档
10. **审查人关注点**：希望 reviewer 重点审查的部分
11. **是否涉及 Owner 授权的新阶段**：阶段性的 Gate 变更

### 审查与合并

- **main 分支及高风险变更**：至少 **1 名非作者**的有效 GitHub `Approve` 后才能合并；Owner 不得自批本人的 PR。
- **产品开发分支 Owner 自主合并**（自 2026-10-10 生效）：仅限 `feature/hbos-portal-product` 的非生产发布、低中风险或隔离候选代码。Owner 本人可在独立技术审查、关键问题闭环、必要测试和 CI 通过后，以明确的本轮 Owner 决定执行本人 PR 的 Squash Merge，无须伪造非作者 GitHub `Approve`。该 Owner 决定须记录在 PR Conversation 中，写明固定 base/head、审查结论、风险与不授权范围；AI 审查不等于 GitHub Approve。
- **不适用自主合并**：`main`、生产部署与真实数据/模型分发，以及登录/身份、IAM/角色/Grant、真实数据导出或权限绕过、敏感业务写入、数据库结构迁移、安全门禁削弱等高风险变更；这些继续履行非作者审查和专门发布授权。对风险有疑义时按高风险处理。
- 所有 Review Conversation 必须解决；存在有效 `Request Changes` 不得绕过。
- 新提交后需要对最新 HEAD 重新核验代码/安全审查和 CI；高风险/主分支既有人工 Approve 按规则更新。
- 合并方式：**Squash Merge**，并核对预期 HEAD、目标分支和实际 squash 提交。
- 功能分支全局默认可能自动删除；Owner 明确要求保留的来源分支必须在合并前落实备份与保留措施，并在合并后实读验证。
- 代码合并不等于安装、部署、公司员工授权、模型/知识资产分发或发布。
- 普通成员不得自行援引 Owner 自主合并或使用 Owner 应急绕过能力。

## 数据库与配置规范

- 数据库结构变更必须通过 Frappe DocType JSON 或 Patch 方式代码化
- 稳定配置项（如系统设置、自定义字段）必须代码化，不得仅在数据库中手动修改
- 迁移脚本必须可重复执行且幂等

## Codex 审查

- 重大 Gate（阶段里程碑）结束时进行一次 Codex 审查
- 日常 PR 不触发 Codex 审查
- Codex 审查由 Owner 发起

## 紧急修复流程

1. 从 `main` 创建 `fix/` 分支
2. 完成修复并测试
3. 创建 PR 并标注为紧急
4. 获得批准后 Squash Merge
5. **禁止**直接 push 到 `main`，即使紧急情况

## Owner 应急管理权限

Owner 保留仓库管理权限，但**仅限以下场景**：

- 仓库故障（如配置损坏导致 CI 无法运行）
- 严重安全事件（如密钥泄露需立即回滚）
- 门禁自身失效（如 Ruleset 配置错误阻止合法操作）

**日常开发不得绕过 PR、适用的审查和 CI 流程。** 上述产品开发分支的 Owner 自主合并是有记录的正常治理路径，不属于应急 Break-glass；应急权限仍须单独补充审计记录。

---

> 如有疑问，请先查阅 `docs/team/10_团队日常开发SOP.md`，或联系 Owner。