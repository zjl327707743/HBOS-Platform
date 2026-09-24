# HBOS Experience Architecture
## EA-5.5 — Interaction QA + Responsive + Accessibility

**状态：OWNER REVIEW FIX-1 IMPLEMENTED / RECHECK PENDING**  
**分支：** `feature/hbos-portal-product`  
**技术基线：** Vue 3 + Ant Design Vue + Vue Router + Pinia

## 1. 目标

EA-5.5 不再修改 HBOS 的视觉母版。

本轮验证 EA-5.4 已冻结的组件与交互规则是否能在真实前端工程中成立，重点覆盖：

- Keyboard / Focus；
- Desktop / Tablet / Mobile；
- Reduced Motion；
- App Switcher；
- Notification Center；
- Command Palette；
- Portal / Business App Boundary；
- Drawer / Full Page / Modal；
- 一张真实的 LIMS V1 Operational Page。

## 2. 已完成的工程化检查

### 2.1 Global Theme

已增加 Ant Design Vue 全局 Theme Config，将 AntD 作为组件行为底座，同时统一：

- primary / info / success / warning / critical；
- radius；
- control height；
- Chinese font stack；
- Table / Modal / Drawer 基础 token。

### 2.2 Keyboard

Command Palette 已支持：

- `⌘K / Ctrl+K` 打开；
- Arrow Up / Down 选择；
- Enter 执行；
- Esc 关闭。

已增加 Skip Link：

- Portal → main content；
- LIMS → LIMS main content。

### 2.3 Focus

全局使用清晰 `:focus-visible`。

Icon-only Header action 必须有：

- aria-label；
- Tooltip；
- >= 44×44 hit area。

### 2.4 Mobile

Portal 在 < 768px：

- Desktop Sidebar 隐藏；
- 使用固定 Bottom Navigation；
- 保留 Home / Work / Apps / Profile。

LIMS 在 < 768px：

- Desktop Local Sidebar 隐藏；
- 使用 Mobile App Navigation；
- 完整专业业务导航通过 Bottom Drawer 打开。

### 2.5 Reduced Motion

继续支持：

```css
@media (prefers-reduced-motion: reduce)
```

关闭 / 降级：

- Pointer particle trail；
- Pointer Aurora；
- ambient animation；
- transition duration。

## 3. LIMS V1 Operational Page

验证路由：

```text
/hbos/lims/results/RESULT-001/review
```

该页面用于验证“专业操作页必须从 V2 Dashboard 收敛为 V1 Operational”。

### Full Page

以下内容位于完整页面：

- Result review；
- specification / result context；
- reviewer conclusion；
- comments；
- attachment context；
- SoD notice；
- activity history。

### Drawer

“样品上下文”使用 Drawer：

- SAMPLE；
- material；
- batch；
- specification version；
- related tests。

原因：它是辅助上下文，不应打断当前复核工作流。

### Modal

“退回”和“提交确认”使用 Modal。

原因：

- 短决策；
- 二次确认；
- reason input。

正式功能接入时，提交必须由 LIMS backend 再执行：

- permission；
- workflow state；
- segregation of duties；
- electronic signature / re-auth policy（如适用）。

Portal 或 Vue 前端不得成为最终权限来源。

## 4. Responsive QA Matrix

| Surface | Desktop | Tablet | Mobile |
|---|---|---|---|
| Global Header | full | full / compressed | compact |
| Portal Sidebar | 224px | 76px | bottom nav |
| App Local Sidebar | 240px | 76px | bottom nav + drawer |
| Hero | two-column | adaptive | single-column |
| App Center | 6 / row | 3 / row | 2 / row |
| Digital Twin | split | stacked | simplified stacked |
| LIMS Operational | main + sticky context | stacked | single column |
| Data Table | normal | horizontal scroll | horizontal scroll |

## 5. Accessibility Gate

EA-5.5 必须满足：

- meaningful keyboard path；
- visible focus；
- skip navigation；
- icon labels；
- no emoji as product icon；
- text + color status semantics；
- reduced-motion fallback；
- mobile replacement for hidden sidebars；
- body Chinese text >= 12px；
- standard body 14px；
- click target >= 44px where interactive.

## 6. 当前验证状态

已完成：

- Portal build CI 已建立；
- Node 22 / npm install 可在 GitHub Actions 执行；
- 第一轮 build 暴露严格 TypeScript 错误；
- 已修复 PointerAtmosphere undefined safety 和 tsconfig Node 组合；
- 修复后 Portal Frontend Gate 已 PASS。

EA-5.5 新增代码提交后，需要再次通过相同 build Gate。

## 7. 本阶段仍然不做

- 不创建 `apps/hbos_portal`；
- 不接 Frappe API；
- 不把 Mock 数据描述成真实业务数据；
- 不执行真实 LIMS approve / reject；
- 不实现电子签名；
- 不修改 LIMS Domain；
- 不修改 Frappe / ERPNext / HRMS 核心源码。

## 8. Definition of Done

EA-5.5 可标记完成，当：

