# M1-FIX-B4：考勤模块架构收敛与单一入口重整

状态：REVIEWING。

执行日期：2026-07-10。

## 本轮定位

M1-FIX-B4 不新增异常三级流程、不做飞书 OAuth、不做领导 Demo、不 closeout M1。本轮只修复 Owner 在真实浏览器 UI 验收中发现的入口混乱问题：桌面入口、Workspace、左侧导航、导入页和报表显示口径必须收敛为一套“海滨考勤”产品主线。

## Git Gate

| 检查项 | 结果 |
| --- | --- |
| 当前分支 | `main` |
| 本轮开始 HEAD | `87c5b3ac3e99d7ec833fb3460213ebe13be9a72d` |
| 最新提交 | `fix: 完成 M1-FIX-B3 考勤工作台与数据一致性` |
| 工作区 | 开始前 clean |
| `main` 与 `origin/main` | `main` ahead 7 / behind 0 |
| 本地敏感/真实数据 | `.env` 与 `docs/data/月度汇总表_20260701_20260703.xlsx` 存在但均被 `.gitignore` 忽略，未被 Git 跟踪 |

## 运行态诊断结论

| 问题 | 结论 |
| --- | --- |
| `/desk/海滨考勤工作台` | 运行态是 `Workspace`，module 为 `HBOS Attendance` |
| `/desk/hbos-attendance-import` | 运行态是 `Page`，title 为 `导入考勤机导出表`，module 为 `HBOS Attendance` |
| 两个 route 是否同 App / Module | 是，均属于 `hb_attendance_app` / `HBOS Attendance` |
| 桌面 icon 为什么灰色 | 当前 Frappe Desk 桌面入口读取 `Desktop Icon.logo_url` / `icon_image` 或 app desktop icon 资产；`hooks.py` 的 `app_icon` 不会直接修复该 Workspace 桌面入口。运行态旧 `Desktop Icon` 的 `logo_url` / `icon_image` 为空、`bg_color=gray`，中文 label 又退化为首字占位，因此 Owner 看到灰色占位 |
| 左侧菜单为什么旧 | B3 只同步了 `Workspace`，没有同步派生的 `Workspace Sidebar`，运行态 Sidebar 仍残留旧 items |
| 当前 HBOS 权威入口 | `导入考勤机导出表`、`考勤导入日志`、`HBOS 打卡流水`、`HBOS 考勤结果`、`月度汇总 / 对账暂存` |
| HRMS 原生入口 | 保留为底层数据 / 管理入口，显示为 `HRMS 原始打卡记录`、`HRMS 原生考勤结果`，不作为左侧默认主导航 |

## 实现方案

本轮采用方案 A：以 `hb_attendance_app.hbos_attendance.setup.after_migrate` 作为单一同步入口，幂等维护运行态对象。

同步对象：

- `Workspace`：继续由版本化 fixture 覆盖，顶部增加 HBOS / HRMS 关系说明。
- `Workspace Sidebar`：同步 `海滨考勤` 和兼容旧 URL 的 `海滨考勤工作台` Sidebar，items 统一为 HBOS 业务主入口。
- `Desktop Icon`：新增/维护主桌面入口 `海滨考勤`，使用 `/assets/hb_attendance_app/hbos-attendance-logo.svg` 作为实际显示图标；旧 `海滨考勤工作台` 图标挂到 `海滨考勤` 的子项以保留 sidebar header 图标元数据，不再作为主桌面孤立入口显示。
- `Page`：导入页增加 `海滨考勤工作台 / 导入考勤机导出表` 说明和返回工作台入口。
- `Report`：不贸然重命名 Report 本体，继续使用现有 `打卡流水` / `考勤结果` 路由；通过 Workspace、Sidebar 和导入页文案明确显示为 HBOS 权威报表。

## 入口关系

```text
桌面入口：海滨考勤
  -> Workspace：海滨考勤工作台
     -> Page：导入考勤机导出表 (/desk/hbos-attendance-import)
     -> DocType：考勤导入日志 / 月度汇总对账暂存
     -> Report：HBOS 打卡流水（中文） -> Employee Checkin
     -> Report：HBOS 考勤结果（中文） -> Attendance
     -> HRMS 原生数据：HRMS 原始打卡记录 / HRMS 原生考勤结果
```

## 数据主线

```text
飞书账号
-> Frappe User
-> HRMS Employee
-> Employee Checkin
-> Attendance
-> HBOS 中文报表 / 导入日志 / 月度暂存
```

当前 M1-FIX-B4 仅收敛入口，不接飞书 OAuth。当前导入员工是 HRMS `Employee`；原始流水写入 HRMS `Employee Checkin`；考勤结果使用 HRMS `Attendance`；月度汇总只是 HBOS 暂存 / 对账，不伪造 `Employee Checkin`。当前不要求每个 `Employee` 都有 `User`。后续 M1-FIX-E 如获授权，再通过手机号 / 邮箱 / 工号绑定 Feishu User -> Frappe User -> HRMS Employee，员工个人权限后续通过 User -> Employee 过滤。

## 本轮不做

- 不进入 M1-FIX-C。
- 不实现异常三级流程。
- 不实现飞书 OAuth。
- 不实现领导 Demo。
- 不 closeout M1。
- 不修改 Frappe / ERPNext / HRMS 核心源码。
- 不提交真实 Excel、`.env`、密钥、数据库、日志、缓存或导入产物。

## 状态口径

- M1-FIX-B2 = COMPLETED。
- M1-FIX-B3 = REVIEWING / Owner UI 验收未通过，不能 closeout。
- M1-FIX-B4 = REVIEWING。
- M1 整体仍未完成。
- M1-FIX-C / D / E = PLANNED / 待授权。
- M2 = NOT STARTED / WAITING OWNER AUTHORIZATION。
