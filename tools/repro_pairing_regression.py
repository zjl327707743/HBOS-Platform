"""离线回归测试: 分机配对修复的多场景验证。

场景:
1. 陈雨欣 8/19: 上班机卡 + 84秒后的上下班机相邻卡 → 1 Present(修复目标)
2. 正常行政班: 8:23 上班机 + 17:34 下班机 → 1 Present 9.19h
3. 同方向 10 分钟内连刷: 上班机 2 张 + 下班机 1 张 → 合并, 1 Present
4. 孤立下班机卡(无上班卡): 口径B → 1 Absent(规则不变)
5. 上够8小时但上班卡 8:02(早班 8:00 标准): 迟到仅 2 分钟仍判迟到(现有口径)
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
    return {"time": datetime(y, mo, d, h, mi, s), "employee_name": "测试", "department": "测试部", "hbos_terminal_sn": sn}


def run(name, cks, expect_present, expect_absent, expect_hours=None):
    atts = pair_employee_checkins(cks, "T-001", "99999999", shift_fn, terminal_aware=True)
    p = sum(1 for a in atts if a[3] == "Present")
    ab = sum(1 for a in atts if a[3] == "Absent")
    hrs = round(atts[0][7], 2) if atts else None
    ok = p == expect_present and ab == expect_absent
    if expect_hours is not None:
        ok = ok and hrs is not None and abs(hrs - expect_hours) < 0.05
    print(f"{'PASS' if ok else 'FAIL'}  {name}: Present={p} Absent={ab} hours={hrs}")
    if not ok:
        for a in atts:
            print("   ", a[2], a[3], a[4], a[7])
    return ok


all_ok = True
# 1. 陈雨欣 8/19(修复目标)
all_ok &= run("陈雨欣 8/19 误刷上班机", [
    ck(2026, 8, 19, 8, 23, 14, IN_2),
    ck(2026, 8, 19, 17, 33, 23, IN_2),
    ck(2026, 8, 19, 17, 34, 47, OUT_1),
], 1, 0, 9.19)

# 2. 正常行政班
all_ok &= run("正常行政班 8:23-17:34", [
    ck(2026, 8, 18, 8, 23, 0, IN_2),
    ck(2026, 8, 18, 17, 34, 0, OUT_1),
], 1, 0, 9.18)

# 3. 同方向 10 分钟内连刷(上班机连刷两张)
all_ok &= run("同方向连刷应合并", [
    ck(2026, 8, 18, 8, 23, 0, IN_2),
    ck(2026, 8, 18, 8, 25, 0, IN_2),
    ck(2026, 8, 18, 17, 34, 0, OUT_1),
], 1, 0, 9.18)

# 4. 孤立下班机卡 → 口径B 缺勤(规则保持不变)
all_ok &= run("孤立下班机卡→缺勤(口径B)", [
    ck(2026, 8, 15, 7, 4, 8, OUT_1),
], 0, 1)

# 5. 跨天夜班: 23:44 上班机 → 次日 8:39 下班机
all_ok &= run("跨天夜班 23:44-08:39", [
    ck(2026, 8, 17, 23, 44, 0, IN_1),
    ck(2026, 8, 18, 8, 39, 0, OUT_1),
], 1, 0, 8.92)

print("\n全部通过" if all_ok else "\n存在失败场景")
sys.exit(0 if all_ok else 1)
