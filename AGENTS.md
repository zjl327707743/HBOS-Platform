# AGENTS.md

本文件约束所有 AI Agent 在新乡海滨智能运营管理平台中的默认行为。

## 项目事实

项目名称：新乡海滨智能运营管理平台。

准确叫法：Frappe/ERPNext 开源底座 + Frappe 多 App 模块化架构 + 外部独立服务扩展。

目标架构：Frappe/ERPNext 开源底座 + 海滨自定义 Frappe App + 外部 AI/视频/算法服务 + Vue/React 驾驶舱 + 飞书集成 + Docker 部署。

主技术栈：Frappe Framework、ERPNext、Frappe HR、Python、JavaScript、MariaDB/MySQL 兼容体系、Redis、Docker、Docker Compose、Vue/React、ECharts、FastAPI。

## M0-R1 范围

M0 第一轮只创建项目工程骨架和 AI 上下文管理文档。

不得执行：

- 安装 Frappe、ERPNext、Frappe HR
- 创建 Frappe bench
- 创建任何 Frappe App
- 创建 `hb_core_app`、`hb_attendance_app`、`hb_feishu_app`
- 编写 `docker-compose.yml`
- 开发考勤业务
- 接入飞书
- 实现 Vue/React 驾驶舱
- 浏览或搬运大量 Obsidian 长文

## 默认读取规则

每轮任务默认只读：

- `CLAUDE.md`
- `AGENTS.md`
- `docs/AI_CONTEXT.md`
- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`

禁止默认递归读取整个 `docs/`。

默认不读：

- `docs/archive`
- `docs/research`
- `docs/legacy`

每轮任务开始前必须说明读取了哪些文档。

只有任务明确涉及当前里程碑时，才读取 `docs/plans/m0_engineering_bootstrap.md`。

只有架构决策变更时，才读取 `docs/adr/`。

## 协作分工

- ChatGPT：规划与上下文管理
- Claude：执行文档或代码变更
- Codex：工程审查与验收复核
- 用户：最终验收与里程碑放行

Agent 必须以用户当前指令为准。若用户只要求审查，则只审查不修改；若用户要求执行，则仅在当前范围内执行。
