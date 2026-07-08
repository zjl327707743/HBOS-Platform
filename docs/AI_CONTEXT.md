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

当前阶段：M0 工程启动与上下文治理已完成并封板；M0-REMOTE 已完成；M1 已完成 M1-R0 规划收口、M1-R1 对象模型验证收口和 M1-R2 配置试运行方案收口。M1-R3 已执行 HRMS 原生考勤最小测试数据试运行并通过 Codex 审查，但实际结论为 PARTIAL / BLOCKED，最终状态收口为 BLOCKED。M1-R3A 已完成运行态阻断诊断与 TEST 数据隔离 / 清理方案，并已通过 Codex 审查收口为 COMPLETED。M1-R3B 已完成运行态最小修复方案，并已通过 Codex 审查收口为 COMPLETED。M1-R3B-FIX 已通过 Codex 审查并收口为 COMPLETED。M1-R3C 已通过 Codex 审查并收口为 COMPLETED，结论为 PARTIAL / GAP_IDENTIFIED。M1-R3D 已通过 Codex 审查并收口为 COMPLETED，结论为 Gap 四类分类、均不需要立即创建 hb_attendance_app。M1-R3E 已通过 Codex 审查并收口为 COMPLETED。M1-R3F 已通过 Codex 审查并收口为 COMPLETED。M1-REQ-DESIGN-DRAFT 已通过 Codex 审查并收口为 COMPLETED。M1-R4 已通过 Codex 审查并收口为 COMPLETED。M1-R5 已通过 Codex 审查并收口为 COMPLETED。M1-R6A 已通过 Codex 审查并收口为 COMPLETED。

当前目标：M1-R5 已通过 Codex 审查并收口为 COMPLETED。M1-R6A 已通过 Codex 审查并收口为 COMPLETED。M1-R6B/R6C/R7 均为 PLANNED，待用户逐轮授权。当前仍不建议创建 `hb_hr_app`，除非后续经审查确认原生 Workspace / Report 或版本化载体不足并获用户明确授权。

当前已在用户授权范围内安装 HRMS，并完成 Frappe HR 图标、基础 HR 模块和 Roster 页面的前端资源修复验证。M0-R3E HRMS 环境可复现性收口已完成并通过 Codex 审查，M0 整体状态为 COMPLETED。

M0-REMOTE 已完成 GitHub Private remote 创建、`origin` 绑定和 `main` 首次 push。M1-R0 已完成方案和诊断并通过 Codex 独立审查；M1-R1 已完成只读对象模型验证记录，并已通过 Codex 独立审查，状态为 COMPLETED。M1-R2 已完成配置试运行方案设计，并已通过 Codex 独立审查，状态为 COMPLETED。M1-R3 已创建部分 `TEST-HBOS-M1R3-` 虚构测试数据；Codex 审查 PASS 后，M1-R3 最终状态收口为 BLOCKED。M1-R3A 已通过 Codex 审查并收口为 COMPLETED。M1-R3B 已通过 Codex 审查并收口为 COMPLETED。M1-R3B-FIX 已通过 Codex 审查并收口为 COMPLETED。M1-R3C 已新增 `TEST-HBOS-M1R3C-*` 虚构 TEST 数据；M1-R3C 已通过 Codex 审查并收口为 COMPLETED，结论为 PARTIAL / GAP_IDENTIFIED。M1-R3D 已通过 Codex 审查并收口为 COMPLETED。M1-R3E 已通过 Codex 审查并收口为 COMPLETED。M1-R3F 已通过 Codex 审查并收口为 COMPLETED。M1-REQ-DESIGN-DRAFT 为 COMPLETED。M1-R4 为 COMPLETED，已通过 Codex 审查并收口。M1-R5 为 COMPLETED，已通过 Codex 审查并收口。M1-R6A 已通过 Codex 审查并收口为 COMPLETED。M1-R6B/R6C/R7 均为 PLANNED。当前不创建海滨自定义 Frappe App，不开发业务代码，不录入真实业务数据，不接飞书真实写入，不实现 SSO，不做前端驾驶舱，除非用户明确授权对应轮次。

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
2. M1-R6A 已通过 Codex 审查并收口为 COMPLETED；M1-R6B/R6C/R7 均为 PLANNED，待用户逐轮授权。

## 边界提醒

不直接修改 Frappe / ERPNext / HRMS 核心源码。优先使用原生配置、角色权限、DocType、报表、导入、API 和低代码定制。自定义 App 只用于海滨特有规则，不用于重写 HRMS 已有功能。M1 初期不立即创建 `hb_attendance_app`。任何飞书真实写入必须由用户明确授权。

任何海滨自定义 App 生成、业务模型实现、真实业务数据配置、飞书真实写入、前端驾驶舱、AI 视频服务实现，以及 Docker volume 删除、site 重建或环境重构，都属于后续轮次或后续明确授权范围。
