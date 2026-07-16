# 10 团队日常开发 SOP

> **面向读者**：HBOS 项目组全体成员（无多人协作经验）
> **前置阅读**：
> - `03_Git与GitHub多人协作规范.md`（分支、提交、PR 规则）
> - `12_常用Git与Docker命令解释.md`（每条命令的含义）
> **目的**：把"每天从上班到下班"的每一步都写成清单，跟着做就行。

---

## 1. 开工前（每日）

> 每天早上到工位后的第一件事。

### 1.1 检查清单

- [ ] **1. 确认 Docker 环境在运行**

  ```bash
  # 进入项目目录（将 <你的HBOS项目路径> 替换为你的实际路径）
  export HBOS_HOME="<你的HBOS项目路径>"
  cd "$HBOS_HOME"
  docker compose ps
  ```

  输出应该看到至少 `backend`、`frontend`、`db` 三个容器 `Up`（运行中）。

  如果容器没启动：
  ```bash
  docker compose up -d
  # 等 30 秒让服务完全启动
  docker compose ps
  ```

- [ ] **2. 确认 Docker 容器健康**

  ```bash
  docker compose exec backend bash -c "bench doctor"
  ```

  输出没有红色报错即为正常。如果报错，先看报错内容，拿不准的问 Owner。

- [ ] **3. 拉取最新代码**

  ```bash
  git checkout main
  git pull origin main
  ```

  如果提示 `Already up to date`，说明你的本地代码已经是最新的。
  如果拉下来新代码，记一下有哪些文件变了（`git log --oneline -5` 看一眼）。

- [ ] **4. 如果拉了新代码，执行 migrate**

  ```bash
  docker compose exec backend bash -c "bench --site frontend migrate"
  ```

  因为新代码可能包含 DocType 变更或 Patch，必须 migrate 才能生效。

- [ ] **5. 查看 GitHub 上有没有新的 PR 需要审查**

  打开浏览器访问 `https://github.com/zjl327707743/HBOS/pulls`，扫一眼。

  如果有分配给自己的 PR 审查请求，记下来今天需要处理。

- [ ] **6. 确认今日任务**

  看一下团队沟通渠道（飞书群/项目看板）中今天的任务分配。确认自己今天要做什么，写在便利贴上或记在 TODO 里。

### 1.2 开工检查的意义

| 步骤 | 为什么要做 | 不做会怎样 |
|------|-----------|-----------|
| Docker 运行 | 开发环境是 Docker 里的，没启动就什么都干不了 | 写代码 → 没法运行 → 不知道对不对 |
| 健康检查 | 提前发现环境问题 | 写了一天代码发现环境一直有问题 |
| 拉最新代码 | 基于别人的最新改动工作 | 后面合并冲突一大堆 |
| 执行 migrate | 数据库结构同步 | 新字段/新表不存在，功能报错 |
| 看 PR | 别人的代码等着审查 | 阻塞团队进度 |
| 确认任务 | 知道今天干什么 | 一天瞎忙，做了不该做的 |

---

## 2. 开发前（每个任务）

> 每开始一个新任务（功能/修复/文档）前，必须完成以下检查。

### 2.1 检查清单

- [ ] **1. 确认任务范围**

  这个任务做什么？改哪些文件？不动哪些文件？**在脑子里过一遍，或者写下来。**

  如果任务描述不清楚，先找 Owner 或任务分配人确认，不要猜。

- [ ] **2. 确认在 main 分支且代码最新**

  ```bash
  git checkout main
  git pull origin main
  ```

- [ ] **3. 从 main 创建新分支**

  ```bash
  git checkout -b feature/任务描述
  ```

  分支命名规则（详见 `03_Git与GitHub多人协作规范.md` 第 3 节）：

  | 做什么 | 分支名示例 |
  |--------|-----------|
  | 新功能 | `feature/attendance-monthly-report` |
  | 修 Bug | `fix/import-null-pointer` |
  | 文档 | `docs/update-sop` |
  | 杂项 | `chore/update-docker-config` |
  | 紧急修复 | `hotfix/login-broken` |

  全部英文小写，单词用 `-` 连接。


- [ ] **4. 阅读相关文档**

  在写代码之前，先花 5 分钟看相关文档：

  | 你要做什么 | 先看哪些文档 |
  |-----------|-------------|
  | 改考勤模块代码 | `apps/hb_attendance_app/` 下的代码文件 |
  | 改 DocType | `06_Frappe自定义内容与数据库迁移规范.md` |
  | 改实体关系 | `01_项目真实结构与代码归属审计.md` 第 2 节 |
  | 涉及密钥/配置 | `09_安全密钥与敏感数据规范.md` |

