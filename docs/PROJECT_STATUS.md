# 项目状态

## 生产取数服务自启 — 2026-10-29

状态：**已修复并运行态验证**。

**现象**：生产看板报「无法连接生产数据服务，请检查网络或服务是否在运行」。

**根因：是我误杀的。** 排查 OCR 无令牌分支时我用了

```bash
HBOS_OCR_PORT=8101 ... uvicorn ...
pkill -f "port 8101"
```

`pkill -f` 匹配整条命令行。生产服务的命令行是
`.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8101 --env-file .env`
—— 同样含 `port 8101`，一起被杀。当时只想清掉临时实例，没考虑到同端口上还有正在用的服务。

**服务本身没坏**：重新拉起后 `/health` 200、`/production/monthly` 返回 6 行、看板 KPI 正常（82.0% / 33.3% / 100.0% / 100.0%）、133 个测试全过。

**根本问题：这个服务一直没有自启配置。** `launchctl list` 里只有 OCR 和两个定时任务，`hbos_production` 从来靠手动起 —— 机器重启、终端关闭、被 pkill 命中都会静默消失，而页面上那句话和「代码坏了」长得一样。

**修复**

```text
services/hbos_production/scripts/start.sh（新增）
  只挑 HBOS_PRODUCTION_* / HBOS_FEISHU_*     不 source 整个 .env
  外部变量优先                                 临时换端口不会被 .env 覆盖
                                               （实测：早先 PORT=8121 仍起在 8101）
  缺飞书凭据 exit 2                            不起「所有接口都 503」的服务
  默认绑 127.0.0.1                             零鉴权服务不能暴露局域网
services/hbos_production/launchd/com.haibin.hbos.production.plist（新增）
  KeepAlive + RunAtLoad                        常驻、被误杀/崩溃自动拉起
  ThrottleInterval 10                          不疯狂重启
services/hbos_production/tests/test_launch_assets.py（新增，6 条）
  plist 可解析/常驻/脚本可执行/只读自己的键/缺凭据非零退出/外部变量优先
```

**运行态验证（本机实测）**

```text
launchctl list        → 13354  0  com.haibin.hbos.production
/health               → 200
/production/monthly   → 6 行，month=2026-10
看板页                → KPI 正常，无失败提示
kill -9 → 14 秒后自动拉起（新 PID 13440，health 200）
```

**现在的自启全景**

```text
com.haibin.hbos.ocr           常驻   launchd
com.haibin.hbos.production    常驻   launchd   ← 本轮新增
com.haibin.hbos.production-warm  定时 07:10 / 16:40
com.haibin.hbos.production-ai    定时 16:30
```

四个服务里现在只有 warm / ai 是定时的，两个常驻服务都有了 KeepAlive。

**我自己的教训（写下来避免再犯）**：以后清理测试进程一律按 **PID** kill，不用 `pkill -f` 匹配端口号 —— 端口是多个服务共用的命名空间，匹配到别人是迟早的事。

## 服务自启迁移方案（服务器部署前置）— 2026-10-27

状态：**只出方案文档，未改任何运行配置**。

新增 `docs/deployment/服务自启与服务器部署.md`。回答「换到服务器上还要不要重做自启」：**要，而且不能照搬。**

关键结论：

- launchd 是 macOS 专属，Linux 上换成 systemd（常驻用 `.service`，定时用 `.timer`）
- **四个服务里有三个本来就没有自启**（`hbos_production` 一直靠手动起），迁移时一并补上
- **`host.docker.internal` 在 Linux 上默认不存在** —— 当前 `docker-compose.yml` 里 `extra_hosts` 一次都没出现，照搬过去容器连不上 OCR，症状与本次排查的「识别服务不可达」完全一样
- **生产看板是浏览器直连 8101**，`VITE_PRODUCTION_SERVICE_ORIGIN` 构建时烘焙进 bundle，换服务器必须重新构建前端；且服务绑 `127.0.0.1`，服务器上浏览器连不到，需要定「暴露端口 + CORS」还是「nginx 反代同源」
- `.venv` 不能跨机器拷（Mac 的 `bin/python` 符号链接在 Linux 上是断的）

文档给了 A（全部进 compose，推荐）/ B（宿主机 systemd）两套完整草案 + 验收清单 + 照搬会坏的三处。

**两个决定已定（Owner 2026-10-27）**：

1. **服务器有 GPU** → OCR 进 compose，走 NVIDIA Container Toolkit 直通。这消除了「OCR 必须留在宿主机」的唯一理由（Mac 拿不到 Metal 加速）。文档补了 GPU 直通前置步骤、镜像基础、以及一个关键提醒：`c1_local_vlm` 走的是 MLX（Apple 专属），Linux + NVIDIA 要换 vLLM 等后端，那是**独立一轮的工作量**，不要在上线时同时换环境+换模型。
2. **看板走 nginx 反代同源**，不做浏览器直连。理由：① HTTPS 页面请求 HTTP 服务会被混合内容静默拦掉，直连等于要再维护一张证书；② 直连要把当前零鉴权的服务绑 `0.0.0.0`，内网任何机器 `curl` 就能拿走全部生产数据（CORS 拦不住 curl）；③ 反代同源时 `fetch` 默认 `same-origin` 会自动带 Frappe session cookie，可用于鉴权。

**遗留一步代码**：`productionServiceConfigured` 现在只看 `SERVICE_ORIGIN.length > 0`，env 留空会被判成「未接入」不发请求。反代上线时需改 3 行加「同源模式」开关。**故意没现在做** —— 本机 mock 模式不涉及，提前改会增加分叉。

## OCR 服务自启与识别链路修复 — 2026-10-27

状态：**已修复并运行态验证**。

**现象**：入库拍照识别页报「识别服务当前不可用 / 识别服务不可达（ConnectionError）」。

**根因**：不是代码缺陷 —— 宿主机 8100 **没有任何进程在监听**。`lsof -iTCP:8100` 为空，`curl 127.0.0.1:8100/health` 返回 000。这个服务一直没有自启配置，机器重启或终端关闭后就没了。

**修复**

