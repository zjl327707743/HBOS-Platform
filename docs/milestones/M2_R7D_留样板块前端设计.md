# M2-R7D 留样板块前端设计（原型 / 视觉方案阶段）

项目名称：新乡海滨智能运营管理平台（HBOS）。

轮次状态：原型 / 视觉方案 REVIEWING → Vue 复刻与生产部署 DEPLOYED（Owner 2026-09-08 已确认测试路径并授权同步生产 `/hbos-lims`）。本文件为 M2-R7D 主文档，覆盖「原型先行 → Vue 复刻 → 生产部署」全流程。

## 输入与依据

- M2-R7 留样管理板块开发方案 rev6（已批准业务口径、角色方案 B+SoD、分支策略 b）。
- `docs/frontend/FRONTEND_IMPLEMENTATION_GUIDE.md`：原型先行 → Owner 审查 → Vue 复刻 → 功能接入。
- 现有 Vue 工程 `frontend/hbos-lims-web`（Vue 3 + Vite + TypeScript + Pinia + Vue Router + Ant Design Vue + ECharts）。
- 现有 R7A 页面 `RetentionView.vue`、`RetentionProductView.vue` 作为复刻基线。

## 本轮交付

| 文件 | 说明 |
| --- | --- |
| `docs/frontend/M2_R7_留样板块前端设计方案.md` | 前端可执行设计方案（页面清单、视觉 Token、角色动作、API 契约、实施步骤、验收清单） |
| `docs/frontend/M2_R7_留样板块前端原型.html` | 交互式 HTML 原型，6 个视图，可用 `#view` 直达 |
| `docs/milestones/M2_R7D_留样板块前端设计.md` | 本文件（轮次主文档） |

设计图渲染文件位于本地可视化目录（非仓库交付物）：`【本地私有路径已省略】`。

## 设计范围

6 个页面：

1. 留样工作台总览（`/retention`）
2. 留样登记与台账（`/retention/samples`）
3. 留样产品（`/retention/products`）
4. 观察任务（`/retention/observations`）
5. 使用申请（`/retention/usage`）
6. 处理申请（`/retention/disposal`）

页面全部采用现有深青侧栏 + 米白内容区 + 绿色主操作视觉基线；库存量展示统一为「结存 / 预占 / 可用量」派生口径；审批链、SoD、4/5 级审批、N/3 观察完整性均按 M2-R7 rev6 口径设计。

## 原型/视觉方案阶段边界

「原型先行」阶段未修改 Vue 工程、未创建 DocType、未写 Python 业务方法、未接真实 API，仅交付上方「本轮交付」三件设计稿；随后经 Owner 确认进入 Vue 复刻与生产部署（见下节）。

## Vue 复刻与生产部署（2026-09-08 · DEPLOYED）

Owner 2026-09-08 确认按本方案进入 Vue 复刻并授权同步生产。在 `m2-r6` 分支 `frontend/hbos-lims-web` 落地留样板块 6 视图：

- **路由与导航**：`/retention`（工作台总览）、`/retention/samples`、`/retention/products`、`/retention/observations`、`/retention/usage`、`/retention/disposal`；侧栏「留样管理」扩为 6 入口。
- **新增文件**：`RetentionDashboardView / RetentionObservationsView / RetentionUsageView / RetentionDisposalView` 四视图；`styles/retention.scss` 共用布局/状态样式；`src/demo/retentionDemo.ts` 演示数据源与演示角色矩阵；`components/retention/DemoBar`（演示横幅 + 身份切换，驱动角色动作矩阵显隐与 SoD 提示）；登记台账/产品沿用真实 R7A 页并小幅对齐（可用量独立列、临期范围筛选、页头样式统一）。
- **数据口径**：登记台账/产品接真实 R7A API；工作台/观察/使用/处理 4 视图因 R7B/C 后端已实现（演示数据源已切换真实 API），先以演示数据（TEST-HBOS-M2-RET-*）渲染完整 UI 与交互并横幅标注，操作不真实落库；R7B/C 后端落地后将 `retentionDemo` 演示数据源替换为 `retention_service` whitelist。
- **验证与部署**：`vue-tsc` 0 错误；六路由浏览器回归无控制台错误；生产构建 `npm run build:prod`；`docker cp` 同步生产容器 `hbos-m0-r3a-frontend-1`（备份 `【内部备份标识已省略】`，root 清旧 assets 防新旧 hash 残留）；`http://localhost:8080/hbos-lims/` 全部页面与主/视图 bundle HTTP 200。

## 验收清单（Owner 审查点）

- 6 个视图的信息层级与交互是否符合 QC / QA / QM / Analyst 日常操作习惯。
- 页面覆盖登记入库、库存预占、观察计划、使用申请、处理销毁全生命周期。
- 角色动作、SoD 提示、4/5 级审批跳过、N/3 完整性提示是否与方案一致。
- 库存量口径、UOM 只读、全检量 2 倍计算规则是否在原型中有正确体现。
- 是否同意进入 Vue 复刻阶段。

**后续（2026-09-08）R7B/C 后端落地与前端真实接入**：新增 Observation / Usage Apply / Disposal Apply DocType 与 retention_service 全链方法（四步锁 / SoD / 4/5 级 / scheduler / 审计）并真实库验证（R7B 13/13、R7C 19/19、并发确认恰一单成功，离线契约 179/179）；观察/使用/处理/工作台四页已由 `retentionDemo` 演示数据切换为 retention_service whitelist（真实 API 接入，含会话角色 `canAction` 显隐与后端 SoD 约束），演示层移除。具体契约见 `src/api/retention.ts` 与后端 `retention_service.py`。

## 状态同步

本文件状态：REVIEWING。对应更新：

- `docs/CURRENT_MILESTONE.md`
- `docs/PROJECT_STATUS.md`
- `docs/milestones/README.md`
- `README.md`
- `docs/AI_CONTEXT.md`
- `docs/READING_GUIDE.md`

## 状态文件说明

本轮进入 REVIEWING，已同步更新上述状态与公共入口文件。`CLAUDE.md`、`AGENTS.md`、`docs/frontend/FRONTEND_IMPLEMENTATION_GUIDE.md` 未含轮次级阶段描述，无需更新。
