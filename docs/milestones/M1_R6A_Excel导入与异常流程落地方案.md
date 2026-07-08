# M1-R6A：Excel 导入与异常流程落地方案 / Gate 判定

项目名称：新乡海滨智能运营管理平台。

状态：COMPLETED。

审查记录：Codex 初审 FAIL（R6A 文档未提交、工作区不 clean），已在 `330f320` 中修复并提交。Codex 复审 PASS。M1-R6A 已从 REVIEWING 收口为 COMPLETED。M1-R6A closeout 完成，后续由 Owner 决定是否授权进入 M1-R6B。

执行日期：2026-07-08。

## 1. 文档定位

本文档是 M1-R6A 的主文档。`docs/milestones/M1_START_GATE.md` 是 M1 阶段门禁文档，不是当前轮次主文档。

### 1.1 M1-R6A 是什么

M1-R6A 是 **R6 的执行前技术落地方案与 Gate 判定轮**。

M1-R6A 不是完整 R6 开发。M1-R6A 在真正写代码、建 App、建 DocType、导入 Excel 之前，先把技术路径查清楚、把 Gate 判定掉、把 R6B/R6C 的边界拆分明。

### 1.2 M1-R6A 严格不做

- 不实现 Excel 导入功能
- 不导入真实 Excel
- 不导入脱敏 Excel
- 不创建 Employee Checkin 测试数据
- 不创建 Attendance 测试数据
- 不创建 App
- 不创建 DocType
- 不写正式导入代码
- 不写异常流程正式代码
- 不启动 M1-R7
- 不接飞书登录
- 不接真实考勤机
- 不正式接飞书请假
- 不接飞书工作台
- 不部署公司内网 / 云服务器
- 不修改 Frappe / ERPNext / HRMS 核心源码

### 1.3 M1-R6A 做完后的流程

```
M1-R6A 完成 → 进入 REVIEWING → 提交 Codex 审查
→ Codex PASS → closeout（状态收口为 COMPLETED）
→ 用户授权 → 进入 M1-R6B
```

Codex PASS 之前不允许进入 R6B。Codex PASS 之后仍需用户逐轮授权。

## 2. R6 范围继承

### 2.1 R6 总目标（继承自 M1-R4）

R6 总目标由 `M1_R4_Demo技术方案与实施路线拆分.md` 第 5.2 节定义：

1. 实现原始打卡流水 Excel 导入（Employee Checkin → Auto Attendance → Attendance）
2. 实现月度汇总 Excel 导入（独立展示或汇总 DocType，不触发 Auto Attendance）
3. 保留导入批次记录
4. 迟到/早退自动识别（late_entry/early_exit 正确置位）
5. 缺卡自动识别（上班单边/下班单边可区分）
6. 缺勤自动识别（按判断顺序：请假→节假日→排班→缺勤）
7. 员工能查看自己的考勤结果和异常
8. 员工能提交考勤异常说明（6 种类型）
9. 部门主管能查看本部门异常并确认/驳回
10. 人事/考勤管理员能最终处理并归档
11. 所有异常处理操作留痕可查
12. 月度汇总报表正确反映全部考勤字段

### 2.2 本轮与 R6 总目标的关系

M1-R6A 不实现以上任何一条目标。M1-R6A 做的是：

- 逐条评估 R6 目标的实现路径。
- 判断每条目标是「HRMS 原生可覆盖」还是「需要自定义开发」。
- 判断是否需要创建 App / DocType。
- 给 R6B 和 R6C 写出明确的执行边界。

R6 总目标的实现分布在 R6B 和 R6C 中，不在 R6A 中。

## 3. 两类 Excel 导入边界

### 3.1 严格区分

需求依据 `M1_考勤一期真实需求确认.md` 第「两类导入必须区分」节已明确：

```
原始打卡流水导入 ≠ 月度汇总 Excel 导入
```

| 维度 | 原始打卡流水导入 | 月度汇总 Excel 导入 |
| --- | --- | --- |
| 数据内容 | 员工 + 日期 + 上班打卡时间 + 下班打卡时间 | 员工 + 月度统计字段（应出勤、实际出勤、迟到次数、早退次数等） |
| 目标对象 | Employee Checkin → Auto Attendance → Attendance | 自定义汇总 DocType 或独立报表展示 |
| 是否触发 Auto Attendance | 触发 | 不触发 |
| 用途 | 生成考勤结果 | 对账、展示、历史数据迁移、演示报表 |
| 导入频率 | 每日或周期性 | 月度 |
| 数据粒度 | 逐条打卡记录 | 逐员工月度汇总行 |

不得把月度汇总表错误当成原始打卡流水。

### 3.2 原始打卡流水导入路径分析

#### 3.2.1 数据流

