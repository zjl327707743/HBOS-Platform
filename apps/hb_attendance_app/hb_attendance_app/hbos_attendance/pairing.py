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
- 分机自 2026-08-14 起实施，此日期前所有机器均为普通考勤机（不分方向）
- 8/14 及之后：打卡方向优先按设备 SN 判定；8/14 前：回退配对算法推断
"""
from datetime import datetime, timedelta

# 上班/下班打卡机 SN（Owner 2026-08-19 确认）
IN_TERMINAL_SNS = {"13750CS_D7C69C16EC0B2447", "13750CS_02281E713F33A9A8"}
OUT_TERMINAL_SNS = {"13750CS_9FB66A86CF3487D7", "13750CS_93C9390B9995FE8C"}

# 分机实施起始日期（Owner 2026-08-20 纠正: 15 号才实施上下分开打卡, 8/14 及之前按旧规则）
SPLIT_MACHINE_START_DATE = "2026-08-15"

# 无菌/三班独立班次人员（Owner 2026-08-19 确认，53 人）:
# 班次体系与通用规则不同:
#   无菌12小时倒班早: 8:30-20:30, 8:31 起算迟到
#   无菌12小时倒班晚: 20:30-次日8:30, 20:31 起算迟到
#   早班: 8:30-16:30, 8:31 起算迟到
#   中班: 16:30-次日0:30, 16:31 起算迟到
#   夜班: 0:30-8:30, 0:31 起算迟到
SPECIAL_SHIFT_NUMS = {
    "10014020",  # 侯泽宇
    "10015055",  # 孙振刚
    "11001009",  # 刘世兵
    "11001011",  # 王蒙蒙
    "11001016",  # 陈艳莉
    "11002037",  # 王敬
    "11004008",  # 杨小净
    "11006100",  # 程玉宾
    "11008013",  # 刘娟
    "11008015",  # 秦瑀
    "11008016",  # 路广
    "11008017",  # 李兴宇
    "11008018",  # 李明
    "11008019",  # 王亚恒
    "11008020",  # 郝光璞
    "11008021",  # 任勇洋
    "11008023",  # 杨明
    "11008024",  # 夏公平
    "11008026",  # 刘昌
    "11008027",  # 任绍香
    "11008028",  # 李剑
    "11008029",  # 曲巧红
    "11008030",  # 荆云艳
    "11008031",  # 杨本锐
    "11008032",  # 孟辉
    "11008034",  # 刘珍珍
    "11008035",  # 宋玲玲
    "11008036",  # 王梅林
    "11008037",  # 刘海芳
    "11008038",  # 郑昌坤
    "11008039",  # 牛同功
    "11008040",  # 李鑫
    "11008041",  # 刘清芳
    "11008043",  # 李聪
    "11008045",  # 沈国锋
    "11008046",  # 马勇
    "11008047",  # 王式卡
    "11008048",  # 王必帅
    "11008049",  # 李慧
    "11008050",  # 吴照帅
    "11008052",  # 李荣花
    "11008053",  # 陈玉姣
    "11008054",  # 江利刚
    "11008055",  # 张明祺
    "11008056",  # 李亚珊
    "11008057",  # 靳露雪
    "11008058",  # 王燕丰
    "11008059",  # 冷现岭
    "11008060",  # 崔学状
    "11008063",  # 李庆辉
    "11009035",  # 张志兴
    "11009037",  # 杜加凯
    "11009039",  # 范青锋
    # Owner 2026-08-19 追加（耿献磊、李世东、管东阳、李笛、陈龙禧、程大梁）
    "11009042",  # 耿献磊
    "11008007",  # 李世东
    "11008009",  # 管东阳
    "11009036",  # 李笛
    "11009040",  # 陈龙禧
    "11009038",  # 程大梁
}

# 四班次倒班人员（Owner 2026-08-20 确认, 9 人）:
# 只上四个班次: 早班 / 中班 / 晚班 / 8:30-16:30 班
# 核心规则: 只要上够 8 小时就算正常出勤
FOUR_SHIFT_NUMS = {
    "10013030",  # 冯慧杰
    "10013023",  # 梁岩
    "10013024",  # 李瑞芳
    "10013026",  # 刘慧玲
    "10013020",  # 路梦菊
    "10013027",  # 秦存利
    "10013019",  # 尚亲风
    "10013028",  # 王颖
    "10013029",  # 左畅
}


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
        checkin_time: 打卡时间（datetime 或 date）。分机自 2026-08-14 起实施，
            此前打卡不按设备判方向，返回 None 回退配对推断。

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


def dedup_checkins(cks, min_gap_min=10, terminal_aware=False):
    """相邻打卡间隔 < min_gap_min 分钟视为重复打卡，保留最早的一条。

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


