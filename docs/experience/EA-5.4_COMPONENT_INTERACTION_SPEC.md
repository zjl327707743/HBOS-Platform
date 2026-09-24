# HBOS Experience Architecture
## EA-5.4 — HBOS Component & Interaction Specification v1

**项目**：HBOS｜海滨智能运营管理平台  
**阶段**：EA-5.4  
**状态**：DESIGN ENGINEERING BASELINE  
**目标前端栈**：Vue 3 + Ant Design Vue + Vue Router + Pinia + Axios + ECharts  
**视觉母版**：EA-5.3 Visual Polish — Bright Aurora / Layered Glass / Premium Motion  
**适用范围**：HBOS Portal、未来 Native HBOS Business Apps、数字孪生入口  
**不适用范围**：Frappe Desk 内部所有原生页面的逐像素重构

---

# 1. EA-5.4 目标

EA-5.4 不再讨论“整体长什么样”。

本阶段把已经确认的 HBOS 视觉方向转成可以直接指导工程实现、代码 Review 和 UI 验收的组件规范。

必须解决：

1. 每个组件的尺寸、间距、字号和层级。
2. 每个组件的默认、Hover、Active、Focus、Disabled、Loading、Error 状态。
3. Portal 与 Business App 如何共享同一套组件语言。
4. 哪些视觉效果属于 V3 / V2 / V1 / V0。
5. 动效、鼠标跟随、玻璃层次在什么场景允许出现。
6. 中文界面如何保证可读性。
7. Ant Design Vue 组件如何被 HBOS Theme 包装，而不是直接裸用。
8. Desktop / Tablet / Mobile 如何响应式降级。
9. Keyboard、Reduced Motion、Focus、Contrast 等可访问性要求。
10. 为正式 `hbos_portal` 和后续业务 APP 前端提供设计冻结依据。

---

# 2. 已冻结的设计原则

## 2.1 视觉母版

HBOS 正式采用：

- Bright Aurora
- Layered Glass
- Premium Motion
- Clear Chinese Information Hierarchy
- Colorful Domain Identity
- Digital Twin Spatial Experience

不再回退到：
- 纯 Ant Design 默认后台
- 全深色 Dashboard
- 全屏高饱和渐变
- 大量 Emoji 作为产品 Icon
- 每个 APP 自己设计一套视觉语言

---

## 2.2 Visual Intensity

### V3 — Expressive / Immersive
适用：
- Portal Home
- App Center
- Command Palette
- Digital Twin
- AI
- Executive / Personal Workspace

允许：
- Aurora Gradient
- Strong Glass
- Mouse-follow Light Field
- Subtle Particle Trail
- 大型 Hero Typography
- Spatial Depth

### V2 — Application Dashboard
适用：
- LIMS 首页
- Inventory 首页
- Attendance 首页
- Equipment Dashboard

允许：
- Medium Glass
- Domain Accent
- KPI / Chart
- 轻量动画
- 局部 Aurora

### V1 — Operational
适用：
- 检验结果录入
- 复核
- 审批
- 仓储操作
- 考勤异常
- 排班
- 盘点

要求：
- 信息效率第一
- 动态背景关闭
- Glass 降为 Light
- 布局稳定
- 表格与表单性能优先

### V0 — Management
适用：
- Frappe Desk
- 系统设置
- 权限
- Master Data
- 技术管理

要求：
- 功能优先
- 只保留 HBOS Branding 和返回入口

---

# 3. Foundation Tokens

## 3.1 Spacing

统一 4px 基础单位。

| Token | px | 用途 |
|---|---:|---|
| `space-1` | 4 | 微间距 |
| `space-2` | 8 | Icon / Label |
| `space-3` | 12 | 控件内部 |
| `space-4` | 16 | Card 基础 padding |
| `space-5` | 20 | 稍大 Card |
| `space-6` | 24 | 页面 section |
| `space-8` | 32 | 页面大区块 |
| `space-10` | 40 | Hero 内部 |
| `space-12` | 48 | 大布局 |
| `space-16` | 64 | 页面留白 |
| `space-20` | 80 | 超大空间 |

