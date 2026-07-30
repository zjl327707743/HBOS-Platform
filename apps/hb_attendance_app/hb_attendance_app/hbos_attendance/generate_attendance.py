"""考勤生成：使用 shift_matcher 规则引擎 + 缺勤补全"""
import frappe
from datetime import datetime, timedelta, date
from hb_attendance_app.hbos_attendance.shift_matcher import match_shifts_v2, SHIFT_DEFS


def generate_attendance(from_date="2026-07-28", to_date="2026-07-30"):
    frappe.db.sql("DELETE FROM tabAttendance WHERE attendance_date BETWEEN %s AND %s AND hbos_source_type='delicloud'", (from_date, to_date))
    frappe.db.commit()

    # 运行规则引擎
    results = match_shifts_v2(from_date=from_date, to_date=to_date)

    # 员工 & 请假
    EI = {e["name"]: e for e in frappe.db.sql("SELECT name,employee_name,department,company FROM tabEmployee WHERE status='Active'", as_dict=1)}
    LV = {}
    for lv in frappe.db.sql("SELECT employee,start_date,end_date,leave_type FROM `tabHBOS Leave Record` WHERE approval_status='已通过'", as_dict=1):
        d = lv["start_date"]
        while d <= lv["end_date"]:
            LV[f"{lv['employee']}|{d.strftime('%Y-%m-%d')}"] = lv["leave_type"]
            d += timedelta(days=1)

    print(f"Matched: {len(results['matched'])}, Late: {len(results['late'])}, Early: {len(results['early'])}")
    print(f"Shifts: {results['stats'].get('shift_distribution', {})}")

    created, late_n, early_n = 0, 0, 0
    stats = {"Present": 0, "On Leave": 0, "Absent": 0}
    # Track which employees have attendance on which dates
    covered = set()

    late_set = {f"{l['employee']}|{l['date']}" for l in results["late"]}
    early_set = {f"{l['employee']}|{l['date']}" for l in results["early"]}

    now = frappe.utils.now_datetime().strftime("%Y-%m-%d %H:%M:%S.%f")

    for r in results["matched"]:
        emp = r["employee"]
        ds = r["date"]
        shift = r["shift"]
        if not shift:
            continue

        ei = EI.get(emp)
        if not ei:
            continue

        in_time = r["in_punch"]
        out_time = r["out_punch"]
        src = r.get("match_source", "")
        lv_type = LV.get(f"{emp}|{ds}")

        # 只有单次打卡且不是跨天且不是今天+晚班 → 缺勤
        is_single = bool(in_time) != bool(out_time)  # XOR: exactly one
        is_cross_day = src.startswith("cross_") or src.startswith("cross_day")
        is_last_day_night = ds == to_date and shift == "晚班" and bool(in_time or out_time)

        if lv_type:
            status = "On Leave"
        elif is_single and not is_cross_day and not is_last_day_night:
            status = "Absent"
        else:
            status = "Present"

        stats[status] = stats.get(status, 0) + 1
        covered.add(f"{emp}|{ds}")

        # 迟到/早退
        late = 1 if f"{emp}|{ds}" in late_set else 0
        if late: late_n += 1
        early = 1 if f"{emp}|{ds}" in early_set else 0
        if early: early_n += 1

        wh = round((out_time - in_time).total_seconds() / 3600, 2) if in_time and out_time else 0.0

        n = f"DELI-ATT-{emp}-{ds}"
        if frappe.db.exists("Attendance", n):
            continue

        ins = in_time.strftime("%Y-%m-%d %H:%M:%S") if in_time else None
        outs = out_time.strftime("%Y-%m-%d %H:%M:%S") if out_time else None

        frappe.db.sql(
            "INSERT INTO tabAttendance (name,creation,modified,docstatus,idx,naming_series,"
            "employee,employee_name,status,attendance_date,company,department,shift,"
            "in_time,out_time,late_entry,early_exit,working_hours,hbos_source_type,leave_type,_user_tags) "
            "VALUES (%s,%s,%s,1,0,'ATT-',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'delicloud',%s,%s)",
            (n, now, now, emp, ei.get("employee_name",""), status, ds,
             ei.get("company",""), ei.get("department",""), shift,
             ins, outs, late, early, wh, lv_type,
             f'{{"src":"{src}","confidence":"{r.get("confidence","")}"}}'))
        created += 1

    frappe.db.commit()

    # ============ 补全缺勤 ============
    fd = datetime.strptime(from_date, "%Y-%m-%d").date()
    td = datetime.strptime(to_date, "%Y-%m-%d").date()

    # 获取每个日期应出勤的员工：当天有打卡 OR 前一天有中班跨天打卡(当天凌晨打卡的OUT)
    should_work = {}  # date_str -> set of employees
    for d in [fd + timedelta(days=i) for i in range((td - fd).days + 1)]:
        ds = d.strftime("%Y-%m-%d")
        should_work[ds] = set()

    # 当天有打卡的员工
    for ck in frappe.db.sql("""
        SELECT DISTINCT employee, DATE(time) AS dt FROM `tabEmployee Checkin`
        WHERE name LIKE 'DELICLOUD-%%' AND employee IS NOT NULL
          AND time >= %s AND time < %s
    """, (from_date, (td + timedelta(days=1)).strftime("%Y-%m-%d")), as_dict=1):
        ds = ck["dt"].strftime("%Y-%m-%d")
        if ds in should_work:
            should_work[ds].add(ck["employee"])

    # 前一天中班跨天：当天 00:00-10:00 有打卡 = 前一天的中班下班 → 前一天算上班
    for ck in frappe.db.sql("""
        SELECT DISTINCT employee, DATE(time) AS dt FROM `tabEmployee Checkin`
        WHERE name LIKE 'DELICLOUD-%%' AND employee IS NOT NULL
          AND HOUR(time) BETWEEN 0 AND 10
          AND time >= %s AND time < %s
    """, (from_date, (td + timedelta(days=1)).strftime("%Y-%m-%d")), as_dict=1):
        prev_day = (ck["dt"] - timedelta(days=1)).strftime("%Y-%m-%d")
        if prev_day in should_work:
            should_work[prev_day].add(ck["employee"])

    for ds, emps in sorted(should_work.items()):
        for emp in emps:
            key = f"{emp}|{ds}"
            if key in covered:
                continue
            # 员工当天有打卡但没有 attendance → 缺勤
            lv_type = LV.get(key)
            status = "On Leave" if lv_type else "Absent"

            ei = EI.get(emp)
            if not ei:
                continue

            n = f"DELI-ATT-{emp}-{ds}"
            if frappe.db.exists("Attendance", n):
                continue

            frappe.db.sql(
                "INSERT INTO tabAttendance (name,creation,modified,docstatus,idx,naming_series,"
                "employee,employee_name,status,attendance_date,company,department,shift,"
                "in_time,out_time,late_entry,early_exit,working_hours,hbos_source_type,leave_type,_user_tags) "
                "VALUES (%s,%s,%s,1,0,'ATT-',%s,%s,%s,%s,%s,%s,'早班',NULL,NULL,0,0,0,'delicloud',%s,%s)",
                (n, now, now, emp, ei.get("employee_name",""), status, ds,
                 ei.get("company",""), ei.get("department",""), lv_type,
                 '{"src":"补全缺勤","confidence":"medium"}'))
            stats[status] = stats.get(status, 0) + 1
            created += 1
            covered.add(key)

    frappe.db.commit()
    frappe.db.sql("UPDATE tabAttendance a INNER JOIN tabEmployee e ON e.name=a.employee SET a.employee_name=e.employee_name, a.department=e.department WHERE a.attendance_date BETWEEN %s AND %s AND a.hbos_source_type='delicloud' AND (a.employee_name='' OR a.employee_name IS NULL)", (from_date, to_date))
    frappe.db.commit()

    print(f"\n=== 考勤生成完成 ===")
    print(f"生成: {created} | 迟到: {late_n} | 早退: {early_n}")
    for s, c in sorted(stats.items()):
        print(f"  {s}: {c}")

    v = frappe.db.sql("SELECT status, COUNT(*) c FROM tabAttendance WHERE attendance_date BETWEEN %s AND %s AND hbos_source_type='delicloud' GROUP BY status ORDER BY status", (from_date, to_date), as_dict=1)
    print("\n=== 验证 ===")
    for r in v:
        print(f"  {r['status']}: {r['c']}")

    return {"created": created, "late": late_n, "early": early_n, "stats": stats}


if __name__ == "__main__":
    generate_attendance()
