# LIMS Portal 前端代码审核报告

状态：**REVIEWING / 已重新基线并完成本轮确认缺陷修补 / 待 Owner 与真实 Frappe 验收**
日期：2026-10-01
审查对象：`frontend/hbos-portal-web/`（Vue 3 + TypeScript + Pinia + Vue Router + Ant Design Vue + Axios）
原审查基线声明：`m2-r10`，但引用混入 `f23ba17` 之前的代码且「工作区无未提交改动」不成立。当前复核基线为 `m2-r10` 的 `553bc53` 加本轮工作区整改。
原稿审查范围：只读静态审查。2026-10-01 Owner 已授权确认检查结果并修补；以下新增复核记录为当前结论。

## 2026-10-01 重新基线与整改处置（当前有效）

原稿正文与行号保留为评审痕迹，不再直接作为当前行动清单；原「9 项 P0」「零单测」等汇总不代表当前代码。本轮没有复用原稿的双 Agent 审查声明，也没有开启新分支。默认入口、当前 Portal 记录、前端源码、后端任务与结果动作契约已交叉核对；仅修复既有批准设计中的缺陷。

| 项目 | 复核与处置 |
| --- | --- |
| P0-08 命令面板扫码入库 | **不成立 / 旧基线**：`f23ba17` 已删除；PortalHome 的原型快捷操作已有 Mock 门控。本轮补 AST 门控与真实组件渲染回归，避免复发。 |
| P0-05 零前端测试 | **不成立 / 旧基线**：`f23ba17` 已新增 14 项回归。CI 未接测试、没有 lint/lockfile 的部分成立，本轮已补齐。 |
| P2-02 后台刷新无 catch | **已在 f23ba17 修复**；本轮补 Provider 部分失败、关联编号和刷新乱序保护，不重复计为新问题。 |
| §3.15 768px 导航缺口、侧栏溢出 | **成立 / 已修**：移动隐藏、底栏显示与底部避让统一为 767.98px；LIMS 菜单独立滚动，顶部固定。真实浏览器验证 768/767px 导航切换及 1280×720 菜单滚动。 |
| P0-06 默认 Mock | **成立 / 已修**：模式只接受显式 `mock`/`frappe`；普通生产构建只允许 Frappe，Mock 有独立构建命令与全站标识。 |
| P0-07、P0-09、§3.19 文案污染 | **成立 / 已修**：稳定性室使用后端数量；只读原因按模式/权限/状态/OOS 表达；连接标签改为当前会话验证状态，不再断言服务健康。数字孪生既有 Mock 门控保留。 |
| P0-01 会话生命周期 | **成立 / 已修**：个人菜单提供 Frappe 标准 POST logout；成功后清空身份/能力/业务投影与 CSRF；失效允许再验证，验证缓存 60 秒，bootstrap 合并并发；旧请求不能恢复已退出身份。500/网络错误仍可进入错误壳，但不标记已认证。 |
| P0-02 任务 status | **硬编码成立，但原业务推论需修正**：现有 LIMS Provider 输出待处理动作，不输出完整待办历史。「已完成 + eval_trend」「已批准 + execute_usage」仍是 open；明确 open/waiting/done 保留，无动作的已关闭/等待状态映射；工作计数只计 open。等待/完成历史不能由前端虚构。 |
| P0-03 分页 | **成立 / 已修**：结果列表、任务看板提供加载更多、已加载/总数及游标；筛选重置游标、追加去重与过期响应保护。Portal 工作汇总遍历 Provider 暴露的游标页；游标循环/后续页失败会显示加载不完整，不承诺超出后端投影上限的完整业务历史。截止筛选和状态统计仅基于已加载任务，界面明确说明。 |
| P0-04 部分失败、trace_id | **成立 / 已修**：汇总、任务、搜索保留成功项并报告失败应用；Shell/查询页/详情页显示安全提示与关联编号，不输出 SQL/堆栈；鉴权失败不伪装成普通空列表。 |
| §3.17 结果动作状态 | **成立 / 已修**：仅草稿可提交；复核/批准按状态与能力；OOS 阻止批准，保持后端仍允许独立复核的语义，未创建第二套业务 Authority。 |
| §3.1 samples 恒假分支、§3.2 Mock 导入 | **已清理**：删除侧栏恒假 samples 项；同源 pending 路由保留。Portal 演示数据改动态 import；不声称所有领域 Mock 数据已经从生产包物理移除。 |
| C 工程门禁 | **已补齐**：锁文件、npm ci、ESLint 10、单元/组件回归、前端/Shell 契约、Mock 模板 AST 门控；`m2-r10` 推送与 Portal 脚本变更触发 CI。启动脚本统一使用 npm ci，原显式 Frappe 环境不会被 dev 命令覆盖。 |
| D 巨型视图拆分 | **保留重构项**：不属于本轮确认的功能/正确性缺陷，未为追求形式进行大范围拆分。原稿其他 P1/P2 改进项仍需逐项重新基线，不在本轮自动全部关闭。 |

验证：`npm ci` 安装成功；34 项单元/组件回归、ESLint、前端契约、Shell 契约、Mock 内容门控和 TypeScript/真实模式构建通过；显式 Mock 构建通过；生产构建拒绝拼错模式和 Mock。Vue 运行回归覆盖实际结果/任务页按钮加载更多与 URL 筛选重置游标。静态契约仍只作为接线检查，不能替代运行回归。

浏览器证据（临时 Mock，非真实 Frappe）：1280×720 时侧栏 bottom=708，菜单 clientHeight=368 / scrollHeight=838，End 后 scrollTop=470、末项落在菜单边界内；768×1024 时侧栏 flex、移动导航 none；767×720 时侧栏 none、移动导航 grid、body padding-bottom=78px。矮窗口后续复测的自动审批因网络传输断开而拒绝执行，未绕过；该补证据项与真实 Frappe Session/数据联调仍待完成。

状态：沿用 **P4-F6-5 REVIEWING**，不新建 M2 轮次、不部署、不推送、不放行样品/管理后台门禁；Owner 最终验收仍待完成。项目状态、当前里程碑、M2 阶段门禁、P4-F6 主实施计划与前端整改记录同步。

---

## 0. 读取的文件（原稿保留）

按项目读取规则，本轮读取：

- `CLAUDE.md`、`AGENTS.md`、`docs/AI_CONTEXT.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/experience/README.md`、`docs/experience/LIMS_P4-F6-5_前端审核整改记录.md`
- `frontend/hbos-portal-web/` 全量源码（60 个 `.vue` / `.ts` / `.css`，8320 行）
- 交叉核对后端契约：`apps/hbos_portal/hbos_portal/contracts/errors.py`、`api/_utils.py`、`api/results.py`；`apps/hb_lims_app/hb_lims_app/hbos_lims/portal/{tasks,results,coa,audit,ledger,retention}.py`
- 构建与门禁脚本：`scripts/portal/lims_frontend_contract.mjs`、`scripts/portal/lims_shell_contract.sh`、`.github/workflows/hbos-portal-frontend.yml`

未读取 `docs/archive`、`docs/research`、`docs/legacy`，未全量读取 `docs/milestones/`。

## 1. 结论

**整体质量：中上（B / 可交付但不可上线）。**

架构方向正确，上次审核（`LIMS_P4-F6-5_前端审核整改记录.md`）的 P0/P1 大部分已真实落地：`unwrapPortalMethod` 统一错误传播、真实模式不再回退 Mock 汇总、语义能力门控 `accessCapabilities`、`LimsLayout` 稳定路由、`redirect` 开放重定向防护、按页面动态加载均已验证有效。

但仍有 **9 项 P0 级问题**，集中在六类：

1. **默认模式不安全** —— `VITE_PORTAL_DATA_MODE` 未配置时静默回退 Mock，且全站没有任何「演示数据」标识，伪造 KPI 会被当成真实数据（P0-06）。
2. **真实模式硬编码演示内容** —— 三条**无条件渲染**的 Mock 专用内容混进生产界面：稳定性室 `A / B`（P0-07）、命令面板「扫码入库」假入口（P0-08）、「演示模式只读」徽标（P0-09）。这是本次审查最严重的一类发现，说明缺少一条「Mock 专用内容必须显式门控」的机械检查。
3. **会话生命周期不闭环** —— 没有登出能力，且会话中途失效后不会重新校验，用户会停留在「已登录的壳 + 空数据」的假状态（P0-01）。
4. **真实模式数据正确性** —— 任务状态被前端硬编码为 `open`（P0-02）；结果/任务列表拿到 `next_cursor` 但完全不用，静默丢数据（P0-03）。
5. **错误不可见** —— Provider 级失败被 `Promise.allSettled` 静默吞成空列表，用户只看到「暂无数据」，后端已经返回的 `trace_id` 在 UI 上从不出现（P0-04）。
6. **测试与工程门禁形同虚设** —— 全仓库 0 个前端单元测试、0 个 lint 配置；现有 `test:contract` / `lims_shell_contract.sh` 是**源码正则字符串匹配**，只证明「某段字符串还在」，不证明任何运行时行为（P0-05）。**P0-07～P0-09 能长期存活正是这一点的直接后果**。

> **审查方式说明**：本报告由两路独立审查交叉验证产出（服务/契约层一路，视图/组件层一路），**两路均已完整返回**，其全部 P0/P1/P2 结论**均由本人逐条复核证据后收录**；未经复核的推断已剔除或明确标注。核实过程中修正/新增了以下判断：

