# LIMS P4-F2 Shell / Dashboard / Operational 设计方案

状态：**P4-F6-5 COA / QUALITY STANDARDS READ-ONLY V1 IMPLEMENTED / LEDGER / AUDIT READ-ONLY V1 IMPLEMENTED / REAL INTEGRATION PENDING**
日期：2026-09-28
适用范围：`frontend/hbos-portal-web` 内的 LIMS 前台产品面
设计路线：**方案 A：Portal Shell 统一承载 + LIMS 内容区分层**

## 1. 设计目标

P4-F2 把 P4-F0 的真实运行审计转成一套可以交给 Owner 审查、再交给工程实现的 LIMS 前台设计基线。目标是让用户从 5178 的 Portal 进入 LIMS 后，继续使用同一套 HBOS 身份、导航和交互语言，同时保留 LIMS 对检验事实、质量规则、权限、SoD、签署链和审计记录的领域拥有权。

本方案覆盖：

- Portal Global Shell 与 LIMS Local Navigation 的边界；
- LIMS Dashboard V2；
- Task Board、Result List / Entry、Sample Registration、Result Ledger 四类 V1 操作面；
- 1440 / 1280 / 768 / 390 四档响应式行为；
- loading、empty、error、permission、session 过期和提交中状态；
- HBOS token 与 LIMS 领域色的映射；
- 页面信息架构、稳定路由和数据责任边界；
- Owner Visual / Interaction Gate 的审查项。

本轮不包含：

- LIMS 业务 API、DocType、工作流或权限代码；
- 结果提交、复核、批准、修订、电子签名的业务实现；
- 将 Portal Summary 或 Task DTO 复制成第二套 LIMS 事实；
- Frappe Desk 管理页面的换皮；
- Inventory、Attendance 或其他 APP 的前端实现；
- 生产 Vue 页面代码。

## 2. 设计决策

### 2.1 Shell 结构

```text
HBOS Global Header
├─ HBOS 品牌 / 返回首页
├─ 全局搜索（应用、样品、批次、结果）
├─ 应用切换
├─ 帮助
└─ 用户菜单 / Frappe Session

LIMS Application Surface
├─ LIMS Local Navigation
│  ├─ 我的工作
│  ├─ 专业业务
│  └─ 返回 HBOS 工作台
└─ LIMS Domain Content
   ├─ Dashboard V2
   ├─ Task / Result / Sample / Ledger V1
   └─ 业务状态、证据和操作
```

Portal 提供 Global Header、应用切换、全局搜索入口、会话恢复和跨应用返回。LIMS 提供本地信息架构、领域内容和业务动作。LIMS 页面不再嵌套 Portal 固定 Sidebar；桌面端使用 LIMS Local Sidebar，移动端使用底部导航和完整业务抽屉。

P4-F0 审查时发现的过渡差异已在本轮 Shell 安全修复中处理：`frontend/hbos-portal-web/src/router/index.ts` 的真实 Frappe 模式现在与 Mock 模式一样使用 `LimsLayout`。真实模式的业务页面仍渲染 pending 状态，避免把 pending 误认为已实现；P4-F6 的第 1 步改为验证这个 Shell 路径、接入真实 LIMS capability projection，再进入 Dashboard 或操作页实现。

### 2.2 视觉强度

| 面 | V-level | 视觉策略 |
| --- | --- | --- |
| LIMS Dashboard | V2 | 适度玻璃、LIMS emerald / cyan、KPI、图表、轻量进入动效 |
| Task Board | V1 | 低装饰、状态和截止时间优先、保留密度 |
| Result List / Entry | V1 | 表格和表单效率优先，冻结限度与签署链固定可见 |
| Sample Registration | V1 | 规则解释优先，决策条和快照信息稳定 |
| Result Ledger | V1 | 受控记录优先，列表与详情关系清晰 |
| Frappe Desk | V0 | 保留现有后台，不在本轮重做 |

### 2.3 角色与 Dashboard 范围

Dashboard 不展示一套固定的“实验室总览”。范围由 LIMS API 根据权限返回，前端只呈现 `scopeLabel` 和允许的指标。

| 用户类型 | 默认范围 | 首要入口 |
| --- | --- | --- |
| LIMS Analyst | 我的任务 | 待检、检验中、结果录入 |
| LIMS Reviewer | 我的复核 | 待复核、超期、结果详情 |
| LIMS QA / QA Manager | 我的审批 + QA 风险 | 待发布 COA、OOS、受控台账 |
| LIMS Manager | 实验室工作负载 | 状态分布、检验组分布、超期风险 |

前端不得根据角色名称自行推断业务权限。无权限的模块不显示；直接访问稳定 URL 时仍由后端访问检查返回最终结论。

## 3. 信息架构与稳定路由

### 3.1 Local Navigation

