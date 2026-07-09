# M1-FIX 功能补漏实施方案

项目名称：新乡海滨智能运营管理平台。

状态：REVIEWING。

执行日期：2026-07-09。

## 文档定位

本文档是 M1-FIX-A 阶段的差距盘点与补漏实施方案。M1 closeout 已通过 Codex 审查并收口为 COMPLETED，但 Owner 亲自验收后发现大量产品功能没有真正页面可体验——「方案完成」不等于「功能完成」。

本轮只做差距盘点与实施方案，不开发、不创建 App、不创建 DocType、不导入数据、不配置真实飞书密钥。

### 数据口径重要更新（2026-07-09 Owner 追加授权）

Owner 明确授权：M1-FIX 后续本地演示与导入验证可使用真实员工姓名和真实考勤数据。数据源文件为 `docs/data/月度汇总表_20260701_20260703.xlsx`。后续不再强制使用「海滨员工甲01」等虚构姓名作为本地演示姓名。

采用**「双轨数据策略」**：

#### A 轨：Owner 本地验收数据

用于本地演示和真实效果验证。

- 来源：`docs/data/月度汇总表_20260701_20260703.xlsx`
- 可使用真实员工姓名、工号、部门、考勤数据
- 用于本地导入、员工匹配、月报展示、Owner 验收
- **不提交 Git**
- 不在 Markdown 文档正文中展开真实姓名明细

#### B 轨：仓库可提交样例数据

如后续需要模板、示例或自动化测试数据，必须另行准备脱敏样例。

- 不含真实员工姓名
- 不含真实手机号、邮箱、工号等个人信息
- 可使用虚构姓名
- 可提交 Git

#### 安全边界（必须遵守）

1. 不把真实 Excel / CSV 提交到 Git
2. 不把真实员工姓名批量写入 Markdown 文档正文
3. 不把真实员工数据做成仓库内 fixture / seed / json / csv / xlsx
4. 不在最终报告中打印真实员工姓名清单
5. 不提交由真实员工数据导出的文件
6. 不提交数据库、日志、缓存、导入产物
7. 不提交 `.env`、token、密钥、真实配置
8. Git 提交中只允许提交方案文档与状态文档

---

## 1. Git Gate 结果

| 检查项 | 结果 |
| --- | --- |
| 当前分支 | `main` ✅ |
| HEAD | `64e883973f92c12036d734bf850ad40c71b205fe` ✅ |
| `main` 与 `origin/main` 一致 | 是 ✅ |
| `git status` clean | 是（无未提交变更）✅ |
| 本轮开始前是否存在未提交变更 | 否 ✅ |

**结论**：Git Gate 全部通过，工作区干净，可以安全开始 M1-FIX-A。

---

## 2. 本轮读取文件清单

| 读取文件 | 用途 |
| --- | --- |
| `CLAUDE.md` | 项目协作规则与执行原则 |
| `AGENTS.md` | Agent 行为约束与禁止事项 |
| `docs/AI_CONTEXT.md` | AI 上下文与阶段状态 |
| `docs/PROJECT_STATUS.md` | 项目总状态台账 |
| `docs/CURRENT_MILESTONE.md` | 当前里程碑与轮次状态 |
| `docs/READING_GUIDE.md` | AI 阅读范围指南与条件读取规则 |
| `docs/milestones/M1_考勤一期真实需求确认.md` | M1 12 条验收标准与需求依据 |
| `docs/milestones/M1_考勤一期产品需求说明书.md` | 产品设计（角色、场景、页面入口、导出等） |
| `docs/milestones/M1_考勤一期技术设计方案.md` | 技术路线（Excel 导入设计、异常 DocType 设计等） |
| `docs/milestones/M1_Demo实施路线图.md` | R4-R7 拆分边界与禁止项 |
| `docs/milestones/M1_CLOSEOUT_考勤一期总收口准备.md` | M1 总收口完整材料（验收矩阵、限制清单） |
| `docs/milestones/M1_R7_飞书登录领导Demo与M1收口准备.md` | R7 飞书登录方案与领导 Demo |
| `docs/milestones/M1_R6B_脱敏打卡流水导入最小实现.md` | R6B 导入最小验证结果（3 员工 × 2 天） |
| `docs/milestones/M1_R6C_异常识别与异常说明流程最小实现.md` | R6C 异常识别（7 场景）与 AR 扩展（11 Custom Field） |
| `docs/milestones/M1_START_GATE.md` | M1 阶段门禁文档，确认当前状态 |
| `README.md` | 人类入口文件，检查过期描述 |

未递归读取 `docs/`，未读取 `docs/archive`、`docs/research`、`docs/legacy`。

---

## 3. 当前系统可体验能力摘要

以下基于 M1 closeout 材料汇总，真实反映当前 `frontend` site 中**实际可操作/可看到**的内容：

| 能力领域 | 当前实际体验状态 | 数据规模 |
| --- | --- | --- |
| Frappe Desk 登录 | 管理员可通过 `http://localhost:8081/login` 登录 | 仅 Administrator |
| HR Workspace 入口 | HRMS 原生 Workspace 可访问（`/app/hr`） | 原生入口，未自定义 |
| 员工管理 | Employee List 可查看已创建的员工 | 当前 3 名虚构员工（R6B），后续将导入 Owner Excel 中的真实员工数据 |
| 班次配置 | Shift Type 4 个已配置（含 R6B 早班） | 4 个 Shift Type |
| 排班管理 | Shift Assignment 可查看 | 3 条排班（2 天） |
| 打卡记录 | Employee Checkin 可查看 | 9 条（July 2: 5 条 + July 3: 4 条） |
| 考勤结果 | Attendance List 可查看 | 6 条（含 late_entry/early_exit 标记） |
| 异常识别 | late_entry/early_exit 自动标记已就绪 | 7 场景验证通过 |
| 异常说明结构 | Attendance Request 已扩展 11 个 Custom Field | **运行时创建被 native validation 阻止** |
| 月度汇总报表 | Query Report SQL 已设计（文档中） | **未在数据库中创建** |
| Excel 导出 | Frappe 原生导出可用（List/Report/Data Export） | 未创建专用 Query Report |
| 考勤工作台 | 入口方案已设计（方案 A/B） | **未在数据库中创建 Workspace** |
| 领导汇总 Demo | 4 项指标 + SQL + Chart 已设计 | **未在数据库中创建 Dashboard** |
| 飞书登录 | Social Login Key 配置参数表已固化 | **端到端验证未执行（6 类 blocker）** |
| 多角色账号 | 仅 Administrator | 无员工/主管/人事/领导账号 |
| 本地数据源 | Owner 已提供 `docs/data/月度汇总表_20260701_20260703.xlsx`（含真实员工姓名与考勤数据） | 可用于本地验证，**不提交 Git** |

**核心问题**：M1 closeout 确认了 **12 条验收标准中 7 条部分完成**，但这 7 条的「部分」主要是「方案已设计但数据库中没有对应页面/报表/入口」。Owner 在浏览器里能看到的只有 HRMS 原生列表页面 + 3 名虚构员工的 2 天数据。Owner 已提供真实 Excel 数据源，后续 M1-FIX-B 将基于该数据源在本地环境中导入验证。

---

## 4. 核心差距摘要

### 4.1 总体判断

M1 closeout 本质是「方案收口」完成，不是「功能收口」完成。关键差距集中在三块：

