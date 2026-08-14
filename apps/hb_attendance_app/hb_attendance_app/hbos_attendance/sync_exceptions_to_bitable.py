import frappe, requests, os
from datetime import datetime

app_id = os.environ.get("FEISHU_APP_ID", "")
app_secret = os.environ.get("FEISHU_APP_SECRET", "")
resp = requests.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    json={"app_id": app_id, "app_secret": app_secret}, timeout=10)
token = resp.json().get("tenant_access_token")

APP_TOKEN = "E1O7bnNhnasUoYsHy7qcAf2DnuU"
TABLE_ID = "tblbLOZa1A8nDJuM"
headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}

records = frappe.db.sql("""
    SELECT a.employee, a.employee_name, emp.employee_number, emp.department,
           a.attendance_date, a.late_entry, a.early_exit, a.shift,
           (SELECT MIN(ec.time) FROM `tabEmployee Checkin` ec
            WHERE ec.employee = a.employee AND DATE(ec.time) = a.attendance_date) as first_checkin,
           (SELECT MAX(ec.time) FROM `tabEmployee Checkin` ec
            WHERE ec.employee = a.employee AND DATE(ec.time) = a.attendance_date) as last_checkin
    FROM tabAttendance a
    LEFT JOIN tabEmployee emp ON emp.name = a.employee
    WHERE (a.late_entry = 1 OR a.early_exit = 1)
      AND a.docstatus < 2
    ORDER BY a.attendance_date DESC, a.employee_name ASC
""", as_dict=True)

total = len(records)
print("Total records:", total)

created = 0
errors = 0
BATCH = 100

for bi in range(0, total, BATCH):
    chunk = records[bi:bi + BATCH]
    batch = []

    for r in chunk:
        ex_type = "迟到"
        if r.late_entry and r.early_exit:
            ex_type = "迟到+早退"
        elif r.early_exit:
            ex_type = "早退"
        first = str(r.first_checkin.strftime("%H:%M:%S")) if r.first_checkin else ""
        last = str(r.last_checkin.strftime("%H:%M:%S")) if r.last_checkin else ""
        batch.append({"fields": {
            "姓名": str(r.employee_name or ""),
            "工号": str(r.employee_number or ""),
            "部门": str(r.department or ""),
            "考勤日期": str(r.attendance_date),
            "异常类型": ex_type,
            "班次": str(r.shift or ""),
            "首次打卡": first,
            "末次打卡": last,
            "唯一键": str(r.employee) + "_" + str(r.attendance_date),
        }})

    resp = requests.post(
        "https://open.feishu.cn/open-apis/bitable/v1/apps/" + APP_TOKEN + "/tables/" + TABLE_ID + "/records/batch_create",
        headers=headers, json={"records": batch}, timeout=120)
    result = resp.json()
    if result.get("code") == 0:
        created += len(batch)
    else:
        errors += len(batch)
        print("  Batch " + str(bi // BATCH + 1) + " error: " + str(result.get("msg", "")))

    print("  " + str(created) + "/" + str(total))

print("\n=== DONE ===")
print("Created: " + str(created))
print("Errors: " + str(errors))
print("URL: https://j0eukrlohu.feishu.cn/base/" + APP_TOKEN + "?table=" + TABLE_ID)
