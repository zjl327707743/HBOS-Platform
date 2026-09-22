import json
import unittest
from pathlib import Path

APP = Path(__file__).parents[1] / "hb_attendance_app"
MOD = APP / "hbos_attendance"


class EntryContractTest(unittest.TestCase):
    def setUp(self):
        # scheduler_events 只由 Frappe 从 app 根 hooks.py 读取；hbos_attendance/ 下
        # 没有 hooks.py（任务书原文写的 MOD/hooks.py 并不存在，故此处指向 APP/hooks.py）。
        self.hooks = (APP / "hooks.py").read_text()
        self.setup = (MOD / "setup.py").read_text()
        self.ws = json.loads(
            (MOD / "workspace/海滨考勤工作台/海滨考勤工作台.json").read_text())

    def test_hooks_registers_rest_leave_stages(self):
        self.assertIn("sync_rest_leave.sync_rest_leave_from_bitable", self.hooks)
        self.assertIn("sync_rest_leave.parse_pending_rest_leaves", self.hooks)
        self.assertIn("sync_rest_leave.verify_pending_rest_leaves", self.hooks)

    def test_hooks_registers_rest_leave_stages_in_order(self):
        # 顺序固定：同步 → 解析 → 核实（解析依赖同步刚落的记录）
        sync = self.hooks.index("sync_rest_leave.sync_rest_leave_from_bitable")
        parse = self.hooks.index("sync_rest_leave.parse_pending_rest_leaves")
        verify = self.hooks.index("sync_rest_leave.verify_pending_rest_leaves")
        self.assertLess(sync, parse)
        self.assertLess(parse, verify)

    def test_hooks_no_longer_registers_swap(self):
        self.assertNotIn("sync_shift_swap", self.hooks)

    def test_sidebar_keeps_rest_leave_drops_swap(self):
        self.assertIn("HBOS Rest Leave Record", self.setup)
        self.assertNotIn("HBOS Shift Swap Record", self.setup)

    def test_workspace_keeps_rest_leave_drops_swap(self):
        labels = [l.get("label") for l in self.ws["links"]]
        self.assertIn("飞书调休记录", labels)
        self.assertNotIn("飞书换班记录", labels)

    def test_swap_artifacts_removed(self):
        self.assertFalse((MOD / "swap_mapping.py").exists())
        self.assertFalse((MOD / "sync_shift_swap.py").exists())
        self.assertFalse((MOD / "doctype/hbos_shift_swap_record").exists())


if __name__ == "__main__":
    unittest.main()
