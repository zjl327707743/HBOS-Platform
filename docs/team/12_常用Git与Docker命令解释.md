# 常用 Git 与 Docker 命令解释

> **面向人群**：没有多人协作经验的团队成员。每条命令用大白话解释——它是干什么的、在哪执行、有什么风险。

---

## 警告

**以下每条命令都标注了安全等级。标有 ⚠️ 或 🔴 的命令在执行前请确认你理解其影响。如果不确定，先问 Owner。**

---

## 安全等级说明

| 等级 | 含义 | 一句话 |
|------|------|--------|
| 🟢 安全 | 只读查看，不会改变任何东西 | 随便看，放心用 |
| 🟡 谨慎 | 会修改本地文件或状态，但影响范围可控 | 只影响你自己的电脑 |
| ⚠️ 危险 | 会影响团队或数据，执行前确认 | 可能会影响别人或数据 |
| 🔴 禁止 | 绝对不能执行 | 除非 Owner 在特定紧急情况下明确授权 |

---

## Git 命令

Git 是"版本管理工具"。你每一次"保存"（commit），Git 都会帮你记住这个版本。你可以随时回到过去任何一个版本。

### 核心概念（30 秒理解）

```
工作区（你电脑上的文件）
    │  git add
    ▼
暂存区（"这次我要提交这些文件"）
    │  git commit
    ▼
本地仓库（你电脑上的版本历史）
    │  git push
    ▼
远程仓库（GitHub 上的版本历史）
```

### 查看类（🟢 安全）

这些命令只看不改，放心使用。

#### `git status` — 查看当前有什么改动

```bash
git status
```

- **在哪执行**：项目的根目录（HBOS 文件夹下）
- **做什么**：告诉你哪些文件改了、哪些是新的、哪些已经暂存了
- **什么时候用**：每次动手前的第一件事。养成习惯，先 `git status` 再看要不要做别的
- **输出示例**：
  ```
  modified:   README.md          ← 这个文件被修改了
  Untracked files: 新文件.txt    ← 这个文件是新的，还没被 Git 跟踪
  ```

#### `git log` — 查看提交历史

```bash
git log                    # 完整历史，按 q 退出
git log --oneline          # 简洁版，每条提交一行
git log --oneline -10      # 只看最近 10 条
git log --oneline --graph  # 图形化显示分支关系
```

- **在哪执行**：项目根目录
- **做什么**：显示谁在什么时候提交了什么
- **什么时候用**：想看看最近大家都做了什么

#### `git diff` — 查看具体改了什么

```bash
git diff                         # 查看未暂存的改动（工作区 vs 暂存区）
git diff --staged                # 查看已暂存但未提交的改动
git diff origin/main...HEAD      # 查看当前分支比 main 多了什么
```

- **在哪执行**：项目根目录
- **做什么**：精确到每一行的改动对比
- **什么时候用**：提交之前看一眼自己改了啥，避免错改
- **为什么重要**：很多时候我们改了东西但不记得改了哪里，`git diff` 让你看清楚每一行变化

#### `git branch` — 查看分支

```bash
git branch          # 查看本地分支，当前分支前面有 *
git branch -a       # 查看所有分支（包括远程）
git branch -r       # 只看远程分支
```

- **在哪执行**：项目根目录
- **做什么**：列出所有分支
- **什么时候用**：想知道自己在哪个分支上、有哪些分支可用

#### `git remote -v` — 查看远程仓库地址

```bash
git remote -v
```

- **在哪执行**：项目根目录
- **做什么**：显示你的本地仓库连接的是哪个 GitHub 仓库
- **什么时候用**：不确定自己是否连对了远程仓库时

---

### 分支操作（🟡 谨慎）

分支是什么？你可以把分支理解为"一条独立的开发线"。每个人在自己的分支上改东西，互不干扰，改完了再合并到一起。

#### `git checkout -b` — 创建并切换到新分支

```bash
git checkout main             # 先切回 main
git pull                      # 拉取最新代码（重要！）
git checkout -b feature/xxx   # 从当前位置创建新分支
```

