# LIMS P4-F6-0 Provider / 路由契约核验记录

状态：**P4-F6-0 PROVIDER ADAPTER IMPLEMENTED / REAL INTEGRATION PENDING**
日期：2026-09-29
范围：LIMS Provider、稳定路由、前台 capability 前置核验

## 1. 核验结论

P4-F6-0 已完成第二轮代码级契约确认。

已通过的部分：

- Provider manifest、访问上下文、summary / tasks / search 基础投影可以在当前 Python 测试环境导入并执行；
- `/hbos/lims/*` 稳定路由与当前 `/hbos-lims/*` 原生路径的正向映射通过；
- `/ledger`、`/samples/new` 别名及 Native deep link 回投通过；
- 路径协议、主机名、片段、反斜杠和 traversal 路径会被拒绝；
- Guest、无关角色、业务角色和 Administrator 的进入边界已有可执行断言；
- 当前 Provider 仍保持只读能力，没有前端绕过 LIMS 权限或 SoD 的写入口。

已确认的领域语义：

- “待检”对应普通检验任务 `HBOS Sample Task.status = 已分配`，执行动作是 `start_task`；
- “检验中”对应任务已进入 `检验中` 且结果尚未提交，结果草稿动作是 `submit_result`；
- “待复核”对应 `HBOS Test Result.result_status = 已提交`，执行动作是 `review_result`；
- “待发布 COA”对应 `HBOS COA.report_status = 已审核`，执行动作是 `publish_coa`，发布线为 LIMS QA / LIMS Manager；
- 七项任务状态和 OOS 候选来自 `workflow_contract.py`，不是前端自定义枚举；
- 结果复核、结果批准和 COA 发布的职责分离、签署和审计边界已有业务服务与契约测试支撑。

已完成的 Provider 适配：

- summary 已按四项确认语义投影 KPI、只读 `scope_label` 和稳定深链；
- `my_tasks()` 已支持 `view=my-testing|my-review|my-approval`、状态、优先级和关键词筛选；
- 任务投影已保留领域 `status`、`action`、`action_label` 和任务视图；
- COA `publish_coa` 已作为独立质量审批任务加入 `my-approval`；
- 通用 Portal tasks API 和前端任务 DTO 已透传这些字段。

尚未完成的集成项：

- summary 尚未扩展风险卡、近期样品、检验组分布、状态分布和最近同步时间的 Dashboard 专用字段；
- 当前环境尚未启动真实 Frappe bench，Provider 集成检查尚未取得真实会话证据；
- 任务查询暂按 Provider 现有 200 条权限感知待办上限聚合，超大数据量分页需在真实站点验证。

因此 Dashboard KPI 和 Task Board 的 Provider 数据契约已具备实现落点；在真实 Frappe 集成检查通过前，仍不开放生产入口和 Result Entry 写操作。

## 2. 当前代码契约快照

### 2.1 Manifest

当前 manifest：

```json
{
  "contract_version": 1,
  "id": "lims",
  "route": "/hbos/lims",
  "migration_mode": "native",
  "capabilities": ["summary", "tasks", "search"]
}
```

`summary`、`tasks`、`search` 是 Provider 数据能力；它们不代表前台页面已经具备可用落点。前端继续通过 `limsCapabilities` 单一投影控制入口显示。

### 2.2 Summary

当前 `project_todo_summary()` 输出四项旧指标；已确认的目标投影如下：

| 当前 ID | 当前中文标签 | 数据来源 | 设计目标 | 结论 |
| --- | --- | --- | --- | --- |
| `my_testing` | 待检 | `HBOS Sample Task.status = 已分配` / `start_task` | 待检 | 已确认，已完成 Provider 投影 |
| `in_testing` | 检验中 | `HBOS Sample Task.status = 检验中`，结果未提交 | 检验中 | 已确认，已完成 Provider 投影 |
| `my_review` | 待复核 | `HBOS Test Result.result_status = 已提交` / `review_result` | 待复核 | 已确认，已完成 Provider 投影 |
| `coa_publish` | 待发布 COA | `HBOS COA.report_status = 已审核` / `publish_coa` | 待发布 COA | 已确认，已完成 Provider 投影 |

Provider 适配已使用上述字段和动作，不再把旧的待办总数改名为四项 KPI。权限范围、空值和深链筛选已由离线契约测试覆盖，真实会话仍需集成验证。

### 2.3 Tasks

当前任务数据已包含 `action`、`action_label`、`status`、`priority`、`due_at`、`overdue`、`assignment_type` 和稳定深链；领域状态枚举由 `workflow_contract.py` 确认。

当前 `get_provider().my_tasks()` 已接受 `limit`、`cursor`、`view`、`status`、`priority` 和 `keyword`。映射为：`my-testing` → `start_task / submit_result`，`my-review` → `review_result`，`my-approval` → `approve_result / publish_coa`；查询先在 LIMS 权限上下文内聚合，再由 Provider 分页。

### 2.4 Routes

已核验的稳定映射：

| 稳定路径 | 当前原生路径 | 结果 |
| --- | --- | --- |
| `/hbos/lims` | `/hbos-lims/dashboard` | 通过 |
| `/hbos/lims/tasks` | `/hbos-lims/tasks` | 通过 |
| `/hbos/lims/ledger` | `/hbos-lims/results/ledger` | 通过 |
| `/hbos/lims/samples/new` | `/hbos-lims/samples` | 通过 |
| `/hbos-lims/results/ledger` | `/hbos/lims/ledger`（回投） | 通过 |
| `/hbos-lims/samples` | `/hbos/lims/samples`（回投） | 通过 |

查询参数会被保留并重新编码；外部主机、片段和 traversal 路径会被拒绝。

## 3. 已执行验证

```text
PYTHONPATH=apps/hb_lims_app python3 -m unittest \\
  apps/hb_lims_app/tests/test_portal_provider_contract.py
→ Ran 23 tests ... OK

PYTHONPATH=apps/hb_lims_app python3 -m pytest -q \\
  test_portal_provider_contract.py test_portal_task_projection.py \\
  test_todo_contract.py test_workflow_contract.py test_coa_contract.py \\
  test_lims_service_contract.py test_lims_guards_contract.py
→ 150 passed, 1 skipped

bash scripts/portal/lims_shell_contract.sh
→ LIMS SHELL CONTRACT PASS

node --check docs/experience/prototypes/lims-p4-f2-v2/app.js
node --check docs/experience/prototypes/lims-p4-f2-v2/modules.js
→ PASS
```

当前环境没有启动 Frappe bench，因此没有伪造集成环境结果；需要在真实站点运行 `hb_lims_app.hbos_lims.portal.integration_checks.run` 作为下一轮 Provider 验证。

本轮尝试执行 `scripts/portal/start_local_workspace.sh` 进入真实集成检查，但当前执行环境未安装或未暴露 `docker` 命令（`docker: command not found`），因此没有启动服务、没有执行站点写入，也没有生成真实会话结果。

## 4. P4-F6-0 退出条件与待确认项

下一步退出条件：

1. 在真实 Frappe 会话下运行 Provider 集成检查；
2. 将 Dashboard 风险、近期样品、分布和最近同步时间拆成受控只读字段；
3. 保持结果录入、复核、批准、样品登记的写 API、SoD、签署和审计边界不变；
4. 已按 Owner 指令先进入 P4-F6-1 的最小 Shell 实现（双品牌、错误态、页面目标能力门控和路由守卫）；真实集成检查通过后，才能继续开放 Dashboard / Task Board 等业务页面。
