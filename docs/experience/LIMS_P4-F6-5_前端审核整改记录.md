# LIMS P4-F6-5 前端审核整改记录

状态：**REVIEWING / 2026-10-08 当前 Site 飞书登录已启用，精确回调通过 / Owner 完整 OAuth 待验收**
日期：2026-09-30；更新：2026-10-08

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

## 7. 2026-10-01 LIMS 侧栏溢出与滚动修复

状态：**SOURCE FIX COMPLETE / UNIT + CONTRACT + BUILD PASS / BROWSER RECHECK PENDING**。工作分支为 Owner 指定的 `m2-r10`，未创建新分支。

Owner 截图显示菜单越过侧栏卡片底部，且没有侧栏滚动条。源码确认：侧栏固定高度且设置 `min-height: 540px`，长菜单未设置滚动容器，也未允许 Flex 子项缩小；矮窗口中最小高度还会覆盖可用视口高度。

修复仅涉及 `AppLocalSidebar.vue` 与 `global.css`：LIMS 侧栏取消最小高度下限，使用 `100vh` / `100dvh` 减去顶部和底部预留高度；标题与返回按钮不缩小，菜单采用 `flex: 1`、`min-height: 0` 和 `overflow-y: auto`，并补齐细滚动条、稳定滚动条间距及滚动边界；移除多余的 Flex 占位元素，为菜单保留可聚焦的键盘滚动入口。导航内容、稳定路由和 capability 门控未改动。

验证：14 项既有前端回归、`test:contract`、`lims_shell_contract.sh`、TypeScript 检查、生产构建与 `git diff --check` 均通过。这些检查不验证浏览器中的滚动几何。浏览器打开本机 5178 预览时，自动审批因网络中断未完成，动作未执行；本轮没有浏览器复测或截图证据。待复核长菜单滚动到底部、矮窗口边界、键盘滚动，以及移动端导航。P4-F6-5 继续 REVIEWING，Owner 与真实 Frappe 运行态门禁保持待办。

## 8. 2026-10-01 当前基线全面复核与缺陷修补

2026-10-01 在 Owner 指定的 `m2-r10` 完成 Portal 当前基线复核与缺陷修补：显式数据模式/生产构建门禁与演示标识、真实文案、侧栏滚动/768px 导航、登出与会话收敛、动作语义任务计数、结果/任务游标分页、Provider 部分失败与 trace_id、锁文件/npm ci/ESLint/测试与 Mock AST 门禁；34 项回归及 lint、两套契约、Mock 门控、两种显式构建通过。浏览器已确认 1280×720 菜单滚动和 768/767px 导航切换；矮窗口补测被自动审批网络断开阻断，真实 Frappe 联调与 Owner 验收仍待完成。P4-F6-5 保持 REVIEWING，不新建分支、不部署、不推送；巨型视图拆分保留重构项。原 P4-F6-7 报告已保留评审痕迹并标注误报、旧基线和本轮处置。

### 证据与实施范围

复核基线：`m2-r10` 的 `553bc53`，保留此前未提交的侧栏滚动和分支审批规则。原报告零单测、命令面板扫码入口和后台刷新无 catch 的陈述不符合 `f23ba17` 后代码，已在原报告显著位置标注，没有用旧行号重复整改。

真实任务投影是待处理动作集合：稳定性时间点「已完成」但待趋势评价、留样申请「已批准」但待执行，仍归 open。后端未提供的等待/完成历史不由前端补造。结果动作继续由现有领域 API 校验，前端仅按能力与状态展示；OOS 禁止批准且允许独立复核。

- `npm ci`：使用新锁文件安装成功；第一次连接重置后有限重试成功。
- `npm run lint`、`npm run test:unit`：34 项通过，覆盖实际 Vue 结果页/任务页加载更多、游标重置、会话 TTL/失效/并发/退出后旧请求、分页多页、部分失败、关联编号、模式门禁、只读文案与真实组件渲染。
- `npm run test:contract`、`npm run test:mock-gate`、`bash scripts/portal/lims_shell_contract.sh`：通过。Mock 门控为模板 AST 检查加组件运行回归；不声称已自动证明任意动态内容都不会污染。
- `VITE_PORTAL_DATA_MODE=frappe npm run build`：类型检查与构建通过；生产构建拒绝 `frape` 与 `mock` 已实测；`npm run build:mock -- --outDir /private/tmp/hbos-portal-review-mock` 通过，未覆盖真实模式 dist。
- Mock 浏览器：1280×720 侧栏 bottom=708，菜单 368/838px，End 后 scrollTop=470，末项在菜单内；768×1024 保留侧栏，767×720 显示底栏和 78px 避让。矮窗口后续动作被自动审批拒绝，原因是审核网络传输断开；未绕过审批，也未获得真实 Frappe Session/业务数据证据。

已同步 PROJECT_STATUS、CURRENT_MILESTONE、M2_START_GATE、P4-F6 实施计划及本主记录；公共入口 README、AI_CONTEXT、READING_GUIDE 追加当前复核状态，CLAUDE/AGENTS 记录 Owner 分支审批规则。没有改架构、业务事实或其他里程碑状态。原稿其他 P1/P2 改进项和巨型视图拆分不作为本轮已全部解决的内容。

公共入口检查 WARN（既有、非 Portal 范围）：README 主线记为 M1-FIX-F，而 AI_CONTEXT / CURRENT_MILESTONE 仍有 M1-FIX-B5 的主线描述；本轮只同步已授权 Portal 进度，没有据此自行更改其他工作线的里程碑事实。

## 9. 2026-10-01 Owner 选定侧栏滚动条方案 B

