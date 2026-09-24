# M2-R8A / M2-R8B 启动门禁确认包

> 状态：**✅ 已全部确认，R8A 已启动**（Owner 2026-09-16 逐项拍板）
>
> 用途：方案第 11.3 节《R8A 启动前置确认门禁》共 7 项，其中第 3 项（工作分支 `m2-r8`）、
> 第 6 项（电子签名路线 ①）已由 Owner 2026-09-15 决策闭环。本包对**剩余 5 项**给出
> 建议值与依据，Owner 2026-09-16 已逐条确认，**门禁 7 项全部闭环，R8A 启动**。
>
> 关联：方案 `docs/milestones/M2_R8_稳定性管理板块开发方案.md` 第 11.3 节 / 第七节 / 5.8 节 / 6.2 节。

---

## 0. 确认结论（Owner 2026-09-16）

| # | 确认项 | 结论 |
| --- | --- | --- |
| 11.3-1 | v9.0 是否正式生效 | **已正式生效** → 系统按 v9.0 实现 |
| 11.3-2 | 角色身份映射 | **采纳方案 6.2 + 新增 `LIMS QP` 与 `LIMS QA Manager`**；**人员权限、身份与群组管理后续统一设置**（本轮只做角色结构性创建，不做用户归属分配） |
| 11.3-4 | 取样延期 10% 基数 | **甲**：`min(ROUND_HALF_UP(时间点值折算天数 × 10%), 15)` |
| 11.3-5 | DocType 清单 | **采纳方案 5.8**：14 主 + 8 子 = 22 |
| 11.3-7 | 期限审批口径 | ① **需审批**（授权使用政策宽容期须经批准）② 委外窗口 **允许留空 = 不限制** |

**R8A 启动前置门禁 7/7 全部闭环**（第 3、6 项 2026-09-15 已闭环）。

---

## 1. 确认项汇总

| # | 确认项 | 建议 | 阻塞范围 | 状态 |
| --- | --- | --- | --- | --- |
| 11.3-1 | v9.0 是否正式生效 | 按 v9.0 实现，关键口径做成可配置以吸收版本风险 | R8A / R8B | ✅ 已确认：已生效，按 v9.0 实现 |
| 11.3-2 | 角色身份映射 | 采纳方案 6.2 表 + 新增 `LIMS QP` 与 `LIMS QA Manager` | R8A | ✅ 已确认（2026-09-16） |
| 11.3-4 | 取样延期 10% 基数口径 | 按方案 7.3 公式：时间点值折算天数 × 10%，上限 15 天 | R8B | ✅ 已确认：采甲 |
| 11.3-5 | DocType 清单核对 | 采纳方案 5.8：14 主 + 8 子 = 22 | R8A / R8B | ✅ 已确认：采纳 |
| 11.3-7 | 期限审批口径 | ① 区间内需审批 ② 委外窗口允许为空=不限制 | R8B | ✅ 已确认：①需审批 ②可留空 |

---

## 2. 逐项详情

### 11.3-1 v9.0 是否正式生效 → 建议：按 v9.0 实现

**规程现状**（方案 2.2 疑点 2）：新版 `SOP-LC-1-00-019` 变更历史 9.0 条填"见封面页"，
但封面页无生效日期，无法判定 v9.0 是否已生效。

**建议**：**按 v9.0 内容实现**，理由与风险控制：

1. 方案全文（第四节全部业务规则、第七节全部算法）**已按 v9.0 展开**，v8.0 仅作差异基线；
   Owner 2026-09-15 提供该套文件时即明确"新版为主"。
2. 方案在设计上已把**最可能变动的口径做了配置化**，把版本风险吸收掉：
   - 显著变化判定（基线口径 / 5% 公式 / 非数值处理）→ 配置在 `HBOS Stability Test Item`（方案 7.4）
   - 委外检测窗口 `outsourced_test_window_days` → 可配置，允许为空
   - 考察条件、时间点、房间上限 → 均为主数据，不写死在代码
