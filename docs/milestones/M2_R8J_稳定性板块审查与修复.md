# M2-R8J 稳定性板块前后端审查与缺陷修复

> 状态：**DEPLOYED / 待 Owner 生产路径验收**（本轮联动、审查缺陷修复及趋势摘要下拉控件宽度修复已按 Owner 授权同步生产；生产发布脚本 pytest **342/342**、生产前端 `build:prod` 通过，生产路径 17 个页面/资源冒烟均返回 200；备份 `【内部备份标识已省略】`；结果页已完成生产浏览器复测）

> 追加状态（2026-09-22）：Owner 已确认并授权侧栏「最近访问」关闭交互同步生产；提交 `934e36a`，完整 pytest **342/342**、前端 `build:prod` 和 `/hbos-lims` 关键路由/主资源 HTTP 200 冒烟通过；备份 `【内部备份标识已省略】`。本次为纯前端资产同步，不涉及后端迁移。
>
> 轮次：M2-R8J（R8 板块整体交付后的独立审查与修复轮），工作分支 `m2-r8`
>
> 上游：M2-R8A~R8D（后端）、R8G/R8H/R8I（前端 7 视图接入真实 API）
>
> 边界：**只做审查与缺陷修复**——不新增功能、不改方案口径。审查对象为稳定性板块全部后端（`stability_service.py` 4306 行 / 22 DocType / 8 状态机 / 6 报表）与前端（7 视图 + `api/stability.ts`）

> 追加状态（2026-09-21）：Owner 确认将“稳定性取样样品未与业务检验结果及稳定性趋势贯通”作为本轮既有业务链缺陷闭环处理；联动实现及后续审查修复已完成生产同步，见 §9、§10。

---

## 1. 本轮审查结论

审查方式：通读后端写路径与守卫层、22 个 DocType 权限配置、前端 7 视图与接口层，做接口名与角色矩阵的前后端 diff，再以**非 Administrator 真实用户**跑端到端模拟与负向安全用例。

**结论：核心设计成立，未发现注入 / XSS / 越权读取类漏洞**：

- 零裸 SQL（全部走 ORM）→ 无 SQL 注入面
- 无 `v-html` / `innerHTML` / `eval` → 无 XSS 面
- **91 个 whitelist 方法全部调用 `_check_action`**，方法名与 `ACTION_ROLES` 注册表零缺口
- 锁协议正确：无任何函数同时持有 Sample 与 Timepoint 两把锁，`_lock_row` 均带 `for_update=True`
- 负向拦截全部生效且独立留痕（越权拦截 / 删除拦截 / SoD 拦截三项审计计数正确增长）
- 6 张 Script Report 对 LIMS 角色渲染正常，对无角色用户 6/6 拒绝

**首轮发现 3 项 P1 + 2 项 P2，后续复核又发现 8 项 P1 + 2 项 P2；全部已修复并完成测试路径回归，详见 §2 与 §4。**

## 2. 缺陷清单与处置