状态：**IMPLEMENTED / LOCAL CHECKS + MOCK BROWSER PASS / REVIEWING**。Owner 在三种案例图中选择方案 B，作为本轮视觉方向批准；在指定的 `m2-r10` 实现，没有创建新分支。

实现仅涉及 `AppLocalSidebar.vue` 和 `global.css`：菜单内容溢出时才显示浅灰蓝圆角滑块，全部可见时无滑块，滑轨透明，悬停、滚动或菜单内键盘聚焦时滑块加深，停止滚动 800ms 后退出滚动态；若仍悬停或聚焦则保留增强色。WebKit 滚动条为固定 6px，其他引擎保留原生 thin 滚动条，稳定 gutter 避免文字位移。菜单保留原生滚轮、拖动和键盘行为，补充键盘焦点轮廓及系统强制颜色适配；卸载时清理滚动计时器。标题和返回按钮继续固定，仅菜单滚动。

验证结果：

- `npm run lint`、34 项 `test:unit`、`test:contract`、`test:mock-gate`、`lims_shell_contract.sh`、`VITE_PORTAL_DATA_MODE=frappe npm run build` 均通过；既有 Ant vendor 大包警告仍在。
- 本机 5193 独立 Mock 浏览器：1280×720 默认滑块为 `rgba(111, 133, 166, 0.34)`，交互加深，退出悬停/聚焦且计时结束后恢复浅色；菜单宽度 58px、clientWidth 52px，状态切换前后不变，滚动条宽度 6px。滚动事件实际设置增强状态，结束后解除。
- 键盘 Home / End 可以滚动菜单；End 动画结束后 scrollTop=470/max=470，末项 bottom=679，小于菜单 bottom=681。键盘聚焦有可见轮廓。
- 1440×540 矮窗口：初始侧栏 bottom=528，菜单高度 233px/content 868px；End 后 scrollTop=635/max=635，末项 bottom=499，小于菜单 bottom=501，标题和返回按钮保留在菜单外。此前矮窗口补测缺口已由本轮 Mock 浏览器证据补齐。
- 768×1024：侧栏 flex、移动导航 none；767×720：侧栏 none、移动导航 grid。1440×900 保存默认及交互实际截图，菜单宽度 218px/clientWidth 212px，状态切换前后不变。

已同步 PROJECT_STATUS、CURRENT_MILESTONE、M2_START_GATE、实施计划及本记录；公共入口文件已检查，本轮无阶段变更，无需追加重复状态描述，§8 所列其他工作线 WARN 保留。本环境指定的 `frontend-design` / `superpowers` 不可用，按项目规则人工实现与复核。P4-F6-5 保持 REVIEWING；视觉方向批准不等于最终交付验收，真实 Frappe 运行态证据仍待补齐。

Owner 后续要求「将滑轨隐藏」：仅修改 CSS，将轨道设为透明并移除交互时的轨道加深，保留滑块和稳定 gutter。本次重新执行真实模式生产构建与 `git diff --check`，均通过；1440×900 Mock 浏览器确认默认、悬停/聚焦及滚动状态的轨道均为 `rgba(0, 0, 0, 0)`，滑块可见且宽度仍为 6px，菜单宽度 218px/clientWidth 212px 不变，滚动到 scrollTop=275/max=275 时末项 bottom=871 小于菜单 bottom=873。已保存隐藏滑轨实际截图。本次没有新增测试或重复执行前述 34 项回归；前述结果属于方案 B 实现验证。

Owner 进一步确认滑块仅在菜单溢出时显示。本轮只做运行态确认，既有 overflow-y: auto 已满足要求，无需更改源码。1440×1200 Mock 预览中，菜单 clientHeight/scrollHeight 均为 893px，最大 scrollTop=0；全部菜单可见，悬停和聚焦时也没有滑块。缩小至 1440×900 后，菜单为 593/868px，滑块出现并可滚至 scrollTop=275/max=275；再放大至 1200px 高后自动恢复无滑块且 scrollTop=0。全过程菜单宽度 218px/clientWidth 212px 不变，滑轨透明。两种实际截图已保存，显示规则已同步至状态记录、M2 门禁和实施计划；本轮没有代码变更或重复执行构建/单测，既有其他工作线 WARN 与真实 Frappe 门禁保持原状态。

Owner 反馈 5178 无法连接服务器：本机检查确认 5178 没有监听进程；同项目已有 Node 服务监听 127.0.0.1:5179。此前侧栏检查使用临时 5193 实例，验证后已关闭。现已在 m2-r10 以 npm run dev:mock -- --host 127.0.0.1 --port 5178 --strictPort 恢复当前源码预览，lsof 确认监听，浏览器确认 5178/hbos/lims 正常显示 LIMS 与 Mock 标识；服务保留供 Owner 继续验收。本轮未修改源码，PROJECT_STATUS 与 M2 门禁已同步；里程碑和轮次未改变，CURRENT_MILESTONE 无需新增记录；公共入口已检查，本次运行入口恢复无需修改入口描述，既有其他工作线 WARN 保留。

## 10. 2026-10-02 恢复 5178 真实开发模式与专业菜单

状态：**REAL FRAPPE MENU + READ-ONLY HTTP RECHECK PASS / REVIEWING**。全程在 Owner 指定的 `m2-r10`，未创建分支。§9 中将 Mock 临时放在 5178 的做法已纠正；当前 5178 为 Vite development + `frappe` 数据源，5179 留给隔离 Frappe 预览，Mock 默认使用 5193。`dev` 是运行方式，`frappe` / `mock` 是数据来源；共享 Vue / CSS 改动适用于两种数据源，此前 Mock 视觉检查未替代真实联调。

### 根因与处理

