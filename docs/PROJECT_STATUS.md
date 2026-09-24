# Project Status

项目名称：新乡海滨智能运营管理平台。

## 当前状态

- 当前阶段：M1-FIX 功能补漏阶段（IN_PROGRESS）；M1 产品交付尚未完成
- 当前轮次：M1-FIX-F（REVIEWING，**第一、二阶段均已上线；整支复查已完成并处置**）
- 当前仓库定位：工程启动文档、AI 上下文、里程碑状态、计划、ADR、环境设计文档、最小 Docker 配置与 M1-FIX 轻量自定义 App
- 当前实现状态：M1-FIX-B2 已 COMPLETED；M1-FIX-B3 为 REVIEWING / Owner UI 验收未通过；M1-FIX-B4 为 REVIEWING / Claude PASS，但 Owner 数据链路验收发现后续问题；M1-FIX-B5 为 REVIEWING；M1-FIX-F 为 REVIEWING（调休模块两阶段均已上线：119 条入库、103 条解析、41 已核实 / 53 核实不通过；已核实调休日已接入考勤豁免与看板；整支复查完成，1 项发现已修、1 项归因已更正）；M1-FIX-C/D/E 未启动。
- 本批最新交付：2026-09-22 完成 **M1-FIX-F 调休模块第一阶段**——飞书调休审批进入系统并按海滨口径完成「加班日提取 → 打卡核实」，产出可人工复核的结论清单。分支 `m1-fix-c-rest-leave`（16 提交），全量测试 311 → **396 通过**。**本阶段只出结论、不改变任何考勤结果**。2026-09-22 已上线：119 条入库、103 条解析出加班日、核实结论 40 已核实 / 53 核实不通过 / 14 解析失败；**考勤结果与上线前逐值一致（零副作用）**。上线中发现并修复三项阻断（模型下线、HBOS_AI_* 未注入队列容器、nginx 需 reload），详见落地记录 §8。详见 `docs/milestones/M1_FIX_F_调休模块第一阶段落地记录.md`。
- 当前远端：`origin` -> `https://github.com/zjl327707743/HBOS.git`，GitHub visibility = `PRIVATE`
- 下一步路线：M1-FIX-F 两阶段均已上线；**建议下一轮优先处理「分机实施前数据修复」**（含 8/14 的 223 条错误缺勤与 `pairing.py` 设备方向判定的按天改造）与台账 #10「重算幂等改造」（本轮已实际踩中其地雷）；M1-FIX-C（异常三级流程）为 PLANNED / 待 Owner 授权；M1-FIX-D/E 未启动。**M2-STOCK-R1（库存模块隔离）为 IN_PROGRESS**，分支 `m2-stock-r1`。

## M1-FIX-F 状态

状态：**REVIEWING**（**第一、二阶段均已上线；整支复查已完成并处置**）。

轮次定位：调休模块（一阶段：同步 + LLM 解析加班日 + 打卡核实 + 落库；二阶段：接入考勤判定豁免）。

业务规则（Owner 2026-09-21 确认）：调休日 = 飞书日期字段区间；加班日 = LLM 从「说明」自由文本提取；核实 = 加班日当天有完整上下班配对，全部通过才「已核实」，否则「核实不通过」转人工。

- 命名说明：原拟沿用 `M1-FIX-C`，但台账中该编号已定义为「异常说明三级流程」，故改用 `M1-FIX-F`；若 Owner 另有口径可重命名。
- 与请假的差异：模板一样，但判定逻辑不同——请假审批通过即豁免；调休须先核实加班日。两条通道分开成表。
- 交付：`rest_leave.py` 纯逻辑模块、DocType 4 个新字段、`sync_rest_leave.py` 三段（同步 → LLM 解析 → 核实，同一 `*/30` 有序列表）、换班（`HBOS Shift Swap Record`）全部产物退休。
- 关键约束：**LLM 结果落库，判定热路径永不调用 LLM**（考勤每 10 分钟重算，热路径调 LLM 成本、延迟、确定性都不可接受）。
- 核实判据：复用系统已算出的考勤结果（`status='Present'` 且 `working_hours >= 2`），不另写一套配对定义。
- 实测依据：飞书调休表 119 条（已通过 107）；96 条同日、8 条跨天；16 条天数与日期跨度不符；**65 条说明只用「号」不用「日」**（初版解析器只认「日」会让 63% 数据落解析失败，已在修复轮补上）；36 条为多行批量说明（列他人加班），故非 LLM 不可。
- 旧模块「代码在、运行态为零」的根因：DocType 从未 migrate，且原测试是静态断言（检查源码字符串，永远为真）。
- 本阶段刻意不接判定；接入点为 `regenerate_attendance`（把已核实的调休日并入传给 `pair_employee_checkins()` 的豁免集合，`pairing.py` 可零改动），但**必须先处理第二阶段硬性前提 F2/F3/F4/F5**。
- 第二阶段硬性前提（本阶段无害）：① 豁免查询必须过滤 `approval_status='已通过'`（新同步写入全部行，含已撤回/已拒绝）；② 重新解析失效键需含 `employee`（现只有 `remarks`）；③ `已核实`/`核实不通过` 是终态，需加重新核实机制；④ 复看三段调度频率（设计定 `*/10`，实际 `*/30`）。
- **2026-09-22 已上线**：119 条入库 → 103 条解析出加班日 → 核实结论 **40 已核实 / 53 核实不通过 / 14 解析失败**（仅「已通过」107 条）。**考勤结果与上线前逐值一致（零副作用）**；判据敞口（7/28-30）实测为零；自洽性对账违规 0 条。
- 上线中发现并修复三项阻断：① `deepseek-v4-flash` 上游下线 → 实测 4 候选后改 `deepseek-flash`；② **`HBOS_AI_*` 只注入 backend，scheduler 与两个 queue 全缺** → 定时任务 0.35 秒「成功」实则走「未配置 AI」分支，且 `bench execute` 手动跑正常、永远测不出；③ **nginx 502 的正解是 `nginx -s reload` 而非 `restart`**（已更正 `docs/HBOS考勤判定规则.md` §13.9 的错误结论）。
- 待 Owner 判读：62%（53/107）不通过的含义；10 天「有打卡却无考勤记录」的引擎缺口（非本轮引入）。
- 主文档：`docs/milestones/M1_FIX_F_调休模块第一阶段落地记录.md`

### M1-FIX-F 第二阶段（接入考勤判定豁免）2026-09-22~24

**已上线**。把「已核实」的调休日接入判定与看板，使其不再被判缺勤、不再被列为「未打卡」。

- 交付：`rest_leave.expand_verified_records`（纯函数）、新建 `rest_leave_apply.verified_rest_dates()`（**「已通过 + 已核实」的唯一查询口径**，有测试防止第二份副本）、`api.py` 并入豁免集合并把记录班次标为 `调休`、看板**两条**标签路径（实时 + 回顾）均接入、`sync_rest_leave.py` 重解析失效键补入 `employee`。
- 测试：396 → **437 全绿**。
- 验收（2026-09-24 实测）：41 个已核实调休日 → 13 条 `On Leave`+`调休`、17 条孤卡豁免无记录、11 条 `Present`（其中 2 条实为跨天配对）。看板实测显示「请假（调休）」。幂等、非调休人员零影响。
- **执行中造成并已修复的数据事故**：`regenerate_attendance` 的清理语句含第二条 DELETE，会删除 `attendance_date > range_end` 的全部记录，故窄窗口重算会静默摧毁后续数据。我按乱序执行窄窗口重算，一度删除 8/15–9/21 全部记录（总数 29146→8004）。已按**时间升序**逐段重建恢复，7/28–9/23 共 58 天无缺日。详见落地记录 §A4。
- **整支复查结论**：功能正确；驳回并更正了我「8/14 属文档已记载遗留问题」的错误归因——8/14 的 223 条缺勤是**本轮重算生成、从未验证**的数据，机制为「取数窗口跨过 8/15 时触发配对严格分支，而 8/14 的卡方向全为 None 致全判孤立上班卡」（实测 58 人当天在两类机器都打过卡却判缺勤）。Owner 决定**暂不处理（选项 C）**，等专门轮次。
- 复查另抓到并已修：**月报把调休算成「正常出勤」**（`is_leave` 只查请假表集合，调休日在建休表）。
- 已更正 `pairing.py:209` 过期注释（写 8/14，常量是 08-15）——该矛盾是本次踩坑的直接诱因。
- 遗留观察见落地记录 §A7（看板第四条消费路径、回顾模式对 17 天无记录者的标签、`PARSE_BATCH_SECONDS` 待校准）。

### 2026-09-24 名单单一来源收敛与 PR 审查修复

Owner 2026-09-24 裁定「一个业务含义只留一份名单」，随后对整支做 PR 审查并修复。

**名单收敛**（行为口径已变，Owner 已知悉）：