```text
我的工作
├─ 工作台                     /hbos/lims
├─ 我的待检                   /hbos/lims/tasks?view=my-testing
├─ 我的复核                   /hbos/lims/tasks?view=my-review
└─ 我的审批                   /hbos/lims/tasks?view=my-approval

专业业务
├─ 样品与检验                 /hbos/lims/samples
│  └─ 样品登记                 /hbos/lims/samples/new
├─ 质量与报告                 /hbos/lims/results
│  └─ 检验结果台账             /hbos/lims/ledger
├─ 检验报告（COA）             /hbos/lims/coa
└─ 质量标准                   /hbos/lims/specifications
├─ 留样管理                   /hbos/lims/retains
├─ 稳定性管理                 /hbos/lims/stability
└─ 合规审计                   /hbos/lims/audit
```

`retains`、`stability` 和 `audit` 只有在对应 LIMS capability 与 API 可用时显示。路由占位不能渲染 Mock 指标或伪造操作。

### 3.2 页面路由

| 页面 | 稳定路径 | 页面级别 | 主数据责任 |
| --- | --- | --- | --- |
| Dashboard | `/hbos/lims` | V2 | LIMS summary / dashboard API |
| Task Board | `/hbos/lims/tasks` | V1 | LIMS task / todo API |
| Result List | `/hbos/lims/results` | V1 | LIMS result list API |
| Result Entry / Review | `/hbos/lims/results/:resultId/review` | V1 full page | LIMS result / workflow API |
| Sample / Sample Ledger | `/hbos/lims/samples` | V1 list / ledger | LIMS sample list API |
| Sample Registration | `/hbos/lims/samples/new` | V1 form | LIMS sample registration API |
| Result Ledger | `/hbos/lims/ledger` | V1 split / single | LIMS controlled ledger API |
| COA Report | `/hbos/lims/coa` | V1 read-only | LIMS COA projection |
| Quality Standards | `/hbos/lims/specifications` | V1 read-only | LIMS specification projection |
| Retain / Stability / Audit | capability route | V1 | 各自 LIMS domain API |

Portal 只负责路由容器、会话和应用访问入口。稳定路径到当前实现路径的解析仍由 LIMS Provider 负责；前端不拼接 `/hbos-lims/...`，不直接访问 MariaDB，也不复制 DocType 查询。当前 Native LIMS 的 `/samples`（登记与台账）以及 `/results/ledger`（受控结果台账）可以继续作为内部实现路径，但稳定前台路径采用上表的拆分契约；Provider 适配器负责内部路径映射。稳定路径到 Native 路径与 Native deep link 回投稳定路径都必须通过同一适配器维护；`/samples/new` 当前回投到稳定 `/samples`，因为 Native `/samples` 仍是登记与台账合并页。

## 4. 三条核心用户旅程

### 4.1 检验员：从待检到提交结果

```text
Portal /hbos/apps
  → LIMS /hbos/lims
  → Dashboard「我的待检」
  → Task Board「我的待检」
  → 任务卡「录入结果 — {任务编号}」
  → Result Entry
  → 查看冻结限度 / 检验项目 / 样品批次
  → 输入结果、仪器、描述
  → 提交结果确认
  → LIMS 后端校验权限、状态和审计
  → 返回任务或结果详情
```

设计重点：主动作始终带记录上下文；提交确认不能只显示“提交”；失败后保留用户输入，并明确是字段校验、业务规则还是会话问题。

### 4.2 复核员：从超期提醒到复核结论

```text
Dashboard 超期 / 待复核提醒
  → Task Board「我的复核」
  → Result Review
  → 结果值与冻结限度并列
  → 样品 / 批次 / 质量标准上下文 Drawer
  → 检验人 → 复核人 → 批准人签署链
  → 通过或退回
  → Modal 输入必要理由
  → LIMS 后端执行 SoD / workflow / audit
```

样品上下文是辅助证据，使用 Drawer；复核本身是核心工作流，使用完整页面。退回和提交确认使用短决策 Modal，不用长表单抽屉承载。

### 4.3 QA：从状态分布到受控台账

```text
Dashboard「待发布 COA / OOS 风险」
  → `/hbos/lims/ledger` Result Ledger
  → 按样品、批次、结果状态、签署状态筛选
  → 列表选择记录
  → 768px 以下切换到详情页
  → 查看修订记录、签署链、内容指纹和受控状态
```

台账默认只读。任何修订、发布和签署仍走 LIMS 领域动作与后端授权。

## 5. Dashboard V2 原型说明

### 5.1 桌面布局

