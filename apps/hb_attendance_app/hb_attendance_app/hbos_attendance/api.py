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
EXCEPTION_BITABLE_APP_TOKEN = "TnDnbgjbPa5erasF407crN7Yn47"
EXCEPTION_BITABLE_TABLE_ID = "tblP3tzAoO7NGBc6"
DELICLOUD_PATH = "/v2.0/cloudappapi"

# ==================== 班次判定名单（模块级常量，供配对算法与修复脚本复用） ====================

# 行政班名单(按工号，强制8:30-17:30判定)
ADMIN_NUMS = {
    '10003001','10003003','10003006',
    '10004003','10004005','10004006','10004020','10004022',
    '10006001','10006002','10006020','10006022','10006030',
    '10007003','10007004','10007007','10007008','10007009',
    '10008003','10008004','10008005','10008006','10008007','10008008','10008009','10008010','10008011','10008012','10008013','10008014',
    '10008015','10008016','10008019','10008021','10008022','10008023','10008025','10008026','10008027',
    '10009002','10009004','10009005','10009006','10009007','10009008','10009009','10009010','10009011','10009013',
    '10009014','10009015','10009016','10009018','10009022','10009023','10009024','10009029',
    '10010003','10010004','10010005','10010006','10010008','10010012',
    '10011001','10011002','10011003','10011005','10011006',
    '10012003','10012005','10012008','10012009','10012010',
    '10013002','10013003','10013004','10013005','10013006','10013007','10013008','10013012','10013013','10013017','10013018','10013022',
    '10014005','10014007','10014016','10014017','10014022',
    '10015001','10015002','10015003','10015004','10015005','10015006','10015007','10015008','10015009','10015010','10015011','10015012','10015013','10015015','10015016','10015018','10015019','10015021','10015022','10015023','10015025','10015026','10015028','10015030','10015031','10015035','10015036','10015039','10015040','10015042','10015043','10015045','10015046','10015047','10015048','10015051','10015052','10015053','10015056','10015057','10015058','10015060','10015061','10015062','10015063','10015064','10015065','10015066','10015068','10015069','10015071',
    '10016001','10016002','10016003','10016004','10016005',
    '11001003','11001004','11001005','11001006','11001007','11001008','11001010','11001018',
    '11002001','11002002','11002003','11002004','11002006','11002007',
    '11003003','11003052','11003055','11003056',
    '11004002','11004004','11004006','11004007','11004010','11004011','11004012','11004014','11004049','11004050',
    '11005005','11005006','11005007','11005008',
    '11006002','11006003','11006005','11006006','11006007','11006008','11006009','11006010','11006011','11006012',
    '11006093','11006104','11006105','11006107','11006112',
    '11007002','11007003','11007004',
    '11008002','11008004','11008005','11008011','11008012',
    '11009003','11009006','11009007','11009008','11009011','11009016','11009017','11009018','11009019','11009020','11009021','11009026','11009028','11009030','11009032','11009033','11009034','11009041','11009042','11009043','11009044','11009045',
}

# 食堂人员(不判迟到早退)
FOOD_NUMS = {
    '11009046','11009047','11009048','11009049','11009050','11009051','11009052',
}

# 无菌倒班(按行政班8:30规则, 8:31起算迟到)
WUJUN_NUMS = {
    '10014020','10015055','11004008',
    '11008005','11008007','11008009','11008011','11008012','11008013','11008015','11008016','11008017','11008018','11008019','11008020','11008021','11008023','11008024','11008026','11008027','11008028','11008029','11008030','11008031','11008032','11008034','11008035','11008037','11008038','11008039','11008040','11008041','11008043','11008045','11008046','11008047','11008048','11008049','11008050','11008052','11008054','11008055','11008056','11008057','11008058','11008059','11008060','11008063',
    '11009035','11009036','11009037','11009038','11009039','11009040',
}

# 安全人员倒班(早班8:30, 8:31起算迟到)
SAFETY_NUMS = {
    '10006022','10006023','10006024','10006025','10006026','10006027','10006028','10006029','10006030','10006031','10006032','10006033','10006034','10006035','11009004',
}

