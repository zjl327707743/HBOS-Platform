# 项目治理待办与 Owner 决策清单

> 生成日期：2026-07-14
> 基于：项目结构审计（`docs/team/01_项目真实结构与代码归属审计.md`）、仓库架构方案（`docs/team/02_目标仓库架构与迁移方案.md`）、项目状态（`docs/PROJECT_STATUS.md`）、当前里程碑（`docs/CURRENT_MILESTONE.md`）、ADR（`docs/adr/`）、协作规则（`CLAUDE.md`、`AGENTS.md`）
> 用途：列出所有需要 Owner 知晓、拍板或授权的事项，按紧迫度排列。每项应足够清晰，Owner 可以直接说"做 X"而不需要阅读完整文档。

---

## 1. 必须立即处理（本周内）

这些事项如果不处理，存在数据丢失或工作中断的直接风险。

### 1.1 推送本地领先的 9 个 commit 到 GitHub

| 项目 | 内容 |
|------|------|
| **问题描述** | 本地 `main` 分支领先 `origin/main` 9 个 commit。这些 commit 包含 M1-FIX-B 系列的全部工作（`hb_attendance_app` 源码、团队协作文档 12 篇、审计文档等），目前仅存在于本地 Mac 上。 |
| **影响** | 如果本地机器硬盘故障、误删目录或系统崩溃，9 个 commit 的全部工作将丢失，无法从 GitHub 恢复。 |
| **建议方案** | 执行 `git push origin main`，将本地领先的 commit 推送到 GitHub Private 仓库。 |
| **前置条件** | 无。当前工作区干净，无未提交变更。 |
| **Owner 需要确认** | "同意推送，执行 `git push origin main`" |
| **风险** | 极低。推送只增加远端 commit，不修改已有历史。 |

### 1.2 创建 Docker 卷数据备份

| 项目 | 内容 |
|------|------|
| **问题描述** | 全部业务数据库（MariaDB）和 site 配置（`site_config.json`、上传附件等）仅存储在 Docker 命名卷中（`hbos-m0-r3a_db-data`、`hbos-m0-r3a_sites`）。如果执行 `docker compose down -v` 或卷损坏，所有数据将永久丢失。当前无任何备份。 |
| **影响** | 数据库丢失意味着所有 Employee、Attendance、Employee Checkin、Shift Type、Shift Assignment、Leave Application、Holiday List、Company、Department、User 以及 Frappe UI 自定义配置全部丢失。site 配置丢失意味着需要重新执行 `bench new-site` 并重新配置所有设置。 |
| **建议方案** | 方案 A（最小）：使用 `docker compose exec db mariadb-dump --all-databases` 导出数据库，并 `docker compose cp` 导出 site_config.json。方案 B（完整）：在 `docker-compose.yml` 同级目录创建 `backups/` 目录，加入定时备份脚本。 |
| **前置条件** | Docker 容器必须处于运行状态。 |
| **Owner 需要确认** | "同意执行方案 A，立即做一次数据库全量备份" 或 "同意执行方案 B，并建立定时备份" |
| **风险** | 不备份的风险远大于备份操作本身。备份操作只读不写，不影响运行中的容器。 |

### 1.3 导出 Frappe UI 自定义配置到 Fixtures

| 项目 | 内容 |
|------|------|
| **问题描述** | 通过 Frappe Desk 界面进行的所有自定义配置（Custom Field、Property Setter、Workspace 自定义、Role 调整、Workflow 配置等）仅存储在数据库中，未通过 Fixture 机制导出为 JSON 文件纳入 Git 版本控制。 |
| **影响** | 如果数据库需要重建（如迁移服务器、恢复备份、或 `docker compose down -v`），所有 UI 层面的自定义配置将丢失，需要手动逐个重新配置。这包括 M1-FIX 阶段创建的所有 Workspace 布局、Desktop Icon、Report 配置等。 |
| **建议方案** | 在 Frappe Desk 中逐模块使用 "Export Fixtures" 功能，将自定义配置导出为 JSON 文件，放入 `apps/hb_attendance_app/hb_attendance_app/fixtures/` 目录，并在 `hooks.py` 的 `fixtures` 列表中注册。 |
| **前置条件** | Frappe Desk 可正常访问（`http://localhost:8081`）。需要确认哪些 DocType 有自定义配置。 |
| **Owner 需要确认** | "同意导出 Fixtures，优先导出 hb_attendance_app 相关的 Workspace、Report、Desktop Icon 配置" |
| **风险** | 低。导出是只读操作，不影响运行中的系统。 |

