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

## B5 后续修正（2026-08-21）

Owner 数据链路验收后续，修复多处班次误判（不改变 B5 主结论，B5 状态仍为 REVIEWING）：

1. **四车间行政班误判迟到**（张旗、魏鑫、贾玖东、杨迪、焦德龙、卞德志、石炬升、侯宇晓、武天祥、荆东芳 10 人，Owner 确认行政班）：
   - 根因：上一轮改动误删 11004010/11004011/11004012/11004014 等工号，且全局规则表把 08:0x 上班卡匹配为「早班 08:00 标准」判迟到。
   - 修复：10 人工号补入 `ADMIN_NUMS`；`api.py` 名单判定短路规则表；新增 `pairing.admin_shift_from_gap`（08:31 起算迟到，夜间/凌晨跨天卡按晚班不判迟到）。
   - 重算 8/15-8/20 后：杨迪、侯宇晓、贾玖东、焦德龙 8 条误判迟到全部清零，班次恢复「行政班早班」。
2. **质量控制部四班次人员**（FOUR_SHIFT_NUMS 9 人，Owner 2026-08-21 确认）：
   - 规则：早班有 8 点/8 点半两种；迟到不卡死，**工作满 8 小时算正常出勤**；不足 8 小时置早退标记（不判迟到）。
   - 王颖 8/15-16 中班 16:20/16:26 打卡（16:00 标准）保持早退标记、不判迟到——与 Owner 确认口径一致（四班次人员不按卡点判迟到）。
3. 配对上限 18h → 13h（防漏下班卡假超长班），纯设备方向顺序配对分支已生效。
4. 新增测试 `apps/hb_attendance_app/tests/test_admin_shift.py`（7 用例），本地全量 58 用例通过。
5. **产假豁免（Owner 2026-08-21）**：陈玉姣（11008053）、王梅林（11008036）产假，缺勤暂不统计，加入 `EXEMPT_NUMS`；重算后两人缺勤记录清零。
6. **吕玉升迟到口径确认（Owner 2026-08-21）**：生产部 12 小时班早班标准 8:00、无宽限；吕玉升 8/17（08:25 上班）与 8/20（08:07 上班）两条迟到判定正确，仪表盘显示 2 次符合规则。
7. **分机孤立卡误判缺勤修复（Owner 2026-08-21，陈雨欣 8/19 案例）**：
   - 现象：陈雨欣 8/19 打卡 08:23:14（上班机）、17:33:23（上班机，误刷）、17:34:47（下班机），被误判 Absent。
   - 根因：① 去重规则把 17:33 上班机卡与 17:34 下班机卡（相隔 84 秒）合并，吞掉唯一的下班机卡；② 分机分支孤立上班机卡直接判缺勤，缺少「当天已有完整上下班结构」兜底。
   - 修复：方向不同的相邻卡不合并；分机分支孤立卡补 day_has_span 兜底；间隔不足 2 小时不配对。
   - 验证：新增离线复现脚本 `tools/repro_chen_yuxin_0819.py` 与回归脚本 `tools/repro_pairing_regression.py`（5 场景全 PASS）；重算 8/15-8/20 后总缺勤 382→366，早退 3→2，迟到 29 不变；陈雨欣 8/19 恢复 Present 9.19h；豁免名单双向核对 0 命中。
8. **配对上限 13h→14h 放宽（Owner 2026-08-21，李明 8/19 案例）**：
   - 现象：李明 8/19 无菌班 08:17:56 上班 → 21:28:17 下班 = 13.17h，超过 13h 上限被拒配，误判 Absent。
   - 根因：无菌 12 小时班加班到 13 小时出头是正常情形，13h 上限误杀。
   - 修复：全部配对窗口上限 13h→14h；`special_shift_from_gap` 12h 分支 19 点后上班视为无菌晚提前到岗不判迟到（张志兴 8/19 19:56 案例）。
   - 验证：新增 3 个测试（13.17h 配对、15.69h 仍拦截、19:56 无菌晚不迟到），测试总数 62 全 PASS；重算后总缺勤 366→326，迟到 30→28（张志兴 19:56 误判迟到消除），早退 2 不变；苗红四、赵明旺等 12 小时班人员大量「有打卡仍缺勤」恢复 Present；冯慧杰 15.69h 假超长班仍被拦截；豁免名单核对 0 命中。
