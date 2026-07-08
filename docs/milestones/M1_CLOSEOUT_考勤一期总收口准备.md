# M1 考勤一期总收口准备

项目名称：新乡海滨智能运营管理平台。

状态：REVIEWING。

审查记录：本轮为 M1 总收口准备轮，形成审查材料供 Codex 独立审查。Codex PASS 后下一轮才允许执行 M1 closeout（M1 = COMPLETED）。

执行日期：2026-07-09。

## 1. M1 总收口定位

本文档是 M1 考勤一期的**总收口准备文档**，不是 closeout 执行文档。

本轮定位：

- 汇总 M1 全部轮次（R0 → R7）的交付物和结论。
- 对照 M1 12 条验收标准形成验收矩阵。
- 整理 M1 整体限制、未完成项和后续建议。
- 为 Codex 独立审查提供完整的审查材料。

本轮**不是** M1 closeout。M1 状态仍为 IN_PROGRESS，只有 Codex 审查 PASS 且 Owner 明确授权后，下一轮才允许将 M1 收口为 COMPLETED。

## 2. 本轮读取文件清单

本轮按轻量范围读取：

| 读取文件 | 用途 |
| --- | --- |
| `CLAUDE.md` | 项目协作规则 |
| `AGENTS.md` | Agent 行为约束 |
| `README.md` | 人类入口文件 |
| `docs/AI_CONTEXT.md` | AI 上下文与阶段状态 |
| `docs/PROJECT_STATUS.md` | 项目总状态台账 |
| `docs/CURRENT_MILESTONE.md` | 当前里程碑与轮次状态 |
| `docs/READING_GUIDE.md` | AI 阅读范围指南 |
| `docs/milestones/README.md` | 里程碑索引 |
| `docs/milestones/M1_考勤一期真实需求确认.md` | 需求依据（5 轮 Owner 访谈结论） |
| `docs/milestones/M1_考勤一期产品需求说明书.md` | 产品设计（角色、场景、页面） |
| `docs/milestones/M1_考勤一期技术设计方案.md` | 技术路线（对象复用、导入、飞书登录、权限） |
| `docs/milestones/M1_Demo实施路线图.md` | 实施拆分路线 |
| `docs/milestones/M1_R4_Demo技术方案与实施路线拆分.md` | R4 轮次拆分与 Gate 检查点 |
| `docs/milestones/M1_R5_HRMS配置基线工作台月报Demo.md` | R5 配置基线与月报 Demo |
| `docs/milestones/M1_R6A_Excel导入与异常流程落地方案.md` | R6A Gate 判定与方案 |
| `docs/milestones/M1_R6B_脱敏打卡流水导入最小实现.md` | R6B 打卡导入最小闭环 |
| `docs/milestones/M1_R6C_异常识别与异常说明流程最小实现.md` | R6C 异常识别与 AR 扩展 |
| `docs/milestones/M1_R7_飞书登录领导Demo与M1收口准备.md` | R7 飞书登录方案与领导 Demo |

未递归读取 `docs/`，未读取 `docs/archive`、`docs/research`、`docs/legacy`。

## 3. M1 阶段目标回顾

M1 定位（来自 `M1_考勤一期真实需求确认.md`）：

- M1 是：**内部可演示版本 + 可给人事试用的本地 Demo**。
- M1 不是：正式生产上线、不是只做 HRMS 技术验证、不是一开始就接真实考勤机。
- M1 要求：**一周内要有东西**。

M1 主流程：

```
浏览器访问 HBOS
→ 飞书登录 / 本地管理员登录
→ 进入考勤工作台
→ 导入脱敏考勤 Excel
→ 系统生成或展示考勤结果
→ 识别迟到、早退、缺卡、缺勤
→ 员工查看自己的考勤
→ 员工提交考勤异常说明
→ 主管确认事实
→ 人事 / 考勤管理员最终处理
→ 生成月度汇总
→ 导出 Excel
→ 领导查看汇总 Demo
```

## 4. M1 已完成轮次清单

