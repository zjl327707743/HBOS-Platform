"""飞书多维表格请假/加班数据同步 + 得力云考勤机同步"""
import frappe
import json
import requests
from datetime import datetime


# 飞书多维表格固定配置
BITABLE_APP_TOKEN = "DNTYbsdcRaomxksiKgNccgXonKg"
BITABLE_TABLE_ID = "tblINWQsvCeHn3gZ"
OVERTIME_BITABLE_APP_TOKEN = "Tb0YwuXY6iglUXkzpcWc5EADnxe"
OVERTIME_BITABLE_TABLE_ID = "tblIQlEJk7TcxItX"
DELICLOUD_PATH = "/v2.0/cloudappapi"

STATUS_MAP = {
    "已通过": "已通过", "审批中": "审批中", "已拒绝": "已驳回",
    "已撤回": "已撤销", "已驳回": "已驳回", "已撤销": "已撤销",
}


# ==================== 飞书请假同步 ====================

@frappe.whitelist()
def sync_from_bitable():
    try: token = _get_token(); records = _fetch_all_records(token)
    except Exception as e: frappe.log_error(str(e), "飞书同步"); frappe.throw(f"读取飞书表格失败: {e}")
    created = updated = skipped = 0
    for record in records:
        fields = record.get("fields", {}); rid = record.get("id", "")
        name = fields.get("姓名", ""); emp_num = fields.get("工号", "")
        if not name or not emp_num: skipped += 1; continue
        emp = frappe.db.get_value("Employee", {"employee_number": emp_num}, "name")
        if not emp: skipped += 1; continue
        st = fields.get("开始时间", 0) or 0; et = fields.get("结束时间", 0) or 0
        sd = datetime.fromtimestamp(st/1000).strftime("%Y-%m-%d") if st else None
        ed = datetime.fromtimestamp(et/1000).strftime("%Y-%m-%d") if et else None
        aid = f"feishu-bitable-{rid}"
        if frappe.db.exists("HBOS Leave Record", {"feishu_approval_id": aid}):
            doc = frappe.get_doc("HBOS Leave Record", {"feishu_approval_id": aid}); is_new = False
        else: doc = frappe.get_doc({"doctype": "HBOS Leave Record", "feishu_approval_id": aid}); is_new = True
        doc.update({"employee": emp, "leave_type": fields.get("请假类型", ""), "start_date": sd, "end_date": ed,
                     "leave_days": float(fields.get("请假天数", 0) or 0),
                     "approval_status": STATUS_MAP.get(fields.get("申请状态", ""), "审批中"),
                     "feishu_sync_time": frappe.utils.now_datetime(), "remarks": fields.get("请假事由", "")})
        try: doc.save(ignore_permissions=True); frappe.db.commit(); created += 1 if is_new else updated; updated += 0 if is_new else 1
        except Exception: skipped += 1
    return {"total": len(records), "created": created, "updated": updated, "skipped": skipped}


# ==================== 飞书加班同步 ====================

