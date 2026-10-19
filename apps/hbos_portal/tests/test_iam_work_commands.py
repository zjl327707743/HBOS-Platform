"""Service-level fault injection only; real MariaDB/HTTP evidence belongs to C."""
from __future__ import annotations

import copy
import types
import unittest
from contextlib import ExitStack, nullcontext
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from .test_iam_policy import Attr, FakeDB, Invalid, PermissionDenied, rule
from hbos_portal.auth import onboarding
from hbos_portal.iam import audit, guards, policy, work_commands as work


class WorkCommandTest(unittest.TestCase):
    def setUp(self):
        self.db = FakeDB()
        def throw(message, kind=Invalid): raise kind(message)
        self.now = datetime(2026, 10, 15, 12)
        self.fake = types.SimpleNamespace(db=self.db, get_all=self.db.get_all, session=Attr(user="manager"), conf=Attr(hbos_iam_enabled=1), flags=Attr(), local=Attr(response={}, request=Attr(method="POST")), PermissionError=PermissionDenied, ValidationError=Invalid, TimestampMismatchError=Invalid, throw=throw, utils=Attr(now_datetime=lambda: self.now, get_datetime=lambda value: value if isinstance(value, datetime) else datetime.fromisoformat(value)))
        self.fake.get_doc = lambda kind, name, **kwargs: self.db.policies[name]
        self.stack = ExitStack()
        for module in (policy, guards, audit, work): self.stack.enter_context(patch.object(module, "frappe", self.fake))
        self.stack.enter_context(patch.object(policy, "_now", return_value=self.now))
        self.stack.enter_context(patch.object(onboarding, "serialize", return_value=nullcontext()))
        self.addCleanup(self.stack.close)

    def summary(self, enabled=True, version=5):
        return {"subject_type": "User", "subject_name": "a", "app_id": "attendance", "version": version, "context_revision": "current-context", "suspended": False, "operations": [{"operation_id": "attendance.read", "label": "查看自己的考勤", "available": True, "ordinary": True, "allowed": enabled, "source": "部门安排", "scopes": [{"scope_type": "SELF", "scope_ref": "", "label": "本人"}] if enabled else []}]}

    def test_wire_intentions_cannot_submit_a_policy_or_unregistered_scope(self):
        app = next(item for item in policy.registered_apps() if item["id"] == "attendance")
        for change in [
            {"operation_id": "attendance.read", "enabled": True, "scopes": [{"scope_type": "SELF", "scope_ref": "EMP-002"}]},
            {"operation_id": "attendance.export", "enabled": True, "scopes": []},
            {"operation_id": "attendance.read", "enabled": True, "scopes": [{"scope_type": "SELF", "scope_ref": ""}], "rules": []},
            {"operation_id": "attendance.read", "enabled": False, "scopes": [{"scope_type": "SELF", "scope_ref": ""}]},
        ]:
            with self.subTest(change=change), self.assertRaises((Invalid, PermissionDenied)):
                work.normalize_changes([change], app)

    def test_plan_uses_current_policy_rules_and_keeps_untouched_management_scope(self):
        old = Attr(version=4, rules=[rule("iam.access.read", "DEPARTMENT", "D1", app="iam")])
        current = Attr(version=5, rules=[rule("iam.access.read", "DEPARTMENT", "D2", app="iam")])
        def read(kind, name, for_update=False): return current if for_update else old
        def summarize(*args, **kwargs): return self.summary(enabled=not bool(kwargs.get("policy_overrides")))
        with patch.object(work, "_authorize", return_value=Attr(department="D1", company="C")), patch.object(policy, "get_policy", side_effect=read), patch.object(policy, "effective_work", side_effect=summarize):
            plan = work.build_plan("User", "a", "attendance", [{"operation_id": "attendance.read", "enabled": False, "scopes": []}])
        preserved = [item for item in plan["_rules"] if item["app_id"] == "iam"]
        self.assertEqual(preserved[0]["scope_ref"], "D2", "An RR snapshot must not restore a revoked untouched grant")
        self.assertEqual(plan["_version"], 5)

    def test_target_department_for_authorization_comes_from_current_read(self):
        old = Attr(name="EMP-001", department="D1", company="C", status="Active")
        current = Attr(name="EMP-001", department="D2", company="C", status="Active")
        def employees(*args, **kwargs): return [current if kwargs.get("for_update") else old]
        def sql(query, *args, **kwargs): return [current] if "tabEmployee" in query else []
        def capability(operation, **kwargs):
            if kwargs.get("department") != "D1": raise PermissionDenied("moved outside delegation")
        with patch.object(self.fake, "get_all", side_effect=employees), patch.object(self.db, "sql", side_effect=sql), patch.object(guards, "require_capability", side_effect=capability):
            with self.assertRaises(PermissionDenied): work._authorize("User", "a", "attendance", write=True)

    def test_delegation_cannot_mint_a_grant_beyond_its_entry_gate_expiry(self):
        end = self.now + timedelta(hours=1)
        gate = rule("app.enter", "DEPARTMENT", "D1", app="iam", valid_until=end)
        delegated = rule("iam.access.manage", "DEPARTMENT", "D1", app="iam")
        doc = Attr(version=1, rules=[gate, delegated])
        with patch.object(guards, "isolated_root", return_value=False), patch.object(policy, "get_current_user", return_value="manager"), patch.object(policy, "get_policy", return_value=doc):
            try:
                deadline = work._grant_deadline("User", Attr(department="D1", company="C"), "attendance")
            except PermissionDenied:
                return  # Conservatively declining an unsupported delegation is safe.
        self.assertIsNotNone(deadline, "An expiring entry gate is not an unbounded grant")
        self.assertLessEqual(deadline, end)

    def _commit_fixture(self, *, changed=True):
        target = Attr(version=5, rules=[])
        target.set = lambda key, value: target.__setitem__(key, value)
        target.save = Mock()
        self.db.savepoint = Mock()
        self.db.rollback = Mock()
        plan = {"_version": 5, "context_revision": "current-context", "changed": changed, "_rules": [dict(rule("attendance.read"))], "before": self.summary(), "after": self.summary(False)}
        return target, plan

    def test_stale_version_is_rejected_before_any_write_or_success_audit(self):
        target, plan = self._commit_fixture()
        with patch.object(policy, "get_current_user", return_value="manager"), patch.object(policy, "get_policy", return_value=target), patch.object(work, "_authorize"), patch.object(audit, "replay", return_value=None), patch.object(work, "build_plan", return_value=plan), patch.object(audit, "append_event") as event:
            with self.assertRaises(Invalid): work.commit_work("User", "a", "attendance", [], 4, "current-context", "request-concurrent-1234")
        target.save.assert_not_called()
        event.assert_not_called()

        self.assertEqual(self.fake.local.response["http_status_code"], 409)

    def test_authority_revoked_before_final_save_rolls_back_without_success_event(self):
        target, plan = self._commit_fixture()
        with patch.object(policy, "get_current_user", return_value="manager"), patch.object(policy, "get_policy", return_value=target), patch.object(work, "_authorize", side_effect=[None, PermissionDenied("revoked")]), patch.object(audit, "replay", return_value=None), patch.object(work, "build_plan", return_value=plan), patch.object(policy, "effective_work", return_value=self.summary()), patch.object(audit, "append_event") as event:
            with self.assertRaises(PermissionDenied): work.commit_work("User", "a", "attendance", [], 5, "current-context", "request-revoked-1234")
        target.save.assert_called_once()
        self.db.rollback.assert_called_once_with(save_point="iam_work_command")
        event.assert_not_called()

    def test_audit_failure_is_in_the_same_rollback_boundary(self):
        target, plan = self._commit_fixture()
        with patch.object(policy, "get_current_user", return_value="manager"), patch.object(policy, "get_policy", return_value=target), patch.object(work, "_authorize"), patch.object(audit, "replay", return_value=None), patch.object(work, "build_plan", return_value=plan), patch.object(policy, "effective_work", return_value=self.summary()), patch.object(audit, "append_event", side_effect=RuntimeError("event write failed")):
            with self.assertRaises(RuntimeError): work.commit_work("User", "a", "attendance", [], 5, "current-context", "request-failure-1234")
        self.db.rollback.assert_called_once_with(save_point="iam_work_command")

    def test_replay_requires_current_authority_and_never_reexecutes_plan(self):
        target, plan = self._commit_fixture()
        previous = {**self.summary(), "changed": True}
        with patch.object(policy, "get_current_user", return_value="manager"), patch.object(policy, "get_policy", return_value=target), patch.object(work, "_authorize") as authority, patch.object(audit, "replay", return_value=previous), patch.object(work, "build_plan") as build:
            result = work.commit_work("User", "a", "attendance", [], 5, "current-context", "request-replay-1234")
        authority.assert_called_once()
        build.assert_not_called()
        target.save.assert_not_called()
        self.assertTrue(result["replayed"])

    def test_no_change_does_not_write_a_personal_policy_or_success_event(self):
        target, plan = self._commit_fixture(changed=False)
        with patch.object(policy, "get_current_user", return_value="manager"), patch.object(policy, "get_policy", return_value=target), patch.object(work, "_authorize"), patch.object(audit, "replay", return_value=None), patch.object(work, "build_plan", return_value=plan), patch.object(audit, "append_event") as event:
            result = work.commit_work("User", "a", "attendance", [], 5, "current-context", "request-unchanged-1234")
        self.assertFalse(result["changed"])
        target.save.assert_not_called()
        event.assert_not_called()

    def _configure(self, rows, settings, department_rows=None):
        self.db.policies['Department-D1'] = Attr(name='Department-D1',subject_type='Department',subject_name='D1',version=1,enabled=1,rules=department_rows if department_rows is not None else [rule('app.enter'),rule('attendance.read')])
        self.db.policies['User-a'] = Attr(name='User-a',subject_type='User',subject_name='a',version=3,enabled=1,rules=rows)
        with patch.object(work,'_authorize',return_value=self.db.employees[0]),patch.object(guards,'isolated_root',return_value=True):
            return work.build_plan('User','a','attendance',kind='configure',settings=settings)

    def test_combined_source_pause_and_function_are_one_finite_plan(self):
        setting=dict(access_state='paused',permission_mode='personal',changes=[dict(operation_id='attendance.read',enabled=False,scopes=[])])
        plan=self._configure([],setting)
        self.assertTrue(plan['after']['suspended']);self.assertFalse(plan['after']['operations'][0]['allowed'])
        self.assertEqual(len([row for row in plan['_rules'] if work._stop(row,'attendance')]),1)
        self.assertEqual(plan['after']['permission_mode'],'personal')
        with self.assertRaises(Invalid):work.normalize_settings({**setting,'rules':[]},work._app('attendance'))

    def test_restore_access_preserves_personal_and_department_denies(self):
        stop=rule('app.enter','ALL','*',effect='deny')
        setting=dict(access_state='normal',permission_mode='personal',changes=[])
        plan=self._configure([rule('attendance.read',effect='deny'),stop],setting)
        self.assertFalse(plan['after']['suspended']);self.assertFalse(plan['after']['operations'][0]['allowed'])
        self.assertTrue(any(row['operation_id']=='attendance.read' and row['effect']=='deny' for row in plan['_rules']))
        self.assertFalse(any(work._stop(row,'attendance') for row in plan['_rules']))
        inherited=self._configure([stop],dict(access_state='normal',permission_mode='department',changes=[]),[rule('app.enter'),rule('attendance.read',effect='deny')])
        self.assertFalse(inherited['after']['operations'][0]['allowed']);self.assertIn('限制',inherited['after']['operations'][0]['reason'])

    def test_department_source_restores_actual_self_without_touching_other_app(self):
        other=rule('iam.access.read','DEPARTMENT','D2',app='iam')
        plan=self._configure([rule('attendance.read',effect='deny'),rule('app.enter','ALL','*',effect='deny'),other],dict(access_state='normal',permission_mode='department',changes=[]))
        self.assertTrue(plan['after']['operations'][0]['allowed']);self.assertEqual(plan['after']['permission_mode'],'department')
        self.assertEqual([row for row in plan['_rules'] if row['app_id']=='iam'],[work.plain_rule(other)])

    def test_ordinary_panel_cannot_replace_a_timed_personal_rule(self):
        with self.assertRaises(PermissionDenied):self._configure([rule('attendance.read',valid_until=self.now+timedelta(days=1))],dict(access_state='normal',permission_mode='department',changes=[]))

    def test_timed_application_stop_is_preserved_and_cannot_be_silently_replaced(self):
        timed=rule('app.enter','ALL','*',effect='deny',valid_until=self.now+timedelta(days=1))
        rows=[rule('attendance.read'),timed]
        with self.assertRaises(PermissionDenied):self._configure(rows,dict(access_state='normal',permission_mode='personal',changes=[]))
        plan=self._configure(rows,dict(access_state='paused',permission_mode='personal',changes=[]))
        self.assertFalse(plan['changed']);self.assertEqual(plan['_rules'],[work.plain_rule(row) for row in rows])

    def test_combined_save_audit_failure_rolls_back_the_whole_plan(self):
        target,plan=self._commit_fixture()
        setting=dict(access_state='paused',permission_mode='department',changes=[])
        with patch.object(policy,'get_current_user',return_value='manager'),patch.object(policy,'get_policy',return_value=target),patch.object(work,'_authorize'),patch.object(audit,'replay',return_value=None),patch.object(work,'build_plan',return_value=plan),patch.object(policy,'effective_work',return_value=self.summary()),patch.object(audit,'append_event',side_effect=RuntimeError('audit unavailable')):
            with self.assertRaises(RuntimeError):work.commit_work('User','a','attendance',expected_version=5,context_revision='current-context',request_id='combined-atomic-failure',kind='configure',settings=setting)
        self.db.rollback.assert_called_once_with(save_point='iam_work_command')

    def test_idempotent_configuration_receipt_preserves_source_but_never_a_secret(self):
        value=audit.safe_snapshot({'permission_mode':'personal','settings':{'access_state':'paused','permission_mode':'department','changes':[]},'password':'private','proof':'private'})
        self.assertEqual(value,{'permission_mode':'personal','settings':{'access_state':'paused','permission_mode':'department','changes':[]}})