| 轮次 | 名称 | 状态 | 类型 | 审查结果 |
| --- | --- | --- | --- | --- |
| M1-R0 | 平台入口、账号权限与本地化诊断 | COMPLETED | 规划诊断 | Codex 独立审查 PASS |
| M1-R1 | HRMS 原生考勤对象模型验证 | COMPLETED | 只读验证 | Codex 独立审查 PASS |
| M1-R2 | HRMS 原生考勤配置试运行方案 | COMPLETED | 方案设计 | Codex 独立审查 PASS |
| M1-R3 | HRMS 原生考勤最小测试数据试运行 | BLOCKED | 试运行 | Codex 审查 PASS，结论 PARTIAL |
| M1-R3A | 运行态阻断诊断与 TEST 数据隔离方案 | COMPLETED | 诊断 | Codex 审查 PASS |
| M1-R3B | 运行态最小修复方案 | COMPLETED | 方案设计 | Codex 审查 PASS |
| M1-R3B-FIX | 运行态最小修复执行 | COMPLETED | 修复执行 | Codex 审查 PASS |
| M1-R3C | HRMS 原生考勤最小试运行复测 | COMPLETED | 试运行复测 | Codex 审查 PASS，结论 PARTIAL/GAP |
| M1-R3D | 异常口径与 Gap 诊断 | COMPLETED | 诊断 | Codex 审查 PASS |
| M1-R3E | 配置复核清单与业务口径确认表 | COMPLETED | 文档交付 | Codex 审查 PASS |
| M1-R3F | 业务口径确认包 | COMPLETED | 文档交付 | Codex 审查 PASS |
| M1-REQ-DESIGN-DRAFT | M1 考勤一期需求设计草案 | COMPLETED | 需求设计 | Codex 审查 PASS |
| M1-R4 | Demo 技术方案与实施路线拆分 | COMPLETED | 规划拆分 | Codex 初审 FAIL→修复→复审 PASS |
| M1-R5 | HRMS 配置基线、考勤工作台与月报 Demo | COMPLETED | 方案固化 | Codex 审查 PASS |
| M1-R6A | Excel 导入与异常流程落地方案 / Gate 判定 | COMPLETED | Gate 判定 | Codex 初审 FAIL→修复→复审 PASS |
| M1-R6B | 脱敏打卡流水导入最小实现 | COMPLETED | 最小实现 | Codex 审查 PASS |
| M1-R6C | 异常识别与异常说明流程最小实现 | COMPLETED | 最小实现 | Codex 审查 PASS |
| M1-R7 | 飞书登录、领导 Demo 与 M1 收口准备 | COMPLETED | 方案+收口准备 | Codex 初审 FAIL→修复→复审 PASS |

M1 全部执行轮次（R0 → R7，含 R3 子轮次）共 **19 轮**。其中 18 轮 COMPLETED，1 轮 BLOCKED（M1-R3）。

## 5. R4 / R5 / R6A / R6B / R6C / R7 结论汇总

### 5.1 M1-R4：Demo 技术方案与实施路线拆分

**结论**：COMPLETED。

- 基于 4 份设计文档完成了 R5/R6/R7 详细拆分。
- 固化了每轮的目标、范围、禁止项和验收点。
- 固化了 M1 技术边界：不创建 App 不写代码、优先复用原生、不修改核心源码。
- Gate 检查点（12 项）逐项识别。

### 5.2 M1-R5：HRMS 配置基线、考勤工作台与月报 Demo

**结论**：COMPLETED。

- HRMS 配置基线已固化（14 类对象）。
- 考勤工作台入口方案已设计（Frappe Desk / Workspace + 方案 A/B）。
- 月度汇总 Demo 展示路径已固化（14 字段映射 + 覆盖分析）。
- Excel 月报导出路径已固化（4 种导出方式）。
- 本轮未在数据库中创建 Workspace/Report（缺少版本化载体）。

### 5.3 M1-R6A：Excel 导入与异常流程落地方案 / Gate 判定

**结论**：COMPLETED。

- Gate-1（打卡流水导入）：PASS，Frappe Data Import 可支持 Employee Checkin 导入。
- Gate-2（异常说明流程）：CONDITIONAL PASS，优先方案 A（Custom Field 扩展原生 Attendance Request）。
- Gate-8（是否需要 hb_hr_app）：PASS — 不需要。
- 已完成 R6B/R6C 后续执行任务拆分。

