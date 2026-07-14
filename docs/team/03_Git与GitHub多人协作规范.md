# 03 Git 与 GitHub 多人协作规范

> **面向读者**：本文件面向没有多人协作经验的团队成员编写。每个规则都附带「为什么」的解释——理解原因比记住规则更重要。

---

## 1. 仓库和权限

### 1.1 当前状态

| 项目 | 当前值 |
|------|--------|
| 仓库地址 | `https://github.com/zjl327707743/HBOS.git` |
| 可见性 | Private（私有） |
| 所属 | 个人账号 `zjl327707743` |
| 唯一分支 | `main` |
| 提交数 | 72 次 |
| 贡献者 | 1 人 |

### 1.2 个人账号 vs GitHub Organization

**当前状态：个人账号私有仓库。**

**短期建议（团队 2-5 人）**：保持个人账号私有仓库即可。GitHub 个人账号支持添加 Collaborator，无需迁移到 Organization。优点：

- 零迁移成本
- 协作人数在个人账号支持范围内
- 不需要管理 Organization 成员、团队、计费

**什么时候迁移到 Organization**：

- 团队超过 5 人且需要分组权限（如前端组、后端组）
- 需要 Org-level CI/CD secrets 和统一策略
- 需要多个仓库归属于同一组织
- 需要对接外部审计或合规要求

**为什么**：Organization 的核心价值在于团队分组和仓库级权限管理。团队人数少时，Collaborator 模式的管理成本更低。过早迁移到 Organization 会增加不必要的配置负担。

### 1.3 角色定义

| 角色 | 权限 | 谁能担任 | 可以做什么 | 不能做什么 |
|------|------|----------|------------|------------|
| **Owner** | 最高 | 项目负责人 | 管理 Collaborator、修改仓库设置、删除仓库、强制推送、绕过分支保护 | --（拥有一切权限） |
| **Maintainer** | 高 | 技术负责人/架构师 | Push 到受保护分支（如 main）、合并 PR、管理 Issue 和 PR 标签 | 删除仓库、管理 Collaborator |
| **Developer** | 中 | 所有开发人员 | 创建分支、推送分支、创建 PR、管理自己的分支 | 直接 Push 到 main、合并 PR、修改仓库设置 |
| **Reviewer** | 读+审 | 任何团队成员 | 查看代码、在 PR 上评论、批准/请求修改 | Push、合并 |

**为什么**：角色的本质是「最小权限原则」——每个人只拥有完成自己工作所需的最小权限。Developer 不能直接 Push main 不是不信任，而是确保所有代码变更都经过审查。

### 1.4 最小权限原则

1. **默认权限最低**：新加入的成员默认为 Developer，不授予 Maintainer。
2. **提权需审批**：任何角色升级需要 Owner 明确批准。
3. **临时提权要回收**：如果需要某人临时拥有更高权限（如处理紧急修复），完成后立即降回原角色。

**何时授予 Maintainer**：只有同时在项目中承担「技术负责人/架构师」角色的人员。Maintainer 能合并 PR，这个权限直接影响 main 分支的质量。

### 1.5 离职和权限回收流程

当团队成员离开项目时，必须在**最后一个工作日当天**完成以下操作：

1. **移除 Collaborator 权限**：Owner 在 `Settings > Collaborators and teams` 中移除该成员。
2. **吊销 Personal Access Token**：如果该成员申请过 Token，在 `Settings > Personal access tokens` 中吊销。
3. **轮换共享密钥**：如果该成员接触过任何共享 Secret（CI 环境变量、数据库密码等），必须在移除成员后立即轮换。
4. **检查部署密钥**：在 `Settings > Deploy keys` 中删除该成员的 SSH 密钥。

**为什么**：离职后残留的访问权限是最常见的安全漏洞来源。即使信任离开的同事，也必须按流程回收权限——这不是针对个人，而是安全底线。

### 1.6 CI Token 和机器人账号

1. **CI/CD 使用独立 Token**：不要使用个人的 GitHub Token 配置 CI/CD。使用 GitHub Actions 自带的 `GITHUB_TOKEN` 或创建专用 Fine-grained personal access token。
2. **机器人账号规则**：
   - 如果一个自动化流程需要独立的 GitHub 身份（如自动发布 Release），使用 GitHub App 而非个人账号 Token。
   - 机器人 Token 的权限必须是代码库所有 Token 中最低的。