### 1.4 确认 `.env` 文件的 Git 忽略状态

| 项目 | 内容 |
|------|------|
| **问题描述** | 审计显示 `.gitignore` 中已包含 `.env` 规则，`git ls-files` 检查确认 `.env` 未被 Git 跟踪。但 `.env` 文件在宿主机上物理存在，包含数据库密码、管理员密码等真实密钥。需要双重确认无误。 |
| **影响** | 如果 `.env` 被意外提交到 Git 历史，数据库密码和管理员密码将永久暴露在 Git 历史中（即使后续删除文件，历史中仍可找回）。由于仓库为 Private，风险相对可控，但仍需确认。 |
| **建议方案** | 执行 `git check-ignore -v .env` 确认忽略规则来源，并检查 `.gitignore` 中 `.env` 规则是否在文件末尾且未被覆盖。同时建议执行 `chmod 600 .env` 限制文件权限。 |
| **前置条件** | 无。 |
| **Owner 需要确认** | "同意确认 .env 忽略状态，并限制文件权限" |
| **风险** | 低。确认操作只读，不修改任何文件。 |

### 1.5 明确 M1-FIX-B3/B4/B5 的最终处理决策

| 项目 | 内容 |
|------|------|
| **问题描述** | M1-FIX-B3（Owner UI 验收未通过）、M1-FIX-B4（Claude PASS 但 Owner 数据链路验收发现后续问题）、M1-FIX-B5（REVIEWING 等待 Owner 审查）三个轮次均处于 REVIEWING 状态，均未 closeout。M1-FIX-C/D/E 处于 PLANNED 状态等待 Owner 授权。 |
| **影响** | 如果不对 B3/B4/B5 做出最终决策（closeout 或继续修复），M1-FIX 阶段无法收敛，M2 无法启动。项目进度停滞在 "审查中" 状态。 |
| **建议方案** | 逐项决策：B3 是否接受当前状态 closeout 还是需要继续修复入口命名问题；B4 数据链路问题是否已由 B5 解决；B5 审查结论是什么。 |
| **前置条件** | Owner 需要在浏览器中实际验收 B5 的报表和数据链路。 |
| **Owner 需要确认** | 对 B3、B4、B5 逐一给出"接受 closeout"或"继续修复（列出具体问题）"的决策。 |

---

## 2. 一周内处理

这些事项有明确风险，但不会立即导致数据丢失。建议在 M1-FIX 收口前完成。

### 2.1 设置 GitHub 分支保护规则

| 项目 | 内容 |
|------|------|
| **问题描述** | GitHub 仓库 `zjl327707743/HBOS`（Private）的 `main` 分支没有任何保护规则。任何人都可以直接 force push 到 `main`，或未经审查直接合并。 |
| **影响** | 虽然当前只有 Owner 一人操作，但一旦误操作（如 `git push --force`），可能覆盖远端历史。未来有第二人加入时，风险急剧上升。 |
| **建议方案** | 在 GitHub 仓库 Settings > Branches 中添加 `main` 分支保护规则：禁止 force push、禁止删除分支、要求 PR 合并（当前可设 0 个审批人，未来有人加入后改为 1）。 |
| **前置条件** | 需要 Owner 有 GitHub 仓库的 Admin 权限（当前 Owner 就是仓库所有者，已有权限）。 |
| **Owner 需要确认** | "同意设置 main 分支保护，禁止 force push 和直接 push" |

### 2.2 将 HRMS 安装纳入 docker-compose 自动化