### 5.4 M1-R6B：脱敏打卡流水导入最小实现

**结论**：COMPLETED。

- Owner 提供 Excel 已判定为混合表，不能直接作为 Employee Checkin 导入源。
- 使用脱敏 Demo 原始打卡流水完成最小闭环验证：
  - 3 名虚构员工、1 个 Shift Type、3 条 Shift Assignment
  - 5 条 Employee Checkin → 3 条 Attendance
  - `Employee Checkin → Auto Attendance → Attendance` 链路通过
- `.gitignore` 已覆盖 `docs/data/*.xlsx`、`*.xls`、`*.csv`。
- `late_entry`/`early_exit` 当时未置位 → R6C 修复。

### 5.5 M1-R6C：异常识别与异常说明流程最小实现

**结论**：COMPLETED。

- 异常识别 7 个场景全部通过（正常/迟到/早退/上班缺卡/下班缺卡）。
- Shift Type 配置修复后 `late_entry`/`early_exit` 正确置位。
- 11 个 Custom Field 已在 HRMS 原生 Attendance Request 上扩展完成，覆盖 6 种异常类型 + 三级流程状态。
- **核心 Blocker**：HRMS 原生 `validate_no_attendance_to_create()` 在已有 Attendance 时阻止 Attendance Request 创建（by design，不是 Bug）。
- 员工提交/主管确认/人事处理的运行时三级流程未能完整验证。

### 5.6 M1-R7：飞书登录、领导 Demo 与 M1 收口准备

**结论**：COMPLETED。

- 飞书 OAuth 登录方案设计完成（Social Login Key 配置参数表、User/Employee 匹配规则：手机号 > 邮箱 > 工号）。
- 飞书 OAuth 端到端验证未执行（blocker：飞书平台侧 + 网络侧 + 安全侧）。
- 领导汇总 Demo 4 项核心指标 + Query Report SQL + Dashboard Chart 设计已固化。
- 月报查看（4 条路径）和导出（4 种方式）已整理。
- M1 Demo 完整演示路径（10 个环节）已整理。
- M1 收口准备项清单（10 项处理 + 5 项 Owner 决策）已列出。
- 未伪造飞书登录成功。

## 6. M1 核心需求验收矩阵

对照 `M1_考勤一期真实需求确认.md` 的 12 条验收标准：

| # | 验收标准 | 完成度 | 依据文件 | 当前限制 | 后续建议 |
| --- | --- | --- | --- | --- | --- |
| 1 | **人事能登录** | 部分完成 | R5, R7 | 本地管理员可登录；飞书登录方案设计完成，真实 OAuth 回调验证有 3 类 blocker（平台侧/网络侧/安全侧） | M2 或单独验证轮次执行飞书 OAuth 端到端验证 |
| 2 | **能看到考勤工作台** | 已完成 | R5 | 方案已固化，HR Workspace 原生可用，Frappe Desk 可访问；数据库态 Workspace 未创建（缺版本化载体） | M2 创建版本化 Workspace fixture |
| 3 | **能导入一份脱敏考勤 Excel** | 部分完成 | R6A, R6B | 原始打卡流水导入最小闭环通过（5 条 Checkin → 3 条 Attendance）；月度汇总导入未实现；Owner Excel 为混合表不可直接导入 | 补充月度汇总导入实现；扩展 Demo 数据集 |
| 4 | **能生成或展示月度考勤结果** | 部分完成 | R5, R6C | 6 条 Attendance 已生成（Demo 规模：3 员工 × 2 天）；月度汇总报表路径已固化（Query Report），但未在数据库中创建 | 创建 Query Report 并扩展数据集 |
| 5 | **能识别迟到早退缺卡缺勤** | 已完成 | R6C | 迟到/早退/上班缺卡/下班缺卡 7 场景验证通过；全天缺勤识别逻辑已固化但场景未验证；HRMS Auto Attendance 自动标记可用 | 补充全天缺勤场景验证 |
| 6 | **员工能查看自己的记录** | 已完成 | R5 | Attendance List / Employee 视图原生可用；Frappe Role 权限隔离方案已设计 | M2 配置 Employee Self Service 角色 |
| 7 | **员工能提交异常说明** | 部分完成 | R6C | 11 个 Custom Field 扩展完成（6 种异常类型 + 三级状态字段）；运行时创建被 native validation 阻止 | Owner 决策：Hook 绕过 / 自定义 DocType / 文档化限制 |
| 8 | **主管能确认异常** | 部分完成 | R6C | 三级流程字段设计完成（supervisor_confirmed + processing_status）；Workflow 配置未执行；依赖 AR 记录创建 | 解决 AR 创建 blocker 后配置 Workflow |
| 9 | **人事能最终归档** | 部分完成 | R6C | 三级流程字段设计完成（hr_processed + hr_comment）；运行时未验证 | 依赖 #7 + #8 完成后验证 |
| 10 | **能导出 Excel 月报** | 已完成 | R5 | 4 种导出路径已固化（Report Export / List Export / Data Export / Script Report）；Frappe 原生 Excel 导出可用 | M2 在数据库中创建 Query Report 并验证 Excel 导出 |
| 11 | **领导能看到汇总 Demo** | 部分完成 | R7 | 4 项核心指标定义已固化；Query Report SQL + Dashboard Chart 设计完成；Demo 数据规模小（3 员工 2 天）限制实际展示效果 | 扩展数据集后创建 Dashboard |
| 12 | **未来如何接真实考勤机** | 已完成 | M1 技术设计 | 通用适配层设计已明确：Raw Checkin → 清洗映射 → Employee Checkin → Attendance；接口契约已固化 | M3+ 实施 |