- [ ] **5. 确认不修改核心源码**

  以下目录**绝对不能改**（除非 Owner 明确授权）：

  | 目录/文件 | 原因 |
  |-----------|------|
  | `runtime/apps/hrms/` | HRMS 开源代码，改了会被上游覆盖 |
  | Docker 容器内的 Frappe/ERPNext 源码 | 不可持久化，容器重建后丢失 |
  | `docker-compose.yml` | 影响所有人，需 Owner 审批 |
  | `.env` | 本地密钥，改了会破坏你自己的环境 |
  | `.gitignore` | 影响所有人，需团队讨论 |

  只能改 `apps/hb_attendance_app/` 和 `docs/` 下的内容。

### 2.2 任务开始的意义

每个任务前创建独立分支，是让"你的工作"和"别人的工作"完全隔离。你在自己的分支上想怎么改都行，不影响别人。不小心改坏了？删掉分支重新来就行。

---

## 3. 开发中

> 写代码过程中的操作规范。

### 3.1 检查清单

- [ ] **1. 小步提交，不要攒一天**

  ```
  正确：改完一个逻辑 → git add → git commit → 继续改下一个
  错误：写了一整天 → 下午 5 点一次性 git add . → git commit
  ```

  每次提交的标准：
  - 完成了一个完整的、可理解的、可回滚的小单元
  - 比如：新增一个 DocType 字段、修复一个 if 判断、完成一个函数

- [ ] **2. 写好 commit message**

  ```
  feat: 新增考勤导入日志的时间范围筛选
  fix: 修复 Employee 不存在时导入报 null pointer
  docs: 补充 SOP 开发中操作规范
  ```

  格式：`类型: 中文描述`（详见 `03_Git与GitHub多人协作规范.md` 第 4 节）

- [ ] **3. 定期 git push 到远端**

  ```bash
  # 第一次推送新分支
  git push -u origin feature/你的分支名

  # 之后每次推送
  git push
  ```

  什么时候 push：
  - 完成一个 commit 后且想备份
  - 准备去吃午饭/下班前（防止电脑出问题丢代码）
  - 至少每 2 小时 push 一次

- [ ] **4. 代码运行在容器中，不在宿主机**

  所有代码通过 bind mount 自动同步到容器。你改 `apps/hb_attendance_app/` 下的文件，容器内即时生效（Python 文件需要重启 backend）。

- [ ] **5. 改完代码后测试**

  | 你改了什么 | 怎么做 |
  |-----------|--------|
  | 功能代码 | 打开浏览器访问 Frappe Desk，手动操作一遍完整流程 |
  | 边界条件 | 故意输入空值、超长字符串、特殊字符，看是否报错 |
  | 数据查询 | 在 Frappe Desk 中查看报表，确认数据正确 |
  | 页面 UI | 检查页面加载、布局、按钮是否正常 |

- [ ] **6. 修改 DocType 后执行 migrate**

  ```bash
  docker compose exec backend bash -c "bench --site frontend migrate"
  ```

  改了 DocType 的 JSON 文件（加字段、改字段类型、改权限）后必须 migrate。

- [ ] **7. 修改 Python 文件后重启 backend**

  ```bash
  docker compose exec backend bash -c "bench restart"
  ```

  只有改了 `.py` 文件才需要重启。改 `.json`、`.md` 不需要。

- [ ] **8. 修改 JS/CSS 后 bench build**

  ```bash
  docker compose exec backend bash -c "bench build"
  ```

  如果改完 JS 页面没变化，build 后再清缓存：
  ```bash
  docker compose exec backend bash -c "bench --site frontend clear-cache"
  ```

### 3.2 修改类型与操作速查

| 修改内容 | 需要 migrate | 需要 restart | 需要 build |
|---------|:---:|:---:|:---:|
| 改 DocType JSON（加字段、改字段类型） | ✅ | | |
| 改 DocType JSON（字段 label、描述） | ✅ | | |
| 改 Python 业务逻辑 (.py) | | ✅ | |
| 改 hooks.py 配置 | | ✅ | |
| 改 JS 前端脚本 (.js) | | | ✅ |
| 改 HTML 模板 | | | ✅ |
| 改 CSS 样式 | | | ✅ |
| 改 fixtures JSON | ✅ | | |
| 改 patches.txt / 新增 Patch | ✅ | | |
| 改文档 (.md) | | | |
| 改 docker-compose.yml | ✅ | ✅ | ✅ |
| 改 .env | ✅ | ✅ | ✅ |

### 3.3 开发中常见问题

**问：我改完代码，浏览器里看不到变化？**

