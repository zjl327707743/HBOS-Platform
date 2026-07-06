# Milestones

本目录用于记录新乡海滨智能运营管理平台的全项目里程碑索引和状态总览。

## 文件定位

- `docs/milestones/README.md`：全项目里程碑索引和状态总览。
- `docs/milestones/M0.md`：M0 工程启动与项目骨架的规划、轮次和状态。
- `docs/milestones/M0_REMOTE.md`：M0 后 GitHub Private remote 创建、绑定和首次 push 记录。
- `docs/milestones/M1_R0_平台入口账号权限与本地化诊断方案.md`：M1-R0 平台入口、账号体系、角色权限、飞书 SSO 可行性和中文化 / 本地化诊断方案。
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
| M1-R1 | HRMS 原生考勤对象模型验证 | PLANNED |
| M2 | 飞书集成 | PLANNED |

## 下一步路线

1. 准备进入 M1-R1。
2. M1-R1：HRMS 原生考勤对象模型验证。

M1 已完成 M1-R0 规划收口，但尚未进入业务开发。M1-R1 仍为 PLANNED。

## 更新规则

每轮任务收尾时，必须检查并更新对应里程碑文件。若本轮改变项目总状态、当前轮次或里程碑状态，还必须同步更新：

- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- 对应的 `docs/milestones/*.md`
