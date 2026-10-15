# PR #34 与 `feature/hbos-portal-product` 口径裁定单

> 生成：2026-10-10 · 交付流程产出，**供 Owner 裁定使用**
> 状态：**待合并的文档候选**，由 **PR #35** 承载（`docs/pr34-base-ruling` → `feature/hbos-portal-product`，实际差异为 4 份文档）
> 关联：PR #34 https://github.com/zjl327707743/HBOS-Platform/pull/34（**Open / 存在合并冲突，截至 2026-10-10 本轮远端复核**）／ PR #35 https://github.com/zjl327707743/HBOS-Platform/pull/35
> Head `feature/hbos-attendance-console` @ `8b7d92f` ／ Base `feature/hbos-portal-product` @ `ddbe9bf3`
> 修订：2026-10-10 追加 §5.8 与 §7 第 8 项（移植分析新发现的两项 Base 测试覆盖不到的差异）
> Owner 范围澄清：现有人员资料为测试人员数据，本轮不以其隐私泄漏作为合并阻塞；本文件对旧来源状态的技术事实不代表对生产凭据、数据迁移或业务规则改动的授权。

---

## 一、结论先行

本次不是文本冲突问题，而是**同一 App 的两条独立演进线**。决定性证据是：

> **Base 自带的治理测试 `test_merge_governance.py`（15 项）对当前 Head 逐个静态比对，14 项失败、1 项未核验。**
> **Base 的 `test_admin_nums_single_source.py` 亦失败**（断言旧引擎必须不存在、策略注册表不得含工号字面量）。

即：**Head 无法通过 Base 的验收**。这不是「解冲突」能修的——两边对同一模块的安全与治理政策根本不同。

### 两条线各自的优势（方向相反）

| 维度 | Base `feature/hbos-portal-product` | Head `feature/hbos-attendance-console` |
| --- | --- | --- |
| 员工名单 | **已去硬编码**：`rule_lists.py` **0 个**工号字面量，改为从 `HBOS Attendance Policy Assignment` **业务数据**解析（`policy_registry.PolicySet`），种子文件明确**不入库** | **338 个**工号字面量硬编码在 `rule_lists.py` |
| 飞书凭据 | 全部环境变量化（`os.environ.get("HBOS_FEISHU_*_APP_TOKEN","")`） | **硬编码字面量**（`api.py:30/32/34`、`rest_leave.py:14`） |
| 重算删除谓词 | **已删除**第二条 `attendance_date > %s`，结构上不可能误删 | **仍在**（`api.py:411`），仅用 35 天滚动窗口**规避** |
| 外部写入 / AI | 默认关闭（`HBOS_FEISHU_SYNC_ENABLED=0`、`HBOS_DELICLOUD_SYNC_ENABLED=0`、`HBOS_AI_ENABLED=0`、`HBOS_AI_ALLOW_PII=0`） | 无开关；AI 以 `HBOS_AI_BASE_URL` 是否存在隐式判定 |
| 导出安全 | `is_private: 1` + `_require_export_permission()` | `is_private: 0` + `insert(ignore_permissions=True)` |
| 写接口守卫 | `_require_hr_read` / `_require_hr_write` 覆盖人员与班次管理 | 班次管理有 `_require_read/_require_write`；**人员管理 5 个接口无任何守卫**（`bind_shift` / `bulk_bind_shift`） |
| 旧引擎 | 4 个旧引擎**已删除**，两个测试守门 | 保留 + 废弃标记，测试要求其**存在** |
| 调休调度 | 单入口 `sync_rest_leave_pipeline`（顺序内聚） | 3 条并列调度（依赖靠注释约束） |
| 平台 App | `hbos_portal` **83 文件**（完整 `auth/`、账号 DocType、`api/csrf.py`） | 37 文件（薄骨架，**全部为 Base 子集路径**） |
| 考勤业务逻辑 | 较旧：**无**滚动窗口修复、**无**长值班配对放宽 | **较新**：含 2026-10-09 两项修复 |
| 门户前端 | 103 文件（LIMS / twin / knowledge 多线） | 69 文件（考勤工作台线） |

**因此：按 Head 解冲突 = 退回 Base 的全部安全加固；按 Base 解冲突 = 丢掉本分支 10 月的考勤行为修复。**

### 建议口径

