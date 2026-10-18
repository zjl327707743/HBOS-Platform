# 考勤页原生化与 Desk 共享视觉层实施记录

项目名称：新乡海滨智能运营管理平台。

轮次：**M3-PORTAL-R1 后续（2026-09-29）**，分支 `feature/hbos-portal-workbench`。

状态：**REVIEWING**（等待 Owner 验收；未 closeout）。

## 一、编号与定位说明

本轮是 **M3-PORTAL-R1 的后续交付**，不新开里程碑编号。原因是 M3-PORTAL-R1 的 R1–R4 已经占用了 `R1`~`R4` 作为**该轮内部阶段**（移植 / 同域通路 / 接数据 / 生产形态），若本轮取名 `M3-PORTAL-R2` 会与其中的「R2 同域通路」正面撞名。故本轮不认领新编号，文档按 `M3_<主题>.md` 命名（与既有 `M1_考勤一期产品需求说明书.md`、`M1_Demo实施路线图.md` 同族）。

**待 Owner 裁定**：若 Owner 希望本轮单独计号（例如 `M3-PORTAL-R5`，或另立 `M3-PORTAL-R2` 并重排既有阶段号），本文件与两份台账可一并改名。

## 二、本轮做了什么

M3-PORTAL-R1 的 R1–R4 用「**同域 iframe 承载真实 Frappe 考勤页面**」实现「导航不出门户」。本轮把其中三个页面**从 iframe 内嵌改为门户 SPA 原生页**：

| 门户路由 | 改造前 | 改造后 |
|---|---|---|
| `/hbos/attendance` | iframe → `/app/hbos-attendance-dashboard` | 门户原生页 `AttendanceDashboardView.vue` |
| `/hbos/attendance/employees` | 无此路由 | 门户原生页 `AttendanceEmployeesView.vue` |
| `/hbos/attendance/board` | 无此路由 | 门户原生页 `AttendanceBoardView.vue` |

后端 `migration_mode` 由 `legacy` 改 `native`；`resolve_stable_route` 由「解析到 Desk 路径」改为「**解析回自身**」，前端据此走 SPA 路由分支、不再进 iframe。

同时给 Desk 侧 6 个考勤页面接了一层**共享视觉层**（`hbos_attendance.bundle.css` + `.hbos-surface` 挂载点），其中仪表盘与部门看板做了完整的 V2/V1 分档改写。

**这两件事是本轮的主体，同属「前端工作台改造」。第三件事（班次管理 RBAC）与前端无关，是核账时发现并一并落地的安全修复，见第五节。**

## 三、工作流 A：门户原生考勤页（iframe → native）

### 改动

- **新增 3 个视图**：`AttendanceDashboardView.vue`（320 行）、`AttendanceEmployeesView.vue`（138 行）、`AttendanceBoardView.vue`（308 行）。
- **新增 3 个 service**：`attendance.ts`、`attendanceBoard.ts`、`attendanceEmployees.ts`。三者都走既有 `frappeClient.callFrappeMethod`，**不新造请求层**。
- **路由登记**：`src/router/index.ts` 新增上述 3 条顶级路由。
- **后端适配层**：`hbos_attendance/portal/manifest.py` 的 `migration_mode` 改 `native`；`portal/routes.py` 把 `CURRENT_DASHBOARD`（`/app/hbos-attendance-dashboard`）换成 `CURRENT_IMPLEMENTATION = STABLE_PREFIX`，并新增 `REGISTERED_PATHS` 白名单（根 / `/dashboard` / `/employees` / `/board`）。
- **白名单而非前缀放行**：未注册路径在**路由解析阶段**就失败（前端落 403），而不是悄悄透传到后端。新增门户页面时必须在此登记。
- **契约测试**：`test_portal_provider_contract.py` 同步更新，由 13 用例增至 **15 用例**（新增 `/employees`、`/board` 两条白名单断言；原「`/hbos/attendance/employees` 应被拒」的负例已按新语义移出拒绝列表；`test_root_and_dashboard_map_to_current_desk_page` 按新语义改名为 `test_registered_routes_map_to_themselves`）。
- **mock 模式对齐**：`src/data/mockPortal.ts` 中考勤的 `migrationMode` 由 `legacy` 改 `native`。该项**只影响 `AppCenterView` 的迁移标签文案**（全仓库仅 `migrationLabel()` 两处消费），不影响路由；改它是因为同一语义在 mock 与 frappe 两个模式下说法不一致，属本轮的同一处漂移。

### 数据来源（未新造数据链路）

三个页面**只做展示投影**，全部复用既有后端只读接口：

