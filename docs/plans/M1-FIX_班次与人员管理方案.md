# HBOS 班次与人员管理功能方案

> 版本：2026-08-20
> 状态：方案已确认，开始分步实施
> 适用：新乡海滨 HBOS Attendance（hb_attendance_app）

## 一、背景与现状

当前考勤判定的班次规则全部硬编码在代码里：

- [api.py](../../apps/hb_attendance_app/hb_attendance_app/hbos_attendance/api.py)：ADMIN_NUMS（行政班）、WUJUN_NUMS（无菌）、SAFETY_NUMS（安全）、FOOD_NUMS（食堂）、EXEMPT_NUMS（豁免）
- [pairing.py](../../apps/hb_attendance_app/hb_attendance_app/hbos_attendance/pairing.py)：SPECIAL_SHIFT_NUMS（无菌独立班次）、FOUR_SHIFT_NUMS（四班次）

痛点：

1. 改任何班次时间都要改代码 + 全月重算
2. 打卡流水的「班次」列读的是历史遗留字段，不更新
3. 无法在线查看部门有哪些班次、哪些班在进行、各班有哪些人

关键约束：考勤每 10 分钟全月重算，规则修改必须带「生效日期」，否则会改写历史。

## 二、目标功能

### 1. 人员管理（Page：hbos-employee-management）

- 员工详情：工号、照片（暂无录入，占位）、姓名、部门、联系方式、入职日期、状态
- 固定班次绑定：每人绑定一个固定班次
- 固定班次在打卡流水的「班次」列显示

### 2. 班次管理（Page：hbos-shift-management）

- 各部门的班次信息（时间、迟到早退标准、绑定人数、状态）
- 正在进行的班次（按当前时间判断）
- 在线修改班次时间，生效方式：**次日生效**（已确认）
- 修改审计记录

## 三、架构设计

### 数据层：HBOS 班次规则 DocType（hbos_shift_rule）

| 字段 | 说明 |
|---|---|
| rule_name | 规则名称，如「一车间-早班」 |
| department | Link Department |
| shift_type | Select：早班/中班/夜班/行政班/8:30班/无菌早(12h)/无菌晚(12h) |
| start_time | 上班时间 Time |
| end_time | 下班时间 Time |
| late_after | 迟到起算 Time |
| early_before | 早退起算（或最小工时小时数） |
| min_hours | 最小工时（默认 8，无菌 12 小时班为 12） |
| effective_from | 生效日期（次日生效默认值） |
| status | Select：草稿/生效/停用 |
| 审计字段 | owner、creation、modified 原生自带 |

现有 8 类硬编码规则迁移为种子数据；硬编码名单**保留做兜底**（已确认）。

### 逻辑层：判定引擎改造

- `_get_shift_and_late` / `special_shift_from_gap` / `four_shift_from_gap` 改为优先读规则表（按 attendance_date 取当时生效版本）
- 硬编码名单作为兜底（规则表无记录时）
- 打卡流水报表「班次」列：优先人员固定班次 → 判定班次 → 兜底「未排班」

### 页面层

- 班次管理页：部门列表 → 班次卡片（含人员数）→ 修改表单
- 人员管理页：员工卡片/表格 → 班次绑定 → 部门筛选

## 四、实施步骤

| 步 | 内容 | 验收 |
|---|---|---|
| 1 | 班次规则 DocType + 种子数据 + 判定引擎接入 | 现有判定结果不变，班次来源改为规则表 |
| 2 | 班次管理页 | 改「一车间早班 8:30→8:00」次日生效，历史不受影响 |
| 3 | 人员管理页 | 绑定后流水班次列正确显示 |
| 4 | 生效机制完善 | 改规则不改历史；HR 角色权限 |
| 5 | 增强（可选） | 批量绑定、班次冲突检测 |

## 五、已确认决策

- 生效方式：**次日生效**（默认），可选立即/指定日期
- 员工照片：暂无录入，留空占位
- 硬编码名单：**保留做兜底**，逐步迁移到绑定