禁止随意出现 `13px / 17px / 29px` 等无 Token 间距，除非组件确有像素级对齐需求。

---

## 3.2 Radius

| 场景 | Radius |
|---|---:|
| 小控件 | 8px |
| Button / Input | 10–12px |
| Normal Card | 16–18px |
| Large Card | 22–24px |
| Hero | 28–32px |
| App Icon | 15–17px |
| Pill / Tag | 999px |

---

## 3.3 Typography

中文优先。

字体：

```css
font-family:
  Inter,
  "SF Pro Display",
  "PingFang SC",
  "Noto Sans SC",
  "Microsoft YaHei",
  system-ui,
  sans-serif;
```

### Desktop

| 层级 | 字号 | Weight | 用途 |
|---|---:|---:|---|
| Hero Display | 56–68 | 850–900 | Portal Hero |
| Page H1 | 32–40 | 800–900 | 页面标题 |
| Section H2 | 20–22 | 800–850 | 模块标题 |
| Card H3 | 14–16 | 750–850 | 卡片标题 |
| Body | 14 | 400–600 | 正文 |
| Dense Body | 13 | 400–600 | 表格 |
| Metadata | 11–12 | 400–650 | 元信息 |
| Micro Label | 10–11 | 700–850 | 技术微标签 |

### Mobile

Hero Display：40–46px  
Page H1：28–32px  
Section：18–20px  
Body：14px 不降低。

### 中文规则

- 中文正文禁止低于 12px。
- 11px 只允许元信息。
- 10px 只允许 Micro Label。
- 中文标题 Letter Spacing 默认 `0 ~ -0.5px`。
- 不对中文使用大量 uppercase / tracking。
- 英文品牌词如 HBOS / LIMS / AI 可保留英文。
- 操作按钮优先使用中文动词。

---

# 4. Glass System

## G3 — Strong Glass
仅 V3。

```css
background: rgba(255,255,255,.54~.76);
backdrop-filter: blur(24~30px) saturate(120~135%);
border: 1px solid rgba(255,255,255,.82~.90);
box-shadow:
  0 18px 56px rgba(47,72,117,.09),
  inset 0 1px rgba(255,255,255,.78);
```

使用：
- Portal Header
- Hero
- Command Palette
- App Center
- Digital Twin major panel

## G2 — Medium Glass
V2 Dashboard。

Blur：18–22px  
Opacity：0.58–0.78

## G1 — Light Glass
V1 Operational。

Blur：8–14px，或完全取消 Blur。  
主要依靠 Surface / Border / Shadow。

---

# 5. Motion Tokens

| Token | Duration |
|---|---:|
| `motion-instant` | 100ms |
| `motion-fast` | 140–180ms |
| `motion-control` | 180–220ms |
| `motion-panel` | 220–300ms |
| `motion-page` | 300–420ms |
| `motion-ambient` | 8–16s |

推荐 Easing：

```css
--ease-standard: cubic-bezier(.2,0,0,1);
--ease-enter: cubic-bezier(0,0,0,1);
--ease-exit: cubic-bezier(.4,0,1,1);
```

禁止：
- 强 Bounce
- 快速循环动画
- 业务表单持续动画
- 数据表格中无意义 Motion

---

# 6. Pointer Atmosphere

这是当前选定视觉的重要组成部分，但仅用于 V3。

## 6.1 Mouse Follow Aurora

- 光斑尺寸：420–520px。
- 低透明度。
- 颜色：Violet / Blue / Aqua。
- 跟随平滑系数约 `0.14–0.20`。
- 不直接紧贴鼠标，应形成惯性。
- 不允许覆盖文字对比度。

## 6.2 Particle Trail

- 仅 Portal / App Center / Digital Twin。
- 粒子数量全屏上限建议 60–90。
- 生命周期 400–900ms。
- Alpha <= 0.08。
- Radius 4–14px。
- 禁止明显圆点飞舞；视觉应接近柔光残影。

