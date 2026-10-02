# 新乡海滨智能运营管理平台

当前本地工作分支（2026-10-02）：`m2-r11`。合并冲突检查通过，已修复 CSRF 缓存、旧请求竞态及 LIMS 会话重试问题，升级 Portal / 网关存在已知漏洞的依赖，并补齐回归和 CI 入口。P4-F6-5 保持 **REVIEWING**，本轮未提交、推送或部署；完整真实角色 / 签署流程与 Owner 验收待办。详见[合并后整改记录](docs/experience/LIMS_P4-F6-5_前端审核整改记录.md#11-2026-10-02-m2-r11-合并后检查与问题修复)。下方 PR #21 的 PASS 属于此前产品发布基线，不代替本轮运行态验收。

2026-10-01 产品发布基线：PR #21 已在 FINAL_REVIEW_PASS 后 squash 合入 `feature/hbos-portal-product`，产品 HEAD `e4b16ee80aaaf21aac2304246a4de1f9fe8995ea`。Owner 最新无破坏验收 PASS、浏览器设密/改密/恢复 final-submit 3/3 PASS，新 squash 四项 CI SUCCESS。IAM-0 已由 clean Draft PR #23 承接，旧 #22 已关闭且未合并；PR #15 仍为 Draft，main 未变化。[当前 Gate](docs/milestones/M1_RP3_统一账号飞书绑定与正式发布.md) 记录本轮收口事实。

Frappe/ERPNext 开源底座 + Frappe 多 App 模块化架构 + 外部独立服务扩展。

## 当前交付

当前 M0 已完成并封板。M1 产品交付仍在 M1-FIX 功能补漏中，尚未完成；当前轮次为 **M1-FIX-F（REVIEWING / 两阶段均已上线）**：调休模块——一阶段把飞书调休审批接入并按「加班日提取 → 打卡核实」产出结论（119 条入库、41 已核实 / 53 核实不通过 / 14 解析失败）；二阶段把已核实调休日**接入考勤判定豁免与看板**（不再判缺勤、看板显示「请假（调休）」）。2026-09-24 追加完成名单单一来源收敛（行政班、无菌各收敛为一份）与 PR 审查 5 项修复。M1-FIX-B2 为 COMPLETED；M1-FIX-B3 为 REVIEWING / Owner UI 验收未通过；M1-FIX-B4 为 REVIEWING / Claude PASS，但 Owner 数据链路验收发现后续问题；M1-FIX-B5 为 REVIEWING；M1-FIX-C/D/E 未启动。**M2-STOCK-R1（库存模块隔离）为 IN_PROGRESS**，分支 `m2-stock-r1`，主文档 `docs/milestones/M2_STOCK_R1_库存模块隔离实施记录.md`；LIMS（M2）、仓储（M3）与 Portal 为已授权并行工作线，进度见各阶段门禁及并行记录。
本轮（2026-10-01）接续 PR #21，执行登录账号模块 UI 规范回归与全功能审修。Owner 已亲自确认 Administrator 能通过本人飞书验证并登录，记为 OWNER_CONFIRMED_SUCCESS；历史成员权限待审批或登录失败记录不再代表当前事实。保留真实绑定、密码、MFA、Secret、企业与回调；不要求重复配置。认证页沿用已有 Ant Design Vue / ConfigProvider / typography / tokens，修复表单、证明期限、错误状态、同路由目标与提交结果处理。破坏性、并发与交接只在独立合成 Site 验证。新版本真人 OAuth、本人收到验证码、第二位真人交接与移动软键盘结果单独记录，未执行不写 PASS。复用现有 P1 / Compose / 卷与常用入口，最终本机 SHA/build ID、远端提交、CI 和制品须一致。公司服务器为 NOT_DEPLOYED。主记录：`docs/milestones/M1_RP3_统一账号飞书绑定与正式发布.md`。PR #21 已 squash 合入 `feature/hbos-portal-product@e4b16ee80aaaf21aac2304246a4de1f9fe8995ea`；该轮产品发布以产品分支为基线；本轮本地工作分支已更新为 `m2-r11`。PR #15 仍 Draft，不推 main；IAM 由 Draft PR #23 单独承接。

平台已包含考勤、仓储库存、LIMS、Portal、知识助理与设备/数字孪生自定义 App。密码和飞书使用同一 Frappe User；原有业务权限仍由原 App 约束。业务通知、生成式知识回答、现场遥测、工艺动画及偏好同步尚未实现，具体状态见前端完整性矩阵。安全变更通知单独记录真实发送状态，不能等同业务通知能力完成。

- [项目状态](docs/PROJECT_STATUS.md)
- [当前里程碑](docs/CURRENT_MILESTONE.md)
- [Mac 常用启动与团队同步](docs/deployment/Mac本地运行与团队同步.md)
- [团队部署、备份与回退](docs/deployment/统一账号与Portal正式部署说明.md)
- [前端完整性矩阵](docs/frontend/统一账号发布与前端完整性矩阵.md)

## 团队构建

在已审查的 clean checkout 使用 Node 22 执行 `bash scripts/release/build_bundle.sh`，生成同源 Portal 和 LIMS 编译资产及六 App 部署包。通用 Gateway 位于 `services/hbos_gateway`，依赖、基线与 HRMS commit 见 `scripts/release/依赖版本锁.json`。既有目标版本不得为了匹配基线而降级。

M0 阶段用于约束后续规划、执行、审查与验收。当前已完成 Frappe / ERPNext / Docker 最小环境启动验证、Frappe HR / HRMS 安装验证、HRMS 前端资源修复、M1 考勤一期边界设计、HRMS 环境可复现性收口、GitHub Private remote 首次同步、M1-R0 规划诊断收口、M1-R1 对象模型验证记录、M1-R2 配置试运行方案设计、M1-R3 局部试运行记录、M1-R3A 阻断诊断方案、M1-R3B 运行态最小修复方案、M1-R3B-FIX 运行态最小修复执行记录、M1-R3C 原生考勤最小试运行复测记录、M1-R3D 异常口径与 Gap 诊断、M1-R3E 配置复核与业务口径确认表、M1-R3F 业务口径确认包、M1 需求设计四份文档、M1-R4 Demo 技术方案与实施路线拆分、M1-R5 HRMS 配置基线、考勤工作台与月度汇总 Demo、M1-R6A Gate 判定和 M1-R6B 脱敏打卡流水导入最小验证；M1 产品验收仍在 M1-FIX 中。
升级必须保留已确认原 Site/数据库，先备份并验证恢复，再迁移及核对原账号/角色/权限/业务关联。制品或 PR 不包含账号数据库、Secret、私有知识索引/原文或真实模型；这些经批准私下部署。

## 协作与边界

`AGENTS.md`、`CLAUDE.md` 为规则入口；进度以状态台账与对应里程碑为准。Portal 本轮不改变其他考勤/库存里程碑的 Owner 验收状态。禁止创建未知替代库、覆盖未知数据库、重置原密码/角色、发布凭据或私有资料。

当前已包含 `apps/hb_attendance_app`。该 App 仅用于考勤导入入口、导入日志和 M1-FIX 必需扩展，不代表启动大而全 HR App。

## 主技术栈

- Frappe Framework
- ERPNext
- Frappe HR
- Python
- JavaScript
- MariaDB/MySQL 兼容体系
- Redis
- Docker
- Docker Compose
- Vue/React
- ECharts
- FastAPI

## 长期仓库规划

长期建议按职责拆分仓库，当前仅记录规划，不在未批准轮次创建这些仓库：

- `haibin-hbos-infra`：基础设施、部署、环境编排与运维脚本
- `hb_core_app`：海滨核心主数据、权限、组织与平台扩展
- `hb_attendance_app`：考勤业务扩展
- `hb_feishu_app`：飞书集成扩展
- `hb_production_app`：生产运营扩展
- `hb_quality_app`：质量管理扩展
- `hb_safety_app`：安全管理扩展
- `hb_ai_ops_app`：AI 运营、视频、算法服务对接扩展
- `hbos-dashboard-web`：Vue/React 驾驶舱与大屏前端

## 当前禁止事项

当前 M1-FIX 仍处于功能补漏阶段。继续禁止：

- 未经 Owner 明确授权，不创建新的自定义 Frappe App
- 不创建 `hb_core_app`、`hb_feishu_app`
- 不把 `hb_attendance_app` 扩大为大而全 HR App
- 不把 HRMS 安装验证等同于考勤业务开发完成
- 不提交真实 `.env` 或真实密钥
- 不提交备份文件、数据库、Docker volume 或运行时数据
- 不开发业务
- 不接飞书真实写入
- 不做前端驾驶舱
- 不浏览或搬运大量 Obsidian 长文
- 不执行 `docker compose down -v`
- 不删除 volume
- 不重建 `frontend` site

**独立前端开发规则**：凡涉及独立前端、驾驶舱、AI 工作台、复杂交互页面，必须先完成原型设计/视觉方案，经 Owner 人工审查通过后再进行前端复刻开发，最后接入真实页面功能和数据。详见 `docs/frontend/FRONTEND_IMPLEMENTATION_GUIDE.md`。

后续路线只记录，不代表已启动：

1. M1-R3C 已通过 Codex 审查并收口，试运行完成但业务闭环未完成。
2. M1-R3D 已通过 Codex 审查并收口，Gap 已四类分类，均不需要立即创建 App。
3. M1-R3E 已通过 Codex 审查并收口，配置复核清单与业务口径确认表已交付。
4. M1-R3F 已通过 Codex 审查并收口，业务口径确认包已交付。
5. M1-REQ-DESIGN-DRAFT 已通过 Codex 审查并收口，需求设计四份文档全部完成。
6. M1-R4 已通过 Codex 审查并收口为 COMPLETED；M1-R4 定位为 Demo 技术方案与实施路线拆分，后续 R5/R6/R7 按递进拆分。
7. M1-R5 已通过 Codex 审查并收口为 COMPLETED；本轮定位为 HRMS 配置基线、考勤工作台与月度汇总 Demo，未启动 R6/R7。
8. M1-R6A 已通过 Codex 审查并收口为 COMPLETED；本轮定位为 Excel 导入与异常流程落地方案 / Gate 判定，已 closeout。
9. M1-R6B 已通过 Codex 审查并收口为 COMPLETED；M1-R6C 为 COMPLETED。M1-R7 已通过 Codex 审查并 closeout 为 COMPLETED。
10. M1-FIX-B 已完成 Excel 导入与真实本地数据闭环实现，M1-FIX-B-FIX 已补齐浏览器导入与中文体验修复，M1-FIX-B2 为 COMPLETED，M1-FIX-B3 为 REVIEWING / Owner UI 验收未通过，M1-FIX-B4 为 REVIEWING / Claude PASS 但数据链路验收发现后续问题，M1-FIX-B5 为 REVIEWING。

## AI 协作方式

- ChatGPT：负责规划、拆解、上下文整理与方案边界确认
- Claude：负责按计划执行文档或代码变更
- Codex：负责工程审查、边界检查、验证与交付复核
- 用户：负责最终验收、取舍确认与里程碑放行

每轮任务开始前，AI 必须说明本轮读取了哪些文档。默认只读 `CLAUDE.md`、`AGENTS.md`、`docs/AI_CONTEXT.md`、`docs/PROJECT_STATUS.md`、`docs/CURRENT_MILESTONE.md`，禁止默认递归读取整个 `docs/`。

## 并行产品工作流：HBOS Portal

Owner 已于 2026-09-24 正式授权 HBOS Workspace / Portal 产品线，作为主业务治理线之外的独立并行工作流。

- 当前开发分支：`m2-r11`（Owner 合并后的本地工作分支；此前 `m2-r10` 记录作为历史保留）
- Draft PR：#15
- Experience Architecture：`docs/experience/`
- 实施计划：`docs/plans/HBOS_PORTAL_IMPLEMENTATION_PLAN.md`
- 前端：`frontend/hbos-portal-web/`
- 薄平台 App：`apps/hbos_portal/`
- 技术栈：Vue 3 + Ant Design Vue + Vue Router + Pinia + Axios + Frappe

当前 Portal Gate：

```text
EA-5.5 = COMPLETE / OWNER APPROVED
Typography Contract v2.0 = APPROVED
P1 Platform Architecture = BASELINE
P2 hbos_portal Skeleton = PASS
P2.1 Frontend Bootstrap Adapter = PASS
P2.2 Real Frappe Runtime Smoke = PASS
P3 Three-App Registry = PASS
P4-F2 LIMS Visual Gate = APPROVED
P4-F6-5 LIMS Read-only Workbench = IMPLEMENTED / AUDIT REMEDIATION VERIFIED / MANAGEMENT V0 GATE CLOSED / REAL RUNTIME EVIDENCE PENDING

LIMS       = entry + summary + tasks + search + results + ledger + audit + COA + quality standards + retention + stability read-only workbenches
Attendance = entry + HR summary
Inventory  = entry + permission-aware summary
```

Attendance 普通员工个人端、Attendance / Inventory Tasks 与 Search 仍保持 Gate，不为了首页展示扩大授权或复制领域逻辑。

Portal 本地开发已提供：

```bash
bash scripts/portal/start_local_workspace.sh
bash scripts/portal/p3_workspace_runtime_smoke.sh
```

第一条用于持续启动真实 Frappe 模式 Portal；第二条用于验证三 Provider、Bootstrap、Inventory Summary、三 Stable Route、Frappe Session 和 Vite API proxy。Owner 本机 Isolated Preview 已于 2026-09-25 完成并通过；P3 Local Runtime = PASS。LIMS P4-F0 真实运行审计已于 2026-09-28 完成，P4-F2 第二版视觉原型已按 Owner 要求交付并于 2026-09-29 通过 Owner Visual Gate，P4-F6 实施计划已交付，当前完成 P4-F6-1 Shell、P4-F6-2 Dashboard V2、P4-F6-3 Task Board V1、P4-F6-4 Result List / Result Entry V1 与 P4-F6-5 Ledger / Audit / COA / Quality Standards / Retention / Stability Read-only V1；P4-F6-0 Provider 适配已完成。两份前端审核报告指出的 P0/P1 已完成代码整改并通过 48 项 LIMS、19 项 Portal 契约测试和构建门禁，交付已提交至 `feature/hbos-portal-product`（`627c3db`）；已尝试真实工作台 smoke，但本机缺少 `docker` 命令，真实 Frappe 运行证据仍待环境恢复，整改记录见 `docs/experience/LIMS_P4-F6-5_前端审核整改记录.md`。

2026-09-28 起，本机 5178 Portal 的 LIMS 入口保留在 `/hbos/lims/*` 同源前台路由。真实 Frappe 模式现在使用 LIMS Local Shell，不展示 Mock 业务数据；Sidebar / 移动导航已改为稳定链接并移除假数字，Provider 已补齐 `/ledger` 到当前 native 台账路径的别名。P4-F6-1 已接入双品牌页头、错误态、页面目标能力门控和路由守卫；P4-F6-2 已接入真实 Provider KPI、任务卡、流程条和加载 / 空 / 错误态；P4-F6-3 已接入三种角色任务视图、筛选、URL 上下文和只读键盘导航；P4-F6-4 已接入结果列表、结果录入、冻结限度、签署链和领域写入动作；P4-F6-5 已接入受控结果台账、审计追踪、检验报告、质量标准、留样工作台和稳定性工作台，稳定性覆盖计划、样品、结果、趋势和实验室环境提示，所有新增领域页先保持只读并由 capability 门控。稳定性工作台已完成 Mock 运行态预览；样品列表与登记仍保持同源 pending，等待独立 Provider 读取 / 登记契约门禁通过；本轮同时移除页头管理后台静态入口并修复窄屏搜索提示换行，运行态记录见 `docs/experience/LIMS_P4-F6-5_STABILITY运行态验收记录.md`，样品门禁见 `docs/experience/LIMS_P4-F6-6_样品_PROVIDER契约门禁.md`。设计文档为 `docs/experience/LIMS_P4-F2_SHELL_DASHBOARD_设计方案.md`，第二版原型入口为 `docs/experience/LIMS_P4-F2_STATIC_VISUAL_GATE.md`，审计基线见 `docs/experience/LIMS_P4-F0_RUNTIME_AUDIT.md`，实施计划为 `docs/experience/LIMS_P4-F6_实施计划.md`。

Portal 是 Experience Shell，不替代 Attendance / Inventory / LIMS 的领域 Authority；运行时身份统一使用 Frappe User + Frappe Session。LIMS 管理后台 V0 目前没有明确 Provider 目标，继续保持关闭，不注册前台管理路由或跳转 Frappe Desk / 8080。PR #15 继续保持 Draft，直到三 APP 工作台运行态、本地验收和下一阶段前端强化 Gate 达到可收口状态。

### 2026-09-30 LIMS 5178 浏览器预览整改

已定位 Owner 截图异常：5178 之前运行的是旧的 Frappe 模式预览进程，Bootstrap 与当前源码不一致；当前 Dashboard 也未完整复刻已验收的 LIMS V2 视觉。现已用当前源码重启 5178 Mock 预览，并补齐实验室主视觉、中文检验员 Hero、四项评审指标、检验流程、任务队列、样品条码与进度、实验室日程及常用操作。真实 Frappe 分支仍不使用 Mock 数据补齐业务，正式 Session / Provider 数据待运行环境恢复后验证。构建、前端契约、Shell 契约和 diff 检查已通过。

### Portal 当前审核修复状态 — 2026-10-01

2026-10-01 Portal 审核修复为 **REVIEWING / 本地验证通过，待 Owner 验收及真实 Frappe 运行态证据**：已处理 CSS token、错误态守卫、防抖与过期响应、刷新异常、强类型工作台、共享映射与六页查询逻辑、真实模式原型入口、回跳校验、环境变量与趋势图文档；Ant gzip 442.13 → 255.57 kB。14 项前端回归、构建和两套契约检查通过；临时 Mock 浏览器确认留样/稳定性实际颜色生效。修复提交 `f23ba17` 已从 `codex/portal-review-fixes` 合入 `m2-r10`；后续开发在 `m2-r10` 继续。详细记录见 `docs/experience/LIMS_P4-F6-5_前端审核整改记录.md`。本轮不部署，不关闭样品/管理后台或真实运行态门禁。

## 2026-10-01 Portal 当前基线复核与修补

2026-10-01 在 Owner 指定的 `m2-r10` 完成 Portal 当前基线复核与缺陷修补：显式数据模式/生产构建门禁与演示标识、真实文案、侧栏滚动/768px 导航、登出与会话收敛、动作语义任务计数、结果/任务游标分页、Provider 部分失败与 trace_id、锁文件/npm ci/ESLint/测试与 Mock AST 门禁；34 项回归及 lint、两套契约、Mock 门控、两种显式构建通过。浏览器已确认 1280×720 菜单滚动和 768/767px 导航切换；矮窗口补测被自动审批网络断开阻断，真实 Frappe 联调与 Owner 验收仍待完成。P4-F6-5 保持 REVIEWING，不新建分支、不部署、不推送；巨型视图拆分保留重构项。原 P4-F6-7 报告已保留评审痕迹并标注误报、旧基线和本轮处置。

详细记录：`docs/experience/LIMS_P4-F6-5_前端审核整改记录.md` §8；重新基线：`docs/experience/LIMS_P4-F6-7_前端代码审核报告.md` 顶部复核节。

Portal 最新运行入口（2026-10-02）：5178 为真实 Frappe 开发，5179 为隔离预览，5193 为 Mock。已恢复旧后端进程导致缺失的专业菜单，补齐九类只读接口与真实侧栏证据；P4-F6-5 保持 REVIEWING，完整真实流程和 Owner 验收待完成。详细记录见 `docs/experience/LIMS_P4-F6-5_前端审核整改记录.md` §10。
团队后续 Portal 代码来源：`feature/hbos-portal-product@e4b16ee80aaaf21aac2304246a4de1f9fe8995ea`。PR #21 保留为已合并的审查与发布证据；Mac 本地运行与本人验收分开记录，公司生产尚未部署。
