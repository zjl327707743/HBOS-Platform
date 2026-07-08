# M1-R6B：脱敏打卡流水导入最小实现

项目名称：新乡海滨智能运营管理平台。

状态：COMPLETED。

执行日期：2026-07-09。

Closeout 日期：2026-07-09。

## 1. 本轮定位

M1-R6B 是 **脱敏原始打卡流水导入最小实现轮**。本轮已由 Owner 授权从 M1-R6A closeout 后进入 R6B。

本轮只做：

1. 识别 Owner 提供 Excel 的真实类型。
2. 确认该文件能否支撑原始打卡流水导入。
3. 固定 Demo 脱敏打卡流水模板。
4. 确认 Employee 匹配规则。
5. 将脱敏原始打卡流水写入 HRMS 原生 `Employee Checkin`。
6. 触发或记录 Auto Attendance 处理结果。
7. 完成最小验证并记录结果。

本轮不做：

- 不启动 M1-R6C。
- 不启动 M1-R7。
- 不做完整异常说明流程。
- 不做员工提交说明、主管确认事实或人事最终处理。
- 不实现月度汇总 Excel 导入。
- 不把月度汇总 Excel 当作原始打卡流水。
- 不提交原始 Excel、脱敏前 Excel、脱敏 Excel 或 CSV。
- 不提交真实人员数据。
- 不接飞书登录、飞书请假、飞书工作台。
- 不接真实考勤机自动同步。
- 不部署公司内网或云服务器。
- 不启动大型 Vue 前端。
- 不创建 `hb_hr_app`。
- 不创建自定义 DocType。
- 不修改 Frappe / ERPNext / HRMS 核心源码。

## 2. 读取文件清单

本轮按轻量范围读取：