- ① 初版把「默认 Mock 模式无标识」列为 P1，经核实后果是用户看到伪造业务数据、直接违反 `docs/AI_CONTEXT.md:141` → **提升为 P0-06**。
- ② 初版把「无超时/无取消」列为 P2，经核实会与翻页 append、稳定性整包覆盖叠加导致数据错配 → **提升为 §3.9**。
- ③ 视图层审查新报出 **3 处真实模式硬编码泄漏**（P0-07 稳定性室 `A / B`、P0-08 命令面板「扫码入库」、P0-09「演示模式只读」），三者**均已回到源码逐字确认**，是本报告初版遗漏的最严重一类问题 → **新增 P0-07～P0-09**。
- ④ 另新增 §3.15～§3.19（768px 导航真空、任务看板三重缺陷、提交按钮缺状态校验、冷启动重复 bootstrap、硬编码「已连接」）与 P2-23～P2-36。

因此 P0 由初版 5 项修订为 **9 项**。

此外，本次审查发现 `LIMS_P4-F6-5_前端审核整改记录.md` 中有 **两条整改声明与当前代码不符**（详见 §3.1），建议同步修正该记录的结论口径。

本轮验证结果：

| 验证项 | 命令 | 结果 |
| --- | --- | --- |
| 类型检查 + 生产构建 | `npm run build` | PASS（3.18s，`vue-tsc -b` 无报错） |
| 前端契约检查 | `npm run test:contract` | PASS（源码正则匹配） |
| Shell 契约检查 | `bash scripts/portal/lims_shell_contract.sh` | PASS（源码字符串匹配） |
| 单元 / 组件 / E2E 测试 | — | **不存在** |
| Lint / 格式检查 | — | **不存在** |
| 真实 Frappe 运行态证据 | — | 未获取（环境仍缺 Docker） |

---

## 2. P0 级问题（上线阻断）

### P0-01 没有登出，且会话失效后不再重新校验

- **位置**：`src/components/layout/GlobalHeader.vue:46-51`（用户菜单只有「个人与设置」+ 一条空 `a-menu-divider`）、`src/stores/portal.ts:77-101`、`src/services/frappeClient.ts:98-100,111-121`
- **证据**：

```vue
<!-- GlobalHeader.vue:46-51 -->
<template #overlay>
  <a-menu>
    <a-menu-item @click="$router.push('/hbos/profile')">个人与设置</a-menu-item>
    <a-menu-divider />
  </a-menu>
</template>
```

- **问题**：全仓库搜索 `logout` / `signOut` / `退出登录` **零命中**。用户没有任何途径主动结束 Frappe Session。同时：

  - `http.interceptors.response` 收到 401/403 `UNAUTHENTICATED` 时调用 `unauthorizedHandler` → `portal.markSignedOut()`，该方法（`portal.ts:111-115`）把 `sessionChecked` 置为 `true`；
  - 但路由守卫 `ensureSession()`（`portal.ts:83`）开头是 `if (sessionChecked.value) return authenticated.value`；
  - 于是在**重新登录成功前**，`markSignedOut` 已把 `sessionChecked` 置真，后续任意导航都会走「已检查」分支并返回 `false`，用户被反复弹回登录页且不会自动复用既有 cookie；反过来，若 `ensureSession` 因非鉴权错误（500/网络）提前返回 `true`（`portal.ts:88-95`），则会停留在「显示已登录的壳 + 空数据 + bootstrap 错误横幅」的假登录态。

- **影响**：安全上无法主动登出（共享终端场景不可接受）；体验上会话过期后状态机不收敛。
- **建议**：

  1. 用户菜单补「退出登录」，调用 Frappe 标准 `POST /api/method/logout`，成功后 `clearCachedCsrfToken()` + `markSignedOut()` + `router.replace({ name: 'login' })`。
  2. `markSignedOut()` 内同时重置 `sessionChecked.value = false`，让下次导航重新校验。
  3. 将 `sessionChecked` 语义拆为 `sessionChecked` 与 `sessionValid`，禁止用「已检查过」代替「仍然有效」。

### P0-02 任务状态被硬编码为 `open`，真实模式任务永远不计入完成

> 当前复核：硬编码已修；领域完成/批准状态不能直接等同已完成待办，见顶部动作语义说明。

- **位置**：`src/services/portalApi.ts:280-298`

```ts
function mapTask(task: BackendTask, appTitle: string): UnifiedTaskDTO {
  return {
    ...
    status: 'open',        // <-- 无条件硬编码
    domainStatus: task.status || undefined,
    ...
  }
}
```

- **问题**：后端 `BackendTask.status` 是真实领域状态（`apps/hb_lims_app/.../portal/tasks.py` 投影 `project_todo`），前端把它降级到 `domainStatus`，却把所有任务 `status` 强制成 `'open'`。直接后果：

  - `stores/portal.ts:39-41` 的 `totalActions = tasks.filter(t => t.status === 'open').length` 永远等于任务总数，「我的工作」计数虚高；
  - `HeroWorkspace.vue:6` 因此恒显示「今天有 N 项工作」（N=全部任务）；
  - `LimsDashboardView.vue:231` 的 `portal.tasks.filter(task => task.status !== 'done')` 永远不过滤，已完成任务也会显示；
  - `MyWorkView.vue:100-107` 的四个作用域筛选**全部失效**：`需要我处理`（要求 `status === 'open'`）永远全量命中，而 `等待别人`（要求 `waiting`）与 `已完成`（要求 `done`）**恒为空列表**——即真实模式下这两个标签页永远没有内容；
  - `UnifiedTaskDTO.status` 的 `waiting` / `done` 两个枚举值在真实模式下**永不可能出现**，是死类型。

- **建议**：新增 `normalizeTaskStatus(raw: string): UnifiedTaskDTO['status']`，按后端真实状态映射（至少覆盖 `已完成/已批准/已关闭/取消 → done`、`待处理/挂起 → waiting`、其余 `open`）；`domainStatus` 继续保留原始中文状态用于展示。建议同时对 `MyWorkView` 的四个作用域补一条断言测试，防止再次回归。

### P0-03 结果列表与任务看板丢弃 `next_cursor`，静默截断

- **位置**：`src/services/limsResults.ts:86-107`（`listLimsResults` 已声明 `cursor` 入参并在 `:48` 返回 `next_cursor`，但视图层既不传游标也不消费返回值）、`src/views/LimsResultListView.vue`、`src/services/portalApi.ts:362-364`（`limit: 20` 且 `BackendTaskPayload.next_cursor` 被丢弃）、`src/views/LimsTaskBoardView.vue`
- **证据**：后端明确支持游标分页 —— `apps/hb_lims_app/.../portal/results.py:120-124` 返回 `"next_cursor": str(next_offset) if next_offset < len(filtered) else None`，`tasks.py:206` 同构；且 `portal/integration_checks.py:38-39,83-84` 把 `next_cursor` 列为必需字段。
- **对比**：`LimsLedgerView.vue:45`、`LimsCoaView.vue:45`、`LimsQualityStandardsView.vue:37`、`LimsAuditView.vue:37` **都已实现**「加载更多」，只有**检验结果列表**和**任务看板**没有。
- **影响**：真实模式下，超过 50 条结果 / 超过 20 条任务的用户永远只能看到第一页，且界面没有任何「还有更多」的提示——属于静默数据丢失，在 LIMS 这种合规场景是严重问题。
- **建议**：为 `listLimsResults` 与 `getFrappeTasksForApps` 补 `cursor` 参数并透传，在两个视图补 `加载更多` 按钮 + `total` 显示；`limit: 20` 改为可配置常量（建议与后端 `normalize_limit` 上限 50 对齐）。

### P0-04 Provider 级失败被静默吞掉，`trace_id` 从不呈现

- **位置**：`src/services/portalApi.ts:325-351`、`353-382`

```ts
const batches = await Promise.allSettled(
  summaryApps.map(async (app) => { ... }),
)
return batches.flatMap((result) => result.status === 'fulfilled' ? result.value : [])
```

- **问题**：

  1. `rejected` 分支被直接丢弃，既不记录也不上报。若 `get_summary` / `get_tasks` 因权限或后端故障失败，UI 得到的是**空数组**，页面渲染成「当前范围暂无工作指标 / 暂无待处理任务」——把**故障**伪装成**真的没数据**。对 LIMS 而言，把「报表加载失败」显示为「没有待检任务」是危险的误导。
  2. `PortalMethodError` / `PortalApiError` 已经携带 `code`、`retryable`、`traceId`（`frappeClient.ts:20-32`、`portalApi.ts:147-159`），但全仓库 `traceId` 只在类定义处出现，**没有任何 UI 展示或上报**。用户报障时无法提供 trace 号，运维无法定位。
  3. 各视图的 `catch` 统一替换为写死的字符串（如 `LimsDashboardView.vue:279`），真实错误码被丢弃。

- **建议**：

  1. `Promise.allSettled` 的 `rejected` 分支收集为 `providerErrors: {appId, code, traceId}[]`，返回给 store，由 Shell 以 `a-alert` 呈现「部分应用数据加载失败」而非空态。
  2. 统一错误呈现组件：显示 `message` + `trace_id`（可复制）+ `retryable` 时提供「重试」。

### P0-05 前端零自动化测试、零 lint，CI 门禁只做字符串匹配

> 当前复核：零单测为旧基线误报；CI/lint/锁文件缺项已在本轮修复，见顶部重新基线记录。

- **位置**：`package.json:6-11`（只有 `dev/build/preview/test:contract`，**无 lint、无 test**）、`scripts/portal/lims_frontend_contract.mjs`、`scripts/portal/lims_shell_contract.sh`、`.github/workflows/hbos-portal-frontend.yml:36-48`
- **证据**：`lims_frontend_contract.mjs` 全部断言形如：

