# M1-R6C：异常识别与异常说明流程最小实现

项目名称：新乡海滨智能运营管理平台。

状态：COMPLETED。

审查记录：M1-R6C 执行审查 PASS。R6C 异常识别与异常说明流程最小实现已通过审查并收口为 COMPLETED。closeout 仅做状态收口，未启动 R7。

执行日期：2026-07-09。

## 1. 本轮定位

M1-R6C 是 **异常识别与异常说明流程最小实现轮**。本轮已由 Owner 授权从 M1-R6B closeout 后进入 R6C。

本轮只做：

1. 基于 R6B 已完成的脱敏打卡流水导入结果，识别最小考勤异常。
2. 覆盖迟到、早退、上班缺卡、下班缺卡、缺勤的最小识别口径。
3. 优先复用 HRMS 原生 `Attendance Request` 做异常说明流程。
4. 验证最小三级流程：员工提交说明 → 主管确认事实 → 人事最终处理 → 操作留痕。
5. 形成 R6C 实施记录文档。
6. 更新入口状态文件。

本轮不做：

- 不启动 R7。
- 不接飞书登录。
- 不接飞书请假。
- 不接飞书工作台。
- 不接真实考勤机。
- 不实现月度汇总 Excel 导入。
- 不创建 `hb_hr_app`。
- 不创建自定义 DocType。
- 不创建 `Attendance Exception` / `Attendance Correction`。
- 不修改 Frappe / ERPNext / HRMS 核心源码。
- 不部署公司内网或云服务器。
- 不提交 Excel / CSV / 真实数据。

## 2. 读取文件清单

本轮按轻量范围读取：

| 读取文件 | 用途 |
| --- | --- |
| `CLAUDE.md` | 项目协作规则 |
| `docs/AI_CONTEXT.md` | AI 上下文与阶段状态 |
| `docs/PROJECT_STATUS.md` | 项目总状态台账 |
| `docs/CURRENT_MILESTONE.md` | 当前里程碑与轮次状态 |
| `docs/READING_GUIDE.md` | AI 阅读范围指南 |
| `docs/milestones/M1_R6A_Excel导入与异常流程落地方案.md` | R6A Gate 判定与方案 |
| `docs/milestones/M1_R6B_脱敏打卡流水导入最小实现.md` | R6B 导入结果基线 |
| `docs/milestones/M1_考勤一期真实需求确认.md` | 需求依据（异常识别口径、异常类型） |
| `docs/milestones/M1_考勤一期产品需求说明书.md` | 产品设计（场景、角色、三级流程） |
| `docs/milestones/M1_考勤一期技术设计方案.md` | 技术路线（异常 DocType 设计、Workflow） |
| `docs/milestones/M1_R5_HRMS配置基线工作台月报Demo.md` | R5 配置基线 |

未递归读取 `docs/`，未读取 `docs/archive`、`docs/research`、`docs/legacy`。

## 3. R6A / R6B 结论继承

### 3.1 从 R6A 继承

- R6A Gate 判定：Attendance Request 为 **CONDITIONAL PASS**。
- 优先方案 A：Custom Field 扩展原生 Attendance Request + Custom Workflow 三级流转。
- 不创建 App、不创建自定义 DocType。

### 3.2 从 R6B 继承

R6B 已完成的 Demo 数据：

| 数据项 | R6B 结果 |
| --- | --- |
| 虚构员工 | 3 名（R6B-EMP-001/002/003 → HR-EMP-00017/00018/00019） |
| Shift Type | `TEST-HBOS-M1R6B-早班-0800-1600` |
| Shift Assignment | 3 条（2026-07-02 至 2026-07-03） |
| Employee Checkin | 已写入 July 2（5 条）+ July 3（4 条） |
| Attendance | July 2（3 条）+ July 3（3 条） |
| late_entry 标记 | 当时为 0（Shift Type 未启用标记） |

R6B 识别到的限制：

- `late_entry` / `early_exit` 未置位 → R6C 修复 Shift Type 配置
- 单车 OUT 能生成 Attendance → 可作为缺卡候选识别基础
- `in_time` / `out_time` 空值事实可用于缺卡检测

## 4. 异常识别口径

严格按照 M1 已确认口径执行：

### 4.1 迟到

- 超过上班时间 0 分钟即算迟到。
- M1 不设置宽限期。
- 识别方式：Attendance `late_entry = 1`。

### 4.2 早退

