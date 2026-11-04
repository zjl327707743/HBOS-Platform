"""G-01 回归：月度考勤表上传入口的服务端写权限门禁。

修复前 ``process_excel`` 只有 ``@frappe.whitelist()``：任何已登录用户
（含零角色 Website User、只读的 HR User）都能 POST 一个 xlsx 进来，
直接以 ``ignore_permissions=True`` 生成 Employee Checkin / Attendance
并 ``frappe.db.commit()``。

本测试锁定修复后的契约：

1. 入口由 ``api._require_hr_write`` 唯一写角色定义守卫，不另造第三套；
2. 门禁位于所有副作用（读取上传文件 / 解析 Excel / 查询 Employee /
   创建 doc / commit）之前；
3. 角色矩阵：Guest、零角色、HR User → deny；
   HR Manager、System Manager、Administrator → allow；
4. ``ignore_permissions`` 仍存在时，必须注明它是「已通过显式服务端 HR
   授权之后」的特权服务写 —— 不得声称它已经消失。
"""

import sys
import types
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).parents[1]
SRC = (APP_ROOT
       / "hb_attendance_app/hbos_attendance/page/hbos_monthly_upload/upload.py")

# 与 api._require_hr_write 保持一致的唯一写角色定义（此处仅用于断言，
# 不作为实现来源）。
SHARED_WRITE_ROLES = {"HR Manager", "System Manager"}

AUTHORIZED_WRITE_NOTE = (
    "privileged service write after explicit server-side HR authorization"
)


def _load_guard(roles):
    """在给定角色集合下导入**真实** api 模块，返回 (guard, thrown)。

    只替换 frappe 运行时外壳（get_roles / throw / whitelist），
    ``_require_hr_write`` 的实现保持生产代码原样。
    """
    thrown = []

    # CI 只装 openpyxl；api.py 顶部的 requests 与本测试无关，按需打桩。
    try:
        import requests  # noqa: F401
    except ImportError:
        sys.modules["requests"] = types.ModuleType("requests")

    frappe = types.ModuleType("frappe")
    frappe.PermissionError = PermissionError

    def get_roles(*_args, **_kwargs):
        return list(roles)

    def throw(msg, exc=None):
        thrown.append((msg, exc))
        raise (exc or Exception)(msg)

    frappe.get_roles = get_roles
    frappe.throw = throw
    frappe.whitelist = lambda *a, **k: (lambda fn: fn)
    frappe.log_error = lambda *a, **k: None
    frappe._dict = dict
    frappe.session = types.SimpleNamespace(user="synthetic@example.test")

    sys.modules["frappe"] = frappe
    for name in [m for m in list(sys.modules)
                 if m == "hb_attendance_app" or m.startswith("hb_attendance_app.")]:
        del sys.modules[name]

    from hb_attendance_app.hbos_attendance.api import _require_hr_write
    return _require_hr_write, thrown


