# Inventory 前端 — 完成度与未决问题清单

> Date: 2026-09-25
>
> Branch: `p4/inventory-frontend-audit`
>
> 用途：**回答「还有哪些没做 / 哪些问题没解决」**。不是设计文档，是盘点表。

## 1. 已完成

| 项 | 状态 | 位置 |
|---|---|---|
| Inventory 自定义面盘点 | ✅ | 见 §3 |
| Inventory V2 概览页 | ✅ 已实现，Owner 已审 | `views/InventoryOverviewView.vue` |
| 入库拍照识别 V1 | ✅ 已实现，Owner 已审 | `views/InventoryIntakeView.vue` |
| **草稿复核页 + 批次页** | ✅ **已实现，Owner 已审** | `InventoryDraftReviewView.vue` / `InventoryBatchView.vue` |
| 四条路由留在 Portal SPA | ✅ | 后端 `routes.py`（含 `draft/` `batch/` 前缀） |
| 侧边栏 / 移动导航（前端自维护，五组） | ✅ | `data/inventoryNav.ts` |
| 「尚未实现」提示页（不留死链接） | ✅ | `views/InventoryUnavailableView.vue` |
| CSRF 令牌（后端接口 + 前端接入） | ✅ 已实现并实测 | `hb_inventory_app.../api.py` + `frappeClient.ts` |
| 403 错误页接线（PortalLayout + InventoryLayout） | ✅ | 两处 |
| 删除 Desk 版失效的「返回仓库工作台」按钮 | ✅ | `hbos_photo_intake.js` |

## 2. 当前完成度

> 本节于 2026-09-25 更新。此前几版把「批次」「库存余额」列为未实现——**那是导航漏改**，
> 两页早已做好（见 §2.2）。

### 2.1 已实现（14 项）

| 组 | 项 |
|---|---|
| 工作台 | 库存概览 |
| 入库作业 | 入库拍照识别 · 库存单据（入库/领用/移库）· 待检批次 |
| 出库作业 | 拣货单 |
| 盘点与对账 | 库存对账 · 库级盘点三对账 |
| 主数据 | 批次 · 货位 · 物料 |
| 报表 | 库存余额 · 效期预警 · 按批号查货位 · 货位明细表 |

### 2.2 一个已修的缺陷：**页面做完了但入口被挡住**

2026-09-25 用户问「是不是只剩采购入库和销售出库」时才发现：
**「批次」与「库存余额」两页早就做好了**，但 `inventoryNav.ts` 里仍是
`implemented: false`——点侧边栏直接落到「这个功能的前端页还没有做出来」。

**根因**：同一件事写在两处（后端路由表 + 前端导航数据），每做一页要改两处。
此前几轮都改对了，唯独这两处漏了。

**修法**：
1. 两项改 `implemented: true` 并补 `stablePath`；
2. **「批次」原来根本进不去**——它只有 `batch/:batchName`（详情路由），
   没有不带参数的入口。补了一个**批次选择器** `/hbos/inventory/batch`
   （与物料/货位同构：进来给列表，选中后地址变成 `/batch/<批号>`）；
3. 加测试 `test_every_registered_native_route_has_a_portal_page`——
   **从 `router/index.ts` 读路由**（不手写，否则「路由改了测试没改」会假通过），
   逐个交给后端 `resolve_stable_route`，断言它们都不被解析去 Desk。

**反向验证过**：临时把 `/pick` 从后端路由表拿掉，那条测试立刻变红——
说明它真能抓到这类漂移，不是摆设。

### 2.3 真正没做的（2 项）

| 项 | 卡在哪 |
|---|---|
| **采购入库**（Purchase Receipt） | 供应商有 1 条，但仍无任何单据；且它带 5 个子表（含采购税），属采购流程 |
| **销售出库**（Delivery Note） | **`Customer` 0 条**，而「客户」是必填——**现在连单都开不出来** |

**客户档案从哪来需要 Owner 定**（SAP 带过来 / 仓管手工建 / 别的路径）。
这条不通，销售出库无法推进。

### 2.4 本轮发现、未修（跨应用或需你定）

| # | 问题 | 影响 | 为什么没修 |
|---|---|---|---|
| 1 | **Portal 没有生产部署路径** — `docker-compose.yml` 的 `hbos-web-prepare` 只构建 `frontend/hbos-lims-web` | Portal 只靠本地 Vite dev server 跑，**无法部署** | 超出范围；需先定同源托管还是独立源 |
| 2 | **两个 smoke 脚本必然失败** — 容器内裸调 `python`（无 `frappe`） | 与 P4 入场 Gate 的「P3 Local Runtime = PASS」记录矛盾 | 属他人范围；`start_local_workspace.sh` 的同款缺陷已修 |
| 3 | **`.global-search` 在 `<768px` 未隐藏** | 390px 下占位文字逐字换行，**影响所有应用** | 超出 Inventory 范围 |
| 4 | **`.back-workspace span` 折叠态未隐藏** | 76px 栏里文字挤成竖排；**LIMS 也有** | 本轮只给 `.inventory-sidebar` 加了限定修复 |
| 5 | **`LimsLayout.vue` 没有错误处理** | bootstrap 失败时 LIMS 静默渲染空壳 | LIMS 归他人 |

### 2.5 明确不做（有意）

- **不重做** Stock Entry / Purchase Receipt / Delivery Note / Batch / Warehouse / Item / 原生报表的**表单本体**——它们留在 ERPNext。
- **不新增 Provider 能力**——概览页只用现有 4 项 summary。
- **不为好看动 ERPNext 的校验与放行门禁**——前端只换皮。

## 3. Inventory 自定义面清单（审计基线，2026-09-25 更新）