# 不计入异常考勤的豁免名单（管理层，Owner 提供 2026-08-13）
# 这些工号的员工: 迟到/早退/缺勤均不进入异常判定
EXEMPT_NUMS = {
    '10003001','10006001','10006025','10006026','10006027',
    '10007003','10007004','10008003','10008004','10008015',
    '10009002','10009013','10010003','10011001','10013002',
    '10013006','10013007','10013008','10015001','10015002',
    '10015005','10015023','10015028','10015069','10016001',
    '11001001','11001003','11001005','11002001','11002002',
    '11002003','11003003','11004002','11004004','11005005',
    '11006002','11006003','11006008','11006107','11006112',
    '11008002','11008004','11008005','11009007','11009013',
    '11009016','11009033','11009041','11009042','11009043',
    # Owner 2026-08-14 追加
    '10004020','11009003','10013018','10003006',
    # Owner 2026-08-14 追加（Excel名单补录人员）
    'HB-梁春盛','HB-尚磊磊','HB-陈广涛','10003002','10004001',
    '10010001','10010002','11009027','10006018','10006019',
    '10007001','10007002','10012001','10014002','10012004',
    '10013001','10014003','10009001','10008001','11003001',
    '11003002','11004001','11004003','11004005','11005001',
    '11006001','11006113','11007001',
}


def _is_exempt(emp_num):
    """判断员工是否在免异常考勤白名单中"""
    return emp_num in EXEMPT_NUMS


def _is_admin_shift_num(emp_num):
    """判断员工是否为行政班人员（周末双休、不判缺勤）"""
    return emp_num in ADMIN_NUMS


def _get_shift_and_late(ck_dt, emp_num="", cross_day=False):
    """返回 (系统班次名, 是否迟到)。系统班次: 早班/中班/晚班/行政班早班"""
    # 食堂不判迟到早退
    if emp_num in FOOD_NUMS:
        return ("行政班早班", False)
    # 无菌倒班: 白班→早班(8:30标准), 夜班→晚班(20:30标准)
    if emp_num in WUJUN_NUMS:
        ts = ck_dt.strftime("%H:%M:%S")
        if ck_dt.hour >= 20 or ck_dt.hour < 4:
            return ("晚班", ts >= "20:31:00")
        return ("早班", ts >= "08:31:00")
    # 安全人员倒班: 早班(8:30标准), 晚班(20:30标准) —— 与无菌倒班一致
    if emp_num in SAFETY_NUMS:
        ts = ck_dt.strftime("%H:%M:%S")
        if ck_dt.hour >= 20 or ck_dt.hour < 4:
            return ("晚班", ts >= "20:31:00")
        return ("早班", ts >= "08:31:00")
    # 行政班名单→行政班早班
    if emp_num in ADMIN_NUMS:
        ts = ck_dt.strftime("%H:%M:%S")
        return ("行政班早班", ts >= "08:31:00")
    h = ck_dt.hour; m = ck_dt.minute; ts = ck_dt.strftime("%H:%M:%S")
    if h >= 20 or h < 4: return ("晚班", h >= 0 and ts > "00:00:00" and h < 4)
    if 4 <= h < 6: return ("早班", False)
    if 6 <= h < 8: return ("早班", False)
    if h == 8: return ("早班", m > 0)
    if 9 <= h < 12: return ("行政班早班", True)
    if 12 <= h < 16: return ("中班", False)
    if 16 <= h < 20:
        if cross_day:
            return ("晚班", False) if h >= 19 else ("中班", False)
        return ("中班", ts > "16:00:00")
    return ("晚班", False)

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
            emp_num = cd.get("employee_num", ""); member_name = cd.get("member_name", "").strip(); cts = rec.get("check_time", 0)
            if not cts: skipped += 1; continue
            try:
                cdt = dt_mod.fromtimestamp(cts)
                # Skip future dates (2030+)
                if cdt.year >= 2030: skipped += 1; continue
                ts = cdt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception: skipped += 1; continue
            # 工号优先匹配姓名: 工号具有唯一性(姓名↔工号一一对应)
            emp = None
            if emp_num:
                emp = frappe.db.get_value("Employee", {"employee_number": emp_num}, "name")
            if not emp and member_name:
                emp = frappe.db.get_value("Employee", {"employee_name": member_name}, "name")
            if not emp: skipped += 1; continue
            # 双重校验: 工号匹配到的员工姓名与打卡机member_name不一致时跳过脏数据
            # (防止考勤机把甲的工号录给乙)
            if emp_num and member_name:
                local_name = frappe.db.get_value("Employee", emp, "employee_name")
                if local_name and local_name != member_name:
                    skipped += 1
                    continue
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

        # Run auto attendance after sync (skip if fails)
        try:
            from hrms.hr.doctype.shift_type.shift_type import process_auto_attendance_for_all_shifts
            process_auto_attendance_for_all_shifts()
        except Exception:
            pass

        # ===== HBOS 考勤生成(配对算法) =====
        # 规则: 行政班 8:30-17:30, 早班 8:00-16:00, 中班 16:00-0:00, 夜班 0:00-8:00
        # 允许提前最多4h打卡; 跨天班次按相邻打卡贪心配对
        # 班次名单与判定逻辑复用模块级 ADMIN_NUMS/FOOD_NUMS/WUJUN_NUMS/SAFETY_NUMS 与 _get_shift_and_late
        from datetime import datetime as _dt, timedelta as _td

        # 考勤生成只算到昨天: 今天数据不完整(下班卡/夜班卡未打), 避免全员假缺勤
        yesterday = (_dt.now() - _td(days=1)).strftime("%Y-%m-%d")
        month_start = _dt.now().replace(day=1).strftime("%Y-%m-%d")
        gen_result = regenerate_attendance(month_start, yesterday)

        return {"total": len(all_recs), "created": created, "skipped": skipped,
                "attendance_generated": gen_result}
    except Exception as e:
        frappe.log_error(str(e), "得力云同步"); frappe.throw(f"得力云同步失败: {e}")