```text
services/hbos_ocr/launchd/com.haibin.hbos.ocr.plist（新增）
  KeepAlive + RunAtLoad  常驻、崩溃自动拉起（另外两个 plist 是定时跑完即退）
  ThrottleInterval 10    崩溃后不疯狂重启
services/hbos_ocr/scripts/start.sh（新增）
  只挑 HBOS_OCR_*        不 source 整个 .env（里面有 DB 密码与飞书密钥）
  令牌缺失 exit 2        不起「/health 200 但 recognize 一律 503」的半残服务
  默认绑 0.0.0.0         绑 127.0.0.1 时容器连不上
services/hbos_ocr/tests/test_auth_boundary.py（新增）
  四种状态分开钉          服务没起 / 未配令牌 503 / 令牌错 401 / 正确 200
services/hbos_ocr/tests/test_launch_assets.py（新增）
  plist 能解析、常驻、脚本可执行、只读 HBOS_OCR_*、缺令牌非零退出
services/hbos_ocr/README.md
  启动命令补上令牌要求 + 三种失败态的排查表
```

**运行态验证（本机实测）**

```text
launchctl list | grep hbos.ocr   → 9342  0  com.haibin.hbos.ocr
curl 127.0.0.1:8100/health       → 200，default_backend=c2_ocr
容器 → host.docker.internal:8100  → 200
带令牌 POST /recognize           → 200
无令牌 / 错令牌                   → 401
未配令牌的服务                    → 503「OCR 内部认证未配置」
kill -9 → 14 秒后自动拉起（新 PID，health 200）
容器内 get_intake_context        → available = True
```

**顺带发现的坑**：README 原来的启动命令**没有载入 `HBOS_OCR_SHARED_TOKEN`**。照它启动，`/health` 200、`get_intake_context` 也报 `available: true`，但真正识别时 503 —— 而页面上三种失败态显示的是同一句话。已在 README 与测试里固化成可区分的三种状态。

**仍未验证**：真实标签照片的识别准确率（本次用的是 1x1 占位图，只验证链路通）、c1 本地大模型后端（未装 mlx-vlm）。

## 第三轮复审修复 — 2026-10-27

状态：**全部修复；`npm run build`、`npm test`、四个测试套件全绿**。

本轮复审报告的 5 个严重 + 5 个一般，全部已复现并修掉。

**S1 缓存超时接管后旧 generation 覆盖新缓存**

已复现（`follower={'generation':'new'}` / 最终缓存 `'old'`）。`_run_refresh()` 现在**写入前先在锁内校验 `_INTENTS.get(key) is intent`**：成功不写缓存、失败不开冷却，只记日志。两条回归测试覆盖「旧线程晚回不覆盖」与「旧线程晚失败不冷却」。

**S2 AI 重复行清理删掉刚更新的行**

已复现（`updated=1, removed=1`，但表里剩的是最旧的 `old-A`）。根因：`keys` 指向最后一条（被更新），`duplicates` 却收「除第一条以外的全部」→ 最后一条既被更新又被删除。现在按 `(产品, 工序)` 分组，**survivor = 最后一条**，`keys` 与 `duplicates` 严格互斥。补了三条重复、指纹未变、dry-run 三个场景。

**S3 非 `FeishuError` 异常仍 500**

已复现（注入 `ReadTimeout` → 500）。两层修复：

- **客户端边界**：`feishu.list_records` / `_token` 把 `httpx.HTTPError`、非 JSON 响应、token 缺字段统一包成 `FeishuError`；
- **端点兜底**：`monthly` / `ai_analysis` 追加 `except Exception → 502`，并保留 `HTTPException` 原样。

**S4 Desk 幂等指纹只有 7 字段**

已补齐到与 Portal/后端一致的 16 字段，并加**三处清单对账测试**（Desk `FINGERPRINT_FIELDS` / Portal `FINGERPRINT_FIELDS` / 后端函数签名）。

**S5 跨源部署报表导出打向 Portal 自己**

新增 `frappeApiUrl()`（优先 `VITE_FRAPPE_BASE_URL`，回退 `VITE_FRAPPE_APP_ORIGIN`），`exportReport` 改用它。另加 **XLSX 魔数校验**（`PK`）—— 200 的 HTML 错误页不再被存成 `.xlsx`。

**一般项**

```text
G1 草稿页 batchLookupState     批次查询失败不再显示「未填」，改「暂不可用」+ 提示
G2 runlock errno               只有 EACCES/EAGAIN 算 LockBusy；EIO/ENOLCK 原样抛（不再伪装成「有人正在跑」）
G3 拣货短缺按 (物料+批次)       同物料两批次各要 5kg、只凑到一批 10kg 现在会正确报短缺
G4 v-html → 插值               服务端错误详情不再用 v-html（删标签≠转义）
G5 防抖 timer 卸载清理          批次/物料/入库/对账四页补 onBeforeUnmount
```

**验证（本机）**

```text
npm test                  184 passed（含 typecheck 前置，21 文件）
npm run build             通过；circular chunk 警告 0
services/hbos_production  133 passed
services/hbos_production_ai 95 passed
apps/hb_inventory_app     160 passed, 1 skipped
git diff --check / compileall  通过
```

**仍未验证**：Frappe 真实 Site（事务 / User Permission / PDF）、Redis `set(nx)` 真实原子性、真实飞书限流恢复。测试全绿不等于生产验收通过。

**文档治理 WARN（仍未处理）**

- `docs/milestones/M1_START_GATE.md:5` 的 `FINAL_REVIEW_BLOCKED` 与 `AI_CONTEXT.md` 的 `FINAL_REVIEW_PASS` 不一致。
- `docs/CURRENT_MILESTONE.md` 的 `M2 = NOT STARTED` 与 `M1_START_GATE.md` / `AI_CONTEXT.md` 的 `M2-STOCK-R1 = IN_PROGRESS` 冲突。

## 第二轮整体审查修复 — 2026-10-27

状态：**全部修复；官方构建 `npm run build` 已通过**。

**致命：`npm run build` 失败**

`InventoryPickView.vue` 用了 `updatePickList` 却没导入 → `TS2304`，官方构建直接失败，且保存/定位在运行时会 `ReferenceError`。

**为什么之前的「vue-tsc 通过」是假绿灯**：我此前跑的是裸 `npx vue-tsc --noEmit` —— 根 `tsconfig.json` 只有 `references` 没有 `files`，裸跑等于什么都没检查（exit 0）。`npm run typecheck` 用的是 `-p tsconfig.app.json`，才会真的查。这条已写进下面的门禁改动。

```text
frontend/src/views/InventoryPickView.vue   补 updatePickList 导入
frontend/package.json                      npm test 现在 = typecheck + vitest
                                           （这正是漏 import 时 test 绿、build 红的原因）
```