先判断改了什么类型的文件：
- 改 Python → 重启 backend
- 改 JS/CSS → bench build + clear-cache
- 改 DocType → bench migrate
- 改文档 → 不需要在浏览器看

**问：migrate 报错了怎么办？**

```bash
# 1. 先看错误信息，截图保存
# 2. 检查是否改错了 JSON 格式（多了逗号、少了括号）
# 3. 用 git diff 对比你改了什么
# 4. 如果是因为别人改了同一个 DocType 导致冲突，参考 06_Frappe 规范第 11 节
# 5. 自己搞不定，问 Owner 或 Claude
```

**问：我改着改着发现任务比想象的大，怎么办？**

先停下来，在团队沟通渠道上说明情况，让 Owner 判断是拆分任务还是调整预期。不要闷头硬干三天。

---

## 4. 提交前

> 本地开发完成，准备 push 和创建 PR 之前的最后检查。

### 4.1 检查清单

- [ ] **1. 运行相关测试**

  ```bash
  # 在容器内运行 App 的测试
  docker compose exec backend bash -c "bench --site frontend run-tests --app hb_attendance_app"
  ```

  所有测试通过才能提交。如果测试失败，先修测试。

- [ ] **2. 检查代码是否干净**

  ```bash
  git status
  ```

  确认：
  - 没有意外的文件被修改（比如改了不该改的）
  - 没有调试代码残留（`print()`、`console.log()`、`frappe.msgprint()`）
  - 没有临时文件（`test.py`、`temp.js`）

- [ ] **3. 用 git diff 检查所有变更**

  ```bash
  git diff origin/main...HEAD
  ```

  逐文件过一遍，确认每行改动都是你故意的，没有手滑误改。

- [ ] **4. 确认没有提交敏感内容**

  | 检查项 | 确认 |
  |--------|------|
  | `.env` 文件不在变更中 | `git status` 里看不到 `.env` |
  | 没有硬编码密码 | `git diff` 里没有 `password =` 带真实值 |
  | 没有真实员工数据 | 代码、注释、测试数据里都没有真人姓名/工号 |
  | 没有数据库备份文件 | commit 里没有 `.sql`、`.sql.gz` 文件 |

- [ ] **5. 确认只改了该改的文件**

  ```bash
  git diff --name-only origin/main...HEAD
  ```

  如果输出中出现了不在你任务范围内的文件，用 `git log` 查一下是不是误操作。如果是，在 push 前修正。

### 4.2 提交前常见遗漏

| 遗漏 | 后果 | 怎么补救 |
|------|------|----------|
| 忘了 export-doc（UI 中改了 DocType 但没导出 JSON） | 你改的配置只在你数据库里，别人看不到 | 立即 `bench export-doc` 导出，追加 commit |
| 忘了 export-fixtures（加了 Custom Field 但没导出） | 同上 | 立即 `bench export-fixtures` 导出，追加 commit |
| 忘了写 Patch（做了数据迁移但没写 Patch） | 别人装 App 后数据不完整 | 补写 Patch，追加到 patches.txt |
| 调试代码没删 | 上线后用户看到奇怪的弹窗或日志 | 全局搜索 `print(`、`console.log`、`msgprint`，删除 |

---

## 5. 创建 Pull Request

> 代码已经 push 到 GitHub，现在要让别人审查。

### 5.1 操作步骤

- [ ] **1. 确保分支已 push 到 GitHub**

  ```bash
  git push origin feature/你的分支名
  ```

- [ ] **2. 打开 GitHub，创建 PR**

  1. 浏览器打开 `https://github.com/zjl327707743/HBOS`
  2. 点击 `Pull requests` 标签
  3. 点击绿色 `New pull request` 按钮
  4. base 选 `main`，compare 选你的分支
  5. 点击 `Create pull request`

- [ ] **3. 填写 PR 描述**

  使用标准模板（详见 `03_Git与GitHub多人协作规范.md` 第 5.2 节）：

  ```markdown
  ## 变更概述
  （2-3 句话说明做了什么、为什么做）

  ## 变更范围
  - `apps/hb_attendance_app/.../xxx.py`
  - `apps/hb_attendance_app/.../xxx.json`

  ## 验证结果
  - [ ] 本地 Frappe Desk 功能验证通过
  - [ ] 正常场景验证通过
  - [ ] 异常场景验证通过

  ## 数据库迁移（如有）
  - 说明迁移内容与回滚方式

  ## 截图（如有 UI 变更）
  （粘贴截图）

  ## 回滚方法
  （说明如何回滚）

  ## 风险
  （评估风险等级和影响范围）
  ```

