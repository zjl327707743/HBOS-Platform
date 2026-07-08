# AGENTS.md

本文件约束所有 AI Agent 在新乡海滨智能运营管理平台中的默认行为。

## 项目事实

项目名称：新乡海滨智能运营管理平台。

准确叫法：Frappe/ERPNext 开源底座 + Frappe 多 App 模块化架构 + 外部独立服务扩展。

目标架构：Frappe/ERPNext 开源底座 + 海滨自定义 Frappe App + 外部 AI/视频/算法服务 + Vue/React 驾驶舱 + 飞书集成 + Docker 部署。

主技术栈：Frappe Framework、ERPNext、Frappe HR、Python、JavaScript、MariaDB/MySQL 兼容体系、Redis、Docker、Docker Compose、Vue/React、ECharts、FastAPI。

## 协作规则与进度来源

`CLAUDE.md` 和 `AGENTS.md` 是协作规则文件，不承载具体项目进度。

`README.md` 是人类入口文件，不能保留过期阶段描述。

当前项目进度以以下文件为准：

- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/milestones/`

所有 Agent 必须以用户当前指令和上述进度文件为准。

## 当前里程碑边界

每轮任务必须按当前里程碑工作，不得擅自扩大范围或提前进入下一里程碑。

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

## 状态更新规则

- 如本轮改变项目状态，必须更新 `docs/PROJECT_STATUS.md`。
- 如本轮改变当前里程碑或轮次，必须更新 `docs/CURRENT_MILESTONE.md`。
- 如本轮属于某个里程碑，必须更新 `docs/milestones/M0.md` 或对应里程碑文件。
- 每轮收尾必须检查公共入口文件是否存在过期阶段描述：`README.md`、`CLAUDE.md`、`AGENTS.md`、`docs/AI_CONTEXT.md`、`docs/READING_GUIDE.md`。
- 每轮收尾必须检查当前阶段门禁文档：M1 阶段为 `docs/milestones/M1_START_GATE.md`，未来 M2/M3 阶段分别为 `docs/milestones/M2_START_GATE.md`、`docs/milestones/M3_START_GATE.md`。阶段门禁文档用于记录当前阶段的目标、边界、门禁、子轮次状态和下一步路线。
- 每轮进入 REVIEWING 或 closeout 时，必须同步更新当前轮次主文档（指本轮实际交付的 `docs/milestones/Mx_Ry_*.md` 文档，例如 `docs/milestones/M1_R3F_业务口径确认包.md`）的状态。
- 每轮输出结果时，必须说明状态文件是否已更新；如未更新，必须说明原因。

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

当前里程碑任务可读取对应的 `docs/milestones/` 文件；例如 M0 任务可读取 `docs/milestones/M0.md`。不得默认全量读取 `docs/milestones/`。

只有任务涉及 Skill、Agent 调度或飞书 skill 选择时，才读取 `docs/AI技能路由规范.md`。

只有架构决策变更时，才读取 `docs/adr/`。

## Agent Skill Routing

所有 Agent 必须遵守：

- `docs/AI技能路由规范.md`

当前仅允许使用用户已确认拥有 / 可用的 skill：

- `superpowers`：全部代码开发、修复、重构、测试、工程规范
- `frontend-design`：前端页面设计、UI、组件、驾驶舱、看板、复杂交互
- `lark-cli`：飞书官方 CLI 工具（`https://github.com/larksuite/cli`），不是统一总 skill
- `lark-shared`：飞书官方共享基础 skill（认证登录、身份切换、权限管理）
- `lark-*`：飞书官方领域 skills（如 `lark-im`、`lark-base`、`lark-doc`、`lark-contact`、`lark-task`、`lark-approval` 等），完整清单见 `docs/AI技能路由规范.md`

候选 skill 不等于已安装 skill。

如果当前环境没有指定 skill，Agent 必须：

1. 明确说明该 skill 不可用。
2. 按项目规则进行等价人工执行。
3. 不得虚构 skill 能力。
4. 不得因为 skill 缺失而改变架构路线。
5. 不得自行替换未确认的 skill 名称。
6. 不得将 `lark-cli` 当作统一总 skill。
7. 未经用户明确授权，不得执行飞书真实写入。飞书真实写入包括但不限于：群消息发送、多维表格写入、通讯录修改、审批操作、邮件发送、云文档编辑、任务创建/修改。

## 提交与文档命名规范

- Git commit message 以后优先使用中文描述。
- 可以保留 conventional commit 前缀，如 `docs`、`fix`、`feat`、`chore`，但冒号后的描述必须使用中文。
- 示例：`docs: 完成 M0-R2 环境设计、里程碑治理与 Skill 路由规范`
- 新增文档文件名优先使用中文或中英混合命名。
- 技术专有名词可保留英文，例如 Frappe、Docker、ERPNext、FastAPI、API、Skill。
- 根目录约定文件可以保留英文，例如 `README.md`、`CLAUDE.md`、`AGENTS.md`。
- 已提交历史文件不为追求中文而随意重命名，除非用户明确要求。

Codex 审查时必须检查：

- 新增文档是否优先中文或中英混合命名。
- commit message 是否使用中文描述。
- 如果使用英文文件名，是否有兼容性、生态约定或根目录约定理由。
- 状态台账是否同步，包括 `docs/PROJECT_STATUS.md`、`docs/CURRENT_MILESTONE.md` 和对应 `docs/milestones/` 文件。
- 公共入口文件是否存在过期阶段描述。
- 当前阶段门禁文档是否同步：M1 阶段为 `docs/milestones/M1_START_GATE.md`，未来 M2/M3 阶段对应为 `M2_START_GATE.md`、`M3_START_GATE.md`。
- 当前轮次主文档（`docs/milestones/Mx_Ry_*.md`）状态是否与本轮交付一致。
- 若 `README.md`、`CLAUDE.md`、`AGENTS.md`、`docs/AI_CONTEXT.md`、`docs/READING_GUIDE.md` 中存在过期阶段描述，应按影响标记 WARN 或 FAIL。

## 协作分工

- ChatGPT：规划与上下文管理
- Claude：执行文档或代码变更
- Codex：工程审查与验收复核
- 用户：最终验收与里程碑放行

Agent 必须以用户当前指令为准。若用户只要求审查，则只审查不修改；若用户要求执行，则仅在当前范围内执行。
