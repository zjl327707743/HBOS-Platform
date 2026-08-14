import frappe
import requests
import os
import json
import hashlib
import time
from datetime import datetime

# DeliCloud API credentials
k = os.environ.get("DELICLOUD_APP_KEY", "")
s = os.environ.get("DELICLOUD_APP_SECRET", "")
PATH = "/v2.0/cloudappapi"
BASE = "https://v2-api.delicloud.com"


def _call(cmd, body=None):
    ts = str(int(time.time() * 1000))
    sig = hashlib.md5((PATH + ts + k + s).encode()).hexdigest().lower()
    h = {
        "Content-Type": "application/json; charset=UTF-8",
        "App-Key": k,
        "App-Timestamp": ts,
        "App-Sig": sig,
        "Api-Module": "CHECKIN",
        "Api-Cmd": cmd,
    }
    r = requests.post(BASE + PATH, json=body or {}, headers=h, timeout=30)
    return r.json()


# Step 1: Init
init_r = _call("checkin_query_init")
print("Init: %s" % init_r.get("code"))

# Step 2: Fetch all records from last checkpoint
nid = frappe.cache().get_value("delicloud_next_id") or 0
try:
    nid = int(nid)
except Exception:
    nid = 0

all_recs = []
loops = 0
while loops < 200:
    r = _call("checkin_query", {"next_id": nid, "page_size": 500})
    if r.get("code") != 0:
        break
    items = r.get("data", {}).get("data", [])
    nn = r.get("data", {}).get("next_id", 0)
    all_recs.extend(items)
    loops += 1
    if not items or nn == nid:
        break
    nid = nn

print("Fetched: %d records" % len(all_recs))

# Step 3: Pre-fetch employee lookup
emp_lookup = {}
for e in frappe.db.get_all("Employee", fields=["name", "employee_number"]):
    if e["employee_number"]:
        emp_lookup[e["employee_number"]] = e["name"]

print("Employee lookup: %d" % len(emp_lookup))

# Step 4: Insert checkins
created = 0
skipped = 0
for rec in all_recs:
    cd = rec.get("check_data", "{}")
    try:
        cd = json.loads(cd) if isinstance(cd, str) else cd
    except Exception:
        cd = {}
    emp_num = cd.get("employee_num", "")
    cts = rec.get("check_time", 0)
    if not emp_num or not cts:
        skipped += 1
        continue
    emp = emp_lookup.get(emp_num)
    if not emp:
        skipped += 1
        continue
    try:
        cdt = datetime.fromtimestamp(int(cts))
        ts_str = cdt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        skipped += 1
        continue
    if frappe.db.exists("Employee Checkin", {"employee": emp, "time": ts_str}):
        continue
    try:
        doc = frappe.get_doc(
            {
                "doctype": "Employee Checkin",
                "employee": emp,
                "time": ts_str,
                "log_type": "IN",
            }
        )
        doc.insert(ignore_permissions=True)
        created += 1
    except Exception:
        skipped += 1
    if created > 0 and created % 300 == 0:
        frappe.db.commit()
        print("  %d checkins..." % created)

frappe.db.commit()

# Save checkpoint
if all_recs:
    frappe.cache().set_value("delicloud_next_id", all_recs[-1].get("id", nid))

print("\n=== STEP 1 COMPLETE ===")
print("Created: %d" % created)
print("Skipped: %d" % skipped)