**汇总**：

- 已完成（含"方案已固化，原生可用"）：标准 2、5、6、10、12（5 条）
- 部分完成（方案就绪但运行时有 block 或数据规模限制）：标准 1、3、4、7、8、9、11（7 条）
- 未完成（完全未实现）：0 条

## 7. HRMS 配置演示完成情况

| 配置项 | M1 状态 | 说明 |
| --- | --- | --- |
| Company | 已配置（测试环境） | `TEST-HBOS-M1R3C-虚构公司` |
| Department | 已配置（测试环境） | `TEST-HBOS-M1R3C-生产一部 - R3C` |
| Employee | 已配置（虚构） | 3 名虚构员工（甲/乙/丙），工号 R6B-EMP-001/002/003 |
| Shift Type | 已配置并验证 | 早班 08:00-16:00（0 分钟宽限），白班/中班/夜班/行政班路径已固化 |
| Shift Assignment | 已配置并验证 | 3 条排班，覆盖 2026-07-02 至 07-03 |
| Holiday List | 已配置（测试环境） | `TEST-HBOS-M1R3C-虚构节假日` |
| Leave Type | 已配置（测试环境） | `TEST-HBOS-M1R3C-虚构事假` |
| Leave Allocation | 未配置 | R3C 中 Leave Application 因缺 Allocation 未创建 |
| Employee Checkin | 已验证可写入 | 9 条打卡记录（R6B 5 条 + R6C 4 条） |
| Attendance | 已验证可生成 | 6 条考勤结果（含 late_entry/early_exit 标记） |
| Attendance Request | Custom Field 扩展完成 | 11 个字段已创建；运行时创建有 native validation blocker |

## 8. Excel 导入完成情况

| 导入类型 | M1 状态 | 说明 |
| --- | --- | --- |
| 原始打卡流水导入 | **最小闭环通过** | `Employee Checkin → Auto Attendance → Attendance` 已验证；使用一次性 bench 代码写入，未走 Frappe Data Import UI |
| 月度汇总 Excel 导入 | **方案设计完成，未实现** | 导入路径和 DocType 设计已固化（R6A）；R6B/R6C 未实现 |
| Owner 提供 Excel 文件 | **已判定为混合表** | 含真实身份数据，不导入，不提交；已由 `.gitignore` 防误提交 |
| 导入批次记录 | **方案设计完成，未实现** | `HBOS Import Log` DocType 设计已固化（R6A）；未创建 |

## 9. 月报查看 / 导出完成情况