**严重 1：缓存等待者竞态**

`_claim_intent` 返回 `(None, None)` 后，等待者再去 `_INTENTS` 查一次 —— leader 恰好在这两次读取之间完成并摘掉自己，等待者什么都查不到，`_await_intent` 返回 `(True, None)`，`_load_once` 直接返回 `None`，`monthly()` 随后 `data["rows"]` 抛 500。

已复现并修复：`_claim_intent` 现在**把 existing intent 一并交出**，`_await_intent(intent, timeout)` 直接等那一个 future。同时补上 leader 异常要**以返回值转交**（`future.result()` 会重抛）。

**严重 2 / 一般 1 / 一般 3：看板失败态重试成功后不切回 ready**

`refreshBoard()` 成功分支只更新 `board`，没切 `phase` —— 失败态模板优先，用户点「重试」拿到数据后仍停在失败页。已补 `phase='ready'` + 清空 `boardFailure`/`refreshFailed`/`refreshFailMessage`；新一轮刷新先撤掉上一次的「已更新」，避免掩盖紧接着的失败。

**严重 3 / 严重 4：幂等指纹漏字段 + 缓存写失败拖垮请求**

- 前后端指纹都从 7 个字段扩到 **16 个**（加来源类型、生产日期、有效期、储存条件、车间、效期类型、供货单位、生产单位、原厂批号）。两边字段清单有测试对账。
- 草稿建好之后，幂等缓存写入与锁释放各自 `try/except` —— 缓存故障只记日志，不能让已成功的建单返回失败（否则用户重试会再建一张）。

**一般 2 / 一般 7：JSON 解析兜底**

`fetchProductionBoard` 的 200 响应、`warm.py` 的 200 响应都加了「解析失败 ⇒ 明确的上游异常/FAILED」，并校验结构。

**一般 4 / 一般 5**

物料详情加 `detailSeq`（搜索已有 `searchSeq`）；报表 `runSeq` 已在必填校验前递增、合计行提示已改为只比较 `rawRowCount > rows.length`（这两条上一轮就修了，本轮确认）。

**一般 6 / 一般 8：附件身份**

新增 `File.hbos_attachment_kind` 自定义字段（`setup.py`），生成货位卡时写 `待检证+货位卡`、复制标签照片时写 `标签照片`。

- `_purge_previous()` 先按标记删，文件名只作为**老数据回退**（且要求标记为空）。
- 前端 `pickCardFile` / `pickIntakePhoto` 优先按 kind 认，文件名正则/扩展名只作老数据回退。

**一般 9：单源格式异常拖垮整块**

`_load_anomalies` / `_load_quality` 的逐源 try 从「只兜 `FeishuError`」扩到「转换+统计阶段的任何异常都算该源失败」，异常类型与源名都记日志。早先一张表字段漂移就能让整个 `/production/monthly` 变 500。

**一般 10：circular chunk**

`vendor-icons` 单独拆块与 `vendor-antd` 互相引用 → `Circular chunk: vendor-icons -> vendor-antd -> vendor-icons`。已把图标并回 `vendor-antd`，警告消失（0 条）。

**验证（本机实测）**

```text
npm run build            通过（这是本轮最重要的一条）
npm test                 174 passed（含 typecheck 前置）
services/hbos_production 124 passed
services/hbos_production_ai 90 passed
apps/hb_inventory_app    159 passed, 1 skipped
git diff --check / compileall  通过
vite build circular 警告  0
```

浏览器实测（mock 5179）：16 条路由 `h1` 全对；拣货单页点「保存」无异常、无未解析元素。

**仍未验证**：Frappe 真实事务 / User Permission / Redis `set(nx)` 原子性 / PDF 生成 —— 需要真实 Site。

**文档治理 WARN（本轮未处理，属历史遗留）**

- `docs/milestones/M1_START_GATE.md:5` 仍写 `FINAL_REVIEW_BLOCKED`，与 README/AI_CONTEXT 的 `FINAL_REVIEW_PASS` 不一致。
- `docs/CURRENT_MILESTONE.md` 仍保留 `M2 = NOT STARTED` 历史段，与 `M1_START_GATE.md` / `AI_CONTEXT.md` 的 `M2-STOCK-R1 = IN_PROGRESS` 冲突。
- 上一轮本文件写的「vue-tsc 通过」是裸 `vue-tsc` 造成的假绿灯，本轮已用 `npm run build` 复核并把 typecheck 并入 `npm test`。

## 优化项（包体 / N+1 / 搜索 / 运行态测试）— 2026-10-27

状态：**已修复；前端包体有构建实测，运行态测试可复现执行**。

**1. 前端包体**

发现一个**既有构建缺陷**：仓库里残留 `frontend/hbos-portal-web/vite.config.js`（10 月 10 日由 `tsc` 生成、已被 .gitignore 忽略）。Vite 优先读 `.js`，所以 `.ts` 里的配置**一直没生效** —— 这也是为什么此前加 `manualChunks` 毫无变化。删掉 .js 后配置才真正起作用。

```text
主包（业务代码）      1,975 kB → 132 kB   (gzip 608 → 43)
vendor-antd          1,371 kB → 863 kB   (gzip 406 → 258)
vendor-icons         新增独立块           127 kB (gzip 25)
vendor-three          679 kB（Twin 页按需加载）
vendor-vue             29 kB
vendor（其他依赖）    247 kB
```

做法：`manualChunks` 按库拆分 + 库存/生产视图改懒加载 + `app.use(Antd)` 全量注册改为**深路径导入 + 逐个注册** + `message`/`Modal` 也走深路径。静态/动态双重导入警告从 2 条降到 0。

**2. 扫码页 N+1**

`print_utils.load_packaging_map()` 一次批量取；`format_packaging_spec/count()` 是纯函数。`hbos_bin.py` 不再逐行调两个各查一次子表的函数（一屏 50 批 = 100 次查询 → 1 次）。

**3. 前置通配符**

物料/批次搜索改为**先前缀（走索引）、没命中再退到包含匹配**。计数与列表使用同一个模式（避免「匹配 N 个」与列表长度对不上）。

**4. 运行态测试**

