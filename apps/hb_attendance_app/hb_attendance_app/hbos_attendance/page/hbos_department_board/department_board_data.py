"""部门实时出勤看板数据层：读库 → 组画像 → 调纯函数 → 聚合。

只读 + 节流同步；不写业务数据。
"""
from datetime import datetime

import frappe

from hb_attendance_app.hbos_attendance.department_board import (
    resolve_expected, live_state, day_review,
)
from hb_attendance_app.hbos_attendance.shift_rules import BUILTIN_SHIFTS
from hb_attendance_app.hbos_attendance.rule_lists import (
    ADMIN_NUMS, EXEMPT_NUMS, FOOD_NUMS, SAFETY_NUMS,
)
from hb_attendance_app.hbos_attendance.pairing import (
    FOUR_SHIFT_NUMS, SPECIAL_SHIFT_NUMS,
)

ROTATE_SYSTEM = {
    "四班次倒班": FOUR_SHIFT_NUMS,
    "无菌倒班": SPECIAL_SHIFT_NUMS,
}


def _rotating_label(nums_by_system, num):
    for label, nums in nums_by_system.items():
        if num in nums:
            return label
    return None


def _builtin_times(shift_type):
    b = BUILTIN_SHIFTS.get(shift_type)
    if not b:
        return (None, None)
    return (b[0][:5], b[2][:5])  # "HH:MM"


def _rule_times_for(dept, shift_type, effective_on):
    """规则表优先：部门精确 → 全部部门 → 内置兜底。返回 (start_hm, late_hm)。"""
    for target in (dept, "全部部门"):
        rows = frappe.db.get_all(
            "HBOS Shift Rule",
            filters={"department": target, "shift_type": shift_type, "status": "生效",
                     "effective_from": ["<=", effective_on]},
            fields=["start_time", "late_after", "effective_from"],
        )
        if rows:
            r = max(rows, key=lambda x: str(x.effective_from or ""))
            if r.start_time and r.late_after:
                return (str(r.start_time)[:5], str(r.late_after)[:5])
            if r.start_time:
                return (str(r.start_time)[:5], None)
    return _builtin_times(shift_type)


def _load_schedule(date_str, emp_names):
    if not emp_names:
        return {}
    out = {}
    rows = frappe.db.get_all(
        "HBOS Employee Schedule",
        filters={"schedule_date": date_str, "employee": ["in", emp_names]},
        fields=["employee", "shift_type", "leave_type"],
    )
    for r in rows:
        st = (r.shift_type or "").strip()
        lt = (r.leave_type or "").strip()
        if lt:
            out[r.employee] = {"kind": "leave", "shift_type": None,
                               "start_time": None, "late_after": None, "leave_type": lt}
        elif st == "休息":
            out[r.employee] = {"kind": "rest", "shift_type": "休息",
                               "start_time": None, "late_after": None, "leave_type": None}
        elif st:
            out[r.employee] = {"kind": "shift", "shift_type": st,
                               "start_time": None, "late_after": None, "leave_type": None}
    return out


def _load_leave_records(date_str, emp_names):
    if not emp_names:
        return {}
    out = {}
    rows = frappe.db.get_all(
        "HBOS Leave Record",
        filters={"approval_status": "已通过",
                 "start_date": ["<=", date_str], "end_date": [">=", date_str],
                 "employee": ["in", emp_names]},
        fields=["employee", "leave_type"],
    )
    for r in rows:
        out.setdefault(r.employee, r.leave_type)
    return out


