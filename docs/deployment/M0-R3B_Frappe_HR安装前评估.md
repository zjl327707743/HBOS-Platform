# M0-R3B Frappe HR 安装前评估

项目名称：新乡海滨智能运营管理平台。

## 本轮目标

本轮只评估 Frappe HR / HRMS 在当前 Frappe / ERPNext Docker 最小环境中的安装可行性、候选安装方式、推荐路径、风险与回滚方案。

本轮不直接安装 HRMS，不创建海滨自定义 Frappe App，不开发考勤业务，不接飞书真实写入，不做前端驾驶舱。

## 本轮读取文件

- `README.md`
- `CLAUDE.md`
- `AGENTS.md`
- `docs/AI_CONTEXT.md`
- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/READING_GUIDE.md`
- `docs/milestones/README.md`
- `docs/milestones/M0.md`
- `docs/deployment/M0-R3A_Frappe_Docker最小环境落地记录.md`
- `docker-compose.yml`
- `.env.example`
- `.gitignore`

## 当前环境事实

当前 Frappe / ERPNext Docker 最小环境已跑通，M0-R3A 状态为 COMPLETED。

| 项目 | 当前事实 |
| --- | --- |
| Compose 项目 | `hbos-m0-r3a` |
| 当前 site | `frontend` |
| 当前访问地址 | `http://localhost:8081/login` |
| ERPNext 版本 | `16.26.2` |
| Frappe 版本 | `16.25.0` |
| 当前已安装 App | `frappe`、`erpnext` |
| HRMS 状态 | 未安装 |

当前容器状态摘要：

- `backend`：运行中
- `db`：运行中且健康
- `frontend`：运行中，宿主机端口 `8081` 映射到容器端口 `8080`
- `queue-long` / `queue-short` / `scheduler` / `websocket`：运行中
- `redis-cache` / `redis-queue`：运行中
- `configurator` / `create-site`：已成功退出

## HRMS 官方信息

官方仓库名称：`frappe/hrms`。

官方文档定位：Frappe HR 是开源 HR 和 Payroll 软件，是基于 Frappe Framework 构建的 HRMS 方案。

官方文档和仓库描述覆盖的主要能力包括：

- 员工管理
- 人事流程
- 入职
- 请假与考勤
- 费用报销
- 绩效管理
- 薪资与税务
- 移动端使用

截至本轮评估，官方 `frappe/hrms` 仓库存在 `version-16` 分支；官方 release 页面可见 `v16.12.0`、`v16.11.0`、`v16.10.1`、`v16.10.0` 等 v16 tag。

本轮直接检查 `version-16` 分支的 `pyproject.toml`，其 Frappe 依赖声明为：

```text
frappe = ">=16.0.0,<17.0.0"
erpnext = ">=16.0.0,<17.0.0"
requires-python = ">=3.10"
```

兼容性判断：

- 当前环境 `frappe 16.25.0` 与 `erpnext 16.26.2` 均落在 HRMS `version-16` 的官方依赖范围内。
- 因此，从主版本依赖范围看，HRMS `version-16` 与当前 v16 环境方向一致。
- 具体采用 `version-16` 分支还是某个 v16 tag，需要在 M0-R3C 安装前再次确认。当前推荐优先 pin 到明确 v16 tag；如官方安装流程更推荐分支，则记录分支 commit。
- 本轮不硬猜某个 tag 与当前镜像的完全运行时兼容性，最终仍以 M0-R3C 实际安装日志、`bench version` 和 Desk 模块访问验证为准。

## 官方参考来源

- Frappe HR 官方介绍文档：`https://docs.frappe.io/hr/introduction`
- `frappe/hrms` 官方 GitHub 仓库：`https://github.com/frappe/hrms`
- `frappe/hrms` 官方 releases：`https://github.com/frappe/hrms/releases`
- `frappe/hrms` `version-16` 分支 `pyproject.toml`：`https://raw.githubusercontent.com/frappe/hrms/version-16/pyproject.toml`
- `frappe/frappe_docker` 官方仓库：`https://github.com/frappe/frappe_docker`

