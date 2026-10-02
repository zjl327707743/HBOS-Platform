# LIMS P4-F6-5 前端审核整改记录

状态：**REVIEWING / 2026-10-02 m2-r11 合并后问题修复与本地验证完成 / 待完整真实流程及 Owner 验收**
日期：2026-09-30；更新：2026-10-02

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
