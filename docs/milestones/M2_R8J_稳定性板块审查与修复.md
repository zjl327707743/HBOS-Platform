# M2-R8J 稳定性板块前后端审查与缺陷修复

> 状态：**DONE / 待 Owner 审查**（离线 311/311、前端 `vue-tsc` 0 错误 + build 成功、实机修复验证 15/16 → 补测 5/5、负向回归 11/11、浏览器真实会话读写全链）
>
> 轮次：M2-R8J（R8 板块整体交付后的独立审查与修复轮），工作分支 `m2-r8`
>
> 上游：M2-R8A~R8D（后端）、R8G/R8H/R8I（前端 7 视图接入真实 API）
>
> 边界：**只做审查与缺陷修复**——不新增功能、不改方案口径。审查对象为稳定性板块全部后端（`stability_service.py` 4306 行 / 22 DocType / 8 状态机 / 6 报表）与前端（7 视图 + `api/stability.ts`）

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

**但发现 3 项 P1 + 2 项 P2 缺陷（均已修复，见 §2），其中 2 项造成业务链断裂。**

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

- **离线契约测试**：**311/311 通过**（`PYTHONPATH=apps/hb_lims_app python3 -m unittest discover -s apps/hb_lims_app/tests`）
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

## 4. 未做 / 边界

- **未修 P3 加固项**（已识别、未处置，供后续轮次评估）：
  1. `Condition` / `Product` / `Room` / `Test Item` 四张主数据 `allow_rename=1`，而文档名即业务编码且参与 `report_period_key` / `sample_cond_point_key` 等**字符串键**（改名不会同步已落库的键）→ 键漂移风险
  2. `current_result`（子表 `Timepoint Item`）仅字段级 `read_only`，无控制器守卫、不在任何 `*_SYSTEM_FIELDS` 元组
  3. 运行期一致性扫描的四类不变式**不含**「Timepoint.status ↔ 结果集一致性」，故低层 `frappe.db.set_value` 直改 status 不被检出（实测扫描返回 `[]`）
  4. `ACTION_ROLES` 为前后端两份手工副本，无一致性测试；`complete_testing` 曾因此漂移（本轮已随 P1-3 移除前端条目）
  5. Result / Report / Ops 三视图 loader 缺 `catch`，`onMounted` 内 `await` 会形成未处理拒绝并静默半加载
  6. `StbGateBanner` 默认 `mode:'demo'` 且保留 `TEST-HBOS-M2-STB-*` 文案（7 视图均显式传 `live`，分支不可达）；`demo/stabilityDemo.ts` 仍置于 `src/demo/`
  7. `equipment_name` 标签为「设备名称」实为设备**类型**枚举（方案字段表即如此，属标签语义问题）
- **未部署生产**：`/hbos-lims` 仍为 R8F 旧前端；本轮改动未提交、未同步生产
- 前端审计日志筛选下拉 `AuditLogView.LOG_TYPES` 未收录稳定性板块事件类型（**既有缺口**，非本轮引入，故未扩大范围）

## 5. 涉及文件

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
