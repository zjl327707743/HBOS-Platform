"""飞书多维表格请假/加班数据同步 + 得力云考勤机同步"""
import frappe
import json
import requests
from datetime import datetime
from datetime import timezone as _tz
from datetime import timedelta as _timedelta

# 得力云 check_time 为标准 UTC 时间戳; 用固定 +8 时区转换, 不依赖容器 TZ 设置
# (2026-08-20 事故: queue worker 容器为 UTC, fromtimestamp 导致打卡时间错位 8 小时)
DELICLOUD_TZ = _tz(_timedelta(hours=8))

from hb_attendance_app.hbos_attendance.pairing import pair_employee_checkins, FOUR_SHIFT_NUMS
from hb_attendance_app.hbos_attendance.rule_lists import ADMIN_NUMS, EXEMPT_NUMS, FOOD_NUMS, SAFETY_NUMS


# 飞书多维表格固定配置
# 请假表（Owner 2026-08-19 确认以此表为准）:
# https://j0eukrlohu.feishu.cn/base/PwSXbltzha1uG1sr38hcQzMrnwb?table=tblmcJzOXsi6zfy3
BITABLE_APP_TOKEN = "PwSXbltzha1uG1sr38hcQzMrnwb"
BITABLE_TABLE_ID = "tblmcJzOXsi6zfy3"
OVERTIME_BITABLE_APP_TOKEN = "Tb0YwuXY6iglUXkzpcWc5EADnxe"
OVERTIME_BITABLE_TABLE_ID = "tblIQlEJk7TcxItX"
EXCEPTION_BITABLE_APP_TOKEN = "TnDnbgjbPa5erasF407crN7Yn47"
EXCEPTION_BITABLE_TABLE_ID = "tblP3tzAoO7NGBc6"
DELICLOUD_PATH = "/v2.0/cloudappapi"

# 旧无菌倒班名单已废弃(2026-08-20): 无菌人员统一走 pairing.py 的 SPECIAL_SHIFT_NUMS,
# 原 WUJUN_NUMS 中 3 名设备动力部人员(11008005/11008011/11008012)误加, 回归通用判定
WUJUN_NUMS = set()


def _is_exempt(emp_num):
    """判断员工是否在免异常考勤白名单中"""
    return emp_num in EXEMPT_NUMS


def _is_admin_shift_num(emp_num):
    """判断员工是否为行政班人员（周末双休、不判缺勤）"""
    return emp_num in ADMIN_NUMS


def _get_shift_and_late(ck_dt, emp_num="", cross_day=False):
    """返回 (系统班次名, 是否迟到)。系统班次: 早班/中班/晚班/行政班早班"""
    # 规则表优先(按部门+班次类型匹配, 硬编码兜底)
    # 为保持纯函数可测性, 规则查询在 regenerate_attendance 外层预加载后传入;
    # 此处直接走硬编码逻辑, 规则表接入见 _get_shift_and_late_with_rules
    return _get_shift_and_late_builtin(ck_dt, emp_num, cross_day)


def _get_shift_and_late_with_rules(ck_dt, emp_num="", cross_day=False, rules_by_dept=None):
    """规则表优先的班次判定。

    rules_by_dept: {dept_name: [{"shift_type","start_time","late_after",...}]}
    部门规则匹配不到或未传规则时回退硬编码。
    """
    if rules_by_dept:
        from hb_attendance_app.hbos_attendance.shift_rules import match_rule_by_time
        # 全局规则 + 部门规则合并匹配(部门优先已在调用方排序)
        for dept_rules in rules_by_dept.values():
            matched = match_rule_by_time(dept_rules, ck_dt, cross_day)
            if matched:
                return matched
    return _get_shift_and_late_builtin(ck_dt, emp_num, cross_day)