- Owner 截图的真实 Bootstrap 仍返回旧版 LIMS `summary / tasks / search`，且缺少语义访问能力，前端因此按现有门控隐藏专业业务入口。经认证的 HTTP 连续三次确认旧能力；同一后端容器中，新启动的 `bench execute` 能读取当前全部 10 项能力。源码挂载指向本工作区，确认是常驻 Web 进程加载旧代码。
- 已清理现有 `frontend` Site 的 Frappe 缓存、重启 `hbos-m0-r3a-backend-1`。重启后 Nginx 仍连接旧容器地址，日志为 `No route to host` / 502；已重载现有 `hbos-m0-r3a-frontend-1` 的 Nginx，恢复真实 API。未安装软件、创建 Site/App、执行迁移或改写业务记录。
- `dev:frappe` 固定默认端口 5178，`dev:mock` 固定默认端口 5193；Vite 默认端口随显式数据源选择，并启用 `strictPort`，占用时失败而非自动递增。真实 API 代理默认值由 8081 对齐现有本机 8080，环境变量可覆盖。隔离脚本既有 5179 → 18091 配置保持有效。更新前端 README，解释模式、端口与旧进程排查方法。

### 真实证据与检查

- `hbos_portal.integration_checks.run` 在现有 Site、新进程中通过：三 Provider 注册无失败，LIMS manifest 与语义权限检查通过。此项与后续 HTTP 分别记录，避免用新进程检查替代 Web 运行态。
- 代理恢复后，通过 5178 正常登录；Bootstrap 连续三次均返回 `summary / tasks / search / results / ledger / audit / coa / specifications / retains / stability`，并返回 `lims.read / lims.results.read / lims.ledger.read / lims.retention.read / lims.results.submit / lims.results.review / lims.results.approve / lims.audit.read`。summary、tasks、results、ledger、audit、coa、specifications、retention、stability 九类只读 HTTP 均 `ok: true`。
- 浏览器通过现有 Administrator 账号正常登录，真实首页显示 Provider KPI 与完整专业菜单，无「演示数据」横幅；结果台账读取现有 Site 的 16 个样品、34 条结果，稳定性工作台读取现有样品、时间点和房间数量。现有测试记录来自该 Site 数据库，不是前端 Mock，也不据此宣称正式业务数据验收完成。
- 1440×900 真实浏览器：菜单 clientHeight/scrollHeight 为 625/868px，End 后 scrollTop=243/max=243，末项 bottom=859px 小于菜单 bottom=861px；滑轨为透明。1440×1200：菜单为 925/925px，最大滚动量为 0，内容全部可见时无滑块。方案 B 已在真实长菜单中验证。
- `npm run lint`、34 项 `test:unit`、`test:contract`、`test:mock-gate`、`lims_shell_contract.sh`、真实模式类型检查/生产构建与 `git diff --check` 通过。Vite 配置解析确认两种数据源均为 development，端口分别 5178/5193，strictPort 为 true；真实代理指向 8080。既有 Ant vendor 大包警告保留。

已同步 PROJECT_STATUS、CURRENT_MILESTONE、M2_START_GATE、实施计划与公共 Portal 入口说明；CLAUDE/AGENTS 无过期 Portal 阶段描述，不需修改。没有改变里程碑/轮次，P4-F6-5 保持 REVIEWING：真实菜单、只读接口与侧栏证据已补齐，完整角色/签署写流程、四档真实截图及 Owner 最终验收继续待办。未提交、未推送；§8 所列其他工作线 WARN 保留。指定的 superpowers / frontend-design 不可用，本轮按项目规则人工执行与复核。


## 11. 2026-10-02 m2-r11 合并后检查与问题修复

状态：**REVIEWING / MERGED BRANCH LOCAL FIX VERIFICATION PASS**。当前分支 `m2-r11`，合并基线 `f13be09795b13e321d3cbcb582f7d976e937a296`，父提交为 `4d9486d` 与 `114a0cb`。Owner 先要求合并冲突 / 漏洞检查及测试，随后授权问题修复。没有未解决的 Git 索引冲突、合并进行中状态或源码冲突标记。

本轮读取 CLAUDE、AGENTS、AI_CONTEXT、PROJECT_STATUS、CURRENT_MILESTONE，按测试 / Skill 路由要求读取 `docs/AI技能路由规范.md`，并定向读取本整改记录、RP3 主文档、M2_START_GATE 与公共入口；未递归读取 docs，也未默认读取 archive / research / legacy。指定的 superpowers 在当前环境不可用，按项目规则人工执行复现、回归、整改与复核。

### 问题与修复

- **CSRF 缓存分叉**：旧 LIMS 拦截器缓存会覆盖 Portal 请求或登录刚取得的安全令牌。`frappeClient.ts` 改为一个缓存与共享的令牌请求，保留调用方显式提供的令牌，LIMS 写入复用 Portal POST 客户端；登录 / 登出、CSRF 拒绝及会话清理后不再使用旧 HTML 注入令牌。错误后不自动重放业务写操作，下一次明确重试取得新令牌。
- **旧请求竞态**：会话切换后，旧令牌请求的结果不能覆盖新缓存；旧操作返回 CSRF_MISMATCH，不误判为 UNAUTHENTICATED 而清空新会话。并发写请求共享一次令牌读取。
- **LIMS 重试仍显示旧错误**：布局重试改为调用同一个 `usePortalSession.synchronize()`，成功后清除错误并重新校验 App 访问资格，再重新进入受路由守卫保护的页面；失去 LIMS 资格转入 403。
- **统一登录入口**：开始修复前工作区已有 `main.ts`、路由、守卫和对应测试修改，失效会话与旧 `/login` 转到 `/hbos/login`，保留安全 `redirect_to`；该已有修改经回归验证并保留。修复期间出现的资料页管理员身份 / 部门展示修改同样保留，未覆盖其他工作线。
- **依赖漏洞**：Portal 的 Vitest `3.2.4 → 4.1.11`，兼容的 js-beautify 间接 glob 固定为 `10.5.0`，同步 package-lock；网关 FastAPI `0.128.8 → 0.142.2`、Starlette `0.49.3 → 1.7.0`，固定新增传递依赖 opentelemetry-api `1.45.0`。新增 `requirements-test.txt` 固定 HTTP 测试依赖 httpx `0.28.1`，发布 CI 安装该文件，生产 Docker 仍只安装 requirements.txt。
- **合并分支治理**：前端 CI push 入口加入 `m2-r11`，当前分支说明与状态台账同步；旧分支 / PR 发布证据按日期保留，不批量替换历史记录。