| 项目 | 内容 |
|------|------|
| **问题描述** | HRMS 是通过 `bench get-app hrms --branch version-16` 手动安装到运行中容器的。当前 `docker-compose.yml` 不包含 HRMS 的自动化安装。如果容器重建，HRMS 不会自动安装。 |
| **影响** | 新成员搭建环境时，需要在容器启动后手动执行 `bench get-app` 和 `bench install-app`，且需要额外处理 HRMS 静态资源同步到 frontend 容器的问题（M0-R3C-FIX 中已诊断此问题）。 |
| **建议方案** | 方案 A（推荐）：修改 `docker-compose.yml` 的 `configurator` 服务，在初始化脚本中加入 HRMS 的 `bench get-app` 和 `bench install-app` 步骤。方案 B：构建包含 HRMS 的自定义 Docker 镜像。方案 A 更适合当前阶段。 |
| **前置条件** | 需要确认 `configurator` 服务的初始化脚本格式和挂载点。需要测试重建容器后 HRMS 能否正常安装。 |
| **Owner 需要确认** | "同意方案 A，将 HRMS 安装加入 docker-compose 自动化" |

### 2.3 创建最小 CI/CD 门禁

| 项目 | 内容 |
|------|------|
| **问题描述** | 当前仓库没有任何 CI/CD 流程。没有自动化检查来验证 `docker-compose.yml` 配置有效性、Python 语法、或 Frappe App 基本结构。 |
| **影响** | 所有质量检查依赖人工审查（Codex）。随着代码量增加，人工审查的遗漏风险上升。 |
| **建议方案** | 创建 `.github/workflows/ci.yml`，包含最小门禁：(1) `docker compose config` 验证 Compose 文件语法；(2) Python 语法检查（`python -m py_compile` 对 `apps/` 目录）；(3) JSON 格式验证（对 fixtures 目录）。不需要完整的测试环境启动。 |
| **前置条件** | 需要创建 `.github/workflows/` 目录和 CI 配置文件。 |
| **Owner 需要确认** | "同意创建最小 CI 门禁，包含 Compose 验证和 Python 语法检查" |

### 2.4 版本锁定 Docker 镜像

| 项目 | 内容 |
|------|------|
| **问题描述** | 当前 `docker-compose.yml` 中 `frappe/erpnext:v16.26.2` 已锁定版本，但 `redis:6.2-alpine` 和 `mariadb:11.8` 使用的是 floating tag（`6.2-alpine` 可能指向 `6.2.x` 的最新小版本，`11.8` 可能指向 `11.8.x` 的最新小版本）。 |
| **影响** | 如果 Redis 或 MariaDB 的 floating tag 在某次 `docker compose pull` 时拉取到不兼容的小版本，可能导致容器启动失败或行为异常。Frappe/ERPNext 镜像 `v16.26.2` 如果未来从 Docker Hub 下架，当前环境无法重建。 |
| **建议方案** | (1) 将 `redis:6.2-alpine` 和 `mariadb:11.8` 替换为精确 digest（如 `redis:6.2-alpine@sha256:xxx`）或至少锁定到精确小版本。(2) 考虑将 `frappe/erpnext:v16.26.2` 镜像推送到私有镜像仓库或 `docker save` 导出为 tar 文件备份。 |
| **前置条件** | 需要先 `docker image inspect` 获取当前 digest。 |
| **Owner 需要确认** | "同意锁定 Redis 和 MariaDB 镜像到精确版本，并备份 frappe/erpnext 镜像" |

### 2.5 创建新环境 bootstrap 脚本

