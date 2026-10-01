# LIMS P4-F6 前台实施计划

状态：**P4-F6-5 REVIEWING / 2026-10-01 FRONTEND FIX VERIFICATION PASS / OWNER ACCEPTANCE AND REAL Frappe RUNTIME EVIDENCE PENDING / MANAGEMENT V0 GATE CLOSED**
日期：2026-10-01
适用分支：`m2-r10`
适用前端：`frontend/hbos-portal-web`
首个实现目标：LIMS Dashboard V2 + Task Board V1 + Result List / Result Entry V1 + Ledger / Audit / COA / Quality Standards Read-only V1

## 1. 计划依据

本计划只在以下门禁通过后生效：

- LIMS P4-F0 真实运行审计已交付；
- P4-F2 IA / Interaction Review 已通过；
- P4-F2 第二版 Visual Gate 已由 Owner 于 2026-09-29 验收通过；
- [LIMS P4-F2 Shell / Dashboard / Operational 设计方案](./LIMS_P4-F2_SHELL_DASHBOARD_设计方案.md) 为视觉、交互、路由和权限边界的 Authority；
- [LIMS 第二版 Visual Gate 交付说明](./LIMS_P4-F2_STATIC_VISUAL_GATE.md) 为中文优先、双品牌和实验室场景的视觉基线；
- [前端实施流程规范](../frontend/FRONTEND_IMPLEMENTATION_GUIDE.md) 继续约束复刻与功能接入顺序。

本计划进入工程实施，但不授权改写 Frappe / ERPNext / HRMS 核心、不复制 LIMS 业务事实、不绕过后端权限，也不把 Frappe Desk 管理页整体换成独立前端。

## 2. 当前事实与实施前阻塞项

### 2.1 已有落点

| 位置 | 当前事实 | 实施要求 |
| --- | --- | --- |
| `LimsLayout.vue` | Mock / real 两种模式都使用 LIMS Local Shell | 保持同源 `/hbos/lims/*`，不回退 8080 |
| `router/index.ts` | Dashboard / tasks / results / ledger / samples 路由已有稳定占位 | 先将 Dashboard、Task Board 注册为真实可用页面，再开放 capability |
| `limsCapabilities.ts` | Mock 只开放已有原型 `dashboard`；真实 Provider 能力必须与已实现页面目标交集后才开放 | 页面实现完成前保持隐藏，完成后由单一 projection 开放 |
| LIMS Provider | 已有 `manifest`、`summary`、`my_tasks`、`search`、`resolve_route` | 不由前端直接访问 LIMS DocType；补契约时保持 Provider 边界 |
| 设计原型 | 第二版是独立静态演示数据 | 不把原型数据、状态或计数复制进生产 Store |

### 2.2 必须先确认的 Provider 契约

当前 `summary.py` 投影的是“我的 LIMS 待办、LIMS 超期、检验待办、稳定性待办”；设计要求的四项 KPI 是“待检、检验中、待复核、待发布 COA”。两者不能仅靠前端改标签解决。

P4-F6-0 必须由 LIMS 领域 Owner / Provider Owner 确认：

1. 四项 KPI 的真实来源、权限范围和空值语义；
2. 任务 DTO 是否需要暴露领域状态（待分配、已分配、检验中、已提交、已复核、已批准、OOS 候选），还是由任务详情 API 补充；
3. Dashboard 风险、近期样品、检验组分布、状态分布和最近同步时间是否已有受控 API；
4. `/hbos/lims/tasks?view=my-testing|my-review|my-approval` 是否能由 Provider 映射为领域查询；
5. `search`、`deep_link` 和 capability projection 是否能支持真实前台落点；
6. 结果录入、复核、批准、样品登记等写操作的 API、SoD、签署和审计契约。

没有上述契约时，前端只能交付 loading / empty / error / pending，不得显示固定业务数字或开放写操作入口。

本轮按 Owner 指令允许在真实集成完成前落地只读 Shell / Dashboard：仅消费已确认的 Provider 字段，未开放写操作；真实 Frappe 集成仍是发布业务页的门槛。