### 验证与审查边界

- 合并检查阶段的全仓离线基线：**1275 passed / 33 skipped**，覆盖 Portal、独立 LIMS 前端、LIMS / 考勤 / 库存 / Portal / 知识 / 孪生后端、网关、本机脚本与 OCR。33 项跳过需要真实 Frappe 运行态；不作为 PASS。
- 修复前新增用例先出现 **5 failed / 2 passed**，修复后通过；追加旧令牌请求竞态用例先 FAIL 后 PASS。最终新增 **8 项前端**回归（CSRF 6、会话重试 2）及 **5 项网关 HTTP**边界回归（正确 JSON、缺失 / 错误认证、身份 / 范围限制、旧政策 / 无效输入、健康响应不泄漏配置）。采用合成令牌与数据，未操作真实账号或业务记录。
- 更新后的锁文件经 `npm ci --ignore-scripts --no-audit --no-fund` 重新安装验证；Portal Node **34/34**、Vitest **60/60**、网关 Python **10/10**通过。ESLint、TypeScript、前端契约、Mock AST 门禁、Shell 契约、真实数据模式生产构建及 `git diff --check` 通过。网关依赖安装和 HTTP 测试使用隔离的 Python 3.12 临时目录，没有更新运行中服务或安装 Frappe。
- 官方 npm Portal 锁文件在线审查：**388 个依赖 / 0 项已知漏洞**；网关固定的 **14 个 Python 包 / 0 项已知漏洞**。OCR 锁文件 **109 个包**与 Portal pypinyin 的合并检查结果为 0 项已知漏洞，本轮未改变其版本。不据此宣称项目没有业务逻辑漏洞。Starlette 已知风险包括特定 URL、表单、静态文件及端点条件；当前项目可利用性未由审查证明。
- **LIMS 独立前端在线依赖审查未完成**：自动审批拒绝向官方 npm 发送该子项目依赖元数据，原因是缺少明确授权；已提出授权请求，尚无答复。未绕过审批。既有离线测试 / 构建通过不替代在线漏洞审查。
- 本轮未执行真实 Frappe / Docker 联调、角色与签署写流程、OAuth / final-submit 或新部署后的 Owner 验收；§10 的旧分支真实只读证据作为历史保留。既有 Ant vendor 构建体积提示保留。

已同步 PROJECT_STATUS、CURRENT_MILESTONE、M2_START_GATE、RP3 账号边界主记录及 README / AI_CONTEXT / READING_GUIDE；CLAUDE / AGENTS 已检查，无过期阶段描述，无需改动。本轮未新增业务轮次，P4-F6-5 保持 REVIEWING。未新建或切换分支、提交、推送、部署或改写真实账号数据；后续先补真实运行态与 Owner 验收，再进行放行。

## 12. 2026-10-07 恢复 5178 开发入口

状态：**LOCAL ENTRY HTTP CHECK PASS / REVIEWING**。Owner 反馈 5178 无法连接服务，按该问题恢复既有 Portal 开发入口；权限管理仍保持“先不动代码、第一步逐项推进”。当前分支为 `m2-r11@27d3558`，没有创建或切换分支。

### 原因与处理

- 5178 没有监听进程，连接失败发生在前端服务入口。仓库 Vite 配置及 package.json 已指定 5178 为真实 Frappe 开发，5193 为 Mock；5178 与固定 P1 的 5188 是不同入口。
- 本机既有 `.env` 的路由摘要为 project `hbos-m0-r3a`、Site `frontend`、HTTP_PORT `8080`；只读取这些路由字段，没有输出凭据。8080 的公开 Frappe ping 返回 HTTP 200 / pong。
- 使用已存在的 Node、npm 和 node_modules，以现有命令恢复前端；未执行会安装 App 或刷新后端的整套启动脚本，也未运行依赖安装。

```bash
cd frontend/hbos-portal-web
VITE_FRAPPE_PROXY_TARGET=http://127.0.0.1:8080 \
VITE_FRAPPE_APP_ORIGIN=http://127.0.0.1:8080 \
npm run dev:frappe -- --host 127.0.0.1
```

开发进程保留运行，仅监听 `127.0.0.1:5178`；Vite 的 strictPort 继续启用，没有自动改端口或切换数据源。

### 实际验证

| 检查 | 本轮结果 |
| --- | --- |
| lsof 监听 | Node 监听 127.0.0.1:5178 |
| /hbos、/hbos/login、/hbos/lims | 均 HTTP 200，返回含 Vite 入口的 HTML |
| /@vite/client、/src/main.ts | 均 HTTP 200；入口模块注入 frappe 数据模式 |
| 5178 代理的 /api/method/frappe.ping | HTTP 200 / pong |
| 无凭据访问受保护 Bootstrap | HTTP 403，未登录仍被拒绝 |

