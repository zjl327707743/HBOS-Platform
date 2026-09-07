"""离线复现: 陈雨欣 8/19 多余上班机卡被误判缺勤。

期望: 当天已有完整 in→out 班次时, 孤立的多余上班机卡视为重复打卡, 不判缺勤。
"""
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "hb_attendance_app"))

from hb_attendance_app.hbos_attendance.pairing import pair_employee_checkins

# 与 api._get_shift_and_late_builtin 一致的班次判定
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


def main():
    # 陈雨欣 8/19 真实数据(已脱敏到必要字段)
    # 08:23:14 上班机(上班) / 17:33:23 上班机(多余, 误刷) / 17:34:47 下班机(下班)
    cks = [
        {"time": datetime(2026, 8, 19, 8, 23, 14), "employee_name": "陈雨欣",
         "department": "厂外QC", "hbos_terminal_sn": "13750CS_02281E713F33A9A8"},
        {"time": datetime(2026, 8, 19, 17, 33, 23), "employee_name": "陈雨欣",
         "department": "厂外QC", "hbos_terminal_sn": "13750CS_02281E713F33A9A8"},
        {"time": datetime(2026, 8, 19, 17, 34, 47), "employee_name": "陈雨欣",
         "department": "厂外QC", "hbos_terminal_sn": "13750CS_9FB66A86CF3487D7"},
    ]
    atts = pair_employee_checkins(cks, "HR-EMP-00208", "10015004", shift_fn,
                                  terminal_aware=True)
    statuses = [a[3] for a in atts]
    print("判定结果:", statuses)
    for a in atts:
        print(" ", a[2], a[3], a[4], "late=", a[5], "hours=", a[7])

    # 断言: 只应有 1 条 Present, 0 条 Absent
    assert statuses.count("Present") == 1, f"期望 1 条 Present, 实际 {statuses}"
    assert statuses.count("Absent") == 0, f"期望 0 条 Absent(多余卡不应判缺勤), 实际 {statuses}"
    print("PASS: 多余上班机卡不再误判缺勤")


if __name__ == "__main__":
    main()
