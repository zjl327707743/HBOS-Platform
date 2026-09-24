# M2-R8A 稳定性主数据与通知单/方案：后端实现与实机验证

> 状态：**DONE / 待 Owner 审查**（实机验证 28/28、离线契约 199/199 全绿；实机流程与负向用例均已留证据）
>
> 轮次：M2-R8A（稳定性板块第一子轮），工作分支 `m2-r8`
>
> 上游依据：《M2_R8 稳定性管理板块开发方案》rev15 第 4/5/6/7/8 节；
> 启动门禁确认记录 `docs/milestones/M2_R8A_启动门禁确认包.md`（Owner 2026-09-16，11.3 的 7 项全部闭环）
>
> 业务依据：《稳定性管理》SOP-LC-1-00-019 **v9.0**（Owner 2026-09-16 确认已正式生效）

---

## 1. 本轮范围（方案 11.1 · R8A）

| 交付物 | 落地 |
| --- | --- |
| 主数据 4 | `HBOS Stability Product` / `Condition` / `Room` / `Test Item` |
| 记录一（考察通知单） | `HBOS Stability Notice` |
| 方案 | `HBOS Stability Protocol` |
| 子表 4 | `HBOS Stability Test Item Form` / `Batch` / `Study Condition` / `Protocol Item` |
| 状态机 2 | `FLOW_STB_NOTICE` / `FLOW_STB_PROTOCOL`（并入 `workflow_contract.FLOW_TRANSITIONS`） |
| 角色 2 | 新增 `LIMS QA Manager`（QA 经理，一般变更批准）/ `LIMS QP`（质量受权人，重大变更批准 / 方案与报告作废） |
| 冻结快照与版本链 | 批准时置 `snapshot_frozen=1`，快照字段此后只读；`version` + `supersedes` 承载版本链 |

**本轮不做**：Sample / Timepoint / Result / Report / Change / Room Log / Equipment / Fault Ticket（R8B~R8D）；
不做温湿度自动采集、仪器取数、GMP 合规电子签名（方案第十二节）。

---

## 2. 代码结构

| 文件 | 职责 |
| --- | --- |
| `hbos_lims/stability_contract.py` | 纯函数与常量（零 Frappe 依赖）：状态机、枚举、4.1 批次/条件规则、冻结快照字段、动作→转移表 |
| `hbos_lims/stability_guards.py` | 控制器层写入守卫：系统字段守卫、冻结快照守卫、删除拦截（含独立审计） |
| `hbos_lims/stability_service.py` | 业务服务（唯一合法写路径）：通知单/方案全链、SoD、越权与非法转移审计、只读聚合 |
| `hbos_lims/doctype/hbos_stability_*` | 6 主 + 4 子 DocType（JSON + 控制器） |
| `tests/test_stability_r8a_contract.py` | 离线契约测试（32 项） |

**权限口径（方案 8.6）**：6 个 LIMS 角色在 DocType 层一律**只读**（create/write/delete 全为 0），
所有写入只能经 `stability_service` —— 离线契约测试逐 DocType/角色断言该口径。

**状态与角色单一来源**：状态转移表只由 `stability_contract` 持有，`workflow_contract` 合并引用；
动作角色表只由 `workflow_contract.ACTION_ROLES` 持有，避免双源漂移。

---

## 3. 本轮修复的缺陷（实机验证中发现）

昨天（2026-09-17）实现完成但未做实机流程验证，本轮验证暴露并修复 4 项：

| # | 缺陷 | 影响 | 处置 |
| --- | --- | --- | --- |
| 1 | `HBOS Stability Protocol.test_method_ref` 的 `fieldtype` / `label` 写反（`fieldtype="检验标准操作规程"`，非法 fieldtype） | 非法 fieldtype 已落库，表单渲染异常 | 按方案 5.2.2 改为 `Data` + label「检验标准操作规程」；新增离线断言**全量字段 fieldtype 合法性 + Link 必须带 options** |
| 2 | `create_stability_notice` 缺 `extra_condition_reason` 入参，而 `submit_notice` 对 >2 条件强制要求该字段；叠加 8.6「DocType 层只读」后用户无法补填 | **>2 个条件的通知单一律无法提交**（影响因素类考察不可用） | 建档入口补齐该参数，并补注释说明「8.6 只读 ⇒ 必须建档时一次收齐」 |
| 3 | 业务埋点的审计 `log_type`（如「多条件复核」「通知单提出」）未登记进 `HBOS Audit Log.log_type` 受控枚举 | `register_review` 等动作**直接抛错不可用** | 按方案 8.1 把 R8A 的 9 个事件补入受控枚举；`review_protocol` 复用既有「复核」；新增离线断言**服务埋点事件必须落在枚举内** |
| 4 | `_check_action` 失败、状态机非法转移、删除尝试**都不写审计**，与方案 8.7 / 8.3 / 门禁 6、17 冲突 | 越权、SoD、非法转移、删除尝试**无痕** | `_check_action` 失败先 `_audit_commit` 再抛错；新增统一 `_reject()` 覆盖全部非法状态守卫；6 个主 DocType 补 `on_trash` 删除拦截（Notice：仅草稿/已驳回/已取消可删；Protocol：仅草稿可删；主数据一律禁删、改用 `is_active=0` 停用）；受控枚举补「删除拦截」 |