3. **不共享个人 Token**：任何情况下不得将自己的 GitHub Personal Access Token 分享给他人。如果需要共享访问，通过添加 Collaborator 解决。Token 泄漏后，立即在 `Settings > Personal access tokens` 中吊销并重新生成。

---

## 2. 分支策略

### 2.1 三种主流分支策略比较

| 维度 | GitHub Flow | GitFlow | GitLab Flow |
|------|------------|---------|-------------|
| **分支数量** | 最少（main + feature 分支） | 最多（master, develop, feature, release, hotfix） | 中等（main + feature + 可选的 environment 分支） |
| **复杂度** | 最低 | 最高 | 中等 |
| **适合团队规模** | 1-10 人 | 10+ 人，有正式发布周期 | 5-20 人，需要环境分支 |
| **发布频率** | 持续发布 | 定期大版本发布 | 持续或定期发布 |
| **学习成本** | 极低 | 高 | 中等 |
| **主要分支** | `main` | `master` + `develop` | `main` |

### 2.2 推荐策略：GitHub Flow

**HBOS 项目使用 GitHub Flow。** 规则如下：

```
main（唯一长期分支）
  ├── feature/xxx（短生命周期，从 main 拉出，合并后删除）
  ├── fix/xxx
  ├── docs/xxx
  ├── chore/xxx
  └── hotfix/xxx（紧急修复，从 main 拉出，合并后删除）
```

**工作流程**：

1. 从 `main` 创建分支
2. 在分支上开发和提交
3. 打开 Pull Request
4. 代码审查并讨论修改
5. 合并到 `main`
6. 删除分支

### 2.3 为什么不用 GitFlow

GitFlow 有 `master`、`develop`、`feature`、`release`、`hotfix` 五种分支类型，对当前 HBOS 团队来说有几大问题：

1. **过度设计**：2-5 人的团队不需要 `develop` 分支。`develop` 分支的本意是在短时间内汇集大量 feature 分支进行集成，然后整体发布。小团队的 feature 分支数量少、合并频率低，`develop` 只增加了同步负担。
2. **合并次数翻倍**：每次发布需要 `feature -> develop` 和 `develop -> master` 两次合并，增加冲突概率。
3. **认知负担高**：没有多人协作经验的团队需要先理解五种分支类型各自的用途和生命周期，学习曲线陡峭。
4. **HBOS 目前没有正式大版本发布周期**：GitFlow 假设定期发布为常规操作，但 HBOS 当前阶段以持续交付为主。

**为什么**：分支策略的选择取决于团队规模和发布模式，而不是「越复杂越专业」。对一个仍在功能验证阶段、2-5 人的团队，GitHub Flow 的分支结构刚好匹配实际需求，不多不少。

### 2.4 为什么不推荐 develop 分支

`develop` 分支在以下几种情况下有价值：

- 团队 10+ 人，同时有多条 feature 分支需要集成测试
- 有专职 QA 团队在 develop 分支上做集成测试
- 发布频率严格固定（如每月一次大版本）

**HBOS 当前不具备这些条件。** 引入 develop 分支只会造成以下问题：

- 开发者需要频繁在 `main` 和 `develop` 之间同步
- 紧急修复需要同时合并到两个分支，容易遗漏
- PR 目标分支选择困惑（应该合到 main 还是 develop？）

**正确的做法**：所有的开发分支都从 `main` 拉出，直接合并回 `main`。当项目真正需要集成测试环境时，再从实际需求出发引入环境分支，而不是照搬教科书。

---

## 3. 分支命名规范

### 3.1 命名格式

```
<类型>/<描述>

要求：
- 全部使用英文小写字母
- 单词之间用短横线 `-` 连接
- 不使用下划线 `_`
- 描述简洁，一眼能看出分支目的
- 总长度建议不超过 50 个字符
```

### 3.2 类型与示例