| # | 级别 | 问题 | 根因 | 处置 |
| --- | --- | --- | --- | --- |
| 1 | P1 | **报告链断裂**：`HBOS Stability Report.conclusion`（评价与结论）无任何写入路径 | `create_stability_report` 不收该参数，全模块无方法写它，而 Report 对 6 个 LIMS 角色**只读**（write=0）；`submit_report` 却硬校验其非空 → 任何 LIMS 角色都无法提交报告 | 新增服务动作 **`save_report_draft`**（准入门、状态不变、仅「草稿」可改），写 `conclusion` / `trend_analysis` / `impurity_profile` / `trend_chart_ref`；前端报告页加「编辑报告内容」弹窗 |
| 2 | P1 | **结果工作流 UI 走不通**：结果页无「提交」入口 | `submitResult` 在 `api/stability.ts` 有定义但视图 **0 引用**；录入后的结果永远停在「草稿」，「复核」（要求已提交）/「批准」（要求已复核）按钮永不出现 | 结果操作列补「提交」按钮（草稿态可见，`can('submit_result')` 门控） |
| 3 | P1 | **`complete_testing` 角色门禁被绕过**（越权） | 该动作同时具备 `@frappe.whitelist()`（公开可调）与 `_check_action(..., system=True)`（直接 return、不做角色判定）；同为系统动作的 `reopen_timepoint` / `mark_superseded` 均无 whitelist，仅它因前端按钮而被暴露 | 按方案 §6.3「系统触发、用户不可直接调用」：**移除 whitelist**，改由 `approve_result` 在「该时间点全部必检项目均已批准」时经 `_maybe_complete_testing` 自动调用；前端移除「完成检测」按钮与接口 |
| 4 | P2 | **`HBOS Stability Equipment.status` 无守卫** | 控制器只有 `on_trash`，无 `validate`、无 `guard_system_fields`，`status` 亦未置 `read_only`；而方案 §8.3 明确 Equipment 用「停用」代替删除，`status` 即受控终止机制 | 新增 `EQUIPMENT_SYSTEM_FIELDS = ("status", "last_fault_date")` + 控制器 `validate`；JSON `status` 置 `read_only=1` |
| 5 | P2 | **故障工单流水子表行可被 LIMS 角色增删改** | `HBOS Stability Fault Sample` 是方案 §8.6 指定「服务专用写入」的 3 张流水表之一，但作为 Fault Ticket 子表，父单给 LIMS 角色 create+write，子表字段 `read_only` 全为 0 | 新增守卫 `guard_child_table_frozen`（按子表内容指纹比对、行序变化不计），挂在 Fault Ticket `validate` |

### 处置中的两项自主决定

- **P2-4 顺带纳入 `last_fault_date`**：它与 `status` 同属「服务层派生 / 受控」字段（由 `open_fault_ticket` 回写），同文件同类缺陷不拆分修复。经核实它由 `frappe.db.set_value` 写入、不走 validate，纳入守卫不影响合法路径（已实测）。
- **新增审计事件 `报告起草`** 已登记进 `HBOS Audit Log.log_type` 受控枚举（方案 §8.1）。这是离线契约测试强制项——首轮测试即因未登记而 FAIL，非可选项。

## 3. 验证证据（2026-09-20）

- **离线契约测试**：**321/321 通过**，其中新增 R8J 契约回归 **10/10**（`PYTHONPATH=apps/hb_lims_app python3 -m unittest discover -s apps/hb_lims_app/tests`）
- **前端**：`vue-tsc -b` **0 类型错误**、`npm run build` 成功
- **实机修复验证**（`frontend` site，非 Administrator 真实用户，`bench migrate` + gunicorn HUP 重载后）：
  - P1-3：无任何 LIMS 角色的用户调用 `complete_testing` → **拒绝**；对照 `cancel_timepoint` / `record_result` / `eval_trend` 同样拒绝；`hasattr(fn, "whitelist") == False`
  - P1-3 自动完成：批准第 1 项必检项目后时间点仍「检测中」，批准第 2 项后**自动流转「已完成」**
  - P1-1：空结论提交 → 拒；`save_report_draft` 写结论 → 提交 ✅ → 审核 ✅ → QA 经理批准（判定有效期）✅，报告终态「已批准」
  - P1-1 角色/状态门：无角色用户、LIMS QP（不在授权集）→ 拒；Reviewer → 允；已批准报告再改 → 拒（状态守卫）；空参数 → 拒
  - P2-4：Analyst / Reviewer / Manager 三者表单直改 `status` 全 **拒**；经 `manage_equipment` 改 **允**
  - P2-5：三者追加 `affected_samples` 行全 **拒**；`open_fault_ticket` 建档时写入 **允**
- **负向回归**：**11/11 通过**（无角色越权 / SoD / 删除拦截 / 系统字段直写全部仍拦截，审计计数正确；一致性扫描 0 违规）
- **端到端正链**：35/38 → 补齐 `save_report_draft` 步骤后 37/39，剩余 2 项为验证脚本参数问题（非应用缺陷）；报告链由「断裂」变为**全链闭环**
- **浏览器真实会话**（`http://localhost:5174`，LIMS Analyst 账号登录，本会话独立 dev server）：
  - 结果视图：`完成检测` 按钮已消失、「提交」按钮出现；点击后结果 **草稿 → 已提交**（后端确认 `HBOS-STB-RES-2026-00039.status = 已提交`）
  - 报告视图：「编辑报告内容」弹窗四字段（评价与结论 / 趋势分析 / 杂质概况分析 / 趋势图引用）齐全；填写保存后 `conclusion` 落库、弹窗关闭；「提交」成功 **草稿 → 待QA审核**
  - 控制台**无报错**
