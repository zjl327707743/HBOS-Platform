from __future__ import annotations

import frappe

from hbos_portal.api.iam_access import _call, _only, _current_departments, _current_employees, _authorized_employees, _work_person
from hbos_portal.iam import guards, policy


@frappe.whitelist()
def list_departments(view_group="daily", **kwargs):
    def load():
        _only(kwargs, {"view_group"})
        rows = _current_departments("iam.departments.read")
        if not rows:
            frappe.throw("没有可读取的部门管理范围。", frappe.PermissionError)
        from hbos_portal.iam.organization import filter_rows, group_filter
        grouped = group_filter("Department", view_group, frappe.conf)[1]
        rows = filter_rows(rows, "Department", view_group, conf=frappe.conf)
        rows.sort(key=lambda row: (row.lft or 0, row.name))
        items, companies = [], set()
        for row in rows:
            employees = _authorized_employees(_current_employees([row.name]), "iam.departments.read")
            members = [_work_person(employee, row) for employee in employees]
            items.append({"id": row.name, "name": row.department_name or row.name, "parent_department": row.parent_department, "company": row.company, "confirmed": not bool(row.disabled), "member_count": len(members), "members": members})
            if row.company:
                companies.add(row.company)
        return {"groups_available": grouped, "items": items, "companies": [{"id": name, "name": name} for name in sorted(companies)]}
    return _call(load)