| 项目 | 内容 |
|------|------|
| **问题描述** | 当前从零搭建 HBOS 开发环境需要阅读多份文档（`04_Docker开发环境复现手册.md`、`07_新成员入职与本地环境上手手册.md`、部署记录等），手动执行多个步骤。没有一个一键脚本可以完成 `.env` 生成、镜像拉取、容器启动、site 创建、HRMS 安装、`hb_attendance_app` 安装的全流程。 |
| **影响** | 新成员入职或 Owner 换机器时，环境搭建过程容易出错。当前环境依赖 Owner 本地 Mac 上的 Docker 卷，无法在其他机器上复现。 |
| **建议方案** | 创建 `scripts/bootstrap.sh`，按顺序执行：(1) 检查 Docker/Compose 是否安装；(2) 从 `.env.example` 交互式生成 `.env`；(3) `docker compose pull`；(4) `docker compose up -d`；(5) 等待 healthy；(6) 创建 site；(7) 安装 HRMS；(8) 安装 `hb_attendance_app`；(9) 导入 fixtures；(10) 打印 Desk 访问地址。 |
| **前置条件** | 需要容器启动后能自动完成 site 创建和 app 安装。这与 2.2（HRMS 自动化）和 1.3（Fixture 导出）密切相关。 |
| **Owner 需要确认** | "同意创建 bootstrap 脚本，在 2.2 和 1.3 完成后执行" |

---

## 3. 后续处理（M2 前）

这些事项不紧急，但应在 M2 正式启动前完成，以确保项目进入多人协作和正式开发阶段时具备基本工程保障。

### 3.1 仓库策略决策与迁移

| 项目 | 内容 |
|------|------|
| **问题描述** | 当前所有内容（文档、Docker 编排、`hb_attendance_app` 源码、团队规范）全部在一个仓库中。文档 `02_目标仓库架构与迁移方案.md` 推荐混合模式（`hbos-docs` 文档仓库 + `hbos-platform` 平台仓库 + `hbos-apps/*` App 仓库）。需要 Owner 决策最终方案。 |
| **影响** | 随着 App 数量增加，单一仓库的提交历史混杂、权限不好区分、CI 配置复杂。但现在不拆分也可以继续开发，只是债务会累积。 |
| **建议方案** | 建议在 M1-FIX 全部 closeout 后、M2 启动前执行拆分。优先执行混合模式的最小拆分：先拆出 `hb_attendance_app` 为独立仓库，其余暂时保留在 monorepo 中。 |
| **前置条件** | M1-FIX 全部 closeout。所有 Fixture 已导出。所有 commit 已 push。 |
| **Owner 需要确认** | 见第 4 节「仓库策略」决策项。 |

### 3.2 从个人账号迁移到 GitHub Organization

| 项目 | 内容 |
|------|------|
| **问题描述** | 当前仓库在 Owner 个人 GitHub 账号 `zjl327707743` 下。随着团队扩展，个人账号不适合作为团队协作的长期方案。 |
| **影响** | 权限管理受限（只能添加 Collaborator，无法设置 Team 级别权限）。仓库归属与个人账号绑定，不便于公司资产管理。 |
| **建议方案** | 创建 GitHub Organization（如 `haibin-hbos`），将仓库迁移到 Organization 下。迁移后 GitHub 会自动重定向，不影响现有 clone 和 remote。 |
| **前置条件** | 需要 Owner 注册 GitHub Organization（免费）。所有 commit 已 push。 |
| **Owner 需要确认** | "同意创建 GitHub Organization 并迁移仓库" |

### 3.3 设置自动化备份

| 项目 | 内容 |
|------|------|
| **问题描述** | 当前无任何自动化备份机制。1.2 建议的是手动一次性备份。 |
| **影响** | 随着真实业务数据增长，每日手动备份不现实。数据丢失的风险随时间推移持续增加。 |
| **建议方案** | 创建 `scripts/backup.sh`，使用 cron 或 launchd 定时执行：(1) `mariadb-dump` 全量导出；(2) 备份 `site_config.json`；(3) 备份 `sites/frontend/private/files/` 上传文件；(4) 保留最近 7 天备份，自动清理旧备份。 |
| **前置条件** | 需要 Owner 确认备份存储位置（本地目录 vs 云存储）。建议先做本地备份，M2 后再考虑云存储。 |
| **Owner 需要确认** | "同意创建定时备份脚本，备份到本地 `backups/` 目录，保留 7 天" |

### 3.4 设置 staging 环境