## 3. 实施顺序

### P4-F6-0：Provider 与路由契约核验

目标：确认真实数据可以支持 P4-F2 设计，而不是先用 UI 推测业务。

工作项：

- 固化 `summary`、`my_tasks`、`search`、`resolve_route` 的响应样例、字段类型、权限范围和错误码；
- 逐条对账四项 KPI 与现有 `project_todo_summary` 的差异；
- 确认 tasks 的 `view` 查询参数与领域筛选映射；
- 确认稳定路由、Native deep link 回投、`/ledger` 和 `/samples/new` 别名；
- 由 Provider 返回 capability 与目标落点，前端只投影，不自行判断角色权限；
- 补齐 Provider 单元 / 契约测试，覆盖无权限、空数据、会话过期、部分 Provider 失败和深链安全校验。

退出条件：Provider 契约通过审查；四项 KPI、任务筛选、错误边界和路由回投均有可执行断言。

### P4-F6-1：LIMS Shell 生产复刻与 capability 接线

目标：将已验收原型的 Shell 语言落到 Vue，不改变业务规则。

工作项：

- 复用现有 `LimsLayout`、`GlobalHeader`、`AppLocalSidebar`、`MobileAppNav`，不新建重复 Shell；
- 将双品牌素材接入受控 branding 配置；原型资产只作为视觉参考，不作为业务数据；
- 将 LIMS emerald / cyan、状态 token、G1 / G2 surface、焦点、减弱动效和 44×44 命中区映射到现有 HBOS CSS / Ant Design Vue 主题；
- 将 capability projection 接到桌面侧栏、移动抽屉和路由守卫；无目标落点时保持隐藏或 pending；
- 统一加载、空、错误、无权限和会话过期组件；错误文案不得暴露 Frappe 方法名；
- 保持返回 HBOS、全局搜索、应用切换和 Frappe Session 入口。

退出条件：真实模式只显示 Provider 返回且有页面目标的入口；Mock 与真实模式均无假数字；Shell 契约脚本、路由测试和 Vue 类型检查通过。

### P4-F6-2：Dashboard V2

目标：先实现检验员、复核员和质量人员都能理解的工作台首页。

页面内容：

- 只读范围标签 `scopeLabel` 与最近同步时间；
- 四项真实 KPI，KPI 进入链接保留筛选上下文；
- “接下来要做”任务列表，展示样品、批次、项目、状态、截止时间、完成进度和下一步；
- 超期 / OOS 风险卡；
- 最近样品和当前样品上下文；
- 检验组分布、任务状态分布及其文本摘要；
- 首次无数据、服务错误、部分模块失败和加载态；
- 1440 / 1280 / 768 / 390 响应式布局；
- reduced-motion、键盘焦点和可访问名称。

数据边界：Dashboard 不创建第二套 Todo，不在前端计算权限范围，不使用静态演示数，不把趋势或“提升百分比”显示为无 API 依据的事实。

退出条件：真实 Provider 数据态与设计基线一致；每个 KPI、风险项和任务动作均能通过稳定路由进入下一页；视觉回归覆盖四档尺寸。

### P4-F6-3：Task Board V1

目标：实现检验员日常最高频的任务安排页。

页面内容：

- `view` 视图：我的待检、我的复核、我的审批；
- 搜索、状态、优先级、截止时间和刷新；
- 桌面任务表 / 状态分组，移动单列任务卡；
- 七项状态语义和 OOS 候选；
- 任务详情上下文、稳定深链和返回路径；
- 列表加载、无匹配、无权限、错误和重试；
- 键盘规则：焦点进入任务后方向键移动，Enter 打开记录，输入框 / 选择控件不拦截方向键。

任务状态只能由 LIMS 后端返回；前端不因点击“开始检验”直接改写业务状态。写操作在结果录入页另行实现并经过后端校验。

退出条件：任务筛选与 URL 保持同步；桌面 / 移动状态语义一致；深链往返和无权限行为通过测试。