def _load_bindings(emp_names):
    """employee -> (shift_type, start_hm, late_hm)。HBOS Employee Shift 主班优先，
    否则 hbos_fixed_shift 回退（对照 roster_export 口径）。"""
    if not emp_names:
        return {}
    binds = frappe.db.get_all(
        "HBOS Employee Shift", fields=["employee", "shift_rule", "is_primary"])
    rules = {r.name: r for r in frappe.db.get_all(
        "HBOS Shift Rule", fields=["name", "shift_type", "start_time", "late_after", "status"])}
    out = {}
    for b in sorted(binds, key=lambda x: not x.is_primary):
        if b.employee not in emp_names:
            continue
        r = rules.get(b.shift_rule)
        if not r or r.status != "生效":
            continue
        out.setdefault(b.employee, (r.shift_type, str(r.start_time or "")[:5] or None,
                                    str(r.late_after or "")[:5] or None))
    # hbos_fixed_shift 兜底
    for e in frappe.db.get_all(
            "Employee", filters={"name": ["in", emp_names], "hbos_fixed_shift": ["is", "set"]},
            fields=["name", "hbos_fixed_shift"]):
        if e.name in out:
            continue
        r = rules.get(e.hbos_fixed_shift)
        if r and r.status == "生效":
            out[e.name] = (r.shift_type, str(r.start_time or "")[:5] or None,
                           str(r.late_after or "")[:5] or None)
    return out


def _load_events(date_str, emp_names):
    """employee -> list[datetime]，含 GPS 卡；升序。"""
    if not emp_names:
        return {}
    out = {}
    rows = frappe.db.sql("""
        SELECT employee, time FROM `tabEmployee Checkin`
        WHERE DATE(time) = %(d)s AND employee IN %(emps)s
        ORDER BY employee, time
    """, {"d": date_str, "emps": emp_names}, as_dict=True)
    for r in rows:
        out.setdefault(r.employee, []).append(r.time)
    return out


def _load_attendance(date_str, emp_names):
    if not emp_names:
        return {}
    out = {}
    rows = frappe.db.get_all(
        "Attendance", filters={"attendance_date": date_str, "employee": ["in", emp_names],
                               "docstatus": ["<", 2]},
        fields=["employee", "status", "late_entry", "early_exit"],
    )
    for r in rows:
        out[r.employee] = {"status": r.status, "late_entry": r.late_entry,
                           "early_exit": r.early_exit}
    return out


def _today():
    return datetime.strptime(frappe.utils.today(), "%Y-%m-%d").date()


@frappe.whitelist()
def get_data(department=None, date_str=None):
    """部门看板数据。date_str 缺省=今天；仅允许今天及以前（实时/回顾）。"""
    today = _today()
    if not date_str:
        date_str = frappe.utils.today()
        target = today
    else:
        try:
            target = datetime.strptime(str(date_str), "%Y-%m-%d").date()
        except Exception:
            frappe.throw("日期格式应为 YYYY-MM-DD")
        if target > today:
            frappe.throw("不能查看未来日期")

    now = datetime.now().replace(microsecond=0)
    mode = "live" if target == today else "review"
    weekday = target.weekday()

    emps = frappe.db.get_all(
        "Employee", filters={"status": "Active"},
        fields=["name", "employee_number", "employee_name", "department"],
        order_by="department, employee_number",
    )
    if department and department != "全部部门":
        emps = [e for e in emps if (e.department or "") == department]
    if not emps:
        return {"departments": _all_depts(), "meta": {"date": date_str, "mode": mode,
                                                      "now_hm": now.strftime("%H:%M"),
                                                      "scope": department or "全部部门"},
                "stats": _empty_stats(), "rows": []}

    emp_names = [e.name for e in emps]
    schedule = _load_schedule(date_str, emp_names)
    leave_recs = _load_leave_records(date_str, emp_names)
    bindings = _load_bindings(emp_names)
    events = _load_events(date_str, emp_names)
    attendance = _load_attendance(date_str, emp_names)

    def _profile(e):
        num = e.employee_number or ""
        sched = schedule.get(e.name)
        if sched and sched["kind"] == "shift" and sched["shift_type"] and not sched["start_time"]:
            # 排班班次时间：优先用部门规则，其次内置
            st, lt = _rule_times_for(e.department or "", sched["shift_type"], target)
            sched = dict(sched, start_time=st, late_after=lt)
        bound_shift, b_start, b_late = bindings.get(e.name, (None, None, None))
        return {
            "num": num,
            "exempt": num in EXEMPT_NUMS,
            "admin_list": num in ADMIN_NUMS,
            "food": num in FOOD_NUMS,
            "safety": num in SAFETY_NUMS,
            "rotate_label": _rotating_label(ROTATE_SYSTEM, num),
            "bound": bool(bound_shift),
            "bound_shift_type": bound_shift,
            "bound_start": b_start,
            "bound_late": b_late,
            "schedule": sched,
            "leave_record": e.name in leave_recs,
            "leave_record_type": leave_recs.get(e.name),
        }

    rows = []
    for e in emps:
        p = _profile(e)
        ev = events.get(e.name, [])
        exp = resolve_expected(p, weekday)
        if mode == "review":
            st = day_review(exp, p, ev, now, attendance=attendance.get(e.name))
        else:
            st = live_state(exp, p, ev, now)
        rows.append({
            "dept": e.department or "",
            "num": p["num"],
            "name": e.employee_name or "",
            "expected_label": exp["label"],
            "kind": exp["kind"],
            "fact_only": exp.get("start_time") is None or exp.get("late_after") is None,
            "state": st["state"], "label": st["label"],
            "first_hm": st["first_hm"], "card_count": st["card_count"],
            "tags": st["tags"], "note": st["note"],
        })

    stats = _aggregate(rows)
    return {"departments": _all_depts(), "meta": {"date": date_str, "mode": mode,
                                                  "now_hm": now.strftime("%H:%M"),
                                                  "scope": department or "全部部门"},
            "stats": stats, "rows": rows}