```
脱敏打卡流水 Excel（员工标识 + 日期 + 上班时间 + 下班时间）
→ 字段映射与校验
→ Employee Checkin（HRMS 原生 DocType，每条打卡一条记录）
→ Auto Attendance（HRMS 原生后台任务，基于 Shift Type + Employee Checkin 自动生成 Attendance）
→ Attendance（HRMS 原生 DocType）
→ 迟到/早退/缺卡/缺勤判定（读取 Attendance + Employee Checkin 字段）
```

#### 3.2.2 Employee Checkin 字段映射

HRMS 原生 Employee Checkin 关键字段（来自 M1-R1 对象模型验证记录）：

| Employee Checkin 字段 | 打卡 Excel 来源 | 说明 |
| --- | --- | --- |
| `employee` | 员工姓名/工号 → Employee Link | 需预先维护 Employee 并匹配 |
| `log_type` | 打卡方向 | IN / OUT |
| `time` | 打卡日期时间 | Excel 中的打卡时间列，需解析为标准 Datetime |
| `shift` | 班次（可选） | 如 Excel 包含班次信息可填入；否则由 Shift Assignment 决定 |
| `device_id` | 来源标记 | 可填入来源文件名或"Excel 导入" |
| `skip_auto_attendance` | 是否跳过自动考勤 | 必须为 0，否则不会触发 Auto Attendance |

#### 3.2.3 导入方式选择

**方式 A：HRMS Data Import（Frappe 原生 data_import 工具）**

能力评估（基于 Frappe v16 Data Import 文档和 M1-R3C 试运行经验）：

| 评估维度 | 结论 |
| --- | --- |
| 支持 Excel/CSV 上传 | 支持，原生支持 .csv/.xlsx |
| 支持 Employee Checkin 作为目标 DocType | HRMS Data Import 理论可导入任意 DocType |
| 字段映射 | Frappe Data Import 提供列→字段映射界面 |
| 批量导入 | 支持，但有单次导入记录数限制 |
| 错误处理 | 提供导入结果摘要（成功/失败/跳过），失败行含错误原因 |
| 导入批次记录 | **不原生支持**。Frappe Data Import 不记录导入批次号、来源文件名等自定义字段 |
| 重复检测 | 依赖 DocType 唯一约束或 name 命名规则 |

**方式 B：自定义导入入口（需创建自定义代码）**

触发条件（任一满足即触发）：
- HRMS Data Import 的字段映射无法覆盖 Employee Checkin 全部必须字段
- 需要对导入数据做复杂校验（如工号→Employee 匹配、时间格式清洗、跨夜判定）
- 需要记录导入批次（导入批次号、导入人、来源文件名、总/成功/失败数）
- 需要在导入后自动触发 Auto Attendance

#### 3.2.4 导入批次记录需求

需求依据 `M1_考勤一期技术设计方案.md` 第「导入批次设计」节：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| 导入批次号 | Data / Autoname | `IMP-YYYY-MM-XXXXX` |
| 导入人 | Link: User | 操作导入的用户 |
| 导入时间 | Datetime | 自动记录 |
| 导入类型 | Select | 原始打卡流水 / 月度汇总 |
| 来源文件名 | Data | 上传的 Excel 文件名 |
| 总记录数 | Int | |
| 成功数 | Int | |
| 失败数 | Int | |
| 失败原因 | Long Text | 汇总或逐条记录 |

M1 实现可先不做复杂批次管理，但若使用自定义导入入口，必须保留导入批次记录。

### 3.3 月度汇总 Excel 导入路径分析

#### 3.3.1 数据流

```
脱敏月度汇总 Excel（员工 + 月度统计字段）
→ 字段映射与校验
→ 自定义月度汇总 DocType（独立于 Employee Checkin / Attendance）
→ 在考勤工作台或报表中展示
→ 不触发 Auto Attendance
```

#### 3.3.2 与原始打卡流水导入的关键区别

- 月度汇总导入**不创建** Employee Checkin
- 月度汇总导入**不触发** Auto Attendance
- 月度汇总导入的目标是**对账和演示**，不是生成考勤结果
- 月度汇总字段（应出勤天数、迟到次数等）是**统计结果**，不是原始记录

#### 3.3.3 实现方式选择

**方式 A：直接导入为自定义 DocType**

需要创建一个月度汇总 DocType，字段对齐现有 Excel 模板的列。导入后作为独立的汇总数据表展示。

**方式 B：作为报表数据源导入**

使用 Frappe Data Import 导入到一个中间表，再通过 Query Report 展示。不创建独立的月度汇总 DocType。

**方式 C：仅做页面展示，不持久化导入**

上传 Excel 后在页面解析并展示，不落库。适合仅用于演示对账的场景。