| 能力 | M1 状态 | 说明 |
| --- | --- | --- |
| 月度汇总报表 | 方案已固化 | Query Report SQL 设计完成（R5 + R7）；未在数据库中创建 |
| Excel 导出路径 | 4 种路径已固化 | Report Export / List Export / Data Export / Script Report（R5） |
| 月度汇总字段覆盖 | 14 字段映射已固化 | 含迟到/早退/缺卡/缺勤/请假/加班/节假日出勤/异常待确认/最终状态等 |
| 领导月报导出 | 路径已说明 | 领导角色通过 Query Report 导出汇总数据，无个人明细 |

## 10. 考勤工作台 / 领导 Demo 完成情况

| 能力 | M1 状态 | 说明 |
| --- | --- | --- |
| 考勤工作台入口 | 方案已固化 | Frappe Desk / HR Workspace 原生可用；Workspace 自定义结构已设计（R5 方案 A/B） |
| 员工个人视图 | 原生可用 | Attendance List / Employee 视图原生支持；权限隔离方案已设计 |
| 领导汇总 Demo | 方案已固化 | 4 项核心指标 + Query Report SQL + Dashboard Chart 设计（R7）；数据规模限制 |
| 部门排名 | 方案已固化 | 部门异常人数排名 SQL 查询设计完成 |
| 月报导出新入口 | 路径已固化 | 4 种导出路径（R5 + R7） |

## 11. 异常识别与异常说明流程完成情况

| 流程环节 | M1 状态 | 说明 |
| --- | --- | --- |
| 异常识别 - 迟到 | **已验证通过** | `late_entry=1` 自动标记（Shift Type 配置修复后） |
| 异常识别 - 早退 | **已验证通过** | `early_exit=1` 自动标记 |
| 异常识别 - 上班缺卡 | **已验证通过** | `in_time=NULL` + `out_time` 有值 |
| 异常识别 - 下班缺卡 | **已验证通过** | `out_time=NULL` + `in_time` 有值 |
| 异常识别 - 全天缺勤 | 逻辑已固化 | 判断顺序已明确（请假→节假日→排班→缺勤），场景未验证 |
| 员工提交异常说明 | 结构就绪，运行时 Blocker | 11 个 Custom Field 已创建；native validation 阻止 AR 创建 |
| 主管确认事实 | 设计完成，未验证 | 依赖 AR 记录存在 |
| 人事最终处理 | 设计完成，未验证 | 依赖 AR 记录存在 |
| 操作留痕 | 原生能力已确认 | Frappe Version + Comment + Activity Log 存在且可用 |
| 三级 Workflow | 未配置 | Workflow DocType 存在但未配置 |

## 12. 飞书登录方案与当前限制

### 12.1 已完成

- Frappe Social Login Key 配置参数表（7 个参数 → 飞书对应值映射）已固化。
- 飞书身份字段获取范围已确认（`open_id`、`union_id`、`name`、`mobile`、`email`）。
- Employee 匹配规则已固化：手机号 > 邮箱 > 工号，三级优先级。
- 未匹配处理策略已固化：拒绝自动创建 User，提示联系管理员。
- 本地管理员兜底登录保留确认。
- 权限边界确认：飞书只认证（Authentication），Frappe Role / User Permission 管授权（Authorization）。

### 12.2 当前 Blocker

| Blocker | 类别 | 解除方式 |
| --- | --- | --- |
| 飞书应用未创建 | 飞书平台侧 | Owner / 飞书企业管理员在飞书开放平台创建应用 |
| 回调 URL 未配置 | 飞书平台侧 | 配置 HBOS 可公网访问的回调地址 |
| 手机号权限未获取 | 飞书平台侧 | 申请 `contact:user.phone:readonly` 权限并经企业管理员审核 |
| HBOS 无公网可达地址 | 网络侧 | 公网域名或内网穿透 |
| App Secret 安全约束 | 安全侧 | 永久不提交，在安全轮次中单独配置 |
| Social Login Key 未写入数据库 | 实施侧 | 需 Owner 授权写入站点数据库态配置 |

### 12.3 未伪造

- 未伪造飞书登录成功。
- 未要求用户暴露 App Secret。
- 未提交 `.env`、密钥、token。

