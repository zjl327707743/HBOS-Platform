# AI Context

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

本轮 Portal 接续固定 Mac 环境，修复真实飞书成员拒绝，交付首次自动开户、拼音登录名及受控换绑/交接。状态 LOCAL_RUNNING / ACCOUNT_CHANGE_UPDATED / LIVE_MEMBER_PERMISSION_PENDING；Secret 与程序企业确认已完成，成员受雇信息权限已提交待审批。真人 OAuth、开户、查收验证码、恢复和交接独立验收。复用 P1 Site、Compose project、原卷、已批准知识/设备及 PR #21 最新代码；不重建、不清库、不重做模块。Owner 已批准当前 Site 的 Administrator 自助绑定许可与本人主动请求的收件验证码，仍须密码、已有 MFA、真实授权及明确确认。公司服务器与正式 HTTPS 继续留后续。主记录：`docs/milestones/M1_RP3_统一账号飞书绑定与正式发布.md`；常用说明：`docs/deployment/Mac本地运行与团队同步.md`。PR #21 的 base 为 `feature/hbos-portal-product`，head 为 `codex/portal-unified-account-release`；不强推、不合并、不推 main/base。

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

- 分支：`feature/hbos-portal-product`
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

当前推进 RP3 的原账号 Site 确认、部署与真实统一账号验收；其他前端研究不自动启动。必须继续遵守 `docs/frontend/FRONTEND_IMPLEMENTATION_GUIDE.md`：独立前端先做原型 / 视觉方案与 Owner Gate，再实施；Desk 后台页面不得为了“好看”被整体重写成独立前端。

Portal 技术栈：Vue 3 + Ant Design Vue + Vue Router + Pinia + Axios；ECharts 按需使用。

团队通用交付已发布至 [PR #21](https://github.com/zjl327707743/HBOS-Platform/pull/21)（Draft、未合并），原账号 Site/HTTPS/本人授权验收仍为未放行。