技术评估：方式 A 最完整但需要创建自定义 DocType；方式 B 最轻量但不持久化；方式 C 适合快速演示但无法支持后续查询。M1 建议优先方式 A 或 B，方式 C 仅作为过渡。

### 3.4 现有人事 Excel 模板字段与系统映射

`M1_考勤一期真实需求确认.md` 记录的现有模板字段：

| 模板字段 | 系统对应 | 导入类型归属 |
| --- | --- | --- |
| 姓名 | Employee `employee_name` | 两者共用（匹配键） |
| 工号 | Employee `employee_number` 或自定义字段 | 两者共用（匹配键） |
| 部门 | Employee `department` | 两者共用 |
| 请假时长（小时） | Leave Application 聚合 | 月度汇总导入 |
| 应出勤天数 | Shift Assignment + Holiday List 计算 | 月度汇总导入 |
| 实际出勤天数 | Attendance `status = Present` 计数 | 月度汇总导入 |
| 计薪时长（小时） | Attendance `working_hours` 聚合 | 月度汇总导入 |
| 迟到次数 | Attendance `late_entry` 计数 | 月度汇总导入 |
| 早退次数 | Attendance `early_exit` 计数 | 月度汇总导入 |
| 旷工天数 | Attendance `status = Absent` 或无 Attendance 判缺勤 | 月度汇总导入 |
| 每日统计列（如 周三 26-07-01） | **非标准列，是原始打卡的汇总结果** | 月度汇总导入 |

注意：现有模板中的每日统计列是打卡结果的汇总展示，不直接对应 Employee Checkin 或 Attendance 的单条记录。导入时需要识别这些列的性质，不得错误映射。

## 4. 异常说明流程落地方案

### 4.1 需求回顾

`M1_考勤一期真实需求确认.md` 定义的异常处理流程：

```
员工提交补卡 / 异常说明
→ 部门主管确认事实
→ 人事 / 考勤管理员最终确认
```

权限原则：

- 员工提交说明
- 主管确认事实
- 考勤管理员修正数据
- 人事最终归档
- 所有修改留痕

异常说明类型（6 种）：

1. 补卡
2. 设备异常
3. 公出 / 会议
4. 班次错误
5. 请假未同步
6. 其他

### 4.2 HRMS 原生 Attendance Request 能力评估

#### 4.2.1 Attendance Request 是什么

HRMS 原生 Attendance Request 是 Frappe HR 提供的考勤申请/修正 DocType。根据 M1-R1 对象模型验证记录和 HRMS 文档，Attendance Request 主要用途：

- 员工申请补卡
- 员工申请修正考勤记录（如班次调整）
- 主管审批

#### 4.2.2 字段与能力核对

| 评估维度 | HRMS 原生 Attendance Request | M1 需求 | 是否满足 |
| --- | --- | --- | --- |
| 员工发起 | 支持，`employee` 字段 | 员工提交异常说明 | 可覆盖 |
| 异常类型 | 原生类型有限（通常为 Work From Home / Shift Change / On Duty 等） | 6 种海滨特有类型（补卡/设备异常/公出会议/班次错误/请假未同步/其他） | **不满足**：原生类型不全覆盖海滨 6 种 |
| 主管审批 | 支持 Workflow（Approval） | 主管确认事实（确认/驳回） | 可覆盖，但需配置 Workflow |
| 人事处理 | 不原生支持「人事最终处理」的独立步骤 | 考勤管理员修正数据 + 人事最终归档 | **不满足**：原生为单级审批，M1 需要三级 |
| 操作留痕 | Frappe 原生支持 Versioning（文档修改历史） | 谁/什么时候/改了什么/修改原因/处理状态 | 可覆盖（Frappe 原生版本历史 + Comment） |
| 与 Attendance 的关联 | 原生支持，可指定 `attendance_date` | 关联考勤日记录 | 可覆盖 |
| 修改原因 | 原生有 `reason` 字段 | 修改原因 | 可覆盖 |

#### 4.2.3 核心 Gap

HRMS 原生 Attendance Request 存在以下 Gap：

1. **异常类型 Gap**：原生类型（Work From Home、Shift Change 等）不全覆盖海滨 6 种异常说明类型。需要自定义 Select 字段或自定义 DocType。
2. **三级流转 Gap**：原生为单级审批（员工→审批人），M1 需要三级（员工→主管确认→人事处理→归档）。需要自定义 Workflow 或状态机。
3. **确认 vs 处理语义 Gap**：原生 Workflow 是「审批」，M1 的主管是「确认事实」而非「审批」，人事是「修正数据」而非简单的批准。

### 4.3 落地方案：方案 A（原生兜底 + 自定义补强）

#### 4.3.1 方案概述

