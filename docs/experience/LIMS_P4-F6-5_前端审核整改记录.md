# LIMS P4-F6-5 前端审核整改记录

状态：**P4-F6-5 审核整改完成 / 真实 Frappe 运行态证据待环境恢复**
日期：2026-09-30

## 1. 审核结论确认

本轮复核确认两份审核报告指出的问题成立，主要集中在真实 Frappe 模式的错误传播、能力边界和前端安全兜底；不涉及 LIMS 业务流程本身的改造。

已确认并处置的阻断项：

1. 稳定性 API 默认 `limit=100` 超过 Portal 上限 50，导致真实模式必然返回错误；前端还会保留 Mock 汇总。
2. 留样与稳定性服务的真实模式回退体会泄漏 Mock 汇总。
3. 各 LIMS 读取服务未统一检查 `ok:false`，后端错误会被吞成空列表。
4. 业务权限拒绝（403）被误判为会话失效并清空登录态。
5. 结果、台账、留样的公开入口能力比领域服务角色范围更宽。
6. COA、质量标准、留样投影存在无界 ORM 读取风险。
7. 结果复核孤儿组件、首页假数据和管理后台死入口仍在前端产物中。

## 2. 已完成修改

### 服务与 API 契约

- 稳定性前端默认上限与后端 `normalize_limit` 对齐为 50。
- `PortalProvider` Protocol 的稳定性默认参数同步为 50，避免接口签名与 API 上限再次分叉。
- 真实 Frappe 分支改为纯空 DTO，不再合并 `mockEnvelope`。
- 新增 `unwrapPortalMethod()`，所有 LIMS 读取服务统一传播 `ok:false` 和错误码。
- 新增稳定性 API 契约测试，覆盖上限、越界错误封装和不派发 Provider。
- Frappe 403 仅在明确 `UNAUTHENTICATED` 时触发登录失效；普通 `FORBIDDEN` 保留在当前页面错误态。
- 登出时清理 CSRF 缓存。
- Mock 模式的结果写入服务 fail-fast，禁止向真实写接口发起请求。
- 业务跳转仅接受站内绝对路径，并拒绝协议相对路径、反斜杠和编码后的路径穿越。

### 权限与入口

- LIMS Provider access context 增加结果读取、台账读取、留样读取、结果提交、复核、批准等语义能力。
- Portal dispatcher 对结果、台账、留样能力增加语义能力校验，复制 URL 不能绕过入口门控。
- 新增 Administrator 三个 LIMS 读取能力、语义能力映射、具备能力可访问和无角色 / 缺失能力拒绝测试；真实 Frappe integration check 同步断言三项读取能力。
- 结果录入页按提交、复核、批准能力分别显隐动作按钮。
- 侧栏与移动导航按 `view` 查询参数精确高亮待检、复核、审批。
- 删除管理后台静态卡片、死按钮、恒不渲染的 management 分支；Management V0 继续关闭。

### 数据读取与工程质量

- COA、质量标准改为带筛选和有限页大小的 `get_list` 查询。
- 留样关联产品只按当前页样品的产品编号读取，不再使用 500 或无界查询。
- 删除未接线的 `_collect_coa_todos`、孤儿 `LimsResultReviewView` 和硬编码 `LimsHomeView`。
- LIMS 路由改为按页面动态加载，构建结果已出现独立页面 chunk。
- 结果页桌面布局调整为设计基线要求的主工作区 `8:4`，768px 下上下堆叠；任务、结果、台账相关断点对齐 1280 / 768 / 390。

## 3. 验证证据

- LIMS Portal Provider / 投影测试：48 项通过，新增 Administrator 三个 LIMS 读取能力断言。
- Portal API 契约测试：19 项通过，新增语义能力映射、允许访问和缺失能力拒绝断言。
- `bash scripts/portal/lims_shell_contract.sh`：`LIMS SHELL CONTRACT PASS`。
- `npm run test:contract`：`LIMS FRONTEND CONTRACT PASS`。
- `npm run build`：`vue-tsc -b && vite build` 通过，路由页面已拆分为独立 chunk。
- `git diff --check`：通过。

本轮未启动本地 Frappe 工作台，因此没有把本地 Mock 预览结果表述为真实 Session 集成通过；真实 Provider 数据、Dashboard 专用风险字段和样品 Provider 仍需在环境恢复后做运行态验收。

## 4. 后续不阻断项

- Portal 与 Native LIMS 的分页字段仍需后续统一 contract，当前不改变业务 Authority。
- Dashboard 的超期/OOS、近期样品和检验组分布继续显示安全空态，待真实 Provider 字段契约补齐后再接图表。
- `npm run test:contract` 是源码级正则防回归检查，用于确认关键接线没有被删除；它不等同于运行时行为测试。更细粒度的前端单元测试框架、通用类型收敛、无障碍表格细节和主 vendor chunk 继续作为后续工程化任务。
