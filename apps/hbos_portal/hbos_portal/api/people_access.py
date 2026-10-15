"""Read-only projections of native, permission-filtered personnel and roles."""
from __future__ import annotations

import frappe

from hbos_portal.api._utils import call_safely
from hbos_portal.contracts.errors import PortalException
from hbos_portal.services.access import require_authenticated_user


def _text(value: object) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise PortalException("INVALID_REQUEST", "筛选内容必须是字符串。")
    value = value.strip()
    if len(value) > 100:
        raise PortalException("INVALID_REQUEST", "筛选内容不能超过 100 字。")
    return value


def _bounded_integer(value: object, maximum: int, label: str) -> int:
    if type(value) is int:
        number = value
    elif isinstance(value, str) and value.isascii() and value.isdecimal():
        # Check the length before converting untrusted, arbitrarily long input.
        digits = value.lstrip("0") or "0"
        if len(digits) > len(str(maximum)):
            raise PortalException("INVALID_REQUEST", f"{label}超出可查询范围。")
        number = int(digits)
    else:
        raise PortalException("INVALID_REQUEST", f"{label}必须是正整数。")
    if number < 1 or number > maximum:
        raise PortalException("INVALID_REQUEST", f"{label}超出可查询范围。")
    return number


def _page_number(value: object) -> int:
    return _bounded_integer(value, 10000, "页码")


def _page_size(value: object) -> int:
    return _bounded_integer(value, 50, "每页数量")


def _literal_like(value: str) -> str:
    return "%" + value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def _read(callback):
    def run():
        require_authenticated_user()
        try:
            return callback()
        except frappe.PermissionError:
            raise PortalException("FORBIDDEN", "你没有查看这些资料的权限。") from None
    return call_safely(run)


def _query(doctype, fields, filters, page, size, order):
    # get_list preserves native row and field permissions for BOTH queries.
    counts = frappe.get_list(doctype, fields=[{"COUNT": "name", "as": "total"}], filters=filters,
                             limit_page_length=1)
    rows = frappe.get_list(doctype, fields=fields, filters=filters, order_by=order,
                           limit_start=(page - 1) * size, limit_page_length=size)
    return rows, int(counts[0].get("total", 0)) if counts else 0


def _mask_phone(value):
    value = str(value or "").strip()
    if not value:
        return ""
    return value[:3] + "****" + value[-4:] if len(value) >= 7 else "****"


@frappe.whitelist(methods=["GET"])
def get_people(source="User", page=1, page_size=10, name="", phone="", department="", position=""):
    def load():
        if source not in ("User", "Employee"):
            raise PortalException("INVALID_REQUEST", "请选择账号资料或员工资料。")
        number, size = _page_number(page), _page_size(page_size)
        filters = []
        title_field = "full_name" if source == "User" else "employee_name"
        phone_field = "mobile_no" if source == "User" else "cell_number"
        if keyword := _text(name):
            filters.append([title_field, "like", _literal_like(keyword)])
        if _text(phone):
            raise PortalException("INVALID_REQUEST", "人员目录不支持手机号筛选。")
        department_value, position_value = _text(department), _text(position)
        if source == "User" and (department_value or position_value):
            raise PortalException("INVALID_REQUEST", "部门和岗位筛选适用于员工资料。")
        if department_value:
            filters.append(["department", "=", department_value])
        if position_value:
            filters.append(["designation", "like", _literal_like(position_value)])
        if source == "User":
            filters.append(["name", "not in", ["Guest", "Administrator"]])
            fields = ["name", "full_name", "mobile_no", "enabled", "role_profile_name"]
        else:
            fields = ["name", "employee_number", "employee_name", "cell_number", "department",
                      "designation", "user_id", "status"]
        rows, total = _query(source, fields, filters, number, size, "name asc")
        items = []
        for row in rows:
            account = row["name"] if source == "User" else row.get("user_id")
            profile = row.get("role_profile_name") if source == "User" else None
            items.append({
                "id": f"{source}:{row['name']}", "record_id": row["name"],
                "display_id": row.get("employee_number") or row["name"],
                "name": row.get(title_field) or row["name"], "phone": _mask_phone(row.get(phone_field)),
                "department": row.get("department") or "", "position": row.get("designation") or "",
                "active": row.get("enabled") in (1, True, "1") if source == "User" else row.get("status") == "Active",
                "account_linked": bool(account), "role_profile": profile or "",
            })
        return {"items": items, "total": total, "source": source, "read_only": True,
                "authorization_domain": "native_personnel", "management_policy_applied": False,
                "position_authorization_connected": False}
    return _read(load)


@frappe.whitelist(methods=["GET"])
def get_organizations():
    def load():
        rows = frappe.get_list("Department", fields=["name", "parent_department"],
                               order_by="name asc", limit_page_length=201)
        return {"items": [{"id": row["name"], "name": row["name"],
                           "parent_id": row.get("parent_department") or None} for row in rows[:200]],
                "truncated": len(rows) > 200, "read_only": True,
                "authorization_domain": "native_personnel", "management_policy_applied": False}
    return _read(load)


@frappe.whitelist(methods=["GET"])
def get_roles(page=1, page_size=10, name=""):
    def load():
        number, size, keyword = _page_number(page), _page_size(page_size), _text(name)
        filters = [["name", "like", _literal_like(keyword)]] if keyword else []
        rows, total = _query("Role", ["name", "creation", "desk_access"], filters, number, size, "name asc")
        return {"items": [{"id": row["name"], "name": row["name"], "created_at": str(row.get("creation") or ""),
                           "description": "现有 Frappe 角色" + (" · 可访问 Desk" if row.get("desk_access") else ""),
                           } for row in rows], "total": total, "read_only": True,
                "authorization_domain": "native_personnel", "management_policy_applied": False,
                "position_authorization_connected": False}
    return _read(load)