**沿用本项目 M3-PORTAL-R1 已用过的「选择性移植（非 merge）」**：以 Base 为骨架，把 Head 的**考勤业务行为与 M3 前端交付物**重新落上去；**不要**把本 PR 直接合并。

---

## 二、冲突清单（109 个文件）

| 类型 | 数量 | 说明 |
| --- | --- | --- |
| `add/add` | 83 | 两边独立新增同一路径 → 同源代码双份实现 |
| `content` | 22 | 两边都改了同一文件 |
| `modify/delete` | 4 | **Base 删除了该文件、Head 修改了它** → 高风险静默丢失点 |

### 2.1 `add/add` 83 个的构成

| 目录 | 数量 | 性质 |
| --- | --- | --- |
| `apps/hb_attendance_app/**` | 38 | 考勤 App 同源双份（`pairing.py`、`rule_lists.py`、`rest_leave.py`、`sync_rest_leave.py`、`portal/*`、3 个新 DocType、15 个测试） |
| `frontend/hbos-portal-web/**` | 36 | 门户前端双份实现 |
| `apps/hbos_portal/**` | 5 | 薄平台 App（`hooks.py`、`integration_checks.py`、`modules.txt`、`pyproject.toml`、`tests/fake_providers.py`） |
| `docs/superpowers/**` | 3 | 设计 / 计划文档 |
| `docs/milestones/**` | 1 | 里程碑文档 |

### 2.2 `content` 22 个的构成

- **配置层 4**：`.env.example`、`.gitignore`、`README.md`、`.github/workflows/hbos-quality-gate.yml`
- **编排层 2**：`docker-compose.yml`、`hooks.py`
- **考勤判定 4**：`api.py`、`page/hbos_attendance_dashboard/dashboard_data.py`、`page/hbos_attendance_dashboard/hbos_attendance_dashboard.js`、`report/月度考勤汇总/月度考勤汇总.py`
- **台账与入口 7**：`docs/AI_CONTEXT.md`、`docs/PROJECT_STATUS.md`、`docs/CURRENT_MILESTONE.md`、`docs/READING_GUIDE.md`、`docs/deployment/M0-R3E_…md`、`docs/milestones/README.md`、`docs/milestones/M1_START_GATE.md`
- **里程碑文档 5**：`M1_FIX_B`、`M1_FIX_B_FIX`、`M1_FIX_B4`、`M1_FIX_B5`、`M1_FIX_功能补漏实施方案`

合计 4 + 2 + 4 + 7 + 5 = **22** ✓

---

## 三、Base 治理测试 × Head 实测对照（**本裁定单的核心证据**）

Base 的 `tests/test_merge_governance.py` 有 15 项测试，逐条对 Head 当前文件做静态比对：