- **验证残留**：全部清理，站点恢复至本轮介入前的基线（Notice / Protocol / Sample 各 1 + 10 个时间点，Result / Report / Change / Room Log / Equipment / Fault Ticket 均为 0）；为取真实会话临时设置的测试账号口令**已删除**（`__Auth` 计数 0）

## 4. 2026-09-21 后续模拟测试复核

上一轮修复后的离线契约、构建和既有浏览器读写链仍然通过，但在测试路径以非 Administrator 角色进行 93 项回滚模拟时，发现以下新的生产阻断项。模拟脚本拦截所有提交并在收尾统一回滚，测试前后稳定性 DocType 记录数一致；因此未污染测试数据。

| # | 级别 | 复现结果 | 代码证据 / 影响 |
| --- | --- | --- | --- |
| 1 | P1 | 普通 `LIMS Analyst` 可通过通用 `insert` 伪造「已批准」变更单，并继续实施 | `HBOSStabilityChange.validate` 对新文档直接跳过系统字段守卫；`status` / `approver_by` 可由接口注入，`implement_change` 只信任状态 |
| 2 | P1 | QA 审核人可继续自批一般变更 | `_approve_change` 未校验审核人与批准人不同，也未校验申请人与批准人不同，违反 SoD |
| 3 | P1 | 样品可使用 A 产品通知单 / 方案登记成 B 产品 | `register_stability_sample` 未校验通知单产品、方案通知单和方案产品与入参产品一致 |
| 4 | P1 | 受托转出后库存流水无法对账 | `transfer_out` 先把 `current_qty` 清零，但流水写入 `qty_delta=0`，形成流水累计量与当前结存不一致 |
| 5 | P1 | 结果页检验项目下拉为空，无法录入新时间点结果 | 前端从计划接口读取 `test_items`，但 `get_stability_schedule` 未返回该字段 |
| 6 | P1 | 趋势图无法可靠区分当前生效值与在途值 | 后端返回 `x/y/raw/condition_type`，前端读取 `result_value/status/is_current`，数据契约不一致 |
| 7 | P1 | 已确认的期限口径①未落实：实际取样日晚于计划日时，无批准延期也可继续取样 | 取样路径只检查政策硬上限，未强制要求存在已批准的取样延期 |
| 8 | P1 | `complete_sampling` 可传入超过政策硬上限的日期（例如 `2030-01-01`）并成功流转 | 该动作直接写入 `actual_sample_date`，缺少 `policy_latest_sample_due` 硬上限校验 |
| 9 | P2 | 月份筛选在分页后执行，合法月份数据可能被错误返回为空 | `get_stability_schedule` 先 `limit_page_length`，再按月份过滤 |
| 10 | P2 | 变更条件追加没有完整输入路径，实施时通常追加 0 个时间点 | `create_stability_change` 与前端 `createChange` 均未接收 / 填写 `extra_conditions`，但实施逻辑依赖该子表 |

上述问题中，1~8 项在当前业务口径下均阻断生产放行；9~10 项会导致数据筛选错误或业务变更落空。经 Owner 授权后，10 项问题已在测试路径完成修复并完成回归验证。

## 5. 复核验证证据