def dedup_checkins_with_mapping(cks, min_gap_min=10, terminal_aware=False):
    """去重并返回 (去重后的卡列表, 原始索引→去重后索引的映射)。

    被合并的重复卡映射到保留它的卡（同一张卡的角色一致）。
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
        if skip_until and ck["time"] <= skip_until:
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


def pair_employee_checkins(cks, eid, emp_num, shift_fn,
                           is_exempt=False, is_admin=False,
                           skip_forward=False, skip_night_lock=False,
                           emp_leave_dates=None, track_roles=False,
                           terminal_aware=False, max_gap_hours=16):
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
        terminal_aware: True 时按设备 SN 区分上下班机(分机规则 2026-08-14 起)：
            上班机卡只能当下班机卡的「上班」，下班机卡只能当「下班」，
            避免纯时间贪心把跨班次卡配错(曹云山 8/19 案例)

    返回记录列表，每条为 9 元组:
    (name, employee, date_str, status, shift, late, in_time_str, working_hours, missing_out)
    """
    if not cks:
        return ([], []) if track_roles else []
    orig_cks = sorted(cks, key=lambda x: x["time"])

    # 设备方向(分机规则 2026-08-14 起): 上班机卡="in", 下班机卡="out", 分机实施前/未知设备 None
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

    # 去重: 10分钟合并, 但上下班机方向不同的相邻卡不合并(陈雨欣 8/19 案例:
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

    # 班次解析: SPECIAL_SHIFT_NUMS 人员走独立班次体系(按时长区分12h/8h), 其他人走原 shift_fn
    special_shift = emp_num in SPECIAL_SHIFT_NUMS
    # 四班次人员: 班次按打卡时段判定, 上够8小时算正常
    four_shift = emp_num in FOUR_SHIFT_NUMS

    def resolve_shift(ck_dt, cross_day, gap_h):
        if special_shift:
            return special_shift_from_gap(ck_dt, gap_h)
        if four_shift:
            return four_shift_from_gap(ck_dt, gap_h)
        return shift_fn(ck_dt, emp_num, cross_day)

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
                # 下班机卡孤立 → 缺勤; 当天已有完整上下班结构时视为重复卡
                used[i] = True
                if not is_exempt and not day_has_span(i):
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
                shift, late = resolve_shift(cks[i]["time"], cross_day, round(gap, 2))
                if is_exempt:
                    late = False
                add(cks[i]["time"].strftime("%Y-%m-%d"), "Present", shift, late,
                    cks[i]["time"].strftime("%Y-%m-%d %H:%M:%S"), round(gap, 2))
                break
            else:
                # 上班机卡孤立 → 缺勤; 但当天已有完整上下班结构 或 前一夜班下班误刷 时不判
                used[i] = True
                if not is_exempt and not day_has_span(i) and not night_out_mispunch(i):
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
                        shift, late = resolve_shift(cks[i]["time"], True, round(gap, 2))
                        if is_exempt:
                            late = False
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
                    shift, late = resolve_shift(cks[p]["time"], True, round(gap, 2))
                    if is_exempt:
                        late = False
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
                    shift, late = resolve_shift(ck1["time"], False, round(gap, 2))
                    if is_exempt:
                        late = False
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
            if is_admin and ck1["time"].weekday() >= 5:
                continue
            add(ds_cur, "Absent", "", False,
                ck1["time"].strftime("%Y-%m-%d %H:%M:%S"), 0)
            continue

        ck2 = cks[best_j]
        mark_pair(i, best_j)
        cd = ck1["time"].date() != ck2["time"].date()
        gap_hours = round((ck2["time"] - ck1["time"]).total_seconds() / 3600, 2)
        shift, late = resolve_shift(ck1["time"], cd, gap_hours)
        if is_exempt:
            late = False
        gap_hours = round((ck2["time"] - ck1["time"]).total_seconds() / 3600, 2)
        add(ck1["time"].strftime("%Y-%m-%d"), "Present", shift, late,
            ck1["time"].strftime("%Y-%m-%d %H:%M:%S"), gap_hours)

    if track_roles:
        return atts, roles
    return atts
