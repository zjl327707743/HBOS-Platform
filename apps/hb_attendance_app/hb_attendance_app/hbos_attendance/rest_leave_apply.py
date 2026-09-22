"""已核实调休日的**唯一**查询入口。

考勤判定（api.py）与部门看板（department_board_data.py）都从这里取数。
两个过滤条件必须同时成立：

    approval_status = 已通过    —— 否则被驳回/撤回的申请也会发放豁免
    verify_status  = 已核实     —— 否则未核实或核实不通过的调休日也会发放豁免

把条件收敛在此处（而非各调用方各写一份）是为了让口径无法漂移：本项目已有
两份分叉的行政班名单作为前车之鉴（daily_feishu_sync.py 与 rule_lists.py）。

本模块只负责取数，不参与判定，也不暴露为接口。
"""
import frappe

from hb_attendance_app.hbos_attendance.rest_leave import expand_verified_records

DOCTYPE = "HBOS Rest Leave Record"

# 唯一的过滤口径。任何调用方都不得自建第二份。
FILTERS = {
    "approval_status": "已通过",
    "verify_status": "已核实",
}


def verified_rest_dates():
    """返回 {employee: {日期}}，仅含已通过且已核实的调休日。

    查不到任何记录时返回 {}——调用方按「无豁免」处理即可。
    """
    rows = frappe.db.get_all(
        DOCTYPE,
        filters=FILTERS,
        fields=["employee", "start_date", "end_date"],
    )
    return expand_verified_records(rows)
