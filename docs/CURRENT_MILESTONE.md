# Current Milestone

## M1-FIX：M1 考勤一期功能补漏阶段

项目名称：新乡海滨智能运营管理平台。

M1 已 closeout 为 COMPLETED，但 Owner 亲自验收后发现大量产品功能没有真正页面可体验——「方案完成」不等于「功能完成」。M1-FIX 阶段定位为功能补漏，补齐 M1 承诺但未实际可体验的产品功能。

## 当前轮次

M1-FIX-B2：导入口径、安全与准确性修复。当前状态：COMPLETED。已通过 Claude 审查（初审 FAIL → B2-FIX 复审 PASS），Codex closeout 已完成。

M1-FIX-B3：考勤工作台入口、App 命名与 HRMS 数据一致性修复。当前状态：REVIEWING，等待 Claude 审查。

M1-FIX-B4：考勤模块架构收敛与单一入口重整。当前状态：REVIEWING / Claude PASS，但 Owner 数据链路验收发现后续问题。B4 只收敛桌面入口、Workspace、Workspace Sidebar、导入页和 HBOS / HRMS 入口口径；M1-FIX-B3 不 closeout。

M1-FIX-B5：导入数据链路核查与报表口径收敛。当前状态：REVIEWING，等待 Owner 和 Claude 审查。B5 只核查真实 Employee / Checkin / Attendance / 月度暂存链路，收敛 HBOS 报表和 HRMS 技术核查入口；M1-FIX-B3 / B4 不 closeout。

M1-FIX-B-FIX：Excel 导入与中文体验修复。历史轮次；当前后续修复由 M1-FIX-B2、M1-FIX-B3、M1-FIX-B4、M1-FIX-B5 管理。

M1-FIX 后续规划轮次（仅规划，不自动启动）：

| 轮次 | 名称 | 优先级 | 状态 |
| --- | --- | --- | --- |
| M1-FIX-A | 差距盘点与实施方案 | — | REVIEWING |
| M1-FIX-B | Excel 导入与真实本地数据闭环 | P0 | REVIEWING |
| M1-FIX-B-FIX | Excel 导入与中文体验修复 | P0 | REVIEWING |
| M1-FIX-B2 | 导入口径、安全与准确性修复 | P0 | COMPLETED |
| M1-FIX-B3 | 考勤工作台入口、App 命名与 HRMS 数据一致性修复 | P0 | REVIEWING / Owner UI 验收未通过 |
| M1-FIX-B4 | 考勤模块架构收敛与单一入口重整 | P0 | REVIEWING / Claude PASS，Owner 数据链路验收发现后续问题 |
| M1-FIX-B5 | 导入数据链路核查与报表口径收敛 | P0 | REVIEWING |
| M1-FIX-C | 异常说明三级流程 | P1 | PLANNED |
| M1-FIX-D | 考勤工作台 + 月报 + 领导 Demo | P1 | PLANNED |
| M1-FIX-E | 飞书 OAuth 最小验证 + Owner 体验脚本 + 总审查 | P2 | PLANNED |

## M1 历史轮次（已完成）

M1 规划收口已完成；产品交付仍在 M1-FIX 中，尚未完成。全部 19 个历史轮次状态见里程碑索引。

M0 已完成并封板。M0-REMOTE 已完成。

权威状态文件：

- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/milestones/M0.md`

权威方案文件：

- `docs/milestones/M1_FIX_功能补漏实施方案.md`

## 本轮范围

M1-FIX-B / M1-FIX-B-FIX 只做 Excel 导入与真实本地数据闭环修复：

- 创建轻量 `hb_attendance_app`
- 创建导入日志
- 支持 Owner 在 Frappe Desk 页面上传考勤机月度导出表、识别预览、确认导入、查看导入日志与中文结果
- 创建 / 匹配 Employee
- 生成打卡流水
- 尝试 HRMS 原生自动考勤，并在必要时记录本地兜底生成
- 生成考勤结果并展示导入统计、重复跳过说明和失败摘要
- 默认白班/行政班为 08:30-17:30
- 不提交真实 Excel、真实员工清单或导入产物

## 本轮禁止事项

-- 不创建 `hb_core_app`
-- 不创建 `hb_feishu_app`
-- 不创建月度汇总 DocType
-- 不创建异常三级流程 DocType
- 不创建/删除/清理 TEST 数据
- 不接真实考勤机
- 不配置真实飞书密钥
- 不要求 Owner 在聊天中粘贴 App Secret
- 不提交 `.env`、密钥、token、数据库、日志、缓存、运行产物
- 不修改 Frappe/ERPNext/HRMS 核心源码
- 不启动大型 Vue/React 前端
- 不启动 M2
- 不把「计划可行」写成「功能已实现」

## M1-FIX 全阶段禁止事项

- 不创建 `hb_core_app`
- 不修改 Frappe/ERPNext/HRMS 核心源码
- 不提交 `.env`、App Secret、密钥、token
- 不提交真实员工姓名、真实工号、真实数据
- 不提交 Excel/CSV 数据文件
- 不接真实考勤机
- 不部署公司内网/云服务器
- 不启动大型 Vue/React 前端
- 不启动 M2
- 不伪造飞书登录成功
- 不执行 `docker compose down -v`
- 不删除 Docker volume
- 不重建 `frontend` site

## 当前状态口径

```
M1     = IN_PROGRESS（产品交付，M1-FIX 中）
M1-FIX = IN_PROGRESS
M1-FIX-A = REVIEWING
M1-FIX-B = REVIEWING
M1-FIX-B-FIX = REVIEWING
M1-FIX-B2 = COMPLETED
M1-FIX-B3 = REVIEWING / Owner UI 验收未通过
M1-FIX-B4 = REVIEWING / Claude PASS，Owner 数据链路验收发现后续问题
M1-FIX-B5 = REVIEWING
M2     = NOT STARTED / WAITING OWNER AUTHORIZATION
```

## 下一轮预告

M1-FIX-B5 已进入 REVIEWING，等待 Owner 和 Claude 审查。M1-FIX-B3 / B4 不 closeout。M1-FIX-C（异常说明三级流程）为 PLANNED / 待 Owner 授权。M1-FIX-D/E 与 M2 均未启动。


## 并行产品工作流：HBOS Portal

Owner 已于 2026-09-24 明确授权 HBOS Portal 独立并行启动。

该授权不改变本文件顶部的 M1-FIX 主里程碑。

Portal 当前状态：

```text
EA-1 ~ EA-4 = BASELINE
EA-5 Owner Visual Gate = APPROVED
EA-5.3 = BASELINE
EA-5.4 = DESIGN ENGINEERING BASELINE
EA-5.5 = COMPLETE / OWNER APPROVED
P4-F6-5 = REVIEWING / 2026-10-01 LOCAL FIX VERIFICATION PASS
REAL Frappe RUNTIME / OWNER ACCEPTANCE = PENDING
```

正式工作分支：`feature/hbos-portal-product`。

当前允许范围为已批准的 Portal/LIMS 前端审核修复和验证。`apps/hbos_portal` 与三业务 Provider 已存在；本轮不创建 App、不改业务 Authority、不进入新的能力门禁。下文按日期记录历史 Gate 推进，当前状态以最新记录为准。


### Portal Phase B 更新

```text
Phase B — Vue Portal Skeleton
= SOURCE INITIALIZED / BUILD VERIFICATION PENDING
```

已在 `frontend/hbos-portal-web/` 初始化经 Owner 批准视觉母版的 Vue 3 + Ant Design Vue 工程骨架。

本轮仍属于“前端复刻”，没有进入“真实功能接入”。

下一 Gate 保持：

```text
EA-5.5 Interaction QA + Responsive + Accessibility
```

在 build Gate 和 EA-5.5 通过前，不创建 `apps/hbos_portal`。


### EA-5.5 已启动

Portal 并行工作流当前更新为：

```text
EA-5.4 = DESIGN ENGINEERING BASELINE
Vue Portal Skeleton = BUILD PASS
EA-5.5 = IN_PROGRESS
```

EA-5.5 当前只做交互、响应式、可访问性和 LIMS V1 Operational Page 验证，不进入真实 API 功能接入。


### Portal EA-5.5 Gate

```text
EA-5.5 Implementation = PASS
HBOS Quality Gate = PASS
Portal Frontend Build Gate = PASS
Owner Product Review = PENDING
```

在 Owner Review 前，EA-5.5 不标记 COMPLETE，不进入真实 Provider / backend implementation。


### Portal Gate Update — 2026-09-25

EA-5.5 已通过 Owner 验收并收口。

下一允许范围：

- P1 `hbos_portal` Platform App Architecture；
- App Registry / Bootstrap / Session / Access / Provider Discovery 设计；
- 不改变 Attendance / Inventory / LIMS 领域 Authority；
- P1 架构收口前不引入业务事实副本。


### Portal P1 Architecture Gate — 2026-09-25

`docs/experience/P1_HBOS_Portal平台App架构.md` 已形成架构基线。

下一允许范围：P2 `apps/hbos_portal` skeleton；不接三业务 APP Provider，不创建业务事实 DocType。


### Portal P2 Gate Update — 2026-09-25

- `apps/hbos_portal` skeleton 已创建；
- Portal Backend Gate = PASS；
- Vue Frappe Bootstrap Adapter = PASS；
- 下一 Gate = P2.2 Runtime Smoke Test；
- 尚未接三业务 APP Provider。


### Portal P2.2 Runtime Gate — 2026-09-25

```text
P2.2 Runtime Smoke Test = PASS
P3 Business App Registration = NEXT
```

Runtime 使用独立 Portal worktree + 临时 Compose override，正式 `main` Attendance 工作区未 switch / stash / reset / clean。

验证完成后：

- `hbos_portal` 已安全卸载；
- site app list 恢复 baseline；
- 28 个 Docker volume 名称保持一致；
- Attendance bind mount 恢复正式工作区；
- 业务数据未改变。

Attendance hook import warning 为非阻断观察项，留在 Attendance Authority 下后续处理。


### Portal P3-LIMS-1 Gate — 2026-09-25

```text
P3 Business App Registration = IN_PROGRESS
P3-LIMS-1 First Real Provider = COMPLETE
P3-LIMS-2 Stable Deep-link Adapter = NEXT
```

Runtime clean-site 已真实验证 Frappe Hook → Portal Registry → LIMS Access → Bootstrap，且没有开启业务数据 capability。

同轮 Attendance G1 与 LIMS → Inventory release integration 继续 PASS。


### Portal P3-LIMS-2 / P3-LIMS-3 Closeout — 2026-09-25

Portal 分支已先同步最新 `main`（含已合并 PR #20 的 LIMS production-entry 修复），同步后保持：

- LIMS `/hbos-lims/*` 正式入口与持久静态资源能力；
- `hbos_portal_provider` 动态 Provider discovery；
- `hbos_portal` Runtime mount / Registry；
- 三业务 App 原有联合门禁。

P3 当前状态：

```text
P3 Business App Registration = IN_PROGRESS
P3-LIMS-1 Manifest / Access / Registration = COMPLETE
P3-LIMS-2 Stable Deep-link Adapter = COMPLETE / RUNTIME PASS
P3-LIMS-3 My Work Projection = COMPLETE / RUNTIME PASS
P3-LIMS-4 Summary Projection = NEXT
P3-LIMS-5 Search Provider = PLANNED
```

LIMS manifest 当前只开放：

```json
["tasks"]
```

Summary / Search 仍未开放。

P3-LIMS-2 已建立 LIMS internal route → stable `/hbos/lims/...` → current `/hbos-lims/...` 的双向适配，并保持 `hbos_portal` 不静态 import LIMS。

P3-LIMS-3 已复用现有 `todo_service.get_my_todos()` 输出 Unified Task DTO，Portal 不创建第二套 Todo，不持有业务状态，不执行 LIMS 业务动作。

最终 Runtime：

```text
Portal Backend Gate = PASS
Portal Frontend Gate = PASS
HBOS Quality Gate = PASS
Platform Integration Gate run 36042393976 = SUCCESS
HBOS PLATFORM clean-site integration = PASS
```

clean-site 已验证 `lims_manifest_capabilities=["tasks"]`、Stable Route、LIMS task provider 调用、LIMS + Inventory release chain 与 LIMS production entry 共存。


### Portal P3-LIMS-4 / P3-LIMS-5 Closeout — 2026-09-25

LIMS 首个完整 Application Provider experience contract 已完成：

```text
P3-LIMS-1 Manifest / Access / Registration = COMPLETE
P3-LIMS-2 Stable Deep-link Adapter = COMPLETE / RUNTIME PASS
P3-LIMS-3 My Work Projection = COMPLETE / RUNTIME PASS
P3-LIMS-4 Summary Projection = COMPLETE / RUNTIME PASS
P3-LIMS-5 Search Provider = COMPLETE / RUNTIME PASS
```

最终 LIMS manifest：

```json
["summary", "tasks", "search"]
```

最新 clean-site authority：

```text
Head = 7cc1804e4d484feef221ba8b513ec07f036af281
Platform Integration Gate run 36045590049 = SUCCESS
HBOS PLATFORM clean-site integration = PASS
```

Portal 当前下一 Gate：

```text
P3-ATT-1 — Attendance Manifest / Access / Stable Entry
```


### Portal P3 — Three-App Registry Baseline — 2026-09-25

三大业务 APP 已同时进入 Portal Registry：

```text
LIMS
  Manifest / Access / Stable Route = COMPLETE
  Tasks = COMPLETE
  Summary = COMPLETE
  Search = COMPLETE

Attendance
  Manifest / Access / Stable Route = COMPLETE
  HR Summary = COMPLETE
  Tasks / Search = GATED
  Ordinary Employee Portal Access = GATED

Inventory
  Manifest / Access / Stable Route = COMPLETE
  Permission-aware Summary = COMPLETE / RUNTIME PASS
  Tasks / Search = GATED
```

三 APP clean-site Registry authority：

```text
registry_entries = ["attendance", "inventory", "lims"]
registry_failures = 0
bootstrap_apps = ["attendance", "inventory", "lims"]
```

Inventory registration Gate：

```text
run 36048253825 = SUCCESS
```

最新真实数据硬化 HEAD：

```text
f6267baf44813c5b89f83adfe744d8f0192d03bb
```

该版本：
- Frappe mode 不再展示原型期 12/12、7 apps、SAMPLE-001、Digital Twin LIVE 等演示数据；
- 没有 Provider 的模块直接隐藏；
- 多 APP Summary 采用 round-robin 选择，避免一个 APP 独占 Hero 四个指标。

最新 Platform Integration Gate `36048726221` = SUCCESS。

P3 下一阶段从“注册 APP”转为“逐 App 数据能力深化”。


### Portal P3-INV-2 — Inventory Permission-aware Summary — 2026-09-25

状态：**COMPLETE / RUNTIME PASS**。

```text
Inventory manifest = ["summary"]
Inventory Summary metrics = 4
Stable Route = /hbos/inventory -> /app/hbos-photo-intake
Raw-SQL report reuse = NONE
Cross-UOM quantity aggregation = NONE
```

权限链：

```text
Frappe Session
  -> permission-aware visible Warehouse
  -> Bin explicitly scoped to visible Warehouse
  -> Inventory semantic projection
  -> Portal dispatcher
```

Runtime authority：

```text
Inventory real-site first pass:
  Head 3c6f1d5f54a5795d4a7b1ed486c8ce32c64ea7e4
  Platform run 36082817979 = SUCCESS

Portal dispatcher / strict three-app code authority:
  Head ea15676af42e14c2eb47bd65fa402481693b0cac
  Platform run 36083304003
  Three-app clean-site integration step = SUCCESS
```

本地运行工具已加入：

```text
scripts/portal/start_local_workspace.sh
scripts/portal/p3_workspace_runtime_smoke.sh
```

下一 Gate：

```text
Owner local P3 workspace smoke
    ->
P4-F0 real runtime screenshot / journey baseline
    ->
three-app frontend strengthening audit / prototype
```


### Portal P3 Local Isolated Preview Closeout — 2026-09-25

状态：**PASS / P3 RUNTIME CLOSEOUT / P4-F0 READY**。

Owner 本机隔离预览最终通过：

```text
Runtime authority = a6411fadaeccf644a47ffbf93595d00ce9e5b04b
Docker project    = hbos-portal-preview
Preview Site      = portal-preview.localhost
Portal            = http://127.0.0.1:5179
Frappe            = http://127.0.0.1:18091
```

验证完成：

```text
Portal Home                       PASS
App Center                        PASS
My Work                           PASS
Attendance Portal Navigation      PASS
Inventory Portal Navigation       PASS
LIMS Portal Navigation            PASS
Portal native /hbos routes        PASS
Frappe Session across navigation  PASS
Inventory Summary                 PASS
Three-App Registry                PASS
New anonymous volumes             0
Formal workspace                  PRESERVED
Formal Docker runtime             PRESERVED
Formal volumes                    PRESERVED
Formal frontend Site              PRESERVED
```

最终实际落地点：

```text
Attendance -> http://127.0.0.1:18091/desk/hbos-attendance-dashboard
Inventory  -> http://127.0.0.1:18091/desk/hbos-photo-intake
LIMS       -> http://127.0.0.1:18091/hbos-lims/dashboard
```

因此：

```text
P3 Three-App Workspace Integration = COMPLETE / LOCAL + REMOTE RUNTIME PASS
P4-F0 Runtime Screenshot / Journey Baseline = READY
```

P4 开始后仍执行前端 Gate：真实页面审计 → 原型 / 视觉方案 → Owner 审查 → 单 App 实施，不允许三个 App 同时直接大规模改代码。


### Portal LIMS 当前入口过渡 — 2026-09-28

上方 2026-09-25 的 18091 落地点是 P3 隔离预览的历史验收记录。按 Owner 最新要求，本机 5178 Portal 点击 LIMS 后使用同源 `/hbos/lims/*` 前台路由，不再从 Portal 直接跳转到 8080 的 LIMS 页面。真实 Frappe 模式暂显示「前台页面待设计」，不展示 Mock 业务数据；点击时由后端路由解析校验访问权限，直接打开 URL 时由权限过滤后的 Bootstrap App 清单校验。Owner 已提供 LIMS 前端规范，P4-F0 审计已完成，完整实现仍等待 P4-F2 原型和 Owner Gate。

### Portal LIMS P4-F0 审计收口 — 2026-09-28

状态：**P4-F0 COMPLETE / AUDIT DELIVERED / P4-F2 NEXT**。

已完成 LIMS P4-F0 真实运行截图和关键旅程审计，覆盖 Portal 同源入口、Native LIMS Dashboard、任务板、结果清单、结果录入/复核、结果台账、样品登记、空态与权限错误态。审计报告为 `docs/experience/LIMS_P4-F0_RUNTIME_AUDIT.md`。本轮保持只读，不改 LIMS 业务流程、权限或页面实现。

截图已在 Codex 浏览器工具中逐张采集并检查；当前工具不能将截图字节落盘，1440/1280/768/390 的持久化截图证据需在 Owner Review 前补存。下一步进入 P4-F2：LIMS Shell 与 Dashboard / Operational 页面原型及视觉方案；Owner Gate 通过后才可实现。

### Portal LIMS P4-F2 设计方案 — 2026-09-29

状态：**P4-F6-5 READ-ONLY WORKBENCH IMPLEMENTED / AUDIT REMEDIATION VERIFIED / MANAGEMENT V0 GATE CLOSED / REAL RUNTIME EVIDENCE PENDING**。

已按 Owner 确认的方案 A 完成 LIMS 前台设计规格与文字原型：

- Portal Global Header + LIMS Local Navigation 的 Shell 边界；
- Dashboard V2 的四项 KPI、超期 / OOS 风险、最近样品和图表文本摘要；
- Task Board、Result List / Entry、Sample Registration、Result Ledger 的 V1 页面结构；
- 1440 / 1280 / 768 / 390 响应式规则；
- loading、empty、error、permission、session expired 和提交中状态；
- HBOS token、LIMS emerald / cyan 领域色、组件和数据权限边界。

方案文档为 `docs/experience/LIMS_P4-F2_SHELL_DASHBOARD_设计方案.md`。本轮补齐了 R1–R11 条件，并完成 R1 / R2 / R6 的入口安全修复：真实模式切换到 `LimsLayout`、Sidebar 与移动导航改为稳定链接、假数字移除、入口按已实现页面目标门控；LIMS Provider 将 `/hbos/lims/ledger` 映射到当前 `/hbos-lims/results/ledger`，并补齐 Native deep link 回投稳定路径的别名，任务导航使用 `view` 查询语义。契约回归脚本为 `scripts/portal/lims_shell_contract.sh`，Provider 路由契约测试已通过。Owner 已通过 IA / Interaction Review，并于 2026-09-29 验收通过第二版 Visual Gate；第一版静态视觉交付已按要求退回，第二版中文优先、双品牌、完整领域与检验员工作流原型已交付至 `docs/experience/prototypes/lims-p4-f2-v2/`，说明和清单在 `docs/experience/LIMS_P4-F2_STATIC_VISUAL_GATE.md`。P4-F6 实施计划已交付至 `docs/experience/LIMS_P4-F6_实施计划.md`，P4-F6-0 第二轮确认与 Provider 适配记录见 `docs/experience/LIMS_P4-F6-0_PROVIDER_ROUTE_核验记录.md`：领域状态、KPI 语义、任务视图方向、结果写入和审计读取边界已由现有工作流、服务和 158 项通过、1 项跳过的测试确认，Provider summary / tasks / results / ledger / audit / coa / specifications / retains / stability 适配已完成；P4-F6-1 已接入双品牌、Shell 错误态和路由守卫，P4-F6-2 已接入四项 KPI、任务卡、流程条和加载 / 空 / 错误态，P4-F6-3 已接入三种任务视图、筛选、URL 上下文和键盘导航，P4-F6-4 已接入结果列表、结果录入、复核深链和领域写入动作，P4-F6-5 已接入受控结果台账、审计追踪、检验报告、质量标准、留样和稳定性工作台只读视图；管理后台 V0 因缺少明确 Provider 目标保持关闭，不注册前台管理路由、不跳转 Frappe Desk 或 8080；留样与稳定性操作仍保持领域服务边界，真实 Frappe 集成证据和 Dashboard 专用字段仍待补齐。

### Portal LIMS P4-F6-5 稳定性运行态预览 — 2026-09-30

状态：**RUNTIME PREVIEW VERIFIED / OWNER REVIEW NEXT**。稳定性工作台、计划、样品入箱台账、稳定性结果和趋势分析已在 Mock Vite 运行态逐页核验，1440 / 1280 / 768 / 390 四档响应式、结果详情只读抽屉和 18 条已实现同源路由均已验证，记录见 [`LIMS_P4-F6-5_STABILITY运行态验收记录.md`](./experience/LIMS_P4-F6-5_STABILITY运行态验收记录.md)。本轮移除了 Global Header 中未受 capability 约束的管理后台菜单，修复窄屏搜索提示竖向换行，并在 Portal 根配置统一中文 locale；契约脚本、Portal build 和全部 48 项 LIMS Portal Provider / 投影测试通过。样品列表与登记仍保持同源 pending，Provider 契约门禁见 [`LIMS_P4-F6-6_样品_PROVIDER契约门禁.md`](./experience/LIMS_P4-F6-6_样品_PROVIDER契约门禁.md)。真实 Frappe Session 与四档持久化截图仍待 Owner Review 前补齐，管理后台 V0 继续关闭。

### Portal LIMS P4-F6-5 前端审核整改 — 2026-09-30

状态：**P0/P1 AUDIT REMEDIATION VERIFIED / REAL Frappe RUNTIME EVIDENCE PENDING**。两份前端审核报告已逐条复核并完成整改：稳定性上限与错误封装、真实模式 Mock 汇总泄漏、`ok:false` 传播、401/403 会话语义、LIMS 语义能力门控、投影查询上限、孤儿页面和管理后台死入口均已处理；结果页桌面 `8:4`、任务 URL `view` 筛选、1280/768/390 响应式和路由 code-splitting 已对齐。48 项 LIMS 契约测试、19 项 Portal API 契约测试、`lims_shell_contract.sh`、`npm run test:contract`、Portal 构建和 `git diff --check` 均通过；语义能力还已加入真实 Frappe integration check。`npm run test:contract` 属于源码级正则防回归检查，不等同于运行时行为测试。交付已提交至 `feature/hbos-portal-product`（`627c3db`）。已尝试执行 `scripts/portal/p3_workspace_runtime_smoke.sh`，但本机缺少 `docker` 命令，在启动 Compose 前退出；真实 Session 运行态仍待具备 Docker/Frappe 工作台的环境验证。详细记录见 [`LIMS_P4-F6-5_前端审核整改记录.md`](./experience/LIMS_P4-F6-5_前端审核整改记录.md)。

### Portal LIMS P4-F6-6 样品 Provider 契约门禁 — 2026-09-30

状态：**CONTRACT GATE / BLOCKED ON PROVIDER CONTRACT**。`/hbos/lims/samples` 与 `/hbos/lims/samples/new` 继续由同源 `LimsPendingView` 承接，不显示固定样品事实、不新增前端直连 DocType、不跳转 8080。现有 `get_result_ledger` 与 `register_sample` 仅作为受后端保护的领域服务，尚未形成可独立审查的样品读取 / 登记 Provider 能力。本轮新增 `test_portal_samples_gate.py`，与管理后台门禁、Provider 路由测试合计 28 项通过，并在门禁文档中补充了 Provider 契约草案和 Owner 逐项签署清单。下一步先由 Provider Owner 确认列表、详情、登记 DTO、`lims.samples.read` / `lims.samples.register` 能力拆分、权限 SoD、审计签署和稳定路由投影，再决定开放只读列表与登记写操作。门禁记录见 [`LIMS_P4-F6-6_样品_PROVIDER契约门禁.md`](./experience/LIMS_P4-F6-6_样品_PROVIDER契约门禁.md)。

### Portal LIMS P4-F6-2 浏览器运行态整改 — 2026-09-30

状态：**MOCK PREVIEW VERIFIED / DASHBOARD V2 VISUAL PARITY IMPROVED / REAL FRAPPE EVIDENCE PENDING**。

已停止 5178 上的旧 Frappe/Vite 预览进程，并以当前源码启动 Mock 预览；Dashboard V2 已补齐实验室主视觉、中文检验员 Hero、四项 Mock 评审指标、检验流程、任务队列、样品条码与进度、实验室日程和按 capability 显示的常用操作。真实模式仍只消费 Provider 数据，未把 Mock 数据补入真实页面。Portal 构建、前端契约、Shell 契约和 diff 检查均通过；真实 Frappe Session 与正式数据仍待 Docker/Frappe 工作台恢复。

### Portal P4-F6-5 审核修复复核 — 2026-10-01

2026-10-01 Portal 审核修复为 **REVIEWING / 本地验证通过，待 Owner 验收及真实 Frappe 运行态证据**：已处理 CSS token、错误态守卫、防抖与过期响应、刷新异常、强类型工作台、共享映射与六页查询逻辑、真实模式原型入口、回跳校验、环境变量与趋势图文档；Ant gzip 442.13 → 255.57 kB。14 项前端回归、构建和两套契约检查通过；临时 Mock 浏览器确认留样/稳定性实际颜色生效。修复分支 `codex/portal-review-fixes`，详细记录见 `docs/experience/LIMS_P4-F6-5_前端审核整改记录.md`。本轮不部署，不关闭样品/管理后台或真实运行态门禁。
