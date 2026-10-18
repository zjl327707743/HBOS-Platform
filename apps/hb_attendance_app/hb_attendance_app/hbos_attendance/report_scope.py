"""Temporary fail-closed scope gate for legacy all-employee Script Reports.

All four Script Report execute() implementations use raw SQL or get_all().
Those paths bypass Frappe's User Permission filtering.  Until an IAM-approved
query-time per-employee/department filter exists, scoped HR users must not run
these all-employee reports through either Desk or the Portal JSON wrapper.

This is intentionally NOT a new department-level report implementation.
"""
from __future__ import annotations

import frappe


_REPORT_SOURCES = frozenset((
    "Employee", "Attendance", "Employee Checkin", "HBOS Leave Record",
    "HBOS Attendance Import Log", "HBOS Shift Rule",
))
_SCOPED_MESSAGE = (
    "当前账号存在部分员工或业务记录的查看范围，暂不能使用全员 SQL 报表。"
    "请改用受权限过滤的人员列表，待部门报表范围接口上线后再开放。"
)


def _require_native_unscoped_read(doctype: str) -> None:
    """Prove native full read authority without reading the report's rows.

    Frappe 16 DatabaseQuery builds the same User Permission, if_owner,
    permission_query_conditions and shared-document conditions as get_list.
    Any such predicate is a scope, even if it currently matches every row.
    In particular, shares-only access is stored in query.conditions rather
    than the returned match string and must not be mistaken for global read.
    """
    try:
        from frappe.model.db_query import DatabaseQuery

        query = DatabaseQuery(doctype, user=frappe.session.user)
        query.fields = [f"`tab{doctype}`.`name`"]
        read_type = query.check_read_permission(doctype)
        condition = query.build_match_conditions()
    except frappe.PermissionError:
        raise
    except Exception:
        # No SQL, user values or internal exception text reaches the caller.
        frappe.throw("无法核实原生数据权限，考勤报表已拒绝访问。", frappe.PermissionError)
    if not isinstance(condition, str):
        frappe.throw("无法核实原生数据权限，考勤报表已拒绝访问。", frappe.PermissionError)
    if read_type != "read" or condition.strip() or query.conditions:
        frappe.throw(_SCOPED_MESSAGE, frappe.PermissionError)


def require_unrestricted_employee_read(*source_doctypes: str) -> None:
    """Only run raw reports with native unscoped read on all data sources.

    Reading the permitted Employee names via get_list enforces the user's
    current native permission_query_conditions and User Permissions.  The raw
    count is internal to this guard and is never returned to the caller.
    Equal counts alone do not prove authority over historical/orphan records
    or import staging JSON. Retain that check, then require a scope-free native
    query for Employee and every source declared by the report implementation.
    The source names are internal constants, never request filters. Genuinely
    unrestricted HR may still read history when the Employee table is empty.
    """
    if getattr(getattr(frappe, "session", None), "user", None) in (None, "", "Guest"):
        frappe.throw("考勤报表需要有效登录会话。", frappe.PermissionError)
    sources = ("Employee",) + tuple(source_doctypes)
    if any(doctype not in _REPORT_SOURCES for doctype in sources):
        frappe.throw("无法核实报表数据来源，考勤报表已拒绝访问。", frappe.PermissionError)

    visible = frappe.get_list(
        "Employee",
        pluck="name",
        limit_page_length=0,
    )
    if not isinstance(visible, (tuple, list)):
        frappe.throw("无法核实员工可见范围，考勤报表已拒绝访问。", frappe.PermissionError)

    permitted = {str(name) for name in visible if name}
    employee_total = int(frappe.db.count("Employee") or 0)
    if len(permitted) != employee_total:
        frappe.throw(_SCOPED_MESSAGE, frappe.PermissionError)
    for doctype in dict.fromkeys(sources):
        _require_native_unscoped_read(doctype)
