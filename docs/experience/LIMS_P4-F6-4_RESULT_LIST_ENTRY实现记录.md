# LIMS P4-F6-4 Result List / Result Entry 实现记录

状态：**P4-F6-4 RESULT LIST / ENTRY V1 IMPLEMENTED / REAL INTEGRATION PENDING**
日期：2026-09-30

## 1. 本轮范围

本轮把第二张 LIMS 前台操作页接入 Portal 同源 Vue SPA：

- `/hbos/lims/results`：检验结果列表，支持关键词、状态、判定筛选和稳定深链；
- `/hbos/lims/results/:resultId`：结果录入详情页；
- `/hbos/lims/results/:resultId/review`：复核入口，复用同一结果上下文和签署链视图。

页面保持中文优先，结果值、冻结限度、样品上下文、签署链和修订记录集中展示；移动端改为单列表单和底部动作区，适配检验员的高频录入路径。

## 2. Provider 与领域边界

- 新增 `results` Provider capability 与 `hbos_portal.api.results.get_results` 查询入口；
- LIMS Provider 复用已有 `lims_service.get_result_ledger()` 的权限和数据边界，投影为 Result List / Result Entry DTO；
- 列表、详情、修订记录和签署链均为只读投影，状态迁移、SoD、审计和签署规则仍由 LIMS 领域服务负责；
- 前台不再跳转 Frappe Desk，也不把原型内存状态当作生产事实。

## 3. Result Entry 写入规则

- 只有真实 Frappe 数据源且结果处于 `草稿` 时开放录入字段；Mock 模式明确显示只读提示；
- `提交结果`、`复核通过`、`批准` 分别调用已有领域服务 `submit_result`、`review_result`、`approve_result`；
- 代理提交要求填写代理原因，前端仅传递意图，最终操作者、权限、状态和审计由后端确认；
- 写入失败保留当前表单内容并显示错误，用户可以修正后重试；Portal 客户端已为非 GET 请求补齐 Frappe CSRF token 获取和请求头。

## 4. 共享能力与视觉

- 结果列表沿用 LIMS Shell、双品牌页头、状态 token、加载 / 空 / 错误态和稳定路由守卫；
- 结果页桌面使用上下文 + 表单 / 证据双栏结构，768px 以下堆叠，390px 使用单列表单和底部动作栏；
- `limits_type`、`limits_text`、`significant_digits` 等冻结标准快照随结果展示，不在前端重新推导判定。

## 5. 验证结果

- `npm run build`：通过；
- `bash scripts/portal/lims_shell_contract.sh`：`LIMS SHELL CONTRACT PASS`；
- LIMS 契约与服务回归：`152 passed, 1 skipped`；
- `git diff --check`：通过；
- 本机未具备可用 Docker / Frappe 运行环境，尚未执行真实会话下的 API 联调和写入操作。

## 6. 下一步

恢复真实 Frappe 会话后，按隔离预览核对结果列表分页、详情权限、代理提交、SoD、审计和状态回填；再根据后端契约补充风险、样品分布和仪器结果字段，不在本轮扩大业务流程范围。
