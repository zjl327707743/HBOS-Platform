"""门户数据端点的契约测试（不连数据库、不起 Frappe）。

覆盖 `report_data.py` / `list_data.py` / `file_api.py` 三个新模块里
**不需要真实数据也能测**的那部分——纯函数与白名单：

- 筛选解析：JSON 字符串要被接受；**非法 JSON 必须抛错而不是退回全量**
  （这是本轮审核抓到的真实缺陷：`filters=not-json` 曾返回全部 61816 行）
- 行数边界：`_bounds` 的钳制与容错
- 返回值规整：`_unpack` 对二元组 / 三元组 / None / dict 的处理
- 白名单：`list_data._spec` 拒绝未注册的 key

需要 Frappe 运行时的部分（`frappe.get_list`、`only_for`）不在这里测——
那是集成测试的范围。
"""
from __future__ import annotations

import sys
import types
import unittest


def _install_frappe_stub():
    """装一个最小 frappe 存根，让模块可以 import。

    只实现被测代码路径真正用到的几个名字。ValidationError 要能被 except，
    故给一个真实的异常类而不是 Mock。
    """

    class ValidationError(Exception):
        pass

    class AuthenticationError(Exception):
        pass

    thrown = []

    def _throw(message, *args, **kwargs):
        thrown.append(str(message))
        raise ValidationError(str(message))

    frappe = types.SimpleNamespace(
        ValidationError=ValidationError,
        AuthenticationError=AuthenticationError,
        throw=_throw,
        only_for=lambda roles: None,
        parse_json=lambda s: __import__("json").loads(s),
        get_attr=lambda path: None,
        get_list=lambda *a, **k: [],
        db=types.SimpleNamespace(count=lambda *a, **k: 0),
        session=types.SimpleNamespace(user="hr@example.com"),
        whitelist=lambda *a, **k: (lambda fn: fn),
    )
    frappe._thrown = thrown
    sys.modules["frappe"] = frappe
    return frappe


class ReportFilterParsingTest(unittest.TestCase):
    """`report_data._clean_filters` —— 本轮修复的核心。"""

    @classmethod
    def setUpClass(cls):
        _install_frappe_stub()

    def _clean(self, raw):
        from hb_attendance_app.hbos_attendance import report_data

        return report_data._clean_filters(raw)

    def test_accepts_json_string(self):
        # 门户经 HTTP 传参时到后端就是 JSON 文本；只判 dict 会把筛选全丢掉
        self.assertEqual({"month": "9"}, self._clean('{"month": "9"}'))

    def test_accepts_dict(self):
        self.assertEqual({"month": "9"}, self._clean({"month": "9"}))

    def test_empty_inputs_become_empty_dict(self):
        for value in (None, "", {}):
            with self.subTest(value=value):
                self.assertEqual({}, self._clean(value))

    def test_drops_blank_values(self):
        # 空值让报表内部的 filters.get() 走「未传」分支，与 Desk 留空筛选框一致
        self.assertEqual(
            {"month": "9"},
            self._clean({"month": "9", "department": "", "employee": None}),
        )

    def test_malformed_json_raises_instead_of_failing_open(self):
        # **失败开放**曾导致 filters=not-json 返回全部 61816 行（22MB）。
        # 宁可报错，也不能默默返回全量。
        with self.assertRaises(Exception):
            self._clean("not-json")

    def test_non_object_json_raises(self):
        # '[1,2,3]' 是合法 JSON 但不是对象，同样不能放行
        with self.assertRaises(Exception):
            self._clean("[1, 2, 3]")

    def test_non_string_keys_are_dropped(self):
        # JSON 的键必是字符串；但 dict 入参可能是别处构造的，防御一下
        self.assertEqual({"ok": "1"}, self._clean({"ok": "1"}))


