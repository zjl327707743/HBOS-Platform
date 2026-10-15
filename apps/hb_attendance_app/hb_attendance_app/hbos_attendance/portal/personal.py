"""The personal endpoint derives its only subject from the Frappe Session."""
from __future__ import annotations

from datetime import datetime, time, timedelta

import frappe


def bounded_request(date_from=None, date_to=None, page=1, page_size=20):
    from frappe.utils import getdate, nowdate
    try:
        end = getdate(date_to or nowdate())
        start = getdate(date_from or end - timedelta(days=30))
        page, page_size = int(page), int(page_size)
        if start > end or (end - start).days > 366 or not 1 <= page <= 10000 or not 1 <= page_size <= 50:
            raise ValueError
    except (TypeError, ValueError, OverflowError):
        frappe.throw("请选择最多367天的有效日期和有界分页。", frappe.ValidationError)
    return start, end, page, page_size


@frappe.whitelist(methods=["GET"])
def get_my_attendance(date_from=None, date_to=None, page=1, page_size=20, **kwargs):
    from hbos_portal.iam import policy
    from hbos_portal.iam.temporary_passwords import check_request
    from hbos_portal.auth.accounts import no_store
    no_store()
    if frappe.conf.get("hbos_iam_enabled") not in (True, 1, "1"):
        frappe.throw("本站点尚未启用本人考勤接口。", frappe.PermissionError)
    # Explicitly inspect the wire parameters too; Frappe ordinarily discards
    # unexpected kwargs before calling a whitelisted Python signature.
    allowed = {"date_from", "date_to", "page", "page_size", "cmd"}
    if set(kwargs) - {"cmd"} or set(frappe.local.form_dict or {}) - allowed:
        frappe.throw("本人考勤不接受员工、账号、部门或任意筛选参数。", frappe.PermissionError)
    check_request()
    user = policy.get_current_user()
    employee = policy.resolve_employee(user)
    decision = policy.evaluate(user, "attendance", "attendance.read", "SELF", "")
    if not decision["allowed"]:
        frappe.throw("尚未安排本人考勤，或安排已停用、失效。", frappe.PermissionError)
    start, end, page, page_size = bounded_request(date_from, date_to, page, page_size)
    params = {"employee": employee.name, "start": start, "end": end,
              "start_time": datetime.combine(start, time.min), "end_time": datetime.combine(end + timedelta(days=1), time.min),
              "limit": page_size, "offset": (page - 1) * page_size}
    # The same bound predicate is shared by rows/count/summary, before any
    # business query. Never use owner, display name, or a client Employee key.
    union = """
      select name as id, date(time) as date, time as time, log_type,
             '' as status, 'Employee Checkin' as source
        from `tabEmployee Checkin`
       where employee=%(employee)s and time >= %(start_time)s and time < %(end_time)s
      union all
      select name as id, attendance_date as date, NULL as time, '' as log_type,
             status, 'Attendance' as source
        from `tabAttendance`
       where employee=%(employee)s and attendance_date between %(start)s and %(end)s
         and docstatus < 2
    """
    counts = frappe.db.sql("select count(*) as records, count(distinct date) as days from (" + union + ") bounded", params, as_dict=True)[0]
    rows = frappe.db.sql("select * from (" + union + ") bounded order by date desc, time desc, source, id limit %(limit)s offset %(offset)s", params, as_dict=True)
    # Recheck immediately before returning; no capability result is cached in
    # the browser or borrowed from a configuration administrator's session.
    if not policy.evaluate(user, "attendance", "attendance.read", "SELF", "")["allowed"]:
        frappe.throw("考勤安排已变化，请重新加载。", frappe.PermissionError)
    return {"ok": True, "data": {"rows": rows, "total": int(counts.records), "page": page, "page_size": page_size,
                                  "summary": {"records": int(counts.records), "days": int(counts.days)}}}
