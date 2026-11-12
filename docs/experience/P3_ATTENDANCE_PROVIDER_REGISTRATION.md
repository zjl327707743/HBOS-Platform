# HBOS Portal P3 — Attendance Provider Registration

**状态：P3-ATT-1 / P3-ATT-2 COMPLETE / RUNTIME GATE PASS**  
**日期：** 2026-09-25  
**分支：** `feature/hbos-portal-product`

## 1. 当前定位

Attendance 当前仍是 Frappe Desk / HR 管理型应用，因此 Portal 首轮采用：

```text
stable product route
/hbos/attendance
        ↓
Attendance-owned resolver
        ↓
current Desk page
/app/hbos-attendance-dashboard
```

migration mode：

```text
legacy
```

普通 Employee 尚未获得 Portal Attendance 入口。当前仅允许：

- HR User
- HR Manager
- System Manager
- Administrator break-glass

直到个人考勤 native UX 与对应授权契约完成后，再扩大普通员工访问。

## 2. P3-ATT-1 — Manifest / Access / Stable Entry

Manifest：

```json
{
  "id": "attendance",
  "route": "/hbos/attendance",
  "migration_mode": "legacy",
  "capabilities": []
}
```

Provider 由 Attendance 自己通过 `hbos_portal_provider` hook 注册。

Portal 不静态 import Attendance。

Runtime Gate 同时验证：

- Provider 被 Portal Registry 发现；
- Administrator bootstrap 可见 Attendance；
- `Page hbos-attendance-dashboard` 存在；
- `Workspace 海滨考勤工作台` 存在；
- Stable Route 解析到当前受控 Desk Page。

## 3. P3-ATT-2 — HR Summary Projection

Summary 不由 Portal 重算 HRMS Attendance。

Attendance Provider 直接复用既有：

```text
hbos_attendance_dashboard.dashboard_data.get_data()
```

并只投影四个 HR 语义指标：

- 异常人员
- 本周迟到
- 本周早退
- 本周缺勤

因此统计口径仍属于 Attendance App。

当前 manifest：

```json
["summary"]
```

Tasks / Search 未开放，因为 Attendance 当前尚无成熟的个人动作投影和稳定语义搜索契约。

## 4. Runtime Authority

Verified code authority：

```text
a7840675c2828dc6e1abbf5d717b43d891ba58db
```

Platform Integration Gate：

```text
run 36047574750 = SUCCESS
```

clean-site 输出：

```json
{
  "registry_entries": ["attendance", "lims"],
  "registry_failures": 0,
  "attendance_resolved_route": "/app/hbos-attendance-dashboard",
  "bootstrap_apps": ["attendance", "lims"]
}
```

Attendance-owned runtime：

```json
{
  "attendance_route": "/hbos/attendance",
  "attendance_mode": "legacy",
  "attendance_capabilities": ["summary"],
  "attendance_resolved_route": "/app/hbos-attendance-dashboard",
  "attendance_summary_status": "normal",
  "attendance_summary_metrics": 4
}
```

## 5. Definition of Done

```text
P3-ATT-1 Registry / Access / Entry = PASS
P3-ATT-1 Ordinary Employee Access = NOT ENABLED BY DESIGN
P3-ATT-2 Summary Projection = PASS
Attendance Tasks = NOT ENABLED
Attendance Search = NOT ENABLED
Business Writes = NONE
Portal → Attendance static import = NONE
```
