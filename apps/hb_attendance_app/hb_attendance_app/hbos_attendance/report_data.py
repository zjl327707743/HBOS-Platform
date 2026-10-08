"""把 4 张考勤报表的数据以 JSON 形式提供给门户。

## 为什么需要

门户不再用 iframe 内嵌 Desk 报表，而是原生重写。报表的取数逻辑（`execute()`）
必须**只保留一份**——若门户另写一套查询，两处口径必然漂移（本项目为「一个业务
含义只留一份名单」专门收敛过行政班名单，同一道理适用）。

故这里做的是**薄包装**：直接调用报表自己的 `execute(filters)`，把返回的
`(columns, data)` 原样转成 JSON。查询、口径、字段含义全部沿用报表本体。

## 权限：为什么必须自己加

Frappe 的报表权限检查在**视图层**（Report 文档的 `roles`），不在 `execute()` 里。
直接调 `execute()` 会绕过它——任何登录用户都能拿到全量考勤数据。
故每个端点都走 `_require_read()`，角色集合与报表 JSON 中声明的 `roles` 一致。

## 边界

只读。不写库、不触发重算、不改任何业务状态。
"""
from __future__ import annotations

import frappe

# 与 report/*/*.json 里声明的 roles 一致：
#   月度考勤汇总 / 打卡流水 / 考勤结果 / 月度汇总暂存 均为 System Manager / HR Manager / HR User
READ_ROLES = ("System Manager", "HR Manager", "HR User")

# 报表模块路径（目录名与文件名都是中文，与 report/ 下的实际结构一一对应）
_REPORTS = {
    "monthly": "hb_attendance_app.hbos_attendance.report.月度考勤汇总.月度考勤汇总",
    "checkins": "hb_attendance_app.hbos_attendance.report.打卡流水.打卡流水",
    "results": "hb_attendance_app.hbos_attendance.report.考勤结果.考勤结果",
    "staging": "hb_attendance_app.hbos_attendance.report.hbos_月度汇总暂存（对账）."
    "hbos_月度汇总暂存（对账）",
}


def _require_read():
    frappe.only_for(list(READ_ROLES))


def _clean_filters(raw) -> dict:
    """接受 dict 或 JSON 字符串，丢掉空值。

    **必须处理字符串**：门户经 HTTP 调用时 `filters` 是 query 参数，到达这里是
    JSON 文本而非 dict；只判 dict 会把筛选**全部丢掉**、静默返回全量数据
    （实测打卡流水因此返回 61815 行，用户看到的「查询没用」就是这个）。

    去空是为了让报表内部的 `filters.get("x")` 走「未传」分支，
    与在 Desk 里留空筛选框的行为一致。
    """
    if isinstance(raw, str):
        try:
            raw = frappe.parse_json(raw)
        except Exception:
            return {}
    if not isinstance(raw, dict):
        return {}
    out = {}
    for key, value in raw.items():
        if value is None or value == "":
            continue
        if isinstance(key, str) and key:
            out[key] = value
    return out


def _run(report_key: str, filters) -> dict[str, object]:
    """调用报表本体的 execute()，把 (columns, data) 转成 JSON。"""
    _require_read()

    module_path = _REPORTS[report_key]
    execute = frappe.get_attr(module_path + ".execute")
    result = execute(_clean_filters(filters)) or ([], [])

    # 报表约定返回 (columns, data)；防御性处理只返回一元的实现
    columns, data = (result if isinstance(result, (list, tuple)) and len(result) == 2
                     else (result, []))

    return {
        "report": report_key,
        "columns": list(columns or []),
        "data": list(data or []),
        "row_count": len(data or []),
    }


@frappe.whitelist()
def get_monthly_summary(filters=None):
    """月度考勤汇总。filters: {month, year, employee, department, from_date, to_date}"""
    return _run("monthly", filters)


@frappe.whitelist()
def get_checkin_flow(filters=None):
    """打卡流水。filters: {from_date, to_date, employee, department, source_device, import_log, hbos_only}"""
    return _run("checkins", filters)


@frappe.whitelist()
def get_attendance_results(filters=None):
    """考勤结果。filters: {from_date, to_date, employee, department, status}"""
    return _run("results", filters)


@frappe.whitelist()
def get_monthly_staging(filters=None):
    """月度汇总 / 对账暂存。filters: {import_log, employee, department}"""
    return _run("staging", filters)
