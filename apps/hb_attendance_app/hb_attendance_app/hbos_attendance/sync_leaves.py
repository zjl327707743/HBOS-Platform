import frappe, requests, os, json
from datetime import datetime

app_id = os.environ.get("FEISHU_APP_ID", "")
app_secret = os.environ.get("FEISHU_APP_SECRET", "")
resp = requests.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    json={"app_id": app_id, "app_secret": app_secret}, timeout=10)
token = resp.json().get("tenant_access_token")
headers = {"Authorization": "Bearer " + token}

APP_TOKEN = "PwSXbltzha1uG1sr38hcQzMrnwb"
TABLE_ID = "tblmcJzOXsi6zfy3"

# Read all records
all_recs = []
pt = None
while True:
    params = {"page_size": 500}
    if pt:
        params["page_token"] = pt
    r = requests.get(
        "https://open.feishu.cn/open-apis/bitable/v1/apps/" + APP_TOKEN + "/tables/" + TABLE_ID + "/records",
        params=params, headers=headers, timeout=10)
    data = r.json()
    items = data.get("data", {}).get("items", [])
    all_recs.extend(items)
    if not data.get("data", {}).get("has_more"):
        break
    pt = data.get("data", {}).get("page_token")

print("Total: " + str(len(all_recs)))

created = 0
updated = 0
skipped = 0

for item in all_recs:
    f = item.get("fields", {})
    status = f.get("申请状态", "")
    if status != "已通过":
        skipped += 1
        continue

    num = f.get("请假人员_工号", "")
    name = f.get("请假人员_姓名", "")
    start_ms = f.get("请假人员_开始时间", 0)
    end_ms = f.get("请假人员_结束时间", 0)
    days = f.get("请假人员_请假天数", 0)
    ltype = f.get("请假类型", "")
    reason = f.get("请假事由", "")
    source_id = f.get("SourceID", "") or ""

    if not num or not name:
        skipped += 1
        continue

    emp = frappe.db.get_value("Employee", {"employee_number": num}, "name")
    if not emp:
        emp = frappe.db.get_value("Employee", {"employee_name": name}, "name")
        if not emp:
            skipped += 1
            continue

    sd = datetime.fromtimestamp(start_ms / 1000).strftime("%Y-%m-%d") if start_ms else None
    ed = datetime.fromtimestamp(end_ms / 1000).strftime("%Y-%m-%d") if end_ms else None
    rid = "feishu-bitable-" + source_id

    existing = frappe.db.exists("HBOS Leave Record", {"feishu_approval_id": rid})
    if existing:
        doc = frappe.get_doc("HBOS Leave Record", {"feishu_approval_id": rid})
        is_new = False
    else:
        doc = frappe.get_doc({"doctype": "HBOS Leave Record", "feishu_approval_id": rid})
        is_new = True

    doc.update({
        "employee": emp, "leave_type": ltype or "",
        "start_date": sd, "end_date": ed,
        "leave_days": float(days) if days else 0,
        "approval_status": "已通过",
        "feishu_sync_time": frappe.utils.now_datetime(),
        "remarks": reason or "",
    })
    try:
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        if is_new:
            created += 1
        else:
            updated += 1
    except:
        skipped += 1

print("Created: " + str(created))
print("Updated: " + str(updated))
print("Skipped: " + str(skipped))
print("Total HBOS Leave Record: " + str(frappe.db.count("HBOS Leave Record")))
