"""Explicit exact-Preview real WSGI management acceptance, inactive by default.

Native password login resumes genuine synthetic sessions. No virtual session,
Site switch, schema action, service start or persisted management configuration.
Fault injection is request-scoped and does not model a real network partition.
"""
import argparse
from dataclasses import replace
from datetime import timedelta
import json
import secrets
import unittest
from unittest.mock import patch
from uuid import uuid4

from hbos_portal.organization.frappe_repository import FrappeRelationRepository
from hbos_portal.organization.management_http import ManagedHTTPApplication, ManagedHTTPBinding
from hbos_portal.organization.relation_service import RelationService
from hbos_portal.organization.storage_schema import (
    ASSIGNMENT, ASSIGNMENT_REVISION, POSITION, POSITION_REVISION, RECEIPT, receipt_key,
)
if __package__:
    from .integration_management_relations import NativeManagedRelationCases, POLICY_KINDS, NOW
    from .integration_management_storage import policy_presence, policy_schema_check
    from .integration_organization_storage import (
        SITE, DB_HASH, KINDS, check_target, native_fingerprints, preflight, schema_check,
    )
else:
    from integration_management_relations import NativeManagedRelationCases, POLICY_KINDS, NOW
    from integration_management_storage import policy_presence, policy_schema_check
    from integration_organization_storage import (
        SITE, DB_HASH, KINDS, check_target, native_fingerprints, preflight, schema_check,
    )


ORIGIN = "http://" + SITE
API = "/api/method/hbos_portal.api.organization_relations."
SECURITY_API = "/api/method/hbos_portal.auth.accounts.get_request_security"
COMMANDS = ("create_position", "update_position", "create_assignment", "update_assignment")


def find_field(value, key):
    if isinstance(value, dict):
        if key in value:
            return value[key]
        for child in value.values():
            result = find_field(child, key)
            if result is not None:
                return result
    elif isinstance(value, list):
        for child in value:
            result = find_field(child, key)
            if result is not None:
                return result
    return None


