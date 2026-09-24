# M2-R8K 我的待办身份绑定

## 状态

**REVIEWING / 已完成审查修复与真实 Frappe 冒烟，待 Owner 测试路径验收**（2026-09-23）。

本轮已完成本地代码实现、审查修复、契约测试和生产构建验证。2026-09-23 生产页面实测已可访问「我的待办」，其既有发布来源未在本次侧栏发布中核定；本次授权仅同步「最近访问」整块移除的前端资源，不代表 R8K 全功能验收或后端重新发布。

### 侧栏发布记录（2026-09-23）

- 移除「最近访问」整块及其专属数据、状态、样式，保留其他侧栏分组与入口；代码提交 `fbb1aee`。
- 生产静态资源备份：`【内部备份标识已省略】`；新构建先同步哈希资源、最后切换 `index.html`，生产与本地构建文件 SHA-256 **87/87 一致**。保留 3 个旧哈希资源以兼容已打开页面。
- 生产浏览器复核：不再显示「最近访问」；「我的待办」角标与 30 条列表正常，五个分组可展开，留样工作台可导航。仅前端静态资源更新，未执行后端迁移或服务重启。

### 审查修复记录（2026-09-22）

- 修复 Frappe 身份 API 调用：统一使用 `frappe.utils.get_fullname` 与 `frappe.utils.today`。
- 无来源单据读权限时按不可见记录处理；稳定性子表改为先逐条校验父单读权限，再读取已授权父单的子表行，避免 `get_list` 直接读取无权限子表。
- 稳定性「录入结果」按稳定性项目粒度扣除已被业务样品覆盖的项目；检验结果查询补取 `reviewer`，恢复检验业务批准动作的 SoD 排除。
- `due_at` 统一序列化为 ISO 字符串，删除稳定性覆盖计算死代码。
- 第一阶段仍只覆盖检验 / 稳定性 / 留样；前端隐藏尚未有规则来源的「质量 / 合规」筛选，避免展示恒为 0 的选项。
- 待办页补齐首次加载失败态、状态 / 优先级筛选、责任角色展示与下拉即时刷新；动作失败不再由前端重复弹错。
- 清理任务看板测试账号与测试检验组默认值；2026-09-23 按 Owner 要求移除侧栏「最近访问」整块及其专属数据、状态和样式。

**已知边界（第一阶段不覆盖，非遗漏）**：`TODO_RULES` 中没有变更（Change）模块规则，因此 `LIMS QA Manager` 与 `LIMS QP` 当前看到的待办数为 0——而「一般变更批准」是 QA 经理专属、「重大变更批准」是 QP 专属，这三类角色的实际工作量尚未进入待办。与方案第一阶段「只覆盖检验 / 稳定性 / 留样」一致，需在第二阶段补 Change 规则；在此之前不应把「待办为 0」理解为「没有待办工作」。

真实 Frappe 会话冒烟已落地并可执行：`HBOS_FRAPPE_SMOKE=1 FRAPPE_SITE=frontend <容器 venv>/bin/python -m pytest apps/hb_lims_app/tests/test_todo_runtime_smoke.py -q`，已接入 `deploy_lims_fix.sh` 的 **7d/8** 步骤（前置要求：backend venv 已装 `pytest`；缺失时脚本会明确报错而不是静默跳过）。三轮审查发现的 3 个纯运行期致命缺陷（`frappe.get_fullname` 不存在、`get_list` 读子表必然无权限、QAM/QP 无业务 DocType 读权限）正是离线桩测试无法覆盖、由该冒烟暴露的。

本轮实现会话所在宿主机没有 `docker` / `bench`，Python 环境也无法导入 `frappe`，因此**离线桩测试无法覆盖纯运行期问题**。真实 Frappe 会话冒烟已由具备容器与 bench 的审查会话补做：**修复前暴露 3 个致命阻断**（`frappe.get_fullname` 不存在 → 所有待办接口 `AttributeError`；`get_list` 读稳定性子表必然 `PermissionError`；`LIMS QA Manager` / `LIMS QP` 无业务 DocType 读权限 → 直接崩溃），修复后**全部角色实测通过**（摘要与列表口径一致、跨模块收敛按项目粒度生效、已同步结果不再产生待办）。

