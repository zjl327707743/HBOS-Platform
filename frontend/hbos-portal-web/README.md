# HBOS Portal Web

HBOS Workspace / Portal 的 Vue 3 高保真前端骨架。

当前阶段：**EA-5.4 Design Engineering / Frontend Reproduction**。

## 技术栈

- Vue 3
- Ant Design Vue
- Vue Router
- Pinia
- Axios（后续 API Adapter 使用；当前不接真实业务 API）
- Vite
- TypeScript
- ECharts（需要图表时再引入）

## 已实现的产品骨架

- `/hbos` — Home
- `/hbos/work` — My Work
- `/hbos/apps` — App Center
- `/hbos/profile` — Profile / Settings
- `/hbos/403` — 403
- 404
- `/hbos/lims` — 独立 LIMS App Shell
- Global Header
- App Switcher
- Notification Center
- Command Palette（⌘K / Ctrl+K）
- Digital Twin Portal Overview
- Pointer Aurora + low-opacity particle trail
- Reduced Motion 降级

## 视觉 Authority

- `docs/experience/EA-5.3_PRODUCT_INTERACTION_REVIEW.md`
- `docs/experience/EA-5.4_COMPONENT_INTERACTION_SPEC.md`
- `docs/experience/prototypes/EA-5.3_VISUAL_BASELINE.html`

## 数据边界

当前仅使用 Mock Provider + DTO 验证产品体验。

前端不得直接读取业务 DocType。正式功能接入必须通过：

```text
Portal UI
  ↓
Portal DTO / Provider Contract
  ↓
Attendance / Inventory / LIMS Provider
  ↓
Application Service / Domain
```

没有真实 capability 的业务块必须隐藏、空状态或独立降级，禁止为了填满首页伪造生产业务数据。

## 本地运行

```bash
npm install
npm run dev
```

## 构建

```bash
npm run build
```

> 当前提交环境访问 npm registry 超时，因此本轮未声称依赖安装 / Vite build 已通过。已完成源码结构和 TypeScript 静态语法检查；依赖可用的 CI / 本地 Node 环境必须继续执行正式 build Gate。

## 当前禁止范围

本阶段不包含：

- `apps/hbos_portal`
- Frappe API 接入
- 真实 App Registry
- 真实业务 Provider
- 第二套身份 / JWT / Role
- Attendance / Inventory / LIMS 业务逻辑
