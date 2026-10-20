from __future__ import annotations

import frappe

from hbos_portal.api.iam_access import _call, _only, _current_departments, _current_employees, _authorized_employees, _work_person
from hbos_portal.iam import guards, policy


@frappe.whitelist()
def list_departments(view_group="daily", target_department=None, company=None, **kwargs):
    def load():
        _only(kwargs, {"view_group", "target_department", "company"})
        rows = _current_departments("iam.departments.read")
        if not rows:
            frappe.throw("没有可读取的部门管理范围。", frappe.PermissionError)
        from hbos_portal.iam.organization import department_view, group_filter
        grouped = group_filter("Department", view_group, frappe.conf)[1]
        rows, company_ids, selected_company = department_view(rows, view_group, target_department, company, conf=frappe.conf)
        rows.sort(key=lambda row: (row.lft or 0, row.name))
        items = []
        for row in rows:
            employees = _authorized_employees(_current_employees([row.name]), "iam.departments.read")
            members = [_work_person(employee, row) for employee in employees]
            items.append({"id": row.name, "name": row.department_name or row.name, "parent_department": row.parent_department, "company": row.company, "confirmed": not bool(row.disabled), "member_count": len(members), "members": members})
        return {"groups_available": grouped, "items": items, "companies": [{"id": name, "name": name} for name in company_ids], "selected_company": selected_company}
    return _call(load, read_only=True)
