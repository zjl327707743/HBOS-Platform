import json
import unittest
from pathlib import Path

APP = Path(__file__).parents[1] / "hb_attendance_app"


class EntryContractTest(unittest.TestCase):
    def test_hooks_registers_both_syncs(self):
        src = (APP / "hooks.py").read_text()
        self.assertIn("sync_rest_leave.sync_rest_leave_from_bitable", src)
        self.assertIn("sync_shift_swap.sync_shift_swap_from_bitable", src)

    def test_sidebar_has_two_new_items(self):
        src = (APP / "hbos_attendance/setup.py").read_text()
        self.assertIn("HBOS Rest Leave Record", src)
        self.assertIn("HBOS Shift Swap Record", src)

    def test_workspace_has_two_new_links(self):
        ws = json.loads((APP / "hbos_attendance/workspace/海滨考勤工作台/海滨考勤工作台.json").read_text())
        labels = [l.get("label") for l in ws["links"]]
        self.assertIn("飞书调休记录", labels)
        self.assertIn("飞书换班记录", labels)


if __name__ == "__main__":
    unittest.main()