| 页面 | 接口 |
|---|---|
| 仪表盘 | `...page.hbos_attendance_dashboard.dashboard_data.get_data` |
| 人员管理 | `...page.hbos_employee_management.employee_management_data`（`get_employees` / `get_departments` / `get_shift_options`） |
| 部门看板 | `...page.hbos_department_board.department_board_data`（`get_data` / `live_sync`） |

仪表盘**日期区间不传时由后端按「本周一~周日」兜底**，前端不重算窗口——两处各算一次必然漂移。

部门看板的**中文状态文案全部取自后端**（`department_board.live_state` / `day_review` 的 `label` 字段），前端不复刻一套 14 状态的中文映射。

趋势图用**内联 SVG 手写**，不引图表库（与门户 LIMS 页同一做法）。

## 四、工作流 B：Desk 共享视觉层

### 新增

- `apps/hb_attendance_app/hb_attendance_app/public/css/hbos_attendance.bundle.css`（10,169 字节）：EBOS 令牌的 Desk 内落地层。
- `hooks.py` 新增一行 `app_include_css = "hbos_attendance.bundle.css"`。
- `tools/apply_hbos_surface.py`：给 6 个页面根容器插入 `$(wrapper).addClass("hbos-surface")` 的一次性 codemod（幂等，已执行完毕）。

### 关键设计约束

- **全部规则限定在 `.hbos-surface` 下**。Desk 的侧边栏、顶栏、原生控件不受影响。变量也**只在该作用域内定义**（`:root` 上没有 `--h-*`，实测为空）。
- **为什么只写一份**：6 个页面各抄一遍色值必然漂移。本项目为「一个业务含义只留一份名单」专门收敛过行政班名单并加了防副本测试，同一道理适用。
- **值以门户 `tokens.css` 为准**。Desk 里引不到门户的 CSS 自定义属性，故把值抄成字面量；两处若漂移以 `tokens.css` 为准（EA-4 §36 把实现版定为权威）。
- **强度分档**（EA-4 §4）：KPI / 图表 = V2（玻璃卡、域色、轻动效）；筛选 / 表格 = V1（实色、密集行、表头吸顶、无动效）。字号只取契约 v2.0 允许的 30 / 20 / 16 / 14 / 12。

### 逐页改动

| 页面 | 改动 |
|---|---|
| 考勤异常仪表盘 | 完整改写为 V2/V1 分档（卡片、域色条、密集表） |
| 部门看板 | 完整改写（玻璃工具条与内容面板、KPI、密集表） |
| 导入考勤机导出表 / 月度考勤汇总 / 人员管理 / 班次管理 | 仅挂 `.hbos-surface` |

### 清理

- `.gitignore` 新增 `apps/*/*/public/dist/`：`bench build` 产物的文件名带内容哈希，入库只会让每次改样式多出一对改名文件；而 `assets.json` 落在 `sites/assets/`（本就不入库），新检出无论如何都要先跑一次 `bench build`，提交 `dist` 并不能省掉这一步。
- `public/build.json` 删掉 `"js/hbos_attendance.bundle.js": []`：该条目**从未产出过文件**（`public/dist/` 下只有 css 与 css-rtl，无 js），全仓库也无任何引用（`app_include_css` 只依赖 css bundle）。本轮是第一次让 `build.json` 变为承重件，顺手清掉这条死声明。

## 五、工作流 C：班次管理服务端 RBAC（与前端无关）

`shift_management_data.py` 的 13 个 `@frappe.whitelist()` 接口此前**全是裸装饰器**：Frappe 语义下任何已登录用户都能直接调，页面角色只挡「能不能打开 Desk 页面」，挡不住直接打接口。已补：

- 读（`HR User` / `HR Manager` / `System Manager`）、写（`HR Manager` / `System Manager`）两组，分别经 `_require_read()` / `_require_write()`。
- 普通 `HR User` 不在写组内——改班次会改变全体人员的判定口径。

**已验证无副作用**：全仓库检索确认这 13 个接口**只有** `hbos_shift_management.js` 一个调用方，无后台任务 / 无内部模块调用，故加角色门禁不会打断任何定时任务。

**本次只修了这一半，必须知悉**：同类缺陷在其他模块仍在。全量盘点（whitelist 接口数 / 角色守卫数）：