def _all_depts():
    return frappe.db.sql("""
        SELECT department AS name, COUNT(*) AS count FROM tabEmployee
        WHERE status = 'Active' GROUP BY department ORDER BY department
    """, as_dict=True)


def _empty_stats():
    return {"total": 0, "expected": 0, "present": 0, "late": 0, "no_card": 0,
            "leave": 0, "rest": 0, "exempt": 0, "unknown": 0, "attendance_rate": None}


_PRESENT_STATES = {"present", "late", "fact_present", "present_offwindow",
                   "out_day", "out_offwindow"}


def _aggregate(rows):
    """统计卡聚合。

    口径（Owner 2026-09-08 确认）：出勤率分母 = 全部应出勤(kind=shift)；
    已到岗(present) = 有卡/考勤出勤；缺勤/未到会真实拉低出勤率。
    before_start(未到上班点) 不计入「未打卡/无考勤」。late 计入 present 与 expected。
    """
    s = _empty_stats()
    s["total"] = len(rows)
    expected = present = no_card = 0
    for r in rows:
        if r["state"] == "late":
            s["late"] += 1
        if r["state"] == "exempt":
            s["exempt"] += 1
        elif r["state"] == "rest":
            s["rest"] += 1
        elif r["state"] == "leave":
            s["leave"] += 1
        elif r["kind"] == "shift":
            expected += 1
            if r["state"] in _PRESENT_STATES:
                present += 1
            elif r["state"] != "before_start":
                no_card += 1
        else:
            s["unknown"] += 1
    s["expected"] = expected
    s["present"] = present
    s["no_card"] = no_card
    s["attendance_rate"] = round(present / expected * 100, 1) if expected else None
    return s


SYNC_THROTTLE_SECONDS = 120  # live_sync 手动同步最小间隔（秒）


@frappe.whitelist()
def live_sync():
    """手动触发得力云打卡同步（节流 ≥120s），返回同步结果。"""
    import time
    key = "hbos_department_board_live_sync_at"
    last = frappe.cache.get_value(key)
    if last:
        try:
            last_f = float(last)
        except Exception:
            last_f = 0
        left = SYNC_THROTTLE_SECONDS - (time.time() - last_f)
        if left > 0:
            return {"throttled": True, "seconds_left": int(left)}
    from hb_attendance_app.hbos_attendance.api import sync_delicloud_checkin
    try:
        result = sync_delicloud_checkin()
    except Exception as e:
        frappe.log_error(str(e), "部门看板手动同步")
        return {"throttled": False, "error": f"同步失败: {e}"}
    frappe.cache.set_value(key, str(time.time()))
    return {"throttled": False, "result": result}
