import frappe
from collections import defaultdict, Counter


def fix_inout():
    all_ck = frappe.db.sql("""
        SELECT name, employee, time, log_type
        FROM `tabEmployee Checkin`
        ORDER BY employee, time
    """, as_dict=True)

    groups = defaultdict(list)
    for ck in all_ck:
        key = f"{ck['employee']}|{ck['time'].strftime('%Y-%m-%d')}"
        groups[key].append(ck)

    updates = 0
    for key, punches in groups.items():
        punches.sort(key=lambda x: x['time'])
        n = len(punches)
        for idx, p in enumerate(punches):
            if n == 1:
                new_type = 'IN'
            elif idx == 0:
                new_type = 'IN'
            elif idx == n - 1:
                new_type = 'OUT'
            elif n % 2 == 0:
                new_type = 'IN' if idx % 2 == 0 else 'OUT'
            else:
                new_type = 'IN' if idx % 2 == 0 else 'OUT'

            if p['log_type'] != new_type:
                frappe.db.sql(
                    "UPDATE `tabEmployee Checkin` SET log_type = %s WHERE name = %s",
                    (new_type, p['name']),
                )
                updates += 1

    frappe.db.commit()
    types = Counter(r[0] for r in frappe.db.sql("SELECT log_type FROM `tabEmployee Checkin`"))
    print(f"Updated: {updates}")
    print(f"Final IN/OUT: {dict(types)}")

    return updates