- 离线契约测试：`PYTHONPATH=apps/hb_lims_app python3 -m unittest discover -s apps/hb_lims_app/tests`，**321/321 通过**，其中新增 R8J 契约回归 **10/10**。
- 前端构建：`vue-tsc -b` 通过，`vite build` 通过；仅有 chunk 体积提示，无构建错误。
- 测试路径既有实机证据：非 Administrator 真实用户读写链、6 张 Script Report、角色门控和上一轮修复项均已验证；本次修复后补充浏览器冒烟：`/stability/ops` 变更条件表单与储存条件下拉、`/stability/results` 检测中时间点 / 检验项目下拉 / 趋势区域、`/stability/schedule` 本月计划与延期/逾期派生区域均正常。
- **实机复核（2026-09-21，第二轮，本文件 §4 十项的逐项实机验证）**：由具备 Frappe bench / Docker CLI 的会话补做，逐项以非 Administrator 真实用户执行：

  | # | 用例 | 结果 |
  | --- | --- | --- |
  | P1-1 | Analyst 通用 `insert` 伪造「已批准」变更单 | **DENIED**（字段「status」为系统字段，禁止通过直接新建写入） |
  | P1-2 | QA 经理自审自批一般变更（SoD） | **DENIED**（变更批准人不得为 QA 审核人） |
  | P1-3 | 通知单产品 A / 入参产品 D 登记样品 | **DENIED**（产品不一致，禁止错配） |
  | P1-4 | 受托转出后流水对账 | 流水累计 `0.0` == 结存 `0.0`（转出前 100.0）**一致** |
  | P1-5 | `get_stability_schedule` 返回 `test_items` | 20 行全部带 items（录入下拉不再为空） |
  | P1-6 | `get_stability_trend` 契约 | 点字段含 `result_value` / `status` / `is_current` / `timepoint` |
  | P1-7 | 实际取样日晚于计划日且无批准延期 | **DENIED**（须先提交并批准取样延期）；按计划日取样 **ALLOWED** |
  | P1-8 | `complete_sampling` 传 `2030-01-01` | **DENIED**（超过有效截止日 2026-12-30） |
  | P2-9 | 月份过滤下推至分页前 | `month=2026-09` 返回行全部匹配该月份 |
  | P2-10 | 变更条件输入路径 | 带 `extra_conditions` 建档 **ALLOWED** 且子表落库 1 行；涉条件但未填条件 **DENIED**；`implement_change` 落点执行 **ALLOWED** |
- **第一轮修复项回归（同一会话实测）**：`complete_testing` 无公开入口 **DENIED**；`save_report_draft` 建档 + 写结论 + 提交报告全链 **ALLOWED**；设备 `status` 表单直写 **DENIED**、经 `manage_equipment` **ALLOWED**
- **负向回归 9/9 通过**：无角色越权（创建 / 读 / 报告草稿 / 温湿度 / 删除）、Manager 删已批准通知单、系统字段直写（Timepoint.status / Sample.current_qty / Equipment.status）全部拦截；运行期一致性扫描 **0 违规**
- **部署同步（2026-09-21）**：`deploy_lims_fix.sh` 全流程通过——预检 `pytest 329 passed`、`git diff --check` 无空格错误、生产前端构建、`bench migrate` + `clear-cache`、备份 `【内部备份标识已省略】`、同步 + 服务重启 + assets 软链重建 + nginx SPA fallback 复注入、17 条路由/资源 HTTP 200。同步后清理了 **58 个历史 root 归属的残留旧 chunk**（R6D 同类隐患），清理后远端 85 个文件与本地 `dist` **文件清单与 md5 集合逐条一致**。生产路径浏览器实测（`http://localhost:8080/hbos-lims/`，LIMS Analyst 真实会话）：结果页「完成检测」已消失、「提交」可用；报告页「编辑报告内容」→ 保存 → 提交全链走通；控制台仅既有噪音（`hrms.bundle.*` 直连 8080 同样 404、socket.io origin，均为本轮之前既有）
- **验证残留**：全部清理，站点恢复至基线（Notice / Protocol / Sample 各 1 + 10 个时间点，其余 0）；临时测试账号口令**已删除**（`__Auth` 计数 0）

## 6. 未做 / 边界

- **未修 P3 加固项**（已识别、未处置，供后续轮次评估）：
  1. `Condition` / `Product` / `Room` / `Test Item` 四张主数据 `allow_rename=1`，而文档名即业务编码且参与 `report_period_key` / `sample_cond_point_key` 等**字符串键**（改名不会同步已落库的键）→ 键漂移风险
  2. `current_result`（子表 `Timepoint Item`）仅字段级 `read_only`，无控制器守卫、不在任何 `*_SYSTEM_FIELDS` 元组
  3. 运行期一致性扫描的四类不变式**不含**「Timepoint.status ↔ 结果集一致性」，故低层 `frappe.db.set_value` 直改 status 不被检出（实测扫描返回 `[]`）
  4. `ACTION_ROLES` 为前后端两份手工副本，无一致性测试；`complete_testing` 曾因此漂移（本轮已随 P1-3 移除前端条目）
  5. Result / Report / Ops 三视图 loader 缺 `catch`，`onMounted` 内 `await` 会形成未处理拒绝并静默半加载
  6. `StbGateBanner` 默认 `mode:'demo'` 且保留 `TEST-HBOS-M2-STB-*` 文案（7 视图均显式传 `live`，分支不可达）；`demo/stabilityDemo.ts` 仍置于 `src/demo/`
  7. `equipment_name` 标签为「设备名称」实为设备**类型**枚举（方案字段表即如此，属标签语义问题）