| 项目 | 内容 |
|------|------|
| **问题描述** | 当前只有 Owner 本地 Mac 上一套环境，既是开发环境也是验收环境。没有独立的 staging 环境用于 M2 阶段的功能验收和 Owner 审查。 |
| **影响** | 开发、测试、验收在同一环境，容易出现"在我机器上能跑"的问题。M2 多人协作时，不同人的修改会互相干扰。 |
| **建议方案** | 找一台机器（可以是另一台 Mac、云服务器或内网机器），用 bootstrap 脚本搭建独立 staging 环境。使用不同端口（如 8082）或不同 Docker Compose project name 隔离。 |
| **前置条件** | bootstrap 脚本已完成（3.5）。需要一台额外的机器或足够资源的云服务器。 |
| **Owner 需要确认** | "同意在 M2 启动前准备 staging 环境" |

### 3.5 添加 Secret 扫描到 CI

| 项目 | 内容 |
|------|------|
| **问题描述** | 当前依赖 `.gitignore` 和人工审查防止密钥泄露。没有自动化扫描来检测是否意外提交了 `.env`、密码、token 或 API key。 |
| **影响** | 如果某次提交意外包含了密钥（如 `.env.example` 被误改为 `.env` 内容），人工审查可能遗漏。虽然仓库是 Private，但密钥泄露到 Git 历史后清除成本很高。 |
| **建议方案** | 在 CI 中加入 `trufflehog` 或 `gitleaks` 扫描，在每次 push 时自动检测。也可以在 `.github/workflows/` 中配置。 |
| **前置条件** | CI 门禁已创建（2.3）。 |
| **Owner 需要确认** | "同意在 CI 中加入 Secret 扫描" |

### 3.6 设置监控和告警

| 项目 | 内容 |
|------|------|
| **问题描述** | 当前对 Docker 容器状态、数据库连接、磁盘使用、应用错误日志无任何监控。M1-R3A 中 Redis 容器退出后，直到试运行失败才发现。 |
| **影响** | 服务异常无法及时发现。容器退出、数据库连接失败、磁盘满等问题可能持续数天无人知晓。 |
| **建议方案** | 最小方案：使用 Docker Compose 内置的 `healthcheck` + 一个简单的健康检查脚本，定时检查各容器状态和 Desk 登录页可达性。进阶方案：引入 Uptime Kuma 或 Grafana + Prometheus。 |
| **前置条件** | 需要 staging 环境或独立的监控服务。 |
| **Owner 需要确认** | "同意在 M2 阶段引入最小监控（healthcheck + Desk 可达性检查）" |

### 3.7 为 `hb_attendance_app` 添加 LICENSE 文件

| 项目 | 内容 |
|------|------|
| **问题描述** | `apps/hb_attendance_app/` 目录下没有 LICENSE 文件。根据审计文档第 9 节，ERPNext 使用 GPLv3（具有传染性），Frappe Framework 使用 MIT。`hb_attendance_app` 作为 ERPNext 的运行时 App，其许可证选择有法律影响。 |
| **影响** | 如果未来需要分发或展示 `hb_attendance_app`，缺少许可证声明会产生法律不确定性。 |
| **建议方案** | 建议咨询法律顾问后选择许可证。如果确定闭源，需要确认 Frappe App 的许可证边界。如果跟随 ERPNext 生态，GPLv3 是常见选择。 |
| **前置条件** | 建议咨询法律顾问。 |
| **Owner 需要确认** | "同意在 M2 前确定 hb_attendance_app 的许可证并添加 LICENSE 文件" |

---

## 4. 需要 Owner 决策的关键问题

以下问题没有明显的"默认正确答案"，需要 Owner 根据业务方向、团队规划和资源做出主动选择。

### 4.1 仓库策略：Monorepo vs 多仓库 vs 混合模式

