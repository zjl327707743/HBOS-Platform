"""飞书「调休」表 → HBOS Rest Leave Record（只读登记，不改考勤判定）。

对齐 api.sync_overtime_from_bitable 的写法：取 token → 分页拉全量 → 只取「已通过」
→ 以 feishu_approval_id 为唯一键 upsert。Owner 2026-09-11：本轮只做记录界面。
"""
import frappe

from hb_attendance_app.hbos_attendance.api import _get_token, _fetch_all_records_custom
from hb_attendance_app.hbos_attendance.swap_mapping import (
    rest_leave_fields, REST_LEAVE_APP_TOKEN, REST_LEAVE_TABLE_ID,
)

DOCTYPE = "HBOS Rest Leave Record"
ID_PREFIX = "feishu-bitable-restleave-"


def _match_employee(num, name):
    """工号优先匹配，其次姓名；都匹配不到返回 None。"""
    if num:
        emp = frappe.db.get_value("Employee", {"employee_number": num}, "name")
        if emp:
            return emp
    if name:
        return frappe.db.get_value("Employee", {"employee_name": name}, "name")
    return None


@frappe.whitelist()
def sync_rest_leave_from_bitable():
    try:
        token = _get_token()
        records = _fetch_all_records_custom(token, REST_LEAVE_APP_TOKEN, REST_LEAVE_TABLE_ID)
    except Exception as e:
        frappe.log_error(str(e), "飞书调休同步")
        frappe.throw(f"读取飞书调休表格失败: {e}")

    created = updated = skipped = 0
    for record in records:
        fields = record.get("fields", {}) or {}
        if fields.get("申请状态") != "已通过":
            skipped += 1
            continue
        rid = record.get("id", "")
        if not rid:
            skipped += 1
            continue
        mapped = rest_leave_fields(fields)
        if not mapped:
            skipped += 1
            continue
        emp = _match_employee(mapped["employee_number"], mapped["employee_name"])
        if not emp:
            skipped += 1
            continue

        aid = ID_PREFIX + rid
        exists = frappe.db.exists(DOCTYPE, {"feishu_approval_id": aid})
        doc = (frappe.get_doc(DOCTYPE, {"feishu_approval_id": aid}) if exists
               else frappe.get_doc({"doctype": DOCTYPE, "feishu_approval_id": aid}))
        doc.update({
            "employee": emp,
            "start_date": mapped["start_date"],
            "end_date": mapped["end_date"],
            "rest_days": mapped["rest_days"],
            "remarks": mapped["remarks"],
            "approval_status": "已通过",
            "feishu_sync_time": frappe.utils.now_datetime(),
        })
        try:
            doc.save(ignore_permissions=True)
            frappe.db.commit()
            if exists:
                updated += 1
            else:
                created += 1
        except Exception as e:
            frappe.log_error(str(e), "飞书调休写入失败")
            skipped += 1

    return {"created": created, "updated": updated, "skipped": skipped}