这是入口、模块传输与代理连通性检查，没有浏览器渲染、真实登录或签署业务验收证据；HTML 200 不代表各业务页面或权限已经完整验收。不因本次恢复重跑无关测试或更新源码。

本轮只有运行进程恢复及文档同步，未修改业务代码、依赖、Site 配置、账号、角色、数据库或 Docker 服务。PROJECT_STATUS、CURRENT_MILESTONE、M2_START_GATE 和公共入口已同步；CLAUDE / AGENTS 的规则无变化，无需修改。未提交、推送或部署。

权限管理的 P1 来源定位仍为 PARTIAL / 实际权限盘点 NOT_RUN；恢复 frontend 的 5178 开发入口不等于找到了 P1，不自动替换固定目标。P4-F6-5 继续 REVIEWING，完整真实角色 / 签署流程与 Owner 验收仍待办。

## 13. 2026-10-08 退出后密码登录来源修复

状态：**LOCAL LOGIN ORIGIN FIX VERIFIED / REVIEWING / Owner 真实登录待复验**。Owner 截图显示退出后密码登录报“安全会话已更新”。沿用既有 `m2-r11`，未创建或切换分支，保留工作区权限原型、资料页及其他已有改动。项目指定 superpowers 当前不可用，按既有规则人工执行；未调整 Skill 路由。

### 根因与最小修复

- 使用匿名会话和虚构账号复现：`127.0.0.1:5178` 的 `password_login` 返回 HTTP 400 / CSRFTokenError，服务端实际消息为“请求来源无效”；同源 localhost 请求返回 HTTP 401 / AuthenticationError，已到密码校验。错误发生于 `require_post`，不能据此认定真实密码错误。
- 只读配置确认既有 frontend Site 的规范来源为 `http://127.0.0.1:8080`，已启用 `hbos_account_test_site=1`，开发来源只有 `http://localhost:5178`。代码还只接受 localhost / .localhost 开发来源，不能直接添加回环 IP 生效。nginx 转发 Host 使用 `$host`；Origin/Host 主机名须保持一致。
- `accounts.require_post` 仅对测试 Site 的显式开发来源增加 `127.0.0.1` / `::1` 支持；不启用隐式回环通配、不改变生产来源、不移除 Origin/Host 匹配、Guest JSON/X-Requested-With 或已登录 Session CSRF 校验。
- `frappeClient` 将“请求来源无效”识别为 `INVALID_ORIGIN`，提示使用配置入口，真实令牌失配仍为 `CSRF_MISMATCH`。没有自动重放密码或业务写请求。

### 本机应用与回退证据

既有 backend 挂载当前 `apps/hbos_portal`。修改配置前校验既有测试标志和规范来源，备份至容器私有目录：

```text
/home/frappe/frappe-bench/sites/frontend/private/backups/login-origin-20261008-ihiexbsc/site_config.json
```

备份目录权限 0700、文件权限 0600，内容未输出或提交。配置仅向原开发来源列表追加 `http://127.0.0.1:5178`，保留原 localhost 和 8080 规范来源。原 Gunicorn 主进程收到 SIGHUP 平滑加载，不重建容器或 Site，不迁移数据库，不修改账号、密码、绑定、角色或权限。若回退，仅还原该私有配置备份并平滑加载，源码按本节最小 diff 撤销，禁止重置整个已有工作区。

### 验证与限制

| 检查 | 结果 |
| --- | --- |
| 修复前新增来源 / 错误提示回归 | 回环 IP 被拒绝，来源提示错误；新增用例复现失败 |
| 后端账号相关隔离测试 | 20 项通过，含显式回环、生产禁用、未配置 / 错端口 / 外部来源 / Host 不匹配拒绝、当前 CSRF 仍必需 |
| Vitest + Node 前端测试 | 66 + 34 = 100 项通过，含退出 → Guest 密码登录 → 新会话令牌、密码只提交一次 |
| lint、类型、LIMS 前端契约、真实模式生产构建 | 通过；既有大 chunk 提示保留 |
| 127.0.0.1:5178 浏览器表单 | 修复后虚构账号返回“账号或密码不正确”，原来源拦截解除；未使用截图密码 |
| 补充真实 HTTP 来源矩阵 / 匿名 Bootstrap | 自动审批连接中断，动作未执行；不记为运行态 PASS，不用隔离测试替代 |
| Owner 真实账号成功登录与完整退出再登录 | 待本人复验，不记 PASS |

浏览器截图为 `/private/tmp/HBOS_登录来源修复验证_20261008.jpg`，只含虚构账号及已清空的密码框，为临时本机证据，不是实际账号成功登录截图。前端构建只做验证，未替换部署制品或远端发布。

收尾时检测到同一工作区其他进程正在修改启动脚本及 `frappeClient` 的 CSRF 消息映射。保留这些改动，将本次 `INVALID_ORIGIN` 分支与消息映射衔接；中间快照的未接入映射 / 类型问题不记通过。最终 lint、类型、66 + 34 项前端测试和真实模式构建连续通过，登录 service 及两份本轮回归文件的 SHA-256 在整轮检查前后一致。其他进程的启动脚本改动不属于本轮修复或完整审查结论。

PROJECT_STATUS、CURRENT_MILESTONE、M2_START_GATE、账号轮次主文档 M1_RP3 与本记录已同步；README、AI_CONTEXT、READING_GUIDE 和 Portal README 已更新，后者的旧 `m2-r10` 当前分支描述已更正。CLAUDE / AGENTS 为规则文件，检查后无需修改。未新增文档文件、提交、推送或部署；新增测试复用既有生态约定文件名，截图使用中文名。