```js
assert.match(capabilities, /lims\.results\.read/)
const styles = read('styles/global.css')
assert.match(styles, /grid-template-columns: minmax\(0, 1\.28fr\) minmax\(250px, \.72fr\)/)
```

  `lims_shell_contract.sh` 全部是 `grep -Fq "..." || fail`。CI workflow 只执行 `npm install` + `npm run build` + `test -f dist/index.html`，**既不跑 `test:contract`，也不跑 `lims_shell_contract.sh`**。

- **影响**：这类门禁只能证明「某段源码字符串还在」，无法捕获任何行为回归（本次审查发现的 P0-02、P0-03、P0-04 全部能顺利通过全部门禁）。同时 CI 用 `npm install` 且**仓库未提交 `package-lock.json`**（`git ls-files frontend/hbos-portal-web` 确认），依赖版本在 CI 上不可复现——`vite`、`ant-design-vue` 任何 minor 升级都可能无声改变构建产物。
- **建议**（按投入产出排序）：

  1. 立刻在 CI 增加 `npm run test:contract` 与 `bash scripts/portal/lims_shell_contract.sh` 两个 step（成本 5 分钟，堵住现在的空档）。
  2. 引入 `vitest` + `@vue/test-utils`，先给纯逻辑函数补单测：`mapTask` / `taskDuePresentation` / `resolveLimsShellCapabilities` / `unwrapPortalMethod` / `safeRedirect`。这几处正是本次 P0 的所在地，且无需 DOM。
  3. 引入 ESLint（`eslint-plugin-vue` + `@typescript-eslint`）与 Prettier，禁止 `any`、禁止单行超长声明。
  4. 提交 `package-lock.json`，CI 改用 `npm ci`。

### P0-06 生产构建默认回退 Mock，且全站没有「演示数据」标识

- **位置**：`src/services/portalProvider.ts:27-30`、`vite.config.ts:7`、`.env.example:1-2`、`src/components/layout/GlobalHeader.vue:22`
- **证据**：

```ts
// portalProvider.ts:27-30
const mode = (import.meta.env.VITE_PORTAL_DATA_MODE || 'mock').toLowerCase()
export const portalDataSource: PortalDataSource = mode === 'frappe' ? 'frappe' : 'mock'
```

```ts
// vite.config.ts:7
const dataMode = (env.VITE_PORTAL_DATA_MODE || 'mock').toLowerCase()
```

- **问题**：

  1. **白名单被反转**：判断写成「非 frappe 一律 mock」，而不是「必须显式声明且取值合法」。env 未配置、拼写错误（`Frappe`、`FRAPPE` 已由 `toLowerCase` 兜住，但 `prod`、`live` 等错值不会）都会静默降级为 Mock，没有任何报错。
  2. **生产构建无硬失败**：`vite.config.ts` 只在 `dataMode === 'frappe'` 时配置代理，不校验 `mode === 'production'` 时的 `dataMode`。用 `vite build` 且漏配 env，产出的包就是 Mock 版。
  3. **全站无 Mock 标识**：`GlobalHeader.vue:22` 只在 Mock 下挂一个通知铃铛，没有任何「演示数据」横幅。于是 `LimsDashboardView.vue:194-199` 的「待检 2 / 检验中 1 / 待复核 1」、`mockPortal.ts:49-54` 的「128 检验批量 / 98.2% 放行率」会被用户直接当作真实业务数字阅读。
- **影响**：直接违反 `docs/AI_CONTEXT.md:141`「真实 Frappe 模式禁止用 Mock 数据补齐缺失业务能力」的立法意图——规则只挡住了「真实模式混入 Mock」，没挡住「本该真实却整站是 Mock」。在制药 LIMS 场景，把伪造的检验类数字呈现给质量人员是安全级问题。
- **建议**：

```ts
// services/portalProvider.ts —— 显式白名单，非法值构建期/加载期硬失败
const raw = import.meta.env.VITE_PORTAL_DATA_MODE
if (raw !== 'mock' && raw !== 'frappe') {
  throw new Error(`VITE_PORTAL_DATA_MODE 非法或未配置：${String(raw)}（仅允许 mock | frappe）`)
}
export const portalDataSource: PortalDataSource = raw
```

```ts
// vite.config.ts —— 生产构建禁止 Mock
if (mode === 'production' && dataMode !== 'frappe') {
  throw new Error('生产构建必须显式设置 VITE_PORTAL_DATA_MODE=frappe')
}
```

  并在 `PortalLayout` / `LimsLayout` 顶部固定渲染 `<a-alert v-if="portalDataSource === 'mock'" type="warning" show-icon banner>当前为演示数据，非真实业务数据</a-alert>`；同时把「Mock 模式必须显示横幅」写成契约脚本断言（避免以后再被删掉）。

### P0-07 真实模式把「稳定性室 A / B」当业务数据展示

- **位置**：`src/views/LimsStabilityWorkbenchView.vue:43`
- **证据**（原文，已折叠观察）：

```vue
<div class="room-card">
  <strong>稳定性室 {{ envelope.dashboard.master.room ? 'A / B' : '—' }}</strong>
  <span>启用房间 {{ envelope.dashboard.master.room || 0 }} 个</span>
```

- **问题**：后端的 `dashboard.master.room` 是**房间数量**（`apps/hb_lims_app/.../portal/stability.py:14` 定义 `master: { condition: number; room: number; test_item: number }`）。前端只拿它做真假判断，然后**无条件打印字符串 `A / B`**。这不是 Mock 分支——真实模式下 `section` 为 `workbench/schedule/samples/results` 时后端都会返回 `master.room`，所以检验员会看到一个**凭空编造的房间名**。
- **影响**：向生产用户展示不存在的房间标识，直接违反「真实 Frappe 模式禁止用 Mock 数据补齐缺失业务能力」。在有 GMP 审计要求的场景，界面出现后端从未下发的设施名称是不可接受的。
- **建议**：房间名必须来自后端；契约只给数量时就只渲染数量：

```vue
<strong>稳定性室 · {{ envelope.dashboard.master.room || 0 }} 个启用房间</strong>
<span v-if="!envelope.dashboard.master.room" class="muted-text">暂无可用稳定性室</span>
```

  若确实需要展示房间名，应在 `stability.py` 的 `master` 中增加 `rooms: [{ name, condition, status }]` 再由前端 `v-for` 渲染。

### P0-08 真实模式下命令面板展示硬编码的「扫码入库」假入口

> 当前复核：此项在 f23ba17 已删除，当前不成立；以下引用仅保留历史痕迹。

- **位置**：`src/components/portal/CommandPalette.vue:46-57`；挂载点 `LimsLayout.vue:36` 与 `PortalLayout.vue:36`（**两种模式、两个布局都会渲染**）
- **证据**：

```vue
<div class="command-section-title">快速操作</div>
<button class="command-result" :class="{ selected: selectedIndex === results.length }" type="button"
        @mouseenter="selectedIndex = results.length" @click="go('/hbos/work')">
  <div class="command-result-icon inventory"><ScanOutlined /></div>
  <div><strong>扫码入库</strong><span>仓储 · 快捷操作</span></div>
  <ArrowRightOutlined class="result-arrow" />
</button>
```

  经查，`CommandPalette.vue` **全文没有任何 `isMock` / `portalDataSource` 门控**（`grep` 零命中）。
- **问题**：真实 Frappe 模式下按 ⌘K 会看到一个并不存在的仓储扫码功能，点击后跳到 `/hbos/work`（与「扫码入库」毫无关系）——既是**假能力**又是**误导跳转**。此外 `selectedIndex` 的键盘漫游把这条硬编码项计入 `results.length`，真实模式下方向键会落到这条假条目上。
- **影响**：与 P0-07 同属「真实模式硬编码」，且这一条连空数据掩护都没有——无条件渲染。
- **建议**：加 Mock 门控或改由 Provider 下发 `quickActions`；键盘索引同步排除该项：

```vue
<div v-if="portalDataSource === 'mock'" class="command-section-title">快速操作</div>
<button v-if="portalDataSource === 'mock'" ...>扫码入库</button>
```

### P0-09 真实模式下向用户显示「演示模式只读」

- **位置**：`src/views/LimsResultEntryView.vue:16`（判定逻辑 `:114-119`）
- **证据**：

```vue
<span v-if="!canWrite" class="lims-readonly-badge">演示模式只读</span>
```

```ts
const canWrite = computed(() => canSubmit.value || canReview.value || canApprove.value)
```

- **问题**：`canWrite === false` 有三种互不相同的成因：① Mock 模式；② 真实模式下用户没有 `lims.results.submit/review/approve` 权限；③ 记录状态没有可执行动作（已批准、`OOS锁定` 等）。后两种是**真实生产状态**，却被统一表述为「演示模式只读」。**「演示模式」这个 Mock 专用词汇泄漏进了真实模式。**
- **影响**：在 GMP 场景让检验员误以为自己在演示环境，属于数据完整性/信任度污染；同时掩盖了「你确实没有该记录的写权限」这一应当明确告知用户的事实。
- **建议**：按模式与真实成因分开表达：

```vue
<span v-if="portalDataSource === 'mock'" class="lims-readonly-badge">演示模式 · 只读</span>
<span v-else-if="!canWrite" class="lims-readonly-badge">
  {{ detail.result.result_status === 'OOS锁定' ? 'OOS 锁定 · 只读' : '当前账号无操作权限 · 只读' }}
</span>
```

---

## 3. P1 级问题（发布前应修）

### 3.1 上次整改记录中两条声明与当前代码不符（需修正文档口径）

- **声明一**：`LIMS_P4-F6-5_前端审核整改记录.md` §2「权限与入口」称「删除管理后台静态卡片、死按钮、恒不渲染的 management 分支」。实际 `src/components/layout/AppLocalSidebar.vue:25` 仍保留恒不渲染的死分支：

