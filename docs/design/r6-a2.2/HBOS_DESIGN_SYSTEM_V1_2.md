# HBOS 前端规范 v1.2 · R6-A2.1 候选

状态：**R6A2_1_DESIGN_REVIEW_READY / 等待 Owner 设计复核**。本规范对应当前 `design/r6-experience-v2/` 的 Vue 3 + Ant Design Vue 合成数据样板；不是正式页面实施、权限策略或部署授权。

v1.2 不推倒 R6-A2 的信息结构与视觉方向，只落实本轮四项修正：**双栏同高与内部滚动、工作台同源背景动效、侧栏残影与页面边界、手机/矮窗口/放大场景重排**。v1.1 全文、R6-A2 验收记录与截图均作为历史保留，不改写原结论。

## 1. 本轮变更边界

| 项 | v1.2 结论 |
|---|---|
| 信息架构、导航、四核心画面、合成数据与任务路径 | **保留** R6-A2；本轮只调整页面骨架容器、滚动归属、背景层与响应式 |
| 部门安排 / 角色与权限 | 左右面板同高；长内容在面板内部滚动；页面标题、面板标题与底部操作稳定；左侧数据少仍填满 |
| 背景 | 复用产品 HBOS 工作台同源 `PointerAtmosphere` + `.aurora-a/b/c` + `.portal-page` 渐变参数；不另造静态管理主题 |
| 动效 | 可暂停、支持系统减少动态效果、页面隐藏停帧、切页不重复创建 |
| 边界 | 单一滚动主体、无横向溢出、无内容越出主内容区、滚动条不产生白色空槽；侧栏/吸顶区域滚动时像素稳定 |
| 产品 / UAT / #61 / #62 / 真实账号与权限 | **未修改**；本轮只在设计目录与本机回环预览服务内工作 |

## 2. 背景与动效：工作台同源合同

### 2.1 同源来源（只读）

- `workspaces/product/frontend/hbos-portal-web/src/components/layout/PointerAtmosphere.vue`
- `workspaces/product/frontend/hbos-portal-web/src/styles/global.css` 中 `.portal-page`、`.aurora`、`.pointer-fx-canvas`、`.pointer-aurora-vue`
- 产品工作位 `fix/feishu-controlled-uat-login @ e1e3c9912913fbdd56706a0800e813d8d666626e`
- 只复制**纯展示参数与绘制逻辑**；样板不包含产品接口、会话、鉴权、埋点或业务请求。

### 2.2 视觉参数（与产品一致）

| 层 | 参数 | 说明 |
|---|---|---|
| 画布渐变 | 8%/8% 紫 `rgba(108,99,255,.13)`、90%/12% 蓝 `rgba(69,166,255,.13)`、70%/84% 青 `rgba(84,224,192,.10)`，底色 `linear-gradient(180deg,#f7faff,#f4f8fd 44%,#eef5fc)` | 与 `.portal-page` 逐值一致 |
| `aurora-a` | 380×380，`#8177ff`，opacity .34，blur 75px，12s alternate float | 左上偏下 |
| `aurora-b` | 440×440，`#64bcff`，opacity .28，blur 75px，14s alternate float | 右上 |
| `aurora-c` | 380×380，`#79ead2`，opacity .20，blur 75px，16s alternate float | 中下 |
| 指针光效 | 480×480 径向光域，紫/蓝/青三色，`filter: blur(18px)`，`mix-blend-mode: multiply`，`translate3d` 跟随 | `PointerAtmosphere.vue` 原参数 |
| 粒子画布 | 全屏 canvas，最多 85 粒，三色 radial gradient，opacity .55 | 原参数 |

实现文件：`src/components/AtmosphereLayer.vue`（单实例容器）、`src/components/brand/PointerAtmosphere.vue`、`src/styles/r6a2_1.css` 第 1 节。

### 2.3 生命周期与可访问性合同

1. **只挂载一次**：`AtmosphereLayer` 位于 `App.vue` 根部、`KeepAlive` 之外；页内切换、员工抽屉开关、身份切换不重建。`window.__R6A21_ATMOSPHERE__.mounts` 用于本地证据断言（跨页多次切换必须保持 1）。
2. **可暂停**：设计预览工具提供“背景动效 / 暂停背景动效”开关；暂停后 aurora 定格（`animation-play-state: paused`）、指针画布隐藏、帧计数冻结；恢复后继续。
3. **减少动态效果**：`prefers-reduced-motion: reduce` 时隐藏指针画布与指针光域、关闭 aurora 动画；页面信息与操作不受影响。
4. **页面隐藏停帧**：`document.visibilityState === 'hidden'` 时停止 rAF；重新可见并允许动态时恢复。
5. **不遮挡、不夺取交互**：背景层 `pointer-events: none`、`z-index: 0`，所有内容层位于其上方；背景仅作氛围，不承担信息。
6. **性能边界**：`contain: strict` + `isolation: isolate` 将背景层限制在固定合成层内，避免滚动内容与背景互相触发大面积重绘。