- **风险**：只影响本地，不影响别人
- **为什么先回 main 再创建**：确保你的新分支是基于最新代码的，否则后面合并时可能有一堆冲突
- **什么时候用**：开始做任何一个新功能之前
- **命名规范**：`feature/功能描述`、`fix/修复描述`

#### `git checkout` — 切换分支

```bash
git checkout main            # 切换到 main 分支
git checkout feature/xxx     # 切换到 feature/xxx 分支
```

- **风险**：切换前确保当前改动已经保存（commit 或 stash），否则可能丢失
- **什么时候用**：要在不同任务之间切换时

#### `git branch -d` — 删除本地分支

```bash
git branch -d feature/xxx    # 安全删除（如果分支没合并会拒绝）
git branch -D feature/xxx    # 强制删除（即使没合并也会删）
```

- **风险**：`-d` 是安全的，`-D` 是强制的，用 `-D` 前确认一下
- **什么时候用**：分支已经合并了、不需要了，清理一下

---

### 提交类（🟡 谨慎）

#### `git add` — 添加文件到暂存区

```bash
git add 文件名                  # 添加指定文件
git add docs/新文档.md          # 添加某个文件
git add .                       # 添加当前目录及其子目录所有改动
git add -p                      # 交互式添加，一块一块确认
```

- **风险**：`git add .` 会把所有改动都加进去，可能误加不该提交的文件
- **什么时候用**：确认要提交之前
- **建议**：开发初期用 `git add .` 没问题，但养成看一眼 `git status` 的习惯

#### `git commit` — 创建提交（存一个版本）

```bash
git commit -m "feat: 添加了用户登录功能"
git commit -m "fix: 修复了首页加载太慢的问题"
git commit -m "docs: 更新了命令手册"
```

- **风险**：只影响本地，可以后期修改
- **提交信息格式**：`类型: 中文描述`
  - `feat` — 新功能
  - `fix` — 修 Bug
  - `docs` — 文档
  - `refactor` — 重构（改代码逻辑但不改功能）
  - `chore` — 杂项
- **什么时候用**：完成一个有意义的改动单元后

#### `git push` — 推送到远端（上传到 GitHub）

```bash
git push                      # 推送到默认远程分支
git push -u origin feature/xxx  # 第一次推送新分支（-u 设置上游）
```

- **风险**：代码上传到 GitHub 后，团队成员就都能看到了
- **什么时候用**：本地提交完成后，想让别人看到或想备份到云端
- **为什么需要 -u**：第一次推送新分支时，Git 不知道要推到远程的哪个分支，`-u` 就是告诉它"记住这个对应关系，以后直接 git push 就行"

#### `git pull` — 拉取远端更新（从 GitHub 下载）

```bash
git pull                      # 拉取当前分支的更新
git pull origin main          # 拉取 main 分支的更新
```

- **风险**：可能产生冲突。如果别人改了跟你一样的文件，需要手动解决
- **什么时候用**：每天开工第一件事、准备 push 之前
- **什么情况下会有冲突**：你和同事都改了同一个文件的同一行。Git 不知道以谁的为准，需要你手动选择

---

### 危险操作（⚠️ 危险）

#### `git reset` — 撤销提交

```bash
git reset --soft HEAD~1     # 撤销最近一次 commit，改动保留在暂存区
git reset --mixed HEAD~1    # 撤销最近一次 commit 和 add，改动保留在工作区（默认）
git reset --hard HEAD~1     # 撤销最近一次 commit，改动全部丢弃！
```

- **三种模式对比**：
  | 模式 | commit 还在吗 | add 还在吗 | 文件改动还在吗 |
  |------|-------------|-----------|--------------|
  | --soft | 撤销了 | 保留 | 保留 |
  | --mixed | 撤销了 | 也撤销了 | 保留 |
  | --hard | 撤销了 | 也撤销了 | **全丢了！** |
