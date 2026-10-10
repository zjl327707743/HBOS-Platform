# 侧边栏「工作台优先」视觉验收

- source visual truth: `/Users/hbzl/.codex/generated_images/01a0c696-d4c7-7552-bf3b-8883c0919029/exec-7a274146-6ec3-414b-8e00-fcba15a40007.png`
- implementation: `http://localhost:4173/stability/schedule`
- implementation capture: Codex in-app browser capture at the implementation URL, 1284 × 988 pixels; CSS viewport and device scale were not exposed by the in-app browser, so no density resampling was applied
- source pixels: 1487 × 1058; implementation pixels: 1284 × 988
- comparison scope: 左侧导航区域；主内容沿用现有真实 LIMS 页面，不复制概念图中的演示数据
- state: 展开侧边栏、稳定性管理展开、取样与检测计划为当前入口

## Findings

无 P0/P1/P2 问题。

- 信息架构：已落地「我的工作 / 全部模块 / 最近访问」三级结构；模块可独立展开或收起。
- 布局与节奏：保留现有 232px 侧栏宽度、深绿色底色和固定底部操作区；子菜单用左侧层级线表达归属。
- 交互状态：当前路由自动展开所属模块；全部展开 / 全部收起、侧栏整体收缩均已验证。
- 角标：稳定性子入口角标仍来自现有真实接口；未新增演示数据源。
- 当前高亮：根入口采用精确匹配，避免进入子页面时同时高亮「稳定性工作台」和具体子页面。

## Required fidelity surfaces

- Fonts and typography: 沿用项目现有系统字体、字号层级和 Ant Design 图标体系。
- Spacing and layout rhythm: 沿用现有 token 与 232px / 64px 展开收缩尺寸，新增模块树缩进与最近访问分隔线。
- Colors and visual tokens: 沿用现有深绿色侧栏、teal 主色、amber 待办色和 danger 角标色。
- Image quality and asset fidelity: 沿用现有 `/joincare-mark.png` 品牌资源；导航图标来自已安装的 `@ant-design/icons-vue`，未用 CSS / SVG 绘制替代。
- Copy and content: 所有入口名称均对应现有 Vue 路由；未新增后端业务入口。

## Interaction evidence

- 模块展开 / 收起：通过浏览器可访问性树确认 `aria-expanded` 由 collapsed / expanded 正确切换。
- 当前路由自动展开：直接打开 `/stability/schedule` 后「稳定性管理」自动展开。
- 全部展开 / 全部收起：五个模块均能批量切换。
- 侧栏整体收缩：展开态与 64px 图标态均已确认。
- 最近访问关闭：每行右侧叉号可独立移除项目，点击不触发路由跳转；关闭状态刷新后保留，全部关闭时可恢复。
- 生产构建：`npm run build:prod` 通过。

## Final result

passed

# LIMS Dashboard V2 视觉验收记录

日期：2026-09-30
页面：http://127.0.0.1:5178/hbos/lims
目标：复核 Owner 已验收的 LIMS P4-F2 V2 原型在 Portal Vue 实现中的首屏落地。

## 验收证据

- 运行进程：当前源码启动的 Vite Mock 预览，已替换旧的 Frappe 模式 5178 进程。
- 浏览器可见：双品牌 Header、LIMS Local Shell、实验室主视觉、中文检验员 Hero、四项工作指标、检验流程条、任务队列、样品条码与进度、实验室日程、常用操作。
- 响应式：窄屏下切换为移动底部导航；1280px 以下 Local Sidebar 切换为图标模式，避免导航文字挤压。
- 数据边界：Mock 指标、样品和日程只在 Mock 分支使用；真实 Frappe 分支只渲染 Provider 返回数据或安全空态。

## 结果

- 视觉目标：PASS
- 中文优先与品牌使用：PASS
- LIMS 模块入口与能力门控：PASS
- 真实模式不补 Mock 业务数据：PASS
- 构建与契约门禁：PASS

真实 Frappe Session 和正式 Provider 字段仍需 Docker/Frappe 工作台恢复后单独验证。

**Final result: passed**