| 项目 | 内容 |
|------|------|
| **问题** | 当前所有内容在一个仓库。未来多 App 时，是继续单仓库（Monorepo）、每个 App 独立仓库（多仓库）、还是文档 + 平台 + App 分三层（混合模式）？ |
| **选项 A：Monorepo** | 所有内容继续放在一个仓库。优点：简单、一个 clone 获得全部、无版本协调问题。缺点：提交历史混杂、权限不好区分、仓库体积随 App 增多而膨胀。 |
| **选项 B：多仓库** | 每个 App 独立仓库。优点：权限清晰、独立 CI/CD、独立版本。缺点：跨仓库协调复杂、新人需要 clone 多个仓库。 |
| **选项 C：混合模式** | `hbos-docs`（文档 + 团队规范）+ `hbos-platform`（Docker 编排 + 部署脚本）+ `hbos-apps/hb_attendance_app` 等 App 独立仓库。优点：文档与代码分离、平台与 App 分离、App 独立演进。缺点：需要维护多个仓库的版本兼容矩阵。 |
| **建议** | 文档 `02_目标仓库架构与迁移方案.md` 推荐选项 C（混合模式）。建议在 M2 启动前完成最小拆分：先拆出 `hb_attendance_app` 为独立仓库，其余保留在 monorepo 中。 |
| **原因** | 当前只有 1 个 App，全拆无必要。但 `hb_attendance_app` 是唯一业务代码，独立出去后 CI/CD 和权限管理更清晰。文档和平台编排可以继续留在当前仓库。 |
| **如果不决定的后果** | 仓库继续膨胀，M2 新 App 加入后拆分成本更高，Git 历史更复杂。 |

### 4.2 GitHub Organization 创建时机

| 项目 | 内容 |
|------|------|
| **问题** | 什么时候从个人账号 `zjl327707743` 迁移到 GitHub Organization？ |
| **选项 A：现在创建** | 立即创建 Organization，迁移仓库。优点：一步到位，后续所有操作都在 Organization 下。缺点：需要 Owner 花时间设置。 |
| **选项 B：M2 启动前创建** | 等 M1-FIX 全部 closeout 后再创建。优点：不打断当前工作流。缺点：当前仓库仍在个人账号下。 |
| **选项 C：有第二人加入时再创建** | 等真正需要多人协作时再创建。优点：不提前做不需要的事。缺点：届时迁移可能打断多人工作。 |
| **建议** | 选项 B。M1-FIX 收口后、M2 启动前是自然的迁移窗口。 |
| **原因** | 当前单人不急需 Organization，但 M2 可能涉及多人协作，提前准备好可以避免后续紧急迁移。 |
| **如果不决定的后果** | 仓库留在个人账号下，未来迁移时需通知所有协作者更新 remote。 |

### 4.3 Staging 环境部署位置

| 项目 | 内容 |
|------|------|
| **问题** | Staging 环境部署在哪里？ |
| **选项 A：云服务器** | 阿里云/腾讯云/AWS 等。优点：独立于本地机器、可公网访问（便于远程验收）。缺点：需要费用、需要 Owner 有云服务账号。 |
| **选项 B：内网机器** | 公司内部服务器或闲置机器。优点：数据安全、无额外费用。缺点：需要内网环境、远程访问不便。 |
| **选项 C：Owner 另一台 Mac** | 如果 Owner 有另一台 Mac。优点：环境一致、管理方便。缺点：受限于个人设备。 |
| **建议** | 选项 A（云服务器）。HBOS 长期目标是 SaaS 化运营，云服务器部署是必须走的路。从 staging 开始积累云部署经验。 |
| **原因** | 云服务器可以同时作为 staging 和未来生产环境的预演。费用可控（低配实例即可满足 staging 需求）。 |
| **如果不决定的后果** | Staging 环境无法搭建，M2 多人协作时开发、测试、验收仍在同一环境。 |

### 4.4 数据库备份策略：频率与保留

| 项目 | 内容 |
|------|------|
| **问题** | 数据库备份的频率和保留策略是什么？ |
| **选项 A：每日全量，保留 7 天** | 每天凌晨全量备份，自动删除 7 天前的备份。 |
| **选项 B：每日全量 + 每周归档，保留 30 天** | 每天全量备份，每周日额外做一次归档备份，保留 30 天。 |
| **选项 C：每日增量 + 每周全量** | 每天增量备份，每周全量备份。 |
| **建议** | 选项 A。当前数据量小，全量备份成本低。7 天保留足够覆盖大部分异常场景。 |
| **原因** | 当前只有测试和演示数据，M1-FIX 阶段不需要复杂的备份策略。M2 正式业务数据上线后再考虑升级到选项 B。 |
| **如果不决定的后果** | 备份策略不确定，不敢自动化备份，数据持续暴露在无保护状态。 |

