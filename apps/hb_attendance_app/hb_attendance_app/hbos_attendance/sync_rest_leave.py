"""飞书「调休」表 → HBOS Rest Leave Record。

与请假同步（api.sync_from_bitable）同模板：取 token → 分页拉全量 → 状态映射
→ 以 feishu_approval_id 为唯一键 upsert。另有取舍不同：
  * 日期区间按天展开后由判定侧处理，本文件只落 start/end 原始区间；
  * 失败记 Error Log 并写进返回摘要，**不在调度任务里 throw**；
  * 匹配不到员工的记录计入 unmatched，不再静默丢弃；
  * 单条记录的任何异常都被就地兜住，不会中断整批、也不会丢摘要。
加班日的解析与核实分别见 parse_pending_rest_leaves / verify_pending_rest_leaves。
"""
import frappe

from hb_attendance_app.hbos_attendance.api import (
    STATUS_MAP, _fetch_all_records_custom, _get_token,
)
from hb_attendance_app.hbos_attendance.rest_leave import (
    ID_PREFIX, PARSE_PENDING, REST_LEAVE_APP_TOKEN, REST_LEAVE_TABLE_ID,
    rest_leave_fields,
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
    """同步飞书调休表。任何失败都记日志并返回摘要，不抛异常。

    摘要键集合在所有返回路径上完全一致（含拉表失败的提前返回），
    调用方可以无条件读取任何一个键。键含义：
      total/created/updated 总数与新增、更新数
      skipped 脏行：飞书行缺 id，或缺人员、缺开始日期等映射不出字段
      unmatched 映射出了字段但匹配不到 Employee（不静默丢弃）
      failed 落库失败（save/commit 抛异常）
      error 拉表阶段的失败原因，非空即表示本次未处理任何记录
    """
    summary = {"total": 0, "created": 0, "updated": 0,
               "skipped": 0, "unmatched": 0, "failed": 0, "error": ""}
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
        # 单条记录的处理整体兜底：员工匹配、exists、get_doc、update、save
        # 任一抛异常都不得冒泡出函数——否则整批中止、摘要丢失、调度链被打断。
        try:
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
            # 必须在校验前暂存旧说明：doc.update 会就地覆盖 doc.remarks，
            # 之后再比较恒为假，「说明被改过 → 重新解析」将永远不触发。
            old_remarks = doc.remarks if exists else None
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
            elif old_remarks != mapped["remarks"]:
                # 说明被改过 → 加班日需重新解析
                doc.verify_status = PARSE_PENDING
            doc.save(ignore_permissions=True)
            frappe.db.commit()
            if exists:
                summary["updated"] += 1
            else:
                summary["created"] += 1
        except Exception as e:
            frappe.log_error(str(e), "飞书调休写入失败")
            summary["failed"] += 1

    return summary
