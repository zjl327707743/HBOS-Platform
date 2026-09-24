"""HBOS 看板/通知共用统计口径（纯模块，无 frappe 依赖，可离线测试）。

口径（Owner 2026-09-08 / 2026-09-11 确认「方案甲」）:
  应出勤 expected   = kind == "shift" 的全部行（分母）
  已到岗 present    = 有到岗卡/考勤出勤（迟到也算到岗）
  迟到   late       = state == "late" 或 tags 含「迟到」（覆盖回顾模式 HRMS 标签）
  未打卡 noCard     = 班次已开始却无到岗卡 → 真预警（absent_expected / no_pair / pending）
  仅下班卡 outOnly  = out_only（跨天夜班次日只刷到下班机）
  班次未定 unknownTime = fact_none（无排班/无绑定，系统不知其上班时间）
  未开始 notStarted = before_start（班次尚未到上班时间）
  缺勤   absent     = absent_day（仅回顾模式的 HRMS Absent）

恒等（每个 state 恰好归入一处）:
  expected == present + noCard + outOnly + unknownTime + notStarted + absent
"""

PRESENT_STATES = {
    "present", "late", "fact_present", "present_offwindow", "out_day", "out_offwindow",
}
OUT_ONLY_STATES = {"out_only"}
UNKNOWN_TIME_STATES = {"fact_none"}
NOT_STARTED_STATES = {"before_start"}
NO_CARD_STATES = {"absent_expected", "no_pair", "pending"}
ABSENT_STATES = {"absent_day"}

_EMPTY = {
    "total": 0, "expected": 0, "present": 0, "late": 0, "noCard": 0,
    "outOnly": 0, "unknownTime": 0, "notStarted": 0, "absent": 0,
    "leave": 0, "rest": 0, "exempt": 0, "attendance_rate": None,
}


def is_late(r):
    return r.get("state") == "late" or "迟到" in (r.get("tags") or [])


def summarize_rows(rows):
    """按口径汇总一组行，返回各桶计数与出勤率。"""
    s = dict(_EMPTY)
    s["total"] = len(rows)
    for r in rows:
        # 「看板不显示异常」的人（Owner 2026-09-11，如设备动力部）：仍出现在明细里，
        # 但不参与任何桶的统计——否则部门表会显示「迟到 5」而展开后一条也看不到。
        if r.get("anomaly_hidden"):
            continue
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
        if st in PRESENT_STATES:
            s["present"] += 1
        elif st in ABSENT_STATES:
            s["absent"] += 1
        elif st in OUT_ONLY_STATES:
            s["outOnly"] += 1
        elif st in UNKNOWN_TIME_STATES:
            s["unknownTime"] += 1
        elif st in NOT_STARTED_STATES:
            s["notStarted"] += 1
        elif st in NO_CARD_STATES:
            s["noCard"] += 1
        # 未知 state 保守落入未打卡, 由恒等断言在测试中暴露
        else:
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
            "dept": dept, "total": s["total"], "expected": s["expected"],
            "present": s["present"], "noCard": s["noCard"], "outOnly": s["outOnly"],
            "unknownTime": s["unknownTime"], "notStarted": s["notStarted"],
            "late": s["late"], "absent": s["absent"], "leave": s["leave"],
        })
    out.sort(key=lambda d: (-(d["noCard"] + d["late"]), -d["total"]))
    return out
