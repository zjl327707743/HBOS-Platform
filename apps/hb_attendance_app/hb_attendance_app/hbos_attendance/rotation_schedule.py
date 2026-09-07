"""HBOS 12 小时倒班自动轮转排班（设备动力部 + 生产部）。

Owner 2026-08-26 确认: 两批人员均 12 小时倒班, 循环「早班 → 夜班 → 休息」三天一轮,
相位错开保证每天 2 人上班(1 早班 + 1 夜班)、1 人休息。

班次映射(系统类型):
  用户「早班」= 8:00-20:00  → 系统「早班」(迟到 08:01)
  用户「夜班」= 20:00-8:00  → 系统「晚班」(迟到 20:01)
  「休息」                   → 「休息」

相位锚点(起点当天班次):
  设备动力部(2026-08-15):
    付全喜 10009025: 晚班   (15晚 16休 17早 18晚 19休 20早)
    李双胜 10009027: 休息   (15休 16早 17晚 18休 19早 20晚)
    贾正利 10009028: 早班   (15早 16晚 17休 18早 19晚 20休)
  生产部(2026-08-26):
    吕玉升 10010011: 早班   (26早 27晚 28休 ...)
    王飞   10010010: 晚班   (26晚 27休 28早 ...)
    袁式梅 10010013: 休息   (26休 27早 28晚 ...)
"""
from datetime import date, timedelta

# 循环顺序: 早班 → 晚班(用户称夜班) → 休息
ROTATION_CYCLE = ["早班", "晚班", "休息"]

# 轮转分组: 每组一个锚点日期 + 该日期当天各成员的班次
ROTATION_GROUPS = [
    {
        "anchor_date": date(2026, 8, 15),
        "members": {
            "10009025": "晚班",  # 付全喜
            "10009027": "休息",  # 李双胜
            "10009028": "早班",  # 贾正利
        },
    },
    {
        "anchor_date": date(2026, 8, 26),
        "members": {
            "10010011": "早班",  # 吕玉升
            "10010010": "晚班",  # 王飞
            "10010013": "休息",  # 袁式梅
        },
    },
]


def rotation_shift_for(anchor_shift, anchor_date, target_date):
    """按锚点班次 + 锚点日期计算目标日期的班次（纯函数，可离线测试）。

    循环「早班 → 晚班 → 休息」，跨周期取模。
    """
    days = (target_date - anchor_date).days
    base = ROTATION_CYCLE.index(anchor_shift)
    return ROTATION_CYCLE[(base + days) % len(ROTATION_CYCLE)]


def generate_rotation_schedule(end_date):
    """生成全部轮转分组排班到 HBOS Employee Schedule（覆盖式，从各锚点日期到 end_date）。

    覆盖式: 先删各组员工从该组锚点日期起的旧排班, 再按相位重写, 避免重复累计。
    休息日写「休息」, 缺勤判定已有的「排班休息日无打卡=休息」逻辑会自动豁免。
    """
    import frappe

    if isinstance(end_date, str):
        end_date = date.fromisoformat(end_date)

    all_nums = [num for g in ROTATION_GROUPS for num in g["members"]]
    emps = frappe.db.get_all(
        "Employee",
        filters={"employee_number": ["in", all_nums]},
        fields=["name", "employee_number"],
    )
    emp_by_num = {e.employee_number: e.name for e in emps}

    created = 0
    for group in ROTATION_GROUPS:
        anchor_date = group["anchor_date"]
        if end_date < anchor_date:
            continue
        # 覆盖式删除: 本组员工从本组锚点日期起的旧排班
        for num in group["members"]:
            emp = emp_by_num.get(num)
            if emp:
                frappe.db.delete(
                    "HBOS Employee Schedule",
                    {"employee": emp, "schedule_date": [">=", anchor_date.isoformat()]},
                )
        # 生成
        d = anchor_date
        while d <= end_date:
            for num, anchor_shift in group["members"].items():
                emp = emp_by_num.get(num)
                if not emp:
                    continue
                shift = rotation_shift_for(anchor_shift, anchor_date, d)
                frappe.get_doc({
                    "doctype": "HBOS Employee Schedule",
                    "employee": emp,
                    "schedule_date": d.isoformat(),
                    "shift_type": shift,
                    "leave_type": "",
                }).insert(ignore_permissions=True)
                created += 1
            d += timedelta(days=1)

    frappe.db.commit()
    return {"generated": created, "until": end_date.isoformat()}
