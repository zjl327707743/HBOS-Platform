# HBOS LIMS Vue 前端开发流程与原型设计

项目名称：新乡海滨智能运营管理平台。

适用对象：Owner、Claude、Codex、ChatGPT 及参与 HBOS LIMS 独立前端设计、开发与审查的 AI Agent。

## 1. 定位与边界

HBOS LIMS 当前已由 `hb_lims_app` 承载 Frappe Desk 后台闭环（样品登记、检验流程、自动判定、COA 发布、审计追踪），本文件面向后续独立 Vue 前端的**原型设计与开发流程**。

独立前端的定位：

- 面向实验室高频操作、检验任务看板、结果录入、COA 报告与合规审计的体验层。
- 不替换 Frappe Desk 后台，不绕过 Frappe 权限，不直接访问数据库。
- 必须通过 `hb_lims_app` 已提供的 whitelist 方法与受控 API 获取、提交数据。
- 本轮只交付原型与开发流程，不进入前端复刻；未经 Owner 审查通过，不得创建 Vue 工程。

本轮前置约束（与 `docs/milestones/M2_START_GATE.md`、`docs/frontend/FRONTEND_IMPLEMENTATION_GUIDE.md` 对齐）：

- M2-LIMS MVP 仍在 REVIEWING，本原型不阻塞 M2-R5 验证收口。
- 原型演示数据一律使用 `TEST-HBOS-M2-*` 前缀，不录入真实样品、人员与检测数据。
- 不创建 `hb_core_app`、`hb_feishu_app`，不修改 Frappe / ERPNext / HRMS 核心源码。
- 不新增后端 DocType 或业务方法；如发现 API 缺口，记录到问题清单，待 Owner 授权后另行处理。

## 2. 开发流程（强制 Gate）

```text
原型/视觉方案 → Owner 审查 →（通过）→ 工程初始化 → 页面复刻 →（完成）→ 功能接入 → 联调验收
                    ↓（未通过）
              回到原型阶段修改
```

### 2.1 原型 / 视觉方案阶段（本轮）

交付物：

- 交互式 HTML 原型：`docs/frontend/M2_LIMS_Vue前端原型.html`。
- 页面清单与信息架构（见第 4 节）。
- 视觉方案（见第 5 节）。
- 组件拆分与页面交互说明（见第 6 节）。

原型覆盖 7 个核心视图：

1. 工作台总览（KPI、检验节奏、任务分布、最近样品、合规状态）。
2. 样品登记（规格自动匹配、检验项目快照、优先级与检验时限）。
3. 待检任务看板（待分配 / 已分配 / 检验中 / 已提交 / 已复核 / 已批准）。
4. 检验结果录入（限度冻结快照、公式计算、自动判定预览、电子签名、修订记录）。
5. COA 报告管理（报告列表、PDF 预览、QA 审核、发布）。
6. 质量标准库（版本管理、检验项目、限度、方法 SOP、生效状态）。
7. 审计追踪查询（用户 / 时间 / 模块 / 操作类型筛选，只读）。

### 2.2 Owner 审查阶段

审查重点：

- 信息层级是否符合实验室角色日常操作习惯。
- 任务看板与结果录入是否覆盖真实闭环路径。
- 视觉语言是否体现 GMP 合规与制药实验室的专业感。
- 组件库选型与 Vue 3 技术栈是否一致。
- 原型是否严格对应 `hb_lims_app` 现有数据与权限边界。

审查结论以 Owner 确认为准。未通过时回到 2.1 修改，不得跳过。

### 2.3 工程初始化阶段

在 Owner 审查通过后执行：

- 推荐技术栈：Vue 3 + Vite + TypeScript + Pinia + Vue Router + Element Plus + ECharts。
- 工程位置建议：仓库内新增 `frontend/hbos-lims-web/`，或按长期规划归入 `hbos-dashboard-web`，以 Owner 决策为准。
- 必须接入 Frappe session 登录态；不自行维护用户体系。
- 建立环境变量与 API 网关配置，不提交密钥。

### 2.4 页面复刻阶段

- 严格按已审查原型实现，不擅自调整视觉与交互。
- 建立公共组件：`AppShell`、`SidebarNav`、`TopBar`、`DataTable`、`StatusPill`、`EmptyState`、`ConfirmDialog`、`PageHeader`、`SignatureStrip`、`AuditDiffViewer`。
- 页面组件按第 4 节拆分，保持单向数据流。
- 桌面优先，平板 / 手机断点按第 5 节策略适配。