3. 若 v9.0 最终未生效而回到 v8.0，需回改的差异点（方案 2.1 差异基线）：
   取样延期 30 天→10%/15 天、检测延期 15 天→30 天、考察用量"新产品 2 倍"删除、
   加速频率、留样类目（属 R7）。**多数落在 R8B 的延期算法，属可局部回改范围。**

**需 Owner 确认**：v9.0 的生效状态；若暂无法确认，是否授权**按 v9.0 实现并在
v9.0 生效状态明确后按需开变更轮微调**。

---

### 11.3-2 角色身份映射 → ✅ Owner 2026-09-16 已确认

**确认内容**：采纳方案 §6.2 映射表，并**新增两个角色**：

| 规程身份 | 系统角色 |
| --- | --- |
| QC 稳定性管理员 / 取样人 / 检测人 / 储存人 / QA 申请人 | `LIMS Analyst` |
| QC 主管 / QC 经理 / QC 资源管理员 | `LIMS Reviewer` |
| QA 审核人 | `LIMS QA` |
| **QA 经理**（一般变更批准） | **`LIMS QA Manager`（新增）** |
| 质量管理负责人 QM（超方案取样批准、报告批准） | `LIMS Manager` |
| **质量受权人 QP**（重大变更批准） | **`LIMS QP`（新增）** |
| 注册人员（>2 条件复核） | `LIMS QA`（先），视需要再新增 |
| 研发部门 | `LIMS Analyst`（先），视需要再新增 |

**含义**：QM 与 QP **不是**同一自然人，QA 经理**不能**由 QA 审核人兼任——
两个新角色在 `after_migrate` 幂等创建（成本与 R7 新增 `LIMS QA` 相同），
6.3 动作矩阵按 8 个角色列落地。

**待 Owner 补充**：上述"注册人员""研发部门"两行的**实际人员归属**，若不补充则按
建议值（先挂 `LIMS QA` / `LIMS Analyst`）落地，后续按 6.2 表调整。

---

### 11.3-4 取样延期 10% 的基数口径 → 建议：按方案 7.3 公式

**规程原文**（新版 4.3.1）：取样延期"≤ 考察日期的 10% 且 ≤15 天"。"考察日期"的基数
有两种读法，需 QC/QA 定：

| 读法 | 公式 | 1 月 | 3 月 | 6 月 | 12 月 | 影响因素 5 天 |
| --- | --- | --- | --- | --- | --- | --- |
| **甲（建议，方案 7.3）**：按**该时间点**的考察日期折算天数取 10% | `min(ROUND_HALF_UP(值折算天数 × 10%), 15)` | 3 天 | 9 天 | 15 天（封顶） | 15 天（封顶） | 1 天 |
| 乙：按**研究总周期**取 10%（再封顶 15 天） | `min(ROUND_HALF_UP(总周期天数 × 10%), 15)` | 15 天 | 15 天 | 15 天 | 15 天 | 1 天 |

**建议采甲**，理由：甲能按时间点远近给出差异化宽容度（早期时间点严格、晚期宽松），
与"越往后数据越稳定、取样窗口可略宽"的实践经验一致；乙会让所有 **≥6 月的时间点
一律顶到 15 天**，10% 规则实际失效，只剩 15 天单独起作用。

**实现细节**（无论采甲采乙均适用）：
- 单位换算：`月 × 30 天`；
- 取整：`ROUND_HALF_UP`（显式，禁银行家舍入）——影响因素 5 天 × 10% = 0.5 取 **1 天**；
- 封顶：`≤ 15 天`；
- 检测延期的 30 天窗口**锚定计划检测日期**，不随取样延期顺延。

---

### 11.3-5 DocType 清单核对 → 建议：采纳方案 5.8

**需逐项核对 22 个 DocType 的名称与父级关系**（方案 5.8 为唯一计数依据）：

**主 DocType（14）**