```text
┌────────────────────────────────────────────────────────────────────────────┐
│ HBOS Header                                                    账户 / 切换 │
├───────────────┬────────────────────────────────────────────────────────────┤
│ LIMS Local    │ 面包屑：LIMS / 工作台       当前范围：{scopeLabel} [刷新]    │
│ Sidebar       │                                                            │
│               │ ┌────────────────────────────────────────────────────────┐ │
│ 我的工作      │ │ 今日实验室工作台                         最近同步时间   │ │
│  工作台       │ │ {scopeLabel}                                            │ │
│  我的待检  2  │ └────────────────────────────────────────────────────────┘ │
│  我的复核  3  │                                                            │
│  我的审批     │ ┌────────┬────────┬────────┬────────┐                     │
│               │ │ 待检   │ 检验中 │ 待复核 │ 待发布 │                     │
│ 专业业务      │ │ count  │ count  │ count  │ COA    │                     │
│  样品与检验   │ │ 进入   │ 进入   │ 进入   │ 进入   │                     │
│  质量与报告   │ └────────┴────────┴────────┴────────┘                     │
│  留样管理     │                                                            │
│  稳定性管理   │ ┌──────────────────────────┬─────────────────────────────┐ │
│  合规审计     │ │ 超期 / OOS 风险          │ 最近样品                    │ │
│               │ │ 文本告警 + 处理入口      │ 样品号 / 批次 / 状态 / 时间  │ │
│ 返回工作台    │ └──────────────────────────┴─────────────────────────────┘ │
│               │ ┌──────────────────────────┬─────────────────────────────┐ │
│               │ │ 检验组分布（图 + 表）    │ 任务状态分布（图 + 表）      │ │
│               │ │ 文本摘要可展开            │ 文本摘要可展开               │ │
│               │ └──────────────────────────┴─────────────────────────────┘ │
└───────────────┴────────────────────────────────────────────────────────────┘
```

### 5.2 KPI 语义

固定保留当前 Native LIMS 已验证的四项：

1. 待检：当前范围内尚未开始的检验任务；
2. 检验中：已分配或已开始但未提交的任务；
3. 待复核：已提交、等待复核的结果；
4. 待发布 COA：已具备发布前条件、等待 QA / QP 动作的记录。

KPI 卡显示数字、语义状态、只读范围标签和进入列表动作。趋势、同比和“提升百分比”只有在 API 提供真实比较窗口时才显示。

P4-F2 不引入范围切换。`scopeLabel` 是 LIMS API 返回的只读文本，前端不能把它渲染成无契约的下拉框。未来如果需要切换范围，Provider 必须同时提供 `scopeOptions`、当前选中值、权限和切换后的数据边界，再单独评审交互契约。

### 5.3 风险模块

风险模块只显示 LIMS API 返回的超期或 OOS 风险。每一条风险至少包含：

- 风险类型文字（超期 / OOS）；
- 记录编号、样品或批次上下文；
- 当前状态；
- 截止时间或发现时间；
- 处理入口。

颜色只强化风险，不独立承担含义。无风险时显示“当前范围内暂无超期或 OOS 风险”，不使用空白卡片。

### 5.4 图表与无障碍

检验组分布和任务状态分布使用 ECharts，但每个图表必须同时提供：

- 图表标题和当前范围；
- 图下方文本摘要；
- 可展开的数据表或列表；
- 颜色、标签和数值三种信息线索。

图表加载失败只影响图表区域，不阻断 KPI 和列表。图表没有数据时使用“当前范围暂无可展示分布”，并提供进入任务列表的动作。

## 6. Operational V1 原型说明

### 6.1 Task Board

#### 桌面

顶部顺序固定为：页面标题 → 当前范围 → 搜索 → 状态 / 优先级 / 截止时间筛选 → 刷新。所有控件有可见标签或等价 `aria-label`。

任务导航入口使用 `view` 查询参数：`my-testing`、`my-review`、`my-approval` 分别表示待检、复核、审批视图；它只控制 Task Board 的当前视图，不改变权限范围。Dashboard 的 `scopeLabel` 是 LIMS API 返回的只读权限范围文本，两者不能互相替代。Task Board 需要把 `view` 映射为领域 API 支持的任务筛选；不支持的值回退到默认视图，并保留安全的 URL 状态。Portal Provider 现有待办 deep link 中的 `scope=mine` 是跨应用稳定链接契约，与 LIMS 本地导航的 `view` 不同。

```text
待检任务                         [我的任务 ▼] [搜索任务] [优先级 ▼] [刷新]
7 个状态栏：待分配 | 已分配 | 检验中 | 已提交 | 已复核 | 已批准 | OOS 候选

┌ 待分配 (2) ┐ ┌ 已分配 (3) ┐ ┌ 检验中 (4) ┐ ...
│ 任务编号   │ │ 任务编号   │ │ 任务编号   │
│ 样品 / 批次│ │ 样品 / 批次│ │ 样品 / 批次│
│ 截止时间   │ │ 优先级     │ │ 检验员     │
│ [处理 — 编号] │ [查看 — 编号] │ [录入 — 编号] │
└────────────┘ └────────────┘ └────────────┘
```