### 4.5 M1-FIX 收口标准：什么算 "完成"

| 项目 | 内容 |
|------|------|
| **问题** | M1-FIX-B3/B4/B5 三个轮次均处于 REVIEWING，需要 Owner 明确什么状态算"可以 closeout"。 |
| **选项 A：所有 B3/B4/B5 问题全部修复后才 closeout** | 严格标准。优点：产品交付质量最高。缺点：M1-FIX 可能持续更久。 |
| **选项 B：B5 通过后即可 closeout B3/B4/B5** | 以 B5 为最终验证点。优点：B5 已覆盖数据链路和报表口径，B3/B4 的入口问题可以作为 M2 优化项。缺点：Owner 体验可能仍有瑕疵。 |
| **选项 C：逐项列出仍需修复的问题，其余 closeout** | Owner 列出 B3/B4/B5 中必须修复的 top 问题，修复后 closeout，其余问题转为 M2 backlog。 |
| **建议** | 选项 C。 |
| **原因** | M1-FIX 的目标是"功能补漏"而非"完美交付"。将非关键问题转为 M2 backlog 可以控制 M1-FIX 的结束边界，避免无限期延长。 |
| **如果不决定的后果** | M1-FIX 无限期停留在 REVIEWING，M2 无法启动。 |

### 4.6 M2 启动条件：M1-FIX 需要做到什么程度

| 项目 | 内容 |
|------|------|
| **问题** | M1-FIX 的哪些轮次必须完成（COMPLETED）才能启动 M2？ |
| **选项 A：M1-FIX-B 全部 closeout** | B3/B4/B5 全部 COMPLETED。M1-FIX-C/D/E 可以转为 M2 的一部分。 |
| **选项 B：M1-FIX-B 全部 closeout + C 完成** | 异常三级流程也必须在 M1 完成。 |
| **选项 C：M1-FIX 全部轮次完成** | B/C/D/E 全部 COMPLETED 后才启动 M2。 |
| **建议** | 选项 A。 |
| **原因** | M1-FIX-C（异常三级流程）、M1-FIX-D（工作台+月报+领导 Demo）、M1-FIX-E（飞书 OAuth）可以自然融入 M2 的考勤业务深化阶段，不必在 M1-FIX 中全部完成。M1-FIX 的核心使命是"让考勤导入链路可用"，这已在 B 系列中完成。 |
| **如果不决定的后果** | M2 启动条件模糊，不知道什么时候可以开始下一阶段。 |

---

## 5. 已确认的决策（记录用）

以下决策已在项目既有文档中明确做出，此处仅汇总记录，不需要 Owner 重新决策。如有变更，应更新对应的 ADR 或协作规则文件。

### 5.1 架构与技术选型

| 编号 | 决策 | 来源 | 决策日期 |
|------|------|------|----------|
| D-001 | 采用 Frappe/ERPNext 作为开源平台底座 | ADR-0001 | 2026-07-05 |
| D-002 | 采用 MariaDB/MySQL 兼容体系作为数据库路线 | ADR-0002 | 2026-07-05 |
| D-003 | 采用 Frappe Desk + Vue/React 双层前端 | ADR-0003 | 2026-07-05 |
| D-004 | 开源复用优先，不修改 Frappe/ERPNext/HRMS 核心源码 | ADR-0004 | 2026-07-05 |
| D-005 | M1 考勤优先评估 Frappe HR/HRMS 原生能力，不立即自研 | ADR-0004 | 2026-07-05 |
| D-006 | 优先使用原生配置、角色权限、DocType、报表、导入、API 和低代码定制 | PROJECT_STATUS.md | M0-FINAL |