1. **Excel 导入闭环缺失**：没有可上传的 Demo Excel/CSV，没有员工匹配规则的前端实现，没有导入结果反馈，没有导入批次记录。
2. **页面/入口缺失**：考勤工作台、月度汇总报表、领导汇总 Demo 均只有文档设计，数据库中没有对应 Workspace/Report/Dashboard。
3. **流程运行时阻断**：Attendance Request 创建被 HRMS 原生 `validate_no_attendance_to_create()` 阻止，异常说明三级流程无法在浏览器中走通。

### 4.2 数据规模差距

| 维度 | M1 closeout 实际值 | M1-FIX 目标值 | 差距 |
| --- | --- | --- | --- |
| 员工数量 | 3 人（虚构） | Owner Excel 中的真实员工人数（本地验收用，不提交 Git） | 待导入 Owner Excel |
| 部门数量 | 1 个 | Owner Excel 中的部门数 | 待导入 Owner Excel |
| 天数覆盖 | 2 天（July 2-3） | Owner Excel 覆盖天数（至少 3 天：07-01 ~ 07-03） | 待扩展 |
| 班次覆盖 | 仅早班 | 白班 + 中班 + 夜班 + 行政班 | 缺 3 种班次 |
| 角色账号 | 1 个（Administrator） | 4 类（人事/员工/主管/领导）+ Administrator 兜底 | 缺 4 类体验账号 |
| 可导入 Excel | 无标准模板 | Owner Excel（本地验收）+ 标准模板（可提交） | 缺导入流程和结果反馈页面 |

数据策略（Owner 已授权）：
- **A 轨（本地验收）**：使用 `docs/data/月度汇总表_20260701_20260703.xlsx` 中的真实员工姓名和数据，不提交 Git。
- **B 轨（仓库模板）**：如需可提交的模板，另行准备脱敏样例数据。

---

## 5. M1-FIX 差距矩阵（20 项）

### 5.1 原始打卡流水 Excel / CSV 导入

| 属性 | 内容 |
| --- | --- |
| 编号 | GAP-01 |
| 需求来源 | M1 真实需求确认 §数据来源与导入；M1 验收标准 #3 |
| M1 承诺 | 能导入一份脱敏考勤 Excel（原始打卡流水） |
| 当前实际可体验状态 | R6B 通过一次性 bench console 代码写入了 5 条 Employee Checkin，验证了 `Employee Checkin → Auto Attendance → Attendance` 链路。但**没有可上传的 Demo Excel 文件、没有 UI 导入入口、没有字段映射预览、没有导入结果反馈页面**。Owner 无法在浏览器中完成「选择文件→上传→预览→导入→看结果」的体验。 |
| 差距判断 | **功能缺口**：方案验证完成，产品体验未完成 |
| 优先级 | P0 |
| 推荐实现方式 | 1. 创建标准 Demo 原始打卡流水 Excel/CSV 模板（中文表头）；2. 优先使用 Frappe Data Import UI（`/app/data-import`）导入 Employee Checkin；3. 如需更好的错误反馈和批次记录，再创建自定义导入入口 |
| 是否需要自定义 App | 否 |
| 是否需要自定义 DocType | 可选：如需导入批次记录，需 `HBOS 导入批次日志`（详见 §6） |
| 风险 | Frappe Data Import 的错误信息对普通用户不够友好；大文件导入可能超时 |
| 验收方式 | 人事角色登录后 → 进入导入页面 → 上传 Excel（优先支持读取 Owner 指定的本地 Excel `docs/data/月度汇总表_20260701_20260703.xlsx`）→ 系统反馈成功/失败行数 → 在 Employee Checkin 列表中可查看导入的打卡记录 → 页面直观展示员工姓名（真实）、工号、部门、考勤结果、异常结果。未匹配员工必须显示行号、姓名、工号、失败原因、处理建议。 |

### 5.2 月度汇总 Excel / CSV 导入

| 属性 | 内容 |
| --- | --- |
| 编号 | GAP-02 |
| 需求来源 | M1 真实需求确认 §两类导入必须区分；M1 技术设计 §月度汇总导入 |
| M1 承诺 | 月度汇总 Excel 导入（区别于原始打卡流水） |
| 当前实际可体验状态 | **完全未实现**。R6A 设计了路径，R6B/R6C 均未实现。Owner 无法上传月度汇总 Excel 并在页面中看到对账结果。 |
| 差距判断 | **功能缺口**：方案已设计，零实现 |
| 优先级 | P1（P0 完成原始打卡流水导入后再做） |
| 推荐实现方式 | 1. 创建 `HBOS 月度考勤汇总` DocType（含 14 字段）；2. 通过 Frappe Data Import 导入；3. 用 Query Report 展示汇总结果 |
| 是否需要自定义 App | 否（可挂在现有 App 下） |
| 是否需要自定义 DocType | 是：`HBOS 月度考勤汇总` |
| 风险 | 字段映射复杂（Owner Excel 为混合表，需先转换为标准模板再导入） |
| 验收方式 | 人事上传月度汇总 Excel → 系统展示汇总表 → 可与系统生成的 Attendance 对比对账 |

### 5.3 Demo 员工 / Demo 账号 / Demo 数据包

| 属性 | 内容 |
| --- | --- |
| 编号 | GAP-03 |
| 需求来源 | Owner 追加要求 §2 Demo 数据包；M1 真实需求确认 §数据策略 |
| M1 承诺 | 至少要有固定 Demo 数据集 + 可复现导入步骤 |
| 当前实际可体验状态 | 仅 3 名虚构员工（R6B-EMP-001/002/003），1 个部门，2 天数据。**Owner 已提供 `docs/data/月度汇总表_20260701_20260703.xlsx`（含真实员工姓名、工号、部门、考勤数据），但尚未在本地 Frappe 中导入和验证**。无 4 类角色体验账号，无完整的 Demo 月考勤表模板。 |
| 差距判断 | **数据缺口 + 流程缺口**：本地可使用真实 Excel 数据（A 轨），但缺少受控导入流程和本地验收脚本 |
| 优先级 | P0 |
| 推荐实现方式 | 1. 基于 Owner 提供的 `月度汇总表_20260701_20260703.xlsx` 在本地创建 Employee 记录（使用真实姓名/工号/部门，不提交 Git）；2. 创建 4 类角色体验账号（hr.demo/employee.demo/manager.demo/leader.demo@hbos.local）；3. 从 Owner Excel 提取原始打卡流水结构用于 Employee Checkin 导入；4. 另准备 B 轨脱敏模板（虚构姓名）用于仓库可提交样例 |
| 是否需要自定义 App | 否 |
| 是否需要自定义 DocType | 否 |
| 风险 | 真实数据不得进入 Git 提交；A 轨与 B 轨的数据切换需清晰文档化；Owner Excel 为月度汇总混合表，需拆分为原始打卡流水格式才能驱动 Employee Checkin → Attendance 闭环 |
| 验收方式 | Owner Excel 数据在本地成功导入 → 页面直观可见真实姓名、工号、部门、考勤结果 → 数据文件未被 Git 跟踪 |

### 5.4 员工匹配规则与失败反馈