任务卡必须展示任务编号、项目、样品、批号、优先级、截止时间和当前责任人。操作按钮的可访问名称绑定具体任务编号，不能重复只读为“录入”或“查看”。

#### 移动

390px 下不展示七栏并排结构。按 EA-5.5 的“侧栏 → 移动入口 / Drawer”原则保留业务导航；任务状态本身使用带可见标签的全宽 `状态` 选择控件，选项为 `全部状态`、待分配、已分配、检验中、已提交、已复核、已批准、OOS 候选，默认选中 `全部状态`。筛选值同步到 URL 的 `status` 查询参数，便于刷新和返回保持上下文。之后显示单列任务卡：

- 顶部固定当前状态和筛选入口；
- 卡片显示主上下文和一个主动作；
- 其他动作放入“更多”菜单；
- 不依靠横向滚动才能发现主动作。

### 6.2 Result List / Result Entry

#### Result List

主表列顺序：结果编号、样品 / 批次、检验项目、状态、判定、截止时间、责任人、操作。列表顶部显示当前筛选条件和结果数量；筛选后空态必须显示“没有匹配结果”，并提供清除筛选。

行操作示例：

- `录入结果 — HBOS-TR-2026-00041`；
- `查看结果 — HBOS-TR-2026-00136`；
- `打开样品上下文 — SAMPLE-...`。

#### Result Entry / Review

桌面采用 `8 : 4`：

```text
┌──────────────────────────────────┬─────────────────────────────┐
│ 结果输入 / 复核结论               │ 样品与质量标准上下文         │
│                                  │ 样品号 / 批号                │
│ 检验项目、原始值、结果值、单位    │ 质量标准版本                 │
│ 冻结限度、自动判定、结果描述      │ 冻结限度摘要                 │
│ 仪器 / 附件 / 备注                │ 检验人 → 复核人 → 批准人      │
│                                  │ 修订记录                     │
│ [保存草稿] [提交结果]             │ [查看完整样品上下文]          │
└──────────────────────────────────┴─────────────────────────────┘
```

必须保持以下业务证据的稳定位置：冻结限度、自动判定、检验项目快照、签署链、修订记录。已批准结果默认只读，修订动作必须有明确的 LIMS 业务入口和提示。

768px 下右侧上下文变为页面下方折叠区；390px 下使用单栏、分段折叠和底部固定操作栏。底部操作栏只显示当前状态允许的动作。

### 6.3 Sample Registration

表单分为四个可扫描区块：

1. 样品基础信息：样品类型、优先级、来源、批次；
2. 质量标准：标准名称、版本、生效状态；
3. 检验项目快照：项目、单位、限度、方法；
4. 登记后冻结规则：哪些字段将在登记后锁定，为什么锁定。

顶部保留“决策条”，清楚说明当前样品是否具备登记条件。底部主动作按照当前状态显示“保存草稿”或“登记样品”，不在前端预判后端权限。

### 6.4 Result Ledger（稳定路径：`/hbos/lims/ledger`）

桌面为列表 + 详情双栏：

- 左侧：可筛选的样品 / 结果记录列表；
- 右侧：受控状态、内容快照、签署链、修订记录和审计摘要；
- 详情不覆盖列表筛选上下文。

768px 改为列表与详情的分段切换；390px 改为列表卡片 → 全屏详情页。详情页提供返回列表和当前筛选条件摘要，避免用户失去位置。

## 7. 共享组件与 Token 映射

### 7.1 现有代码到设计组件的映射

不新建重复 Shell。实现时沿用现有文件并逐步收敛命名责任：

| 设计责任 | 当前代码 | 实现要求 |
| --- | --- | --- |
| `HbosGlobalHeader` | `components/layout/GlobalHeader.vue` | 继续复用；不复制第二个 Header |
| `LimsAppShell` | `components/layout/LimsLayout.vue` | 作为真实模式 LIMS 路由容器；保留 Global Header、Local Sidebar、移动导航 |
| `LimsLocalSidebar` | `components/layout/AppLocalSidebar.vue` | 使用统一 `limsCapabilities` projection 驱动；不新建第二套 Sidebar |
| `LimsMobileNavigation` | `components/layout/MobileAppNav.vue` | 继续复用，补齐完整专业业务 Drawer |
| `PortalShell` | `components/layout/PortalLayout.vue` | 只承载 Portal 固定导航页面，不作为最终 LIMS Shell |

本轮 Shell 安全修复已移除 `AppLocalSidebar.vue` 的徽标 `5 / 2 / 3` 和静态按钮，改为稳定 `RouterLink`；未来徽标只在 LIMS Provider 返回真实计数时显示，否则隐藏。当前代码已收敛到单一 `limsCapabilities` 来源：Mock 只返回已有原型视图，真实模式读取 Provider manifest 的 capability projection；现阶段 `summary` 只投影为可用 Dashboard，`tasks` / `search` 仍是数据能力，尚未注册本地操作页时不显示入口。留样、稳定性和审计入口在真实 Frappe 模式下按同一 capability projection 门控，避免 pending 页面伪装成已上线能力。`managementRoute` 接线和更多页面 capability 映射属于 P4-F6，不是本轮已完成的业务页面实现。管理后台不属于 LIMS 业务 IA，见下方 §7.3。契约回归脚本为 `scripts/portal/lims_shell_contract.sh`。

