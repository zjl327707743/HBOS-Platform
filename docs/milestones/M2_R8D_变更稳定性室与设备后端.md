# M2-R8D 稳定性后端：变更、稳定性室与设备

> 状态：**DONE / 待 Owner 审查**（离线契约 **311/311** 全量、实机端到端 **39/39**、R8B 回归 **40/40**、R8C 回归 **34/34**）
>
> 轮次：M2-R8D，工作分支 `m2-r8`
>
> 上游：M2-R8A（主数据 + 通知单 + 方案）、M2-R8B（样品 + 时间点）、M2-R8C（结果 + 报告）、R8G/R8H（前端已接 4 视图）
>
> 边界：**本轮只做后端**；「变更·稳定性室·设备」视图的前端接入另起一轮。方案拆轮表中 R8D 的「其余 5 张报表」以**只读接口**承载（数据源就绪，Script Report 物化与前端接入同轮做），见 §5

---

## 1. 本轮交付

| 交付物 | 内容 |
| --- | --- |
| DocType ×4 + 子表 ×1 | `HBOS Stability Change`（变更审批表）；`HBOS Stability Room Log`（温湿度记录，业务键 `room_date_period_key` unique）；`HBOS Stability Equipment`（设备台账）；`HBOS Stability Fault Ticket` + 子表 `HBOS Stability Fault Sample`（故障工单 + 受影响样品流水表） |
| 状态机 ×2 | `FLOW_STB_CHANGE` / `FLOW_STB_FAULT`（并入 `workflow_contract`；方案 8 条状态机至此全部落地） |
| 变更链 10 动作 | create / submit / review（按级别分流）/ approve_general（QAM 专属）/ approve_major（QP 专属）/ reject / cancel / implement（7.9 原子事务）/ assess / reopen（校验 supersedes） |
| 稳定性室 8 动作 | log_room_env / manage_equipment / open_fault_ticket / start_fault_handling / submit_fault_assessment / return_fault_handling / close_fault_ticket + only-read |
| 只读接口 ×5 | changes / change_detail / room_logs（超标筛选）/ equipments / fault_tickets（含子表） |
| scheduler 扩展 | 设备/校准/确认到期（≤30 天）+ 温湿度缺卡（工作日 × 班次，依 Holiday List）+ **运行期一致性扫描**（方案 8.6 四类不变式） |
| 审计 | `doc_events` 4 DocType 全量捕获；新增受控枚举 17 类（变更 8 + 温湿度 2 + 设备 1 + 故障 5 + 一致性异常 1） |
| 契约 | `stability_contract.py` 增 2 状态机 + 受控枚举 + `make_room_log_key`；`stability_guards.py` 增 4 组系统字段守卫与删除拦截常量 |

**命名系列**（不含 `#`）：`HBOS-STB-CHG-.YYYY.-` / `HBOS-STB-RML-.YYYY.-` / `HBOS-STB-EQP-` / `HBOS-STB-FLT-.YYYY.-`。

## 2. 关键实现口径

- **变更审批 SoD（方案 6.2 / S7）**：一般变更批准 `LIMS QA Manager` **专属（无 Manager 兜底）**；重大变更批准 `LIMS QP` 专属；`review_change` 按 `change_level` 分流（一般→待QA经理批准、重大→待QP批准）
- **7.9 变更实施落点**：`implement_change` 单一原子事务——按 `change_scope` 分派（涉方案→Protocol 新版本 version+1 + supersedes + 原版置已作废；涉通知单→新 Notice 草稿 version+1；涉条件与时间点→锁内 `_append_conditions_impl` 幂等仅新增；涉样品→拒绝并引导走 `register_stability_sample` 重新入箱），落点审计 + 置「已实施」同成同败
- **`append_conditions` 受控入口打通**：R8B 的「变更单未落地一律拒绝」守卫自动解除，前置 `已批准 且 change_scope ∈ {涉条件与时间点, 涉方案}` 不变
- **Room Log**：业务键 `{room}#{log_date}#{period}` unique + 应用层查重双保险；上下限从 Room 快照（只读）；`within_spec` 控制器判定；超标必填异常描述；**全状态禁删**（温湿度原始记录）
- **Equipment**：全状态禁删（用「停用」）；到期日供 scheduler 扫描；`last_fault_date` 由 `open_fault_ticket` 同事务回写
- **Fault Ticket**：`affected_samples` 子表由服务写入（流水表特例，LIMS 角色无 create/write）；`待处理` 可直接关闭（判定无影响），但**必须关联偏差或 CAPA**；三非终态均可关闭
- **运行期一致性扫描（8.6 / P2 rev12）**：scheduler 每日四类不变式（生效指针 / 流水对账 / 日期链 / 业务键唯一）→ 违反写审计 `一致性异常` + 进 summary `consistency_violations` 清单；**只检出告警、不自动修复**