- **已部署生产**：`/hbos-lims` 已同步至本轮成果（第一轮提交 `e447f97`；第二轮改动随本次同步一并上线），备份 `【内部备份标识已省略】` 可回滚；后端为 bind mount 实时生效
- 前端审计日志筛选下拉 `AuditLogView.LOG_TYPES` 未收录稳定性板块事件类型（**既有缺口**，非本轮引入，故未扩大范围）

## 7. 涉及文件

- `hbos_lims/stability_service.py`（`complete_testing` 去 whitelist、新增 `_maybe_complete_testing`、`approve_result` 接入自动完成、新增 `save_report_draft`）
- `hbos_lims/stability_guards.py`（新增 `EQUIPMENT_SYSTEM_FIELDS`、`_table_signature`、`guard_child_table_frozen`）
- `hbos_lims/workflow_contract.py`（注册 `save_report_draft`；系统动作注释补「无 whitelist」说明）
- `hbos_lims/doctype/hbos_stability_equipment/hbos_stability_equipment.py`（新增 `validate`）
- `hbos_lims/doctype/hbos_stability_equipment/hbos_stability_equipment.json`（`status` 置 `read_only`）
- `hbos_lims/doctype/hbos_stability_fault_ticket/hbos_stability_fault_ticket.py`（`validate` 接入子表守卫）
- `hbos_lims/doctype/hbos_audit_log/hbos_audit_log.json`（`log_type` 枚举补 `报告起草`）
- `frontend/hbos-lims-web/src/api/stability.ts`（移除 `completeTesting`、新增 `saveReportDraft`、角色矩阵同步）
- `frontend/hbos-lims-web/src/views/StabilityResultView.vue`（补「提交」、移除「完成检测」）
- `frontend/hbos-lims-web/src/views/StabilityReportView.vue`（新增「编辑报告内容」弹窗与保存动作）
- `hbos_lims/stability_guards.py`（补系统字段伪造、受控写入与取样日期守卫）
- `hbos_lims/stability_service.py`（补变更 SoD、样品关联、库存流水、计划项目、趋势契约、月份过滤与变更条件实施）
- `frontend/hbos-lims-web/src/api/stability.ts`（补计划项目、趋势字段与变更条件输入契约）
- `frontend/hbos-lims-web/src/views/StabilityOpsView.vue`（补变更后考察条件表单与储存条件选项）
- `apps/hb_lims_app/tests/test_stability_r8j_contract.py`（新增 R8J 10 项离线契约回归）

## 8. 上线后 Owner 验收修复（2026-09-21）

上线后 Owner 在 `/hbos-lims` 稳定性工作台发现仍有 R8G 时期的占位文案：「样品 / 时间点 / 结果」KPI 卡显示 `待 R8B~R8D`、提示「后端尚未交付，不展示占位数字」，且右侧整块面板标题为「待 R8B~R8D 接入」。

**根因**：R8G 时期后端只有 R8A，后端 `get_stability_dashboard` 的 docstring 明确写着「R8B~R8D 的时间点/结果/报告类 KPI 待对应子轮落地后并入」，前端据此把该项硬编码为占位；其后 R8B/R8C/R8D 相继交付，**无人回收该占位**（R8G 的验证记录「『样品 / 时间点 / 结果』显示『待 R8B~R8D』而非占位数字」当时是符合预期的，交付后即成为陈旧陈述）。这不是后端缺数据，是**前后端各留了一处未随子轮推进回收的占位**。

**处置**：

