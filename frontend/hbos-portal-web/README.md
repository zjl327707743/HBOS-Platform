# HBOS Portal Web

HBOS Workspace / Portal 的 Vue 3 + Ant Design Vue 前端。

当前阶段：**EA-5.5 COMPLETE / P2.1 Bootstrap Adapter**。

## 数据模式

Portal 前端明确支持两种模式。

### 1. Mock 模式

默认：

```bash
VITE_PORTAL_DATA_MODE=mock
```

用途：
- UI / Experience 开发；
- 不要求 Frappe 运行；
- 使用 `src/data/mockPortal.ts`。

### 2. Frappe 模式

```bash
VITE_PORTAL_DATA_MODE=frappe
VITE_FRAPPE_PROXY_TARGET=http://127.0.0.1:8081
```

用途：
- 调真实 `hbos_portal` bootstrap；
- 使用现有 Frappe Session；
- 不创建第二套登录。

当前真实 endpoint：

```text
/api/method/hbos_portal.api.bootstrap.get_bootstrap
/api/method/hbos_portal.api.search.search
```

本地开发建议先在 Frappe 8081 登录，再运行 Vite 5178。Cookie 按同源主机通过开发代理转发。

## 当前真实接入边界

P2.1 只接 Portal Shell Bootstrap：

- current Frappe user；
- avatar URL；
- branding / company logo URL；
- visible app manifests；
- app access。

尚未接：
- Attendance summary / tasks；
- Inventory summary / tasks；
- LIMS summary / tasks；
- Digital Twin real provider。

因此 Frappe 模式下业务聚合区可以为空，这是正确的 capability-driven 行为，不应回退到伪造数据。

## 技术栈

- Vue 3
- Ant Design Vue
- Vue Router
- Pinia
- Axios
- Vite
- TypeScript
- ECharts（按需）

## 本地运行

```bash
npm install
npm run dev
```

## 构建

```bash
npm run build
```

Architecture authority：

- `docs/experience/EA-3_APPLICATION_CONTRACT_ACCESS.md`
- `docs/experience/P1_HBOS_Portal平台App架构.md`