- **什么时候用**：
  - 刚 commit 完发现漏了东西，用 `--soft` 撤销后重新加
  - 刚 commit 完发现改错了，但还想留改动，用 `--mixed`
  - **谨慎用 `--hard`**

#### `git rebase` — 重写历史

```bash
git rebase main              # 把当前分支的提交接到 main 最新版本后面
```

- **风险**：会改写提交历史。如果分支已经 push 给别人了，rebase 后强行 push 会让别人崩溃
- **什么时候用**：自己的分支上整理提交历史（比如把 10 个零碎提交合并成 3 个干净的）
- **规则**：只 rebase 你还没 push 出去的分支

#### `git stash` — 暂存改动

```bash
git stash                      # 暂存当前所有改动
git stash pop                  # 恢复最近一次暂存
git stash list                 # 查看所有暂存
```

- **风险**：低，但 stash 是"临时存放"，不要依赖它长期存储。时间久了容易忘
- **什么时候用**：正在改一个功能，突然需要切分支修 Bug，但又不想提交半成品

---

### 禁止操作（🔴 禁止）

#### `git push --force` / `git push -f` — 强制推送

- **为什么禁止**：会直接覆盖远程仓库上的提交历史。如果有同事在你之前 push 了代码，他们的工作会被你覆盖掉
- **如果真的需要用**：必须先用 `git push --force-with-lease`，它至少会检查远程有没有你本地不知道的新提交。但这也要 Owner 确认后才执行

#### `git reset --hard origin/main` — 丢弃所有本地修改

- **为什么禁止**：会把本地所有没 push 的改动全部永久删除，无法恢复
- **如果真的需要用**：先 `git stash` 保存一下，确认不用了再执行

#### `git clean -fd` — 删除所有未跟踪文件

- **为什么禁止**：会删除所有 Git 不知道的文件（新创建但没 add 的文件）
- **如果真的需要用**：先 `git clean -n`（预览模式，只看不删），确认无误后再考虑

---

## Docker 命令

Docker 像一个"集装箱"系统。它把程序、依赖、配置全部打包在一个独立的环境中运行，不依赖你的电脑装了什么。

我们的项目有这些容器（你可以理解为"虚拟小电脑"）：

| 容器名 | 干什么的 |
|--------|---------|
| backend | Frappe 后端服务 |
| frontend | 网页前端 |
| db | MariaDB 数据库 |
| redis-cache | Redis 缓存 |
| redis-queue | Redis 消息队列 |
| websocket | WebSocket 实时通信 |
| scheduler | 定时任务调度器 |
| queue-short | 短任务队列 |
| queue-long | 长任务队列 |
| configurator | 配置初始化 |
| create-site | 站点创建 |

### 查看类（🟢 安全）

#### `docker ps` — 查看运行中的容器

```bash
docker ps                  # 看有哪些容器在跑
docker ps -a               # 看所有容器（包括已停止的）
```

- **在哪执行**：终端任意位置
- **做什么**：列出运行中的容器、运行了多久、端口映射

#### `docker compose ps` — 查看 Compose 项目的容器

```bash
docker compose ps
```

- **在哪执行**：项目根目录（包含 `docker-compose.yml` 的文件夹）
- **做什么**：专门看当前项目的容器状态
- **和 docker ps 的区别**：`docker compose ps` 只看当前项目的容器，`docker ps` 看所有 Docker 容器

#### `docker logs` — 查看容器日志

```bash
docker logs 容器名                    # 查看完整日志
docker logs --tail 50 容器名          # 只看最后 50 行
docker logs --tail 100 -f 容器名      # 看最后 100 行并实时跟踪
```

- **在哪执行**：终端任意位置
- **做什么**：看某个容器打印了什么
- **什么时候用**：
  - "为什么登录不了" → 看 `backend` 容器的日志
  - "为什么页面打不开" → 看 `frontend` 容器的日志
  - "数据库有问题吗" → 看 `db` 容器的日志

#### `docker compose logs -f` — 实时查看所有容器日志

```bash
docker compose logs -f                # 所有容器的实时日志
docker compose logs -f backend        # 只看 backend 的实时日志
```

