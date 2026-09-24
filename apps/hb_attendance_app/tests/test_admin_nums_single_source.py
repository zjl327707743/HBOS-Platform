import ast
import unittest
from pathlib import Path

MOD = Path(__file__).parents[1] / "hb_attendance_app/hbos_attendance"
SYNC = MOD / "daily_feishu_sync.py"
RULES = MOD / "rule_lists.py"


def _module_level_names(src, var):
    """取模块级赋值 var = {...} 的字面量集合；不是字面量返回 None。"""
    for n in ast.parse(src).body:
        if (isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
                and n.targets[0].id == var):
            try:
                return set(map(str, ast.literal_eval(n.value)))
            except Exception:
                return None
    return None


class SingleSourceOfTruthTest(unittest.TestCase):
    """行政班名单只能有一份。

    事故背景：ADMIN_NUMS 曾在三处各写一份且严重分叉——
      rule_lists.py（判定用，权威）、daily_feishu_sync.py（飞书同步）、
      pair_checkins.py（旧引擎，死代码）。
    飞书与判定差 71 个工号（57 只在飞书、14 只在判定），导致同一人同一天
    在两套输出里一个判缺勤、一个不算缺勤。Owner 2026-09-24 裁定：
    以 rule_lists.py 为准。

    根治办法不是「把数字抄一致」（下次还会分叉），而是让飞书同步直接引用
    唯一来源。本测试守住这条。
    """

    def setUp(self):
        self.sync_src = SYNC.read_text()

    def test_sync_does_not_define_its_own_admin_list(self):
        """飞书同步不得再自建 ADMIN_NUMS 字面量。"""
        local = _module_level_names(self.sync_src, "ADMIN_NUMS")
        self.assertIsNone(
            local,
            "daily_feishu_sync.py 不得自定义 ADMIN_NUMS（发现 %s 个工号）；"
            "应从唯一来源导入，否则名单会再次分叉" % (len(local) if local else "?"),
        )

    def test_sync_imports_admin_list_from_single_source(self):
        """必须从 api（其再导出 rule_lists 的绑定）导入。"""
        self.assertRegex(
            self.sync_src,
            r"from hb_attendance_app\.hbos_attendance\.api import [^\n]*ADMIN_NUMS",
            "daily_feishu_sync.py 必须从 api 导入 ADMIN_NUMS",
        )

    def test_authoritative_list_is_the_rules_module(self):
        """权威来源是 rule_lists.ADMIN_NUMS，且 api 再导出同一个对象。"""
        rules = _module_level_names(RULES.read_text(), "ADMIN_NUMS")
        self.assertIsNotNone(rules, "rule_lists.py 必须定义 ADMIN_NUMS 字面量")
        self.assertGreater(len(rules), 100)

        api_src = (MOD / "api.py").read_text()
        self.assertIn("ADMIN_NUMS", api_src)
        self.assertIn("from hb_attendance_app.hbos_attendance.rule_lists import", api_src)


if __name__ == "__main__":
    unittest.main()
