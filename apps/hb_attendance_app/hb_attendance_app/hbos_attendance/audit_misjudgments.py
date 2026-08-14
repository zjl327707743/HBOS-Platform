"""审计 HBOS 生成的 Attendance 中疑似跨天班次误判。

检查两类误判：
1. Present 但 working_hours > 12 —— 旧算法把跨天班次的上下班卡错误配对成超长班
2. late_entry=1 但当天首卡在 4:00~8:30 之间、且前一天晚上 20:00 后有打卡 ——
   疑似夜班的下班卡被旧算法当成早班迟到上班卡

用法:
    bench --site frontend execute hb_attendance_app.hbos_attendance.audit_misjudgments.run
"""
import frappe
from datetime import timedelta
from collections import defaultdict


def run():
    # 所有 HBOS Present 记录
    atts = frappe.db.sql("""
        SELECT a.name, a.employee, emp.employee_name, emp.employee_number,
               emp.department, a.attendance_date, a.late_entry, a.working_hours, a.shift
        FROM tabAttendance a
        JOIN tabEmployee emp ON emp.name = a.employee
        WHERE a.name LIKE 'HBOS-ATT-%%' AND a.status = 'Present' AND a.docstatus < 2
    """, as_dict=True)

    # 加载所有打卡
    dates = [a["attendance_date"] for a in atts]
    if not dates:
        frappe.msgprint("没有 HBOS Present 记录")
        return {}
    min_d = min(dates) - timedelta(days=1)
    max_d = max(dates) + timedelta(days=1)

    cks = frappe.db.sql("""
        SELECT ec.employee, ec.time
        FROM `tabEmployee Checkin` ec
        WHERE DATE(ec.time) BETWEEN %s AND %s
        ORDER BY ec.employee, ec.time
    """, (str(min_d), str(max_d)), as_dict=True)

    by_emp = defaultdict(list)
    for c in cks:
        by_emp[c["employee"]].append(c["time"])

    long_shift = []      # 超长班
    cross_day_late = []  # 疑似跨天误判迟到

    for a in atts:
        emp = a["employee"]
        ds = str(a["attendance_date"])
        times = by_emp.get(emp, [])

        # 1) 超长班
        if a["working_hours"] and a["working_hours"] > 12:
            long_shift.append({
                "employee_name": a["employee_name"],
                "employee_number": a["employee_number"],
                "department": a["department"],
                "attendance_date": ds,
                "shift": a["shift"],
                "working_hours": a["working_hours"],
                "late": a["late_entry"],
            })

        # 2) 跨天误判迟到: late=1 且当天首卡 4:00~8:30, 前一天晚 20:00 后有卡
        if not a["late_entry"]:
            continue
        day_cks = [t for t in times if str(t.date()) == ds]
        if not day_cks:
            continue
        first = min(day_cks)
        hm = first.hour * 60 + first.minute
        if not (4 * 60 <= hm <= 8 * 60 + 30):
            continue
        prev_ds = (first.date() - timedelta(days=1)).strftime("%Y-%m-%d")
        prev_night = [t for t in times if str(t.date()) == prev_ds and t.hour >= 20]
        if prev_night:
            cross_day_late.append({
                "employee_name": a["employee_name"],
                "employee_number": a["employee_number"],
                "department": a["department"],
                "attendance_date": ds,
                "shift": a["shift"],
                "first_checkin": first.strftime("%H:%M:%S"),
                "prev_night_checkin": prev_night[-1].strftime("%m-%d %H:%M"),
            })

    frappe.msgprint(
        "审计完成：超长班 {} 条，疑似跨天误判迟到 {} 条".format(len(long_shift), len(cross_day_late))
    )
    return {
        "long_shift_count": len(long_shift),
        "cross_day_late_count": len(cross_day_late),
        "long_shift_samples": long_shift[:20],
        "cross_day_late_samples": cross_day_late[:20],
    }