| # | Base 测试 | Head 实测 | 判据 |
| --- | --- | --- | --- |
| 1 | `test_regeneration_never_deletes_after_requested_range` | **FAIL** | Head `api.py:411` 仍含 `attendance_date > %s` |
| 2 | `test_regeneration_has_no_commit_between_delete_and_rebuild` | 未核验 | 事务边界，需读全文判定 |
| 3 | `test_hr_management_endpoints_have_server_side_guards` | **FAIL** | `employee_management_data.py` 无任何 `_require_*`；`shift_management_data.py` 用的是 `_require_read/_require_write`，Base 断言的是 `_require_hr_read/_require_hr_write` |
| 4 | `test_exports_are_private` | **FAIL** | Head `export.py:115/416` 为 `"is_private": 0`，`roster_export.py:306` 同；两文件均无 `_require_export_permission` |
| 5 | `test_schedule_import_rejects_server_paths` | **FAIL** | `shift_management_data.py` 无「不允许通过 API 读取服务器任意文件路径」 |
| 6 | `test_rest_leave_is_one_ordered_scheduler_job` | **FAIL** | Head `hooks.py` 挂了 3 条并列函数，无 `sync_rest_leave_pipeline` |
| 7 | `test_runtime_sources_do_not_embed_employee_policy_memberships` | **FAIL** | `rule_lists.py` 含 **338** 个 8 位工号（Base 为 0）；`pairing/rotation/api/roster` 亦含 |
| 8 | `test_external_resource_ids_are_configuration_not_source_literals` | **FAIL** | `api.py` 含 `PwSXbltzha1uG1sr38hcQzMrnwb`；`rest_leave.py` 含 `XLD0bPiGXaP0JTsicHCcSLA4nlQ` |
| 9 | `test_external_writes_and_ai_are_default_off` | **FAIL** | Head `.env.example` 无 `HBOS_FEISHU_SYNC_ENABLED` / `HBOS_DELICLOUD_SYNC_ENABLED` / `HBOS_AI_ENABLED` / `HBOS_AI_ALLOW_PII`；`ai_review.py` 无 `_env_flag("HBOS_AI_ENABLED")` |
| 10 | `test_legacy_duplicate_engines_are_absent` | **FAIL** | 四个旧引擎在 Head 仍存在 |
| 11 | `test_delicloud_cursor_advances_only_after_successful_writes` | **FAIL** | Head `api.py` 无 `if all_recs and write_failed == 0:` |
| 12 | `test_dashboard_uses_authoritative_attendance_and_has_rbac` | **FAIL** | Head `dashboard_data.py` 无 `frappe.only_for`，且含 Base 明令禁止的 `daily_present`（3 处）与 `Zero-checkin absent detection`（1 处） |
| 13 | `test_dashboard_escapes_identity_fields_before_html` | **FAIL** | Head `hbos_attendance_dashboard.js` 无 `function escHtml(` |
| 14 | `test_clean_site_installs_required_apps_explicitly` | **FAIL** | Head `docker-compose.yml` 无 `bench --site $SITE_NAME install-app …` 序列 |
| 15 | `test_clean_site_declares_runtime_custom_fields` | **FAIL** | Head `setup.py` 声明的是另一组字段（`hbos_source_type` 等），**不含** `hbos_fixed_shift` / `hbos_terminal_sn` / `hbos_delicloud_id` / `hbos_employee_num` / `hbos_dept_name` / `hbos_check_type` |

**另有 Base `test_admin_nums_single_source.py` 的 `test_deprecated_duplicate_engines_are_removed` 与 `test_policy_registry_has_no_production_identity_literals` 同样失败。**

> ⚠ 上表为**静态比对**（按 Base 测试中的字符串 / 正则判据对 Head 文件取样），不是运行态测试结果。判据命令见 §8，可复现。

---

## 四、耦合冲突（**必须成组裁定，否则运行态报错**）

### 4.1 `hooks.py` ↔ 4 个被删除的旧引擎

- Head `hooks.py:32` **仍调度** `daily_feishu_sync.daily_sync_to_feishu`（`"0 10 * * *"`）。
- Base 已删除 `daily_feishu_sync.py` 并从 `hooks.py` 移除该调度项。
- 取 Head 的 `hooks.py` + Base 的删除结果 → **每天 10:00 `ImportError`**。

### 4.2 `hooks.py` ↔ `sync_rest_leave.py` 入口名

- Base 在 `hooks.py` 只挂 `sync_rest_leave.sync_rest_leave_pipeline`（定义于 Base `sync_rest_leave.py:505`）。
- Head 的 `sync_rest_leave.py` **没有** `sync_rest_leave_pipeline`，只有三个独立函数。
- 取 Base 的 `hooks.py` + Head 的 `sync_rest_leave.py` → **`AttributeError`**。

### 4.3 互相矛盾的治理测试

同一路径 `tests/test_admin_nums_single_source.py` 是 `add/add`，两边断言**方向相反**：

| | 断言 | 要求 |
| --- | --- | --- |
| **Base** | `test_deprecated_duplicate_engines_are_removed` | 旧引擎**必须不存在** |
| **Head** | `LEGACY = ("pair_checkins.py", "shift_matcher.py", "generate_attendance.py")` | 旧引擎**必须存在**且带废弃标记 |

**无论取哪个版本，另一侧的治理保证必然失效。** 这是政策冲突，只能由 Owner 选一条。

---

## 五、逐项裁定建议

> ✅ = 有硬证据支撑的强建议；⚠ = 需 Owner 产品裁定

### 5.1 配置层 → **取 Base，做加法**（✅）