- [ ] **4. 指定 Reviewer**

  在 PR 页面右侧 `Reviewers` 区域，点击齿轮图标，选择审查人。

  | 谁来审 | 什么情况 |
  |--------|---------|
  | Codex（Reviewer） | 默认，所有代码 PR |
  | Owner | 影响业务逻辑、安全、权限、数据模型的 PR |
  | 任何 Developer | 文档、配置等非代码变更 |

- [ ] **5. 关联 Issue**

  如果这个 PR 解决了某个 Issue，在描述中写 `Closes #123`。

- [ ] **6. 附上截图**

  如果修改了 UI（页面、表单、报表、Workspace），必须截图贴到 PR 描述中。Reviewer 看着截图审查比纯读代码高效得多。

- [ ] **7. 如果有 AI 辅助生成代码，勾选声明**

  ```markdown
  ## AI 辅助声明
  - [ ] 本 PR 部分代码由 AI 辅助生成
  - [ ] 已人工逐行审查所有 AI 生成的代码
  - [ ] 无硬编码密钥、Token 或敏感信息
  ```

### 5.2 创建 PR 的注意事项

- **一个 PR 只做一件事**。不要把"修复 Bug"和"新增功能"放在同一个 PR 里。
- **PR 标题要清晰**。用 `feat:` / `fix:` / `docs:` 前缀。
- **不要觉得 PR 太小不好意思**。小 PR 是最好审查的 PR。

---

## 6. PR 审查期间

> 等待 Reviewer 审查代码，处理审查意见。

### 6.1 检查清单

- [ ] **1. 关注 GitHub 通知**

  Reviewer 会在 PR 页面留下评论。每个评论可能是：
  - **Comment**：建议，不阻塞合并，你自己判断是否改
  - **Request Changes**：必须修改，不改不能合并

- [ ] **2. 处理审查意见**

  收到审查意见后：

  ```
  1. 仔细阅读每一条评论
  2. 理解 Reviewer 为什么提出这个意见
  3. 在本地修改代码
  4. 提交到同一个分支
  5. 推送到 GitHub
  ```

  ```bash
  # 在你的 feature 分支上继续修改
  git checkout feature/你的分支名
  # ... 修改代码 ...
  git add .
  git commit -m "fix: 按审查意见修改 XX 逻辑"
  git push
  ```

  PR 会自动更新，不需要再创建新的 PR。

- [ ] **3. 回复审查评论**

  在 PR 页面对每条评论回复：
  - 如果按意见改了：回复 `Done` 或 `已修改`，附上 commit hash
  - 如果没改但有原因：回复你的理由（比如"这个场景下不会出现 XX 情况"）
  - 如果不太明白意见：回复提问，不要猜

- [ ] **4. 何时可以合并**

  PR 可以合并的条件（全部满足）：

  - [ ] 所有 `Request Changes` 已解决
  - [ ] 至少一个 Reviewer 点了 `Approve`
  - [ ] 所有 CI 检查通过（如果有配置）
  - [ ] 没有合并冲突
  - [ ] 需要 Owner 验收的 PR，Owner 已确认
  - [ ] PR 描述完整（变更范围、回滚方法都有）

  **满足条件后，由 Maintainer 执行合并。PR 作者自己不能合并自己的 PR。**

### 6.2 审查期间的礼仪

- **不要防御**。Reviewer 指出问题不是否定你的能力，是让代码更好。
- **及时响应**。收到审查意见后，尽量当天回复和处理。
- **如果审查意见让你困惑**，直接问。不要猜别人的意图。

---

## 7. 合并后

> PR 被合并到 main 后，你的分支代码已经进入主分支。

### 7.1 检查清单

- [ ] **1. 切回 main 并拉取最新代码**

  ```bash
  git checkout main
  git pull origin main
  ```

- [ ] **2. 在 Docker 中执行 migrate**

  ```bash
  docker compose exec backend bash -c "bench --site frontend migrate"
  ```

  这一步确保你本地数据库与最新代码一致。

- [ ] **3. 验证环境正常**

  ```bash
  # 健康检查
  docker compose exec backend bash -c "bench doctor"

  # 浏览器访问 Frappe Desk，确认功能正常
  ```

- [ ] **4. 删除本地 feature 分支**

  ```bash
  git branch -d feature/你的分支名
  ```

  如果提示 `not fully merged`，说明分支可能没被合并到 main，先检查 GitHub 确认 PR 已合并再执行。

  如果确定要强制删除（分支已合并但 Git 没识别）：
  ```bash
  git branch -D feature/你的分支名
  ```

- [ ] **5. 如果是 Release 版本，更新 Changelog**

  参考 `03_Git与GitHub多人协作规范.md` 第 8.3 节，在 App 的 `CHANGELOG.md` 中记录本次变更。