| 模块 | 接口数 | 守卫 |
|---|---|---|
| `hbos_shift_management/shift_management_data.py` | 13 | 16（**本轮已补**） |
| `hbos_department_board/department_board_data.py` | 2 | 2（早前已补） |
| `doctype/hbos_attendance_import_log/hbos_attendance_import_log.py` | 2 | 3（早前已补） |
| `page/hbos_employee_management/employee_management_data.py` | 5 | **0**（含写接口 `bind_shift` / `bulk_bind_shift`） |
| `page/hbos_monthly_upload/upload.py` | 1 | **0**（上传即写） |
| `api.py` | 4 | **0** |
| `report/月度考勤汇总/export.py` | 2 | **0** |
| `report/月度考勤汇总/月度考勤汇总.py` | 1 | **0** |
| `roster_export.py` | 1 | **0** |
| `sync_rest_leave.py` | 1 | **0** |

**「班次管理已加门禁」不能读成「写接口已收敛」**。`employee_management_data.bind_shift` / `bulk_bind_shift` 的爆炸半径与班次管理同级（同样改人员班次绑定），仍在裸奔。

## 六、验收（本机实测，均为本轮独立复现）

### 自动化

- 考勤全量回归：`python3 -m unittest discover -s apps/hb_attendance_app/tests` → **460 tests OK**（本轮前 458；契约测试文件由 13 增至 15，净 +2）。
- 门户生产构建：`npm run build`（`vue-tsc -b && vite build`）→ **通过**，3312 模块，dist 产物 `index-MF-e_1eK.js` / `index-BSo-Aeji.css`。

### 浏览器实测（真实数据）

实测入口：Vite dev `5178`（frappe 模式，同域代理）；生产容器 `8081` 已确认服务同一份产物（`/hbos/` 返回的 asset 哈希 `index-MF-e_1eK.js` / `index-BSo-Aeji.css` 与本机 dist 一致，`/hbos/attendance` 200）。

**1. 门户原生三页与后端逐值一致**

| 页面 | 页面显示 | 后端接口 | 判定 |
|---|---|---|---|
| 仪表盘（09-28~10-04 默认窗口） | 迟到 3 / 早退 0 / 缺勤 1931 / 异常人员 404 / 出勤率 53.8% / 总人数 696 | `total_late=3, total_early=0, total_absent=1931, anomaly_people=404, attendance_rate=53.8, total_employees=696`，`date_range=2026-09-28 ~ 2026-10-04` | **逐值一致** |
| 仪表盘（点查询改窗口后） | 3 / 0 / 173 / 152 / 75.1% / 696 | 随窗口变化正常刷新 | 通过 |
| 人员管理 | 共 696 人，表含 工号/姓名/部门/联系方式/入职日期/固定班次 | `get_employees` | 通过 |
| 部门看板 | 42.2% 出勤率 / 505 应出勤 / 213 已到岗 / 0 迟到 / 20 未打卡 / 0 缺勤 / 3 请假 / 53 休息；meta `2026-09-29 · 实时（13:16）` | `stats` 逐字段相同（`expected=505, present=213, late=0, noCard=20, absent=0, leave=3, rest=53, attendance_rate=42.2`） | **逐值一致** |

**2. Desk 侧视觉层生效且未污染外壳**

| 页面 | 实测 |
|---|---|
| `/desk/hbos-attendance-dashboard` | `.hbos-surface` 已挂；`.dash-stat` 计算样式 = 圆角 18px、`rgba(47,72,117,.09) 0 18px 56px`、padding `20px 16px`；KPI 3/0/1931/404/53.8%/696 **与门户原生页同窗口逐值一致** |
| `/desk/hbos-department-board` | `.hbos-surface` 已挂；工具条计算样式 = 圆角 24px、`rgba(255,255,255,.68)`、`backdrop-filter: blur(24px)`；KPI 42.2%/505/213/0/20/0/3/53 **与门户原生页逐值一致** |
| `/desk/hbos-employee-management`（仅挂 class 的页面） | `.hbos-surface` 已挂，画布 `#f4f8fd`、字体 Inter 栈生效；**侧边栏字体未受影响**（仍为 Desk 自身 InterVariable），作用域隔离成立 |

同一份数据在「门户原生页 / Desk 页 / 后端接口」三处得到相同数值，是本轮**最强的一条交叉验证**。

**3. 控制台**

三条原生页加载期间**无新增错误**。仅有的三类报错均为**本轮之前已记录**的既有项，非本轮引入：

- `GET /website_script.js → 404`：Vite 代理覆盖缺口（已记于 M3-PORTAL-R1 缺口清单）。
- `socket.io: Invalid origin`：M0-R3C-FIX 已记录的既有现象。
- 登录前 `GET /api/method/hbos_portal.api.bootstrap.get_bootstrap → 403`：未认证时正常；登录后实测 **200**。

（会话中另见 `POST ...dashboard_data.get_data → 400`，系本人在调试时手工发的 POST 探针；应用自身走 GET，实测 200。）

