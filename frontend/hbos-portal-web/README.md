# HBOS Portal Web

## 人员与权限：完整Site恢复执行组件离线验证 — 2026-10-10

当前进度 **S02_FULL_SITE_RESTORE_COMPONENTS_OFFLINE_VALIDATED / PARTIAL / REVIEWING / 5178_REAL_READONLY**；[本轮主记录](../../docs/milestones/M2_人员权限完整Site恢复执行组件实施记录.md)、[验收摘要](../../docs/milestones/evidence/人员权限_完整Site恢复执行组件验收摘要_20261010.json)。**222/222离线PASS**，20文件Python3.10 AST通过；安全私有落地、有限stdio / 固定loopback转发组件和内存生命周期规划已实现。真实ROOT / clone恢复 / 解密 / 网络 / 本人登录NOT_RUN，listener / 可信持久登记 / 全阶段执行清理未实现，生产服务HARD_BLOCKED。

本轮20次Docker只读源码 / UID核验，两段五角色metadata MATCH，零原SQL / 服务控制 / 真实资源创建。源码PID1为Frappe1000:1000、DB999:999、Redis999:1000；新卷初始化未核。登录hash升级 / Hook / 通知 / 重置 / 2FA副作用未闭合，有限写入NOT_READY。下一步先补这些运行门禁及执行器，不提前请求创建运行许可。5178保持既有真实只读，管理GET NOT_READY / POST关闭 / Grant NOT_RUN；S01-B/S02 PARTIAL、C/S03—S06 NOT_STARTED、P4-F6-5 REVIEWING与所有旧门禁保留。状态 / 本轮主记录 / M2 Gate / 相关规范 / 公共入口同步，CLAUDE / AGENTS仅规则检查。无新分支、提交、推送或部署。以下前序记录只表示当时状态，以本段为准。


前序安全层记录（2026-10-10）：**S02_FULL_SITE_RESTORE_GUARDS_OFFLINE_VALIDATED / PARTIAL / REVIEWING / 5178_REAL_READONLY**；[安全工具实施记录](../../docs/milestones/M2_人员权限完整Site恢复安全工具实施记录.md)、[验收摘要](../../docs/milestones/evidence/人员权限_完整Site恢复安全工具验收摘要_20261010.json)与[执行包](../../docs/plans/人员权限_完整Site恢复执行包.md)。新增11个 release 校验源码 / 测试文件，**94/94离线PASS**（input35/ownership29/relay20/plan10），Python3.12.14及3.10 AST通过。真实既有五备份 / before只读验证PASS，public0/private9/auth2、gzip SQL29683935bytes；未提取 / 解密 / 导入或连接原SQL。默认CLI只打印提案，无执行参数；5容器/0新网络/9卷/1relay矩阵均不可执行，UID / 新DB ID仍占位。 守卫只验证输入、最小HTTP政策、namespace-precheck元数据与精确清理argv；healthcheck禁用、daemon日志none、restart=no。没有Docker调用、服务控制、网络访问或资源创建，未改变原App / 前端 / schema / 配置 / Compose。 恢复执行器、realpath / 创建登记、listener / stdio传输、完整exec清理 / 截止时间、登录有限副作用与请求全清单仍待完成；完整恢复 / 网络实测 / 本人登录NOT_RUN，运行NOT_READY。下一步先补这些代码与离线审查，使行动具体可复核，再核对精确Owner创建运行许可。5178保持既有真实只读，GET NOT_READY/POST关闭/Grant NOT_RUN；S01-B/S02 PARTIAL，C/S03—S06 NOT_STARTED，P4-F6-5 REVIEWING及全部旧门禁保留。以下前序记录仅表示当时状态，接续以本段为准。