P4-F6-5 仍 REVIEWING，权限管理原型仍待 Owner 审查，P1 PARTIAL / 实际盘点 NOT_RUN、Q1 / Q2 与 S01—S06 门禁保持原状；本次登录修复不构成权限实现或业务验收批准。


## 14. 2026-10-08 个人资料与管理后台入口修复

状态：**LOCAL DESK NAVIGATION FIX VERIFIED / REVIEWING / Owner 登录后点击待复验**。沿用既有 `m2-r11`，不创建或切换分支；保留工作区已有登录修复、权限原型及其他变更。superpowers 当前不可用，按项目规则人工执行等价定位、回归与核对。

### 根因与修复

- 原入口将 `/app` 和 `/app/user/<当前用户>` 发往 Portal 开发来源 5178。Vite 返回 Portal HTML，Vue catch-all 显示截图中的 HBOS 404；这不是已证实的账号权限错误。
- 实际 Frappe 16 使用 `/desk`；8080 上的旧 `/app` 会 301 到 `/desk`，因此旧路径本身不是后台 404 的根因。修复使用规范 `/desk` 路径和当前用户 ID 编码，避免依赖旧别名。
- `ProfileSettingsView.vue` 通过既有 `businessNavigationTarget` 解析来源，两个入口改为带真实 href 的 Ant Design Vue 链接，触发整页导航；沿用原有 Desk 权限与用户身份校验，不增加授权。
- Vite 在 Frappe 开发模式未显式配置 `VITE_FRAPPE_APP_ORIGIN` 时默认采用实际 API 代理目标。显式配置优先；生产缺省仍使用同源，隔离预览不会被固定到 8080。移除工作区此前 dev 命令对页面来源的硬编码，来源统一由配置解析。

### 验证与边界

| 检查 | 结果 |
| --- | --- |
| 新增组件回归 | 修复前两入口缺少预期 href；修复后覆盖本机 8080、隔离 18091、生产同源、当前用户编码及无 Desk 权限隐藏 |
| Vite 配置回归 | 开发随实际代理、显式覆盖、生产同源全部通过 |
| 前端测试 | Vitest 70 + Node 35 = 105 项通过 |
| lint、类型检查、LIMS 前端契约、真实模式生产构建 | 通过；既有大 chunk 提示保留 |
| 原 5178 的 /app 与用户路径 | HTTP 200 返回 Portal HTML，解释 SPA 404 |
| 8080 的 /app 与用户路径 | 301 到对应 /desk 路径，旧别名有效 |
| 8080 的 /desk 与当前用户路径（匿名） | 301 到带正确 redirect-to 的 Frappe 登录页，跟随跳转 HTTP 200 |
| 5178 实际运行模块 | 两入口 href 与 /desk 路径已加载；公开页面来源解析为 http://127.0.0.1:8080 |
| 匿名浏览器打开当前用户资料路径 | 到达 Frappe 登录页，URL 保留 /desk/user/Administrator 回跳目标，未进入 Portal 404 |
| 登录后真实资料编辑 / Desk 页面及 Owner 点击验收 | 待复验，不记 PASS |

浏览器证据：`/private/tmp/HBOS_资料后台入口路由验证_20261008.jpg`，是未登录时的受控登录页，不代表成功登录或资料编辑验收。截图已保存；收尾重新打开 5178 复验页时自动审批服务连接中断，未执行该次导航，没有绕过审批。HTTP 与已完成的浏览器目标验证不受此限制。

本次没有修改后端源码、Site、账号、凭据、角色或数据库，没有执行真实业务写入。构建仅验证，未提交、推送或远端部署。PROJECT_STATUS、CURRENT_MILESTONE、M2_START_GATE、M1_RP3 与本记录已同步；README、AI_CONTEXT、READING_GUIDE、Portal README 和配置示例已更新。CLAUDE / AGENTS 的规则已检查，无需修改；未新增文档文件，回归复用既有测试文件。

P4-F6-5 保持 REVIEWING，权限管理 UI_PROTOTYPE_DRAFT / 待审、P1 PARTIAL / 实际盘点 NOT_RUN、Q1 / Q2 未确认和 S01—S06 NOT_STARTED / 验收 NOT_RUN 均不变。


## 15. 2026-10-08 当前 Site 飞书登录启用准备

状态：**FEISHU LOGIN ENABLED / EXACT REDIRECT ACCEPTED / OWNER OAUTH PENDING / REVIEWING**。Owner 提供应用凭据并明确要求启用飞书登录；沿用 `m2-r11`，复用现有 OAuth、单次 state / 浏览器 nonce、PKCE、企业和内部成员核验实现。本轮不开发新登录方式或绑定旁路。superpowers、lark-shared 在当前环境未找到，按项目规则人工等价执行。

### 当前环境与已完成工作