## 安装方式候选

### 方案 A：在现有容器 / bench 内安装 HRMS

候选执行方式只供 M0-R3C 参考，本轮不执行：

```text
docker compose exec backend bench get-app hrms --branch version-16
docker compose exec backend bench --site frontend install-app hrms
docker compose exec backend bench --site frontend migrate
docker compose exec backend bench --site frontend list-apps
```

优点：

- 操作路径短，能最快验证 HRMS 是否能装进当前 site。
- 不需要立即重构镜像或 Compose 文件。
- 适合一次性本地验证和错误证据收集。

风险：

- 当前 Compose 主要持久化 `sites` 和 `logs`，没有把 bench 的 `apps` 目录设计为明确持久化目标。
- `bench get-app` 下载到容器内的 App 代码可能随容器重建丢失。
- `install-app` 会修改当前 `frontend` site 和数据库，可能污染已经跑通的 ERPNext 最小环境。
- 如果安装失败，当前 site 可能进入半迁移或半安装状态。

是否适合当前阶段：

- 仅适合作为 M0-R3C 的短期验证方案，并且必须先备份 site / 数据卷。
- 不适合作为长期可复现部署方案。

是否污染当前最小环境：

- 会污染当前 `frontend` site，因为安装会写数据库、site 配置和迁移状态。

回滚方式：

- 安装前执行 site 备份并记录 `bench version`、`bench --site frontend list-apps`。
- 失败后优先使用安装前备份恢复。
- 如本地测试环境可丢弃，可停止容器并清理相关 Docker volumes 后按 M0-R3A 重新初始化。
- 不把容器内临时下载的 HRMS App 视为可长期保留资产。

### 方案 B：重新构建包含 HRMS 的自定义镜像或扩展 Compose 流程

候选执行方式只供 M0-R3C 或后续轮次参考，本轮不执行：

- 基于官方 `frappe/frappe_docker` 自定义应用镜像思路，将 HRMS `version-16` 或明确 v16 tag 纳入镜像构建。
- 使用新镜像启动环境，再创建或迁移 site，并执行 `install-app hrms`。
- 在文档中固定 HRMS 来源、tag / branch、构建命令、安装日志和回滚步骤。

优点：

- HRMS App 代码随镜像存在，符合容器不可变和可复现部署原则。
- 容器重建后不容易丢失 App 代码。
- 更适合后续从本地验证过渡到长期开发或部署方案。

风险：

- 需要新增或调整镜像构建流程，变更面大于方案 A。
- 需要再次核对官方 `frappe_docker` 自定义 App 构建方式。
- 可能需要新建 site 或迁移当前 site，执行成本更高。
- 如果直接改现有 Compose，仍可能影响当前已跑通的最小环境。

是否适合当前阶段：

- 适合作为 M0-R3C 的推荐方向，但应尽量使用独立测试 site / 独立 Compose project 或清晰备份后的可回滚流程。
- 如果 M0-R3C 只追求最小验证，可先采用方案 A；如果 M0-R3C 要形成可复现环境，应采用方案 B。

是否污染当前最小环境：

- 如果使用独立 site / 独立 Compose project，可降低对当前 `frontend` site 的污染。
- 如果复用当前 site，仍会修改数据库和 site 状态。

回滚方式：

- 保留 M0-R3A 已验证配置不变。
- 新镜像和扩展 Compose 变更必须独立提交，失败时可通过 Git 回退配置。
- 若使用独立 Docker volumes，失败时可停止容器并删除本轮新增 volumes。
- 若复用当前 site，必须先备份并保留恢复命令。

## 推荐方案

M0-R3C 推荐采用“先备份、再隔离验证、最后记录”的方式。

优先推荐：