def regenerate_attendance(range_start, range_end):
    """按 HBOS 配对算法重新生成 Attendance。

    参数:
        range_start: 生成范围的起始日期 (YYYY-MM-DD)
        range_end: 生成范围的结束日期 (YYYY-MM-DD)，含当天

    流程:
        1. 删除该范围内所有 HBOS-ATT-* 记录（保留 HRMS 原生记录）
        2. 对打卡流水做 10 分钟去重 + 贪心配对（凌晨打卡向前跨天配对）
        3. 计算工作时长写入 working_hours
        4. 零打卡缺勤生成 Absent
    """
    from collections import defaultdict
    from datetime import datetime as _dt, timedelta as _td
    from datetime import date as _date, timedelta as _tdelta

    # 拉取足够多的历史打卡确保配对上下文(覆盖生成范围+前后各1天)
    fetch_start = (_date.fromisoformat(range_start) - _tdelta(days=1)).strftime("%Y-%m-%d")
    fetch_end = (_date.fromisoformat(range_end) + _tdelta(days=1)).strftime("%Y-%m-%d")

    all_ck = frappe.db.sql("""
        SELECT ec.employee, ec.time, emp.employee_name, emp.employee_number, emp.department
        FROM `tabEmployee Checkin` ec
        JOIN tabEmployee emp ON emp.name = ec.employee
        WHERE DATE(ec.time) BETWEEN %s AND %s
        ORDER BY ec.employee, ec.time
    """, (fetch_start, fetch_end), as_dict=True)

    by_emp = defaultdict(list)
    for ck in all_ck:
        by_emp[ck["employee"]].append(ck)

    # 请假日期集合: employee -> set(日期)，配对分支与零打卡分支共用
    leaves = frappe.db.get_all(
        "HBOS Leave Record",
        filters={"approval_status": "已通过"},
        fields=["employee", "start_date", "end_date"],
    )
    emp_leave_dates = defaultdict(set)
    for l in leaves:
        if not l.start_date or not l.end_date:
            continue
        cur = l.start_date if isinstance(l.start_date, _date) else _date.fromisoformat(str(l.start_date))
        le = l.end_date if isinstance(l.end_date, _date) else _date.fromisoformat(str(l.end_date))
        while cur <= le:
            emp_leave_dates[l.employee].add(cur.strftime("%Y-%m-%d"))
            cur += _tdelta(days=1)

    # 清空生成范围内已有用 HBOS 逻辑生成的 Attendance(保留 HRMS 生成的)
    frappe.db.sql(
        "DELETE FROM tabAttendance WHERE name LIKE 'HBOS-ATT-%%' AND attendance_date BETWEEN %s AND %s",
        (range_start, range_end),
    )
    frappe.db.commit()

    # 对每个员工做贪心配对
    # 规则: 先去重(相邻10min内合并), 然后凌晨打卡优先向前配对
    att_to_insert = []
    for eid, cks in by_emp.items():
        cks.sort(key=lambda x: x["time"])

        # 去重: 相邻打卡间隔<10min视为重复, 保留最早的
        # 10分钟是上限: 跨班次背靠背卡(如 07:54夜班下班+08:07早班上班)间隔13分钟, 不能合并
        dedup_ck = []
        skip_until = None
        for i in range(len(cks)):
            if skip_until and cks[i]["time"] <= skip_until:
                continue
            dedup_ck.append(cks[i])
            skip_until = cks[i]["time"] + _td(minutes=10)
        cks = dedup_ck

        used = [False] * len(cks)

        # ===== 阶段0: 跨天夜班配对优先锁定 =====
        # 夜班/晚班上班卡(22:00-24:00) 与 次日凌晨/早晨下班卡(04:00-10:00) 优先配对
        # 先锁定这些无歧义的夜班对, 避免主循环把「中班下班卡」配给夜班上班卡,
        # 导致次日早晨的夜班下班卡被误判为早班迟到(李开新 8/8 08:05 案例)
        # 固定早班群体(行政/安全/食堂)不参与
        emp_num_for_night = cks[0].get("employee_number", "") if cks else ""
        if emp_num_for_night not in ADMIN_NUMS and emp_num_for_night not in SAFETY_NUMS and emp_num_for_night not in FOOD_NUMS:
            for i in range(len(cks)):
                if used[i]: continue
                h_i = cks[i]["time"].hour
                if 22 <= h_i <= 23:
                    for j in range(i + 1, len(cks)):
                        if used[j]: continue
                        cj = cks[j]["time"]
                        if cj.date() == cks[i]["time"].date():
                            continue
                        if not (4 <= cj.hour < 10):
                            continue
                        gap = (cj - cks[i]["time"]).total_seconds() / 3600
                        if 4 <= gap <= 18:
                            used[i] = True; used[j] = True
                            shift, late = _get_shift_and_late(cks[i]["time"], emp_num_for_night, cross_day=True)
                            if _is_exempt(emp_num_for_night):
                                late = 0
                            hours = round(gap, 2)
                            att_to_insert.append((
                                "HBOS-ATT-" + eid + "-" + cks[i]["time"].strftime("%Y-%m-%d"),
                                eid, cks[i]["time"].strftime("%Y-%m-%d"), "Present", shift,
                                1 if late else 0, cks[i]["time"].strftime("%Y-%m-%d %H:%M:%S"), hours, 0
                            ))
                            break

        # ===== 主循环: 剩余卡的贪心配对 =====
        for i in range(len(cks)):
            if used[i]: continue
            ck1 = cks[i]
            h = ck1["time"].hour
            emp_num = ck1.get("employee_number", "")
            is_exempt = _is_exempt(emp_num)

            # 凌晨/早晨打卡(H<10)向前配对(跨天班次下班卡)
            # 倒班员工早上7-9点的卡既可能是早班上班卡, 也可能是前夜晚班下班卡
            # 向前配对优先, 消除「晚班下班卡被误判为早班迟到」的错配
            # 固定早班群体(行政/安全/食堂)无跨天班次, 跳过向前配对
            fixed_morning = is_exempt or emp_num in ADMIN_NUMS or emp_num in SAFETY_NUMS or emp_num in FOOD_NUMS
            paired = False
            if h < 10 and i > 0 and not fixed_morning:
                # 向前配对 — 前一天 14:00 后的卡(中班/晚班上班卡)
                for p in range(i - 1, -1, -1):
                    if used[p]: continue
                    if cks[p]["time"].date() == ck1["time"].date():
                        continue
                    if cks[p]["time"].hour < 14:
                        continue
                    gap = (ck1["time"] - cks[p]["time"]).total_seconds() / 3600
                    if 2 <= gap <= 18:
                        used[p] = True; used[i] = True
                        shift, late = _get_shift_and_late(cks[p]["time"], cks[p].get("employee_number", ""), cross_day=True)
                        hours = round(gap, 2)
                        if _is_exempt(cks[p].get("employee_number", "")):
                            late = 0
                        att_to_insert.append((
                            "HBOS-ATT-" + eid + "-" + cks[p]["time"].strftime("%Y-%m-%d"),
                            eid, cks[p]["time"].strftime("%Y-%m-%d"), "Present", shift,
                            1 if late else 0, cks[p]["time"].strftime("%Y-%m-%d %H:%M:%S"), hours, 0
                        ))
                        paired = True
                        break

            if paired:
                continue

            # 凌晨打卡(0-4点)无法向前配对→缺勤；豁免人员除外
            if h < 4:
                used[i] = True
                if is_exempt:
                    continue
                ds_cur = ck1["time"].strftime("%Y-%m-%d")
                if ds_cur in emp_leave_dates.get(eid, set()):
                    continue
                # 行政班周末加班: 周末只要有打卡记录就不算异常
                if emp_num in ADMIN_NUMS:
                    ck_date = ck1["time"].date()
                    if ck_date.weekday() >= 5:
                        continue
                att_to_insert.append((
                    "HBOS-ATT-" + eid + "-" + ck1["time"].strftime("%Y-%m-%d"),
                    eid, ck1["time"].strftime("%Y-%m-%d"), "Absent", "", 0,
                    ck1["time"].strftime("%Y-%m-%d %H:%M:%S"), 0, 0
                ))
                continue

            # 正常向后配对: 同一天内配对, 时长2-12小时(业务规则)
            # 下限2小时: 间隔<2h的两张卡是重复打卡(忘记已打卡/多台考勤机), 不配成短班
            # 上限12小时: 最长班次12小时
            # 跨天只允许中班/晚班(16:00-24:00 上班、次日凌晨/早晨下班)
            # 行政班固定 8:30-17:30 无跨天班次, 其上班卡跨天必为「漏下班卡」错配
            best_j = -1
            for j in range(i + 1, len(cks)):
                if used[j]: continue
                gap = (cks[j]["time"] - ck1["time"]).total_seconds() / 3600
                if 2 <= gap <= 18:
                    cross_day = cks[j]["time"].date() != ck1["time"].date()
                    if cross_day:
                        if emp_num in ADMIN_NUMS:
                            continue
                    best_j = j; break

            if best_j == -1:
                # 孤立的上班卡(有上班无下班) → 判缺勤；豁免人员不判
                used[i] = True
                if is_exempt:
                    continue
                ds_cur = ck1["time"].strftime("%Y-%m-%d")
                if ds_cur in emp_leave_dates.get(eid, set()):
                    continue
                # 行政班周末加班: 周末只要有打卡记录就不算异常
                # (周末加班可能只有单卡, 如只打上班卡或下班卡)
                if emp_num in ADMIN_NUMS:
                    ck_date = ck1["time"].date()
                    if ck_date.weekday() >= 5:
                        continue
                att_to_insert.append((
                    "HBOS-ATT-" + eid + "-" + ck1["time"].strftime("%Y-%m-%d"),
                    eid, ck1["time"].strftime("%Y-%m-%d"), "Absent", "", 0,
                    ck1["time"].strftime("%Y-%m-%d %H:%M:%S"), 0, 0
                ))
                continue
            ck2 = cks[best_j]
            used[i] = True; used[best_j] = True
            cd = ck1["time"].date() != ck2["time"].date()
            shift, late = _get_shift_and_late(ck1["time"], emp_num, cross_day=cd)
            if is_exempt:
                late = 0
            gap_hours = round((ck2["time"] - ck1["time"]).total_seconds() / 3600, 2)
            att_to_insert.append((
                "HBOS-ATT-" + eid + "-" + ck1["time"].strftime("%Y-%m-%d"),
                eid, ck1["time"].strftime("%Y-%m-%d"), "Present", shift,
                1 if late else 0, ck1["time"].strftime("%Y-%m-%d %H:%M:%S"), gap_hours, 0
            ))

    # 批量插入(去重: 同一天Present优先, 其次保留第一条)
    seen = {}
    for name, emp, date, status, shift, late, ck, wh, miss_out in att_to_insert:
        key = emp + "_" + date
        if key in seen:
            # Present 覆盖 Absent；缺卡标记只在覆盖时继承为 0
            if status == "Present" and seen[key][3] == "Absent":
                seen[key] = (name, emp, date, status, shift, late, ck, wh, miss_out)
            continue
        seen[key] = (name, emp, date, status, shift, late, ck, wh, miss_out)
    deduped = list(seen.values())

    for i in range(0, len(deduped), 500):
        chunk = deduped[i:i+500]
        values = ",".join(
            "('%s','%s','%s','%s','%s',%s,'%s',%s,%s)" % (name, emp, date, status, shift, str(late), ck, str(wh), str(miss_out))
            for name, emp, date, status, shift, late, ck, wh, miss_out in chunk
        )
        frappe.db.sql("INSERT IGNORE INTO tabAttendance (name, employee, attendance_date, status, shift, late_entry, creation, working_hours, hbos_missing_out) VALUES " + values)
    frappe.db.commit()

    # ===== 零打卡缺勤: 在职员工当天完全无打卡 → 生成 Absent =====
    # 豁免: 已通过的请假记录覆盖当天 → 判 On Leave, 不算缺勤
    zero_absent = []
    leave_absent = []
    active_emps = frappe.db.get_all(
        "Employee",
        filters={"status": "Active"},
        fields=["name", "employee_number", "department"],
    )

    d = _date.fromisoformat(range_start)
    end_d = _date.fromisoformat(range_end)
    while d <= end_d:
        ds = d.strftime("%Y-%m-%d")
        is_weekend = d.weekday() >= 5  # 周六(5)/周日(6)
        ck_emps = frappe.db.sql("SELECT DISTINCT ec.employee FROM `tabEmployee Checkin` ec WHERE DATE(ec.time) = %s", ds, as_dict=True)
        ck_emp_set = set(c["employee"] for c in ck_emps)

        for e in active_emps:
            if e["name"] in ck_emp_set:
                continue
            key = e["name"] + "_" + ds
            if key in seen:
                continue
            # 请假豁免
            if ds in emp_leave_dates.get(e["name"], set()):
                leave_absent.append(("HBOS-ATT-" + e["name"] + "-" + ds, e["name"], ds, "On Leave", "", 0, ds + " 00:00:00", 0, 0))
                seen[key] = leave_absent[-1]
                continue
            # 豁免名单: 不计入异常考勤
            if _is_exempt(e.get("employee_number", "")):
                continue
            # 行政班周末双休: 周六/周日无打卡不算缺勤
            if is_weekend and e.get("employee_number", "") in ADMIN_NUMS:
                continue
            zero_absent.append(("HBOS-ATT-" + e["name"] + "-" + ds, e["name"], ds, "Absent", "", 0, ds + " 00:00:00", 0, 0))
            seen[key] = zero_absent[-1]
        d += _tdelta(days=1)

    # 批量插入请假记录
    for i in range(0, len(leave_absent), 500):
        chunk = leave_absent[i:i+500]
        values = ",".join(
            "('%s','%s','%s','%s','%s',%s,'%s',%s,%s)" % (name, emp, date, status, shift, str(late), ck, str(wh), str(miss_out))
            for name, emp, date, status, shift, late, ck, wh, miss_out in chunk
        )
        frappe.db.sql("INSERT IGNORE INTO tabAttendance (name, employee, attendance_date, status, shift, late_entry, creation, working_hours, hbos_missing_out) VALUES " + values)

    # 批量插入零打卡缺勤
    for i in range(0, len(zero_absent), 500):
        chunk = zero_absent[i:i+500]
        values = ",".join(
            "('%s','%s','%s','%s','%s',%s,'%s',%s,%s)" % (name, emp, date, status, shift, str(late), ck, str(wh), str(miss_out))
            for name, emp, date, status, shift, late, ck, wh, miss_out in chunk
        )
        frappe.db.sql("INSERT IGNORE INTO tabAttendance (name, employee, attendance_date, status, shift, late_entry, creation, working_hours, hbos_missing_out) VALUES " + values)
    frappe.db.commit()

    # ===== 孤卡补缺: 员工当天有打卡但所有卡都被跨天配对消耗(生成范围内无记录) → 补 Absent =====
    # 典型场景: 早上 8 点的卡被配给前一天晚班下班, 当天再无其他打卡,
    # 零打卡缺勤因「当天有打卡」跳过, 导致该员工当天完全没有考勤记录。
    # 请假豁免同样应用。
    orphan_days = []
    d = _date.fromisoformat(range_start)
    while d <= end_d:
        ds = d.strftime("%Y-%m-%d")
        is_weekend = d.weekday() >= 5
        # 每个有打卡但(生成后)无记录的在职员工
        rows = frappe.db.sql("""
            SELECT DISTINCT ec.employee, e.employee_number
            FROM `tabEmployee Checkin` ec
            JOIN tabEmployee e ON e.name = ec.employee
            WHERE DATE(ec.time) = %s AND e.status = 'Active'
              AND NOT EXISTS (
                  SELECT 1 FROM tabAttendance a
                  WHERE a.employee = ec.employee AND a.attendance_date = %s AND a.docstatus < 2
              )
        """, (ds, ds), as_dict=True)
        for r in rows:
            key = r["employee"] + "_" + ds
            if key in seen:
                continue
            if ds in emp_leave_dates.get(r["employee"], set()):
                continue
            # 豁免名单: 不计入异常考勤
            if _is_exempt(r.get("employee_number", "")):
                continue
            # 行政班周末双休: 周六/周日不算缺勤
            if is_weekend and r.get("employee_number", "") in ADMIN_NUMS:
                continue
            orphan_days.append(("HBOS-ATT-" + r["employee"] + "-" + ds, r["employee"], ds, "Absent", "", 0, ds + " 00:00:00", 0, 0))
            seen[key] = orphan_days[-1]
        d += _tdelta(days=1)

    # 批量插入孤卡缺勤
    for i in range(0, len(orphan_days), 500):
        chunk = orphan_days[i:i+500]
        values = ",".join(
            "('%s','%s','%s','%s','%s',%s,'%s',%s,%s)" % (name, emp, date, status, shift, str(late), ck, str(wh), str(miss_out))
            for name, emp, date, status, shift, late, ck, wh, miss_out in chunk
        )
        frappe.db.sql("INSERT IGNORE INTO tabAttendance (name, employee, attendance_date, status, shift, late_entry, creation, working_hours, hbos_missing_out) VALUES " + values)
    frappe.db.commit()

    return {
        "paired_present": sum(1 for x in deduped if x[3] == "Present"),
        "paired_absent": sum(1 for x in deduped if x[3] == "Absent"),
        "zero_absent": len(zero_absent),
        "orphan_absent": len(orphan_days),
        "leave_absent": len(leave_absent),
        "range": [range_start, range_end],
    }