| 位置 | 修法 |
| --- | --- |
| 后端 `get_stability_dashboard` | 补 `sample_count` / `timepoint_count` / `result_count` 与 `timepoint_by_status`（待取样/待检测/检测中/已完成/已取消 五态）真实计数；更正 docstring 与 `scope` 串 |
| 前端 KPI | 原占位卡拆为 3 张真实 KPI 卡（稳定性样品 / 时间点 / 检测结果），KPI 由 6 张增至 **8 张，恰好铺满 4×2 栅格**（原 4+2 留两个空位） |
| 前端面板 | 「待 R8B~R8D 接入」面板改为**「时间点执行结构」**（五态分布 + 取样与检测计划入口） |
| 孤儿样式 | 删除因本次改动失去引用的 `.stb-timeline*` 共 5 条规则 |
| `api/stability.ts` 头注释 | 更正为「R8A~R8D 后端全量，7 视图全部接入，无演示数据」 |

**验证**：生产路径浏览器实测（`http://localhost:8080/hbos-lims/stability`，LIMS Analyst 真实会话）——KPI 8 张均为真实计数（通知单待批 0 / 已批准 1 / 方案待审 0 / 已批准 1 / 产品 3 / 样品 1 / 时间点 10 / 结果 0）；执行结构 待取样 8 / 待检测 0 / 检测中 2 / 已完成 0 / 已取消 0；页面正文**已无**任何「待 R8B / 尚未交付」文案；控制台仅既有噪音（`hrms.bundle.*` 直连 8080 亦 404、socket.io origin），无新增错误；窄屏 2 列 / 宽屏 4 列自适应、无横向溢出。离线契约 **321/321**。源码全库 grep 确认该类文案已清除。

**同步**：提交 `b61f83d`，经 `deploy_lims_fix.sh` 同步生产（备份 `【内部备份标识已省略】`），清理 5 个历史残留 chunk 后远端 **86 文件与本地 `dist` md5 逐条一致**，`/hbos-lims/` 引用新 bundle `index-BRnnDybL.js`。

### 8.2 侧边栏稳定性角标为原型遗留的硬编码数字

同批验收中 Owner 发现侧边栏「取样与检测计划」与「结果录入与趋势」恒显**红色**角标 `4` / `3`。

**根因**：与 §8.1 同一类——两个数字是 R8F HTML 原型（`docs/frontend/M2_R8_稳定性板块前端原型.html`）里的字面量 `<span class="nav-badge red">4</span>` / `<span class="nav-badge">3</span>`，Vue 复刻时**保留了位置、未接数据**；而 `.nav-badge` 基类样式为 `background: var(--danger)`，故恒显红色，看起来像告警。同文件另有一条 `// TODO: 联调后从 API 读取待办角标数` + `const pendingCount = 0`，说明「接真实数据」当时只做了一半。

**处置**：

| 项 | 修法 |
| --- | --- |
| 数据来源 | 复用 `get_stability_dashboard` 已返回的 `timepoint_by_status`（**不新增后端接口**）：取样与检测计划 = 待取样 + 待检测；结果录入与趋势 = 检测中（待录结果） |
| 颜色 | `danger`（红）→ **`amber`**：待办工作量不是错误，与「待检任务看板」既有 amber 角标一致；红色留给真正的逾期/异常 |
| 显示条件 | 数量为 0 时不显示（沿用同文件既有约定）；补 `title` 说明含义，避免数字含义不明 |
| 请求时机 | 仅具备 LIMS 角色时请求；进入稳定性板块时刷新，避免动作后角标滞后 |

**验证**：生产路径浏览器实测——侧栏角标 `8` / `2`（amber），与工作台「时间点执行结构」的 待取样 8 / 待检测 0 / 检测中 2 **完全一致**；`title` 分别为「待执行时间点（待取样 + 待检测）：8」「检测中时间点（待录入结果）：2」；控制台无新增错误；源码已无裸 `class="nav-badge"` 硬编码；离线契约 **321/321**。

**同步**：提交 `6e06155`，经 `deploy_lims_fix.sh` 同步生产（备份 `【内部备份标识已省略】`），清理 3 个残留 chunk 后远端 **86 文件与本地 `dist` md5 逐条一致**，`/hbos-lims/` 引用新 bundle `index-B0BcaDgw.js`。