### 7.2 组件清单

| 组件 | 责任 | 状态要求 |
| --- | --- | --- |
| `HbosGlobalHeader` | 全局身份、搜索、应用切换、会话 | default / compact / session-expired |
| `LimsLocalSidebar` | LIMS IA、返回工作台 | expanded / collapsed / mobile drawer |
| `LimsKpiCard` | Dashboard 指标入口 | loading / value / empty / unavailable |
| `LimsStatusTag` | 状态、判定、风险语义 | text + icon + color |
| `LimsFilterBar` | 搜索与筛选 | labelled / active / clear / loading |
| `LimsTaskCard` | 任务上下文与主动作 | overdue / disabled / action pending |
| `LimsTaskLane` | 任务状态分组 | loading / empty / error |
| `LimsDataTable` | 结果和台账密度 | sticky header / keyboard / responsive |
| `ResultContextPanel` | 样品、批次、标准、限度 | read-only / loading / unavailable |
| `DecisionBar` | 样品登记条件解释 | pass / warning / blocked |
| `SignatureChain` | 检验人、复核人、批准人 | pending / completed / blocked |
| `LimsEmptyState` | 首次无数据与筛选无匹配 | context-specific action |
| `LimsErrorState` | 权限、会话、服务和业务错误 | safe copy / retry / back |
| `LimsMobileActionBar` | 移动端主动作 | status-aware / safe-area |

### 7.3 管理后台入口（V0）

`管理后台` 保留为 Local Sidebar 底部的独立 V0 入口，不纳入 §3.1 的业务导航树。它只有在当前用户和 LIMS Provider 返回 `managementConsole` capability 以及可用目标路由时显示；当前 `LimsLayout` 尚未传入 `managementRoute`，因此不会渲染该入口，待 P4-F6 完成 capability projection 与目标路由接线后再开放。点击必须是有明确目标的链接或路由动作，不能继续使用无行为的静态 button。它进入 Frappe / LIMS 管理面后保持 V0，不复制到 P4 V1 操作页。

### 7.4 Token 基线

| 类别 | LIMS P4-F2 约束 |
| --- | --- |
| Spacing | 4px 基础单位；页面区块 24 / 32px；卡片内边距 16 / 20px |
| Radius | 控件 10–12px；普通卡片 16–18px；大卡片 22–24px；标签 999px |
| Typography | 标题 32–40px；区块 20–22px；正文 14px；密集表格 13px；元信息 11–12px |
| Domain accent | LIMS 使用 emerald / cyan；仅做应用识别和重点强调 |
| Status | `neutral / info / success / warning / critical / processing / disabled` |
| Surface | Dashboard 使用 G2 Medium Glass；操作页使用 G1 Light Glass 或普通 Surface |
| Motion | Dashboard 轻量 180–300ms；操作页减少动效；遵守 reduced-motion |
| Focus | 所有键盘焦点清晰；icon-only 控件命中区至少 44×44px |

### 7.5 状态语义

| 业务语义 | 状态 token | 文字示例 |
| --- | --- | --- |
| 检验通过 | success | 已通过 |
| 等待复核 | processing | 待复核 |
| OOS / 阻断 | critical | OOS / 已阻断 |
| 临近截止 | warning | 即将超期 |
| 已批准 | success | 已批准 |
| 不可用 | disabled | 当前不可用 |

状态必须同时使用文字或图标；不能只依赖绿色、黄色或红色。

## 8. Loading / Empty / Error 状态矩阵

| 场景 | 用户看到的内容 | 恢复动作 |
| --- | --- | --- |
| 首次加载 | 页面骨架、卡片骨架、表格行骨架 | 等待；不显示空态 |
| 刷新中 | 保留旧数据，局部 loading overlay | 可继续浏览；动作按钮按接口要求禁用 |
| 首次无数据 | “当前没有需要你处理的检验任务” | 查看全部样品 / 去样品登记 |
| 筛选无匹配 | “没有匹配结果” + 当前条件 | 清除筛选 |
| 无权限 | “当前账号无权访问此 LIMS 页面” | 返回工作台 / 联系管理员 |
| 会话过期 | “登录状态已过期，请重新登录” | 重新登录并保留目标路径 |
| LIMS 服务不可用 | “LIMS 数据暂时不可用” | 重试 / 返回工作台 |
| 业务校验失败 | 字段级错误 + 顶部摘要 | 修正字段；保留已填内容 |
| 提交中 | 主按钮显示提交中，避免重复提交 | 等待结果；失败可重试 |
| 提交失败 | 明确失败原因，不显示 Python / Frappe 方法名 | 重试 / 返回详情 |