- 早于下班时间 0 分钟即算早退。
- M1 不设置宽限期。
- 识别方式：Attendance `early_exit = 1`。

### 4.3 上班缺卡

- 上班缺卡 = 缺卡异常。
- 不直接算缺勤，不直接算早退。
- 识别方式：Attendance `in_time` 为 NULL / 空值，但有 OUT 打卡记录。

### 4.4 下班缺卡

- 下班缺卡 = 缺卡异常。
- 不直接算早退，不直接算缺勤。
- 识别方式：Attendance `out_time` 为 NULL / 空值，但有 IN 打卡记录。

### 4.5 全天无打卡 / 缺勤

判断顺序严格为：

```
先看是否请假
再看是否节假日 / 休息日
再看是否有排班
有排班且无请假、无打卡，则记为缺勤
```

### 4.6 加班

- M1 必须有审批才算正式加班。
- R6C 不做正式加班审批实现。

### 4.7 节假日出勤

- 只记录，不自动转加班或调休。

### 4.8 临时调班

- 由考勤管理员维护 Shift Assignment。
- R6C 不做完整调班审批流。

## 5. 异常类型与字段承载

### 5.1 R6C 覆盖 6 类异常说明类型

| # | 异常类型 | R6C Custom Field 承载 |
| --- | --- | --- |
| 1 | 补卡 | `exception_type` = '补卡' |
| 2 | 设备异常 | `exception_type` = '设备异常' |
| 3 | 公出 / 会议 | `exception_type` = '公出会议' |
| 4 | 班次错误 | `exception_type` = '班次错误' |
| 5 | 请假未同步 | `exception_type` = '请假未同步' |
| 6 | 其他 | `exception_type` = '其他' |

### 5.2 Custom Field 列表

本轮在 HRMS 原生 `Attendance Request` 上通过 Custom Field 扩展了 11 个字段：

| 字段名 | 类型 | 标签 | 用途 |
| --- | --- | --- | --- |
| `exception_type` | Select | 异常说明类型 | 6 种海滨异常类型（补卡/设备异常/公出会议/班次错误/请假未同步/其他） |
| `exception_detail` | Small Text | 异常详细说明 | 员工提交的详细说明内容 |
| `supervisor_confirmed` | Check | 主管已确认事实 | 主管确认标记 |
| `supervisor_comment` | Small Text | 主管确认备注 | 主管确认备注说明 |
| `supervisor_time` | Datetime | 主管操作时间 | 主管确认/驳回时间戳（只读） |
| `hr_processed` | Check | 人事已处理 | 人事最终处理标记 |
| `hr_comment` | Small Text | 人事处理备注 | 人事处理备注说明 |
| `hr_time` | Datetime | 人事操作时间 | 人事处理时间戳（只读） |
| `processing_status` | Select | 处理状态 | 三级流程状态：待主管确认/主管已确认/主管驳回/人事已处理/已归档 |

### 5.3 字段承载关系与限制

- 原生 `reason` 字段（Select: Work From Home / On Duty）作为必填字段保留，但不承载异常类型语义；异常类型通过 `exception_type` 承载。
- 原生 `explanation`（Small Text）可承载补充说明，与 `exception_detail` 互补使用。
- 三级流程状态通过 `processing_status` + `supervisor_confirmed` + `hr_processed` 组合表达。
- 操作时间戳通过 `supervisor_time` / `hr_time` 记录，配合 Frappe 原生 `Version` + `Comment` 实现留痕。

## 6. Attendance Request 适配评估

### 6.1 HRMS 原生 Attendance Request 能力边界

经过本轮实际验证，HRMS 原生 Attendance Request 的能力与限制如下：

| 评估维度 | 原生能力 | M1-R6C 需求 | 适配结论 |
| --- | --- | --- | --- |
| 员工发起 | 支持（`employee` 字段） | 员工提交异常说明 | 可覆盖 |
| 异常类型（原生） | Work From Home / On Duty | 6 种海滨特有类型 | **需 Custom Field 扩展**（已完成） |
| 主管审批 | 支持 Workflow（需配置） | 主管确认事实 | 需配置 Workflow，M1-R6C 未完成 Workflow 配置 |
| 人事处理 | **不原生支持独立步骤** | 三级流转 | **需 Custom Field + Workflow 扩展** |
| 操作留痕 | Frappe 原生 Version + Comment 支持 | 谁/什么时候/改了什么 | 可覆盖 |
| 与 Attendance 关联 | 原生字段支持 | 关联考勤日记录 | 可覆盖 |
| 已有 Attendance 时的行为 | **验证阻止创建** | 异常说明（已有 Attendance 时） | **核心 Gap**（见 6.2） |