**未处置（非本次缺陷）**：同文件 `const pendingCount = 0`（「待检任务看板」角标）亦为未接数据的桩，但 `v-if="pendingCount > 0"` 恒为假、不显示任何内容，不会误导；属既有的未完成项，按「不扩大范围」未改。

## 9. 本轮追加：业务检验结果与稳定性结果/趋势联动（2026-09-21）

Owner 已确认“样品登记选择稳定性取样即为稳定性检测样品”的联动方案，本轮在 R8J 已部署基线上完成实现，并于 Owner 授权后同步生产。

| 链路 | 实现口径 |
| --- | --- |
| 样品登记 | `HBOS Sample.stability_timepoint` 显式关联 `HBOS Stability Timepoint`；来源为“稳定性/稳定性取样”时服务端强制绑定，并校验时间点状态、稳定性产品编码、批号、来源标准、重复绑定与已有结果。 |
| 结果唯一来源 | 业务操作 `HBOS Test Result` 仍是唯一录入入口；提交、复核、批准、修订均调用 `sync_standard_test_result`，稳定性侧只保存带 `source_test_result` 的受控投影。 |
| 状态与趋势 | 投影状态镜像业务结果；批准时切换稳定性 `is_current=1` 与时间点项目指针，既有趋势接口的“已批准 + 当前生效”取数规则继续生效。 |
| 防重复 | 已绑定业务样品的时间点禁止在稳定性页面再次录入、提交、复核、批准、修订或作废；投影以业务结果 Link 幂等。 |
| 前端路径 | 样品登记选择“稳定性取样”后必须选择时间点；选项来自真实稳定性计划接口，并展示产品、批号、条件、时间点和单号。 |

基础联动实现阶段验证证据：离线契约 **326/326 通过**（含新增联动契约）；`npm run build`（含 `vue-tsc -b`）通过；`git diff --check` 通过。未做生产部署、未做真实站点数据写入，待 Owner 按“样品登记 → 生成任务 → 业务结果提交/复核/批准 → 稳定性结果与趋势”路径验收；本轮审查修复后的最终证据见 §10。

本轮追加涉及：`HBOS Sample` / `HBOS Stability Result` DocType 字段、`lims_service.py`、`stability_service.py`、`stability_contract.py`、`stability_guards.py`、样品控制器、`frontend/hbos-lims-web/src/views/SampleView.vue`、两份 API 契约和 R8J 离线测试。

## 10. 本轮审查反馈修复（2026-09-21）

本轮针对 Owner/Reviewer 提出的 2 项 P0、2 项 P1 及 2 项 P2 风险完成代码修复，并补齐 P0-5 的映射维护入口。Owner 已确认后按既有 `deploy_lims_fix.sh` 流程完成生产同步、`bench migrate`、缓存清理、服务重载和生产冒烟。