| 类型 | 用途 | 示例 | 生命周期 |
|------|------|------|----------|
| `feature/` | 新功能开发 | `feature/attendance-monthly-report`、`feature/employee-import-excel` | 从 main 拉出，PR 合并后删除 |
| `fix/` | Bug 修复 | `fix/login-timeout-error`、`fix/attendance-late-entry-missing` | 同上 |
| `docs/` | 文档增改 | `docs/git-collaboration-guide`、`docs/api-reference-update` | 同上 |
| `chore/` | 杂项（配置、依赖、工具） | `chore/update-frappe-v16.26.3`、`chore/add-pre-commit-hooks` | 同上 |
| `hotfix/` | 紧急线上修复 | `hotfix/production-login-broken` | 同上，但优先级最高 |

### 3.3 更多示例

```
# 好
feature/shift-schedule-management
fix/employee-name-display-encoding
docs/milestone-m1-fix-b5-report
chore/docker-compose-redis-healthcheck
hotfix/attendance-import-null-pointer

# 不好（避免这样写）
feature/我的考勤功能        # 不要用中文
fix/something             # 不要用模糊描述
dev/zjl/bug-fix           # 不要加个人名字前缀
feature/add_A_new_module  # 不要用下划线
FEATURE/LoginPage         # 不要用大写
```

**为什么用英文小写 + 短横线**：

- **兼容性**：不同操作系统对大小写的处理方式不同（Windows 不区分，Linux 区分），小写避免分支名在跨平台时出问题。
- **URL 友好**：分支名可能出现在 GitHub URL 中，短横线可读性优于下划线。
- **一致性**：团队统一命名规范后，任何成员看到分支名就知道它的类型和目的。

---

## 4. Commit 规范

### 4.1 Conventional Commits 格式

```
<类型>: <简短描述>

<可选的详细正文>

<可选的脚注>
```

### 4.2 类型

| 类型 | 含义 | 使用场景 |
|------|------|----------|
| `feat` | 新功能 | 新增一个用户可见的功能 |
| `fix` | Bug 修复 | 修复一个产品缺陷 |
| `docs` | 文档 | 增改文档（README、开发指南、API 文档等） |
| `test` | 测试 | 新增或修改测试代码 |
| `refactor` | 重构 | 改变代码结构但不改变功能 |
| `chore` | 杂项 | 依赖更新、构建配置、CI 配置等 |
| `build` | 构建 | 影响构建系统或外部依赖的变更 |
| `ci` | CI/CD | 持续集成/部署的配置变更 |

### 4.3 HBOS 特定规则

**描述使用中文**，类型使用英文。这与项目当前惯例一致：

```
feat: 新增考勤月度汇总报表
fix: 修复 Employee Checkin 导入时 null pointer 异常
docs: 完成 M1-FIX-B5 数据链路与报表口径收敛
chore: 升级 Frappe 至 v16.26.3
refactor: 提取打卡流水解析为独立工具函数
test: 补齐 Attendance 数据链路单元测试
build: 新增 Docker Compose healthcheck 配置
ci: 添加 GitHub Actions PR 自动检查
```

### 4.4 一次 Commit 应该包含什么

**一个逻辑单元**。一个 Commit 应该是一次完整的、可理解的、可回滚的变更。判断标准是：如果有人想撤销这次修改，只撤销这一个 Commit 就能回到干净状态。

包含以下内容就是好的 Commit：
- 实现一个完整的小功能（如「新增考勤导入日志 DocType」）
- 修复一个 Bug（如「修复登陆页中文乱码」）
- 一次文档更新（如「完成 M1-FIX-B5 方案文档」）
- 一次配置变更（如「为 Frappe backend 容器添加 healthcheck」）

### 4.5 一次 Commit 不应该包含什么

| 不应该包含 | 为什么 | 应该怎么做 |
|------------|--------|------------|
| 混合无关修改 | 一个 Commit 修了 Bug 又改了配置又加了文档——无法理解、无法单独回滚 | 拆成三个独立 Commit |
| 大文件（>1MB） | 二进制文件（Excel、图片、PDF）每次提交都会永久保存在 Git 历史中，仓库体积膨胀不可逆 | 大文件用 Git LFS 管理，测试数据用 `.gitignore` 排除 |
| Secret / 密钥 | 一旦提交，即使立即删除也无法从 Git 历史中彻底抹去 | 使用 `.env` 文件（已在 `.gitignore` 中排除），通过环境变量传入 |
| 未完成的功能 | 提交不完整的代码会导致其他开发者拉取后无法运行 | 在本地完成后再提交；如果必须中断，用 `git stash` 暂存 |
| 调试代码 | `console.log`、`print()` 等调试语句 | 提交前清理 |
| 生成文件 | 编译产物、日志、缓存、依赖包 | 在 `.gitignore` 中排除 |