- **行政班**：`ADMIN_NUMS` 原在三处各一份且严重分叉——`rule_lists.py`（判定用，178 人）、`daily_feishu_sync.py`（221 人）、`pair_checkins.py`（139 人）。飞书与判定差 **71 个工号**（57 只在飞书、14 只在判定），同一人同一天在两套输出里一个判缺勤、一个不算缺勤。裁定以 `rule_lists.py` 为准，`daily_feishu_sync.py` 删除本地 221 人副本改为引用（不是「把数字抄一致」——那样下次仍会分叉）。
- **无菌**：`WUJUN_NUMS` 原有两份（`api.py` 空集 / `daily_feishu_sync.py` 48 人），而现行体系是 `pairing.py` 的 `SPECIAL_SHIFT_NUMS`（59 人）。48 人那份混入 3 名设备动力部人员、漏掉 14 名无菌车间人员。裁定以 `SPECIAL_SHIFT_NUMS` 为准。**实测行为变化**：仅 1 人（耿献磊，无菌车间）失去周末双休豁免；3 名设备动力部人员获得豁免。
- **`EXCLUDE_NUMS` 未改行为**，只补注释：20 人手工项中有 7 人已属无菌体系、7 人已属 `FOOD_NUMS`，另 6 人横跨 5 个部门来源不明。「无菌是否应整批排除」这一口径未定，属业务问题，**留待 Owner 裁定**。
- **旧引擎加废弃标记**：`pair_checkins.py` / `shift_matcher.py` / `generate_attendance.py` 全仓库无引用但文件仍在，各自含第 3 份名单或旧班次逻辑，已补「已废弃·请勿使用」docstring（未删文件，清理另开一轮）。
- 新增 `tests/test_admin_nums_single_source.py` 守住单一来源，并已加固：旧断言用 `assertIsNone(_module_level_names(...))`，而该助手在「名字不存在」与「存在但非字面量」两种情形下都返回 None，`ADMIN_NUMS = set(...) | {...}` / 放进 `if`、`try`、函数体 / `ADMIN_NUMS.update(...)` 都能让断言**假通过**；现改为 AST 扫描任何本地绑定或原地修改（已用上述形态做过变异验证，均能抓出）。

**PR 审查修复**（5 项，均为实际缺陷）：

- **去重窗口与配对下限对撞**：`dedup_checkins` 窗口 120min、配对下限 `2 <= gap` 即 120min，闭区间下**恰好相隔 2h** 的上下班卡先被去重成一张、再配不上 → 孤卡误判缺勤（仅影响方向未知的卡：8/15 前、GPS 卡、未登记设备）。改为严格小于，边界让给配对。已补 2 条回归测试并做变异验证（改回 `<=` 时测试失败）。
- **`.env.example` 缺 9 个变量**：compose 引用的 `FEISHU_*`、`DELICLOUD_*`、`HBOS_AI_*`、`HBOS_NOTIFY_*` 一个都没收录。compose 的 `${VAR}` 缺项时展开为空串、不报错，故新环境照模板建 `.env` 会让 AI 复核与 9 点考勤卡片**静默失效**（与已记录的 `HBOS_AI_*` 只注入 backend 同类）。已补齐占位符与说明。
- **CI 门禁误伤 `.env.example`**：`.github/workflows/hbos-quality-gate.yml` 的「禁止 `.env`」用了 `(^|/)\.env` 而无 `$` 锚点（其余各检查都有），会把占位符模板 `.env.example` 一并判违规。已补 `$` 锚点。
- **部门看板 XSS**：`hbos_department_board.js` 的部门名（来自 `tabEmployee.department`，用户可写）与服务端错误文案直接拼进 HTML，同文件其余 8 处均已 `escape_html`。已补齐。
- **月报 AI 复核定位用 `list.index`**：`target.index((r, dates))` 是 O(n²) 且 `==` 命中相同内容元组时会定位到错误下标，改 `enumerate`。

**审核同时发现（未在本轮修，见下方风险）**：本地 `origin` 地址明文内嵌 GitHub PAT，需吊销并改凭据助手。

## 状态更新制度

项目总状态必须在每轮任务收尾时同步更新。

- 如本轮改变项目状态，必须更新 `docs/PROJECT_STATUS.md`。
- 如本轮改变当前里程碑或轮次，必须更新 `docs/CURRENT_MILESTONE.md`。
- 如本轮属于某个里程碑，必须更新 `docs/milestones/M0.md` 或对应里程碑文件。
- 输出结果时必须说明状态文件是否已更新；如未更新，必须说明原因。

## M1-R3 状态

状态：BLOCKED。

执行结论：PARTIAL / BLOCKED。

收口记录：M1-R3 已通过 Codex 审查，审查结果为 PASS；由于本轮实际结果不是成功完成，而是 PARTIAL / BLOCKED，M1-R3 不标记为 COMPLETED，最终状态收口为 BLOCKED。

本轮目标：

- 在本地 `frontend` site 中使用 `TEST-HBOS-M1R3-` 前缀虚构最小测试数据试运行 HRMS 原生考勤配置链路。
- 覆盖早班、中班、夜班、跨夜班和 14 个打卡 / 请假 / 加班 / 节假日 / 调班场景。
- 记录 HRMS 原生可用项、需配置项和 Gap。

当前结果：

- 已创建 `TEST-HBOS-M1R3-虚构节假日`。
- 已创建 `TEST-HBOS-M1R3-生产一部 - 健D`、`TEST-HBOS-M1R3-生产二部 - 健D`。
- 已创建 `TEST-HBOS-M1R3-虚构事假`。
- `TEST-HBOS-M1R3-虚构公司` 标准创建在 `tabCompany` insert 阶段遇到 lock wait / 长时间阻塞，未创建。
- TEST User / Employee 创建未完成，导致 Shift Type、Shift Assignment、Employee Checkin、Leave Application 和 Attendance 闭环未执行完成。
- 14 个考勤场景未生成 Attendance，不能判定 HRMS 原生考勤链路通过。
- 本轮未越界，未继续创建测试数据，未清理 TEST 数据，未提交 `.env`、密钥、数据库、日志、缓存、备份或运行时产物。

本轮结论：

- 当前仍不建议创建 `hb_attendance_app`。
- 阻断点是运行态 ORM 写入 / 数据库连接或锁问题，不是 HRMS 原生对象模型已被证明无法覆盖。
- M1-R3A 已完成运行态阻断诊断与 TEST 数据隔离 / 清理方案，并已通过 Codex 审查收口为 COMPLETED。
- M1-R3B 已完成运行态最小修复方案，并已通过 Codex 审查收口为 COMPLETED；本轮未执行修复、未清理 TEST 数据、未继续试运行。
- M1-R3B-FIX 已通过 Codex 审查，审查结果 PASS，状态已从 REVIEWING 收口为 COMPLETED。
- M1-R3B-FIX 只执行 `docker compose up -d redis-cache redis-queue`，未再执行额外服务启动 / 重启，未清理 TEST 数据，未继续试运行。
- M1-R3B-FIX 已确认 `redis-cache`、`redis-queue`、queue worker、scheduler、`bench doctor` 和 `/login` 已恢复或改善。
- M1-R3B-FIX 只读计数确认当前 TEST 数据包括 Employee 8、Shift Type 4、Shift Assignment 14、Employee Checkin 22、Leave Application 2、Attendance 12 等；本轮没有手工创建、删除或清理 TEST 数据，计数高于 M1-R3A / M1-R3B 旧记录，来源需在 M1-R3C 或清理授权前复核。
- M1-R3C 已按用户授权执行 HRMS 原生考勤最小试运行复测，使用新前缀 `TEST-HBOS-M1R3C-*` / `test-hbos-m1r3c-*`，未覆盖旧 `TEST-HBOS-M1R3-*` 数据。
- Company / User / Employee 写入阻断已解除：Company 1、User 8、Employee 8 已成功创建。
- M1-R3C 最终计数包括 Department 2、Holiday List 1、Shift Type 4、Shift Assignment 14、Employee Checkin 22、Leave Type 1、Attendance 13；Leave Application 因缺少 Leave Allocation 未创建。
- 14 个场景已完成复测记录：正常早班、中班、夜班、跨夜班、临时调班等基础链路可用；迟到 / 早退标记、缺卡、请假前置、全天缺勤、加班和节假日业务口径仍存在配置或业务 Gap。
- M1-R3C 已通过 Codex 审查并收口为 COMPLETED，结论为 PARTIAL / GAP_IDENTIFIED。M1-R3C 是试运行完成，不是考勤业务闭环完成。
- M1-R3D 已完成异常口径与 Gap 诊断文档交付，并已通过 Codex 审查收口为 COMPLETED；结论为 Gap 四类分类、均不需要立即创建 hb_attendance_app。
- M1-R3E 已形成配置复核清单与海滨业务口径确认表，并已通过 Codex 审查收口为 COMPLETED；8/10 项业务口径阻塞 M1-R4。
- M1-R3F 已形成面向业务负责人的确认包，并已通过 Codex 审查收口为 COMPLETED；9 项确认主题中 7 项必须确认，2 项可先按默认值推进。
- M1-REQ-DESIGN-DRAFT 已通过 Codex 审查并收口为 COMPLETED；初审员工姓名脱敏 blocker 已修复，复审 PASS。
- M1-R4 已通过 Codex 审查并收口为 COMPLETED。Codex 初审发现状态入口 blocker，修复后复审 PASS。主文档 `docs/milestones/M1_R4_Demo技术方案与实施路线拆分.md` 已交付。
- M1-R5 已通过 Codex 审查并收口为 COMPLETED。Codex 审查 PASS。本轮已完成 HRMS 配置基线整理（14 类对象）、考勤工作台入口方案设计（方案 A/B）、月度汇总 Demo 展示路径设计（14 字段映射与覆盖分析）、Excel 导出路径说明（4 种导出方式）、R5 风险与后续 Gate 评估（9 项技术评估）。本轮未创建 App、未创建 DocType、未修改核心源码、未动数据库。主文档 `docs/milestones/M1_R5_HRMS配置基线工作台月报Demo.md` 已交付。

## 已确认架构方向

准确叫法：Frappe/ERPNext 开源底座 + Frappe 多 App 模块化架构 + 外部独立服务扩展。

长期架构：Frappe/ERPNext 开源底座 + 海滨自定义 Frappe App + 外部 AI/视频/算法服务 + Vue/React 驾驶舱 + 飞书集成 + Docker 部署。