```vue
<RouterLink v-if="limsCapabilities.has('samples')" class="local-nav" to="/hbos/lims/samples" ...>样品与检验</RouterLink>
```

  而 `src/services/limsCapabilities.ts:20-23` 的 `IMPLEMENTED_PAGE_TARGETS` 两张 Set 都**不含 `samples`**，故该 `v-if` 恒为假。同理 `MobileAppNav.vue` 与路由表 `samples/new`、`samples`（`router/index.ts:53-54`）都指向 `LimsPendingView`。三者是同一批死代码，应一并清理或明确标注门禁状态。

- **声明二**：同记录称「真实模式改为纯空 DTO，不再合并 mock 汇总」。当前 `LimsDashboardView.vue:194-199、243-247、255-262` 仍硬编码 `previewMetrics`、`128 / 98.2%`、`SAMPLE-001 阿莫西林` 等演示数字。**但**它们全部包在 `isMock` 三元里（`metrics`、`contextCards`、`currentSample`），真实模式确实不渲染。因此这不是功能回归，而是文档口径过宽——应把结论精确化为「真实模式不渲染 Mock，但 Mock 常量仍随包发布」。

### 3.2 Mock 数据随生产包发布

- **位置**：`src/data/mockPortal.ts`（静态导入于 `src/services/portalProvider.ts:1-10`）、`src/services/limsResults.ts:59-74` 等各 service 内的 `mockResults` 常量
- **证据**：构建产物 `dist/assets/index-Cnm-QK1F.js` 与多个 chunk 中可直接 grep 到 `设计预览`、`SAMPLE-001`、`阿莫西林`。
- **影响**：真实 Frappe 模式下用户下载的 JS 里带着一整套虚构业务数据，体积与信息卫生都受影响（`dist` 总量 2.0 MB）。
- **建议**：Mock 数据改为 `if (import.meta.env.VITE_PORTAL_DATA_MODE !== 'frappe') { const m = await import('@/data/mockPortal') }` 的动态导入，让 Rollup 在真实模式构建时摇掉；或按 `mode` 拆两个入口 module。

### 3.3 6 个视图同时 `onMounted` + `watch(route.fullPath)`，首次进入重复请求

- **位置**：`LimsTaskBoardView.vue:332-340`、`LimsLedgerView.vue:166-167`、`LimsResultListView.vue:173-174`、`LimsQualityStandardsView.vue:112`、`LimsCoaView.vue:135-136`、`LimsAuditView.vue:130-131`、`LimsRetentionWorkbenchView.vue:133`
- **证据**（以检验结果列表为例）：

```ts
watch(() => route.fullPath, async () => { readRouteState(); await loadResults() })
onMounted(async () => { readRouteState(); await loadResults() })
```

- **影响**：首屏必然发起两次相同的 Provider 请求。更糟的是 `watch` 与 `onMounted` 的 Promise 无序号保护，后返回的旧响应会覆盖新响应（**无任何 `AbortController` / seq 守卫**，全仓库 grep 零命中），快速切换筛选条件时可出现数据与 URL 不一致。
- **建议**：删除 `onMounted`，改用 `watch(..., { immediate: true })`；`loadXxx` 内部加递增 `requestSeq`，仅接受最新序号的响应；需要时用 `AbortController` 真正取消。

### 3.4 「我的与设置」全部是装饰性开关，且后端 `preferences` 被完全忽略

- **位置**：`src/views/ProfileSettingsView.vue:34-43,60-62`、`src/services/portalApi.ts:68-71,306-317`
- **问题**：主题 / 动效 / 表格密度 / 三项工作偏好共 6 个开关只写本地 `ref`，不持久化、不驱动任何样式（`density` 变量甚至只出现在模板里）。同时后端 bootstrap 已经返回 `preferences: { reduce_motion, density }`（`portalApi.ts:68-70`），`getFrappePortalData()` 却**根本没有把它映射进 store**（`portalApi.ts:306-317` 的返回对象里没有该字段）。「管理个人资料」按钮（`:28`）也没有 `@click`。
- **影响**：用户改设置后刷新即失效，且无法区分「设计占位」还是「功能坏了」。
- **建议**：二选一——要么接入 `preferences`（映射进 store、落到 `<html>` 的 class / CSS 变量、可选持久化到 Frappe User 字段），要么把这些控件标注为「规划中」并 `disabled`，同时删掉无动作按钮。

### 3.5 无分页 / 无全量的 Hero 指标挑选逻辑，且 `heroMetrics` 在真实模式下短暂持有 Mock

- **位置**：`src/stores/portal.ts:43-69,117-148`
- **问题**：

  1. `bootstrap()` 在真实模式下先执行 `heroMetrics.value = data.heroMetrics`（`getFrappePortalData()` 返回 `[]`，`portalApi.ts:312`），随后 `void refreshSummaries()` **不 await**。因此首帧渲染时 `heroMetrics` 为空/旧值，与「同一 store 内 Mock 常量被写入」的路径难以审计。
  2. `refreshSummaries()` 的 `while (selected.length < 4)` 双层挑选循环（`:130-143`）把跨 App 指标交叉取前 4 条，逻辑晦涩且没有「按权重/优先级」的显式规则；`summaryMetrics` 与 `heroMetrics` 两个字段语义重叠。
  3. `refreshTasks()` 里 `apps.value = apps.value.map(...)` 在异步回调中整体替换数组（`:160-163`），与同函数内 `getPortalTasks(apps.value)` 读取的是不同快照，存在竞态。

- **建议**：明确 `summaryMetrics`（全量）与 `heroMetrics`（首页精选）的职责并加注释；把挑选规则抽成纯函数并加单测；避免在 `bootstrap` 中写入任何 Mock 常量（Mock 分支单独返回即可）。

### 3.6 契约类型只存在于编译期，运行时无任何校验

- **位置**：`src/contracts/portal.ts`（121 行纯 interface）、`src/services/portalApi.ts:25-145` 的 `Backend*` interface
- **问题**：`data.apps.filter(...)`、`mapApp(value)`、`dispatch.data.metrics || []` 等全部直接信任后端 JSON。TypeScript 的 `strict` / `noUncheckedIndexedAccess` 已开启（`node_modules/@vue/tsconfig/tsconfig.json`），能挡住内部索引误用，但**挡不住后端字段改名或缺失**——`manifest.capabilities` 若变成 `undefined`，`new Set(undefined || [])` 会静默得到一个空能力集，表现为「所有菜单消失」，且不报错。
- **建议**：引入 `zod`（或手写 `assertManifest()` 守卫）在 `unwrap()` 边界做一次运行时校验，失败即抛带 `trace_id` 的明确错误；至少为 `manifest` / `access` / `dispatch` 三个关键结构补守卫。

### 3.7 两个巨型工作台视图不可维护

- **位置**：`src/views/LimsStabilityWorkbenchView.vue`（123 行，**最长行 6154 字符**）、`src/views/LimsRetentionWorkbenchView.vue`（140 行，**最长行 6207 字符**）、`src/styles/global.css`（1853 行，最长行 376）
- **问题**：多个 `<script setup>` 把几十个 `ref` / `computed` / 列定义 / 映射表压缩到同一行（见 `LimsRetentionWorkbenchView.vue:104-114`）。`git diff` 在这种文件上完全不可读，代码审查事实上失效；`LimsStabilityWorkbenchView.vue:66` 一整段模板塞在单行内。
- **建议**：至少（a）每个声明一行；（b）把 tab/列定义/状态映射抽到 `src/views/lims/` 下的 `.ts` 模块；（c）把 6154 字符的表单行模板拆成子组件。建议加入 Prettier 的 `printWidth` 强制约束。

### 3.8 `any` 与类型断言破坏类型安全网

- **位置**：`LimsRetentionWorkbenchView.vue:104,113,114,116,127`（`ref<any>`、`(row: any)`、`rows: any[]`、`item: any`）
- **影响**：`vue-tsc` 全绿给人「类型安全」的错觉，但留样工作台的数据访问恰好全部绕过类型检查——而这里是本次唯一出现 `any` 的模块，也是列定义最复杂的模块。
- **建议**：为 `selectedApplication` 定义联合类型 `LimsRetentionUsage | LimsRetentionDisposal`；`filteredRows` / `attentionItems` 用泛型或显式行类型。

### 3.9 请求无超时、无取消、无请求序号，慢响应会覆盖新筛选结果

- **位置**：`src/services/frappeClient.ts:40-46`（`axios.create()` **未设 `timeout`**，只有 CSRF 探测设了 15s，见 `:67`）；受影响调用点 `LimsLedgerView.vue:130-156`、`LimsStabilityWorkbenchView.vue:66,114`、`LimsCoaView.vue:135`、`LimsAuditView.vue:130`、`LimsQualityStandardsView.vue:112`；服务层无 `signal` 参数（`limsResults.ts:86-92`、`limsLedger.ts:131-139`、`limsStability.ts:175`、`limsRetention.ts:207`）
- **问题**：除 §3.3 的「`onMounted` + `watch` 双发」外还有两类并发缺陷：

  1. **翻页与筛选交错**：`LimsLedgerView.vue:142-143` 的 `loadMore` 直接向现有数组 append，而 `watch(route.fullPath)` 触发的非 append 请求可能后到，导致**重复行或筛选结果与列表错配**。
  2. **整包覆盖**：`LimsStabilityWorkbenchView.vue:108,109` 两处都写同一个 `envelope.value`，而 `limsStability.ts:175-196` 每次返回**整包**（后端对非当前 section 返回空数组）。迟到的 `section=schedule` 响应会把已经渲染的 `trend` / 产品选项清空，图表退回空态。
  3. 网络挂起时 `loading` 永不结束（无超时）。

