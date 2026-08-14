import frappe
from collections import defaultdict
from datetime import date, timedelta


SHIFT_NAMES = {
    "早班": "早班",
    "中班": "中班",
    "晚班": "晚班",
    "行政班": "行政班",
    "行政班早班": "行政班",
    "白班": "行政班",
}


def execute(filters=None):
    filters = filters or {}
    conditions = []
    values = {}

    if filters.get("from_date"):
        conditions.append("a.attendance_date >= %(from_date)s")
        values["from_date"] = filters["from_date"]
    if filters.get("to_date"):
        conditions.append("a.attendance_date <= %(to_date)s")
        values["to_date"] = filters["to_date"]
    if filters.get("employee"):
        conditions.append("a.employee = %(employee)s")
        values["employee"] = filters["employee"]
    if filters.get("department"):
        conditions.append("emp.department = %(department)s")
        values["department"] = filters["department"]
    if filters.get("month") and filters.get("year"):
        conditions.append("MONTH(a.attendance_date) = %(month)s")
        values["month"] = int(filters["month"])
        conditions.append("YEAR(a.attendance_date) = %(year)s")
        values["year"] = int(filters["year"])

    # 豁免名单过滤: 经理以上人员不计入异常考勤
    from hb_attendance_app.hbos_attendance.api import EXEMPT_NUMS
    if EXEMPT_NUMS:
        quoted = ",".join("'%s'" % v.replace("'", "") for v in sorted(EXEMPT_NUMS))
        conditions.append("emp.employee_number NOT IN (%s)" % quoted)

    where = " AND ".join(conditions) if conditions else "1=1"

    # Get all attendance records
    attendance = frappe.db.sql(
        f"""
        SELECT
            a.name, a.employee, a.attendance_date, a.status,
            a.late_entry, a.early_exit, a.shift, a.working_hours,
            emp.employee_name, emp.employee_number, emp.department
        FROM tabAttendance a
        LEFT JOIN tabEmployee emp ON emp.name = a.employee
        WHERE {where}
        ORDER BY emp.employee_number, a.attendance_date
        """,
        values,
        as_dict=True,
    )

    # Get leave records for the same period
    leave_conditions = ["lr.approval_status = '已通过'", "lr.docstatus < 2"]
    leave_values = {}
    if filters.get("month") and filters.get("year"):
        leave_conditions.append(
            "MONTH(lr.start_date) <= %(month)s AND MONTH(lr.end_date) >= %(month)s"
        )
        leave_values["month"] = int(filters["month"])
        leave_conditions.append("YEAR(lr.start_date) <= %(year)s AND YEAR(lr.end_date) >= %(year)s")
        leave_values["year"] = int(filters["year"])
    elif filters.get("from_date") and filters.get("to_date"):
        leave_conditions.append(
            "lr.start_date <= %(to_date)s AND lr.end_date >= %(from_date)s"
        )
        leave_values["from_date"] = filters["from_date"]
        leave_values["to_date"] = filters["to_date"]

    leave_where = " AND ".join(leave_conditions) if leave_conditions else "1=1"
    leave_records = frappe.db.sql(
        f"""
        SELECT lr.employee, lr.start_date, lr.end_date, lr.leave_type, lr.leave_days
        FROM `tabHBOS Leave Record` lr
        WHERE {leave_where}
        """,
        leave_values,
        as_dict=True,
    )

    # Build per-employee leave date set
    emp_leave_dates = defaultdict(set)
    emp_leave_detail = defaultdict(list)
    for lr in leave_records:
        d = lr["start_date"]
        if isinstance(d, str):
            d = date.fromisoformat(d)
        end = lr["end_date"]
        if isinstance(end, str):
            end = date.fromisoformat(end)
        while d <= end:
            emp_leave_dates[lr["employee"]].add(str(d))
            d += timedelta(days=1)
        # Store detail
        emp_leave_detail[lr["employee"]].append({
            "start": str(lr["start_date"]),
            "end": str(lr["end_date"]),
            "type": lr["leave_type"],
            "days": lr["leave_days"],
        })

    # Build per-employee summary
    if attendance:
        emp_summary = {}
        for a in attendance:
            emp = a["employee"]
            if emp not in emp_summary:
                emp_summary[emp] = {
                    "employee": emp,
                    "employee_name": a["employee_name"] or "",
                    "employee_number": a["employee_number"] or "",
                    "department": a["department"] or "",
                    "shifts": defaultdict(int),
                    "late_list": [],
                    "early_list": [],
                    "absent_list": [],
                    "leave_list": [],
                    "normal_list": [],
                }

            s = emp_summary[emp]
            shift_display = SHIFT_NAMES.get(a["shift"], a["shift"] or "未排班")
            s["shifts"][shift_display] += 1

            date_str = str(a["attendance_date"])
            day_label = date_str[8:]

            # Check if this date is a leave day
            is_leave = date_str in emp_leave_dates.get(emp, set())

            if is_leave:
                s["leave_list"].append(day_label)
            elif a["status"] == "Absent":
                s["absent_list"].append(day_label)
            elif a["late_entry"] and a["early_exit"]:
                s["late_list"].append(day_label)
            elif a["late_entry"]:
                s["late_list"].append(day_label)
            elif a["early_exit"]:
                s["early_list"].append(day_label)
            else:
                s["normal_list"].append(day_label)

        # Build report rows
        data = []
        for emp in sorted(emp_summary.keys()):
            s = emp_summary[emp]
            shift_counts = s["shifts"]
            # Build leave detail string
            leave_details = emp_leave_detail.get(emp, [])
            leave_detail_str = "  ".join(
                f"{ld['start'][5:]}-{ld['end'][5:]}" for ld in leave_details
            )
            data.append({
                "employee": s["employee"],
                "employee_name": s["employee_name"],
                "employee_number": s["employee_number"],
                "department": s["department"],
                "shift_行政班": shift_counts.get("行政班", 0),
                "shift_早班": shift_counts.get("早班", 0),
                "shift_中班": shift_counts.get("中班", 0),
                "shift_晚班": shift_counts.get("晚班", 0),
                "shift_未排班": shift_counts.get("未排班", 0),
                "late_count": len(s["late_list"]),
                "early_count": len(s["early_list"]),
                "absent_count": len(s["absent_list"]),
                "leave_count": len(s["leave_list"]),
                "normal_count": len(s["normal_list"]),
                "late_detail": "  ".join(s["late_list"]),
                "early_detail": "  ".join(s["early_list"]),
                "absent_detail": "  ".join(s["absent_list"]),
                "leave_detail": "  ".join(s["leave_list"]),
            })

        return _columns(), data

    return _columns(), []


