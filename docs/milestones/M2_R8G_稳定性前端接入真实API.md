# M2-R8G 稳定性前端接入真实 API（工作台 + 考察申请与方案）

> 状态：**DONE / 待 Owner 审查**（实机端到端与负向用例 28/28、只读接口 7/7、离线契约 203/203；
> 浏览器以真实会话走通读 + 写全链）
>
> 轮次：M2-R8G，工作分支 `m2-r8`
>
> 上游：M2-R8A（稳定性后端，见 `M2_R8A_后端实现与实机验证.md`）、M2-R8F（前端复刻，演示数据）
>
> 边界：**未部署生产**（按规则先给测试端链接，Owner 确认后再同步 `/hbos-lims`）
>
> **后续进展（M2-R8B，2026-09-18）**：本轮「其余 5 视图」中，「样品入箱与台账」与「取样与检测计划」
> 所需的后端已由 **M2-R8B** 交付（5 DocType + 时间点生成 + 延期审批 + 标签 + 看板报表 + scheduler）；
> 这两视图的前端接入另起一轮。其余 3 视图仍待 R8C/R8D。见
> `docs/milestones/M2_R8B_稳定性样品与时间点后端.md`。

---

## 1. 本轮做了什么

R8A 交付了后端、R8F 交付了前端，但前端 7 视图**零 API 调用**（全演示数据），且顶部还挂着
「R8A 门禁 5 项未闭环」这一**已过期**的提示条。本轮：

1. **后端补 5 个只读接口**（R8A 只交付了 3 个：dashboard / notices / notice_detail）
2. **前端新增 `src/api/stability.ts`**，接入「稳定性工作台」与「考察申请与方案」两视图（读 + 写全接）
3. **按角色控制按钮显隐**，与后端 `ACTION_ROLES` 逐行对齐
4. **其余 5 视图**保留演示数据，但顶栏明确标注「演示数据 · 待 R8B~R8D」
5. 修掉验证中发现的 2 项 R8A 遗留缺陷（见 §3）

## 2. 新增的后端只读接口

| 方法 | 用途 |
| --- | --- |
| `get_stability_products(keyword, include_inactive)` | 建档选产品 + 「产品规则」tab |
| `get_stability_master(doctype, keyword, include_inactive)` | 储存条件 / 稳定性室 / 检验项目（**doctype 走白名单**，防越权读取） |
| `get_stability_protocols(notice, status, keyword, limit, offset)` | 「稳定性方案」tab（批量补产品名，避免 N+1） |
| `get_stability_protocol_detail(protocol_name)` | 方案详情（批次/条件/项目 + 冻结快照 + 签署链） |
| `get_stability_audit(doc_name, limit)` | 详情抽屉的审计摘要（限定稳定性 DocType；不改 R6D 既有 `get_audit_log`） |

均沿用既有约定：模块级 `@frappe.whitelist()`、入口 `_check_action(action, doctype, doc_name)`、
只读投影不返回占位值；4 个新动作已注册进 `workflow_contract.ACTION_ROLES`（6 个 LIMS 角色 + System）。

## 3. 修复的 R8A 遗留缺陷

| # | 缺陷 | 影响 | 处置 |
| --- | --- | --- | --- |
| 1 | `HBOS Stability Protocol` **没有 `snapshot_frozen` 字段**，而控制器调用 `guard_snapshot_frozen(..., SNAPSHOT_FIELDS_PROTOCOL)` | 守卫读 `before.get("snapshot_frozen")` 恒为 None ⇒ **方案批准后快照字段的只读保护完全失效**（方案 7.7 要求；Notice 有、Protocol 漏建） | 补字段 + `approve_protocol` 批准时置 1 + 纳入 `PROTOCOL_SYSTEM_FIELDS`；新增契约断言「契约声明的快照字段必须真实存在于对应 DocType」 |
| 2 | 命名系列写作 `HBOS-STB-NOT-.YYYY.-####` | Frappe `set_name_by_naming_series()` 对系列**无条件追加 `.#####`**，系列自带的 `#` 被当字面量 ⇒ 实际生成 **`HBOS-STB-NOT-2026-####00009`** 这类畸形单号（既有 DocType 用的是 `HBOS-SMP-.YYYY.-`，不带 `#`） | 改为 `HBOS-STB-NOT-.YYYY.-` / `HBOS-STB-PRO-.YYYY.-`（与既有约定一致）；清理 4 条钉住旧值的 **Property Setter**；新增契约断言「命名系列不得含 `#`」 |

第 2 项同时更正了方案 §5.2.x/§5.8 与 `M2_R8A_启动门禁确认包.md` 中的全部命名系列写法（36 处），
并在两处加了口径说明，供 R8B~R8D 遵循（**系列不含 `#`、以 `-` 结尾**）。

> 说明：这是**实现细节更正**，不影响 Owner 2026-09-16 对 DocType 清单与父级关系的确认结论。

## 4. 前端改动