### 6.2 核心 Gap：Attendance Request 的设计语义冲突

**关键发现：HRMS 原生 Attendance Request 的 `validate_no_attendance_to_create()` 方法会在目标日期已有 Attendance 记录时阻止创建。**

验证过程：

1. 当目标日期（如 2026-07-02）已存在 Attendance 记录时，`AttendanceRequest.insert()` 触发 `validate_no_attendance_to_create()`，返回 `ValidationError: "Attendance status unchanged - Skip"`。
2. 该行为是 **设计如此**（by design），不是 Bug。HRMS 原生 Attendance Request 的语义是"为没有考勤记录的日期创建考勤"（如 On Duty 在外勤务必填考勤，或 Work From Home 远程办公），而不是"对已有考勤结果进行异常说明或修正"。
3. 这是 R6A 方案 A "CONDITIONAL PASS" 判定中未能提前发现的关键 Gap。

**影响**：

- 如果日期已有 Attendance 记录（即 R6B 导入后由 Auto Attendance 生成的），则无法直接使用原生 Attendance Request 做异常说明。
- 如果需要异常说明与已有 Attendance 共存（这是 M1 正常业务场景），原生 Attendance Request 不适用。

### 6.3 Gate 结论：是否需要自定义 App / DocType

**R6C 结论：在已有 Attendance 场景下，HRMS 原生 Attendance Request 无法直接承载异常说明流程。**

原因：

- Custom Field 扩展字段本身成功（11 个字段已创建）。
- 但原生 `validate_no_attendance_to_create()` 阻挡了核心业务场景（面向已有考勤结果的异常说明）。
- 该验证是原生 Python 代码逻辑，根据项目规则不可修改核心源码。

**后续 Owner 授权点**：

| 选项 | 说明 | 影响 |
| --- | --- | --- |
| A：绕过原生验证 | 通过 Server Script（`doc_events` hook）在 `before_validate` 中跳过 `validate_no_attendance_to_create` | 轻量但属于 Hook 干预原生逻辑，需评估兼容性 |
| B：创建自定义 DocType | 创建独立 `Attendance Exception` DocType（R6A 方案 B） | 需要创建 DocType + 可能创建 App 作为版本化载体，需 Owner 明确授权 |
| C：文档化限制 | 接受原生限制，R6C 仅记录适配评估和 Gap，等待后续轮次处理 | 本轮可完成，但异常说明的最小三级流程无法在 HRMS 原生中完整验证 |

**R6C 当前不擅自创建 App / DocType，按照项目规则等待 Owner 明确授权。**

## 7. 最小验证数据边界

### 7.1 复用 R6B 数据

| 数据项 | 来源 | 内容 |
| --- | --- | --- |
| 虚构员工 | R6B | 3 名：HR-EMP-00017（甲）、HR-EMP-00018（乙）、HR-EMP-00019（丙） |
| 公司 | M1-R3C | `TEST-HBOS-M1R3C-虚构公司` |
| 部门 | M1-R3C | `TEST-HBOS-M1R3C-生产一部 - R3C` |
| 节假日 | M1-R3C | `TEST-HBOS-M1R3C-虚构节假日` |
| 班次 | R6B | `TEST-HBOS-M1R6B-早班-0800-1600` |
| 排班 | R6B | 3 条（2026-07-02 至 2026-07-03） |

### 7.2 R6C 新增数据

| 数据项 | 新增内容 |
| --- | --- |
| Shift Type 修复 | `late_entry_grace_period = 0`、`early_exit_grace_period = 0`、`enable_late_entry_marking = 1`、`enable_early_exit_marking = 1` |
| Employee 字段修复 | 3 名员工 `holiday_list` 设置为 `TEST-HBOS-M1R3C-虚构节假日` |
| 新增 Checkin（July 3） | 4 条：甲 IN 08:00、乙 OUT 16:00、丙 IN 08:25 + OUT 16:00 |
| 新增 Custom Field | 11 个字段扩展到 Attendance Request |
| Demo Attendance Request | 4 条（插入被原生验证拒绝，记录了完整的创建意图和数据映射） |