- **建议**：全局 `timeout: 20000`；服务函数签名统一加 `signal?: AbortSignal` 并透传（`frappeClient.ts:123-144` 需同步加参）；视图层加递增请求序号守卫，只接受最新序号响应；稳定性工作台拆为 `getStabilitySchedule/getStabilityTrend` 等局部方法，或提供 `mergeSection(prev, next)` 显式合并，禁止整包覆盖。

### 3.10 列表接口用 `payload.data || 空信封` 兜底，把「畸形成功响应」伪装成「暂无数据」

- **位置**：`limsResults.ts:106`、`limsCoa.ts:101`、`limsSpecifications.ts:101`、`limsAudit.ts:74`、`limsLedger.ts:147-149`、`limsRetention.ts:228`、`limsStability.ts:195`（7 个服务同构）
- **问题**：`unwrapPortalMethod` 已经验证了 `ok:true` 且 `data !== undefined`，但紧接着的 `payload.data || emptyEnvelope()` 把「后端返回 `{ok:true, data:{}}`（Python 侧字段缺失或返回 None）」这一**畸形响应**翻译成空列表。用户看到「暂无数据」，与「真的没有数据」无法区分——在需要数据可靠性排查的合规场景，这会导致排查方向错误。
- **建议**：区分「有内容」与「结构不完整」：

```ts
const payload = unwrapPortalMethod(response)
if (!payload?.data) {
  throw new PortalMethodError({ code: 'INVALID_RESPONSE', message: 'LIMS 返回结构不完整。' })
}
return payload.data
```

  确需允许空页的字段（如 `results`）在**字段级**给 `?? []`，而不是整包兜底。

### 3.11 前端硬编码了第二份能力真值表，且比后端更严

- **位置**：`src/services/limsCapabilities.ts:25-29,48-50` vs 后端 `apps/hbos_portal/hbos_portal/services/access.py:11-15`
- **证据**：后端真值表只有 3 条：

```python
SEMANTIC_ACCESS_REQUIREMENTS = {
    ("lims", "results"): "lims.results.read",
    ("lims", "ledger"): "lims.ledger.read",
    ("lims", "retains"): "lims.retention.read",
}
```

  前端 `REQUIRED_ACCESS_CAPABILITY` 抄了同样 3 条，但 `limsCapabilities.ts:48-50` **额外**要求 `lims.audit.read`；后端没有 `("lims", "audit")` 条目（`hb_lims_app/.../portal/access.py:56-57` 只在 reviewer/manager/system 角色下才追加 `AUDIT_READ_CAPABILITY`）。
- **影响**：两份真值表必然漂移。一旦后端把 `lims.audit.read` 改名，审计页将对**所有用户**永久不可达，而前端只会静默落到 `router/index.ts:92` 的 `forbidden`，没有任何诊断信息。同时 `coa` / `specifications` / `stability` 三项前后端都不做语义校验，任何 `can_enter` 用户都能读。
- **建议**：由 bootstrap 下发 `requiredAccessCapability` 映射（单一真值源），前端只消费；短期内至少在契约测试中断言前后端映射集合相等。

### 3.12 Mock 分支忽略过滤/分页/日期参数，默认开发模式无法暴露接线缺陷

- **位置**：`limsResults.ts:93-96`（忽略 `cursor`/`limit`）、`limsCoa.ts:92-94`、`limsSpecifications.ts:92-94`、`limsAudit.ts:54-66`（忽略 `user`/`from_date`/`to_date`）、`limsLedger.ts:111-129`（忽略 `sample_type`/`material`/`cursor`，`:125` `groups` 是硬编码常量）、`limsRetention.ts:207-222`（`:215-219` 用同一个 `status` 同时过滤 samples/usage/disposal，且 `summary` 过滤后**不重算**——`mockEnvelope.summary` 恒为 `sample_total: 3, in_stock: 3, ...`，而 KPI 卡直接渲染它）、`limsStability.ts:175-191`（忽略 `limit`/`offset`/`month`/`condition`/`exec_status` 等，`:190` 甚至硬编码 `params.stability_product === 'STB-P-AMX' ? data.trend : null`）
- **影响**：由于 §P0-06 的默认模式就是 Mock，**开发者日常看到的界面恰好是参数接线错误 100% 不可见的那一套**。这是 P0-02 / P0-03 / §3.10 能长期存活并通过全部门禁的根因。另外留样 KPI 与实际列表数字自相矛盾（过滤后 `samples_total` 变了但 `summary` 不变），会直接暴露给 Owner 验收。
- **建议**：抽出 `applyQuery(rows, { keyword, status, limit, cursor })` 供 Mock 分支复用，实现与真实接口同语义的过滤与分页；Mock 的 `summary` 从过滤结果派生而非写死。

### 3.13 Portal 首页专业布局在生产环境永不出现，两套布局只有 Mock 分支被验收

- **位置**：`src/views/PortalHome.vue:57`、`src/services/portalApi.ts:314`
- **证据**：

```ts
// PortalHome.vue:57
const showProfessionalHome = computed(() => portal.businessPulse.length > 0)
```

  而 `getFrappePortalData()` 返回 `businessPulse: []`（`portalApi.ts:314`）——真实模式**恒为空数组**。
- **影响**：生产环境 100% 走普通员工版首页，专业/管理者版首页（含 BusinessPulse、DigitalTwin）**从未在真实数据下被验收过**。这是一条静默的「布局分支不可达」，也让 EA-5.3 关于「管理者首页更密」的设计在真实模式失效。
- **建议**：改为按真实能力/角色判定（如 `portal.user.roleLabel` 或 bootstrap 下发的 `density` preference），而不是用「某数组非空」当隐式开关；`preferences.density` 已在 bootstrap 里返回却未被映射（见 §3.4）。

### 3.14 响应式只有 3 个断点，且全局与 scoped 断点混用

- **位置**：`src/styles/global.css` 仅 `1280 / 768 / 390` 三档（`:345,351,964,970,1098,1127,1161,1343,1347,1614,1621,1699,1705,1767,1839,1846`），而各视图 scoped 样式又自造 `1250 / 1000 / 980 / 760 / 700 / 767 / 600` 等断点（如 `LimsQualityStandardsView.vue:119` 用 760px）
- **问题**：桌面到平板区间（769–1279px）缺少定义；scoped 断点与全局断点不同步，容易在 768–760px 之间出现布局跳变。`LimsTaskBoardView` 使用 `role="table"` 自绘表格（`:109-118`），窄屏横向溢出风险靠 `overflow` 兜底而非响应式列。
- **建议**：在 `theme/tokens.css` 固化断点变量并统一为 `1280 / 1024 / 768 / 390`，视图只引用同一套值。

### 3.15 恰好 768px 宽度下导航完全消失（iPad 竖屏无导航）

- **位置**：`src/styles/global.css:1127-1131` ↔ `:1654-1655` ↔ `:1705-1709` —— 三段规则互相冲突
- **证据**（原文，已核实）：

```css
@media (max-width: 768px) { .portal-sidebar, .app-local-sidebar { display: none; } }   /* 1127-1131 */

.mobile-portal-nav, .mobile-app-nav { display: none; }                                  /* 1654-1655 无条件隐藏 */

@media (max-width: 767px) { body { padding-bottom: 78px; }                              /* 1705-1709 */
  .mobile-portal-nav, .mobile-app-nav { position: fixed; ... } }
```

- **问题**：断点差 1px。宽度**恰好等于 768px** 时，侧栏被 `max-width:768px` 隐藏，而移动底栏要到 `max-width:767px` 才显示 → **两者都不渲染，页面没有任何主导航**，只剩 Header 的应用切换器和命令面板兜底。768×1024 正是 iPad 竖屏标准视口，属真实高频设备；`body { padding-bottom: 78px }` 同样落在 767px 块内，存在同样的 1px 缺口。
- **建议**：把两处断点统一为同一个值（推荐 `767.98px` 或统一 768px），并把 `body { padding-bottom }` 移入同一断点块。

### 3.16 任务看板的三处真实模式缺陷（分页、截止筛选、状态计数）

- **位置**：`src/views/LimsTaskBoardView.vue:219-226`（`currentQuery` 不含 `due`）、`:195-202`（`dueFilter` 只过滤已加载数据）、`:190-194`（`statusCounts` 基于已过滤数据）、`:100`（标题把单页数量当总数）；`src/services/portalApi.ts:362-375`（`limit: 20` 硬编码，`total`/`next_cursor` 被丢弃）
- **证据**：后端 `apps/hbos_portal/hbos_portal/api/tasks.py:10-21` 的 `get_tasks` 签名**没有 `due` 参数**：

```python
def get_tasks(app_id, limit=20, cursor=None, view=None, status=None, priority=None, keyword=None)
```

- **问题**（三个独立缺陷，均由「前端本地过滤 + 单页数据」叠加造成，且**仅在真实模式显形**，因为 Mock 分支忽略 query）：

  1. **截止时间筛选只作用于前 20 条**：真实超期任务若排在第 21 条之后，页面会显示「当前视图暂无待处理任务」（`:139`）——给出**错误的清空结论**。
  2. **状态计数 chip 归零**：`status` 已下推服务端过滤，`tasks.value` 只剩该状态，于是选中「已提交」后其余状态 chip 全部显示 0。而该 chip 条的 `aria-label` 是「任务状态统计」，语义上是**工作量总览**，归零会让人误以为其他队列已清空。
  3. **标题数字不是总数**：`{{ visibleTasks.length }} 项任务` 实为单页数量，而后端 `total` 在 `portalApi` 层就被丢弃，前端**根本无法显示真实总量**。