### 2.5 功能接入阶段

- 对接 `hb_lims_app` 已存在的 whitelist 方法（见第 7 节）。
- 所有写操作必须展示结果确认与失败原因；修订操作必须填写原因并二次确认。
- 空状态、加载状态、错误状态、权限不足状态必须覆盖。
- 审计追踪页面保持只读，禁止在前端本地删除或修改审计记录。

### 2.6 联调与验收阶段

验收清单：

- 角色权限：LIMS Analyst / Reviewer / Manager 三视角可见性与操作可用性正确。
- 业务闭环：登记 → 生成任务 → 分配 → 开始 → 提交（自动判定）→ 复核 → 批准 → COA 创建 / 审核 / 发布。
- 数据完整性：提交后原始数据不可改，修订生成 Revision 且原因必填。
- 报表与导出：COA PDF、样品台账、检验结果清单、审计追踪查询可用。
- 离线单测 + 浏览器回归 + Owner 人工验收。

## 3. 技术选型

| 层 | 选型 | 说明 |
| --- | --- | --- |
| 框架 | Vue 3 + TypeScript | 组件化、类型安全，适配现有 Vue 技术栈 |
| 构建 | Vite | 快速开发与生产构建 |
| 状态 | Pinia | 会话、当前任务、筛选条件、草稿状态 |
| 路由 | Vue Router | 工作台 / 样品 / 任务 / 结果 / COA / 标准 / 审计 |
| UI | Element Plus | 与 `FRONTEND_IMPLEMENTATION_GUIDE.md` 的 Vue 首选一致 |
| 图表 | ECharts | 任务分布、检验节奏、趋势分析 |
| HTTP | Axios | 对接 Frappe REST API |
| 样式 | SCSS + CSS 变量 | 与原型设计 Token 一致 |

不混用多套组件库；不以美观为由绕过 Frappe 权限与 API 边界。

## 4. 页面清单与信息架构

### 4.1 路由结构

```text
/hbos-lims
├── /dashboard             工作台总览
├── /samples               样品登记 / 样品台账
├── /tasks                 待检任务看板
├── /results/:id           检验结果录入
├── /coas                   COA 报告管理
├── /specs                 质量标准库
└── /audit                 审计追踪查询
```

### 4.2 页面职责与关键交互

| 页面 | 数据来源（现有后端对象） | 关键交互 | 权限参考 |
| --- | --- | --- | --- |
| 工作台总览 | HBOS Sample / Sample Task / Test Result / COA | KPI 卡片、任务分布、最近样品、合规状态 | 三个 LIMS 角色可见 |
| 样品登记 | HBOS Specification / Sample(+Item) | 选规格自动带出检验项目快照，登记后锁定 | Analyst 可登记，Manager 可管理 |
| 待检任务看板 | HBOS Sample Task | 看板拖拽 / 状态筛选，超时与 OOS 预警 | Analyst 开始本人任务，Manager 分配 |
| 检验结果录入 | HBOS Test Result / Calculation / Result Revision | 公式计算、自动判定预览、签名、修订原因 | Analyst 提交，Reviewer 复核，Manager 修订 |
| COA 报告管理 | HBOS COA(+Item) / Print Format | 报告预览、QA 审核、发布 PDF | Reviewer 审核，Manager 发布 |
| 质量标准库 | HBOS Specification(+Item) / Test Item / Calculation | 版本对比、生效状态、项目明细 | Manager 维护 |
| 审计追踪查询 | HBOS Result Revision / 审计查询报表 | 多维筛选、只读表格、变更前后对比 | Reviewer / Manager |

## 5. 视觉方案

### 5.1 设计语言

制药实验室风格：洁净、严谨、信息密度适中、状态语义明确。不使用营销式大图、渐变光斑或娱乐化动效。

### 5.2 色彩 Token

| Token | 值 | 用途 |
| --- | --- | --- |
| `--primary` | `#0c7c6a` | 主操作、选中态、品牌色 |
| `--primary-soft` | `#e3f2ee` | 主色浅底、当前选中 |
| `--pass` | `#1d8a5b` | 合格、已批准 |
| `--warn` | `#d1871d` | 即将超时、待复核 |
| `--danger` | `#c24d3f` | OOS、超时、拒绝 |
| `--info` | `#2b6cb0` | 信息、草稿流转 |
| `--ink` | `#162623` | 正文 |
| `--muted` | `#5f726d` | 次级文字 |
| `--line` | `#d8e2dd` | 分隔线 / 描边 |
| `--sidebar` | `#0d2b28` | 深色侧栏 |