| 面 | 前端现状 |
|---|---|
| 库存概览 | ✅ 原生（V2） |
| 入库拍照识别 | ✅ 原生（V1；Desk 版保留给管理员直连） |
| 草稿复核（拍照识别建的） | ✅ 原生 |
| 库存单据（入库 / 领用出库 / 移库） | ✅ 原生（可写，含出库放行预检） |
| 待检批次 | ✅ 原生（只读工作台；放行归 LIMS） |
| 拣货单 | ✅ 原生（可写；货位定位复用 ERPNext 的 set_item_locations） |
| 库存对账 | ✅ 原生（可写、**会调账**） |
| 批次 / 货位 / 物料 | ✅ 原生（只读；批次可打印货位卡与重新生成） |
| 库存余额 | ✅ 原生（ERPNext 标准报表，实时查询模式） |
| 效期预警 / 按批号查货位 / 货位明细表 / 库级盘点三对账 | ✅ 原生 |
| **采购入库** | ❌ 未做 |
| **销售出库** | ❌ 未做 |

**留在 ERPNext 的**：所有单据的**表单本体**（Stock Entry / Purchase Receipt /
Delivery Note 等）与原生报表引擎。前端只做入口、编排与呈现，不重写业务规则。

## 4. 「点入库拍照识别跳到后端仓库工作台」——**已解决**

**原现象**：从 Portal 概览页点「入库拍照识别」，整页离开 Portal 落到 Frappe Desk。

**原因**：该页前端版本当时还不存在，后端 `resolve_stable_route('/hbos/inventory/intake')`
返回 `/app/hbos-photo-intake`，Frappe 再 301 到 `/desk/hbos-photo-intake`。

**现已消除**：`/hbos/inventory/intake` 改为 identity 解析（返回自身），前端页由
`InventoryIntakeView.vue` 提供。实测点入口后停在 Portal SPA，路由为
`/hbos/inventory/intake`，页面正常渲染。

**Desk 版页面保留可用**（管理员/技术直连），但**不再是仓管的路径**。

## 5. Desk 版「返回仓库工作台」按钮 —— **已删除**

按 Owner 决定删除。两条依据：

1. **反口径**：它把用户往回带进 Desk 环境，与「仓管不跳 Frappe 后台」相反。
2. **它本来就是坏的**：实测点击**没有任何反应**——`data-route="Workspaces/仓库工作台"`
   是无人消费的命名，页面没有 click 处理，Frappe / ERPNext 全程也没有全局处理器认这个属性。

删除后 Desk 页面本身的出口由 Desk chrome 提供（面包屑 + 侧边栏），因为该页同时是
`仓库工作台` 的 Sidebar Item 与 Shortcut（`workspace_setup.py` 保证）；前端版本另有
侧边栏统一的「← 返回 HBOS 工作台」。原测试
`test_photo_intake_page_has_a_way_back_to_the_workspace` 已改写为
`test_photo_intake_page_no_longer_carries_a_back_button`，把「为什么删」与
「回路由谁提供」都记进断言。

## 6. 草稿复核页 + 批次页的关键判断（实现时做了两处修正）

原型审查通过后，实现时对着真实数据发现两个**原型没说准**的地方，都改掉了：

### 6.1 「有 3 项没填」必须看来源类型，不能一律说「可以不填」

原型里那句「本次来源是自产，可以不填」是**写死的**。实现时接上真实字段
（`Batch.hbos_source_type`）后分成三种情形：

| 来源类型 | 文案 |
|---|---|
| 自产 | ⓘ 可以不填（原文案） |
| **外购** | ⚠ **必须填**——待检证要印这三项，现在提交会缺栏，收货方可能不认 |
| **未记录** | ⚠ 平台无法判断，**不替用户下结论**，请自行确认 |

第三种是刻意的：不知道就说不知道，不猜。这与 `api._enrich_from_master`「多命中不猜、
只列候选」是同一条纪律。

### 6.2 批次页「卡片为何不在」有三种原因，不能共用一句文案

原型只有一个「生成失败」态。实现时发现还有两种同样常见的情形，且**下一步动作完全不同**：

| 情形 | 判定 | 文案与动作 |
|---|---|---|
| 入库单**还没提交** | 该批次无已提交的入库单 | ⓘ 提交后就自动出，**不需要**在这里手动生成 |
| 提交了但**生成失败** | 有已提交入库单、无附件 | ⚠ 提供「重新生成」+ 说明「不影响入库本身」 |
| **外部已有批次** | 无放行状态字段（非本流程建） | ⓘ 本工作台的入库流程不涉及它 |

三态合并会让「还没提交」的用户误以为出错了、去点「重新生成」——而那时
`StockEntry.on_submit` 钩子还没跑过，生成了也是多余的。

### 6.3 附件地址是跨源绝对地址

实测确认：`HBOS-B2607519-待检证+货位卡.pdf` 的下载链接必须是
`http://localhost:8080/private/files/...`（Frappe 源），不能是相对路径。
直连该地址返回 `200 / application/pdf / 72638 bytes` ✅。

## 7. 待 Owner 决策

1. **客户档案从哪来**（`Customer` 目前 0 条）——这是销售出库的唯一阻塞项。
2. **采购入库要不要做**（供应商有 1 条，但仍无单据；它带 5 个子表含采购税）。
3. Portal 将来**同源托管**还是**独立部署**（决定 §2.4 第 1 项；同源的话 CSRF
   与私有文件跨源问题在正式环境都不存在）。
4. 是否授权修 §2.4 里那些**跨应用**的问题（第 2–5 项）——不属于 Inventory，但在挡路。
5. **测试环境的脏数据**（Stock Entry 里几张「已取消」的测试单）——Owner 已定
   「正式部署前再处理」。