前序完整Site恢复准备记录（2026-10-10，当时状态）：**S02_FULL_SITE_RESTORE_PREPARATION_REVIEWED / PARTIAL / REVIEWING / 5178_REAL_READONLY**；[完整Site恢复准备](../../docs/milestones/M2_人员权限完整Site恢复准备记录.md)、[摘要](../../docs/milestones/evidence/人员权限_完整Site恢复准备摘要_20261010.json)、[执行包](../../docs/plans/人员权限_完整Site恢复执行包.md)。本轮仅检查运行元数据、源文件与备份hash，零原SQL连接、无App初始化/服务控制/资源创建/新快照复制。9 App与完整env已盘点，尚非原子快照；Node依赖内容未盘点、env有变化，不能仅原镜像复原。复制/落地/实际解密/App启动/本人登录/实际网络验收NOT_RUN。singlebridge准备提案已弃用；none+container:本次新DBnetns与宿主受限HTTP relay（含受控exec子进程）尚未实现，网络执行NOT_READY，5组件互访同clone loopback，非peer端口ACL，提案要求克隆Docker组件无publish/原网络。克隆须作废旧Sessions。a7d3的5容器/0新Docker网络/9卷/1宿主受限HTTP relay提案未创建，hbos-restore.localhost:18092不变；下一步先实现并离线审查安全恢复工具、请求白名单和命令/挂载矩阵，再请求具体Owner创建运行许可，当前不询问执行许可；双栈解析与20GiB阈值不证明入口或峰值。GET NOT_READY/POST关闭/Grant NOT_RUN，全部旧门禁保留。无代码变更、历史测试未重跑。

前序人员与权限记录（2026-10-10，原站备份与隔离SQL验收）：[原站备份与隔离SQL验收](../../docs/milestones/M2_人员权限原站备份与隔离SQL验收记录.md)已完成，**S02_ORIGINAL_BACKUP_SQL_RESTORE_VALIDATED / PARTIAL / REVIEWING / 5178_REAL_READONLY**（[验收摘要](../../docs/milestones/evidence/人员权限_原站备份与隔离SQL验收摘要_20261010.json)）。Owner确认窗口后，最终备份attempt4 PASS、8.400962125秒，原websocket暂停/解冻及其余窗口服务恢复，同12个原容器公开原态与最终元数据（挂载数组规范排序）匹配，原生八表/配置hash/旧4文件与2目录保全；源私有0700/0600，6个验证输入加manifest共7文件源/主机hash匹配。隔离SQL、账户与业务关联指纹及三类归档读取PASS（User18/凭据6/User角色关联103），新容器/卷/临时凭据已清理；5178人员页200、ping pong、两RQ worker注册/订阅/PID1/hostname匹配且空闲。两次producer失败的备份NOT_STARTED且原12公开状态MATCH、SIGINT位误读已更正；第一次SQL验收因挂载数组顺序误报FAIL，原报告保留，规范排序后另报告重验PASS。全局事务UNAVAILABLE/认证1045、websocket内部自动重启与完整连续冻结证据NOT_VERIFIED；完整Site文件落地/key解密/原App启动/本人业务登录恢复NOT_RUN。八管理表仍缺失，管理GET NOT_READY、POST关闭、Grant NOT_RUN。S01-B/S02 PARTIAL、C/S03—S06 NOT_STARTED、P4-F6-5 REVIEWING及全部原Q1/Q2、Date、固定P1/完整恢复/Owner与管理门禁保留。正式源码/测试/前端/配置/schema及Compose未改，未安装/创建App或创建bench；实际停启/冻结与私有备份已执行，14原生/428离线等历史测试本段未重跑，无commit/push/新分支。以下保留前序交付当时的记录。


