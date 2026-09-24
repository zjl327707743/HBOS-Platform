# M2-R8C 稳定性后端：结果、趋势评估与报告

> 状态：**DONE / 待 Owner 审查**（离线契约 **288/288** 全量、实机端到端 **34/34**、R8B 回归 **40/40**）
>
> 轮次：M2-R8C，工作分支 `m2-r8`
>
> 上游：M2-R8A（主数据 + 通知单 + 方案）、M2-R8B（样品 + 时间点 + 计划）、M2-R8G/R8H（前端已接 4 视图）
>
> 边界：**本轮只做后端**；「结果录入与趋势」「报告与有效期」两视图的前端接入另起一轮（R8D 或另立前端轮）

---

## 1. 本轮交付

| 交付物 | 内容 |
| --- | --- |
| DocType ×2 | `HBOS Stability Result`（结果版本链 + 生效指针）；`HBOS Stability Report`（报告 + QA 判定有效期） |
| 状态机 ×2 | `FLOW_STB_RESULT` / `FLOW_STB_REPORT`（并入 `workflow_contract`） |
| 子表字段 | `Timepoint Item.current_result`（Link Result，行锁内维护，R8B 按前向兼容承诺由本轮补建） |
| 服务方法 | 结果 9 个（record / submit / review / return / approve / revise / void / mark_superseded / eval_trend）+ 报告 8 个（create / submit / review / approve / reject / void / 2 只读详情）+ 只读 4 个（results / result_detail / trend / reports）+ 外推助手 `get_stability_validity_advice` + 客户存量扫描 `get_stability_customer_scan` |
| 契约增强 | `stability_contract.py` +348 行：结果/报告状态机常量、`check_significant_change`（双套判定规则）、`trend_line`（最小二乘，**不含统计控制限**）、`advise_validity`（ICH Q1E 分支）、`make_report_period_key` / `check_report_scope`、`check_customer_code` |
| hooks | `HBOS Stability Result` / `HBOS Stability Report` 全量审计捕获；`Customer.validate` 注册 `validate_customer_code`（仅当已被稳定性专项报告引用时强制命名规范，不干扰非稳定性客户） |
| 角色注册 | 17 个新动作入 `ACTION_ROLES`；`SCOPED_ACTION_ROLES` 新增机制——R3 检验流程与稳定性结果的 4 个**同名动作**（submit/review/approve/revise_result）按 DocType 作用域分别授权，避免互相放宽 |

**命名系列**：`HBOS-STB-RES-.YYYY.-` / `HBOS-STB-RPT-.YYYY.-`（不含 `#`，沿用 R8G 口径）。

## 2. 关键实现口径

- **结果版本链**（方案 7.7）：`result_version_key = timepoint#item#revision_no` 唯一；`is_current` 生效指针 + `Timepoint Item.current_result` 归属一致性
- **六步原子切换**（方案 6.3.5 / 门禁 11、15）：`approve_result` 在 Timepoint 行锁内同事务完成——旧版「已批准→已修订」+ `is_current` 1→0、新版「已复核→已批准」+ `is_current` 0→1、回写指针、commit；`mark_superseded` 为系统内部子步骤（幂等、非公开入口）
- **修订不改旧版**（P0-1）：`revise_result` 仅新建草稿（`supersedes` 指向旧版），旧版保持「已批准 + is_current=1」直到新版批准
- **作废与重开**（门禁 19）：`void_result` 作废生效件时同事务清指针 + 按**必检项目粒度**判定重开——时间点「已完成」才调 `reopen_timepoint`，已「检测中」保持原状态仅记审计
- **显著变化判定**（方案 7.4）：按 `HBOS Stability Test Item` 配置驱动（相对变化超阈值 / 超规格限度 / 跳过）；基线优先级 ①同条件 0 月已批准 ②出厂全检 ③首点，**按储存条件隔离选取**
- **趋势图**（方案 7.5）：最小二乘趋势线；**不计算统计控制限**（QA 口径待确认前不展示，接口 note 明示）
- **有效期外推**（方案 7.6，ICH Q1E 简化分支）：建档时服务端计算 `proposed_validity_*` 并写依据；QA 批准时以 `final_validity_*` **判定**（外推助手只给建议，判定为独立动作）
- **报告防重键**（rev11~14）：`report_period_key` 含 `product_code#year#type#source_doctype#source_name#client_code#seq`，专项报告 `seq` 服务端分配 + 冲突重试（≤3 次）；**非专项报告 customer/client_code/seq 必须为空**（建档与提交双侧校验）
- **审计**：结果/报告全量 doc_events 捕获 + 业务埋点 15 类新事件（结果录入/提交/复核/退回/批准/修订/作废/被取代/生效结果作废/显著变化判定/趋势评估/报告四态/有效期判定），全部入 §8.1 受控枚举

