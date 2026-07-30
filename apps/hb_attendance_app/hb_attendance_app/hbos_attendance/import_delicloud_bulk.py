import frappe
import json
import hashlib
import requests
import time as tmod
from datetime import datetime, timedelta


def import_all_delicloud_checkins():
    import os

    APP_KEY = os.environ.get("DELICLOUD_APP_KEY", "")
    APP_SECRET = os.environ.get("DELICLOUD_APP_SECRET", "")
    PATH = "/v2.0/cloudappapi"
    BASE = "https://v2-api.delicloud.com"

    def _call(cmd, body=None):
        ts = str(int(tmod.time() * 1000))
        sig = hashlib.md5((PATH + ts + APP_KEY + APP_SECRET).encode()).hexdigest().lower()
        h = {
            "Content-Type": "application/json; charset=UTF-8",
            "App-Key": APP_KEY, "App-Timestamp": ts, "App-Sig": sig,
            "Api-Module": "CHECKIN", "Api-Cmd": cmd,
        }
        r = requests.post(BASE + PATH, json=body or {}, headers=h, timeout=30)
        return r.json()

    # 初始化
    init_r = _call("checkin_query_init")
    print(f"Init: code={init_r.get('code')}")

    # 拉取全部
    all_recs = []
    nid = 0
    loops = 0
    while loops < 200:
        r = _call("checkin_query", {"next_id": nid, "page_size": 500})
        if r.get("code") != 0:
            print(f"API error: {r}")
            break
        items = r.get("data", {}).get("data", [])
        nn = r.get("data", {}).get("next_id", 0)
        all_recs.extend(items)
        loops += 1
        print(f"  Page {loops}: next_id={nid} -> {nn}, items={len(items)}, total={len(all_recs)}")
        if not items or nn == nid:
            break
        nid = nn

    print(f"\nTotal fetched: {len(all_recs)} records")

    CHECK_TYPE_CN = {
        "fa": "人脸", "fp": "指纹", "pass": "密码", "card": "刷卡",
        "app_scan": "APP扫码", "gps": "GPS定位", "wifi": "WiFi打卡",
        "out_work": "外勤", "reissue": "补签", "flexible": "灵活卡",
    }

    # 清空旧数据
    frappe.db.sql("DELETE FROM `tabEmployee Checkin` WHERE name LIKE 'DELICLOUD-%%'")
    frappe.db.commit()
    print("Cleared old data")

    inserted = 0
    skipped = 0
    errors = 0

    for rec in all_recs:
        rid = rec.get("id", "")
        if not rid:
            skipped += 1
            continue

        cd = rec.get("check_data", "{}")
        try:
            cd = json.loads(cd) if isinstance(cd, str) else cd
        except Exception:
            cd = {}

        member_name = cd.get("member_name", "")
        emp_num = cd.get("employee_num", "")
        dept_name = cd.get("dept_name", "")
        device_name = cd.get("device_name", "")
        cts = rec.get("check_time", 0)
        check_type = rec.get("check_type", "")
        terminal_id = rec.get("terminal_id", "")

        if not cts or not member_name:
            skipped += 1
            continue

        # 得力云 check_time 为 标准 UTC 时间戳，直接使用
        try:
            check_time = datetime.fromtimestamp(int(cts))
        except Exception:
            skipped += 1
            continue

        check_type_cn = CHECK_TYPE_CN.get(check_type, check_type)
        if not check_type_cn:
            check_type_cn = check_type

        name = f"DELICLOUD-{rid}"
        now = frappe.utils.now_datetime()
        now_str = now.strftime("%Y-%m-%d %H:%M:%S.%f")
        time_str = check_time.strftime("%Y-%m-%d %H:%M:%S")

        # 完整原始数据
        extra_info = json.dumps({
            "delicloud_id": rid,
            "delicloud_user_id": rec.get("user_id", ""),
            "check_data_raw": cd,
        }, ensure_ascii=False)

        try:
            frappe.db.sql("""
                INSERT INTO `tabEmployee Checkin` (
                    `name`, `creation`, `modified`, `modified_by`, `owner`,
                    `docstatus`, `idx`,
                    `employee`, `employee_name`, `time`,
                    `log_type`, `device_id`,
                    `hbos_source_type`,
                    `hbos_delicloud_id`, `hbos_employee_num`, `hbos_dept_name`,
                    `hbos_check_type`, `hbos_terminal_sn`,
                    `latitude`, `longitude`,
                    `_user_tags`
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    1, 0,
                    NULL, %s, %s,
                    %s, %s,
                    'HBOS raw checkin import',
                    %s, %s, %s,
                    %s, %s,
                    0, 0,
                    %s
                )
            """, (
                name, now_str, now_str, "Administrator", "Administrator",
                member_name,
                time_str,
                "IN" if check_type != "out_work" else "OUT",
                device_name or terminal_id,
                str(rid),
                emp_num,
                dept_name,
                check_type_cn,
                terminal_id,
                extra_info,
            ))
            inserted += 1
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"  Error {rid}: {e}")

        if inserted % 500 == 0:
            frappe.db.commit()
            print(f"  Committed: {inserted}")

    frappe.db.commit()

    # 清除缓存，让自定义字段生效
    frappe.clear_cache(doctype="Employee Checkin")

    print(f"\n=== IMPORT COMPLETE ===")
    print(f"Fetched: {len(all_recs)}")
    print(f"Inserted: {inserted}")
    print(f"Skipped: {skipped}")
    print(f"Errors: {errors}")

    return {"fetched": len(all_recs), "inserted": inserted, "skipped": skipped, "errors": errors}