前序只读预检（2026-10-10，备份执行前）：[原站只读预检](../../docs/milestones/M2_人员权限原站只读预检记录.md)已完成，**S02_ORIGINAL_READONLY_PREFLIGHT_COMPLETED / PARTIAL / REVIEWING / 5178_REAL_READONLY**。实际frontend / DB摘要精确匹配，五来源InnoDB与24必需列PASS，COUNT18/0/1/14/31；八管理表全缺，正式预检在tables以STORAGE_PREFLIGHT_SCHEMA_INVALID停止。10诊断SELECT含正式预检2，零transaction_writes、rollback/destroy PASS，未初始化。只读诊断完成不等于结构或启用PASS；管理GET仍NOT_READY。原站备份工具release路径缺失，现已有镜像 / 权限 / 磁盘 / 备份总量仅元数据确认，原样stdin备份操作包已准备但未执行。下一段先确定停写一致性窗口 / 原服务恢复措施，再按同次私有备份与隔离SQL恢复范围执行；不建表 / 人员 / 政策 / pins或启GET。5178既有真实只读；本段未改代码 / 配置 / 服务 / 缓存 / schema，未备份 / 恢复或浏览器复验。前段14原生 / 428离线PASS为历史证据，本段未重跑。S01-B/S02 PARTIAL，C/S03—S06 NOT_STARTED，Grant NOT_RUN，P4-F6-5 REVIEWING；原Q1/Q2、Date、固定P1 / 完整恢复 / Owner及管理门禁保留。 以下为前序交付当时的记录。

2026-10-09 后端接续：[S01-B 来源适配基础](../../docs/milestones/M2_人员权限S01B来源适配实施记录.md)已实现并通过 65 项针对性离线测试（新适配 37 + A 回归 28），结果运行未验证；B 仍 PARTIAL，下一段为 S02 基础岗位 / 任职存储及受控服务。本次未修改前端、API 或 5178 真实只读运行方式，未重跑前端测试。下方 126 项前端验证为前序证据。