- 以 HRMS 原生 Attendance Request 为**数据载体**（存储异常说明记录）。
- 通过**自定义字段**补齐 6 种异常说明类型。
- 通过**自定义 Workflow** 实现三级状态流转。
- 操作留痕利用 Frappe 原生 `Version`（文档修改历史）+ `Comment`（处理备注）。

#### 4.3.2 具体措施

**Step 1：扩展 Attendance Request 字段**

不创建新 DocType，而是在 HRMS 原生 Attendance Request 上通过 Custom Field 添加：

| 自定义字段 | 类型 | 选项/说明 |
| --- | --- | --- |
| `exception_type` | Select | 补卡 / 设备异常 / 公出会议 / 班次错误 / 请假未同步 / 其他 |
| `supervisor_confirmed` | Check | 主管是否确认事实 |
| `supervisor_comment` | Small Text | 主管确认备注 |
| `hr_processed` | Check | 人事是否已处理 |
| `hr_comment` | Small Text | 人事处理备注 |
| `final_status` | Select | 待主管确认 / 主管已确认 / 主管驳回 / 人事已处理 / 已归档 |

注意：通过 Custom Field 扩展原生 DocType 是 Frappe 官方支持的定制方式，不需要创建自定义 App。Custom Field 可以通过 Fixture（JSON 文件）版本化，也可以通过 Frappe Desk 界面配置。

**Step 2：配置 Workflow 状态流转**

```
草稿（Draft）
→ 待主管确认（Pending Supervisor）
→ 主管已确认（Supervisor Confirmed）或 主管驳回（Supervisor Rejected）
→ 待人事处理（Pending HR）
→ 人事已处理（HR Processed）
→ 已归档（Archived）
```

Workflow 配置通过 Frappe Desk 的 Workflow 界面完成，或通过 Fixture 版本化。

**Step 3：操作留痕**

- 依赖 Frappe 原生 `Version` 记录每次修改（谁、什么时候、改了什么）。
- 主管确认备注写入 `supervisor_comment`。
- 人事处理备注写入 `hr_comment`。
- 处理状态写入 `final_status`。

#### 4.3.3 方案 A 的优势

- 不需要创建自定义 App
- 不需要创建自定义 DocType（仅扩展原生 Attendance Request）
- Custom Field + Workflow 可通过 Fixture 版本化
- 利用 Frappe 原生 Version history 实现留痕

#### 4.3.4 方案 A 的风险

- Custom Field 依赖 HRMS 原生 Attendance Request DocType 不因 HRMS 版本升级而删除
- Workflow 配置较复杂，三级状态流转需要测试验证
- 如果 Attendance Request 的扩展字段过多，可能影响原生升级路径

### 4.4 落地方案：方案 B（自定义 DocType）

#### 4.4.1 触发条件

方案 B 是备选方案，仅在方案 A 经 R6B 实施验证后确认不可行时触发。触发条件：

- HRMS 原生 Attendance Request 不允许 Custom Field 扩展异常类型
- Workflow 三级流转无法通过原生 Workflow 配置实现
- 原生 Attendance Request 的业务语义与海滨异常说明流程冲突

#### 4.4.2 方案 B 设计（仅设计，不实现）

参照 `M1_考勤一期技术设计方案.md` 第「异常说明 / 主管确认 / 人事归档实现评估」节：

**Attendance Exception（考勤异常说明记录）**

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `employee` | Link: Employee | 发起员工 |
| `attendance_date` | Date | 异常日期 |
| `exception_type` | Select | 补卡 / 设备异常 / 公出会议 / 班次错误 / 请假未同步 / 其他 |
| `description` | Text | 员工提交的详细说明 |
| `supervisor` | Link: Employee | 主管（从 Employee `reports_to` 自动获取） |
| `supervisor_status` | Select | 待确认 / 已确认 / 已驳回 |
| `supervisor_comment` | Small Text | 主管确认备注 |
| `supervisor_time` | Datetime | 主管操作时间 |
| `hr_user` | Link: User | 处理的人事 |
| `hr_status` | Select | 待处理 / 已处理 / 已归档 |
| `hr_comment` | Small Text | 人事处理备注 |
| `hr_time` | Datetime | 人事操作时间 |
| `status` | Select | 待主管确认 / 主管已确认 / 主管驳回 / 人事已处理 / 已归档 |

**Attendance Correction（考勤修正记录）**

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `attendance` | Link: Attendance | 关联考勤记录 |
| `field_changed` | Data | 修改的字段名 |
| `old_value` | Data | 修正前值 |
| `new_value` | Data | 修正后值 |
| `correction_reason` | Text | 修正原因 |
| `corrected_by` | Link: User | 操作人 |
| `correction_time` | Datetime | 操作时间 |

注意：方案 B 仅为设计记录，**本轮不创建这些 DocType**。是否需要在 R6B 或 R6C 中创建，取决于方案 A 的验证结果和用户授权。

