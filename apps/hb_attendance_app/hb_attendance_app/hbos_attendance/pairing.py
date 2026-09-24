"""HBOS 打卡配对纯函数（无 Frappe 依赖，可离线测试）。

规则依据：docs/HBOS考勤判定规则.md（2026-08-17 修订）

零点夜班规则（Owner 2026-08-17 确认）：
- 夜班时间段 0:00-8:00，0:00 整不算迟到，0:01 起算迟到
- 0-4 点的卡先尝试向前配对（前一天 14 点后的上班卡 = 中班/晚班下班拖过零点）
- 向前配对失败后，尝试与当天 4:00-10:00 的下班卡配对（零点夜班完整班次）
- 两步都失败才判缺勤（凌晨孤卡）

下夜班休息日规则（Owner 2026-08-17 确认）：
- 当天打卡全部被前一夜班配对消耗（如早晨 8 点的下班卡）时，当天视为休息日，
  不补缺勤。原「孤卡补缺」逻辑已删除。

分机上下班规则（Owner 2026-08-19 确认）：
- 上班打卡机 SN：
  - 13750CS_D7C69C16EC0B2447（办公楼外考勤机）
  - 13750CS_02281E713F33A9A8（厂区二道门西考勤机）
- 下班打卡机 SN：
  - 13750CS_9FB66A86CF3487D7（办公楼内考勤机）
  - 13750CS_93C9390B9995FE8C（宿舍二楼东考勤机）
- 分机自 SPLIT_MACHINE_START_DATE（2026-08-15，见下方常量）起实施，
  此日期前所有机器均为普通考勤机（不分方向）
- 该常量及之后：打卡方向优先按设备 SN 判定；常量之前：回退配对算法推断
  （此处曾误写 2026-08-14，与常量不符，见 role_from_terminal 的说明）
"""
from datetime import datetime, timedelta

from hb_attendance_app.hbos_attendance.policy_registry import (
    POLICY_FOUR_SHIFT,
    POLICY_SPECIAL_SHIFT,
    PolicySet,
)

# 上班/下班打卡机 SN（Owner 2026-08-19 确认）
IN_TERMINAL_SNS = {"13750CS_D7C69C16EC0B2447", "13750CS_02281E713F33A9A8"}
OUT_TERMINAL_SNS = {"13750CS_9FB66A86CF3487D7", "13750CS_93C9390B9995FE8C"}

# 分机实施起始日期（Owner 2026-08-20 纠正: 15 号才实施上下分开打卡, 8/14 及之前按旧规则）
SPLIT_MACHINE_START_DATE = "2026-08-15"

# 特殊班次/四班次的“规则类型”仍由代码定义；具体人员由
# HBOS Attendance Policy Assignment 业务数据维护，不在源码保存真实身份。
SPECIAL_SHIFT_NUMS = PolicySet(POLICY_SPECIAL_SHIFT)
FOUR_SHIFT_NUMS = PolicySet(POLICY_FOUR_SHIFT)


def admin_shift_from_gap(ck_dt, gap_h=None):
    """行政班名单人员判定(Owner 2026-08-21): 08:31 起算迟到, 夜间/凌晨卡不判迟到。

    背景: 四车间行政班 08:0x 打卡曾被全局规则表匹配为「早班 08:00 标准」误判迟到,
    名单人员在规则表之后短路此硬编码判定。
    """
    h = ck_dt.hour
    m = ck_dt.minute
    if h >= 20 or h < 4:
        return ("晚班", False)
    return ("行政班早班", (h > 8) or (h == 8 and m >= 31))


def four_shift_from_gap(ck_dt, gap_h):
    """四班次判定: 只判班次名, 不判迟到。

    专属规则(Owner 2026-08-21): 早班有8点/8点半两种, 迟到不卡死,
    只要工作时长满 8 小时就算正常出勤。不足 8 小时由 api.py 置早退标记。
    """
    h = ck_dt.hour
    m = ck_dt.minute
    if h >= 20 or h < 4:
        return ("夜班", False)
    if h < 9:
        if h == 8 and m >= 30:
            return ("8:30班", False)
        return ("早班", False)
    if h < 16:
        return ("行政班", False)
    return ("中班", False)