**4. 生产容器未受影响**

`frontend`（8080）Up 9 天、`portal`（8081）Up 19 小时，本轮**未重建任何容器、未跑 `migrate`、未写运行态数据库**。唯一触及运行态的动作是**按本轮源码重建了门户 dist**（`portal` 容器以只读方式挂载该目录，故 8081 立即服务新产物）；考勤 App 的 `public/dist` 与 `sites/assets` **未重新构建**——Desk 侧新样式是上一批（2026-09-28）`bench build` 的产物。

## 七、本轮未做

- 未改判定核心：`pairing.py` / `api.py` / `rule_lists.py` **零改动**（本轮只碰展示层与 portal 适配层）。
- 未跑 `bench build`（`build.json` 的改动对产物无影响：删掉的是一个从未产出文件的空 entry，已验证 `public/dist/` 下无 js 产物）。
- 未重建容器、未 `migrate`、未 `install-app`、未改 compose。
- 未修第五节列出的其余 9 处无守卫写接口（只盘点、只修班次管理这一处）。
- 未做门户导航改造（见第八节）。
- 未接飞书真实写入，未提交任何真实数据 / 截图 / Excel / CSV。
- 未移入 `docs/experience/`（见第八节）。

## 八、遗留与风险（记录，不修）

1. **两个原生子页无导航入口**（可用性问题，非缺陷）。`/hbos/attendance/employees` 与 `/hbos/attendance/board` 路由可用、后端白名单已登记、直连 URL 实测正常，但**门户侧没有任何链接指向它们**（门户的应用内导航 `AppLocalSidebar.vue` 是 LIMS 专用，考勤没有对应侧栏）。属于**新前端开发活动**，按 `docs/frontend/FRONTEND_IMPLEMENTATION_GUIDE.md` 的原型先行 Gate，需先出原型并经 Owner 审查，故本轮**不擅自加导航**。

2. **设计文档引用悬空**。本轮及上一批代码多处引用 `docs/experience/EA-4_DESIGN_SYSTEM_V1.md`（设计令牌与分档）与 `EA-5.4_COMPONENT_INTERACTION_SPEC.md`（字号契约 v2.0），但**本分支没有 `docs/experience/` 目录**——该目录只存在于 `main`（EA-1~EA-4）与 `origin/p4/inventory-frontend-audit`（含 EA-5.x 全文）。Owner 2026-09-29 裁定：**保留引用，不移植**，在本文件留档即为此项说明。后果：注释里的「依据」在本分支内**无法就地核对**，审查者需切到 p4 系分支查阅。

3. **iframe 通路仍保留**。本轮只把考勤三个页面改为原生，`BusinessEmbedView.vue`、`businessRoutes.ts`（现为空表，同时充当 iframe 白名单）、Vite 的 12 条 Frappe 代理前缀**均未删除**——其他 App（LIMS / 库存）仍可能需要。

4. **Vite 代理覆盖缺口与 3 个 CSS bundle 既有 404** 未处理，同 M3-PORTAL-R1 已记录的缺口。M3 文档记的 CSS 哈希（`desk.bundle.VALCFTBN.css` 等）在实测中已随 Frappe 重新构建变为新哈希且**返回 200**，即该项**可能已自愈**，待后续轮次确认。

5. **`M3_START_GATE.md` 不存在**。按 `AGENTS.md`，`M3_START_GATE.md` 应在 M3 启动前创建；实际只有 `M1_START_GATE.md`，`M2` / `M3` / `M4` 均未创建门禁文档。属既有治理缺口（非本轮引入），需 Owner 决定是否补建。

6. **第五节列出的 9 处无守卫写接口**。其中 `employee_management_data.bind_shift` / `bulk_bind_shift` 优先级最高（与已修部分同级爆炸半径）。

## 九、提交划分

本轮改动按性质拆两个提交（便于独立审查）：

1. **前端工作台改造**（工作流 A + B + 清理）：门户原生三页、Desk 共享视觉层、mock 对齐、`build.json` 与 `.gitignore` 清理。
2. **班次管理写接口服务端 RBAC**（工作流 C）：与前端无耦合，独立成提交。

## 十、状态台账更新

- `docs/PROJECT_STATUS.md`：M3-PORTAL-R1 节新增本后续交付；状态口径行同步。
- `docs/CURRENT_MILESTONE.md`：M3-PORTAL-R1 段落新增本后续交付；「下一轮预告」同步。
- `docs/milestones/README.md`：文件索引新增本文件；M3 行说明补齐。
- `README.md`：修正过期描述「R4 生产形态未启动」（R4 已于 2026-09-28 交付）。