def _columns():
    return [
        {"label": "员工姓名", "fieldname": "employee_name", "fieldtype": "Data", "width": 100},
        {"label": "工号", "fieldname": "employee_number", "fieldtype": "Data", "width": 100},
        {"label": "部门", "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 150},
        {"label": "行政班(天)", "fieldname": "shift_行政班", "fieldtype": "Int", "width": 85},
        {"label": "早班(天)", "fieldname": "shift_早班", "fieldtype": "Int", "width": 85},
        {"label": "中班(天)", "fieldname": "shift_中班", "fieldtype": "Int", "width": 85},
        {"label": "晚班(天)", "fieldname": "shift_晚班", "fieldtype": "Int", "width": 85},
        {"label": "迟到(次)", "fieldname": "late_count", "fieldtype": "Int", "width": 80},
        {"label": "早退(次)", "fieldname": "early_count", "fieldtype": "Int", "width": 80},
        {"label": "缺勤(天)", "fieldname": "absent_count", "fieldtype": "Int", "width": 80},
        {"label": "请假(天)", "fieldname": "leave_count", "fieldtype": "Int", "width": 80},
        {"label": "正常(天)", "fieldname": "normal_count", "fieldtype": "Int", "width": 80},
        {"label": "迟到详情", "fieldname": "late_detail", "fieldtype": "Small Text", "width": 500},
        {"label": "早退详情", "fieldname": "early_detail", "fieldtype": "Small Text", "width": 500},
        {"label": "缺勤详情", "fieldname": "absent_detail", "fieldtype": "Small Text", "width": 500},
        {"label": "请假详情", "fieldname": "leave_detail", "fieldtype": "Small Text", "width": 500},
    ]