# M0 Engineering Bootstrap Plan

项目名称：新乡海滨智能运营管理平台。

## M0 总目标

M0 的目标是完成工程启动、上下文治理、架构边界确认和后续实施前的准备工作，为 Frappe/ERPNext 开源底座、海滨自定义 Frappe App、外部 AI/视频/算法服务、Vue/React 驾驶舱、飞书集成和 Docker 部署建立清晰的协作基础。

准确叫法：Frappe/ERPNext 开源底座 + Frappe 多 App 模块化架构 + 外部独立服务扩展。

## M0 第一轮范围

本轮只创建项目工程骨架和 AI 上下文管理文档。

本轮不安装、不运行、不生成 Frappe/ERPNext，不创建任何 Frappe App，不写 Docker Compose，不做业务代码。

## 本轮交付物清单

- `README.md`
- `CLAUDE.md`
- `AGENTS.md`
- `docs/AI_CONTEXT.md`
- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/READING_GUIDE.md`
- `docs/plans/m0_engineering_bootstrap.md`
- `docs/adr/0001-use-frappe-erpnext-as-platform-base.md`
- `docs/adr/0002-use-mariadb-compatible-database.md`
- `docs/adr/0003-use-dual-layer-frontend.md`
- `docs/adr/0004-open-source-reuse-and-frappe-hr-attendance-first.md`

## 明确不做事项

- 不安装 Frappe、ERPNext 或 Frappe HR
- 不创建 Frappe bench
- 不创建 `hb_core_app`
- 不创建 `hb_attendance_app`
- 不创建 `hb_feishu_app`
- 不写 `docker-compose.yml`
- 不开发考勤业务
- 不接飞书
- 不做前端驾驶舱
- 不浏览或搬运大量 Obsidian 长文

## 验收标准

- 所有本轮交付物文件均已创建
- 文档明确项目名称：新乡海滨智能运营管理平台
- 文档明确准确架构叫法：Frappe/ERPNext 开源底座 + Frappe 多 App 模块化架构 + 外部独立服务扩展
- 文档明确主技术栈：Frappe Framework、ERPNext、Frappe HR、Python、JavaScript、MariaDB/MySQL 兼容体系、Redis、Docker、Docker Compose、Vue/React、ECharts、FastAPI
- `CLAUDE.md`、`AGENTS.md`、`docs/AI_CONTEXT.md`、`docs/READING_GUIDE.md` 均写入 AI 上下文读取规则
- 未安装、运行或生成 Frappe/ERPNext
- 未创建 Frappe App
- 未创建 Docker Compose
- 未写业务代码

## M0-R2 预告

下一轮 M0-R2 再规划 Frappe/Docker 环境，包括环境方案、仓库拆分策略、部署边界和后续执行步骤。

M0-R2 不在本轮实现。本轮只为 M0-R2 留出规划入口。
