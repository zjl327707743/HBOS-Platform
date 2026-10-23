# 考勤 Desk 页视觉改造与门户应用内导航实施记录

项目名称：新乡海滨智能运营管理平台。

分支：`feature/hbos-portal-workbench`。

状态：**REVIEWING**（等待 Owner 验收；未 closeout）。

## 一、编号与定位

本文件同时记录 2026-10-02 的两批交付，它们共用同一次前端工作：

- **工作流 A**：Desk 侧 4 个考勤页的视觉改造（补齐上一批只挂 class 未改版的部分）+ 页面缓存失效机制。
- **工作流 B**：门户考勤的应用内导航（Owner 审查原型后选定「顶部页签 + 管理后台入口」）。

编号仍为 **M3-PORTAL-R1 后续**，不新开里程碑号（理由同 `M3_考勤页原生化与Desk共享视觉层.md`：`R1`~`R4` 已被 M3-PORTAL-R1 用作内部阶段号）。是否单独计号**待 Owner 裁定**。

## 二、工作流 A：Desk 四页视觉改造

### 改动前的问题

上一批（`ada6dff`）把 6 个 Desk 页面挂上了 `.hbos-surface`，但**只有仪表盘与部门看板真正做了视觉改写**（+103 / +65 行），另外 4 个页面只加了挂载点（各 +3 行）。后果是：这 4 页的旧 Frappe 风格内容浮在新的蓝色画布上，与新改的两页观感割裂。

### 本次改动的四页

| 页面 | 改造要点 |
|---|---|
| **人员管理** | 裸 `row/col` 表单 → 玻璃工具条（部门 / 搜索 / 查询 + 右侧「共 N 人」计数）；`table-bordered` → 实色密集表（表头吸顶、数字等宽）；补空 / 加载 / 错误三态 |
| **导入考勤机导出表** | 内联样式从 Frappe 变量（`--border-color` / `--fg-color`）改为 HBOS 令牌；指标卡墙 → 定义列表；新增三步流程条（选表 → 识别 → 导入） |
| **月度考勤上传** | 居中 600px 卡片 → 左对齐「选择文件 ｜ 本次处理结果」双栏；月份 / 年份并排；回执面板从空卡片改为定义列表 + 30px 大数字 |
| **班次管理** | `card` / `list-group` / `badge` 组件 → 实色面板与密集表；部门列表带人数；规则看板 `rb-*` 样式里硬编码的色值（`#eef2f7` / `#2c3e50` / `#fafbfc` / `#e0e0e0`）与字号（11 / 13 / 15）全部换成 `var(--h-*)` 与契约允许的 12 / 14 / 16；状态徽章走共享 `.h-badge--*` |

### 设计原则（沿用 M3 那批，未另起炉灶）

- **色值只写一份**：全部走 `hbos_attendance.bundle.css` 在 `.hbos-surface` 下定义的 `--h-*`；字号只取契约 v2.0 允许的 30 / 20 / 16 / 14 / 12。
- **强度分档**：四页都是 V1 操作面（实色面板、密集行、表头吸顶、无动效）；玻璃只留在工具条外壳上。班次管理是四处里**唯一一屏没有任何玻璃**的页面——编辑器里最不该出现的就是会动的装饰。
- **定义列表取代指标卡墙**（导入页 / 月度上传）：这些是只读事实而非 KPI，每项一个色块卡会让人以为它们各自独立、可点击、可比较大小。
- **步骤条是信息不是装饰**（导入页）：该页确实是一条三步流程，步骤条回答「我卡在哪一步」；三个并列按钮做不到这件事。

### 顺带修掉的 XSS 隐患

人员管理、班次管理的部门名 / 姓名 / 规则名取自 `tabEmployee.department` 等**用户可写字段**，此前直接拼进 HTML。已统一转义（人员管理走 `frappe.utils.escape_html`，班次管理新增 `esc` 助手）。

## 三、工作流 A 的关键发现：页面缓存不会自愈

**这是本轮最值钱的产出，因为它解释了此前反复「改了看不到」的全部现象。**

Frappe 把标准 `Page` 的脚本缓存在**浏览器 localStorage**（`_page:<页面名>`），下次打开直接读缓存、**不再问服务端**（`frappe/public/js/frappe/views/pageview.js` 的 `with_page`）。失效判据是同文件 `desk.js` 的 `sync_pages`：

```js
if (!page_info[name] || page_info[name].modified != p.modified)
    delete localStorage["_page:" + name];
```

即比对 **`Page` 文档的 `modified` 时间戳**。而修改磁盘上的 `<page>.js` **不会**动 `Page` 文档——所以：

- 改完页面 JS，服务端确实在发新代码（可用 `bench execute frappe.desk.desk_page.get --kwargs '{"name": "..."}'` 验证返回的 `script` 字段），
- 但**所有看过该页的浏览器会一直跑旧版本，且永远不会自愈**；
- **普通刷新（F5 / Cmd+Shift+R）没用**——刷新不清 localStorage。Frappe 的 `Ctrl+Shift+R`（**Control** 键，不是 Mac 的 Command）会清，但它清掉整个 localStorage，代价比必要的大。