| 文件 | 建议 | 依据 |
| --- | --- | --- |
| `.env.example` | **取 Base**，追加 Head 独有的 `PORTAL_PORT=8081` | Base 是严格超集：额外含 4 组 `HBOS_FEISHU_*_APP_TOKEN/_TABLE_ID`、4 个 enabled/pii 开关、`HBOS_AI_TIMEOUT`、`HBOS_OCR_*` |
| `.gitignore` | **取并集** | Base 含 `.release/`、`apps/hbos_portal/hbos_portal/public/portal/`、`apps/hb_lims_app/…/public/hbos-lims/`、`reports/P1/screenshots/`、`frontend/*/vite.config.js`、`*.tsbuildinfo`、`dist/`；Head 含 `apps/*/*/public/dist/`、`frontend/hbos-portal-web/vite.config.js`。**互不覆盖** |
| `.github/workflows/hbos-quality-gate.yml` | **取 Base** | Base 版多 `fetch-depth: 0` 与「固化 PR 变更文件清单」步骤 |
| `README.md` | 取 Base 骨架 + 合并 Head 的考勤工作台描述 | 均为台账类文本 |

### 5.2 编排层 `docker-compose.yml` → **取并集**（✅）

Base 有 OCR 服务与三 App 挂载及 clean-site 安装序列；Head 有 `portal` 服务（`${PORTAL_PORT:-8081}`）+ 8 处挂载 + 6 处 `PYTHONPATH`。**两边不重叠**，且 Base 的 `test_clean_site_installs_required_apps_explicitly` 要求保留其安装序列。

### 5.3 考勤 App → **以 Base 为骨架，重落 Head 的业务增量**（✅ 本 PR 的核心工时）

**不可整份取 Head**——会同时退回 §3 的 14 项加固。

**Head 侧必须重落的增量（Base 没有）**

1. 长值班配对放宽（设备动力部 24 小时，`5b23628`）——**业务行为修复，必须保留**
2. 调休模块一 / 二阶段（二阶段豁免接入 `rest_leave_apply.verified_rest_dates()`）
3. 月度汇总「AI 复核」与 4 个页内动作（`ai_review.py` 的业务逻辑）
4. M3 门户增量：`public/css/hbos_attendance.bundle.css`、`public/js/hbos_attendance.bundle.js`、`bump_page_cache.py`、`file_api.py`、`list_data.py`、`report_data.py`、3 个 page、3 个新 DocType、`portal/*`、`tests/test_portal_data_endpoints.py`
5. 部门看板与规则看板（`board_stats.py`、`department_board.py`、`rules_board.py`、`roster_export.py`、`schedule_import.py`）

**关于「月末丢一天」修复——建议采用 Base 的结构性修复为主**

- Base 已**直接删除**第二条 DELETE 谓词，`regenerate_attendance` 在结构上不可能删除请求范围之外的数据（有测试 `test_regeneration_never_deletes_after_requested_range` 守门）。
- Head 的 `REGENERATE_LOOKBACK_DAYS = 35` 是**规避**手段：把窗口拉长到不跨月空洞。
- **建议**：以 Base 的 bounded DELETE 为主修复；随后单独裁定是否仍需 35 天回溯（它改变的是**每日重算范围**，而非删除范围）。若保留，需在 Base 的测试断言下重新论证——**Base 的测试只禁 `attendance_date > %s`，不禁止更长的 BETWEEN 窗口**，故二者可共存，但取舍须明确写进文档。

**关于名单——建议采用 Base 的「名单进业务数据」**

- Head `rule_lists.py` 有 **338 个**工号字面量；Base 为 **0**，全部由 `HBOS Attendance Policy Assignment` 解析，种子经 `policy_migration.import_policy_seed()` 从**管理员控制的本地路径**导入且**明确要求不入库**。
- 我方 2026-09-24 的「名单单一来源收敛」（221→178）只把三份**收敛为一份硬编码**；Base 更进一步，把名单**移出了源码**。
- **建议**：采纳 Base 方案。本分支的 178 / 59 人名单应转化为 `HBOS Attendance Policy Assignment` 的业务数据行（私有种子），而非重新写回源码。
- ⚠ 这会影响 Head 依赖 `rule_lists.ADMIN_NUMS` 等常量的全部测试（如 `test_admin_nums_single_source.py`），需一并改造。

### 5.4 `apps/hbos_portal/**` → **取 Base**（✅）

- Base 83 / Head 37 / 公共路径 37 / **Head 独有 0** → Base 在路径层面是 Head 的**严格超集**。
- Base 独有 46 文件是完整账号体系（`auth/` 20+ 模块、账号 DocType、`api/csrf.py`、`api/diagnostics.py`）。
- ⚠ **需核对重复实现**：Head 新增的 `file_api.get_csrf_token`（考勤侧取 CSRF token）与 Base 的 `apps/hbos_portal/hbos_portal/api/csrf.py` **可能是同一问题的两个解**，取 Base 时应确认不留下两套 CSRF 通路。

