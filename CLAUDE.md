# CLAUDE.md

本文件是 Claude 在本项目中的默认协作入口。项目名称：新乡海滨智能运营管理平台。

## 项目定案

准确叫法：Frappe/ERPNext 开源底座 + Frappe 多 App 模块化架构 + 外部独立服务扩展。

长期架构：Frappe/ERPNext 开源底座 + 海滨自定义 Frappe App + 外部 AI/视频/算法服务 + Vue/React 驾驶舱 + 飞书集成 + Docker 部署。

主技术栈：Frappe Framework、ERPNext、Frappe HR、Python、JavaScript、MariaDB/MySQL 兼容体系、Redis、Docker、Docker Compose、Vue/React、ECharts、FastAPI。

## M0 第一轮边界

本轮只做文档和目录骨架。

禁止事项：

- 不安装、不运行、不生成 Frappe/ERPNext
- 不创建 `hb_core_app`、`hb_attendance_app`、`hb_feishu_app`
- 不写 Docker Compose
- 不做业务代码
- 不开发考勤业务
- 不接飞书
- 不做前端驾驶舱
- 不浏览或搬运大量 Obsidian 长文

## AI 上下文读取规则

默认只读以下文件：

- `CLAUDE.md`
- `AGENTS.md`
- `docs/AI_CONTEXT.md`
- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`

禁止默认递归读取整个 `docs/`。

以下目录默认不读：

- `docs/archive`
- `docs/research`
- `docs/legacy`

每轮任务开始前必须说明读取了哪些文档。

只有任务明确涉及当前里程碑时，才读取 `docs/plans/m0_engineering_bootstrap.md`。

只有架构决策变更时，才读取 `docs/adr/`。

## 执行原则

严格按当前里程碑工作，不扩大范围，不提前实现下一轮内容。任何安装、运行、生成、业务开发、集成或部署动作，都必须等用户明确批准。