### 4.6 提交粒度

**不要攒大量修改在一个 Commit 里。** 开发过程中频繁提交，每个提交做一件事。

```
# 好：多个小 Commit
feat: 新增 HBOS Import Log DocType
feat: 新增导入日志列表视图
feat: 新增导入日志统计脚本
fix: 修复导入日志日期字段无效值

# 不好：一个大 Commit
feat: 完成整个导入日志功能（含 DocType、视图、脚本、修复）  # 范围太大
```

**为什么**：小 Commit 更容易审查、更容易定位问题、更容易回滚。如果一个大 Commit 引入了 Bug，需要整个回滚，而小 Commit 可以细粒度地只回滚出问题的那个。

---

## 5. Pull Request

### 5.1 核心规则

1. **禁止直接向 main 推送**：所有变更必须通过 Pull Request 合并。这是代码质量的最后防线。
2. **每项任务一个 PR**：一个 PR 解决一个问题。不要在一个 PR 中混合多个不相关的变更。
3. **PR 创建者不能自己合并**：需要至少一个其他人审查。

### 5.2 PR 描述模板

创建 PR 时，使用以下模板填写描述：

```markdown
## 变更概述
<!-- 用 2-3 句话说明这个 PR 做了什么、为什么要做 -->

## 变更范围
<!-- 列出修改的文件和模块 -->
- `hb_attendance_app/hb_attendance_app/doctype/hbos_import_log/`
- `hb_attendance_app/hb_attendance_app/doctype/hbos_import_log/hbos_import_log.json`
- `hb_attendance_app/hb_attendance_app/doctype/hbos_import_log/hbos_import_log.py`

## 验证结果
<!-- 你做了什么验证？功能是否通过？ -->
- [ ] 本地 Frappe Desk 功能验证通过
- [ ] 导入测试：导入 50 条打卡记录，全部成功匹配 Employee
- [ ] 异常场景验证：Employee 不存在的记录正确跳过并记录日志

## 数据库迁移（如有）
<!-- 是否有新增 DocType、Custom Field、Patch？说明迁移步骤与回滚方式 -->
- 新增 DocType `HBOS Import Log`，含 8 个字段
- 迁移自动触发（`bench migrate`），无需手动操作
- 回滚方式：删除 DocType（仅含日志数据，不影响业务数据）

## 截图（如有 UI 变更）
<!-- 如果修改了前端或 Frappe Desk UI，附上截图 -->

## 回滚方法
<!-- 如果这个 PR 需要回滚，怎么做？ -->
回滚 commit 即可，无数据库破坏性变更。

## 风险
<!-- 这个 PR 有什么风险？是否影响已有功能？ -->
- 低风险：新增 DocType 不影响现有功能
- `bench migrate` 会自动执行，部署后需观察 migrate 日志
```

### 5.3 Reviewer 指定

1. **默认 Reviewer**：项目的 Maintainer 或技术负责人。
2. **跨模块修改**：如果修改涉及多个模块，指定对应模块的负责人。
3. **至少一人**：每个 PR 至少被一人审查通过后才能合并。
4. **敏感变更**：涉及数据库结构、权限、安全的 PR，必须由 Owner 或 Maintainer 审查。

### 5.4 Owner 验收

以下情况需要 Owner 验收：

- 影响现有业务逻辑的变更
- 新增用户可见的功能
- 涉及安全、权限、认证的变更
- 数据模型变更（新增或修改 DocType）
- 影响部署或运维的变更

**Owner 验收不等于代码审查。** 代码审查由技术负责人完成（关注代码质量），Owner 验收关注功能是否符合预期（关注产品意图）。

### 5.5 AI 生成代码必须人工检查

