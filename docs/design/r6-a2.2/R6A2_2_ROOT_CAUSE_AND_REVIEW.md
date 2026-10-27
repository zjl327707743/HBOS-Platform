# R6-A2.2｜大屏自适应与个人中心收口

状态：`R6A2_2_DESIGN_REVIEW_READY`；`VISUAL_OWNER_ACCEPTANCE=PENDING_OWNER`。上一轮 R6-A2.1 的 Owner 视觉退回仍然有效；本轮只交付原型供复核，不自行宣称 Owner 通过。

## 1. 先给实测根因

在修改前的 1920×1080 CSS 视口、DPR 1、Chrome 默认 100% 缩放下，`.workspace` 是宽 1920px 的横向 flex，管理侧栏 224px，`.main-content.fit-page` 本身为 **1696px**、`flex: 1 1 0%`、`min-width: 0`、无 `max-width`。外层工作区没有把主区限制成窄岛。

真正的问题位于 `src/styles/app.css` 的 **`@media (min-width:1800px)`** 公共规则：

```css
.main-content:not(.personal-main)>div:not(.context-row),
.main-content:not(.personal-main)>.context-row,
.main-content:not(.personal-main)>.page-footer {
  max-width: 1440px;
  margin-inline: auto;
}
```

R6-A2.1 又把 `.main-content.fit-page` 设为纵向 flex。上面这些直接子项的左右 auto 外边距阻止横轴拉伸，但未指定 `width`，导致页面子项按内容固有尺寸收缩居中。`max-width:1440px` 只是上限，并非实际窄宽度；不是 `.departments-layout` 或 `.roles-layout` 单独写死了整页宽度。计算样本：

| 1920 修改前 | 部门 | 角色 |
|---|---:|---:|
| 工作区可用宽度 | 1696 | 1696 |
| 直接页面子项 / 双栏 grid 宽 | 708.81 | 726 |
| 有效宽度占比 | 41.8% | 42.8% |
| grid 列宽 | 240 + 24 + 444.81 | 210 + 22 + 494 |
| 页面子项计算后左右外边距 | 461.59 / 461.59 | 453 / 453 |
| 面包屑宽及左边界 | 299 / x=922.5 | 311 / x=916.5 |
| 标题与 grid 左边界 | x=717.59 | x=709 |
| 页脚宽及左边界 | 294.31 / x=924.84 | 294.31 / x=924.84 |

1728px 时该媒体查询不生效；两页的内容均为 1440 / 1504px（95.7%），所以跨过 1800px 反而出现突降。原始 DOM 包含 workspace、侧栏、main、context、页面子项、标题、grid、两侧 `PanelFrame`、页脚的矩形、`width/max-width/min-width/flex/grid-template-columns/margin/justify-content` 及滚动尺寸：`evidence/r6a2_2/before/measurements.json`；修后同结构见 `after/measurements.json`。

## 2. 修复与设计选择

- 在同一公共宽屏规则上增加 `width:100%`，保留 `max-width:1440px` 和居中，不逐卡片硬编码放大；标题、面包屑、主体与页脚因此共享边界。宽屏部门及角色导航统一 240px、间距 24px，右侧使用剩余空间。
- `src/styles/r6a2_2.css` 为短窗口增加公共降级：桌面高度 ≤700px 时主内容区承载纵向滚动，面板自然增长并保持等高，面板正文不另设短内滚区。1024×600 的角色正文由修前 178 / 939px 内滚，变为 939 / 939px 自然内容，主区 524 / 1285px 滚动；可使用滚轮和聚焦后 PageDown 到达底部。1024×701 的角色内滚在阅读/编辑态分别为 279/270px；700 以下转自然流。固定底部只在常规高度保留，短窗中随主区滚动。
- 个人中心删除“这是你的个人空间”和“保管好登录方式”两块右栏，保留密码、飞书及恢复项的状态、说明和动作；安全帮助放在密码/恢复项。上方改称“我的工作身份”，系统 Administrator 的工号、部门、岗位明确为“不适用”，员工待关联显示“待核对”。单列桌面最大宽度 1160px，保持普通员工与管理导航分离。
- 同源 PointerAtmosphere、aurora、角色范围与模拟权限模型没有改变；工作仍仅限设计目录。浏览器标题与预览标记更新为 R6-A2.2，规范候选为 `HBOS_DESIGN_SYSTEM_V1_3_CANDIDATE.md`。

## 3. 视口实测与对照

