# AI Context

项目名称：新乡海滨智能运营管理平台。

## 架构定案

准确叫法：Frappe/ERPNext 开源底座 + Frappe 多 App 模块化架构 + 外部独立服务扩展。

长期架构包括：

- Frappe/ERPNext 开源底座
- 海滨自定义 Frappe App
- 外部 AI/视频/算法服务
- Vue/React 驾驶舱
- 飞书集成
- Docker 部署

主技术栈：Frappe Framework、ERPNext、Frappe HR、Python、JavaScript、MariaDB/MySQL 兼容体系、Redis、Docker、Docker Compose、Vue/React、ECharts、FastAPI。

## 当前上下文

当前阶段：M0 第一轮工程启动。

当前目标：只创建项目工程骨架和 AI 上下文管理文档。

本轮不安装、不运行、不生成 Frappe/ERPNext，不创建海滨 Frappe App，不写 Docker Compose，不开发业务代码。

## AI 默认读取规则

默认只读以下文件：

- `CLAUDE.md`
- `AGENTS.md`
- `docs/AI_CONTEXT.md`
- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`

禁止默认递归读取整个 `docs/`。

默认不读取：

- `docs/archive`
- `docs/research`
- `docs/legacy`

每轮任务开始前，必须说明本轮读取了哪些文档。

只有任务明确涉及当前里程碑时，才读取：

- `docs/plans/m0_engineering_bootstrap.md`

只有架构决策变更时，才读取：

- `docs/adr/`

## 边界提醒

M0 第一轮只建立协作上下文与文档骨架。任何环境安装、容器编排、App 生成、业务模型、飞书对接、前端驾驶舱、AI 视频服务实现，都属于后续轮次。