当前实现：`LimsTaskBoardView` 已接入 `/hbos/lims/tasks`，完成三种角色视图、状态 / 优先级 / 截止时间 / 关键词筛选、桌面任务表、移动单列任务卡、加载 / 空 / 错误态和键盘焦点移动。真实 Provider 筛选参数已接入，业务动作仍保持只读导航；详细记录见 [`LIMS_P4-F6-3_TASK_BOARD实现记录.md`](./LIMS_P4-F6-3_TASK_BOARD实现记录.md)。真实 Frappe 集成核验仍待环境恢复。

### P4-F6-4：第一张 V1 操作页——Result List / Result Entry

目标：在 Dashboard / Task Board 稳定后，落地一张真实高频操作页，验证共享前端体系。

实施范围：

- Result List：样品、批次、项目、结果值、冻结限度、状态、截止时间；
- Result Entry：样品上下文、项目方法、标准快照、原始记录、仪器编号、结果值、异常说明；
- 含量、水分、定性项目的字段展示由真实项目契约驱动；
- 限度提示只作录入参考，最终判定由 LIMS 后端完成；
- 暂存、提交确认、失败保留输入、提交中状态；
- 复核人与检验人、批准人与检验人 / 复核人 SoD 只由后端判定；
- 结果详情的签署链和审计摘要只读展示。

本阶段不实现留样、稳定性、报告发布和审计写操作；这些页面在共享语言验证后按领域 capability 逐项接入。

退出条件：Result Entry 的真实 API 契约、权限、SoD、审计和状态迁移均有测试；不允许用原型的内存状态冒充生产事实。

当前实现：`LimsResultListView` 已接入 `/hbos/lims/results`，`LimsResultEntryView` 已接入结果详情与复核深链；Provider 新增 `results` capability，列表、详情、冻结限度、签署链和修订记录由 LIMS 领域投影提供。真实模式仅在后端允许的状态下开放提交、复核、批准动作，并通过现有领域服务执行；详细记录见 [`LIMS_P4-F6-4_RESULT_LIST_ENTRY实现记录.md`](./LIMS_P4-F6-4_RESULT_LIST_ENTRY实现记录.md)。

### P4-F6-5：其余领域按 capability 逐项接入

顺序建议：

1. 受控结果台账 / 审计只读视图；
2. 检验报告（COA）与质量标准只读视图；
3. 留样工作台及观察、使用、处理视图；
4. 稳定性考察、时间点、结果趋势和环境设备视图；
5. 具备明确 Provider 目标后再开放管理后台 V0 入口。

每一项都必须经过：领域 API 契约 → capability 注册 → Vue 复刻 → Provider / 权限测试 → 视觉回归 → Owner 复核。