def safety_shift_from_gap(ck_dt):
    """安全部倒班判定（Owner 2026-09-11 对齐班次规则表「安全部-倒班晚班 21:00-8:30」）。

    晚班 21:00 上班、21:01 起算迟到（原 20:31 会把 20:5x 提前到岗误判迟到，
    樊祥岩/王翔宇/谷亚超 9/10 案例）；早班 8:30 / 8:31 与规则表一致。
    """
    h = ck_dt.hour
    ts = ck_dt.strftime("%H:%M:%S")
    if h >= 20 or h < 4:
        return ("晚班", ts >= "21:01:00")
    return ("早班", ts >= "08:31:00")


def special_shift_from_gap(ck_dt, gap_h=None, emp_num=None):
    """独立班次体系判定（SPECIAL_SHIFT_NUMS 人员专用）。

    参数:
        ck_dt: 上班打卡时间
        gap_h: 该班次时长(小时)，未知时 None
    返回 (班次名, 是否迟到)。

    班次定义（Owner 2026-08-19 确认）:
        无菌早: 8:30-20:30 (12h), 8:31 起算迟到
        无菌晚: 20:30-次日8:30 (12h), 20:31 起算迟到
        早班:   8:30-16:30 (8h), 8:31 起算迟到
        中班:   16:30-次日0:30 (8h), 16:31 起算迟到
        夜班:   0:30-8:30 (8h), 0:31 起算迟到
    12 小时与 8 小时班按时长区分(10h 为界); 时长未知时按时段推断。
    """
    h = ck_dt.hour
    ts = ck_dt.strftime("%H:%M:%S")

    if gap_h is not None and gap_h >= 10:
        # 12小时倒班: 上班卡在 8:30(无菌早) 或 20:30(无菌晚)
        # 19点后开始的 12h 班视为无菌晚提前到岗(张志兴 8/19 案例: 19:56 上班不判迟到)
        if h >= 19:
            return ("无菌晚", ts >= "20:31:00")
        return ("无菌早", ts >= "08:31:00")

    # 8小时班(或时长未知): 按时段推断
    if h < 4:
        return ("夜班", ts > "00:30:00")
    if h < 9:
        return ("早班", ts >= "08:31:00")
    if h < 20:
        return ("中班", ts >= "16:31:00")
    # 20:30 时段按班次定义只有无菌晚
    return ("无菌晚", ts >= "20:31:00")


def role_from_terminal(terminal_sn, checkin_time=None):
    """按设备 SN 判定打卡方向。

    参数:
        terminal_sn: 打卡设备 SN
        checkin_time: 打卡时间（datetime 或 date）。分机自 SPLIT_MACHINE_START_DATE
            （2026-08-15，见文件顶部常量）起实施，此前打卡不按设备判方向，返回 None
            回退配对推断。**注意常量是判定依据，勿按此注释记忆**——本注释曾误写
            8/14，与常量不一致，导致以为「重算 8/14 安全」而生成整日误判缺勤。

    返回 "in"（上班打卡）/ "out"（下班打卡）；未指定设备或分机实施前返回 None。
    """
    if checkin_time is not None:
        from datetime import date as _date
        d = checkin_time.date() if isinstance(checkin_time, datetime) else checkin_time
        if isinstance(d, _date) and d.strftime("%Y-%m-%d") < SPLIT_MACHINE_START_DATE:
            return None
    if terminal_sn in IN_TERMINAL_SNS:
        return "in"
    if terminal_sn in OUT_TERMINAL_SNS:
        return "out"
    return None


def dedup_checkins(cks, min_gap_min=120, terminal_aware=False):
    """相邻打卡间隔 < min_gap_min 分钟视为重复打卡，保留最早的一条。

    去重窗口由 10 分钟放宽到 2 小时(120min) (Owner 2026-09-08 确认):
    下班不止打一次卡(同机重复刷卡, 间隔常达几十分钟)被 2h 合并为最早卡,
    消除「多余下班卡落孤立 → 误判缺勤」(黄法普/于洋 9/7 案例)。
    **间隔恰好 2h 的卡不合并**——那是配对下限本身，理由见 dedup_checkins_with_mapping。

    terminal_aware=True 时: 上下班机方向不同的相邻卡不合并
    (陈雨欣 8/19 案例: 17:33 上班机卡与 17:34 下班机卡相隔 84 秒,
     合并会吞掉唯一的下班机卡, 导致误判缺勤)。
    """
    out, _ = dedup_checkins_with_mapping(cks, min_gap_min, terminal_aware)
    return out


