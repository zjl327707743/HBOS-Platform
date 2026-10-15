# LIMS P4-F6-5 留样工作台实现记录

状态：**已完成 Portal 只读工作台 V1 / 真实集成待运行态验收**
日期：2026-09-30

## 本轮交付

- 新增 `retains` Portal capability，并保持 `/hbos/lims/*` 同源路由，不跳转 Frappe Desk。
- 新增留样领域只读投影：留样登记与台账、留样产品规则、观察计划与年度完整性、使用申请、处理申请和工作台摘要。
- 观察、使用、处理数据继续调用 `retention_service.py` 的权限保护方法；Portal 不复制状态机、库存写路径、审批签署或 SoD 规则。
- 新增 `LimsRetentionWorkbenchView.vue`，以中文为主，提供工作台、登记与台账、产品规则、观察任务、使用申请、处理申请六个分区。
- 详情抽屉为只读，并明确登记、库存调整、观察录入、审批和处理动作仍由既有领域服务负责；本轮不新增高风险写按钮。
- 桌面侧栏、移动抽屉、路由和 capability projection 已同步，Mock / Frappe 两种模式均只开放已实现目标。

## 业务边界

| Portal 可见内容 | 仍由 LIMS 领域服务负责 |
| --- | --- |
| 批次、产品、结存、储存、观察和申请状态的只读展示 | 留样登记、库存调整、观察选取 / 录入 / 审核 |
| 观察计划、年度 N/3 完整性、使用 / 处理申请链路 | 使用申请创建、库存确认、QC / QA / QM 审批、取样执行 |
| 临期、待观察、待审批工作台提醒 | 销毁、续留、处理、监督、取消和审计写入 |

## 契约与验证

- `scripts/portal/lims_shell_contract.sh`：通过。
- `npm run build`：通过；仅保留既有 Vite 大包警告。
- `git diff --check`：通过。
- 新增 `test_portal_retention_projection.py`；本机没有可用的 Frappe / pytest 运行环境，已完成 AST 解析，真实 Frappe 集成测试待工作台恢复后执行。

## 下一步

进入留样运行态验收：使用真实 Frappe Session 核对各角色可见范围、空态 / 无权限态和状态数量；随后再决定是否为观察录入、使用申请和处理申请补充受 capability 与 SoD 约束的 Portal 操作入口。