如果代码由 AI（包括 Claude Code、GitHub Copilot 等）辅助生成，必须在 PR 描述中明确标注并完成人工检查：

```markdown
## AI 辅助声明
- [ ] 本 PR 部分代码由 AI 辅助生成
- [ ] 已人工逐行审查所有 AI 生成的代码
- [ ] 变量命名、逻辑正确性、边界条件已确认
- [ ] 无硬编码密钥、Token 或敏感信息
- [ ] 无虚假设（如「假设数据格式为……」未在代码中显式处理）
```

**为什么**：AI 生成的代码可能包含安全隐患、与实际业务不符的逻辑、或对 Frappe/ERPNext 的 API 使用不正确。人工检查是必要的安全网。

---

## 6. 代码审查

### 6.1 审查清单

审查者在 Review PR 时必须逐项确认：

**功能性**
- [ ] 代码实现的功能与 PR 描述一致
- [ ] 边界条件已处理（空值、最大值、异常输入）
- [ ] 错误处理完整（不会静默吞掉错误）
- [ ] 数据库操作使用了参数化查询（Frappe ORM 默认防注入，但自定义 SQL 必须检查）

**安全性**
- [ ] 无硬编码密钥、Token、密码
- [ ] 无调试日志（`console.log`、`print`、`frappe.log_error` 中的敏感数据）
- [ ] 用户输入已验证
- [ ] 权限检查已到位（Frappe `has_permission` 或在 Doctype 中配置）

**代码质量**
- [ ] 变量和函数命名清晰
- [ ] 函数不超过 50 行
- [ ] 文件不超过 800 行
- [ ] 无深层嵌套（不超过 4 层）
- [ ] 重复代码已提取
- [ ] 符合项目现有代码风格

**可维护性**
- [ ] 关键逻辑有注释说明
- [ ] 新增或修改的 DocType 字段含义清晰
- [ ] 如有数据库变更，迁移和回滚方式已说明

### 6.2 谁可以审查

- **所有 Developer 都可以审查**：审查不是 Maintainer 的专属职责。阅读和理解别人的代码是提升团队整体水平最好的方式。
- **PR 作者不能审查自己的 PR**：审查者不能是 PR 作者本人。
- **新人也可以审查**：新成员审查他人代码时可以侧重可读性和理解障碍——「如果我看不懂，说明代码或注释需要改进」。

### 6.3 审查决策

| 决策 | 含义 | 下一步 |
|------|------|--------|
| **Approve（批准）** | 代码通过审查，可以合并 | PR 作者合并（或 Maintainer 合并） |
| **Comment（评论）** | 有建议或问题，但不阻塞合并 | PR 作者自行判断是否修改后合并 |
| **Request Changes（请求修改）** | 有必须修复的问题，合并被阻止 | PR 作者修复后重新请求审查 |

### 6.4 审查时间预期

| PR 大小 | 预期首次审查时间 | 预期完整审查周期 |
|---------|-----------------|------------------|
| 小（<50 行，简单修改） | 4 小时内 | 半天内 |
| 中（50-200 行，一个完整功能） | 1 个工作日内 | 1-2 个工作日 |
| 大（200-500 行，多个关联文件） | 1-2 个工作日 | 2-3 个工作日 |

**为什么**：没有人喜欢提交 PR 后石沉大海。设定时间预期让团队成员知道什么时候该跟进。如果超过预期时间没有得到审查，请直接在团队沟通渠道上提醒。

### 6.5 审查礼仪

1. **对代码不对人**：使用「这段逻辑在 XX 情况下可能抛出异常」而不是「你写错了」。
2. **区分必须修改和建议修改**：用「必须」表示阻塞性问题，用「建议」表示改进意见。
3. **不要审查风格问题**：风格交给自动化工具（formatter、linter），审查者聚焦逻辑、架构和安全。
4. **给出具体建议**：不要只说「这里有问题」，给出改进方案或参考代码。
5. **收到审查意见后不要防御**：审查者的目标是提升代码质量，不是否定你的能力。

---

## 7. 合并策略

### 7.1 三种合并方式比较

