# HBOS Experience Architecture
## EA-5.5 — Interaction QA + Responsive + Accessibility

**状态：IMPLEMENTATION PASS / OWNER REVIEW PENDING**  
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
