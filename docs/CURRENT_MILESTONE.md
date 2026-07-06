# Current Milestone

## M0：工程启动与上下文治理

项目名称：新乡海滨智能运营管理平台。

## 当前轮次

M0-R2C/R2D：状态收口与提交。

权威计划文件：

- `docs/plans/M0-R2_Frappe_Docker最小环境方案设计.md`

权威状态文件：

- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/milestones/M0.md`

## 本轮范围

只做 M0-R2 批次状态收口、AI Skill 路由文档纳入、中文提交与文档命名规范固化，并创建一次 Git 提交。

交付内容：

- `docs/AI技能路由规范.md`
- `CLAUDE.md` 中的 Skill 使用规则
- `AGENTS.md` 中的 Agent Skill Routing 规则
- `docs/AI_CONTEXT.md` 中的 Skill 路由说明
- `docs/READING_GUIDE.md` 中的 Skill 路由条件读取规则
- 中文提交与新增文档中文命名优先规则
- 项目状态、当前里程碑和 M0 里程碑文件更新

## 本轮禁止事项

- 不安装、不运行、不生成 Frappe/ERPNext
- 不创建 Frappe bench
- 不创建 `hb_core_app`、`hb_attendance_app`、`hb_feishu_app`
- 不写 Docker Compose
- 不创建 `.env`
- 不创建 `.gitignore`
- 不启动容器
- 不做业务代码
- 不开发考勤业务
- 不接飞书
- 不接飞书真实写入
- 不做前端驾驶舱
- 不引入外部源码
- 不 push

## 当前批次状态

- M0-R2 设计文档已完成，Codex 审查为 PASS_WITH_WARNINGS，尚未提交。
- M0-R2A 默认入口文档过期描述修复已完成。
- M0-R2B 里程碑状态管理规范已完成。
- M0-R2C AI Skill 路由文档纳入已完成。
- M0-R2D 中文提交与文档命名规范已完成。
- M0-R2、M0-R2A、M0-R2B、M0-R2C、M0-R2D 将一起收口提交。
- M0-R3 仍未开始。

## 验收标准

- `docs/AI技能路由规范.md` 存在
- `docs/AI技能路由规范.md` 区分已确认可用 skill 与候选 skill
- `CLAUDE.md` 和 `AGENTS.md` 引用 `docs/AI技能路由规范.md`
- `docs/AI_CONTEXT.md` 补充 Skill 路由说明
- `docs/READING_GUIDE.md` 将 `docs/AI技能路由规范.md` 设为条件读取
- `CLAUDE.md` 和 `AGENTS.md` 固化中文提交与新增文档中文命名优先规则
- 新增文档已尽量使用中文或中英混合文件名
- 未出现 skill 安装、飞书真实写入、Frappe 安装、App 创建、Docker Compose、`.env`、`.gitignore`、容器启动或业务代码

## 下一轮预告

下一轮指向 M0-R3：Frappe / Docker 最小环境落地准备。M0-R3 尚未开始，必须等待用户明确批准后再执行。