| 方式 | 效果 | main 分支历史 | 适用场景 |
|------|------|--------------|----------|
| **Merge commit** | 保留分支完整历史，创建一个合并提交 | 完整但噪音多（每个 PR 有几个 commit 就有几个条目） | 大型开源项目，需要完整审计追踪 |
| **Squash merge** | 将分支上所有 commit 压缩为一个 commit 再合并 | 干净，每个 PR 一个 commit | **推荐：中小团队、持续交付** |
| **Rebase merge** | 将分支上的 commit 按顺序 replay 到 main 顶端 | 线性历史，无合并提交 | 追求线性历史但不想丢失粒度 |

### 7.2 推荐策略：Squash Merge

**HBOS 项目使用 Squash merge。**

```
# 分支上有 3 个 commit
fix: 修复导入手册字段名错误
fix: 补充 Employee 不存在时的错误提示
fix: 修复导入日志日期格式为 ISO 8601

# Squash merge 后在 main 上合并为 1 个 commit
fix: 修复考勤导入字段名、Employee 匹配与日期格式问题 (#42)
```

**为什么推荐 Squash merge**：

1. **main 历史干净**：每个 PR 在 main 上就是一个 commit。回溯时非常清晰——一个 commit = 一个完整体积的变更。
2. **易于回滚**：如果一个 PR 引入了问题，`git revert` 只需要处理一个 commit。
3. **对审查友好**：审查者不需要对着 15 个微 commit 来回切换理解变更全貌。

**什么时候不用 Squash merge**：

- 当分支上的每个 commit 都是独立且有意为之的逻辑单元时，可以考虑 Rebase merge 保留粒度。但对当前团队规模和经验水平，Squash merge 是更安全的选择。

### 7.3 谁能合并

- **Maintainer**：可以合并所有 PR。
- **Developer**：可以合并自己创建且已通过审查的 PR（需 Maintainer 在仓库设置中开启）。
- **建议默认做法**：PR 作者提交 PR、他人审查、Maintainer 执行合并。这样确保至少两个人参与了每一次 main 分支变更。

### 7.4 什么时候不能合并

| 条件 | 操作 |
|------|------|
| CI 未通过 | **不能合并**。必须先修复 CI 失败。 |
| 有未解决的「Request Changes」 | **不能合并**。必须先处理审查意见。 |
| 存在合并冲突 | **不能合并**。必须先解决冲突（见 7.5）。 |
| PR 描述不完整 | **不应合并**。要求 PR 作者补全描述，特别是变更范围和回滚方法。 |
| Owner 验收未通过 | **不能合并**（仅适用于需要 Owner 验收的变更，见 5.4）。 |

### 7.5 冲突解决步骤

当分支与 `main` 发生冲突时：

```bash
# 1. 切换到你的分支
git checkout fix/attendance-import-bug

# 2. 确保本地 main 是最新的
git checkout main
git pull origin main

# 3. 回到你的分支，合并 main
git checkout fix/attendance-import-bug
git merge main

# 4. 如果提示冲突，Git 会告诉你哪些文件冲突
# 打开冲突文件，找到 <<<<<<<, =======, >>>>>>> 标记
# 手动选择保留哪一方的修改，或合并双方修改

# 5. 解决后标记为已解决
git add <冲突文件>

# 6. 完成合并
git commit -m "chore: 解决与 main 的合并冲突"

# 7. 推送
git push origin fix/attendance-import-bug
```

**冲突解决原则**：

1. **理解双方修改再决策**：不理解为什么要这样写之前，不要随便覆盖他人的代码。
2. **与原作者沟通**：如果你不确定某个冲突内容应该保留哪个版本，直接在 PR 评论区问原作者。
3. **完整测试**：解决冲突后，必须在本地运行验证，确保合并后的代码功能正常。

---

## 8. 版本与标签

### 8.1 App 版本号规则

HBOS 自定义 Frappe App 使用语义化版本号（Semantic Versioning）：

```
<主版本号>.<次版本号>.<修订号>

示例：1.3.2

1  = 主版本号（有不兼容的 API 变更时递增）
3  = 次版本号（新增向下兼容的功能时递增）
2  = 修订号（向下兼容的问题修复时递增）
```