| 属性 | 内容 |
| --- | --- |
| 编号 | GAP-04 |
| 需求来源 | Owner 追加要求 §3 员工匹配规则；M1 技术设计 §导入方式 |
| M1 承诺 | 工号 > 手机号 > 邮箱 > 姓名（仅 Demo 且唯一）四级匹配 |
| 当前实际可体验状态 | R6B 导入时使用硬编码的 `employee` 字段值直接写入，没有经过匹配规则校验、没有失败行反馈。Frappe Data Import 原生支持按字段匹配（如 `employee_number`），但**未配置、未验证、无错误反馈 UI**。 |
| 差距判断 | **功能缺口**：匹配规则已设计，未在产品中落地。真实姓名可以用于本地辅助展示，但正式匹配仍不得只依赖姓名。 |
| 优先级 | P0 |
| 推荐实现方式 | 1. Frappe Data Import 模板中指定匹配字段为 `employee_number`（优先级 1）；2. 如 Data Import 匹配失败，错误行会在导入结果中展示；3. 如需更友好的中文错误提示（展示未匹配行号、姓名、工号、失败原因、建议处理方式），需创建自定义导入入口 |
| 是否需要自定义 App | 否（Frappe Data Import 原生支持，仅需配置模板） |
| 是否需要自定义 DocType | 可选：如需友好的中文错误反馈，需 `HBOS 导入批次日志` |
| 风险 | Frappe Data Import 的错误提示为英文，需要配置中文翻译或自定义错误展示 |
| 验收方式 | 故意导入一条未匹配员工的打卡记录 → 导入结果明确展示该行失败 → 显示失败原因（如「未找到工号为 XXX 的员工」）→ 不被静默丢弃 |

### 5.5 Employee Checkin 写入

| 属性 | 内容 |
| --- | --- |
| 编号 | GAP-05 |
| 需求来源 | M1 技术设计 §Excel 导入设计 |
| M1 承诺 | 原始打卡流水导入 → Employee Checkin |
| 当前实际可体验状态 | R6B 已通过 bench console 验证 Employee Checkin 可写入（5 条 + 4 条）。但**不是通过 UI 导入，不是通过 Excel/CSV 上传**。 |
| 差距判断 | **体验缺口**：能力已验证，但入口和流程未产品化 |
| 优先级 | P0（与 GAP-01 合并推进） |
| 推荐实现方式 | 通过 Frappe Data Import UI 导入 Employee Checkin，配置字段映射模板 |
| 是否需要自定义 App | 否 |
| 是否需要自定义 DocType | 否 |
| 风险 | 批量导入大量打卡记录时 Auto Attendance 触发时机需关注 |
| 验收方式 | 通过 Data Import 上传 Demo Excel → Employee Checkin 列表中出现对应打卡记录 |

### 5.6 Auto Attendance / Attendance 生成

| 属性 | 内容 |
| --- | --- |
| 编号 | GAP-06 |
| 需求来源 | M1 技术设计 §HRMS 原生对象复用 |
| M1 承诺 | Employee Checkin → Auto Attendance → Attendance（含 late_entry/early_exit） |
| 当前实际可体验状态 | R6B/R6C 已验证 Attendance 可由 Auto Attendance 生成，`late_entry`/`early_exit` 在 Shift Type 配置修复后正确置位。但**只有 6 条 Attendance（3 员工 × 2 天），缺少中班/夜班/跨夜班的 Attendance 验证**。 |
| 差距判断 | **规模缺口**：能力已验证通过，但覆盖场景不足以支撑 Demo 演示 |
| 优先级 | P1（与 GAP-03 Demo 数据包合并推进） |
| 推荐实现方式 | 扩展 Demo 数据包覆盖面（中班/夜班/行政班/跨夜班）→ Employee Checkin 写入 → 执行 `process_auto_attendance()` → 验证 Attendance 生成正确 |
| 是否需要自定义 App | 否 |
| 是否需要自定义 DocType | 否 |
| 风险 | 跨夜班 Attendance 日期归属可能与人工理解不一致 |
| 验收方式 | 4 种班次的 Attendance 均正确生成，late_entry/early_exit 按预期置位 |

### 5.7 迟到 / 早退 / 缺卡 / 缺勤识别

| 属性 | 内容 |
| --- | --- |
| 编号 | GAP-07 |
| 需求来源 | M1 真实需求确认 §考勤规则；M1 验收标准 #5 |
| M1 承诺 | 能识别迟到、早退、缺卡、缺勤 |
| 当前实际可体验状态 | R6C 已验证 7 个场景（正常/迟到/早退/上班缺卡/下班缺卡），`late_entry`/`early_exit` 正确置位。但**缺勤（全天无打卡）场景未验证**；缺卡识别逻辑只在文档中固化，产品中没有专门的「异常清单」页面。 |
| 差距判断 | **部分缺口**：迟到/早退识别已验证，缺勤场景未验证，缺卡无独立展示页面 |
| 优先级 | P1 |
| 推荐实现方式 | 1. 补充全天缺勤 Demo 数据并验证；2. 创建 Query Report「考勤异常清单」展示所有异常（迟到/早退/缺卡/缺勤），支持按部门/日期筛选 |
| 是否需要自定义 App | 否 |
| 是否需要自定义 DocType | 否（Query Report 即可） |
| 风险 | 全天缺勤的判断依赖请假/节假日/排班数据完整性 |
| 验收方式 | 在「考勤异常清单」页面中可看到所有异常类型的人员列表和详情 |

### 5.8 海滨考勤工作台

| 属性 | 内容 |
| --- | --- |
| 编号 | GAP-08 |
| 需求来源 | M1 产品需求说明书 §页面/入口设计；M1 验收标准 #2 |
| M1 承诺 | 能看到考勤工作台（各角色登录后的主入口） |
| 当前实际可体验状态 | R5 已设计方案 A（Frappe Desk Workspace 自定义入口）和方案 B（Dashboard 卡片聚合）。但**数据库中未创建 Workspace**。当前 HRMS 原生 Workspace（`/app/hr`）仅展示原生模块入口（HR Setup / Leaves / Shift & Attendance / Recruitment 等），没有海滨自己的考勤工作台入口。Owner 在浏览器中只能看到 HRMS 原生页面。 |
| 差距判断 | **功能缺口**：方案已设计，零实现 |
| 优先级 | P0 |
| 推荐实现方式 | 1. 创建海滨考勤工作台（Frappe Desk Workspace），中文名「海滨考勤」；2. 包含快捷入口卡片：打卡数据导入、考勤异常清单、月度汇总报表、员工考勤查询；3. 按角色展示不同的快捷操作（人事看到全部、主管看到本部门、员工看到个人）；4. 所有页面名称、菜单、标签使用中文 |
| 是否需要自定义 App | **是**：需创建 `hb_attendance_app` 或轻量承载 App 来版本化管理 Workspace fixture |
| 是否需要自定义 DocType | 否（Workspace 是 Frappe Desk 配置，不依赖自定义 DocType） |
| 风险 | 缺少版本化载体（App）时，Workspace 只能写入数据库而不能通过 fixture 版本化管理；建议创建轻量 App 承载 |
| 验收方式 | 登录后在 Desk 左侧看到「海滨考勤」Workspace → 点击后展示考勤相关快捷入口卡片 |

### 5.9 员工个人考勤视图

| 属性 | 内容 |
| --- | --- |
| 编号 | GAP-09 |
| 需求来源 | M1 产品需求说明书 §员工个人考勤视图；M1 验收标准 #6 |
| M1 承诺 | 员工能查看自己的考勤记录（今日状态、本月记录、异常清单、请假/加班记录） |
| 当前实际可体验状态 | HRMS 原生 Attendance List 支持按 Employee 筛选，Frappe 原生支持 Employee Self Service 角色。但**当前无独立的「员工个人考勤视图」页面**，无「今日考勤状态卡片」，无「本月异常清单」聚合。3 名虚构员工没有对应的 User 账号，无法以员工身份登录体验。 |
| 差距判断 | **体验缺口**：原生列表可用但没有产品化的个人视图；没有员工体验账号 |
| 优先级 | P1 |
| 推荐实现方式 | 1. 创建员工体验账号；2. 配置 Employee Self Service 角色与权限；3. 创建 Query Report「我的考勤」展示当月记录和异常；4. 可选：Dashboard 卡片展示「今日考勤状态」（上班/下班打卡时间、是否异常） |
| 是否需要自定义 App | 否 |
| 是否需要自定义 DocType | 否 |
| 风险 | 需仔细配置 User Permission 确保员工只能看自己的数据 |
| 验收方式 | 以员工账号「employee.demo@hbos.local」登录 → 在「我的考勤」页面看到本人当月记录和异常标记 |

