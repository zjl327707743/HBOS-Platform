# Current Milestone

## M1-FIX：M1 考勤一期功能补漏阶段

项目名称：新乡海滨智能运营管理平台。

M1 已 closeout 为 COMPLETED，但 Owner 亲自验收后发现大量产品功能没有真正页面可体验——「方案完成」不等于「功能完成」。M1-FIX 阶段定位为功能补漏，补齐 M1 承诺但未实际可体验的产品功能。

## 当前轮次

M1-FIX-B2：导入口径、安全与准确性修复。当前状态：COMPLETED。已通过 Claude 审查（初审 FAIL → B2-FIX 复审 PASS），Codex closeout 已完成。

M1-FIX-B3：考勤工作台入口、App 命名与 HRMS 数据一致性修复。当前状态：REVIEWING，等待 Claude 审查。

M1-FIX-B4：考勤模块架构收敛与单一入口重整。当前状态：REVIEWING / Claude PASS，但 Owner 数据链路验收发现后续问题。B4 只收敛桌面入口、Workspace、Workspace Sidebar、导入页和 HBOS / HRMS 入口口径；M1-FIX-B3 不 closeout。

M1-FIX-B5：导入数据链路核查与报表口径收敛。当前状态：REVIEWING，等待 Owner 和 Claude 审查。B5 只核查真实 Employee / Checkin / Attendance / 月度暂存链路，收敛 HBOS 报表和 HRMS 技术核查入口；M1-FIX-B3 / B4 不 closeout。2026-08-21 后续修正：四车间 10 人行政班误判迟到修复、质量控制部四班次人员「满 8 小时算正常」口径收敛、配对上限 13h（见 B5 主文档「B5 后续修正」节）。2026-09-02 追加：班次管理页新增「规则看板」Tab，三类班次判定规则可视化（规则记录/内置班次/名单与配对参数）。2026-09-02 再追加：规则看板可导出班次人员维护表（5-sheet：部门-班次-人员主表 + 豁免/特殊班次/行政班名单/说明）。

M1-FIX-B-FIX：Excel 导入与中文体验修复。历史轮次；当前后续修复由 M1-FIX-B2、M1-FIX-B3、M1-FIX-B4、M1-FIX-B5 管理。

M1-FIX 后续规划轮次（仅规划，不自动启动）：

| 轮次 | 名称 | 优先级 | 状态 |
| --- | --- | --- | --- |
| M1-FIX-A | 差距盘点与实施方案 | — | REVIEWING |
| M1-FIX-B | Excel 导入与真实本地数据闭环 | P0 | REVIEWING |
| M1-FIX-B-FIX | Excel 导入与中文体验修复 | P0 | REVIEWING |
| M1-FIX-B2 | 导入口径、安全与准确性修复 | P0 | COMPLETED |
| M1-FIX-B3 | 考勤工作台入口、App 命名与 HRMS 数据一致性修复 | P0 | REVIEWING / Owner UI 验收未通过 |
| M1-FIX-B4 | 考勤模块架构收敛与单一入口重整 | P0 | REVIEWING / Claude PASS，Owner 数据链路验收发现后续问题 |
| M1-FIX-B5 | 导入数据链路核查与报表口径收敛 | P0 | REVIEWING |
| M1-FIX-C | 异常说明三级流程 | P1 | PLANNED |
| M1-FIX-D | 考勤工作台 + 月报 + 领导 Demo | P1 | PLANNED |
| M1-FIX-E | 飞书 OAuth 最小验证 + Owner 体验脚本 + 总审查 | P2 | PLANNED |

## M1 历史轮次（已完成）

M1 规划收口已完成；产品交付仍在 M1-FIX 中，尚未完成。全部 19 个历史轮次状态见里程碑索引。

M0 已完成并封板。M0-REMOTE 已完成。

权威状态文件：

- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/milestones/M0.md`

权威方案文件：

- `docs/milestones/M1_FIX_功能补漏实施方案.md`

## 本轮范围

M1-FIX-B / M1-FIX-B-FIX 只做 Excel 导入与真实本地数据闭环修复：

- 创建轻量 `hb_attendance_app`
- 创建导入日志
- 支持 Owner 在 Frappe Desk 页面上传考勤机月度导出表、识别预览、确认导入、查看导入日志与中文结果
- 创建 / 匹配 Employee
- 生成打卡流水
- 尝试 HRMS 原生自动考勤，并在必要时记录本地兜底生成
- 生成考勤结果并展示导入统计、重复跳过说明和失败摘要
- 默认白班/行政班为 08:30-17:30
- 不提交真实 Excel、真实员工清单或导入产物

## 本轮禁止事项

-- 不创建 `hb_core_app`
-- 不创建 `hb_feishu_app`
-- 不创建月度汇总 DocType
-- 不创建异常三级流程 DocType
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
M1     = IN_PROGRESS（产品交付，M1-FIX 中）
M1-FIX = IN_PROGRESS
M1-FIX-A = REVIEWING
M1-FIX-B = REVIEWING
M1-FIX-B-FIX = REVIEWING
M1-FIX-B2 = COMPLETED
M1-FIX-B3 = REVIEWING / Owner UI 验收未通过
M1-FIX-B4 = REVIEWING / Claude PASS，Owner 数据链路验收发现后续问题
M1-FIX-B5 = REVIEWING
M2     = NOT STARTED / WAITING OWNER AUTHORIZATION
```

## 下一轮预告

M1-FIX-B5 已进入 REVIEWING，等待 Owner 和 Claude 审查。M1-FIX-B3 / B4 不 closeout。M1-FIX-C（异常说明三级流程）为 PLANNED / 待 Owner 授权。M1-FIX-D/E 与 M2 均未启动。
