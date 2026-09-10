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


def _plus_one_minute(hm):
    """返回 HM 之后 1 分钟的 "HH:MM"（跨零点回到 00:00）。"""
    h, m = (hm or "00:00").split(":")[:2]
    total = (int(h) * 60 + int(m) + 1) % (24 * 60)
    return f"{total // 60:02d}:{total % 60:02d}"


def bound_times(start_hm, late_hm):
    """绑定的迟到起算点：缺省或早于上班时间（规则数据错误）时回落到上班时间 +1 分钟。

    例：环保部「两班倒中班 13:00-20:00」的 late_after 误填 08:31（比上班时间还早），
    若不修正，「首卡晚于 late_after 即迟到」对任何 08:31 之后的到岗都成立 → 必然误判迟到。
    """
    if not start_hm:
        return (start_hm, late_hm)
    if not late_hm or late_hm <= start_hm:
        return (start_hm, _plus_one_minute(start_hm))
    return (start_hm, late_hm)


def pick_bound_rule(bound_rules, ref_hm):
    """在多条绑定规则里挑与参考时间最接近的上班时间那条（倒班人员会绑定多个班次）。

    bound_rules: [{"shift_type","start_hm","late_hm"}, ...]
    ref_hm: 当天首张到岗卡时间 "HH:MM"；为 None（当天无卡）时取第一条（主班）。
    返回 (shift_type, start_hm, late_hm) 或 None。
    """
    if not bound_rules:
        return None
    if not ref_hm:
        r = bound_rules[0]
        return (r.get("shift_type"), r.get("start_hm"), r.get("late_hm"))
    try:
        h, m = ref_hm.split(":")[:2]
        ref_min = int(h) * 60 + int(m)
    except Exception:
        r = bound_rules[0]
        return (r.get("shift_type"), r.get("start_hm"), r.get("late_hm"))

    best = None
    best_dist = None
    for r in bound_rules:
        st = r.get("start_hm")
        if not st:
            continue
        try:
            sh, sm = st.split(":")[:2]
            st_min = int(sh) * 60 + int(sm)
        except Exception:
            continue
        dist = abs(ref_min - st_min)
        if best_dist is None or dist < best_dist:
            best_dist = dist
            best = r
    if best is None:
        return None
    return (best.get("shift_type"), best.get("start_hm"), best.get("late_hm"))


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
        stype = profile.get("bound_shift_type")
        st_hm = profile.get("bound_start")
        # 带上上班时间：同一 shift_type 可能对应多个时段（如环保部 13:00-20:00 记作「行政班」），
        # 只显示类型名会误导（看着像 08:30 上班）
        label = f"{stype} {st_hm}" if (stype and st_hm) else (stype or "固定班次")
        return {"kind": "shift", "shift_type": stype,
                "start_time": st_hm, "late_after": profile.get("bound_late"),
                "label": label}

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


def arrival_events(events, out_events):
    """可用于「到岗」判定的卡：剔除已知的下班机卡。

    夜班人员当天的下班卡（早上 8 点或凌晨离开）若被当成到岗卡，会误判迟到
    （吕玉升 2026-09-10：08:01 下班机卡被算成早班到岗 → 误标迟到）。
    方向未知的卡（分机实施前、GPS/手机打卡、未登记设备）仍保留，不改变旧行为。
    """
    if not out_events:
        return events
    outs = set(out_events)
    return [e for e in events if e not in outs]


def _out_only_state(events, out_events, now):
    """当天只有下班机卡、没有到岗卡 → 只报事实，不判到岗/迟到/缺勤。"""
    outs = sorted(out_events) if out_events else sorted(events)
    last = outs[-1] if outs else None
    return {"state": "out_only", "label": "仅下班卡",
            "first_hm": None, "out_hm": last.strftime("%H:%M") if last else None,
            "card_count": len(events), "tags": [],
            "note": "当天仅有下班卡，无到岗卡，未判迟到/缺勤"}


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
    st = _live_state_inner(expected, profile, events, now, out_events)
    if st.get("out_hm") is None:
        st["out_hm"] = _out_hm(st["state"], st["first_hm"], out_events or [], day or now.date())
    return st


def _live_state_inner(expected, profile, events, now, out_events=None):
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
    arrivals = arrival_events(events, out_events)

    # 当天只有下班机卡（无到岗卡）：班次还没开始 → 尚未上班；已过班次点 → 只报事实
    if events and not arrivals:
        start_dt_ = _hm_to_dt(start, day)
        if start and start_dt_ and now < start_dt_:
            return {"state": "before_start", "label": f"未开始（{start} 上班）",
                    "first_hm": None, "card_count": len(events), "tags": [], "note": ""}
        return _out_only_state(events, out_events, now)

    # 到点判定不适用（起算点未知/食堂）→ 只报打卡事实
    # 文案区分「已打卡（有个卡，但不知道几点上班，不判到点）」与「已到岗（按班次判定的到岗）」
    if not start or not late:
        if arrivals:
            first = arrivals[0]
            return {"state": "fact_present", "label": f"已打卡 {first.strftime('%H:%M')}",
                    "first_hm": first.strftime("%H:%M"), "card_count": len(events),
                    "tags": [], "note": "仅记录打卡事实，不判到点/迟到（班次起算点待排班/规则确认）"}
        return {"state": "fact_none", "label": "无打卡记录",
                "first_hm": None, "card_count": 0, "tags": [],
                "note": "仅记录打卡事实，不判到点/迟到（班次起算点待排班/规则确认）"}

    win = _window_start_hm(start)
    start_dt = _hm_to_dt(start, day)
    late_dt = _hm_to_dt(late, day)
    first = _first_in_window(arrivals, win, day)

    if not first:
        if arrivals:
            f0 = arrivals[0]
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
    st = _day_review_inner(expected, profile, events, now, attendance, out_events)
    if st.get("out_hm") is None:
        st["out_hm"] = _out_hm(st["state"], st["first_hm"], out_events or [], day or now.date())
    return st


def _day_review_inner(expected, profile, events, now, attendance=None, out_events=None):
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

    arrivals = arrival_events(events, out_events)

    # 当天只有下班机卡（无到岗卡）→ 只报事实，不判到岗/迟到（与实时模式同口径）
    if events and not arrivals:
        return _out_only_state(events, out_events, now)

    if not expected.get("start_time") or not expected.get("late_after"):
        if arrivals:
            f0 = arrivals[0]
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
    f0 = arrivals[0]
    return {"state": "out_offwindow", "label": f"已打卡 {f0.strftime('%H:%M')}",
            "first_hm": f0.strftime("%H:%M"), "card_count": len(events),
            "tags": [], "note": "当日有卡但无 HRMS 配对考勤结果"}
