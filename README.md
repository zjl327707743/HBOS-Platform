# 新乡海滨智能运营管理平台

新乡海滨智能运营管理平台面向企业级智能运营管理，长期目标是在 Frappe/ERPNext 开源底座上建设海滨自定义业务 App、外部 AI/视频/算法服务、Vue/React 驾驶舱、飞书集成与 Docker 部署体系。

准确架构叫法：Frappe/ERPNext 开源底座 + Frappe 多 App 模块化架构 + 外部独立服务扩展。

## 当前阶段

当前处于 M0 工程启动阶段。

当前真实进度以以下文件为准：

- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/milestones/README.md`
- `docs/milestones/M0.md`

当前状态摘要：

- M0-R1 工程骨架与 AI 上下文治理已完成
- M0-R2 环境设计、里程碑治理与 Skill 路由规范已完成
- M0-R2E 公共入口文件收尾规则补强已完成
- M0-R3A Frappe / Docker 最小环境落地已开始，配置已准备；本轮已获授权执行 Docker 验证，但镜像拉取在 Docker Hub token 获取处失败，容器未启动，Desk 未验证

M0 阶段用于约束后续规划、执行、审查与验收。本轮允许 Frappe / ERPNext / Docker 最小环境启动验证，但仍禁止创建自定义 Frappe App、业务代码、飞书真实写入和前端驾驶舱。

## 仓库定位

当前仓库用于承载 M0 工程启动文档、AI 协作规则、里程碑状态、阅读指南、计划文档、架构决策记录和最小 Docker 环境配置。

它不是业务代码仓库，也不是 Frappe App 仓库；当前只包含经 M0-R3A 授权创建的最小 Docker 本地验证配置。

## 主技术栈

- Frappe Framework
- ERPNext
- Frappe HR
- Python
- JavaScript
- MariaDB/MySQL 兼容体系
- Redis
- Docker
- Docker Compose
- Vue/React
- ECharts
- FastAPI

## 长期仓库规划

长期建议按职责拆分仓库，当前仅记录规划，不在未批准轮次创建这些仓库：

- `haibin-hbos-infra`：基础设施、部署、环境编排与运维脚本
- `hb_core_app`：海滨核心主数据、权限、组织与平台扩展
- `hb_attendance_app`：考勤业务扩展
- `hb_feishu_app`：飞书集成扩展
- `hb_production_app`：生产运营扩展
- `hb_quality_app`：质量管理扩展
- `hb_safety_app`：安全管理扩展
- `hb_ai_ops_app`：AI 运营、视频、算法服务对接扩展
- `hbos-dashboard-web`：Vue/React 驾驶舱与大屏前端

## 当前禁止事项

M0 阶段明确禁止：

- 不创建自定义 Frappe App
- 不创建 `hb_core_app`、`hb_attendance_app`、`hb_feishu_app`
- 不提交真实 `.env` 或真实密钥
- 不开发业务
- 不接飞书真实写入
- 不做前端驾驶舱
- 不浏览或搬运大量 Obsidian 长文

## AI 协作方式

- ChatGPT：负责规划、拆解、上下文整理与方案边界确认
- Claude：负责按计划执行文档或代码变更
- Codex：负责工程审查、边界检查、验证与交付复核
- 用户：负责最终验收、取舍确认与里程碑放行

每轮任务开始前，AI 必须说明本轮读取了哪些文档。默认只读 `CLAUDE.md`、`AGENTS.md`、`docs/AI_CONTEXT.md`、`docs/PROJECT_STATUS.md`、`docs/CURRENT_MILESTONE.md`，禁止默认递归读取整个 `docs/`。
