# Reading Guide

本指南用于限制 AI 在新乡海滨智能运营管理平台中的默认阅读范围，避免上下文膨胀和误读旧资料。

## 默认读取文件

每轮任务默认只读：

- `CLAUDE.md`
- `AGENTS.md`
- `docs/AI_CONTEXT.md`
- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`

每轮任务开始前必须说明读取了哪些文档。

## 禁止默认递归读取

禁止默认递归读取整个 `docs/`。

默认不读取以下目录：

- `docs/archive`
- `docs/research`
- `docs/legacy`

除非用户明确要求，否则不要浏览或搬运大量 Obsidian 长文。

## 公共入口文件收尾检查规则

默认读取规则不变。

每轮收尾审查可读取以下公共入口文件：

- `README.md`
- `CLAUDE.md`
- `AGENTS.md`
- `docs/AI_CONTEXT.md`
- `docs/READING_GUIDE.md`
- `docs/frontend/FRONTEND_IMPLEMENTATION_GUIDE.md`（仅前端相关轮次）

此外，每轮收尾还必须检查：

- 当前阶段门禁文档：M1 阶段为 `docs/milestones/M1_START_GATE.md`，未来 M2/M3 阶段分别为 `docs/milestones/M2_START_GATE.md`、`docs/milestones/M3_START_GATE.md`。阶段门禁文档用于记录当前阶段的目标、边界、门禁、子轮次状态和下一步路线。
- 当前轮次主文档：指本轮实际交付的 `docs/milestones/Mx_Ry_*.md` 文档，例如 `docs/milestones/M1_R3F_业务口径确认包.md`。每轮进入 REVIEWING 或 closeout 时，必须同步更新该轮次主文档状态。

这些文件不一定每轮修改，但必须检查是否存在过期阶段描述。检查公共入口文件不等于允许递归读取整个 `docs/`。

## 条件读取规则

只有任务明确涉及当前里程碑时，才读取：

- `docs/plans/m0_engineering_bootstrap.md`

只有任务涉及独立前端开发、驾驶舱、AI 工作台或复杂交互页面时，才读取：

- `docs/frontend/FRONTEND_IMPLEMENTATION_GUIDE.md`

## 里程碑文件读取规则

- 默认不全量读取 `docs/milestones/`。
- 当前里程碑任务可读取对应文件，例如 M0 任务读取 `docs/milestones/M0.md`。
- `docs/milestones/README.md` 可作为里程碑索引读取。
- 每轮任务收尾时，如项目状态、当前轮次或里程碑状态发生变化，必须同步更新对应里程碑文件。

M0 历史任务曾允许读取：

- `docs/plans/M0-R2_Frappe_Docker最小环境方案设计.md`
- `docs/deployment/Frappe_Docker最小部署设计.md`
- `docs/deployment/本地开发环境变量说明.md`

## Skill 路由读取规则

- `docs/AI技能路由规范.md` 仅在涉及 Skill、Agent 调度、飞书 skill 选择或相关审查时读取。
- 不因存在 Skill 路由文档而默认全量读取 `docs/`。
- 不因存在飞书 skill 而默认执行飞书真实写入。

只有架构决策变更时，才读取：

- `docs/adr/`

## 当前里程碑提醒

当前 M0 已完成并封板，M0-REMOTE 已完成，M1-R0 已完成并通过 Codex 独立审查，M1-R1 已完成 HRMS 原生考勤对象模型验证记录并收口为 COMPLETED，M1-R2 已完成 HRMS 原生考勤配置试运行方案并通过 Codex 独立审查收口为 COMPLETED。M1-R3 已执行 HRMS 原生考勤最小测试数据试运行并通过 Codex 审查，实际结论为 PARTIAL / BLOCKED，最终状态收口为 BLOCKED：部分 TEST 数据已落库，14 个打卡场景未完成闭环验证。M1-R3A 已完成运行态阻断诊断与 TEST 数据隔离 / 清理方案，并已通过 Codex 审查收口为 COMPLETED。M1-R3B 已完成运行态最小修复方案，并已通过 Codex 审查收口为 COMPLETED。M1-R3B-FIX 已通过 Codex 审查并收口为 COMPLETED；该轮只执行 `docker compose up -d redis-cache redis-queue`。M1-R3C 已通过 Codex 审查并收口为 COMPLETED，结论为 PARTIAL / GAP_IDENTIFIED。M1-R3D 已通过 Codex 审查并收口为 COMPLETED，结论为 Gap 四类分类、均不需要立即创建 hb_attendance_app。M1-R3E 已通过 Codex 审查并收口为 COMPLETED。M1-R3F 已通过 Codex 审查并收口为 COMPLETED。M1-REQ-DESIGN-DRAFT 已通过 Codex 审查并收口为 COMPLETED。M1-R4 已通过 Codex 审查并收口为 COMPLETED，主文档 `docs/milestones/M1_R4_Demo技术方案与实施路线拆分.md` 已交付。M1-R5 已通过 Codex 审查并收口为 COMPLETED，主文档 `docs/milestones/M1_R5_HRMS配置基线工作台月报Demo.md` 已交付。M1-R6A 已通过 Codex 审查并收口为 COMPLETED，主文档 `docs/milestones/M1_R6A_Excel导入与异常流程落地方案.md` 已交付。M1-R6B 已通过 Codex 审查并收口为 COMPLETED，主文档 `docs/milestones/M1_R6B_脱敏打卡流水导入最小实现.md` 已交付。M1-R6C = COMPLETED，异常识别与异常说明流程最小实现已通过 Codex 审查并 closeout。M1-R7 = COMPLETED，飞书登录、领导 Demo 与 M1 收口准备已通过 Codex 审查并 closeout。M1 = COMPLETED（已 closeout）。M0-R3A 已完成 Frappe / ERPNext / Docker 最小本地环境落地，M0-R3C 已完成 Frappe HR / HRMS 安装验证，M0-R3C-FIX 已完成 HRMS 前端资源与 Roster 白屏诊断修复，M0-R3D 已完成 HRMS 能力盘点与 M1 考勤一期边界设计，M0-R3E 已完成 HRMS 环境可复现性收口并通过 Codex 审查。

下一步路线只记录，不代表已启动：

1. M1-R5 已通过 Codex 审查并收口为 COMPLETED，已交付 HRMS 配置基线、考勤工作台入口、月度汇总 Demo 和 Excel 月报导出路径。
2. M1 已 closeout 为 COMPLETED，但 Owner 验收发现功能缺口。
3. M1-FIX 功能补漏阶段已启动，M1-FIX-A 为 REVIEWING。
4. M1-FIX-B Excel 导入与真实本地数据闭环已实现并进入 REVIEWING。
5. M1-FIX-B2 已 COMPLETED；当前 M1-FIX-B3 为 REVIEWING，修复考勤工作台入口、App 命名与 HRMS 数据一致性。M1 产品交付未完成，M1-FIX-C/D/E 未启动。

后续涉及 HRMS 环境治理、前端资源复核、能力盘点或 M1 考勤一期边界时，可读取 M0-R3C 安装验证记录、M0-R3C-FIX 修复记录、M0-R3D 设计记录、M0-R3E 环境可复现性收口记录、官方 Frappe HR、`frappe/hrms`、`frappe/frappe_docker`、ERPNext / Frappe v16 资料。

不得因 HRMS 已安装而擅自创建新的海滨自定义 Frappe App；`hb_attendance_app` 仅限 M1-FIX-B 已授权的轻量导入能力，不得扩大范围；不得接飞书真实写入；不得做前端驾驶舱；不得提交真实 `.env` 或真实密钥。
