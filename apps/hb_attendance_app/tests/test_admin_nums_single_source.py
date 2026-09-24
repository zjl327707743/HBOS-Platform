import re
import unittest
from pathlib import Path

MOD = Path(__file__).parents[1] / "hb_attendance_app/hbos_attendance"
RULES = MOD / "rule_lists.py"
PAIRING = MOD / "pairing.py"
REGISTRY = MOD / "policy_registry.py"
POLICY_DOCTYPE = MOD / "doctype/hbos_attendance_policy_assignment/hbos_attendance_policy_assignment.json"


class PolicyRegistrySingleSourceTest(unittest.TestCase):
    """Employee policy membership is business data, not source-code identity lists."""

    def test_rule_lists_are_database_backed_facades(self):
        src = RULES.read_text()
        self.assertIn("PolicySet", src)
        self.assertIn("POLICY_ADMIN", src)
        self.assertIn("POLICY_EXEMPT", src)
        self.assertNotRegex(src, r"\b\d{8}\b")
        self.assertNotRegex(src, r"HB-[\u4e00-\u9fff]{2,}")

    def test_pairing_special_membership_is_database_backed(self):
        src = PAIRING.read_text()
        self.assertIn("PolicySet(POLICY_SPECIAL_SHIFT)", src)
        self.assertIn("PolicySet(POLICY_FOUR_SHIFT)", src)
        self.assertNotRegex(src, r"\b\d{8}\b")

    def test_policy_registry_has_no_production_identity_literals(self):
        src = REGISTRY.read_text()
        self.assertIn("HBOS Attendance Policy Assignment", src)
        self.assertNotRegex(src, r"\b\d{8}\b")
        self.assertNotRegex(src, r"HB-[\u4e00-\u9fff]{2,}")

    def test_policy_doctype_is_versioned_business_data(self):
        src = POLICY_DOCTYPE.read_text()
        for field in ("employee", "policy_type", "enabled", "effective_from", "effective_to"):
            self.assertIn(f'"fieldname": "{field}"', src)

    def test_deprecated_duplicate_engines_are_removed(self):
        for name in (
            "daily_feishu_sync.py",
            "pair_checkins.py",
            "shift_matcher.py",
            "generate_attendance.py",
        ):
            self.assertFalse((MOD / name).exists(), f"{name} should not remain in clean candidate")


if __name__ == "__main__":
    unittest.main()
