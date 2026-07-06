# AI 技能路由规范

本文定义"新乡海滨智能运营管理平台"在开发、审查、前端设计、飞书集成、文档维护等场景下，AI Agent 应如何选择和使用 skill。

适用对象：

- Claude
- Codex
- Cursor
- GPT
- 其他参与本项目开发、审查、设计和文档维护的 AI Agent

## 1. 总原则

1. 任何任务开始前，必须先遵守 `CLAUDE.md`、`AGENTS.md`、`docs/AI_CONTEXT.md`、`docs/PROJECT_STATUS.md`、`docs/CURRENT_MILESTONE.md` 的上下文边界。
2. 不允许为了调用 skill 而扩大任务范围。
3. 不允许默认递归扫描整个 `docs/` 目录。
4. 不允许默认读取 `docs/archive/`、`docs/research/`、`docs/legacy/` 等历史资料目录。
5. skill 生成的设计、代码、文档只能作为初稿，最终必须经过业务、架构、代码、权限和安全审查。
6. 如果当前环境没有某个指定 skill，Agent 必须说明该 skill 不可用，并按本项目规则进行等价人工执行，不得虚构能力。
7. 如果 skill 名称尚未确定，必须保留 `【待确认：...】` 占位，不得自行改名。
8. 当前项目默认只信任用户已确认拥有 / 可用的 skill：`superpowers`、`frontend-design`、`lark-cli`（飞书官方 CLI 工具）+ `lark-*` 官方领域 skills。

## 2. 已安装 Skill 使用矩阵

### 2.1 通用开发 Skill

| 任务类型 | 当前使用 skill | 适用场景 | 输出要求 |
|---|---|---|---|
| 全部代码开发 | `superpowers` | 任意代码实现、修复、重构、测试、工程规范 | 最小 diff；只改本轮范围；遵守仓库入口文档 |
| 代码质量与工程规范 | `superpowers` | 代码结构、命名、异常处理、测试补齐、可维护性检查 | 输出具体问题和最小修正建议 |
| Frappe / ERPNext 开发 | `superpowers` | DocType、Workspace、Report、权限、表单、后台页面、自定义 App | 优先复用 Frappe 标准能力；不得修改核心源码 |
| 数据模型设计 | `superpowers` | DocType、业务字段、主数据、模块数据边界 | 明确数据归属；禁止跨模块直连数据库 |
| API / 集成开发 | `superpowers` | 外部接口、Webhook、事件、幂等、重试、同步日志 | 明确接口契约、幂等键、失败记录和权限边界 |
| Docker / 部署 / 环境 | `superpowers` | Docker Compose、环境变量、启动脚本、部署说明 | 不泄露密钥；不破坏现有环境；保持可回滚 |
| 安全与权限审查 | `superpowers` | 登录、权限、数据隔离、密钥、审计、生产配置 | 不泄露密钥；不绕过权限；不弱化审计 |
| 前端页面设计 | `frontend-design` + `superpowers` | 平台首页、驾驶舱、看板、排班日历、视频审核页、复杂交互页 | 先给信息架构、页面布局、组件拆分，再进入代码 |
| 前端代码实现 | `superpowers` + 必要时 `frontend-design` | Vue / React / TypeScript / 组件实现 / 页面联调 | 设计由 `frontend-design` 辅助；代码实现仍遵守 `superpowers` |
| 文档维护 | 无专用 skill，按项目文档规则执行 | README、ADR、计划、验收、交接、状态文档 | 更新当前必要文档；避免长篇历史散文 |
| 代码审查 | 无专用 skill，交由 Codex 独立审查 | Claude 完成开发后，由 Codex 或审查 Agent 独立审查 | 输出 PASS / FAIL；FAIL 必须列 blocker 和最小修正建议 |

### 2.2 飞书 / Lark Skill 说明

飞书官方 CLI 工具：

- `lark-cli`：飞书官方 CLI 工具（`https://github.com/larksuite/cli`），不是统一总 skill。它提供命令行入口，底层由 `lark-*` 领域 skills 承载具体能力。

飞书官方共享基础 skill：

- `lark-shared`：飞书官方共享基础 skill，负责应用配置、认证登录、身份切换、权限管理、安全规则。由其他 `lark-*` skill 自动加载，无需手动调用。

所有飞书 skill 均来自飞书官方仓库：`https://github.com/larksuite/cli/tree/main/skills`。