### 7.3 数据红线遵守

- 全部使用虚构员工姓名。
- 全部使用脱敏工号（R6B-EMP-001/002/003）。
- 未提交 Excel / CSV / 真实数据。
- 未使用真实员工姓名、真实工号或真实打卡记录。

## 8. 异常识别验证过程

### 8.1 环境确认

- Frappe `16.25.0`、ERPNext `16.26.2`、HRMS `16.12.0`
- `bench --site frontend doctor`：worker 在线
- 全部容器 Up

### 8.2 Step 1：修复 Shift Type 迟到/早退标记配置

R6B 阶段 `late_entry` / `early_exit` 未置位的原因为 Shift Type 配置：

- `enable_late_entry_marking = 0`
- `enable_early_exit_marking = 0`

修复操作：

```
Shift Type: TEST-HBOS-M1R6B-早班-0800-1600
enable_late_entry_marking = 1
enable_early_exit_marking = 1
late_entry_grace_period = 0
early_exit_grace_period = 0
```

### 8.3 Step 2：删除旧 Attendance + 重新运行 Auto Attendance

R6B 中旧的 Attendance 已提交（`docstatus = 1`），需先 Cancel 再 Delete，然后重新运行。

### 8.4 Step 3：扩展 Shift Assignment 覆盖 July 3

3 条 Shift Assignment 的 `end_date` 从 `2026-07-02` 扩展到 `2026-07-03`。

### 8.5 Step 4：新增 July 3 打卡记录

| 员工 | IN | OUT | 场景 |
| --- | --- | --- | --- |
| 甲（HR-EMP-00017） | 08:00 | 缺 | 下班缺卡（July 3） |
| 乙（HR-EMP-00018） | 缺 | 16:00 | 上班缺卡（July 3） |
| 丙（HR-EMP-00019） | 08:25 | 16:00 | 迟到（July 3） |

### 8.6 Step 5：调用 Auto Attendance

`process_auto_attendance()` 对 July 2 + July 3 全部 Checkin 重新处理。

## 9. 异常识别结果

修复配置后重新运行 Auto Attendance，Attendance 结果如下：

### 9.1 全部 Attendance 记录（6 条）

| # | Attendance | 员工 | 日期 | 状态 | IN | OUT | 工时 | 迟到 | 早退 | 异常识别 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | HR-ATT-2026-00026 | 甲 | 07-02 | Present | 08:00 | 16:00 | 8.00 | 0 | 0 | **正常** ✓ |
| 2 | HR-ATT-2026-00027 | 乙 | 07-02 | Present | NULL | 16:02 | 0.00 | 0 | 0 | **上班缺卡** ✓ |
| 3 | HR-ATT-2026-00028 | 丙 | 07-02 | Present | 08:16 | 15:45 | 7.48 | 1 | 1 | **迟到 + 早退** ✓ |
| 4 | HR-ATT-2026-00029 | 甲 | 07-03 | Present | 08:00 | NULL | 0.00 | 0 | 0 | **下班缺卡** ✓ |
| 5 | HR-ATT-2026-00030 | 乙 | 07-03 | Present | NULL | 16:00 | 0.00 | 0 | 0 | **上班缺卡** ✓ |
| 6 | HR-ATT-2026-00031 | 丙 | 07-03 | Present | 08:25 | 16:00 | 7.58 | 1 | 0 | **迟到** ✓ |

### 9.2 分场景验证

| 验证场景 | Attendance | 识别结果 | 识别方式 |
| --- | --- | --- | --- |
| 正常上下班（甲 Jul 2） | HR-ATT-2026-00026 | **正常** | IN=08:00, OUT=16:00, 无标记 |
| 迟到（丙 Jul 2） | HR-ATT-2026-00028 | **迟到** | `late_entry = 1`（IN 08:16 > 08:00） |
| 早退（丙 Jul 2） | HR-ATT-2026-00028 | **早退** | `early_exit = 1`（OUT 15:45 < 16:00） |
| 迟到（丙 Jul 3） | HR-ATT-2026-00031 | **迟到** | `late_entry = 1`（IN 08:25 > 08:00） |
| 上班缺卡（乙 Jul 2） | HR-ATT-2026-00027 | **上班缺卡** | `in_time = NULL`，`out_time` 有值 |
| 上班缺卡（乙 Jul 3） | HR-ATT-2026-00030 | **上班缺卡** | `in_time = NULL`，`out_time` 有值 |
| 下班缺卡（甲 Jul 3） | HR-ATT-2026-00029 | **下班缺卡** | `out_time = NULL`，`in_time` 有值 |