def night_out_days_from_roles(cks, roles):
    """夜班下班日集合: 8:00-10:00 被配对为「下班」的打卡日期。

    Owner 2026-08-20 确认: 夜班下班卡一般在 8-10 点(8 点前打卡算早退)。
    cks 与 roles 长度一致（均为去重后的卡）。用于零打卡豁免:
    夜班下班日之后的第一个整天无打卡日算休息, 不计缺勤。
    """
    return {
        cks[i]["time"].date()
        for i, r in enumerate(roles)
        if r == "out" and 8 <= cks[i]["time"].hour < 10
    }


def dedup_checkins_with_mapping(cks, min_gap_min=120, terminal_aware=False):
    """去重并返回 (去重后的卡列表, 原始索引→去重后索引的映射)。

    被合并的重复卡映射到保留它的卡（同一张卡的角色一致）。
    去重窗口默认 2 小时(120min) (Owner 2026-09-08 确认): 同机重复刷卡
    (下班二次打卡, 间隔几分钟~1 小时多)合并为最早卡, 避免多余卡落孤立误判缺勤。
    合并判据是**严格小于** min_gap_min，恰好等于的卡不合并（让给配对下限，
    见函数内注释）。
    terminal_aware=True 时: 上下班机方向不同的相邻卡不合并
    (陈雨欣 8/19 案例: 17:33 上班机卡与 17:34 下班机卡相隔 84 秒,
     合并会吞掉唯一的下班机卡, 导致误判缺勤)。
    """
    def role_of(ck):
        if not terminal_aware:
            return None
        if ck["time"].date().strftime("%Y-%m-%d") < SPLIT_MACHINE_START_DATE:
            return None
        sn = ck.get("hbos_terminal_sn") or ""
        if sn in IN_TERMINAL_SNS:
            return "in"
        if sn in OUT_TERMINAL_SNS:
            return "out"
        return None

    out = []
    mapping = {}
    skip_until = None
    last_kept = None
    for idx, ck in enumerate(cks):
        # 判据用严格小于：间隔恰好 = min_gap_min 的卡不合并。
        # 窗口 120min 与配对下限（pair_employee_checkins 的 `2 <= gap`，即 120min）
        # 若是闭区间就会严丝合缝对撞——恰好相隔 2h 的上下班卡先被去重成一张，
        # 配对侧再怎么放宽也配不上，只剩孤卡判缺勤。左闭右开（合并 < 120）把
        # 边界让给配对，两张卡都留得住。
        if skip_until and ck["time"] < skip_until:
            if role_of(ck) and role_of(ck) != role_of(cks[last_kept]):
                # 方向不同的卡不合并, 重新作为独立卡保留
                last_kept = len(out)
                mapping[idx] = last_kept
                out.append(ck)
                skip_until = ck["time"] + timedelta(minutes=min_gap_min)
            else:
                mapping[idx] = last_kept
            continue
        last_kept = len(out)
        mapping[idx] = last_kept
        out.append(ck)
        skip_until = ck["time"] + timedelta(minutes=min_gap_min)
    return out, mapping


def shift_may_be_unfinished(ck_time, now_dt, max_gap_hours):
    """孤立上班卡的理论下班时刻尚未到 → 班次可能还没结束，不判缺勤。

    Owner 2026-09-11：凌晨重算「昨天」时，当晚 18:00 后上班的夜班还没下班
    （下班卡次日 8 点才打），其上班卡必然配对失败，若直接判缺勤会一次误报上百人
    （实测 9/10 有 99 人如此）。判据用「上班卡 + 最长班次时长 > 现在」——超过这个
    时刻仍无下班卡，才算真的缺卡。
    """
    if now_dt is None:
        return False
    return ck_time + timedelta(hours=max_gap_hours) > now_dt