- [ ] **6. 如果是 Release 版本，打 Tag**

  ```bash
  git tag -a v0.4.0 -m "v0.4.0: 新增考勤月度汇总报表"
  git push origin v0.4.0
  ```

  版本号规则见 `03_Git与GitHub多人协作规范.md` 第 8.1 节。

### 7.2 合并后的注意事项

- 合并后不需要手动通知别人——GitHub 会自动通知相关人。
- 合并后如果发现 Bug，按正常流程创建新的 `fix/` 分支，不要直接在 main 上改。

---

## 8. 收工前（每日）

> 每天下班前的最后 5 分钟。

### 8.1 检查清单

- [ ] **1. 确认今天的工作已 push**

  ```bash
  git status
  ```

  如果有还没 push 的 commit，立即 push：
  ```bash
  git push
  ```

  如果工作未完成，至少要 commit 并 push（即使代码不完美），在 commit message 中加 `[WIP]` 标记：
  ```bash
  git add .
  git commit -m "feat: [WIP] 考勤汇总报表开发中，已完成数据查询逻辑"
  git push
  ```

- [ ] **2. 确认 PR 状态**

  打开 `https://github.com/zjl327707743/HBOS/pulls`，检查：
  - 自己的 PR 有没有新的审查意见需要处理
  - 分配给自己的审查任务是否已完成

- [ ] **3. 确认 Docker 环境正常**

  ```bash
  docker compose ps
  ```

  所有容器应该是 `Up` 状态。如果有关键容器退出，检查日志：
  ```bash
  docker compose logs --tail 30
  ```

- [ ] **4. 简单记录今天做了什么**

  在团队沟通渠道（飞书群）或项目看板上，用 2-3 句话记录：
  - 今天完成了什么
  - 有什么阻塞
  - 明天计划做什么

  示例：
  > 今日完成：考勤导入日志的日期筛选功能已开发完成，PR #45 等待审查。
  > 阻塞：无。
  > 明日计划：开始考勤月度汇总报表的数据查询逻辑。

  不需要长篇大论，1 分钟能写完就行。

- [ ] **5. 可选：停止 Docker 环境**

  如果电脑不关机且明天继续用，可以不管它。
  如果想省资源：
  ```bash
  docker compose stop
  ```

  注意：**不要用 `docker compose down`**（会删除容器），更**不要用 `docker compose down -v`**（会删除数据库！）。

### 8.2 收工检查的意义

| 步骤 | 为什么 | 忘了会怎样 |
|------|--------|-----------|
| 代码 push | 代码在云端有备份 | 电脑坏了/丢了 → 今天的代码全没了 |
| 确认 PR | 别人的代码可能被你阻塞 | 团队进度卡住 |
| 检查 Docker | 环境问题不过夜 | 明天早上发现环境挂了，浪费半天排查 |
| 简单记录 | 团队知道你在做什么 | 重复劳动、进度不透明 |

---

## 9. 每周维护（周五）

> 每周五下午或收工前完成，预计 15-30 分钟。

### 9.1 检查清单

- [ ] **1. 数据库备份**

  ```bash
  docker compose exec backend bash -c "bench --site frontend backup"
  ```

  备份文件位置在 Docker 卷中。查看备份：
  ```bash
  docker compose exec backend bash -c "bench --site frontend list-backups"
  ```

  把最新的备份文件复制到宿主机安全位置（可选但推荐）：
  ```bash
  # 根据 list-backups 的输出确定文件名
  docker cp backend:/home/frappe/frappe-bench/sites/frontend/private/backups/ backup_YYYYMMDD/
  ```

- [ ] **2. 检查 Docker 镜像更新**

  ```bash
  docker compose pull
  ```

  如果有新镜像，说明上游 Frappe/ERPNext 发布了更新。**不要立即更新**——先看 Release Notes，确认兼容性，在团队沟通渠道上确认后再更新。

- [ ] **3. 检查依赖漏洞（如有工具）**

  如果项目配置了依赖扫描工具（如 `pip-audit`），运行一次：
  ```bash
  docker compose exec backend bash -c "pip-audit"
  ```

  如果有高危漏洞，记录并报告 Owner。

- [ ] **4. 回顾本周**

  在团队中简短回顾（口头或飞书消息）：

  - 本周完成了哪些 PR？
  - 有哪些卡住的问题？
  - 有什么可以改进的地方？

  不需要正式会议，5 分钟同步即可。

