# LIMS P4-F6-6 样品 Provider 契约门禁

状态：**P4-F6-6 CONTRACT GATE / BLOCKED ON PROVIDER CONTRACT**
日期：2026-09-30
范围：`/hbos/lims/samples`、`/hbos/lims/samples/new`

## 1. 门禁结论

样品页面继续保留在 LIMS 同源前台路由中，但暂不开放为可用业务页：

- `/hbos/lims/samples`：保留稳定路由，当前由 `LimsPendingView` 承接；
- `/hbos/lims/samples/new`：保留登记入口，当前由 `LimsPendingView` 承接；
- 不显示固定样品数量、虚构状态或模拟登记表单；
- 不跳转 Frappe Desk、8080 或原生 LIMS 页面；
- 不新增前端直连 DocType，也不改变样品登记业务流程、权限或 SoD。

这不是页面实现失败，而是 Provider 数据与写入契约尚未形成可审查的单一能力边界。继续把当前占位页标记为“已实现”会让前端误造样品事实，因而本门禁保持关闭。

## 2. 已核对的现有能力

### 可复用但不能直接当作前端契约的领域服务

- `get_result_ledger(sample_type=None, material=None)` 已存在，受 LIMS 角色检查保护，返回样品、结果、修订和 COA 关联数据；
- `register_sample(...)` 已存在，受角色、规格、ERP Item / Batch、稳定性绑定和工作流校验保护；
- `ledger` Provider projection 已复用结果聚合，可作为样品台账只读数据的候选来源。

### 当前 Provider / 前端事实

- Provider manifest 和 capabilities 尚未声明 `samples`；
- Provider 入口尚无独立的样品列表 / 样品详情 / 登记 API 契约；
- 前端 `limsCapabilities` 虽保留 `samples` 类型，但 `IMPLEMENTED_PAGE_TARGETS` 不包含样品页，因此不会把占位页投影成可用能力；
- 样品列表与登记路由的 `meta.capability` 仍用于安全守卫，缺少能力时保持 pending；
- 现有 `ledger` 能力不等同于“样品登记”能力，不能用台账结果推导登记权限。

## 3. 开放前必须确认的契约

Provider Owner 与 LIMS 领域 Owner 需要逐项确认并写入可执行测试：

| 契约项 | 必须明确的内容 |
| --- | --- |
| 样品列表 / 台账 | 查询字段、分页、排序、样品状态、批次 / 物料 / 日期筛选、空值语义 |
| 样品详情 | 样品上下文、检验项目、规格快照、当前流程状态、关联结果和可安全展示的审计摘要 |
| 登记接口 | 独立 API 方法、请求 DTO、幂等键、草稿 / 提交语义、失败回填和会话过期行为 |
| 能力拆分 | 至少区分 `lims.samples.read` 与 `lims.samples.register`，不得用列表读取能力代替写入能力 |
| 权限与 SoD | 可见范围、登记角色、复核 / 批准冲突、跨部门边界和后端拒绝码 |
| 审计与签署 | 样品创建、修改、提交、撤回、关联批次的审计事件及签署要求 |
| 路由投影 | `/hbos/lims/samples`、`/hbos/lims/samples/new` 的 capability target、稳定 deep link 和返回上下文 |
| 状态与错误 | loading、empty、permission、session expired、冲突和重复提交的安全文案 |

前端开放条件是 Provider 返回能力与目标落点，并通过上述契约测试；仅有 Python 领域函数或已有台账数据，不足以开放样品前台。

## 4. 实现顺序与退出条件

1. Provider Owner 提供样品列表 / 详情 / 登记的响应样例和权限矩阵；
2. 补充 `manifest`、capability projection、stable route 与前后端契约测试；
3. 先实现只读样品列表与详情，完成四档响应式、中文状态和实验室上下文；
4. 单独审查登记写操作的 SoD、审计和签署，再决定是否开放 `/samples/new`；
5. 通过 Owner Review 后，才把 `samples` 加入 `IMPLEMENTED_PAGE_TARGETS` 和导航投影。

退出条件：样品读取与登记能力分别可测试、可授权、可回滚；前端不复制业务事实；未授权用户只能看到安全的无权限 / pending 状态；任何失败都不会回退到 8080。

## 5. Provider 契约草案（待 Owner 确认）

以下只是把现有 LIMS 领域字段整理成审查输入，不代表已经注册能力或冻结 API 名称。

### 只读列表 / 详情

建议 Provider 提供分页读取能力，前端只消费投影字段：

```json
{
  "rows": [
    {
      "sample_id": "HBOS-SMP-...",
      "material_name": "",
      "material_code": "",
      "batch_no": "",
      "sample_type": "",
      "sample_source": "",
      "specification": "",
      "spec_version": "",
      "priority": "",
      "status": "",
      "requestor": "",
      "received_date": "",
      "test_due_date": "",
      "oos_locked": false
    }
  ],
  "total": 0,
  "next_cursor": null,
  "scope_label": "",
  "generated_at": ""
}
```

最低查询参数建议为 `keyword`、`sample_type`、`material`、`status`、`limit`、`cursor`；详情响应再按权限补充检验项目、结果摘要、规格快照和安全审计摘要。`scope_label` 只表示后端已判定的可见范围，不允许前端自行推导。

### 登记写入

登记接口必须独立于列表读取能力，建议先冻结以下边界再实现表单：

- 请求必须有幂等键，并明确草稿 / 提交动作的区别；
- 返回 `sample_id`、当前状态、下一步动作和审计事件标识；
- 规格、物料、批次、稳定性绑定和工作流校验全部由 LIMS 领域服务执行；
- `FORBIDDEN`、`SESSION_EXPIRED`、`CONFLICT`、`VALIDATION_FAILED`、`RETRYABLE` 等错误码需有安全中文文案；
- 登记能力必须单独受 `lims.samples.register` 控制，不能因拥有 `lims.samples.read` 自动获得。

## 6. Owner 契约确认清单

请对每一项选择“通过 / 修改 / 否决”，并在备注中写明字段、角色或错误码调整。未完成前不开放 `samples` capability。

| # | 确认项 | 通过 | 修改 | 否决 | 备注 |
| --- | --- | :---: | :---: | :---: | --- |
| 1 | 样品列表字段、分页、筛选和空值语义 | ⬜ | ⬜ | ⬜ |  |
| 2 | 样品详情可见字段与结果摘要范围 | ⬜ | ⬜ | ⬜ |  |
| 3 | `lims.samples.read` 读取能力与可见范围 | ⬜ | ⬜ | ⬜ |  |
| 4 | `lims.samples.register` 登记能力与角色边界 | ⬜ | ⬜ | ⬜ |  |
| 5 | 登记 DTO、幂等键、草稿 / 提交语义 | ⬜ | ⬜ | ⬜ |  |
| 6 | SoD、电子签名和审计事件 | ⬜ | ⬜ | ⬜ |  |
| 7 | 错误码、会话过期和冲突处理 | ⬜ | ⬜ | ⬜ |  |
| 8 | 稳定路由、返回上下文和 capability target | ⬜ | ⬜ | ⬜ |  |

## 7. 当前下一步

本轮已新增 `apps/hb_lims_app/tests/test_portal_samples_gate.py`，回归确认 manifest 不发布 `samples`，Provider 不暴露未审查的样品适配器；相关 28 项 Provider / 门禁测试通过。在真实 Frappe Session 可用前，不修改样品业务 API，不新增样品假数据。下一项工程动作是补齐 Provider 契约样例与测试；在此之前继续完成真实 Session 复核、四档持久化截图和 Owner Review。