- 5178 的实际后端是 `hbos-m0-r3a` / `frontend` / 8080。其飞书配置字段原先均缺失，`HBOS External Identity` 记录为 0；历史 P1 的真人成功不代表此 Site 已配置。
- 使用用户明确提供的凭据向飞书官方应用 Token、企业信息和机器人信息接口验证：均成功，机器人为“海滨小助手”，企业为“健康元药业集团股份有限公司”。未输出或持久化 Token、未读取成员清单或聊天，未向飞书写业务数据。
- 已创建 Site 私有备份目录 `/home/frappe/frappe-bench/sites/frontend/private/backups/feishu-login-20261008-jungc1vb`（0700），包含原 `site_config.json`、待启用 Secret、已由官方接口发现的企业标识、非活动配置草案（各 0600）。原先不存在活动 Secret / 企业私有文件；草案带 `requires_owner_confirmation=true`，没有修改活动配置或公开入口。主机隐藏输入使用的临时 Secret 文件已删除。
- 当前 backend 缺少自动开户所需 pypinyin。只从官方 PyPI 下载既有 `requirements.txt` 锁定的 0.55.0 wheel，SHA-256 与仓库 `d53b1e8ad2cdb815fb2cb604ed3123372f5a28c6f447571244aca36fc62a286f` 一致，离线安装到现有 backend bench Python。运行态版本及合成姓名“张三”→ `zhangsan` 已验证；没有创建真实账号。
- 此次只补现有 backend 容器中的依赖，不重建容器或改镜像、Compose。容器重建须使用已存在的 `Dockerfile.portal` / 锁定 requirements 构建路径，不能假定临时容器层安装会自动保留；本轮未改变队列 / scheduler 环境。
- 账号 / OAuth / 诊断定向隔离测试 39 项通过；补齐临时测试依赖并采用包发现方式后，Portal 后端全部 68 项通过。最初的单文件 / 顶层发现方式存在 stub 或相对导入问题，主机原本也缺 pypinyin，未将这些中间失败记为 PASS；最终依赖仅展开在主机临时目录，没有安装到主机系统 Python。

### 首次准备时的确认要求（Owner 已确认）

现有 `scripts/release/configure_feishu.py` 要求确认发现的企业全称及控制台条件，不能仅凭 Secret 将 `app_published` / `redirect_registered` 标记为已核实。已向 Owner 询问：

1. “健康元药业集团股份有限公司”是否就是本项目批准接入的企业。
2. 下列精确回调是否已登记，内部可用范围及登录 / 成员读取权限是否已获批发布。

```text
http://127.0.0.1:5178/api/method/hbos_portal.auth.feishu.callback
```

用户 OAuth 仅请求 `contact:user.base:readonly`；应用身份另须具备既有内部成员核验所需权限（含 `contact:user.employee:readonly` 的在职状态，企业信息接口本次已验证成功）。不申请聊天读取、广泛业务写入或验证码发送权限。

只读打开飞书控制台因自动审批服务连接中断被拒绝，操作未执行；未用其他浏览器或低层方式绕过。不能据此确认回调、发布范围或成员权限已经就绪。Owner 答复到达前不应用草案，不启用普通成员自动开户或 Administrator 绑定许可，不更改原规范来源。

### 原定应用与复验步骤（已应用，真实回调未通过）

收到上述明确确认后，只将本 Site 私有待启用 Secret / 企业标识和草案字段写入活动配置，保留现有 Origin/Host、CSRF 与账号策略；不得用 P1 身份映射替代当前 Site 的本人验证。平滑加载 Web 后核对 `get_status`、受保护 OAuth start、正确的 client_id / callback / scope、单次 state、PKCE 和浏览器 nonce；不输出授权票据或 Secret。

`configured=true` 只代表配置条件满足。真人 OAuth、成员状态、已有账号本人绑定 / 新成员普通开户、退出再登录和 Owner 验收仍分别待执行；没有自动映射到 Administrator，也不启用收件验证码或高风险交接。

若撤销准备，保留原活动配置，仅清理本次明确命名的待启用材料；若已应用再回退，使用本节私有配置备份并平滑加载，私有凭据按原存在性恢复，不重置工作区或数据库。依赖回退可只卸载本轮新增的 pypinyin；不影响原 Frappe 或 App。

PROJECT_STATUS、CURRENT_MILESTONE、M2_START_GATE、M1_RP3、README、AI_CONTEXT、READING_GUIDE 和 Portal README 已同步；CLAUDE / AGENTS 规则已检查，无需修改。P4-F6-5 保持 REVIEWING，权限原型待审、P1 PARTIAL / NOT_RUN、Q1 / Q2 与 S01—S06 门禁不变。未新建分支、App、文档文件、提交、推送或远端部署。


### Owner 确认后的实际应用与飞书结果（保存回调前，历史）

Owner 随后明确回复“已确认”。应用前重新核对 `m2-r11` 与默认规则 / 状态文件，校验原私有草案、当前 Site、活动凭据缺失和企业证据。最初 Gunicorn 识别保护把主进程与 worker 一并计入，因唯一性检查失败而在配置写入前停止；只读核实 PID 1 为 master 后修正运行脚本，不改仓库源码。

已将既有私有 Secret / 企业标识和草案字段原子应用到 frontend Site，文件 0600。另存 `site_config.before-apply.json` 和无凭据 `applied_receipt.json` 于本节原备份目录。原 `hbos_portal_origin` 保留，Administrator / privileged 绑定许可、收件验证码及高风险交接均未启用。Web 仅向核实的 Gunicorn master PID 1 发送 SIGHUP，不重建 Site 或容器。

| 实际检查 | 结果 |
| --- | --- |
| 8080 / 5178 get_status（应用后） | HTTP 200，configured=true、missing=[]，PKCE=true，callback 正确 |
| 两次独立匿名 OAuth start | HTTP 302 到 accounts.feishu.cn；client_id、精确 callback、基础身份 scope 正确，state / PKCE / nonce 各自不同 |
| 浏览器绑定 | HttpOnly、SameSite=Lax；输出仅布尔检查，不记录 state、Cookie、code 或 Secret |
| 匿名 Bootstrap | HTTP 403，配置启用不产生匿名访问权限 |
| 实际 Portal 登录页 | “使用飞书登录”按钮已启用，已保存本机截图 |
| 点击后实际飞书授权页 | **错误 20029：重定向 URL 有误**，未到本人授权或回调，不记登录成功 |
| 保护处理后的 5178 状态 | configured=false，仅缺 redirect_registration；start 302 回 /hbos/login?status=config_required |
| 真实用户 / 绑定 / 角色变更 | 未执行；没有创建普通账号或映射 Administrator |

