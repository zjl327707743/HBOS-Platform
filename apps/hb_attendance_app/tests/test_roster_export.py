import unittest
from pathlib import Path

from hb_attendance_app.hbos_attendance.roster_classify import classify, LIST_SYSTEMS
from hb_attendance_app.hbos_attendance.pairing import SPECIAL_SHIFT_NUMS, FOUR_SHIFT_NUMS
from hb_attendance_app.hbos_attendance.rule_lists import (
    ADMIN_NUMS, EXEMPT_NUMS, FOOD_NUMS, SAFETY_NUMS,
)

APP = Path(__file__).parents[1] / "hb_attendance_app"
ROSTER = APP / "hbos_attendance/roster_export.py"
JS = APP / "hbos_attendance/page/hbos_shift_management/hbos_shift_management.js"


class RosterClassifyTest(unittest.TestCase):
    """归行优先级：豁免 > 绑定班次 > 名单 > 通用倒班。"""

    def _member(self, nums):
        # 豁免测试：豁免优先级最高，任一豁免成员都应归 ""。
        return sorted(nums)[0]

    def _list_member(self, nums):
        # 名单测试代表样本：真实名单间存在交叉（如行政班成员同时命中豁免名单，
        # 或一人同属多个名单）。归行优先级下这些成员不会落到本名单：
        #   豁免(0) > 绑定(1) > 名单按 LIST_SYSTEMS 顺序取前(2-6)
        # 因此须排除豁免名单及其他名单的交叉成员，保证样本恰好归本名单。
        others = set(EXEMPT_NUMS)
        for other_nums, _ in LIST_SYSTEMS:
            if other_nums is not nums:
                others |= set(other_nums)
        pool = sorted(nums - others)
        self.assertTrue(pool, "名单无可用代表样本")
        return pool[0]

    def test_exempt_returns_empty(self):
        self.assertEqual(classify(self._member(EXEMPT_NUMS)), "")

    def test_bound_shift_type_beats_list(self):
        # 行政班名单人员绑定了 早班 规则 → 早班行(绑定优先于名单)
        admin_num = self._list_member(ADMIN_NUMS)
        self.assertEqual(classify(admin_num, "早班"), "早班")

    def test_list_members_map_to_system(self):
        self.assertEqual(classify(self._list_member(SPECIAL_SHIFT_NUMS)), "无菌倒班")
        self.assertEqual(classify(self._list_member(FOUR_SHIFT_NUMS)), "四班次倒班")
        self.assertEqual(classify(self._list_member(ADMIN_NUMS)), "行政班")
        self.assertEqual(classify(self._list_member(SAFETY_NUMS)), "安全倒班")
        self.assertEqual(classify(self._list_member(FOOD_NUMS)), "食堂")

    def test_unknown_goes_generic(self):
        self.assertEqual(classify("99999999"), "通用倒班")

    def test_list_systems_covers_five_lists(self):
        keys = {id(nums) for nums, _ in LIST_SYSTEMS}
        self.assertIn(id(SPECIAL_SHIFT_NUMS), keys)
        self.assertIn(id(FOUR_SHIFT_NUMS), keys)
        self.assertIn(id(ADMIN_NUMS), keys)
        self.assertIn(id(SAFETY_NUMS), keys)
        self.assertIn(id(FOOD_NUMS), keys)
        self.assertEqual(len(LIST_SYSTEMS), 5)


if __name__ == "__main__":
    unittest.main()