### 2.3 HBOS 第一阶段常用飞书 Skills

| skill | 用途 | HBOS 第一阶段场景 |
|---|---|---|
| `lark-shared` | 应用配置、认证登录、身份切换、权限管理 | 所有飞书操作的共享基础，自动加载 |
| `lark-im` | 即时通讯、消息收发、群聊管理、交互卡片 | 考勤异常通知、审批提醒、消息推送 |
| `lark-base` | 多维表格（Base）操作 | 考勤数据台账、排班表、异常记录 |
| `lark-doc` | 飞书云文档读写 | 考勤制度文档、操作手册 |
| `lark-sheets` | 电子表格操作 | 考勤导入导出、排班表 |
| `lark-contact` | 通讯录查询 | 员工信息查询、部门组织架构 |
| `lark-task` | 任务管理 | 考勤异常待办、审批跟进任务 |
| `lark-approval` | 审批管理 | 考勤补卡审批、请假审批 |
| `lark-attendance` | 考勤打卡记录查询 | 考勤数据核对 |
| `lark-openapi-explorer` | 飞书原生 OpenAPI 探索 | 未封装为 skill 的飞书 API 能力发现 |

### 2.4 已安装但按需使用的飞书 Skills

以下飞书 skill 已安装但非 HBOS 第一阶段高频场景，按需使用：

| skill | 用途 | 启用条件 |
|---|---|---|
| `lark-calendar` | 日历与日程管理 | 排班日历、会议安排 |
| `lark-drive` | 云空间文件管理 | 文件上传下载、云盘操作 |
| `lark-markdown` | Markdown 文件管理 | Markdown 文档创建与编辑 |
| `lark-slides` | 幻灯片操作 | 汇报材料生成 |
| `lark-mail` | 邮件操作 | 邮件通知 |
| `lark-wiki` | 知识库管理 | 知识库文档组织 |
| `lark-event` | 实时事件订阅 | 事件驱动自动化 |
| `lark-vc` | 视频会议记录查询 | 会议纪要提取 |
| `lark-vc-agent` | 视频会议会中能力 | 会议实时参与 |
| `lark-minutes` | 妙记（会议纪要） | 会议录音转文字 |
| `lark-whiteboard` | 画板操作 | 架构图、流程图编辑 |
| `lark-skill-maker` | 自定义 Skill 创建 | 封装项目专属飞书操作 |
| `lark-workflow-meeting-summary` | 会议纪要整理工作流 | 周期性会议总结 |
| `lark-workflow-standup-report` | 日程待办摘要 | 每日站会报告 |
| `lark-okr` | OKR 管理 | 目标与关键结果 |
| `lark-apps` | 妙搭应用开发与托管 | 应用创建与部署 |
| `lark-note` | 会议纪要直查 | 已知 note_id 的纪要查询 |

### 2.5 飞书集成安全规则

1. 未经用户明确授权，不允许执行飞书真实写入。
2. 飞书真实写入包括但不限于：发群消息、写多维表格、创建任务、提交审批、修改通讯录、创建日程、写文档、发送邮件、编辑知识库。
3. 仅允许在用户明确授权时执行真实写入。
4. 通讯录读取、审批查询等只读操作默认允许，但不得大规模导出或滥用。
5. 敏感操作前默认先 dry-run 或只读验证。
6. 不得因为安装了飞书 skill 就自动执行真实写入。
7. 飞书集成优先通过飞书集成模块（`hb_feishu_app`）统一管理，不得分散写入各业务模块。
8. 飞书 skill 调用应遵循最小权限原则，仅使用当前任务必需的 skill。

## 3. 候选 Skill 池（未安装，不得直接调用）

以下 skill 只是后续可评估对象。除非用户明确说明已经安装，否则 Agent 不得假装可用，也不得把它们写入"当前使用 skill"。

