import unittest

# resolve_wiki_obj_token 是无依赖纯函数，放在 swap_mapping（纯标准库模块）里，
# 使本测试无需 frappe / requests 即可运行（本机与 CI 都没有 bench）。
from hb_attendance_app.hbos_attendance.swap_mapping import resolve_wiki_obj_token


class _Resp:
    def __init__(self, payload):
        self._p = payload

    def json(self):
        return self._p


class ResolveWikiTokenTest(unittest.TestCase):
    def test_success_returns_obj_token(self):
        def fake_get(url, params=None, headers=None, timeout=None):
            self.assertIn("wiki/v2/spaces/get_node", url)
            return _Resp({"code": 0, "data": {"node": {"obj_token": "XLD0bPiGXaP0JTsicHCcSLA4nlQ",
                                                       "obj_type": "bitable"}}})
        self.assertEqual(resolve_wiki_obj_token("tok", "node123", get=fake_get),
                         "XLD0bPiGXaP0JTsicHCcSLA4nlQ")

    def test_nonzero_code_raises(self):
        def fake_get(url, params=None, headers=None, timeout=None):
            return _Resp({"code": 131006, "msg": "node not found"})
        with self.assertRaises(Exception) as ctx:
            resolve_wiki_obj_token("tok", "node123", get=fake_get)
        self.assertIn("131006", str(ctx.exception))

    def test_missing_obj_token_raises(self):
        def fake_get(url, params=None, headers=None, timeout=None):
            return _Resp({"code": 0, "data": {"node": {}}})
        with self.assertRaises(Exception):
            resolve_wiki_obj_token("tok", "node123", get=fake_get)

    def test_network_error_raises(self):
        def fake_get(url, params=None, headers=None, timeout=None):
            raise RuntimeError("conn reset")
        with self.assertRaises(Exception):
            resolve_wiki_obj_token("tok", "node123", get=fake_get)


if __name__ == "__main__":
    unittest.main()