## 6.3 Reduced Motion

```css
@media (prefers-reduced-motion: reduce)
```

必须：
- 关闭 Particle Trail
- 关闭 Pointer Aurora
- 关闭 Hero Sweep
- 减少页面 transition
- KPI 不滚动计数

---

# 7. Global Header

## 7.1 Desktop Geometry

- Height：80px。
- Radius：24px。
- Sticky top：10–12px。
- Horizontal padding：20px。
- Logo mark：40×40px。
- Search height：50px。
- Action icon hit area：48×48px。
- Avatar：46px。

## 7.2 内容顺序

```text
HBOS Brand
→ Current Context
→ Global Search / Command
→ App Switcher
→ Notification
→ Help
→ User
```

## 7.3 Header Icon

正式使用 Ant Design Icons：
- `AppstoreOutlined`
- `BellOutlined`
- `QuestionCircleOutlined`
- `UserOutlined`

禁止用文字“应用 / 通知 / 帮助”替代顶层入口。

每个 Icon Button：
- 48×48 desktop
- >=44×44 mobile
- Hover 上浮 1–2px
- Background 从 0.54 → 0.85
- 有 Tooltip

## 7.4 Notification Bell

铃铛是 Notification Center 入口。

红点只表示：
- 有未读且值得注意的信息。

不要把所有后台事件都产生红点。

---

# 8. Notification Center

Notification ≠ My Work。

## 分类

### Action Required
需要用户知道并可能需要动作。

### Risk
风险提醒。

### Information
普通信息。

### System
同步 / 升级 / 连接状态。

默认铃铛中心展示：
- Action Required
- Risk
- 重要 Information

System 低价值消息默认折叠。

---

# 9. Portal Sidebar

固定 Portal Navigation 只能有：

```text
首页
我的工作
应用中心

个人
我的
设置
```

禁止：
- LIMS
- Inventory
- Attendance
- Digital Twin

作为 Portal 固定一级导航。

业务 APP 必须通过：
- App Center
- App Switcher
- Search
- Command Palette
- Deep Link

进入。

## Desktop

Expanded：224px  
Collapsed：72–76px  
Item height：44–46px  
Icon：18px  
Text：13px

---

# 10. App Local Sidebar

业务 APP 内使用。

例如 LIMS：

```text
我的工作
工作台
我的待检
我的复核
我的审批

专业业务
样品与检验
质量与报告
留样管理
稳定性管理
合规审计
```

## Geometry

Expanded：232–248px  
Collapsed：72–76px  
Item：42–44px

必须有：

```text
← 返回 HBOS 工作台
```

但返回入口不能比业务导航更显眼。

---

# 11. Hero Workspace

Portal Home V3 核心组件。

## Geometry

- Radius：30–32px。
- Padding：40–44px。
- Min height：400–440px。
- Desktop Grid：约 `1.08 : 0.92`。
- Mobile 单列。

## 内容

左侧：
- Context kicker
- Greeting
- Hero Action Count
- Supporting text
- Hero Metrics

右侧：
- System Status
- Digital Twin Mini Preview / Role Context

## Hero Count

必须统计“真正需要我处理”的任务。

不包括：
- waiting
- done
- pure information

---

# 12. Hero Metric

数量：建议 3–4 个。

Desktop：
- Value：30–36px。
- Label：12–13px。
- Meta：11px。

Metric 不能变成主业务事实副本，只是 Provider Summary 投影。

---

# 13. Application Center

## Home Compact App Center

只展示：
- Pinned
- Most Relevant
- Recent
- Digital Twin
- More Apps

建议 5–7 项。

当前设计：
- LIMS
- Inventory
- Attendance
- Equipment
- Digital Twin
- More

## Tile

Desktop：
- Height：145–155px。
- Icon：52–56px。
- Title：13px。
- Meta：11px。

## Full App Center

未来分类：

```text
常用
最近使用
全部应用
```