主技术栈：Frappe Framework、ERPNext、Frappe HR、Python、JavaScript、MariaDB/MySQL 兼容体系、Redis、Docker、Docker Compose、Vue/React、ECharts、FastAPI。

## M0-R1 状态

状态：已完成并封板。

本轮目标：

- 创建根目录说明文档
- 创建 AI 协作上下文文档
- 创建当前里程碑文档
- 创建 M0 工程启动计划
- 创建四个基础 ADR

本轮未做：

- 未安装 Frappe/ERPNext/Frappe HR
- 未创建 Frappe bench
- 未创建任何 Frappe App
- 未创建 `hb_core_app`、`hb_attendance_app`、`hb_feishu_app`
- 未写 Docker Compose
- 未开发考勤业务
- 未接入飞书
- 未开发前端驾驶舱

## M0-R2 状态

状态：已完成并通过 Codex 审查，已提交。

本轮目标：

- 设计 Frappe / ERPNext / Docker 最小本地开发环境方案
- 设计最小服务清单、目录规划、端口规划、数据卷规划和环境变量分组
- 明确 M0-R3 才允许真正落地 `docker-compose.yml` 与 Frappe 环境

本轮未做：

- 未安装 Frappe/ERPNext/Frappe HR
- 未创建 Frappe bench
- 未创建任何 Frappe App
- 未创建 `hb_core_app`、`hb_attendance_app`、`hb_feishu_app`
- 未写 Docker Compose
- 未创建 `.env`
- 未启动容器
- 未开发考勤业务
- 未接入飞书
- 未开发前端驾驶舱

## M0-R2B 状态

状态：已完成并通过 Codex 审查，已提交。

本轮目标：

- 建立里程碑规划和状态文件机制
- 固化每轮收尾必须更新状态的规则
- 新增 `docs/milestones/README.md` 和 `docs/milestones/M0.md`
- 更新协作规则、项目状态、当前里程碑、阅读指南和 M0-R2 计划

本轮未做：

- 未安装 Frappe/ERPNext/Frappe HR
- 未创建 Frappe bench
- 未创建任何 Frappe App
- 未写 Docker Compose
- 未创建 `.env`
- 未创建 `.gitignore`
- 未启动容器
- 未开发考勤业务
- 未接入飞书
- 未开发前端驾驶舱

## M0-R2C 状态

状态：已完成。

本轮目标：

- 收口 M0-R2 批次状态台账
- 确认 M0-R3 未开始
- 创建一次 Git 提交

本轮未做：

- 未安装任何 skill
- 未执行飞书真实写入
- 未安装 Frappe/ERPNext/Frappe HR
- 未创建 Frappe bench
- 未创建任何 Frappe App
- 未写 Docker Compose
- 未创建 `.env`
- 未启动容器
- 未开发业务代码
- 未开发前端驾驶舱

## M0-R2A 状态

状态：已完成并通过 Codex 审查，已提交。

本轮目标：

- 修复默认入口文档中的过期当前轮次描述
- 确保状态入口指向当前真实进度

## M0-R2D 状态

状态：已完成。

本轮目标：

- 新增并纳入 `docs/AI技能路由规范.md`
- 明确已确认可用 skill 与候选 skill 的边界
- 将 skill 路由规则接入 `CLAUDE.md`、`AGENTS.md`、`docs/AI_CONTEXT.md` 和 `docs/READING_GUIDE.md`
- 固化 Git 提交描述优先中文的规则
- 固化新增文档名称优先中文或中英混合的规则
- 将 M0-R2 批次新增英文文档改为中文或中英混合文件名

本轮未做：

- 未安装 Frappe/ERPNext/Frappe HR
- 未创建 Frappe bench
- 未创建任何 Frappe App
- 未写 Docker Compose
- 未创建 `.env`
- 未创建 `.gitignore`
- 未启动容器
- 未开发考勤业务
- 未执行飞书真实写入
- 未开发前端驾驶舱

## M0-R2E 状态

状态：已完成。

本轮目标：

- 修复 `README.md` 中过期的阶段描述
- 在协作规则中补强公共入口文件收尾检查规则
- 同步项目状态、当前里程碑和 M0 里程碑台账
- 创建一次 Git 提交

本轮未做：

- 未安装 Frappe/ERPNext/Frappe HR
- 未创建 Frappe bench
- 未创建任何 Frappe App
- 未写 Docker Compose
- 未创建 `.env`
- 未创建 `.gitignore`
- 未启动容器
- 未开发考勤业务
- 未执行飞书真实写入
- 未开发前端驾驶舱

## M0-R3A 状态

状态：COMPLETED。

本轮目标：

- 创建 Frappe / ERPNext / Docker 最小本地环境配置
- 创建 `.env.example`、`.gitignore` 和落地记录文档
- 基于官方 `frappe/frappe_docker` 资料确认版本和服务结构
- 拉取镜像、启动容器、初始化本地测试 site、验证 Frappe Desk

当前结果：

- 已创建最小 Docker 配置和落地记录
- 已基于官方 `pwd.yml` 确认服务结构与镜像 tag
- 原执行时本机执行 `docker --version && docker compose version` 返回 `zsh:1: command not found: docker`
- 本轮 M0-R3A-VERIFY 已获用户授权继续执行真实 Docker 本地启动验证
- 本轮确认 `docker --version` 和 `docker compose version` 已可用
- 已从 `.env.example` 生成本地 `.env`，`.env` 被 `.gitignore` 忽略且未被 Git 追踪
- 已执行 `docker compose pull`，但在拉取镜像时失败：Docker Hub token 获取返回 EOF
- M0-R3A-PULL-RETRY 已重试 `docker compose pull` 并成功拉取 `redis:6.2-alpine`、`mariadb:11.8`、`frappe/erpnext:v16.26.2`
- 首次 `docker compose up -d` 遇到宿主机 `8080` 端口占用，仅调整本地 `.env` 的 `HTTP_PORT=8081` 后启动成功；`.env` 未被 Git 追踪
- `create-site` 已成功完成，测试 site 为 `frontend`
- `bench version` 验证：ERPNext `16.26.2`，Frappe `16.25.0`
- Frappe Desk 登录页已通过 `http://localhost:8081/login` 验证，返回 `HTTP 200`

本轮未做：

- 未创建 `hb_core_app`
- 未创建 `hb_attendance_app`
- 未创建 `hb_feishu_app`
- 未安装自定义 Frappe App
- 未安装 Frappe HR / HRMS
- 未开发考勤业务
- 未执行飞书真实写入
- 未开发前端驾驶舱
- 未写 Python/JavaScript/TypeScript 业务代码
- 未引入第三方业务源码
- 未 push
- 未配置 remote
- 未提交真实密钥

## M0-R3B 状态

状态：COMPLETED。

本轮目标：

- 评估 Frappe HR / HRMS 官方信息、v16 分支 / tag 与当前环境的兼容性
- 比较现有容器 / bench 内安装与自定义镜像 / 扩展 Compose 流程两种候选方案
- 给出 M0-R3C 推荐安装方式、边界、风险和回滚建议
- 更新项目状态、当前里程碑和 M0 里程碑台账
- 根据 Codex 审查结论收口 M0-R3B 状态

当前结论：

- 当前环境为 ERPNext `16.26.2`、Frappe `16.25.0`，site 为 `frontend`，Desk 地址为 `http://localhost:8081/login`
- 当前仅安装 `frappe` 和 `erpnext`，未安装 HRMS
- 官方 `frappe/hrms` 存在 `version-16` 分支和 v16 tag；`version-16` 依赖声明要求 Frappe / ERPNext `>=16.0.0,<17.0.0`
- 从主版本范围看，HRMS `version-16` 与当前 Frappe / ERPNext v16 环境方向一致；具体 tag / branch 仍需 M0-R3C 实际安装验证
- 推荐 M0-R3C 在备份和可回滚前提下安装 HRMS，并只验证 HRMS App 和基础 HR 模块可访问
- M0-R3B 已通过 Codex 审查，状态已从 REVIEWING 收口为 COMPLETED

本轮未做：

- 未安装 Frappe HR / HRMS
- 未创建 `hb_core_app`
- 未创建 `hb_attendance_app`
- 未创建 `hb_feishu_app`
- 未安装自定义 Frappe App
- 未开发考勤业务
- 未执行飞书真实写入
- 未开发前端驾驶舱
- 未写 Python/JavaScript/TypeScript 业务代码
- 未修改 `docker-compose.yml`、`.env.example`、`.gitignore`
- 未提交真实密钥
- 未 push

## M0-R3C 状态

状态：COMPLETED。

本轮目标：

- 将 M0-R3B 从 REVIEWING 收口为 COMPLETED
- 备份当前 `frontend` site 并记录安装前环境状态
- 基于官方 `frappe/hrms` 的 `version-16` 分支安装 Frappe HR / HRMS
- 验证 HRMS App 已安装，基础 HR 模块可在 Desk 中访问
- 记录安装命令、日志摘要、版本、验证结果、风险与回滚方式

当前结果：

- 安装前已完成 site 备份，备份位于 Docker volume 内的 `/home/frappe/frappe-bench/sites/frontend/private/backups/`
- HRMS 来源为官方 `frappe/hrms` 仓库 `version-16` 分支，分支 commit 为 `666bf10a9271421abc361bded124d2d961a977e3`
- 已执行 `bench get-app hrms --branch version-16`
- 已执行 `bench --site frontend install-app hrms`
- 已执行 `bench --site frontend migrate`
- 已执行最小必要服务刷新
- 安装后 `bench version` 显示 `hrms 16.12.0 version-16 (666bf10)`
- 安装后 `bench --site frontend list-apps` 显示 `hrms 16.12.0 version-16`
- Desk 登录页 `http://localhost:8081/login` 返回 `HTTP 200`
- 登录后 `/app/hr`、`/app/hr-setup`、`/app/employee`、`/app/leave-application`、`/app/shift-and-attendance` 均可访问并返回 `HTTP 200`
- HR Workspace 已包含 `HR Setup`、`Leaves`、`Shift & Attendance`、`Recruitment` 等入口

