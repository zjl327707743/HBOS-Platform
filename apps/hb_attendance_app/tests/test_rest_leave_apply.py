import re
import unittest
from pathlib import Path

SRC = (Path(__file__).parents[1]
       / "hb_attendance_app/hbos_attendance/rest_leave_apply.py")

# 调休 DocType。它给「已通过」这半边的扫描划定**调休域**：
# approval_status 是请假/调休共用的字段名，请假域也合法地写死同一个字面量
# （api.py:352、daily_feishu_sync.py:40、sync_leaves.py:80），
# 所以单看字面量无法判断新增的那份属于哪个域，必须连带调休 DocType 一起看。
REST_LEAVE_DOCTYPE = '"HBOS Rest Leave Record"'

# 「已核实」半边。两种写法都要认：字面量，或 rest_leave.py 里既有的 VERIFY_OK
# 常量（含 `rest_leave.VERIFY_OK` 这种带前缀写法）——只认字面量的话，
# 本代码库更惯用的常量写法会整条溜过扫描。
# 必须匹配「键 : 值」成对形式：verify_status 这个键本身在调休同步流水线里是合法的
# （sync_rest_leave.py:219,302,361,466 用它取 PARSE_PENDING / VERIFY_PENDING 待处理记录），
# 只有「值 = 已核实」才构成豁免口径。
_VERIFIED_FILTER_RE = re.compile(
    r'"verify_status"\s*:\s*(?:"已核实"|(?:[\w.]*\.)?VERIFY_OK)')

# 「已通过」半边。本代码库没有对应常量，只有字面量一种写法。
_APPROVED_FILTER_RE = re.compile(r'"approval_status"\s*:\s*"已通过"')


def _package_modules_except_this_one():
    """调休包内除本模块外的所有 .py（含 page/report/doctype 子目录）。"""
    for p in sorted(SRC.parent.rglob("*.py")):
        if p.name == "rest_leave_apply.py":
            continue
        yield p


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
        """少了「已核实」，未核实/核实不通过的调休日也会发放豁免。"""
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

    def test_filter_literals_appear_only_in_the_constant(self):
        """常量存在 ≠ 常量被使用：内联字面量绕过 FILTERS 时必须失败。

        目录扫描按文件名跳过了本模块（它守的是「别处有没有第二份」），
        所以「本模块自己就带了第二份」只能在这里抓：
        每个过滤键在源码里只允许出现一次，即 FILTERS 里那一次。
        """
        for key in ('"approval_status"', '"verify_status"'):
            count = self.src.count(key)
            self.assertEqual(
                count, 1,
                "%s 在本模块出现 %d 次，应恰好 1 次（只允许在 FILTERS 常量里）；"
                "多出来的那次是绕过常量的内联过滤条件" % (key, count))

    def test_query_call_site_uses_the_constant(self):
        """定义了 FILTERS 却不用（改成内联字面量或 dict(FILTERS)）也要失败。"""
        self.assertRegex(self.src, r"filters\s*=\s*FILTERS")


class SingleSourceOfTruthTest(unittest.TestCase):
    """全库只能有一处写死调休豁免口径（已通过 + 已核实），防止口径分叉。

    两半分开守，因为它们的可判别性不同：
    - verify_status 是调休域独有字段，键本身就能定位调休域 → 可全包扫；
    - approval_status 是请假/调休共用字段 → 必须连带调休 DocType 一起看，
      否则会误伤请假域的既有合法查询。
    """

    def test_only_one_module_filters_on_verified(self):
        hits = []
        for p in _package_modules_except_this_one():
            if _VERIFIED_FILTER_RE.search(p.read_text()):
                hits.append(p.name)
        self.assertEqual(hits, [],
                         "「已核实」过滤条件只能出现在 rest_leave_apply.py，"
                         "否则两处口径会漂移：%s" % hits)

    def test_only_one_module_filters_on_approved(self):
        """「已通过」单独一份同样要守——半边口径漂移一样发错豁免。"""
        hits = []
        for p in _package_modules_except_this_one():
            text = p.read_text()
            if REST_LEAVE_DOCTYPE in text and _APPROVED_FILTER_RE.search(text):
                hits.append(p.name)
        self.assertEqual(hits, [],
                         "调休域里的「已通过」过滤条件只能出现在 rest_leave_apply.py，"
                         "否则两处口径会漂移：%s" % hits)


if __name__ == "__main__":
    unittest.main()
