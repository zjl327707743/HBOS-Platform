import frappe, requests, os, json
from collections import Counter
from datetime import datetime, timedelta, date
from collections import defaultdict

from hb_attendance_app.hbos_attendance.api import EXEMPT_NUMS

# 飞书异常汇总排除名单 = 豁免名单(EXEMPT_NUMS, 82人) + 飞书侧额外排除的食堂/无菌工号
EXCLUDE_NUMS = set(EXEMPT_NUMS) | {
    '11009034','11009043','11009033','11009052','11009046','11009050','11009051',
    '11009048','11009049','11009047','11009042','11009041','11009038','11009040',
    '11009037','11009039','11009036','11009035','11009044','11009045'
}

WUJUN_NUMS = {
    '10014020','10015055','11004008',
    '11008005','11008007','11008009','11008011','11008012','11008013','11008015','11008016','11008017','11008018','11008019','11008020','11008021','11008023','11008024','11008026','11008027','11008028','11008029','11008030','11008031','11008032','11008034','11008035','11008037','11008038','11008039','11008040','11008041','11008043','11008045','11008046','11008047','11008048','11008049','11008050','11008052','11008054','11008055','11008056','11008057','11008058','11008059','11008060','11008063',
}

ADMIN_NUMS = {
    '10003001','10003003','10003006','10004003','10004005','10004006','10004020','10004022','10006001','10006002','10006020','10006022','10006030','10007003','10007004','10007007','10007008','10007009','10008003','10008004','10008005','10008007','10008008','10008009','10008010','10008011','10008012','10008013','10008015','10008016','10008019','10008021','10008022','10008023','10008025','10008026','10008027','10009002','10009004','10009005','10009006','10009007','10009008','10009009','10009010','10009011','10009013','10009014','10009015','10009016','10009018','10009022','10009023','10009024','10009029','10010003','10010004','10010005','10010006','10010008','10010012','10011001','10011002','10011003','10011005','10011006','10012003','10012005','10012008','10012009','10012010','10013002','10013003','10013004','10013005','10013006','10013007','10013008','10013012','10013013','10013017','10013018','10013022','10014005','10014007','10014016','10014017','10014022','10015001','10015002','10015003','10015004','10015005','10015006','10015007','10015008','10015009','10015010','10015011','10015012','10015013','10015015','10015016','10015018','10015019','10015021','10015022','10015023','10015025','10015026','10015028','10015030','10015031','10015035','10015036','10015039','10015040','10015042','10015043','10015045','10015046','10015047','10015048','10015051','10015052','10015053','10015056','10015057','10015058','10015060','10015061','10015062','10015063','10015064','10015065','10015066','10015068','10015069','10015071','10016001','10016002','10016003','10016004','10016005','11001003','11001004','11001005','11001006','11001007','11001008','11001010','11001018','11002001','11002002','11002003','11002004','11002006','11002007','11003003','11003052','11003055','11003056','11004002','11004004','11004006','11004007','11004010','11004011','11004012','11004014','11004049','11004050','11005005','11005006','11005007','11005008','11006002','11006003','11006005','11006006','11006007','11006008','11006009','11006010','11006011','11006012','11006093','11006104','11006105','11006107','11006112','11007002','11007003','11007004','11008002','11008004','11008011','11008012','11009003','11009006','11009007','11009008','11009011','11009016','11009017','11009018','11009019','11009020','11009021','11009026','11009028','11009030','11009032','11009033','11009034','11009041','11009042','11009043','11009044','11009045'
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
                if num in ADMIN_NUMS and num not in WUJUN_NUMS and ds in weekends:
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
