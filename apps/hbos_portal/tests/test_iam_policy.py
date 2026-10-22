from __future__ import annotations

import importlib
import json
import sys
import types
import unittest
from contextlib import ExitStack
from datetime import datetime, timedelta
from unittest.mock import patch

sys.modules.setdefault("frappe", types.SimpleNamespace())
from hbos_portal.iam import audit, guards, policy


class Attr(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__


class PermissionDenied(Exception):
    pass


class Invalid(Exception):
    pass


def rule(operation, kind="SELF", ref="", effect="allow", app="attendance", **extra):
    row = Attr(app_id=app, operation_id=operation, effect=effect, scope_type=kind, scope_ref=ref, include_descendants=0, valid_from=None, valid_until=None, qualification_ref=None)
    row.update(extra)
    return row


class FakeDB:
    def __init__(self):
        self.users = {"a": Attr(name="a", enabled=1, modified="1"), "b": Attr(name="b", enabled=1, modified="1"), "manager": Attr(name="manager", enabled=1, modified="1"), "Administrator": Attr(name="Administrator", enabled=1, modified="1")}
        self.employees = [Attr(name="EMP-001", user_id="a", department="D1", company="C", status="Active", employee_number="0001", modified="1"), Attr(name="EMP-002", user_id="b", department="D2", company="C", status="Active", employee_number="0002", modified="1")]
        self.departments = [Attr(name="D1", company="C", modified="1"), Attr(name="D2", company="C", modified="1")]
        self.policies = {}
        self.events = []
        self.sql_calls = []

    def rows(self, doctype):
        return {"User": list(self.users.values()), "Employee": self.employees, "Department": self.departments, "Company": [Attr(name="C")], "DocType": [Attr(name=policy.POLICY), Attr(name="Employee")], policy.POLICY: list(self.policies.values()), policy.RULE: [Attr(**dict(row), parent=doc.name, name=f"{doc.name}-{index}") for doc in self.policies.values() for index, row in enumerate(doc.rules)], audit.EVENT: self.events}[doctype]

    def matches(self, row, filters):
        for key, expected in (filters or {}).items():
            actual = row.get(key)
            if isinstance(expected, list) and expected[0] == "in":
                if actual not in expected[1]: return False
            elif actual != expected: return False
        return True

    def get_all(self, doctype, filters=None, fields=None, pluck=None, limit_page_length=0, **kwargs):
        rows = [row for row in self.rows(doctype) if self.matches(row, filters)]
        if limit_page_length: rows = rows[:limit_page_length]
        return [row.get(pluck) for row in rows] if pluck else [Attr({field: row.get(field) for field in fields}) if fields else row for row in rows]

    def get_value(self, doctype, name, field="name", **kwargs):
        filters = name if isinstance(name, dict) else {"name": name}
        rows = self.get_all(doctype, filters=filters)
        return (Attr({key: rows[0].get(key) for key in field}) if isinstance(field, list) else rows[0].get(field)) if rows else None

    def exists(self, doctype, name): return bool(self.get_value(doctype, name))

    def sql(self, query, params=None, **kwargs):
        self.sql_calls.append((query, params))
        if "where user_id=%s" in query:
            return self.get_all("Employee", filters={"user_id": params[0]}, limit_page_length=2)
        if "where department=%s" in query:
            return self.get_all("Employee", filters={"department": params[0]})
        if "where request_id=%s" in query:
            return self.get_all(audit.EVENT, filters={"request_id": params[0]}, limit_page_length=2)
        if "where department in" in query:
            return self.get_all("Employee", filters={"department": ["in", params["departments"]]})
        if "where subject_type=%s" in query:
            return self.get_all(policy.POLICY, filters={"subject_type": params[0], "subject_name": params[1]}, fields=["name"], limit_page_length=2)
        if "order by name for update" in query:
            import re
            doctype = re.search(r"from `tab([^`]+)`", query).group(1)
            fields = [field.strip('`') for field in query.split("select ", 1)[1].split(" from ", 1)[0].split(',')]
            return self.get_all(doctype, fields=fields)
        return [(0,)] if "count(*)" in query else []


class IAMPolicyTest(unittest.TestCase):
    def setUp(self):
        self.db = FakeDB()
        def throw(message, kind=Invalid): raise kind(message)
        self.fake = types.SimpleNamespace(db=self.db, get_all=self.db.get_all, session=Attr(user="manager"), conf=Attr(hbos_iam_enabled=1), flags=Attr(), local=Attr(response={}, request=Attr(method="POST")), PermissionError=PermissionDenied, ValidationError=Invalid, throw=throw)
        self.fake.get_doc = lambda doctype, name, **kwargs: self.db.policies[name]
        self.now = datetime(2026, 10, 15, 12)
        self.stack = ExitStack()
        for module in (policy, guards, audit): self.stack.enter_context(patch.object(module, "frappe", self.fake))
        self.stack.enter_context(patch.object(policy, "_now", return_value=self.now))
        self.addCleanup(self.stack.close)
        self.store("Department", "D1", [rule("app.enter"), rule("attendance.read")])

    def store(self, kind, name, rows, enabled=1):
        doc = Attr(name=f"{kind}-{name}", subject_type=kind, subject_name=name, version=1, enabled=enabled, modified="1", rules=rows)
        self.db.policies[doc.name] = doc
        return doc

    def test_employee_resolution_is_exact_and_leading_zero_number_is_preserved(self):
        self.assertEqual(policy.resolve_employee("a").employee_number, "0001")
        self.assertIsNone(policy.resolve_employee("manager", required=False))
        self.db.employees.append(Attr(self.db.employees[0], name="DUPLICATE"))
        with self.assertRaises(PermissionDenied): policy.resolve_employee("a", required=False)

    def test_fixed_read_retry_rolls_back_and_rechecks_instead_of_reusing_authorization(self):
        from unittest.mock import Mock
        class Conflict(Exception): pass
        self.fake.QueryDeadlockError = Conflict
        self.db.rollback = Mock()
        read = Mock(side_effect=[Conflict(), PermissionDenied('revoked')])
        with patch('time.sleep'), self.assertRaises(PermissionDenied):
            policy.current_read(read)
        self.assertEqual(read.call_count, 2)
        self.db.rollback.assert_called_once()
        read = Mock(side_effect=Conflict())
        with patch('time.sleep'), self.assertRaises(Conflict):
            policy.current_read(read)
        self.assertEqual(read.call_count, 4)

    def test_default_self_permission_fresh_db_and_no_role_fallback(self):
        self.assertTrue(policy.evaluate("a", "attendance", "attendance.read", "SELF", "")["allowed"])
        self.assertFalse(policy.evaluate("b", "attendance", "attendance.read", "SELF", "")["allowed"])
        self.db.users["a"].enabled = 0
        self.assertFalse(policy.evaluate("a", "attendance", "attendance.read", "SELF", "")["allowed"])

    def test_transfer_projection_uses_new_department_but_cannot_replace_the_employee(self):
        self.store('Department','D2',[rule('app.enter'),rule('attendance.read',effect='deny')])
        projected=Attr(self.db.employees[0],department='D2')
        current=policy.effective_work('User','a','attendance')
        after=policy.effective_work('User','a','attendance',employee_context=projected)
        self.assertTrue(current['operations'][0]['allowed']);self.assertFalse(after['operations'][0]['allowed'])
        self.assertEqual(self.db.employees[0].department,'D1')
        self.assertFalse(policy.effective_work('User','a','attendance',employee_context=self.db.employees[1])['operations'][0]['allowed'])

    def test_configured_self_scope_does_not_claim_access_before_first_password_completion(self):
        from hbos_portal.iam import temporary_passwords
        with patch.object(temporary_passwords,'status',return_value={'pending':True}):
            result=policy.evaluate('a','attendance','attendance.read','SELF','')
        self.assertFalse(result['allowed']);self.assertIn('首次改密',result['reason'])

    def test_unknown_objects_operations_and_unintegrated_export_are_rejected(self):
        for args in [("attendance", "attendance.read", "SELF", "EMP-002"), ("attendance", "attendance.read", "DEPARTMENT", "D1"), ("attendance", "attendance.export", "SELF", ""), ("unknown", "read", "SELF", "")]:
            self.assertFalse(policy.evaluate("a", *args)["allowed"])

    def test_disabled_site_flag_fails_closed_without_permission_table_queries(self):
        for disabled in (0, "0", "false", None):
            self.fake.conf.hbos_iam_enabled = disabled
            self.assertFalse(policy.evaluate("a", "attendance", "attendance.read", "SELF", "")["allowed"])
            with self.assertRaises(PermissionDenied): guards.require_capability("iam.access.read", department="D1")
            self.assertFalse(any(app["integrated"] for app in policy.registered_apps()))

    def test_disabled_or_conflicting_employee_cannot_read(self):
        self.db.employees[0].status = "Inactive"
        self.assertFalse(policy.evaluate("a", "attendance", "attendance.read", "SELF", "")["allowed"])

    def test_explicit_app_stop_has_precedence_and_removal_recomputes_current_defaults(self):
        self.store("User", "a", [rule("app.enter", "ALL", "*", "deny"), rule("attendance.read")])
        self.assertFalse(policy.evaluate("a", "attendance", "attendance.read", "SELF", "")["allowed"])
        self.db.policies["User-a"].rules = []
        self.db.policies["Department-D1"].rules = []
        self.assertFalse(policy.evaluate("a", "attendance", "attendance.read", "SELF", "")["allowed"])

    def test_per_action_object_pairs_and_limited_denials(self):
        now = self.now
        gates = [rule("app.enter", "WAREHOUSE", ref, app="synthetic") for ref in ("A", "B")]
        inherited = gates + [rule("read", "WAREHOUSE", ref, app="synthetic") for ref in ("A", "B")] + [rule("write", "WAREHOUSE", "A", app="synthetic")]
        own = [rule("read", "WAREHOUSE", "A", "deny", app="synthetic")]
        self.assertFalse(policy._decide(own, inherited, "synthetic", "read", "WAREHOUSE", "A", now)[0])
        self.assertTrue(policy._decide(own, inherited, "synthetic", "read", "WAREHOUSE", "B", now)[0])
        self.assertFalse(policy._decide(own, inherited, "synthetic", "write", "WAREHOUSE", "B", now)[0])
        own = [rule("read", "WAREHOUSE", "A", app="synthetic")]
        self.assertFalse(policy._decide(own, inherited, "synthetic", "read", "WAREHOUSE", "B", now)[0])

    def test_preview_uses_same_evaluator_without_writes_or_session_switch(self):
        before = json.dumps(self.db.policies, sort_keys=True)
        preview = policy.preview_effective_work("User", "a", "attendance", [rule("app.enter", "ALL", "*", "deny")])
        self.assertFalse(preview["operations"][0]["allowed"])
        self.assertTrue(policy.effective_work("User", "a", "attendance")["operations"][0]["allowed"])
        self.assertEqual(json.dumps(self.db.policies, sort_keys=True), before)
        self.assertEqual(self.fake.session.user, "manager")

    def test_context_revision_changes_on_expiry_membership_and_revocation(self):
        row = self.db.policies["Department-D1"].rules[1]
        row.valid_until = self.now + timedelta(minutes=1)
        before = policy.current_revision('a')
        with patch.object(policy, "_now", return_value=self.now + timedelta(minutes=2)):
            self.assertNotEqual(policy.current_revision('a'), before)
        self.db.employees[0].department = "D2"
        self.assertNotEqual(policy.current_revision('a'), before)

    def test_subject_app_revision_ignores_unrelated_people_apps_and_modified_times(self):
        before = policy.revision_digests('a')['app_revisions']['attendance']
        self.db.users['b'].enabled = 0
        self.db.employees[1].department = 'D1'
        self.store('User', 'b', [rule('attendance.read', effect='deny')])
        self.assertEqual(policy.revision_digests('a')['app_revisions']['attendance'], before)
        self.store('User', 'a', [rule('app.enter', app='iam_demo')])
        self.assertEqual(policy.revision_digests('a')['app_revisions']['attendance'], before)
        self.db.users['a'].modified = 'unrelated-profile'
        self.db.policies['Department-D1'].version += 1
        self.assertEqual(policy.revision_digests('a')['app_revisions']['attendance'], before)
        self.db.policies['Department-D1'].rules.append(rule('attendance.read', effect='deny'))
        self.assertNotEqual(policy.revision_digests('a')['app_revisions']['attendance'], before)
        self.assertFalse(policy.evaluate('a','attendance','attendance.read','SELF','')['allowed'])

    def test_subject_revision_tracks_qualification_registration_and_duplicate_association(self):
        before = policy.revision_digests('a')['app_revisions']['attendance']
        self.db.policies['Department-D1'].rules[1].qualification_ref = 'not-integrated'
        self.assertNotEqual(policy.revision_digests('a')['app_revisions']['attendance'], before)
        self.db.policies['Department-D1'].rules[1].qualification_ref = None
        self.db.employees.append(Attr(self.db.employees[0], name='duplicate'))
        self.assertNotEqual(policy.revision_digests('a')['app_revisions']['attendance'], before)
        self.assertFalse(policy.evaluate('a','attendance','attendance.read','SELF','')['allowed'])

    def test_target_context_tracks_related_expiry_but_not_unrelated_user(self):
        context = policy.effective_work("User", "a", "attendance")["context_revision"]
        self.db.users["b"].modified = "unrelated-change"
        self.assertEqual(policy.effective_work("User", "a", "attendance")["context_revision"], context)
        self.db.policies["Department-D1"].rules[1].valid_until = self.now + timedelta(minutes=1)
        context = policy.effective_work("Department", "D1", "attendance")["context_revision"]
        with patch.object(policy, "_now", return_value=self.now + timedelta(minutes=2)):
            self.assertNotEqual(policy.effective_work("Department", "D1", "attendance")["context_revision"], context)
        self.assertFalse(any("order by name for update" in query and "`tabUser`" in query for query, params in self.db.sql_calls))

    def test_management_delegation_checks_target_not_business_access(self):
        self.store("User", "manager", [rule("app.enter", "DEPARTMENT", "D1", app="iam"), rule("iam.access.manage", "DEPARTMENT", "D1", app="iam")])
        guards.require_capability("iam.access.manage", department="D1", app_id="attendance", target_user="a")
        with self.assertRaises(PermissionDenied): guards.require_capability("iam.access.manage", department="D2", app_id="attendance", target_user="b")
        self.assertEqual(guards.managed_departments("iam.access.manage"), ["D1"])
        self.assertFalse(policy.evaluate("manager", "attendance", "attendance.read", "SELF", "")["allowed"])

    def test_self_approval_and_department_management_inheritance_are_denied(self):
        self.store("User", "a", [rule("app.enter", "DEPARTMENT", "D1", app="iam"), rule("iam.access.manage", "DEPARTMENT", "D1", app="iam")])
        self.fake.session.user = "a"
        with self.assertRaises(PermissionDenied): guards.require_capability("iam.access.manage", department="D1", target_user="a")
        self.db.policies.pop("User-a")
        self.db.policies["Department-D1"].rules += [rule("app.enter", "DEPARTMENT", "D1", app="iam"), rule("iam.access.manage", "DEPARTMENT", "D1", app="iam")]
        with self.assertRaises(PermissionDenied): guards.require_capability("iam.access.manage", department="D1", target_user="b")

    def test_controlled_context_is_request_local_nested_and_resets_on_failure(self):
        with self.assertRaises(PermissionDenied): guards.require_controlled_write()
        with self.assertRaises(RuntimeError):
            with guards.controlled_write():
                with guards.controlled_write(): guards.require_controlled_write()
                raise RuntimeError()
        self.assertEqual(self.fake.flags.hbos_iam_write_depth, 0)

    def test_audit_replay_binds_actor_and_content_and_never_replays_secret(self):
        payload = {"enabled": True}
        self.db.events = [Attr(name="event", actor="manager", request_id="request-1234", request_hash=audit.request_hash("save", "User", "a", payload), operation="save", subject_type="User", subject_name="a", after_json=json.dumps({"changed": True, "temporary_password": "never-return", "proof": "never-return"}))]
        self.assertEqual(audit.replay("request-1234", "save", "User", "a", payload), {"changed": True})
        with self.assertRaises(Invalid): audit.replay("request-1234", "save", "User", "a", {"enabled": False})
        self.assertEqual(self.fake.local.response["http_status_code"], 409)
        self.fake.session.user = "b"
        with self.assertRaises(Invalid): audit.replay("request-1234", "save", "User", "a", payload)

    def test_rule_validation_rejects_unknown_descendants_and_unregistered_qualification(self):
        for row in [rule("attendance.export"), rule("attendance.read", "DEPARTMENT", "D1"), rule("attendance.read", include_descendants=1), rule("attendance.read", qualification_ref="unverified-text"), rule("app.enter", "ALL", "", "deny")]:
            with self.assertRaises(ValueError): policy.validate_rule(row)

    def test_native_guards_only_restrict_managed_security_changes(self):
        before = Attr(user_id="a", department="D1", company="C", status="Active")
        employee = Attr(before, department="D2")
        employee.get_doc_before_save = lambda: before
        with self.assertRaises(PermissionDenied): guards.guard_employee(employee)
        with guards.controlled_write(): guards.guard_employee(employee)
        unchanged = Attr(before, designation="different non-security field")
        unchanged.get_doc_before_save = lambda: before
        guards.guard_employee(unchanged)
        user_permission = Attr(user="a")
        with self.assertRaises(PermissionDenied): guards.guard_user_permission(user_permission)

    def test_policy_and_event_controllers_reject_direct_native_write(self):
        model = types.ModuleType("frappe.model.document")
        model.Document = type("Document", (), {})
        with patch.dict(sys.modules, {"frappe.model": types.ModuleType("frappe.model"), "frappe.model.document": model}):
            for slug, klass in [("policy", "HBOSIAMPolicy"), ("rule", "HBOSIAMRule"), ("change_event", "HBOSIAMChangeEvent")]:
                controller = importlib.import_module(f"hbos_portal.hbos_portal.doctype.hbos_iam_{slug}.hbos_iam_{slug}")
                with patch.object(controller, "frappe", self.fake):
                    with self.assertRaises(PermissionDenied): getattr(controller, klass)().validate()

    def test_controller_requires_version_increment_and_audit_is_immutable(self):
        model = types.ModuleType("frappe.model.document")
        model.Document = type("Document", (), {})
        with patch.dict(sys.modules, {"frappe.model": types.ModuleType("frappe.model"), "frappe.model.document": model}):
            controller = importlib.import_module("hbos_portal.hbos_portal.doctype.hbos_iam_policy.hbos_iam_policy")
            event_controller = importlib.import_module("hbos_portal.hbos_portal.doctype.hbos_iam_change_event.hbos_iam_change_event")
            with patch.object(controller, "frappe", self.fake), patch.object(event_controller, "frappe", self.fake):
                obj = controller.HBOSIAMPolicy()
                obj.name, obj.subject_type, obj.subject_name, obj.version, obj.rules = "User-a", "User", "a", 1, []
                obj.get_doc_before_save = lambda: Attr(subject_type="User", subject_name="a", version=1, rules=[])
                with guards.controlled_write():
                    with self.assertRaises(Invalid): obj.validate()
                    obj.version = 2
                    obj.validate()
                    event = event_controller.HBOSIAMChangeEvent()
                    event.is_new = lambda: False
                    with self.assertRaises(PermissionDenied): event.validate()
                    with self.assertRaises(PermissionDenied): event.on_trash()

    def test_audit_count_and_page_use_identical_authorized_subjects(self):
        with patch.object(guards, "require_capability"), patch.object(guards, "managed_departments", return_value=["D1"]), patch.object(guards, "isolated_root", return_value=False):
            result = audit.list_events()
        self.assertEqual(result["total"], 0)
        count, page = [(query, params) for query, params in self.db.sql_calls if "`tabHBOS IAM Change Event`" in query]
        count_where = count[0].split(" where ")[1]
        page_where = page[0].split(" where ")[1].split(" order by ")[0]
        self.assertEqual(count_where, page_where)
        self.assertIn("EMP-001", count[1].values())
        self.assertNotIn("EMP-002", count[1].values())
        self.assertNotIn("before_json", page[0])
        self.assertNotIn("after_json", page[0])


class CurrentReadDB(FakeDB):
    """A distinct current-read path: API target reads may not use get_all."""
    def __init__(self):
        super().__init__()
        self.rollback = lambda: None
        for index, row in enumerate(self.departments):
            row.update(department_name='Department ' + row.name, parent_department=None, disabled=0, lft=index + 1)
        for row in self.employees:
            row.update(employee_name=row.name, designation='Analyst')

    def sql(self, query, params=None, **kwargs):
        if 'from `tabDepartment` where name in' in query:
            self.sql_calls.append((query, params))
            return [Attr(row) for row in self.departments if row.name in params['departments']]
        if 'from `tabEmployee` where department in' in query:
            self.sql_calls.append((query, params))
            rows = [row for row in self.employees if row.department in params['departments']]
            rows = [row for row in rows if ('employee_id' not in params or row.name == params['employee_id']) and ('user_id' not in params or row.user_id == params['user_id'])]
            if 'search' in params:
                text = params['search'].strip('%').lower()
                rows = [row for row in rows if text in (row.employee_name + row.employee_number).lower()]
            return [Attr(row) for row in sorted(rows, key=lambda row: (row.employee_name, row.name))]
        if 'select name,enabled from `tabUser` where name=%s for update' == query:
            self.sql_calls.append((query, params))
            return [Attr(self.users[params[0]])] if params[0] in self.users else []
        return super().sql(query, params, **kwargs)


class IAMCurrentReadAPITest(unittest.TestCase):
    store = IAMPolicyTest.store

    def setUp(self):
        base = IAMPolicyTest()
        with patch(__name__ + '.FakeDB', CurrentReadDB):
            base.setUp()
        self.addCleanup(base.doCleanups)
        self.db, self.fake = base.db, base.fake
        self.fake.TimestampMismatchError = type('Conflict', (Exception,), {})
        self.fake.QueryDeadlockError = type('Deadlock', (Exception,), {})
        self.fake.QueryTimeoutError = type('LockTimeout', (Exception,), {})
        self.fake.logger = lambda name: types.SimpleNamespace(error=lambda *args: None)
        self.fake.whitelist = lambda *args, **kwargs: lambda function: function
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        with patch.dict(sys.modules, {'frappe': self.fake}):
            self.api = importlib.import_module('hbos_portal.api.iam_access')
            self.departments_api = importlib.import_module('hbos_portal.api.iam_departments')
        for module in (self.api, self.departments_api):
            self.stack.enter_context(patch.object(module, 'frappe', self.fake))
        self.stack.enter_context(patch.object(policy, 'current_revision', return_value='current-revision'))
        from hbos_portal.auth import accounts
        self.stack.enter_context(patch.object(accounts, 'browser_session_context', return_value='a' * 64))
        original_all = self.fake.get_all
        def no_employee_snapshot(doctype, *args, **kwargs):
            if doctype in {'Employee', 'User'}:
                raise AssertionError('API target read used an unlocked snapshot')
            return original_all(doctype, *args, **kwargs)
        self.fake.get_all = no_employee_snapshot
        self.delegate('iam', ['iam.access.read', 'iam.departments.read'])

    def test_database_lock_conflicts_are_retryable_and_never_report_saved(self):
        for kind in (self.fake.QueryDeadlockError, self.fake.QueryTimeoutError):
            def failed():
                raise kind('private database detail')
            result = self.api._call(failed)
            self.assertFalse(result['ok'])
            self.assertEqual(self.fake.local.response['http_status_code'], 409)
            self.assertEqual(result['error']['code'], 'CONFLICT')
            self.assertTrue(result['error']['retryable'])
            self.assertNotIn('private database detail', str(result))

    def delegate(self, app, operations):
        return self.store('User', 'manager', [rule('app.enter', 'DEPARTMENT', 'D1', app=app)] + [rule(operation, 'DEPARTMENT', 'D1', app=app) for operation in operations])

    def test_attendance_only_delegation_gets_matching_metadata_without_people_or_audit_entry(self):
        self.delegate('attendance', ['iam.access.read', 'iam.people.read', 'iam.audit.read'])
        result = self.api.get_capabilities()
        self.assertTrue(result['ok'], result)
        self.assertIn('iam.access.read', result['data']['capabilities'])
        self.assertNotIn('iam.people.read', result['data']['capabilities'])
        self.assertNotIn('iam.audit.read', result['data']['capabilities'])
        metadata = self.api.get_registered_apps()
        self.assertTrue(metadata['ok'], metadata)
        self.assertEqual([app['id'] for app in metadata['data']['apps']], ['attendance'])

    def test_no_read_delegation_does_not_return_an_app_registry(self):
        self.delegate('iam', ['iam.access.manage'])
        result = self.api.get_registered_apps()
        self.assertFalse(result['ok'])
        self.assertEqual(self.fake.local.response['http_status_code'], 403)

    def test_dispatcher_cmd_is_allowed_but_unknown_wire_fields_are_not_dropped(self):
        for function, method in [(self.api.get_capabilities, 'get_capabilities'), (self.api.get_registered_apps, 'get_registered_apps'), (self.departments_api.list_departments, 'list_departments')]:
            prefix = 'iam_departments' if method == 'list_departments' else 'iam_access'
            cmd = 'hbos_portal.api.' + prefix + '.' + method
            self.fake.form_dict = Attr(cmd=cmd)
            self.assertTrue(function(cmd=cmd)['ok'])
            self.assertFalse(function(cmd=cmd, employee='EMP-002')['ok'])
            self.assertEqual(self.fake.local.response['http_status_code'], 400)
            # Simulate a field discarded by dispatcher argument normalization.
            self.fake.form_dict = Attr(cmd=cmd, ignore_permissions=True)
            self.assertFalse(function(cmd=cmd)['ok'])
            self.assertEqual(self.fake.local.response['http_status_code'], 400)

    def test_app_people_wire_accepts_only_its_exact_query_fields_and_cmd(self):
        self.fake.form_dict = Attr(cmd='hbos_portal.api.iam_access.list_app_people', app_id='attendance', page=1, page_size=1)
        result = self.api.list_app_people('attendance', page=1, page_size=1, cmd=self.fake.form_dict.cmd)
        self.assertTrue(result['ok'], result)
        self.fake.form_dict.filters = {'department': 'D2'}
        self.assertFalse(self.api.list_app_people('attendance', page=1, page_size=1, cmd=self.fake.form_dict.cmd)['ok'])
        self.assertEqual(self.fake.local.response['http_status_code'], 400)

    def test_app_people_count_page_and_status_use_current_scoped_rows(self):
        self.db.users['a'].enabled = 0
        result = self.api.list_app_people('attendance', page=1, page_size=1)
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['data']['total'], 1)
        self.assertEqual([row['id'] for row in result['data']['items']], ['EMP-001'])
        self.assertEqual(result['data']['items'][0]['employee_number'], '0001')
        self.assertEqual(result['data']['items'][0]['account_status'], 'disabled')
        queries = [(query, params) for query, params in self.db.sql_calls if 'from `tabEmployee` where department in' in query]
        self.assertTrue(queries)
        # Owner decision (PR60 final gate): management reads use a non-locking
        # snapshot and every row is re-authorized; write commands lock and
        # re-check inside their own transaction. The invariant that still must
        # hold is one current, scoped population for count/page/status.
        self.assertTrue(all(not query.endswith('for update') and params['departments'] == ('D1',) for query, params in queries))
        self.assertNotIn('EMP-002', json.dumps(result))

    def test_out_of_scope_filter_and_moved_employee_do_not_disclose_existence(self):
        denied = self.api.list_app_people('attendance', department='D2')
        self.assertFalse(denied['ok'])
        self.db.employees[0].department = 'D2'
        moved = self.api.get_work_subject('EMP-001', 'attendance')
        absent = self.api.get_work_subject('NO-SUCH-EMPLOYEE', 'attendance')
        self.assertFalse(moved['ok'])
        self.assertEqual(moved['error'], absent['error'])
        self.assertFalse(any('select name,enabled from `tabUser`' in query for query, params in self.db.sql_calls))

    def test_recheck_before_count_excludes_a_delegation_withdrawn_during_population_read(self):
        original = guards.require_capability
        calls = 0
        def withdraw(operation, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                self.db.policies['User-manager'].rules = []
            return original(operation, **kwargs)
        with patch.object(guards, 'require_capability', side_effect=withdraw):
            result = self.api.list_app_people('attendance')
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['data']['total'], 0)
        self.assertEqual(result['data']['items'], [])

    def test_effective_read_checks_current_target_without_snapshot_work_authorizer(self):
        raw = dict(subject_type='User', subject_name='a', app_id='attendance', version=0, context_revision='r', operations=[], suspended=False)
        with patch.object(policy, 'effective_work', return_value=raw), patch.object(self.api.work_commands, '_authorize', side_effect=AssertionError('snapshot authorizer called')):
            result = self.api.get_effective_access('User', 'a', 'attendance')
        self.assertTrue(result['ok'], result)
        self.db.employees[0].department = 'D2'
        with patch.object(policy, 'effective_work') as effective:
            denied = self.api.get_effective_access('User', 'a', 'attendance')
        self.assertFalse(denied['ok'])
        effective.assert_not_called()

    def test_department_members_and_counts_use_the_same_current_scope(self):
        self.db.users['a'].enabled = 0
        result = self.departments_api.list_departments()
        self.assertTrue(result['ok'], result)
        self.assertEqual(len(result['data']['items']), 1)
        department = result['data']['items'][0]
        self.assertEqual(department['id'], 'D1')
        self.assertEqual(department['member_count'], 1)
        self.assertEqual(department['members'][0]['account_status'], 'disabled')
        self.assertNotIn('EMP-002', json.dumps(result))


    def test_department_list_retries_entire_scoped_read_after_deadlock(self):
        current = self.departments_api._current_employees
        calls = 0
        def transient(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise self.fake.QueryDeadlockError('synthetic read conflict')
            return current(*args, **kwargs)
        with patch.object(self.departments_api, '_current_employees', side_effect=transient), patch('time.sleep'):
            result = self.departments_api.list_departments()
        self.assertTrue(result['ok'], result)
        self.assertEqual(calls, 2)
        self.assertEqual(result['data']['items'][0]['member_count'], 1)

    def test_department_list_conflict_then_revocation_cannot_return_prior_members(self):
        current = self.departments_api._current_employees
        def withdraw(*args, **kwargs):
            current(*args, **kwargs)  # Rows existed in the discarded transaction.
            self.db.policies['User-manager'].rules = []
            raise self.fake.QueryDeadlockError('synthetic read conflict')
        with patch.object(self.departments_api, '_current_employees', side_effect=withdraw), patch('time.sleep'):
            result = self.departments_api.list_departments()
        self.assertFalse(result['ok'])
        self.assertEqual(self.fake.local.response['http_status_code'], 403)
        self.assertNotIn('data', result)
        self.assertNotIn('EMP-001', json.dumps(result))

    def test_department_list_exhausted_conflict_is_bounded_and_read_classified(self):
        with patch.object(self.departments_api, '_current_employees', side_effect=self.fake.QueryDeadlockError('private database detail')) as read, patch('time.sleep'):
            result = self.departments_api.list_departments()
        self.assertEqual(read.call_count, 4)
        self.assertEqual(result['error']['code'], 'READ_CONFLICT')
        self.assertEqual(self.fake.local.response['http_status_code'], 409)
        self.assertNotIn('private database detail', str(result))
