# HBOS Portal Web

HBOS Workspace / Portal 的 Vue 3 + Ant Design Vue 前端。

当前阶段：**EA-5.5 COMPLETE / P3 THREE-APP WORKSPACE INTEGRATION**。

## 数据模式

Portal 前端明确支持两种模式。

### 1. Mock 模式

默认：

```bash
VITE_PORTAL_DATA_MODE=mock
```

用途：

- UI / Experience 原型开发；
- 不要求 Frappe 运行；
- 使用 `src/data/mockPortal.ts`；
- 不作为真实运行态验收依据。

### 2. Frappe 模式

```bash
VITE_PORTAL_DATA_MODE=frappe
VITE_FRAPPE_PROXY_TARGET=http://127.0.0.1:8080
VITE_FRAPPE_APP_ORIGIN=http://127.0.0.1:8080
```

实际端口以项目根目录私有 `.env` 的 `HTTP_PORT` 为准。

用途：

- 调真实 `hbos_portal` API；
- API 请求通过 Vite proxy 保持 Portal 开发同源；
- Provider Resolver 返回的业务页面通过 `VITE_FRAPPE_APP_ORIGIN` 打开 Frappe origin，避免 `/app/...` 或 `/hbos-lims/...` 落到 Vite 404；
- 使用现有 Frappe Session；
- 不创建第二套登录；
- 只渲染真实 Registry / Provider 暴露的能力。

当前真实 endpoint 包括：

```text
/api/method/hbos_portal.api.bootstrap.get_bootstrap
/api/method/hbos_portal.api.summary.get_summary
/api/method/hbos_portal.api.tasks.get_tasks
/api/method/hbos_portal.api.search.search
/api/method/hbos_portal.api.routes.resolve_route
```

## 当前三 APP 真实能力

```text
LIMS
  Entry / Access / Stable Route = enabled
  Summary / Tasks / Search = enabled

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
npm install --no-audit --no-fund --package-lock=false

VITE_PORTAL_DATA_MODE=frappe \
VITE_FRAPPE_PROXY_TARGET=http://127.0.0.1:8080 \
VITE_FRAPPE_APP_ORIGIN=http://127.0.0.1:8080 \
npm run dev -- --host 127.0.0.1 --port 5178
```

若 `HTTP_PORT` 不是 8080，请替换 proxy target。

## 构建

```bash
npm run build
```

## 技术栈

- Vue 3
- Ant Design Vue
- Vue Router
- Pinia
- Axios
- Vite
- TypeScript
- ECharts（按需）

## 设计与架构 Authority

- `docs/experience/EA-3_APPLICATION_CONTRACT_ACCESS.md`
- `docs/experience/EA-4_DESIGN_SYSTEM_V1.md`
- `docs/experience/EA-5.4_COMPONENT_INTERACTION_SPEC.md`
- `docs/experience/P1_HBOS_Portal平台App架构.md`
- `docs/frontend/FRONTEND_IMPLEMENTATION_GUIDE.md`

Portal 是 Experience Shell，不拥有 Attendance / Inventory / LIMS 业务事实。