class LifecycleCurrentReadTest(unittest.TestCase):
    """Simulate an older RR snapshot; these are not concurrent MariaDB tests."""

    def test_employee_scope_is_loaded_by_a_current_document_read(self):
        from hbos_portal.iam import people
        old = Attr(name="EMP-001", department="D1", company="C", user_id="a")
        current = Attr(name="EMP-001", department="D2", company="C", user_id="a")
        fake = types.SimpleNamespace(get_doc=Mock(side_effect=lambda *a, **kw: current if kw.get("for_update") else old))
        def authorize(operation, **kwargs):
            if kwargs["department"] != "D1":
                raise PermissionDenied("moved outside delegation")
        with patch.object(people, "frappe", fake), patch.object(guards, "require_capability", side_effect=authorize):
            with self.assertRaises(PermissionDenied):
                people._employee("EMP-001", "iam.people.read")
        fake.get_doc.assert_called_once_with("Employee", "EMP-001", for_update=True)

    def test_pending_password_state_cannot_be_hidden_by_an_old_snapshot(self):
        from hbos_portal.iam import temporary_passwords as temporary
        def get_value(*args, **kwargs):
            state = (1, 1, "future", 2) if kwargs.get("for_update") else (0, 0, None, 1)
            return Attr(zip(temporary.FIELDS, state))
        fake = types.SimpleNamespace(db=Attr(get_value=Mock(side_effect=get_value)))
        with patch.object(temporary, "frappe", fake), patch.object(temporary, "available", return_value=True):
            self.assertEqual(temporary.status("a"), dict(pending=True, temporary=True, expires_at="future", generation=2, can_claim=False))

    def test_managed_user_uses_current_department_and_current_policy(self):
        calls = []
        def get_value(kind, filters, field="name", **kwargs):
            calls.append((kind, filters, kwargs))
            return "POLICY-D2" if kwargs.get("for_update") and filters == {"subject_type": "Department", "subject_name": "D2"} else None
        fake = types.SimpleNamespace(db=Attr(exists=lambda *a: True, get_value=get_value, sql=Mock(return_value=[Attr(department="D2")])))
        with patch.object(guards, "frappe", fake), patch.object(policy, 'enabled_flag', return_value=False):
            self.assertTrue(guards._managed_user("a"))
        self.assertTrue(all(kwargs.get("for_update") for _, _, kwargs in calls))
        self.assertIn("for update", fake.db.sql.call_args.args[0])


