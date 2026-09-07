"""离线复现: 跨天夜班下班误刷上班机 → 次日误判缺勤。

场景: 12 小时晚班 20:00-次日 8:00, 员工夜班下班时先误刷在上班机(8-10点),
40 秒后再在正常下班机打卡。修复目标: 误刷的上班机卡视为「前一夜班的下班误刷」,
不判次日缺勤。
"""
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "hb_attendance_app"))

from hb_attendance_app.hbos_attendance.pairing import pair_employee_checkins

IN_1 = "13750CS_D7C69C16EC0B2447"   # 办公楼外(上班机)
IN_2 = "13750CS_02281E713F33A9A8"   # 厂区二道门西(上班机)
OUT_1 = "13750CS_9FB66A86CF3487D7"  # 办公楼内(下班机)
OUT_2 = "13750CS_93C9390B9995FE8C"  # 宿舍二楼东(下班机)


def shift_fn(ck_dt, emp_num, cross_day=False):
    h = ck_dt.hour; m = ck_dt.minute; ts = ck_dt.strftime("%H:%M:%S")
    if h >= 20 or h < 4: return ("晚班", h >= 0 and ts > "00:00:00" and h < 4)
    if 4 <= h < 8: return ("早班", False)
    if h == 8: return ("早班", m > 0)
    if 9 <= h < 12: return ("行政班早班", True)
    if 12 <= h < 16: return ("中班", False)
    if 16 <= h < 20:
        if cross_day: return ("晚班", False) if h >= 19 else ("中班", False)
        return ("中班", ts > "16:00:00")
    return ("晚班", False)


def ck(y, mo, d, h, mi, s, sn):
    return {"time": datetime(y, mo, d, h, mi, s), "employee_name": "测试",
            "department": "生产部", "hbos_terminal_sn": sn}


def run(name, cks, expect_present, expect_absent, absent_dates=()):
    atts = pair_employee_checkins(cks, "T-001", "99999999", shift_fn, terminal_aware=True)
    p = sum(1 for a in atts if a[3] == "Present")
    ab = sum(1 for a in atts if a[3] == "Absent")
    ab_dates = {a[2] for a in atts if a[3] == "Absent"}
    ok = p == expect_present and ab == expect_absent
    if absent_dates:
        ok = ok and ab_dates == set(absent_dates)
    print(f"{'PASS' if ok else 'FAIL'}  {name}: Present={p} Absent={ab} 缺勤日期={sorted(ab_dates)}")
    if not ok:
        for a in atts:
            print("   ", a[2], a[3], a[4], "hours=", a[7])
    return ok


all_ok = True

# 1. 吕玉升 8/16: 8/15 20:24 晚班上班 → 8/16 08:36 误刷上班机 + 08:37 正常下班
all_ok &= run("吕玉升 8/16 夜班下班误刷上班机", [
    ck(2026, 8, 15, 20, 24, 31, IN_1),
    ck(2026, 8, 16, 8, 36, 37, IN_1),   # 误刷
    ck(2026, 8, 16, 8, 37, 10, OUT_1),
], 1, 0)

# 2. 庞冠军 8/16: 8/15 19:39 晚班上班(提前) → 8/16 08:06 误刷 + 08:07 正常下班
all_ok &= run("庞冠军 8/16 夜班下班误刷(提前到岗19:39)", [
    ck(2026, 8, 15, 19, 39, 27, IN_1),
    ck(2026, 8, 16, 8, 6, 15, IN_1),    # 误刷
    ck(2026, 8, 16, 8, 7, 36, OUT_1),
], 1, 0)

# 3. 边界: 真正缺勤(早上孤立上班卡, 前一日无夜班卡) → 仍判缺勤
all_ok &= run("真正缺勤(前一日无夜班卡)仍判缺勤", [
    ck(2026, 8, 16, 8, 30, 0, IN_1),
], 0, 1, ("2026-08-16",))

# 4. 边界: 夜班下班正常打在下班机(无误刷) → 正常配对不误伤
all_ok &= run("夜班下班正常打在下班机不误伤", [
    ck(2026, 8, 15, 20, 24, 0, IN_1),
    ck(2026, 8, 16, 8, 37, 0, OUT_1),
], 1, 0)

# 5. 边界: 当天完整上下班 + 早上多余上班机卡(王廷伟同类, 应已被 day_has_span 处理)
all_ok &= run("当天完整班次+多余上班卡(王廷伟类)", [
    ck(2026, 8, 16, 7, 40, 0, IN_1),
    ck(2026, 8, 16, 8, 0, 0, IN_1),
    ck(2026, 8, 16, 16, 10, 0, OUT_1),
], 1, 0)

print("\n全部通过" if all_ok else "\n存在失败场景")
sys.exit(0 if all_ok else 1)