当前实现：`LimsLedgerView` 已接入 `/hbos/lims/ledger`，`LimsAuditView` 已接入 `/hbos/lims/audit`，`LimsCoaView` 已接入 `/hbos/lims/coa`，`LimsQualityStandardsView` 已接入 `/hbos/lims/specifications`，`LimsRetentionWorkbenchView` 已接入 `/hbos/lims/retains/*`，`LimsStabilityWorkbenchView` 已接入 `/hbos/lims/stability/*`。Provider 新增 `ledger` / `audit` / `coa` / `specifications` / `retains` / `stability` capability；台账复用服务端结果聚合与冻结字段，审计复用审计事件和对象筛选，COA 与质量标准复用 Frappe 权限过滤的只读列表和明细投影，留样复用 `retention_service` 的观察 / 使用 / 处理只读投影，稳定性复用 `stability_service` 的工作台、计划、样品、结果与趋势只读接口。稳定性前台覆盖工作台、取样与检测计划、样品入箱台账、稳定性结果和趋势分析，保留日期链、储存条件、稳定性室、规格限和显著变化提示；不开放生成时间点、登记结果、延期审批或环境设备写操作。Bootstrap 继续透传 `lims.audit.read` 语义能力，审计入口按访问能力门控；COA、质量标准、留样和稳定性工作台当前不开放前台高风险写操作。管理后台 V0 已完成门禁复核：因缺少明确 Provider 目标、管理 API 和只读投影，`management` capability、路由和菜单均保持关闭，不跳转 Frappe Desk 或 8080。`/hbos/lims/samples` 与 `/samples/new` 当前继续保持同源占位，不被误标为已实现能力；样品读取与登记契约门禁见 [`LIMS_P4-F6-6_样品_PROVIDER契约门禁.md`](./LIMS_P4-F6-6_样品_PROVIDER契约门禁.md)。详细记录见 [`LIMS_P4-F6-5_LEDGER_AUDIT实现记录.md`](./LIMS_P4-F6-5_LEDGER_AUDIT实现记录.md)、[`LIMS_P4-F6-5_COA_SPEC实现记录.md`](./LIMS_P4-F6-5_COA_SPEC实现记录.md)、[`LIMS_P4-F6-5_RETENTION实现记录.md`](./LIMS_P4-F6-5_RETENTION实现记录.md)、[`LIMS_P4-F6-5_STABILITY实现记录.md`](./LIMS_P4-F6-5_STABILITY实现记录.md) 与 [`LIMS_P4-F6-5_MANAGEMENT_V0门禁记录.md`](./LIMS_P4-F6-5_MANAGEMENT_V0门禁记录.md)。

## 4. 文件与组件落点

| 责任 | 首选落点 |
| --- | --- |
| 稳定路由与页面注册 | `frontend/hbos-portal-web/src/router/index.ts` |
| LIMS Shell | `frontend/hbos-portal-web/src/components/layout/LimsLayout.vue` |
| 桌面 / 移动本地导航 | `AppLocalSidebar.vue`、`MobileAppNav.vue` |
| capability projection | `src/services/limsCapabilities.ts` + Provider manifest |
| 领域数据适配 | `src/services/portalApi.ts`、LIMS 专用 service / composables |
| Dashboard | `src/views/LimsHomeView.vue` 或拆分 `lims/` 目录后的 Dashboard 组件 |
| Task Board | 新增 LIMS 业务视图与可复用任务列表组件 |
| Result List / Entry | 新增 LIMS 业务视图；不得复用静态原型内存数据 |
| 主题和响应式 | `src/styles/global.css` 与 Ant Design Vue token |
| 后端 Provider | `apps/hb_lims_app/.../portal/`；不移动到 Portal 业务层 |
| 契约测试 | `apps/hb_lims_app/tests/`、Portal tests、前端单测 / 类型检查 |

组件命名沿用已确认映射：`LimsLayout`、`AppLocalSidebar`、`GlobalHeader`、`MobileAppNav`。不新建 `LimsLocalSidebar` 或第二套 `HbosGlobalHeader`。

## 5. 测试与验收矩阵

### Provider / 后端

- summary 四项 KPI 语义、权限范围、空值和错误；
- tasks 的 `view`、分页、状态、截止时间和 deep link；
- search 只返回当前用户可见记录；
- stable route 正向、反向、别名、查询参数和 traversal 防护；
- 角色、SoD、签署、状态迁移和审计不由前端绕过；
- 单一 Provider 失败不拖垮 Portal 其他 App。

### 前端

- `vue-tsc`、单元测试、构建和路由契约；
- Mock / real 两种数据源均不显示未经 capability 授权的入口；
- Dashboard / Task Board 的 loading、empty、error、permission、session expired；
- 1440 / 1280 / 768 / 390 视觉回归；
- 键盘、焦点、`aria-label`、reduced-motion；
- 搜索、筛选、返回、刷新、深链和浏览器后退；
- Result Entry 的字段保留、提交中、失败重试和后端状态回填。

### Owner 验收

- 首屏 10 秒内找到下一项检验任务；
- 从待检到结果录入上下文连续；
- 状态和下一步动作不混淆；
- 中文优先、品牌、实验室元素和响应式符合已验收原型；
- 真实业务事实、权限和签署不被前端演示数据替代。