class MonthlyUploadAuthzContractTest(unittest.TestCase):
    def setUp(self):
        self.src = SRC.read_text()
        self.entry = self._entry_body()

    def _entry_body(self):
        start = self.src.index("def process_excel(")
        end = self.src.index("\ndef _assign_shift_type(", start)
        return self.src[start:end]

    # ---------- 入口形态 ----------

    def test_entry_is_whitelisted_but_not_guest_callable(self):
        at = self.src.index("@frappe.whitelist()")
        decorator = self.src[at:self.src.index("\n", at)]
        self.assertNotIn("allow_guest", decorator,
                         "上传入口不得允许 Guest 调用")

    # ---------- 门禁存在性与唯一性 ----------

    def test_entry_executes_shared_hr_write_guard(self):
        self.assertIn("_require_hr_write()", self.entry)

    def test_guard_reuses_shared_api_helper(self):
        self.assertIn(
            "from hb_attendance_app.hbos_attendance.api import _require_hr_write",
            self.entry,
        )

    def test_no_third_write_role_definition_is_introduced(self):
        """不得在本文件内再造 Attendance 写角色集合。"""
        for token in ('"HR Manager"', "'HR Manager'",
                      '"System Manager"', "'System Manager'",
                      "WRITE_ROLES"):
            with self.subTest(token=token):
                self.assertNotIn(token, self.src)

    # ---------- 门禁必须在副作用之前 ----------

    def test_guard_precedes_every_side_effect(self):
        guard_at = self.entry.index("_require_hr_write()")
        side_effects = (
            ('frappe.request.files.get("file")', "读取上传文件 body"),
            ("openpyxl.load_workbook", "解析 Excel"),
            ('frappe.db.get_value("Employee"', "查询 Employee"),
            (".insert(", "创建任何 doc"),
            ("frappe.db.commit()", "commit"),
        )
        for anchor, what in side_effects:
            with self.subTest(side_effect=what):
                at = self.entry.index(anchor)
                self.assertLess(
                    guard_at, at,
                    "%s 发生在写权限门禁之前 —— 未授权请求会被业务处理" % what)

    def test_guard_is_the_first_statement_after_decorator(self):
        """门禁不得被塞进 try/条件分支里 —— 否则可能被绕过或延后。"""
        guard_at = self.entry.index("_require_hr_write()")
        before = self.entry[:guard_at]
        for bad in ("try:", "if ", "for ", "with "):
            with self.subTest(bad=bad):
                self.assertNotIn(
                    "\n    %s" % bad, before,
                    "门禁之前不得出现控制流语句：%s" % bad)

    # ---------- 角色矩阵（真实 guard 实现） ----------

    def test_role_matrix(self):
        cases = (
            ("Guest（零角色）", set(), False),
            ("零角色 Website User", set(), False),
            ("HR User only", {"HR User"}, False),
            ("HR Manager", {"HR Manager"}, True),
            ("System Manager", {"System Manager"}, True),
            # Frappe 下 Administrator 持有全部角色（含 System Manager），
            # 因此通过的是 System Manager 分支，而不是一条特例后门。
            ("Administrator", {"System Manager", "HR Manager", "HR User"}, True),
        )
        for label, roles, allowed in cases:
            with self.subTest(subject=label):
                guard, thrown = _load_guard(roles)
                if allowed:
                    guard()
                    self.assertEqual(thrown, [], "合法主体不应被拒绝")
                else:
                    with self.assertRaises(PermissionError):
                        guard()
                    self.assertEqual(len(thrown), 1, "拒绝必须经过 frappe.throw")

    def test_read_only_role_is_not_silently_promoted(self):
        """HR User 是读角色：不得因为看到 Desk 页面就获得写能力。"""
        guard, _ = _load_guard({"HR User"})
        with self.assertRaises(PermissionError):
            guard()

    def test_guard_denies_when_role_set_is_empty_not_allow(self):
        """缺失角色必须 DENY，绝不能默认放行。"""
        guard, _ = _load_guard(set())
        with self.assertRaises(PermissionError):
            guard()

    # ---------- 特权写必须被如实标注 ----------

    def test_privileged_writes_are_annotated_honestly(self):
        lines = [ln for ln in self.src.splitlines()
                 if "ignore_permissions=True" in ln
                 and not ln.lstrip().startswith("#")]
        self.assertTrue(
            lines,
            "若 ignore_permissions 已被移除，请同步更新 B2 证据并调整本测试")
        for ln in lines:
            with self.subTest(line=ln.strip()):
                self.assertIn(AUTHORIZED_WRITE_NOTE, ln)

    def test_comment_does_not_claim_ignore_permissions_is_gone(self):
        for ln in self.src.splitlines():
            if "ignore_permissions" in ln and ln.strip().startswith("#"):
                self.assertNotIn("已移除", ln)
                self.assertNotIn("已消失", ln)


if __name__ == "__main__":
    unittest.main()