9. **跨天夜班下班误刷上班机修复（Owner 2026-08-21，吕玉升/庞冠军 8/16 案例）**：
   - 现象：12 小时晚班（20:00-次日 8:00）员工夜班下班时先误刷在上班机（8-10 点），40 秒后再在正常下班机打卡，次日误判 Absent。
   - 根因：8/15 20:24 夜班上班与 8/16 08:37 正常下班卡正确配对后，08:36 误刷的上班机卡成了次日的孤立上班卡，算法把它当成新一天的上班卡，找不到下班卡即判缺勤。
   - 修复：新增 `night_out_mispunch` 兜底——孤立上班机卡在 8-10 点且前一日存在上班机卡（夜班上班，间隔 8-14h）时，视为前一夜班下班误刷，不判缺勤。
   - 验证：新增离线复现脚本 `tools/repro_night_out_mispunch.py`（5 场景）+ 3 个单元测试（测试总数 65 全 PASS）；重算后吕玉升 8/16、庞冠军 8/16 两条误判缺勤清除（总缺勤 326→321，其中 2 条为本修复，另 3 条为飞书请假同步覆盖江利刚年假所致）；真正缺勤（前一日无夜班卡）仍判缺勤，夜班下班正常打在下班机不误伤。
10. **遗留问题（待处理）**：7/28-8/14 分机实施前数据存在异常——全量重算时该区间每天产生 500-600 条缺勤（8/15 后每天仅 ~70 条）；窄区间（8/1-8/5）重算正常，配对算法本身在窄上下文正确，全量上下文下的根因未定位。当前该区间数据状态：7/28-7/31 为异常重算结果、8/1-8/5 已恢复、8/6-8/14 记录被重算副作用删除。8/15 后数据已确认准确。另有黄法普 8/17 单卡 07:45 上班无下班卡（漏打下班卡，非夜班下班误刷），待 Owner 确认是否需豁免。
11. **HBOS 汉化完善（Owner 2026-08-26）**：
    - 新增 `translations/zh.csv`：汉化 6 个 DocType 名称（HBOS Attendance Import Log→考勤导入日志、Employee Schedule→员工排班、Employee Shift→员工班次、Leave Record→请假记录、Overtime Record→加班记录、Shift Rule→班次规则）、模块名 HBOS Attendance→海滨考勤、HBOS Settings→HBOS 设置。
    - 字段 `Series`→编号（JSON 直接改 + 翻译兜底）；`打卡流水` 报表列 `HRMS Employee ID`→员工（HRMS）。
    - `hooks.py` app_title→海滨考勤、app_description 改中文。
    - 顺带修复 migrate 报错的 scheduler 路径笔误：`hb_attendance_app.hb_attendance_app.hbos_attendance.daily_feishu_sync.daily_sync_to_feishu`（多一层）→ `hb_attendance_app.hbos_attendance.daily_feishu_sync.daily_sync_to_feishu`，4 条 cron 方法路径已验证可解析。
    - `.gitignore` 增加例外，让 translations/zh.csv（源码）可提交，不被全局 `*.csv` 规则误伤。
    - 验证：migrate + clear-cache 后，`_(...)` 运行时返回中文；4 条 cron 路径 callable 全 True。
12. **设备动力部 12 小时倒班自动轮转排班（Owner 2026-08-26）**：
    - 需求：设备动力部 3 人（付全喜 10009025、李双胜 10009027、贾正利 10009028）12 小时倒班，循环「早班(8:00-20:00) → 夜班(20:00-8:00，即系统晚班) → 休息」三天一轮，相位错开保证每天 2 人上班、1 人休息。
    - 相位锚点（2026-08-15 起点）：付全喜=晚班、李双胜=休息、贾正利=早班。
    - 实现：新增 `rotation_schedule.py`——纯函数 `rotation_shift_for`（锚点+循环取模算班次）+ `generate_rotation_schedule`（覆盖式写入 HBOS Employee Schedule）；在 `regenerate_attendance` 开头调用，生成到「重算终点」与「未来 30 天」的较晚者，休息日写「休息」由现有「排班休息日无打卡=休息」逻辑自动豁免缺勤。
    - 验证：新增 `test_rotation_schedule.py`（5 用例，测试总数 70 全 PASS）；生成排班覆盖 8/15-9/25 共 126 条，三人 8/15-8/24 期间 0 条 Absent，上班日班次与排班表完全一致。
13. **生产部 12 小时倒班自动轮转排班（Owner 2026-08-26）**：
    - 需求：生产部 3 人（吕玉升 10010011、王飞 10010010、袁式梅 10010013）同规则轮转，循环「早班 → 夜班 → 休息」三天一轮。
    - 相位锚点（2026-08-26 起点）：吕玉升=早班、王飞=晚班、袁式梅=休息。
    - 实现：`rotation_schedule.py` 重构为多分组 `ROTATION_GROUPS`（每组独立锚点日期 + 成员班次），原设备动力部锚点不变，新增生产部组；`generate_rotation_schedule` 遍历全部分组覆盖式生成。
    - 验证：`test_rotation_schedule.py` 扩充至 10 用例（含两组相位、无重复工号校验），测试总数 75 全 PASS；生产部排班覆盖 8/26-9/25 共 93 条，8/26 当日吕玉升=早班、王飞=晚班、袁式梅=休息与 Owner 描述一致。
