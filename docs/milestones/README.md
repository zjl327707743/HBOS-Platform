# Milestones

本目录用于记录新乡海滨智能运营管理平台的全项目里程碑索引和状态总览。

## 文件定位

- `docs/milestones/README.md`：全项目里程碑索引和状态总览。
- `docs/milestones/M0.md`：M0 工程启动与项目骨架的规划、轮次和状态。
- `docs/milestones/M0_REMOTE.md`：M0 后 GitHub Private remote 创建、绑定和首次 push 记录。
- `docs/milestones/M1_R0_平台入口账号权限与本地化诊断方案.md`：M1-R0 平台入口、账号体系、角色权限、飞书 SSO 可行性和中文化 / 本地化诊断方案。
- `docs/milestones/M1_R1_HRMS原生考勤对象模型验证记录.md`：M1-R1 HRMS 原生考勤对象模型验证记录。
- `docs/milestones/M1_R2_HRMS原生考勤配置试运行方案.md`：M1-R2 HRMS 原生考勤配置试运行方案。
- `docs/milestones/M1_R3_HRMS原生考勤最小测试数据试运行记录.md`：M1-R3 HRMS 原生考勤最小测试数据试运行记录。
- `docs/milestones/M1_R3A_运行态阻断诊断与TEST数据隔离清理方案.md`：M1-R3A 运行态阻断诊断与 TEST 数据隔离 / 清理方案。
- `docs/milestones/M1_R3B_运行态最小修复方案.md`：M1-R3B 运行态最小修复方案。
- `docs/milestones/M1_R3B_FIX_运行态最小修复执行记录.md`：M1-R3B-FIX 运行态最小修复执行记录。
- `docs/milestones/M1_R3C_HRMS原生考勤最小试运行复测记录.md`：M1-R3C HRMS 原生考勤最小试运行复测记录。
- `docs/milestones/M1_R3D_异常口径与Gap诊断.md`：M1-R3D 异常口径与 Gap 诊断。
- `docs/milestones/M1_R3E_配置复核与业务口径确认表.md`：M1-R3E 配置复核清单与业务口径确认表。
- `docs/milestones/M1_R3F_业务口径确认包.md`：M1-R3F 业务口径确认包。
- 后续每个大里程碑单独一个文件，例如 `M1.md`、`M2.md`。

## 里程碑文件规则

- 每个大里程碑一个文件。
- 文件名使用里程碑编号，例如 `M0.md`、`M1.md`、`M2.md`。
- 里程碑主文件可保留 `M0` / `M1` / `M2` 编号命名，标题使用中文，便于索引和跨文档引用。
- 新增普通文档名称优先使用中文或中英混合；`README.md` 等约定文件可保留英文。
- 每个里程碑文件应记录目标、范围、不做事项、轮次拆分、当前状态和验收条件。
- 每轮完成后必须更新相关里程碑状态。

## 状态枚举

- `PLANNED`：已规划，尚未开始。
- `IN_PROGRESS`：正在执行。
- `REVIEWING`：已完成本轮交付，等待审查或验收。
- `COMPLETED`：已验收完成并封板。
- `BLOCKED`：受阻，等待用户决策或外部条件。
- `CANCELLED`：已取消。

## 当前里程碑表

| 里程碑 | 名称 | 状态 |
| --- | --- | --- |
| M0 | 工程启动与项目骨架 | COMPLETED |
| M0-REMOTE | GitHub Private remote 收口 | COMPLETED |
| M1 | 考勤一期 | IN_PROGRESS |
| M1-R0 | 平台入口账号权限与本地化诊断方案 | COMPLETED |
| M1-R1 | HRMS 原生考勤对象模型验证 | COMPLETED |
| M1-R2 | HRMS 原生考勤配置试运行方案 | COMPLETED |
| M1-R3 | HRMS 原生考勤最小测试数据试运行 | BLOCKED |
| M1-R3A | 运行态阻断诊断与 TEST 数据隔离 / 清理方案 | COMPLETED |
| M1-R3B | 运行态最小修复方案 | COMPLETED |
| M1-R3B-FIX | 运行态最小修复执行 | COMPLETED |
| M1-R3C | HRMS 原生考勤最小试运行复测 | COMPLETED |
| M1-R3D | HRMS 原生考勤异常口径与配置 Gap 诊断 | COMPLETED |
| M1-R3E | 配置复核清单与业务口径确认表 | COMPLETED |
| M1-R3F | 业务口径确认包 | COMPLETED |
| M1-R4 | 后续考勤配置 / 报表或异常口径验证 | PLANNED |
| M2 | 飞书集成 | PLANNED |

## 下一步路线

1. M1-R3F 已通过 Codex 审查并收口，9 项确认主题中 7 项必须确认，2 项可先按默认值推进。
2. M1-R4 保持 PLANNED，尚未启动；M1-R4 前必须完成 7 项阻塞性确认主题的业务口径确认或 Owner 临时拍板。

M1 已完成 M1-R0 规划收口，M1-R1 已通过 Codex 独立审查并收口为 COMPLETED，M1-R2 已通过 Codex 独立审查并收口为 COMPLETED。M1-R3 已执行并通过 Codex 审查，但实际结论为 PARTIAL / BLOCKED，最终状态收口为 BLOCKED：部分 TEST 数据已落库，14 个打卡场景未完成 Attendance 闭环验证。M1-R3A 已完成运行态阻断诊断与 TEST 数据隔离 / 清理方案，并已通过 Codex 审查收口为 COMPLETED。M1-R3B 已完成运行态最小修复方案，并已通过 Codex 审查收口为 COMPLETED。M1-R3B-FIX 已通过 Codex 审查并收口为 COMPLETED。M1-R3C 已通过 Codex 审查并收口为 COMPLETED，结论为 PARTIAL / GAP_IDENTIFIED。M1-R3D 已通过 Codex 审查并收口为 COMPLETED，结论为 Gap 四类分类、均不需要立即创建 hb_attendance_app。M1-R3E 已通过 Codex 审查并收口为 COMPLETED。M1-R3F 已通过 Codex 审查并收口为 COMPLETED。M1 尚未进入业务开发，M1-R4 仍为 PLANNED。

## 更新规则

每轮任务收尾时，必须检查并更新对应里程碑文件。若本轮改变项目总状态、当前轮次或里程碑状态，还必须同步更新：

- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- 对应的 `docs/milestones/*.md`
