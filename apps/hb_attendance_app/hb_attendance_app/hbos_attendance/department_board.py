"""部门实时出勤看板 - 纯状态判定模块（无 frappe 依赖，可离线测试）。

仅负责「画像/排班/打卡事件 → 期望班次与状态」的纯逻辑；
所有数据读取、名单命中、班次时间解析都在数据层完成，此处不 import 名单常量。
"""
from datetime import datetime

# 行政班名单人员无排班/绑定时的工作日起算点
ADMIN_WORK_START = "08:30"
ADMIN_WORK_LATE = "08:31"


def _hm_to_dt(hm, day):
    if not hm:
        return None
    try:
        h, m = (hm or "00:00").split(":")[:2]
        return datetime(day.year, day.month, day.day, int(h), int(m))
    except Exception:
        return None


def resolve_expected(profile, weekday):
    """返回该员工在目标日期的期望班次。weekday: 0=周一 .. 6=周日。

    优先级: 豁免 > 排班 > 固定绑定 > 名单归类 > 在册待确认。
    """
    if profile.get("exempt"):
        return {"kind": "exempt", "shift_type": None, "start_time": None,
                "late_after": None, "label": "豁免"}

    s = profile.get("schedule")
    if s:
        if s.get("kind") == "rest":
            return {"kind": "rest", "shift_type": "休息", "start_time": None,
                    "late_after": None, "label": "休息"}
        if s.get("kind") == "leave":
            lt = s.get("leave_type") or ""
            return {"kind": "leave", "shift_type": None, "start_time": None,
                    "late_after": None, "label": f"请假（{lt}）" if lt else "请假"}
        if s.get("kind") == "shift":
            return {"kind": "shift", "shift_type": s.get("shift_type"),
                    "start_time": s.get("start_time"), "late_after": s.get("late_after"),
                    "label": s.get("shift_type") or "排班"}

    if profile.get("bound"):
        return {"kind": "shift", "shift_type": profile.get("bound_shift_type"),
                "start_time": profile.get("bound_start"), "late_after": profile.get("bound_late"),
                "label": profile.get("bound_shift_type") or "固定班次"}

    if profile.get("admin_list"):
        if weekday < 5:
            return {"kind": "shift", "shift_type": "行政班",
                    "start_time": ADMIN_WORK_START, "late_after": ADMIN_WORK_LATE,
                    "label": "行政班"}
        return {"kind": "rest", "shift_type": "休息", "start_time": None,
                "late_after": None, "label": "行政班·周末"}

    if profile.get("food"):
        return {"kind": "shift", "shift_type": None, "start_time": None,
                "late_after": None, "label": "食堂"}
    if profile.get("safety"):
        return {"kind": "shift", "shift_type": None, "start_time": None,
                "late_after": None, "label": "安全倒班"}
    if profile.get("rotate_label"):
        return {"kind": "shift", "shift_type": None, "start_time": None,
                "late_after": None, "label": profile.get("rotate_label")}

    return {"kind": "unknown", "shift_type": None, "start_time": None,
            "late_after": None, "label": "在册待确认"}


# --- 实时/回顾状态判定 ---