### 5.10 主管本部门异常视图

| 属性 | 内容 |
| --- | --- |
| 编号 | GAP-10 |
| 需求来源 | M1 产品需求说明书 §主管本部门异常视图；M1 验收标准 #8 |
| M1 承诺 | 主管能查看本部门异常员工列表和详情 |
| 当前实际可体验状态 | 仅设计完成。**数据库中没有按部门筛选的异常视图页面，没有「确认事实」/「驳回」按钮**。Attendance Request 创建被 native validation 阻止，导致主管确认流程无法走通。 |
| 差距判断 | **功能缺口**：页面和流程均未实现 |
| 优先级 | P1 |
| 推荐实现方式 | 1. 创建 Query Report「本部门考勤异常」按部门筛选；2. 解决 Attendance Request 创建 blocker 后配置 Workflow：员工提交→主管确认/驳回→人事处理 |
| 是否需要自定义 App | 否 |
| 是否需要自定义 DocType | 见 §6.3（Attendance Request blocker 解决方案） |
| 风险 | 依赖 AR blocker 解决方案 |
| 验收方式 | 以主管账号「manager.demo@hbos.local」登录 → 看到本部门异常列表 → 可以逐条确认或驳回 |

### 5.11 人事异常处理入口

| 属性 | 内容 |
| --- | --- |
| 编号 | GAP-11 |
| 需求来源 | M1 产品需求说明书 §人事/考勤管理员处理入口；M1 验收标准 #9 |
| M1 承诺 | 人事能最终归档，包括员工管理、班次管理、数据导入、异常处理工作台 |
| 当前实际可体验状态 | HRMS 原生 Employee/Shift Type/Shift Assignment 列表可访问。但**没有集成的「人事异常处理工作台」**——员工管理、班次管理、导入入口、异常处理分散在不同原生页面，没有一个统一入口。 |
| 差距判断 | **体验缺口**：原生能力可凑，但没有产品化的统一工作台 |
| 优先级 | P1 |
| 推荐实现方式 | 在海滨考勤工作台中聚合入口：员工管理、班次管理、打卡数据导入、异常处理工作台、月度汇总、操作日志 |
| 是否需要自定义 App | 否（Workspace 聚合即可） |
| 是否需要自定义 DocType | 否 |
| 风险 | 低 |
| 验收方式 | 以人事账号「hr.demo@hbos.local」登录 → 在「海滨考勤」工作台中看到所有管理入口快捷卡片 |

### 5.12 异常说明三级流程

| 属性 | 内容 |
| --- | --- |
| 编号 | GAP-12 |
| 需求来源 | M1 真实需求确认 §异常处理流程；M1 验收标准 #7、#8、#9 |
| M1 承诺 | 员工提交异常说明 → 主管确认事实 → 人事最终处理 → 操作留痕 |
| 当前实际可体验状态 | 11 个 Custom Field 已在 HRMS 原生 Attendance Request 上扩展完成（6 种异常类型 + 三级状态字段）。但**核心 Blocker**：HRMS 原生 `validate_no_attendance_to_create()` 在已有 Attendance 时阻止 Attendance Request 创建（这是 by design，不是 Bug）。导致整个三级流程无法在浏览器中走通。 |
| 差距判断 | **运行时阻断**：数据结构已就绪，流程被 native validation 阻止 |
| 优先级 | P1 |
| 推荐实现方式 | 见 §6.3 详细分析 |
| 是否需要自定义 App | 见 §6.3 |
| 是否需要自定义 DocType | 见 §6.3 |
| 风险 | 无论选哪种方案，都需要修改运行态行为（Hook 覆盖/自定义 DocType/文档化限制） |
| 验收方式 | 员工提交异常说明 → 主管看到并确认/驳回 → 人事最终处理 → 操作记录可查 |

### 5.13 操作留痕

| 属性 | 内容 |
| --- | --- |
| 编号 | GAP-13 |
| 需求来源 | M1 真实需求确认 §操作留痕 |
| M1 承诺 | 记录谁、什么时候、改了什么、修改原因、处理状态 |
| 当前实际可体验状态 | Frappe 原生 Version（DocType 级别修改历史）+ Comment + Activity Log 存在且可用。但**未针对考勤异常处理场景做集成展示**——操作留痕分散在不同原生日志中，没有统一的「考勤操作日志」视图。 |
| 差距判断 | **体验缺口**：能力存在但不聚合，人事难以快速定位某次异常处理的操作历史 |
| 优先级 | P1 |
| 推荐实现方式 | 创建 Query Report「考勤操作日志」聚合 Attendance/Attendance Request 的 Version 记录，按操作人/时间/操作类型筛选 |
| 是否需要自定义 App | 否 |
| 是否需要自定义 DocType | 否 |
| 风险 | Frappe Version 记录粒度较粗（记录整个 DocType 的修改前后差异），需确认是否满足「改了什么的业务描述」需求 |
| 验收方式 | 在「考勤操作日志」页面按操作人/日期筛选，可看到对应的操作记录 |

### 5.14 月度汇总报表

| 属性 | 内容 |
| --- | --- |
| 编号 | GAP-14 |
| 需求来源 | M1 产品需求说明书 §月度汇总报表；M1 验收标准 #4 |
| M1 承诺 | 能在页面看到月度汇总报表（14 字段：员工姓名、部门、应出勤、实际出勤、迟到/早退/缺卡/缺勤次数、请假、加班、节假日出勤、异常待确认、最终状态、备注） |
| 当前实际可体验状态 | R5 已设计 Query Report SQL（14 字段映射和覆盖分析）。但**数据库中未创建 Query Report**。Owner 无法在浏览器中看到月度汇总报表。 |
| 差距判断 | **功能缺口**：方案已设计，零实现 |
| 优先级 | P1 |
| 推荐实现方式 | 1. 在数据库中创建 Query Report「月度考勤汇总表」（中文名）；2. 配置 14 个字段列；3. 支持按部门/月份筛选；4. 所有字段标签使用中文 |
| 是否需要自定义 App | 否（但需版本化载体，建议在轻量 App 中以 fixture 形式保存） |
| 是否需要自定义 DocType | 否（Query Report 即可） |
| 风险 | SQL 需要关联 Employee/Attendance/Shift Assignment/Leave Application 多表，复杂度较高 |
| 验收方式 | 人事登录 → 进入「月度汇总报表」→ 选择 2026-06 → 看到全员月度汇总表（14 字段齐全） |

### 5.15 月报导出

| 属性 | 内容 |
| --- | --- |
| 编号 | GAP-15 |
| 需求来源 | M1 产品需求说明书 §月度汇总与导出；M1 验收标准 #10 |
| M1 承诺 | 能导出 Excel 月报 |
| 当前实际可体验状态 | R5 已固化 4 种导出路径（Report Export/List Export/Data Export/Script Report），Frappe 原生 Excel 导出可用。但**因为 Query Report 未创建，导出入口实际上不可用**——没有什么可以导出的。 |
| 差距判断 | **依赖缺口**：导出能力原生就绪，但没有可导出的报表 |
| 优先级 | P1（与 GAP-14 月度汇总报表合并推进） |
| 推荐实现方式 | 在 Query Report「月度考勤汇总表」创建后，直接使用 Frappe Report Export 导出 Excel |
| 是否需要自定义 App | 否 |
| 是否需要自定义 DocType | 否 |
| 风险 | 低（Frappe 原生导出已成熟） |
| 验收方式 | 在月度汇总报表页面点击「导出」→ 下载 Excel 文件 → 文件内容与页面展示一致 |

