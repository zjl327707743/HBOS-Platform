import unittest
from pathlib import Path

from hb_attendance_app.hbos_attendance.rule_lists import (
    ADMIN_NUMS, EXEMPT_NUMS, FOOD_NUMS, SAFETY_NUMS,
)
from hb_attendance_app.hbos_attendance import rules_board
from hb_attendance_app.hbos_attendance.shift_rules import BUILTIN_SHIFTS
from hb_attendance_app.hbos_attendance.pairing import (
    FOUR_SHIFT_NUMS, IN_TERMINAL_SNS, OUT_TERMINAL_SNS, SPECIAL_SHIFT_NUMS,
)

APP = Path(__file__).parents[1] / "hb_attendance_app"
API = APP / "hbos_attendance/api.py"
DATA = APP / "hbos_attendance/page/hbos_shift_management/shift_management_data.py"
JS = APP / "hbos_attendance/page/hbos_shift_management/hbos_shift_management.js"


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


class RulesBoardDataTest(unittest.TestCase):
    def test_builtin_shifts_matches_constant(self):
        result = rules_board.builtin_shifts()
        self.assertEqual(len(result), len(BUILTIN_SHIFTS))
        by_key = {r["shift_type"]: r for r in result}
        for k, v in BUILTIN_SHIFTS.items():
            self.assertEqual(by_key[k]["start_time"], v[0])
            self.assertEqual(by_key[k]["end_time"], v[1])
            self.assertEqual(by_key[k]["late_after"], v[2])
            self.assertEqual(by_key[k]["min_hours"], v[3])

    def test_list_groups_cover_all_constant_groups(self):
        groups = {g["key"]: g for g in rules_board.list_groups()}
        expected = {
            "ADMIN_NUMS": ADMIN_NUMS,
            "EXEMPT_NUMS": EXEMPT_NUMS,
            "FOOD_NUMS": FOOD_NUMS,
            "SAFETY_NUMS": SAFETY_NUMS,
            "SPECIAL_SHIFT_NUMS": SPECIAL_SHIFT_NUMS,
            "FOUR_SHIFT_NUMS": FOUR_SHIFT_NUMS,
            "IN_TERMINAL_SNS": IN_TERMINAL_SNS,
            "OUT_TERMINAL_SNS": OUT_TERMINAL_SNS,
        }
        self.assertEqual(set(groups.keys()), set(expected.keys()))
        for key, src in expected.items():
            g = groups[key]
            self.assertEqual(g["count"], len(src))
            self.assertEqual(set(g["nums"]), set(src))
            self.assertEqual(len(g["nums"]), len(set(g["nums"])), f"{key} 工号应唯一")

    def test_pairing_params_has_key_params(self):
        params = {p["name"]: p["value"] for p in rules_board.pairing_params()}
        self.assertEqual(params["打卡去重间隔"], "10 分钟")
        self.assertEqual(params["最短班次"], "2 小时")
        self.assertEqual(params["连续无打卡缺勤门槛"], "3 天起判")

    def test_priority_chain_non_empty_and_ordered(self):
        chain = rules_board.priority_chain()
        self.assertGreater(len(chain), 3)
        steps = [s["step"] for s in chain]
        self.assertEqual(steps, sorted(steps))
        self.assertEqual(chain[0]["name"], "排班表")
        self.assertIn("硬编码兜底", [s["name"] for s in chain])


class RulesBoardContractTest(unittest.TestCase):
    """get_rules_board 依赖 frappe 运行态，测试按仓库惯例用文件内容校验契约。"""

    def test_data_module_declares_whitelisted_get_rules_board(self):
        content = DATA.read_text()
        self.assertIn("@frappe.whitelist()", content)
        self.assertIn("def get_rules_board(", content)
        for key in ("rules", "builtin_shifts", "lists", "pairing_params", "priority_chain"):
            self.assertIn(key, content)
        self.assertIn("assigned_count", content)
        # 复用现有时间规范化函数，口径一致
        self.assertIn("_fmt_rule", content)

    def test_data_module_imports_rules_board_builders(self):
        content = DATA.read_text()
        self.assertIn("import rules_board as rb", content)
        for builder in ("builtin_shifts", "list_groups", "pairing_params", "priority_chain"):
            self.assertIn(f"rb.{builder}", content)


if __name__ == "__main__":
    unittest.main()
