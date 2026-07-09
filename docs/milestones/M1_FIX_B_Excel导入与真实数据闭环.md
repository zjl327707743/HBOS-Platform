# M1-FIX-B：Excel 导入与真实本地数据闭环

项目名称：新乡海滨智能运营管理平台。

状态：REVIEWING。

执行日期：2026-07-09。

## 1. 本轮目标

M1-FIX-B 是代码实现轮，只补齐 Excel 导入与真实本地数据闭环。本轮不启动 M1-FIX-C/D/E，不启动 M2，不做 closeout，不触发 Codex 审查。

本轮完成：

- 创建轻量自定义 App：`hb_attendance_app`。
- 创建导入批次日志 DocType：`HBOS Attendance Import Log`。
- 创建最小 Workspace：`海滨考勤工作台`。
- 支持读取本地 `.xlsx` 月度汇总表。
- 支持员工工号优先匹配，未匹配时本地创建 Employee。
- 支持 Department 不存在时本地创建。
- 将月度汇总表转换生成 Demo `Employee Checkin`。
- 尝试 HRMS 原生 Auto Attendance。
- 必要时使用受控 fallback 创建 `Attendance`，并在日志中标记。
- 在导入日志中记录统计、字段识别摘要、异常统计摘要和失败摘要。

本轮未做：

- 未创建 `HBOS Monthly Attendance Summary`。
- 未创建 `HBOS Attendance Exception`。
- 未实现异常三级流程。
- 未接飞书 OAuth。
- 未配置飞书 App ID / Secret。
- 未修改 Frappe / ERPNext / HRMS 核心源码。
- 未提交真实 Excel / CSV / 真实员工清单 / 导入产物。
- 未启动 M2。

## 2. Git Gate

启动前检查结果：

| 检查项 | 结果 |
| --- | --- |
| 当前分支 | `main` |
| HEAD | `37b662845b22ac1b5b1941e51572a0df6b780a66` |
| `git status` | clean |
| `main` 相对 `origin/main` | ahead 1 |
| 未跟踪真实 Excel / CSV | 无未跟踪；真实 Excel 为 ignored |
| `.gitignore` 覆盖真实 Excel | `docs/data/*.xlsx` 覆盖 |

## 3. 数据源口径

本轮本地使用 Owner 授权文件：

`docs/data/月度汇总表_20260701_20260703.xlsx`

该文件只用于本地导入验证，不提交 Git，不在本文档中展开真实姓名、工号或人员清单。

## 4. Excel 类型识别

识别结果：

| 项 | 结果 |
| --- | --- |
| 工作表 | `月度汇总表_20260701_20260703` |
| 物理行数 | 1265 |
| 员工身份行 | 824 |
| 表头行 | 第 2 行 |
| 身份字段 | `姓名`、`工号`、`部门` |
| 汇总字段 | `请假时长(小时)`、`应出勤天数`、`实际出勤天数`、`计薪时长 (小时)`、`迟到次数`、`早退次数`、`旷工天数` |
| 日列 | `周三 26-07-01`、`周四 26-07-02`、`周五 26-07-03` |
| 覆盖期间 | 2026-07-01 至 2026-07-03 |
| 类型判定 | 月度汇总表 / Demo 转换导入 |

结论：该文件不是一行一条原始打卡流水。本轮按“月度汇总表转换生成 Demo Checkin / Attendance”处理，不伪称为真实打卡机原始流水。

## 5. 员工匹配规则

实现优先级：

1. `Employee.employee_number`
2. `Employee.attendance_device_id`
3. 姓名唯一匹配
4. 本地 Demo 创建 Employee

创建 Employee 时：

- 使用现有默认 Company。
- Department 不存在时创建。
- `employee_number` 与 `attendance_device_id` 优先使用 Excel 工号。
- 使用固定本地占位生日 `1990-01-01` 满足 HRMS 必填校验，不来自真实 Excel。
- 不删除既有 Employee。
- 不覆盖既有 Employee 关键字段。

## 6. 导入与生成策略

本轮导入方法位于：

`hb_attendance_app.hbos_attendance.doctype.hbos_attendance_import_log.hbos_attendance_import_log`

提供：

- `preview_import`
- `run_import`

转换策略：

- 解析 `.xlsx` OOXML，支持 `inlineStr`、`sharedStrings` 和普通值。
- 月度汇总日列中的时间 token 转为 Demo Checkin。
- 多个时间 token 使用首个作为 IN、最后一个作为 OUT。
- 单个时间 token 使用可解释的合成 IN/OUT 规则生成 Demo Checkin，并在异常摘要中标记“单时间点转换”。
- 同一员工、同一时间、同一 `log_type` 已存在时跳过并计入 `skipped_duplicates`。
- 已存在当日 active Shift Assignment 时复用既有排班，避免重复排班失败。

## 7. Auto Attendance 与 fallback

本轮创建 4 个 M1-FIX-B Demo Shift Type：

- `HBOS-M1-FIX-B-白班-0800-1600`
- `HBOS-M1-FIX-B-中班-1600-0000`
- `HBOS-M1-FIX-B-夜班-0000-0800`
- `HBOS-M1-FIX-B-跨夜班-2000-0400`