已知风险：

- 本轮采用现有容器 / bench 内安装验证，适合 M0-R3C 验证，不代表长期可复现部署方案已经完成。
- 当前 Compose 的 `configurator` 会基于镜像内 `apps` 目录重写 `sites/apps.txt`；后续如要长期保留 HRMS，应治理自定义镜像或 Compose 持久化策略。

本轮未做：

- 未创建 `hb_core_app`
- 未创建 `hb_attendance_app`
- 未创建 `hb_feishu_app`
- 未创建任何海滨自定义 Frappe App
- 未开发考勤业务规则
- 未配置飞书
- 未执行飞书真实写入
- 未开发前端驾驶舱
- 未写 Python/JavaScript/TypeScript 业务代码
- 未修改 Frappe/ERPNext/HRMS 核心源码
- 未修改 `docker-compose.yml`
- 未修改 `.env.example`
- 未提交 `.env`
- 未提交真实密钥
- 未 push

## M0-R3C-FIX 状态

状态：COMPLETED。

本轮目标：

- 复现并诊断 Frappe HR 图标缺失、HRMS 子模块图标缺失和 `/hr/roster` 白屏问题。
- 修复 HRMS 前端资源 404 与 Roster 静态资源不可访问问题。
- 验证 Frappe HR 图标、基础 HR 模块和 Roster 页面可访问。
- 更新项目状态、当前里程碑、M0 里程碑台账和修复记录。

当前结果：

- 复现到 `/assets/hrms/...` JS、CSS、SVG、favicon 资源返回 `404 text/html`，Roster 页面因资源缺失呈现白屏。
- 诊断根因为当前容器内 `sites/assets` 指向容器本地 `/home/frappe/frappe-bench/assets`，而 frontend 容器没有 backend 中 `bench get-app hrms` 得到的 app public 目录，导致 HRMS assets 软链在 frontend 中不可解析。
- 已执行 `bench --site frontend clear-cache`、`clear-website-cache`、`bench build` 和最小必要服务刷新。
- 已用解引用方式将 backend 构建后的真实静态资源同步到 frontend 容器实际 Nginx 资源目录。
- 已将官方 HRMS app 同步到 scheduler、queue 和 websocket 容器，并在 bench venv 中注册，避免后台服务因 `No module named 'hrms'` 重启。
- HTTP 验证显示 Frappe、ERPNext、HRMS 和 Roster 关键静态资源均返回 `HTTP 200`。
- 浏览器验证显示 `/app` Frappe HR 图标不再 broken，`/app/employee`、`/app/employee-checkin`、`/app/attendance`、`/app/shift-type` 均可渲染，`/hr/roster/` 已显示 Roster 月视图。

已知风险：

- 当前修复是运行时容器资源同步和运行时 app 同步，适合 M0-R3C-FIX 诊断修复，不代表长期可复现部署方案已经完成。
- 后续如重建 frontend、scheduler、queue 或 websocket 容器，仍需治理 HRMS 自定义镜像、Compose assets 持久化或部署流程。
- 浏览器控制台仍存在 `socket.io` Invalid origin 相关提示，本轮判断为非 HRMS 资源白屏根因，留待后续环境治理。

本轮未做：

- 未创建 `hb_core_app`
- 未创建 `hb_attendance_app`
- 未创建 `hb_feishu_app`
- 未创建任何海滨自定义 Frappe App
- 未开发考勤业务规则
- 未配置飞书
- 未执行飞书真实写入
- 未做 Vue / React 前端驾驶舱
- 未新增 Python / JavaScript / TypeScript 业务代码
- 未修改 Frappe / ERPNext / HRMS 核心源码
- 未修改 `docker-compose.yml`
- 未修改 `.env.example`
- 未提交 `.env`
- 未提交真实密钥
- 未配置 remote
- 未 push

## M0-R3D 状态

状态：COMPLETED。

本轮目标：

- 只读盘点 HRMS 原生考勤能力。
- 结合新乡海滨考勤一期需求，设计 M1 最小边界。
- 设计 M1 分轮计划、自定义 App 决策建议、飞书边界和 M1 启动前待确认清单。
- 更新项目状态、当前里程碑和 M0 里程碑台账。
- 创建一次 Git 提交。

当前结果：

- 已确认当前环境为 Frappe `16.25.0`、ERPNext `16.26.2`、HRMS `16.12.0 version-16 (666bf10)`，site 为 `frontend`，Desk `http://localhost:8081/login` 返回 `HTTP 200`。
- 已确认本地核心容器均为 Up，`db` healthy。
- 已确认当前未创建 `hb_core_app`、`hb_attendance_app`、`hb_feishu_app`。
- 已确认当前未录入真实员工、打卡、班次、考勤、请假、假日等业务数据；`Employee`、`Attendance`、`Employee Checkin`、`Shift Type`、`Shift Assignment`、`Shift Schedule`、`Leave Application`、`Holiday List` 均为 0 条。
- 已盘点 HRMS 原生能力：Employee、Attendance、Employee Checkin、Auto Attendance、Shift Type、Shift Assignment、Shift Schedule、Leave Application、Holiday List、Department / Branch / Company、Employee Attendance Tool、Attendance 报表、Biometric / 外部考勤设备集成思路、Payroll 边界。
- 已形成 M1 一期推荐边界：优先用测试数据验证 HRMS 原生对象，覆盖测试员工、早 / 中 / 夜班、Employee Checkin 导入、Auto Attendance、迟到早退、请假联动和最小报表。
- 已明确 M1 初期不建议立即创建 `hb_attendance_app`；只有 HRMS 原生对象无法表达海滨特有规则或验收报表必须定制时，才进入自定义 App 决策。
- 已明确 M1 一期不做飞书真实写入；飞书请假 / 加班同步应另开飞书集成阶段，并需用户明确授权。

本轮未做：

- 未创建 `hb_core_app`
- 未创建 `hb_attendance_app`
- 未创建 `hb_feishu_app`
- 未创建任何自定义 Frappe App
- 未新增 Python / JavaScript / TypeScript 业务代码
- 未修改 Frappe / ERPNext / HRMS 核心源码
- 未录入真实员工数据
- 未配置真实班次
- 未配置真实考勤规则
- 未配置真实请假 / 审批流
- 未接飞书真实写入
- 未做 Vue / React 前端驾驶舱
- 未修改 `docker-compose.yml`
- 未修改 `.env.example`
- 未提交 `.env`
- 未提交真实密钥
- 未配置 remote
- 未 push

## M0-R3E 状态

状态：COMPLETED。

本轮目标：

- 只读确认当前 Frappe / ERPNext / HRMS 容器环境、版本、apps 清单和 Desk 可访问性。
- 识别当前 HRMS 运行态安装带来的可复现性风险。
- 比较运行态文档化恢复、安装脚本 / 运维手册、自定义镜像三种可复现策略。
- 设计 M1 环境保护规则和 HRMS 恢复手册草案。
- 明确本轮不修改 `docker-compose.yml`、`.env.example`、`.gitignore`，不重建容器，不删除 volume，不重新安装 HRMS。

当前结果：

- 当前容器均处于运行状态，`db` healthy。
- Desk 地址 `http://localhost:8081/login` 返回 `HTTP 200 text/html; charset=utf-8`。
- `bench version` 显示 ERPNext `16.26.2`、Frappe `16.25.0`、HRMS `16.12.0 version-16 (666bf10)`。
- `bench --site frontend list-apps` 显示 `frappe`、`erpnext`、`hrms`。
- 已确认 HRMS 仍属于运行态安装成果，仓库当前没有固化包含 HRMS 的自定义镜像。
- 已新增 `docs/deployment/M0-R3E_HRMS环境可复现性收口.md`，记录风险、策略、M1 环境保护规则和恢复手册草案。
- M0-R3E 已通过 Codex 审查，状态已从待审查收口为 COMPLETED。
- 当前推荐 M1-R1 至 M1-R5 期间优先保护当前已跑通环境，不急于重构镜像；如未来多人开发、服务器部署、长期交付或 CI/CD，再单独启动环境可复现阶段。

本轮未做：

- 未执行 `docker compose down -v`
- 未删除 Docker volume
- 未重建 site
- 未重新安装 HRMS
- 未修改 `docker-compose.yml`
- 未修改 `.env.example`
- 未修改 `.gitignore`
- 未创建 `hb_core_app`
- 未创建 `hb_attendance_app`
- 未创建 `hb_feishu_app`
- 未创建任何海滨自定义 Frappe App
- 未新增 Python / JavaScript / TypeScript 业务代码
- 未修改 Frappe / ERPNext / HRMS 核心源码
- 未录入真实员工数据
- 未配置真实班次或真实考勤规则
- 未接飞书真实写入
- 未做 Vue / React 前端驾驶舱
- 未提交 `.env`、备份文件或真实密钥
- 未配置 remote
- 未 push

## M0-FINAL 状态

状态：COMPLETED。

M0 最终边界：

- Docker / Frappe / ERPNext / HRMS 基线已跑通。
- HRMS 已安装并验证。
- HR Workspace 可访问。
- HR 基础 DocType 存在。
- HRMS 环境可复现性风险、保护规则和恢复手册草案已收口。
- 当前仍未创建自定义 App。
- 当前仍未开发考勤业务。
- 当前仍未接飞书。
- M0-FINAL 收口时仍无远端 remote；M0-REMOTE 已在后续轮次完成 GitHub Private remote 创建、`origin` 绑定和 `main` 首次 push。