### 5.5 `frontend/hbos-portal-web/**` → **需 Owner 产品裁定**（⚠）

| | Base | Head |
| --- | --- | --- |
| 文件数 | 103 | 69 |
| 公共路径 | 47 | 47 |
| 独有 | 56 | 22 |
| `package.json` | `0.4.0`，依赖含 `three` | `0.4.0`，依赖含 `dayjs` |

同版本号、依赖不同 → 同一产品的两条分化线。Base 覆盖 LIMS / twin / knowledge；Head 是考勤工作台线。

**建议**：以 Base 为基线，把 Head 独有的 22 个文件（考勤三视图、`attendanceNav.ts`、`AttendanceLayout.vue`、相关 service）逐个移植进去。**不要整体取 Head**——会删掉 Base 的多业务线页面入口。

### 5.6 台账与文档 `docs/**` → **人工合写**（⚠）

- `AI_CONTEXT.md` / `PROJECT_STATUS.md` / `CURRENT_MILESTONE.md` / `READING_GUIDE.md` 是状态台账：Base 记平台/门户线，Head 记考勤线，**同一项目的不同侧面**，需人工合写。
- Head 独有的里程碑文档与原型 HTML（`M1_FIX_设备动力部*`、`M3_*`、`M3_PORTAL_R1_*`、`M4_STOCK_R1_*`、两个原型）应**作为新增文件并入**。

### 5.7 `apps/hb_stock_app/**`（14 文件）→ **建议移出本 PR**（⚠）

属 M4-STOCK-R1 库存隔离线（台账记为 IN_PROGRESS、分支 `m4-stock-r1`），Base **不含**该目录。建议剥离，另开 PR，避免未完成的另一条线混入考勤交付。

### 5.8 移植分析追加：两项 Base 治理测试**覆盖不到**、但移植时必须带上的差异（2026-10-10 追加）

做移植增量盘点时，逐模块比对（`base → head`）额外发现两处差异。两者的共同点是：**Base 的 15 项治理测试都检查不到**——所以只看 §3 那张表会漏掉它们，必须单列。

#### (a) `attendance_notify.py`：Head 上没有飞书出站总开关

| | Base | Head |
| --- | --- | --- |
| `feishu_write_enabled()` 定义 | **有**（读 `HBOS_FEISHU_SYNC_ENABLED`） | **无** |
| `HBOS_FEISHU_SYNC_ENABLED` 引用 | **有** | **无** |
| `base → head` diff | —— | `+1 / -10`（净删 9 行，删掉的就是开关与其守卫） |

即 Head 的「每日 09:00 到岗卡片」在**全新环境里没有 kill switch**，会被直接发往飞书群。

**为什么 §3 那张表看不出来**：Base 的 `test_external_writes_and_ai_are_default_off` 只检查 `.env.example` 的键与 `ai_review.py` 的两行，**不检查 `attendance_notify.py`**。所以这条回归在 15 项测试里零覆盖。

**处置**：移植时保留 Base 的 `feishu_write_enabled()` 与其在 `send_daily_report` 中的守卫，**不要**照 Head 删掉。

#### (b) `rotation_schedule.py`：Head 仍留有 9 行真实员工姓名注释

| | Base | Head |
| --- | --- | --- |
| 行尾中文姓名注释（形如 `# 姓名`） | **0 行** | **9 行** |
| 8 位工号字面量（作为 `members` 字典的键） | 0 | 6 个去重（9 处） |

**为什么 §3 那张表看不出全貌**：Base 的 `test_runtime_sources_do_not_embed_employee_policy_memberships` 用两个正则判定，其中姓名用的是 `HB-[一-鿿]{2,}` —— **要求 `HB-` 前缀**。本文件的姓名注释是裸中文名、无该前缀，**不匹配**，故姓名这一半不会被该测试抓到（工号那一半会命中，所以该测试确实 FAIL，但失配原因只是工号）。

**与既有去标识化工作的关系**：`8b7d92f`（「去标识化——把本会话写入的真实员工姓名换为工号」）已处理 6 个文件，但其提交信息明确写了「**只处理本会话写入的文件**」——`rotation_schedule.py` **不在**那批里，因此一直没人动过它。