| 变更类型 | 版本号变化 | 示例 |
|----------|-----------|------|
| 不兼容的 API 变更、重大架构改动 | 主版本号 +1，次版本号和修订号归零 | `1.3.2` -> `2.0.0` |
| 新增向下兼容的功能 | 次版本号 +1，修订号归零 | `1.3.2` -> `1.4.0` |
| Bug 修复、性能优化 | 修订号 +1 | `1.3.2` -> `1.3.3` |
| 开发阶段 | 主版本号 0 | `0.1.0`、`0.2.0` |

**HBOS 当前处于开发阶段，版本号应为 `0.x.x`。** 进入正式生产发布后，升级为 `1.0.0`。

### 8.2 Release Tag 格式

```bash
# 为 App 创建 Release Tag
git tag -a v1.3.2 -m "v1.3.2: 新增考勤月度汇总报表，修复导入 null pointer 问题"

# 推送 Tag 到远端
git push origin v1.3.2
```

**Tag 命名规则**：`v<语义化版本号>`，例如 `v0.3.1`、`v1.0.0`。

**什么时候打 Tag**：
- 每次完成一个里程碑的功能集合并发布时
- 每次修复一个紧急上线 Bug 发布 hotfix 后
- 不要为每个 PR 合并打 Tag，Tag 是给「发布版本」用的

### 8.3 Changelog 维护

在 App 根目录维护 `CHANGELOG.md`，每次发布时更新：

```markdown
# Changelog

## [0.3.1] - 2026-07-14

### Added
- 新增考勤月度汇总报表
- 新增 HBOS Import Log 导入批次追踪

### Fixed
- 修复 Employee Checkin 导入时姓名字段匹配大小写敏感问题
- 修复导入日志中文乱码

### Changed
- 导入默认班次从固定 08:30-17:30 改为支持班次模板配置

## [0.3.0] - 2026-07-01

### Added
- 新增 Excel 考勤机导出表识别与导入
- 新增 Employee 自动创建与匹配
```

### 8.4 依赖版本矩阵

| 组件 | 当前版本 | 版本策略 |
|------|---------|----------|
| Frappe Framework | 16.25.0 | 跟随官方 release，不跨主版本 |
| ERPNext | 16.26.2 | 跟随官方 release，不跨主版本 |
| HRMS | 16.12.0 (version-16) | 固定 version-16 分支，不追 version-17 |
| HBOS Attandance App | 0.x.x | 内部语义化版本 |
| MariaDB | 11.8 | 跟随 Docker Compose 配置 |
| Redis | 6.2-alpine | 稳定版本，不频繁变更 |

**为什么**：Frappe/ERPNext/HRMS 的版本是耦合的——HRMS version-16 只兼容 Frappe/ERPNext >=16.0.0 <17.0.0。跨主版本升级需要评估全量兼容性，不能随意进行。

---

## 9. 常见场景处理

### 9.1 紧急修复（Hotfix）

当 main 分支上发现紧急 Bug 需要立即修复：

```bash
# 1. 从 main 拉出 hotfix 分支
git checkout main
git pull origin main
git checkout -b hotfix/login-null-pointer

# 2. 修复 Bug 并提交
git add .
git commit -m "fix: 修复登录页 null pointer 导致 500 错误"

# 3. 推送分支
git push origin hotfix/login-null-pointer

# 4. 立即创建 PR，标题加 [紧急] 前缀
# PR 标题: [紧急] fix: 修复登录页 null pointer

# 5. 通知 Reviewer 优先处理

# 6. 合并后删除分支
git branch -d hotfix/login-null-pointer
```

**Hotfix 特殊规则**：

1. **最小改动原则**：只修复问题本身，不要在 hotfix 中夹带其他修改。
2. **优先审查**：通知 Reviewer 立即处理，必要时直接当面沟通。
3. **合并后验证**：合并到 main 后，在本地拉取最新代码验证修复生效。
4. **补 Tag**：如果是生产环境的紧急修复，合并后给修复版本打 Tag。

### 9.2 冲突解决

（详细步骤见 7.5）

**冲突的心理准备**：

- 冲突是正常的。它不等于你做错了什么，只是多人同时修改了同一段代码。
- 解决冲突时优先沟通而不是猜测。在 PR 评论区问一句「你这部分逻辑的原因是什么」只需要 30 秒，比猜错后引入 Bug 代价小得多。