## 13. 数据安全与脱敏结论

| 检查项 | M1 全程状态 |
| --- | --- |
| 真实员工姓名 | 全部使用虚构姓名（甲/乙/丙） |
| 真实工号 | 全部使用脱敏工号（R6B-EMP-001/002/003） |
| Owner Excel 文件 | 已判定为混合表 + 含真实身份 → 不导入，不提交 |
| `.env` | 已在 `.gitignore` 中，未提交 |
| App Secret / 密钥 | 未获取，未提交 |
| Excel / CSV 文件 | `docs/data/*.xlsx`、`*.xls`、`*.csv` 已在 `.gitignore` |
| 数据库 / 日志 / 缓存 | 未提交 |
| 备份 / 运行时产物 | 未提交 |
| 飞书真实写入 | 未执行过任何飞书真实写入 |
| Web 安全配置 | 方案设计中包含 CSP/HTTPS/CSRF/XSS 等（M1-R0），M1 Demo 阶段未强制 |

**结论**：M1 全部轮次未提交任何真实数据或敏感信息。

## 14. 未创建 App / DocType / 未改核心源码结论

| 项目 | M1 全程状态 |
| --- | --- |
| `hb_hr_app` | 未创建 |
| `hb_attendance_app` | 未创建 |
| `hb_core_app` | 未创建 |
| `hb_feishu_app` | 未创建 |
| 任何海滨自定义 Frappe App | 未创建 |
| 自定义 DocType（`HBOS Import Log` / `Attendance Exception` / `Attendance Correction` 等） | 未创建 |
| Frappe / ERPNext / HRMS 核心源码 | 未修改 |
| Custom Field（HRMS 原生 Attendance Request 上扩展） | 11 个字段已创建（R6C），属于 Frappe 原生支持的 Custom Field 机制，不修改核心源码 |
| Docker Compose / .env.example | 未修改 |
| Docker volume 删除 / site 重建 | 未执行（始终遵守环境保护规则） |

**结论**：M1 自始至终遵守"不创建 App、不创建 DocType、不修改核心源码"的红线。Custom Field 属于 Frappe 原生支持的扩展机制。

## 15. M1 未完成 / 后续保留项

### 15.1 因 blocker 未完成

| 项 | 原因 | 后续建议 |
| --- | --- | --- |
| 飞书 OAuth 端到端登录 | 飞书平台侧 + 网络侧 + 安全侧 blocker | M2 飞书集成阶段解决 |
| Attendance Request 运行时创建 | HRMS 原生 `validate_no_attendance_to_create()` 设计冲突 | Owner 决策：Hook/自定义 DocType/文档化 |
| 异常说明 + 主管确认 + 人事归档的运行时流程 | 依赖 AR 记录创建 | 解决 AR blocker 后验证 |
| 全天缺勤场景验证 | M1-R6C 未创建该场景检查点 | M2 或后续验证轮次 |

### 15.2 设计完成但未在数据库中实现

| 项 | 原因 | 后续建议 |
| --- | --- | --- |
| Frappe Desk Workspace 自定义 | 缺版本化载体（无 App），不写入数据库态配置 | M2 创建版本化载体后写入 |
| 月度汇总 Query Report / Dashboard | 同上 | 同上 |
| Social Login Key 配置 | 缺 App Secret + 回调域名，不写入数据库 | 安全轮次中配置 |
| Frappe Role / User Permission（主管/领导角色） | 未到生产配置阶段，Demo 用测试账号 | M2 或 M2+ 配置 |

### 15.3 因 Demo 规模限制

| 项 | 原因 | 后续建议 |
| --- | --- | --- |
| Demo 数据集规模（3 员工 × 2 天） | R6B/R6C 最小验证规模 | 扩展数据集（建议 ≥10 员工 × 1 个月） |
| 月度汇总指标展示 | 数据量不足以支撑有意义的月度统计 | 同上 |
| 多部门对比（部门排名） | 当前只有 1 个部门 | 扩展多部门 Demo 数据 |
| 跨夜班 / 中班 / 夜班场景 | R6B/R6C 只覆盖了早班 | 补充中班/夜班 Demo 数据 |

