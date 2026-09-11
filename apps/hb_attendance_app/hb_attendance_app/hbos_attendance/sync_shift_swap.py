"""飞书「换班」表 → HBOS Shift Swap Record（只读登记，不改考勤判定）。

注意：换班表链接是 /wiki/ 形式，其节点 ID 不是 bitable app_token，
必须先用 wiki API 解析真实 obj_token，否则读取会失败（且不能静默跳过）。
"""
import frappe
import requests

from hb_attendance_app.hbos_attendance.api import _get_token, _fetch_all_records_custom
from hb_attendance_app.hbos_attendance.swap_mapping import (
    swap_fields, resolve_wiki_obj_token, SWAP_WIKI_NODE, SWAP_TABLE_ID,
)

DOCTYPE = "HBOS Shift Swap Record"
ID_PREFIX = "feishu-bitable-swap-"


def _match_employee(num, name):
    if num:
        emp = frappe.db.get_value("Employee", {"employee_number": num}, "name")
        if emp:
            return emp
    if name:
        return frappe.db.get_value("Employee", {"employee_name": name}, "name")
    return None


@frappe.whitelist()
def sync_shift_swap_from_bitable():
    try:
        token = _get_token()
        app_token = resolve_wiki_obj_token(token, SWAP_WIKI_NODE, requests.get)
        records = _fetch_all_records_custom(token, app_token, SWAP_TABLE_ID)
    except Exception as e:
        frappe.log_error(str(e), "飞书换班同步")
        frappe.throw(f"读取飞书换班表格失败: {e}")

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
        mapped = swap_fields(fields)
        if not mapped:
            skipped += 1
            continue
        applicant = _match_employee(mapped["applicant_number"], mapped["applicant_name"])
        substitute = _match_employee(mapped["substitute_number"], mapped["substitute_name"])
        if not applicant or not substitute:
            skipped += 1
            continue

        aid = ID_PREFIX + rid
        exists = frappe.db.exists(DOCTYPE, {"feishu_approval_id": aid})
        doc = (frappe.get_doc(DOCTYPE, {"feishu_approval_id": aid}) if exists
               else frappe.get_doc({"doctype": DOCTYPE, "feishu_approval_id": aid}))
        doc.update({
            "applicant": applicant,
            "substitute": substitute,
            "swap_date": mapped["swap_date"],
            "repay_date": mapped["repay_date"],
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
            frappe.log_error(str(e), "飞书换班写入失败")
            skipped += 1

    return {"created": created, "updated": updated, "skipped": skipped}
