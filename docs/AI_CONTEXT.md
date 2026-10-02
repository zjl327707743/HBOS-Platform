# AI Context

最新事实：PR #21 已完成 FINAL_REVIEW_PASS，并 squash 合入 `feature/hbos-portal-product@e4b16ee80aaaf21aac2304246a4de1f9fe8995ea`。Owner 最新无破坏验收 PASS，团队合成浏览器 final-submit 3/3 PASS，新 squash 四项 CI SUCCESS。旧 #22 已关闭未合并，IAM-0 由 clean Draft PR #23 承接；PR #15 仍 Draft，main 未变化。真实 Owner 凭据、绑定、MFA 与 P1 原卷保持不变。下方 BLOCKED/WAITING 记录仅为合并前历史，不再代表当前 Gate。

## 账号小范围收尾 — 2026-10-01

本轮接续交付基线 `eee1c5e22c57be3436244e77c65e189bd7eee242` 与 PR #21，仅做资料登录渠道、唯一个人导航、折叠偏好说明、飞书头像同步及 C03/C07/C09/F03 缺项补测；不重新全量审计、重画页面或新增账号功能。真实 Administrator 已成功飞书登录为 USER_CONFIRMED_SUCCESS，绑定、密码、MFA、Secret、企业与回调保留。本机沿用既有 P1 Site/Compose/入口，发布分支不合并、不强推、不推 main/base。 补测确认并修复参与页期限遗漏与 GET 回调未提交记录，原矩阵历史保持；最终浏览器新凭据步骤由工具要求人工接手，团队脚本与未执行状态单列。


项目名称：新乡海滨智能运营管理平台。

## 架构定案

准确叫法：Frappe/ERPNext 开源底座 + Frappe 多 App 模块化架构 + 外部独立服务扩展。

长期架构包括：

- Frappe/ERPNext 开源底座
- 海滨自定义 Frappe App
- 外部 AI/视频/算法服务
- Vue/React 驾驶舱
- 飞书集成
- Docker 部署

主技术栈：Frappe Framework、ERPNext、Frappe HR、Python、JavaScript、MariaDB/MySQL 兼容体系、Redis、Docker、Docker Compose、Vue/React、ECharts、FastAPI。

## 当前上下文

本轮账号 UI、统一账号、飞书、Knowledge/Twin 与发布收口已经通过 PR #21 完成并进入产品分支。当前产品 Authority 为 `feature/hbos-portal-product@e4b16ee80aaaf21aac2304246a4de1f9fe8995ea`；Owner 真人飞书基线和浏览器密码生命周期 3/3 均已通过，未执行的真人高风险交接/实体设备项目继续按历史记录保留。公司服务器仍 NOT_DEPLOYED。

当前目标：M1-FIX-B5 为 REVIEWING，等待 Owner 和 Claude 审查。M1-FIX-B3 / B4 不 closeout。M1 产品交付仍未完成，M1-FIX-C/D/E 未启动。LIMS（M2）、仓储（M3）与 Portal 为已授权并行工作线，进度见对应门禁。

当前已在用户授权范围内安装 HRMS，并完成 Frappe HR 图标、基础 HR 模块和 Roster 页面的前端资源修复验证。M0-R3E HRMS 环境可复现性收口已完成并通过 Codex 审查，M0 整体状态为 COMPLETED。

M0-REMOTE 已完成 GitHub Private remote 创建、`origin` 绑定和 `main` 首次 push。M1-R0 已完成方案和诊断并通过 Codex 独立审查；M1-R1 已完成只读对象模型验证记录，并已通过 Codex 独立审查，状态为 COMPLETED。M1-R2 已完成配置试运行方案设计，并已通过 Codex 独立审查，状态为 COMPLETED。M1-R3 已创建部分 `TEST-HBOS-M1R3-` 虚构测试数据；Codex 审查 PASS 后，M1-R3 最终状态收口为 BLOCKED。M1-R3A 已通过 Codex 审查并收口为 COMPLETED。M1-R3B 已通过 Codex 审查并收口为 COMPLETED。M1-R3B-FIX 已通过 Codex 审查并收口为 COMPLETED。M1-R3C 已新增 `TEST-HBOS-M1R3C-*` 虚构 TEST 数据；M1-R3C 已通过 Codex 审查并收口为 COMPLETED，结论为 PARTIAL / GAP_IDENTIFIED。M1-R3D 已通过 Codex 审查并收口为 COMPLETED。M1-R3E 已通过 Codex 审查并收口为 COMPLETED。M1-R3F 已通过 Codex 审查并收口为 COMPLETED。M1-REQ-DESIGN-DRAFT 为 COMPLETED。M1-R4 为 COMPLETED，已通过 Codex 审查并收口。M1-R5 为 COMPLETED，已通过 Codex 审查并收口。M1-R6A 已通过 Codex 审查并收口为 COMPLETED。M1-R6B 为 COMPLETED。M1-R6C 为 COMPLETED（已通过 Codex 审查并 closeout）。M1-R7 为 COMPLETED（已通过 Codex 审查并 closeout）。M1 历史 closeout 已完成，但 Owner UI 验收发现产品功能缺口，因此当前 M1 产品交付仍处于 M1-FIX IN_PROGRESS。M1-FIX-B 已创建轻量 `hb_attendance_app`、导入日志和 `海滨考勤工作台`，并使用 Owner 本地真实 Excel 完成导入闭环验证；M1-FIX-B-FIX 已补齐页面导入与中文体验；M1-FIX-B4 已收敛运行态入口主线；M1-FIX-B5 已核查真实 Employee / Employee Checkin / Attendance / 月度暂存数据链路，新增月度汇总暂存报表并增强 HBOS 报表过滤；真实 Excel、真实员工清单和导入产物不提交 Git。LIMS（M2）、仓储（M3）与 Portal 为已授权并行工作线，进度见对应门禁。当前不接飞书真实写入，不实现 SSO，不做前端驾驶舱，除非用户明确授权对应轮次。
其他业务里程碑以各自已登记主文档为准，本轮不扩大考勤/库存范围。新增代码通过独立净化发布分支交付；私有运行报告、账号、知识和模型不进入新可达对象。