## 3. 实施中发现并处置的缺陷

| # | 缺陷 | 处置 |
| --- | --- | --- |
| 1 | **六步切换漏持久化 `is_current`（实机发现）**：`approve_result` 第 (b) 步 `old.is_current = 0` 只赋值未保存，而 `mark_superseded` 用自己的副本落库了状态变更，产生「已修订 + `is_current=1`」第三态（违反门禁 11/15，趋势/报告会读到失效版本） | `mark_superseded` 落库后重读旧版并**显式保存** `is_current=0`；实机断言「不存在第三态」通过 |
| 2 | **非专项报告填客户仅被 Link 校验拦截（实机发现）**：`create_stability_report` 未调 `check_report_scope`，客户不存在时是 Frappe Link 校验报错，**真实存在但命名合规的客户会被放行**（违反 rev14 P2-2 键语义） | 建档入口补 `check_report_scope` 范围校验；实机验证：非专项报告填真实合规客户被明确拦截 |
| 3 | R8B 遗留——`Timepoint Item.current_result` 悬空 Link 未建 | 本轮建表时同步创建（R8B 主文档 §2 已留承诺） |

## 4. 实机验证证据（2026-09-18）

脚本：容器内 `/tmp/r8c_e2e.py`（venv 直连，非 Administrator 身份走全链）。

- 结果链：录入 → 草稿 v1 非生效 → 重复录入在途被拒 → 批准后指针回写 ✔
- 版本链：修订件草稿且旧版不变 → 修订号递增 + supersedes → 显著变化判定（基线 100 → 106，+6% ≥ 5% 阈值，同条件基线）→ 检测人自审/复核人自批 SoD 拦截 → 六步原子切换（旧 已修订/0、新 已批准/1、指针指向新版、无第三态）✔
- 作废重开：complete_testing 在全部必检项目批准后成功（R8B 前向守卫自动打通）→ 作废生效件清指针 → 多项目粒度重开回退「检测中」→ 其余项目结果不受影响 ✔
- 报告链：外推助手可读 → 建档写入外推建议 → 非专项报告填客户拦截（Link 校验 + 范围校验双证）→ 未审核批准拒 → 审核人自批拒 → 未填 QA 判定有效期拒 → 批准定有效期 → QA 越权作废拒 → QP 作废 ✔
- 越权/删除/只读：Analyst 越权 approve/void 拒 → 已批准结果禁删（方案 8.3）→ 结果台账/详情修订链/趋势接口（无控制限）/报告台账/客户存量扫描/scheduler 趋势逾期项 ✔
- **R8B 回归 40/40**（同文件改动后重跑）；验证残留 TEST 单据已清理

## 5. 未做 / 边界

- 前端「结果录入与趋势」「报告与有效期」两视图仍为演示数据，接入另起一轮
- `HBOS Stability Change`（R8D）未动：`append_conditions` 继续保持 R8B 的受控拒绝
- 趋势图统计控制限不实现（方案 7.5 口径待 QA 确认）
- 未部署生产

## 6. 涉及文件

- `hbos_lims/doctype/hbos_stability_result/`（新增）
- `hbos_lims/doctype/hbos_stability_report/`（新增）
- `hbos_lims/doctype/hbos_stability_timepoint_item/`（+`current_result`）
- `hbos_lims/stability_contract.py` / `stability_service.py` / `stability_guards.py` / `workflow_contract.py` / `hooks.py`
- `tests/test_stability_r8c_contract.py`（新增 42 项）；`tests/test_stability_r8b_contract.py`（+9 行前向兼容修正）
- DocType 落库：`bench --site frontend migrate` 已执行（上会话完成，本轮实机探查确认）