- **建议**：三选一或组合——(a) 后端 `get_tasks` 增加 `due` 参数并把 `due` 加入 `currentQuery()`；(b) `statusCounts` 改用一份不带 `status` 过滤的数据集（或由后端直接返回 `status_counts` 汇总）；(c) 短期至少把标题改为「已加载 N 项」并把 `total`/`next_cursor` 透传，实现游标分页，避免给出错误结论。

### 3.17 「提交结果」按钮缺少「仅草稿可提交」的状态前置校验

- **位置**：`src/views/LimsResultEntryView.vue:115`（对比 `:116-117`）
- **证据**：

```ts
const canSubmit  = computed(() => portalDataSource === 'frappe' && limsAccessCapabilities.value.includes('lims.results.submit'))
const canReview  = computed(() => portalDataSource === 'frappe' && ... && detail.value?.result.result_status === '已提交')
const canApprove = computed(() => portalDataSource === 'frappe' && ... && detail.value?.result.result_status === '已复核')
```

  后端硬校验（`apps/hb_lims_app/.../hbos_lims/lims_service.py:544-546`）：

```python
if result.result_status != "草稿":
    frappe.throw(f"检测记录 {result_name} 状态为 {result.result_status}，仅草稿可提交。")
```

- **问题**：`canReview` / `canApprove` 都带状态校验，**唯独 `canSubmit` 没有**。对 `已复核 / 已批准 / OOS锁定` 的记录，有提交权限的检验员会看到一个**可点击的主按钮**，点了必然被后端拒绝，而前端只给出通用提示「结果提交未完成，已保留当前输入，请检查后重试。」（`:168`）——把服务端的硬校验错报成用户输入错误。`OOS锁定` 记录尤其危险：它诱导用户对已锁定记录发起写操作。
- **建议**：`canSubmit` 补 `&& detail.value?.result.result_status === '草稿'`，并让错误提示区分「状态不允许」与「网络/服务错误」。

### 3.18 冷启动重复 bootstrap，首屏产生约 6 个并发请求

- **位置**：`src/views/LimsDashboardView.vue:276,285` + `src/components/layout/LimsLayout.vue:61-70` + `src/stores/portal.ts:57-60`
- **证据**：

```ts
// LimsDashboardView（子组件）
if (!portal.user) await portal.bootstrap()
await Promise.all([portal.refreshSummaries(), portal.refreshTasks()])

// LimsLayout（父布局）
onMounted(async () => { if (!portal.user) { try { await portal.bootstrap() } catch {} } ... })

// stores/portal.ts:57-60（bootstrap 内部）
if (dataSource.value === 'frappe') { void refreshTasks(); void refreshSummaries() }
```

- **问题**：Vue 中**子组件 `onMounted` 先于父布局执行**。子视图进入时 `portal.user` 仍为 `null` → 发起 `bootstrap()`；父布局 onMounted 时请求仍在途、`user` 尚未落库 → **再发一次 `bootstrap()`**。首屏合计约 2×bootstrap + bootstrap 内 2 个 `void refresh*` + dashboard 的 2 个 `Promise.all` ≈ **6 个并发请求**，且四路响应写同一批 store ref（`summaryMetrics`/`tasks`），存在后写覆盖先写的窗口。
- **建议**：`bootstrap()` 做**单飞（in-flight 复用）**，`LimsLayout` 不再主动调用、只渲染 `portal.bootstrapError` 横幅；加载动作统一交给路由守卫 `ensureSession()`。

### 3.19 真实模式两处「硬编码状态断言」：HeroWorkspace 的「已连接」与 DigitalTwinPanel

- **位置**：`src/components/portal/HeroWorkspace.vue:30-34`（渲染于 `PortalHome.vue:3-9`，未做模式门控）；`src/components/portal/DigitalTwinPanel.vue:10-11,22-26,72-74,89`（门控在 `PortalHome.vue:20`）
- **证据**：

```vue
<div class="status-title"><span>工作台状态</span><a-tag color="success">已连接</a-tag></div>
<div class="status-row"><i class="blue"></i><span>统一身份与会话</span><b>已连接</b></div>
```

```vue
<a-tag color="processing">LIVE READY</a-tag>
<span class="node n1">M606B · 正常</span><span class="node n2">M607B · 过滤阶段</span>
<small>温湿度 / 压差 / 洁净区状态均在许可范围</small>
```

- **问题**：

  1. `HeroWorkspace` 的绿色「已连接」**不来自任何健康检查或会话探测**，是硬编码常量，且用了 `color="success"` 语义色。与同一卡片里的真实值（`appCount`、`totalActions`）混排，会让用户相信「身份与会话已连接」也被验证过——而 store 明确存在 `bootstrapError` / `isAuthError` 分支，会话完全可能已失效。
  2. `DigitalTwinPanel` 除 `statuses` 外几乎全是硬编码：设备编号、状态、环境结论、`LIVE READY` 徽标，且三个模式切换按钮与「进入 3D 空间」按钮**均无点击处理**。它当前没进生产，只是因为真实模式的 `twinStatuses` 恒为 `[]`（`portalApi.ts:315`）导致父组件 `v-if` 不渲染——**安全性依赖「上游永远为空」这一偶然条件**。一旦真实孪生 Provider 接入并返回非空，演示文案会立刻被当成真实设备状态展示。
- **建议**：`HeroWorkspace` 改为由 `portal.authenticated` 驱动（或降级为不带断言的 neutral 文案）；`DigitalTwinPanel` 的节点/状态改为由 `statuses` 派生，删除或补齐无行为按钮，并为整块加显式 `demo` 标记，避免未来误上线。

---

## 4. P2 级问题（改进项）

> 说明：原初版列为 P2 的「无超时 / 无取消」已按证据升级为 §3.9（P1 级）。下表为纯改进项。

| 编号 | 位置 | 问题 | 建议 |
| --- | --- | --- | --- |
| P2-01 | `frappeClient.ts:59-74` | `readCookie('csrftoken')` 与 Frappe 实际的 `csrf_token` cookie 名不匹配（后端 `hb_lims_app/.../lims_service.py:281-284` 走 Frappe 原生 `get_csrf_token()`），导致每次写操作都多发一次 GET；且 `ensureCsrfToken()` **无 in-flight 去重**，并发写会重复请求 | 改读 `csrf_token`（兼容前缀 cookie）；用 `cachedCsrfPromise` 做单飞 |
| P2-02 | `stores/portal.ts:57-60` | `void refreshTasks()` / `void refreshSummaries()` 两个函数只有 `try/finally` 没有 `catch`，内部一抛即为**未处理 Promise rejection**（当前被 `allSettled` 意外兜住，修完 P0-04 后会直接暴露为控制台报错） | 函数内补 `catch` 并写入 store 的 `partialError` |
| P2-03 | `limsResults.ts:4-29` vs `limsLedger.ts:24-49` | `LimsResultRow` 与 `LimsLedgerResult` **26 个字段逐字重复** | 在 `contracts/lims.ts` 抽 `LimsResultRowBase` 供两处 `extends`，否则后端加字段必然只改一处 |
| P2-04 | `portalApi.ts:147-172` vs `frappeClient.ts:20-38` | `PortalApiError` + `unwrap` 与 `PortalMethodError` + `unwrapPortalMethod` **双份同义实现**；调用方 `instanceof` 判断必然漏掉一半错误，`stores/portal.ts:62,89` 的 `isAuthError` 也只识别 axios 错误 | 统一到 `frappeClient` 的 `PortalMethodError` |
| P2-05 | `portalApi.ts:116,157` | 成功路径的 `BackendDispatch.trace_id` 未使用；`PortalApiError.traceId` 全仓**仅赋值、无任何展示或上报** | 成功路径写埋点；失败路径在提示中展示短 trace，便于与后端 `frappe.log_error` 对齐 |
| P2-06 | `limsResults.ts:59-74`、`limsCoa.ts:47-76`、`limsSpecifications.ts:50-76`、`limsRetention.ts:147-186`、`limsStability.ts:128-159`、`limsAudit.ts:31-42`、`limsLedger.ts:82-109` | Mock 业务数据内联在 7 个 service 文件里，违反 `data/` 单一数据源 | 迁到 `src/data/*.mock.ts`，配合 P0-06 用动态 import 隔离 |
| P2-07 | `limsAudit.ts:61-66` | Mock 恒返回固定 `targets`，与真实模式的 `payload.data.targets` 来源不同 → 两模式下筛选下拉选项不一致 | Mock 复用同一 DTO 结构并由数据派生 |
| P2-08 | `portalApi.ts:257-268` | 日期解析 `raw.slice(0,10)` + `raw.match(/T(\d{2}:\d{2})/)`：Frappe 常见的 `YYYY-MM-DD HH:mm:ss`（无 `T`）会**静默丢掉时间**；UTC 字符串按本地零点比较可差一天 | 统一日期库解析并归一化两种格式；后端明确时区契约 |
| P2-09 | `portalApi.ts:411-412` | `appTitle: item.app_id.toUpperCase()` → 其他应用显示为 `INVENTORY` 而非「仓储库存」；无 `entity_id` 时 `id` 可能撞 `v-for` key | 用 bootstrap manifest 做 appId→短名映射；无 id 时用稳定索引/哈希 |
| P2-10 | `limsRetention.ts:225`、`limsStability.ts:193` 等 | `{ app_id: 'lims', ...params, limit }` 的展开顺序让调用方传入的 `app_id` 可覆盖常量（字面量被类型挡住，对象变量可绕过） | 把 `app_id` 放到展开之后，或从参数类型中剔除 |
| P2-11 | `contracts/portal.ts:112-121` | `LimsQueueItemDTO` 在真实模式**恒为 `[]`**（`portalApi.ts:316`），只有 Mock 填充（消费点 `LimsDashboardView.vue:214`） | 重命名 `MockLimsQueueItemDTO` 或在契约注释标明 Mock-only |
| P2-12 | `limsCapabilities.ts:20-23,44` | Mock / frappe 两个集合**内容完全相同**；`samples` 出现在 `:44` 循环里却不在任何集合中（永远为 false）→ 整个 `Record<PortalDataSource, …>` 与 `samples` 项均为死代码 | 删除该 Record（直接用一个 Set）与 `samples` 项，或补齐差异并加注释说明差异原因 |
| P2-13 | `businessNavigation.ts:29-33` | `%(?:2f\|2e\|5c)` 校验后只 `decodeURIComponent` 一次，`%252e%252e` 可绕过该检查（LIMS 分支另有 `startsWith('/hbos/lims/')` 兜底，实际影响有限） | 循环解码至稳定，或对解码结果重新做同一套校验 |
| P2-14 | `LimsDashboardView.vue:205`、`HeroWorkspace.vue:5` | 两处问候语各自**写死**且互相矛盾：一个恒为「上午好」，一个恒为「晚上好」 | 统一抽 `greetingFor(now)` 工具函数 |
| P2-15 | `GlobalHeader.vue:29-38` | 「帮助」按钮无 `@click`，是死按钮 | 接帮助文档或移除 |
| P2-16 | `NotificationCenter.vue:105-113` | 通知数据（`SAMPLE-001 · 阿莫西林含量结果`、`16:08`）硬编码，且只在 Mock 模式挂载（`GlobalHeader.vue:22`） | 明确标注为 Mock 分支或接入 Provider |
| P2-17 | `GlobalHeader.vue:48` | 「个人与设置」用 `@click="$router.push(...)"` 的 `a-menu-item`，丢失键盘/语义一致性 | 改用 `<RouterLink>` 并保留菜单 key 语义 |
| P2-18 | `index.html:7` | `<title>HBOS Portal Prototype</title>` 与路由 `afterEach` 的中文标题不一致，首屏闪烁 | 改为中文正式标题 |
| P2-19 | `index.html` | 未声明 favicon，控制台 404 | 补 `favicon.ico` / `link rel="icon"` |
| P2-20 | `LimsResultEntryView.vue:145-153` | 代提交判定用 `portal.user.id`（Frappe email）与后端 `analyst`（可能是用户全名）直接比较，可能误判 | 改为比较后端返回的规范化 user 标识 |
| P2-21 | 全局 | 无障碍仅覆盖 `aria-label` 与 `role="table"/"tablist"`；卡片式列表缺统一的 `aria-busy` / 空态语义 | 抽统一 `<AppState>`（loading/empty/error）组件并统一 `aria-live` |
| P2-22 | `portalApi.ts:365-370` | 仅对 `app.id === 'lims'` 透传 `view/status/priority/keyword`，其余 App 查询参数被静默忽略 | 改为按能力声明统一透传 |

