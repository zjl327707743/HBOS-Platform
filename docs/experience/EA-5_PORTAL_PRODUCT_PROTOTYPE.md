# HBOS Experience Architecture
## EA-5 — Portal Product Prototype

**状态：IN_PROGRESS / OWNER VISUAL GATE APPROVED**  
**工作分支：** `feature/hbos-portal-product`  
**Owner 授权日期：** 2026-09-24

## 1. 目的

EA-5 将 EA-1～EA-4 的体验架构落成可评审的 HBOS Portal 产品原型。

本阶段已经确认：

- Portal 是企业级用户工作空间，不是第四个业务系统；
- LIMS、Inventory、Attendance 等业务应用保持独立；
- Portal 固定导航不直接挂业务 APP；
- Business App 通过 App Center / App Switcher / Search / Command Palette / Deep Link 进入；
- Frappe Desk 继续作为 HBOS Management Console；
- 数字孪生是 HBOS 一级空间化能力，不应在产品扩展时被弱化；
- Portal 视觉母版采用 Bright Aurora + Layered Glass + Premium Motion。

## 2. 已完成的原型验证

EA-5 已覆盖：

- Home
- My Work
- App Center
- Command Palette
- Profile / Settings
- 403
- 404
- LIMS 独立 App Shell
- Digital Twin Portal Overview

Owner 已确认总体方向成立，并要求保留：

- 明亮、留白、清晰信息层级；
- 动态玻璃边缘和 Aurora 渐变；
- 高级低频背景 Motion；
- 鼠标跟随光场和柔光拖尾；
- 更大的 Global Header 和 Icon hit area；
- 数字孪生空间化入口。

## 3. Portal / Business App 边界

Portal 固定导航：

```text
首页
我的工作
应用中心

我的
设置
```

业务应用不进入 Portal 固定 Sidebar。

进入 LIMS 后：

```text
HBOS Global Header
        +
LIMS Local Navigation
        +
LIMS Business Content
```

Portal Sidebar 不继续显示。

## 4. 当前视觉母版

冻结参考：

- `docs/experience/prototypes/EA-5.3_VISUAL_BASELINE.html`

这份 HTML 是设计对照物，不是生产代码。

生产实现必须使用 Vue 3 + Ant Design Vue，并遵守：

- `docs/experience/EA-5.4_COMPONENT_INTERACTION_SPEC.md`
- `docs/frontend/FRONTEND_IMPLEMENTATION_GUIDE.md`

## 5. 数据原则

原型中的业务数据仅用于验证信息架构。

正式 Portal：

```text
Vue UI
  ↓
Portal DTO / Provider Contract
  ↓
Attendance / Inventory / LIMS Provider
  ↓
Application Service / Domain
  ↓
Frappe ORM / ERPNext / HRMS
```

没有真实 Provider capability 的模块必须隐藏、空状态或独立降级，禁止为了填满首页制造业务数字。

## 6. 当前 Gate

已通过：

- EA-1 Surface Responsibility
- EA-2 User Journey & IA
- EA-3 Application Contract & Access
- EA-4 Design System
- EA-5 Owner Visual Direction Gate
- EA-5.3 Product Interaction Review
- EA-5.4 Component & Interaction Specification

下一步：

- EA-5.5 Interaction QA + Responsive + Accessibility
- Vue 3 Portal Skeleton
- 再进入 `hbos_portal` Frappe App / Registry / Provider 实现

在 EA-5.5 结束前，不创建正式业务数据副本，不将 Portal 变成业务域 Owner。
