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
            if _to_secs(st) == 0:
                late_after = r.get("late_after") or BUILTIN_SHIFTS.get(r["shift_type"], ("", "", "", 8))[2]
                return (r["shift_type"], ck_secs > _to_secs(late_after))
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
            late_after = r.get("late_after") or BUILTIN_SHIFTS.get(r["shift_type"], ("", "", "", 8))[2]
            best = (r["shift_type"], ck_secs > _to_secs(late_after))
    return best


def _to_secs(t_str):
    try:
        hh, mm, ss = (t_str or "00:00:00").split(":")
        return int(hh) * 3600 + int(mm) * 60 + int(ss)
    except Exception:
        return 0
