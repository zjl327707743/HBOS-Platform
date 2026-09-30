# LIMS P4-F6-3 Task Board V1 实现记录

状态：**P4-F6-3 TASK BOARD V1 IMPLEMENTED / REAL INTEGRATION PENDING**
日期：2026-09-30
范围：`frontend/hbos-portal-web` 的 LIMS 只读任务看板

## 1. 本轮交付

- `/hbos/lims/tasks` 已接入 `LimsTaskBoardView`，真实模式和 Mock 模式均使用同源前台路由。
- 支持“我的待检 / 我的复核 / 我的审批”三种 `view` 视图，并将视图、状态、优先级、截止时间和关键词同步到 URL。
- 真实模式把筛选条件传给 Portal Provider 的 `tasks` 契约；Mock 模式保留静态任务作为原型预览，并按动作映射视图。
- 桌面端采用任务表行，移动端降级为单列任务卡；七项状态语义使用统一状态标签和数量摘要。
- 提供加载、无匹配、无任务、错误和重试状态；没有任务时不显示推测数字。
- 任务行支持 Tab 聚焦、Enter 打开稳定深链、上下方向键移动焦点。
- 看板不直接写入任务状态，“开始检验 / 提交结果 / 复核 / 批准”等动作只作为 Provider 返回的下一步文字；业务写操作留到 Result Entry 阶段。

## 2. 数据边界

| 内容 | 来源 | 状态 |
| --- | --- | --- |
| 角色视图 | URL `view` + LIMS Provider `view` | 已接入 |
| 任务状态 / 优先级 / 截止时间 | LIMS Provider tasks DTO | 已接入 |
| 搜索 / 状态 / 优先级 | Provider `keyword` / `status` / `priority` | 已接入 |
| 风险判断、权限范围、状态迁移 | LIMS 后端 | 前端不计算 |
| 任务动作执行 | Result Entry / 后端业务服务 | 本轮不开放 |

前端只负责筛选和导航，不复制待办查询、不修改业务状态、不绕过 SoD 或签署校验。

## 3. 验证

```text
npm run build
→ vue-tsc -b + vite build PASS

bash scripts/portal/lims_shell_contract.sh
→ LIMS SHELL CONTRACT PASS

Provider / LIMS contract tests
→ 150 passed, 1 skipped
```

真实 Frappe 集成仍待运行环境恢复；本轮没有伪造真实任务结果。

## 4. 下一步

恢复真实 Frappe 会话后，核对三种 `view`、筛选参数、分页游标、稳定深链和无权限返回；随后进入 P4-F6-4 Result List / Result Entry，先完成真实 API、权限、SoD、审计和状态迁移契约。