新增 `services/hbos_production/tests/test_runtime_http.py`：**起真的 uvicorn、走真的 socket**，验证并发单飞、失败传播、缓存跨重启、yesterday 日期。`services/hbos_production_ai/tests/test_runtime_lock.py`：真起两个进程抢 flock。`apps/hb_inventory_app/tests/test_packaging_runtime_contract.py`：把在容器里实测过的子表结构（`desc tabHBOS Packaging Detail`）固化成断言。

**验证**

```text
services/hbos_production      pytest 118 passed（含 5 条真 HTTP）
services/hbos_production_ai   pytest  90 passed（含 2 条跨进程锁）
apps/hb_inventory_app         unittest 148 passed, 1 skipped
frontend/hbos-portal-web      vitest 165 passed；vue-tsc 通过；vite build 通过
git diff --check / compileall 通过
```

**浏览器实测（mock 模式，5179）**：15 条路由逐条打开，`h1` 全部正确、无未解析的 `a-*` 元素；下拉选项、日期选择器、时间线、描述列表、头像、DropDown、搜索弹窗均正常渲染。

**仍未验证**：Frappe 真实 Site 上的权限矩阵、Redis `set(nx)` 原子性（只在容器里核过表结构，没跑并发写）、PDF 生成、flock 在容器内的行为。

**优化 6 的边界**：上面的运行态测试覆盖的是**服务层**（生产取数 / AI 调度），不是 Frappe 侧。Frappe 真实事务、User Permission 矩阵、PDF 渲染仍需要真实 Site，本轮没有。

## C 批复审修复（幂等边界与数据保全）— 2026-10-27

状态：**已修复并跑通测试；运行态仍未验证**。

分支 `p4/production-dashboard`。本轮修复审报告的严重 3/4/5 与剩余一般问题。

**修了什么**

```text
apps/hb_inventory_app/hbos_inventory/api.py
  包装语义        _parse_packaging(None) = 不动；([]) = 清空（语义未变，前端改为正确传参）
  幂等键          payload 指纹：同 request_id 不同内容 → 抛「请求内容已变化」，不再返回旧单据
  原子抢占        cache.set(lock, nx=True, ex=60)；抢不到等 2 秒后明确提示「正在生成」
  锁释放          建单成功/失败都释放（失败用 except BaseException + re-raise）
  建单主体        _create_intake_draft_inner() 拆出，只为让锁释放集中一处
  unit_weight     允许 0/空（只有件数），只拒绝负数与非有限值（A 批已改）
  request_id      新增入参，与 Portal 同语义
frontend/.../services/intake.ts
  幂等键          nonce + 关键字段哈希：同草稿重试同 id，换照片/物料/批次/数量 → 新 id
                  进入页面生成新 nonce（修「离开再进来命中上一张单」）
  包装            没有有效行 → null，不是 []
frontend/.../views/InventoryIntakeView.vue
  packagingPayload()  无有效行返回 null；半填行**报错**而不是静默丢弃
                     （静默丢弃会让「没填包装」变成 `[]`，正好触发清空）
  onMounted           调 beginIntakeOperation()
apps/hb_inventory_app/.../page/hbos_photo_intake/hbos_photo_intake.js
  Desk 路径       同样生成 request_id、换照片换 nonce、空包装传 null
services/hbos_production_ai/app/main.py
  _engine_signature()  模型 / 温度 / 端点进指纹 —— 换模型必重跑（原实现会全 skipped）
  status          清理失效行失败 → partial（不是 ok）
services/hbos_production_ai/app/writer.py
  cleanupFailed   删除失败逐条上报（含 recordId / 产品 / 工序 / 原因）
services/hbos_production_ai/app/llm.py
  _retryable()    只重试超时/连接/408/429/5xx；400/401/403/404 立即失败
services/hbos_production_ai/app/runlock.py（新增）
  跨进程锁        flock 独占；拿不到就跳过本轮（避免两进程各建一行重复数据）
services/hbos_production/app/main.py
  _persist()      每个 key 一把落盘锁 —— 旧快照不能最后落地盖掉新快照
apps/hb_inventory_app/www/hbos_bin.py
  短码精确匹配    命中多个（不同公司的同名货位）→ 报候选，不再取第一个
frontend/.../views/InventoryDraftReviewView.vue
  文案            「数量可在动作条修改」→「本页不能改，请放弃草稿重新录入」（页面本来就没有编辑控件）
frontend/...（4 处）
  请求序号        物料搜索 / 批次搜索 / 货位切换库存 / 拣货单位 / AI 报告
```

**验证**

```text
services/hbos_production      pytest 113 passed
services/hbos_production_ai   pytest  88 passed
apps/hb_inventory_app         unittest 136 passed, 1 skipped
frontend/hbos-portal-web      vitest 156 passed（15 文件）；vue-tsc 通过；vite build 通过
git diff --check              通过
python compileall             通过
```

**未验证**：Redis 上的 `set(nx=True)` 原子性、Frappe 真实事务与回滚、flock 在容器内的行为、PDF 生成。这些都需要真实 Site / Redis / 容器环境，本机没有。

**仍未修（剩余一般项）**

```text
一般 14 的剩余部分  —— 目前已覆盖物料/批次搜索、货位切换、拣货单位、AI 报告；
                      其余列表页的初次加载没有序号（并发首屏风险低）
优化 1/2  —— 前端包体与静态/动态双重导入
优化 4    —— 扫码页包装 N+1 查询
优化 5    —— 搜索用前置通配符
优化 6    —— 运行态测试（Redis 并发、真实事务、PDF）
```

致命 1/2 按 Owner 决定不修。

## B 批复审修复（失败路径不得显示成正常）— 2026-10-27

状态：**已修复并跑通测试；运行态仍未验证**。

分支 `p4/production-dashboard`。本轮修复审报告的**严重 2** 与相关的几条一般问题：数据源部分/全部失败时的展示语义、取数失败原因区分、批次/物料/货位下拉的错误态、`/production/yesterday` 的日期。

**修了什么**