def _window_start_hm(start_time):
    """入窗口起点 = start_time - 4h；跨零点钳制到当天 00:00。返回 "HH:MM"。"""
    if not start_time:
        return None
    h, m = (start_time or "00:00").split(":")[:2]
    secs = (int(h) * 60 + int(m)) * 60 - 4 * 3600
    if secs < 0:
        return "00:00"
    hh, mm = divmod(secs // 60, 60)
    return f"{hh:02d}:{mm:02d}"


def _first_in_window(events, window_hm, day):
    wd = _hm_to_dt(window_hm, day)
    if wd is None:
        return None
    for e in events:
        if e >= wd:
            return e
    return None


def _base_state(expected, profile, events, now):
    """把 expected 折叠成展示用基础行状态（不含到点判定前的确定性分支）。"""
    return {
        "state": expected["kind"], "label": expected["label"],
        "first_hm": None, "out_hm": None, "card_count": len(events),
        "tags": [], "note": "",
    }


# 下班认定沿用配对算法的最短班次口径：不足 2 小时的两张卡不算一个班次
MIN_SHIFT_HOURS = 2

# 只有这些状态代表「人已到岗」，才谈得上「已下班」
_ON_DUTY_STATES = {"present", "late", "present_offwindow", "fact_present",
                   "out_day", "out_offwindow"}


def _out_hm(state, first_hm, out_events, day):
    """返回当天的下班打卡时间 "HH:MM"；没有可信下班卡则 None。

    判据（与 pairing 保持一致）：
    - out_events 只收「下班机」卡（数据层按设备 SN 判定），避免误把上班卡当下班；
    - 该下班卡须晚于首次到岗卡、且间隔 >= 最短班次 2 小时（误刷/连刷不算）；
    - 同一天有多张合格下班卡时取最后一张（真正走人的那次）。
    """
    if not out_events or state not in _ON_DUTY_STATES or not first_hm:
        return None
    start = _hm_to_dt(first_hm, day)
    if start is None:
        return None
    qualified = [o for o in out_events
                 if o.date() == day and o > start
                 and (o - start).total_seconds() >= MIN_SHIFT_HOURS * 3600]
    return qualified[-1].strftime("%H:%M") if qualified else None


def live_state(expected, profile, events, now, out_events=None, day=None):
    """实时模式（now 注入）。out_events: 当天下班机打卡（数据层按设备 SN 判定）。

    day: 目标日期（回顾模式下 now 是今天、目标却是历史日，必须显式传入）。
    """
    st = _live_state_inner(expected, profile, events, now)
    st["out_hm"] = _out_hm(st["state"], st["first_hm"], out_events or [], day or now.date())
    return st


def _live_state_inner(expected, profile, events, now):
    kind = expected["kind"]
    # 豁免/休息优先：管理层豁免或排班休息不因请假记录改标
    if kind in ("rest", "exempt"):
        return _base_state(expected, profile, events, now)

    # 排班请假 → 请假（有卡属异常边缘，仍显示请假并提示人工核实）
    if kind == "leave":
        st = _base_state(expected, profile, events, now)
        if events:
            st["note"] = "排班标注请假但当天有打卡，请人工核实"
        return st

    # 已通过请假记录 → 请假（含无排班/绑定/名单命中的 unknown 员工，不被短路）
    if profile.get("leave_record") and not events:
        lt = profile.get("leave_record_type") or ""
        return {"state": "leave", "label": f"请假（{lt}）" if lt else "请假",
                "first_hm": None, "card_count": 0, "tags": [], "note": "已通过请假记录"}

    # 无请假记录的待确认员工 → 在册待确认（防御分支）
    if kind == "unknown":
        return _base_state(expected, profile, events, now)

    start = expected.get("start_time")
    late = expected.get("late_after")
    day = now.date()

    # 到点判定不适用（起算点未知/食堂）→ 只报打卡事实
    # 文案区分「已打卡（有个卡，但不知道几点上班，不判到点）」与「已到岗（按班次判定的到岗）」
    if not start or not late:
        if events:
            first = events[0]
            return {"state": "fact_present", "label": f"已打卡 {first.strftime('%H:%M')}",
                    "first_hm": first.strftime("%H:%M"), "card_count": len(events),
                    "tags": [], "note": "仅记录打卡事实，不判到点/迟到（班次起算点待排班/规则确认）"}
        return {"state": "fact_none", "label": "无打卡记录",
                "first_hm": None, "card_count": 0, "tags": [],
                "note": "仅记录打卡事实，不判到点/迟到（班次起算点待排班/规则确认）"}

    win = _window_start_hm(start)
    start_dt = _hm_to_dt(start, day)
    late_dt = _hm_to_dt(late, day)
    first = _first_in_window(events, win, day)

    if not first:
        if events:
            f0 = events[0]
            return {"state": "present_offwindow", "label": f"已打卡 {f0.strftime('%H:%M')}（班次时段外）",
                    "first_hm": f0.strftime("%H:%M"), "card_count": len(events),
                    "tags": [], "note": ""}
        if now < start_dt:
            return {"state": "before_start", "label": f"未开始（{start} 上班）",
                    "first_hm": None, "card_count": 0, "tags": [], "note": ""}
        if now < late_dt:
            return {"state": "pending", "label": f"未到班次点（{start} 上班，尚未打卡）",
                    "first_hm": None, "card_count": 0, "tags": [], "note": ""}
        return {"state": "absent_expected", "label": "无打卡记录（已到班次点）",
                "first_hm": None, "card_count": 0, "tags": [],
                "note": "班次时段内无卡，未定性为缺勤，请以月度考勤汇总为准"}

    first_hm = first.strftime("%H:%M")
    if first > late_dt:
        return {"state": "late", "label": f"已到岗 {first_hm}", "first_hm": first_hm,
                "card_count": len(events), "tags": ["迟到"], "note": ""}
    return {"state": "present", "label": f"已到岗 {first_hm}", "first_hm": first_hm,
            "card_count": len(events), "tags": [], "note": ""}


def day_review(expected, profile, events, now, attendance=None, out_events=None, day=None):
    """回顾模式。attendance: None | {status, late_entry, early_exit}"""
    st = _day_review_inner(expected, profile, events, now, attendance)
    st["out_hm"] = _out_hm(st["state"], st["first_hm"], out_events or [], day or now.date())
    return st


def _day_review_inner(expected, profile, events, now, attendance=None):
    kind = expected["kind"]
    if attendance:
        a = attendance
        status = a.get("status")
        # 回顾模式也填首卡时间（此前为空），供明细「首卡」列与「已下班」判定使用
        first_hm = events[0].strftime("%H:%M") if events else None
        if status == "Present":
            tags = []
            if a.get("late_entry"):
                tags.append("迟到")
            if a.get("early_exit"):
                tags.append("早退")
            return {"state": "out_day", "label": "出勤", "first_hm": first_hm,
                    "card_count": len(events), "tags": tags, "note": "以 HRMS 考勤结果为准"}
        if status == "Absent":
            return {"state": "absent_day", "label": "缺勤", "first_hm": None,
                    "card_count": len(events), "tags": [], "note": "以 HRMS 考勤结果为准"}
        if status in ("On Leave", "Half Day"):
            return {"state": "leave", "label": "请假", "first_hm": first_hm,
                    "card_count": len(events), "tags": [], "note": "以 HRMS 考勤结果为准"}
        # 其他状态（None/未生成等）回落下方逻辑

    if kind in ("rest", "exempt"):
        return _base_state(expected, profile, events, now)
    if kind == "leave":
        if not events:
            return _base_state(expected, profile, events, now)
        st = _base_state(expected, profile, events, now)
        st["note"] = "排班标注请假但当天有打卡，请人工核实"
        return st
    # 已通过请假记录 → 请假（含无排班/绑定/名单命中的 unknown 员工，不被短路）
    if profile.get("leave_record") and not events:
        lt = profile.get("leave_record_type") or ""
        return {"state": "leave", "label": f"请假（{lt}）" if lt else "请假",
                "first_hm": None, "card_count": 0, "tags": [], "note": "已通过请假记录"}
    # 无请假记录的待确认员工 → 在册待确认（防御分支）
    if kind == "unknown":
        return _base_state(expected, profile, events, now)

    if not expected.get("start_time") or not expected.get("late_after"):
        if events:
            f0 = events[0]
            return {"state": "fact_present", "label": f"已打卡 {f0.strftime('%H:%M')}",
                    "first_hm": f0.strftime("%H:%M"), "card_count": len(events),
                    "tags": [], "note": "班次起算点待排班/规则确认，仅记录打卡事实"}
        return {"state": "fact_none", "label": "无打卡记录",
                "first_hm": None, "card_count": 0, "tags": [],
                "note": "班次起算点待排班/规则确认，仅记录打卡事实"}

    # 期望上班但无当日配对考勤记录：不判缺勤（尊重既有「连续无卡 3 天起判」等口径）
    if not events:
        return {"state": "no_pair", "label": "当日无配对考勤记录",
                "first_hm": None, "card_count": 0, "tags": [],
                "note": "当日有排班/固定班次但无配对考勤记录，未判缺勤"}
    f0 = events[0]
    return {"state": "out_offwindow", "label": f"已打卡 {f0.strftime('%H:%M')}",
            "first_hm": f0.strftime("%H:%M"), "card_count": len(events),
            "tags": [], "note": "当日有卡但无 HRMS 配对考勤结果"}