## 3. 页面骨架：视口适配双栏合同

### 3.1 适用页面

`部门安排`、`角色与权限` 使用 `main-content.fit-page` 骨架：

```text
.main-content.fit-page   display:flex; flex-direction:column; overflow:hidden
├─ .context-row          固定（面包屑/返回）
├─ .page-heading         固定（页面标题与说明）
├─ .departments-layout / .roles-layout   flex:1; min-height:0; 单行网格
│   ├─ PanelFrame(aside)   .panel-frame-header / .panel-frame-scroll / .panel-frame-footer
│   └─ PanelFrame(section) .panel-frame-header / .panel-frame-scroll / .panel-frame-footer
└─ .page-footer          固定（设计候选与合成数据说明）
```

### 3.2 不变量（回归检查逐项断言）

1. 左右面板 `getBoundingClientRect().height` 差值 ≤ 1px，且各自等于网格行高；左侧数据只有 3 条时同样成立，**不缩成短卡**。
2. 长内容只滚动 `data-scroll-region="department-detail|role-detail|department-list|role-navigation"`；fit 页 `.main-content` 为 `overflow: hidden` 且 `scrollHeight === clientHeight`，**页面不整体滚动**。
3. 内部滚动前后，页面标题、面板标题、底部操作与页面页脚位置不变（≤0.5px），底部操作始终在视口内可见可点击。
4. 稀疏/长列表、切换部门或角色、编辑态与阅读态切换后不变量仍成立。
5. 面板标题与底部操作背景不透明，滚动内容不会从其后透出；圆角以内不出现滚动条白色空槽。
6. 手机与放大场景取消面板内滚：改为单列自然文档流，底部操作在文档末尾完整可达。

### 3.3 面板容器公共组件 `PanelFrame`

| 插槽 / 属性 | 合同 |
|---|---|
| `region`（必填） | 渲染为 `data-scroll-region="…"`，供回归测量与定位 |
| `label`（必填） | 滚动区的可访问名称，`role="region"` + `tabindex="0"`，键盘可聚焦滚动 |
| `#header` | 固定在面板顶部，不随内容滚动 |
| 默认插槽 | 唯一内部滚动区 `.panel-frame-scroll` |
| `#footer` | 固定在面板底部，承载主要操作/状态；不得包含会无限增长的内容 |
| `as` / `surface` | 语义标签（`aside` / `section`）与统一表面样式 |

矮窗口（`min-width:761px` 且 `max-height:760px`）压缩页头与面板内边距，不隐藏信息；`max-height:560px` 时主体回退为页面滚动，但仍保持双栏同高。

## 4. 响应式、边界与残影

| 场景 | 处理 |
|---|---|
| 1440×1000 / 1280×720 / 1024×600 | 视口适配双栏；列宽 240/200/200px（部门）与 210/190/168px（角色）；标题与底部稳定 |
| 手机 390×844 | 单列自然文档流；局部导航吸顶于顶栏下；部门选择变横向滚动条；角色模板横排、详情纵向；无嵌套双滚动 |
| 200% 放大等效 | 视口宽 720 CSS px + DPR 2。**这是布局等效方法，不是原生浏览器 zoom 实测**；原生 200% 仍为 NOT_RUN |
| 横向溢出 | `documentElement.scrollWidth === clientWidth`；内容面右边界不超过 `.main-content` 右边界 |
| 滚动主体 | 桌面：仅 `.main-content` 或面板内滚区；手机：仅窗口滚动。fit 页禁止双滚动 |
| 侧栏与吸顶 | 侧栏不透明、`isolation: isolate`；手机 `position: sticky` 且不被内容覆盖；滚动时像素稳定 |
| 滚动条 | 主内容/内滚区使用细滚动条、透明轨道，不出现白色空槽；`overscroll-behavior: contain` 防止滚动链 |
| 页面边界 | `.main-content.fit-page` 裁剪内部溢出；页脚固定在主内容底部；不在视口内出现被撕开的半截固定元素 |
| 长截图 | 禁止用整页长截图证明布局；证据一律为单视口截图 + DOM 测量 + 滚动/动效录屏 |

## 5. 公共组件与状态（v1.2 全表）