- **在哪执行**：项目根目录
- **做什么**：终端会持续显示日志输出，按 Ctrl+C 停止
- **什么时候用**：排查问题时，想看发生了什么

#### `docker inspect` — 查看容器详细信息

```bash
docker inspect 容器名
```

- **做什么**：显示容器的完整配置信息（网络、挂载卷、环境变量等）
- **什么时候用**：需要了解容器是怎么配置的

---

### 容器操作（🟡 谨慎）

#### `docker compose up -d` — 启动所有服务

```bash
docker compose up -d
```

- **在哪执行**：项目根目录
- **做什么**：启动 docker-compose.yml 里定义的所有容器
- **-d 是什么意思**：后台运行（detached），不在终端里占据你的窗口
- **什么时候用**：环境搭建完第一次启动、电脑重启后需要恢复环境

#### `docker compose stop` — 停止所有服务

```bash
docker compose stop
```

- **在哪执行**：项目根目录
- **做什么**：停止所有容器但不删除它们
- **和 down 的区别**：`stop` 只是暂停，容器还在；`down` 会删除容器
- **什么时候用**：下班关环境但明天还要接着用

#### `docker compose restart` — 重启

```bash
docker compose restart                 # 重启所有
docker compose restart backend         # 只重启某一个
```

- **在哪执行**：项目根目录
- **做什么**：停止然后立即启动
- **什么时候用**：改了一些配置文件想让容器重新加载
- **为什么不是每次都 restart**：Frappe 环境下有些东西改完不需要重启，详见 `04_Docker开发环境复现手册.md`

#### `docker exec -it <容器名> bash` — 进入容器

```bash
docker exec -it backend bash
```

- **在哪执行**：终端任意位置
- **做什么**：进入容器内部的命令行，就像登录了一台小 Linux 服务器
- **-it 是什么意思**：`-i` 交互模式、`-t` 分配终端。没有这两个参数就没法打字
- **什么时候用**：
  - 需要在容器内执行 bench 命令
  - 想看容器内的文件结构
  - 需要调试容器内的问题
- **怎么退出**：输入 `exit` 或按 Ctrl+D

---

### 危险操作（⚠️ 危险）

#### `docker compose down` — 停止并删除容器

```bash
docker compose down
```

- **风险**：删除容器（但数据在 volume 中不会丢失）
- **为什么数据不会丢**：数据库文件存在 Docker 的 volume（数据卷）里，跟容器是分开的。删了容器不等于删了数据库
- **什么时候用**：环境出了奇怪的问题，想从头重建

#### `docker compose build` — 重新构建镜像

```bash
docker compose build                 # 重新构建所有镜像
docker compose build --no-cache      # 完全重新构建（不使用缓存，更慢但更彻底）
```

- **风险**：耗时长、消耗网络流量。但不会丢数据
- **什么时候用**：Dockerfile 或依赖改了，需要重建镜像

#### `docker compose pull` — 拉取最新镜像

```bash
docker compose pull
```

- **风险**：可能会拉到不兼容的新版本
- **什么时候用**：Owner 通知大家"更新了基础镜像，大家拉一下"

---

### 禁止操作（🔴 禁止，除非 Owner 授权）

#### `docker compose down -v` — 删除容器和数据卷

- **为什么禁止**：`-v` 会把数据卷（volume）也删掉。数据库的所有数据都在卷里，删了就没了
- **什么情况下用**：环境完全重建时（由 Owner 确认和操作）

#### `docker volume rm` — 删除数据卷

- **为什么禁止**：同上，直接删数据库数据
- **什么情况下用**：清理不再需要的测试数据（由 Owner 确认）

#### `docker system prune` — 清理所有未使用数据

```bash
docker system prune            # 清理停止的容器、未使用的网络等
docker system prune -a         # 还会清理未使用的镜像
docker system prune -a --volumes   # 还会清理未使用的数据卷！
```

- **为什么禁止**：最后一条会清数据卷，可能误删项目的数据库
- **什么情况下用**：磁盘空间不够了，但必须确认没有重要的 volume 被删