后续架构原则：

- 不直接修改 Frappe / ERPNext / HRMS 核心源码。
- 优先使用原生配置、角色权限、DocType、报表、导入、API 和低代码定制。
- 自定义 App 只用于海滨特有规则，不用于重写 HRMS 已有功能。
- M1 初期不立即创建 `hb_attendance_app`。
- 飞书真实写入必须用户明确授权。
- 不得执行 `docker compose down -v`，不得删除 volume，不得重建 `frontend` site。
- `.env`、备份文件、密钥、数据库、Docker volume 和运行时数据不得提交。

## M0 后续路线记录

M0-FINAL 收口后的路线已执行到 M1-R5：

1. M0-REMOTE：已完成。
2. M1-R0：已通过 Codex 独立审查，状态 COMPLETED。
3. M1-R1：已通过 Codex 独立审查，状态 COMPLETED。
4. M1-R2：已通过 Codex 独立审查，状态 COMPLETED。
5. M1-R3：BLOCKED，已执行 HRMS 原生考勤最小测试数据试运行并通过 Codex 审查，实际结论为 PARTIAL / BLOCKED。
6. M1-R3A：COMPLETED，运行态阻断诊断与 TEST 数据隔离 / 清理方案，已通过 Codex 审查。
7. M1-R3B：COMPLETED，运行态最小修复方案，已通过 Codex 审查。
8. M1-R3B-FIX：COMPLETED，运行态最小修复已执行并通过 Codex 审查。
9. M1-R3C：COMPLETED，HRMS 原生考勤最小试运行复测，结论为 PARTIAL / GAP_IDENTIFIED。
10. M1-R3D：COMPLETED，HRMS 原生考勤异常口径与配置 Gap 诊断，已通过 Codex 审查。
11. M1-R3E：COMPLETED，配置复核清单与业务口径确认表已通过 Codex 审查。
12. M1-R3F：COMPLETED，业务口径确认包已通过 Codex 审查。
13. M1-REQ-DESIGN-DRAFT：COMPLETED，需求设计四份文档已通过 Codex 审查。
14. M1-R4：COMPLETED，Demo 技术方案与实施路线拆分已通过 Codex 审查并收口。
15. M1-R5：COMPLETED，HRMS 配置基线、考勤工作台与月度汇总 Demo 已通过 Codex 审查并收口。主文档 `docs/milestones/M1_R5_HRMS配置基线工作台月报Demo.md` 已交付。
16. M1-R6A：COMPLETED，Excel 导入与异常流程落地方案 / Gate 判定，主文档 `docs/milestones/M1_R6A_Excel导入与异常流程落地方案.md` 已交付，Codex 审查 PASS。
17. M1-R6B：COMPLETED，脱敏打卡流水导入最小验证，主文档 `docs/milestones/M1_R6B_脱敏打卡流水导入最小实现.md` 已交付并完成 closeout。
18. M1-R6C：COMPLETED，异常识别与异常说明流程最小实现已通过 Codex 审查并 closeout。
19. M1-R7：COMPLETED，飞书登录、领导 Demo 与 M1 收口准备，已通过 Codex 审查并 closeout。
20. M1-R8：PLANNED（可选缓冲轮，因 M1 closeout 完成可能跳过）。
21. M1 总收口：历史 closeout 已完成；Owner UI 验收发现功能缺口后，当前 M1 产品交付仍在 M1-FIX 中，尚未完成。
22. M1-FIX-A：REVIEWING，功能补漏差距盘点与实施方案已交付。
23. M1-FIX-B：REVIEWING，Excel 导入与真实本地数据闭环已实现。
24. M1-FIX-B2：COMPLETED，导入口径、安全与准确性修复已通过 Claude 审查并 closeout。
25. M1-FIX-B3：REVIEWING / Owner UI 验收未通过，考勤工作台入口、App 命名与 HRMS 数据一致性修复不能 closeout。
26. M1-FIX-B4：REVIEWING / Claude PASS，但 Owner 数据链路验收发现后续问题；B4 不 closeout。
27. M1-FIX-B5：REVIEWING，导入数据链路核查与报表口径收敛已交付，等待 Owner 和 Claude 审查。
28. M2-STOCK-R1：IN_PROGRESS，库存模块隔离——新建独立 `stock` 站点（只装 frappe + erpnext）、新增 `hb_stock_app` 与「海滨库存」工作台，使库存数据与考勤站点 `frontend` 物理隔离。分支 `m2-stock-r1`，主文档 `docs/milestones/M2_STOCK_R1_库存模块隔离实施记录.md`。Task 3（建站 + frontend 备份）、Task 4（App 安装 + 工作台生成 + migrate 幂等）、Task 5（HAIBIN 公司 + 默认仓库）已交付 PASS，Task 7/8 待续。

## M1-FIX 状态

状态：IN_PROGRESS。

M1 已 closeout 为 COMPLETED，但 Owner 亲自验收后发现「方案完成」不等于「功能完成」——大量产品功能没有真正页面可体验。M1-FIX 阶段定位为功能补漏，补齐 M1 承诺但未实际可体验的产品功能。

M1-FIX-A：REVIEWING。本轮为差距盘点与补漏实施方案，主文档 `docs/milestones/M1_FIX_功能补漏实施方案.md` 已交付。识别 20 项差距、给出自定义 App/DocType 初步判断、拆分 M1-FIX-B/C/D/E 推荐顺序。

M1-FIX-B：REVIEWING。本轮已创建轻量 `hb_attendance_app`、导入日志和 `海滨考勤工作台`，支持 Owner 本地真实 Excel 识别、员工匹配 / 创建、打卡流水适配生成、HRMS 自动考勤尝试、本地兜底生成标记和导入日志统计。主文档 `docs/milestones/M1_FIX_B_Excel导入与真实数据闭环.md` 已交付。

M1-FIX-B-FIX：REVIEWING。本轮补齐 `导入考勤机导出表` 浏览器入口、中文 `打卡流水` / `考勤结果` 报表、重复导入可读说明、兜底生成说明和默认白班/行政班 08:30-17:30。主文档 `docs/milestones/M1_FIX_B_FIX_Excel导入与中文体验修复.md` 已交付。

M1-FIX-B2：COMPLETED。导入口径、安全与准确性修复已通过 Claude 审查并 closeout。

M1-FIX-B3：REVIEWING / Owner UI 验收未通过。本轮不 closeout B3，Owner 真实浏览器发现桌面 icon、左侧导航、导入页归属和 HBOS / HRMS 入口口径仍混乱。

M1-FIX-B4：REVIEWING / Claude PASS，但 Owner 数据链路验收发现后续问题。本轮按 Owner 确认的方案 A 收敛运行态入口：`after_migrate` 幂等同步 Workspace、Workspace Sidebar、Desktop Icon；桌面入口显示为 `海滨考勤` 并使用实际可见 SVG；导入页增加 `海滨考勤工作台 / 导入考勤机导出表` 说明和返回入口；HBOS 报表与 HRMS 原生入口显示口径已区分。主文档 `docs/milestones/M1_FIX_B4_考勤模块架构收敛与单一入口重整.md` 已交付，B4 本轮不 closeout。