### 修复

1. **一次性**：把 6 个 `Page` 的 `modified` 顶到当前时间（只写这一个字段），并 `clear_cache`。之后用户**普通刷新**即生效。
2. **长期**：新增 `hbos_attendance/bump_page_cache.py`（按 `hbos-%` 前缀匹配，可反复执行、只写 `modified`），把这件事变成一条命令：

```
docker exec hbos-m0-r3a-backend-1 sh -c 'cd /home/frappe/frappe-bench && bench --site frontend execute hb_attendance_app.hbos_attendance.bump_page_cache.run'
```

3. **记录**：写入 `docs/frontend/FRONTEND_IMPLEMENTATION_GUIDE.md` §1.1.1，并注明「改了页面却看不到变化时，先怀疑这里，再怀疑代码」。

注：本次顶时间戳时发现**仪表盘与部门看板的 `Page.modified` 也是陈旧的**（`2026-09-28 16:29`，而它们的 JS 是同日 `23:15`/`23:31` 改的）——这两页此前的改动同样处于「改了但看不到」的状态。可能正是此前反复确认未果的来源。

## 四、工作流 A 中我引入并修复的缺陷（必须留档）

为修「人员管理与班次管理抢同一个顶层函数名 `renderPage`」（两个脚本都在 Desk 常驻求值，后求值者覆盖前者，导致其中一页渲染出另一页内容），我把两页的函数收进 IIFE。

**但 `hbos_employee_management.js` 里我把 `on_page_load` 的赋值留在了闭包外**，而它在闭包内调 `renderPage` —— 结果 `ReferenceError: renderPage is not defined`，**页面整个空白**。

排查顺序也因此被误导了一轮：清掉缓存后症状从「显示旧界面」变成「显示空白页」，我最初以为仍是缓存问题。真正确认靠的是浏览器控制台里的那条 ReferenceError。

**已修**，并将 `on_page_load` 赋值移入 IIFE。修复后用脚本对六个页面做了边界自检（IIFE 位置 vs 赋值位置），确认另外三个文件没有同类问题——它们本就是「赋值在前、包裹在后、被包裹的是内部辅助函数」的合法结构。

## 五、工作流 B：门户考勤应用内导航

### 改动前的问题

门户里的考勤**只有一个入口**（仪表盘）：

- 人员管理、部门看板两页路由可用、能直连打开，但**没有任何链接指向它们**；
- 门户的应用内导航组件（`AppLocalSidebar.vue`）的菜单**写死了 LIMS 的条目**，且只被 `LimsLayout.vue` 引用——考勤没有对应的导航组件。

### Gate：先出原型

按 `docs/frontend/FRONTEND_IMPLEMENTATION_GUIDE.md` 的「原型先行 → Owner 审查 → 复刻实现」，本轮**先出了三案对比原型**（`docs/frontend/prototypes/2026-10-02-考勤应用内导航方案.html`）：

| 方案 | 判断 |
|---|---|
| A · 左侧应用栏 | 与 LIMS 对称，用户不用重学导航；占 208px，表格横向空间被挤 |
| **B · 顶部横向页签** | **Owner 选定**。考勤只三页、且是「同一件事的三个视角」，页签更贴合；表格拿满宽度 |
| C · 仪表盘内入口卡 | 结构最省，但每次切换要先回仪表盘 |

原型用**真实设计令牌**（取自 `tokens.css`），不是示意色。Owner 同时裁定：**班次管理 / 导入 / 月度上传暂不搬进门户**（那是 3 个新页面 + 各自数据层，另开一轮），导航右侧留「管理后台」入口链到 Desk。

### 实现

- **新增 `AttendanceLayout.vue`**：对齐 `LimsLayout` 的结构——GlobalHeader（context 显示 `ATTENDANCE`）+ aurora 背景 + 内容区 + 底部移动导航 + CommandPalette。不加 `lims-aurora` 那种 tints 变体：默认 `aurora-a` 就是紫罗兰 `#8177ff`，与考勤域色（`--hbos-domain-attendance` 的 `#6b60ff→#8c61ff`）同族。
- **三条路由改为挂在该布局下的子路由**（原来是并列的顶层路由）。顺带修掉一个此前遗漏：那三条顶层路由**不带门户外壳**，没有 GlobalHeader、没有 aurora 背景，所以玻璃卡浮在纯白底上显得发空；挂上布局后与 LIMS 一致。
- **页签**：考勤仪表盘 / 人员管理 / 部门看板。高亮用**精确匹配**（`route.path === tab.to`），因为 `/hbos/attendance` 是另两条的前缀，用 `startsWith` 会让三个页签同时点亮。
- **管理后台**：`<a href="/app/海滨考勤工作台" target="_blank">`。指向 Workspace 而非某个具体页面——那里才是「导入 / 月度汇总 / 班次管理 / 报表」的家。**新开页签**而不内嵌：按分层约定，Frappe Desk 是 V0 管理控制台、保留自身身份，不与门户逐像素一致。

