"""Temporary fail-closed scope gate for legacy all-employee Script Reports.

All four Script Report execute() implementations use raw SQL or get_all().
Those paths bypass Frappe's User Permission filtering.  Until an IAM-approved
query-time per-employee/department filter exists, scoped HR users must not run
these all-employee reports through either Desk or the Portal JSON wrapper.

This is intentionally NOT a new department-level report implementation.
"""
from __future__ import annotations

import frappe


def require_unrestricted_employee_read() -> None:
    """Only run unscoped reports when Frappe can read every Employee.

    Reading the permitted Employee names via get_list enforces the user's
    current native permission_query_conditions and User Permissions.  The raw
    count is internal to this guard and is never returned to the caller.
    We intentionally do not accept a request's employee/department filter as
    proof of authorization.
    """
    if getattr(getattr(frappe, "session", None), "user", None) in (None, "", "Guest"):
        frappe.throw("考勤报表需要有效登录会话。", frappe.PermissionError)

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
        frappe.throw(
            "当前账号仅有部分员工查看权限，暂不能使用全员 SQL 报表。"
            "请改用受权限过滤的人员列表，待部门报表范围接口上线后再开放。",
            frappe.PermissionError,
        )