## AI 默认读取规则

默认只读以下文件：

- `CLAUDE.md`
- `AGENTS.md`
- `docs/AI_CONTEXT.md`
- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`

禁止默认递归读取整个 `docs/`。

默认不读取：

- `docs/archive`
- `docs/research`
- `docs/legacy`

每轮任务开始前，必须说明本轮读取了哪些文档。

只有任务明确涉及当前里程碑时，才读取：

- `docs/plans/m0_engineering_bootstrap.md`

只有架构决策变更时，才读取：

- `docs/adr/`

## Skill 路由

本项目通过 `docs/AI技能路由规范.md` 管理不同任务类型对应的 AI skill 使用规则。

当前已确认拥有 / 可用的 skill：

- `superpowers`
- `frontend-design`
- `lark-cli`（飞书官方 CLI 工具，不是统一总 skill）
- `lark-shared`（飞书官方共享基础 skill）
- `lark-*` 官方领域 skills（详见 `docs/AI技能路由规范.md`）

未安装 skill 只能进入候选池，不得直接调用。任何 Agent 在执行开发、审查、前端设计、集成、文档维护前，必须先根据该文件判断本轮应使用的 skill。

## 提交与文档命名

本项目后续 Git 提交描述优先使用中文。可以保留 `docs`、`fix`、`feat`、`chore` 等 conventional commit 前缀，但冒号后的描述应使用中文。

新增文档名称优先使用中文或中英混合命名。技术专有名词可以保留英文，例如 Frappe、Docker、ERPNext、FastAPI、API、Skill。

Skill 路由规范文件为：

- `docs/AI技能路由规范.md`

## 后续路线

后续路线只记录，不代表已启动：

1. M1-R5 已通过 Codex 审查并收口为 COMPLETED，已交付 HRMS 配置基线、考勤工作台入口、月度汇总 Demo 和 Excel 月报导出路径。
2. M1 历史 closeout 已完成，但产品交付仍在 M1-FIX 中，尚未完成。M1-FIX-B3 为 REVIEWING / Owner UI 验收未通过；M1-FIX-B4 为 REVIEWING / Claude PASS，但 Owner 数据链路验收发现后续问题；M1-FIX-B5 为 REVIEWING。LIMS（M2）、仓储（M3）与 Portal 为已授权并行工作线，进度见对应门禁。
2. M1 历史 closeout 已完成，但产品交付仍在 M1-FIX 中，尚未完成。M1-FIX-B3 为 REVIEWING / Owner UI 验收未通过；M1-FIX-B4 为 REVIEWING / Claude PASS，但 Owner 数据链路验收发现后续问题；M1-FIX-B5 为 REVIEWING。库存 M2-STOCK-R1 保持 IN_PROGRESS；其余 M2 轮次不由本任务推进。

## 前端实施流程规范

独立前端（Vue/React 驾驶舱、AI 工作台、复杂交互页面）开发必须遵循"原型先行 + Owner 审查 + 复刻实现 + 功能接入"流程。详见：

- `docs/frontend/FRONTEND_IMPLEMENTATION_GUIDE.md`

核心规则：凡涉及漂亮页面、驾驶舱、AI 工作台、复杂交互页面，必须先使用 `frontend-design` skill 产出原型/视觉方案，Owner 人工审查通过后再进入前端复刻和功能接入。Frappe Desk 后台页面不要强行重做成独立前端。

## 边界提醒

不直接修改 Frappe / ERPNext / HRMS 核心源码。优先使用原生配置、角色权限、DocType、报表、导入、API 和低代码定制。自定义 App 只用于海滨特有规则，不用于重写 HRMS 已有功能。`hb_attendance_app` 已在 M1-FIX-B 经 Owner 授权创建，后续不得擅自扩大为大而全 HR App。任何飞书真实写入必须由用户明确授权。

任何海滨自定义 App 生成、业务模型实现、真实业务数据配置、飞书真实写入、前端驾驶舱、AI 视频服务实现，以及 Docker volume 删除、site 重建或环境重构，都属于后续轮次或后续明确授权范围。


## HBOS Portal 并行工作流（Owner 已授权）

2026-09-24，Owner 已明确授权正式启动 HBOS Workspace / Portal 产品线。

该工作流与既有 Attendance / Inventory / LIMS 治理线并行；Portal 是 Experience Shell，不替代业务 App 的领域 Authority。

Authority：

- 当前开发分支：`m2-r10`（已整合 Portal 产品线与 `codex/portal-review-fixes`）
- Draft PR：#15
- 设计文档：`docs/experience/`
- 前端规范：`docs/frontend/FRONTEND_IMPLEMENTATION_GUIDE.md`
- Portal 前端：`frontend/hbos-portal-web/`
- Portal Platform App：`apps/hbos_portal/`

既有设计 / 实施基线（正式发布进度以 RP3 主记录为准）：

```text
EA-1～EA-4 = BASELINE
EA-5 Owner Visual Gate = APPROVED
EA-5.3 = BASELINE
EA-5.4 = DESIGN ENGINEERING BASELINE
EA-5.5 = COMPLETE / OWNER APPROVED

