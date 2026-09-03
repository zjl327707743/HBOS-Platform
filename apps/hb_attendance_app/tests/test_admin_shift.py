import unittest
from datetime import datetime

from hb_attendance_app.hbos_attendance.pairing import (
    admin_shift_from_gap,
    pair_employee_checkins,
)


class AdminShiftFromGapTest(unittest.TestCase):
    """行政班名单人员判定（Owner 2026-08-21 确认）:
    四车间行政班 08:0x 打卡曾被全局规则表匹配为「早班 08:00 标准」误判迟到。
    名单人员统一 08:31 起算迟到; 20 点后与 0-4 点的跨天卡按晚班不判迟到。
    """

    def test_0803_not_late(self):
        # 杨迪 8/17 08:03 上班: 行政班 8:30 标准, 提前到岗不迟到
        self.assertEqual(admin_shift_from_gap(datetime(2026, 8, 17, 8, 3)),
                         ("行政班早班", False))

    def test_0830_on_time(self):
        self.assertEqual(admin_shift_from_gap(datetime(2026, 8, 17, 8, 30)),
                         ("行政班早班", False))

    def test_0831_late(self):
        self.assertEqual(admin_shift_from_gap(datetime(2026, 8, 17, 8, 31)),
                         ("行政班早班", True))

    def test_2330_night_card_not_late(self):
        # 焦德龙 8/15 23:30 上班机卡: 夜间卡不按早班 8:00 标准判迟到
        self.assertEqual(admin_shift_from_gap(datetime(2026, 8, 15, 23, 30)),
                         ("晚班", False))

    def test_0003_midnight_card_not_late(self):
        # 焦德龙 8/15 00:03 下班机卡: 凌晨跨天收尾卡不判迟到
        self.assertEqual(admin_shift_from_gap(datetime(2026, 8, 15, 0, 3)),
                         ("晚班", False))


def _admin_shift_fn(ck_dt, emp_num="", cross_day=False):
    """适配 pair_employee_checkins 的 shift_fn 签名。"""
    return admin_shift_from_gap(ck_dt)


class AdminPairingTest(unittest.TestCase):
    """四车间行政班完整配对: 侯宇晓 8/16 真实卡链 08:08 上班机 → 17:39 下班机。"""

    def _ck(self, day, hour, minute, sn=None):
        d = {"time": datetime(2026, 8, day, hour, minute),
             "employee_name": "侯宇晓", "department": "四车间"}
        if sn:
            d["hbos_terminal_sn"] = sn
        return d

    def test_houyuxiao_0816_not_late(self):
        cks = [self._ck(16, 8, 8, "13750CS_D7C69C16EC0B2447"),
               self._ck(16, 17, 39, "13750CS_93C9390B9995FE8C")]
        atts = pair_employee_checkins(cks, "HR-EMP-00033", "11004014",
                                      _admin_shift_fn, terminal_aware=True)
        s = {(a[2], a[3], a[4], a[5], a[7]) for a in atts}
        # 行政班早班 9.52h, 不迟到, 不缺勤
        self.assertIn(("2026-08-16", "Present", "行政班早班", 0, 9.52), s)
        self.assertNotIn(("2026-08-16", "Absent", "", 0, 0), s)

    def test_yangdi_0817_not_late(self):
        cks = [self._ck(17, 8, 3, "13750CS_D7C69C16EC0B2447"),
               self._ck(17, 17, 51, "13750CS_93C9390B9995FE8C")]
        atts = pair_employee_checkins(cks, "HR-EMP-00041", "11004011",
                                      _admin_shift_fn, terminal_aware=True)
        s = {(a[2], a[3], a[4], a[5]) for a in atts}
        self.assertIn(("2026-08-17", "Present", "行政班早班", 0), s)


if __name__ == "__main__":
    unittest.main()
