# Current Milestone

## M1-FIX：M1 考勤一期功能补漏阶段

项目名称：新乡海滨智能运营管理平台。

M1 已 closeout 为 COMPLETED，但 Owner 亲自验收后发现大量产品功能没有真正页面可体验——「方案完成」不等于「功能完成」。M1-FIX 阶段定位为功能补漏，补齐 M1 承诺但未实际可体验的产品功能。

## 当前轮次

M1-FIX-A：功能补漏差距盘点与实施方案。当前状态：REVIEWING。

M1-FIX 后续规划轮次（仅规划，不自动启动）：

| 轮次 | 名称 | 优先级 | 状态 |
| --- | --- | --- | --- |
| M1-FIX-A | 差距盘点与实施方案 | — | REVIEWING |
| M1-FIX-B | Excel 导入与 Demo 数据闭环 | P0 | PLANNED |
| M1-FIX-C | 异常说明三级流程 | P1 | PLANNED |
| M1-FIX-D | 考勤工作台 + 月报 + 领导 Demo | P1 | PLANNED |
| M1-FIX-E | 飞书 OAuth 最小验证 + Owner 体验脚本 + 总审查 | P2 | PLANNED |

## M1 历史轮次（已完成）

M1 已 closeout 为 COMPLETED。全部 19 轮次状态（R0 → R7，含 R3 子轮次）均为 COMPLETED（除 M1-R3 为 BLOCKED）。M1-R8 为 PLANNED（可选缓冲轮）。

M0 已完成并封板。M0-REMOTE 已完成。

权威状态文件：

- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/milestones/M0.md`

权威方案文件：

- `docs/milestones/M1_FIX_功能补漏实施方案.md`

## 本轮范围

M1-FIX-A 只做差距盘点与实施方案：

- 执行 Git Gate 检查并记录结果
- 读取 M1 关键文档还原当前实际可体验状态
- 输出 20 项差距矩阵（缺口编号、需求来源、M1 承诺、当前实际、差距判断、优先级、推荐实现方式、是否需要自定义 App/DocType、风险、验收方式）
- 给出是否需要自定义 App/DocType 的清晰判断
- 给出 M1-FIX-B/C/D/E 推荐拆分顺序
- 输出 Owner 需确认的 5 项 Gate 决策建议
- 更新项目状态文档使 M1-FIX-A 进入 REVIEWING

## 本轮禁止事项

- 不创建 App
- 不创建 DocType
- 不写业务代码
- 不导入 Excel/CSV
- 不创建/删除/清理 TEST 数据
- 不接真实考勤机
- 不配置真实飞书密钥
- 不要求 Owner 在聊天中粘贴 App Secret
- 不提交 `.env`、密钥、token、数据库、日志、缓存、运行产物
- 不修改 Frappe/ERPNext/HRMS 核心源码
- 不启动大型 Vue/React 前端
- 不启动 M2
- 不把「计划可行」写成「功能已实现」

## M1-FIX 全阶段禁止事项

- 不创建 `hb_core_app`
- 不修改 Frappe/ERPNext/HRMS 核心源码
- 不提交 `.env`、App Secret、密钥、token
- 不提交真实员工姓名、真实工号、真实数据
- 不提交 Excel/CSV 数据文件
- 不接真实考勤机
- 不部署公司内网/云服务器
- 不启动大型 Vue/React 前端
- 不启动 M2
- 不伪造飞书登录成功
- 不执行 `docker compose down -v`
- 不删除 Docker volume
- 不重建 `frontend` site

## 当前状态口径

```
M1     = COMPLETED（但 Owner 验收发现功能缺口）
M1-FIX = IN_PROGRESS
M1-FIX-A = REVIEWING
M2     = PLANNED / NOT STARTED / WAITING OWNER AUTHORIZATION
```

## 下一轮预告

等待 Owner 审阅 M1-FIX-A 方案后，授权进入 M1-FIX-B（Excel 导入与 Demo 数据闭环）。M2 未启动。