- `README.md`
- `CLAUDE.md`
- `AGENTS.md`
- `docs/AI_CONTEXT.md`
- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/READING_GUIDE.md`
- `docs/milestones/README.md`
- `docs/milestones/M1_START_GATE.md`
- `docs/milestones/M1_R6A_Excel导入与异常流程落地方案.md`
- `docs/data/月度汇总表_20260701_20260703.xlsx`（仅做本地结构识别，不提交）

未递归读取 `docs/`，未读取 `docs/archive`、`docs/research`、`docs/legacy`。

## 3. Owner 提供 Excel 文件分类 Gate

文件路径：

`docs/data/月度汇总表_20260701_20260703.xlsx`

检查结果：

| 检查项 | 结果 |
| --- | --- |
| 文件名 | `月度汇总表_20260701_20260703.xlsx` |
| 是否位于仓库内 | 是，位于 `docs/data/` |
| 是否被 Git 跟踪 | 否，`git ls-files -- docs/data/月度汇总表_20260701_20260703.xlsx` 无输出 |
| `.gitignore` 覆盖 | 本轮已补充 `docs/data/*.xlsx`、`docs/data/*.xls`、`docs/data/*.csv` |
| 是否包含真实姓名 / 工号 / 部门 | 是。表头含 `姓名`、`工号`、`部门`，且检测到 824 行同时含身份列数据；具体人员值未写入文档 |
| 工作表 | `月度汇总表_20260701_20260703` |
| 结构识别方式 | 读取 OOXML 结构，不输出真实人员值 |
| 表结构 | 1265 行、13 列 |
| 汇总字段 | `姓名`、`工号`、`部门`、`请假时长(小时)`、`应出勤天数`、`实际出勤天数`、`计薪时长(小时)`、`迟到次数`、`早退次数`、`旷工天数` |
| 每日列 | `周三 26-07-01`、`周四 26-07-02`、`周五 26-07-03` |
| 每日时间形态 | K-M 每日列共 2107 个非空时间形态单元格；每个单元格检测到 1 个时间 token |
| 最终判定 | **混合表**：月度 / 日度汇总字段 + 每日时间列 |
| 是否可直接用于 R6B 导入验证 | 否 |

判定说明：

该文件不是标准原始打卡流水模板。它同时包含人员身份、汇总指标和每日统计列。每日列虽然存在时间形态内容，但每个单元格只有一个时间 token，缺少稳定的 `IN / OUT` 字段，也不是一行一条打卡记录。因此它不能直接作为 `Employee Checkin` 导入源。

可作为 R6B 参考的字段：

- 员工匹配参考：`工号`、`姓名`、`部门`。
- 业务口径参考：`应出勤天数`、`实际出勤天数`、`请假时长(小时)`、`计薪时长(小时)`、`迟到次数`、`早退次数`、`旷工天数`。
- 每日统计参考：`周三 26-07-01`、`周四 26-07-02`、`周五 26-07-03`。

不能直接用于 `Employee Checkin` 的原因：

- 含真实人员身份，不能导入或提交。
- 不是逐条打卡流水。
- 缺少稳定的 `IN / OUT` 字段。
- 每日时间列需要脱敏、拆分和方向判断后才可能转换为原始流水。
- 月度 / 日度汇总 Excel 导入不在 R6B 范围内。

## 4. R6A Gate 结论继承

R6A 已明确：

```text
原始打卡流水导入 ≠ 月度汇总 Excel 导入
```

R6B 本轮只承接原始打卡流水最小导入链路：

```text
脱敏原始打卡流水
→ Employee 匹配
→ Employee Checkin
→ Auto Attendance 或处理记录
→ 最小验证结果
```

R6A 中关于月度汇总导入、导入批次 DocType、异常说明流程和完整 R6 验收的内容，不在本轮实现。

## 5. 原始打卡流水导入范围

R6B 固定的最小原始打卡流水模板：

| 字段 | 类型 | 目标 |
| --- | --- | --- |
| `employee_match_key` | 脱敏工号 / `attendance_device_id` | 匹配 `Employee.attendance_device_id` |
| `employee_name_demo` | 虚构姓名 | 仅用于人工核对，不作为真实人员数据 |
| `department_demo` | Demo 部门 | 可使用虚构配置或真实组织层级名，但不保留真实人员身份 |
| `checkin_time` | Datetime | 映射 `Employee Checkin.time` |
| `log_type` | `IN` / `OUT` | 映射 `Employee Checkin.log_type` |
| `shift` | Shift Type 名称 | 映射 `Employee Checkin.shift` |
| `source_file` | 来源标记 | 本轮映射到 `Employee Checkin.device_id` |
| `skip_auto_attendance` | 0 / 1 | 本轮固定为 `0` |

本轮 Demo 未保存任何 Excel / CSV 文件。Demo 原始流水只作为一次性内存数据写入本地 Frappe site。

## 6. Demo 脱敏数据边界

本轮本地验证使用：

- 3 名虚构员工。
- 脱敏工号：`R6B-EMP-001`、`R6B-EMP-002`、`R6B-EMP-003`。
- 新 R6B 班次：`TEST-HBOS-M1R6B-早班-0800-1600`。
- 复用既有虚构配置底座：
  - Company：`TEST-HBOS-M1R3C-虚构公司`
  - Department：`TEST-HBOS-M1R3C-生产一部 - R3C`
  - Holiday List：`TEST-HBOS-M1R3C-虚构节假日`

复用原因：尝试创建独立 R6B Company 时，ERPNext 默认公司初始化会触发 `Parent Department: All Departments` 链接校验问题；该错误发生在显式 commit 前，未留下 R6B 残留。为减少副作用，本轮复用既有虚构公司 / 部门 / 节假日，仅新增 R6B 班次、虚构员工、排班和打卡记录。

未使用真实员工姓名、真实工号或未脱敏 Excel 数据。

## 7. Employee Checkin 字段映射

| Employee Checkin 字段 | R6B Demo 来源 | 验证结果 |
| --- | --- | --- |
| `employee` | `attendance_device_id` 匹配 Employee | 成功 |
| `time` | Demo `checkin_time` | 成功 |
| `log_type` | Demo `IN` / `OUT` | 成功 |
| `shift` | `TEST-HBOS-M1R6B-早班-0800-1600` | 成功 |
| `device_id` | `M1-R6B-DEMO-RAW-CHECKIN` | 成功 |
| `skip_auto_attendance` | 固定 `0` | 成功 |

同一员工同一天多次打卡处理口径：

- 原始流水每条打卡写入一条 `Employee Checkin`。
- 同一员工同一天有多条记录时，依赖 `log_type` 和 Shift Type 的 `Strictly based on Log Type in Employee Checkin` 规则判断 IN / OUT。
- 本轮不做复杂多次打卡清洗；多次打卡的去重、取最早 IN / 最晚 OUT 等规则留到 R6C 或后续导入增强。

## 8. Employee 匹配规则

本轮优先匹配：

1. `Employee.attendance_device_id` = 脱敏工号。
2. 若后续文件没有工号，则再评估 `Employee.name` 或其他字段。

R6B Demo 只验证 `attendance_device_id` 匹配，不使用真实姓名匹配。

## 9. Data Import / 导入方式选择

R6A 判定 Frappe / HRMS 原生 Data Import 理论可导入 `Employee Checkin`。

本轮实际执行选择：

- 不上传 Owner Excel。
- 不保存任何 Demo Excel / CSV。
- 不创建正式导入模块。
- 使用一次性 bench 执行代码，将脱敏 Demo 原始打卡流水写入 HRMS 原生 `Employee Checkin`，再调用 Shift Type 原生 `process_auto_attendance()`。

原因：

- Owner 文件被判定为混合表且含真实身份，不能直接导入。
- 本轮重点是验证 `Employee Checkin → Auto Attendance → Attendance` 最小闭环。
- 不提交脱敏 CSV / Excel，避免误把样例数据纳入仓库。
- 后续如 Owner 授权，可在 M1-R6C 或后续专门导入验证轮继续用 Frappe Data Import UI / Data Import DocType 做同模板上传验证。

## 10. 最小验证过程

本轮在本地 Docker / Frappe site `frontend` 中执行。

环境确认：

- `frappe 16.25.0`
- `erpnext 16.26.2`
- `hrms 16.12.0`
- `bench --site frontend doctor`：worker 在线。

验证数据：

| 场景 | Demo 原始打卡 |
| --- | --- |
| 正常上下班 | `08:00 IN`、`16:00 OUT` |
| 上班缺卡 | `16:02 OUT` |
| 迟到 + 早退候选 | `08:16 IN`、`15:45 OUT` |

执行结果：

| 指标 | 结果 |
| --- | --- |
| Demo 员工 | 3 |
| R6B Shift Type | 1 |
| Shift Assignment | 3 |
| Employee Checkin | 5 |
| Auto Attendance 调用 | `process_auto_attendance completed` |
| Attendance 生成 | 3 |
| 导入成功数 | 5 |
| 导入失败数 | 0 |
| 失败原因记录方式 | 本轮无失败；后续正式 Data Import 使用 Frappe Data Import 错误结果，正式导入入口再评估批次日志 |

## 11. 导入结果

`Employee Checkin` 写入结果：

| 场景 | 写入条数 | 是否关联 Attendance |
| --- | ---: | --- |
| 正常上下班 | 2 | 是 |
| 上班缺卡 | 1 | 是 |
| 迟到 + 早退候选 | 2 | 是 |

数据库复核：

```text
r6b_employees = 3
r6b_checkins = 5
r6b_attendance = 3
```

## 12. Auto Attendance 处理结果

Attendance 结果：

| 场景 | Attendance 状态 | in_time | out_time | working_hours | late_entry | early_exit |
| --- | --- | --- | --- | ---: | ---: | ---: |
| 正常上下班 | Present | `08:00` | `16:00` | 8.00 | 0 | 0 |
| 上班缺卡 | Present | 空 | `16:02` | 0.00 | 0 | 0 |
| 迟到 + 早退候选 | Present | `08:16` | `15:45` | 7.48 | 0 | 0 |

结论：

- `Employee Checkin → Auto Attendance → Attendance` 最小链路通过。
- 单边 OUT 能生成 Attendance，并保留 `in_time` 为空、`out_time` 有值的事实，可作为上班缺卡候选。
- 迟到 / 早退候选能生成 Attendance，但 HRMS 本轮配置下 `late_entry` / `early_exit` 未置位。

## 13. 失败记录与限制

限制：

1. Owner Excel 是混合表，不能直接作为 R6B 原始打卡流水导入源。
2. 本轮未验证 Frappe Data Import UI 上传流程，只验证了字段映射后的 `Employee Checkin` 写入与 Auto Attendance 链路。
3. 新建独立 R6B Company 触发 ERPNext 默认部门初始化校验问题，未继续扩大处理，改用既有虚构配置底座。
4. HRMS 原生 Auto Attendance 未自动置位迟到 / 早退字段；需后续复核 Shift Type 相关字段、HRMS 版本规则或补充报表计算。
5. 缺卡仅通过 Attendance 的 `in_time` / `out_time` 空值事实识别，本轮不实现完整异常说明流程。

## 14. 本轮未做内容

- 未提交 Owner Excel。
- 未提交任何 Excel / CSV。
- 未实现月度汇总 Excel 导入。
- 未把月度汇总 / 混合 Excel 当作原始打卡流水。
- 未创建 App。
- 未创建自定义 DocType。
- 未写正式导入模块。
- 未写正式异常流程代码。
- 未启动 R6C。
- 未启动 R7。
- 未接飞书登录、飞书请假、飞书工作台。
- 未接真实考勤机自动同步。
- 未修改 Frappe / ERPNext / HRMS 核心源码。
- 未部署公司内网或云服务器。

## 15. R6C 后续边界

R6C 仍保持 PLANNED / 待授权 / 未启动。

R6C 可在 Owner 授权后继续：

- 复核迟到 / 早退字段未置位原因。
- 基于 Attendance + Employee Checkin 形成异常候选展示。
- 验证 Attendance Request 或后续自定义异常对象的最小流程。
- 做员工提交说明、主管确认、人事最终处理和留痕。
- 整合月度汇总报表字段。

R6C 不因 R6B 完成而自动启动。

## 16. 当前状态

- `M1-R6A = COMPLETED`
- `M1-R6B = COMPLETED`
- `M1-R6C = PLANNED / 待授权 / 未启动`
- `M1-R7 = REVIEWING`

## 17. Closeout 结论

M1-R6B 已通过 Codex 审查并完成 closeout，状态收口为 COMPLETED。

Closeout 结论：

- R6B 脱敏打卡流水导入最小闭环已完成。
- Owner 提供 Excel 已判定为混合表，不能直接作为 `Employee Checkin` 导入源。
- 原始 Excel 未提交，`docs/data/` 数据文件已由 `.gitignore` 防误提交。
- `Employee Checkin` 最小写入验证完成。
- Auto Attendance 已处理并生成 Attendance。
- M1-R6C / M1-R7 未启动；下一步只能等待 Owner 授权后进入 M1-R6C。