| # | 名称 | 角色 | 命名规则 |
| --- | --- | --- | --- |
| 1 | HBOS Stability Product | 主数据 | `field:product_code` |
| 2 | HBOS Stability Condition | 主数据 | `field:condition_code` |
| 3 | HBOS Stability Room | 主数据 | `field:room_code` |
| 4 | HBOS Stability Test Item | 主数据 | `field:item_code` |
| 5 | HBOS Stability Notice | 记录一（考察通知单） | `HBOS-STB-NOT-.YYYY.-` |
| 6 | HBOS Stability Protocol | 方案 | `HBOS-STB-PRO-.YYYY.-` |
| 7 | HBOS Stability Sample | 记录二（存放清单） | `HBOS-STB-SMP-.YYYY.-` |
| 8 | HBOS Stability Timepoint | 附件二（独立主） | `HBOS-STB-TPT-.YYYY.-` |
| 9 | HBOS Stability Result | 结果 | `HBOS-STB-RES-.YYYY.-` |
| 10 | HBOS Stability Report | 报告 | `HBOS-STB-RPT-.YYYY.-` |
| 11 | HBOS Stability Change | 记录三（变更审批表） | `HBOS-STB-CHG-.YYYY.-` |
| 12 | HBOS Stability Room Log | 记录四（温湿度记录） | `HBOS-STB-RML-.YYYY.-` |
| 13 | HBOS Stability Equipment | 设备台账 | `HBOS-STB-EQP-` |
| 14 | HBOS Stability Fault Ticket | 故障工单 | `HBOS-STB-FLT-.YYYY.-` |

> **命名系列更正（M2-R8G，2026-09-18）**：上表原列的 `-####` / `-#####` 写法在本版
> Frappe 下**不可用**——`set_name_by_naming_series()` 会对系列无条件追加 `.#####`，
> 系列自带 `#` 会生成 `HBOS-STB-NOT-2026-####00009` 之类的畸形单号（R8A 实际发生）。
> 已按上文更正为**不含 `#`、以 `-` 结尾**的写法（与既有 `HBOS-SMP-.YYYY.-` 同一约定）。
> **Owner 2026-09-16 确认的是 DocType 清单与父级关系，命名写法属实现细节，此处更正不影响确认结论。**

**子表（8）**

| # | 名称 | 父 DocType |
| --- | --- | --- |
| 1 | HBOS Stability Test Item Form（适用剂型） | Test Item |
| 2 | HBOS Stability Batch（批次明细） | Notice / Protocol（共享） |
| 3 | HBOS Stability Study Condition（试验条件明细） | Notice / Protocol（共享） |
| 4 | HBOS Stability Protocol Item（考察项目明细） | Protocol |
| 5 | HBOS Stability Sample Log（取样/返还/销毁流水） | Sample |
| 6 | HBOS Stability Timepoint Item（时间点项目 + 生效指针） | Timepoint |
| 7 | HBOS Stability Timepoint Delay（延期申请与审批） | Timepoint |
| 8 | HBOS Stability Fault Sample（故障受影响样品） | Fault Ticket |

**另有**（不建 DocType）：1 个 Print Format（`hbos_stability_sample` 样品标签）
+ 6 个 Script Report。**合计 14 主 + 8 子 = 22 DocType。**

**R8A + R8B 本轮实际创建的**：

| 轮次 | 新建 DocType |
| --- | --- |
| R8A | 主数据 4（#1–4）+ Notice（#5）+ Protocol（#6）+ 子表 4（Test Item Form / Batch / Study Condition / Protocol Item） |
| R8B | Sample（#7）+ Sample Log + Timepoint（#8）+ Timepoint Item + Timepoint Delay |

其余（Result / Report / Change / Room Log / Equipment / Fault Ticket / Fault Sample）
留 R8C / R8D。

---

### 11.3-7 期限审批口径 → 建议：①② 均取方案默认

**① 落在 `(planned_due_date, policy_latest_due_date]` 区间内是否必须审批？**

