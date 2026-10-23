"""Personal service boundary tests with explicit dependency injection, not Site evidence."""
from __future__ import annotations

import sys
import types
import unittest
from contextlib import ExitStack
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch

PORTAL = Path(__file__).resolve().parents[2] / "hbos_portal"
if str(PORTAL) not in sys.path:
    sys.path.insert(0, str(PORTAL))
sys.modules.setdefault("frappe", types.SimpleNamespace(whitelist=lambda **kwargs: lambda func: func))
if not hasattr(sys.modules["frappe"], "whitelist"):
    sys.modules["frappe"].whitelist = lambda **kwargs: lambda func: func

from hb_attendance_app.hbos_attendance.portal import personal
from hbos_portal.iam import policy


class Attr(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__


class Denied(Exception):
    pass


class Invalid(Exception):
    pass


class PersonalAttendanceTest(unittest.TestCase):
    def setUp(self):
        def throw(message, kind=Invalid): raise kind(message)
        self.calls = []
        def sql(query, params, **kwargs):
            self.calls.append((query, dict(params)))
            if "count(*)" in query:
                return [Attr(records=2, days=1)]
            return [Attr(id="CHECK-A", date=date(2026, 10, 14), time="08:01", log_type="IN", status="", source="Employee Checkin"), Attr(id="ATT-A", date=date(2026, 10, 14), time=None, log_type="", status="Present", source="Attendance")]
        self.fake = types.SimpleNamespace(conf=Attr(hbos_iam_enabled=1), local=Attr(form_dict=Attr()), db=Attr(sql=sql), PermissionError=Denied, ValidationError=Invalid, throw=throw)
        self.no_store, self.session_gate = Mock(), Mock()
        security = types.ModuleType("hbos_portal.iam.temporary_passwords")
        security.check_request = self.session_gate
        accounts = types.ModuleType("hbos_portal.auth.accounts")
        accounts.no_store = self.no_store
        utils = types.ModuleType("frappe.utils")
        utils.getdate = lambda value: value if isinstance(value, date) else date.fromisoformat(value)
        utils.nowdate = lambda: "2026-10-15"
        utils.get_system_timezone = lambda: "Asia/Shanghai"
        self.stack = ExitStack()
        self.stack.enter_context(patch.dict(sys.modules, {"hbos_portal.iam.temporary_passwords": security, "hbos_portal.auth.accounts": accounts, "frappe.utils": utils}))
        self.stack.enter_context(patch.object(personal, "frappe", self.fake))
        self.current_user = self.stack.enter_context(patch.object(policy, "get_current_user", return_value="user-a"))
        self.employee = self.stack.enter_context(patch.object(policy, "resolve_employee", return_value=Attr(name="EMP-A", user_id="user-a")))
        self.evaluator = self.stack.enter_context(patch.object(policy, "evaluate", return_value={"allowed": True}))
        self.addCleanup(self.stack.close)

    def read(self, **kwargs):
        return personal.get_my_attendance(date_from="2026-10-01", date_to="2026-10-15", **kwargs)

    def test_identity_comes_only_from_session_and_sql_predicate_is_shared(self):
        result = self.read()
        self.employee.assert_called_once_with("user-a")
        self.assertEqual(self.evaluator.call_count, 2)
        self.assertTrue(all(call.args == ("user-a", "attendance", "attendance.read", "SELF", "") for call in self.evaluator.call_args_list))
        self.assertEqual(len(self.calls), 2)
        count, rows = self.calls
        self.assertEqual(count[1], rows[1])
        self.assertEqual(count[1]["employee"], "EMP-A")
        self.assertEqual(count[0].count("employee=%(employee)s"), 2)
        self.assertEqual(rows[0].count("employee=%(employee)s"), 2)
        self.assertIn("limit %(limit)s offset %(offset)s", rows[0])
        self.assertEqual(result["data"]["total"], 2)
        self.assertEqual(result["data"]["summary"], {"records": 2, "days": 1})
        self.assertEqual((result['data']['date_from'], result['data']['date_to'], result['data']['site_timezone']), ('2026-10-01','2026-10-15','Asia/Shanghai'))
        self.assertEqual(set(result["data"]["rows"][0]), {"id", "date", "time", "log_type", "status", "source"})
        self.no_store.assert_called_once()

    def test_wire_subject_and_arbitrary_filters_are_refused_before_business_queries(self):
        for key in ("employee", "employee_id", "user", "department", "filters", "fields", "order_by"):
            with self.subTest(key=key):
                self.fake.local.form_dict = Attr({key: "B"})
                with self.assertRaises(Denied): self.read()
        self.assertEqual(self.calls, [])
        self.employee.assert_not_called()

    def test_signature_kwargs_cannot_silently_replace_the_actor(self):
        with self.assertRaises(Denied): self.read(employee="EMP-B")
        self.assertEqual(self.calls, [])

    def test_temporary_state_and_missing_employee_are_not_bypassed(self):
        self.session_gate.side_effect = Denied("password change required")
        with self.assertRaises(Denied): self.read()
        self.employee.assert_not_called()
        self.session_gate.side_effect = None
        self.employee.side_effect = Denied("identity conflict")
        with self.assertRaises(Denied): self.read()
        self.assertEqual(self.calls, [])

    def test_ungranted_manager_and_disabled_site_do_not_query_business_data(self):
        self.evaluator.return_value = {"allowed": False}
        with self.assertRaises(Denied): self.read()
        self.fake.conf.hbos_iam_enabled = 0
        self.evaluator.return_value = {"allowed": True}
        with self.assertRaises(Denied): self.read()
        self.assertEqual(self.calls, [])

    def test_revocation_at_final_check_refuses_to_return_the_loaded_projection(self):
        self.evaluator.side_effect = [{"allowed": True}, {"allowed": False}]
        with self.assertRaises(Denied): self.read()
        self.assertEqual(len(self.calls), 2)

    def test_retry_after_read_conflict_still_refuses_a_new_revocation_and_discards_loaded_rows(self):
        class Conflict(Exception): pass
        self.fake.QueryDeadlockError = Conflict
        self.fake.db.rollback = Mock()
        self.evaluator.side_effect = [{'allowed':True}, Conflict(), {'allowed':False}]
        with patch.object(policy,'frappe',self.fake), patch('time.sleep'), self.assertRaises(Denied):
            self.read()
        self.assertEqual(self.current_user.call_count, 2)
        self.assertEqual(len(self.calls), 2)
        self.fake.db.rollback.assert_called_once()

    def test_invalid_dates_and_unbounded_page_are_refused(self):
        for params in [{"page": 0}, {"page_size": 51}, {"page": "1.5"}, {"date_from": ""}, {"date_to": ""}, {"date_from": "2026-2-01"}, {"date_to": "2026-02-30"}, {"date_from": "not-a-date"}, {"date_from": "2026-10-16", "date_to": "2026-10-15"}, {"date_from": "2025-01-01", "date_to": "2026-10-15"}]:
            with self.subTest(params=params), self.assertRaises(Invalid):
                personal.bounded_request(**params)