M1-FIX-B5：REVIEWING。本轮核查真实数据库中 Employee / Employee Checkin / Attendance / HBOS Attendance Import Log / 月度汇总暂存链路；确认 HRMS 原生月度考勤表空表主因是用户默认 Company 指向 Demo，正确 Company 下有 2026-07 Attendance；修复 HBOS 报表固定 500 行截断与缺少部门 / 批次过滤的问题；新增 `HBOS 月度汇总暂存（对账）` 报表；HRMS 原生入口降级为技术核查。2026-08-21 后续修正（本轮）：① 分机孤立卡误判缺勤修复——方向不同的相邻卡不合并（陈雨欣 8/19 案例）+ 当天已有完整上下班结构时孤立卡不判缺勤；② 配对上限 13h→14h 放宽（李明 8/19 无菌班 13.17h 案例），19 点后 12h 班按无菌晚不判迟到（张志兴 8/19）；③ 跨天夜班下班误刷上班机修复（吕玉升/庞冠军 8/16 案例）；重算 8/15-8/20 后总缺勤 382→321，迟到 30→28，早退 3→2；豁免名单双向核对 0 命中。2026-08-27 后续修正：⑨ 月度考勤汇总新增「异常考勤导出」按钮（格式对齐 HBOS 异常考勤报表参考文件：总览/缺勤汇总/迟到早退三表）；⑩ 考勤判定规则收敛——配对上限 14h→16h、有卡就不判缺勤、连续无打卡 1-2 天不判缺勤 3 天起判（缺勤 8/15-26 由 489 收敛至 134，误判率大幅下降）；⑪ 2026 年度离职名单批量处理（78 人名单，系统匹配 10 人，新增 5 人标记 Left）；⑫ 人员状态维护——曹凯莉产假豁免、曹祖军退休 Left、刘凤岭/马照辉长期病假豁免、王卫勋离职 Left、张习方数据修正（11004052 改名 + 11004009 停用），8/15-26 缺勤最终收敛至 71。主文档 `docs/milestones/M1_FIX_B5_导入数据链路核查与报表口径收敛.md` 已交付。**2026-08-21 后续修正**：四车间 10 人行政班误判迟到修复（补回 ADMIN_NUMS + 名单短路规则表 + `admin_shift_from_gap`）；质量控制部四班次人员按「工作满 8 小时算正常」口径收敛；配对上限 18h→13h；陈玉姣/王梅林产假加入豁免名单；新增 7 个测试用例，本地全量 58 用例通过。8/15 后数据已重算验证准确；7/28-8/14 分机前数据存在全量重算缺勤异常（根因未定位），为遗留问题。2026-09-02 追加：班次管理页新增「规则看板」Tab，三类班次判定规则可视化（规则记录含绑定人数 / 内置班次 / 名单与配对参数），判定逻辑零改动。2026-09-02 再追加：规则看板可导出班次人员维护表（5-sheet：部门-班次-人员主表 + 豁免/特殊班次/行政班名单/说明）。2026-09-03 追加：月度考勤汇总新增「AI复核」（enable_ai 隐藏临时列）——确认人次后逐人调 LLM 复核当月异常（迟到/早退/缺勤）生成 AI 列，随「导出 Excel」透传，重新筛选自动复位。2026-09-08 追加：工作台新增「部门看板」（Desk 页面实时出勤快照 + 历史回顾；排班优先+规则推断、通用倒班计入应出勤、保守迟到判定、回顾不判缺勤、60s 自动刷新 + 手动同步 120s 节流、+8 时区、接口角色门禁）——代码与测试已入库（全量 144 通过），设计 spec / 实施计划已提交，运行态 migrate 注册待 Owner 授权。2026-09-11 追加：考勤提醒改发飞书卡片（只列异常部门+人名，正常部门汇总一行；渲染失败自动降级纯文本；判定口径与调度不变）。2026-09-15 追加：卡片运行态验证完成（Owner 授权）——实测裁定 interactive 报文外壳字段名为顶层 `card`（`code:0`）；原稿写的 `content` 会被拒（`code:19002`）且按设计不补发纯文本，等于提醒每天静默消失；干跑数字与看板同源一致、恒等式成立；已实发卡片到群（`sent: true`）；backend/scheduler 已 `restart` 加载新代码，次日 09:00 起自动发卡片。2026-09-24 追加：名单单一来源收敛（行政班 221→178 单一来源、无菌 48→59 改用 `SPECIAL_SHIFT_NUMS`、`EXCLUDE_NUMS` 冗余标注、旧引擎补废弃标记）与 PR 审查 5 项修复（去重窗口与配对下限对撞、`.env.example` 缺 9 变量、CI `.env` 门禁误伤模板、部门看板 XSS、月报 AI 复核 `list.index`），详见上方「2026-09-24 名单单一来源收敛与 PR 审查修复」节。

M1-FIX 后续规划（仅规划，不自动启动）：

| 轮次 | 名称 | 优先级 | 状态 |
| --- | --- | --- | --- |
| M1-FIX-A | 差距盘点与实施方案 | — | REVIEWING |
| M1-FIX-B | Excel 导入与真实本地数据闭环 | P0 | REVIEWING |
| M1-FIX-B-FIX | Excel 导入与中文体验修复 | P0 | REVIEWING |
| M1-FIX-B2 | 导入口径、安全与准确性修复 | P0 | COMPLETED |
| M1-FIX-B3 | 考勤工作台入口、App 命名与 HRMS 数据一致性修复 | P0 | REVIEWING / Owner UI 验收未通过 |
| M1-FIX-B4 | 考勤模块架构收敛与单一入口重整 | P0 | REVIEWING / Claude PASS，Owner 数据链路验收发现后续问题 |
| M1-FIX-B5 | 导入数据链路核查与报表口径收敛 | P0 | REVIEWING |
| M1-FIX-C | 异常说明三级流程 | P1 | PLANNED |
| M1-FIX-D | 考勤工作台 + 月报 + 领导 Demo | P1 | PLANNED |
| M1-FIX-E | 飞书 OAuth 最小验证 + Owner 体验脚本 + 总审查 | P2 | PLANNED |
| M1-FIX-F | 调休模块（一阶段：同步+解析+核实；二阶段：接入判定豁免） | P1 | REVIEWING / 两阶段均已上线 |

状态口径：
- M1 = IN_PROGRESS（产品交付仍在 M1-FIX 中）
- M1-FIX = IN_PROGRESS
- M1-FIX-A = REVIEWING
- M1-FIX-B = REVIEWING
- M1-FIX-B-FIX = REVIEWING
- M1-FIX-B2 = COMPLETED
- M1-FIX-B3 = REVIEWING / Owner UI 验收未通过
- M1-FIX-B4 = REVIEWING / Claude PASS，Owner 数据链路验收发现后续问题
- M1-FIX-B5 = REVIEWING
- M1-FIX-F = REVIEWING / 两阶段均已上线，整支复查已处置
- M1-FIX-C/D/E = PLANNED
- M2-STOCK-R1 = IN_PROGRESS（库存模块隔离，分支 `m2-stock-r1`）
- M2 其余轮次 = NOT STARTED / WAITING OWNER AUTHORIZATION

M1-FIX 全程禁止：不创建 `hb_core_app`，不把 `hb_attendance_app` 扩大为大而全 HR App，不修改 Frappe/ERPNext/HRMS 核心源码，不提交 `.env`/App Secret/密钥/token/真实数据/Excel/CSV，不接真实考勤机，不部署公司内网/云服务器，不启动大型 Vue/React 前端，不在 M1-FIX 轮次内做 M2 工作（M2-STOCK-R1 已在独立分支 `m2-stock-r1` 进行，不在本分支展开），不伪造飞书登录成功，不执行 `docker compose down -v`，不删除 Docker volume，不重建 `frontend` site。

## M0-REMOTE 状态

状态：COMPLETED。

本轮目标：

- 创建 GitHub Private 仓库。
- 添加 `origin`。
- 首次 push `main`。
- 确认 `origin/main` 与本地 `main` 一致。
- 记录远端信息和下一步 M1-R0 路线。

当前结果：

- GitHub 仓库：`https://github.com/zjl327707743/HBOS`
- Git remote URL：`https://github.com/zjl327707743/HBOS.git`
- visibility：`PRIVATE`
- 首次 push 的本地 HEAD：`0a29ca526a417d7ec666234f9312dd3de47a687b`
- 首次 push 后本地 `main` 与 `origin/main` 一致。
- M0-REMOTE 本轮仅完成远端创建、绑定、push 和状态记录；当时 M1 尚未启动。当前 M1-R0 已收口为 COMPLETED。

本轮未做：

- 未创建自定义 Frappe App。
- 未创建 `hb_attendance_app`。
- 未开发考勤业务。
- 未开发飞书集成。
- 未实现 SSO。
- 未修改中文化源码。
- 未修改 Frappe / ERPNext / HRMS 核心源码。
- 未执行 `docker compose down -v`。
- 未删除 volume。
- 未重建 `frontend` site。
- 未提交 `.env`、备份、密钥、数据库、日志、缓存或运行时产物。

## M1 状态

状态：COMPLETED。

M1 考勤一期已 closeout。M1 全程为规划、验证与 Demo 准备阶段，不代表进入正式业务开发。

当前轮次：

- M1-R0：COMPLETED。
- M1-R1：COMPLETED。
- M1-R2：COMPLETED。
- M1-R3：BLOCKED。
- M1-R3A：COMPLETED。
- M1-R3B：COMPLETED。
- M1-R3B-FIX：COMPLETED。
- M1-R3C：COMPLETED。
- M1-R3D：COMPLETED。
- M1-R3E：COMPLETED。
- M1-R3F：COMPLETED。
- M1-R4：COMPLETED。
- M1-R5：COMPLETED。
- M1-R6A：COMPLETED。
- M1-R6B：COMPLETED。
- M1-R6C：COMPLETED，异常识别与异常说明流程最小实现已通过 Codex 审查并 closeout。
- M1-R7：COMPLETED，飞书登录、领导 Demo 与 M1 收口准备，已通过 Codex 审查并 closeout。
- M1-R8：PLANNED（可选缓冲轮）。

M1-R0 当前结果：

- 已新增 `docs/milestones/M1_R0_平台入口账号权限与本地化诊断方案.md`。
- 已通过 Codex 独立审查，并在 M1-R0-CLOSEOUT 中收口为 COMPLETED。
- 已明确 HBOS 账号目标：飞书登录为主，HBOS 内部账号自动映射，Frappe 权限体系承接系统权限和审计。
- 已规划平台入口、账号体系、角色权限、飞书 SSO 可行性和中文化 / 本地化诊断。
- 已明确 M1-R1 前置条件。

M1-R0 未做：

- 未创建自定义 Frappe App。
- 未创建 `hb_attendance_app`。
- 未开发考勤业务。
- 未接真实飞书。
- 未写入飞书。
- 未实现 SSO。
- 未修改 Frappe / ERPNext / HRMS 核心源码。
- 未修改中文翻译源码。
- 未执行 `docker compose down -v`。
- 未删除 volume。
- 未重建 `frontend` site。
- 未提交 `.env`、备份、密钥、数据库、日志、缓存或运行时产物。

M1-R1 当前结果：

