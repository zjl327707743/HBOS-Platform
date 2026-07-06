# M0-R2 Frappe Docker Environment Design

项目名称：新乡海滨智能运营管理平台。

## M0-R2 目标

M0-R2 的目标是设计 Frappe / ERPNext / Docker 最小本地开发环境方案，明确后续落地前需要确认的服务边界、目录规划、端口规划、数据卷规划、环境变量分组和风险点。

本轮只输出设计文档，不执行安装、生成、运行或部署动作。

## 本轮范围

- 设计 Frappe / ERPNext 最小 Docker 服务组成。
- 设计本地开发目录、端口、数据卷和环境变量分类。
- 说明本地开发密钥与 `.env` 的管理原则。
- 更新当前项目状态、当前里程碑和阅读指南。
- 为 M0-R3 真正落地最小环境预留清晰边界。

## 明确不做事项

- 不安装 Frappe、ERPNext 或 Frappe HR。
- 不创建 Frappe bench。
- 不创建任何 Frappe App。
- 不创建 `hb_core_app`、`hb_attendance_app`、`hb_feishu_app`。
- 不编写 `docker-compose.yml`。
- 不启动容器。
- 不开发考勤业务。
- 不接入飞书。
- 不实现 Vue/React 驾驶舱。
- 不引入外部源码。
- 不配置远端仓库。
- 不 push。

## 设计交付物清单

- `docs/plans/M0-R2_Frappe_Docker最小环境方案设计.md`
- `docs/deployment/Frappe_Docker最小部署设计.md`
- `docs/deployment/本地开发环境变量说明.md`
- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/READING_GUIDE.md`

## M0-R3 执行边界

M0-R3 才允许在用户明确批准后进入实际最小环境落地，包括：

- 选择具体 Frappe / ERPNext / Frappe HR 镜像版本。
- 编写 `docker-compose.yml` 或等价环境编排文件。
- 创建本地 `.env` 文件并加入忽略规则。
- 拉取镜像、启动容器、初始化 site。
- 验证 Frappe Desk 和 ERPNext 基础页面可访问。

M0-R2 不执行上述动作，只做方案设计。

## M0-R2 验收标准

- 三个新增 M0-R2 设计文档存在。
- 设计文档覆盖最小服务清单、本地目录、端口、数据卷和环境变量分组。
- 状态文档明确 M0-R1 已完成，M0-R2 为设计阶段成果。
- 当前里程碑指向 M0-R2，并明确 M0-R3 才进入实际环境落地。
- 阅读指南保留默认读取规则，并补充 M0-R2 允许读取的计划和部署设计文档。
- 仓库内没有 `docker-compose.yml`、`.env`、Frappe bench、Frappe App、业务代码、飞书代码或前端驾驶舱代码。

## 状态文件更新要求

M0-R2 收尾时必须更新：

- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/milestones/M0.md`

如果后续审查要求补充 M0-R2A 或 M0-R2B，也必须同步更新上述状态文件。

## 风险点

- Frappe Docker 版本：镜像标签、启动命令和变量约定可能随版本变化，M0-R3 前需要锁定版本。
- ERPNext / Frappe HR 兼容性：ERPNext、Frappe Framework 和 Frappe HR / HRMS 必须匹配同一兼容版本线。
- MariaDB 版本：数据库版本需要符合 Frappe / ERPNext 支持范围，避免字符集、排序规则或迁移兼容问题。
- Mac 本地性能：Docker Desktop 在 macOS 上可能存在 I/O 慢、内存不足和文件同步性能问题。
- 端口冲突：本地可能已有 80、443、8000、8080、3306、6379 等端口占用。
- 数据卷清理风险：删除数据库、站点文件或 Redis 数据卷可能造成环境状态丢失，M0-R3 必须明确备份与清理步骤。
