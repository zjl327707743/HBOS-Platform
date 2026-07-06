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

## 公共入口文件收尾检查规则

默认读取规则不变。

每轮收尾审查可读取以下公共入口文件：

- `README.md`
- `CLAUDE.md`
- `AGENTS.md`
- `docs/AI_CONTEXT.md`
- `docs/READING_GUIDE.md`

这些文件不一定每轮修改，但必须检查是否存在过期阶段描述。检查公共入口文件不等于允许递归读取整个 `docs/`。

## 条件读取规则

只有任务明确涉及当前里程碑时，才读取：

- `docs/plans/m0_engineering_bootstrap.md`

## 里程碑文件读取规则

- 默认不全量读取 `docs/milestones/`。
- 当前里程碑任务可读取对应文件，例如 M0 任务读取 `docs/milestones/M0.md`。
- `docs/milestones/README.md` 可作为里程碑索引读取。
- 每轮任务收尾时，如项目状态、当前轮次或里程碑状态发生变化，必须同步更新对应里程碑文件。

M0 历史任务曾允许读取：

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

当前 M0 已完成并封板，M0-REMOTE 已完成，M1-R0 已完成并通过 Codex 独立审查，M1-R1 已完成 HRMS 原生考勤对象模型验证记录并收口为 COMPLETED，M1-R2 已形成 HRMS 原生考勤配置试运行方案并进入 REVIEWING。M0-R3A 已完成 Frappe / ERPNext / Docker 最小本地环境落地，M0-R3C 已完成 Frappe HR / HRMS 安装验证，M0-R3C-FIX 已完成 HRMS 前端资源与 Roster 白屏诊断修复，M0-R3D 已完成 HRMS 能力盘点与 M1 考勤一期边界设计，M0-R3E 已完成 HRMS 环境可复现性收口并通过 Codex 审查。

下一步路线只记录，不代表已启动：

1. Codex 审查 M1-R2。
2. 审查通过后再决定是否进入 M1-R3：HRMS 原生考勤最小测试数据试运行。

后续涉及 HRMS 环境治理、前端资源复核、能力盘点或 M1 考勤一期边界时，可读取 M0-R3C 安装验证记录、M0-R3C-FIX 修复记录、M0-R3D 设计记录、M0-R3E 环境可复现性收口记录、官方 Frappe HR、`frappe/hrms`、`frappe/frappe_docker`、ERPNext / Frappe v16 资料。

不得因 HRMS 已安装而创建海滨自定义 Frappe App；不得开发业务代码；不得接飞书真实写入；不得做前端驾驶舱；不得提交真实 `.env` 或真实密钥。
