# M1-R5：HRMS 配置基线、考勤工作台与月报 Demo

项目名称：新乡海滨智能运营管理平台。

状态：COMPLETED。

审查记录：Codex 审查 PASS。本轮 closeout 将 M1-R5 从 REVIEWING 收口为 COMPLETED；未开发、未试运行、未动数据库、未创建 App / DocType / 代码。主文档 `docs/milestones/M1_R5_HRMS配置基线工作台月报Demo.md` 已交付。

执行日期：2026-07-08。

## 1. 文档定位

本文档是 M1-R5 的主文档。`docs/milestones/M1_START_GATE.md` 是 M1 阶段门禁文档，不是当前轮次主文档。

M1-R5 定位为 **HRMS 配置基线、考勤工作台入口、月度汇总 Demo 展示路径与 Excel 月报导出路径**。

## 2. 本轮目标

本轮只做：

- HRMS / Frappe 原生考勤配置基线整理与最小落地方案。
- 考勤工作台入口方案。
- 月度汇总 Demo 展示路径。
- Excel 月报导出路径。
- R5 执行记录、验证记录和状态同步。

本轮不做：

- 不实现 R6 的脱敏 Excel 导入。
- 不实现 R6 的完整异常说明流程。
- 不实现 R7 的飞书登录。
- 不接真实考勤机。
- 不正式接飞书请假。
- 不接飞书工作台。
- 不启动大型 Vue 前端。
- 不创建新的 Frappe App。
- 不创建新的自定义 DocType。
- 不修改 Frappe / ERPNext / HRMS 核心源码。

## 3. 读取范围与 Skill 路由

本轮按用户指定读取了以下文件：