@frappe.whitelist()
def sync_overtime_from_bitable():
    try: token = _get_token(); records = _fetch_all_records_custom(token, OVERTIME_BITABLE_APP_TOKEN, OVERTIME_BITABLE_TABLE_ID)
    except Exception as e: frappe.log_error(str(e), "飞书加班同步"); frappe.throw(f"读取飞书加班表格失败: {e}")
    created = updated = skipped = 0
    for record in records:
        fields = record.get("fields", {}); rid = record.get("id", "")
        name = fields.get("加班人员明细_姓名", ""); emp_num = fields.get("加班人员明细_工号", "")
        if not name or not emp_num: skipped += 1; continue
        emp = frappe.db.get_value("Employee", {"employee_number": emp_num}, "name")
        if not emp: skipped += 1; continue
        st = fields.get("加班人员明细_开始时间", 0) or 0; et = fields.get("加班人员明细_结束时间", 0) or 0
        sd = datetime.fromtimestamp(st/1000).strftime("%Y-%m-%d %H:%M:%S") if st else None
        ed = datetime.fromtimestamp(et/1000).strftime("%Y-%m-%d %H:%M:%S") if et else None
        aid = f"feishu-bitable-overtime-{rid}"
        if frappe.db.exists("HBOS Overtime Record", {"feishu_approval_id": aid}):
            doc = frappe.get_doc("HBOS Overtime Record", {"feishu_approval_id": aid}); is_new = False
        else: doc = frappe.get_doc({"doctype": "HBOS Overtime Record", "feishu_approval_id": aid}); is_new = True
        doc.update({"employee": emp, "overtime_type": "工作日加班", "start_time": sd, "end_time": ed,
                     "duration_hours": float(fields.get("加班人员明细_时长", 0) or 0),
                     "approval_status": STATUS_MAP.get(fields.get("申请状态", ""), "审批中"),
                     "feishu_sync_time": frappe.utils.now_datetime(), "overtime_reason": fields.get("加班原因", "")})
        try: doc.save(ignore_permissions=True); frappe.db.commit(); created += 1 if is_new else updated; updated += 0 if is_new else 1
        except Exception: skipped += 1
    return {"total": len(records), "created": created, "updated": updated, "skipped": skipped}


# ==================== 得力云考勤机同步 ====================

def _delicloud_call(cmd, body=None):
    import os, hashlib, time as tmod
    k = os.environ.get("DELICLOUD_APP_KEY", ""); s = os.environ.get("DELICLOUD_APP_SECRET", "")
    ts = str(int(tmod.time() * 1000))
    sig = hashlib.md5((DELICLOUD_PATH + ts + k + s).encode()).hexdigest().lower()
    h = {"Content-Type": "application/json; charset=UTF-8", "App-Key": k, "App-Timestamp": ts, "App-Sig": sig,
         "Api-Module": "CHECKIN", "Api-Cmd": cmd}
    r = requests.post("https://v2-api.delicloud.com" + DELICLOUD_PATH, json=body or {}, headers=h, timeout=30)
    return r.json()