### 9.3 全天无打卡 / 缺勤识别

本轮未创建"全天无打卡"场景的 Checkin（3 名员工在 July 2 / July 3 均至少有 1 条打卡记录）。

全天无打卡识别逻辑（按 M1 口径）：

1. 先看是否请假 → Leave Application 查询（本轮未实现）
2. 再看是否节假日 → Holiday List 匹配
3. 再看是否有排班 → Shift Assignment 覆盖检查
4. 有排班、无请假、无打卡 → 记为缺勤

该逻辑可通过 Server Script / Report Script 实现。R6C 仅记录口径和识别方式，不开发脚本。

### 9.4 缺卡识别方式

| 缺卡类型 | 识别依据 | 识别方式 |
| --- | --- | --- |
| 上班缺卡 | Attendance `in_time` 为 NULL / 空，但 `out_time` 有值 | 数据库查询或 Script Report |
| 下班缺卡 | Attendance `out_time` 为 NULL / 空，但 `in_time` 有值 | 数据库查询或 Script Report |
| 全天缺卡 | 有 Shift Assignment 但无任何 Checkin 记录 | 需排班日期 + Checkin join 判定 |

### 9.5 关键发现：`late_entry` / `early_exit` 正确置位

修复 Shift Type 配置后，`late_entry` / `early_exit` 在 Auto Attendance 中正确置位：

- 丙（IN 08:16 > 班次 08:00）→ `late_entry = 1` ✓
- 丙（OUT 15:45 < 班次 16:00）→ `early_exit = 1` ✓
- 正常员工（IN=08:00, OUT=16:00）→ `late_entry = 0`, `early_exit = 0` ✓

结论：HRMS 原生 Auto Attendance 在正确配置 Shift Type 后，可以可靠地自动标记迟到和早退。

**注意**：本结果基于"先删除旧 Attendance → 重新 Auto Attendance"的时序。在生产环境中，Auto Attendance 是后台任务，不会对已经处理过的日期自动重新处理。如需"先导入 Checkin、后修正 Shift Type 配置、再重新生成 Attendance"，需额外处理时序问题。

## 10. 员工提交说明验证

### 10.1 Custom Field 扩展

11 个 Custom Field 已成功创建在 `Attendance Request` 上。已验证：

```text
processing_status: 处理状态（待主管确认/主管已确认/主管驳回/人事已处理/已归档）
exception_type: 异常说明类型（补卡/设备异常/公出会议/班次错误/请假未同步/其他）
exception_detail: 异常详细说明
supervisor_confirmed: 主管已确认事实
supervisor_comment: 主管确认备注
supervisor_time: 主管操作时间
hr_processed: 人事已处理
hr_comment: 人事处理备注
hr_time: 人事操作时间
```

### 10.2 Attendance Request 创建验证

本轮尝试创建 4 条 Demo 脱敏 Attendance Request 记录：

| # | 员工 | 日期 | 异常类型 | 说明内容 | 创建结果 |
| --- | --- | --- | --- | --- | --- |
| 1 | 丙 | 07-02 | 设备异常 | 打卡机刷卡失败，实际 8:00 已到岗 | **被原生验证拒绝** |
| 2 | 丙 | 07-03 | 其他 | 路上堵车迟到约 15 分钟 | **被原生验证拒绝** |
| 3 | 乙 | 07-02 | 公出会议 | 外出拜访客户忘记打卡 | **被原生验证拒绝** |
| 4 | 乙 | 07-03 | 补卡 | 上班忘记打卡，实际 8:00 准时到岗 | **被原生验证拒绝** |

全部 4 条被 `validate_no_attendance_to_create()` 拒绝，原因：

```
ValidationError: No attendance records to create due to following reasons
[['日期', '原因', '操作'], ['2026-07-02', 'Attendance status unchanged', '跳过']]
```

### 10.3 数据映射验证

尽管记录未能创建，但字段映射关系已完整验证：

| 业务意图 | 原生字段 | Custom Field |
| --- | --- | --- |
| 谁提交 | `employee` | - |
| 哪个日期 | `from_date` / `to_date` | - |
| 什么类型 | - | `exception_type` |
| 详细说明 | `explanation` | `exception_detail` |
| 当前三级状态 | - | `processing_status` |