再增加：
- Search
- Pin
- Category（APP 数量 > 12 时）

禁止手机桌面式铺满 20 个 Icon。

---

# 14. Application Icon

## Prototype

Ant Design Icon + HBOS Gradient Background。

## Production

未来建立 HBOS App Icon Set：

- Soft Rounded
- Gradient
- Layered / Semi-3D
- 统一视角和边缘高光

Icon 本身不能承担 Status Semantic。

Domain Color：
- Attendance：Indigo / Violet
- Inventory：Amber / Orange
- LIMS：Emerald / Cyan
- Equipment：Cyan / Blue
- Digital Twin：Blue / Violet / Aqua

---

# 15. My Work

My Work 是：

> Action Inbox

不是 Activity Feed。

## Scope

```text
需要我处理
今天
本周
超期
等待别人
已完成
```

默认打开：

```text
需要我处理
```

## Task Row

Desktop：
- Height：64–72px。
- App Icon：40–42px。
- Title：13–14px。
- Metadata：11px。
- Due：11–12px。

点击：
- Deep Link 到业务 APP。

Portal v1 不直接执行高风险 Business Action。

---

# 16. Business Pulse

只针对 Professional / Manager。

普通员工可隐藏。

Metric 卡：
- 每组 2×2。
- Value：26–32px。
- Trend：11px。
- Sparkline 可选。

没有真实 Provider 时必须隐藏，不展示假数字。

---

# 17. Digital Twin Panel

数字孪生是 HBOS 一级特色能力。

## Home Variant

包含：
- Spatial Preview
- M606B / M607B
- Status
- Process Mode
- Equipment Health
- Environment
- 进入 3D

推荐高度：
- Desktop：380–420px。

## Modes

```text
运行态势
工艺流程
设备健康
```

## 独立应用

未来：

```text
/hbos/digital-twin
```

完整 3D、设备、工艺、历史状态和培训。

Portal 内只提供 Overview。

---

# 18. Quick Action / Recent

每个首页最多 3–5 个。

组件高度约 88–100px。

Quick Action 必须来自 Provider。

Portal 不自己知道：
- 扫码入库是什么 API
- 样品登记是什么 API

---

# 19. Command Palette

快捷键：

```text
⌘ K
Ctrl K
```

## Desktop

Width：640–720px。  
Radius：22–26px。  
Strong Glass G3。

支持：

```text
搜索
应用切换
业务实体搜索
快速动作
最近访问
```

## Result

每条高度 52–64px。

结构：
- App icon
- title
- type / app / subtitle
- keyboard action

必须支持键盘上下选择和 Enter。

---

# 20. Drawer / Page / Modal

## Drawer

适用于：
- 快速详情
- Read-only Preview
- Search Result Preview
- 轻编辑 <= 约 8 个字段
- Related Context
- Batch / Sample / Employee 摘要

Desktop width：
- 420px small
- 560px standard
- 720px wide

复杂内容不得使用 Drawer。

## Full Page

必须用于：
- 检验结果录入
- 复核 / 批准
- 电子签名
- 复杂出入库
- 盘点
- 长表单
- 多段 Workflow
- 大型 Table
- Analytics

## Modal

仅用于：
- 确认
- Reject Reason
- 删除
- 简单 re-confirm
- 小型不可恢复动作

---

# 21. Data Table

HBOS 的核心业务组件之一。

必须支持：
- Sticky Header
- Resize Column
- Hide / Show Column
- Saved View
- Filter
- Search
- Bulk Action
- Row selection
- Loading
- Empty
- Permission State
- Keyboard

## Density

Comfortable：
- Row 48–52px。

Compact：
- Row 38–42px。

中文表格正文：
- 13px。

---

# 22. Filter Bar

组成顺序：

```text
Primary Filters
Search
Advanced Filter
Saved View
Reset
```

不要把所有过滤器永久展开。

高频 2–4 个放在 Bar。

其余进：
- Filter Drawer / Popover。

---

# 23. Form