### 5.16 领导汇总 Demo

| 属性 | 内容 |
| --- | --- |
| 编号 | GAP-16 |
| 需求来源 | M1 产品需求说明书 §领导汇总 Demo；M1 验收标准 #11 |
| M1 承诺 | 领导能看到汇总 Demo（本月异常人数、迟到总次数、缺卡总次数、部门排名） |
| 当前实际可体验状态 | R7 已设计 4 项核心指标 + Query Report SQL + Dashboard Chart。但**数据库中未创建 Dashboard 和 Dashboard Chart**。Owner 无法以领导视角看到任何汇总数据。 |
| 差距判断 | **功能缺口**：方案已设计，零实现 |
| 优先级 | P1 |
| 推荐实现方式 | 1. 创建 Dashboard「领导看板 - 考勤汇总」；2. 创建 4 个 Dashboard Chart（异常人数卡片、迟到次数卡片、缺卡次数卡片、部门排名柱状图）；3. 数据基于 Query Report SQL；4. 所有指标名称、图表标题使用中文 |
| 是否需要自定义 App | 否（但需版本化载体） |
| 是否需要自定义 DocType | 否 |
| 风险 | 依赖 Demo 数据扩展到足够规模（≥10 员工 × 完整月），否则指标没有展示价值 |
| 验收方式 | 以领导账号「leader.demo@hbos.local」登录 → 看到领导看板 → 4 项指标有数值 → 部门排名可切换 |

### 5.17 多角色体验账号与权限路径

| 属性 | 内容 |
| --- | --- |
| 编号 | GAP-17 |
| 需求来源 | Owner 追加要求 §2.2 虚构账号；M1 产品需求说明书 §用户角色 |
| M1 承诺 | 4 类角色（人事/员工/主管/领导）+ 系统管理员兜底 |
| 当前实际可体验状态 | 仅 Administrator 一个可用账号。**没有人事、员工、主管、领导的体验账号**。无法验证不同角色的权限隔离和页面差异。 |
| 差距判断 | **功能缺口**：零体验账号 |
| 优先级 | P2 |
| 推荐实现方式 | 1. 创建 4 个 Frappe User（hr.demo/employee.demo/manager.demo/leader.demo@hbos.local）；2. 创建对应的 Employee 记录；3. 配置 Frappe Role：HR Manager / Employee Self Service / Leave Approver / 自定义领导角色；4. 配置 User Permission 实现数据隔离（员工只看自己，主管只看本部门） |
| 是否需要自定义 App | 否 |
| 是否需要自定义 DocType | 否 |
| 风险 | Frappe User Permission 配置较复杂，需仔细验证每个角色的数据可见范围 |
| 验收方式 | 分别以 4 个角色账号登录 → 每个人看到的页面和数据与预期角色权限一致 |

### 5.18 飞书 OAuth 最小验证

| 属性 | 内容 |
| --- | --- |
| 编号 | GAP-18 |
| 需求来源 | Owner 追加要求 §4 飞书 OAuth 最小验证；M1 验收标准 #1 |
| M1 承诺 | 飞书扫码登录成功 + 自动匹配 Employee |
| 当前实际可体验状态 | M1-R7 已设计 Social Login Key 配置参数表和员工匹配规则。但**真实 OAuth 端到端验证未执行**，原因为 6 类 blocker（飞书应用未创建/回调 URL 未配置/手机号权限未获取/HBOS 无公网地址/App Secret 安全约束/Social Login Key 未写入数据库）。根据飞书验收分级，当前为 **C 级**（凭证未提供，仍停留方案）。 |
| 差距判断 | **验证缺口**：方案完整但未执行真实验证 |
| 优先级 | P2 |
| 推荐实现方式 | 1. Owner 在飞书开放平台创建应用 → 获取 App ID + App Secret；2. Owner 配置回调域名（本地可用内网穿透如 ngrok）；3. 在 Frappe Social Login Key 中写入配置（不提交）；4. 执行端到端验证：扫码→登录→匹配 Employee→进入对应页面；5. 安全红线：App Secret 仅通过本地未提交配置文件/环境变量传递，不写入文档，不提交 Git |
| 是否需要自定义 App | **是**：建议创建 `hb_feishu_app` 承载飞书相关 OAuth 配置、回调和员工匹配逻辑 |
| 是否需要自定义 DocType | 否（Social Login Key 是 Frappe 原生 DocType） |
| 风险 | 需要 Owner 提供飞书开放平台权限和回调域名配置；内网穿透方案仅适合本地验证 |
| 验收方式 | A 级：浏览器点击「飞书登录」→ 扫码 → 登录成功 → 正确匹配 Employee；B 级：配置完成但回调/权限/域名阻塞，记录具体阻塞原因；C 级：凭证未提供 |

### 5.19 本地 Administrator 兜底登录

| 属性 | 内容 |
| --- | --- |
| 编号 | GAP-19 |
| 需求来源 | M1 真实需求确认 §M1 主入口「同时允许本地管理员登录作为管理兜底」 |
| M1 承诺 | 本地管理员账号可兜底登录 |
| 当前实际可体验状态 | Administrator 可正常登录。✅ **已满足**。但需在 M1-FIX 各轮中持续确保不被破坏。 |
| 差距判断 | **无缺口**：当前可用，需持续保持 |
| 优先级 | 持续保障 |
| 推荐实现方式 | 保持当前 Administrator 账号可用；在各轮开发和配置变更后验证管理员登录不中断 |
| 是否需要自定义 App | 否 |
| 是否需要自定义 DocType | 否 |
| 风险 | 飞书 OAuth 配置或权限变更可能间接影响本地登录；需在每次变更后验证 |
| 验收方式 | 在飞书登录无法使用时，Administrator 仍可正常登录 Frappe Desk |

### 5.20 未来真实考勤机接口说明

| 属性 | 内容 |
| --- | --- |
| 编号 | GAP-20 |
| 需求来源 | M1 验收标准 #12 |
| M1 承诺 | 技术方案说明未来如何接真实考勤机 |
| 当前实际可体验状态 | M1 技术设计中已固化通用适配层设计：`考勤机/门禁/Excel/API → 原始打卡记录 Raw Checkin → 清洗映射 → Employee Checkin → Attendance`。✅ **方案已满足**。 |
| 差距判断 | **无缺口**：方案已明确，属于未来 M3+ 实施内容 |
| 优先级 | 无需补漏（方案已完整） |
| 推荐实现方式 | 接口契约已固化，M3+ 实施 |
| 是否需要自定义 App | 否（M1 范围内不需要） |
| 是否需要自定义 DocType | 否（M1 范围内不需要） |
| 风险 | 不同品牌考勤机数据格式差异大，需 M3+ 逐型号适配 |
| 验收方式 | M1 范围内无需验收，方案已作为 M1 交付物 |

---

## 6. 是否需要自定义 App / DocType 的初步判断

### 6.1 总体判断

M1-FIX 大部分缺口可以通过 HRMS/Frappe 原生能力（Data Import、Query Report、Dashboard、Workspace、Social Login Key、Custom Field、Frappe Role/User Permission）补上，**但存在 3 类需要 Gate 决策的场景**。

### 6.2 候选 App