### 9.3 回滚一个已合并的 PR

```bash
# 1. 切换到 main
git checkout main
git pull origin main

# 2. 找到那个 PR 合并后的 commit hash
# GitHub PR 页面的合并 commit 通常在 PR 底部可见
# 或者用 git log 查找
git log --oneline -20

# 3. 使用 git revert 创建一个反向 commit
git revert <commit-hash>
# 示例：git revert a1b2c3d

# 4. 如果是 Squash merge，commit message 格式如下：
# revert: 回滚导入日志 DocType (#42)
#
# 原因：导入后 Employee 匹配性能严重下降，需重新设计方案后重新提交

# 5. 推送
git push origin main
```

**为什么用 `git revert` 而不是 `git reset`**：

- `git revert` 创建一个新的 commit 来撤销变更，不修改历史——其他人已经基于这个 commit 在开发了，强制改历史会导致他们的分支混乱。
- `git reset` 修改历史，只能用于尚未推送到远端的本地分支。
- **对 main 绝对禁止 `git reset --hard`。**

### 9.4 多人在同一文件上工作

**场景**：你和同事都在修改同一个文件的同一个区域。

**最佳实践**：

1. **提前沟通**：如果你知道要修改某个复杂文件，在团队沟通渠道上先说一声：「我要动 `attendance.py` 里的导入逻辑，大概改 50 行」。
2. **拆分文件**：如果一个文件频繁引发多人冲突，说明它太臃肿了。考虑拆分为多个小文件，每人负责不同文件。
3. **小步快跑**：改完一小部分就提交、创建 PR、合并，减少同时修改的概率。
4. **拉取最新代码**：开始工作前先 `git pull`，确保基于最新版本。

**冲突发生时**：

```bash
# 假设你和同事都修改了 hb_attendance_app/.../attendance.py
# 你的分支先合并了，同事后来创建 PR 时发现冲突

# 同事的操作：
git checkout main
git pull origin main
git checkout fix/colleagues-change
git merge main
# 手动解决冲突
git add attendance.py
git commit -m "chore: 解决 attendance.py 与你分支的合并冲突"
git push origin fix/colleagues-change
# 推送后 PR 自动更新，可继续审查
```

**规则**：先合并的人不用处理冲突，后合并的人负责解决冲突。这是减少团队摩擦的自然规则。

---

## 附录 A：Git 命令速查

| 操作 | 命令 |
|------|------|
| 创建并切换到新分支 | `git checkout -b feature/xxx` |
| 查看当前分支 | `git branch` |
| 切换到已有分支 | `git checkout <分支名>` |
| 查看文件变更 | `git status` 或 `git diff` |
| 暂存变更 | `git add <文件>` |
| 提交 | `git commit -m "类型: 描述"` |
| 推送分支 | `git push origin <分支名>` |
| 拉取最新 main | `git checkout main && git pull origin main` |
| 删除本地分支 | `git branch -d <分支名>` |
| 查看提交历史 | `git log --oneline -20` |
| 放弃本地未提交的修改 | `git checkout -- <文件>` （谨慎使用）|

## 附录 B：常见问题

**问：我忘记创建分支、直接在 main 上改了怎么办？**

答：不要 commit。先 `git stash` 暂存修改，然后 `git checkout -b feature/xxx` 创建新分支，再 `git stash pop` 恢复修改。如果已经 commit 了但没有 push，联系 Maintainer 帮忙把 commit 移到新分支上。

**问：我的 PR 太小了，要不要合并几个小 PR 再提？**

答：不要合并。小 PR 是最受欢迎的 PR——审查快、风险低、回滚简单。宁可被同事说「你 PR 太小了」也不要被说「你的 PR 我看了一个小时还没看完」。

**问：我该多久提交一次 Commit？**

答：做完一个可以运行的小步骤就提交。没有固定频率，但如果你发现自己写了一个小时还没提交过，说明你的提交粒度可能太大了。

---

> **维护信息**：本文件由项目 Maintainer 维护。规则变更需通过 PR 流程，经团队讨论通过后生效。最后更新：2026-07-14。