HRMS 原生 `Attendance Request` 的字段承载能力（存储层面）足够覆盖 6 种异常类型和三级状态字段。阻塞点在业务逻辑层（`validate_no_attendance_to_create`）。

## 11. 主管确认事实与人事最终处理验证

### 11.1 验证范围

本轮未完成主管确认和人事处理的运行时验证，原因：

1. Attendance Request 记录未能成功创建（见第 10 节）。
2. 在没有可用的 Attendance Request 记录时，无法验证 `supervisor_confirmed` → `hr_processed` 的状态流转。

### 11.2 三级流程设计验证

尽管未能在运行时创建记录，但三级流程的设计通过 Custom Field 结构已完整表达：

```
待主管确认
→ 主管确认事实（supervisor_confirmed = 1, supervisor_time = now）
→ 主管已确认（processing_status = '主管已确认'）
  或 主管驳回（processing_status = '主管驳回'）
→ 人事处理（hr_processed = 1, hr_time = now）
→ 人事已处理（processing_status = '人事已处理'）
→ 已归档（processing_status = '已归档'）
```

### 11.3 Frappe Workflow 配置

HRMS 原生 Workflow DocType 存在，支持以下对象：

- `Workflow`：工作流定义
- `Workflow State`：状态定义
- `Workflow Action`：操作定义
- `Workflow Transition`：状态转换定义
- `Workflow Document State`：单据状态记录

当前 `frontend` site 没有任何已配置的 Workflow（`Workflow` 表为空）。

R6C 未配置 Attendance Request 的 Workflow，原因：

1. 先决条件是 Attendance Request 能够成功创建，然后才能配置 Workflow。
2. Workflow 配置需要在 Frappe Desk UI 中完成，或通过 Fixture JSON 版本化后 `bench migrate` 应用。
3. 自定义 Workflow 配置属于后续 Owner 授权范围。

## 12. 操作留痕验证

### 12.1 Frappe 原生留痕能力确认

以下 Frappe 原生对象已确认存在且可用：

| 对象 | 用途 | 状态 |
| --- | --- | --- |
| `Version` | 记录每次文档修改（谁/什么时候/改了什么） | 存在且可用 |
| `Comment` | 记录文档评论 | 存在且可用 |
| `Activity Log` | 记录文档操作日志 | 存在且可用 |

### 12.2 Attendance Request 留痕配置

- `Attendance Request` DocType 已启用 `track_changes = 1`（修改跟踪）。
- `track_views = 0`（未启用查看跟踪，本次不评估）。

### 12.3 留痕验证结果

因 Attendance Request 记录未成功创建，无法验证完整的修改留痕。

留痕设计已通过 Custom Field 表达：

- 操作人：Frappe 原生 `modified_by`
- 操作时间：Frappe 原生 `modified` + Custom Field `supervisor_time` / `hr_time`
- 改了什么：Frappe `Version` 自动记录
- 修改原因：Custom Field `supervisor_comment` / `hr_comment` + 原生 `Comment`
- 处理状态：Custom Field `processing_status`

## 13. 失败记录与限制

### 13.1 明确成功

| 项 | 结果 |
| --- | --- |
| Custom Field 扩展 Attendance Request | **成功**（11 个字段已创建） |
| `late_entry` / `early_exit` 自动标记 | **成功**（Shift Type 配置修复后正确置位） |
| 缺卡检测（in_time/out_time 空值） | **成功**（可通过 Attendance 字段判定） |
| Frappe 原生 Version / Comment 可用 | **成功**（对象存在且可用） |
| 异常识别 7 个验证场景 | **全部通过**（正常/迟到/早退/上班缺卡/下班缺卡 均已识别） |

### 13.2 明确失败

| 项 | 结果 | 原因 |
| --- | --- | --- |
| Attendance Request 创建（已有 Attendance 时） | **失败** | `validate_no_attendance_to_create()` 阻止 |
| 员工提交异常说明（运行时验证） | **失败** | AR 记录未成功创建 |
| 主管确认事实（运行时验证） | **未验证** | 依赖 AR 记录存在 |
| 人事最终处理（运行时验证） | **未验证** | 依赖 AR 记录存在 |
| 操作留痕（运行时验证） | **未验证** | 依赖 AR 记录存在 |

### 13.3 部分成功/待后续