- [ ] **5. 清理本地分支**

  ```bash
  # 查看本地分支
  git branch

  # 删除已经合并的分支（保留 main）
  git branch -d feature/已合并的分支名
  ```

  如果分支显示 `not fully merged` 但你确认 PR 已合并，通常是因为使用了 Squash merge，Git 本地判断不了。用 `-D` 强制删除：
  ```bash
  git branch -D feature/已合并的分支名
  ```

- [ ] **6. 检查 .gitignore 是否生效**

  ```bash
  # 确认敏感文件不会被提交
  git status --ignored
  ```

  确认 `.env`、`volumes/`、`docs/data/*.xlsx` 等文件在 ignored 列表中。

### 9.2 每周维护的意义

这些维护动作花的时间不多，但能防止累积性问题在几周后爆发。特别是数据库备份——没有备份就没有后悔药。

---

## 10. 紧急故障处理

> 生产环境或开发环境出现严重问题时的标准流程。

### 10.1 什么算紧急

| 情况 | 算紧急吗 | 处理方式 |
|------|:---:|------|
| Frappe Desk 完全打不开（500 错误） | 是 | 立即处理 |
| 数据库连接失败 | 是 | 立即处理 |
| 所有容器都挂了 | 是 | 立即处理 |
| 数据丢失 | 是 | 立即处理 |
| 某个报表数据不对 | 是（如果影响业务） | 尽快处理 |
| 页面某个按钮不响应 | 视情况 | 当天处理 |
| 页面样式有点歪 | 否 | 创建 Issue，排期处理 |
| 某条日志打印了警告 | 否 | 创建 Issue，排期处理 |

### 10.2 响应步骤

- [ ] **1. 确认问题**

  ```
  在团队沟通渠道（飞书群）发出警报：
  "@所有人 [紧急] 环境出现 XX 问题，现象是 YY，正在排查。"
  ```

  不要闷头自己修，先让团队知道出问题了。

- [ ] **2. 快速诊断**

  ```bash
  # 看容器状态
  docker compose ps

  # 看关键日志
  docker compose logs --tail 100 backend
  docker compose logs --tail 50 db

  # 健康检查
  docker compose exec backend bash -c "bench doctor"
  ```

- [ ] **3. 找到修复人**

  | 问题类型 | 谁来修 |
  |---------|--------|
  | Docker 环境问题 | 熟悉 Docker 的成员 |
  | 数据库问题 | Owner 或熟悉数据库的成员 |
  | 代码 Bug | 该模块最近有提交的人 |
  | 不确定 | Owner 判断 |

- [ ] **4. 先恢复，再找根因**

  ```
  正确顺序：
  1. 恢复服务（让系统能用）—— 优先
  2. 记录事故时间和现象
  3. 排查根因
  4. 修复根因
  5. 预防再次发生

  错误顺序：
  1. 排查根因（花了 3 小时）
  2. 修复根因（又花了 1 小时）
  3. 恢复服务
  → 系统挂了 4 小时，而不是 30 分钟
  ```

  恢复手段：
  - 数据库问题：恢复最近的备份
  - 容器问题：`docker compose restart`
  - 代码问题：`git revert` 回滚有问题的 commit

- [ ] **5. 记录事故**

  事故恢复后，在 `docs/` 下记录事故报告（文件名示例：`incident_20260714_docker_outage.md`）：

  ```markdown
  ## 事故报告：2026-07-14 Docker 环境宕机

  **时间**：2026-07-14 14:30 - 15:00（30 分钟）
  **影响**：Frappe Desk 无法访问，所有开发工作中断
  **根因**：db 容器因磁盘空间不足自动退出
  **修复**：清理 Docker 镜像缓存，释放 20GB 空间，重启 db 容器
  **预防**：添加磁盘空间监控，每周五检查磁盘使用率
  ```

### 10.3 紧急修复的代码流程

如果是代码 Bug 导致的紧急问题：

```bash
# 1. 从 main 创建 hotfix 分支
git checkout main
git pull origin main
git checkout -b hotfix/紧急修复描述

# 2. 修复 Bug
# ... 改代码 ...

# 3. 提交并推送
git add .
git commit -m "fix: 修复 XX 紧急问题"
git push -u origin hotfix/紧急修复描述

# 4. 创建 PR，标题加 [紧急] 前缀
# 5. 通知 Reviewer 优先处理
# 6. 合并后，切回 main 拉取最新，验证修复
```

---

## 11. 日常命令速查表

> 把最常用的命令汇总在这里，方便随时查阅。

### 11.1 Git 命令

