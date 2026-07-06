# Reading Guide

本指南用于限制 AI 在新乡海滨智能运营管理平台中的默认阅读范围，避免上下文膨胀和误读旧资料。

## 默认读取文件

每轮任务默认只读：

- `CLAUDE.md`
- `AGENTS.md`
- `docs/AI_CONTEXT.md`
- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`

每轮任务开始前必须说明读取了哪些文档。

## 禁止默认递归读取

禁止默认递归读取整个 `docs/`。

默认不读取以下目录：

- `docs/archive`
- `docs/research`
- `docs/legacy`

除非用户明确要求，否则不要浏览或搬运大量 Obsidian 长文。

## 条件读取规则

只有任务明确涉及当前里程碑时，才读取：

- `docs/plans/m0_engineering_bootstrap.md`

## 里程碑文件读取规则

- 默认不全量读取 `docs/milestones/`。
- 当前里程碑任务可读取对应文件，例如 M0 任务读取 `docs/milestones/M0.md`。
- `docs/milestones/README.md` 可作为里程碑索引读取。
- 每轮任务收尾时，如项目状态、当前轮次或里程碑状态发生变化，必须同步更新对应里程碑文件。

当前 M0-R2 任务允许读取：

- `docs/plans/M0-R2_Frappe_Docker最小环境方案设计.md`
- `docs/deployment/Frappe_Docker最小部署设计.md`
- `docs/deployment/本地开发环境变量说明.md`

## Skill 路由读取规则

- `docs/AI技能路由规范.md` 仅在涉及 Skill、Agent 调度、飞书 skill 选择或相关审查时读取。
- 不因存在 Skill 路由文档而默认全量读取 `docs/`。
- 不因存在飞书 skill 而默认执行飞书真实写入。

只有架构决策变更时，才读取：

- `docs/adr/`

## 当前里程碑提醒

当前 M0-R2C/R2D 只做状态收口、Skill 路由文档纳入、中文提交与文档命名规范固化、Git 提交，不做功能开发。

不得安装、运行或生成 Frappe/ERPNext；不得创建海滨 Frappe App；不得写 Docker Compose；不得创建 `.env`；不得创建 `.gitignore`；不得启动容器；不得开发业务代码。M0-R3 才允许在用户明确批准后进入实际最小环境落地。