class NativeIdentityLifecycleGuardTest(unittest.TestCase):
    def setUp(self):
        self.db = FakeDB()
        self.db.policies["Department-D1"] = Attr(name="Department-D1", subject_type="Department", subject_name="D1", rules=[], version=1)
        def throw(message, kind=Invalid):
            raise kind(message)
        self.fake = types.SimpleNamespace(db=self.db, conf=Attr(hbos_iam_enabled=1), flags=Attr(), throw=throw, PermissionError=PermissionDenied)
        self.stack = ExitStack()
        for module in (guards, policy):
            self.stack.enter_context(patch.object(module, "frappe", self.fake))
        self.addCleanup(self.stack.close)

    def test_delete_permission_denies_only_current_managed_identities(self):
        for doc in [Attr(doctype="User", name="a"), Attr(doctype="Employee", name="EMP-001", user_id="a", department="D1")]:
            with self.subTest(doctype=doc.doctype):
                self.assertFalse(guards.identity_has_permission(doc, user="manager", ptype="delete"))
                self.assertTrue(guards.identity_has_permission(doc, user="manager", ptype="read"))
        self.assertTrue(guards.identity_has_permission(Attr(doctype="User", name="b"), ptype="delete"))
        self.assertTrue(guards.identity_has_permission(Attr(doctype="Employee", name="EMP-002", user_id="b", department="D2"), ptype="delete"))

    def test_trash_and_rename_do_not_trust_controlled_or_document_flags(self):
        doc = Attr(doctype="User", name="a", flags=Attr(ignore_permissions=True))
        with guards.controlled_write():
            with self.assertRaises(PermissionDenied):
                guards.guard_identity_delete(doc, "on_trash")
            with self.assertRaises(PermissionDenied):
                guards.guard_identity_rename(doc, "before_rename", "a", "renamed", True)

    def test_persisted_employee_scope_cannot_be_laundered_by_detaching_payload(self):
        doc = Attr(doctype="Employee", name="EMP-001", user_id="", department="D2")
        with self.assertRaises(PermissionDenied):
            guards.guard_identity_delete(doc)
        with self.assertRaises(PermissionDenied):
            guards.guard_identity_rename(doc, old="EMP-001", new="OTHER")

    def test_rollout_disabled_and_unmanaged_legacy_lifecycle_remain_native(self):
        doc = Attr(doctype="User", name="b")
        guards.guard_identity_delete(doc)
        guards.guard_identity_rename(doc)
        self.fake.conf.hbos_iam_enabled = 0
        managed = Attr(doctype="User", name="a")
        self.assertTrue(guards.identity_has_permission(managed, ptype="delete"))
        guards.guard_identity_delete(managed)
        guards.guard_identity_rename(managed)

    def test_http_preflight_denies_fixed_native_delete_routes_before_controller(self):
        self.fake.session = Attr(user="Administrator")
        self.fake.local = Attr(request=Attr(method="DELETE", path="/api/resource/User/a"), form_dict=Attr())
        for path, args in [
            ("/api/resource/User/a", {}),
            ("/api/v2/document/Employee/EMP-001", {}),
            ("/api/method/frappe.client.delete", {"doctype": "User", "name": "a"}),
            ("/api/v2/method/frappe.client.delete", {"doctype": "Employee", "name": "EMP-001"}),
            ("/api/method", {"cmd": "frappe.desk.reportview.delete_items", "doctype": "User", "items": '["b","a"]'}),
            ("/api/method/other.path", {"cmd": "frappe.client.delete", "doctype": "User", "name": "a"}),
        ]:
            self.fake.local.request.path = path
            self.fake.local.form_dict = Attr(args)
            with self.subTest(path=path), self.assertRaises(PermissionDenied):
                guards.check_identity_request()
        self.fake.local.request.path = "/api/resource/User/b"
        self.fake.local.form_dict = Attr()
        guards.check_identity_request()  # old unmanaged HR lifecycle still native
        self.fake.local.request.path = "/api/resource/User/a"
        self.fake.local.request.method = "GET"
        guards.check_identity_request()  # the added hook grants/denies no normal reads

    def test_old_bulk_delete_job_cannot_borrow_administrator_authority(self):
        self.fake.local = Attr(job=Attr(user="Administrator"))
        self.fake.session = Attr(user="Administrator")
        with self.assertRaises(PermissionDenied):
            guards.check_identity_job("frappe.desk.reportview.delete_bulk", {"doctype": "User", "items": ["a"], "user": "unmanaged-spoof"})
        guards.check_identity_job("frappe.desk.reportview.delete_bulk", {"doctype": "User", "items": ["b"]})
        guards.check_identity_job("unrelated.job", {"doctype": "User", "items": ["a"]})

    def test_native_bulk_dictionary_or_scalar_cannot_evade_target_preflight(self):
        for names in ['{"a":true}', '"a"', '{"name":"a"}', '[{"name":"a"}]', 'null']:
            with self.subTest(names=names), self.assertRaises(PermissionDenied):
                guards._deny_managed_deletions("User", names)