P2 Portal Skeleton / Bootstrap / Runtime = PASS
P3 Three-App Registry = PASS
P4-F2 LIMS Design Revision = V2 STATIC VISUAL GATE APPROVED / P4-F6-5 READ-ONLY WORKBENCH IMPLEMENTED / AUDIT REMEDIATION VERIFIED / MANAGEMENT V0 GATE CLOSED / REAL RUNTIME EVIDENCE PENDING

LIMS       = entry + summary + tasks + search
Attendance = entry + HR summary
Inventory  = entry + permission-aware summary
```

Inventory Summary 不直接消费现有 raw-SQL 库存报表。Inventory App 先使用当前 Frappe Session 的 permission-aware Warehouse 可见范围，再显式限制 Bin 查询，并只向 Portal 投影计数型指标；不同 UOM 的库存数量不跨物料求和。

Attendance 普通员工个人入口、Attendance / Inventory Tasks 与 Search 仍未开放。

真实 Frappe 模式禁止用 Mock 数据补齐缺失业务能力。Mock 仅用于 UI / Experience 开发。

本地工作台：

```bash
bash scripts/portal/start_local_workspace.sh
```

完整本地运行态验收：

```bash
bash scripts/portal/p3_workspace_runtime_smoke.sh
```

本地 smoke 会验证七个 Site App、三 Provider、Bootstrap、Inventory Summary、三 Stable Route、Administrator Frappe Session 以及 Vite → Frappe API proxy；它不删除 volume、不重建 Site、不写三业务 App 的业务事实。

P4-F0 已完成 LIMS 真实运行审计，报告为 `docs/experience/LIMS_P4-F0_RUNTIME_AUDIT.md`；P4-F2 第一版视觉交付已按 Owner 要求退回，第二版中文优先、双品牌、完整领域和检验员工作流原型位于 `docs/experience/prototypes/lims-p4-f2-v2/`，交付说明为 `docs/experience/LIMS_P4-F2_STATIC_VISUAL_GATE.md`。Owner 已于 2026-09-29 验收通过 Visual Gate，P4-F6 实施计划已交付至 `docs/experience/LIMS_P4-F6_实施计划.md`，P4-F6-0 第二轮确认与适配记录为 `docs/experience/LIMS_P4-F6-0_PROVIDER_ROUTE_核验记录.md`，当前已完成 P4-F6-1 Shell、P4-F6-2 Dashboard V2、P4-F6-3 Task Board V1、P4-F6-4 Result List / Result Entry V1 和 P4-F6-5 Ledger / Audit / COA / Quality Standards / Retention / Stability Read-only V1，稳定性工作台已完成 Mock 运行态预览。两份前端审核报告中的 P0/P1 已完成代码整改，整改记录为 `docs/experience/LIMS_P4-F6-5_前端审核整改记录.md`；交付已提交至 `feature/hbos-portal-product`（`627c3db`），已尝试真实工作台 smoke 但本机缺少 `docker` 命令，真实 Frappe 运行证据仍待环境恢复。真实模式 `/hbos/lims/*` 使用 `LimsLayout`，Sidebar / 移动导航使用稳定链接，假数字移除，统一 `limsCapabilities` 按页面目标和语义能力门控；Dashboard 的专用风险 / 样品 / 分布字段继续保持安全空态，待真实 Provider 契约补齐。样品列表与登记暂不开放，等待独立 Provider 读取 / 登记契约门禁；Desk 后台页面不得为了“好看”被整体重写成独立前端。

Portal 技术栈：Vue 3 + Ant Design Vue + Vue Router + Pinia + Axios；当前稳定性趋势图使用 SVG，没有 ECharts 依赖。

管理后台 V0 门禁：当前没有明确的 LIMS Provider 管理目标、管理 API 或只读投影，因此不发布 `management` capability，不注册前台管理路由，也不跳转 Frappe Desk / 8080。记录见 `docs/experience/LIMS_P4-F6-5_MANAGEMENT_V0门禁记录.md`。

2026-09-30 浏览器运行态整改：Owner 截图对应的 5178 仍是旧 Frappe 模式进程，旧 Bootstrap 与当前源码不一致，导致能力菜单为空；已停止旧进程并以当前源码启动 Mock 预览。LIMS Dashboard V2 现补齐实验室主视觉、中文 Hero、样品条码 / 检验进度、实验室日程、任务态势和按 capability 显示的常用操作。Mock 评审数据只在 Mock 分支存在，真实 Frappe 分支继续不使用 Mock 回退。npm run build、npm run test:contract、lims_shell_contract.sh 和 git diff --check 已通过；真实 Frappe Session 运行证据仍待 Docker/Frappe 工作台恢复。

### Portal 当前审核修复状态 — 2026-10-01

2026-10-01 Portal 审核修复为 **REVIEWING / 本地验证通过，待 Owner 验收及真实 Frappe 运行态证据**：已处理 CSS token、错误态守卫、防抖与过期响应、刷新异常、强类型工作台、共享映射与六页查询逻辑、真实模式原型入口、回跳校验、环境变量与趋势图文档；Ant gzip 442.13 → 255.57 kB。14 项前端回归、构建和两套契约检查通过；临时 Mock 浏览器确认留样/稳定性实际颜色生效。修复提交 `f23ba17` 已从 `codex/portal-review-fixes` 合入 `m2-r10`；后续开发在 `m2-r10` 继续。详细记录见 `docs/experience/LIMS_P4-F6-5_前端审核整改记录.md`。本轮不部署，不关闭样品/管理后台或真实运行态门禁。

## 2026-10-01 Portal 当前基线复核与修补

2026-10-01 在 Owner 指定的 `m2-r10` 完成 Portal 当前基线复核与缺陷修补：显式数据模式/生产构建门禁与演示标识、真实文案、侧栏滚动/768px 导航、登出与会话收敛、动作语义任务计数、结果/任务游标分页、Provider 部分失败与 trace_id、锁文件/npm ci/ESLint/测试与 Mock AST 门禁；34 项回归及 lint、两套契约、Mock 门控、两种显式构建通过。浏览器已确认 1280×720 菜单滚动和 768/767px 导航切换；矮窗口补测被自动审批网络断开阻断，真实 Frappe 联调与 Owner 验收仍待完成。P4-F6-5 保持 REVIEWING，不新建分支、不部署、不推送；巨型视图拆分保留重构项。原 P4-F6-7 报告已保留评审痕迹并标注误报、旧基线和本轮处置。

详细记录：`docs/experience/LIMS_P4-F6-5_前端审核整改记录.md` §8；重新基线：`docs/experience/LIMS_P4-F6-7_前端代码审核报告.md` 顶部复核节。

Portal 最新入口（2026-10-02）：`m2-r10` / 5178 真实 Frappe / 5179 隔离 / 5193 Mock。真实专业菜单、九类只读接口及侧栏已复测；P4-F6-5 仍 REVIEWING，完整真实流程与 Owner 验收待完成，见 `docs/experience/LIMS_P4-F6-5_前端审核整改记录.md` §10。此前 5178 Mock 说明为历史过程，不再作为当前启动依据。
当前推进 RP3 的原账号 Site 确认、部署与真实统一账号验收；其他前端研究不自动启动。必须继续遵守 `docs/frontend/FRONTEND_IMPLEMENTATION_GUIDE.md`：独立前端先做原型 / 视觉方案与 Owner Gate，再实施；Desk 后台页面不得为了“好看”被整体重写成独立前端。

Portal 技术栈：Vue 3 + Ant Design Vue + Vue Router + Pinia + Axios；ECharts 按需使用。

团队通用交付已通过 [PR #21](https://github.com/zjl327707743/HBOS-Platform/pull/21) 合入产品分支；后续团队基线为 `feature/hbos-portal-product@e4b16ee80aaaf21aac2304246a4de1f9fe8995ea`。PR #15/main 仍需独立 Gate。