| 候选 App | 触发条件 | 当前是否需要 |
| --- | --- | --- |
| `hb_attendance_app` | 需要版本化管理 Workspace/Report/Dashboard fixture；或需要自定义考勤业务逻辑 | **M1-FIX 可能需要创建轻量版**（仅承载 fixture，不写业务代码）。原因：Workspace/Query Report/Dashboard 写入数据库后无法通过 Git 版本化，重建环境会丢失。但如果不重建环境、仅做 Demo 演示，可以不创建 App。 |
| `hb_feishu_app` | 需要飞书 OAuth 自定义回调逻辑或员工匹配脚本 | **M1-FIX-E 可能需要创建**。原因：Frappe Social Login Key 原生支持标准 OAuth，但飞书的员工匹配（手机号>邮箱>工号三级优先级 + 未匹配提示）可能需要自定义回调钩子。 |

### 6.3 候选 DocType

| 候选 DocType | 触发条件 | 当前是否需要 | 详细分析 |
| --- | --- | --- | --- |
| `HBOS 导入批次日志` | 需要记录 Excel 导入的批次号、导入人、时间、成功/失败数 | **P0 推荐创建** | 原因：Frappe Data Import 原生不提供批次级别的导入历史查询。不创建则无法追溯「谁在什么时候导入了什么文件、多少成功多少失败」。创建后最小字段：`批次号`(Data)、`导入人`(Link: User)、`导入时间`(Datetime)、`导入类型`(Select: 原始打卡流水/月度汇总)、`来源文件名`(Data)、`总记录数`(Int)、`成功数`(Int)、`失败数`(Int)、`失败原因`(Text)。不修改核心源码。需要 Owner 授权。 |
| `HBOS 月度考勤汇总` | 需要承载月度汇总 Excel 导入的对账数据 | **P1 推荐创建** | 原因：HRMS 原生 Attendance 按日记录，没有「月度汇总快照」对象。如果直接从 Excel 导入月度汇总数据用于对账和演示，需要一个承载 DocType。不创建则月度汇总导入无法落地。创建后最小字段：`员工`(Link: Employee)、`部门`(Link: Department)、`月份`(Data)、`应出勤天数`(Float)、`实际出勤天数`(Float)、`迟到次数`(Int)、`早退次数`(Int)、`缺卡次数`(Int)、`缺勤天数`(Float)、`请假天数`(Float)、`加班小时`(Float)、`节假日出勤`(Int)、`异常待确认数`(Int)、`最终状态`(Select)、`备注`(Text)。不修改核心源码。需要 Owner 授权。 |
| `HBOS 考勤异常` | Attendance Request 创建被 native validation 阻止时的替代方案 | **P1 评估，默认不创建** | 原因：见下方 §6.4 详细分析。 |
| `HBOS 考勤修正` | 人事修正考勤数据时记录修正前后值和原因 | **M1-FIX 暂不创建** | 原因：M1 范围内的修正操作可以通过 HRMS 原生 Attendance Request 或直接编辑 Attendance 记录实现（配合 Frappe Version 留痕）。后续业务量增大时再评估。 |

### 6.4 Attendance Request Blocker 解决方案对比

当前核心 Blocker：HRMS 原生 `validate_no_attendance_to_create()` 方法在 Employee 当日已有 Attendance 记录时，阻止创建 Attendance Request。这是 HRMS by design 的行为——Attendance Request 的设计意图是「补录缺勤日的考勤」，不是「修正已有 Attendance 的异常」。

三种候选方案：

| 方案 | A：Hook 绕过 | B：自定义 DocType `HBOS 考勤异常` | C：不要 Attendance Request，直接在 Attendance 上扩展 |
| --- | --- | --- | --- |
| 做法 | 写一个 Frappe Hook 覆盖 `validate_no_attendance_to_create`，允许在已有 Attendance 时创建 AR | 创建独立 DocType `HBOS 考勤异常`，字段包含 11 个 Custom Field + 关联 Attendance，完全脱离 Attendance Request | 在 Attendance DocType 上用 Custom Field 扩展异常说明字段，异常处理直接在 Attendance 上操作 |
| 优点 | 最大化复用 HRMS 原生 AR 和 Workflow 机制 | 不受 HRMS 升级影响；字段和流程完全可控 | 最简单：不创建新 DocType，不绕过原生校验 |
| 缺点 | 修改了 HRMS 运行态行为（虽然不是改核心源码）；HRMS 升级可能冲突 | 需要重新实现三级流程（Workflow 或自定义状态机）；与 HRMS 原生 AR 功能割裂 | Attendance 原生不支持 Workflow；在考勤结果上直接做业务操作不够规范 |
| 是否修改核心源码 | 否（Hook 是 Frappe 扩展机制） | 否 | 否（Custom Field） |
| 是否影响后续维护 | HRMS 升级时 Hook 需要回归测试 | 维护独立的 DocType + Workflow | 低影响，但后续业务复杂时可能需要迁移 |
| 是否需要 Owner 授权 | 是 | 是 | 是 |
| **推荐** | **M1-FIX 首选方案 A** | 方案 A 不可行时的备选 | 短期应急，不推荐 |

**M1-FIX 推荐方案**：优先方案 A（Hook 绕过），因为：
1. 11 个 Custom Field 已经创建在 Attendance Request 上（R6C 已完成），不需要重建数据结构。
2. Hook 是 Frappe 官方支持的扩展机制，不修改核心源码。
3. Workflow 可复用 HRMS 原生的 Workflow DocType。
4. 实施成本最低。

---

## 7. M1-FIX 推荐拆分方案

### 总体原则

- 每轮只做一轮的事，不提前实现下一轮功能。
- P0 > P1 > P2 严格按优先级推进。
- 每轮完成后必须 Owner 亲自在浏览器中验证，不依赖文档自证。
- Codex 不在 A/B/C/D 小阶段审查，只在 M1-FIX 全部完成、Owner 体验通过后统一审查。

### M1-FIX-B：Excel 导入与 Demo 数据闭环（P0 优先级）

**覆盖缺口**：GAP-01、GAP-03、GAP-04、GAP-05

**目标**：

1. 本地数据导入（A 轨 — Owner 真实数据，不提交 Git）：
   - 基于 `docs/data/月度汇总表_20260701_20260703.xlsx` 中的员工姓名、工号、部门创建 Employee 记录
   - 从该 Excel 的每日时间列中提取原始打卡流水数据，导入 Employee Checkin
   - 页面应能直观展示真实姓名、工号、部门、考勤结果、异常结果
2. 创建 4 类体验账号（User + Employee）：
   - `hr.demo@hbos.local`（人事/考勤管理员）
   - `employee.demo@hbos.local`（普通员工）
   - `manager.demo@hbos.local`（部门主管）
   - `leader.demo@hbos.local`（领导）
3. 员工匹配规则落地：
   - 配置 Frappe Data Import 模板，匹配字段为 `employee_number`（工号，优先级 1）
   - 手机号 > 邮箱 > 姓名按优先级降级
   - 验证匹配成功和失败的场景
   - 未匹配员工必须展示：行号、姓名、工号、失败原因、处理建议
4. Employee Checkin 导入闭环：
   - 通过 Data Import UI 上传 Excel
   - 验证 Employee Checkin 列表可查看导入结果
5. Auto Attendance 生成：
   - 执行 `process_auto_attendance()` 生成 Attendance
   - 验证 `late_entry`/`early_exit` 正确置位
6. 异常覆盖验证：
   - 基于真实数据覆盖迟到/早退/上班缺卡/下班缺卡/全天缺勤/请假/节假日出勤/跨夜班/正常出勤等场景
7. 如 Owner 授权：创建 `HBOS 导入批次日志` DocType 记录导入历史

