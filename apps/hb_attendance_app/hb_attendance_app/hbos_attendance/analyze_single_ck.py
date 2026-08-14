import frappe
from datetime import datetime, timedelta

start_d = "2026-08-01"
end_d = "2026-08-02"

raw = frappe.db.sql("""
    SELECT emp.name as eid, emp.employee_name, emp.employee_number, emp.department,
           DATE(ec.time) as d, MIN(ec.time) as ck
    FROM `tabEmployee Checkin` ec
    JOIN tabEmployee emp ON emp.name = ec.employee
    WHERE DATE(ec.time) BETWEEN %s AND %s
    GROUP BY emp.name, emp.employee_name, emp.employee_number, emp.department, DATE(ec.time)
    HAVING COUNT(*) = 1
    ORDER BY d, emp.employee_number
""", (start_d, end_d), as_dict=True)

lines = []
lines.append("TOTAL SINGLE CHECKIN DAYS: " + str(len(raw)))

ok_count = 0
miss_count = 0

for r in raw:
    eid = r.eid
    d = r.d
    ck = r.ck
    prev_d = (d - timedelta(days=1)).strftime("%Y-%m-%d")
    next_d = (d + timedelta(days=1)).strftime("%Y-%m-%d")

    adj = frappe.db.sql("""
        SELECT time, DATE(time) as dd FROM `tabEmployee Checkin`
        WHERE employee = %s AND (DATE(time) = %s OR DATE(time) = %s)
        ORDER BY time
    """, (eid, prev_d, next_d))

    min_gap = None
    paired = "无"

    prev_last = None
    for a in adj:
        if str(a[1]) == prev_d:
            prev_last = a[0]
    if prev_last:
        gap = (ck - prev_last).total_seconds() / 3600
        if gap > 0 and (min_gap is None or gap < min_gap):
            min_gap = gap
            paired = "前天" + prev_last.strftime("%m-%d %H:%M")

    next_first = None
    for a in adj:
        if str(a[1]) == next_d and next_first is None:
            next_first = a[0]
    if next_first:
        gap = (next_first - ck).total_seconds() / 3600
        if gap > 0 and (min_gap is None or gap < min_gap):
            min_gap = gap
            paired = "后天" + next_first.strftime("%m-%d %H:%M")

    gap_str = str(round(min_gap, 1)) + "h" if min_gap is not None else "无"
    name = r.employee_name or "?"
    num = r.employee_number or ""
    dept = r.department or ""
    date_str = str(d)
    ck_str = ck.strftime("%H:%M")

    if min_gap is None or min_gap > 4:
        miss_count += 1
        lines.append("MISS|" + date_str + "|" + name + "|" + num + "|" + dept + "|" + ck_str + "|" + paired + "|" + gap_str)
    else:
        ok_count += 1
        lines.append("OK|" + date_str + "|" + name + "|" + num + "|" + dept + "|" + ck_str + "|" + paired + "|" + gap_str)

lines.append("")
lines.append("=== SUMMARY ===")
lines.append("OK(<=4h): " + str(ok_count))
lines.append("MISS(>4h/no): " + str(miss_count))

with open("/home/frappe/frappe-bench/sites/single_ck_analysis.txt", "w") as f:
    f.write("\n".join(lines))

print("Written to /home/frappe/frappe-bench/sites/single_ck_analysis.txt")
print("Total: " + str(len(raw)) + "  OK: " + str(ok_count) + "  MISS: " + str(miss_count))