## 5. 是否需要创建 `hb_hr_app` 的判定

### 5.1 判定原则

继承 `M1_R4_Demo技术方案与实施路线拆分.md` 的判定原则：

- 仅在 HRMS 原生能力确实无法覆盖、且经用户明确授权时，才创建自定义 App
- 自定义 App 只用于海滨特有规则，不用于重写 HRMS 已有功能
- 倾向命名为 `hb_hr_app`
- 不得为"可能需要的自定义"提前创建空 App

### 5.2 R6 范围内各需求的载体分析

| R6 需求 | 是否可用原生能力 | 如原生不满足，是否需要 App | 判定 |
| --- | --- | --- | --- |
| 原始打卡流水导入 | Frappe Data Import 可覆盖基础导入 | 如需自定义导入入口，可通过 Server Script 实现，不一定需要独立 App | 暂不需要 App |
| 导入批次记录 | Frappe Data Import 不原生支持 | 自定义 DocType `HBOS Import Log` 可通过 Custom DocType 创建 | 需要 DocType，不一定需要独立 App |
| 月度汇总导入 | 无原生对应 DocType | 自定义月度汇总 DocType | 需要 DocType，不一定需要独立 App |
| 迟到/早退识别 | Attendance `late_entry`/`early_exit` 原生字段 | 需确认置位条件并通过配置实现 | 原生可覆盖 |
| 缺卡识别 | 无原生直接判定 | 可通过 Client Script / Server Script 基于 Checkin 数据判定 | 原生 + 脚本可覆盖 |
| 缺勤识别 | Attendance `status = Absent` 原生 | 完整判断逻辑（请假→节假日→排班→缺勤）需要 Server Script | 原生 + 脚本可覆盖 |
| 异常说明 6 种类型 | 原生 Attendance Request 类型不全覆盖 | 方案 A：Custom Field 扩展；方案 B：自定义 DocType | 方案 A 不需要 App |
| 三级流转流程 | 原生 Workflow 可配置 | 需自定义 Workflow | 原生 + 配置可覆盖 |
| 操作留痕 | Frappe 原生 Version | 原生已支持 | 原生可覆盖 |
| 月度汇总报表 | Query Report / Script Report | 原生已支持 | 原生可覆盖 |
| Excel 导出 | Frappe Report Export / List Export | 原生已支持 | 原生可覆盖 |

### 5.3 判定结论

**M1-R6A 判定：R6B 不需要创建 `hb_hr_app`。**

理由：

1. 原始打卡流水导入优先用 Frappe Data Import，自定义导入入口、导入批次记录、月度汇总 DocType 可通过 Custom DocType（非 App 级别）实现。
2. 异常说明流程优先用方案 A（Custom Field 扩展原生 Attendance Request + Custom Workflow），不需要自定义 DocType。
3. 迟到/早退/缺卡/缺勤识别优先用原生字段 + Server Script / Client Script 实现。
4. 月度汇总报表和 Excel 导出优先用 Frappe Query Report / Report Export 实现。
5. Custom DocType 可以通过 Frappe Desk 界面直接创建，或通过 `hooks.py` + Fixture 在 site 中注册，不依赖独立的 Frappe App。

**保留选项**：如果 R6B 实施过程中发现多个 Custom DocType + Custom Script + Custom Workflow 的配置难以管理，或需要跨环境迁移，可重新评估是否需要创建 `hb_hr_app` 作为版本化载体。该评估属于 R6B 执行中的决策点，不属于 R6A 的 Gate 判定。

## 6. R6B / R6C 后续执行任务拆分

### 6.1 拆分原则

R6 总目标的工作量较大，建议拆为两个执行轮次：

- **R6B**：原始打卡流水导入 + 月度汇总导入 + 导入批次记录 + 迟到/早退/缺卡/缺勤识别
- **R6C**：异常说明三级流程 + 操作留痕 + 月度汇总报表整合 + R6 验收

### 6.2 M1-R6B：Excel 导入与考勤异常自动识别

**定位**：实现两类 Excel 导入 + 考勤异常自动识别。不实现异常说明流程。

**目标**：

1. 实现原始打卡流水 Excel 导入（Employee Checkin → Auto Attendance → Attendance）
2. 实现月度汇总 Excel 导入（独立展示或汇总 DocType，不触发 Auto Attendance）
3. 保留导入批次记录（HBOS Import Log DocType）
4. 迟到自动识别（late_entry 正确置位，宽限期 0 分钟）
5. 早退自动识别（early_exit 正确置位，宽限期 0 分钟）
6. 缺卡自动识别（上班单边/下班单边可区分）
7. 缺勤自动识别（按判断顺序：请假→节假日→排班→缺勤）