| 候选 skill | 可能用途 | 启用条件 |
|---|---|---|
| `webapp-testing` | 独立 Vue / React 前端页面测试、交互回归测试 | 后续建设 `hbos-dashboard-web` 或复杂前端页面时再评估 |
| `skill-creator` | 创建海滨项目内部专属 skill | 当项目规范稳定、需要沉淀内部 skill 时再评估 |
| `mcp-builder` | 构建 MCP 工具或服务接口 | 当 HBOS 需要对外暴露 AI 工具接口时再评估 |
| `docx` | Word 文档生成或编辑 | 当项目需要大量生成验收报告、制度文件、交接文档时再评估 |
| `xlsx` | Excel / 表格文件生成或分析 | 当项目需要大量导出、清洗、生成 Excel 台账时再评估 |
| `pdf` | PDF 读取、表单提取、报告处理 | 当项目需要处理 PDF 表单、报告、验证材料时再评估 |
| `pptx` | PPT / 汇报材料生成 | 当项目需要自动生成领导汇报材料时再评估 |
| `brand-guidelines` | 品牌风格规范 | 当 HBOS 形成正式视觉规范后再评估 |
| `theme-factory` | 主题、色彩、暗色模式、CSS 变量 | 当统一前端主题体系启动后再评估 |
| `web-artifacts-builder` | 临时 HTML 原型、可视化 Demo | 当需要快速做非生产级交互原型时再评估 |

## 4. 禁止规则

1. 未安装的 skill 只能列为候选，不得直接调用。
2. 不得自行编造 skill 名称。
3. 不得因为缺少某个 skill 而改变项目架构。
4. 不得为了使用 skill 扩大任务范围。
5. 第三方 skill 必须先由用户确认来源、用途和权限风险后才能安装。
6. 带 Bash、网络访问、文件写入、密钥读取、飞书写入能力的 skill 必须格外谨慎。
7. 飞书真实写入必须得到用户明确授权，范围包括但不限于发群消息、写多维表格、创建任务、提交审批、修改通讯录、创建日程、写文档、发送邮件、编辑知识库。
8. 当前项目默认只信任用户已确认拥有 / 可用的 skill：`superpowers`、`frontend-design`、`lark-cli`（飞书官方 CLI 工具）+ `lark-*` 官方领域 skills。

## 5. 前端 Skill 特殊规则

1. Frappe Desk 用于稳定后台、表单、台账、流程、权限、报表和配置。
2. Vue / React 用于平台首页、驾驶舱、AI 看板、生产看板、考勤排班日历、视频审核中心等高视觉、高交互页面。
3. `frontend-design` 只负责页面设计、组件拆分、交互建议和代码初稿。
4. 前端 skill 不得决定数据模型、权限边界、后端架构、数据库结构和部署方案。
5. 独立前端不得自行维护用户体系。
6. 独立前端不得绕过 Frappe 权限。
7. 独立前端不得直接访问数据库。
8. 独立前端必须通过受控 API 获取数据。

## 6. Frappe / ERPNext 开发特殊规则

1. 不修改 Frappe / ERPNext 核心源码。
2. 业务扩展必须通过自定义 App、DocType、Workspace、Custom Page、Report、Hook、API 等方式实现。
3. 标准后台能力优先复用 Frappe，不为了"好看"重复造后台。
4. 涉及权限、审计、流程、台账的功能，优先放入 Frappe 自定义 App。
5. AI、视频、复杂算法、高频推理、大模型网关等能力不强行塞进 Frappe，应作为独立服务接入。

## 7. 第一阶段限制

第一阶段仅服务 M0 / M1 工程启动和考勤闭环。

允许范围：

- Frappe / ERPNext / Frappe HR 基础环境
- Docker Compose
- MariaDB
- `hb_core_app`
- `hb_attendance_app`
- `hb_feishu_app`
- 基础用户、组织、角色、权限
- 考勤数据导入、排班、异常判断、结果汇总
- 飞书通知或待办提醒
- 必要的 AI 协作规则和工程文档

禁止范围：

- 完整 MES
- 完整 LIMS
- 完整 QMS
- 完整 EHS
- 复杂驾驶舱
- 复杂 AI Agent
- 视频合规深度集成
- Kubernetes
- 高可用集群
- 多数据库拆分
- 大规模前端微应用体系

## 8. Agent 执行要求

每轮任务开始时，Agent 应说明：

1. 本轮读取了哪些入口文档。
2. 本轮任务类型是什么。
3. 本轮应使用哪些 skill。
4. 哪些 skill 名称仍为 `【待确认：...】`。
5. 本轮明确不做什么。

每轮任务结束时，Agent 应说明：

1. 修改了哪些文件。
2. 是否新增或调整了 skill 路由规则。
3. 是否存在未确认的 skill 名称占位。
4. 是否保持最小 diff。
5. 是否有后续需要用户补充确认的 skill 名称。