def _get_shift_and_late_builtin(ck_dt, emp_num="", cross_day=False):
    """硬编码班次判定(兜底)。"""
    # 食堂不判迟到早退
    if emp_num in FOOD_NUMS:
        return ("行政班早班", False)
    # 安全人员倒班: 早班(8:30标准), 晚班(20:30标准) —— 与无菌倒班一致
    if emp_num in SAFETY_NUMS:
        ts = ck_dt.strftime("%H:%M:%S")
        if ck_dt.hour >= 20 or ck_dt.hour < 4:
            return ("晚班", ts >= "20:31:00")
        return ("早班", ts >= "08:31:00")
    # 行政班名单→行政班早班(8:31起算迟到; 夜间/凌晨卡不判迟到, Owner 2026-08-21)
    if emp_num in ADMIN_NUMS:
        from hb_attendance_app.hbos_attendance.pairing import admin_shift_from_gap
        return admin_shift_from_gap(ck_dt)
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
    """飞书请假同步（以 Owner 指定的请假表格为准）。

    字段: 请假人员_姓名/工号/开始时间/结束时间/请假天数 + SourceID(审批实例ID) + 申请状态
    去重键: feishu-bitable-<SourceID>
    """
    try: token = _get_token(); records = _fetch_all_records(token)
    except Exception as e: frappe.log_error(str(e), "飞书同步"); frappe.throw(f"读取飞书表格失败: {e}")
    created = updated = skipped = 0
    for record in records:
        fields = record.get("fields", {}); rid = record.get("id", "")
        name = fields.get("请假人员_姓名", "") or ""
        emp_num = fields.get("请假人员_工号", "") or ""
        source_id = fields.get("SourceID", "") or ""
        if not name or not emp_num: skipped += 1; continue
        emp = frappe.db.get_value("Employee", {"employee_number": emp_num}, "name")
        if not emp: skipped += 1; continue
        st = fields.get("请假人员_开始时间", 0) or 0
        et = fields.get("请假人员_结束时间", 0) or 0
        sd = datetime.fromtimestamp(st/1000).strftime("%Y-%m-%d") if st else None
        ed = datetime.fromtimestamp(et/1000).strftime("%Y-%m-%d") if et else None
        # 去重键: SourceID 过长(集体审批单超140字符)时用 SHA-256 截断, 原始ID存 feishu_source_id
        import hashlib
        raw_source = source_id or rid
        digest = hashlib.sha256(raw_source.encode()).hexdigest()[:40]
        aid = f"feishu-bitable-{digest}"
        existing = frappe.db.exists("HBOS Leave Record", {"feishu_approval_id": aid})
        if not existing:
            # 兼容旧记录: 此前以原始 SourceID 为键(长度<140时)
            legacy_aid = f"feishu-bitable-{raw_source}"
            existing = frappe.db.exists("HBOS Leave Record", {"feishu_approval_id": legacy_aid})
            if existing:
                aid = legacy_aid
        if existing:
            doc = frappe.get_doc("HBOS Leave Record", {"feishu_approval_id": aid}); is_new = False
        else: doc = frappe.get_doc({"doctype": "HBOS Leave Record", "feishu_approval_id": aid}); is_new = True
        doc.update({"employee": emp, "leave_type": fields.get("请假类型", ""), "start_date": sd, "end_date": ed,
                     "leave_days": float(fields.get("请假人员_请假天数", 0) or 0),
                     "approval_status": STATUS_MAP.get(fields.get("申请状态", ""), "审批中"),
                     "feishu_sync_time": frappe.utils.now_datetime(), "remarks": fields.get("请假事由", ""),
                     "feishu_source_id": raw_source})
        try:
            doc.save(ignore_permissions=True); frappe.db.commit()
            if is_new: created += 1
            else: updated += 1
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
                # 得力云 check_time 为 UTC 时间戳, 用固定 +8 时区转换(不依赖容器 TZ)
                cdt = dt_mod.fromtimestamp(cts, tz=DELICLOUD_TZ).replace(tzinfo=None)
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
            # 设备信息采集(2026-08-18 新增): 分打卡机区分上下班，打卡记录需保留打卡机信息
            device_name = cd.get("device_name", "")
            terminal_sn = rec.get("terminal_id", "")
            deli_id = str(rec.get("id", ""))
            check_type = rec.get("check_type", "")
            dept_name = cd.get("dept_name", "")
            # GPS/外勤打卡: 手机定位打卡, 无考勤机 SN, 名称标记为「手机打卡」
            # (Owner 2026-08-27 确认: 手机打卡不参与方向判定, 不判缺勤)
            if (check_type or "").lower() in ("gps", "out_work"):
                device_name = "手机打卡"
            existing = frappe.db.get_value("Employee Checkin", {"employee": emp, "time": ts}, "name")
            if existing:
                # 历史记录回填设备信息(字段为空时才写入, 不覆盖已有值)
                try:
                    for fname, val in (("device_id", device_name), ("hbos_terminal_sn", terminal_sn),
                                       ("hbos_delicloud_id", deli_id), ("hbos_employee_num", emp_num),
                                       ("hbos_dept_name", dept_name), ("hbos_check_type", check_type)):
                        if val and not frappe.db.get_value("Employee Checkin", existing, fname):
                            frappe.db.set_value("Employee Checkin", existing, fname, val,
                                                update_modified=False)
                except Exception:
                    pass
                continue
            try:
                doc = frappe.get_doc({
                    "doctype": "Employee Checkin",
                    "employee": emp, "time": ts, "log_type": lt,
                    "device_id": device_name,
                    "hbos_terminal_sn": terminal_sn,
                    "hbos_delicloud_id": deli_id,
                    "hbos_employee_num": emp_num,
                    "hbos_dept_name": dept_name,
                    "hbos_check_type": check_type,
                })
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

    # 自动轮转排班(设备动力部 12h 倒班, Owner 2026-08-26 确认):
    # 生成到「重算终点」与「未来 30 天」的较晚者, 保证休息日在排班表中有记录,
    # 缺勤判定的「排班休息日无打卡=休息」逻辑会自动豁免, 不会误判缺勤。
    from hb_attendance_app.hbos_attendance.rotation_schedule import generate_rotation_schedule
    _rot_until = max(range_end, (_date.today() + _tdelta(days=30)).isoformat())
    generate_rotation_schedule(_rot_until)

    # 拉取足够多的历史打卡确保配对上下文(覆盖生成范围+前后各1天)
    fetch_start = (_date.fromisoformat(range_start) - _tdelta(days=1)).strftime("%Y-%m-%d")
    fetch_end = (_date.fromisoformat(range_end) + _tdelta(days=1)).strftime("%Y-%m-%d")

    all_ck = frappe.db.sql("""
        SELECT ec.employee, ec.time, emp.employee_name, emp.employee_number, emp.department,
               ec.hbos_terminal_sn, ec.hbos_check_type
        FROM `tabEmployee Checkin` ec
        JOIN tabEmployee emp ON emp.name = ec.employee
        WHERE DATE(ec.time) BETWEEN %s AND %s
          AND emp.status = 'Active'
        ORDER BY ec.employee, ec.time
    """, (fetch_start, fetch_end), as_dict=True)

    by_emp = defaultdict(list)
    for ck in all_ck:
        by_emp[ck["employee"]].append(ck)

    # GPS 打卡日期集合(Owner 2026-08-27 确认): 当天存在任意 GPS/外勤打卡时,
    # 视为已打卡出勤(外勤/居家/手机打卡), 不判缺勤。GPS/外勤打卡无考勤机 SN,
    # 方向未知, 直接参与配对会误判缺勤(姚娜 8/26 案例: 08:20 gps + 17:33 gps 被判 Absent)。
    gps_ck_set = set()
    for eid, cks in by_emp.items():
        for c in cks:
            ctype = (c.get("hbos_check_type") or "").lower()
            if ctype in ("gps", "out_work"):
                gps_ck_set.add((eid, c["time"].strftime("%Y-%m-%d")))


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

    # 排班表中的请假日期也计入请假豁免(排班表优先于飞书请假)
    # 排班「休息」的日期单独记录(休息日无打卡=无记录, 不生成 On Leave)
    emp_rest_dates = defaultdict(set)
    for s in frappe.db.get_all("HBOS Employee Schedule",
            filters={"leave_type": ["is", "set"]},
            fields=["employee", "schedule_date", "leave_type"]):
        emp_leave_dates[s.employee].add(str(s.schedule_date))
    for s in frappe.db.get_all("HBOS Employee Schedule",
            filters={"shift_type": "休息"},
            fields=["employee", "schedule_date"]):
        emp_rest_dates[s.employee].add(str(s.schedule_date))

    # 清空生成范围内已有用 HBOS 逻辑生成的 Attendance(保留 HRMS 生成的)
    # 同时清掉 range_end 之后的残留(当天数据不完整的假缺勤, 由早期版本生成)
    frappe.db.sql(
        "DELETE FROM tabAttendance WHERE name LIKE 'HBOS-ATT-%%' AND attendance_date BETWEEN %s AND %s",
        (range_start, range_end),
    )
    frappe.db.sql(
        "DELETE FROM tabAttendance WHERE name LIKE 'HBOS-ATT-%%' AND attendance_date > %s",
        (range_end,),
    )
    frappe.db.commit()

    # 对每个员工做贪心配对（纯函数，见 pairing.py）
    # 规则: 先去重(相邻10min内合并), 凌晨卡先向前配对, 再零点夜班配对, 最后向后配对
    # 同时记录每个员工的「夜班下班日」集合(8-10点的下班卡日期), 用于零打卡休息豁免
    from hb_attendance_app.hbos_attendance.pairing import dedup_checkins_with_mapping, night_out_days_from_roles
    # 班次规则表预加载 + 按日期版本化(历史稳定: 某天用当天生效的规则版本)
    # 结构: {(department, shift_type): [(effective_from, rule), ...]} 按 effective_from 升序
    # 注意: 状态包含「生效」和「停用」——停用的规则是旧版本, 对生效日期之前的历史仍有效
    rules_versioned = {}
    for r in frappe.db.get_all(
        "HBOS Shift Rule",
        filters={"status": ["in", ["生效", "停用"]], "effective_from": ["<=", range_end]},
        fields=["name", "department", "shift_type", "start_time", "end_time", "late_after", "min_hours", "effective_from"],
        order_by="department, shift_type, effective_from",
    ):
        key = (r.department, r.shift_type)
        rules_versioned.setdefault(key, []).append(r)

    def shift_fn_with_rules(ck_dt, emp_num, cross_day=False):
        # 按打卡日期取该日生效的规则版本(生效日期 <= 打卡日期 的最新版)
        # 部门专属规则优先于全局规则: 员工的部门有专属规则时用它, 否则用「全部部门」规则
        day = ck_dt.date().strftime("%Y-%m-%d")
        eid = emp_num_to_eid.get(emp_num, "") if emp_num else ""
        emp_dept = frappe.db.get_value("Employee", eid, "department") if eid else None
        rules_by_dept = {}
        for (dept, _stype), versions in rules_versioned.items():
            chosen = None
            for v in versions:
                if str(v.effective_from) <= day:
                    chosen = v
            if chosen is not None:
                rules_by_dept.setdefault(dept, []).append(chosen)
        # 部门专属优先
        if emp_dept and emp_dept in rules_by_dept:
            dept_rules = rules_by_dept[emp_dept]
            from hb_attendance_app.hbos_attendance.shift_rules import match_rule_by_time
            matched = match_rule_by_time(dept_rules, ck_dt, cross_day)
            if matched:
                return matched
        # 全局兜底(全部部门 - HD)
        for global_name in ("全部部门 - HD", "全部部门"):
            if global_name in rules_by_dept:
                from hb_attendance_app.hbos_attendance.shift_rules import match_rule_by_time
                matched = match_rule_by_time(rules_by_dept[global_name], ck_dt, cross_day)
                if matched:
                    return matched
        return _get_shift_and_late_with_rules(ck_dt, emp_num, cross_day, rules_by_dept)

    # 固定班次绑定: 员工 -> 绑定的规则名列表(多班次轮班支持)
    # 数据源: HBOS Employee Shift(多绑定) + Employee.hbos_fixed_shift(单绑定兼容)
    fixed_shift_map = {}
    for b in frappe.db.get_all("HBOS Employee Shift",
            fields=["employee", "shift_rule"]):
        fixed_shift_map.setdefault(b.employee, []).append(b.shift_rule)
    for e in frappe.db.get_all("Employee",
            fields=["name", "hbos_fixed_shift"],
            filters={"hbos_fixed_shift": ["is", "set"]}):
        if e.name not in fixed_shift_map:
            fixed_shift_map[e.name] = [e.hbos_fixed_shift]

    # 排班表(员工排班): 排班优先于一切规则
    schedule_map = {}
    for s in frappe.db.get_all("HBOS Employee Schedule",
            fields=["employee", "schedule_date", "shift_type", "leave_type"]):
        schedule_map.setdefault(s.employee, {})[str(s.schedule_date)] = s

    def shift_fn_with_fixed(ck_dt, emp_num, cross_day=False):
        """判定优先级: 排班表 > 固定班次绑定 > 部门/全局规则 > 硬编码。

        行政班名单人员(Owner 2026-08-21): 硬编码短路规则表——
        四车间行政班 08:0x 打卡曾被全局规则表匹配为「早班 08:00 标准」误判迟到,
        名单人员统一 08:31 起算迟到, 20 点后/凌晨卡按晚班不判迟到。
        """
        if emp_num in ADMIN_NUMS:
            return _get_shift_and_late_builtin(ck_dt, emp_num, cross_day)
        eid = emp_num_to_eid.get(emp_num, "") if emp_num else ""
        # 1. 排班表优先
        if eid:
            day = ck_dt.date().strftime("%Y-%m-%d")
            sched = schedule_map.get(eid, {}).get(day)
            if sched and sched.shift_type == "休息":
                # 休息日来上班(Owner 2026-08-21 口径A): 正常出勤, 不判迟到不判异常
                return ("休息日加班", False)
            elif sched and sched.shift_type:
                stype = sched.shift_type
                # 找该班次类型的默认时间, 用于迟到判定
                from hb_attendance_app.hbos_attendance.shift_rules import BUILTIN_SHIFTS
                default = BUILTIN_SHIFTS.get(stype)
                if default:
                    late_after = default[2]
                    ts = ck_dt.strftime("%H:%M:%S")
                    # 夜班跨零点特殊处理
                    if stype == "夜班":
                        return (stype, ck_dt.hour < 4 and ts > late_after)
                    return (stype, ts > late_after)
                return (stype, False)
        # 2. 固定班次绑定
        bound_rules = fixed_shift_map.get(eid) if eid else None
        if bound_rules:
            day = ck_dt.date().strftime("%Y-%m-%d")
            # 收集绑定的全部规则(按日期取最新版本), 用 match_rule_by_time 自动选最匹配的
            candidates = []
            for rule_name in bound_rules:
                versions = [
                    v for key, versions in rules_versioned.items()
                    for v in versions
                    if v.name == rule_name and str(v.effective_from) <= day
                ]
                if versions:
                    candidates.append(max(versions, key=lambda v: str(v.effective_from)))
            if candidates:
                from hb_attendance_app.hbos_attendance.shift_rules import match_rule_by_time
                matched = match_rule_by_time(candidates, ck_dt, cross_day)
                if matched:
                    return matched
        return shift_fn_with_rules(ck_dt, emp_num, cross_day)

    # 工号→员工ID 映射(固定班次匹配用)
    emp_num_to_eid = {
        e.employee_number: e.name
        for e in frappe.db.get_all("Employee",
            fields=["name", "employee_number"],
            filters={"employee_number": ["is", "set"]})
    }
    # 工号→部门映射: 环保部/质量控制部配对上限放宽到 18h(Owner 2026-08-27),
    # 其余部门保持 16h
    emp_num_to_dept = {
        e.employee_number: e.department
        for e in frappe.db.get_all("Employee",
            fields=["name", "employee_number", "department"],
            filters={"employee_number": ["is", "set"]})
    }
    MAX_GAP_DEPTS = {"环保部", "质量控制部"}

    emp_night_out_days = {}
    att_to_insert = []
    for eid, cks in by_emp.items():
        cks.sort(key=lambda x: x["time"])
        emp_num = cks[0].get("employee_number", "") if cks else ""
        is_admin = emp_num in ADMIN_NUMS
        # 环保部/质量控制部配对上限 18h, 其余 16h
        max_gap_hours = 18 if emp_num_to_dept.get(emp_num) in MAX_GAP_DEPTS else 16
        # 有排班记录的员工放开行政班约束(排班表明确今天上什么班, 夜班跨天合法)
        has_schedule = bool(schedule_map.get(eid))
        if has_schedule:
            is_admin = False
        skip_forward = is_admin or emp_num in SAFETY_NUMS or emp_num in FOOD_NUMS or _is_exempt(emp_num)
        skip_night_lock = is_admin or emp_num in SAFETY_NUMS or emp_num in FOOD_NUMS
        deduped_cks, dedup_mapping = dedup_checkins_with_mapping(cks, terminal_aware=True)
        atts, roles = pair_employee_checkins(
            deduped_cks, eid, emp_num, shift_fn_with_fixed,
            is_exempt=_is_exempt(emp_num),
            is_admin=is_admin,
            skip_forward=skip_forward,
            skip_night_lock=skip_night_lock,
            emp_leave_dates=emp_leave_dates.get(eid, set()),
            track_roles=True,
            max_gap_hours=max_gap_hours,
            terminal_aware=True,
        )
        # 只保留生成范围内的记录: range_end 之后(今天)的卡只作配对伙伴,
        # 不生成当天考勤记录(当天数据不完整, 下班卡未打, 否则全员假缺勤)
        atts = [a for a in atts if range_start <= a[2] <= range_end]
        # GPS/外勤打卡日期: 去掉 Absent(Owner 2026-08-27 确认, 视为已出勤)
        atts = [
            a for a in atts
            if not (a[3] == "Absent" and (eid, a[2]) in gps_ck_set)
        ]
        att_to_insert.extend(atts)
        emp_night_out_days[eid] = night_out_days_from_roles(deduped_cks, roles)

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

    # 四班次人员(Owner 2026-08-20): 上够8小时算正常出勤, 不足8小时置早退标记
    four_shift_emps = set(
        r[1] for r in deduped
        if frappe.db.get_value("Employee", r[1], "employee_number") in FOUR_SHIFT_NUMS
    )
    deduped = [
        (name, emp, date, status, shift, late, ck, wh, miss_out,
         1 if emp in four_shift_emps and status == "Present" and wh < 8 else 0)
        for name, emp, date, status, shift, late, ck, wh, miss_out in deduped
    ]

    for i in range(0, len(deduped), 500):
        chunk = deduped[i:i+500]
        values = ",".join(
            "('%s','%s','%s','%s','%s',%s,%s,'%s',%s,%s)" % (name, emp, date, status, shift, str(late), str(early), ck, str(wh), str(miss_out))
            for name, emp, date, status, shift, late, ck, wh, miss_out, early in chunk
        )
        frappe.db.sql("INSERT IGNORE INTO tabAttendance (name, employee, attendance_date, status, shift, late_entry, early_exit, creation, working_hours, hbos_missing_out) VALUES " + values)
    frappe.db.commit()

    # ===== 零打卡缺勤: 在职员工当天完全无打卡 =====
    # 豁免顺序(Owner 2026-08-19/20 确认):
    #   请假 → On Leave
    #   豁免名单 → 跳过
    #   行政班周末 → 休息
    #   单天无打卡(连续计数第1天) → 休息, 不判缺勤
    #   连续无打卡从第2天起 → Absent
    # Owner 2026-08-27 修订: 连续无打卡 1-2 天不判缺勤, 连续 3 天及以上才判缺勤
    # 连续计数在有打卡/已有考勤记录/请假/豁免/行政班周末时归零
    zero_absent = []
    leave_absent = []
    emp_streak = {}
    active_emps = frappe.db.get_all(
        "Employee",
        filters={"status": "Active"},
        fields=["name", "employee_number", "department"],
    )

    # 从 range_start 前一天开始, 预置连续计数(该天不生成记录)
    d = _date.fromisoformat(range_start) - _tdelta(days=1)
    end_d = _date.fromisoformat(range_end)
    while d <= end_d:
        ds = d.strftime("%Y-%m-%d")
        is_weekend = d.weekday() >= 5  # 周六(5)/周日(6)
        in_range = range_start <= ds <= range_end
        ck_emps = frappe.db.sql("SELECT DISTINCT ec.employee FROM `tabEmployee Checkin` ec WHERE DATE(ec.time) = %s", ds, as_dict=True)
        ck_emp_set = set(c["employee"] for c in ck_emps)

        for e in active_emps:
            eid = e["name"]
            if eid in ck_emp_set:
                emp_streak[eid] = 0
                continue
            key = eid + "_" + ds
            # 已有考勤记录(配对分支: 有卡或孤卡) → 连续计数归零
            if key in seen:
                emp_streak[eid] = 0
                continue
            # 排班休息日: 无打卡=休息(不生成任何记录)
            if ds in emp_rest_dates.get(eid, set()):
                emp_streak[eid] = 0
                continue
            # 请假豁免
            if ds in emp_leave_dates.get(eid, set()):
                emp_streak[eid] = 0
                if in_range:
                    leave_absent.append(("HBOS-ATT-" + eid + "-" + ds, eid, ds, "On Leave", "", 0, ds + " 00:00:00", 0, 0))
                    seen[key] = leave_absent[-1]
                continue
            # 豁免名单: 不计入异常考勤
            if _is_exempt(e.get("employee_number", "")):
                emp_streak[eid] = 0
                continue
            # 行政班周末双休: 周六/周日无打卡不算缺勤
            if is_weekend and e.get("employee_number", "") in ADMIN_NUMS:
                emp_streak[eid] = 0
                continue
            # 夜班下班次日休息(叠加豁免, Owner 2026-08-20 确认):
            # 前一天是夜班下班日(8-10点打下班卡) → 休息, 且连续计数归零
            if (d - _tdelta(days=1)) in emp_night_out_days.get(eid, set()):
                emp_streak[eid] = 0
                continue
            # 连续无打卡 1-2 天不判缺勤, 连续 3 天及以上才判缺勤 (Owner 2026-08-27 确认)
            emp_streak[eid] = emp_streak.get(eid, 0) + 1
            if emp_streak[eid] >= 3 and in_range:
                zero_absent.append(("HBOS-ATT-" + eid + "-" + ds, eid, ds, "Absent", "", 0, ds + " 00:00:00", 0, 0))
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

    # 注意: 原「孤卡补缺」逻辑已删除（Owner 2026-08-17 确认）——
    # 员工当天打卡全部被前一夜班配对消耗时（下夜班休息日，如早晨 8 点的下班卡
    # 配给前晚夜班），当天视为休息日，不再补判缺勤。
    # 见 docs/HBOS考勤判定规则.md 5.3 修订与 pairing.py。

    return {
        "paired_present": sum(1 for x in deduped if x[3] == "Present"),
        "paired_absent": sum(1 for x in deduped if x[3] == "Absent"),
        "zero_absent": len(zero_absent),
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

    # 1. 查询迟到/早退记录（含首次/末次打卡时间）；豁免名单不计入异常考勤
    exempt_where = ""
    if EXEMPT_NUMS:
        quoted = ",".join("'%s'" % v.replace("'", "") for v in sorted(EXEMPT_NUMS))
        exempt_where = f" AND emp.employee_number NOT IN ({quoted})"
    records = frappe.db.sql(f"""
        SELECT a.employee, a.employee_name, emp.employee_number, emp.department,
               a.attendance_date, a.late_entry, a.early_exit, a.shift, a.working_hours,
               (SELECT MIN(ec.time) FROM `tabEmployee Checkin` ec
                WHERE ec.employee = a.employee AND DATE(ec.time) = a.attendance_date) as first_checkin,
               (SELECT MAX(ec.time) FROM `tabEmployee Checkin` ec
                WHERE ec.employee = a.employee AND DATE(ec.time) = a.attendance_date) as last_checkin
        FROM tabAttendance a
        LEFT JOIN tabEmployee emp ON emp.name = a.employee
        WHERE (a.late_entry = 1 OR a.early_exit = 1)
          AND a.docstatus < 2{exempt_where}
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