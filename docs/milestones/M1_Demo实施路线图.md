# M1 Demo 实施路线图

项目名称：新乡海滨智能运营管理平台。

状态：COMPLETED。

审查记录：M1-REQ-DESIGN-DRAFT 已通过 Codex 审查并收口为 COMPLETED。

执行日期：2026-07-08。

## 文档定位

本文档是 M1 考勤一期 Demo 的实施拆分路线图，基于 `M1_考勤一期真实需求确认.md`、`M1_考勤一期产品需求说明书.md` 和 `M1_考勤一期技术设计方案.md` 编写。本文档把 M1-R4 及后续 R5/R6/R7 拆分清楚，每轮有明确目标、禁止项和验收点。

本路线图是建议方案，最终执行轮次和顺序由用户决定。

## M1-R4 新定位

```
M1-R4：M1 Demo 技术方案与实施路线拆分
```

M1-R4 不再只是 HRMS 配置复测。M1-R4 不直接大开发。M1-R4 应基于 PRD 和技术设计拆分后续 R5/R6/R7 等执行轮次。

## 一周内最小交付路线

按照"一周内要有东西"的要求，建议 M1 最小交付路径：

```
M1-R4：路线拆分 + 配置基线（本轮）
  ↓
M1-R5：HRMS 配置 + Demo 数据 + 考勤工作台 + 月度汇总
  ↓
M1-R6：Excel 导入 + 异常处理流程
  ↓
M1-R7：飞书登录 + 领导 Demo + 收尾
```

R5/R6/R7 仅为建议，实际启动需用户逐轮授权。

## M1-R4：路线拆分与配置基线

目标：

- 基于 4 份设计文档，拆分后续 R5/R6/R7 详细实施计划
- 确认 Demo 数据范围（哪些部门、多少员工、哪个时间段）
- 确认 HRMS 配置基线（Shift Type、Holiday List、Company、Department 等）
- 确认 Demo 数据集的可复现导入步骤

禁止项：

- 不直接大开发
- 不创建 App / DocType / 代码
- 不导入真实数据
- 不动 TEST 数据

验收点：

- R5/R6/R7 路线确定
- Demo 数据范围确认
- 配置基线确认

## M1-R5：HRMS 配置 + Demo 数据 + 考勤工作台 + 月度汇总

目标：

- 完成 HRMS 生产级配置基线（Company、Department、Employee、Shift Type、Holiday List、Leave Type、Leave Allocation 最小配置）
- 准备 Demo 脱敏数据集（基于真实组织架构、虚构员工姓名）
- 搭建 Frappe Desk 考勤工作台 Workspace
- 实现月度汇总 Query Report（Frappe 原生）
- 实现月度汇总 Excel 导出

禁止项：

- 不导入真实员工姓名（确认后按脱敏规则）
- 不接真实考勤机
- 不创建 `hb_hr_app`（除非自定义 Workspace / Report 需要）
- 不接飞书登录
- 不接飞书工作台

验收点：

- 人事能在考勤工作台看到员工、班次、节假日配置
- 能在页面看到月度汇总报表
- 能导出月度汇总 Excel

## M1-R6：Excel 导入 + 异常处理流程

目标：

- 实现原始打卡流水 Excel 导入（Employee Checkin → Auto Attendance → Attendance）
- 实现月度汇总 Excel 导入（独立展示或汇总 DocType）
- 保留导入批次记录
- 实现考勤异常处理三级流程（员工提交→主管确认→人事归档）
- 如 HRMS 原生 Attendance Request 不满足，创建自定义 Attendance Exception DocType

禁止项：

- 不接真实考勤机
- 不接飞书请假
- 不创建 `hb_hr_app`（除非自定义 DocType 需要）
- 不修改核心源码

验收点：

- 能导入脱敏打卡流水 Excel 并生成 Attendance
- 能导入月度汇总 Excel 并对账展示
- 导入批次日志可查
- 员工能提交异常说明
- 主管能确认/驳回异常
- 人事能最终处理并归档
- 操作留痕可查

## M1-R7：飞书登录 + 领导 Demo + 收尾

目标：

- 接入飞书 OAuth 登录
- 实现飞书身份 → Employee 自动匹配
- 搭建领导汇总 Demo 视图
- M1 整体收尾、文档整理、Demo 演示准备

禁止项：

- 不接飞书工作台
- 不接入飞书请假
- 不部署到公司服务器/云服务器
- 不正式上线生产

验收点：

- 飞书扫码登录成功
- 登录后自动匹配 Employee 并进入对应角色页面
- 本地管理员账号可兜底登录
- 领导能看到汇总指标和部门排名
- M1 Demo 可完整演示

## 不直接大开发原则

- 每轮只做一轮的事，不提前实现下一轮功能
- 优先复用 HRMS 原生对象和能力
- 只在原生无法覆盖时创建自定义 DocType
- `hb_hr_app` 只有在至少一轮实施验证后、用户明确授权时才创建
- 所有开发只在本机 Docker 环境中进行

## 状态与下一步

- M1-REQ-DESIGN-DRAFT：COMPLETED，已通过 Codex 审查并收口。
- M1-R4：PLANNED，尚未启动。
- M1-R5/R6/R7：PLANNED（建议），需用户逐轮授权。

本轮未试运行，未创建、删除或清理 TEST 数据，未创建 App / DocType / 代码。