@frappe.whitelist()
def sync_delicloud_checkin():
    try:
        from datetime import datetime as dt_mod
        init_r = _delicloud_call("checkin_query_init")
        if init_r.get("code") != 0: frappe.throw("得力云初始化失败")

        last_id = frappe.cache.get_value("delicloud_next_id") or 0
        try: last_id = int(last_id)
        except Exception: last_id = 0

        all_recs = []; nid = last_id; loops = 200
        while loops > 0:
            r = _delicloud_call("checkin_query", {"next_id": nid, "page_size": 500})
            if r.get("code") != 0: break
            items = r.get("data", {}).get("data", []); all_recs.extend(items)
            nn = r.get("data", {}).get("next_id", 0)
            if not items or nn == nid: break
            nid = nn; loops -= 1

        if not all_recs: return {"total": 0, "created": 0, "skipped": 0}

        created = skipped = 0
        for rec in all_recs:
            cd = rec.get("check_data", "{}")
            try: cd = json.loads(cd) if isinstance(cd, str) else cd
            except Exception: cd = {}
            emp_num = cd.get("employee_num", ""); cts = rec.get("check_time", 0)
            if not emp_num or not cts: skipped += 1; continue
            emp = frappe.db.get_value("Employee", {"employee_number": emp_num}, "name")
            if not emp: skipped += 1; continue
            try: cdt = dt_mod.fromtimestamp(cts); ts = cdt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception: skipped += 1; continue
            lt = "IN"
            if frappe.db.exists("Employee Checkin", {"employee": emp, "time": ts}): continue
            try:
                doc = frappe.get_doc({"doctype": "Employee Checkin", "employee": emp, "time": ts, "log_type": lt})
                doc.insert(ignore_permissions=True); created += 1
            except Exception: skipped += 1

        frappe.db.commit()
        if all_recs:
            lid = all_recs[-1].get("id", nid)
            frappe.cache.set_value("delicloud_next_id", lid)

        # Run auto attendance after sync
        from hrms.hr.doctype.shift_type.shift_type import process_auto_attendance_for_all_shifts
        process_auto_attendance_for_all_shifts()

        # Generate attendance for any checkin dates without attendance
        frappe.db.sql("""
            INSERT IGNORE INTO tabAttendance (name, employee, attendance_date, status, shift, late_entry, early_exit, docstatus, creation, modified, owner, modified_by)
            SELECT CONCAT('HBOS-ATT-', ec.employee, '-', DATE(ec.time)), ec.employee, DATE(ec.time), 'Present', '早班', 0, 0, 1, NOW(), NOW(), 'Administrator', 'Administrator'
            FROM `tabEmployee Checkin` ec
            WHERE NOT EXISTS (SELECT 1 FROM tabAttendance a WHERE a.employee = ec.employee AND a.attendance_date = DATE(ec.time))
            GROUP BY ec.employee, DATE(ec.time)
        """)

        # Step A: single checkin → Absent
        frappe.db.sql("""UPDATE tabAttendance a SET a.status = 'Absent'
            WHERE (SELECT COUNT(*) FROM `tabEmployee Checkin` ec WHERE ec.employee = a.employee AND DATE(ec.time) = a.attendance_date) = 1""")

        # Step B: 中班 cross-day pair (14:00-23:59 + next day 00:00-10:00) → Present
        frappe.db.sql("""UPDATE tabAttendance a SET a.status = 'Present' WHERE a.status = 'Absent'
            AND (SELECT COUNT(*) FROM `tabEmployee Checkin` ec WHERE ec.employee = a.employee AND DATE(ec.time) = a.attendance_date) = 1
            AND EXISTS (SELECT 1 FROM `tabEmployee Checkin` ec WHERE ec.employee = a.employee AND DATE(ec.time) = a.attendance_date AND TIME(ec.time) BETWEEN '14:00:00' AND '23:59:59')
            AND EXISTS (SELECT 1 FROM `tabEmployee Checkin` ec WHERE ec.employee = a.employee AND DATE(ec.time) = DATE_ADD(a.attendance_date, INTERVAL 1 DAY) AND TIME(ec.time) BETWEEN '00:00:00' AND '10:00:00'
                AND (SELECT COUNT(*) FROM `tabEmployee Checkin` ec2 WHERE ec2.employee = a.employee AND DATE(ec2.time) = DATE_ADD(a.attendance_date, INTERVAL 1 DAY)) = 1)""")
        frappe.db.sql("""UPDATE tabAttendance a SET a.status = 'Present' WHERE a.status = 'Absent'
            AND (SELECT COUNT(*) FROM `tabEmployee Checkin` ec WHERE ec.employee = a.employee AND DATE(ec.time) = a.attendance_date) = 1
            AND EXISTS (SELECT 1 FROM `tabEmployee Checkin` ec WHERE ec.employee = a.employee AND DATE(ec.time) = a.attendance_date AND TIME(ec.time) BETWEEN '00:00:00' AND '10:00:00')
            AND EXISTS (SELECT 1 FROM `tabEmployee Checkin` ec WHERE ec.employee = a.employee AND DATE(ec.time) = DATE_SUB(a.attendance_date, INTERVAL 1 DAY) AND TIME(ec.time) BETWEEN '14:00:00' AND '23:59:59'
                AND (SELECT COUNT(*) FROM `tabEmployee Checkin` ec2 WHERE ec2.employee = a.employee AND DATE(ec2.time) = DATE_SUB(a.attendance_date, INTERVAL 1 DAY)) = 1)""")

        # Step C: 夜班 cross-day pair (20:00-23:59 + next day 00:00-08:00) → Present
        frappe.db.sql("""UPDATE tabAttendance a SET a.status = 'Present' WHERE a.status = 'Absent'
            AND (SELECT COUNT(*) FROM `tabEmployee Checkin` ec WHERE ec.employee = a.employee AND DATE(ec.time) = a.attendance_date) = 1
            AND EXISTS (SELECT 1 FROM `tabEmployee Checkin` ec WHERE ec.employee = a.employee AND DATE(ec.time) = a.attendance_date AND TIME(ec.time) BETWEEN '20:00:00' AND '23:59:59')
            AND EXISTS (SELECT 1 FROM `tabEmployee Checkin` ec WHERE ec.employee = a.employee AND DATE(ec.time) = DATE_ADD(a.attendance_date, INTERVAL 1 DAY) AND TIME(ec.time) BETWEEN '00:00:00' AND '08:00:00'
                AND (SELECT COUNT(*) FROM `tabEmployee Checkin` ec2 WHERE ec2.employee = a.employee AND DATE(ec2.time) = DATE_ADD(a.attendance_date, INTERVAL 1 DAY)) = 1)""")
        frappe.db.sql("""UPDATE tabAttendance a SET a.status = 'Present' WHERE a.status = 'Absent'
            AND (SELECT COUNT(*) FROM `tabEmployee Checkin` ec WHERE ec.employee = a.employee AND DATE(ec.time) = a.attendance_date) = 1
            AND EXISTS (SELECT 1 FROM `tabEmployee Checkin` ec WHERE ec.employee = a.employee AND DATE(ec.time) = a.attendance_date AND TIME(ec.time) BETWEEN '00:00:00' AND '08:00:00')
            AND EXISTS (SELECT 1 FROM `tabEmployee Checkin` ec WHERE ec.employee = a.employee AND DATE(ec.time) = DATE_SUB(a.attendance_date, INTERVAL 1 DAY) AND TIME(ec.time) BETWEEN '20:00:00' AND '23:59:59'
                AND (SELECT COUNT(*) FROM `tabEmployee Checkin` ec2 WHERE ec2.employee = a.employee AND DATE(ec2.time) = DATE_SUB(a.attendance_date, INTERVAL 1 DAY)) = 1)""")

        # Step D: Cross-day with non-single next/prev day
        frappe.db.sql("""UPDATE tabAttendance a SET a.status = 'Present' WHERE a.status = 'Absent'
            AND (SELECT COUNT(*) FROM `tabEmployee Checkin` ec WHERE ec.employee = a.employee AND DATE(ec.time) = a.attendance_date) = 1
            AND EXISTS (SELECT 1 FROM `tabEmployee Checkin` ec WHERE ec.employee = a.employee AND DATE(ec.time) = a.attendance_date AND TIME(ec.time) BETWEEN '14:00:00' AND '23:59:59')
            AND EXISTS (SELECT 1 FROM `tabEmployee Checkin` ec WHERE ec.employee = a.employee AND DATE(ec.time) = DATE_ADD(a.attendance_date, INTERVAL 1 DAY) AND TIME(ec.time) BETWEEN '00:00:00' AND '10:00:00')""")
        frappe.db.sql("""UPDATE tabAttendance a SET a.status = 'Present' WHERE a.status = 'Absent'
            AND (SELECT COUNT(*) FROM `tabEmployee Checkin` ec WHERE ec.employee = a.employee AND DATE(ec.time) = a.attendance_date) = 1
            AND EXISTS (SELECT 1 FROM `tabEmployee Checkin` ec WHERE ec.employee = a.employee AND DATE(ec.time) = a.attendance_date AND TIME(ec.time) BETWEEN '00:00:00' AND '10:00:00')
            AND EXISTS (SELECT 1 FROM `tabEmployee Checkin` ec WHERE ec.employee = a.employee AND DATE(ec.time) = DATE_SUB(a.attendance_date, INTERVAL 1 DAY) AND TIME(ec.time) BETWEEN '14:00:00' AND '23:59:59')""")

        # Step E: Fix shifts based on first checkin time
        frappe.db.sql("""UPDATE tabAttendance a
            INNER JOIN (SELECT employee, DATE(time) as att_date, MIN(TIME(time)) as first_time FROM `tabEmployee Checkin` GROUP BY employee, DATE(time)) ci
            ON ci.employee = a.employee AND ci.att_date = a.attendance_date
            SET a.shift = CASE
                WHEN HOUR(ci.first_time) >= 14 AND HOUR(ci.first_time) < 20 THEN '中班'
                WHEN HOUR(ci.first_time) >= 20 OR HOUR(ci.first_time) < 4 THEN '晚班'
                WHEN HOUR(ci.first_time) >= 6 AND HOUR(ci.first_time) < 10 THEN '早班'
                ELSE '行政班早班' END""")

        # Step F: 行政/办公室 → 行政班早班
        frappe.db.sql("""UPDATE tabAttendance a INNER JOIN tabEmployee emp ON emp.name = a.employee SET a.shift = '行政班早班'
            WHERE (emp.department LIKE '%行政%' OR emp.department LIKE '%办公室%' OR emp.department LIKE '%财务%' OR emp.department LIKE '%采购%'
                OR emp.department LIKE '%市场%' OR emp.department LIKE '%技术%' OR emp.department LIKE '%设备%' OR emp.department LIKE '%QC%'
                OR emp.department LIKE '%QA%' OR emp.department LIKE '%安全%' OR emp.department LIKE '%人事%' OR emp.department LIKE '%注册%'
                OR emp.department LIKE '%质量%' OR emp.department LIKE '%总经办%' OR emp.department LIKE '%生产部%' OR emp.department LIKE '%AI%')""")

        # Step G: Late detection
        frappe.db.sql("""UPDATE tabAttendance a SET a.late_entry = 0""")
        frappe.db.sql("""UPDATE tabAttendance a
            INNER JOIN (SELECT employee, DATE(time) as att_date, MIN(TIME(time)) as first_time FROM `tabEmployee Checkin` GROUP BY employee, DATE(time)) ci
            ON ci.employee = a.employee AND ci.att_date = a.attendance_date
            SET a.late_entry = 1
            WHERE (a.shift = '行政班早班' AND ci.first_time > '08:30:00')
               OR (a.shift = '早班' AND ci.first_time > '08:00:00')
               OR (a.shift = '中班' AND ci.first_time > '16:00:00')""")

        frappe.db.commit()

        return {"total": len(all_recs), "created": created, "skipped": skipped}
    except Exception as e:
        frappe.log_error(str(e), "得力云同步"); frappe.throw(f"得力云同步失败: {e}")


