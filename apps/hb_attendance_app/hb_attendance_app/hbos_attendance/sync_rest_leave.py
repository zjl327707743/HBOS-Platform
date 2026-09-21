"""飞书「调休」表 → HBOS Rest Leave Record。

与请假同步（api.sync_from_bitable）同模板：取 token → 分页拉全量 → 状态映射
→ 以 feishu_approval_id 为唯一键 upsert。另有取舍不同：
  * 日期区间按天展开后由判定侧处理，本文件只落 start/end 原始区间；
  * 失败记 Error Log 并写进返回摘要，**不在调度任务里 throw**；
  * 匹配不到员工的记录计入 unmatched，不再静默丢弃。
加班日的解析与核实分别见 parse_pending_rest_leaves / verify_pending_rest_leaves。
"""
import frappe

from hb_attendance_app.hbos_attendance.api import (
    STATUS_MAP, _fetch_all_records_custom, _get_token,
)
from hb_attendance_app.hbos_attendance.rest_leave import (
    ID_PREFIX, PARSE_PENDING, REST_LEAVE_APP_TOKEN, REST_LEAVE_TABLE_ID,
    VERIFY_PARSE_FAIL, VERIFY_PENDING, rest_leave_fields,
)

DOCTYPE = "HBOS Rest Leave Record"


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
    """同步飞书调休表。任何失败都记日志并返回摘要，不抛异常。"""
    summary = {"total": 0, "created": 0, "updated": 0,
               "skipped": 0, "unmatched": 0, "error": ""}
    try:
        token = _get_token()
        records = _fetch_all_records_custom(
            token, REST_LEAVE_APP_TOKEN, REST_LEAVE_TABLE_ID)
    except Exception as e:
        frappe.log_error(str(e), "飞书调休同步")
        summary["error"] = str(e)
        return summary

    summary["total"] = len(records)
    for record in records:
        fields = record.get("fields", {}) or {}
        rid = record.get("id", "")
        if not rid:
            summary["skipped"] += 1
            continue
        mapped = rest_leave_fields(fields)
        if not mapped:
            summary["skipped"] += 1
            continue
        emp = _match_employee(mapped["employee_number"], mapped["employee_name"])
        if not emp:
            # 不静默丢弃：匹配不到必须可见，否则调休会无声消失
            summary["unmatched"] += 1
            frappe.log_error(
                "调休记录匹配不到员工: %s / %s"
                % (mapped["employee_number"], mapped["employee_name"]),
                "飞书调休同步")
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
            "approval_status": STATUS_MAP.get(fields.get("申请状态", ""), "审批中"),
            "feishu_sync_time": frappe.utils.now_datetime(),
        })
        if not exists:
            # 新记录等待 LLM 解析加班日
            doc.verify_status = PARSE_PENDING
        elif doc.remarks != mapped["remarks"]:
            # 说明被改过 → 加班日需重新解析
            doc.verify_status = PARSE_PENDING
        try:
            doc.save(ignore_permissions=True)
            frappe.db.commit()
            if exists:
                summary["updated"] += 1
            else:
                summary["created"] += 1
        except Exception as e:
            frappe.log_error(str(e), "飞书调休写入失败")
            summary["skipped"] += 1

    return summary
