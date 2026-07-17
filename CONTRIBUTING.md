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

- 至少 **1 名非作者**的批准后才能合并
- 所有 Review Conversation 必须解决
- 新提交推送后旧批准自动失效，需重新审查
- 合并方式：**Squash Merge**（将分支所有提交压缩为一个干净 commit）
- 合并后自动删除功能分支
- 普通成员**不得**使用 Owner 应急绕过能力

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

**日常开发不得绕过 PR、Review 和 CI 流程。** 每次使用应急权限必须补充审计记录。

---

> 如有疑问，请先查阅 `docs/team/10_团队日常开发SOP.md`，或联系 Owner。