14. **离职人员停止考勤统计（Owner 2026-08-26）**：
    - 人员：曹福喜（11004050 设备动力部）、秦鑫磊（11001006 一车间）、荆东芳（11004051 四车间）、荆海彦（11004017 四车间）共 4 人离职。
    - 处理：Employee.status 改为 Left；删除 4 人全部排班表记录；删除 4 人全部考勤记录（HBOS-ATT + DELI-ATT 共 23 条）。
    - 代码加固：`regenerate_attendance` 的打卡流水查询增加 `emp.status = 'Active'` 过滤，离职人员打卡流水不再进入配对，配合零打卡分支已有的 Active 过滤，离职人员彻底不再生成考勤。
    - 验证：4 人 status=Left、考勤记录 0 条、排班 0 条；重算后不再出现；测试总数 75 全 PASS。
15. **侯振雷生病暂豁免异常考勤（Owner 2026-08-26）**：
    - 人员：侯振雷（11001010 设备动力部），生病请假，暂不计异常考勤。
    - 处理：加入 `EXEMPT_NUMS` 豁免名单（注释注明「生病暂豁免，病愈后移除」）；重算 8/15-8/26 后其 6 条 Absent（8/18-21、8/25-26）全部清除。
    - 说明：EXEMPT_NUMS 为硬编码名单，病愈复工后需从名单移除该工号。
16. **排班表导入报错「排班表文件不存在」修复（Owner 2026-08-26）**：
    - 现象：班次管理页导入排班表时报「排班表文件不存在」。
    - 根因：① 前端用 `frappe.client.get` 读 File 文档的 `content` 字段，但 File DocType 无此字段（内容在磁盘，运行时 `get_content()` 读取），`content` 恒为 undefined → 后端 `file_content` 为空 → 抛「排班表文件不存在」；② 附带暴露：`parse_xlsx_matrix` 对纵向式文件（如四车间排班表只有 Sheet1）也会「成功」解析出垃圾行，导致后续 vertical 解析永不触发。
    - 修复：① 前端改传 `file_url`；② 后端加 `file_url` 分支用 `get_content(encodings=())` 读原始字节；③ `parse_xlsx_matrix` 增加「必须有『班次说明』sheet」判别，无此 sheet 返回空；④ 抽取 `_cell_value` 兼容 shared string / inlineStr 两种 xlsx 存储格式（WPS/部分工具导出用 inlineStr）。
    - 验证：新增 `test_schedule_import.py`（3 用例），测试总数 78 全 PASS；端到端重导四车间排班表 created=142 / skipped=11（修复前 created=0 / skipped=992）；四车间排班 144→286 条，姓名/日期/班次正确。
17. **月度考勤汇总新增「导出异常考勤」按钮（Owner 2026-08-27）**：
    - 需求：在月度考勤汇总界面加「导出异常考勤」按钮，一键导出格式对齐 Owner 提供的「HBOS异常考勤报表」参考文件（总览 / 缺勤汇总 / 迟到早退 三个工作表，深蓝标题+隔行条纹+KPI 卡片+日期带星期）。
    - 实现：`export.py` 新增 `export_exceptions`（按月份/日期范围/员工/部门导出，剔除豁免名单 EXEMPT_NUMS，缺勤/迟到/早退三维聚合，日期带星期 `MM-DD(周六)`）；`月度考勤汇总.js` onload 加「导出异常考勤」按钮。
    - 验证：`export_exceptions` 端到端生成 `HBOS异常考勤报表_YYYYMMDD-YYYYMMDD.xlsx`，格式与参考文件一致（工作表名、标题、KPI、日期格式、列宽）。
18. **考勤判定规则收敛（Owner 2026-08-27，误判率大幅下降）**：
    - 背景：魏雨 8/26（07:48-23:31=15.72h）、8/22（07:46→8/23 00:00=16.24h）等「早到+加班到深夜」真实超长班被 14h 配对上限误判缺勤；陈雨欣/王廷炜/吕玉升等双机连刷误判此前已修复。
    - 规则变更：
      ① 配对上限 14h→16h（保留 16h 上限防漏卡假超长班；冯慧杰 15.7h 真实加班恢复配对）；
      ② **有卡就不判缺勤**（当天存在任意打卡记录时，即使配对失败/超长班/孤立卡，也不判缺勤）；
      ③ **连续无打卡 1-2 天不判缺勤，连续 3 天及以上从第 3 天起判缺勤**。
    - 验证：79 测试全 PASS；8/15-8/26 缺勤 489→240→210→134（三轮规则收敛）；抽查确认剩余 Absent 全部为「连续 3 天及以上无打卡」；魏雨 8/22、8/26 缺勤均消除。
