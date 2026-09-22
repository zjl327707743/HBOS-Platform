import unittest
from pathlib import Path

SRC = (Path(__file__).parents[1]
       / "hb_attendance_app/hbos_attendance/rest_leave_apply.py")


class VerifiedRestDatesContractTest(unittest.TestCase):
    """口径契约：两个过滤条件缺一不可，且不得在别处出现第二份。"""

    def setUp(self):
        self.src = SRC.read_text()

    def test_module_exists_with_entry(self):
        self.assertIn("def verified_rest_dates(", self.src)

    def test_reads_rest_leave_doctype(self):
        self.assertIn('"HBOS Rest Leave Record"', self.src)

    def test_requires_approved(self):
        """少了「已通过」，被驳回/撤回的申请也会发豁免。"""
        self.assertIn('"approval_status": "已通过"', self.src)

    def test_requires_verified(self):
        """少了「已核实」，未核实/核实不通过的调休日也会发豁免。"""
        self.assertIn('"verify_status": "已核实"', self.src)

    def test_filters_exist_as_module_constant(self):
        """两个条件必须来自同一个常量，避免被复制成第二份。"""
        self.assertIn("FILTERS", self.src)
        self.assertIn("FILTERS", self.src.split("def verified_rest_dates")[0])

    def test_delegates_expansion_to_pure_module(self):
        self.assertIn("expand_verified_records", self.src)

    def test_is_not_whitelisted(self):
        """内部查询入口，不应暴露为接口。"""
        self.assertNotIn("@frappe.whitelist", self.src)


class SingleSourceOfTruthTest(unittest.TestCase):
    """全库只能有一处写死「已核实」的查询条件，防止口径分叉。"""

    def test_only_one_module_filters_on_verified(self):
        pkg = SRC.parent
        hits = []
        for p in sorted(pkg.rglob("*.py")):
            if p.name == "rest_leave_apply.py":
                continue
            text = p.read_text()
            if '"verify_status"' in text and '"已核实"' in text:
                hits.append(p.name)
        self.assertEqual(hits, [],
                         "「已核实」过滤条件只能出现在 rest_leave_apply.py，"
                         "否则两处口径会漂移：%s" % hits)


if __name__ == "__main__":
    unittest.main()