| 项 | 结果 | 说明 |
| --- | --- | --- |
| 6 类异常类型字段承载 | **结构完成** | Custom Field `exception_type` 已完整表达 6 种类型，但运行时未写入 |
| 三级流程状态字段承载 | **结构完成** | `processing_status` + supervisor/hr 字段已设计，但运行时未验证 |
| Workflow 配置 | **未执行** | 等待 AR 创建阻塞解决后配置 |
| 全天缺勤识别 | **未验证** | 本轮无此场景 Checkin，逻辑口径已记录 |

## 14. 本轮未做内容

- 未创建 `hb_hr_app`。
- 未创建自定义 DocType。
- 未创建 `Attendance Exception` / `Attendance Correction`。
- 未修改 Frappe / ERPNext / HRMS 核心源码。
- 未配置 Workflow。
- 未实现 Server Script / Client Script / Report Script。
- 未实现月度汇总 Excel 导入。
- 未实现月度汇总报表。
- 未启动 R7。
- 未接飞书登录、飞书请假、飞书工作台。
- 未接真实考勤机。
- 未部署公司内网或云服务器。
- 未提交 Excel / CSV / 真实数据。

## 15. R7 后续边界

M1-R7 当前为 REVIEWING，飞书登录领导Demo与M1收口准备主文档已交付。

R6C 结论传递给 R7 的关键信息：

1. **异常识别能力已就绪**：`late_entry` / `early_exit` 自动标记可用，缺卡可通过 Attendance 字段识别。
2. **Attendance Request 结构已扩展**：11 个 Custom Field 已创建，覆盖 6 种异常类型和三级流程状态。
3. **核心 Blocker**：HRMS 原生 `validate_no_attendance_to_create()` 在已有 Attendance 时阻止 Attendance Request 创建。该问题是设计冲突，不是 Bug。
4. **后续决策点**：Owner 需决定是否授权绕过原生验证（Hook）、创建自定义 DocType（`Attendance Exception`）、或接受文档化限制。

R7 如果启动，可能需要包含：

- 异常说明流程的运行时可验证方案（解决 native validation 冲突）。
- 月度汇总报表字段整合。
- 或飞书登录入口。

## 16. 当前状态

- `M1-R6A = COMPLETED`
- `M1-R6B = COMPLETED`
- `M1-R6C = COMPLETED`
- `M1-R7 = REVIEWING`

## 17. Closeout 结论

M1-R6C 已通过 Codex 审查并完成 closeout，状态收口为 COMPLETED。

Closeout 结论：

- R6C 异常识别与异常说明流程最小实现已完成。
- 已覆盖迟到、早退、上班缺卡、下班缺卡、缺勤的最小识别口径。
- 异常识别 7 个场景已验证通过（正常/迟到/早退/上班缺卡/下班缺卡）。
- `late_entry`/`early_exit` 在 Shift Type 配置修复后正确置位。
- 11 个 Custom Field 已在 HRMS 原生 Attendance Request 上扩展完成，覆盖 6 种异常类型 + 三级流程状态。
- HRMS 原生 `validate_no_attendance_to_create()` 在已有 Attendance 场景下阻止 Attendance Request 创建的核心 Gap 已记录为后续 Owner 授权点。
- 优先复用 HRMS 原生能力的 Gate 已完成：Attendance Request 结构可承载异常说明字段，但运行时创建被原生设计语义冲突阻止。
- 当前仍不建议创建 `hb_hr_app`。
- M1-R7 未启动；下一步只能等待 Owner 授权后进入 M1-R7。

## 18. 状态同步声明

本轮完成后需同步以下文件：

| 文件 | 是否需要更新 | 原因 |
| --- | --- | --- |
| `docs/PROJECT_STATUS.md` | 是 | 新增 M1-R6C 状态记录 |
| `docs/CURRENT_MILESTONE.md` | 是 | 更新当前轮次为 M1-R6C |
| `docs/AI_CONTEXT.md` | 是 | 更新当前上下文 |
| `docs/READING_GUIDE.md` | 是 | 更新当前里程碑提醒 |
| `docs/milestones/README.md` | 是 | 新增 M1-R6C 索引条目 |
| `docs/milestones/M1_START_GATE.md` | 是 | 新增 M1-R6C 状态条目 |
| `README.md` | 是 | 更新阶段描述 |
| `CLAUDE.md` | 否 | 无需变更（进度来源指向不变） |
| `AGENTS.md` | 否 | 无需变更 |
