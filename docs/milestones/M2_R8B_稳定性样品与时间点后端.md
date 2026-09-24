# M2-R8B 稳定性后端：样品、时间点与取样检测计划

> 状态：**DONE / 待 Owner 审查**（离线契约 **244/244**、实机端到端 **40/40**、补充验证 **10/10**）
>
> 轮次：M2-R8B，工作分支 `m2-r8`
>
> 上游：M2-R8A（主数据 + 通知单 + 方案后端）、M2-R8G（前端接入真实 API）
>
> 边界：**本轮只做后端 + 标签 + 报表**；「样品入箱与台账」「取样与检测计划」两视图的前端接入另起一轮
>
> **后续进展（M2-R8H，2026-09-18）**：本轮交付的后端已由 **M2-R8H** 接入「样品入箱与台账」与「取样与检测计划」两个视图（读 + 写全接、按角色显隐），并补了跨时间点延期列表接口与 schedule 的三层日期列。见 `docs/milestones/M2_R8H_稳定性样品与计划前端接入.md`。
>
> **后续进展（M2-R8C，2026-09-18）**：本轮的 Result 前向兼容守卫已由 **M2-R8C** 全部打通（`complete_testing` 在全部必检项目批准后放行、`current_result` 补建并纳入六步切换维护、`Timepoint Item` 增加生效结果指针）。见 `docs/milestones/M2_R8C_稳定性结果与报告后端.md`。

---

## 1. 本轮交付

| 交付物 | 内容 |
| --- | --- |
| DocType ×5 | `HBOS Stability Sample` + `Sample Log`（子）；`HBOS Stability Timepoint` + `Timepoint Item` + `Timepoint Delay`（子） |
| 状态机 ×3 | `FLOW_STB_SAMPLE` / `FLOW_STB_TIMEPOINT` / `FLOW_STB_TIMEPOINT_DELAY`（并入 `workflow_contract`） |
| 服务方法 | 样品 9 个 + 时间点 12 个 + 4 只读接口 + `scheduler_scan` |
| 标签 | Print Format「HBOS 稳定性样品标签」（附件一电子化） |
| 报表 | Script Report「取样与检测计划看板」（方案 5.6 第 2 项，**本表为唯一交付轮**） |
| scheduler | `hooks.py` 既有 `"30 0 * * *"` 条目并列追加 `stability_service.scheduler_scan` |

**命名系列**（沿用 R8G 口径，不含 `#`）：`HBOS-STB-SMP-.YYYY.-` / `HBOS-STB-TPT-.YYYY.-`。

## 2. 关键实现口径

- **单一写路径**：`current_qty` 只由 入箱 / 取样出库 / 返还 / 销毁 / 手动调整 五个方法变更，每次写 `Sample Log` 流水
- **四步锁协议 + 锁顺序**：无锁校验 → `SELECT … FOR UPDATE` → 锁内复核 → 写入+流水+commit；同事务需两把锁时**固定 Sample → Timepoint**（方案 7.8）
- **时间点生成**（方案 7.1）：入箱登记成功后自动触发（**登记先提交**，生成失败不回滚登记，写 `时间点生成失败` 审计 + 样品上置 `timepoint_gen_error` 告警标记，可手动重跑）；锁内按 `sample_cond_point_key` **幂等仅新增**
- **延期**（方案 7.3）：取样/检测分离；同一 `delay_type` 无在途；日期链**四段全链校验**；`apply_by ≠ approver_by`（SoD）；禁止批准日期倒退；有效截止日按 `approve_at` 降序取最后一条已批准
- **逾期纯派生**（方案 8.4）：不进 `status` 枚举、不改单据状态；看板与 scheduler 用 `effective_due_date` 判定
- **权限**：5 张表的 LIMS 角色一律只读（`Sample Log` / `Timepoint Delay` 属「服务专用写入」，不授予任何角色权限）；系统字段 `read_only` + 控制器 `validate` 守卫

### Result（R8C）依赖的前向兼容守卫

`HBOS Stability Result` 属 R8C。本轮按下述方式落地（**正确判定，非桩**）：

| 位置 | 本轮行为 |
| --- | --- |
| `complete_testing` 前置「全部必检项目均有已批准 Result」 | 按 Result DocType/字段存在性取值，未落地时视为「无已批准结果」⇒ 拒绝。实机验证确认：无结果时被拒并列出缺结果的项目 |
| `reopen_timepoint` | 已实现并登记（系统动作，角色豁免）；守卫「仅当 status=已完成 才调用」，本轮无公开调用方，由 R8C 的 `void_result` 同事务调用 |
| `import_zero_month_result` | 校验 `is_zero_month=1` 且来源 ∈ {出厂全检, 委外} → 待取样 → 待检测 + 写 `0 月数据豁免校验` 审计（含来源单据）；**Result 落库与 `baseline_*` 字段留 R8C**（字段在 Result 上） |
| `cancel_timepoint` 前置「已有已批准 Result 须先全部作废 / 无在途 Result」 | 同上按 DocType 存在性守卫 |
| `append_conditions` | 受控入口；`HBOS Stability Change` 属 R8D，未落地时一律拒绝；`_append_conditions_impl` 已备好供 R8D 的 `implement_change` 同事务调用（**已兑现（M2-R8D，2026-09-20）**：`implement_change` 7.9 原子事务与受控入口均已打通，实机验证追加 4 时间点成功。见 `docs/milestones/M2_R8D_变更稳定性室与设备后端.md`） |

**未建 `Timepoint Item.current_result`**：其 Link 目标 `HBOS Stability Result` 属 R8C，
按 R8A 先例（Room 不 Link 到 R8D 的 Equipment）本轮不建悬空 Link，由 R8C 补。
（**已兑现（M2-R8C，2026-09-18）**：`current_result` 字段随 R8C 建表补建，六步原子切换在 Timepoint 行锁内维护该指针。见 `docs/milestones/M2_R8C_稳定性结果与报告后端.md`。）