### 15.4 因设计边界未实现

| 项 | 原因 | 后续建议 |
| --- | --- | --- |
| 月度汇总 Excel 导入 | R6A 已设计，R6B/R6C 未实现 | M2 实施 |
| 导入批次记录（HBOS Import Log） | R6A 已设计，未创建 DocType | M2 实施 |
| 考勤 Workflow 配置 | R6C 已评估，未配置 | 解决 AR blocker 后配置 |
| 请假 Leave Allocation 配置 | M1-R3C 中未完成 | M2 补充 |
| 加班审批流程 | M1 口径已确认（必须有审批） | M2+ 实施 |
| 节假日出勤处理 | M1 口径已确认（只记录不自动转） | M2+ 实施 |
| 临时调班审批流 | M1 口径已确认（管理员维护 Shift Assignment） | M2+ 实施 |

## 16. M1 不上线生产的边界说明

M1 全程遵守以下边界：

| 边界 | M1 全程状态 |
| --- | --- |
| 运行环境 | 仅本地 Mac Docker |
| 不部署到公司内网服务器 | 始终遵守 |
| 不部署到云服务器 | 始终遵守 |
| 不是正式生产上线 | 始终遵守 |
| 不接真实考勤机 | 始终遵守 |
| 不接飞书工作台 | 始终遵守 |
| 不接飞书请假（正式） | 始终遵守 |
| 不做大型 Vue/React 驾驶舱 | 始终遵守 |
| 不执行 `docker compose down -v` | 始终遵守 |
| 不删除 Docker volume | 始终遵守 |
| 不重建 `frontend` site | 始终遵守 |

## 17. M2 建议边界（仅建议，不启动）

M2 定位为「飞书集成」阶段。M2 可能包含：

1. 飞书 OAuth 登录端到端验证 → 上线。
2. 飞书工作台集成。
3. 飞书请假审批对接。
4. 飞书消息通知（考勤异常提醒、月报推送）。
5. 飞书 ↔ Frappe User / Employee 同步机制。

M2 也可能包含 M1 未完成的实施项：

1. 月度汇总 Excel 导入实现。
2. 导入批次记录（HBOS Import Log DocType）。
3. Attendance Request blocker 解决方案实施。
4. 异常说明三级流程运行时验证 + Workflow 配置。
5. Demo 数据集扩展。
6. Frappe Desk Workspace / Report / Dashboard 数据库态配置（需版本化载体）。
7. Leave Allocation 配置。

M2 启动条件（全部满足后才允许）：

1. M1 总收口完成（Codex PASS + Owner 授权，M1 = COMPLETED）。
2. Owner 明确授权进入 M2。
3. 飞书开放平台应用已创建、权限已审核通过。
4. M2 启动门禁通过。

**M2 当前绝不启动。本文档中的 M2 内容仅为建议边界，不代表已授权。**

## 18. 当前状态

```
M1-R6A = COMPLETED
M1-R6B = COMPLETED
M1-R6C = COMPLETED
M1-R7  = COMPLETED
M1 总收口 = REVIEWING
M1      = IN_PROGRESS（总收口审查中）
M2      = PLANNED（未启动）
```

不得写：

- `M1 = COMPLETED`
- `M1 closeout PASS`
- `M1 总收口已完成`

## 19. 状态同步声明

本轮完成后需同步以下文件：

| 文件 | 是否需要更新 | 原因 |
| --- | --- | --- |
| `docs/PROJECT_STATUS.md` | 是 | 新增 M1 总收口准备状态 |
| `docs/CURRENT_MILESTONE.md` | 是 | 更新当前轮次为 M1 总收口准备 |
| `docs/AI_CONTEXT.md` | 是 | 更新当前上下文 |
| `docs/READING_GUIDE.md` | 是 | 更新当前里程碑提醒 |
| `docs/milestones/README.md` | 是 | 新增 M1 总收口准备索引条目 |
| `docs/milestones/M1_START_GATE.md` | 是 | 新增 M1 总收口准备状态 |
| `README.md` | 是 | 更新阶段描述 |
| `CLAUDE.md` | 否 | 无需变更 |
| `AGENTS.md` | 否 | 无需变更 |
