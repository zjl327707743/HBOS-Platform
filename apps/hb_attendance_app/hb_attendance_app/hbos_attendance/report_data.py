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

    **解析失败必须抛错，不能退回空字典**：退回等于「筛选丢了但查询照跑」——
    实测 `filters=not-json` 会返回全部 61816 行（22MB）。失败开放 + 无行数上限
    是最坏的组合，故宁可 400 也不默默返回全量。

    去空是为了让报表内部的 `filters.get("x")` 走「未传」分支，
    与在 Desk 里留空筛选框的行为一致。
    """
    if raw in (None, ""):
        return {}
    if isinstance(raw, str):
        try:
            raw = frappe.parse_json(raw)
        except Exception:
            frappe.throw("筛选条件不是合法的 JSON。", frappe.ValidationError)
    if not isinstance(raw, dict):
        frappe.throw("筛选条件必须是 JSON 对象。", frappe.ValidationError)

    out = {}
    for key, value in raw.items():
        if value is None or value == "":
            continue
        if isinstance(key, str) and key:
            out[key] = value
    return out


# 与 list_data 一致的行数上限。报表的 execute() 是全量算出来的（后端没有分页接口），
# 故这里只能「算全量、截一段」——但那也远好过把 22MB JSON 塞给浏览器。
# 上限之外由前端分页承担。
MAX_ROWS = 500


def _bounds(limit, start) -> tuple[int, int]:
    try:
        limit = max(1, min(int(limit), MAX_ROWS))
    except (TypeError, ValueError):
        limit = MAX_ROWS
    try:
        start = max(0, int(start))
    except (TypeError, ValueError):
        start = 0
    return limit, start


def _run(report_key: str, filters, limit=MAX_ROWS, start=0) -> dict[str, object]:
    """调用报表本体的 execute()，截取一段返回。

    报表的 execute() 没有分页参数（它是 Frappe 的脚本报表约定，返回全量），
    所以这里**算全量、只回一段**。真正的代价在 execute() 内部，截断只是防止
    把整份结果序列化给浏览器。
    """
    _require_read()

    module_path = _REPORTS[report_key]
    execute = frappe.get_attr(module_path + ".execute")

    try:
        result = execute(_clean_filters(filters))
    except frappe.ValidationError:
        raise
    except (TypeError, ValueError) as exc:
        # 报表内部对 month/year 之类做 int() 转换，类型不对会抛 ValueError。
        # 直接透出会变成 HTTP 500，用户只看到「服务器错误」。
        frappe.throw(f"筛选条件不合法：{exc}", frappe.ValidationError)

    columns, data = _unpack(result)
    limit, start = _bounds(limit, start)

    return {
        "report": report_key,
        "columns": columns,
        "data": data[start:start + limit],
        "total": len(data),
        "limit": limit,
        "start": start,
    }


def _unpack(result) -> tuple[list, list]:
    """把报表的返回值规整成 (columns, data)。

    Frappe 脚本报表的约定是二元组 `(columns, data)`，但也允许三元组
    （第三位是 message）。原实现只认 `len == 2`，三元组会被当成 columns、
    data 变空——页面看起来「正常但没数据」，最难查。这里显式处理。
    """
    if result is None:
        return [], []
    if isinstance(result, (list, tuple)):
        if len(result) >= 2:
            return list(result[0] or []), list(result[1] or [])
        if len(result) == 1:
            return list(result[0] or []), []
    if isinstance(result, dict):
        # 非标准返回：当作「列名 → 值」的窄表处理，比静默给空表好
        return [{"label": str(k), "fieldname": str(k)} for k in result], [result]
    return [], []


@frappe.whitelist()
def get_monthly_summary(filters=None, limit=MAX_ROWS, start=0):
    """月度考勤汇总。filters: {month, year, employee, department, from_date, to_date}"""
    return _run("monthly", filters, limit, start)


@frappe.whitelist()
def get_checkin_flow(filters=None, limit=MAX_ROWS, start=0):
    """打卡流水。filters: {from_date, to_date, employee, department, source_device, import_log, hbos_only}"""
    return _run("checkins", filters, limit, start)


@frappe.whitelist()
def get_attendance_results(filters=None, limit=MAX_ROWS, start=0):
    """考勤结果。filters: {from_date, to_date, employee, department, status}"""
    return _run("results", filters, limit, start)


@frappe.whitelist()
def get_monthly_staging(filters=None, limit=MAX_ROWS, start=0):
    """月度汇总 / 对账暂存。filters: {import_log, employee, department}"""
    return _run("staging", filters, limit, start)
