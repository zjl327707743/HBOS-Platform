"""HBOS 看板/通知共用统计口径（纯模块，无 frappe 依赖，可离线测试）。

口径（Owner 2026-09-08 / 2026-09-10 确认）:
  应出勤 expected = kind == "shift" 的行（含缺勤行）
  已到岗 present  = 有卡/考勤出勤（迟到也算到岗）
  迟到   late     = state == "late" 或 tags 含「迟到」（覆盖回顾模式 HRMS 标签）
  缺勤   absent   = state == "absent_day"（仅已定性缺勤；计入 expected，不计入 noCard）
  无打卡 noCard   = 期望上班、未到岗、且 state 不属于 {before_start, absent_day}
  恒等: expected == present + noCard + absent
"""

PRESENT_STATES = {
    "present", "late", "fact_present", "present_offwindow", "out_day", "out_offwindow",
}

_EMPTY = {
    "total": 0, "expected": 0, "present": 0, "late": 0,
    "noCard": 0, "absent": 0, "leave": 0, "rest": 0, "exempt": 0,
    "attendance_rate": None,
}


def _tags(r):
    return r.get("tags") or []


def is_late(r):
    return r.get("state") == "late" or "迟到" in _tags(r)


def summarize_rows(rows):
    """按口径汇总一组行，返回计数与出勤率。"""
    s = dict(_EMPTY)
    s["total"] = len(rows)
    for r in rows:
        st = r.get("state")
        if st == "exempt":
            s["exempt"] += 1
            continue
        if st == "rest":
            s["rest"] += 1
            continue
        if st == "leave":
            s["leave"] += 1
            continue
        if st == "unknown":
            continue
        if r.get("kind") != "shift":
            continue
        s["expected"] += 1
        if is_late(r):
            s["late"] += 1
        if st == "absent_day":
            s["absent"] += 1
            continue
        if st in PRESENT_STATES:
            s["present"] += 1
        elif st != "before_start":
            s["noCard"] += 1
    s["attendance_rate"] = (
        round(s["present"] / s["expected"] * 100, 1) if s["expected"] else None
    )
    return s


def group_by_dept(rows):
    """按部门分组；无部门归「未分组」（保持首次出现顺序）。"""
    out = {}
    for r in rows:
        out.setdefault(r.get("dept") or "未分组", []).append(r)
    return out


def dept_summary(rows):
    """每部门一行汇总，按 (未打卡+迟到) 降序、其次在册人数降序。"""
    out = []
    for dept, drows in group_by_dept(rows).items():
        s = summarize_rows(drows)
        out.append({
            "dept": dept,
            "total": s["total"],
            "expected": s["expected"],
            "present": s["present"],
            "noCard": s["noCard"],
            "late": s["late"],
            "absent": s["absent"],
            "leave": s["leave"],
        })
    out.sort(key=lambda d: (-(d["noCard"] + d["late"]), -d["total"]))
    return out