class NativeManagementHTTPCases(unittest.TestCase):
    """Composition deliberately avoids rerunning inherited native CLI cases."""
    native = None

    def setUp(self):
        from werkzeug.test import Client
        from werkzeug.wrappers import Response
        import frappe.app
        from frappe.utils.password import update_password

        f = self.native
        self.fixture = NativeManagedRelationCases()
        self.fixture.native = f
        self.now = NOW
        self.clients = []
        self.session_ids = set()
        self.role_id = "MR-HTTP-ROLE-" + uuid4().hex
        self.log_tables = {}
        self.addCleanup(self.cleanup)
        self.fixture.setUp()
        self.fixture._cleanups.clear()  # This test owns the exact composed cleanup.
        for kind in ("Activity Log", "Error Log"):
            self.log_tables[kind] = {row[0] for row in f.db.sql(f"SELECT name FROM `tab{kind}`")}
        f.set_user("Administrator")
        for user in (self.fixture.manager, self.fixture.beneficiary):
            f.db.sql("UPDATE `tabUser` SET first_name=%s,full_name=%s WHERE name=%s",
                     ("管理HTTP合成用户", "管理HTTP合成用户", user))
        f.db.sql("INSERT INTO `tabHas Role` (name,parent,parenttype,parentfield,role,idx,modified) "
                 "VALUES (%s,%s,'User','roles','System Manager',1,NOW(6))",
                 (self.role_id, self.fixture.beneficiary))
        self.manager_password = secrets.token_urlsafe(40)
        self.ordinary_password = secrets.token_urlsafe(40)
        update_password(self.fixture.manager, self.manager_password)
        update_password(self.fixture.beneficiary, self.ordinary_password)
        f.db.commit()
        self.database_class = type(f.local.db)
        self.native_application = frappe.app.application
        self.binding = ManagedHTTPBinding(site_id=SITE, database_sha256=DB_HASH, origin=ORIGIN,
            approval_verifier=self.fixture.approvals(), clock=lambda: self.now, enabled=True)
        self.application = ManagedHTTPApplication(self.native_application, binding=self.binding)
        self.client = Client(self.application, Response, use_cookies=True)
        self.clients.append(self.client)
        self.token = self.login(self.client, self.fixture.manager, self.manager_password)
        self.reconnect()

    def reconnect(self):
        f = self.native
        if getattr(f.local, "db", None):
            f.db.close()
        f.init(site=SITE, sites_path=".", force=True)
        f.connect()
        f.set_user("Administrator")
        check_target(f, DB_HASH)
        f.db.rollback()
        return f

    def cleanup(self):
        f = self.reconnect()
        users = (self.fixture.manager, self.fixture.beneficiary, self.fixture.approver)
        sessions = f.db.sql("SELECT sid FROM `tabSessions` WHERE user IN (%s,%s,%s)", users)
        self.session_ids.update(row[0] for row in sessions)
        for sid in self.session_ids:
            f.db.sql("DELETE FROM `tabSessions` WHERE sid=%s AND user IN (%s,%s,%s)", (sid, *users))
            f.cache.hdel("session", sid)
        f.db.sql("DELETE FROM `tabHas Role` WHERE name=%s AND parent=%s", (self.role_id, self.fixture.beneficiary))
        for user in users:
            f.db.sql("DELETE FROM `__Auth` WHERE doctype='User' AND name=%s", (user,))
            f.cache.hdel("login_failed_count", user)
            f.cache.hdel("redirect_after_login", user)
            f.clear_cache(user=user)
        # Login/error records belong to this run's exact new IDs, never all logs.
        for kind, previous in self.log_tables.items():
            current = {row[0] for row in f.db.sql(f"SELECT name FROM `tab{kind}`")}
            for key in current - previous:
                f.db.sql(f"DELETE FROM `tab{kind}` WHERE name=%s", (key,))
        f.db.commit()
        self.fixture.cleanup()
        self.manager_password = self.ordinary_password = None

    def login(self, client, user, password):
        response = client.post("/api/method/login", base_url=ORIGIN,
            json={"usr": user, "pwd": password}, headers={"Origin": ORIGIN, "Accept": "application/json"},
            buffered=True)
        try:
            self.assertEqual(response.status_code, 200)
            body = response.get_json()
            self.assertIn(find_field(body, "message"), ("Logged In", "No App"))
            cookie = client.get_cookie("sid", domain=SITE)
            self.assertIsNotNone(cookie)
            self.assertNotEqual(cookie.value, "Guest")
            self.session_ids.add(cookie.value)
        finally:
            response.close()
        response = client.get(SECURITY_API, base_url=ORIGIN,
            headers={"Accept": "application/json"}, buffered=True)
        try:
            self.assertEqual(response.status_code, 200)
            token = find_field(response.get_json(), "csrf_token")
            self.assertTrue(isinstance(token, str) and len(token) >= 16)
            return token
        finally:
            response.close()

    def on_managed_request(self):
        request = getattr(self.native.local, "request", None)
        return bool(request and request.path in {API + command for command in COMMANDS}
                    and getattr(self.native.local, "site", None) == SITE)

    def args(self, command, payload, *, actor=None, **extra):
        body = dict(payload=payload, idempotency_key=str(uuid4()), expected_revision=0,
                    reason="管理HTTP整请求隔离合成验收")
        body.update(extra)
        self.fixture.requests.add(receipt_key(SITE, actor or self.fixture.manager, command, body["idempotency_key"]))
        return body

    def request(self, command, body, *, client=None, token=None, method="POST", origin=ORIGIN, **extra):
        headers = {"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"}
        if origin is not None:
            headers["Origin"] = origin
        if token is not False:
            headers["X-Frappe-CSRF-Token"] = self.token if token is None else token
        response = (client or self.client).open(API + command, method=method, base_url=ORIGIN,
            json=body, headers=headers, buffered=True, **extra)
        try:
            return response.status_code, response.get_json(), response.get_data(as_text=True)
        finally:
            response.close()

    def counts(self):
        f = self.reconnect()
        return tuple(f.db.count(kind) for kind in (POSITION, POSITION_REVISION, ASSIGNMENT, ASSIGNMENT_REVISION, RECEIPT))

    def denied(self, response, before, *, code=None):
        status, body, raw = response
        self.assertGreaterEqual(status, 400)
        self.assertIsNone(find_field(body, "record_id"))
        if code:
            self.assertIn(code, raw)
        self.assertEqual(self.counts(), before)

    def stable_forbidden(self, response):
        body = response[1]
        self.assertIsInstance(body, dict)
        message = body.get("message")
        self.assertIsInstance(message, dict)
        self.assertIs(message.get("ok"), False)
        self.assertEqual(message.get("error", {}).get("code"), "FORBIDDEN")
        forbidden = {"exc", "exc_type", "exception", "traceback", "_server_messages", "_exc_source"}
        pending = [body]
        while pending:
            value = pending.pop()
            if isinstance(value, dict):
                self.assertFalse(set(value) & forbidden)
                pending.extend(value.values())
            elif isinstance(value, list):
                pending.extend(value)

    def successful(self, response):
        status, body, _ = response
        self.assertEqual(status, 200)
        record = find_field(body, "record_id")
        self.assertTrue(isinstance(record, str) and len(record) == 36)
        self.assertNotEqual(find_field(body, "authorization_effect"), "allow")
        self.assertIsNot(find_field(body, "runtime_verified"), True)
        return record

    def after_execute(self, action):
        original = RelationService.execute

        def wrapped(service, *args, **kwargs):
            result = original(service, *args, **kwargs)
            if self.on_managed_request():
                action(service, result)
            return result

        return patch.object(RelationService, "execute", wrapped)

    def test_native_password_login_session_resume_and_successful_committed_create_update(self):
        payload = self.fixture.position_payload()
        first = self.successful(self.request("create_position", self.args("create_position", payload)))
        second = self.successful(self.request("update_position", self.args("update_position",
            {**payload, "title": "合成HTTP岗位改名"}, record_id=first, expected_revision=1)))
        self.assertEqual(second, first)
        self.assertEqual(self.counts(), (1, 2, 0, 0, 2))
        self.assertEqual(self.native.db.get_value(POSITION, first, "revision"), 2)

    def test_assignment_routes_commit_and_self_benefit_request_is_refused(self):
        first = self.successful(self.request("create_position", self.args("create_position", self.fixture.position_payload())))
        person_payload = self.fixture.assignment_payload(first)
        assignment = self.successful(self.request("create_assignment", self.args("create_assignment", person_payload)))
        ended = self.successful(self.request("update_assignment", self.args("update_assignment",
            {**person_payload, "status": "revoked"}, record_id=assignment, expected_revision=1)))
        self.assertEqual(ended, assignment)
        self.assertEqual(self.counts(), (1, 1, 1, 2, 3))
        self.assertEqual(self.native.db.get_value(ASSIGNMENT, assignment, "subject_user"), self.fixture.beneficiary)
        before = self.counts()
        self_payload = self.fixture.assignment_payload(first, employee=self.fixture.manager_employee)
        self.denied(self.request("create_assignment", self.args("create_assignment", self_payload)), before)

    def test_missing_or_wrong_csrf_wrong_origin_and_guest_session_refused(self):
        from werkzeug.test import Client
        from werkzeug.wrappers import Response
        before = self.counts()
        for token, origin in ((False, ORIGIN), ("synthetic-wrong-token", ORIGIN),
                              (None, "https://other.invalid"), (None, None)):
            with self.subTest(token_present=token is not False, origin_valid=origin == ORIGIN):
                self.denied(self.request("create_position", self.args("create_position", self.fixture.position_payload()),
                                         token=token, origin=origin), before)
        guest = Client(self.application, Response, use_cookies=True)
        self.clients.append(guest)
        response = self.request("create_position", self.args("create_position", self.fixture.position_payload()), client=guest)
        self.stable_forbidden(response)
        self.denied(response, before)

    def test_get_unknown_fields_and_client_management_identity_refused(self):
        before = self.counts()
        response = self.request("create_position", self.args("create_position", self.fixture.position_payload()), method="GET")
        self.stable_forbidden(response)
        self.denied(response, before)
        for field, value in (("unexpected", True), ("actor_user", "Administrator"), ("policy_ref", "request-injected")):
            with self.subTest(field=field):
                body = self.args("create_position", self.fixture.position_payload())
                body[field] = value
                self.denied(self.request("create_position", body), before)

    def test_plain_native_application_and_disabled_wrapper_cannot_write(self):
        from werkzeug.test import Client
        from werkzeug.wrappers import Response
        before = self.counts()
        for application in (self.native_application, ManagedHTTPApplication(self.native_application)):
            client = Client(application, Response, use_cookies=True)
            self.clients.append(client)
            token = self.login(client, self.fixture.manager, self.manager_password)
            self.denied(self.request("create_position", self.args("create_position", self.fixture.position_payload()),
                                     client=client, token=token), before)

    def test_native_system_manager_role_does_not_supply_management_policy(self):
        from werkzeug.test import Client
        from werkzeug.wrappers import Response
        client = Client(self.application, Response, use_cookies=True)
        self.clients.append(client)
        token = self.login(client, self.fixture.beneficiary, self.ordinary_password)
        before = self.counts()
        body = self.args("create_position", self.fixture.position_payload(), actor=self.fixture.beneficiary)
        self.denied(self.request("create_position", body, client=client, token=token), before)

    def test_native_session_refresh_threshold_commits_fact_and_session_tail(self):
        """Age an actual resumed session; execute native update, without patching it."""
        commits, observed = [], {}
        original = self.database_class.commit

        def commit(db, *args, **kwargs):
            if self.on_managed_request():
                commits.append(db.transaction_writes)
            return original(db, *args, **kwargs)

        def age_session(service, result):
            f = self.native
            session = f.local.session_obj
            self.assertEqual(session.sid, self.client.get_cookie("sid", domain=SITE).value)
            old = f.utils.now_datetime() - timedelta(seconds=601)
            session.data.data.last_updated = old
            # This exact synthetic session is already authenticated. Aging its
            # real persisted timestamp makes the final DB assertion distinguish
            # a completed native refresh from silently ignored session writes.
            f.db.sql("UPDATE `tabSessions` SET lastupdate=%s WHERE sid=%s AND user=%s",
                     (old, session.sid, self.fixture.manager))
            observed.update(sid=session.sid, old=old, session=session)

        with patch.object(self.database_class, "commit", commit), self.after_execute(age_session):
            record = self.successful(self.request("create_position", self.args("create_position", self.fixture.position_payload())))
        self.assertEqual(len(commits), 2)
        self.assertGreaterEqual(commits[0], 3)
        self.assertGreaterEqual(commits[1], 1)
        self.assertEqual(self.counts(), (1, 1, 0, 0, 1))
        row = self.native.db.sql("SELECT lastupdate,sessiondata FROM `tabSessions` WHERE sid=%s AND user=%s",
                                  (observed["sid"], self.fixture.manager))
        self.assertEqual(len(row), 1)
        self.assertGreater(row[0][0], observed["old"])
        self.assertGreater(self.native.utils.get_datetime(json.loads(row[0][1])["last_updated"]), observed["old"])
        self.assertEqual(self.native.db.get_value(POSITION, record, "revision"), 1)

    def test_unapproved_third_commit_after_real_session_refresh_is_refused(self):
        def age_and_queue(service, result):
            f = self.native
            f.local.session_obj.data.data.last_updated = f.utils.now_datetime() - timedelta(seconds=601)

            def queue_after_native_session():
                # sync_database adds the native session update after this first
                # callback. Adding here puts the forbidden commit after it.
                f.request.after_response.add(lambda: f.db.commit(chain=True))

            f.request.after_response.add(queue_after_native_session)

        with self.after_execute(age_and_queue):
            response = self.request("create_position", self.args("create_position", self.fixture.position_payload()))
        self.assertGreaterEqual(response[0], 400)
        self.assertIn("SAVE_RESULT_UNKNOWN", response[2])
        self.assertIsNone(find_field(response[1], "record_id"))
        # Both allowed commits have completed. Rejecting a third one cannot
        # honestly report that the first fact write was rolled back.
        self.assertEqual(self.counts(), (1, 1, 0, 0, 1))

    def test_revision_receipt_and_serialization_faults_roll_back_whole_request(self):
        import frappe.utils.response
        before = self.counts()
        for stage in ("revision", "receipt", "serialization"):
            with self.subTest(stage=stage):
                if stage == "serialization":
                    original = frappe.utils.response.orjson_dumps

                    def fail(value, *args, **kwargs):
                        if self.on_managed_request() and find_field(value, "record_id"):
                            raise TypeError("SYNTHETIC_RESPONSE_SERIALIZATION_FAILURE")
                        return original(value, *args, **kwargs)

                    context = patch.object(frappe.utils.response, "orjson_dumps", fail)
                else:
                    method = "append_revision" if stage == "revision" else "insert_receipt"
                    original = getattr(FrappeRelationRepository, method)

                    def fail(repository, *args, **kwargs):
                        result = original(repository, *args, **kwargs)
                        if self.on_managed_request():
                            raise RuntimeError("SYNTHETIC_MANAGED_" + stage.upper() + "_FAILURE")
                        return result

                    context = patch.object(FrappeRelationRepository, method, fail)
                with context:
                    self.denied(self.request("create_position", self.args("create_position", self.fixture.position_payload())), before)

    def test_same_key_replay_and_conflict_remain_currently_authorized(self):
        body = self.args("create_position", self.fixture.position_payload())
        first = self.successful(self.request("create_position", body))
        before = self.counts()
        replay = self.request("create_position", body)
        self.assertEqual(self.successful(replay), first)
        self.assertIs(find_field(replay[1], "replayed"), True)
        self.assertEqual(self.counts(), before)
        self.denied(self.request("create_position", {**body, "reason": "合成同键不同内容"}), before)
        f = self.reconnect()
        self.fixture.install(replace(self.fixture.policy, status="revoked", revision=2, authority_generation=2), approved=False, expected=1)
        f.db.commit()
        self.denied(self.request("create_position", body), before)

    def test_delay_after_execute_expires_policy_before_actual_commit(self):
        before = self.counts()
        with self.after_execute(lambda service, result: setattr(self, "now", self.fixture.policy.valid_until_utc)):
            self.denied(self.request("create_position", self.args("create_position", self.fixture.position_payload())), before)

    def test_before_commit_policy_source_and_master_changes_refuse_and_roll_back(self):
        for change in ("policy", "source", "master"):
            with self.subTest(change=change):
                before = self.counts()

                def register(service, result):
                    def mutate():
                        f = self.native
                        if change == "policy":
                            self.fixture.install(replace(self.fixture.policy, status="revoked", revision=2, authority_generation=2),
                                                 native=f, approved=False, expected=1)
                        elif change == "source":
                            f.db.sql("UPDATE `tabDepartment` SET disabled=1,modified=NOW(6) WHERE name=%s", (self.fixture.department,))
                        else:
                            f.db.sql("UPDATE `tabHBOS Position` SET revision=99,status='inactive' WHERE name=%s", (result.record_id,))
                    self.native.db.before_commit.add(mutate)

                with self.after_execute(register):
                    self.denied(self.request("create_position", self.args("create_position", self.fixture.position_payload())), before)
                self.assertEqual(self.native.db.get_value("Department", self.fixture.department, "disabled"), 0)
                self.assertEqual(self.native.db.get_value("HBOS Organization Management Policy", self.fixture.policy_id, "revision"), 1)

    def test_before_commit_recursive_and_early_commit_are_refused(self):
        for phase in ("early", "recursive"):
            with self.subTest(phase=phase):
                before = self.counts()

                def register(service, result):
                    if phase == "early":
                        self.native.db.commit()
                    else:
                        self.native.db.before_commit.add(lambda: self.native.db.commit())

                with self.after_execute(register):
                    self.denied(self.request("create_position", self.args("create_position", self.fixture.position_payload())), before)

    def test_rollback_failure_returns_unavailable_without_success_and_closes_connection(self):
        original = self.database_class.rollback
        before = self.counts()

        def rollback(db, *args, **kwargs):
            if self.on_managed_request() and not kwargs.get("save_point"):
                raise RuntimeError("SYNTHETIC_ROLLBACK_TRANSPORT_FAILURE")
            return original(db, *args, **kwargs)

        with patch.object(self.database_class, "rollback", rollback), self.after_execute(
                lambda service, result: setattr(self, "now", self.fixture.policy.valid_until_utc)):
            response = self.request("create_position", self.args("create_position", self.fixture.position_payload()))
            self.assertGreaterEqual(response[0], 400)
            self.assertIn("SOURCE_UNAVAILABLE", response[2])
            self.assertNotIn("SAVE_RESULT_UNKNOWN", response[2])
            self.assertIsNone(find_field(response[1], "record_id"))
        self.assertEqual(self.counts(), before)

    def test_sql_commit_and_after_commit_faults_report_unknown_never_false_rollback(self):
        for phase in ("sql_commit_return", "after_commit"):
            with self.subTest(phase=phase):
                before = self.counts()
                body = self.args("create_position", self.fixture.position_payload())
                if phase == "sql_commit_return":
                    original = self.database_class.commit

                    def commit(db, *args, **kwargs):
                        result = original(db, *args, **kwargs)
                        if self.on_managed_request():
                            raise RuntimeError("SYNTHETIC_COMMIT_RETURN_TRANSPORT_FAILURE")
                        return result

                    context = patch.object(self.database_class, "commit", commit)
                else:
                    def register(service, result):
                        def fail():
                            raise RuntimeError("SYNTHETIC_AFTER_COMMIT_FAILURE")
                        self.native.db.after_commit.add(fail)
                    context = self.after_execute(register)
                with context:
                    response = self.request("create_position", body)
                    self.assertGreaterEqual(response[0], 400)
                    self.assertIn("SAVE_RESULT_UNKNOWN", response[2])
                    self.assertIsNone(find_field(response[1], "record_id"))
                after = self.counts()
                self.assertEqual(after, tuple(value + delta for value, delta in zip(before, (1, 1, 0, 0, 1))))
                replay = self.request("create_position", body)
                self.successful(replay)
                self.assertIs(find_field(replay[1], "replayed"), True)
                self.assertEqual(self.counts(), after)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("preflight", "test"), default="preflight")
    parser.add_argument("--expected-database-sha256", required=True)
    args = parser.parse_args()
    import frappe
    frappe.init(site=SITE, sites_path=".")
    frappe.connect()
    try:
        frappe.db.sql("START TRANSACTION READ ONLY")
        report = check_target(frappe, args.expected_database_sha256)
        report["preflight"] = preflight(frappe)
        report["policy_tables_present"] = policy_presence(frappe)
        if not all(report["preflight"]["tables_present"].values()) or not all(report["policy_tables_present"].values()):
            raise RuntimeError("MANAGED_SCHEMA_REQUIRED")
        if any(frappe.db.count(kind) for kind in (*KINDS, *POLICY_KINDS)):
            raise RuntimeError("MANAGED_TABLES_NOT_EMPTY")
        report["relation_schema"] = schema_check(frappe)
        report["policy_schema"] = policy_schema_check(frappe)
        frappe.db.rollback()
        if args.phase == "test":
            before = native_fingerprints(frappe)
            NativeManagementHTTPCases.native = frappe
            suite = unittest.defaultTestLoader.loadTestsFromTestCase(NativeManagementHTTPCases)
            names = [test.id().rsplit(".", 1)[1] for test in suite]
            result = unittest.TextTestRunner(verbosity=2).run(suite)
            # Every WSGI request destroys its local DB; obtain a clean CLI context.
            frappe.init(site=SITE, sites_path=".", force=True)
            frappe.connect()
            frappe.set_user("Administrator")
            report["tests_run"] = result.testsRun
            report["test_names"] = names
            report["test_status"] = "PASS" if result.wasSuccessful() else "FAIL"
            report["native_preservation"] = "PASS" if native_fingerprints(frappe) == before else "FAIL"
            report["final_native_counts"] = preflight(frappe)["native_counts"]
            report["final_managed_counts"] = {kind: frappe.db.count(kind) for kind in (*KINDS, *POLICY_KINDS)}
            report["tables_empty"] = not any(report["final_managed_counts"].values())
            report["real_native_password_session"] = True
            report["administrator_http_no_policy"] = "NOT_RUN: no Administrator password use/change or fabricated session."
            report["fault_injection"] = "Request-limited synthetic hooks; no claim of real network loss."
            report["limits"] = "No real management activation, external service request, Date qualification, business grant or full restore."
            print(json.dumps(report, ensure_ascii=False, default=str))
            if not result.wasSuccessful() or not report["tables_empty"] or report["native_preservation"] != "PASS":
                raise SystemExit(1)
        else:
            print(json.dumps(report, ensure_ascii=False, default=str))
    finally:
        if getattr(frappe.local, "db", None):
            frappe.db.rollback()
        frappe.destroy()


if __name__ == "__main__":
    main()