```text
services/hbos_production/app/main.py
  _load_anomalies / _load_quality  新增 sourceCount（配置的源总数）
                                   前端据此区分「部分失败」与「全部失败」
  /production/yesterday            date 改为真实的**昨日**（原为 monthly().updatedAt = 今天）

frontend/src/services/productionBoard.ts
  fetchProductionBoard  → BoardResult 四态：
                            ready / not_configured / unreachable / upstream_error / unauthorized
                          区分 401/403、503、5xx、网络失败 —— 不再一律「未接入」
  AnomalyInfo / QualityInfo 增加 sourceCount

frontend/src/views/ProductionDashboardView.vue
  boardFailure         按原因给不同标题 + 「重试」按钮（未接入态除外）
  anomalySourceNote    部分车间失败 → 「闭环率为部分口径」
                       全部车间失败 → 「异常数据全部取不到」，
                       **不再落到「当月无异常记录」**
  qualitySourceNote    部分 QC 表失败 → 「合格率为部分口径」
  refreshFailMessage   刷新失败时把具体原因带出来（原为固定一句「仍是旧数据」）

frontend/src/services/inventoryDocs.ts
  getBatch → BatchLookup（found / not_found / error），404 与 401/403/网络/5xx 分开
frontend/src/services/inventoryMaster.ts
  getItem  → ItemLookup（同上）

frontend/src/views/InventoryBatchView.vue
  state 增加 error（原所有异常都进 missing）
  attachmentsState      附件列表读不到 → 「无法确认卡片是否已生成」，
                        不再说成「卡片尚未生成」
  doRegenerate          生成成功但回读失败时不再报「重新生成失败」
frontend/src/views/InventoryDraftReviewView.vue
  attachmentsState      照片读不到 → 「无法读取附件列表」，不再说成「没有照片」
frontend/src/views/InventoryItemView.vue
  detailState 增加 error（原所有异常都进 missing）
frontend/src/views/Inventory{Entry,Pick,Reconcile}View.vue
  warehouseOptionsState 货位下拉取不到 → 明确提示 + 重试，不再静默变空下拉
frontend/src/views/InventoryIntakeView.vue
  contextState          入库上下文取不到 → 明确提示 + 重试
```

**验证**

```text
services/hbos_production      pytest 112 passed
services/hbos_production_ai   pytest  66 passed
apps/hb_inventory_app         unittest 119 passed, 1 skipped
frontend/hbos-portal-web      vitest 151 passed（15 文件）；vue-tsc 通过；vite build 通过
git diff --check              通过
python compileall             通过
```

**未验证**：任何页面的浏览器实测。生产看板要 8101 取数服务、库存页要 8081 Frappe，两者本轮都没起，所以「失败态长什么样」只经过类型检查与源码级回归测试。

**仍未修（C 批）**

```text
严重 3  包装缺省 [] 会清空已有批次包装（既有缺陷，前端 || [] 是旧代码）
严重 4  幂等键跨页面复用 + 后端非原子
严重 5  AI 指纹未覆盖模型/温度
一般 3  并发落盘可能被旧快照覆盖
一般 7  失效行删除失败仍返回成功
一般 8  AI 写回无跨进程运行锁
一般 9  LLM 对不可重试错误也重试
一般 14 物料搜索/批次搜索/货位切换/拣货单位/AI 报告 仍无请求序号
一般 16 货位短码「精确匹配」命中多个时仍取第一个
一般 17 草稿页文案称数量可改，但无编辑控件
```

致命 1/2 按 Owner 决定不修。

## A 批复审修复（上一轮回归）— 2026-10-27

状态：**已修复并跑通测试；运行态仍未验证**。

分支 `p4/production-dashboard`。复审报告指出 6 个严重问题与多条一般问题，本轮只修 **A 批（上一轮引入的回归 + 已确认的低成本项）**，B/C 批未动。

**修了什么**

```text
services/hbos_production/app/main.py
  _INTENTS + Future      每个 key 一个在途刷新，成功值/异常/完成状态都在里面
                         冷启动 leader 失败时等待者收到**同一个异常**（实测 6 并发 → 1 次 producer、6 个异常）
  _NEGATIVE_UNTIL        失败冷却 10 秒：上游挂了不让每个请求各捅一次
  _claim_intent()        手动刷新与后台刷新**共用**同一个 per-key 标记
                         （实测修复前 ['bg','manual'] 两个 producer，修复后只有 ['bg']）
  _load_once()           等待超时后接管的是**新 generation**，不再递归等同一个 event
  _persist()             落盘前校验也放进 try；异常兜底从 OSError 放宽到 Exception
  _plausible_rows()      先逐行验 label 是字符串再比较，混入 None 不再抛 TypeError
services/hbos_production/app/warm.py
  ConnectError/ConnectTimeout → UNREACHABLE（可直连兜底）
  ReadTimeout/协议错误        → FAILED（服务可能仍在跑，不重复拉飞书）
services/hbos_production/app/contract.py
  删除 is_excluded() 与 EXCLUDE_* 常量（生产路径从未调用；真实口径是 ROW_MEMBERS 白名单）
services/hbos_production/tests/test_contract.py
  改为断言白名单契约 + 喂噪声产品断言六行全 0
apps/hb_inventory_app/hbos_inventory/api.py
  unit_weight 回退为「拒绝负数/非有限」，允许 0/空（DocType 非必填、打印支持「10瓶」）
frontend/.../ProductionDashboardView.vue
  收率达标率分母要求 targetYieldRate !== null；缺目标值的品种单独点名
frontend/.../InventoryReportView.vue
  runSeq 提前到必填校验之前；只有合计行时也显示提示
```

**验证**

```text
services/hbos_production      pytest 108 passed
services/hbos_production_ai   pytest  66 passed
apps/hb_inventory_app         unittest 119 passed, 1 skipped
frontend/hbos-portal-web      vitest 145 passed（14 文件）；vue-tsc 通过；vite build 通过
git diff --check              通过
python compileall             通过
```

**仍未修（B / C 批，及复审里明确排除的项）**

```text
严重 2  部分车间/QC 取数失败仍显示为完整 KPI          B 批
严重 3  包装缺省 [] 会清空已有批次包装（既有缺陷）      C 批
严重 4  幂等键跨页面复用 + 后端非原子                  C 批
严重 5  AI 指纹未覆盖模型/温度                         C 批
一般 1/10/11/12/13/14  失败被显示成「空/找不到」的其余路径  B/C 批
一般 3/5/7/8/9/16/17   并发落盘覆盖、yesterday 日期、清理失败、运行锁、LLM 重试等  C 批
致命 1/2  生产服务鉴权、库存仓库权限                    按 Owner 决定，不修
```

## 库存 / 生产看板代码审查修复（第 1–3 轮）— 2026-10-27

状态：**已修复并跑通测试；不含权限项，运行态未验证**。

分支 `p4/production-dashboard`。本轮按 Owner 授权**只做审查报告的第 1、2 轮 + 第 3 轮非权限部分**，**不合并 #39 / #46**。