截图均为 Chrome 156 headless、默认浏览器缩放 100%、DPR 1、仿真减少动态效果下的**原生单视口 PNG**，尺寸即 CSS 视口，未拼接或补灰带。1920×1080、1728×900 的部门、角色、个人中心均有修改前后对照，见 [评审入口](http://127.0.0.1:50056/review/)。此前 Owner 的三张原图没有随本会话附件提供；“修改前”是本次修改前从现有预览实际采集的基线，而非冒称 Owner 原图。另在 macOS 桌面 Chrome 正常窗口直接打开了原型并目视检查。

| 视口 | 可用宽度 | 双栏宽 / 占比 | 部门左 / 右宽 | 角色左 / 右宽 | 双栏高度差 |
|---|---:|---:|---:|---:|---:|
| 1920×1080 | 1696 | 1440 / 84.9% | 240 / 1176 | 240 / 1176 | 0 / 0px |
| 1728×900 | 1504 | 1440 / 95.7% | 240 / 1176 | 240 / 1176 | 0 / 0px |
| 1600×900 | 1376 | 1312 / 95.3% | 240 / 1048 | 240 / 1048 | 0 / 0px |
| 1440×1000 | 1216 | 1152 / 94.7% | 240 / 888 | 240 / 888 | 0 / 0px |
| 1280×720 | 1072 | 1020 / 95.1% | 200 / 800 | 190 / 812 | 0 / 0px |
| 1024×600 | 836 | 792 / 94.7% | 200 / 576 | 168 / 608 | 0 / 0px |
| 390×844 | 390 | 358 / 91.8% | 单列 | 单列 | 不适用 |
| 2560×1440 | 2336 | 1440 / 61.6% | 240 / 1176 | 240 / 1176 | 0 / 0px |

2560 下按 1440px 最大宽度居中，故占比低于 70%，是避免超宽阅读行的有意上限。个人中心 1920/1728 的身份和安全面板均宽 1150px，1280 下 1160px，390 下 358px。各视口的侧栏及 main 宽、面板宽高、主区/内部滚动 `clientHeight/scrollHeight`、边界和详细计算样式均逐项列在评审入口表格和原始 JSON；手机侧栏是横向栏，不从水平可用宽度扣除。

## 4. 回归与未测项

- 构建成功；`npm test` 中 9 项模拟模型测试通过。继承原有检查的相关常规桌面、窄屏、背景、滚动与交互项，串行复测 88/88；本轮新增宽度、对齐、短窗、键盘/滚轮、四身份和 409/403/500/401 的 42/42 项通过；公共规则对员工/变更记录页、移动端恢复入口及缩放式窗口调整的 5/5 项补充检查通过。1024 原来的“主区绝不滚动”断言与新短窗合同冲突，已由新短窗可用性检查替代；原 v1.2 检查和记录未覆盖。
- 继承回归并行运行时曾有一次员工侧栏滚动前后像素哈希不一致（87/88，`regression-inherited-parallel-first.json/.log`）；当时脚本未保存失败图片，不能断言确切原因。随后单独运行 88/88；更新组件规范文字后，在最终构建上再次串行复测 88/88，侧栏前后截图和哈希已保存。存在一次未解释的像素波动，建议 Owner 在自身浏览器实际滚动时留意。
- macOS 桌面 Chrome **原生 200%**：通过浏览器原生缩放按钮状态确认 200%，分别进入角色编辑并滚动至取消、部门选择并打开确认、个人中心打开恢复方式；退出后恢复 100%。这是实际浏览器 UI 操作，不是 DPR 或 CSS 缩放仿真。该次操作后将短窗阈值从 680 调整至 700px 并更新组件规范，实际 200% 短窗位于两者共同覆盖范围；最终构建没有重复原生 UI 操作，详见 `evidence/r6a2_2/native-zoom-200.md`。此为单台设备的操作验证，不代表所有系统/浏览器。
- 普通滚轮、聚焦后键盘滚动已测；**物理触控板手势未测**。OS 的真实减少动态效果开关未切换（浏览器媒体仿真通过）；真人首次理解、屏幕阅读器、其他浏览器与操作系统未测。无真实账号、权限、认证、数据或 UAT 写入测试。
- Vite 构建有既有的大 JS chunk 提示；未尝试在本轮重构产品或引入性能工作。

## 5. 只读边界与交接

- 唯一设计源码：`/Users/hb/Projects/HBOS/design/r6-experience-v2/`。静态预览服务 PID 74497，经既有 `scripts/服务控制.py` 核验脚本、cwd、回环监听及 dist 根；未重启、未占用新端口。最终 dist 的 CSS `index-D15SfjBi.css`，JS `index-JU3HHQiB.js`。
- 开工及收口只读核对：product `fix/feishu-controlled-uat-login @ e1e3c9912913fbdd56706a0800e813d8d666626e` clean；UAT detached 同 SHA clean；platform `main @ 2675411893b0ea7a82830ba726dc819b9c17ff72`，保留原有脏项；远端产品分支 `1a0d44de1399afca513855f3688eb06c1978429e`。#61 / #62 均 OPEN、Draft，head 分别 `5266651a5b82c4f2cf26792d1827cbc2194ae050` / `e1e3c9912913fbdd56706a0800e813d8d666626e`。
- 保留 v1.2 规范、R6-A2.1 记录及原证据；旧评审入口保存在 `/review/r6a2_1.html`。未改统一入口及产品仓库状态台账：本轮范围仅设计原型，不能将原型结果写入正式产品源码或里程碑。

## 6. 完成回执

```text
SOURCE_WORKSPACE / PREVIEW_SERVICE: design/r6-experience-v2 / 127.0.0.1:50056, PID 74497，归属已核验
WIDE_SCREEN_1920_LAYOUT: PASS（1440 / 1696 = 84.9%，两页右栏 1176px）
WIDE_SCREEN_1728_LAYOUT: PASS（1440 / 1504 = 95.7%，两页右栏 1176px）
EQUAL_HEIGHT_1440_1280: PASS（部门/角色均 0px）
SHORT_VIEWPORT_USABILITY: PASS（1024×600 主区自然滚动，键盘/滚轮及底部操作可达）
PROFILE_REDUNDANT_CARD_REMOVAL: PASS（两块均删除）
PROFILE_CONTENT_BALANCE: PENDING_OWNER（单列 1150–1160px，身份和状态已测试）
BACKGROUND_REGRESSION: PASS（动效、暂停、媒体仿真；另有一次侧栏像素波动，见 §4）
KEY_INTERACTION_REGRESSION: PASS（模拟交互；真人/触控板未测）
NATIVE_ZOOM_200: PASS（macOS Chrome 原生 UI，三页操作，恢复 100%）
PRODUCT_CODE_CHANGED: NO
UAT_CHANGED: NO
PR61_PR62_CHANGED: NO
VISUAL_OWNER_ACCEPTANCE: PENDING_OWNER
STOP_STATE: R6A2_2_DESIGN_REVIEW_READY
```