**创建内容**：
- 本地 Employee 创建脚本（从 Owner Excel 读取，不提交 Git）
- 4 类角色体验账号
- Data Import 模板配置
- 可能：`HBOS 导入批次日志` DocType（需 Owner 授权）
- B 轨脱敏模板（虚构姓名，可提交 Git）

**禁止项**：
- 不把 Owner Excel / 真实数据提交 Git
- 不在 Markdown 文档中展开真实姓名明细
- 不实现月度汇总 Excel 导入（留给 FIX-C）
- 不实现异常说明三级流程（留给 FIX-C）
- 不创建考勤工作台（留给 FIX-D）
- 不接飞书（留给 FIX-E）
- 不修改核心源码

**验收方式**：Owner 以人事账号登录 → 上传 Excel → 看到导入成功/失败数（未匹配员工显示详细信息）→ Employee Checkin 列表有数据（直观展示真实姓名/工号/部门）→ Attendance 列表中看到考勤结果 → 迟到/早退/缺卡正确标记

### M1-FIX-C：异常说明三级流程（P1 优先级）

**覆盖缺口**：GAP-07、GAP-12、GAP-13

**目标**：

1. 解决 Attendance Request 创建 Blocker：
   - 方案 A（推荐）：Frappe Hook 绕过 `validate_no_attendance_to_create`
   - 验证 AR 在有 Attendance 的场景下可成功创建
2. 异常说明三级流程贯通：
   - 员工：以 `employee.demo` 登录 → 查看自己的异常 → 提交异常说明（选择类型：补卡/设备异常/公出会议/班次错误/请假未同步/其他）
   - 主管：以 `manager.demo` 登录 → 看到本部门待处理异常 → 确认事实或驳回
   - 人事：以 `hr.demo` 登录 → 看到主管已确认的异常 → 最终处理/归档
3. 操作留痕验证：
   - 确认 Frappe Version + Comment + Activity Log 可记录三级流程的操作历史
4. 缺勤场景验证：
   - 补充全天缺勤 Demo 数据并验证识别正确
5. 如 Owner 授权：配置 Frappe Workflow 实现状态流转

**创建内容**：
- Frappe Hook 文件（`hb_attendance_app/hooks.py` 或轻量 App 内）
- 可能：Frappe Workflow 配置

**禁止项**：
- 不创建月度汇总报表（留给 FIX-D）
- 不创建考勤工作台（留给 FIX-D）
- 不接飞书（留给 FIX-E）
- 不修改核心源码

**验收方式**：Owner 以 3 个角色分别登录 → 完整走通员工提交→主管确认→人事归档的流程 → 操作历史可追溯

### M1-FIX-D：考勤工作台 + 月报 + 领导 Demo（P1 优先级）

**覆盖缺口**：GAP-02、GAP-08、GAP-09、GAP-10、GAP-11、GAP-14、GAP-15、GAP-16

**目标**：

1. 海滨考勤工作台：
   - 创建 Frappe Desk Workspace「海滨考勤」（中文名）
   - 包含快捷入口：打卡数据导入、考勤异常清单、月度汇总报表、员工考勤查询
   - 按角色展示不同入口
2. 月度汇总报表：
   - 创建 Query Report「月度考勤汇总表」（14 字段）
   - 支持按部门/月份筛选
3. 月报导出：
   - 通过 Frappe Report Export 导出 Excel
4. 领导汇总 Demo：
   - 创建 Dashboard「领导看板 - 考勤汇总」
   - 4 个 Dashboard Chart（中文指标名）
5. 员工个人考勤视图：
   - 创建 Query Report「我的考勤」
6. 主管本部门异常视图：
   - 创建 Query Report「本部门考勤异常」
7. 月度汇总 Excel 导入：
   - 创建 `HBOS 月度考勤汇总` DocType（需 Owner 授权）
   - 实现月度汇总 Excel 导入与对账展示

**创建内容**：
- Workspace「海滨考勤」
- Query Report「月度考勤汇总表」「我的考勤」「本部门考勤异常」「考勤操作日志」
- Dashboard「领导看板 - 考勤汇总」+ 4 个 Dashboard Chart
- 可能：`HBOS 月度考勤汇总` DocType（需 Owner 授权）
- 可能：轻量 App（`hb_attendance_app`）用于版本化管理 fixture（需 Owner 授权）

**禁止项**：
- 不接飞书（留给 FIX-E）
- 不修改核心源码
- 不做大型 Vue/React 前端

**验收方式**：Owner 以人事/员工/主管/领导 4 个角色分别登录 → 各自看到对应的工作台和报表 → 月度汇总可筛选可导出 → 领导看板有数据

### M1-FIX-E：飞书 OAuth 最小验证 + Owner 体验脚本 + 总审查准备（P2 优先级）

**覆盖缺口**：GAP-17、GAP-18

**目标**：

1. 飞书 OAuth 真实最小验证：
   - Owner 在飞书开放平台创建应用 → 提供 App ID + App Secret（通过安全方式，不在聊天中粘贴）
   - 配置回调域名（内网穿透或公网地址）
   - 在 Frappe Social Login Key 中写入配置
   - 执行端到端验证：扫码→登录→匹配 Employee
   - 记录验证结果等级（A/B/C）
2. 多角色体验账号权限配置：
   - 配置 Frappe Role 和 User Permission
   - 验证每个角色的数据隔离
3. 本地 Administrator 兜底登录：
   - 确认飞书登录配置未影响本地管理员登录
4. Owner 体验脚本：
   - 编写 M1-FIX 逐项体验清单（按角色、按场景）
   - 列出每项体验的地址、账号、操作步骤、预期结果
5. M1-FIX 总审查材料：
   - 汇总 M1-FIX-B/C/D/E 全部交付物
   - 整理一次性 Codex 总审查提示词

**创建内容**：
- Social Login Key 配置（写入数据库，不提交）
- Owner 体验脚本（`docs/milestones/M1_FIX_Owner体验脚本.md`）
- M1-FIX 总审查材料（`docs/milestones/M1_FIX_总审查材料.md`）

**禁止项**：
- 不提交 App Secret、`.env`、密钥
- 不伪造飞书登录成功
- 不启动 M2

**验收方式**：飞书 A 级或 B 级验证完成 → Owner 按体验脚本逐项走通 → 准备 Codex 总审查材料

---

## 8. M1-FIX-A 本轮输出项

### 8.1 Owner 需在本轮确认的 5 项 Gate 决策

| # | 决策项 | 建议 | 影响 |
| --- | --- | --- | --- |
| G1 | 是否需要创建 `hb_attendance_app`（轻量版）承载 Workspace/Report/Dashboard fixture？ | 建议 M1-FIX-D 启动前创建 | 不创建则 Workspace/Report/Dashboard 只能写数据库无法 Git 版本化；创建后重建环境可恢复 |
| G2 | 是否需要创建 `HBOS 导入批次日志` DocType？ | 建议 M1-FIX-B 中创建 | 不创建则无法追溯导入历史 |
| G3 | 是否需要创建 `HBOS 月度考勤汇总` DocType？ | 建议 M1-FIX-D 中创建 | 不创建则月度汇总导入无法落地 |
| G4 | Attendance Request Blocker 方案选择？ | 推荐方案 A（Hook 绕过） | 方案 A 成本最低，但 HRMS 升级时需回归测试 |
| G5 | 飞书验证时间窗口？ | 建议 M1-FIX-E 执行 | 需 Owner 准备飞书开放平台应用和回调域名 |

### 8.2 数据安全红线重申

所有 M1-FIX 阶段必须遵守：