## 3. 实施中发现并处置的四项方案缺口

| # | 缺口 | 处置 |
| --- | --- | --- |
| 1 | §4.1/§6.3.3 要求强校验「送样日期距**全检样送样日期** ≤ 3 周」，但 §5.3.1 字段表**无承载字段** | Sample 增 `send_date`（送样日期）与 `full_test_sample_date`（全检样送样日期），`register_stability_sample` 校验 `send_date ≤ full_test_sample_date + 21 天`（实机负向验证通过） |
| 2 | §7.3 说委外检测窗口 `outsourced_test_window_days`「可配置、留空=不限制」，但**未定义存放位置** | 落在 `HBOS Stability Product`（该单已有 `is_outsource`）；委外且留空 ⇒ 检测侧不做上限拦截 |
| 3 | §6.3.4 给 `complete_sampling` 定的审计事件「取样完成」**不在 §8.1 受控枚举内**（方案自身不一致） | 按 6.3.4 补入枚举；并**全量对差** 6.3.3/6.3.4 的事件列与枚举，确认无其他遗漏 |
| 4 | §5.6 指定标签目录为 `print_format/hbos_stability_sample/`，但 Frappe 标准 Print Format **按 scrub(格式名) 定位模板**（实测报 `No template found at .../hbos_稳定性样品标签/...`） | 目录改名为 `hbos_稳定性样品标签`（与仓库既有中文报表目录 `留样台账` 等一致） |

## 4. 标签尺寸结论（方案第十五节待确认第 11 项）

**读了附件一原件**（`【本地私有路径已省略】`）：
**原件未定义标签物理尺寸**——它是一张 A4 页面上的表格（页边距 2.5cm，表格内容宽 4684 twips ≈ **82.6mm**）；
文中出现的 `-31115 / 41275` 是内嵌小图标的**锚点偏移**（该图 7.62×7.3mm），不是标签尺寸。

**本轮做法**：内容与字段严格对齐附件一（品名 / 批号 / 留样数量及号码 / 留样位号 /
储存人-复核人 / 储存条件 / 储存日期 + 公司中英文名 + 标题 + 编码）；尺寸取**内容宽 82.6mm × 55mm**，
并**集中在模板一处**（`.stb-label` 的 `width/min-height`），实物规格确认后一行即可改。
**待确认第 11 项仍开放**：待 Owner 提供实物规格。

## 5. 实机验证证据（2026-09-18）

### 5.1 离线契约 **244/244**

新增 `test_stability_r8b_contract.py`（41 项）：5 DocType 契约、3 条状态机、
**门禁 10 全流程覆盖**（遍历稳定性全部流程断言「每处转移都有动作 / 动作不超出转移表」）、
时间点生成规则、延期算法与日期链、**门禁 5 时间边界**、0 月豁免。

> 顺带修正 R8A 契约测试里审计事件扫描的**正则缺陷**（首参为常量名时匹配不到，导致该守卫实际只校验了 12/40 个埋点）。

### 5.2 实机端到端 **40/40**

入箱登记 → 自动生成时间点（10 个）→ 重跑幂等；取样扣减/返还回补/流水完整；
处置四件套（进入待处置→快照→取消回退→销毁→结存归零）；超期进箱强制评估四件套；
送样 3 周校验；0 月免取样；时间点流转与取消；延期申请→批准→驳回（含日期链与 SoD 负向）；
越权（Analyst/Reviewer/QA/QP 四种身份）；4 个只读接口；scheduler 扫描。

### 5.3 补充验证 **10/10**

- 报表「取样与检测计划看板」渲染（18 列 / 20 行）与按执行状态筛选
- 标签 Print Format 渲染，含附件一全部关键字段，尺寸集中在模板一处
- **门禁 16①**：非特权用户表单 `save()` 改 `status` / `plan_test_date` **被拒**
- **门禁 1**：重复 `sample_cond_point_key` **被 DB 唯一约束拒绝**（`IntegrityError 1062`）
- **门禁 16③**：`frappe.db.set_value` 低层直写**按设计不被 validate 拦截**，但其后果**可被流水对账检出**

## 6. 未做 / 边界

- **不做前端**：两个视图的前端接入另起一轮（R8H）
- **不做** Result / Report / Change / Room Log / Equipment / Fault（R8C/R8D）
- scheduler 未实现设备校准、温湿度缺卡、趋势评估逾期的扫描项（R8C/R8D，**本轮不占位**）
- 未部署生产；未改动 R7 代码；未改 R8A 既有方法签名

## 7. 涉及文件

**新增**
- `doctype/hbos_stability_sample/`、`hbos_stability_sample_log/`、`hbos_stability_timepoint/`、
  `hbos_stability_timepoint_item/`、`hbos_stability_timepoint_delay/`
- `print_format/hbos_稳定性样品标签/`
- `report/取样与检测计划看板/`
- `tests/test_stability_r8b_contract.py`

**修改**
- `stability_contract.py`（+2 状态机与延期机、+日期/延期/生成纯函数）
- `stability_guards.py`（+样品/时间点系统字段集与删除拦截集）
- `stability_service.py`（+21 动作、+4 只读、+scheduler_scan）
- `workflow_contract.py`（+3 流程、+22 动作角色）
- `doctype/hbos_audit_log/hbos_audit_log.json`（+23 审计事件）
- `doctype/hbos_stability_product/hbos_stability_product.json`（+`outsourced_test_window_days`）
- `hooks.py`（+2 张单的审计捕获、scheduler 追加）
- `tests/test_stability_r8a_contract.py`（修正审计事件扫描正则）
