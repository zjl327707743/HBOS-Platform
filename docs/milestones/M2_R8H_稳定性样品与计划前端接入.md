# M2-R8H 稳定性前端接入：样品入箱与台账 + 取样与检测计划

> 状态：**DONE / 待 Owner 审查**（离线契约 246/246、`vue-tsc` 0 错误、`npm run build` 成功、
> 浏览器真实会话走通读 + 写全链与角色门控、375px 三页无溢出）
>
> 轮次：M2-R8H，工作分支 `m2-r8`
>
> 上游：M2-R8B（样品与时间点后端）、M2-R8G（同类接入的前例）
>
> 边界：**未部署生产**（先给测试端链接，Owner 确认后再同步 `/hbos-lims`）

---

## 1. 本轮做了什么

R8B 交付了样品与时间点的后端，但「样品入箱与台账」与「取样与检测计划」两个视图仍是
R8F 的**零 API 演示数据**。本轮把它们接入真实后端（读 + 写全接），并去掉顶部
「演示数据 · 待 R8B~R8D」标识。至此稳定性 7 视图中**已有 4 个接真实后端**，
其余 3 个（结果与趋势 / 报告与有效期 / 变更·稳定性室·设备）仍待 R8C/R8D。

## 2. 后端补 3 处（不改 R8B 既有方法签名）

| # | 内容 | 原因 |
| --- | --- | --- |
| 1 | `get_stability_schedule` 行内增列 `policy_latest_sample_due` / `policy_latest_test_due` / `delay_state` | 「计划台账」要展示**三层日期**（计划检测日 / 有效截止日 / 政策硬上限）与延期状态 |
| 2 | 新增 `get_stability_delays(delay_type, status, keyword, limit)` | 「延期审批」tab 需要**跨时间点**的延期行列表（原接口只能按单个时间点取） |
| 3 | `workflow_contract` 注册 `get_stability_delays` 只读角色 | 同上 |

顺带把 `_policy_latest_test` 的入参由「对象」改为「值」，消除调用处构造匿名对象的脏写法。

## 3. 前端改动

| 文件 | 变化 |
| --- | --- |
| `src/api/stability.ts` | 增补样品/时间点/延期/日程的 Row 类型与 5 个只读 + 17 个写操作；`ACTION_ROLES` 补 R8B 全部动作 |
| `src/views/StabilitySampleView.vue` | 重写：KPI 由真实样品派生；台账 + 筛选；详情抽屉（摘要 + Sample Log + 时间点 + 动作）；动作弹窗 |
| `src/views/StabilityScheduleView.vue` | 重写：月度看板（**整月日期列**）、时间点日期链、本周到期、计划台账（三层日期）、延期审批（含批准/驳回） |
| `src/components/stability/StbInboxDrawer.vue` | **新增**：真实建档（通知单/方案/产品/条件/房间 + 3 周字段；超期自动要求评估四件套） |
| `src/components/stability/StbDelayDrawer.vue` | **新增**：申请延期（选中时间点后显示计划日与政策上限，日期选择器按区间禁用） |
| `vite.config.ts` | dev 代理补 `/printview`（标签打印走 Frappe 打印视图） |
| `src/demo/stabilityDemo.ts` | 删除这两个视图不再引用的两节（含已孤儿的 `Kpi`），630+ 行 → 356 行 |

**标签打印**：`window.open('/printview?doctype=HBOS Stability Sample&name=…&format=HBOS 稳定性样品标签')`。
生产为同源部署天然可用；开发环境靠新增的代理条目。

**月度看板**：原型的「7 天窗口」是原型样例产物，接真实数据后按已确认口径改为**整月日期列**
（行 = 产品/批号/条件，列 = 所选月份 1 号至月末，单元格显示该日的时间点），保留了原型的网格视觉语言。

## 4. 实施中发现并处置的问题

| # | 问题 | 处置 |
| --- | --- | --- |
| 1 | 「储存复核」等**无需填写表单的动作**也弹出了一个**空白确认框**，用户不点「确定」动作不会执行（实测：复核未落库） | 引入 `NEEDS_FORM` 白名单，无输入的动作直接执行、不弹空框 |
| 2 | `StbInboxDrawer` 的 `Promise.all` 解构名与 promise 个数不匹配（6 名 vs 5 个），导致 `products()` / 条件列表错位 | 修正解构 |

## 5. 验证证据（2026-09-18）

### 5.1 静态

- 离线契约 **246/246**（新增 2 项：R8H 只读接口导出与角色注册、schedule 三层日期字段）
- `npx vue-tsc -b --force` **0 错误**；`npm run build` **成功**

### 5.2 浏览器真实会话（`http://localhost:5173`）

- **样品入箱与台账**：顶部标识为「已接入真实后端」；KPI 由真实样品派生（在箱 1 / 本月入箱 2 /
  强制评估 1 / 待处置 0）；台账列出真实样品；详情抽屉显示摘要、Sample Log（入库 +10 → 10 瓶）与时间点
- **角色门控**：以 `LIMS QA` 身份，样品详情只出现「储存复核 / 进入待处置」，
  取样、返还、手动调整、受托转出等（A / M 专属）正确隐藏
- **写操作**：「储存复核」直接执行并落库（复核人 = 当前用户）
- **取样与检测计划**：月度看板按整月日期列渲染，4 个真实时间点落在正确单元格；
  日期链面板显示 8 项日期（计划取样 / 实际取样 / 取样有效截止 / 取样政策上限 / 计划检测 /
  检测有效截止 / 检测政策上限 / 延期上限）与延期历史；
  计划台账三层日期与延期状态均正确（「取样延期 延至 2026-09-18」）；
  延期审批 tab 汇总「待批准 0 · 已批准 1 · 已驳回 1」并列出真实行
- **写操作**：「取消时间点」→ 原因弹窗 → 提交成功，状态变为「已取消」
- **375px**：样品页（含详情抽屉）、计划看板、计划台账三处均无页面级横向溢出

> 验证期间为取得真实会话，临时给测试用户 `r7c-qa1@test.local` 设过密码，**验证后已删除
> `__Auth` 记录还原**。

## 6. 未做 / 边界

- **不部署生产**；不做「结果与趋势」「报告与有效期」「变更·稳定性室·设备」三视图（R8C/R8D）
- **不给 `complete_testing` 前端入口**：其后端前置为「全部必检项目均有已批准 Result」，
  Result 属 R8C——放上去必然失败，只会误导；由 R8C 的结果批准流程触发后自动打通
- 未改动 R8A/R8B 既有方法签名；未改动 R7 代码

## 7. 涉及文件

- `frontend/hbos-lims-web/src/api/stability.ts`
- `frontend/hbos-lims-web/src/views/StabilitySampleView.vue`、`StabilityScheduleView.vue`
- `frontend/hbos-lims-web/src/components/stability/StbInboxDrawer.vue`、`StbDelayDrawer.vue`
- `frontend/hbos-lims-web/src/demo/stabilityDemo.ts`、`vite.config.ts`
- `apps/hb_lims_app/hb_lims_app/hbos_lims/stability_service.py`、`workflow_contract.py`
- `apps/hb_lims_app/tests/test_stability_r8b_contract.py`