| 选项 | 含义 | 影响 |
| --- | --- | --- |
| **甲（方案默认，建议）** | **需审批**——授权使用政策宽容期须经 QA Manager 批准 | 延期走 `apply_delay → approve_delay` 完整流程，有效期按 `effective_due_date` 判定 |
| 乙 | **自动允许**——10%/15 天/30 天属规程自动允许范围，仅需记录原因 | 简化为"记录 + 审计"，不建审批链；延期子表仍保留但状态直接置已批准 |

**建议采甲**：新乡海滨本次是首次上稳定性模块，审批留痕比事后追认更稳；且方案 §7.3 已按甲
完成全部设计（延期状态机、SoD、日期链校验），改乙需回改 6.3 动作矩阵与 11.2 门禁 18。

**② 委外检测窗口 `outsourced_test_window_days` 是否允许配置为"不限制"（留空）？**

| 选项 | 含义 |
| --- | --- |
| **甲（方案默认，建议）** | **允许留空 = 不限制**——规程 4.3.2"委外检测项目视具体情况定"即此 |
| 乙 | **不允许留空**——必须填天数（默认 30 天） |

**建议采甲**：与规程原文一致；留空时委外项目只用取样侧政策上限判定，
检测侧不做 30 天窗口拦截。

---

## 3. 确认后即启动的 R8A + R8B 范围

Owner 已选定**先交付 R8A + R8B**（方案 11.1 推荐路径：直接替代纸质时间表与取样计划）。

| 轮次 | 交付物 | 对应前端视图 |
| --- | --- | --- |
| **R8A** | 4 主数据（Product / Condition / Room / Test Item）+ Notice + Protocol（含 Batch / Study Condition / Protocol Item 子表）+ `FLOW_STB_NOTICE` / `FLOW_STB_PROTOCOL` + 新增 `LIMS QP` / `LIMS QA Manager` 角色 + 批准后冻结快照与版本链 | 稳定性工作台、考察申请与方案 |
| **R8B** | Sample(+Sample Log) + Timepoint（独立主，含 Timepoint Item / Timepoint Delay）+ 样品标签 Print Format + 时间点自动生成 + 取样与检测计划看板报表 + `FLOW_STB_SAMPLE` / `FLOW_STB_TIMEPOINT` + 延期审批 + 0 月免取样导入 | 样品入箱与台账、取样与检测计划 |

**本轮不做**：Result / Report / Change / Room Log / Equipment / Fault Ticket（R8C / R8D）；
不做温湿度自动采集、仪器取数、GMP 合规电子签名（方案第十二节）。

**验证方式**：每轮收尾按方案 11.2 跨轮验收门禁留证据（唯一性与并发 / 批准后修改拦截 /
时间边界 / 审计不可绕过 / 子表只追加 / 动作矩阵与状态机全一致 等），
并在**测试路径** `http://localhost:5173/stability` 连通前端验证后再进下一轮。

---

## 4. 确认记录

| 项 | 确认结果 | 确认人 | 日期 |
| --- | --- | --- | --- |
| 11.3-1 v9.0 生效状态 | ✅ 已正式生效，系统按 v9.0 实现 | Owner | 2026-09-16 |
| 11.3-2 角色身份映射 | ✅ 采纳 §6.2 + 新增 LIMS QP / LIMS QA Manager；人员权限、身份与群组管理后续统一设置（本轮不做用户归属分配） | Owner | 2026-09-16 |
| 11.3-4 延期 10% 基数 | ✅ 甲（该时间点值折算天数 × 10%，`ROUND_HALF_UP`，上限 15 天） | Owner | 2026-09-16 |
| 11.3-5 DocType 清单 | ✅ 采纳 5.8（14 主 + 8 子 = 22） | Owner | 2026-09-16 |
| 11.3-7① 区间内审批 | ✅ 需审批（授权使用政策宽容期须经批准，走 `apply_delay → approve_delay`） | Owner | 2026-09-16 |
| 11.3-7② 委外窗口 | ✅ 允许留空 = 不限制（留空时委外项目只按取样侧政策上限判定） | Owner | 2026-09-16 |
