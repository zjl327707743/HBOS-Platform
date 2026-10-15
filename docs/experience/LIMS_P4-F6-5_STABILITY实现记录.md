# LIMS P4-F6-5 稳定性工作台实现记录

状态：**P4-F6-5 STABILITY READ-ONLY WORKBENCH V1 IMPLEMENTED / RUNTIME PREVIEW VERIFIED / REAL INTEGRATION PENDING**

日期：2026-09-30

## 本轮交付

- 新增稳定性 Portal 投影与 API：工作台、取样与检测计划、样品入箱台账、稳定性结果、趋势数据均复用 `stability_service` 的角色校验入口。
- 新增 `stability` Provider capability、Manifest、协议和集成检查契约。
- 新增同源路由 `/hbos/lims/stability/*`，不再跳转 Frappe Desk。
- 新增中文优先的 `LimsStabilityWorkbenchView`：
  - 工作台 KPI、待处理时间点、执行进度、稳定性室与检验项目概况；
  - 计划日期链、储存条件、稳定性室、逾期派生和时间点详情；
  - 样品批次、入箱位置、结存与状态；
  - 结果值、规格限、版本、显著变化和 OOS / OOT 提示；
  - 产品 / 检验项目 / 条件趋势序列、规格限和 R² 文本摘要。
- 桌面侧栏与移动导航增加稳定性工作台及四个只读子入口。
- Portal 根 `a-config-provider` 统一使用中文 locale，避免首页和业务表格的 Ant Design 默认英文空态。

## 安全与边界

- 所有真实数据由 `stability_service` 提供，未在 Portal 适配层直接读库或复制权限逻辑。
- 本轮不开放生成时间点、完成取样、登记结果、复核批准、延期审批、环境设备维护等写操作。
- 趋势图仅接受产品和检验项目同时选定后请求；只展示当前版本、已批准结果，统计控制限仍显示为待质量部门确认。
- Mock 数据仅用于界面开发，真实模式缺少 capability 或会话时由现有 Portal 守卫处理。

## 验证

- `npm run build`：通过（仅保留既有大 chunk 警告）。
- `bash scripts/portal/lims_shell_contract.sh`：通过。
- `PYTHONPATH=. python3 -m unittest tests.test_portal_stability_projection tests.test_portal_provider_contract`：25 项通过。
- `git diff --check`：通过。
- 稳定性 Mock Vite 运行态已逐页核验，记录见 [`LIMS_P4-F6-5_STABILITY运行态验收记录.md`](./LIMS_P4-F6-5_STABILITY运行态验收记录.md)。
- 18 条已实现 LIMS 同源路由已完成 Mock 回归；样品登记 / 样品台账仍按 capability 门禁保持待设计，不补造 Provider 数据。
- 稳定性领域的真实 Frappe 运行态、权限账号矩阵和四档持久化截图仍待本地工作台恢复后验收；Mock 运行态已验证结果详情只读抽屉。当前本机会话没有 Docker CLI，8080 Frappe 服务未监听。
