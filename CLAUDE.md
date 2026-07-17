# CLAUDE.md

本文件是 Claude 在本项目中的默认协作入口。项目名称：新乡海滨智能运营管理平台。

## 项目定案

准确叫法：Frappe/ERPNext 开源底座 + Frappe 多 App 模块化架构 + 外部独立服务扩展。

长期架构：Frappe/ERPNext 开源底座 + 海滨自定义 Frappe App + 外部 AI/视频/算法服务 + Vue/React 驾驶舱 + 飞书集成 + Docker 部署。

主技术栈：Frappe Framework、ERPNext、Frappe HR、Python、JavaScript、MariaDB/MySQL 兼容体系、Redis、Docker、Docker Compose、Vue/React、ECharts、FastAPI。

## 进度来源

`CLAUDE.md` 是 Claude 协作规则入口，不承载具体项目进度。

当前项目进度以以下文件为准：

- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/milestones/`

## 当前里程碑边界

每轮任务必须以用户当前指令和 `docs/CURRENT_MILESTONE.md` 为准。

禁止事项：

- 不安装、不运行、不生成 Frappe/ERPNext
- 未经用户明确授权，不创建 `hb_core_app`、`hb_attendance_app`、`hb_feishu_app`
- 不写 Docker Compose
- 不做业务代码
- 不开发考勤业务
- 不接飞书
- 不做前端驾驶舱
- 不浏览或搬运大量 Obsidian 长文

## 每轮任务收尾强制要求

- 状态台账必须检查：`docs/PROJECT_STATUS.md`、`docs/CURRENT_MILESTONE.md`、`docs/milestones/` 中的对应里程碑文件。
- 公共入口文件必须检查：`README.md`、`CLAUDE.md`、`AGENTS.md`、`docs/AI_CONTEXT.md`、`docs/READING_GUIDE.md`。
- 当前阶段门禁文档必须检查：M1 阶段为 `docs/milestones/M1_START_GATE.md`，未来 M2/M3 阶段分别为 `docs/milestones/M2_START_GATE.md`、`docs/milestones/M3_START_GATE.md`。
- 当前轮次主文档必须检查：指本轮实际交付的 `docs/milestones/Mx_Ry_*.md` 文档，例如 `docs/milestones/M1_R3F_业务口径确认包.md`。
- 如本轮改变项目状态，必须更新 `docs/PROJECT_STATUS.md`。
- 如本轮改变当前里程碑或轮次，必须更新 `docs/CURRENT_MILESTONE.md`。
- 如本轮属于某个里程碑，必须更新 `docs/milestones/M0.md` 或对应里程碑文件。
- 每轮进入 REVIEWING 或 closeout 时，必须同步更新当前轮次主文档状态。
- 公共入口文件不一定每轮修改，但必须检查是否存在过期阶段描述。
- 禁止只更新状态台账而忽略 `README.md` 等人类入口文件。
- 输出结果时必须说明状态台账是否已更新；如未更新，必须说明原因。
- 输出结果时必须说明公共入口文件是否已检查、哪些入口文件需要更新、哪些入口文件无需更新及原因。

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

当前里程碑任务可读取对应的 `docs/milestones/` 文件；例如 M0 任务可读取 `docs/milestones/M0.md`。不得默认全量读取 `docs/milestones/`。

只有任务涉及 Skill、Agent 调度或飞书 skill 选择时，才读取 `docs/AI技能路由规范.md`。

只有架构决策变更时，才读取 `docs/adr/`。

## Skill 使用规则

涉及 Skill、Agent 调度或飞书 skill 选择的任务，必须读取：

- `docs/AI技能路由规范.md`

当前已确认可用 skill：

- `superpowers`：全部代码开发、修复、重构、测试、工程规范
- `frontend-design`：前端页面设计、UI、组件、驾驶舱、看板、复杂交互
- `lark-cli`：飞书官方 CLI 工具（`https://github.com/larksuite/cli`），不是统一总 skill
- `lark-shared`：飞书官方共享基础 skill（认证登录、身份切换、权限管理）
- `lark-*`：飞书官方领域 skills（如 `lark-im`、`lark-base`、`lark-doc`、`lark-contact`、`lark-task`、`lark-approval` 等），详见 `docs/AI技能路由规范.md`

未安装 skill 只能作为候选，不得直接调用。

禁止：

- 默认递归读取整个 `docs/`
- 因 skill 输出扩大任务范围
- 未经审查直接采纳 skill 生成的代码或设计
- 自行编造未确认的 skill 名称
- 假装已安装候选 skill
- 将 `lark-cli` 当作统一总 skill
- 未经用户明确授权执行飞书真实写入

## 提交与文档命名规范

- Git commit message 以后优先使用中文描述。
- 可以保留 conventional commit 前缀，如 `docs`、`fix`、`feat`、`chore`，但冒号后的描述必须使用中文。
- 示例：`docs: 完成 M0-R2 环境设计、里程碑治理与 Skill 路由规范`
- 新增文档文件名优先使用中文或中英混合命名。
- 技术专有名词可保留英文，例如 Frappe、Docker、ERPNext、FastAPI、API、Skill。
- 根目录约定文件可以保留英文，例如 `README.md`、`CLAUDE.md`、`AGENTS.md`。
- 已提交历史文件不为追求中文而随意重命名，除非用户明确要求。

## 执行原则

严格按当前里程碑工作，不扩大范围，不提前实现下一轮内容。任何安装、运行、生成、业务开发、集成或部署动作，都必须等用户明确批准。

**独立前端开发规则**：凡涉及独立前端、漂亮页面、驾驶舱、AI 工作台、复杂交互页面，必须先完成原型设计/视觉方案，经 Owner 人工审查通过后再进行前端复刻开发，最后接入真实页面功能和数据。详见 `docs/frontend/FRONTEND_IMPLEMENTATION_GUIDE.md`。
