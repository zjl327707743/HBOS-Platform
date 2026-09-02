import unittest
from pathlib import Path

from hb_attendance_app.hbos_attendance.rule_lists import (
    ADMIN_NUMS, EXEMPT_NUMS, FOOD_NUMS, SAFETY_NUMS,
)

APP = Path(__file__).parents[1] / "hb_attendance_app"
API = APP / "hbos_attendance/api.py"


class RuleListsExtractionTest(unittest.TestCase):
    """名单常量已从 api.py 抽到纯模块 rule_lists.py（api.py re-export 同名）。"""

    def test_rule_lists_module_exposes_constants(self):
        self.assertGreater(len(ADMIN_NUMS), 100)
        self.assertGreater(len(EXEMPT_NUMS), 50)
        self.assertIn("11004014", ADMIN_NUMS)  # 侯宇晓（四车间行政班）
        self.assertTrue(all(isinstance(x, str) for x in ADMIN_NUMS))
        self.assertTrue(all(isinstance(x, str) for x in EXEMPT_NUMS))

    def test_api_reimports_rule_lists_constants(self):
        content = API.read_text()
        self.assertIn(
            "from hb_attendance_app.hbos_attendance.rule_lists import "
            "ADMIN_NUMS, EXEMPT_NUMS, FOOD_NUMS, SAFETY_NUMS",
            content,
        )
        # 名单集合字面量不应再定义在 api.py 中
        self.assertNotIn("ADMIN_NUMS = {", content)
        self.assertNotIn("EXEMPT_NUMS = {", content)


if __name__ == "__main__":
    unittest.main()
