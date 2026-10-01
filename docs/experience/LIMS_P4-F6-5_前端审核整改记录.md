# LIMS P4-F6-5 前端审核整改记录

状态：**REVIEWING / 2026-10-01 Portal 审核修复与本地验证完成 / 待 Owner 验收及真实 Frappe 运行态证据**
日期：2026-09-30；更新：2026-10-01

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

本轮已切换到 `feature/hbos-portal-product` 并提交 `627c3db`。随后执行 `scripts/portal/p3_workspace_runtime_smoke.sh`，因本机没有 `docker` 命令，在 Compose 启动前退出；因此真实 Frappe Session、401/403 运行态和 stability / retention 真实数据仍未验证。

## 4. 后续不阻断项

- Portal 与 Native LIMS 的分页字段仍需后续统一 contract，当前不改变业务 Authority。
- Dashboard 的超期/OOS、近期样品和检验组分布继续显示安全空态，待真实 Provider 字段契约补齐后再接图表。
- `npm run test:contract` 是源码级正则防回归检查，用于确认关键接线没有被删除；它不等同于运行时行为测试。更细粒度的前端单元测试框架、通用类型收敛、无障碍表格细节和主 vendor chunk 继续作为后续工程化任务。

## 5. 2026-10-01 Portal 审核确认与修补

本次由 Owner 明确授权确认审核结果并执行修复，沿用已批准的 P4-F2 原型和 P4-F6-5 实施范围。工作分支为 `codex/portal-review-fixes`，基线为本地 `feature/hbos-portal-product` 的 `e718001`。没有推进样品 Provider 或管理后台门禁。

### 核验结论

- 四个页面的未定义 CSS token、bootstrap 错误被路由守卫误判为无权限、搜索逐字符请求、刷新函数缺少最终异常兜底均确认。刷新函数的风险以 Provider 抛出异常为前提；现有 API 聚合内部已经使用 `Promise.allSettled`，不能据此声称每次子请求失败都会产生未处理 rejection。
- 留样页的五处显式 `any`（审核写为六处，基线实数为五处）、留样/稳定性工作台压缩写法、重复映射和查询样板均确认。
- 当前基线中台账页与结果页的「已提交」均为 `processing`，审核所称该项已分叉不成立；重复定义仍应收敛。草稿、复核及稳定性标签存在其他差异，本轮统一视觉映射，不改业务状态。
- 原型扫码入口、偏好按钮和本地开关、固定应用数与问候语、未接线的 3D 控件，以及环境变量/趋势图文档缺口均确认。
- Portal `src/` 未发现 `v-html`、`innerHTML`、`console.*` 或硬编码本地服务地址。能力名与后端 access/manifest 对齐；样品能力仍未发布。构建产物和依赖未被 Git 跟踪。这些核验只覆盖本轮 Portal 源码，不等于全面安全认证。

### 修复交付

1. COA / 质量标准 / 留样 / 稳定性页面统一使用既有 HBOS 文本与边框 token；LIMS 强调色放入 `:root`，兼顾脱离页面根节点的 Drawer。
2. 实际路由守卫抽入 `portalGuard.ts`：先做登录校验；bootstrap 非鉴权失败时留在当前 URL。两套 Shell 显示错误与重试，并暂不挂载业务页；恢复 bootstrap 后强制重新经过能力门控。
3. 搜索加入 280ms 防抖、过期响应保护、关闭/卸载取消和可见错误态；移除假扫码操作及其键盘选择槽位。
4. `refreshTasks` / `refreshSummaries` 捕获异常、复位 loading，保留上次成功结果并在 Shell 显示失败提示。
5. 留样/稳定性工作台重排为多行；留样申请采用 Usage/Disposal 联合类型与字段收窄，提醒项有独立 DTO，显式 `any` 全部移除。
6. 图标、中文应用名和主应用展示顺序收敛到 `appIcons.ts`；状态/判定色收敛到 `limsStatus.ts`；六个列表页共用 `useLimsQueryPage` 管理 URL、加载、错误、分页互斥和过期响应。
7. 工作偏好按钮连接设置页，应用数和筛选项来自 Provider；真实模式偏好控件禁用并标注「即将开放」；数字孪生仅在 Mock 预览中展示，3D 入口标注未开放；问候语改为中性「你好」。
8. 登录回跳与业务导航复用 `internalPath.ts`；补记 `VITE_BASE` / `VITE_FRAPPE_BASE_URL`；移除 README 中未使用的 ECharts 依赖声明。Ant Design 仅注册实际用到的组件及其子组件。

### 验证与限制

- `npm run test:unit`：14 项通过，使用真实 Store、守卫、Vue 生命周期和 Shell 渲染，Provider 为隔离测试夹具。覆盖 500/网络错误、401/未认证403、能力拒绝与重试、刷新失败、防抖/乱序/取消、URL 恢复、旧页面响应、回跳安全、CSS token 和 Ant 子组件注册。
- `npm run test:contract`、`bash scripts/portal/lims_shell_contract.sh`、`npm run build` 和 `git diff --check`：通过。
- 5193 独立 Mock 浏览器预览：留样强调色实际为 `rgb(23, 74, 69)`、辅助文字为 `rgb(66, 86, 117)`；稳定性正文为 `rgb(23, 37, 60)`、SVG 趋势线为 `rgb(32, 170, 131)`。检查页没有浏览器 error/warn；临时页面和进程已关闭。
- Ant chunk：1459.68 → 857.22 kB，gzip 442.13 → 255.57 kB。仍存在大于 500 kB 的 vendor chunk 警告，不将其描述为已完全解决。
- 本轮未部署、未推送、未执行真实 Frappe Session/业务数据联调；不将夹具与 Mock 浏览器验证记为真实集成通过。Owner 最终验收及此前真实运行态 Gate 保持待办。

### 文档与治理检查

已同步 `PROJECT_STATUS.md`、`CURRENT_MILESTONE.md`、M2 阶段门禁、本轮主文档和实施计划；M1/M3 门禁已检查，并修正 M1 门禁中「M2 其余轮次未启动」的过期并行工作线描述；本轮不改变其业务子轮状态。README、AI_CONTEXT 和 READING_GUIDE 中 Portal 当前状态已同步，并修正与已授权并行工作线矛盾的「M2 未启动」描述；CLAUDE/AGENTS 只规定默认协作边界，无需因本轮修复修改。Skill 路由未变；本环境没有 `superpowers`，按项目规则做等价人工执行。新增文件为 TypeScript 源码和 Node 测试，英文文件名沿用前端生态约定；没有新增英文文档或提交信息。

## 6. 2026-10-01 合并至 m2-r10

按 Owner 指令，将源工作区尚未提交的 50 个文件整改提交为 `f23ba17`（`fix: 完成 Portal 前端审查整改与状态同步`），再将 `codex/portal-review-fixes` 合入 `m2-r10`。后续开发工作分支为 `m2-r10`。

合并前重新执行 14 项前端单元回归、前端契约、Shell 契约、TypeScript 检查与生产构建，全部通过。合并无冲突；本轮只整合既有整改及同步分支记录，P4-F6-5 继续为 REVIEWING，Owner 验收与真实 Frappe 运行态证据仍待补齐。主工作区既有未跟踪的 `LIMS_P4-F6-7_前端代码审核报告.md` 保留，不纳入合并提交。