## 六、验收（本机实测）

### 自动化

- 考勤全量回归：**467 通过**。
- 门户生产构建：`npm run build`（`vue-tsc -b && vite build`）→ **通过**，3315 模块。

### 浏览器实测（真实数据，登录态为真实 Administrator）

**Desk 四页**（浏览器缓存按第三节办法失效后）：

| 页面 | 实测 |
|---|---|
| 人员管理 | `.emp-toolbar` 存在、`.`emp-tbl` 696 行、表头 `position: sticky`、计数「共 696 人」 |
| 导入考勤机导出表 | `.imp-steps` 三步条存在、双栏面板、定义列表 |
| 月度考勤表上传 | `.mu-layout` 双栏存在、**旧版 `.card-body` 计数为 0** |
| 班次管理 | `.sm-heading` 存在、部门卡 29 个带人数、**旧版 `.list-group` 计数为 0** |

**门户导航**：

| 项 | 实测 |
|---|---|
| 三个页签渲染 | 考勤仪表盘 / 人员管理 / 部门看板，`href` 正确 |
| 页签切换 | 点「人员管理」→ URL 变 `/hbos/attendance/employees`、高亮随之移动、数据表出 |
| 部门看板 | 点入后高亮正确、出勤率 46.9% / 应出勤 508 / 已到岗 238 |
| 管理后台 | `/app/海滨考勤工作台` → 200 → 302 → `/desk/海滨考勤工作台` |
| 门户外壳 | `.aurora` 计数 2、GlobalHeader 存在（此前缺失） |

**控制台**：除既有的 `socket.io Invalid origin` 与登录前的 403 外，无新增错误。

## 七、本轮未做

- 未把班次管理 / 导入 / 月度上传搬进门户（Owner 已裁定另开一轮）。
- 未对四个 Desk 页做移动端适配（Desk 管理页按既有约定不做移动端重排）。
- 未改判定核心 `pairing.py` / `api.py` / `rule_lists.py`。
- 未重建容器、未 `migrate`、未跑 `bench build`（页面 JS 每次打开直读，不走资源管线）。
- 未提交任何真实数据、截图或导出文件。

## 八、运行态影响（须知悉）

1. **动过运行中数据库一次**：6 个 `Page` 的 `modified` 被顶到当前时间（只写该字段）。这是让缓存失效的唯一办法。
2. **`apps/hb_attendance_app` 是 bind-mount 进容器的**：本轮改的 4 个页面 JS 立即落在生产路径上。Desk 每次打开直读文件，所以**改动即时生效**；但常驻进程内存里的 Python 不受影响（本轮未改 Python）。
3. **本记录所载工作与 `m1-fix-pairing-long-duty` 分支的连班修复彼此独立**，后者仍未生效（需重启 + 定向重算，待 Owner 授权）。

## 九、遗留与风险（记录，不修）

1. **`docs/experience/` 在本分支不存在**，但代码多处引用 `EA-4` / `EA-5.4`（Owner 2026-09-29 裁定保留引用、不移植）。后果：注释里的「依据」在本分支内无法就地核对。
2. **`M3_START_GATE.md` 缺失**（M2 / M3 / M4 均未建门禁文档，既有治理缺口）。
3. **两个原生子页此前无入口的问题**本轮已解决；但**考勤之外**的应用（库存等）若也走 native 模式，同样会遇到「有页面没导航」——建议把「新增 native 应用必须同时交导航」写进前端规范（本轮未改规范）。
4. **本轮未跑 CI**（CI 只在 PR 到 main 时触发）；本地已跑等价检查：Python 语法编译、全量单测、前端构建。

## 十、状态台账更新

- `docs/PROJECT_STATUS.md`：M3-PORTAL-R1 节新增本轮两批交付；状态口径行同步。
- `docs/CURRENT_MILESTONE.md`：M3-PORTAL-R1 段落新增；「下一轮预告」同步。
- `docs/milestones/README.md`：文件索引新增本文件。
- `README.md` / `docs/AI_CONTEXT.md`：各补一行本轮状态。
- `docs/frontend/FRONTEND_IMPLEMENTATION_GUIDE.md`：新增 §1.1.1「改完页面 JS 必须让浏览器缓存失效」。

## 十三、后续变更（Owner 2026-10-08）

本文件第十二节所述的两项决定已被 Owner 于 2026-10-08 变更：

| 本文件原记录 | 现决定 |
|---|---|
| 「班次管理 / 导入 / 月度上传**暂不搬进门户**」（第五节） | **全部搬进**；其中班次管理保留 Desk iframe 作为有意的例外 |
| 「**新开页签**而不内嵌」（第五节末） | 改为**门户原生 AntD 渲染**；仅班次管理保留内嵌 |

变更后的交付见 `docs/milestones/M3_考勤面板全面化与分组导航.md`。本文件其余内容（Desk 四页改造、页面缓存机制）**不受影响，继续有效**。
