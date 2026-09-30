# LIMS P4-F6-2 Dashboard V2 实现记录

状态：**P4-F6-2 DASHBOARD V2 IMPLEMENTED / REAL INTEGRATION PENDING**
日期：2026-09-29
范围：`frontend/hbos-portal-web` 的 LIMS Dashboard V2 只读工作台

## 1. 本轮交付

- 真实 Frappe 模式的 `/hbos/lims` 已使用 `LimsDashboardView`，Mock 模式继续保留已验收的静态原型首页。
- 四项 KPI 从 Portal Provider summary 投影，保留 `scopeLabel`、生成时间、状态和稳定深链。
- Portal Store 保留全量摘要，Portal 首页的跨应用摘要裁剪不会截断 LIMS 四项 KPI。
- “接下来要做”从 Portal Provider task DTO 投影，展示领域状态、动作、截止时间、优先级和稳定深链。
- 增加检验流程条：任务分配 → 开展检验 → 提交结果 → 复核 → 批准。
- 增加加载、空数据、错误和刷新状态；错误文案保持用户可读，不暴露 Frappe 方法名。
- 风险卡、近期样品、检验组分布暂以“数据待接入”占位，不显示固定数字或模拟业务事实。
- Dashboard 使用中文优先、LIMS emerald / cyan、双品牌 Shell、响应式任务卡和 44×44 刷新按钮。

## 2. 数据边界

| 页面内容 | 当前来源 | 状态 |
| --- | --- | --- |
| 待检 / 检验中 / 待复核 / 待发布 COA | LIMS Provider summary | 已接入 |
| 当前权限范围 | Provider `scope_label` | 已接入 |
| 任务列表与领域状态 | LIMS Provider tasks | 已接入 |
| 超期 / OOS 风险卡 | Dashboard 专用 Provider 字段 | 待接入 |
| 近期样品 / 检验组分布 | Dashboard 专用 Provider 字段 | 待接入 |

前端不计算权限范围、不复制 DocType 查询、不改变业务状态，也不开放结果录入、复核、批准和 COA 发布写操作。

## 3. 验证

```text
npm run build
→ vue-tsc -b + vite build PASS

bash scripts/portal/lims_shell_contract.sh
→ LIMS SHELL CONTRACT PASS

Provider / LIMS contract tests
→ 150 passed, 1 skipped
```

真实 Frappe 集成仍待 Docker/Frappe 环境恢复；当前没有伪造 Dashboard 的真实数据结果。

## 4. 下一步

恢复真实运行环境后，执行 Provider 集成检查，核对四项 KPI、scopeLabel、任务深链和超大任务集分页；随后接入 Dashboard 专用风险、近期样品和分布字段，再进入 Task Board V1。