导入会调用 HRMS 原生 `Shift Type.process_auto_attendance()`。

首次全量导入中：

- Auto Attendance 已实际触发。
- fallback 已使用。
- fallback 用于补齐 Auto Attendance 未覆盖但本地 Demo 需要展示的 Attendance。

不能把 fallback 写成“Auto Attendance 已完全跑通”。本轮口径为：Auto Attendance 已尝试并生成部分结果，fallback 确实参与了本地 Demo 闭环。

## 8. 验证统计

### Preview

导入日志：`HBOS-ATT-IMP-2026-00001`

| 指标 | 结果 |
| --- | ---: |
| 物理行数 | 1265 |
| 员工身份行 | 824 |
| 覆盖日期 | 2026-07-01 至 2026-07-03 |
| 写入数据 | 否 |

### 5 行烟测

导入日志：`HBOS-ATT-IMP-2026-00003`

| 指标 | 结果 |
| --- | ---: |
| 成功行数 | 5 |
| 失败行数 | 0 |
| 创建 Employee | 5 |
| 创建 Checkin | 28 |
| 创建 Attendance | 15 |
| 使用 Auto Attendance | 是 |
| 使用 fallback | 否 |

### 首次全量导入

导入日志：`HBOS-ATT-IMP-2026-00004`

| 指标 | 结果 |
| --- | ---: |
| 匹配员工行 | 824 |
| 创建 Employee | 745 |
| 创建 Checkin | 2777 |
| 创建 Attendance | 2235 |
| 跳过重复 Checkin | 43 |
| 失败行 | 24 |
| 使用 Auto Attendance | 是 |
| 使用 fallback | 是 |

首次全量导入的 24 个失败行原因均为 HRMS 已存在当日 active Shift Assignment 后阻止重复排班。随后已修复为复用既有排班。

### 最终幂等复跑

导入日志：`HBOS-ATT-IMP-2026-00005`

| 指标 | 结果 |
| --- | ---: |
| 匹配员工行 | 824 |
| 成功行数 | 824 |
| 失败行数 | 0 |
| 新增 Employee | 0 |
| 新增 Checkin | 75 |
| 新增 Attendance | 0 |
| 跳过重复 Checkin | 2863 |
| 使用 Auto Attendance | 是 |
| 使用 fallback | 否 |

最终本地数据库对象计数：

| DocType | 当前数量 |
| --- | ---: |
| Employee | 769 |
| Employee Checkin | 2933 |
| Attendance | 2281 |
| HBOS Attendance Import Log | 5 |

## 9. 异常识别摘要

最终幂等复跑日志中的异常摘要：

| 类型 | 次数 |
| --- | ---: |
| 跨夜班 | 353 |
| 单时间点转换 | 841 |
| 迟到 | 1101 |
| 早退 | 294 |
| 全天缺勤 | 1003 |
| 正常出勤 | 13 |

说明：由于源文件是月度汇总表而非原始流水，异常摘要用于本地 Demo 和导入反馈，不等同于真实打卡机流水精确判责结果。

## 10. 页面体验路径

Owner 可通过 Frappe Desk 体验：

1. 打开 `http://localhost:8081/app`。
2. 进入 Workspace：`海滨考勤工作台`。
3. 打开 `考勤导入日志` 查看 `HBOS Attendance Import Log`。
4. 打开 `HBOS-ATT-IMP-2026-00005` 查看最终成功导入统计。
5. 打开 `HBOS-ATT-IMP-2026-00004` 查看首次全量创建统计与 fallback 标记。
6. 打开 `Employee Checkin` 查看导入/转换生成的 Checkin。
7. 打开 `Attendance` 查看生成的 Attendance。

## 11. 环境修复说明

本轮创建 `hb_attendance_app` 后需要重建 Frappe 服务以挂载仓库内 app。由于原 compose 未持久化 `apps/`，重建后运行态 HRMS 源码不可见，但 site 仍安装 `hrms`。为恢复环境并提高可复现性，本轮新增：

- `runtime/` ignored 目录，用于本地运行态 app 源码。
- `runtime/apps/hrms` bind mount 到 Frappe Python 服务。
- `PYTHONPATH` 指向 `apps/hrms` 与 `apps/hb_attendance_app`。

`runtime/` 已加入 `.gitignore`，不提交 HRMS 第三方源码。

## 12. 已知限制

- Owner Excel 是月度汇总表，不是原始打卡流水。
- 单时间点日列需要合成另一侧 Checkin，已在异常摘要中标记。
- 首次全量导入使用过 fallback，后续仍需继续补齐更稳定的原生 Auto Attendance 路径。
- 本轮未实现异常三级流程，留给 M1-FIX-C。
- 本轮未实现完整考勤工作台、月报与领导 Demo，留给 M1-FIX-D。
- 本轮未实现飞书 OAuth，留给 M1-FIX-E。

## 13. 状态口径

```
M1-FIX = IN_PROGRESS
M1-FIX-A = REVIEWING
M1-FIX-B = REVIEWING
M1-FIX-C/D/E = PLANNED
M2 = NOT STARTED / WAITING OWNER AUTHORIZATION
```

本轮不 closeout，等待 Owner 验收。