| 做什么 | 命令 |
|--------|------|
| 查看当前状态 | `git status` |
| 查看改动内容 | `git diff` |
| 查看最近提交 | `git log --oneline -10` |
| 拉取最新代码 | `git checkout main && git pull origin main` |
| 创建新分支 | `git checkout -b feature/分支名` |
| 切换分支 | `git checkout 分支名` |
| 添加文件 | `git add 文件名` 或 `git add .` |
| 提交 | `git commit -m "feat: 描述"` |
| 推送分支 | `git push -u origin 分支名`（首次）/ `git push`（后续） |
| 删除本地分支 | `git branch -d 分支名` |
| 暂存改动 | `git stash` |
| 恢复暂存 | `git stash pop` |
| 撤销最近提交 | `git reset --soft HEAD~1` |
| 查看分支差异 | `git diff origin/main...HEAD` |

### 11.2 Docker 命令

| 做什么 | 命令 |
|--------|------|
| 启动环境 | `docker compose up -d` |
| 停止环境 | `docker compose stop` |
| 重启环境 | `docker compose restart` |
| 查看容器状态 | `docker compose ps` |
| 查看日志 | `docker compose logs --tail 50` |
| 实时日志 | `docker compose logs -f backend` |
| 进入容器 | `docker compose exec backend bash` |
| 退出容器 | `exit` 或 Ctrl+D |

### 11.3 Bench 命令（容器内执行）

| 做什么 | 命令 |
|--------|------|
| 健康检查 | `bench doctor` |
| 数据库迁移 | `bench --site frontend migrate` |
| 构建前端 | `bench build` |
| 清除缓存 | `bench --site frontend clear-cache` |
| 重启服务 | `bench restart` |
| 查看已安装 App | `bench --site frontend list-apps` |
| 创建备份 | `bench --site frontend backup` |
| 查看备份 | `bench --site frontend list-backups` |
| 进入 Python 控制台 | `bench --site frontend console` |
| 导出 DocType | `bench --site frontend export-doc hb_attendance_app "DocType Name"` |
| 导出 Fixture | `bench --site frontend export-fixtures --app hb_attendance_app` |
| 运行测试 | `bench --site frontend run-tests --app hb_attendance_app` |

### 11.4 常用组合命令（复制粘贴用）

```bash
# 开始一天工作
cd "$HBOS_HOME"     # 使用上面定义的 HBOS_HOME
docker compose up -d
docker compose ps
git checkout main && git pull origin main
docker compose exec backend bash -c "bench --site frontend migrate"

# 开始新功能
git checkout main && git pull origin main
git checkout -b feature/功能名

# 改完代码后的完整操作
git add .
git commit -m "feat: 功能描述"
git push
docker compose exec backend bash -c "bench --site frontend migrate && bench restart"

# 改完 JS/CSS 后的操作
git add .
git commit -m "feat: 前端修改描述"
git push
docker compose exec backend bash -c "bench build && bench --site frontend clear-cache"

# 收工前
git status
git push
docker compose ps
```

---

## 附录 A：角色职责速查

| 角色 | 主要职责 | 不能做的事 |
|------|---------|-----------|
| **Owner** | 产品方向决策、验收功能、管理仓库权限、审批敏感变更 | -- |
| **Claude (AI)** | 辅助开发、代码生成、文档编写、问题解答 | 不能替代人工审查，不能直接操作生产环境 |
| **Codex (Reviewer)** | 审查代码质量、检查安全漏洞、检查代码规范 | 不能合并 PR（除非也是 Maintainer） |
| **Developer** | 写代码、创建 PR、修复 Bug、写文档 | 不能直接 push main、不能合并自己的 PR、不能改核心源码 |

## 附录 B：SOP 不覆盖的场景

本 SOP 覆盖了日常开发 90% 的操作。以下场景不在本 SOP 范围内，需要参考对应文档：

| 场景 | 参考文档 |
|------|---------|
| 新人搭建环境 | `07_新成员入职与本地环境上手手册.md` |
| 版本发布 | `08_版本发布回滚备份与环境管理.md` |
| 数据库迁移协作 | `06_Frappe自定义内容与数据库迁移规范.md` |
| 安全密钥泄露 | `09_安全密钥与敏感数据规范.md` 第 9 节 |
| 冲突解决 | `03_Git与GitHub多人协作规范.md` 第 7.5 节 |
| 开源代码二次开发 | `05_开源代码二次开发与升级规范.md` |

---

---

## 10. G1D 多人协作治理（2026-07-17 生效）

### 10.1 分支与合并规则

> 以下规则已通过 GitHub 仓库设置强制执行，违反操作将被 GitHub 拒绝。