---

## 4. 实机验证证据（2026-09-18）

**环境**：site `frontend`，容器 `hbos-m0-r3a-*`，Frappe/ERPNext v16；
`bench --site frontend migrate` 已执行（10 个 DocType 全部落库）。
测试数据一律 `TEST-HBOS-M2-STB-*` 前缀（主数据在名内、单据在 `study_reason`/`purpose` 内，
因为命名系列由方案 5.8 固定为 `HBOS-STB-NOT/PRO-.YYYY.-####`）。

### 4.1 正向全链（通知单 → 方案）

| 步骤 | 结果 |
| --- | --- |
| 建档（3 条件 + 补充原因 + 3 批） | 草稿 |
| `register_review` → `submit_notice` | 待QC经理确认 |
| `confirm_notice_qc`（QC 线） | 待批准 |
| `approve_notice`（异人） | 已批准 + `snapshot_frozen=1` |
| `create_stability_protocol` → `submit_protocol` | 待QA审核 |
| `review_protocol` → `approve_protocol`（异人） | 已批准 |
| `void_protocol`（QP） | 已作废 |
| `close_notice`（无未终态时间点） | 已关闭 |

### 4.2 负向用例

| 用例 | 结果 |
| --- | --- |
| 新产品类仅 2 批 | 拒（4.1 批次下限） |
| 3 条件缺补充原因 / 未 `register_review` 即提交 | 拒 |
| Analyst 越权 `confirm_notice_qc` | 拒 + 越权审计 |
| 申请人自批 `approve_notice` / QA 审核人自批 `approve_protocol` | 拒 + SoD 审计（独立提交，回滚后仍在） |
| 批准后修改冻结快照字段 | 拒（7.7） |
| 已批准通知单重复提交 | 拒 + 审计 |
| QA 越权 `void_protocol` | 拒 + 越权审计 |
| 年度持续稳定性考察类建方案单 | 拒（4.2.5） |
| 删除已关闭通知单 / 删除主数据 | 拒 + 删除拦截审计；草稿可删 |

**结果：实机 28/28 通过；离线契约 199/199 全绿**（其中稳定性 R8A 契约 28 项，含本轮新增的 2 项回归守卫）。
审计事件分布实测含 SoD 拦截 / 越权拦截 / 删除拦截 / 多条件复核 / 通知单提出·确认·批准·取消·关闭 / 方案起草提交·批准·作废 等。

### 4.3 跨轮验收门禁（方案 11.2）在 R8A 的覆盖

| 门禁 | R8A 覆盖 |
| --- | --- |
| 1 唯一性与并发 | 主数据唯一键（`product_code`/`condition_code`/`room_code`/`item_code`）；并发用例属 R8B |
| 2 批准后修改拦截与版本快照 | ✅ 冻结字段只读负向用例 |
| 6 审计不可绕过 | ✅ 越权 / SoD / 非法转移 / 删除拦截均留痕（负向用例） |
| 10 动作矩阵与状态机全一致 | ✅ 离线断言：每处转移都有动作、动作不越出转移表、角色逐行对齐 6.3.1/6.3.2 |
| 16 禁止绕过业务服务 | ✅ DocType 层 LIMS 角色全只读；`_check_action` + 系统字段守卫 + 冻结守卫 |
| 17 违规审计独立持久化 | ✅ `_audit_commit` 先落审计再抛错 |

---

## 5. 本轮未做 / 待后续

- **前端未接真实 API**：R8F 的稳定性 7 视图仍为演示数据。R8A 对应的「稳定性工作台」「考察申请与方案」
  两视图的真实接入待 R8B 落地后按方案 §8 顺序统一推进。
- **合规审计日志前端筛选项未含新事件类型**：`AuditLogView.vue` 的 `LOG_TYPES` 为写死常量，
  新事件行可正常显示与筛选值以外的浏览，但下拉筛选器未包含新增类型（前端范畴，随前端接入轮处理）。
- **R8B~R8D 未启动**：Sample / Timepoint / Result / Report / Change / Room Log / Equipment / Fault Ticket、
  样品标签 Print Format、6 报表、scheduler 一致性扫描等。
- **违规审计的 R7 侧同源问题**：`retention_service._check_action` 同样不在角色不足时留痕；
  R7 已 DEPLOYED 收口，本轮**未改动 R7**，仅登记为待评估项。

---

## 6. 相关文件

- 方案：`docs/milestones/M2_R8_稳定性管理板块开发方案.md`
- 启动门禁确认包：`docs/milestones/M2_R8A_启动门禁确认包.md`
- 前端（演示数据）：`docs/milestones/M2_R8F_稳定性板块前端Vue复刻与生产部署.md`