- `README.md`
- `CLAUDE.md`
- `AGENTS.md`
- `docs/AI_CONTEXT.md`
- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/READING_GUIDE.md`
- `docs/milestones/README.md`
- `docs/milestones/M1_START_GATE.md`
- `docs/milestones/M1_考勤一期真实需求确认.md`
- `docs/milestones/M1_考勤一期产品需求说明书.md`
- `docs/milestones/M1_考勤一期技术设计方案.md`
- `docs/milestones/M1_Demo实施路线图.md`
- `docs/milestones/M1_R4_Demo技术方案与实施路线拆分.md`
- `docs/AI技能路由规范.md`

本轮任务类型为文档维护、配置基线设计与执行记录整理。根据 `docs/AI技能路由规范.md`，文档维护无专用 skill，按项目文档规则人工执行；未调用飞书 skill，未执行飞书真实写入。

## 4. 本轮实现边界与最小落地判断

当前仓库是工程启动文档、状态台账、Docker 最小配置与 M1 文档仓库，不是 Frappe App 仓库。当前仓库内没有已存在的 `hb_hr_app`、`hb_attendance_app` 或其他可承载 Frappe Workspace / Report fixture 的自定义 App。

因此，本轮不在 Frappe Desk 中直接创建数据库态 Workspace、Report 或配置数据。原因：

- Frappe Desk 中创建的 Workspace / Report / 配置数据主要落在站点数据库中。
- 本轮禁止创建新的 Frappe App，缺少安全的版本化载体来提交这些数据库态配置。
- 本轮禁止创建新的自定义 DocType，不能用自定义对象承载月度汇总或异常记录。
- 本轮不得导入真实员工姓名或未脱敏真实数据。

本轮的最小落地结果为：

- 固化 HRMS 配置基线清单。
- 固化考勤工作台入口结构。
- 固化月度汇总 Demo 字段映射和展示路径。
- 固化 Excel 月报导出路径。
- 明确后续若需要真实 Workspace / Report 版本化，应在 R5 审查后由用户授权选择实现方式。

## 5. HRMS 配置基线

M1 Demo 至少需要以下 HRMS / Frappe 原生对象或能力。

| 对象 / 能力 | M1-R5 基线用途 | 本轮处理方式 | 数据与脱敏要求 |
| --- | --- | --- | --- |
| Company / 公司 | Demo 组织归属、员工与考勤数据根节点 | 使用真实组织架构名称可行；本轮记录配置步骤，不写库 | 可使用真实组织架构 |
| Department / 部门 | 员工部门、主管范围、报表筛选 | 使用真实部门结构可行；本轮记录配置步骤，不写库 | 可使用真实部门结构 |
| Employee / 员工主数据 | 考勤主体、User / Employee 关联、报表维度 | 必须使用虚构员工姓名；本轮不导入员工数据 | 不得使用真实员工姓名 |
| Shift Type / 班次类型 | 白班、中班、夜班、行政班 | 使用 HRMS 原生 Shift Type；配置 0 分钟迟到 / 早退宽限口径 | 不涉及真实人员数据 |
| Shift Assignment / 排班 | 员工排班、应出勤计算依据 | 使用 HRMS 原生 Shift Assignment；R5 仅定义路径 | 不导入真实人员排班 |
| Holiday List / 节假日 | 节假日、休息日与节假日出勤判断 | 使用 HRMS / ERPNext 原生 Holiday List | 可按真实日历配置 |
| Employee Checkin / 打卡记录 | 原始打卡流水目标对象 | R5 仅记录入口；R6 再做脱敏 Excel 导入 | 不导入真实流水 |
| Attendance / 考勤结果 | 月度汇总基础数据源 | 使用 HRMS 原生 Attendance；R5 仅定义展示路径 | 不生成新真实数据 |
| Leave Application / 请假 | 请假天数 / 小时聚合来源 | 使用 HRMS 原生 Leave Application；正式接飞书请假不在 R5 | 不接飞书请假 |
| Attendance Request / 补卡或考勤申请 | 如当前 HRMS 版本可用，作为补卡 / 考勤申请入口 | R5 仅列为工作台入口；完整异常说明流程放 R6 | 不实现完整异常流程 |
| Role / 权限角色 | 员工、主管、人事、领导、系统管理员权限边界 | 使用 Frappe Role / User Permission 设计路径 | 不新增真实账号 |
| Workspace / 工作台入口 | 聚合考勤相关对象与报表入口 | 优先 Frappe Workspace / Desk；本轮记录结构，不写库 | 不接飞书工作台 |
| Report / 月度汇总报表或可导出路径 | 月度汇总 Demo、Excel 导出 | 优先 Frappe Report / List Export / Data Export | 不创建自定义 DocType |

### 5.1 建议配置步骤

在后续获得数据库配置授权或版本化载体授权后，可按以下顺序配置：

1. 确认 Company 使用真实组织架构名称，但不录入真实员工姓名。
2. 建立 Department 结构，允许映射真实部门。
3. 使用虚构姓名建立 Demo Employee，保留部门、工号等必要演示字段的脱敏版本。
4. 建立 Shift Type：白班、中班、夜班、行政班。
5. 建立 Holiday List，覆盖 Demo 月份的工作日、休息日与节假日。
6. 建立 Shift Assignment，覆盖 Demo 员工和 Demo 月份。
7. 通过 Employee Checkin / Attendance 的 List View 或 Report 路径展示打卡记录与考勤结果。
8. 使用 Leave Application 手动维护或演示请假数据；飞书请假不在 R5。
9. 如当前 HRMS 版本提供 Attendance Request，作为补卡 / 考勤申请入口先挂入工作台。
10. 配置 Role / User Permission 的目标边界，真实隔离验证留给后续执行轮。

## 6. 考勤工作台入口

R5 工作台优先使用 Frappe Desk / Workspace，不启动大型 Vue 前端，不接飞书工作台。

建议 Workspace 名称：`考勤工作台`。

工作台至少聚合以下入口：

| 分组 | 入口 | 原生对象 / 能力 | 说明 |
| --- | --- | --- | --- |
| 主数据 | 员工信息 | Employee | 人事维护 Demo 员工；姓名必须虚构 |
| 配置 | 班次配置 | Shift Type | 白班、中班、夜班、行政班 |
| 配置 | 排班 | Shift Assignment | Demo 月排班入口 |
| 记录 | 打卡记录 | Employee Checkin | R6 导入前作为查看入口 |
| 结果 | 考勤结果 | Attendance | Auto Attendance 或手工结果查看入口 |
| 请假 | 请假记录 | Leave Application | R5 可手工创建演示；不接飞书请假 |
| 申请 | 考勤申请 / 补卡入口 | Attendance Request（如当前版本可用） | R5 仅提供入口；完整流程 R6 |
| 报表 | 月度汇总报表 | Frappe Report / List View / Query Report 候选 | R5 固化展示路径 |
| 导出 | Excel 月报导出 | Report Export / List View Export / Data Export | R5 固化导出路径 |

### 6.1 最小落地结果

由于本轮不创建 App、不创建自定义 DocType，且当前仓库没有可版本化 Workspace fixture 的合法载体，本轮不直接写入 Frappe Workspace 数据库记录。

R5 的工作台最小落地是可审查的结构方案：后续若用户授权数据库态配置，可在 Frappe Desk 中按上表创建 Workspace；若用户授权版本化实现，则应先确定是否创建 `hb_hr_app` 或其他合法 fixture 载体。

## 7. 月度汇总 Demo 展示路径

R5 月度汇总 Demo 的目标是让人事 / 领导能看到月度汇总路径，并能说明字段来源、可覆盖程度和导出方式。本轮不实现 R6 的导入，不把月度汇总 Excel 当作原始打卡流水。

### 7.1 字段映射

| 月度汇总字段 | 原生可覆盖字段 / 对象 | 需要计算或汇总 | 暂无法直接覆盖 / 后续补充 |
| --- | --- | --- | --- |
| 员工姓名 | Employee `employee_name` | 无 | Demo 姓名必须虚构 |
| 部门 | Employee `department` | 无 | 可用真实部门结构 |
| 应出勤天数 | Shift Assignment、Holiday List | 需要按月份、排班、节假日汇总 | Query / Script Report 计算 |
| 实际出勤天数 | Attendance `status = Present` | 需要按 Employee + 月份计数 | 需先有 Attendance 数据 |
| 迟到次数 | Attendance `late_entry` | 需要按月份汇总 | M1-R3C 已暴露置位 Gap，需后续复测 |
| 早退次数 | Attendance `early_exit` | 需要按月份汇总 | M1-R3C 已暴露置位 Gap，需后续复测 |
| 缺卡次数 | Employee Checkin 单边打卡、Attendance 异常口径 | 需要规则计算 | R6 识别逻辑补齐 |
| 缺勤天数 | Attendance `status = Absent`，或有排班无请假无打卡 | 需要按业务判断顺序计算 | R6 完整缺勤判断补齐 |
| 请假天数 / 小时 | Leave Application | 需要按请假类型、半天 / 全天 / 小时汇总 | 飞书请假不在 R5 |
| 加班小时 | Attendance `working_hours`、Shift Type 标准工时、加班审批 | 需要审批口径和计算 | R5 不实现加班审批 |
| 节假日出勤 | Holiday List + Attendance | 需要匹配节假日并计数 | 需后续报表计算 |
| 异常待确认数 | Attendance Request 候选；未来 Attendance Exception 候选 | 需要状态汇总 | 完整异常说明流程在 R6 |
| 最终考勤状态 | Attendance、异常处理状态 | 需要规则计算 | R6/R7 或未来自定义能力补齐 |
| 备注 | 报表备注或人工说明 | 需要报表层补充 | 无自定义 DocType 时不持久化 |

### 7.2 展示路径候选

优先级从高到低：

1. Frappe 原生 Report / Query Report：以 Attendance、Employee、Shift Assignment、Holiday List、Leave Application 为来源聚合。
2. Attendance / Employee Checkin / Leave Application 的 List View 组合筛选：作为无自定义 Report 时的最小演示路径。
3. Data Export 导出的多对象数据离线汇总：只作为过渡演示，不作为最终产品能力。
4. Script Report：如 Query Report 无法覆盖缺卡、节假日出勤、异常待确认数等字段，再评估。

本轮不创建 Query Report / Script Report 数据库记录，原因同第 4 节：当前缺少安全版本化载体。

## 8. Excel 月报导出路径

R5 Excel 导出路径只针对“月报展示 / 导出路径”，不是脱敏 Excel 导入，也不是原始打卡流水导入。

优先路径：

1. Frappe Report Export：月度汇总 Report 形成后，使用报表页面导出 Excel。
2. List View Export：对 Attendance、Employee Checkin、Leave Application 等原生对象按月份和部门筛选后导出。
3. Data Export：用于导出原生 DocType 数据，辅助离线汇总或验收核对。

注意：

- 不把月度汇总 Excel 当作原始打卡流水。
- 不在 R5 实现 Excel 导入。
- 不在 R5 创建导入批次记录。
- 不提交真实人员数据或未脱敏 Excel。

## 9. R5 验收点

| 编号 | 验收点 | R5 结果 |
| --- | --- | --- |
| 1 | 能说明 HRMS 配置基线包含哪些对象 | 已完成，见第 5 节 |
| 2 | 能看到或明确设计“考勤工作台”入口 | 已完成，见第 6 节 |
| 3 | 工作台能聚合考勤相关原生对象入口 | 已完成结构设计，见第 6 节 |
| 4 | 能看到或明确设计“月度汇总 Demo”展示路径 | 已完成，见第 7 节 |
| 5 | 能说明 Excel 月报导出路径 | 已完成，见第 8 节 |
| 6 | 不创建 App | 已遵守 |
| 7 | 不创建 DocType | 已遵守 |
| 8 | 不启动 R6/R7 功能 | 已遵守 |
| 9 | 状态进入 `M1-R5 = REVIEWING`（执行完成）→ closeout 后状态收口为 `M1-R5 = COMPLETED` | 已同步 |
| 10 | 后续 `M1-R6/R7` 仍未启动 | 已同步 |

## 10. R5 风险与后续 Gate

以下内容均为技术评估或后续 Gate，不代表 Owner 已确认要创建 App / DocType。

| 风险 / Gate | R5 结论 |
| --- | --- |
| HRMS 原生 Workspace 是否足够支撑考勤工作台 | 原生 Workspace 足以聚合入口；如需版本化和跨环境迁移，需要 fixture 载体 |
| HRMS 原生 Report 是否足够支撑月度汇总 | 基础字段可通过 Report / Query Report 汇总；缺卡、异常待确认、节假日出勤等字段需要计算 |
| 是否需要后续创建 `hb_hr_app` | 仍是后续决策 Gate；R5 不创建。若要版本化 Workspace / Report / 自定义逻辑，可能需要评估 |
| 是否需要后续创建 Attendance Exception / Attendance Correction | 仍是 R6 Gate；只有 Attendance Request 无法覆盖异常说明流程时才评估 |
| 缺卡次数、异常待确认数、节假日出勤等字段是否需要后续计算 | 需要后续计算或报表逻辑；R5 不实现 |
| Excel 导出是否能满足人事现有模板 | 原生导出可满足基础表格导出；模板格式兼容性需后续拿脱敏模板验证 |
| R6 导入时是否需要自定义导入批次记录 | 仍是 R6 Gate；若使用自定义导入入口，必须保留导入批次记录 |
| 历史 TEST 数据是否影响 Demo | R5 未清理 TEST 数据；如进入真实演示配置，需用户授权清理或隔离 |

## 11. 验证记录

本轮执行了以下验证：

- 读取限定入口、M1 设计文档和 R4 主文档，未递归读取整个 `docs/`。
- 确认当前仓库没有已存在的自定义 Frappe App 目录可承载 Workspace / Report fixture。
- 确认本轮没有新增 App、没有新增 DocType、没有修改 Frappe / ERPNext / HRMS 核心源码。
- 确认本轮只新增 / 修改 `.md` 文档。

本轮未执行：

- 未启动或重启 Docker 服务。
- 未写入 Frappe site 数据库。
- 未导入真实员工姓名。
- 未导入未脱敏真实数据。
- 未接真实考勤机。
- 未接飞书登录。
- 未正式接飞书请假。
- 未接飞书工作台。

## 12. 状态同步

本轮完成后状态为：

- `M1-R5 = COMPLETED`
- `M1-R4 = COMPLETED`
- `M1-R6 = PLANNED / 待授权 / 未启动`
- `M1-R7 = PLANNED / 待授权 / 未启动`

已同步更新：

- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/milestones/README.md`
- `docs/milestones/M1_START_GATE.md`
- 公共入口文件中的过期状态描述

## 13. 完成确认

- [x] 已整理 HRMS 配置基线。
- [x] 已形成考勤工作台入口方案。
- [x] 已形成月度汇总 Demo 展示路径。
- [x] 已形成 Excel 月报导出路径。
- [x] 已列出 R5 风险与后续 Gate。
- [x] 本轮未启动 M1-R6。
- [x] 本轮未启动 M1-R7。
- [x] 本轮未接真实考勤机。
- [x] 本轮未接飞书登录。
- [x] 本轮未正式接飞书请假。
- [x] 本轮未接飞书工作台。
- [x] 本轮未创建 App。
- [x] 本轮未创建 DocType。
- [x] 本轮未修改核心源码。
- [x] 本轮未提交真实员工姓名或未脱敏数据。
