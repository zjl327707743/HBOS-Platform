# M1-FIX-B5：导入数据链路核查与报表口径收敛

状态：REVIEWING。

执行日期：2026-07-10。

## 本轮定位

M1-FIX-B5 不 closeout B3 / B4，不进入 M1-FIX-C / D / E，不实现异常三级流程、不实现飞书 OAuth、不做领导 Demo。本轮只处理 Owner 真实 UI 验收发现的数据链路和报表口径混乱问题：先用真实数据库核查导入数据在哪里，再把人事主入口收敛到 HBOS 权威报表和月度暂存报表。

## Git Gate

| 检查项 | 结果 |
| --- | --- |
| 当前分支 | `main` |
| 本轮开始 HEAD | `49d341826c97d4f57557581ab557ee8c1bacea2a` |
| 最新提交 | `fix: 完成 M1-FIX-B4 考勤模块入口收敛` |
| 工作区 | 开始前 clean |
| `main` 与 `origin/main` | `main` ahead 8 / behind 0 |
| 本地敏感/真实数据 | `.env` 与 `docs/data/月度汇总表_20260701_20260703.xlsx` 存在，均不得提交；本轮只输出聚合计数，不输出真实员工明细 |

## 数据链路核查表

| 检查项 | 真实数据库结果 |
| --- | --- |
| 当前 HRMS Employee 数 | 769 |
| 导入创建 / 匹配 Employee | 月度暂存 JSON 共 1647 行、750 个唯一员工键；1647 行均按 `employee_number` 匹配到 HRMS Employee；本轮核查未发现未匹配行。导入日志累计 `created_employees=0`，说明当前数据主要匹配既有 HRMS Employee |
| 2026-07 Employee Checkin 数 | 9403 |
| Checkin Company 分布 | `健康元新乡海滨` 9394；`TEST-HBOS-M1R3C-虚构公司` 9 |
| Checkin Department 分布 | 覆盖多个 HRMS Department；数量最高的分布包括无菌倒班、2车间工艺组、倒班二班、倒班一班、倒班三班等。最终报告只记录聚合，不输出员工行级信息 |
| HBOS 导入相关 Checkin | 9394 条来自 HBOS 设备标记：`HBOS-M1-FIX-B-MONTHLY-ADAPTER` 6506，`HBOS-M1-FIX-B-REWORK` 2888。当前历史 Checkin 尚无 `hbos_import_log` 字段，不能逐条精确反查批次；B5 已补字段用于后续原始流水批次追踪 |
| 2026-07 Attendance 数 | 6768 |
| Attendance docstatus | 6768 条均为 docstatus=1 |
| Attendance Company 分布 | `健康元新乡海滨` 4518；Company 未设置 2250 |
| HRMS Auto Attendance 来源 | 当前已标记 `hbos_source_type = HRMS Auto Attendance` 的 893 条；另有 5875 条未标记 / 既有结果 |
| HBOS fallback / HBOS import 来源 | 当前按 `hbos_source_type = HBOS fallback` 或 `hbos_fallback_generated=1` 统计为 0；历史 2250 条 Company 为空的 Attendance 来自早期导入兜底路径，字段标记不完整，B5 不回写历史业务数据 |
| 月度汇总暂存行数 | 1647 行 |
| 月度汇总暂存对应 Import Log | `HBOS-ATT-IMP-2026-00020` 824 行；`HBOS-ATT-IMP-2026-00021` 823 行 |
| HRMS 月度考勤表为什么无数据 | HRMS 原生 `Monthly Attendance Sheet` 只读 submitted `Attendance`，且强制按 Company 过滤。当前用户默认 Company 为 `健康元新乡海滨 (Demo)`，该公司 2026-07 Attendance 为 0；选择正确公司 `健康元新乡海滨` 时，原生月度表返回 1561 行 |
| HBOS 打卡流水为什么像只有部分数据 | B4 前报表 SQL 固定 `limit 500`，真实 2026-07 Checkin 有 9403 条，因此默认只显示前 500 条会误导 Owner |
| HBOS 考勤结果为什么和 HRMS 原生结果不一致 | B4 前报表同样固定 `limit 500`；且 HBOS 报表显示 `docstatus < 2`，HRMS 月度表只取 `docstatus = 1` 且按 Company 过滤。历史 Attendance 中 2250 条 Company 为空，会被 HRMS 月度表的 Company 条件排除 |
| 当前导入页导入成功后看哪里 | 原始打卡流水：`HBOS 打卡流水`；考勤结果：`HBOS 考勤结果`；月度汇总表：`HBOS 月度汇总暂存（对账）`；批次记录：`考勤导入日志` |

## 根因与修复

