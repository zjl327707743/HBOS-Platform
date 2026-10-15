# LIMS P4-F6-5 受控结果台账与审计只读视图实现记录

状态：**P4-F6-5 LEDGER / AUDIT READ-ONLY V1 IMPLEMENTED / REAL INTEGRATION PENDING**
日期：2026-09-30

## 1. 本轮范围

按 P4-F6-5 的第一项顺序，本轮将两类质量追溯页面接入 Portal 同源 Vue SPA：

- `/hbos/lims/ledger`：受控结果台账，按样品批次查看检验项目、冻结限度、结果、判定和记录状态；
- `/hbos/lims/audit`：合规审计追踪，只读查看提交、复核、批准、修订、OOS 和越权 / SoD 事件。

页面沿用已验收的 LIMS Shell、中文优先视觉和状态 token，不开放导出、编辑或删除动作。

## 2. Provider 与权限边界

- 新增 `ledger`、`audit` Provider capability 以及对应 Portal API；
- `ledger` 复用 LIMS `get_result_ledger()` 的权限守卫与服务端派生字段；
- `audit` 复用 LIMS `get_audit_log()` / `get_audit_targets()`，保留对象、事件、字段前后值、原因和记录指纹；
- Portal Bootstrap 透传应用的语义访问能力；审计入口只有在 `lims.audit.read` 能力存在时渲染；
- 检验员仍可查看受控结果台账，但无审计读取能力时不会看到审计导航；后端权限拒绝仍是最终事实来源。

## 3. 前端交互

- 台账支持关键词、记录状态、判定筛选，左侧样品批次列表与右侧结果明细联动；
- 结果项目可回到 Result Entry 详情，限度、判定和签署链保持只读；
- 审计页支持关键词、事件类型、对象筛选，事件详情在侧边抽屉展示；
- 两页均提供加载、空、错误和继续加载状态，移动端收敛为单列布局；
- 页面不复制原生 Frappe Desk 页面，也不在前端重新计算判定或权限。

## 4. 验证结果

- `npm run build`：通过；
- `bash scripts/portal/lims_shell_contract.sh`：`LIMS SHELL CONTRACT PASS`；
- LIMS 契约与服务回归：`154 passed, 1 skipped`；
- 新增台账 / 审计投影测试：通过；
- `git diff --check`：通过；
- 本机未具备可用 Docker / Frappe 运行环境，尚未执行真实账号下的台账、审计权限和页面联调。

## 5. 下一步

恢复真实 Frappe 会话后，核对 Analyst、Reviewer、LIMS QA、Manager、System Manager 五类访问边界和分页深链；再进入 P4-F6-5 第二项“检验报告（COA）与质量标准只读视图”。
