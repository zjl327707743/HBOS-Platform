import frappe
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta


@frappe.whitelist()
def get_data(start_str=None, end_str=None):
    """Fetch anomaly dashboard data: summary cards, charts, and table.

    Defaults to current week (Mon-Sun) if start_str is not provided.
    """
    frappe.only_for(["HR Manager", "HR User", "System Manager"])
    # Default to current week
    today = date.today()
    if not start_str:
        start = today - timedelta(days=today.weekday())
    else:
        start = date.fromisoformat(start_str)
    if not end_str:
        end = start + timedelta(days=6)
    else:
        end = date.fromisoformat(end_str)
    start_str = start.isoformat()
    end_str = end.isoformat()

    # ---------- Active employee snapshot ----------
    active_emps = frappe.db.get_all(
        "Employee",
        filters={"status": "Active"},
        fields=["name", "employee_name", "employee_number", "department"],
    )
    emp_index = {e.name: e for e in active_emps}
    total_employees = len(active_emps)

    # ---------- Attendance query (all statuses in range) ----------
    atts = frappe.db.sql(
        """
        SELECT a.employee, emp.employee_name, emp.employee_number, emp.department,
               a.attendance_date, a.late_entry, a.early_exit, a.status, a.shift, a.working_hours
        FROM tabAttendance a
        JOIN tabEmployee emp ON emp.name = a.employee
        WHERE a.attendance_date BETWEEN %(start)s AND %(end)s
          AND a.docstatus < 2
        ORDER BY a.attendance_date DESC
        """,
        {"start": start_str, "end": end_str},
        as_dict=True,
    )

    # ---------- Aggregate per employee ----------
    from hb_attendance_app.hbos_attendance.api import _is_exempt
    emp_data = defaultdict(lambda: {
        "late_dates": set(), "early_dates": set(), "absent_dates": set(),
        "name": "", "num": "", "dept": "",
    })
    # 已有考勤记录的 (员工, 日期) 集合, 零打卡检测不得重复计数
    seen_emp_date = set()
    for r in atts:
        eid = r.employee
        if _is_exempt(r.employee_number or ""):
            continue
        emp_data[eid]["name"] = r.employee_name or ""
        emp_data[eid]["num"] = r.employee_number or ""
        emp_data[eid]["dept"] = r.department or ""
        ds = str(r.attendance_date)
        key = (eid, ds)
        if key in seen_emp_date:
            continue
        seen_emp_date.add(key)
        if r.late_entry:
            emp_data[eid]["late_dates"].add(ds)
        if r.early_exit:
            emp_data[eid]["early_dates"].add(ds)
        if r.status == "Absent":
            emp_data[eid]["absent_dates"].add(ds)

    # ---------- Build row list ----------
    rows = []
    for eid, data in emp_data.items():
        lc = len(data["late_dates"])
        ec = len(data["early_dates"])
        ac = len(data["absent_dates"])
        if lc == 0 and ac == 0 and ec == 0:
            continue
        rows.append({
            "eid": eid,
            "name": data["name"],
            "num": data["num"],
            "dept": data["dept"],
            "late_count": lc,
            "early_count": ec,
            "absent_count": ac,
            "total_anomaly": lc + ac + ec,
        })

    rows.sort(key=lambda x: -x["total_anomaly"])

    # ---------- Summary / card stats ----------
    total_late = sum(r["late_count"] for r in rows)
    total_early = sum(r["early_count"] for r in rows)
    total_absent = sum(r["absent_count"] for r in rows)
    anomaly_people = len(rows)
    attendance_rate = round((1 - total_absent / max(total_employees * max((end - start).days, 1), 1)) * 100, 1)
    daily_avg_late = round(total_late / max((end - start).days + 1, 1), 1)

    # ---------- Top 15 late ----------
    top_late = sorted(rows, key=lambda x: -x["late_count"])[:15]

    # ---------- Top 15 absent ----------
    top_absent = sorted(rows, key=lambda x: -x["absent_count"])[:15]

    # ---------- Department aggregation ----------
    dept_late = Counter()
    dept_early = Counter()
    dept_absent = Counter()
    for r in rows:
        dept = r["dept"] or "未知部门"
        dept_late[dept] += r["late_count"]
        dept_early[dept] += r["early_count"]
        dept_absent[dept] += r["absent_count"]

    dept_anomaly_data = []
    all_depts = set(list(dept_late.keys()) + list(dept_absent.keys()))
    for dept in all_depts:
        dept_anomaly_data.append({
            "name": dept,
            "late": dept_late.get(dept, 0),
            "early": dept_early.get(dept, 0),
            "absent": dept_absent.get(dept, 0),
        })
    dept_anomaly_data.sort(key=lambda x: -(x["late"] + x["absent"] + x["early"]))

    # ---------- Daily trend (per-date anomaly counts) ----------
    # 趋势图直接按 emp_data 的去重日期集合聚合, 与排行表口径一致, 避免重复计数
    daily_late2 = Counter()
    daily_early2 = Counter()
    daily_absent2 = Counter()
    for eid, data in emp_data.items():
        for ds in data["late_dates"]:
            daily_late2[ds] += 1
        for ds in data["early_dates"]:
            daily_early2[ds] += 1
        for ds in data["absent_dates"]:
            daily_absent2[ds] += 1

    all_dates = sorted({str(start + timedelta(days=i)) for i in range((end - start).days + 1)})
    trend_labels = [dd[5:] for dd in all_dates]  # MM-DD
    trend_late = [daily_late2.get(dd, 0) for dd in all_dates]
    trend_early = [daily_early2.get(dd, 0) for dd in all_dates]
    trend_absent = [daily_absent2.get(dd, 0) for dd in all_dates]

    # ---------- Table rows (anomaly leaderboard) ----------
    table_rows = []
    for r in rows:
        table_rows.append({
            "name": r["name"],
            "num": r["num"],
            "dept": r["dept"],
            "late_count": r["late_count"],
            "early_count": r["early_count"],
            "absent_count": r["absent_count"],
        })

    return {
        # Summary cards
        "total_late": total_late,
        "total_early": total_early,
        "total_absent": total_absent,
        "anomaly_people": anomaly_people,
        "total_employees": total_employees,
        "attendance_rate": attendance_rate,
        "daily_avg_late": daily_avg_late,
        "date_range": f"{start_str} ~ {end_str}",
        # Top 15 charts
        "top_late_names": [r["name"] for r in top_late],
        "top_late_counts": [r["late_count"] for r in top_late],
        "top_absent_names": [r["name"] for r in top_absent],
        "top_absent_counts": [r["absent_count"] for r in top_absent],
        # Dept anomaly bar
        "dept_names": [d["name"] for d in dept_anomaly_data[:10]],
        "dept_late": [d["late"] for d in dept_anomaly_data[:10]],
        "dept_early": [d["early"] for d in dept_anomaly_data[:10]],
        "dept_absent": [d["absent"] for d in dept_anomaly_data[:10]],
        # Daily trend
        "trend_labels": trend_labels,
        "trend_late": trend_late,
        "trend_early": trend_early,
        "trend_absent": trend_absent,
        # Anomaly leaderboard table
        "table_rows": table_rows,
    }
