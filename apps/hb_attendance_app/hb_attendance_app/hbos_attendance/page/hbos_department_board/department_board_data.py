"""部门实时出勤看板数据层：读库 → 组画像 → 调纯函数 → 聚合。

只读 + 节流同步；不写业务数据。
"""
from datetime import datetime, timedelta, timezone

import frappe

from hb_attendance_app.hbos_attendance.department_board import (
    resolve_expected, live_state, day_review, bound_times, pick_bound_rule,
    arrival_events,
)
from hb_attendance_app.hbos_attendance.shift_rules import BUILTIN_SHIFTS
from hb_attendance_app.hbos_attendance.rule_lists import (
    ADMIN_NUMS, EXEMPT_NUMS, FOOD_NUMS, SAFETY_NUMS, LATE_EXEMPT_NUMS,
    ANOMALY_HIDDEN_NUMS,
)
from hb_attendance_app.hbos_attendance.pairing import (
    FOUR_SHIFT_NUMS, SPECIAL_SHIFT_NUMS,
)
from hb_attendance_app.hbos_attendance.board_stats import summarize_rows, dept_summary

# 与 api.py DELICLOUD_TZ 同基准：打卡时间已按 +8 转 naive 存储，今天/now 同用 +8 对齐
TZ_PLUS8 = timezone(timedelta(hours=8))

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
            st, lt = _fmt_hm(r.start_time), _fmt_hm(r.late_after)
            if st:
                return (st, lt)
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


def _fmt_hm(v):
    """Time 字段（frappe 返回 timedelta，或字符串）→ "HH:MM"；无效返回 None。

    注意 str(timedelta(seconds=30660)) == "8:31:00"（不补零），
    直接切片会得到 "8:31:"，故必须按整数重新格式化。
    """
    if v is None or v == "":
        return None
    try:
        parts = str(v).split(":")
        return "%02d:%02d" % (int(parts[0]), int(parts[1]))
    except Exception:
        return None


def _load_bindings(emp_names):
    """employee -> [{shift_type, start_hm, late_hm}, ...]（主班优先）。

    一名员工可绑定多条规则（倒班：如环保部 早班 + 13:00 中班），
    必须全部返回，由调用方按当天打卡时间挑最接近的班次
    （原来只取第一条，倒班人员会被套用错误的班次→误判迟到）。
    """
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
        out.setdefault(b.employee, []).append({
            "shift_type": r.shift_type,
            "start_hm": _fmt_hm(r.start_time),
            "late_hm": _fmt_hm(r.late_after),
        })
    # hbos_fixed_shift 兜底（单绑定字段）
    for e in frappe.db.get_all(
            "Employee", filters={"name": ["in", emp_names], "hbos_fixed_shift": ["is", "set"]},
            fields=["name", "hbos_fixed_shift"]):
        if e.name in out:
            continue
        r = rules.get(e.hbos_fixed_shift)
        if r and r.status == "生效":
            out[e.name] = [{
                "shift_type": r.shift_type,
                "start_hm": _fmt_hm(r.start_time),
                "late_hm": _fmt_hm(r.late_after),
            }]
    return out


def _load_events(date_str, emp_names):
    """返回 (events, out_events)。

    events:     employee -> 当天全部打卡时间(升序)，含 GPS 卡；
    out_events: employee -> 当天「下班机」打卡（按设备 SN 判定；分机实施前为空），
                供「已下班」判定使用——误把上班卡当下班会伪造「已下班」。

    events 升序是纯函数的前置契约，故 SQL 必须 ORDER BY employee, time。
    """
    events, out_events = {}, {}
    if not emp_names:
        return events, out_events
    from hb_attendance_app.hbos_attendance.pairing import role_from_terminal
    rows = frappe.db.sql("""
        SELECT employee, time, hbos_terminal_sn FROM `tabEmployee Checkin`
        WHERE DATE(time) = %(d)s AND employee IN %(emps)s
        ORDER BY employee, time
    """, {"d": date_str, "emps": emp_names}, as_dict=True)
    for r in rows:
        events.setdefault(r.employee, []).append(r.time)
        if role_from_terminal(r.hbos_terminal_sn or "", r.time) == "out":
            out_events.setdefault(r.employee, []).append(r.time)
    return events, out_events


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
    return datetime.now(TZ_PLUS8).replace(tzinfo=None).date()