- Portal Frontend Gate PASS；
- HBOS Quality Gate PASS；
- mobile navigation 不丢失功能入口；
- Command Palette keyboard path PASS；
- Reduced Motion 降级存在；
- LIMS V1 Operational Page 编译通过；
- Drawer / Page / Modal 边界得到实现验证；
- Owner 对 Portal + LIMS 两级体验无结构性异议。

通过后：

```text
EA-5.5 = COMPLETE
Frontend Reproduction Gate = PASS
Next = P1 hbos_portal Backend Architecture
```


## 9. CI Closeout — 2026-09-24

EA-5.5 当前实现已通过：

```text
HBOS Quality Gate = PASS
HBOS Portal Frontend Gate = PASS
```

Portal Frontend Gate 已验证：

- npm install；
- vue-tsc；
- Vite build；
- dist/index.html 存在。

期间 CI 发现并修复：

1. PointerAtmosphere strict TypeScript undefined safety；
2. tsconfig Node option incompatibility；
3. Ant Design Vue Table theme token type incompatibility。

因此 EA-5.5 工程实现 Gate 已通过；最终 COMPLETE 仍等待 Owner 产品体验验收。


## 10. Owner Review Round 1 — 2026-09-24

Owner 已在真实浏览器运行环境完成第一轮产品验收并给出以下反馈：

1. 总体前端方向认可；
2. Hero “今天有 5 项工作需要你处理”字号过大；
3. 其他导航、卡片、说明文字相对偏小，需要重新平衡中文字体层级；
4. Portal 工作台 Sidebar 未跟随页面滚动；
5. Header 后续需要支持企业 Logo；
6. 飞书登录完成后，用户头像应支持展示飞书头像。

本轮 Fix-1 处理：

- Hero Display 上限从 64px 收敛至 56px，并调整 line-height / tracking；
- Sidebar / Section / Card / Meta 字号整体做中文可读性提升；
- 修复 `.portal-page overflow: hidden` 对 sticky 的破坏，改为横向 clip + 纵向 visible；
- 强化 Portal / App Sidebar 的 sticky / align-self；
- Global Header 增加可选 `companyLogoUrl` 品牌位；
- `PortalUser` 增加 `avatarUrl` 与 `identityProvider`；
- Header Avatar 支持远程头像 URL，缺失时继续使用文字头像回退。

当前原型仍不伪造企业 Logo 或飞书头像。正式图片来源将在后续 Frappe / 飞书身份接入阶段由 bootstrap / identity mapping 提供。


## 11. Owner Review Round 2 — 2026-09-24

Owner 复核 Fix-1 后确认：

- Hero 主标题当前大小基本可接受；
- 页面整体仍存在“主标题合适，但第二 / 第三层文字偏小”的不协调感。

Fix-2 不再修改 Hero 结构，而是统一中文 Typography Rhythm：

- Body baseline：14px → 15px；
- Dense body：13px → 13.5px；
- Metadata：12px → 12.5px；
- Micro label：11px → 11.5px；
- Sidebar / Local Nav：统一约 14px；
- Section description：13px；
- App title：14.5px；
- Task title：14px；
- Status / business metric supporting text：12–12.5px；
- Header brand caption / search text同步放大；
- Tablet / Mobile 保留响应式降级，避免移动端过密。

本轮目标是提高中文信息层级的连续性，不继续放大 Hero，也不改变布局结构。


## 12. Owner Review Round 3 — Typography Governance

Owner 指出当前页面存在字号不统一问题。

代码审计确认旧样式中同时存在大量 8–40px、半像素字号和多组 clamp，说明此前视觉迭代产生了过多组件级字号特例。

本轮不再进行逐块目测修字，而是建立 **Typography Contract v1.1**：

```text
Display     52
Page Title  32
Section     20
Card/Nav    14
Body        14
Meta        12
Micro       11
KPI         30
```

并新增独立 `src/theme/typography.css` 作为最终语义覆盖层。

原则：

- 同语义 = 同字号；
- 不再使用半像素字号；
- 组件不得自行创建字号；
- Responsive 只允许规范中明确列出的降级值。

后续若需要修改字号，应修改 Token / Typography Contract，而不是修改单个页面。


## 13. Owner Review Round 4 — Global Type Scale Increase

Owner 在 Typography Contract v1.1 真实运行后确认：

- Hero 52px 已可接受；
- 除 Hero 外，其余文字整体仍偏小。

本轮升级为 Typography Contract v1.2：

```text
Display     52  (unchanged)
Page Title  34
Section     22
Card/Nav    15
Body        15
Meta        13
Micro       12
KPI         32
Greeting    22
```

本轮只调整统一 Token，不改变页面结构、不重新引入组件级字号特例。


## 14. Owner Review Round 5 — Large Workspace Typography

Owner 确认 Hero 52px 保持不变，但要求其余文字整体继续放大。

Typography Contract 升级为 v1.3：

```text
Display     52  (unchanged)
Page Title  36
Section     24
Card/Nav    16
Body        16
Meta        14
Micro       13
KPI         34
Greeting    24
```

本轮仍只调整统一 Token 与 Typography Contract，不改变页面布局和信息结构。
