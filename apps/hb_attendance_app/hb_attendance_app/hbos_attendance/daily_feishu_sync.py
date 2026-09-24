import frappe, requests, os, json
from collections import Counter
from datetime import datetime, timedelta, date
from collections import defaultdict

# ADMIN_NUMS 从唯一来源导入（rule_lists.py，经 api 再导出）。
# 曾经此处自建过一份 221 人的副本，与判定的 178 人差 71 个工号，
# 导致同一人同一天「判定判缺勤、飞书不算缺勤」。Owner 2026-09-24 裁定以
# rule_lists.py 为准，故此处不再自建，直接引用。
# ADMIN_NUMS 与 SPECIAL_SHIFT_NUMS 均从唯一来源导入，不自建副本。
# 曾经此处另有两份本地名单，都已分叉：
#   ADMIN_NUMS（221 人）与判定的 178 人差 71 个工号；
#   WUJUN_NUMS（48 人）是旧无菌名单，已被 SPECIAL_SHIFT_NUMS（59 人）取代，
#   且其中混入 3 名设备动力部人员、漏掉 14 名无菌车间人员。
# 违反「一个业务含义只留一份名单」会直接造成同一人两套结论，故一律引用。
from hb_attendance_app.hbos_attendance.api import ADMIN_NUMS, EXEMPT_NUMS
from hb_attendance_app.hbos_attendance.pairing import SPECIAL_SHIFT_NUMS

# 飞书异常汇总排除名单：这些人的迟到/缺勤一律不进飞书报告。
#
# 结构（2026-09-24 复核）：
#   EXEMPT_NUMS      豁免名单（管理层等），权威定义在 rule_lists.py
#   下面手工那 20 人 飞书侧额外排除，实际横跨 7 个部门，并非只有食堂/无菌
#
# ⚠️ 已知冗余与待定项（本文件上方那段注释里说的「理清」就是指这里）：
#   · 20 人中有 7 人（11009035-40、11009042）已属 SPECIAL_SHIFT_NUMS 无菌体系；
#   · 另有 7 人（11009046-52）已属 FOOD_NUMS 食堂名单；
#   · 剩 6 人（11009033 市场部、11009034 财务部、11009041 无菌车间、
#     11009043 设备动力部、11009044 质量保证部、11009045 质量控制部）
#     看不出属于哪个既有名单，疑似「因个人原因不报」的一次性手工排除。
#
# ⚠️ 未改动的原因：把上面 14 个冗余项删掉、改为引用 SPECIAL/FOOD 并不能保持
#   行为不变——SPECIAL_SHIFT_NUMS 有 59 人，其中 52 人从未进过本排除名单。
#   即「无菌是否应当整批排除」这一口径本身未定，属业务问题，留待 Owner 裁定。
EXCLUDE_NUMS = set(EXEMPT_NUMS) | {
    '11009034','11009043','11009033','11009052','11009046','11009050','11009051',
    '11009048','11009049','11009047','11009042','11009041','11009038','11009040',
    '11009037','11009039','11009036','11009035','11009044','11009045'
}