# ==================== 考勤异常同步到飞书多维表格 ====================

@frappe.whitelist()
def sync_attendance_exceptions_to_bitable():
    """将迟到/早退记录同步到飞书多维表格「考勤异常汇总」"""
    import hashlib
    from datetime import datetime as dt_mod

    app_token = EXCEPTION_BITABLE_APP_TOKEN
    table_id = EXCEPTION_BITABLE_TABLE_ID
    if not app_token or not table_id:
        frappe.throw("请先在 HBOS Attendance 中配置飞书考勤异常多维表格（EXCEPTION_BITABLE_APP_TOKEN / EXCEPTION_BITABLE_TABLE_ID）")

    try:
        token = _get_token()
    except Exception as e:
        frappe.throw(f"获取飞书 token 失败: {e}")

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 1. 查询迟到/早退记录（含首次/末次打卡时间）
    records = frappe.db.sql("""
        SELECT a.employee, a.employee_name, emp.employee_number, emp.department,
               a.attendance_date, a.late_entry, a.early_exit, a.shift, a.working_hours,
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

    if not records:
        return {"total": 0, "created": 0, "updated": 0, "message": "暂无迟到/早退记录"}

    # 2. 获取飞书表格中已有记录，用于去重
    existing = {}
    page_token = None
    while True:
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"
        params = {"page_size": 500}
        if page_token:
            params["page_token"] = page_token
        resp = requests.get(url, params=params, headers=headers, timeout=30)
        data = resp.json()
        if data.get("code") != 0:
            frappe.throw(f"读取飞书表格失败: {data.get('msg')}")
        for item in data.get("data", {}).get("items", []):
            unique_key = item.get("fields", {}).get("唯一键", "")
            if unique_key:
                existing[unique_key] = item.get("record_id")
        if not data.get("data", {}).get("has_more"):
            break
        page_token = data.get("data", {}).get("page_token")

    # 3. 逐条写入/更新
    created = 0
    updated = 0
    skipped = 0
    batch_size = 50

    for i in range(0, len(records), batch_size):
        chunk = records[i:i + batch_size]
        batch_body = {"records": []}

        for r in chunk:
            # 异常类型
            if r.late_entry and r.early_exit:
                ex_type = "迟到+早退"
            elif r.late_entry:
                ex_type = "迟到"
            elif r.early_exit:
                ex_type = "早退"
            else:
                continue

            # 唯一键: employee + attendance_date
            unique_key = f"{r.employee}_{r.attendance_date}"

            # 格式化打卡时间
            first_ck = r.first_checkin.strftime("%H:%M:%S") if r.first_checkin else ""
            last_ck = r.last_checkin.strftime("%H:%M:%S") if r.last_checkin else ""

            fields = {
                "姓名": r.employee_name or "",
                "工号": r.employee_number or "",
                "部门": r.department or "",
                "考勤日期": int(dt_mod.combine(r.attendance_date, dt_mod.min.time()).timestamp() * 1000) if r.attendance_date else 0,
                "异常类型": ex_type,
                "班次": r.shift or "",
                "首次打卡": first_ck,
                "末次打卡": last_ck,
                "同步时间": int(dt_mod.now().timestamp() * 1000),
                "唯一键": unique_key,
            }

            if unique_key in existing:
                # 更新已有记录
                batch_body["records"].append({
                    "record_id": existing[unique_key],
                    "fields": fields,
                })
                updated += 1
            else:
                batch_body["records"].append({"fields": fields})
                created += 1

        if not batch_body["records"]:
            continue

        # 分批写入（飞书限制 500 条/次）
        for j in range(0, len(batch_body["records"]), 500):
            sub = {"records": batch_body["records"][j:j + 500]}
            # 区分新增和更新
            has_updates = any("record_id" in rec for rec in sub["records"])
            if has_updates:
                # 混合模式：先创建新记录，再更新已有记录
                new_recs = [rec for rec in sub["records"] if "record_id" not in rec]
                update_recs = [rec for rec in sub["records"] if "record_id" in rec]

                if new_recs:
                    create_resp = requests.post(
                        f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create",
                        headers=headers, json={"records": new_recs}, timeout=60)
                    if create_resp.json().get("code") != 0:
                        frappe.log_error(f"飞书批量创建失败: {create_resp.json()}", "考勤异常同步")

                if update_recs:
                    update_resp = requests.post(
                        f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_update",
                        headers=headers, json={"records": update_recs}, timeout=60)
                    if update_resp.json().get("code") != 0:
                        frappe.log_error(f"飞书批量更新失败: {update_resp.json()}", "考勤异常同步")
            else:
                create_resp = requests.post(
                    f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create",
                    headers=headers, json=sub, timeout=60)
                if create_resp.json().get("code") != 0:
                    frappe.log_error(f"飞书批量创建失败: {create_resp.json()}", "考勤异常同步")

        frappe.db.commit()

    return {
        "total": len(records),
        "created": created,
        "updated": updated,
        "message": f"同步完成：共 {len(records)} 条异常记录，新增 {created} 条，更新 {updated} 条",
    }


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