所有错误文案由前端做安全映射。`frappe.client.get_list`、`frappe.desk.query_report.run`、`@frappe.whitelist()` 等实现细节只进入日志或开发诊断，不进入用户提示。

## 9. Responsive 规则

| 视口 | Shell | Dashboard | 操作页 |
| --- | --- | --- | --- |
| 1440 | Global Header + 240px Local Sidebar | KPI 4 列；风险、最近样品和图表两列 | 结果页 8:4；台账列表 / 详情双栏 |
| 1280 | Local Sidebar 232px；内容收窄 | KPI 2×2；图表保持双栏 | 表格密度不降低；上下文面板可收窄 |
| 768 | Local Sidebar 折叠 76px；Header 压缩 | 单列或 2 列；风险先于图表 | 结果上下文堆叠；台账列表 / 详情切换 |
| 390 | Global Header compact；底部导航 + 业务抽屉 | 单列卡片；指标显示关键数值和入口 | 任务卡 / 结果表单 / 台账详情单列；底部主动作栏 |

数据表在必要时允许横向查看列，但编号、状态和主动作要在首屏或卡片摘要中可见；核心动作不能只能通过横向滚动发现。桌面侧栏隐藏后，所有 LIMS IA 必须通过移动导航或完整抽屉保留。

## 10. Accessibility 与交互门禁

- Portal → LIMS 页面保留 skip link，焦点落到主要内容；
- Global Header、Local Sidebar、底部导航和 Drawer 的键盘顺序连续；
- icon-only 控件必须有 `aria-label`、Tooltip 和至少 44×44px 命中区；
- 搜索、筛选、状态列和操作按钮均有稳定可访问名称；
- 图表有文本摘要和可展开数据表；
- 状态同时使用文字 / 图标 / 颜色；
- 表单错误既在字段附近显示，也在顶部提供摘要；
- `prefers-reduced-motion: reduce` 时关闭光场、粒子和非必要过渡；
- 中文正文不低于 12px，常规正文使用 14px；
- 任何高风险动作在提交前提供清晰的记录上下文和必要理由字段。

### 10.1 键盘交互

EA-5.4 已冻结可访问焦点、44×44 命中区和 Command Palette 的上下选择 / Enter 执行规则；LIMS 操作面补充以下路径：

- Task Card：Tab 进入当前可操作卡片，Enter 打开记录；卡片内动作按视觉顺序排列；
- Task Board：在卡片列表获得焦点后，`ArrowUp / ArrowDown` 移动同一状态栏中的卡片，`ArrowLeft / ArrowRight` 切换状态栏；输入框和选择控件获得焦点时不拦截方向键；
- Result / Ledger Table：Tab 进入行，Enter 打开记录或详情；筛选条件通过 Esc 清除临时弹层焦点；
- Drawer / Modal：打开后焦点进入标题或第一控件，Esc 关闭辅助 Drawer / Modal，关闭后回到触发控件；
- 移动端状态选择控件使用原生或 Ant Design Vue 键盘语义，不模拟横向看板的方向键操作。

键盘交互的实现不得改变 LIMS 后端动作、权限或状态，只改变焦点移动和路由打开行为。

## 11. 数据与权限边界

```text
Portal
├─ Frappe Session / 登录恢复
├─ Global Shell / App Switcher / Search entry
├─ stable route container
└─ cross-app summary / task projection

LIMS
├─ KPI / task / result / sample / ledger facts
├─ business permissions and role scope
├─ workflow / SoD / signature / audit
├─ validation and write operations
└─ current implementation route resolver
```

前端显示“可操作”不等于授权。所有写操作由 LIMS 后端再次校验当前用户、记录状态、SoD、签署和审计要求。Portal 不执行高风险 LIMS 动作，不创建第二套 Todo，不缓存业务状态作为事实来源。

## 12. 审查记录与条件闭合

### 12.1 Owner 条件审核记录 — 2026-09-28

审查结论：**PASS WITH CONDITIONS**。本次核验确认以下问题真实存在，并已在本版设计中闭合为实现前置条件：