2026-10-08 人员与权限：**5178_REAL_READONLY / FRONTEND_REAL_READONLY_REVIEWING**。按 Owner 指令，当前 [5178 人员页](http://127.0.0.1:5178/hbos/admin/people) / [角色页](http://127.0.0.1:5178/hbos/admin/roles)接入真实 Frappe 读取，使用既有会话和原生权限；User / Employee 显式选择，手机号服务端脱敏，错误不回退到合成数据，未接入的写入全部禁用。真实模式导航和路由已开放，构建包含只读页面并排除本次 Mock 页面 / 夹具；5193 仅保留旧演示资产。S01-A 已完成纯协议与离线校验，整体 S01 PARTIAL，B / C 与 S02—S06 未开始，岗位授权未启用。前端 Vitest 91 + Node 35 及类型 / lint / Mock Gate / LIMS 契约 / 真实构建通过；详情见[实施主记录](../../docs/milestones/M2_人员权限5178接入与S01A实施记录.md)。不替代固定 P1 或 Owner 真实授权验收。以下为其他任务和前序记录。

当前飞书登录已启用（2026-10-08）：Owner 保存精确回调后，控制台已显示该 URL 且当前修改已发布；飞书授权页正常出现，20029 消失。当前 frontend Site 的 HTTP 状态 configured=true、missing=[]，PKCE 与浏览器绑定验证通过。本次没有点击本人授权或创建账号，绑定记录仍为 0；正常登录从 [5178 登录页](http://127.0.0.1:5178/hbos/login)发起，原 Administrator 须本人验证绑定，不自动关联。见[整改记录 §15](../../docs/experience/LIMS_P4-F6-5_前端审核整改记录.md#15-2026-10-08-当前-site-飞书登录启用准备)。状态为 FEISHU LOGIN ENABLED / OWNER OAUTH PENDING，P4-F6-5 REVIEWING 与权限 / P1 门禁不变。以下为前序记录。

HBOS Workspace / Portal 的 Vue 3 + Ant Design Vue 前端。

当前阶段：**P4-F6-5 REVIEWING / 2026-10-08 飞书登录已启用 / 完整真实流程与 Owner 验收待完成**。

2026-10-08：个人资料与管理后台使用 Frappe `/desk/user/<当前用户>` 和 `/desk` 原生整页链接，避免后台路径落入 Portal 404。`VITE_FRAPPE_APP_ORIGIN` 未显式配置时，开发模式跟随实际 `VITE_FRAPPE_PROXY_TARGET`（含隔离预览），生产构建保持同源；显式配置优先。前端 105 项测试及工程检查通过，实际匿名路由已验证，登录后内容待 Owner 复验。见[整改记录 §14](../../docs/experience/LIMS_P4-F6-5_前端审核整改记录.md#14-2026-10-08-个人资料与管理后台入口修复)。

2026-10-08：既有 frontend 测试 Site 的开发来源补齐 `http://127.0.0.1:5178`，浏览器虚构账号已进入密码校验，真实账号成功登录待 Owner 复验。开发来源必须完整、显式配置在 `hbos_portal_development_origins`，并且仅对已有 `hbos_account_test_site` 生效；不要为生产站点启用该测试标志。生产使用配置的规范来源。`localhost` 与 `127.0.0.1` 不是同一来源，Origin 与代理 Host 的主机名也必须一致；刷新页面无法修复未获准来源。详见[整改记录 §13](../../docs/experience/LIMS_P4-F6-5_前端审核整改记录.md#13-2026-10-08-退出后密码登录来源修复)。

2026-10-07：5178 无监听导致连接失败，已用现有 `dev:frappe` 命令恢复 127.0.0.1:5178 → 8080；首页 / 登录 / LIMS 入口、Vite 模块和 ping 代理检查通过，匿名 Bootstrap 403。只恢复前端进程并同步文档，没有改动源码、Site 或真实账号。详见[整改记录 §12](../../docs/experience/LIMS_P4-F6-5_前端审核整改记录.md#12-2026-10-07-恢复-5178-开发入口)。这不是固定 P1 5188 的恢复或权限盘点完成。

当前本地开发分支：`m2-r11`，沿用 Owner 已指定分支；2026-10-01 的 `m2-r10` 合并记录为前序基线。

## 数据模式

Portal 前端明确支持两种模式。

### 1. Mock 模式

必须显式选择（未配置或拼写错误会停止启动）：

```bash
VITE_PORTAL_DATA_MODE=mock
```

用途：

- UI / Experience 原型开发；
- 不要求 Frappe 运行；
- 动态加载 `src/data/mockPortal.ts`，全站显示「演示数据」标识；
- 不作为真实运行态验收依据。

### 2. Frappe 模式

```bash
VITE_PORTAL_DATA_MODE=frappe
VITE_FRAPPE_PROXY_TARGET=http://127.0.0.1:8080
VITE_FRAPPE_APP_ORIGIN=http://127.0.0.1:8080
```

实际端口以项目根目录私有 `.env` 的 `HTTP_PORT` 为准。

其他环境变量：`VITE_BASE` 默认为 `/`，同时用于静态资源和前端路由基路径；`VITE_FRAPPE_BASE_URL` 默认为空，API 使用当前 origin 的 `/api`（开发时由 Vite 代理）。通常保持该值为空；如指向独立 API origin，须由部署环境配置携带凭证的 CORS 和 Session Cookie。变量示例见 `.env.example`。

用途：

- 调真实 `hbos_portal` API；
- API 请求通过 Vite proxy 保持 Portal 开发同源；
- Attendance / Inventory 的业务页面按 Provider Resolver 返回路径通过 `VITE_FRAPPE_APP_ORIGIN` 打开 Frappe origin；LIMS `/hbos/lims/*` 保持在 Portal 同源前台，Dashboard、Task Board、Result List / Result Entry、受控结果台账与审计追踪已接入，其他业务页按实现进度逐项开放；
- 使用现有 Frappe Session；
- 不创建第二套登录；
- 只渲染真实 Registry / Provider 暴露的能力。

当前真实 endpoint 包括：

```text
/api/method/hbos_portal.api.bootstrap.get_bootstrap
/api/method/hbos_portal.api.summary.get_summary
/api/method/hbos_portal.api.tasks.get_tasks
/api/method/hbos_portal.api.results.get_results
/api/method/hbos_portal.api.ledger.get_ledger
/api/method/hbos_portal.api.audit.get_audit
/api/method/hbos_portal.api.coa.get_coas
/api/method/hbos_portal.api.specifications.get_specifications
/api/method/hbos_portal.api.retention.get_retention
/api/method/hbos_portal.api.stability.get_stability
/api/method/hbos_portal.api.search.search
/api/method/hbos_portal.api.routes.resolve_route
```

## 当前三 APP 真实能力

```text
LIMS
  Entry / Access / Stable Route = enabled
  Provider Summary / Tasks / Search = enabled
  LIMS Shell 页面目标 = dashboard / Task Board / Result List / Result Entry / Ledger / Audit / COA / Quality Standards / Retention / Stability Workbench 已接入；样品列表与登记暂保持同源 pending，等待独立 Provider 读取 / 登记契约门禁；审计入口按 `lims.audit.read` 访问能力门控，COA、质量标准、留样和稳定性工作台为只读；稳定性工作台已完成 Mock 运行态预览，管理后台页头入口保持关闭

Attendance
  Entry / Access / Stable Route = enabled
  HR Summary = enabled
  Tasks / Search = gated
  Ordinary Employee Entry = gated

Inventory
  Entry / Access / Stable Route = enabled
  Permission-aware Summary = enabled
  Tasks / Search = gated
```

真实 Frappe 模式不得使用 Mock 数据填充缺失能力。

Inventory Summary 只基于当前会话用户可见的 Warehouse 范围读取 ERPNext Bin，并只投影计数型指标；不会直接复用现有 raw-SQL 库存报表，也不会跨不同 UOM 汇总数量。

## 推荐：完全隔离临时预览

如果目标只是让 Agent 临时启动、人工查看，而不影响原 `frontend` Site / 8080 / 原 Docker volumes，优先使用：

```bash
bash scripts/portal/start_isolated_preview.sh
```

默认隔离资源：

```text
Docker project = hbos-portal-preview
Preview Site   = portal-preview.localhost
Frappe         = http://127.0.0.1:18091
Portal         = http://127.0.0.1:5179
```

该模式使用独立 Compose project、独立 database / Redis / sites / assets volumes 和独立端口；外部飞书、得力云、AI 同步全部禁用。启动脚本还会比较启动前后的 Docker container / volume 清单，若出现非 preview namespace 的新资源则停止并要求人工审查。

停止但保留 preview volumes：

```bash
bash scripts/portal/stop_isolated_preview.sh
```

彻底清理 preview 环境：

```bash
bash scripts/portal/stop_isolated_preview.sh --purge
```

`--purge` 只对 `hbos-portal-preview` Compose project 执行，不对原项目执行 `down -v`。

隔离 preview Site 是 clean site，因此不会包含原 `frontend` Site 的真实业务数据。这是临时 UI / integration review 的推荐模式。

## 本地运行

推荐使用仓库根目录的一键启动脚本：

```bash
bash scripts/portal/start_local_workspace.sh
```

它会：

- 启动现有 Frappe / ERPNext / HBOS Docker 服务；
- 确保 `hbos_portal` 已安装到当前 Site；
- 验证 Attendance / Inventory / LIMS 三个 Provider 已注册；
- 以 `frappe` 数据模式启动 Portal Vite；
- 默认在 `http://127.0.0.1:5178` 提供工作台。

按 `Ctrl+C` 只停止 Portal Vite，Docker 业务服务保持运行。

如需完整运行态验收而不是持续开发：

```bash
bash scripts/portal/p3_workspace_runtime_smoke.sh
```

该脚本会验证：

- 七个 Site App；
- 三业务 Provider Registry；
- Portal Bootstrap；
- Inventory Summary；
- 三 APP Stable Route；
- Administrator Frappe Session；
- Vite → Frappe Session/API 代理链。

Smoke 结束时会自动关闭本次临时 Vite 进程，不删除 Docker volume、不重建 Site、不写 Attendance / Inventory / LIMS 业务事实。

## 手工启动

需要手工运行时，先确保 Frappe 已在根目录 `.env` 的 `HTTP_PORT` 启动，然后：

```bash
cd frontend/hbos-portal-web
npm ci --no-audit --no-fund

VITE_PORTAL_DATA_MODE=frappe \
VITE_FRAPPE_PROXY_TARGET=http://127.0.0.1:8080 \
VITE_FRAPPE_APP_ORIGIN=http://127.0.0.1:8080 \
npm run dev -- --host 127.0.0.1 --port 5178
```

若 `HTTP_PORT` 不是 8080，请替换 proxy target。

`dev` 是 Vite 的开发运行方式，`frappe` / `mock` 是数据来源，两者不是同一维度。`npm run dev` 未显式设置 `VITE_PORTAL_DATA_MODE` 时会直接失败；常用简写与默认端口如下：

| 用途 | 端口 | 数据来源 |
|---|---|---|
| 本机开发工作台 | `5178` | `frappe`，默认 API 代理到 `8080`，可由环境变量覆盖 |
| 隔离 Frappe 预览 | `5179` | `frappe`，由隔离脚本代理到 `18091` |
| 临时 UI 演示 | `5193` | `mock`，不连接真实后端 |

开发服务启用 `strictPort`，端口占用时直接失败，避免自动切换到另一工作线的端口。

```bash
# 真实后端（frappe 模式，/api 代理到 Frappe）
VITE_FRAPPE_PROXY_TARGET=http://127.0.0.1:8080 \
VITE_FRAPPE_APP_ORIGIN=http://127.0.0.1:8080 \
npm run dev:frappe -- --host 127.0.0.1

# 仅 UI 演示（mock 模式，不连后端，禁止作为真实运行态证据）
npm run dev:mock -- --host 127.0.0.1
```

侧栏与业务页面使用同一套源码，Mock 验证不能替代真实运行态验收。若源码中的 Provider 能力已更新，但真实 Bootstrap 仍返回旧能力，应核对后端源码挂载、刷新 Frappe 缓存并重启对应开发后端 Web 服务，再重新加载 Portal。若重启后出现 502，应检查现有 Nginx 是否仍缓存旧容器地址，确认后重载代理；不要为显示菜单而绕过 capability 门控。2026-10-02 已按此流程恢复本机 5178 的完整 LIMS 专业菜单，详细证据见 `docs/experience/LIMS_P4-F6-5_前端审核整改记录.md` §10。

## 回归验证

```bash
npm run lint
npm run test:unit
npm run test:contract
npm run test:mock-gate
bash ../../scripts/portal/lims_shell_contract.sh
```

单元回归使用隔离 Provider 夹具和真实 Vue/Store/守卫逻辑，不需要运行 Frappe；源码契约检查用于保护关键接线。真实 Session 联调仍是独立验收项。

## 构建

生产构建必须明确使用 Frappe 数据源，禁止回退演示数据：

```bash
VITE_PORTAL_DATA_MODE=frappe npm run build
```

演示开发与演示构建使用独立命令，不能作为真实运行态证据：

```bash
npm run dev:mock
npm run build:mock
```

CI 在 `m2-r10` 上使用 `npm ci`，执行 ESLint、单元/组件回归、前端契约、Shell 契约、Mock 内容门控和真实模式生产构建。

## 技术栈

- Vue 3
- Ant Design Vue
- Vue Router
- Pinia
- Axios
- Vite
- TypeScript
- SVG 稳定性趋势图（当前没有 ECharts 依赖）

## 设计与架构 Authority

- `docs/experience/EA-3_APPLICATION_CONTRACT_ACCESS.md`
- `docs/experience/EA-4_DESIGN_SYSTEM_V1.md`
- `docs/experience/EA-5.4_COMPONENT_INTERACTION_SPEC.md`
- `docs/experience/P1_HBOS_Portal平台App架构.md`
- `docs/frontend/FRONTEND_IMPLEMENTATION_GUIDE.md`

Portal 是 Experience Shell，不拥有 Attendance / Inventory / LIMS 业务事实。