| 组件 | 位置 | 状态与行为 |
|---|---|---|
| `PageHeading` | 既有 | 路径、标题、一句说明、区域动作；fit 页固定不滚 |
| `AtmosphereLayer` | **新增** | 工作台同源背景；单实例；暂停/减少动态/隐藏停帧；不夺取交互 |
| `PointerAtmosphere` | **新增（产品纯展示代码移植）** | 指针粒子与光域；`paused` 属性；DPR 上限 2；参数与产品一致 |
| `PanelFrame` | **新增** | 双栏面板同高、头尾固定、唯一内部滚动区、可聚焦滚动 |
| `StatusTag` | 既有 | 颜色 + 文字 + 图标/点；不单靠颜色 |
| 员工工具栏 | 既有 | 搜索、部门、账号状态、可清除筛选；切回保留 |
| 员工表格 | 既有 | 头像姓名、工号、部门岗位、账号、待处理、直达动作；固定表头；手机转任务卡 |
| `EmployeeDrawer` | 既有 | 分区与底部动作；手机全屏；未保存关闭需确认 |
| 角色比较卡 / 范围选择 | 既有 | 按用途比较；部门可搜索；不默认含下级 |
| 角色功能分组 | 既有 | 阅读态文字状态；编辑态勾选；搜索与展开保留真实映射 |
| 变更确认 | 既有 | 谁、应用、前后角色、范围、增删能力、影响对象与限制 |
| `VerificationPanel` | 既有 | 明示设计预览不输入真实密码；不可当作正式 proof/MFA |
| `ResourceState` | 既有 | 正常/骨架/空/失败/无权限；fit 页内不撑破页面 |
| 消息与恢复 | 既有 | 忙碌锁定、成功摘要、失败就地恢复；不假成功 |

组件展示入口：预览右上“设计预览”→ 统一组件规范（`/#/spec`），已加入 v1.2 背景与面板条目。

## 6. 回归检查与证据合同

本地工具（不属于产品代码）：

```bash
# 回归检查：布局/滚动/边界/动效/交互，输出 JSON 与 PASS/FAIL
node scripts/check_r6a2_1.mjs

# 证据采集：单视口截图、DOM 边界测量、滚动/动效录屏
node scripts/capture_r6a2_1.mjs
```

- 回归脚本输出：`evidence/r6a2_1/regression-checks.json`（本轮 113/113 PASS，含每个视口的实测数值）。
- 采集输出：`evidence/r6a2_1/capture-manifest.json`、`evidence/r6a2_1/dom-measurements.json`、`evidence/r6a2_1/media/screenshots/`、`evidence/r6a2_1/recordings/`；采集聚合断言保存在 `evidence/r6a2_1-checks.json`（417 项，与实现回归分开）。
- 独立复核：`evidence/r6a2_1/verification/report.md` 与 `verification.json`，由未参与实现的复核 Agent 用独立脚本复测，不与实现自证混用。
- 所有截图必须为单视口原图（位图尺寸 = CSS 视口 × DPR）；录屏为 webm 原始 + mp4 转码 + poster。
- 录屏工具限制：headless Chrome CDP 录屏表面为 1440×913，Playwright 以灰边补足 1440×1000 帧；有效画面缺少页面最底部约 87px。截图/DOM 证据完整 1440×1000，不把录屏冒充真实屏幕或原生浏览器窗口录制。

**本轮明确 NOT_RUN（不得用脚本断言替代）**：真实原生浏览器 200% 缩放、真人首次理解与易用性、正式系统性能/安全/真实授权。系统减少动态效果使用浏览器媒体仿真验证，仍不冒充真人偏好切换。

## 7. Token 与动效参数增补

沿用 v1.1 品牌 token（主色 `#5754df`、蓝 `#4897ec`、画布 `#f4f6fb`、正文/次要/辅助 `#192a45/#566780/#5f6e86`、结构线 `#e5e9f2`、控件边界 `#8793aa` 等），不新增管理主题色。

v1.2 增补：背景层参数见 §2.2；面板圆角沿用内容 16px；内滚条 10px 细轨、透明底；动效节奏沿用悬停 160ms / 面板 200ms，背景浮动 12/14/16s，暂停与减少动态优先于任何持续动画。

## 8. 实施前边界（不变）

- 依赖仍为产品锁文件解析值：Vue **3.5.43**、Ant Design Vue **4.2.6**、icons-vue **7.0.1**；本设计目录未改产品依赖、路由或公共主题。
- 原型无真实 API、OAuth、数据库、UAT 写入或会话逻辑；业务动作只改变页面内存。
- 真实接口与安全时序缺口见 `ENGINEERING_MAPPING.md`；Owner 批准设计后，从届时重新核对的产品集成 SHA 另行进入 R6-B。
- 本规范不授权合并 PR、部署、真实账号或权限变更。