飞书真实返回优先于人工登记确认。仅将 `hbos_feishu_redirect_registered` 改回 0 并平滑加载，其他私有配置与 PKCE 保留，防止未通过的授权继续显示可用。私有 receipt 已记录 REJECTED_20029 / login_available=false。实际安全设置链接已打开，但该浏览器没有控制台会话，停在本人扫码登录页；已向 Owner 请求扫码登录后核对，或自行添加保存下列精确 URL 后复验：

```text
http://127.0.0.1:5178/api/method/hbos_portal.auth.feishu.callback
```

该安全设置为 `https://open.feishu.cn/app/cli_aa973f7d17b81cd8/safe`。没有代替本人扫码、批准新增权限或保存控制台配置。截图 `/private/tmp/HBOS_飞书回调20029_20261008.jpg` 为当前实际失败证据；此前 `/private/tmp/HBOS_飞书登录已启用_20261008.jpg` 只说明应用后的短暂启用状态，不代表当前入口仍开放。控制台登录页保留供 Owner 操作。

本次源码未变化，前序 68 项隔离测试不重跑；新增运行态 HTTP / 浏览器证据如上，未完成真人 OAuth、成员核验、已有账号本人绑定和退出重登。若干配置 / HTTP 工具调用曾因自动审批服务连接中断未执行，同一低风险动作重新申请后成功；本轮实际控制台导航成功，不再将旧的打开失败作为当前访问障碍，当前缺口是本人控制台登录与精确回调保存。

状态台账、M2 门禁、M1_RP3 和公共入口已更新为实际回调拒绝；CLAUDE / AGENTS 为规则文件，无需修改。继续不新增轮次、分支、App、提交、推送或远端部署；权限原型及 P1 / Q1 / Q2 / S01—S06 门禁保持原状。


### Owner 保存回调后的最终复验与启用

Owner 明确回复“已保存”。复核默认规则、状态文件、M2 门禁、账号主记录和 `m2-r11` 后，只恢复当前 frontend Site 的 `hbos_feishu_redirect_registered=1`，保留既有私有凭据和所有其他配置；向 Gunicorn master PID 1 发送 SIGHUP 平滑加载。没有修改仓库源码、Site 来源、账号、角色、其他回调或应用权限。

在 Owner 已登录的飞书控制台安全设置中，只读确认精确 URL 已存在，应用为“海滨小助手”、状态“已启用”、企业匹配，并显示“当前修改均已发布”；没有编辑或删除其他登记项。

为避免验证时自动为当前飞书人员开户，浏览器授权探测使用未由 HBOS 签发的测试 state 和公开的测试 PKCE challenge。真实飞书已经显示“海滨小助手”本人授权确认页，20029 消失；停在授权按钮之前，没有点击授权、兑换 code、读取成员资料或建立 HBOS 身份。该探测票据不能用来正常登录；测试页已关闭，正常操作须从 Portal 重新发起。

| 最终检查 | 结果 |
| --- | --- |
| 控制台精确回调与发布状态 | URL 完全匹配 5178 callback，当前修改均已发布 |
| 实际飞书授权页面 | 正常显示本人授权确认，20029 已消失 |
| 5178 get_status | HTTP 200，configured=true、missing=[]、PKCE=true，callback 完全匹配 |
| 正常 start 的 HTTP 验证 | HTTP 302，client_id / callback / scope 正确，fresh state / PKCE 及 HttpOnly / SameSite=Lax 浏览器绑定存在；未跟随授权 |
| Site 身份绑定记录 | 仍为 0，本轮未创建真实账号或绑定 |
| 本人完整 OAuth / 当前成员核验 / 原账号绑定 / 退出重登 | 待本人执行，不记 PASS |

私有 `applied_receipt.json` 已更新为 ACCEPTED_AUTHORIZATION_PROMPT / login_available=true / owner_oauth=NOT_COMPLETED_BY_AGENT；文件为 0600。当前 Site 没有飞书身份绑定，原 Administrator 不自动关联；相关管理员 / privileged 绑定许可仍未开启，若 Owner 需要使用原管理员身份，须在明确目标后走原有本人验证 / MFA / 绑定流程，不用普通新账号替代原目标。

本轮没有源码或依赖变更，不重复前序已通过的 68 项隔离测试。正常 start 验证仅保留布尔结果，未记录 state、Cookie、code、Token 或 Secret。浏览器证据 `/private/tmp/HBOS_飞书精确回调已通过_20261008.jpg` 是授权确认页，不能作为已登录成功证明；先前 20029 截图为历史失败证据。

切回 Portal 登录页的浏览器动作因自动审批服务连接中断未执行；没有绕过该动作，已保存当前授权页证据并关闭测试页，避免 Owner 误用未签发的探测票据。Owner 自行保留的控制台页未关闭，正常登录使用 `http://127.0.0.1:5178/hbos/login`。最终 HTTP 和私有 receipt 更新均已完成，不因该可选导航失败将配置写成未启用。

PROJECT_STATUS、CURRENT_MILESTONE、M2_START_GATE、M1_RP3、README、AI_CONTEXT、READING_GUIDE、Portal README 和本记录已同步为当前启用状态；CLAUDE / AGENTS 为规则文件，无需修改。P4-F6-5 仍 REVIEWING；权限原型待审、P1 PARTIAL / NOT_RUN、Q1 / Q2 与 S01—S06 门禁保持原状。未创建分支、App、提交、推送或远端部署。