| 编号 | 核验结论 | 本版处理 |
| --- | --- | --- |
| R1 | 真实 Frappe 模式当前使用 `PortalLayout`，LIMS Local Shell 只在 Mock 模式存在 | 已切换真实 `/hbos/lims/*` 路由到 `LimsLayout`；业务页面继续 pending，P4-F6 第 1 步改为验证并接入真实 capability projection |
| R2 | `AppLocalSidebar.vue` 存在写死 `5 / 2 / 3`、静态按钮和无路由行为 | 已移除假数字和静态按钮，改为稳定 `RouterLink`；未来计数由 Provider projection 提供，无数据隐藏；新增契约回归脚本 |
| R3 | 当前 `/samples` 同时承担登记与台账语义 | 拆为 `/samples` 列表 / 台账与 `/samples/new` 登记 |
| R4 | `[范围]` 控件没有 API 枚举契约 | 改为只读 `当前范围：{scopeLabel}`；范围切换另开契约 |
| R5 | 390px 下七状态栏缺少选择形态和默认值 | 定义全宽 `状态` 选择控件，默认 `全部状态`，URL 同步 `status` |
| R6 | `/results/ledger` 与结果详情同前缀且语义混淆 | 稳定路径改为 `/hbos/lims/ledger`；`hb_lims_app` Provider 已将其映射到当前 `/hbos-lims/results/ledger`，并要求详情动态路由之后声明 |
| R7 | `管理后台` 在代码中存在，但不在业务 IA 中 | 定义为 Local Sidebar 底部独立 V0 capability 入口，不进入业务树 |
| R8 | 设计组件名与现有代码名不同 | 增加现有文件到设计组件映射，不新建重复 Shell |
| R9 | 仅定义焦点样式，未定义任务卡 / 表格键盘路径 | 增加 Task Board、Table、Drawer / Modal 键盘规则 |
| R10 | Owner Review 项没有可签署格式 | §12.2 改为通过 / 修改 / 否决 / 备注清单 |
| R11 | P4-F0 尚无四档持久化截图，直接称 Visual Gate 不完整 | 拆成 IA / Interaction Gate 与静态 Visual Gate 两段 |

### 12.1.1 复审补充项 — N1–N5

复审结论：**PASS**。以下补充项已落实。

| 编号 | 复审发现 | 本版处理 |
| --- | --- | --- |
| N1 | Native deep link 只有 stable → implementation 单向映射 | `IMPLEMENTATION_TO_STABLE_ALIASES` 补齐 `/results/ledger` → `/ledger`；`/samples` 明确回投稳定列表 / 台账路径，并加入往返契约测试 |
| N2 | `portalDataSource === 'mock'` 不能代表页面是否有可用落点 | Sidebar / Mobile 共用 `limsCapabilities`；Mock 仅暴露已有原型，真实模式从 Provider manifest 投影；数据 capability 没有本地页面时不渲染入口 |
| N3 | 移动抽屉前缀激活会造成多个入口同时高亮 | 所有 Drawer `RouterLink` 使用 `exact-active-class="active"`，样式改用 `.router-link-exact-active` |
| N4 | 导航筛选 `scope` 与 Dashboard `scopeLabel` 语义相撞 | LIMS 本地导航改用 `view=my-testing|my-review|my-approval`；`scopeLabel` 保持只读权限范围，Portal 既有 `scope=mine` 跨应用 deep link 契约保持不变 |
| N5 | 设计措辞容易让人误以为 capability 接线已经完成 | §7.1 明确当前 projection 边界；`managementRoute` 接线、页面 capability 注册和真实操作页落地列为 P4-F6 |

分支核验：当前工作区分支为 `m2-r9`，`feature/hbos-portal-product` 与当前 HEAD `095c243` 指向同一提交，现有 Portal 改动位于同一提交图上；本轮未执行分支改名或迁移。

### 12.2 IA / Interaction Owner Review 清单

Owner 结论：**通过（2026-09-28）**。本结论覆盖下列九项 IA / Interaction 审查项，现进入静态 Visual Gate；备注栏保留后续追踪空间。

| # | 审查项 | 通过 | 修改 | 否决 | Owner 备注 |
| ---: | --- | :---: | :---: | :---: | --- |
| 1 | Shell：Global Header + LIMS Local Navigation；真实模式先落 LIMS App Shell | ✅ |  |  | Owner 2026-09-28 |
| 2 | Dashboard 四项 KPI 语义与只读范围标签 | ✅ |  |  | Owner 2026-09-28 |
| 3 | `/samples` 列表 / 台账与 `/samples/new` 登记拆分 | ✅ |  |  | Owner 2026-09-28 |
| 4 | `/hbos/lims/ledger` 稳定路径及 Provider 内部映射 | ✅ |  |  | Owner 2026-09-28 |
| 5 | Result Entry `8:4` 与冻结限度、签署链位置 | ✅ |  |  | Owner 2026-09-28 |
| 6 | 390px 状态选择控件、默认 `全部状态` 与 URL 同步 | ✅ |  |  | Owner 2026-09-28 |
| 7 | 空态、权限、服务不可用、会话过期和错误安全映射 | ✅ |  |  | Owner 2026-09-28 |
| 8 | LIMS emerald / cyan 与 shared semantic status 的关系 | ✅ |  |  | Owner 2026-09-28 |
| 9 | Retain / Stability / Audit 的 capability-driven 入口 | ✅ |  |  | Owner 2026-09-28 |