| 文件 | 变化 |
| --- | --- |
| `src/api/stability.ts` | **新增**：7 个只读 + 14 个写操作 + `ACTION_ROLES` / `canAction` / `SOD_NOTE`（照 `api/retention.ts` 范式） |
| `src/views/StabilityDashboardView.vue` | 重写：KPI / 待办通知单 / 待审方案 / 主数据计数 / 产品清单全部来自真实 API；**后端未交付的指标标注「待 R8B~R8D」，不展示占位数字** |
| `src/views/StabilityStudyView.vue` | 重写：通知单列表（关键字 + 状态筛选）+ 详情 + 状态机流程 + 冻结快照 + 签署链；**状态 × 角色双过滤的动作按钮**（提交/QC 确认/批准/驳回/取消/关闭 + 注册人员复核）；方案 tab（列表 + 详情抽屉 + 起草/提交/审核/批准/驳回/作废）；产品规则 / 条件与项目 tab 接主数据 |
| `src/components/stability/StbNoticeDrawer.vue` | 改为真实建档：产品/条件/批次来自主数据接口，>2 条件时强制填补充原因并提示需先注册人员复核 |
| `src/components/stability/StbProtocolDrawer.vue` | **新增**：方案起草（从已批准通知单继承批次与条件 + 选检验项目）与详情两态 |
| `src/components/stability/StbAuditDrawer.vue` | 改为真实审计（`get_stability_audit`，按对象过滤），不再用写死的摘要 |
| `src/components/stability/StbGateBanner.vue` | 由「过期的门禁提示条」改为两态：**已接入真实后端**（绿）/ **演示数据 · 待 R8B~R8D**（黄）；删除已闭环的门禁项抽屉 |
| `src/demo/stabilityDemo.ts` | 删除已接入视图不再引用的导出（dashboard / study 两节 + 门禁常量 + 审计摘要）；其余 5 视图的演示数据保留 |

## 5. 验证证据（2026-09-18）

### 5.1 离线契约

`cd apps/hb_lims_app && python3 -m unittest discover -s tests` → **203/203 OK**
（新增 4 项：命名系列不含 `#`、快照字段必须存在、只读接口已导出、新只读动作已注册角色）

### 5.2 实机接口

- R8A 端到端 + 负向用例 **28/28 通过**（建档→复核→提交→QC确认→批准→方案→审核→批准→作废→关闭；
  越权 / SoD 自批 / 冻结快照 / 非法转移 / 删除拦截）
- 只读接口 **7/7 通过**（产品 / 条件房间项目 / 白名单拦截任意 DocType / 方案台账 / 方案冻结标记 /
  方案详情 / 批准后修改冻结字段被拒）

### 5.3 浏览器（`http://localhost:5173`，真实会话）

- **工作台**：KPI 通知单待批/已批准、方案待审/已批准、稳定性产品 2；主数据 条件 3 / 房间 1 / 项目 1；
  待办通知单与产品清单均为真实数据；「样品 / 时间点 / 结果」显示「待 R8B~R8D」而非占位数字
- **考察申请与方案**：通知单 3 条真实数据；详情条件/批次/用量/冻结快照/签署链正确；
  状态机流程步进正确（草稿 → 待QC经理确认 → 待批准 → 已批准 → 已关闭）
- **写操作**：以 `LIMS QA` 身份对草稿执行「提交」→ 状态变为**待QC经理确认**、申请人回填、
  动作集按角色收敛为「驳回」（QA 无 `confirm_notice_qc` 权限）——**读写链路与角色门控均实测通过**
- **审计抽屉**：显示该单的真实审计事件（通知单提出 / 修改 / 创建）
- **主数据 tab**：储存条件 3 条、检验项目 1 条真实数据
- **方案 tab**：真实方案 `HBOS-STB-PRO-2026-00001`，产品名带出、状态与动作正确
- 演示视图（样品入箱）：显示「演示数据 · 待 R8B~R8D」标识（区别于已接入页面）
- **375px 移动端**：工作台 / 考察申请与方案 / 样品入箱三页均无页面级横向溢出

### 5.4 构建

`npx vue-tsc -b --force` → **0 错误**；`npm run build` → **成功**

## 6. 未做 / 边界

- **未部署生产**：按规则先给 Owner 测试端链接（`http://localhost:5173/stability`），确认后再同步 `/hbos-lims`
- **其余 5 视图未接真实后端**：样品入箱 / 取样与检测计划 / 结果与趋势 / 报告与有效期 /
  变更·稳定性室·设备——后端接口属 R8B~R8D，本轮仅明确标注
- **未启动 R8B**；未改动 R7 留样板块
- **合规审计日志页的筛选项**仍是写死常量（`AuditLogView.vue` 的 `LOG_TYPES`），
  稳定性新事件在表格中可见但下拉筛不到——属前端遗留，未在本轮处理
- **验证期间的临时账号操作已还原**：为取真实会话临时给测试用户 `r7c-qa1@test.local` 设过密码，
  验证后已删除 `__Auth` 记录，恢复原状

## 7. 相关文件

- `frontend/hbos-lims-web/src/api/stability.ts`（新增）
- `frontend/hbos-lims-web/src/views/StabilityDashboardView.vue`、`StabilityStudyView.vue`
- `frontend/hbos-lims-web/src/components/stability/`（4 个组件）
- `apps/hb_lims_app/hb_lims_app/hbos_lims/stability_service.py`（+5 只读接口）
- `apps/hb_lims_app/hb_lims_app/hbos_lims/workflow_contract.py`（+4 动作角色）
- `apps/hb_lims_app/tests/test_stability_r8a_contract.py`（+4 断言）
