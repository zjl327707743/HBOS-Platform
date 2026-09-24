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


def _local_bindings(src, var):
    """模块内对该名字的**任何**本地绑定或原地修改，返回 [(行号, 形式), ...]。

    不能用 `_module_level_names(...) is None` 来判「没有自建副本」：该助手在
    「名字不存在」与「名字存在但取值不是字面量」两种情形下都返回 None，于是
    `ADMIN_NUMS = set(EXEMPT_NUMS) | {...}` / `dict(...)` / 放在 `if`、`try`
    或函数体内 这些形态会让断言**假通过**，名单照旧分叉（本项目正是被
    「永远为真的静态断言」坑过一次）。这里不解析取值、只看 AST 里有没有写。
    """
    hits = []
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == var for t in n.targets):
                hits.append((n.lineno, "赋值"))
        elif isinstance(n, ast.AnnAssign):
            if isinstance(n.target, ast.Name) and n.target.id == var:
                hits.append((n.lineno, "注解赋值"))
        elif isinstance(n, ast.AugAssign):
            if isinstance(n.target, ast.Name) and n.target.id == var:
                hits.append((n.lineno, "增量赋值"))
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
            base = n.func.value
            if isinstance(base, ast.Name) and base.id == var:
                # ADMIN_NUMS.update(...) / .add(...) 会改到导入来的那一份，
                # 等于绕过「只引用不自建」，把分叉写进全局唯一来源里
                hits.append((n.lineno, "原地修改 .%s()" % n.func.attr))
    return hits


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
        """飞书同步不得以任何形式在本地写 ADMIN_NUMS（含非字面量形态）。"""
        local = _local_bindings(self.sync_src, "ADMIN_NUMS")
        self.assertEqual(
            local, [],
            "daily_feishu_sync.py 对 ADMIN_NUMS 存在本地绑定/修改 %s；"
            "应从唯一来源导入，否则名单会再次分叉" % (local,),
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


class DeprecatedLegacyMarkerTest(unittest.TestCase):
    """旧引擎文件必须带废弃标记。

    它们内含第 3 份 ADMIN_NUMS / 旧班次逻辑，全仓库无引用，但文件本身还在。
    没有标记时，改动名单的人会以为「有几处来源」，不知道改哪儿才是对的。
    Owner 2026-09-24 决定：暂不删文件，但必须加标记。
    """

    LEGACY = ("pair_checkins.py", "shift_matcher.py", "generate_attendance.py")

    def test_legacy_files_carry_deprecation_marker(self):
        for name in self.LEGACY:
            with self.subTest(file=name):
                doc = ast.get_docstring(ast.parse((MOD / name).read_text())) or ""
                self.assertIn("已废弃", doc,
                              "%s 缺少「已废弃」docstring 标记——该文件是全仓库无引用的"
                              "旧引擎残留，无标记会让改动名单的人误判来源" % name)


class SterileListSingleSourceTest(unittest.TestCase):
    """无菌名单也只能有一份。

    事故背景：WUJUN_NUMS 曾有两份——api.py 空集、daily_feishu_sync.py 48 人；
    而 pairing.py 的 SPECIAL_SHIFT_NUMS（59 人）才是现行体系。三份并存且不一致，
    48 人那份还混入 3 名设备动力部人员、漏掉 14 名无菌车间人员。
    Owner 2026-09-24 裁定：以 SPECIAL_SHIFT_NUMS 为准。
    """

    def setUp(self):
        self.sync_src = SYNC.read_text()

    def test_sync_does_not_define_its_own_sterile_list(self):
        local = _local_bindings(self.sync_src, "WUJUN_NUMS")
        self.assertEqual(
            local, [],
            "daily_feishu_sync.py 对 WUJUN_NUMS 存在本地绑定/修改 %s；"
            "应引用 pairing.SPECIAL_SHIFT_NUMS，否则无菌名单会再次分叉" % (local,),
        )

    def test_sync_imports_sterile_list_from_pairing(self):
        self.assertRegex(
            self.sync_src,
            r"from hb_attendance_app\.hbos_attendance\.pairing import [^\n]*SPECIAL_SHIFT_NUMS",
            "daily_feishu_sync.py 必须从 pairing 导入 SPECIAL_SHIFT_NUMS",
        )


if __name__ == "__main__":
    unittest.main()
