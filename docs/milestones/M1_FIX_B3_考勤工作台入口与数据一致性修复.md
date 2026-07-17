# M1-FIX-B3：考勤工作台入口与数据一致性修复

状态：REVIEWING，等待 Claude 独立审查。

## 入口关系

```text
桌面 Apps → 海滨考勤 → 海滨考勤工作台
  → 导入考勤机导出表（Page: hbos-attendance-import）
  → 考勤导入日志 / 月度汇总对账暂存（HBOS Attendance Import Log）
  → HBOS 打卡流水（中文）（Report: 打卡流水）
  → HBOS 考勤结果（中文）（Report: 考勤结果）
```

工作台同时保留明确标注的 HRMS 原生 `Employee Checkin`、`Attendance` 入口，避免与 HBOS 中文报表混淆。

## HRMS 数据关系结论

| 检查项 | 结论 |
| --- | --- |
| 导入创建的员工 | 是，HRMS `Employee` |
| 导入写入的打卡 | 是，HRMS `Employee Checkin` |
| 考勤结果 | 是，HRMS `Attendance` |
| 月度汇总 | 是，`HBOS Attendance Import Log.monthly_summary_staging` 暂存/对账数据，不生成打卡 |
| 工作台报表 | 是，HBOS 报表读取 HRMS Employee / Employee Checkin / Attendance；导入日志读取 HBOS 扩展 DocType |
| HRMS 模拟数据与 HBOS 导入数据 | 可能并存；考勤结果以 `hbos_source_type`、`hbos_import_log` 区分，打卡以来源设备/导入批次说明区分；本轮未删除历史数据 |
| 未来飞书登录 | 飞书账号 → Frappe `User` → HRMS `Employee`；当前未配置 OAuth 或创建员工账号绑定 |

## 范围与验证

- 本轮只修复 App/Workspace/报表入口和展示口径，不启动 M1-FIX-C/D/E。
- 运行态 Workspace 已同步为三张卡片和七个入口；Desktop Module 标签为“海滨考勤”。
- 未读取或提交真实 Excel、`.env`、密钥、数据库或运行产物。
