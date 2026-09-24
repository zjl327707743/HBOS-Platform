"""HBOS 12 小时倒班自动轮转排班（设备动力部 + 生产部）。

Owner 2026-08-26 确认: 两批人员均 12 小时倒班, 循环「早班 → 夜班 → 休息」三天一轮,
相位错开保证每天 2 人上班(1 早班 + 1 夜班)、1 人休息。

班次映射(系统类型):
  用户「早班」= 8:00-20:00  → 系统「早班」(迟到 08:01)
  用户「夜班」= 20:00-8:00  → 系统「晚班」(迟到 20:01)
  「休息」                   → 「休息」

相位分段(段起点当天各成员班次; 某天的班次取「起点 <= 该天」的最后一段):
  设备动力部:
    段1 2026-08-15: 付全喜 晚班 / 李双胜 休息 / 贾正利 早班
  生产部:
    段1 2026-08-15: 吕玉升 晚班 / 王飞 休息 / 袁式梅 早班
    段2 2026-08-30: 吕玉升 早班 / 王飞 晚班 / 袁式梅 休息

  说明 1: 生产部段1 原按 8/26 快照记录(吕玉升早/王飞晚/袁式梅休), 与 8/15 起算等价
  (8/26-8/15=11, ≡2 mod 3), Owner 2026-09-10 明确锚点为 8/15, 故统一改记 8/15。
  说明 2 (Owner 2026-09-10 确认): 生产部自 2026-08-30 起实际轮转整体前移一天,
  8/15-8/29 与段1 吻合, 8/30 起与段2 吻合(两人实际打卡各 12/12 吻合), 故按段2 重排。
"""
from datetime import date, timedelta

# 循环顺序: 早班 → 晚班(用户称夜班) → 休息
ROTATION_CYCLE = ["早班", "晚班", "休息"]

# 轮转分组: 每组由若干「相位段」组成, 每段一个起点日期 + 该日各成员的班次。
# 某天的班次取「起点 <= 该天」的最后一段 —— 支持现场调整相位(如生产部 8/30 起前移一天)。
ROTATION_GROUPS = [
    {
        "name": "设备动力部",
        "segments": [
            {
                "anchor_date": date(2026, 8, 15),
                "members": {
                    "10009025": "晚班",  # 付全喜
                    "10009027": "休息",  # 李双胜
                    "10009028": "早班",  # 贾正利
                },
            },
        ],
    },
    {
        "name": "生产部",
        "segments": [
            {
                "anchor_date": date(2026, 8, 15),
                "members": {
                    "10010011": "晚班",  # 吕玉升
                    "10010010": "休息",  # 王飞
                    "10010013": "早班",  # 袁式梅
                },
            },
            {
                # Owner 2026-09-10: 现场自 8/30 起相位整体前移一天
                "anchor_date": date(2026, 8, 30),
                "members": {
                    "10010011": "早班",  # 吕玉升
                    "10010010": "晚班",  # 王飞
                    "10010013": "休息",  # 袁式梅
                },
            },
        ],
    },
]

# 兼容旧称: 每组第一个段的锚点/成员
GROUP_ANCHOR_KEY = "anchor_date"
GROUP_MEMBERS_KEY = "members"


def group_start_date(group):
    """组的起始日 = 最早一段的起点(覆盖式删除从这里开始)。"""
    return min(seg["anchor_date"] for seg in group["segments"])


def group_member_nums(group):
    """组内全部工号（跨所有段去重，保序）。"""
    seen = []
    for seg in group["segments"]:
        for num in seg["members"]:
            if num not in seen:
                seen.append(num)
    return seen


def group_shift_for(group, num, target_date):
    """取「起点 <= target_date」的最后一段, 算该员工当天班次; 无适用段返回 None。"""
    chosen = None
    for seg in group["segments"]:
        if seg["anchor_date"] <= target_date:
            chosen = seg
    if chosen is None or num not in chosen["members"]:
        return None
    return rotation_shift_for(chosen["members"][num], chosen["anchor_date"], target_date)


def rotation_shift_for(anchor_shift, anchor_date, target_date):
    """按锚点班次 + 锚点日期计算目标日期的班次（纯函数，可离线测试）。

    循环「早班 → 晚班 → 休息」，跨周期取模。
    """
    days = (target_date - anchor_date).days
    base = ROTATION_CYCLE.index(anchor_shift)
    return ROTATION_CYCLE[(base + days) % len(ROTATION_CYCLE)]


def generate_rotation_schedule(end_date):
    """Generate owned ROTATION schedules without overwriting human/imported decisions.

    Ownership rules:
    - only ROTATION rows in the requested window may be replaced;
    - LEGACY / IMPORT / MANUAL / SWAP rows are protected and win;
    - this helper never commits. The caller owns the transaction.
    """
    import frappe

    if isinstance(end_date, str):
        end_date = date.fromisoformat(end_date)

    all_nums = [n for g in ROTATION_GROUPS for n in group_member_nums(g)]
    emps = frappe.db.get_all(
        "Employee",
        filters={"employee_number": ["in", all_nums]},
        fields=["name", "employee_number"],
    )
    emp_by_num = {e.employee_number: e.name for e in emps}

    created = 0
    protected = 0
    for group in ROTATION_GROUPS:
        start_date = group_start_date(group)
        if end_date < start_date:
            continue

        # Replace only rows this generator owns, and only inside the requested window.
        for num in group_member_nums(group):
            emp = emp_by_num.get(num)
            if emp:
                frappe.db.delete(
                    "HBOS Employee Schedule",
                    {
                        "employee": emp,
                        "schedule_date": [
                            "between",
                            [start_date.isoformat(), end_date.isoformat()],
                        ],
                        "source_type": "ROTATION",
                    },
                )

        d = start_date
        while d <= end_date:
            ds = d.isoformat()
            for num in group_member_nums(group):
                emp = emp_by_num.get(num)
                if not emp:
                    continue

                # Any non-rotation authoritative row wins over automatic rotation.
                existing = frappe.db.get_value(
                    "HBOS Employee Schedule",
                    {"employee": emp, "schedule_date": ds},
                    ["name", "source_type"],
                    as_dict=True,
                )
                if existing:
                    protected += 1
                    continue

                shift = group_shift_for(group, num, d)
                if not shift:
                    continue
                frappe.get_doc({
                    "doctype": "HBOS Employee Schedule",
                    "employee": emp,
                    "schedule_date": ds,
                    "shift_type": shift,
                    "leave_type": "",
                    "source_type": "ROTATION",
                    "source_ref": group["name"],
                }).insert(ignore_permissions=True)
                created += 1
            d += timedelta(days=1)

    return {
        "generated": created,
        "protected": protected,
        "until": end_date.isoformat(),
    }
