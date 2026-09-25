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

## 2. 没做 / 没解决（按优先级）

### 2.1 入库流程已整条打通

```text
① 拍照识别 → 生成草稿          /hbos/inventory/intake        ✅
② 草稿复核 + 提交               /hbos/inventory/draft/:name    ✅
③ 取货位卡 / 待检证去贴货位      /hbos/inventory/batch/:name    ✅
```

**仓管全程不出 Portal。**

**唯一未运行验证的**：「提交入库」与「放弃草稿」两步。它们**写业务数据**（入账 / 删单），
按纪律未在浏览器里点完。代码逻辑与接口契约已逐条核对（见 §2.3 表）。**验收时请走这两步。**

### 2.2 本轮发现、**未修**（越界或需你定）

| # | 问题 | 影响 | 为什么没修 |
|---|---|---|---|
| 3 | **Portal 没有生产部署路径** —— `docker-compose.yml` 的 `hbos-web-prepare` 只构建 `frontend/hbos-lims-web`，`hbos-portal-web` 不在里面 | Portal 只靠本地 Vite dev server 跑，**无法部署** | 超出本轮；需先定 Portal 是同源托管还是独立源 |
| 4 | **`p2_2_runtime_smoke.sh` / `p3_workspace_runtime_smoke.sh` 必然失败** —— 容器内裸调 `python`（系统解释器无 `frappe`） | 与 P4 §2 入场 Gate 及 §10「P3 Local Runtime = PASS」记录矛盾 | 属他人范围；`start_local_workspace.sh` 的同款缺陷本轮已修 |
| 5 | **`.global-search` 在 `<768px` 未隐藏** —— 390px 下被压到 89px，占位文字逐字换行 | 全局 `GlobalHeader`，**影响所有应用** | 超出 Inventory 范围，改它要动全局样式 |
| 6 | **`.back-workspace span` 在 `<=1199px` 未隐藏** —— 76px 宽栏里文字挤成竖排 | **LIMS 与 Inventory 都有**；本轮只给 `.inventory-sidebar` 加了限定修复 | LIMS 归他人，未代改 |
| 7 | **`LimsLayout.vue` 也没有错误处理** —— 与 `InventoryLayout` 同款缺口（我给自己这个补了） | bootstrap 失败时 LIMS 页面静默渲染空壳 | LIMS 归他人 |
| 8 | **概览页的 4 项 summary 之外没有更细数据** | 概览页只能显示异常计数，没有「待检批次 / 近期效期」等 | 需扩 Provider 能力，超出「不新增后端」口径 |
| 9 | **`migration_mode` 改为 `hybrid` 后，Portal 应用中心的标签会变** | 若无其他显示逻辑依赖 `legacy`，只是文案变化 | 已改，仅记录 |

### 2.3 明确不做（有意）

- **不把 Stock Entry / Purchase Receipt / Delivery Note / Batch / Warehouse / Item / 原生报表重做成前端页** —— 后台能力原样保留，前端只做入口。
- **不新增 Provider 能力** —— 概览页只用现有 4 项 summary。
- **不为「好看」动 ERPNext 的校验与放行门禁** —— 前端只换皮。

## 3. Inventory 自定义面清单（审计基线）

| 面 | 前端现状 |
|---|---|
| 库存概览 | ✅ 本轮前端化 |
| 入库拍照识别 | ✅ 本轮前端化（Desk 版保留给管理员直连） |
| **草稿复核（拍照识别建的）** | ✅ 本轮前端化 |
| **批次（查看 / 打印货位卡 / 重新生成）** | ✅ 本轮前端化 |
| 库存单据 / 采购入库 / 待检与放行 | ❌ 无（点进去是「尚未实现」提示页） |
| 销售出库 / 拣货单 | ❌ 无 |
| 库存对账 / 库级盘点三对账 | ❌ 无 |
| 货位 / 物料 | ❌ 无（批次已前端化） |
| 库存余额 / 效期预警 / 按批号查货位 / 货位明细表 | ❌ 无（四个报表在 Desk） |

**通用 Stock Entry 表单**（任意入库 / 出库 / 移库，非拍照识别建的）仍走 Desk ——
Owner 已定**另起一轮**处理。

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

1. Portal 将来**同源托管**还是**独立部署**（决定 §2.2 第 3 项怎么做；同源的话
   CSRF 与私有文件跨源问题在正式环境都不存在）。
2. 是否授权修 §2.2 里那些**跨应用**的问题（第 4/5/6/7 项）——它们不属于 Inventory，
   但都在挡路。
3. **通用 Stock Entry 表单前端化**（任意入库 / 出库 / 移库）——另起一轮，等排期。