### 5.3 字体与间距

- 中文字体：`PingFang SC`、`Noto Sans SC`、`Microsoft YaHei`。
- 编号 / 数据 / 时间：等宽字体（SF Mono / JetBrains Mono）。
- 卡片圆角：`8px`（与项目规范一致，不放大圆角）。
- 间距体系：`4 / 8 / 12 / 14 / 16 / 22px`。
- 表格行高紧凑，状态用 Pill 表达，不依赖纯色块大卡片。

### 5.4 响应式策略

- 桌面（>1180px）：完整侧栏、多列 KPI、6 列看板。
- 平板（640-1180px）：侧栏收窄为图标栏，主内容单列，看板横向滚动。
- 手机（<640px）：顶部操作收拢，KPI 单列，表单单列，COA 预览简化。

## 6. 组件拆分

### 6.1 布局组件

- `AppShell`：侧栏 + 顶栏 + 内容区。
- `SidebarNav`：模块导航、待办角标。
- `TopBar`：面包屑、全局搜索、通知、用户信息。

### 6.2 业务组件

- `SampleRegisterForm`：样品基础信息 + 规格匹配 + 项目快照预览。
- `TaskKanban`：状态列、任务卡片、拖拽流转。
- `ResultEntryPanel`：限度快照、公式输入、判定预览、签名条。
- `RevisionTimeline`：修订记录时间线 / 变更对比。
- `CoaPreview`：COA 文档预览（对齐 Print Format）。
- `SpecVersionPanel`：版本列表 + 检验项目明细。
- `AuditQueryTable`：筛选条件 + 只读审计表。
- `StatusPill`：统一状态语义。
- `SignatureStrip`：检验人 / 复核人 / 批准人三段签名。
- `EmptyState` / `ErrorState` / `LoadingSkeleton`：统一反馈。

## 7. API 契约映射

以下均为 `hb_lims_app.hbos_lims.lims_service` 现有 whitelist 方法，前端不新增后端业务接口：

| 前端动作 | 后端方法 | 说明 |
| --- | --- | --- |
| 登记样品 | `register_sample` | 规格生效校验 + 项目快照 |
| 生成检验任务 | `generate_tasks` | 按待检项目生成任务 |
| 分配任务 | `assign_task` | 待分配 → 已分配 |
| 开始检验 | `start_task` | 自动创建检测记录 |
| 提交结果 | `submit_result` | 公式计算 + 自动判定 + 电子签名 |
| 复核结果 | `review_result` | 已提交 → 已复核 |
| 批准结果 | `approve_result` | 已复核 → 已批准 |
| 修订结果 | `revise_result` | 生成 Revision + 新版本，原因必填 |
| 创建 COA | `create_coa` | 仅检验完成且结果全部批准 |
| 审核 COA | `review_coa` | 草稿 → 已审核 |
| 发布 COA | `publish_coa` | 生成 PDF 附件归档 |
| 样品放行 / 拒绝 | `release_sample` / `reject_sample` | 终态流转 |

查询类数据优先复用现有 Script Report（待检任务看板 / 样品台账 / 检验结果清单 / COA 发布记录 / 审计追踪查询），前端通过 Frappe REST 报表接口读取。

## 8. 风险与待确认

- **工程落位**：`frontend/hbos-lims-web/` 还是统一 `hbos-dashboard-web`，需 Owner 决策。
- **登录方式**：Frappe Desk session 同域部署，还是独立域 + token 代理，需在工程初始化阶段确认。
- **看板拖拽**：拖拽只触发已确认状态动作，不绕过后端状态机。
- **仪器数据**：`instrument_used` 当前为预留字段，仪器集成属于 M2 之外的扩展模块，不在本前端首版范围。
- **OOS 调查**：MVP 只保留 OOS 候选锁定与标记，完整调查流程前端另行规划。

## 9. 状态记录

- 本轮为 M2-LIMS 前端原型设计与开发流程设计，属于原型 / 视觉方案阶段。
- 产出文件：
  - `docs/frontend/M2_LIMS_Vue前端原型.html`
  - `docs/frontend/M2_LIMS_Vue前端开发流程.md`
- 状态：REVIEWING（等待 Owner 审查）；未进入前端复刻。
- 当前未修改 `hb_lims_app` 代码、未创建 Vue 工程、未接真实 API。