1. 保留当前已跑通的 M0-R3A 最小环境作为基线。
2. 在安装 HRMS 前备份 `frontend` site，并记录当前 App 清单与版本。
3. 优先评估使用包含 HRMS 的自定义镜像或扩展 Compose 流程，避免容器重建后丢失 `bench get-app` 下载的 App 代码。
4. 如 M0-R3C 需要快速验证，可在现有容器中执行方案 A，但必须明确这是短期本地验证，不作为长期部署方案。
5. 安装完成后只验证 HRMS App 是否出现在 Desk、基础 HR 模块是否可访问、版本是否可记录。

不推荐：

- 不直接修改 Frappe / ERPNext / HRMS 核心源码。
- 不把 HRMS 安装成功等同于考勤业务开发完成。
- 不在 M0-R3C 创建 `hb_attendance_app` 或任何海滨自定义 App。
- 不把飞书接入、审批流、考勤规则、前端驾驶舱混入 HRMS 安装验证。

## M0-R3C 边界建议

下一轮如果进入 HRMS 安装验证，只允许：

- 安装 HRMS。
- 验证 HRMS App 出现在 Desk。
- 验证基础 HR 模块可访问。
- 记录安装命令、日志摘要、版本、App 清单和访问验证结果。
- 记录回滚方式和是否污染当前 site。

仍禁止：

- 创建 `hb_core_app`。
- 创建 `hb_attendance_app`。
- 创建 `hb_feishu_app`。
- 开发考勤规则。
- 接入飞书真实写入。
- 做自定义 Vue / React 前端。
- 修改 Frappe / ERPNext / HRMS 核心源码。

## 风险与回滚

| 风险 | 说明 | 最小应对 |
| --- | --- | --- |
| HRMS 与当前 v16 镜像版本不匹配 | 虽然 HRMS `version-16` 声明兼容 Frappe / ERPNext 16，但具体 tag 与当前镜像仍需实际验证 | M0-R3C 安装前固定 tag / branch，并记录失败日志 |
| `bench get-app` 持久化风险 | 在容器中下载 App 可能不随容器重建保留 | 优先自定义镜像；若短期验证，记录其临时性 |
| `install-app` 数据卷污染 | 安装会修改 site 数据库和迁移状态 | 安装前备份 site 和 volumes |
| 重新创建 site 成本 | 失败后可能需要删除 volume 并重建 site | 保留 M0-R3A 操作记录和初始化命令 |
| 端口 / 容器状态变化 | 当前已用 `8081` 规避宿主机 `8080` 占用 | 不在 M0-R3B 修改端口；M0-R3C 如需调整只改本地 `.env` |

回滚方式：

- 安装前执行 site 备份。
- 保留安装前 `bench version` 和 `bench --site frontend list-apps` 输出。
- 如失败，优先从备份恢复 site。
- 如本地测试环境可丢弃，可执行 `docker compose down` 后按记录清理本轮新增 volume，再回到 M0-R3A 初始化路径。
- 如采用自定义镜像 / Compose 扩展，失败时通过 Git 回退配置文件，并删除本轮新增镜像或 volumes。

## 本轮结论

状态：REVIEWING。

HRMS `version-16` 与当前 Frappe / ERPNext v16 环境在官方依赖范围上匹配，但本轮不执行安装。M0-R3C 应在备份和可回滚前提下安装 HRMS，并只验证 HRMS 出现和基础模块可访问，不进入考勤业务开发。

## 未做事项

- 未安装 HRMS。
- 未创建 `hb_core_app`。
- 未创建 `hb_attendance_app`。
- 未创建 `hb_feishu_app`。
- 未开发考勤业务。
- 未接飞书真实写入。
- 未做前端驾驶舱。
- 未新增 Python / JavaScript / TypeScript 业务代码。
- 未修改 `docker-compose.yml`、`.env.example`、`.gitignore`。
- 未 push。
