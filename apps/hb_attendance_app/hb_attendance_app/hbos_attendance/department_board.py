"""部门实时出勤看板 - 纯状态判定模块（无 frappe 依赖，可离线测试）。

仅负责「画像/排班/打卡事件 → 期望班次与状态」的纯逻辑；
所有数据读取、名单命中、班次时间解析都在数据层完成，此处不 import 名单常量。
"""
from datetime import datetime, time as _dt_time

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


# --- 以下为接口锁定占位（后续任务实现），保证模块可导入 ---

def live_state(expected, profile, events, now):
    """实时状态行。签名锁定，由后续任务实现（当前仅占位，禁止提前判定）。"""
    raise NotImplementedError("live_state 由后续任务实现")


def day_review(expected, profile, events, now):
    """日终复核状态行。签名锁定，由后续任务实现（当前仅占位，禁止提前判定）。"""
    raise NotImplementedError("day_review 由后续任务实现")
