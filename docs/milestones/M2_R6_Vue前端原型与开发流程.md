# M2-R6：Vue 前端原型与开发流程

项目名称：新乡海滨智能运营管理平台。

## 轮次状态

状态：REVIEWING（等待 Owner 审查；未进入前端复刻）。

## 本轮目标

- 结合《海滨药业LIMS系统开发方案》与 `hb_lims_app` 实际业务闭环，产出 HBOS LIMS 独立 Vue 前端的原型设计与开发流程。
- 覆盖 7 个核心视图：工作台总览、样品登记、待检任务看板、结果录入、COA 报告、质量标准库、审计追踪查询。
- 明确前端实施 Gate：原型 / 视觉方案 → Owner 审查 → 工程初始化 → 页面复刻 → 功能接入 → 联调验收。

## 交付内容

- `docs/frontend/M2_LIMS_Vue前端原型.html`：交互式 HTML 原型，演示数据一律 `TEST-HBOS-M2-*` 前缀，覆盖桌面与移动端。
- `docs/frontend/M2_LIMS_Vue前端开发流程.md`：定位边界、强制 Gate、技术选型、页面清单与信息架构、视觉方案、组件拆分、API 契约映射、风险与待确认项。
- 本地渲染验证：桌面与移动端截图位于临时目录（`/tmp/hbos_lims_desktop.png`、`/tmp/hbos_lims_mobile.png`），仅用于本轮验证，不入库。

### 设计关键点

| 项 | 结论 |
| --- | --- |
| 技术栈 | Vue 3 + Vite + TypeScript + Pinia + Vue Router + Element Plus + ECharts（与 FRONTEND_IMPLEMENTATION_GUIDE 的 Vue 首选一致） |
| 定位 | 独立展示与交互层，不替换 Frappe Desk 后台，不绕过 Frappe 权限，不直接访问数据库 |
| API 边界 | 复用 `hb_lims_app.hbos_lims.lims_service` 现有 whitelist 方法（register_sample / generate_tasks / assign_task / start_task / submit_result / review_result / approve_result / revise_result / create_coa / review_coa / publish_coa / release_sample / reject_sample）与 5 个 Script Report |
| 数据 | 全部虚构 `TEST-HBOS-M2-*`，无真实样品 / 人员 / 检测数据 |
| Skill | `frontend-design` skill 当前环境不可用，按项目规则进行等价人工设计；未虚构 skill 能力，未改变架构路线 |

### 视觉与交互

- 制药实验室风格：洁净、严谨、信息密度适中，状态语义明确。
- 色彩 Token、字体与间距体系、响应式断点已在开发流程文档第 5 节固化。
- 关键交互：规格自动匹配并冻结快照、任务看板状态流转、结果公式计算与自动判定预览、电子签名三段条、修订原因必填、COA PDF 预览、审计只读查询。

## Owner 审查项

- 信息层级是否符合实验室角色日常操作习惯。
- 工作台 / 看板 / 结果录入 / COA 是否覆盖真实闭环路径。
- 视觉语言是否体现 GMP 合规与制药实验室专业感。
- 组件库选型与 Vue 3 技术栈是否一致。
- 原型是否严格对应 `hb_lims_app` 现有数据与权限边界。

## Gate 状态

- 当前停留在“原型 / 视觉方案”阶段，状态 REVIEWING。
- 未创建 Vue 工程，未写前端代码，未接真实 API。
- Owner 审查通过后才可进入工程初始化与页面复刻；未通过则回到原型阶段修改，不得跳过。

## 本轮未做

- 未创建 Vue 工程 / 未初始化 `frontend/hbos-lims-web`。
- 未修改 `hb_lims_app` 代码、未新增 DocType / 业务方法。
- 未修改 Frappe / ERPNext / HRMS 核心源码。
- 未接真实仪器、未录入真实样品 / 人员 / 检测数据。
- 未提交 `.env`、密钥、Excel / CSV、数据库或运行时产物。

## 台账与入口检查

- 状态台账：已更新 `docs/PROJECT_STATUS.md`、`docs/CURRENT_MILESTONE.md`、`docs/milestones/README.md`、`docs/milestones/M2_LIMS_总方案与轮次拆分.md`。
- 公共入口文件：`README.md`、`CLAUDE.md`、`AGENTS.md`、`docs/AI_CONTEXT.md`、`docs/READING_GUIDE.md` 已检查并同步本轮状态。
- 阶段门禁：`docs/milestones/M2_START_GATE.md` 已检查，独立前端规则与 MVP 边界未变。

## 下一步

Owner 审查原型；通过后按开发流程执行工程初始化（Vue 3 + Vite + TypeScript）与页面复刻，再进入功能接入。M2-R5 验证收口与 M2-R6 原型审查并行，均不阻塞对方。