**处置**：移植时以 Base 的 `rotation_schedule.py` 为准（Base 走 `get_rotation_assignments()` 从业务数据取名单，文件内既无工号也无姓名），此问题随之消失。**但**：若最终决定保留 Head 版该文件，须先清掉这 9 行姓名注释。

> 这两条同时说明一件事：**§3 的 15 项测试是一道好闸门，但不是全量**。移植后仍应单独扫一遍 `HB-` 前缀之外的裸姓名与注释。

---

## 六、解决冲突后 CI 会跑什么（真正的验收闸门）

当前 PR **无任何 CI 结果**：GitHub 不对存在合并冲突的 PR 运行 `pull_request` 工作流（head SHA `8b7d92f` 的 check-run 数为 0）。冲突解决后，以下 Base 工作流会触发：

| 工作流 | 命中本 PR | 会做什么 |
| --- | --- | --- |
| `platform-integration-gate.yml` | ✅ **命中**（PR 到 `feature/hbos-portal-product`；路径含 `apps/hb_attendance_app/**`、`docker-compose.yml`、`.env.example`；**无 `head_ref` 限制**） | 三 App clean-site 安装 + `migrate` 冒烟、构建门户产物、`npm ci` + `test:unit` + `build:prod` |
| `hbos-portal-backend.yml` | ✅ 命中 | 门户后端闸门 |
| `hbos-portal-frontend.yml` | ✅ 命中 | 门户前端闸门 |
| `attendance-integration-gate.yml` | ❌ **跳过**（`if: github.head_ref == 'integration/pr9-attendance-clean'`） | —— |
| `portal-unified-account-release.yml` | ✅ 命中（路径含 `apps/hbos_portal/**`、`frontend/hbos-portal-web/**`） | 统一账号发布检查 |

> **只有把冲突真正解决、让 workflow 跑起来，才有可复现的验收证据。** 交付报告中的「测试 510 通过」来自仓库记录、未在运行态复跑，**不能替代**该闸门。

---

## 七、推荐裁定的事项（8 项；技术建议不自动等于 Owner 正式批准）

| # | 事项 | 选项 | 建议 |
| --- | --- | --- | --- |
| **1** | **解决路径** | (A) 选择性移植到 Base 骨架（非 merge）／(B) 在本分支解冲突后 merge／(C) 拆多个小 PR | **(A)**——依据是在 Base 的 15 项治理测试下 Head 失败 14 项，merge 无可行解 |
| **2** | **名单归属**（§5.3） | (A) 采纳 Base「名单进业务数据 + 私有种子」／(B) 保留 Head 的硬编码单一来源 | **(A)**；需同时裁定本分支 178 / 59 人名单如何转成业务数据行 |
| **3** | **月末丢失修复**（§5.3） | (A) 用 Base 的 bounded DELETE，弃用 35 天回溯／(B) 二者并存／(C) 保留 Head 方案 | **(A)** 或 **(B)**，不建议 (C) |
| **4** | **旧引擎政策**（§4.3） | (A) 采纳 Base「必须删除」／(B) 采纳 Head「保留 + 废弃标记」 | **(A)**，并删除 Head 版 `LEGACY` 断言 |
| **5** | **门户前端基线**（§5.5） | (A) Base 为基线 + 移植 Head 22 文件／(B) Head 为基线／(C) 暂不动前端 | **(A)**；需确认 Base 的 LIMS / twin 页面要保留 |
| **6** | **`apps/hb_stock_app` 归属**（§5.7） | (A) 移出本 PR／(B) 随本 PR 进入 Portal | **(A)** |
| **7** | **凭据与身份数据处置** | (A) 移植时改为 env，**不重写历史**，另定是否轮换 4 个 token／(B) 仅改当前版本／(C) 保持现状 | **(A)**。Owner 已确认本次属于测试人员数据，本轮不启动隐私清理；有效凭据、系统访问权限和生产写入仍需独立核验 |
| **8** | **考勤卡片出站开关**（§5.8a） | (A) 移植时保留 Base 的 `feishu_write_enabled()` + `HBOS_FEISHU_SYNC_ENABLED`（默认关闭）／(B) 采用 Head 的无开关形态 | **(A)**——这是真实飞书**出站**的总闸，缺它则新环境一上线就会往群里发卡片；且该回归**不在** Base 15 项测试覆盖内，只能靠本单发现 |