19. **离职人员批量标记（Owner 2026-08-27，2026 年度离职名单）**：
    - 名单：`2026年度离职人员名单.xlsx`（1-8 月共 78 人去重）。
    - 处理：系统匹配到 10 人，其中 6 人此前已处理（曹福喜/秦鑫磊/荆东芳/荆海彦/梁玉翠），本轮新增标记 5 人（崔利明 11006121、李佳斌 11009026、李风义 11006058、赵腾飞 11008001、路花明 10009010）status→Left 并清理考勤+排班。
    - 验证：5 人 status=Left、考勤 0 条、排班 0 条；重算后 8/15-26 缺勤 240→210（李风义/崔利明离职后无打卡缺勤正确排除）。名单其余 68 人未在系统建档或姓名不一致，无数据可处理。
20. **人员状态维护（Owner 2026-08-27）**：
    - 曹凯莉（10008020 仓储部）：产假，加入 EXEMPT_NUMS 豁免。
    - 曹祖军（11003029 三车间）：退休，status→Left，清考勤排班。
    - 刘凤岭（11003033 三车间）、马照辉（11003016 三车间）：长期病假，加入 EXEMPT_NUMS 豁免。
    - 王卫勋（11006096 六车间（规范））：离职，status→Left，清考勤排班。
    - 张习方数据修正：11004052 建档姓名「李开新」改为「张习方」（Owner 确认）；11004009（重复/错误档案）确认无此人，status→Left，清考勤排班。
    - 验证：8/15-26 缺勤 134→123→92→81→71（多轮人员排除）；11004052 张习方 8/15-26 考勤 8 天全部 Present 无误判。

## 2026-09-02 后续交付：规则看板

在「班次管理」页新增「规则看板」Tab（页顶 Tab 切换，班次设置功能原样保留），把三类班次判定规则可视化：

- 班次规则记录：`HBOS Shift Rule` 全量记录（含实时计算的绑定人数），生效/草稿默认展示，已停用历史可展开。
- 内置默认班次：8 种内置班次（早/中/夜/晚/行政/8:30/无菌早/无菌晚）。
- 名单规则：行政班、豁免、无菌/三班、四班次、安全、食堂、上下班打卡机 SN 共 8 组卡片，点击展开完整工号。
- 配对算法参数：去重 10 分钟、最短 2h、最长 16h/18h、跨天夜班锁定、零点夜班、GPS 豁免、3 天缺勤门槛等。
- 判定优先级链：排班表 > 固定班次绑定 > 部门/全局规则 > 名单短路 > 硬编码兜底。

实现：`rule_lists.py`（名单常量纯模块，api.py re-export）、`rules_board.py`（静态数据纯函数）、
`shift_management_data.get_rules_board()`（白名单端点）、`hbos_shift_management.js`（Tab + 渲染）。
名单常量从 api.py 抽离为纯模块，判定逻辑零改动。新增离线测试 9 例，全量 88 通过。

## 2026-09-02 追加交付：班次人员维护表导出

规则看板新增「导出班次人员维护表」按钮，导出 5-sheet xlsx（`HBOS班次人员维护表_YYYYMMDD.xlsx`）：

- 部门-班次-人员：主表，行 = 有人的「部门×班次体系」组合；人员归行优先级 豁免(不进主表) > 绑定班次 > 名单(无菌/四班次/行政/安全/食堂) > 通用倒班；姓名含工号。
- 豁免人员：EXEMPT_NUMS 在职成员（含原因）。
- 特殊班次：无菌倒班/四班次/安全倒班/食堂 名单在职成员。
- 行政班名单：ADMIN_NUMS 在职成员。
- 说明：口径与数据日期。

实现：`roster_classify.py`（归行纯函数）、`roster_export.py`（export_shift_roster 白名单端点 + openpyxl 5-sheet）、规则看板按钮。只读不触发考勤生成。新增离线测试，全量 97 通过。

## 状态口径

- M1-FIX-B2 = COMPLETED。
- M1-FIX-B3 = REVIEWING / Owner UI 验收未通过。
- M1-FIX-B4 = REVIEWING / Claude PASS，但 Owner 数据链路验收发现后续问题。
- M1-FIX-B5 = REVIEWING。
- M1 整体仍未完成。
- M1-FIX-C / D / E = PLANNED / 待授权。
- M2 = NOT STARTED / WAITING OWNER AUTHORIZATION。
