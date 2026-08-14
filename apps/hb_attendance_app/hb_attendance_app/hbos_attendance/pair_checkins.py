import frappe, requests, os, json, time
from datetime import datetime, timedelta
from collections import defaultdict

# ===== SHIFT RULES =====
# 行政班: 8:30-17:30, early 4:30-8:30, late >8:30
# 早班:   8:00-16:00, early 4:00-8:00, late >8:00
# 中班:   16:00-0:00, early 12:00-16:00, late >16:00, cross-day
# 夜班:   0:00-8:00,  early 20:00(prev)-0:00, late >0:00, cross-day

ADMIN_NUMS = {
    '10006001','10006002','10006020','10006022','10006030',
    '10007003','10007004','10007007','10007008','10007009',
    '10008003','10008004','10008005','10008007','10008008','10008009','10008010','10008011','10008012','10008013',
    '10008016','10008019','10008021','10008022','10008023','10008025','10008026','10008027',
    '10009002','10009004','10009005','10009006','10009007','10009008','10009009','10009010','10009011','10009013',
    '10009014','10009015','10009016','10009018','10009022','10009023','10009024','10009029',
    '10010003','10010004','10010005','10010006','10010008','10010012',
    '10011001','10011002','10011003','10011005','10011006',
    '10012010',
    '10013002','10013003','10013004','10013005','10013006','10013007','10013008','10013012','10013013','10013017','10013018','10013022',
    '10014005','10014016','10014017','10014022',
    '10016001','10016002','10016004','10016005',
    '11001003','11001004','11001008','11001010',
    '11002001','11002002','11002003','11002004','11002006','11002007',
    '11003003','11003052','11003055','11003056',
    '11004002','11004004','11004006','11004007','11004010','11004011','11004012','11004014','11004049','11004050',
    '11005005','11005006','11005007','11005008',
    '11006002','11006003','11006005','11006006','11006007','11006008','11006009','11006010','11006011','11006012',
    '11006093','11006104','11006105','11006107','11006112',
    '11007002','11007003','11007004',
    '11008002','11008004','11008005','11008011','11008012',
    '11009011','11009026','11009028','11009030','11009032','11009041','11009042','11009043','11009045',
}

def get_shift_and_late(ck_time, emp_num=""):
    if emp_num in ADMIN_NUMS:
        ts = ck_time.strftime("%H:%M:%S")
        return ("行政班", ts > "08:30:00")
    h = ck_time.hour
    m = ck_time.minute
    t = h * 60 + m  # minutes since midnight
    ts = ck_time.strftime("%H:%M:%S")

    # 夜班: 20:00-23:59 (提前) or 0:00-4:00 (上班时间)
    if h >= 20 or h < 4:
        late = h >= 0 and ts > "00:00:00" and h < 4  # 0:01+ = late
        if h >= 20:
            late = False  # 20:00+ = early, not late
        return ("夜班", late)

    # 早班: 4:00-8:00 (提前), 行政班: 4:30-8:30
    if 4 <= h < 6:
        return ("早班", False)  # very early, always 早班
    if 6 <= h < 8:
        return ("早班", False)  # early for 早班

    # 8:00-8:30 ambiguous: 早班(late) or 行政班(on time)
    if h == 8:
        if m < 30:
            return ("早班", m > 0)  # 8:01-8:29 = 早班迟到, 8:00=OK
        else:
            return ("行政班", m > 30)  # 8:31+ = 行政班迟到, 8:30=OK

    # 9:00-12:00: 行政班迟到 or 早班迟到
    if 9 <= h < 12:
        return ("行政班", True)

    # 12:00-16:00: 中班(提前)
    if 12 <= h < 16:
        return ("中班", False)

    # 16:00-20:00: 中班
    if 16 <= h < 20:
        return ("中班", ts > "16:00:00")

    return ("夜班", False)


# ===== STEP 1: Load checkins =====
all_cks = frappe.db.sql("""
    SELECT ec.employee, ec.time,
           emp.employee_name, emp.employee_number, emp.department
    FROM `tabEmployee Checkin` ec
    JOIN tabEmployee emp ON emp.name = ec.employee
    WHERE DATE(ec.time) BETWEEN '2026-07-28' AND '2026-08-04'
    ORDER BY ec.employee, ec.time
""", as_dict=True)

by_emp = defaultdict(list)
for ck in all_cks:
    by_emp[ck["employee"]].append(ck)

# ===== STEP 2: Greedy pairing =====
pairs = []
missing = []

for eid, cks in by_emp.items():
    cks.sort(key=lambda x: x["time"])
    used = [False] * len(cks)

    for i in range(len(cks)):
        if used[i]:
            continue
        ck1 = cks[i]

        # Find closest next checkin within 0.5-18h
        best_j = -1
        for j in range(i + 1, len(cks)):
            if used[j]:
                continue
            gap = (cks[j]["time"] - ck1["time"]).total_seconds() / 3600
            if 0.5 <= gap <= 18:
                best_j = j
                break

        if best_j == -1:
            missing.append({
                "employee_name": ck1["employee_name"], "employee_number": ck1["employee_number"],
                "department": ck1["department"], "time": ck1["time"]
            })
            used[i] = True
            continue

        ck2 = cks[best_j]
        used[i] = True
        used[best_j] = True

        shift, late = get_shift_and_late(ck1["time"], ck1.get("employee_number", ""))

        pairs.append({
            "employee_name": ck1["employee_name"], "employee_number": ck1["employee_number"],
            "department": ck1["department"], "in_time": ck1["time"], "out_time": ck2["time"],
            "shift": shift, "late": late,
            "gap_h": round((ck2["time"] - ck1["time"]).total_seconds() / 3600, 1)
        })