| 编号 | 修复方案 | 落地结果 |
| --- | --- | --- |
| P0-1 跨模块越权 | 业务结果在提交/复核/批准/修订前先执行稳定性同步预检；目标为“已批准”时，按 `HBOS Stability Result` 作用域校验审批角色，Reviewer-only 不得借业务侧批准稳定性结果。 | 预检失败发生在业务源记录变更前，拒绝并保留越权审计，不再出现“业务侧批准导致稳定性生效”。 |
| P0-4 修订批准崩溃 | `mark_superseded` 重新保存旧投影后，按名称重新加载旧记录，再写 `is_current=0`。 | 消除 Frappe `TimestampMismatchError`，旧版取代、新版批准和当前指针切换可继续完成。 |
| P1-2 SoD | 同步批准路径要求复核人存在且 `reviewer != approver`，同时复用稳定性批准角色作用域校验。 | 业务侧连续由同一人复核、批准时，稳定性投影不会被批准。 |
| P1-3 已取消时间点 | 同步预检锁定时间点并只允许“待检测 / 检测中 / 已完成”；已取消、已关闭等状态直接拒绝并独立审计。 | 源业务结果不会写入已取消时间点；预检审计与源事务分离，避免错误记录被回滚。 |
| P0-5 映射不可维护 | 新增 Manager/System Manager 服务方法、API 和稳定性主数据页面维护入口；提供业务检验项目真实主数据选择、重复映射校验、结果存在后冻结和审计。 | 首次同步前可由 LIMS Manager 配置 `base_test_item`；本轮不替业务方虚构 4 个实际映射。 |
| P2-6 整点锁死 | 稳定性页面人工录入改为按检验项目阻断：仅已被绑定业务样品覆盖的项目禁止重复录入，其余必检项目仍可人工录入。 | 业务样品与稳定性人工补录可在同一时间点按项目并存，避免时间点永久卡死。 |
| P2-7 并发重复绑定 | 登记服务在检查重复绑定前锁定 `HBOS Stability Timepoint` 行；事务内再次复核既有业务样品和稳定性结果。 | 并发登记同一时间点时串行化，后到请求收到重复绑定拒绝。未对可为空的 `stability_timepoint` 建裸唯一索引，避免所有非稳定性样品共用空值时互相冲突。 |
| P1-8 复核准入死锁 | 新增 `_assert_independent_approver_exists(reviewer)`：复核准入前按**业务与稳定性 `approve_result` 角色矩阵的交集**（排除 System Manager，不写死角色名单）查启用用户，除本次复核人外为空则拒绝复核。业务侧 `review_result` 显式传入 `reviewer=_user()`（前置校验早于 `result.reviewer` 赋值）。 | 消除永久卡死：业务 `approve_result` ∈ {Reviewer, Manager}、稳定性 `approve_result` ∈ {QA, QA Manager, Manager}，交集仅 Manager，叠加「批准人 ≠ 复核人」后**唯一可行组合是 Reviewer 复核 + Manager 批准**。此前 Manager 一旦复核，该记录既无人可批准（角色交集内无他人），也无法用 `revise_result` 回退（业务状态机不允许 `已复核 → 已提交`）。现改为一句话前置拒绝并给出可执行提示，且随角色矩阵变化自动放宽。 |

### 验证证据

- 后端本地全量契约回归：**334/334 通过**；生产发布脚本完整 pytest：**342/342 通过**。
- 前端：`vue-tsc -b && npm run build` 及生产 `VITE_BASE=/hbos-lims/ ... vite build` 均通过；构建仅保留既有大 chunk 提示，无编译错误；趋势摘要下拉控件宽度回归契约已覆盖。
- Python AST：`lims_service.py`、`stability_service.py`、R8J 契约测试文件全部解析通过。
- `git diff --check`：通过。
- 生产同步：Frappe `bench --site frontend migrate`、`clear-cache`、后端/前端/队列/调度器/WebSocket 重启及 nginx 配置重载均成功；生产备份为 `【内部备份标识已省略】`。
- 生产 HTTP 冒烟：`/hbos-lims` 稳定性及既有业务路径共 17 个页面/资源全部返回 **200**。
- 生产浏览器复测：结果录入与趋势页产品、检验项目下拉框及展开菜单均保持在趋势摘要卡片边界内，长文本按宽度省略显示。
- **实机逐项复测**（`frontend` site，非 Administrator 真实用户；由具备 Frappe bench / Docker CLI 的会话执行）：P0-1 Reviewer 批准业务结果 → 拒绝且业务停在「已复核」；P0-4 修订件 提交 → 复核 → 批准 **成功**，六步切换正确（旧版 `已批准→已修订`、`is_current` 1→0；新版 `已复核→已批准`、0→1、指针切换）；P1-2 同一人复核 + 批准 → SoD 拒绝；P1-3 已取消时间点同步 → 拒绝，无稳定性结果写入且拒绝独立入审计；P0-5 映射维护 Analyst 拒 / Manager 允 / 重复映射拒 / 已有结果后拒；P2-6 被业务样品覆盖的项目拒、未覆盖项目允；P1-8 Manager 复核 → **前置拒绝**（原为永久卡死）、Reviewer 复核 + Manager 批准 → 通过。全部用例结束后运行期一致性扫描 **0 违规**，测试数据与映射已还原至基线。

本轮追加涉及：`lims_service.py`、`stability_service.py`、`frontend/hbos-lims-web/src/api/stability.ts`、`frontend/hbos-lims-web/src/views/StabilityStudyView.vue`、`frontend/hbos-lims-web/src/styles/stability.scss`、`test_stability_r8j_contract.py`，以及本轮状态台账文件。