**明确未做（仍开放）**：

- 致命 1：生产取数服务无身份/权限校验（`services/hbos_production` 仍只靠 CORS 与 `127.0.0.1` 绑定）；
- 致命 2：库存扫码页与四张报表绕过 Warehouse User Permission（`hbos_bin.py` 只判登录；报表用裸 SQL）；
- 对应地，`is_excluded()` 死代码、货位卡 PDF 的后端识别标识未动。

> 产品分支 `feature/hbos-portal-product` 上这两项已由 #39 / #46 修好（`warehouse_scope.py`、`require_service_token` + Portal 代理）。本分支**没有**带过来，因此上述风险在本分支仍然成立。

**第 1 轮 —— 缓存并发 / 落盘 / 快照 / 预热**

```text
services/hbos_production/app/main.py
  _cached()            single-flight：只有抢到刷新权的请求起线程（实测 5 并发曾起 5 个 producer）
  _cold_load()         冷启动同样单飞：N 个请求只拉一次 13 张表；领导者失败时等待者自己顶上
  _persist()           唯一临时名（tempfile）+ 失败清理，消除并发写同一 .tmp 的覆盖
  _plausible()         拒绝空 rows；逐行校验六个固定 label 与字段类型
  _restore()           校验 stale_at / built_at 是有限数值，异常一律丢弃
  monthly()            质量不再冻进 board 快照；新增 qualityDataAsOf，两者各有时间戳
services/hbos_production/app/warm.py
  WarmResult           三态枚举：SUCCESS / UNREACHABLE / FAILED；502 后不再回退直连
```

**第 2 轮 —— 日期 / AI 幂等 / KPI 语义**

```text
services/hbos_production/app/contract.py     _as_date → 复用 parse_month_day（点号/斜杠/中文/ISO 统一）
services/hbos_production_ai/app/sources.py   _sort_key 统一成 YYYYMMDD；全表日期不可解析时拒绝分析
                                             stats_fingerprint_parts：统计输入纳入指纹
services/hbos_production_ai/app/main.py      _fingerprint 接收 stats_parts
services/hbos_production_ai/app/writer.py    清理失效工序行与重复行（新增 feishu.delete_record）
services/hbos_production_ai/app/stats.py     _month 复用统一解析（`2026年10月01日` 不再变 `2026年10`）
services/hbos_production_ai/app/parse.py     `完整报告` 非空校验
frontend/.../ProductionDashboardView.vue     分母为 0 返回 null 显示「—」；pctText 只在 null/NaN 显示「—」
                                             「近 12 个月无异常记录」→「当月无异常记录」
```

**第 3 轮 —— 前端错误语义与安全加固（不含权限）**

```text
intake.ts              lookupItemMaster 返回 found / not_found / error（不再把网络/权限故障说成「未建档」）
inventoryDocs.ts       getItemMasterInfo 返回 null 表示没查到（界面「暂不可用」而非「未填」）
                       hasSubmittedIntakeEntry 返回 true | false | null
                       searchBatches 增加真实 total / truncated
inventoryMaster.ts     countItems 失败返回 null（不再把「不知道」当 0，避免漏报截断）
InventoryBatchView     货位卡按后端文件名正则识别（不再「第一个 PDF」）；入库单状态未知有独立文案
InventoryDraftReview   404 与网络/权限/5xx 分开；标签照片优先最早创建的那张
InventoryEntryView     单位查询按行独立序号；放行预检加请求序号 + 批号快照校验
InventoryReportView    请求序号防覆盖；合计行提示分支移到空结果之前
inventoryReports.ts    CSV 公式注入防护（= + - @ Tab CR；数值与纯数字串不加前缀）
productionBoard.ts     fetchAiAnalysis 三态 ready / empty / unavailable；报告缓存加 5 分钟 TTL + 手动失效
hbos_inventory/portal/summary.py   「有库存物料」改 actual_qty > 0
www/hbos_bin.py        合计按 UOM 分组；短码前缀命中多个时报「候选不唯一」，不再静默取第一个
www/hbos_bin.html      不再硬编码 kg
feishu.py              上游判定 token 失效时清缓存并重试一次（不再一路 502 到重启）
api.py                 包装单件重量必须 > 0 且有限；create_intake_draft 增加 request_id 幂等
```

**验证结果（本机）**

```text
services/hbos_production      pytest 101 passed
services/hbos_production_ai   pytest  66 passed
apps/hb_inventory_app         unittest 107 passed, 1 skipped（静态/契约测试，非 Site 运行态）
frontend/hbos-portal-web      vitest 143 passed（14 文件）；vue-tsc 通过；vite build 通过
python compileall             通过
```

**未验证（NOT_VERIFIED）**：Frappe 真实 Site 上的权限矩阵、并发锁竞争、PDF 生成、幂等键在 Redis 上的实际行为。当前环境无可用 Site。

**已知环境问题（非本轮引入）**：`pytest apps/hb_inventory_app/tests` 会因 `hb_inventory_app` 包名解析到外层目录而 collect 失败；CI 与本地都改用 `python -m unittest discover -s tests`（在 App 目录内执行）。

**下一轮建议**：致命 1 的最小版本（服务间 token + 未配置即 503）约 20 行，不涉及 Portal 代理层；致命 2 需要先定「仓库级 User Permission 是否为正式口径」。

## 并行权限治理 IAM-0 — 2026-10-01

Owner 已批准进入统一身份与权限治理。当前仅交付设计、角色—动作—范围矩阵、只读源码盘点工具与本机任务书；实际 Site 盘点和隔离验收仍为 NOT_RUN，不修改账号、角色或业务数据，不替代原账号收尾。入口：[IAM-0 治理资料](governance/iam/README.md)。

## PR #21 合并后收口 — 2026-10-01

状态：**FINAL_REVIEW_PASS / MERGED_TO_PORTAL_PRODUCT**。PR #21 已使用 expected-head squash 合入 `feature/hbos-portal-product`，产品 HEAD `e4b16ee80aaaf21aac2304246a4de1f9fe8995ea`；Owner 最新无破坏验收 PASS，团队合成浏览器 final-submit 3/3 PASS，新 squash 四项 CI SUCCESS。旧 #22 已关闭未合并，IAM-0 由 clean Draft PR #23 仅承接原 11 文件增量；PR #15 仍 Open Draft，main 未变化。