---

## Bench 命令（在 backend 容器内执行）

Bench 是 Frappe 的命令行工具。这些命令**必须在 backend 容器内部执行**，不能在你的电脑终端直接执行。

先进入容器：

```bash
docker exec -it backend bash
```

进去以后就可以用 bench 命令了。

### 查看类（🟢 安全）

#### `bench version` — 查看版本

```bash
bench version
```

- **做什么**：显示当前 Frappe 和 bench 的版本号
- **什么时候用**：排查问题时确认版本

#### `bench --site frontend list-apps` — 查看已安装的 App

```bash
bench --site frontend list-apps
```

- **做什么**：列出安装了哪些 Frappe App
- **--site frontend 是什么意思**：指定在哪个站点上执行。我们的站点名叫 `frontend`

#### `bench doctor` — 健康检查

```bash
bench doctor
```

- **做什么**：检查 Frappe 环境的各项配置是否正常
- **什么时候用**：出问题时先跑一下看看有没有明显问题

#### `bench console` — Python 交互式控制台

```bash
bench --site frontend console
```

- **做什么**：进入 Frappe 的 Python 环境，可以直接写 Python 代码操作数据库
- **什么时候用**：想快速查数据、测试一小段代码
- **注意**：这里改数据是直接生效的，没有"撤销"按钮

---

### 常规操作（🟡 谨慎）

#### `bench --site frontend migrate` — 执行数据库迁移

```bash
bench --site frontend migrate
```

- **风险**：会修改数据库结构。理论上安全，但执行前确保你知道为什么需要 migrate
- **什么是迁移**：当你安装了新 App 或拉了代码后，可能需要新增或修改数据库表结构，migrate 就是做这件事的
- **什么时候执行**：拉完新代码后、装完新 App 后

#### `bench build` — 构建前端资源

```bash
bench build
```

- **风险**：低。只是重新编译 JS/CSS 文件
- **什么时候用**：改了前端 JS 或 CSS 后，需要重新编译才能看到效果

#### `bench --site frontend clear-cache` — 清除缓存

```bash
bench --site frontend clear-cache
```

- **风险**：低。只是清掉 Redis 缓存，下次访问时会重新生成
- **什么时候用**：改了东西但页面上看不到变化（可能是缓存导致的）

#### `bench restart` — 重启后台进程

```bash
bench restart
```

- **风险**：会短暂中断服务（几秒钟）
- **什么时候用**：改了 Python 后端代码后需要重启才能生效

---

### 危险操作（⚠️ 危险）

#### `bench --site frontend install-app <app名>` — 安装新 App

```bash
bench --site frontend install-app hb_core_app
```

- **风险**：会修改站点配置和数据库结构
- **什么时候用**：新 App 开发完成、需要安装到站点测试
- **前提**：必须确认该 App 已经准备好（不要装半成品）

#### `bench --site frontend uninstall-app <app名>` — 卸载 App

```bash
bench --site frontend uninstall-app hb_core_app
```

- **风险**：可能会删除该 App 相关的数据库表
- **什么时候用**：确认某个 App 不再需要
- **确认后再执行**

---

### 禁止操作（🔴 禁止，除非 Owner 授权）

#### `bench new-site` — 创建新站点

- **为什么禁止**：站点是核心架构的一部分，由 Docker 环境在初始化时自动创建
- **什么情况下用**：只有 Owner 在规划新环境时

#### `bench drop-site` — 删除站点

- **为什么禁止**：会删除站点和所有数据
- **什么情况下用**：永远不要在开发环境执行

---

## 常见场景命令组合

每个场景都附上了完整的命令序列，按顺序执行即可。

### 场景 1：开始一天的工作

```bash
# 1. 进入项目目录
# 1. 进入项目目录（将 <你的HBOS项目路径> 替换为你的实际路径）
export HBOS_HOME="<你的HBOS项目路径>"
cd "$HBOS_HOME"

# 2. 切到 main 分支
git checkout main

# 3. 拉取最新代码
git pull

# 4. 启动 Docker 环境
docker compose up -d

# 5. 等几秒钟让服务启动，然后确认一下
docker compose ps
```