### 5.2 开发与协作规则

| 编号 | 决策 | 来源 | 决策日期 |
|------|------|------|----------|
| D-007 | 不创建 `hb_core_app`、`hb_feishu_app`（未经 Owner 明确授权） | CLAUDE.md | M0-R1 |
| D-008 | 不执行 `docker compose down -v`、不删除 volume、不重建 `frontend` site | CURRENT_MILESTONE.md | M0-FINAL |
| D-009 | 飞书真实写入（群消息、多维表格、通讯录、审批、邮件、云文档、任务）必须用户明确授权 | AGENTS.md | M0-R2D |
| D-010 | 独立前端开发必须原型先行 → Owner 审查 → 复刻实现 → 功能接入 | FRONTEND_IMPLEMENTATION_GUIDE.md | M1-R6B |
| D-011 | Git commit message 优先使用中文描述 | CLAUDE.md | M0-R2D |
| D-012 | 新增文档文件名优先使用中文或中英混合命名 | CLAUDE.md | M0-R2D |

### 5.3 安全与数据

| 编号 | 决策 | 来源 | 决策日期 |
|------|------|------|----------|
| D-013 | `.env` 不提交 Git（已在 `.gitignore` 中） | PROJECT_STATUS.md | M0-R3A |
| D-014 | 真实员工数据（`docs/data/*.xlsx`、`docs/data/*.csv`）不提交 Git | CURRENT_MILESTONE.md | M1-FIX |
| D-015 | 不提交备份文件、数据库、Docker volume 或运行时数据 | PROJECT_STATUS.md | M0-FINAL |

---

## 决策速查表

| 序号 | 决策项 | 紧迫度 | 建议 | 所属章节 |
|------|--------|--------|------|----------|
| 1 | 推送 9 个 commit | 立即 | 执行 `git push origin main` | 1.1 |
| 2 | 数据库备份 | 立即 | 方案 A，执行一次全量备份 | 1.2 |
| 3 | 导出 Fixtures | 立即 | 导出 hb_attendance_app 相关配置 | 1.3 |
| 4 | .env 忽略状态确认 | 立即 | 双重确认 + 限制文件权限 | 1.4 |
| 5 | B3/B4/B5 最终决策 | 立即 | 逐项给出 closeout 或修复指令 | 1.5 |
| 6 | 分支保护 | 一周内 | 设置 main 分支保护规则 | 2.1 |
| 7 | HRMS 自动化安装 | 一周内 | 方案 A，修改 docker-compose | 2.2 |
| 8 | 最小 CI 门禁 | 一周内 | Compose 验证 + Python 语法检查 | 2.3 |
| 9 | 版本锁定 | 一周内 | 锁定 Redis/MariaDB 精确版本 | 2.4 |
| 10 | Bootstrap 脚本 | 一周内 | 创建一键环境搭建脚本 | 2.5 |
| 11 | 仓库策略 | M2 前 | 混合模式，先拆 hb_attendance_app | 4.1 |
| 12 | GitHub Organization | M2 前 | M1-FIX 收口后创建 | 4.2 |
| 13 | Staging 环境位置 | M2 前 | 云服务器 | 4.3 |
| 14 | 备份策略 | M2 前 | 每日全量，保留 7 天 | 4.4 |
| 15 | M1-FIX 收口标准 | 当前 | 选 C，列出必修复项后 closeout | 4.5 |
| 16 | M2 启动条件 | M2 前 | M1-FIX-B 全部 closeout 即可 | 4.6 |
| 17 | 自动化备份 | M2 前 | 创建定时备份脚本 | 3.3 |
| 18 | Secret 扫描 | M2 前 | CI 中加入 trufflehog/gitleaks | 3.5 |
| 19 | 监控告警 | M2 前 | 最小 healthcheck + Desk 可达性 | 3.6 |
| 20 | LICENSE 文件 | M2 前 | 咨询法律顾问后确定 | 3.7 |

---

*本文档基于 2026-07-14 项目审计生成。Owner 做出决策后，应在对应章节标记决策结果和日期。*