合并前发现并修复的原生 MFA Administrator proof P1 已完成回归；本次收口未修改 Owner 密码、MFA、飞书绑定、Secret、业务数据或 P1 卷。合并前 BLOCKED/WAITING 状态继续作为历史证据保留，但不再作为当前项目状态。

团队后续 Portal Authority：`feature/hbos-portal-product@e4b16ee80aaaf21aac2304246a4de1f9fe8995ea`。

## 账号小范围收尾 — 2026-10-01

本轮接续交付基线 `eee1c5e22c57be3436244e77c65e189bd7eee242` 与 PR #21，仅做资料登录渠道、唯一个人导航、折叠偏好说明、飞书头像同步及 C03/C07/C09/F03 缺项补测；不重新全量审计、重画页面或新增账号功能。真实 Administrator 已成功飞书登录为 USER_CONFIRMED_SUCCESS，绑定、密码、MFA、Secret、企业与回调保留。本机沿用既有 P1 Site/Compose/入口，发布分支不合并、不强推、不推 main/base。 补测确认并修复参与页期限遗漏与 GET 回调未提交记录，原矩阵历史保持；最终浏览器新凭据步骤由工具要求人工接手，团队脚本与未执行状态单列。


项目：新乡海滨智能运营管理平台。架构：Frappe/ERPNext 开源底座 + Frappe 多 App 模块化架构 + 外部独立服务扩展。

## 当前 Portal 轮次 — 2026-10-01

本轮（2026-10-01）接续 PR #21，执行登录账号模块 UI 规范回归与全功能审修。Owner 已亲自确认 Administrator 能通过本人飞书验证并登录，记为 OWNER_CONFIRMED_SUCCESS；历史成员权限待审批或登录失败记录不再代表当前事实。保留真实绑定、密码、MFA、Secret、企业与回调；不要求重复配置。认证页沿用已有 Ant Design Vue / ConfigProvider / typography / tokens，修复表单、证明期限、错误状态、同路由目标与提交结果处理。破坏性、并发与交接只在独立合成 Site 验证。新版本真人 OAuth、本人收到验证码、第二位真人交接与移动软键盘结果单独记录，未执行不写 PASS。复用现有 P1 / Compose / 卷与常用入口，最终本机 SHA/build ID、远端提交、CI 和制品须一致。公司服务器为 NOT_DEPLOYED。主记录：`docs/milestones/M1_RP3_统一账号飞书绑定与正式发布.md`。PR #21 head `codex/portal-unified-account-release`、base `feature/hbos-portal-product`；不强推、不自动合并、不推 main/base。