- 已新增 `docs/milestones/M1_R1_HRMS原生考勤对象模型验证记录.md`。
- M1-R1 已通过 Codex 独立审查，并在 M1-R1-CLOSEOUT 中从待审查状态收口为 COMPLETED。
- 已通过只读命令确认当前运行态环境：Frappe `16.25.0`、ERPNext `16.26.2`、HRMS `16.12.0 version-16 (666bf10)`，site 为 `frontend`，Desk 登录页 `http://localhost:8081/login` 返回 `HTTP 200`。
- 已通过只读元数据查询确认 User、Employee、Department、Company、Holiday List、Shift Type、Shift Assignment、Employee Checkin、Attendance、Attendance Request、Leave Application、Leave Type 等 DocType 存在。
- 已确认 Shift Type 原生具备自动考勤、IN / OUT 判断、工时计算、迟到早退宽限、打卡时间窗等字段。
- 已确认 Employee Checkin 可承接打卡原始记录，Attendance 可承接日考勤结果，Leave Application / Leave Type 可承接请假对象。
- 已确认 `Shift & Attendance` 等 HR Workspace 入口存在，并确认 `Monthly Attendance Sheet`、`Shift Attendance`、`Employees working on a holiday` 等原生报表存在。
- 已形成需求映射和 Gap List，初步结论为 M1 初期优先复用 HRMS 原生能力，不建议现在创建 `hb_attendance_app`。
- 已建议下一轮为 M1-R2：HRMS 原生考勤配置试运行方案。

M1-R1 未做：

- 未创建自定义 Frappe App。
- 未创建 `hb_attendance_app`。
- 未新增业务 DocType。
- 未开发考勤业务。
- 未接真实考勤机。
- 未接真实飞书。
- 未写入飞书。
- 未实现 SSO。
- 未修改 Frappe / ERPNext / HRMS 核心源码。
- 未修改中文翻译源码。
- 未录入真实员工、真实考勤或真实生产数据。
- 未创建测试员工、测试打卡或测试考勤结果。
- 未执行 `docker compose down -v`。
- 未删除 volume。
- 未重建 `frontend` site。
- 未提交 `.env`、备份、密钥、数据库、日志、缓存或运行时产物。

M1-R2 当前结果：

- 已新增 `docs/milestones/M1_R2_HRMS原生考勤配置试运行方案.md`。
- M1-R2 已通过 Codex 独立审查，并在 M1-R2-CLOSEOUT 中从待审查状态收口为 COMPLETED。
- 已承接 M1-R1 结论：HRMS 原生能力是 M1 初期主路线，当前不建议创建 `hb_attendance_app`。
- 已设计最小测试组织、最小班次、最小打卡场景、HRMS 配置步骤草案、打卡数据导入字段草案、验收用例、成功标准、风险与待确认事项。
- 已明确 M1-R2 只是方案设计，不执行配置试运行，不创建测试数据，不生成可直接导入的 CSV / Excel 测试数据文件。
- 已建议下一轮为 M1-R3：HRMS 原生考勤最小测试数据试运行。

M1-R2 未做：

- 未执行配置试运行。
- 未创建测试 Employee / Shift Type / Employee Checkin / Attendance / Leave Application。
- 未创建可直接导入的 CSV / Excel / JSON 测试数据文件。
- 未创建自定义 Frappe App。
- 未创建 `hb_attendance_app`。
- 未新增业务 DocType。
- 未开发考勤业务。
- 未接真实考勤机。
- 未接真实飞书。
- 未写入飞书。
- 未实现 SSO。
- 未修改 Frappe / ERPNext / HRMS 核心源码。
- 未修改中文翻译源码。
- 未录入真实员工、真实打卡、真实考勤或真实生产数据。
- 未执行 `docker compose down -v`。
- 未删除 volume。
- 未重建 `frontend` site。
- 未提交 `.env`、备份、密钥、数据库、日志、缓存或运行时产物。

M1-R3 当前结果：

- 已新增 `docs/milestones/M1_R3_HRMS原生考勤最小测试数据试运行记录.md`。
- M1-R3 已通过 Codex 审查，审查结果 PASS。
- M1-R3 实际结论为 PARTIAL / BLOCKED，最终状态收口为 BLOCKED，不标记为 COMPLETED。
- 本轮曾创建部分 `TEST-HBOS-M1R3-*` 虚构测试数据。
- 当前只读诊断确认已落库范围包括 2 个 Department、1 个 Holiday List、1 个 Leave Type、8 个 Employee、4 个 Shift Type、6 个 Shift Assignment 和 12 条 Employee Checkin。
- Company 与 User 未创建成功，Attendance 与 Leave Application 为 0。
- 14 个打卡 / 请假 / 加班 / 节假日 / 调班场景未完成 Attendance 闭环验证。
- 当前仍不建议创建 `hb_attendance_app`。

M1-R3A 当前结果：

- 已新增 `docs/milestones/M1_R3A_运行态阻断诊断与TEST数据隔离清理方案.md`。
- M1-R3A 只做运行态阻断诊断和 TEST 数据隔离 / 清理方案，已通过 Codex 审查并收口为 COMPLETED。
- M1-R3A-CLOSEOUT 仅做状态收口，未修复服务、未清理 TEST 数据、未继续创建测试数据。
- 诊断发现 `redis-cache` 与 `redis-queue` 容器已退出，queue worker 和 websocket 反复重启。
- `bench doctor` 因 Redis Queue 连接失败无法完成；`bench --site frontend list-apps` 与 `http://localhost:8081/login` 在本轮检查中长时间无返回。
- MariaDB 可见进程列表未捕获活动阻塞 SQL，但当前账号缺少 `PROCESS` 权限，无法读取 InnoDB 事务与锁等待详情。
- 当前判断阻断更可能来自运行态 Redis / queue / websocket / site 请求路径异常和潜在数据库连接 / 锁状态，而不是 HRMS 原生对象模型已被证明不可用。
- 已形成清理顺序建议：Attendance、Leave Application、Employee Checkin、Shift Assignment、Shift Type、Employee、User、Leave Type、Department、Holiday List、Company。
- 清理和修复均需用户后续明确授权。

M1-R3A 未做：

- 未继续创建测试数据。
- 未继续执行配置试运行。
- 未清理或删除 TEST 数据。
- 未创建自定义 Frappe App。
- 未创建 `hb_attendance_app`。
- 未新增 DocType。
- 未开发考勤业务。
- 未接真实考勤机。
- 未接真实飞书。
- 未写入飞书。
- 未实现 SSO。
- 未修改 Frappe / ERPNext / HRMS 核心源码。
- 未修改中文翻译源码。
- 未提交 `.env`、备份、密钥、数据库、日志、缓存或运行时产物。

M1-R3B 当前结果：

- 已新增 `docs/milestones/M1_R3B_运行态最小修复方案.md`。
- M1-R3B 只制定运行态最小修复方案，已通过 Codex 审查并收口为 COMPLETED。
- 方案承接 M1-R3A 诊断结论：`redis-cache` 与 `redis-queue` 退出，queue worker 和 websocket 反复重启，`bench doctor` 因 Redis Queue 连接失败无法完成，`list-apps` 与 `/login` 存在长时间无返回症状。
- M1-R3B-FIX 已按方案执行运行态最小修复，并已通过 Codex 审查收口为 COMPLETED。
- M1-R3B-FIX 只读计数确认当前 TEST 数据范围包括 Employee 8、Shift Type 4、Shift Assignment 14、Employee Checkin 22、Leave Application 2、Attendance 12 等；该计数高于 M1-R3A / M1-R3B 旧记录，需在 M1-R3C 或清理授权前复核。
- 方案覆盖 Redis、worker、scheduler、`bench doctor`、`list-apps`、login 的最小诊断与修复步骤草案。
- 方案覆盖 Company / User / Employee 创建阻断的复测路径。
- 方案明确本轮不清理 TEST 数据，清理需用户另行授权。
- 方案明确 M1-R3C 进入条件：运行态稳定、TEST 数据隔离边界明确、用户授权重新试运行。
- 当前仍不建议创建 `hb_attendance_app`。

M1-R3B 未做：

- M1-R3B 方案轮本身未执行运行态修复；运行态修复执行已在 M1-R3B-FIX 中记录并收口为 COMPLETED。
- 未清理或删除 TEST 数据。
- 未继续创建测试数据。
- 未执行 HRMS 配置试运行。
- 未创建自定义 Frappe App。
- 未创建 `hb_attendance_app`。
- 未新增 DocType。
- 未开发考勤业务。
- 未接真实考勤机。
- 未接真实飞书。
- 未写入飞书。
- 未实现 SSO。
- 未修改 Frappe / ERPNext / HRMS 核心源码。
- 未提交 `.env`、备份、密钥、数据库、日志、缓存或运行时产物。

M1-R3C 当前结果：

- 已新增 `docs/milestones/M1_R3C_HRMS原生考勤最小试运行复测记录.md`。
- M1-R3C 已在用户明确授权下使用虚构 TEST 数据重新试运行，并已通过 Codex 审查收口为 COMPLETED。
- M1-R3C 结论为 PARTIAL / GAP_IDENTIFIED；这是试运行完成，不是考勤业务闭环完成。
- 本轮使用新前缀 `TEST-HBOS-M1R3C-*` / `test-hbos-m1r3c-*`，未覆盖旧 `TEST-HBOS-M1R3-*` 数据。
- 运行态复核显示 `/login` 返回 HTTP 200，scheduler enabled，`bench doctor` 显示 worker online，Redis / queue / scheduler / frontend / backend / db 容器可用。
- Company / User / Employee 写入阻断已解除：Company 1、User 8、Employee 8 已成功创建。
- M1-R3C 最终虚构数据计数包括 Department 2、Holiday List 1、Shift Type 4、Shift Assignment 14、Employee Checkin 22、Leave Type 1、Attendance 13；Leave Application 因缺少 Leave Allocation 未创建。
- 14 个场景已完成复测记录：8 个通过，6 个为 GAP / PARTIAL。Attendance 可由 HRMS 原生生成；迟到 / 早退未置位是 Gap，缺卡 / 缺勤口径是 Gap，请假因 Leave Allocation 未闭环是 Gap，加班仅体现 `working_hours`，业务口径待定义。
- 当前仍不建议创建 `hb_attendance_app`。
- M1-R3D 已通过 Codex 审查并收口为 COMPLETED；M1-R3E 已通过 Codex 审查并收口为 COMPLETED；M1-R4 未启动。