1. HRMS 原生“月度考勤表”不是 M1 主报表。它依赖 submitted Attendance、正确 Company 和 HRMS 原生字段展示；当前用户默认公司是 Demo，公司条件导致 2026-07 空表。本轮在 UI 和文档中将 HRMS 原生入口降级为技术核查入口。
2. HBOS 打卡流水 / 考勤结果被 `limit 500` 截断。本轮移除固定截断，并新增日期、员工、部门、导入批次 / 来源过滤器。
3. “月度汇总 / 对账暂存”不应打开普通 Import Log 列表。本轮新增 `HBOS 月度汇总暂存（对账）` Script Report，专门读取 `monthly_summary_staging` JSON，明确不写入 Employee Checkin、不触发 Auto Attendance。
4. 历史 Employee Checkin 没有 HBOS 批次字段，只能通过 `device_id` 聚合识别 HBOS 导入/适配来源。本轮在 `after_migrate` 为 Employee Checkin 增加 `hbos_import_log`、`hbos_source_type`、`hbos_calc_version`，后续原始流水导入会写入批次，不回写历史业务数据。
5. 导入页摘要过于笼统。本轮区分月度汇总暂存和原始流水导入：月度汇总显示暂存员工数 / 月度行数 / 不写入 Checkin / 不触发 Auto Attendance；原始流水显示写入打卡、重复跳过、Attendance 生成结果。

## 验证结果

| 验证项 | 结果 |
| --- | --- |
| Python 编译检查 | 通过 |
| 离线回归测试 | `PYTHONPATH=apps/hb_attendance_app python -m unittest discover -s apps/hb_attendance_app/tests`，16 项通过 |
| JSON fixture 检查 | Workspace 与 3 个 Report JSON 均可解析 |
| `bench --site frontend migrate` | 通过；已执行 `after_migrate`，同步 Workspace、Workspace Sidebar、Desktop Icon、Custom Field 与 Report |
| `bench --site frontend clear-cache` / `clear-website-cache` | 通过 |
| `bench build --app hb_attendance_app` | 未通过；当前 Frappe / ERPNext 容器内均无 `node`，报错 `node: not found`。本轮 Page / Report JS 已通过 migrate 和 Desk 运行态加载验证 |
| 报表空条件执行 | `打卡流水` 9447 行；`考勤结果` 6793 行；`HBOS 月度汇总暂存（对账）` 1647 行 |
| 报表 2026-07 执行 | `打卡流水` 9403 行；`考勤结果` 6768 行；`HBOS 月度汇总暂存（对账）` 1647 行 |
| 月度暂存分批执行 | `HBOS-ATT-IMP-2026-00020` 为 824 行；`HBOS-ATT-IMP-2026-00021` 为 823 行 |
| 运行态对象检查 | Workspace 存在且 `module = HBOS Attendance`；Page `hbos-attendance-import` 存在；3 个 Script Report 存在；Employee Checkin 已有 `hbos_import_log`、`hbos_source_type`、`hbos_calc_version` |
| Sidebar / Desktop Icon | `Workspace Sidebar` 中存在 `海滨考勤` 与 `海滨考勤工作台`；Desktop Icon `海滨考勤` 使用 `/assets/hb_attendance_app/hbos-attendance-logo.svg`、`bg_color = blue`、`hidden = 0`，不再是灰色占位 |
| 浏览器验证 | Playwright 登录真实 Desk 后验证 `/app/海滨考勤工作台` 与 `/app/hbos-attendance-import`；工作台、导入页、返回路径、HBOS 报表按钮和月度暂存按钮均可见 |
| HRMS 月度表口径复核 | `健康元新乡海滨 (Demo)` 在 2026-07 Attendance 为 0；正确公司 `健康元新乡海滨` 在 2026-07 submitted Attendance 为 4518 |

## 用户主入口口径

```text
海滨考勤工作台
-> 导入考勤机导出表
-> 考勤导入日志
-> HBOS 打卡流水
-> HBOS 考勤结果
-> 月度汇总 / 对账暂存
```

HRMS 原生入口只作为技术核查 / 底层数据入口，文案必须明确为：

- `技术核查 / HRMS 原生数据`
- `HRMS 原始打卡记录（技术核查用）`
- `HRMS 原生考勤结果（技术核查用）`

## 数据主线

```text
飞书账号
-> Frappe User
-> HRMS Employee
-> Employee Checkin
-> Attendance
-> HBOS 中文报表 / 导入日志 / 月度暂存
```

当前导入员工是 HRMS Employee；Employee 可以暂时没有 User。后续 M1-FIX-E 如获授权，再通过手机号 / 邮箱 / 工号做 Feishu -> Frappe User -> HRMS Employee 绑定，员工个人权限后续通过 User -> Employee 过滤。

## 本轮不做

- 不进入 M1-FIX-C。
- 不实现异常三级流程。
- 不实现飞书 OAuth。
- 不实现领导 Demo。
- 不 closeout M1。
- 不 closeout M1-FIX-B3 / B4。
- 不修改 Frappe / ERPNext / HRMS 核心源码。
- 不提交真实 Excel、`.env`、密钥、数据库、日志、缓存或导入产物。
- 不删除历史数据；`HBOS-ATT-IMP-2026-00012` 至 `00014` 等历史 Running 批次本轮只记录，不清理。

## 状态口径

- M1-FIX-B2 = COMPLETED。
- M1-FIX-B3 = REVIEWING / Owner UI 验收未通过。
- M1-FIX-B4 = REVIEWING / Claude PASS，但 Owner 数据链路验收发现后续问题。
- M1-FIX-B5 = REVIEWING。
- M1 整体仍未完成。
- M1-FIX-C / D / E = PLANNED / 待授权。
- M2 = NOT STARTED / WAITING OWNER AUTHORIZATION。