def daily_sync_to_feishu():
    """每天10点自动同步异常考勤到飞书多维表格"""
    try:
        app_id = os.environ.get("FEISHU_APP_ID", "")
        app_secret = os.environ.get("FEISHU_APP_SECRET", "")
        resp = requests.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": app_id, "app_secret": app_secret}, timeout=10)
        token = resp.json().get("tenant_access_token")
        headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}

        today = date.today()
        month_start = today.replace(day=1)
        start_str = month_start.strftime("%Y-%m-%d")
        end_str = today.strftime("%Y-%m-%d")

        # Leave dates
        leaves = frappe.db.get_all("HBOS Leave Record", filters={"approval_status": "已通过"},
            fields=["employee", "start_date", "end_date"])
        emp_leave_dates = {}
        for l in leaves:
            emp = l.employee; sd = l.start_date; ed = l.end_date
            if not sd or not ed: continue
            d = sd
            while d <= ed:
                if emp not in emp_leave_dates: emp_leave_dates[emp] = set()
                emp_leave_dates[emp].add(str(d))
                d += timedelta(days=1)

        # Query HBOS from month start to today
        atts = frappe.db.sql("""
            SELECT a.employee, emp.employee_name, emp.employee_number, emp.department,
                   a.attendance_date, a.late_entry, a.status, a.shift
            FROM tabAttendance a
            JOIN tabEmployee emp ON emp.name = a.employee
            WHERE a.attendance_date BETWEEN %s AND %s
              AND a.name LIKE 'HBOS-ATT-%%'
        """, (start_str, end_str), as_dict=True)

        emp_data = defaultdict(lambda: {"late_dates": [], "absent_dates": [], "name": "", "num": "", "dept": ""})
        for r in atts:
            num = r.employee_number
            if num in EXCLUDE_NUMS: continue
            emp_data[num]["name"] = r.employee_name or ""
            emp_data[num]["num"] = num
            emp_data[num]["dept"] = r.department or ""
            ds = str(r.attendance_date)
            if r.late_entry:
                emp_data[num]["late_dates"].append(ds[5:])
            if r.status == "Absent" and r.shift != "双休":
                is_leave = ds in emp_leave_dates.get(r.employee, set())
                if not is_leave:
                    emp_data[num]["absent_dates"].append(ds[5:])

        # Zero-checkin absent
        weekends = set()
        d = month_start
        while d <= today:
            if d.weekday() >= 5:  # Saturday=5, Sunday=6
                weekends.add(d.strftime("%Y-%m-%d"))
            d += timedelta(days=1)

        d = month_start
        while d <= today:
            ds = d.strftime("%Y-%m-%d")
            has_ck = frappe.db.sql("SELECT DISTINCT ec.employee FROM `tabEmployee Checkin` ec WHERE DATE(ec.time) = %s", ds, as_dict=True)
            has_ck_set = set(c["employee"] for c in has_ck)
            all_emps = frappe.db.get_all("Employee", filters={"status": "Active"}, fields=["name", "employee_name", "employee_number", "department"])
            for e in all_emps:
                num = e["employee_number"]
                if num in EXCLUDE_NUMS: continue
                if num in ADMIN_NUMS and num not in SPECIAL_SHIFT_NUMS and ds in weekends:
                    continue
                if e["name"] not in has_ck_set:
                    if not emp_data[num]["num"]:
                        emp_data[num] = {"late_dates": [], "absent_dates": [], "name": e["employee_name"] or "", "num": num, "dept": e["department"] or ""}
                    is_leave = ds in emp_leave_dates.get(e["name"], set())
                    if not is_leave:
                        emp_data[num]["absent_dates"].append(ds[5:])
            d += timedelta(days=1)

        rows = []
        for num, data in emp_data.items():
            if not data["late_dates"] and not data["absent_dates"]: continue
            rows.append({
                "name": data["name"], "num": data["num"], "dept": data["dept"],
                "late_count": len(data["late_dates"]),
                "absent_count": len(data["absent_dates"]),
                "late_detail": "  ".join(sorted(data["late_dates"])),
                "absent_detail": "  ".join(sorted(data["absent_dates"])),
            })
        rows.sort(key=lambda x: (-x["late_count"] - x["absent_count"], x["num"]))

        # Create new Bitable
        month_name = today.strftime("%m月")
        day_range = start_str[5:] + "-" + end_str[5:]
        r = requests.post("https://open.feishu.cn/open-apis/bitable/v1/apps",
            headers=headers, json={"name": month_name + day_range + "异常汇总"}, timeout=10)
        APP_TOKEN = r.json()["data"]["app"]["app_token"]
        TABLE_ID = r.json()["data"]["app"]["default_table_id"]

        rf = requests.get(f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/fields", headers=headers, timeout=10)
        for f in rf.json().get("data", {}).get("items", []):
            requests.delete(f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/fields/{f['field_id']}", headers=headers, timeout=10)

        for fn in ["姓名","工号","部门","迟到次数","缺勤天数","迟到日期","缺勤日期"]:
            requests.post(f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/fields",
                headers=headers, json={"field_name": fn, "type": 1}, timeout=10)

        requests.patch(f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}",
            headers=headers, json={"name": "考勤异常汇总"}, timeout=10)

        # Grant full access + transfer ownership
        YOUR_OPEN_ID = "ou_968a3e1bb42aff62b69dbf71076de8a6"
        requests.post(f"https://open.feishu.cn/open-apis/drive/v1/permissions/{APP_TOKEN}/members?type=bitable",
            headers=headers, json={"member_type": "openid", "member_id": YOUR_OPEN_ID, "perm": "full_access"}, timeout=10)
        requests.post(f"https://open.feishu.cn/open-apis/drive/v1/permissions/{APP_TOKEN}/members/transfer_owner?type=bitable",
            headers=headers, json={"member_type": "openid", "member_id": YOUR_OPEN_ID}, timeout=10)

        # Write data
        created = 0
        for bi in range(0, len(rows), 100):
            chunk = rows[bi:bi+100]
            batch = [{"fields": {"姓名": r["name"], "工号": r["num"], "部门": r["dept"], "迟到次数": str(r["late_count"]), "缺勤天数": str(r["absent_count"]), "迟到日期": r["late_detail"], "缺勤日期": r["absent_detail"]}} for r in chunk]
            resp = requests.post(f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/batch_create",
                headers=headers, json={"records": batch}, timeout=120)
            if resp.json().get("code") == 0: created += len(batch)

        frappe.log(f"Daily Feishu sync: {created} records, {len(rows)} employees, URL: https://j0eukrlohu.feishu.cn/base/{APP_TOKEN}", "feishu_daily_sync")
        return f"OK: {created} records"
    except Exception as e:
        frappe.log_error(str(e), "feishu_daily_sync")
        return f"Error: {e}"
