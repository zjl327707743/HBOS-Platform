import frappe
import json
from datetime import datetime
from collections import Counter


def run_import():
    with open("/tmp/delicloud_checkin.json") as f:
        records = json.load(f)

    emp_lookup = {}
    emp_by_name = {}
    for e in frappe.db.get_all("Employee", fields=["name", "employee_name", "employee_number"]):
        if e["employee_number"]:
            emp_lookup[e["employee_number"]] = e
            emp_by_name[e["employee_name"]] = e

    print(f"Employee lookup: {len(emp_lookup)}")

    CHECK_MAP = {
        "fp": "IN", "fa": "IN", "pass": "IN", "card": "IN",
        "app_scan": "IN", "gps": "IN", "wifi": "IN",
        "reissue": "IN", "flexible": "IN", "out_work": "OUT",
    }

    seen = set()
    rows = []
    skipped = 0
    name_match = 0

    for r in records:
        cd = json.loads(r.get("check_data", "{}"))
        emp_num = cd.get("employee_num", "").strip()
        member_name = cd.get("member_name", "").strip()
        ts = int(r["check_time"])
        terminal_id = r.get("terminal_id", "")
        log_type = CHECK_MAP.get(r.get("check_type", ""), "IN")
        check_time = datetime.fromtimestamp(ts)

        emp = emp_lookup.get(emp_num)
        if emp is None and member_name:
            emp = emp_by_name.get(member_name)
            if emp is not None:
                name_match += 1

        if emp is None:
            skipped += 1
        else:
            key = f"{emp['name']}|{check_time.strftime('%Y-%m-%d %H:%M:%S')}"
            if key not in seen:
                seen.add(key)
                rows.append((emp, check_time, log_type, terminal_id))

    print(f"Filtered: {len(rows)} records")
    print(f"Skipped: {skipped}")
    print(f"Name-matched: {name_match}")

    inserted = 0
    for i in range(0, len(rows), 200):
        chunk = rows[i:i + 200]
        for emp, check_time, log_type, terminal_id in chunk:
            doc = frappe.new_doc("Employee Checkin")
            doc.employee = emp["name"]
            doc.time = check_time
            doc.log_type = log_type
            doc.device_id = terminal_id
            doc.hbos_source_type = "HBOS raw checkin import"
            try:
                doc.insert(ignore_permissions=True)
                inserted += 1
            except Exception:
                pass
        frappe.db.commit()
        print(f"Progress: {inserted}/{len(rows)}")

    frappe.db.commit()

    total = frappe.db.count("Employee Checkin")
    types = Counter(r[0] for r in frappe.db.sql("SELECT log_type FROM `tabEmployee Checkin`"))
    emp_cnt = frappe.db.sql("SELECT COUNT(DISTINCT employee) FROM `tabEmployee Checkin`")[0][0]
    dates = frappe.db.sql("SELECT DATE(time) d, COUNT(*) c FROM `tabEmployee Checkin` GROUP BY d ORDER BY d")

    print(f"\n=== IMPORT COMPLETE ===")
    print(f"Inserted: {inserted}")
    print(f"Total Checkin: {total}")
    print(f"IN/OUT: {dict(types)}")
    print(f"Employees: {emp_cnt}")
    for d in dates:
        print(f"  {d[0]}: {d[1]} records")

    return inserted