## 目标与范围

将海滨 LIMS 侧栏「我的待办」改造成基于 Frappe 当前会话身份的跨模块待办中心，合并展示：

- 「指派给我」：来源单据人员字段等于 `frappe.session.user`；
- 「我的角色待处理」：当前会话业务角色拥有当前动作权限且未被明确指派给其他用户。

本轮覆盖检验业务、稳定性、留样三类既有事实源，不创建持久化待办 DocType，不改变原业务状态机和动作权限。

## 交付内容

- 新增纯数据规则 `todo_contract.py` 与聚合服务 `todo_service.py`：当前会话身份、Administrator 特判、项目粒度跨模块收敛、派生稳定性结果排除、统一字段和摘要缓存。
- 新增 Vue 待办 API、Pinia store、`/my-todos` 页面和侧栏个人摘要角标；保留稳定性子项全局角标，不再叠加稳定性分组汇总角标。
- 补齐六类来源深链：检验任务、稳定性取样、稳定性结果、留样观察、留样使用、留样处理；`/tasks` 深链带 `scope=mine`。
- 直接动作统一委托原业务 API；成功和失败均刷新待办，失败不做乐观删除；路由型动作进入已有业务页面。
- 页面仅在 `/my-todos` 前台可见时每 60 秒轮询，登出和 401 清理个人待办状态。

## 验证证据

- 前端单元测试：7 passed。
- 前端待办契约测试：6 passed。
- 后端 LIMS 测试集：`pytest` 395 passed、1 skipped；离线门禁 `PYTHONPATH=apps/hb_lims_app python3 -m unittest discover -s apps/hb_lims_app/tests` **335 tests OK（skipped=1）**。两个 runner 都把真实 Frappe 冒烟识别为「跳过」而非失败（该冒烟模块不得在导入期调用 `pytest.importorskip`，否则 unittest loader 会按 import 错误处理、把离线门禁弄红）。
- `npm run build`：通过；仅保留既有 Vite 大 chunk 警告。
- 2026-09-23 侧栏回归：前端单测 7/7、`npm run build` 通过；本地浏览器确认「最近访问」不再渲染，五个模块分组展开/收起正常，检验、质量、留样、稳定性、合规及「我的待办」入口均可导航到对应页面。审计追踪页的报表权限提示仍由当前账号权限决定。
- 真实 Frappe 冒烟：**已执行并通过**——容器内 `HBOS_FRAPPE_SMOKE=1 FRAPPE_SITE=frontend /home/frappe/frappe-bench/env/bin/python -m pytest /home/frappe/frappe-bench/apps/hb_lims_app/tests/test_todo_runtime_smoke.py -q` → `1 passed`；另以非 Administrator 真实用户逐角色调用 `get_my_todos` / `get_my_todo_summary` 实测（Analyst 30 / Reviewer 22 / Manager 43 / QAM 0 / QP 0 / 无角色 0，摘要与列表总数逐一致，`due_at` 为 ISO 字符串）。
- 冒烟已接入 `deploy_lims_fix.sh` **7d/8** 步骤（backend venv 缺 `pytest` 时脚本显式报错并给出安装命令，不静默跳过）。
- 关键提交：`1c55a14`（深链与原业务动作）、`3fe0e05`（实施台账）。

## Owner 验收重点

1. 使用不同 Analyst / Reviewer / Manager 身份，确认两类归属标签、个人角标和列表过滤口径。
2. 检查 Administrator 只看到明确指派给自己的记录，不展开全部业务角色待办。
3. 验证稳定性已同步结果不产生待办；稳定性样品的已映射项目收敛到稳定性线，未映射项目仍出现在检验业务待办。
4. 从六类待办点击进入来源页，确认目标记录定位；目标已不存在时显示来源编号提示且不报空对象错误。
5. 在待办页执行直接动作，确认仍由原业务 API 做权限/状态校验，成功后待办刷新，失败不伪造完成。