def pair_employee_checkins(cks, eid, emp_num, shift_fn,
                           is_exempt=False, is_admin=False,
                           skip_forward=False, skip_night_lock=False,
                           emp_leave_dates=None, track_roles=False,
                           terminal_aware=False, max_gap_hours=16,
                           is_late_exempt=False, now_dt=None,
                           special_shift=None, four_shift=None):
    """对单个员工按时间升序的打卡做 HBOS 配对。

    参数:
        cks: dict 列表，每项至少含 "time"（datetime）、"employee_name"、"department"
        eid: Employee 记录名（用于生成 Attendance name）
        emp_num: 工号（传给 shift_fn）
        shift_fn: (ck_dt, emp_num, cross_day) -> (班次名, 是否迟到)
        is_exempt: 豁免名单，迟到清零且不判缺勤
        is_admin: 行政班名单，禁止跨天配对，周末孤卡/缺勤豁免
        skip_forward: 固定早班群体（行政/安全/食堂/豁免），跳过向前配对与零点夜班配对
        skip_night_lock: 行政/安全/食堂，跳过阶段 0 跨天夜班优先锁定
        emp_leave_dates: {"YYYY-MM-DD"}，请假日期不判缺勤
        track_roles: True 时返回 (atts, roles)，roles 与去重后的 cks 对齐，
            每张卡为 "in"（上班打卡）或 "out"（下班打卡）；未配对的卡按设备方向标记
        terminal_aware: True 时按设备 SN 区分上下班机（分机规则自
            SPLIT_MACHINE_START_DATE 起，见文件顶部常量）：
            上班机卡只能当下班机卡的「上班」，下班机卡只能当「下班」，
            避免纯时间贪心把跨班次卡配错(曹云山 8/19 案例)

    返回记录列表，每条为 9 元组:
    (name, employee, date_str, status, shift, late, in_time_str, working_hours, missing_out)
    """
    if not cks:
        return ([], []) if track_roles else []
    orig_cks = sorted(cks, key=lambda x: x["time"])

    # 设备方向(分机规则自 SPLIT_MACHINE_START_DATE 起, 见文件顶部常量): 上班机卡="in",
    # 下班机卡="out", 分机实施前/未知设备 None
    def terminal_role(ck):
        if not terminal_aware:
            return None
        if ck["time"].date().strftime("%Y-%m-%d") < SPLIT_MACHINE_START_DATE:
            return None
        sn = ck.get("hbos_terminal_sn") or ""
        if sn in IN_TERMINAL_SNS:
            return "in"
        if sn in OUT_TERMINAL_SNS:
            return "out"
        return None

    # 去重: 2小时合并同机重复刷卡, 但上下班机方向不同的相邻卡不合并(陈雨欣 8/19 案例:
    # 17:33 上班机卡与 17:34 下班机卡相隔 84 秒, 合并会吞掉唯一的下班机卡)
    cks = dedup_checkins(orig_cks, terminal_aware=terminal_aware)
    used = [False] * len(cks)
    atts = []
    # 每张卡的方向: 配对中的第二张卡 = 下班打卡；其余（含未配对卡）默认上班打卡
    roles = ["in"] * len(cks) if track_roles else None
    leave_dates = emp_leave_dates or set()

    # 预标记设备方向(未配对的卡保留设备方向, 供 night_out_days 等下游使用)
    if roles is not None:
        for i, ck in enumerate(cks):
            if terminal_role(ck) == "out":
                roles[i] = "out"

    # 分机约束回退(Owner 2026-08-20 确认): 某天完全没有下班机卡时(如刘兴军 8/14
    # 两张卡都打在上班机), 该天回退按时间配对, 不做「必须下班机卡」约束
    days_with_out = {ck["time"].date() for ck in cks if terminal_role(ck) == "out"}

    def mark_pair(i, j):
        used[i] = True
        used[j] = True
        if roles is not None:
            roles[i] = "in"
            roles[j] = "out"

    def add(date_str, status, shift, late, in_str, hours):
        atts.append(("HBOS-ATT-" + eid + "-" + date_str, eid, date_str, status, shift,
                     1 if late else 0, in_str, hours, 0))

    def day_has_span(i):
        """多次卡兜底(Owner 2026-08-20 确认): 当天(ck1所在日)存在至少一张上班卡和一张下班卡,
        且「第一次上班卡→最后一次下班卡」间隔 2-{max_gap_hours}h 时, 视为当天已有完整班次结构,
        当前孤立卡是重复打卡, 不判缺勤。"""
        day = cks[i]["time"].date()
        day_cards = [q for q in range(len(cks)) if cks[q]["time"].date() == day]
        day_ins = [q for q in day_cards if terminal_role(cks[q]) != "out"]
        day_outs = [q for q in day_cards if terminal_role(cks[q]) == "out"]
        if len(day_cards) >= 2 and day_ins and day_outs:
            first_in = min(day_ins, key=lambda q: cks[q]["time"])
            last_out = max(day_outs, key=lambda q: cks[q]["time"])
            gap = (cks[last_out]["time"] - cks[first_in]["time"]).total_seconds() / 3600
            return cks[last_out]["time"] > cks[first_in]["time"] and 2 <= gap <= max_gap_hours
        return False

    def night_out_mispunch(i):
        """跨天夜班下班误刷上班机(Owner 2026-08-21 确认): 孤立上班机卡在 8-10 点,
        且前一日存在上班机卡(夜班上班, 间隔 8-14h)时, 视为前一夜班的下班误刷, 不判缺勤。
        (吕玉升 8/16 案例: 8/15 20:24 夜班上班 → 8/16 08:36 下班误刷在上班机)"""
        c = cks[i]
        if c["time"].hour < 8 or c["time"].hour >= 10:
            return False
        if terminal_role(c) != "in":
            return False
        prev_date = c["time"].date() - timedelta(days=1)
        for p in range(len(cks)):
            if cks[p]["time"].date() != prev_date:
                continue
            if terminal_role(cks[p]) != "in":
                continue
            gap = (c["time"] - cks[p]["time"]).total_seconds() / 3600
            if 8 <= gap <= 14:
                return True
        return False

    def night_out_dup(i):
        """前一夜班的下班卡(Owner 2026-09-11): 早 4-12 点的孤立下班机卡,
        且前一日 18 点后存在上班机卡时, 视为该夜班的下班卡(已被前一日配对消耗或重复),
        当日不再另立缺勤。韩百泉 9/10 08:17 案例(前夜 20 点上夜班, 次日 8 点下班)。"""
        c = cks[i]
        if not (4 <= c["time"].hour < 12):
            return False
        if terminal_role(c) != "out":
            return False
        prev_date = c["time"].date() - timedelta(days=1)
        for p in range(len(cks)):
            if cks[p]["time"].date() != prev_date:
                continue
            if terminal_role(cks[p]) != "in":
                continue
            if cks[p]["time"].hour >= 18:
                return True
        return False

    # 班次解析: SPECIAL_SHIFT_NUMS 人员走独立班次体系(按时长区分12h/8h), 其他人走原 shift_fn
    # 运行态默认从数据库策略成员关系判断；纯函数测试可显式注入，
    # 避免为了单测把真实员工身份重新硬编码回源码。
    if special_shift is None:
        special_shift = emp_num in SPECIAL_SHIFT_NUMS
    if four_shift is None:
        four_shift = emp_num in FOUR_SHIFT_NUMS

    def resolve_shift(ck_dt, cross_day, gap_h):
        if special_shift:
            return special_shift_from_gap(ck_dt, gap_h)
        if four_shift:
            return four_shift_from_gap(ck_dt, gap_h)
        return shift_fn(ck_dt, emp_num, cross_day)

    def compute_shift(ck_dt, cross_day, gap_h):
        """算班次并应用豁免：is_exempt（全部异常豁免）与 is_late_exempt（仅不记迟到）。"""
        shift, late = resolve_shift(ck_dt, cross_day, gap_h)
        if is_exempt or is_late_exempt:
            late = False
        return shift, late

    # ===== 分机后纯设备方向顺序配对 (Owner 2026-08-21 确认) =====
    # 8/15 起上下班打卡分机: 上班机卡=上班, 下班机卡=下班, 方向由设备确定,
    # 不需要任何启发式(向前配对/时段锁定/猜班次)。
    # 规则:
    #   1. 上班机卡按时间顺序向后找最近的未用下班机卡, 组成一对
    #   2. 跨天自然支持(23:44 上班 → 次日 08:39 下班)
    #   3. 上班机卡孤立 = 缺勤(口径B); 下班机卡孤立 = 缺勤(口径B)
    #   4. 间隔超过 16 小时不配对(异常数据)
    #   5. 间隔不足 2 小时不配对(上下班机相邻连刷, 误刷方向)
    # 孤立卡不判缺勤的兜底: 当天已有完整上下班结构时视为重复卡
    # (陈雨欣 8/19 案例: 17:33 误刷上班机, 正常上下班结构已存在)
    if terminal_aware and any(terminal_role(c) is not None for c in cks):
        for i in range(len(cks)):
            if used[i]:
                continue
            role_i = terminal_role(cks[i])
            if role_i == "out":
                # 下班机卡孤立 → 缺勤; 但以下情形不判:
                #   a) 当天已有完整上下班结构 → 视为重复卡(陈雨欣 8/19)
                #   b) 属前一夜班的下班卡(早 4-12 点, 且前一日 18 点后有上班机卡)
                #      —— 该卡已被前一日的配对消耗或因故重复, 当日不再另立缺勤
                used[i] = True
                if not is_exempt and not day_has_span(i) and not night_out_dup(i):
                    ds_cur = cks[i]["time"].strftime("%Y-%m-%d")
                    if ds_cur not in leave_dates:
                        add(ds_cur, "Absent", "", False,
                            cks[i]["time"].strftime("%Y-%m-%d %H:%M:%S"), 0)
                continue
            # 上班机卡: 向后找最近的未用下班机卡
            for j in range(i + 1, len(cks)):
                if used[j]:
                    continue
                if terminal_role(cks[j]) != "out":
                    continue
                gap = (cks[j]["time"] - cks[i]["time"]).total_seconds() / 3600
                if gap < 0:
                    continue
                if gap > max_gap_hours:
                    # 超过上限: 正常班次最长12小时(无菌12h), 超过上限的
                    # 「配对」必是漏下班卡导致的假超长班(冯慧杰 8/15 15.69h 案例)
                    continue
                if gap < 2:
                    # 不足2小时: 上下班机相邻连刷/误刷方向, 不配对
                    continue
                mark_pair(i, j)
                cross_day = cks[i]["time"].date() != cks[j]["time"].date()
                shift, late = compute_shift(cks[i]["time"], cross_day, round(gap, 2))
                add(cks[i]["time"].strftime("%Y-%m-%d"), "Present", shift, late,
                    cks[i]["time"].strftime("%Y-%m-%d %H:%M:%S"), round(gap, 2))
                break
            else:
                # 上班机卡孤立 → 缺勤; 但以下情形不判:
                #   a) 当天已有完整上下班结构(重复卡) b) 前一夜班下班误刷上班机
                #   c) 班次可能尚未结束(凌晨重算"昨天"时, 当晚夜班还没下班)
                used[i] = True
                if (not is_exempt and not day_has_span(i) and not night_out_mispunch(i)
                        and not shift_may_be_unfinished(cks[i]["time"], now_dt, max_gap_hours)):
                    ds_cur = cks[i]["time"].strftime("%Y-%m-%d")
                    if ds_cur not in leave_dates:
                        add(ds_cur, "Absent", "", False,
                            cks[i]["time"].strftime("%Y-%m-%d %H:%M:%S"), 0)
        if track_roles:
            return atts, roles
        return atts

    # ===== 阶段 0: 跨天夜班优先锁定 =====
    # 夜班/晚班上班卡(22:00-24:00) 与 次日凌晨/早晨下班卡(04:00-10:00) 优先配对
    # 先锁定无歧义的夜班对，避免主循环把「中班下班卡」配给夜班上班卡
    # 分机实施后: 上班卡须来自上班机, 下班卡须来自下班机
    if not skip_night_lock:
        for i in range(len(cks)):
            if used[i]:
                continue
            h_i = cks[i]["time"].hour
            if 22 <= h_i <= 23:
                if terminal_role(cks[i]) == "out":
                    continue
                for j in range(i + 1, len(cks)):
                    if used[j]:
                        continue
                    cj = cks[j]["time"]
                    if cj.date() == cks[i]["time"].date():
                        continue
                    if not (4 <= cj.hour < 10):
                        continue
                    if terminal_role(cks[j]) == "in":
                        continue
                    gap = (cj - cks[i]["time"]).total_seconds() / 3600
                    if 4 <= gap <= max_gap_hours:
                        mark_pair(i, j)
                        shift, late = compute_shift(cks[i]["time"], True, round(gap, 2))
                        add(cks[i]["time"].strftime("%Y-%m-%d"), "Present", shift, late,
                            cks[i]["time"].strftime("%Y-%m-%d %H:%M:%S"), round(gap, 2))
                        break

    # ===== 主循环: 剩余卡的贪心配对 =====
    for i in range(len(cks)):
        if used[i]:
            continue
        ck1 = cks[i]
        h = ck1["time"].hour
        paired = False
        ck1_role = terminal_role(ck1)

        # 凌晨/早晨打卡(H<10)向前配对(跨天班次下班卡)
        # 倒班员工早上 7-9 点的卡既可能是早班上班卡，也可能是前夜晚班下班卡
        # 向前配对优先，消除「晚班下班卡被误判为早班迟到」的错配
        # 固定早班群体(行政/安全/食堂/豁免)无跨天班次，跳过向前配对
        # 分机实施后: 下班机卡才向前配对(找上班机卡); 上班机卡不向前
        if h < 10 and i > 0 and not skip_forward and ck1_role != "in":
            for p in range(i - 1, -1, -1):
                if used[p]:
                    continue
                if cks[p]["time"].date() == ck1["time"].date():
                    continue
                if cks[p]["time"].hour < 14:
                    continue
                if terminal_role(cks[p]) == "out":
                    continue
                gap = (ck1["time"] - cks[p]["time"]).total_seconds() / 3600
                if 2 <= gap <= 14:
                    mark_pair(p, i)
                    shift, late = compute_shift(cks[p]["time"], True, round(gap, 2))
                    add(cks[p]["time"].strftime("%Y-%m-%d"), "Present", shift, late,
                        cks[p]["time"].strftime("%Y-%m-%d %H:%M:%S"), round(gap, 2))
                    paired = True
                    break
        if paired:
            continue

        # 零点夜班配对(Owner 2026-08-17 新增规则):
        # 0-4 点的卡向前配对失败后，尝试与当天 4:00-10:00 的下班卡配对
        # (零点夜班 0:00-8:00，下班卡在 8:00 之后；刘兴军 8/3 00:47→08:00 案例)
        # 迟到起算点为 0:00（由 shift_fn 判定）
        # 分机后回退: 当天无下班机卡时按时间配对(陈文芬 8/14 案例: 01:50→08:26
        # 同在上半机, 设备约束失效, 需按时间配对)
        if h < 4 and not skip_forward and ck1_role != "out":
            day_has_no_out_local = ck1["time"].date() not in days_with_out
            for j in range(i + 1, len(cks)):
                if used[j]:
                    continue
                cj = cks[j]["time"]
                if cj.date() != ck1["time"].date():
                    break
                if cj.hour >= 10:
                    break
                if not day_has_no_out_local and terminal_role(cks[j]) == "in":
                    continue
                gap = (cj - ck1["time"]).total_seconds() / 3600
                if 2 <= gap <= 12:
                    mark_pair(i, j)
                    shift, late = compute_shift(ck1["time"], False, round(gap, 2))
                    add(ck1["time"].strftime("%Y-%m-%d"), "Present", shift, late,
                        ck1["time"].strftime("%Y-%m-%d %H:%M:%S"), round(gap, 2))
                    paired = True
                    break
            if paired:
                continue

        # 凌晨孤卡(0-4点)无法配对 → 缺勤；豁免/请假/行政班周末人员除外
        if h < 4:
            used[i] = True
            if is_exempt:
                continue
            ds_cur = ck1["time"].strftime("%Y-%m-%d")
            if ds_cur in leave_dates:
                continue
            if is_admin and ck1["time"].weekday() >= 5:
                continue
            # 多次卡兜底: 当天已有完整上下班结构 → 本卡为重复卡
            if day_has_span(i):
                continue
            add(ds_cur, "Absent", "", False,
                ck1["time"].strftime("%Y-%m-%d %H:%M:%S"), 0)
            continue

        # 正常向后配对: 间隔 2-18 小时
        # 跨天只允许中班/晚班(16:00-24:00 上班、次日凌晨/早晨下班)
        # 行政班固定 8:30-17:30 无跨天班次
        # 分机实施后: 上班机卡向后找下班机卡; 下班机卡不向后配对
        # 回退: 当天完全没有下班机卡时按时间配对(设备规则失效的兜底)
        best_j = -1
        day_has_no_out = ck1["time"].date() not in days_with_out
        if ck1_role != "out":
            for j in range(i + 1, len(cks)):
                if used[j]:
                    continue
                if not day_has_no_out and terminal_role(cks[j]) == "in":
                    continue
                gap = (cks[j]["time"] - ck1["time"]).total_seconds() / 3600
                if 2 <= gap <= max_gap_hours:
                    cross_day = cks[j]["time"].date() != ck1["time"].date()
                    # 行政班禁止跨天(死规则, Owner 2026-08-20 重申):
                    # 行政班固定 8:30-17:30, 其上班卡跨天必为「漏下班卡」错配
                    if cross_day and is_admin:
                        continue
                    best_j = j
                    break

        if best_j == -1:
            # 孤立的上班卡(有上班无下班) → 判缺勤；豁免/请假/行政班周末人员除外
            used[i] = True
            if is_exempt:
                continue
            ds_cur = ck1["time"].strftime("%Y-%m-%d")
            if ds_cur in leave_dates:
                continue
            # 夜班下班日重复卡(Owner 2026-08-19 确认):
            # 8-10 点的孤立卡, 若前一晚 20 点后有夜班上班卡, 视为夜班下班重复打卡,
            # 不判缺勤(李云雷 8/16 08:19/08:22/08:34 案例: 08:19 已配给前夜晚班,
            # 08:22 去重, 08:34 为多余的下班重复卡)
            is_night_out_duplicate = False
            if 8 <= ck1["time"].hour < 10 and i > 0:
                prev_date = ck1["time"].date() - timedelta(days=1)
                if any(cks[p]["time"].date() == prev_date and cks[p]["time"].hour >= 20
                       for p in range(i)):
                    is_night_out_duplicate = True
            if is_night_out_duplicate:
                continue
            # 多次卡兜底: 当天已有完整上下班结构 → 本卡为重复卡
            if day_has_span(i):
                continue
            # 班次可能尚未结束: 凌晨重算「昨天」时, 当晚夜班(18 点后上班)的下班卡
            # 要次日早上才产生, 此时孤立上班卡是必然的, 不能判缺勤(Owner 2026-09-11)
            if shift_may_be_unfinished(ck1["time"], now_dt, max_gap_hours):
                continue
            if is_admin and ck1["time"].weekday() >= 5:
                continue
            add(ds_cur, "Absent", "", False,
                ck1["time"].strftime("%Y-%m-%d %H:%M:%S"), 0)
            continue

        ck2 = cks[best_j]
        mark_pair(i, best_j)
        cd = ck1["time"].date() != ck2["time"].date()
        gap_hours = round((ck2["time"] - ck1["time"]).total_seconds() / 3600, 2)
        shift, late = compute_shift(ck1["time"], cd, gap_hours)
        gap_hours = round((ck2["time"] - ck1["time"]).total_seconds() / 3600, 2)
        add(ck1["time"].strftime("%Y-%m-%d"), "Present", shift, late,
            ck1["time"].strftime("%Y-%m-%d %H:%M:%S"), gap_hours)

    if track_roles:
        return atts, roles
    return atts
