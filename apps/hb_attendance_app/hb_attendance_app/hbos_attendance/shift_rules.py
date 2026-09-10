"""HBOS 班次规则查询与匹配（规则表优先, 硬编码兜底）。

数据源: HBOS Shift Rule DocType, 每部门每班次类型一条生效规则。
匹配优先级: 部门精确匹配 > 全局规则(部门="全部部门") > 硬编码兜底。
"""
from datetime import datetime, time as dt_time

# 班次类型 → (默认上班时, 默认下班时, 默认迟到起算, 默认最小工时)
BUILTIN_SHIFTS = {
    "早班": ("08:00:00", "16:00:00", "08:01:00", 8),
    "中班": ("16:00:00", "00:00:00", "16:01:00", 8),
    "夜班": ("00:00:00", "08:00:00", "00:01:00", 8),
    "晚班": ("20:00:00", "08:00:00", "20:01:00", 12),
    "行政班": ("08:30:00", "17:30:00", "08:31:00", 8),
    "8:30班": ("08:30:00", "16:30:00", "08:31:00", 8),
    "无菌早(12h)": ("08:30:00", "20:30:00", "08:31:00", 12),
    "无菌晚(12h)": ("20:30:00", "08:30:00", "20:31:00", 12),
}


def match_rule_by_time(rules, ck_dt, cross_day=False):
    """从规则列表里按打卡时间匹配班次。

    rules: [{"shift_type", "start_time", "late_after", ...}]
    ck_dt: 上班卡时间
    返回 (shift_type, 是否迟到) 或 None(无匹配)。

    匹配策略: 选择「上班时间 ≤ 打卡时间」中差值最小的规则(最接近的班次);
    若所有规则上班时间都晚于打卡时间, 选差值最小者(提前打卡)。
    夜班(0点上班)单独处理: 0-4点的卡优先匹配夜班。
    """
    t = ck_dt.strftime("%H:%M:%S")
    ck_secs = _to_secs(t)
    # 夜班跨零点: 0-4点的卡优先匹配上班时间=00:00的规则
    if ck_secs < 4 * 3600:
        for r in rules:
            st = r.get("start_time") or BUILTIN_SHIFTS.get(r["shift_type"], ("", "", "", 8))[0]
            st_secs = _to_secs(st)
            if st_secs == 0:
                return (r["shift_type"], ck_secs > _effective_late_secs(r, st_secs))
        return None
    # 其余时段: 选上班时间最接近的规则
    best = None
    best_dist = None
    for r in rules:
        st = r.get("start_time") or BUILTIN_SHIFTS.get(r["shift_type"], ("", "", "", 8))[0]
        st_secs = _to_secs(st)
        if st_secs == 0:
            continue  # 夜班规则不参与白天匹配
        dist = abs(ck_secs - st_secs)
        if best_dist is None or dist < best_dist:
            best_dist = dist
            best = (r["shift_type"], ck_secs > _effective_late_secs(r, st_secs))
    return best


def _effective_late_secs(rule, start_secs):
    """规则的迟到起算秒数；数据异常（早于/等于上班时间）时回落「上班 +1 分钟」。

    例：环保部「两班倒中班 13:00-20:00」的 late_after 误填 08:31，
    若不修正，「晚于 late_after 即迟到」对任何 08:31 后到岗恒成立 → 必然误判迟到。
    """
    raw = rule.get("late_after")
    la = _to_secs(raw) if raw else _to_secs(
        BUILTIN_SHIFTS.get(rule["shift_type"], ("", "", "", 8))[2])
    if start_secs and la <= start_secs:
        return start_secs + 60
    return la


def _to_secs(t_val):
    """Time 值 → 当日秒数。

    兼容三种形态：frappe 从库中读出的 datetime.timedelta（Time 字段）、
    字符串 "HH:MM" / "HH:MM:SS"、以及 datetime.time。
    早期实现只按字符串 split，遇到 timedelta 会抛异常被吞成 0，
    导致所有规则被当成 0 点上班（夜班）跳过 —— 规则表实际从未生效。
    """
    if t_val is None or t_val == "":
        return 0
    if hasattr(t_val, "total_seconds"):          # timedelta
        return int(t_val.total_seconds())
    try:
        parts = (str(t_val) or "00:00:00").split(":")
        hh = int(parts[0])
        mm = int(parts[1]) if len(parts) > 1 else 0
        ss = float(parts[2]) if len(parts) > 2 else 0
        return int(hh * 3600 + mm * 60 + ss)
    except Exception:
        return 0
