# M2-R8I 稳定性前端接入：结果与趋势、报告与有效期、变更·稳定性室·设备

> 状态：**DONE / 待 Owner 审查**（`vue-tsc` 0 错误、`npm run build` 成功、浏览器真实会话读写全链 + 角色显隐 + 375px 三页无溢出）
>
> 轮次：M2-R8I（R8E 拆轮表中的 R8D 前端接入部分，实际以前端接入轮交付），工作分支 `m2-r8`
>
> 上游：M2-R8C（结果 + 报告后端）、M2-R8D（变更 + 稳定性室 + 设备后端）、R8G/R8H（前 4 视图已接入）
>
> 边界：**本轮为稳定性板块前端接入的最后一轮**——至此 7 视图全部接入真实后端，演示数据层退役

---

## 1. 本轮交付

| 交付物 | 内容 |
| --- | --- |
| Script Report ×5 | 稳定性台账 / 稳定性检测进度跟踪 / 年度持续稳定性考察覆盖清单 / 稳定性室温湿度记录查询（超标筛选）/ 设备与校准到期清单（方案 5.6 第 1/3/4/5/6 项；第 2 项已在 R8B 交付）——**方案 6 张报表全部物化**。有效截止日列由服务层派生函数计算（`effective_*_due` 非 DB 列，方案 P0-2 口径） |
| `api/stability.ts` 扩展 | +64 个接口函数与类型：R8C 结果 9 写 + 报告 6 写 + 只读 6（results / resultDetail / trend / validityAdvice / reports / reportDetail）；R8D 变更 10 写 + 稳定性室 7 写 + 只读 5；`ACTION_ROLES` 补 6.3.5~6.3.8 全部动作角色 |
| 视图 ×3 重写 | 「结果录入与趋势」三栏（检测中时间点 + 录入表单 + 结果表含复核/批准/作废动作 + ECharts 趋势线含线性拟合与在途虚线 + 外推建议卡）；「报告与有效期」三栏（报告列表 + 摘要含批准动作链 + 外推助手）+ 新建报告抽屉 + 批准（QA 判定有效期）弹窗；「变更·稳定性室·设备」三标签（变更清单含提交/审核/批准/实施/后评估全链按钮 + 温湿度记录表 + 设备台账与故障工单动作链） |
| 横幅更新 | 3 视图 `mode="live"` + 轮次专属说明；工作台 note 更新为「7 视图已全部接入」 |
| 演示层退役 | `stabilityDemo.ts` 由 356 行裁剪为 21 行（仅保留 `Tone`/`TONE_CLASS`/`toneClass` 语义色工具，供稳定性视图共用），孤儿演示数据全删 |

## 2. 实施中发现并处置

| # | 问题 | 处置 |
| --- | --- | --- |
| 1 | 方案 5.6 报表初版把 `effective_sample_due` / `effective_test_due` 当 DB 列查询，实机报 1054 | 改为服务层派生（`_effective_sample_due` / `_effective_test_due`），与方案 P0-2「有效截止日 = 已批准延期顺延日或政策上限」口径一致 |
| 2 | `get_stability_room_logs` 等只读接口在浏览器首测 417（Analyst 权限被拒） | 排查为 gunicorn worker 持有 R8D 之前的旧模块缓存；`kill -HUP` 重载后判定与契约一致，非代码缺陷 |
| 3 | 前端 `get_stability_master` 只返回主数据行、无按模块缓存，房间/检验项目下拉每次挂载都请求 | 维持现状（数据量小）；未引入额外缓存抽象 |

## 3. 验证证据（2026-09-20）

- **离线**：契约测试全量 **311/311**（R8D 23 项 + R8B/C 回归）
- **实机报表**：5 张 Script Report 以非 Administrator（Analyst）身份 `query_report.run` 全部渲染（稳定性台账 10 行 / 检测进度 2 行 / 覆盖清单 3 行 / 温湿度查询 / 设备到期）
- **浏览器真实会话**（`http://localhost:5173`，测试账号登录）：
  - 结果视图：录入 108.5 → `record_result` 200 → 表格出现 v3 草稿、v2 已批准·生效、v1 已修订三版本共存；趋势图 + 外推建议 4 个月渲染
  - 报告视图：2027 年度报告建档 → 服务端算出外推建议 4 个月；报告列表与摘要真实渲染
  - Ops 视图：温湿度记录写入（23.5℃ / 52%RH → 在控，上下限快照正确）→ 表格实时渲染；Reviewer 建设备 → 报故障 → 关闭（填偏差引用）全链 200
  - **角色显隐**：Analyst 在设备标签只见「报故障」（无「设备建档」，后端 `manage_equipment` R/M 专属被拒）；Reviewer 多出「设备建档」「开始处理」「关闭」——前端矩阵与后端 `ACTION_ROLES` 一致
  - **375px 移动端**：results / reports / ops 三页 `scrollWidth == 375`，无横向溢出
- 验证残留（报告 / 设备 / 故障 / 温湿度 / 结果草稿）已全部清理；验证用测试账号密码已统一重置（仅本地 TEST 环境）

## 4. 未做 / 边界

- 未部署生产（按惯例先给测试端链接，Owner 确认后再同步 `/hbos-lims`）
- 趋势图统计控制限不实现（QA 口径待确认，接口 note 已明示）
- 专项报告的客户 Link 补充在 Frappe Desk 完成（前端建档入口按方案仅收非专项必填项）

## 5. 涉及文件

- `hbos_lims/report/稳定性台账/` 等 5 个目录（新增）
- `frontend/hbos-lims-web/src/api/stability.ts`（+64 函数 + 角色矩阵）
- `frontend/hbos-lims-web/src/views/StabilityResultView.vue` / `StabilityReportView.vue` / `StabilityOpsView.vue`（重写）
- `frontend/hbos-lims-web/src/components/stability/StbGateBanner.vue`（文案更新）
- `frontend/hbos-lims-web/src/views/StabilityDashboardView.vue`（note 更新）
- `frontend/hbos-lims-web/src/demo/stabilityDemo.ts`（356 → 21 行）