# ==================== 通用工具函数 ====================

def _get_token():
    cache_key = "feishu_tenant_token"
    token = frappe.cache.get_value(cache_key)
    if token: return token
    import os
    app_id = os.environ.get("FEISHU_APP_ID", ""); app_secret = os.environ.get("FEISHU_APP_SECRET", "")
    resp = requests.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                         json={"app_id": app_id, "app_secret": app_secret}, timeout=10)
    data = resp.json(); token = data.get("tenant_access_token")
    if not token: raise Exception(f"获取飞书token失败: {data}")
    expires = data.get("expire", 7200) - 300
    frappe.cache.set_value(cache_key, token, expires_in_sec=expires)
    return token


def _fetch_all_records(token):
    return _fetch_all_records_custom(token, BITABLE_APP_TOKEN, BITABLE_TABLE_ID)


def _fetch_all_records_custom(token, app_token, table_id):
    all_records = []; page_token = None
    while True:
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"
        params = {"page_size": 100}
        if page_token: params["page_token"] = page_token
        resp = requests.get(url, params=params, headers={"Authorization": f"Bearer {token}"}, timeout=30)
        data = resp.json()
        if data.get("code") != 0: raise Exception(f"读取表格失败: {data.get('msg')}")
        items = data.get("data", {}).get("items") or []; all_records.extend(items)
        if not data.get("data", {}).get("has_more"): break
        page_token = data.get("data", {}).get("page_token")
        if len(all_records) > 10000: break
    return all_records