## 3. 实施中发现并处置的方案缺口

| # | 缺口 | 处置 |
| --- | --- | --- |
| 1 | 方案 7.9「涉条件与时间点」落点要求 `_append_conditions_impl` 从变更单取**变更后新条件**，但 5.5.1 Change 字段表**无承载字段**（R8B 的 `_extra_conditions_of` 已按 `change.extra_conditions` 子表结构预留） | Change 挂**共享子表** `HBOS Stability Study Condition`（方案 5.8 已定其为 Notice/Protocol 共享子表，本处置扩为三处共享），**不新增 DocType，总数保持 14 主 + 8 子 = 22** |
| 2 | 方案 6.3.8 的 `handle_exception`（异常登记/关闭）无独立 DocType 承载，温湿度异常已由 `log_room_env` 的 `exception_desc`/`action_taken`/`deviation_ref`/`capa_ref` 字段组承载 | **不单独建动作**；异常处理由 Room Log 字段组 + Fault Ticket 承载，本表留档 |
| 3 | 5.6 拆轮表将「其余 5 张报表」分给 R8D；R8B 已交付 1 张（取样与检测计划看板） | 本轮交付 5 张报表的**只读数据源**（`get_stability_room_logs` 含超标筛选、`get_stability_equipments` 含到期日、`get_stability_fault_tickets`、`get_stability_changes`、scheduler summary 含设备到期/缺卡/一致性清单）；Script Report 物化与「变更·稳定性室·设备」前端视图接入同轮做（前端另起一轮） |

## 4. 实机验证证据（2026-09-20）

脚本：容器内 `/tmp/r8d_e2e.py`（venv 直连，非 Administrator 身份走全链）。

- 变更链：落点与对象不匹配拒绝 → 审核按级别分流 → Analyst 越权批准拒 → QAM 批准一般变更 → 重复批准拒（非法转移）✔
- 实施落点：`implement_change` 原子事务追加 4 个中间条件时间点（6→10）→ 未批准不可实施 ✔
- 后评估与重启：达标→已评估完成（终态）；重大变更 QP 专属（QA/QAM 越权均拒）；不达标→后评估不通过（终态）；`reopen_change` 校验新单 supersedes 指向（未指向拒、指向通过）✔
- 温湿度：在控建档 → 同房间同日同班次重复拒 → 超标 `within_spec=0` → 超标无异常描述拒 → 原始记录禁删 → 超标筛选可读 ✔
- 设备与故障：建档 → 台账禁删 → 工单待处理 → 受影响样品子表写入 → 未关联偏差/CAPA 拒 → Analyst 越权关闭拒 → Reviewer 直接关闭（P2-3）→ 处理中/待评估/退回处理/评估后关闭全转移 ✔
- 只读与扫描：变更台账 / 设备列表 / 故障列表含子表 / scheduler 设备到期 + 温湿度缺卡 + 一致性扫描三项全部就绪 ✔
- 审计：15 类 R8D 事件全部实机落地（变更 8 类 + 温湿度 2 + 设备 1 + 故障 5）✔
- **R8B 回归 40/40、R8C 回归 34/34**；验证残留 TEST 单据已清理

## 5. 未做 / 边界

- 「变更·稳定性室·设备」前端视图仍为演示数据，接入另起一轮（R8E 方案与原型已有）
- 5 张 Script Report 未物化（只读数据源已就绪，与前端接入同轮做）
- `_implement_new_sample` 定为引导式（涉样品落点拒绝并提示走 `register_stability_sample`）——新样品入箱涉及全量登记字段，不宜由变更单隐式创建
- 未部署生产

## 6. 涉及文件

- `hbos_lims/doctype/hbos_stability_change/`（新增，含 `extra_conditions` 共享子表字段）
- `hbos_lims/doctype/hbos_stability_room_log/` / `hbos_stability_equipment/` / `hbos_stability_fault_ticket/` / `hbos_stability_fault_sample/`（新增）
- `hbos_lims/stability_contract.py` / `stability_service.py` / `stability_guards.py` / `workflow_contract.py` / `hooks.py`
- `hbos_lims/doctype/hbos_audit_log/`（受控枚举 +17）
- `tests/test_stability_r8d_contract.py`（新增 23 项）
- DocType 落库：`bench --site frontend migrate` 已执行（4 主 + 1 子全部落库）