视图/组件层审查补充（P2-23～P2-36）：

| 编号 | 位置 | 问题 | 建议 |
| --- | --- | --- | --- |
| P2-23 | `LimsTaskBoardView.vue:109-134` | `role="table"`/`role="row"` 已有，但表头与单元格是裸 `<span>`，缺 `role="columnheader"`/`role="cell"`，读屏无法获知列含义 | 补 ARIA 角色，或改用原生 `<table>` 语义的 `a-table` |
| P2-24 | `LimsTaskBoardView.vue:29-42` | `role="tablist"` + `role="tab"` 用法不成立（无 `tabpanel`、无方向键漫游），实际只是筛选按钮 | 改 `role="group"` + `:aria-pressed` |
| P2-25 | 全站（如 `LimsCoaView.vue:40`） | 装饰性 Ant 图标未 `aria-hidden`，读屏会念出 "arrow-right" | 统一封装 `<Icon>` 或逐个加 `aria-hidden="true"` |
| P2-26 | `GlobalHeader.vue:24` | 普通 `<div class="group-brand" aria-label="健康元集团标识">` 无 role，`aria-label` 被浏览器忽略（内部 `img` 已有等价 `alt`） | 删除该 `aria-label` |
| P2-27 | `PortalSidebar.vue:2` | `<aside>` 无 `aria-label`，与 `AppLocalSidebar.vue:2` 的 `aria-label="LIMS 应用导航"` 不一致 | 补 `aria-label="主导航"` |
| P2-28 | `global.css:1831`、`LimsCoaView.vue:148` | 表格内 `.lims-audit-link` 无 `min-height`（实测约 20px），`.lims-text-action` 为 36px，均低于 44px 触控目标 | 统一 `min-height: 44px` |
| P2-29 | `MobilePortalNav.vue:6`、`global.css:1707-1717` | 纯数字徽标无语义（读屏只念数字）；固定底栏 `bottom: 10px` 未加 `env(safe-area-inset-bottom)`，iPhone 会被 Home Indicator 遮挡 | 加 `sr-only` 前缀文案；改 `bottom: calc(10px + env(safe-area-inset-bottom))` |
| P2-30 | `LimsTaskBoardView.vue:173` | `statusOptions` 为硬编码 7 项，但后端 COA 待办会返回 `status: "已审核"`（`hb_lims_app/.../portal/tasks.py:133`）→ 该状态既不在 chip 统计里、也无法被下拉选中 | `statusOptions` 改为 `computed`，合并后端实际出现的状态集合 |
| P2-31 | `router/index.ts:55`、`:43` | `lims-result-review` 是**无任何入口的死路由**；`retains/products` 有页内 Tab 但 `AppLocalSidebar.vue:30-36` 与 `MobileAppNav.vue:39-45` 都无对应导航项（导航缺失） | 抽 `LIMS_NAV` 单一数据源并加守卫断言（每个 `meta.limsCapability` 必须能在 nav 找到或显式标 `hidden`）；补 `retains/products` 侧栏项 |
| P2-32 | `MyWorkView.vue:140` | 文案承诺「点击进入处理」，落地却是只读看板；后端深链携带的 `coa=<name>`（`hb_lims_app/.../portal/tasks.py:139-143`）被看板静默忽略 | 文案改「查看任务」，或看板消费 `coa` 做行高亮/打开详情 |
| P2-33 | `AppCenterView.vue:83` vs `AppCenter.vue:75` | 迁移标签英文混排中文界面，且两处文案不一致（`Legacy · Desk` vs `Legacy`） | 统一为「旧版 Desk / 混合 / 原生」并抽到 `constants/appMigration.ts` |
| P2-34 | `GlobalHeader.vue:9-10` | 品牌名硬编码 `'海滨实验室'/'HBOS'`，而 `portal.branding.productName/companyName` 已由 bootstrap 返回（`portalApi.ts:205-212`） | 优先取 `branding`，硬编码仅作 fallback |
| P2-35 | `LimsRetentionWorkbenchView.vue:131` | `value < new Date().toISOString().slice(0, 10)` 用 **UTC** 日期比较 → Asia/Shanghai 每天 00:00–08:00 期间「留样期至 = 今天」的批次被误标超期 | 改 `new Date().toLocaleDateString('sv-SE')` 或统一日期库 |
| P2-36 | `LimsRetentionWorkbenchView.vue:121-124` vs `LimsStabilityWorkbenchView.vue:114` | 留样工作台切换分区时**不重置** `status`，而下拉选项随分区变化 → 下拉框显示一个已失效的值、列表却不过滤（稳定性工作台已正确重置，属口径分叉） | 照抄 stability 的 `watch(section, () => { keyword=''; status=''; active=''; loadData() })` |

另有若干经核实但优先级更低的项，一并记录：

- `BusinessPulse.vue:12-24`：`<linearGradient id="spark-gradient">` 位于 `v-for` 内，**多个元素共用同一 DOM id**，`url(#spark-gradient)` 只能解析到第一个；当前各卡样式一致所以看不出，一旦首卡被卸载就会丢渐变。
- `LimsCoaView.vue:107-112`：概览卡把「全量 `total`」与「当前已加载页过滤值」混排，加载 50/共 120 时显示「报告总数 120 / 待审核 3」，会让人误判待审核只有 3 份。
- `LimsStabilityWorkbenchView.vue:109`：`refreshTrend` 用 `section='trend'` 的响应**整包覆盖** envelope，而后端该分区不返回 dashboard/schedule/samples → 页头与 KPI 数据被清空（当前靠「趋势页不渲染 KPI」侥幸不显形）。同 §3.9 的整包覆盖问题。
- `LimsResultEntryView.vue:10,84`：从台账点进详情后「返回结果清单」跳到另一个列表，丢失来源上下文；建议 `router.back()` 或带 `query.from`。
- `LimsResultEntryView.vue:189`：仅 `onMounted` 加载、无 `watch(() => route.params.resultId)`。**当前不可达**（没有同记录内切换 resultId 的 UI 路径），但一旦加入「上一条/下一条」即成为缺陷，属零成本防御。
- `LimsCoaView.vue:132`、`LimsQualityStandardsView.vue:110`：`openDetail` 无竞态保护，快速连点两行时先发响应可能覆盖后点的那条。
- `AppCenterView.vue:9-12` + `global.css:613-616`：全站唯一手写原生 `<input>`，`outline: 0` 移除了唯一焦点指示（WCAG 2.4.7 失败），且只有 `placeholder` 无 `aria-label`/`<label>`，图标未 `aria-hidden`。建议改 `a-input-search` 或最小修复（`<label class="sr-only">` + `:focus-visible` 描边）。
- 各列表页 `a-table` 全部 `:pagination="false"` + 无限「加载更多」，无虚拟滚动；审计页还叠加 `aria-live="polite"`，每次追加都会触发读屏播报。
- `PointerAtmosphere.vue:33-37,74-98`：两条 60fps 常驻 `rAF` 自递归（`animatePointer` 与 `render`），空闲时仍整屏 `clearRect`。清理逻辑正确，但低端设备/电池成本真实，建议无粒子时暂停 `render`。
- `LimsDashboardView.vue:112,125,148,249-252`：真实模式留下 4 处「后端字段接入后 / 等待 Provider 返回」等**开发进度话术**。此处**值得肯定的是没有编造任何数字**（`isMock ? previewMetrics : rawMetrics.value` 写法正确），但实现细节不该呈现给生产用户，建议改为业务中性空态并移入 `import.meta.env.DEV`。
- `MyWorkView.vue:16`：`来自 4 个业务应用` 是写死断言（同页的 `actionableCount` 却是真实值）；`ProfileSettingsView.vue:28,41-43`、`GlobalHeader.vue:29-38`、`AppCenter.vue:25-32`、`BusinessPulse.vue:8` 存在多处无行为死控件；`AppSwitcher.vue:83-85` 与 `AppCenter.vue:70-72` 用 `['lims','inventory','attendance','equipment'].includes(app.id)` 硬编码白名单，与 `AppCenterView.vue:38`「未来新增第 4、第 10 个 APP 无需重写主导航」的文案自相矛盾（新增第 5 个 app 会静默不显示）；`AppSwitcher.vue:35-41`「数字孪生 / 空间化运营入口」实际跳 `/hbos/apps`。