### 场景 2：做一个功能修改

```bash
# 1. 确保在 main 分支且是最新代码
git checkout main
git pull

# 2. 创建新分支（取一个有意义的名字）
git checkout -b feature/添加用户导入功能

# 3. ... 写代码 ...

# 4. 看看做了哪些改动
git status
git diff

# 5. 添加到暂存区并提交
git add .
git commit -m "feat: 添加用户批量导入功能"

# 6. 推送到 GitHub
git push -u origin feature/添加用户导入功能

# 7. 如果改了后端代码，需要进容器重启
docker exec -it backend bash
bench restart
exit

# 8. 如果改了前端资源
docker exec -it backend bash
bench build
bench --site frontend clear-cache
exit
```

### 场景 3：紧急修复一个 Bug

```bash
# 1. 如果你正在别的分支上改东西，先暂存
git stash

# 2. 切到 main 更新
git checkout main
git pull

# 3. 从 main 创建修复分支
git checkout -b fix/登录页面报错

# 4. ... 修 Bug ...

# 5. 提交并推送
git add .
git commit -m "fix: 修复登录页面 500 错误"
git push -u origin fix/登录页面报错

# 6. 切回之前的分支继续工作
git checkout feature/之前的开发分支
git stash pop    # 恢复之前暂存的改动
```

### 场景 4：查看为什么登录不了

```bash
# 1. 先看 backend 容器有没有在跑
docker compose ps backend

# 2. 看 backend 的实时日志
docker compose logs -f backend

# 3. 尝试在别处登录，观察日志输出什么错误

# 4. 按 Ctrl+C 停止看日志

# 5. 如果还不行，进容器做健康检查
docker exec -it backend bash
bench doctor
exit
```

---

## 命令速查表

| 我想做什么 | 命令 |
|-----------|------|
| 看看自己改了什么 | `git status` |
| 看看改了哪些具体内容 | `git diff` |
| 看看谁提交了什么 | `git log --oneline -10` |
| 开始新功能 | `git checkout -b feature/功能名` |
| 保存一个版本 | `git add .` 然后 `git commit -m "..."` |
| 上传到 GitHub | `git push` |
| 拉取最新代码 | `git pull` |
| 暂存半成品改动 | `git stash` |
| 恢复暂存的改动 | `git stash pop` |
| 撤销最近一次提交（保留改动） | `git reset --soft HEAD~1` |
| 启动 Docker 环境 | `docker compose up -d` |
| 停止 Docker 环境 | `docker compose stop` |
| 查看容器状态 | `docker compose ps` |
| 看容器日志 | `docker compose logs -f` |
| 只读后端日志 | `docker compose logs -f backend` |
| 进入容器内部 | `docker exec -it backend bash` |
| 数据库迁移 | `bench --site frontend migrate`（容器内） |
| 重新编译前端 | `bench build`（容器内） |
| 清缓存 | `bench --site frontend clear-cache`（容器内） |
| 重启服务 | `bench restart`（容器内） |
| 健康检查 | `bench doctor`（容器内） |
| 看安装了哪些 App | `bench --site frontend list-apps`（容器内） |

---

## 最后的提醒

1. **不确定时，先问**。宁肯多问一句，不要因为误操作丢了代码或数据。
2. **养成 `git status` 的习惯**。每次操作前先看一眼，很多问题可以提前避免。
3. **提交粒度小一点**。不要攒了一整天的改动一次性提交。改完一个逻辑就提交一次，出了问题也容易定位。
4. **每次 push 前先 pull**。这能避免大部分冲突。
5. **如果遇到冲突不要慌**。Git 会明确告诉你哪些文件有冲突。打开文件找到 `<<<<<<<` 和 `>>>>>>>` 标记，和同事商量一下保留谁的版本。
6. **🔴 标记的命令一定要记住**，这些是真正会造成不可逆损害的操作。