M1-R3C 未做：

- 未使用真实员工、真实部门、真实考勤机、真实飞书或生产数据。
- 未清理、删除或覆盖旧 TEST 数据。
- 未创建自定义 Frappe App。
- 未创建 `hb_attendance_app`。
- 未新增 DocType。
- 未开发考勤业务代码。
- 未接真实考勤机。
- 未接真实飞书。
- 未写入飞书。
- 未实现 SSO。
- 未修改 Frappe / ERPNext / HRMS 核心源码。
- 未提交 `.env`、备份、密钥、数据库、日志、缓存或运行时产物。

M1-R3D 当前结果：

- 已新增 `docs/milestones/M1_R3D_异常口径与Gap诊断.md`。
- M1-R3D 只做异常口径与 Gap 诊断，并已通过 Codex 审查收口为 COMPLETED。
- M1-R3D-CLOSEOUT 仅做状态收口，未继续试运行，未创建、删除或清理 TEST 数据，未创建 App / DocType / 代码。
- 已承接 M1-R3C 结论：14 个场景中 8 个通过，6 个为 GAP / PARTIAL；Attendance 可由 HRMS 原生生成。
- 已将迟到 `late_entry` 未置位、早退 `early_exit` 未置位归入 HRMS 配置复核优先。
- 已将上班缺卡 / 下班缺卡归入原生报表 / 自定义报表和海滨业务规则定义。
- 已将全天缺勤未生成 Attendance 归入 HRMS 配置复核优先，必要时用报表补足候选识别。
- 已将请假受 Leave Allocation 阻断归入 HRMS 请假配置和海滨请假口径定义。
- 已将加班仅体现 `working_hours` 归入海滨业务规则定义，报表可先识别候选。
- 已补充节假日出勤、临时调班需要待遇、审批、追溯等业务口径。
- 当前仍不建议创建 `hb_attendance_app`。8 个 Gap 均不需要立即创建自定义 App。
- M1-R3E 已通过 Codex 审查并收口为 COMPLETED；M1-R4 未启动。

M1-R3D 未做：

- 未继续试运行。
- 未创建、删除或清理 TEST 数据。
- 未创建自定义 Frappe App。
- 未创建 `hb_attendance_app`。
- 未新增 DocType。
- 未开发考勤业务代码。
- 未接真实考勤机。
- 未接真实飞书。
- 未写入飞书。
- 未实现 SSO。
- 未修改 Frappe / ERPNext / HRMS 核心源码。
- 未提交 `.env`、备份、密钥、数据库、日志、缓存或运行时产物。

M1-R3E 当前结果：

- 已新增 `docs/milestones/M1_R3E_配置复核与业务口径确认表.md`。
- M1-R3E 只做文档交付，不做试运行、不清理 TEST 数据、不开发业务。
- HRMS 配置复核清单覆盖迟到 `late_entry`、早退 `early_exit`、全天缺勤、Leave Allocation、缺卡基础字段、加班候选字段、节假日出勤基础配置和临时调班基础配置。
- 海滨业务口径确认表覆盖迟到、早退、上班缺卡、下班缺卡、全天缺勤、半天请假、全天请假、加班、节假日出勤和临时调班。
- 已记录缺卡异常候选表、缺勤候选表、加班候选表和调班追溯表为 M1-R4 报表候选；本轮未实现报表。
- 已明确 Attendance 生成不等同于海滨考勤业务闭环完成。
- 当前仍不建议创建 `hb_attendance_app`。
- M1-R3E 已通过 Codex 审查并收口为 COMPLETED；M1-R4 未启动。

M1-R3E 未做：

- 未继续试运行。
- 未创建、删除或清理 TEST 数据。
- 未创建自定义 Frappe App。
- 未创建 `hb_attendance_app`。
- 未新增 DocType。
- 未开发考勤业务代码。
- 未接真实考勤机。
- 未接真实飞书。
- 未写入飞书。
- 未实现 SSO。
- 未修改 Frappe / ERPNext / HRMS 核心源码。
- 未提交 `.env`、备份、密钥、数据库、日志、缓存或运行时产物。

## M1-R6A 状态

状态：COMPLETED。

审查记录：Codex 初审 FAIL（R6A 文档未提交、工作区不 clean），已在 `330f320` 中修复并提交。Codex 复审 PASS。M1-R6A 已从 REVIEWING 收口为 COMPLETED。本次 closeout 仅做状态收口，未启动 R6B/R6C/R7，未修改方案结论。

本轮目标：

- 明确 R6 的最小实现路径。
- 核验 HRMS/Frappe 原生能力能否支撑原始打卡流水导入、月度汇总 Excel 导入、Attendance Request 异常说明流程、员工→主管→人事的三级处理流程。
- 判断 R6B 是否需要自定义导入入口、导入批次记录、Attendance Exception、Attendance Correction、`hb_hr_app`。
- 拆分 R6B / R6C 后续执行任务。

当前结果：

- 已明确两类 Excel 导入边界（原始打卡流水导入 ≠ 月度汇总 Excel 导入）。
- 已完成 Frappe Data Import 对 Employee Checkin 导入的能力评估：PASS，原生可覆盖；如需导入批次记录则需自定义 DocType `HBOS Import Log`。
- 已完成 Attendance Request 对异常说明三级流程的能力评估：CONDITIONAL PASS，优先方案 A（Custom Field 扩展原生 Attendance Request + Custom Workflow），方案 B 为备选。
- 已判定 R6B/R6C 不需要创建 `hb_hr_app`。
- 已判定 R6B 需要创建有限的自定义 DocType（`HBOS Import Log`、月度汇总 DocType）。
- 已拆分 R6B（Excel 导入与自动识别）和 R6C（异常流程与月度汇总整合）的详细边界和目标。
- 已完成 6 项 R6 相关 Gate 的逐项判定。
- 本轮未导入 Excel、未创建 App、未创建 DocType、未写代码、未动数据库。
- 本轮未接真实考勤机、未接飞书、未修改核心源码。

M1-R6A 未做：

- 未实现 Excel 导入功能。
- 未导入真实或脱敏 Excel。
- 未创建 App。
- 未创建 DocType。
- 未写正式导入代码。
- 未写异常流程正式代码。
- 未启动 M1-R7。
- 未接飞书登录。
- 未接真实考勤机。
- 未正式接飞书请假。
- 未接飞书工作台。
- 未部署公司内网/云服务器。
- 未修改 Frappe / ERPNext / HRMS 核心源码。
- 未提交 `.env`、备份、密钥、数据库、日志、缓存或运行时产物。

## M1-R6B 状态

状态：COMPLETED。

本轮目标：

- 识别 Owner 提供 Excel 的真实类型。
- 确认该 Excel 能否支撑原始打卡流水导入。
- 固定 Demo 脱敏原始打卡流水模板。
- 验证 Employee 匹配规则。
- 写入 HRMS 原生 `Employee Checkin`。
- 触发或记录 Auto Attendance 处理结果。
- 形成 R6B 主文档并同步状态。

当前结果：

- Owner 提供的 `docs/data/月度汇总表_20260701_20260703.xlsx` 位于仓库目录内，但未被 Git 跟踪。
- 本轮已补充 `.gitignore`：`docs/data/*.xlsx`、`docs/data/*.xls`、`docs/data/*.csv`，防止真实导出文件误提交。
- 该 Excel 被判定为混合表：包含姓名、工号、部门、应出勤、实际出勤、迟到、早退、旷工等汇总字段，也包含 2026-07-01 至 2026-07-03 每日时间列。
- 该 Excel 含真实人员身份列，不可直接作为 R6B `Employee Checkin` 导入源，不提交，不导入。
- R6B 使用脱敏 Demo 原始打卡流水在本地 `frontend` site 验证。
- 已创建 3 名虚构员工、1 个 R6B Shift Type、3 条 Shift Assignment、5 条 Employee Checkin。
- 已调用 HRMS 原生 `process_auto_attendance()`，生成 3 条 Attendance。
- `Employee Checkin -> Auto Attendance -> Attendance` 最小链路通过。
- 迟到 / 早退候选 Attendance 已生成，但 `late_entry` / `early_exit` 未置位；该限制留给 R6C 或后续配置复核。
- Codex 审查 PASS 后，本轮已完成 closeout，状态收口为 COMPLETED。

M1-R6B 未做：

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
- 未提交真实员工姓名、真实工号或未脱敏数据。

## 前端实施流程规范（M1-R6B 后补充）

在 M1-R6B closeout 后，Owner 确认新增前端实施流程规范，本轮执行记录：

- 已新增 `docs/frontend/FRONTEND_IMPLEMENTATION_GUIDE.md`：定义前端分层（Frappe Desk vs Vue/React 独立前端）、独立前端启动 Gate（原型先行 → Owner 审查 → 前端复刻 → 功能接入）、组件库选择原则、Agent Skill 使用要求。
- 已更新 `docs/AI_CONTEXT.md`：加入前端实施流程规范摘要和链接。
- 已更新 `docs/READING_GUIDE.md`：加入前端规范的读取条件和公共入口文件检查清单。
- 已更新入口文件 `README.md`、`CLAUDE.md`、`AGENTS.md`：补充独立前端开发规则摘要。
- 已更新 `docs/adr/0003-use-dual-layer-frontend.md`：补充前端实施流程规范引用。
- 本轮未启动实际前端开发、不引入 npm 包、不创建 Vue/React 工程、不修改业务代码、不改变 M1 当前范围。

## M0 后续路线记录