> **§7 第 7 项的补充（2026-10-10）**：身份数据残留不止那两份名单文档。`rotation_schedule.py` 另有 9 行裸姓名注释（详见 §5.8b），且**不在** Base 治理测试的姓名正则覆盖内。

---

## 八、附：证据命令（可复现）

```bash
# 冲突全量 109，分类计数 add/add 83 · content 22 · modify-delete 4
git merge-tree --write-tree origin/feature/hbos-portal-product HEAD | grep '^CONFLICT'

# Base 的 15 项治理测试（本裁定单 §3 对照表的来源）
git show origin/feature/hbos-portal-product:apps/hb_attendance_app/tests/test_merge_governance.py

# 关键失配的判据
git show HEAD:apps/hb_attendance_app/hb_attendance_app/hbos_attendance/rule_lists.py \
  | grep -oE "'[0-9]{8}'" | wc -l                                  # 338（Base 为 0）
git show HEAD:apps/hb_attendance_app/hb_attendance_app/hbos_attendance/api.py \
  | grep -n 'attendance_date > %s'                                  # 仍在（Base 已删）
git grep -nE 'BITABLE_APP_TOKEN = "' HEAD -- apps/hb_attendance_app # 硬编码字面量
git show HEAD:apps/hb_attendance_app/hb_attendance_app/hbos_attendance/report/月度考勤汇总/export.py \
  | grep -n 'is_private'                                            # 0（Base 为 1）

# 平台 App 双份体量：Base 83 · Head 37 · Head 独有 0
git ls-tree -r --name-only origin/feature/hbos-portal-product -- apps/hbos_portal | wc -l
git ls-tree -r --name-only HEAD -- apps/hbos_portal | wc -l

# §5.8a 出站总开关：Base 3 处命中 / Head 0 处
P=apps/hb_attendance_app/hb_attendance_app/hbos_attendance
git show origin/feature/hbos-portal-product:$P/attendance_notify.py \
  | grep -cE 'feishu_write_enabled|HBOS_FEISHU_SYNC_ENABLED'      # Base: 3
git show HEAD:$P/attendance_notify.py \
  | grep -cE 'feishu_write_enabled|HBOS_FEISHU_SYNC_ENABLED'      # Head: 0
git diff --numstat origin/feature/hbos-portal-product:$P/attendance_notify.py \
  HEAD:$P/attendance_notify.py                                     # +1  -10

# §5.8b 姓名注释：Head 9 行 / Base 0 行
git show HEAD:$P/rotation_schedule.py | grep -cE '# *[一-鿿]{2,3}$'   # Head: 9
git show origin/feature/hbos-portal-product:$P/rotation_schedule.py \
  | grep -cE '# *[一-鿿]{2,3}$'                                        # Base: 0
# 注意：Base 治理测试的姓名正则是 `HB-[一-鿿]{2,}`，**要求 HB- 前缀**，
# 故上面这 9 行裸姓名不会被该测试抓到。
git show origin/feature/hbos-portal-product:apps/hb_attendance_app/tests/test_merge_governance.py \
  | grep -n 'HB-'                                                    # 见姓名正则
```

---

## 九、交付边界声明

- 本裁定单**只做分析**：未修改任何被冲突的文件，未解决冲突，未 rebase，未 force push，未合并 PR。
- **未动运行态**：未执行 `migrate`、未重建容器、未写数据库、未跑 Frappe 测试套件（本机容器承载约 700 名员工的在跑数据）。
- **落点**：本文件于 2026-10-10 提交于分支 `docs/pr34-base-ruling`（基于 `feature/hbos-portal-product` 的 `ddbe9bf`），并由 **PR #35** 承载；该 PR 实际新增 **4 份文档**，此文件只是其中一份。
- **修订记录**：
  - 2026-10-10 初版 —— 冲突分类、15 项治理测试对照、三组耦合冲突、7 项裁定事项。
  - 2026-10-10 追加 §5.8 与 §7 第 8 项 —— 移植分析发现的两项 Base 测试覆盖不到的差异（出站总开关、姓名注释残留）。
  - 截至本轮最新远端复核，PR #34 仍 Open / mergeable=false；来源分支 `feature/hbos-attendance-console` 保留，作为选择性移植的来源。
  - 本节所引的 `HEAD` 均指 `feature/hbos-attendance-console` 的 `8b7d92f`。