**输入**：
- M1-R5 配置基线（Shift Type、Holiday List 等）
- M1-R6A Gate 判定结论（本轮文档）
- 员工 Demo 数据（虚构姓名、真实组织架构）
- 脱敏打卡流水 Excel（用户提供）

**允许的修改范围**：

- 创建 Custom DocType：`HBOS Import Log`（导入批次记录）
- 创建 Custom DocType：月度汇总 DocType（如选择方案 A）
- 创建 Server Script：缺卡判定逻辑、缺勤判定逻辑
- 配置 Frappe Data Import 模板或自定义导入入口
- 创建或配置 Shift Type、Holiday List
- 导入 Demo 员工数据（虚构姓名）
- 在本地 Docker 环境中执行导入验证

**禁止项**：
- 不实现异常说明流程（留给 R6C）
- 不创建 `hb_hr_app`（除非 R6B 执行中确认 Custom DocType + Script 不可管理）
- 不创建 `Attendance Exception` 或 `Attendance Correction`（留给 R6C，如需要）
- 不接真实考勤机
- 不接飞书登录/请假/工作台
- 不修改 Frappe / ERPNext / HRMS 核心源码
- 不使用真实员工姓名
- 不部署公司内网/云服务器

**验收点**：

1. 能导入脱敏打卡流水 Excel，生成 Employee Checkin
2. Employee Checkin 导入后能触发 Auto Attendance 生成 Attendance
3. 能导入月度汇总 Excel，在页面中展示且不触发 Auto Attendance
4. 导入批次日志可查（批次号、导入人、时间、文件、成功/失败数）
5. Attendance 中迟到记录 `late_entry = 1`
6. Attendance 中早退记录 `early_exit = 1`
7. 能识别并展示上班缺卡、下班缺卡、全天无打卡
8. 缺勤按判断顺序（请假→节假日→排班→缺勤）正确判定

**Codex 审查**：需要。R6B 完成后进入 REVIEWING，提交 Codex 审查。

**Closeout**：需要。Codex PASS 后执行 closeout 状态收口。

### 6.3 M1-R6C：异常说明流程与 R6 收口

**定位**：实现异常说明三级流程 + 操作留痕 + 月度汇总报表整合 + R6 整体验收。

**目标**：

1. 员工能查看自己的考勤结果和异常清单
2. 员工能提交考勤异常说明（6 种类型：补卡/设备异常/公出会议/班次错误/请假未同步/其他）
3. 部门主管能查看本部门异常并逐条确认/驳回
4. 人事/考勤管理员能最终处理并归档
5. 所有异常处理操作留痕可查（谁/什么时候/改了什么/修改原因/处理状态）
6. 月度汇总报表整合迟到/早退/缺卡/缺勤/异常待确认/最终状态全部字段
7. R6 12 项验收标准逐项确认

**输入**：
- M1-R6B 导入与异常识别结果
- M1-R6A 异常流程落地方案（方案 A 或方案 B）
- M1-R5 考勤工作台入口结构

**允许的修改范围**：

- 通过 Custom Field 扩展 Attendance Request（方案 A）
- 或创建自定义 DocType：`Attendance Exception`、`Attendance Correction`（方案 B，需用户授权）
- 配置 Workflow 实现三级状态流转
- 创建 Client Script / Server Script 实现业务逻辑
- 创建或调整 Query Report / Script Report 整合月度汇总全部字段
- 配置权限（员工看自己、主管看本部门、人事看全公司）

**禁止项**：
- 不接真实考勤机
- 不接飞书登录/请假/工作台
- 不创建 `hb_hr_app`（除非 R6B/R6C 实施验证确认需要）
- 不修改 Frappe / ERPNext / HRMS 核心源码
- 不使用真实员工姓名
- 不部署公司内网/云服务器

**验收点**：

1. 员工能在考勤工作台查看自己的考勤结果和异常
2. 员工能提交考勤异常说明（6 种类型可选）
3. 主管能查看本部门异常列表并确认/驳回
4. 人事能最终处理并归档
5. 操作留痕可查（Version history + Comment）
6. 月度汇总报表完整展示迟到/早退/缺卡/缺勤/请假/加班/节假日出勤/异常待确认/最终状态
7. R6 全部 12 项验收标准逐项确认

**Codex 审查**：需要。R6C 完成后进入 REVIEWING，提交 Codex 审查。

**Closeout**：需要。Codex PASS 后执行 closeout 状态收口。

### 6.4 R6B / R6C 关系

```
M1-R6A（本轮）：Gate 判定 + 技术落地方案
  ↓ Codex PASS + 用户授权
M1-R6B：Excel 导入 + 异常自动识别（不包含异常说明流程）
  ↓ Codex PASS + 用户授权
M1-R6C：异常说明流程 + 月度汇总整合 + R6 收口
  ↓ Codex PASS
R6 总验收完成 → 用户决定是否进入 M1-R7
```