## 6. 发布、回滚与停止条件

### 发布顺序

1. 先发布 Provider 契约与测试；
2. 再发布前端 Shell / capability 适配；
3. 再灰度 Dashboard；
4. Dashboard 稳定后开放 Task Board；
5. 第一张 V1 操作页单独发布；
6. 通过 Owner 验收后再开放下一领域。

### 回滚

- Provider 契约失败：保留旧摘要 / 任务能力，隐藏新入口；
- Dashboard 数据异常：返回安全的 loading / error / pending 页面，不显示猜测数值；
- Task Board 失败：保持 LIMS Shell 和 Dashboard 可用，入口按 capability 隐藏；
- Result Entry 失败：关闭写操作 capability，保留只读结果 / 台账入口；
- 任一权限或 SoD 回归：立即停止该页面发布并回退到 pending，不回退后端安全校验。

### 立即停止条件

- 前端直接访问数据库或复制 LIMS 业务事实；
- 生产页面出现原型固定数字、虚构任务或虚构仪器状态；
- 后端返回的权限 / SoD 被前端绕过；
- stable route 再次跳转 8080 原生后台；
- 视觉实现偏离已验收原型且未重新取得 Owner 审查。

## 7. 当前下一步

P4-F6-0 第二轮确认记录见 [`LIMS_P4-F6-0_PROVIDER_ROUTE_核验记录.md`](./LIMS_P4-F6-0_PROVIDER_ROUTE_核验记录.md)。业务状态、KPI 语义、任务视图、领域状态、结果写入和审计读取边界已从现有工作流与服务确认；Provider summary / tasks / results / ledger / audit / coa / specifications / retains / stability 适配已完成，真实 Frappe 集成证据和 Dashboard 专用只读字段仍待补齐。本轮已完成 P4-F6-1 Shell、P4-F6-2 Dashboard V2、P4-F6-3 Task Board V1、P4-F6-4 Result List / Result Entry V1，以及 P4-F6-5 Ledger / Audit / COA / Quality Standards / Retention / Stability Read-only V1：双品牌、错误态、页面目标与语义能力门控、稳定路由守卫、四项 KPI、任务卡、流程条、数据状态、三种任务视图、结果列表、结果录入、受控台账、审计追踪、检验报告、质量标准、留样和稳定性工作台只读明细已落地。两份前端审核报告中的 P0/P1 已逐条整改，记录见 [`LIMS_P4-F6-5_前端审核整改记录.md`](./LIMS_P4-F6-5_前端审核整改记录.md)；样品路径仍由同源 pending 页面承接，Provider 尚未声明可独立审查的样品读取 / 登记能力，契约门禁见 [`LIMS_P4-F6-6_样品_PROVIDER契约门禁.md`](./LIMS_P4-F6-6_样品_PROVIDER契约门禁.md)。详细记录见各 P4-F6 实现记录。真实集成通过前仅开放后端领域服务明确允许的结果写操作；稳定性工作台已完成 Mock 运行态预览，下一步进入真实 Frappe Session 复核、四档截图留证和 Owner Review，管理后台 V0 继续保持关闭。

## 2026-10-01 审核修复状态

2026-10-01 Portal 审核修复为 **REVIEWING / 本地验证通过，待 Owner 验收及真实 Frappe 运行态证据**：已处理 CSS token、错误态守卫、防抖与过期响应、刷新异常、强类型工作台、共享映射与六页查询逻辑、真实模式原型入口、回跳校验、环境变量与趋势图文档；Ant gzip 442.13 → 255.57 kB。14 项前端回归、构建和两套契约检查通过；临时 Mock 浏览器确认留样/稳定性实际颜色生效。修复提交 `f23ba17` 已从 `codex/portal-review-fixes` 合入 `m2-r10`；后续开发在 `m2-r10` 继续。详细记录见 `docs/experience/LIMS_P4-F6-5_前端审核整改记录.md`。本轮不部署，不关闭样品/管理后台或真实运行态门禁。