class ReportBoundsTest(unittest.TestCase):
    """`report_data._bounds` —— 行数上限是防 22MB 响应的那道闸。"""

    @classmethod
    def setUpClass(cls):
        _install_frappe_stub()

    def _bounds(self, limit, start):
        from hb_attendance_app.hbos_attendance import report_data

        return report_data._bounds(limit, start)

    def test_clamps_to_max(self):
        from hb_attendance_app.hbos_attendance.report_data import MAX_ROWS

        self.assertEqual(MAX_ROWS, self._bounds(10 ** 9, 0)[0])

    def test_floor_is_one(self):
        self.assertEqual(1, self._bounds(0, 0)[0])
        self.assertEqual(1, self._bounds(-5, 0)[0])

    def test_negative_start_becomes_zero(self):
        self.assertEqual(0, self._bounds(10, -3)[1])

    def test_garbage_falls_back(self):
        from hb_attendance_app.hbos_attendance.report_data import MAX_ROWS

        self.assertEqual(MAX_ROWS, self._bounds("abc", 0)[0])
        self.assertEqual(0, self._bounds(10, "abc")[1])

    def test_string_numbers_are_coerced(self):
        self.assertEqual((10, 5), self._bounds("10", "5"))


class ReportUnpackTest(unittest.TestCase):
    """`report_data._unpack` —— 报表返回值规整。"""

    @classmethod
    def setUpClass(cls):
        _install_frappe_stub()

    def _unpack(self, result):
        from hb_attendance_app.hbos_attendance import report_data

        return report_data._unpack(result)

    def test_two_tuple(self):
        self.assertEqual((["c"], ["d"]), self._unpack((["c"], ["d"])))

    def test_three_tuple_keeps_columns_and_data(self):
        # Frappe 脚本报表允许 `(columns, data, message)`。原实现只认 len==2，
        # 三元组会把整个元组当成 columns、data 变空 → 页面「正常但没数据」。
        columns, data = self._unpack((["c"], ["d"], "msg"))
        self.assertEqual(["c"], columns)
        self.assertEqual(["d"], data)

    def test_none(self):
        self.assertEqual(([], []), self._unpack(None))

    def test_one_tuple(self):
        self.assertEqual((["c"], []), self._unpack((["c"],)))

    def test_dict_becomes_one_row(self):
        columns, data = self._unpack({"a": 1})
        self.assertEqual("a", columns[0]["fieldname"])
        self.assertEqual({"a": 1}, data[0])


class ListSpecWhitelistTest(unittest.TestCase):
    """`list_data._spec` —— key 白名单。"""

    @classmethod
    def setUpClass(cls):
        _install_frappe_stub()

    def test_known_keys_resolve(self):
        from hb_attendance_app.hbos_attendance import list_data

        for key in ("import-log", "feishu-leave", "feishu-overtime", "feishu-rest-leave"):
            with self.subTest(key=key):
                self.assertIn("doctype", list_data._spec(key))

    def test_unknown_key_raises(self):
        from hb_attendance_app.hbos_attendance import list_data

        for key in ("", "employee", "../Employee", "HBOS Leave Record"):
            with self.subTest(key=key):
                with self.assertRaises(Exception):
                    list_data._spec(key)

    def test_every_spec_starts_with_name_column(self):
        # name 是 DocType 的稳定主键，前端 row-key 依赖它。
        # 缺了会退化成整行 JSON，而那个兜底在「两行显示值完全相同」时不唯一。
        from hb_attendance_app.hbos_attendance import list_data

        for key, spec in list_data.LIST_SPECS.items():
            with self.subTest(key=key):
                self.assertEqual("name", spec["columns"][0]["fieldname"])

    def test_filter_fields_are_declared_columns(self):
        # 能筛的字段必须也是展示列，否则用户筛了却看不到依据
        from hb_attendance_app.hbos_attendance import list_data

        for key, spec in list_data.LIST_SPECS.items():
            shown = {c["fieldname"] for c in spec["columns"]}
            for fieldname in spec.get("filters", []):
                with self.subTest(key=key, field=fieldname):
                    self.assertIn(fieldname, shown)


if __name__ == "__main__":
    unittest.main()