R6B 和 R6C 均有独立的 Codex 审查和 closeout。两轮均需用户逐轮授权后启动。

## 7. Gate 判定汇总

### 7.1 承接 M1-R4 Gate 检查点

M1-R4 第 9 节列出了 12 项 Gate 检查点。以下针对 R6 相关的 Gate 做 R6A 判定：

| Gate | R4 原状态 | R6A 判定 | 判定依据 |
| --- | --- | --- | --- |
| Gate-1：HRMS Data Import 对打卡流水导入的支持 | 技术评估/待验证 | **PASS**：Frappe Data Import 理论可支持 Employee Checkin 导入；如需自定义导入入口（导入批次记录），走 Custom DocType + Server Script | HRMS Data Import 原生支持 Excel/CSV 导入任意 DocType |
| Gate-2：Attendance Request 是否足够支撑异常说明流程 | 技术评估/待验证 | **CONDITIONAL PASS**：方案 A（Custom Field + Custom Workflow）可满足；如方案 A 在 R6B 验证不通过，则切换方案 B | M1-R6A 第 4.3 节分析 |
| Gate-3：月度汇总 Excel 与原始打卡流水字段混淆 | 技术评估/待验证 | **PASS**：M1-R6A 已明确两类导入严格区分（第 3 节），R6B 实施时需在代码和 UI 层面强制执行 | 两类导入数据流和触发逻辑不同 |
| Gate-6：缺席判断逻辑完整性 | 技术评估/待验证 | **CONDITIONAL PASS**：判定顺序（请假→节假日→排班→缺勤）可通过 Server Script 实现，但需 R6B 验证各环节数据是否就绪 | M1-R6A 第 3.2 节判定 |
| Gate-8：是否需要创建 `hb_hr_app` | 技术评估/决策 Gate | **PASS（不创建）**：M1-R6A 判定 R6B/R6C 不需要创建 `hb_hr_app` | M1-R6A 第 5 节判定 |
| Gate-9：是否需要自定义 DocType | 技术评估/决策 Gate | **CONDITIONAL**：需要创建 `HBOS Import Log` 和月度汇总 DocType；Attendance Exception / Correction 在方案 A 下不需要，方案 B 下需要 | M1-R6A 第 5.2 节分析 |

### 7.2 核心 Gate 判定

**Gate-1：打卡流水导入**

判定：**PASS**。

HRMS/Frappe 原生能力可覆盖打卡流水 Employee Checkin 导入。补充路径：如需导入批次记录，创建 Custom DocType `HBOS Import Log` + Server Script 即可，不需要创建 App。

**Gate-2：异常说明流程**

判定：**CONDITIONAL PASS**。

优先方案 A：Custom Field 扩展原生 Attendance Request + Custom Workflow 三级流转。不创建自定义 App。R6B 先按方案 A 执行；如果方案 A 在 R6B 实施中验证不通过（如 Custom Field 无法覆盖 6 种异常类型、Workflow 三级流转不可行），则在 R6C 中切换到方案 B。

**Gate-8：是否需要 hb_hr_app**

判定：**不需要**。

R6 全部需求均可通过原生能力 + Custom DocType + Custom Field + Server Script + Custom Workflow 覆盖，不依赖独立 Frappe App。

**Gate-9：是否需要自定义 DocType**

判定：**需要有限的自定义 DocType**。

必须创建：
- `HBOS Import Log`（导入批次记录）
- 月度汇总 DocType（如选择方案 A 的月度汇总导入）

可选创建（仅在方案 A 失败时）：
- `Attendance Exception`（考勤异常说明记录）
- `Attendance Correction`（考勤修正记录）

以上 DocType 均通过 Frappe Custom DocType 机制创建，不依赖独立 App。

## 8. 风险与待验证项

| 风险 | 级别 | 说明 | 验证轮次 |
| --- | --- | --- | --- |
| Frappe Data Import 对 Employee Checkin `time` 字段的日期时间解析 | 中 | Excel 中的打卡时间可能是文本格式，Frappe Data Import 能否正确解析为 Datetime 需验证 | R6B |
| Auto Attendance 在 Employee Checkin 批量导入后的触发时机 | 中 | Auto Attendance 是后台任务，批量导入后能否及时触发需验证 | R6B |
| Custom Field 扩展 Attendance Request 的兼容性 | 中 | HRMS 版本升级可能影响 Custom Field；需在 R6B 中先做字段兼容性确认 | R6B |
| Custom Workflow 三级流转的状态管理 | 中 | 三级流转（员工→主管→人事）比原生二级审批复杂，需验证 Workflow 配置是否支持 | R6C |
| 缺卡判定依赖 Employee Checkin 数据的完整性 | 中 | 缺卡判定需要完整的 IN/OUT 打卡记录；Excel 导入可能只有部分字段 | R6B |
| 月度汇总导入与现有 Excel 模板格式的兼容性 | 中 | 现有人事 Excel 模板包含每日统计列，导入字段映射需适配 | R6B |
| 缺勤判断顺序在 Server Script 中的实现复杂度 | 低 | 请假→节假日→排班→缺勤的判断顺序逻辑清晰，Server Script 可实现 | R6B |
| Custom DocType 的管理和版本化 | 低 | 如果 Custom DocType 数量增多（3-4 个），后续可能需要统一版本化载体 | R6C 后评估 |