---

## 5. 已验证为「做对了」的部分（避免回退）

以下为本次审查确认有效、后续修改时不应破坏的设计：

1. **错误契约双层统一**：后端 `contracts/errors.py` 只回 `{code, message, retryable, trace_id}`，`call_safely` 把 traceback 只写日志不回传；前端 `unwrapPortalMethod()` 强制 `ok:false` 抛错，不再静默成空列表。方向正确。
2. **能力门控语义正确**：`limsCapabilities.ts:15-29` 明确区分「Provider 声明的数据访问能力」与「用户语义权限（`accessCapabilities`）」，路由守卫 `router/index.ts:82-94` 据此区分 `forbidden` 与 `lims-pending`，解析不了就退回 pending 而不是放行。这是我见过的正确做法，请保留。
3. **管理后台 V0 门禁未被突破**：`lims_shell_contract.sh` 会断言 `"management"` 不出现、路由不注册、不跳 `/desk` 或 `:8080`，当前代码合规。
4. **开放重定向防护**：`PortalLoginView.vue:52-56` 拒绝协议相对路径与非站内路径，正确。
5. **Mock 写操作 fail-fast**：`limsResults.ts:130-141` 三个写服务在非 frappe 模式下直接 reject，不会误发真实写请求。
6. **登录请求例外处理**：`frappeClient.ts:116` 排除 `/api/method/login` 自身的 401 触发全局跳转，避免登录页死循环，细节到位。
7. **`redirect` 透传 + 会话恢复**：登录成功后 `router.replace(safeRedirect(route.query.redirect))`，链路完整。

---

## 6. 建议的修改顺序（可直接排期）

| 轮次 | 范围 | 对应问题 | 预计改动面 |
| --- | --- | --- | --- |
| **F6-7-0（当天止血）** | ① **清除真实模式硬编码演示内容**（稳定性室 `A / B`、命令面板「扫码入库」、「演示模式只读」）；② 数据模式白名单 + 生产构建硬失败 + 全站 Mock 横幅；③ `refreshTasks/refreshSummaries` 补 `catch` | P0-07 / P0-08 / P0-09 / P0-06、P2-02 | `LimsStabilityWorkbenchView.vue`、`CommandPalette.vue`、`LimsResultEntryView.vue`、`portalProvider.ts`、`vite.config.ts`、`PortalLayout.vue`、`LimsLayout.vue`、`stores/portal.ts` |
| **F6-7-A（P0 正确性）** | 登出与会话状态机、任务状态映射、结果列表游标分页、提交按钮状态校验、768px 断点、任务看板三重缺陷 | P0-01 / P0-02 / P0-03、§3.15 / 3.16 / 3.17 | `stores/portal.ts`、`frappeClient.ts`、`portalApi.ts`、`GlobalHeader.vue`、`LimsResultListView.vue`、`LimsTaskBoardView.vue`、`LimsResultEntryView.vue`、`MyWorkView.vue`、`global.css` |
| **F6-7-B（P0 可观测）** | Provider 部分失败上报、`provider_errors` 呈现、trace_id 呈现、统一错误/空态组件 | P0-04、§3.10、P2-05、P2-21 | `portalApi.ts`、各 `Lims*View.vue` 的错误态、新增 `components/global/AppState.vue` |
| **F6-7-C（P0 工程门禁）** | CI 接契约脚本、`package-lock.json` + `npm ci`、vitest 覆盖纯函数、ESLint + Prettier、**新增「Mock 专用内容必须显式门控」检查** | P0-05（P0-07～09 的根因） | `.github/workflows/hbos-portal-frontend.yml`、`package.json`、`scripts/portal/lims_frontend_contract.mjs`、新增 `src/**/__tests__` |
| **F6-7-D（契约加固）** | `contract_version` 校验、边界运行时解码、能力真值表单一来源、统一错误类型、`limit` 常量对齐 | §3.11、P2-04 | `portalApi.ts`、`frappeClient.ts`、`limsCapabilities.ts`、后端 bootstrap |
| **F6-7-E（并发与 Mock 可信）** | axios 超时 + `signal` + 请求序号；bootstrap 单飞；稳定性拆方法/合并；Mock 分支实现同语义过滤分页与统计 | §3.9 / 3.12 / 3.18 / 3.19、P2-36 | 8 处加载器、7 个 lims 服务、`stores/portal.ts`、`src/data/*.mock.ts` |
| **F6-7-F（去重与清理）** | 抽 `useLimsListPage` + `LimsOverviewCards` + `LimsFilterBar`；9 份状态色映射收敛为单一 `limsStatusTone`；死代码清理、Mock 动态导入、巨型视图拆分、导航 `LIMS_NAV` 单一源、导航 origin 校验 | §3.1 / 3.2 / 3.7 / 3.8、P2-11/12/13/31、P2-D 各项 | `LimsCoa*`、`LimsQualityStandards*`、`LimsRetention*`、`LimsStability*`、`AppLocalSidebar.vue`、`businessNavigation.ts` |
| **F6-7-G（体验与 a11y 收尾）** | 设置持久化或标注禁用、首页布局判定修正、断点统一、ARIA/焦点/触控目标、死控件与文案 | §3.4 / 3.13 / 3.14、P2-14~20、P2-23~30、P2-32~35 | `ProfileSettingsView.vue`、`PortalHome.vue`、`HeroWorkspace.vue`、`DigitalTwinPanel.vue`、`theme/tokens.css`、`AppCenterView.vue` |

> **建议的执行顺序理由**：F6-7-0 的四项改动都很小，但 P0-07～P0-09 是**当前真实模式正在发生的用户可见污染**（不是潜在风险），且修完即可让「真实模式还剩多少 Mock 泄漏」变成可枚举的有限集合——这是后续所有轮次的前提。F6-7-C 的「Mock 专用内容门控检查」应当与 F6-7-0 同期落地，否则同类泄漏一定复发。

---

## 7. 审查范围声明与遗留

- 本次为**只读代码审查**，未修改任何业务代码；报告本身为新增文档。
- **两路独立审查交叉验证**：服务/契约层一路（覆盖全部 `services/`、`contracts/`、`data/`），视图/组件层一路（覆盖全部 18 个 views + 9 个 layout + 8 个组件，并独立跑过 `vue-tsc --noEmit`）。**两路均已完整返回**；其中新报出的 3 条真实模式硬编码泄漏（P0-07～P0-09）与 768px 导航真空（§3.15）**均已由本人回到源码逐字复核后才收录**。视图层报告中的推断性结论（如「当前不可达但属定时炸弹」的 `resultId` 监听缺失）已明确标注「当前不构成缺陷」。
- 未获取真实 Frappe Session 运行态证据（本机仍缺 `docker`），因此 P0-03（分页截断）、P0-04（错误呈现）、§3.13（首页布局分支）、§3.16（任务看板全量筛选）的**真实数据表现**仍需在环境恢复后用真实 Provider 复核。
- 未运行无障碍自动化扫描（无 axe / Lighthouse 依赖），P2-23～P2-29 的 a11y 结论基于静态代码审读与 CSS 数值核算。
- 历史复核基线：`docs/experience/LIMS_P4-F6-5_前端审核整改记录.md` 的结论需按 §3.1 修正措辞后继续作为 Authority。

## 8. 状态台账影响

- 本报告为**只读审查交付**，本轮**不修改**任何业务代码、不改变当前里程碑或轮次。
- 按项目规则，`docs/PROJECT_STATUS.md`、`docs/CURRENT_MILESTONE.md`、`docs/milestones/` 对应文件**本轮不需更新**，原因：审查未改变项目状态，仅新增一份 REVIEWING 状态的审核报告。
- `README.md`、`CLAUDE.md`、`AGENTS.md`、`docs/AI_CONTEXT.md`、`docs/READING_GUIDE.md` 已检查：本次审查未产生阶段描述变更，无需更新。其中 `docs/AI_CONTEXT.md:157` 的 P4-F6-5 状态描述仍与事实一致，未过期。
- 待 Owner 确认后，建议在 `docs/experience/README.md` 的 P4 段落追加本报告链接，并将 §3.1 的两条口径修正回写 `LIMS_P4-F6-5_前端审核整改记录.md`。