Label：
- 12–13px。
- Weight 600–700。

Input：
- Height 38–42px。
- Radius 10–12px。

关键 Business Form 必须有：
- Save State
- Validation Summary
- Dirty State
- Unsaved Navigation Guard

---

# 24. Status Tag

所有 APP 使用统一 Semantic：

| Semantic | 用途 |
|---|---|
| Neutral | 普通状态 |
| Info | 信息 |
| Processing | 正在处理中 |
| Success | 成功 / 合规 |
| Warning | 风险 / 待关注 |
| Critical | 严重 / 阻断 |
| Disabled | 不可操作 |

颜色不是唯一表达方式。

必须：
- 色 + 文字
- 必要时加 Icon

---

# 25. Primary / Secondary Action

每一页只能有一个视觉上最强 Primary Action。

例如：

```text
登记样品
开始检验
提交结果
保存
```

不要同一区域同时出现 3 个蓝色 Primary Button。

---

# 26. Empty State

必须包含：

```text
发生了什么
为什么
下一步可做什么
```

示例：

```text
暂无待复核结果

当前没有需要你复核的检验结果。

[查看全部样品]
```

---

# 27. Loading

默认：
- Skeleton。

不使用整页 Spinner。

Provider 并行加载：
- 每个模块独立 Skeleton。
- 一项失败不影响其他模块。

---

# 28. Error

分类：

```text
业务规则
权限
Provider Error
网络
系统错误
离线
```

业务错误必须使用用户语义。

不要暴露：
- Python traceback
- DocType 内部异常
- SQL Error

---

# 29. 403

包含：
- 明确权限原因
- 返回 HBOS
- 查看可用应用
- 可选联系业务管理员

不提示：
- “系统异常”

---

# 30. 404

包含：
- 页面可能迁移
- 返回首页
- 应用中心
- 可选全局搜索

---

# 31. Notification vs My Work

## My Work
回答：

> 我要做什么？

## Notification
回答：

> 发生了什么？

## Business Pulse
回答：

> 我的业务运行得怎么样？

三者不得混为同一个 Feed。

---

# 32. Home Density Profiles

## Employee

展示：
- Hero
- App Center
- 0–3 personal tasks
- Personal Status
- Recent
默认不展示：
- Business Pulse
- Team KPI

Digital Twin：
- 只有对该员工相关时显示。

## Professional

展示：
- Hero
- App Center
- My Work
- Business Pulse
- Digital Twin
- Quick Actions

## Manager

Professional +
- Team Risk
- Approval
- Department / Operation Summary

不是独立“领导门户”。

---

# 33. Responsive

## >= 1600
Wide desktop。

Content max：
- Portal：1560–1600。
- Business App：1440–1600。

## 1200–1599
Desktop 标准。

## 768–1199
Sidebar 折叠到 72–76px。

## < 768
Mobile：
- Sidebar → Drawer / Bottom access。
- Global Header 64–72px。
- Hero 单列。
- Digital Twin Preview 简化。
- 大型专业 Table 可提示桌面端或横屏。

---

# 34. Accessibility

必须：

- 所有点击区域 >= 44×44px。
- Focus visible。
- Keyboard Navigation。
- `aria-label`。
- Reduced Motion。
- Contrast >= WCAG AA。
- 色彩不作为唯一状态含义。
- Icon-only Button 必须 Tooltip + aria-label。

---

# 35. Ant Design Vue Mapping

| HBOS Component | AntD 基础 |
|---|---|
| Header actions | Button / Dropdown / Badge |
| Notification | Badge / Drawer / List |
| Command Palette | Modal / Input / List |
| App Switcher | Popover / Drawer |
| Sidebar | Menu（可自定义渲染） |
| Status | Tag / Badge |
| Form | Form / Input / Select / DatePicker |
| Table | Table |
| Drawer | Drawer |
| Confirmation | Modal |
| Empty | Empty |
| Skeleton | Skeleton |
| Toast | Message / Notification |
| Tabs | Tabs / Segmented |