## 9. 输入文档

本轮读取并依据以下文档：

| 输入文档 | 用途 |
| --- | --- |
| `README.md` | 入口文件过期状态检查 |
| `CLAUDE.md` | 协作规则和进度来源 |
| `AGENTS.md` | Agent 行为约束 |
| `docs/AI_CONTEXT.md` | AI 上下文与阶段状态 |
| `docs/PROJECT_STATUS.md` | 项目总状态台账 |
| `docs/CURRENT_MILESTONE.md` | 当前里程碑与轮次状态 |
| `docs/READING_GUIDE.md` | AI 阅读范围指南 |
| `docs/milestones/README.md` | 里程碑索引 |
| `docs/milestones/M1_START_GATE.md` | M1 阶段门禁文档 |
| `docs/milestones/M1_考勤一期真实需求确认.md` | 需求依据（两类导入区分、异常流程、异常类型等） |
| `docs/milestones/M1_考勤一期产品需求说明书.md` | 产品设计（场景、角色、页面设计） |
| `docs/milestones/M1_考勤一期技术设计方案.md` | 技术路线（导入设计、异常 DocType 设计、导入批次设计、通用适配层） |
| `docs/milestones/M1_Demo实施路线图.md` | 实施拆分路线 |
| `docs/milestones/M1_R4_Demo技术方案与实施路线拆分.md` | R5/R6/R7 详细拆分与 Gate 检查点 |
| `docs/milestones/M1_R5_HRMS配置基线工作台月报Demo.md` | R5 配置基线与工作台设计 |

本轮任务类型为文档分析与方案设计，涉及技术判定和路线拆分。根据 `docs/AI技能路由规范.md`，文档分析与方案设计无专用 skill，按项目文档规则人工执行；未调用飞书 skill，未执行飞书真实写入。

## 10. 状态同步

### 10.1 本轮状态变更

| 项目 | 变更前 | 变更后 |
| --- | --- | --- |
| M1-R6A | （新增） | COMPLETED（Codex 审查 PASS，已 closeout） |
| M1-R6 | PLANNED | PLANNED（已拆分为 R6B/R6C） |
| M1-R7 | PLANNED | PLANNED（不变） |

### 10.2 需同步的文件

本轮主文档新增后，需同步以下状态台账：

- `docs/PROJECT_STATUS.md`：新增 M1-R6A 状态记录
- `docs/CURRENT_MILESTONE.md`：更新当前轮次为 M1-R6A
- `docs/milestones/README.md`：新增 M1-R6A 里程碑索引条目
- `docs/milestones/M1_START_GATE.md`：新增 M1-R6A 状态条目
- `README.md`：更新阶段描述（如存在过期描述）
- `docs/AI_CONTEXT.md`：更新当前上下文（如存在过期描述）

## 11. 完成确认

- [x] 已明确 M1-R6A 定位为 Gate 判定轮，不是 R6 完整开发
- [x] 已明确两类 Excel 导入边界（打卡流水 ≠ 月度汇总）
- [x] 已完成 HRMS 原生 Data Import 对打卡流水导入的能力评估
- [x] 已完成 Attendance Request 对异常说明三级流程的能力评估
- [x] 已给出异常说明落地方案 A（Custom Field + Custom Workflow）和方案 B（自定义 DocType）
- [x] 已判定 R6B/R6C 不需要创建 `hb_hr_app`
- [x] 已判定 R6B 需要创建有限的自定义 DocType（HBOS Import Log、月度汇总 DocType）
- [x] 已拆分 R6B（Excel 导入与自动识别）和 R6C（异常流程与月度汇总整合）的详细边界
- [x] 已完成 R6 相关 Gate 的逐项判定
- [x] 已列出 R6 实施前待验证的风险项
- [x] 本轮未导入 Excel、未创建 App、未创建 DocType、未写代码、未动数据库
- [x] 本轮未接真实考勤机、未接飞书、未修改核心源码
- [x] M1-R6A Codex 审查 PASS，已从 REVIEWING 收口为 COMPLETED