| 项目 | 实际状态 |
| --- | --- |
| 唯一 User 与密码/飞书账号流程 | 统一账号与受控变更已实现并分层测试；密码记录保留；Owner 已确认本人飞书成功登录，新版本正常回归单列 |
| 五应用与已批准前端 | Administrator 五入口实际打开；普通用户按原角色仅开放知识/设备；未实现项明确标注 |
| 备份恢复/保留校验/production 制品 | 当前 P1 原卷已备份并迁移，账号/密码/角色/权限/业务/身份指纹保留；Portal 与 LIMS 编译资产已部署 |
| 通用 Gateway/团队依赖 | 版本化通用代码、Dockerfile、完整 lock 已提供；私有资料不进 Git |
| 真实 PR/CI | [PR #21](https://github.com/zjl327707743/HBOS-Platform/pull/21) 已合并到 Portal 产品分支；当前 CI/制品以产品 HEAD `e4b16ee80aaaf21aac2304246a4de1f9fe8995ea` 为准 |
| 固定 Mac 入口 | P1 的 loopback 同源入口 5188 已运行；本机隐藏设密工具已提供，未自动修改密码 |
| Owner 本人验收 | Owner 已确认 Administrator 本人飞书成功登录；第二位员工开户、本人验证码与交接另行记录，合成测试不替代真人 |
| 公司服务器 | 未部署，固定 IP / 正式 HTTPS 后续；不影响已交付 Mac 状态 |

## 其他既有里程碑

M0 已完成并封板。考勤 M1 产品验收仍由 M1-FIX 主记录维护，不因本轮 Portal 代码测试而 closeout；M1-FIX-F 原状态为 REVIEWING。库存 M2-STOCK-R1 原状态为 IN_PROGRESS，其余独立轮次不由本任务推进。历史记录见 `docs/milestones/` 对应主文档，本公开状态摘要不携带人员、私有路径或内部运行报告。

本轮未回退或重建既有 Portal 开发分支，未重做 P0，未覆盖候选数据库，未重置原密码/角色。Owner 已选择 P1 作为固定本地使用环境；保留原 Site 和数据，未删除数据库、用户、文件或卷。公司生产首次部署另行授权。

## 生产看板（P4）

### HBOS Portal 生产看板模块 — 取数服务 + 前端复刻 — 2026-10-02

状态：**取数服务已实现并验证；前端已复刻进 Portal；等配凭据即可显示真数**。

**Owner 2026-10-02 五个决定（全部确认）**：取数架构 = B 独立服务；模型 = 健康元 deepseek-flash 且先只跑 4BMA；
不做人工确认；定时 = launchd 每天 16:30；原型视觉门 = 过。

**本日交付（三类）**：

```text
① 架构文档
 docs/frontend/P4_生产看板_取数架构方案对比.md      A/B/C 对比，定 B
 docs/frontend/P4_生产看板_AI分析服务规格.md         AI 规格（含 §8 决定、§8.1 复用 HBOS_AI_* 约定）

② 前端复刻（新增 5 + 改 7）
 src/data/productionNav.ts · src/services/productionBoard.ts
 src/components/layout/ProductionLayout.vue · ProductionLocalSidebar.vue
 src/views/ProductionDashboardView.vue
 改：router / mockPortal / portalProvider / AppCenter / AppSwitcher / .env.example / launch.json

③ 取数服务（新服务 services/hbos_production）
 app/{config,feishu,sources,contract,main}.py · tests/ · README · requirements · pyproject · .env.example
```

**取数服务要点**：

- 照 `services/hbos_ocr` 的模式（独立 FastAPI 服务，绑 127.0.0.1:8101，凭据在 `.env` 且已 gitignore）；
- **口径全部实现在 `app/contract.py`（纯函数，不依赖 FastAPI/飞书）**：收料日期落月、加权目标收率、
  F13 三成员合并、四车间不录、无值留 None；前端**不做任何计算**，避免前后端两套算法；
- 四个接口：`/health`、`/production/monthly`、`/production/yesterday`、`/production/ai-analysis`；
- **两条纪律**：取不到就 503（**不返回 0 或空行**）；没有值就留 None（不填 0）。

**已验证**（非仅静态）：

```text
services/hbos_production   pytest 21 passed（口径单测 16 + 服务冒烟 5）
                           uvicorn 实起 → /health 200；未配凭据时三个数据接口均 503 且响应体无数字
frontend/hbos-portal-web   npx vue-tsc -b --noEmit → exit 0
                           mock 模式实跑：首页宫格出现 Production 且可点入；/hbos/production 与
                           /production/center 两页正常、侧边栏高亮正确；375 宽无横向溢出
```

**⚠️ 实现中发现并修掉一个真 bug**：飞书 datetime 字段返回**当地午夜**的毫秒时间戳，
用 `utcfromtimestamp` 解析会得到**前一天**（`2025-10-01` → `2025-09-30`）。
本看板正是「按收料日期落月」，每天少一天会让跨月批次落错月。
已改为固定 **UTC+8** 解释，并有测试锁住。

**待办**：

```text
配 HBOS_FEISHU_APP_ID / SECRET 到 services/hbos_production/.env
  → 起服务 → 前端配 VITE_PRODUCTION_SERVICE_ORIGIN=http://127.0.0.1:8101
  → 看板自动从「未接入」切到正常态
AI 分析服务（launchd 脚本，先跑 4BMA）—— 待配模型 key
```

**本轮未做**：未建 Frappe App、未注册 provider、未写飞书、未实现 AI 分析服务、
未改既有 openclaw 项目、未提交任何凭据。

**已知台账滞后**：本文件顶部仍记载 M1-FIX 为当前阶段，`docs/CURRENT_MILESTONE.md` 的 Portal 段停留在 P3-LIMS closeout；是否一并更新待 Owner 指示。

### HBOS Portal 生产看板 — 质量合格率口径 + AI 工艺分析放开到 6 产品 — 2026-10-10

状态：**已完成并实跑验证（只读飞书 + 写 AI 结果表）**。

**Owner 2026-10-10 两条指令**：① 质量合格率按原 openclaw 数值显示 **99.9%**；异常闭环率**维持现有实算**；
②「把工艺提升与改进方案 AI 分析做好」。

**先查清的事实（本轮的关键结论）**：既有 openclaw 看板的 `质量合格率 99.9%` 与 `异常闭环率 96%`
**都是代码里写死的字符串常量**，不是算出来的 —— 见 `generate_daily_report.py:686-687` 等 4 处逐字重复；
同一张看板下方的「异常警报」列表又把每行状态硬编码成「正在跟踪」（0% 闭环），与 KPI 卡的 96% 自相矛盾。
所以 96% 本平台**无法复现**（历史上从未被计算过），Owner 只要求沿用质量合格率那一个数。

**另核**：Owner 提供的《新乡海滨产品质量数据汇总》多维表格（54 张表）**不适合做合格率** ——
只有 18 张有结论列且结论恒定（F13(B) 998 条无一条不合格；回收品表单选值全「符合」），
4BMA(M3) 的 `异常事件登记` 1086 条只有 1 条；该表是按**合格放行批**登记的台账，本就不收不合格批。
真实可算值是 100%，算不出 99.9%。

**本日交付**：

```text
① 前端（改 2）
 views/ProductionDashboardView.vue   质量合格率 → 99.9%（QUALITY_RATE 常量 + 出处注释）
                                     AI 面板：四色评级标签 / 按严重度排序 / 折叠展开 / 分档计数 / 分析日期列
 services/productionBoard.ts         closureLabel 注释订正为「全车间统一 = 事件原因」

② AI 分析服务（改 3 + 新增 1）
 services/hbos_production_ai/app/sources.py        修复多表形态工艺描述解析（会静默出错）
 services/hbos_production_ai/tests/test_sources.py 新增 8 个单测（5 种表形态 + 边界）
 services/hbos_production_ai/{.env,.env.example}   HBOS_AI_PRODUCTS 放开到 6 个在产产品

③ 文档（改 3）
 docs/frontend/P4_生产看板视觉方案与页面结构.md     REV 8 变更说明 + §6.3bis/§6.3ter/§6.5bis
 docs/frontend/P4_生产看板_AI分析服务规格.md        状态改为「已实现并放开到 6 产品」
 services/hbos_production_ai/README.md             当前范围 + 放开时踩到的表结构差异坑
```

**AI 分析放开时发现并修掉的缺陷（静默出错，不报错只是结论错）**：
各产品的工艺描述表**结构并不一致** —— 4BMA 用 `项目`；F9/F12/F13 用 `序号`（F9 是裸数字 `1/2/3`）；
无菌两张表用 `工艺描述/工艺参数/设备参数` 且**一表多规格**。原实现只认 4BMA 一种形态，
其余产品要么读不到工序、要么把 `序号`/`基本信息` 当工序喂给模型。修复见
`app/sources.py::parse_craft_records()`。

**已验证（非仅静态）**：

```text
services/hbos_production_ai   pytest 26 passed（原 18 + 新增 8）
                              实跑 DRY_RUN=1 → 6 产品全部 ok，工序数与工艺描述表实际列数吻合
                              实跑写回 → 结果表 62 行（4BMA 8 / F9 11 / F12 7 / F13 6 / 无菌美罗 18 / 无菌亚胺 12）
                              再跑一次 → skipped 8（4BMA 幂等生效，未重复追加）
frontend/hbos-portal-web      npx vue-tsc -b → exit 0
                              实起 dev server：质量合格率 99.9%、异常闭环率 65.7%（44/67）、
                              AI 面板 62 条按严重度排序 + 展开/收起可用
```

**异常闭环率口径复核（2026-10-10 只读）**：4 车间日报异常表 + 滚动 12 自然月 + `事件原因` 非空。
二车间 9/31、三车间 8/9、六车间 0（空表不计入）、无菌 31/31 —— 合计 48/71 = 67.6%（当日）。
看板 65.7% 系服务端缓存态；差值全部来自无菌表是活的（数字会动正说明它在取数）。

**本轮未做**：未改既有 openclaw 项目、未提交任何凭据、未新增/修改飞书表结构（只向
`AI工艺分析结果` 幂等写入结果行）、未改 Frappe 侧。