@frappe.whitelist()
def get_data(department=None, date_str=None):
    """部门看板数据。date_str 缺省=今天；仅允许今天及以前（实时/回顾）。"""
    frappe.only_for(["HR Manager", "HR User", "System Manager"])
    today = _today()
    if not date_str:
        date_str = today.isoformat()
        target = today
    else:
        try:
            target = datetime.strptime(str(date_str), "%Y-%m-%d").date()
        except Exception:
            frappe.throw("日期格式应为 YYYY-MM-DD")
        if target > today:
            frappe.throw("不能查看未来日期")

    now = datetime.now(TZ_PLUS8).replace(tzinfo=None, microsecond=0)
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
                "stats": summarize_rows([]), "dept_stats": [], "rows": []}

    emp_names = [e.name for e in emps]
    schedule = _load_schedule(date_str, emp_names)
    leave_recs = _load_leave_records(date_str, emp_names)
    bindings = _load_bindings(emp_names)
    events, out_events = _load_events(date_str, emp_names)
    attendance = _load_attendance(date_str, emp_names)

    def _profile(e):
        num = e.employee_number or ""
        sched = schedule.get(e.name)
        if sched and sched["kind"] == "shift" and sched["shift_type"] and not sched["start_time"]:
            # 排班班次时间：优先用部门规则，其次内置
            st, lt = _rule_times_for(e.department or "", sched["shift_type"], target)
            sched = dict(sched, start_time=st, late_after=lt)
        # 绑定规则：按当天首张「到岗」卡挑最接近的班次（倒班人员绑定多个班次）
        # 注意必须排除下班机卡——夜班人员凌晨的下班卡会把参考时间拉到 00:0x，
        # 从而挑中错误的班次并误判迟到（卞德志 9/10：00:01 下班卡 + 15:53 上班卡）。
        ev_today = events.get(e.name, [])
        arrivals_today = arrival_events(ev_today, out_events.get(e.name, []))
        ref_hm = arrivals_today[0].strftime("%H:%M") if arrivals_today else None
        picked = pick_bound_rule(bindings.get(e.name) or [], ref_hm)
        if picked:
            bound_shift = picked[0]
            b_start, b_late = bound_times(picked[1], picked[2])
        else:
            bound_shift, b_start, b_late = (None, None, None)
        return {
            "num": num,
            "exempt": num in EXEMPT_NUMS,
            "late_exempt": num in LATE_EXEMPT_NUMS,
            "admin_list": num in ADMIN_NUMS,
            "food": num in FOOD_NUMS,
            "safety": num in SAFETY_NUMS,
            "rotate_label": _rotating_label(ROTATE_SYSTEM, num) or "通用倒班",
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
        # 豁免人员（管理层/产假/长期病假等不计异常考勤者）不进看板（Owner 2026-09-11）。
        # 在源头跳过：KPI、部门表、明细因此一致，无需各处分别过滤。
        if p["exempt"]:
            continue
        ev = events.get(e.name, [])
        outs = out_events.get(e.name, [])
        exp = resolve_expected(p, weekday)
        if mode == "review":
            st = day_review(exp, p, ev, now, attendance=attendance.get(e.name),
                            out_events=outs, day=target)
        else:
            st = live_state(exp, p, ev, now, out_events=outs, day=target)
        rows.append({
            "dept": e.department or "",
            "num": p["num"],
            "name": e.employee_name or "",
            "expected_label": exp["label"],
            "kind": exp["kind"],
            "fact_only": exp.get("start_time") is None or exp.get("late_after") is None,
            "state": st["state"], "label": st["label"],
            "first_hm": st["first_hm"], "out_hm": st.get("out_hm"),
            "card_count": st["card_count"],
            "tags": st["tags"], "note": st["note"],
            # 看板不显示异常（Owner 2026-09-11，如设备动力部）：行照常展示，
            # 但统计口径与前端都不把它当异常（判定与数据均未改动）
            "anomaly_hidden": p["num"] in ANOMALY_HIDDEN_NUMS,
        })

    return {"departments": _all_depts(), "meta": {"date": date_str, "mode": mode,
                                                  "now_hm": now.strftime("%H:%M"),
                                                  "scope": department or "全部部门"},
            "stats": summarize_rows(rows), "dept_stats": dept_summary(rows), "rows": rows}


def _all_depts():
    """按部门统计在册人数；豁免人员不计入（与看板口径一致，Owner 2026-09-11）。"""
    where = "WHERE status = 'Active'"
    values = ()
    if EXEMPT_NUMS:
        where += " AND IFNULL(employee_number, '') NOT IN (%s)" % ", ".join(
            ["%s"] * len(EXEMPT_NUMS))
        values = tuple(sorted(EXEMPT_NUMS))
    return frappe.db.sql("""
        SELECT department AS name, COUNT(*) AS count FROM tabEmployee
        %s GROUP BY department ORDER BY department
    """ % where, values, as_dict=True)


SYNC_THROTTLE_SECONDS = 120  # live_sync 手动同步最小间隔（秒）


@frappe.whitelist()
def live_sync():
    """手动触发得力云打卡同步（节流 ≥120s），返回同步结果。"""
    frappe.only_for(["HR Manager", "HR User", "System Manager"])
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