**A 轨（Owner 本地验收数据）允许**：
- 本地运行 / 本地导入 / 本地页面验收使用真实姓名和真实考勤数据
- 数据源：`docs/data/月度汇总表_20260701_20260703.xlsx`

**A 轨禁止**：
- 不把真实 Excel / CSV 提交到 Git
- 不把真实员工姓名批量写入 Markdown 文档正文
- 不把真实员工数据做成仓库内 fixture / seed / json / csv / xlsx
- 不在最终报告中打印真实员工姓名清单
- 不提交由真实员工数据导出的文件

**B 轨（仓库可提交）规则**：
- 如需要模板或自动化测试数据，必须使用虚构姓名
- 不含任何真实个人信息
- 可提交 Git

**全阶段禁止**：
- 不提交 `.env`、App Secret、密钥、token
- 不提交数据库、日志、缓存、备份、运行时产物
- 不修改 Frappe/ERPNext/HRMS 核心源码
- 飞书 App Secret 仅通过本地未提交配置传递
- Git 提交中只允许提交方案文档与状态文档

---

## 9. 状态更新

### 9.1 项目总状态

```
M1     = COMPLETED（但 Owner 验收发现功能缺口）
M1-FIX = IN_PROGRESS
M1-FIX-A = REVIEWING
M2     = PLANNED / NOT STARTED / WAITING OWNER AUTHORIZATION
```

### 9.2 状态文件更新计划

本轮将更新：
- `docs/PROJECT_STATUS.md`：新增 M1-FIX 状态段，M1 状态补充 Owner 验收发现
- `docs/CURRENT_MILESTONE.md`：当前轮次从 M1 closeout 切换到 M1-FIX-A
- `docs/milestones/README.md`：新增 M1-FIX-A 条目
- `docs/AI_CONTEXT.md`：补充 M1-FIX 阶段上下文
- `README.md`：当前阶段描述更新
- `docs/milestones/M1_START_GATE.md`：补充 M1-FIX-A 状态

无需更新：
- `CLAUDE.md`：无过期阶段描述（只描述规则，不描述具体阶段）
- `AGENTS.md`：同 CLAUDE.md
- `docs/READING_GUIDE.md`：当前里程碑提醒需更新

---

## 10. 下一步建议

等待 Owner 审阅 M1-FIX-A 方案后：

1. **确认 5 项 Gate 决策**（§8.1）
2. **授权 M1-FIX-B**：Excel 导入与 Demo 数据闭环
3. **不直接启动 M2**：M1-FIX 全部完成 + Owner 体验通过 + Codex 总审查通过后，再讨论 M2

---

## 附录 A：M1 12 条验收标准与 M1-FIX 对应关系

| # | 验收标准 | M1 closeout 状态 | 本轮差距判断 | M1-FIX 轮次 |
| --- | --- | --- | --- | --- |
| 1 | 人事能登录 | 部分完成 | 缺飞书真实验证 + 人事体验账号 | FIX-E |
| 2 | 能看到考勤工作台 | 已完成（方案） | 数据库无 Workspace | FIX-D |
| 3 | 能导入脱敏考勤 Excel | 部分完成 | 无 Demo Excel、无 UI 导入、无结果反馈 | FIX-B |
| 4 | 能生成/展示月度考勤结果 | 部分完成 | 无 Query Report，数据规模极小 | FIX-D |
| 5 | 能识别迟到早退缺卡缺勤 | 已完成 | 缺勤场景未验证，缺卡无独立展示 | FIX-C |
| 6 | 员工能查看自己的记录 | 已完成（原生列表） | 无产品化个人视图，无员工体验账号 | FIX-D |
| 7 | 员工能提交异常说明 | 部分完成 | AR 创建被 native validation 阻止 | FIX-C |
| 8 | 主管能确认异常 | 部分完成 | 依赖 AR 创建 + Workflow 未配置 | FIX-C |
| 9 | 人事能最终归档 | 部分完成 | 依赖 AR 创建 + Workflow 未配置 | FIX-C |
| 10 | 能导出 Excel 月报 | 已完成（路径） | 无 Query Report 可导出 | FIX-D |
| 11 | 领导能看到汇总 Demo | 部分完成 | 无 Dashboard，数据规模极小 | FIX-D |
| 12 | 未来如何接真实考勤机 | 已完成 | 无需补漏 | — |

## 附录 B：Demo 数据包字段规范（中文）

### 数据策略（双轨制）

M1-FIX 采用双轨数据策略：

| 轨道 | 用途 | 数据源 | 是否提交 Git | 是否含真实姓名 |
| --- | --- | --- | --- | --- |
| A 轨 | Owner 本地验收 | `docs/data/月度汇总表_20260701_20260703.xlsx` | 否 | 是（本地使用，不提交） |
| B 轨 | 仓库可提交模板/样例 | 另行准备脱敏数据 | 是 | 否（虚构姓名） |

### 员工表示例字段（B 轨）
`员工工号`、`员工姓名`、`部门`、`公司`、`手机号`、`公司邮箱`、`用户ID`

### 原始打卡流水示例字段（B 轨）
`员工工号`、`员工姓名`、`部门`、`日期`、`班次类型`、`应上班时间`、`应下班时间`、`实际上班打卡`、`实际下班打卡`、`请假时长`、`备注`、`预期结果`、`异常类型`

### 月度汇总示例字段（B 轨）
`员工工号`、`员工姓名`、`部门`、`月份`、`应出勤天数`、`实际出勤天数`、`迟到次数`、`早退次数`、`缺卡次数`、`缺勤天数`、`请假天数`、`加班小时`、`节假日出勤`、`异常待确认`、`最终状态`、`备注`

### 员工姓名示例（B 轨 — 虚构）
`海滨员工甲01`、`海滨员工甲02`、`海滨员工乙01`、`海滨员工丙01`……B 轨使用虚构姓名。

A 轨使用 Owner Excel 中的真实姓名，仅用于本地验收，不写入文档正文，不提交 Git。

### 部门名称示例
`生产一部`、`生产二部`、`行政管理部`、`品质管理部`……使用与真实组织架构对应的虚构部门名。

### 账号邮箱示例
`hr.demo@hbos.local`、`employee.demo@hbos.local`、`manager.demo@hbos.local`、`leader.demo@hbos.local`

### 菜单/按钮/标签中文示例
「海滨考勤」「打卡数据导入」「考勤异常清单」「月度汇总报表」「领导看板」「提交异常说明」「确认事实」「驳回」「最终归档」「导出月报」「我的考勤」「本部门异常」「考勤操作日志」

---

## 附录 C：M1-FIX 禁止项总清单

M1-FIX 全程禁止：
- 不创建 `hb_core_app`
- 不安装非必要 App
- 不修改 Frappe/ERPNext/HRMS 核心源码
- 不提交 `.env`、App Secret、密钥、token
- **不提交真实员工姓名、真实工号、真实数据到 Git**（A 轨数据仅本地验收使用）
- **不把真实 Excel / CSV 提交到 Git**
- **不把真实员工姓名批量写入 Markdown 文档正文**
- **不把真实员工数据做成仓库内 fixture / seed / json / csv / xlsx**
- B 轨脱敏数据如准备则可提交（不含任何真实个人信息）
- 不提交数据库、日志、缓存、备份、运行时产物
- 不接真实考勤机
- 不部署公司内网/云服务器
- 不启动大型 Vue/React 前端
- 不启动 M2
- 不伪造飞书登录成功
- 不要求 Owner 在聊天中粘贴 App Secret
- 不执行 `docker compose down -v`
- 不删除 Docker volume
- 不重建 `frontend` site