| 规则 | 要求 |
|------|------|
| 合并方式 | 仅允许 **Squash Merge**（Merge Commit 和 Rebase Merge 已关闭） |
| 合并后分支 | **自动删除**已合并的功能分支 |
| 直接 push main | **禁止**（所有成员，包括 Write 权限） |
| force push main | **禁止** |
| 删除 main 分支 | **禁止** |
| 线性历史 | 要求 PR 分支与 main 无分叉（需 rebase 后再合并） |

### 10.2 PR 门禁要求

每个合并到 main 的 PR 必须满足：

- [ ] **至少 1 名非作者批准**（Owner 也不能批准自己的 PR）
- [ ] **新提交后旧批准失效**（推送新 commit 后需重新审查）
- [ ] **所有 Review Conversation 已解决**
- [ ] **HBOS 质量门禁（CI）全部通过**
- [ ] **PR 描述完整**（使用 `.github/pull_request_template.md` 模板）

### 10.3 日常开发完整流程

```
每天早上：
  git checkout main
  git pull origin main
  docker compose ps

创建功能分支：
  git checkout -b feat/<scope>-<description>
  # 禁止基于旧分支创建新分支，禁止长期存在的个人分支

开发完成后：
  git fetch origin
  git diff origin/main...HEAD          # 检查差异
  docker compose exec backend python3 -m unittest discover -s apps/hb_attendance_app/tests -v
  git add <files>
  git commit -m "feat: <description>"
  git push -u origin feat/<scope>-<description>

创建 PR：
  1. 打开 https://github.com/zjl327707743/HBOS/pulls
  2. 点击 "New pull request"
  3. base: main, compare: feat/<scope>-<description>
  4. 使用 PR 模板填写完整描述
  5. 等待 CI 通过
  6. 请求 Reviewer 审查

Review 与修改：
  - Reviewer 在 PR 页面提交 Review（Approve / Request Changes / Comment）
  - 如需修改：在本地同一分支修改 → git push → 旧批准自动失效
  - 所有 Conversation 标记为 Resolved 后通知 Reviewer 重新审查

合并：
  - 满足所有门禁后，点击 "Squash and merge"
  - 合并后分支自动删除
  - 本地同步：git checkout main && git pull origin main
```

### 10.4 冲突处理

```
1. git checkout main && git pull origin main
2. git checkout <你的功能分支>
3. git merge main          # 在本地将 main 合并到功能分支
4. 解决冲突文件（搜索 <<<<<<< 标记）
5. git add <冲突文件>
6. git commit -m "chore: 解决与 main 的合并冲突"
7. git push
8. 通知 Reviewer 重新审查（旧批准已失效）
```

### 10.5 紧急修复流程

1. 从 `main` 创建 `fix/<description>` 分支
2. 完成修复并验证
3. 创建 PR 并在标题标注 `[紧急]`
4. 获得批准后 Squash Merge
5. **禁止**以任何理由直接 push 到 `main`，即使紧急情况

### 10.6 Owner 应急管理权限（Break-glass）

Owner 保留仓库管理权限，但**仅限以下场景**：

| 场景 | 示例 |
|------|------|
| 仓库故障 | CI 配置损坏导致所有 PR 被阻塞 |
| 严重安全事件 | 密钥泄露需立即回滚 |
| 门禁自身失效 | Ruleset 配置错误阻止合法操作 |

**日常开发不得绕过 PR、Review 和 CI 流程。** 每次使用应急权限必须：

1. 记录时间、原因、操作内容
2. 追加到 `docs/team/audits/` 目录下的审计报告

### 10.7 禁止普通成员直接操作 main

- 任何 Write 权限成员**不得**直接 push、force push 或删除 `main` 分支
- 所有变更必须通过 PR → Review → CI → Squash Merge
- 合并操作由 PR 作者或 Reviewer 在 GitHub UI 完成

### 10.8 Codex 审查时机

- Codex 审查**仅在重大 Gate（阶段里程碑）结束时**进行一次
- 日常 PR **不触发** Codex 审查
- Codex 审查由 Owner 发起

### 10.9 配置、迁移和数据库资产代码化

- 数据库结构变更必须通过 Frappe DocType JSON 或 Patch 代码化
- 稳定配置项（系统设置、自定义字段）必须代码化，不得仅在数据库中手动修改
- 迁移脚本必须可重复执行且幂等

---

> **文档维护者**：HBOS 开发团队
> **创建日期**：2026-07-14
> **最后更新**：2026-07-17（G1D-A 多人协作治理生效）
> **相关文档**：
> - `03_Git与GitHub多人协作规范.md`
> - `06_Frappe自定义内容与数据库迁移规范.md`
> - `12_常用Git与Docker命令解释.md`
> - `CONTRIBUTING.md`（仓库根目录）
> - `.github/pull_request_template.md`（PR 模板）