### 12.3 静态 Visual Gate

IA / Interaction 清单通过后，另开静态视觉原型审查。静态视觉原型必须在 1440、1280、768、390 四档提供可持久化截图或等价可审查预览，至少覆盖：

- LIMS App Shell（Global Header + Local Sidebar）；
- Dashboard V2 数据态、首次无数据态和服务错误态；
- Task Board 桌面栏与 390px 单列状态筛选；
- Result Entry 桌面 `8:4`、768px 堆叠和 390px 底部动作栏；
- Result Ledger 列表 / 详情切换。

P4-F0 记录的截图持久化限制仍然有效；当前文字规格和 ASCII 线框不代替静态 Visual Gate。

## 13. 原型交付与 Owner Review 范围

本文件是 P4-F2 的设计规格、交互文字原型和条件闭合记录。IA / Interaction Owner Review 已于 2026-09-28 通过；第二版静态视觉原型已交付于 [`LIMS_P4-F2_STATIC_VISUAL_GATE.md`](./LIMS_P4-F2_STATIC_VISUAL_GATE.md) 及其兼容 HTML 入口，并于 2026-09-29 通过 Owner Visual Gate。P4-F6 实施计划已交付于 [`LIMS_P4-F6_实施计划.md`](./LIMS_P4-F6_实施计划.md)，P4-F6-0 Provider 适配已完成，当前仍需真实 Frappe 集成验证和 Dashboard 专用只读字段确认：

1. 方案 A 的 Shell 边界与真实模式先落 App Shell 的顺序；
2. Dashboard 四项 KPI 的语义与只读范围标签；
3. `/samples`、`/samples/new` 与 `/ledger` 的路由契约；
4. Result Entry 的 `8 : 4` 结构、冻结限度和签署链位置；
5. 移动端状态选择、单栏、底部动作栏和台账详情切换方式；
6. 空态、权限、服务不可用和会话过期的用户文案；
7. LIMS emerald / cyan 领域色与 shared semantic status 的关系；
8. Retain / Stability / Audit 作为 capability-driven 后续页面；
9. Visual Gate 已通过，P4-F6 实施计划已交付；文字线框和静态原型均不替代真实 Provider 验证。

本轮允许在 Gate 前保留的代码变更仅限 Portal Shell 安全 carve-out：真实模式使用 `LimsLayout`、稳定导航、别名适配、能力门控和契约回归。该边界已随 IA / Interaction Review 通过得到 Owner 追认；它不授权提前实现 LIMS 业务页面、业务 API、权限或流程。

### P4-F2 退出条件

```text
P4-F0 真实运行审计                         COMPLETE
P4-F2 Shell / IA / V2 / V1 设计方案          本文
R1–R11 条件闭合                              本文
Shell 安全修复（R1 / R2）                    PASS
IA / Interaction Owner Review                 APPROVED
第二版静态视觉原型 / Visual Gate              APPROVED · 2026-09-29
implementation plan                         DELIVERED
真实 Frappe Provider 集成                     PENDING
Vue 页面实现                                  Provider 集成通过后
```

本轮没有修改 LIMS 业务页面、业务 API、权限或流程；仅交付 Portal LIMS Shell 安全修复和独立静态视觉原型。Owner 已验收 Visual Gate，P4-F6 实施计划已交付；其第 1 步为验证 Shell 与真实 capability projection，然后才实现 Dashboard 与一张 V1 Operational Page。

## 14. 2026-09-29 视觉交付修订记录

Owner 对第一版视觉交付提出退回意见：界面必须以中文为主，完整体现 LIMS 领域，检验员需要能连续理解任务、进行状态和下一步操作，并纳入健康元集团与海滨公司原始标识。本节修订覆盖静态视觉交付，不改变已通过的权限边界、SoD、状态语义和路由契约。

第一版静态 HTML 不再作为视觉基线。第二版原型位于 [`prototypes/lims-p4-f2-v2/index.html`](./prototypes/lims-p4-f2-v2/index.html)，交付说明和 Owner 清单位于 [`LIMS_P4-F2_STATIC_VISUAL_GATE.md`](./LIMS_P4-F2_STATIC_VISUAL_GATE.md)。第二版以检验员“今日工作 → 任务 → 结果录入 → 复核 / 批准 → 受控台账”为主线，同时将报告、标准、留样、稳定性、审计和全部功能纳入本地工作区。

第二版仍是只读演示原型：所有记录、结果、签署和状态变化均为当前浏览器会话内的模拟；没有接入 API、权限写入、仪器监控或库存操作。Owner 已于 2026-09-29 验收通过 Visual Gate，P4-F6-0 Provider 适配、P4-F6-1 Shell 和 P4-F6-2 Dashboard V2 已完成；真实 Frappe 会话集成检查、Dashboard 专用字段和 Task Board V1 仍待继续。