原则：

> Ant Design Vue 是行为基础，不是最终视觉样式。

必须通过：
- HBOS Theme Tokens
- Wrapper Components
- CSS Variables

统一视觉。

---

# 36. Recommended Component Package Structure

初始 Portal：

```text
src/
├── design-system/
│   ├── tokens/
│   ├── primitives/
│   ├── motion/
│   └── icons/
│
├── components/
│   ├── global/
│   │   ├── GlobalHeader.vue
│   │   ├── NotificationCenter.vue
│   │   ├── AppSwitcher.vue
│   │   └── CommandPalette.vue
│   │
│   ├── portal/
│   │   ├── HeroWorkspace.vue
│   │   ├── AppCenter.vue
│   │   ├── MyWork.vue
│   │   ├── BusinessPulse.vue
│   │   └── DigitalTwinPanel.vue
│   │
│   └── shared/
│       ├── HBOSCard.vue
│       ├── HBOSStatus.vue
│       ├── HBOSEmpty.vue
│       └── HBOSError.vue
```

等第二个 Native APP 真正复用以后，再抽：

```text
packages/hbos-ui
```

不要现在提前制造大型共享组件库。

---

# 37. Interaction Review Checklist

每个新页面 Review 时必须检查：

### 信息层级
- 第一眼知道页面目标吗？
- Primary Action 是否明确？
- 有没有 DocType 思维泄漏？

### Navigation
- Portal / App boundary 正确吗？
- 是否有稳定返回路径？
- 是否支持 Deep Link？

### Typography
- 中文是否太小？
- Metadata 是否过多？
- 英文是否过度？

### Icon
- 是否使用统一 System Icon？
- 有没有 Emoji？
- App Icon 是否使用正确 Domain Identity？

### Motion
- 是否符合 Visual Level？
- 是否干扰业务操作？
- Reduced Motion 是否可用？

### Permissions
- 隐藏菜单是否同时有后端校验？
- 无权限是否进入 403？

### Data
- 是否基于 DTO / Provider？
- 是否直接依赖业务 DocType？

---

# 38. EA-5.4 Definition of Done

EA-5.4 可标记完成，当：

- Global Header 规格冻结。
- Portal Sidebar 规格冻结。
- App Local Sidebar 规格冻结。
- Glass G1/G2/G3 冻结。
- Typography 冻结。
- Icon 基线冻结。
- Motion / Pointer Atmosphere 冻结。
- Hero / App Center / My Work / Digital Twin 规格冻结。
- Notification / Command Palette 交互定义完成。
- Drawer / Page / Modal 规则冻结。
- Table / Form / Filter 基线冻结。
- Empty / Loading / Error / 403 / 404 定义完成。
- Responsive 定义完成。
- Accessibility Gate 定义完成。
- Ant Design Vue Mapping 定义完成。

完成后：

```text
EA-5.4 = DESIGN ENGINEERING FROZEN
```

---

# 39. 下一阶段

下一阶段建议：

## EA-5.5 — Interaction QA + Responsive + Accessibility

集中验证：

- Keyboard
- Mobile
- Tablet
- Reduced Motion
- Focus
- Drawer
- Command Palette
- Notification Center
- App Switcher
- LIMS V1 Operational Page

随后才进入：

```text
P1 — hbos_portal Frappe App Architecture
P2 — Real Portal Skeleton
P3 — App Registry / Auth / Access
P4 — Three-App Registration
P5 — Data Adaptation
```

---

# 40. 本阶段最终冻结语句

HBOS 的视觉与交互不再由单个页面临时决定。

从 EA-5.4 起：

> **所有 HBOS Native UI 必须符合统一 Component Contract、Visual Intensity、Chinese Typography、Motion、Accessibility 和 Portal / App Boundary。**

Portal 是产品 Shell。

Business App 是专业工作空间。

Digital Twin 是一级空间化能力。

Management Console 是后台。

这四者共享 HBOS 品牌，但承担不同的用户任务。