print("Total pairs: " + str(len(pairs)))
print("Total missing: " + str(len(missing)))

# ===== STEP 3: Filter 8/1-8/2 =====
aug_pairs = [p for p in pairs if "2026-08-01" <= p["in_time"].strftime("%Y-%m-%d") <= "2026-08-02"]
aug_late = [p for p in aug_pairs if p["late"]]
aug_missing = [m for m in missing if "2026-08-01" <= m["time"].strftime("%Y-%m-%d") <= "2026-08-02"]

print("\n8/1-8/2 pairs: " + str(len(aug_pairs)))
print("8/1-8/2 late: " + str(len(aug_late)))
print("8/1-8/2 missing: " + str(len(aug_missing)))

# Check key people
for name in ["张小贞", "邱磊"]:
    print("\n=== " + name + " ===")
    for p in pairs:
        if p["employee_name"] == name:
            tag = "迟到" if p["late"] else "OK"
            print("  " + p["in_time"].strftime("%m-%d") + " | " + p["shift"] + " | " + p["in_time"].strftime("%H:%M") + "→" + p["out_time"].strftime("%m-%d %H:%M") + " | gap=" + str(p["gap_h"]) + "h | " + tag)
    for m in missing:
        if m["employee_name"] == name:
            print("  缺卡: " + m["time"].strftime("%m-%d %H:%M"))

# ===== STEP 4: Write to Feishu =====
app_id = os.environ.get("FEISHU_APP_ID", "")
app_secret = os.environ.get("FEISHU_APP_SECRET", "")
resp = requests.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    json={"app_id": app_id, "app_secret": app_secret}, timeout=10)
token = resp.json().get("tenant_access_token")
headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}

APP_TOKEN = "XtAcbZlYiaIS0isKsXKcu8i7nIT"
TABLE_ID = "tblCKtlHkx748aK6"

# Delete old
all_ids = []
pt = None
while True:
    params = {"page_size": 500}
    if pt: params["page_token"] = pt
    r = requests.get(f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records",
        params=params, headers=headers, timeout=10)
    for item in r.json().get("data", {}).get("items", []):
        all_ids.append(item["record_id"])
    if not r.json().get("data", {}).get("has_more"): break
    pt = r.json().get("data", {}).get("page_token")

for i in range(0, len(all_ids), 500):
    chunk = all_ids[i:i+500]
    requests.delete(f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/batch_delete",
        headers=headers, json={"records": chunk}, timeout=30)
print("Deleted: " + str(len(all_ids)))

# Merge
results = {}
for p in aug_late:
    key = (p["employee_number"] or "") + "_" + p["in_time"].strftime("%Y-%m-%d")
    out_d = (p["out_time"].strftime("%m-%d %H:%M") if p["out_time"].date() != p["in_time"].date()
             else p["out_time"].strftime("%H:%M"))
    results[key] = {
        "employee_name": p["employee_name"], "employee_number": p["employee_number"],
        "department": p["department"], "attendance_date": p["in_time"].strftime("%Y-%m-%d"),
        "category": "迟到", "shift": p["shift"],
        "first_ck": p["in_time"].strftime("%H:%M"), "last_ck": out_d
    }

for m in aug_missing:
    key = (m["employee_number"] or "") + "_" + m["time"].strftime("%Y-%m-%d")
    if key not in results:
        results[key] = {
            "employee_name": m["employee_name"], "employee_number": m["employee_number"],
            "department": m["department"], "attendance_date": m["time"].strftime("%Y-%m-%d"),
            "category": "缺卡", "shift": "",
            "first_ck": m["time"].strftime("%H:%M"), "last_ck": ""
        }
    else:
        results[key]["category"] = results[key]["category"] + "+缺卡"

rows = sorted(results.values(), key=lambda x: (x["attendance_date"], x["employee_number"]))
print("Rows: " + str(len(rows)))

created = 0
BATCH = 100
for bi in range(0, len(rows), BATCH):
    chunk = rows[bi:bi + BATCH]
    batch = [{"fields": {
        "姓名": r["employee_name"], "工号": r["employee_number"],
        "部门": r["department"], "考勤日期": r["attendance_date"],
        "异常类别": r["category"], "班次": r["shift"],
        "首次打卡": r["first_ck"], "末次打卡": r["last_ck"],
    }} for r in chunk]
    resp = requests.post(
        f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/batch_create",
        headers=headers, json={"records": batch}, timeout=120)
    if resp.json().get("code") == 0:
        created += len(batch)
    print("  " + str(created) + "/" + str(len(rows)))

print("\nDONE: " + str(created))
print("https://j0eukrlohu.feishu.cn/base/" + APP_TOKEN + "?table=" + TABLE_ID)
