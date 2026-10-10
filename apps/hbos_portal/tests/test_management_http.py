"""Synthetic request/commit boundaries; no Site, session, SQL or network I/O."""
from collections import deque
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch
from uuid import uuid4

from hbos_portal.authorization.errors import ContractError
from hbos_portal.organization.management_storage import PinnedPolicyApprovalVerifier
from hbos_portal.organization.management_http import (
    COMMANDS, MAX_BODY, PREFIX, ManagedHTTPApplication, ManagedHTTPBinding,
    _CommitGate, _RequestAborted, _RequestScope, _request_scope, _validate_request, execute_request,
)
from hbos_portal.organization.relation_service import RelationCommandResult


SITE = "synthetic-site"
ORIGIN = "https://synthetic-site.invalid"
DB_HASH = hashlib.sha256(b"synthetic-db").hexdigest()
ACTOR = "synthetic-manager@example.invalid"
SID = "synthetic-cookie-session"
CSRF = "synthetic-native-csrf"
NOW = datetime(2026, 10, 10, tzinfo=timezone.utc)


class FakeCallbackManager:
    def __init__(self):
        self._callbacks = deque()
        self._functions = self._callbacks  # Native Frappe CallbackManager ABI.

    def add(self, callback):
        self._callbacks.append(callback)

    def run(self):
        while self._callbacks:
            self._callbacks.popleft()()

    def reset(self):
        self._callbacks.clear()


class FakeDB:
    """Records ordering and errors without implementing SQL transaction semantics."""
    def __init__(self, events):
        self.events = events
        self.before_commit = FakeCallbackManager()
        self.after_commit = FakeCallbackManager()
        self.before_rollback = FakeCallbackManager()
        self.after_rollback = FakeCallbackManager()
        self.committed = False
        self.closed = False
        self.commit_error = None
        self.rollback_error = None
        self.sql_calls = []
        self.transaction_writes = 0

    def commit(self):
        if self.closed:
            raise AssertionError("closed connection cannot commit")
        self.before_commit.run()
        self.events.append("sql-commit")
        if self.commit_error is not None:
            raise self.commit_error
        self.committed = True
        self.transaction_writes = 0
        self.after_commit.run()

    def rollback(self, **kwargs):
        self.events.append(("rollback", kwargs))
        if self.rollback_error is not None:
            raise self.rollback_error
        self.before_commit.reset()
        self.after_commit.reset()
        self.before_rollback.run()
        self.after_rollback.run()

    def sql(self, query, values=None, **kwargs):
        if self.closed:
            raise AssertionError("closed connection cannot query")
        self.sql_calls.append((query, values, kwargs))
        return [("synthetic-db", "REPEATABLE-READ")]

    def close(self):
        self.events.append("connection-closed")
        self.closed = True


class DynamicDBProxy:
    """Minimal request-local proxy: accessing it after destroy is an error."""
    def __init__(self, native):
        object.__setattr__(self, "_native", native)

    def _actual(self):
        try:
            return self._native.local.db
        except AttributeError:
            raise RuntimeError("request-local database proxy is unbound") from None

    def __getattr__(self, name):
        return getattr(self._actual(), name)

    def __setattr__(self, name, value):
        setattr(self._actual(), name, value)


class FakeRepository:
    def __init__(self, events):
        self.events = events
        self.depth = 0

    @contextmanager
    def transaction(self):
        self.events.append("root-begin")
        self.depth += 1
        try:
            yield
        finally:
            self.depth -= 1
            self.events.append("root-end")

    def lock_writer(self):
        if self.depth != 1:
            raise AssertionError("commit proof requires a transaction")
        self.events.append("root-lock")


class FakeRequest:
    def __init__(self, payload=None, *, raw=None):
        self.method = "POST"
        self.scheme = "https"
        self.host = "synthetic-site.invalid"
        self.mimetype = "application/json"
        self.content_type = "application/json"
        self.is_json = True
        self.path = PREFIX + "create_position"
        self.args = {}
        self.after_response = FakeCallbackManager()
        self.headers = {"Origin": ORIGIN, "X-Frappe-CSRF-Token": CSRF}
        self.cookies = {"sid": SID}
        self._data = json.dumps(payload or {}, ensure_ascii=False).encode() if raw is None else raw
        self.content_length = len(self._data)

    def get_data(self, **kwargs):
        return self._data

    def get_json(self, **kwargs):
        return json.loads(self._data)


def fake_native(request=None):
    events = []
    session = SimpleNamespace(user=ACTOR, sid=SID, data={"csrf_token": CSRF})
    request = request or FakeRequest()
    database = FakeDB(events)
    return SimpleNamespace(db=database, events=events, session=session, conf={},
        local=SimpleNamespace(site=SITE, request=request, session=session, form_dict={},
            response={}, response_headers={}, flags=SimpleNamespace(), db=database), flags=SimpleNamespace(), request=request,
        destroy=lambda: events.append("request-destroyed"), PermissionError=RuntimeError)


class FakeNativeSession:
    """Slot-bound native-style method which may perform its own one commit."""
    __slots__ = ("native", "user", "should_commit", "double_commit", "calls")

    def __init__(self, native):
        self.native = native
        self.user = ACTOR
        self.should_commit = True
        self.double_commit = False
        self.calls = 0

    def update(self):
        self.calls += 1
        if not self.should_commit:
            return False
        self.native.events.append("native-session-write")
        self.native.db.transaction_writes += 1
        self.native.db.commit()
        if self.double_commit:
            self.native.db.commit()
        return True


def position_request(**changes):
    payload = dict(payload=dict(title="合成岗位", company="COMPANY-A", department="DEPT-A", designation=None,
        status="active"), idempotency_key=str(uuid4()), expected_revision=0, reason="合成 HTTP 验收")
    payload.update(changes)
    return payload


def enabled_binding(**changes):
    options = dict(site_id=SITE, database_sha256=DB_HASH, origin=ORIGIN,
                   approval_verifier=PinnedPolicyApprovalVerifier(), clock=lambda: NOW, enabled=True)
    options.update(changes)
    return ManagedHTTPBinding(**options)


class RequestBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.payload = position_request()
        self.native = fake_native(FakeRequest(self.payload))
        self.scope = _RequestScope(enabled_binding(), "create_position")

    def validate(self, command="create_position"):
        return _validate_request(self.native, self.scope, command)

    def assert_code(self, code, action=None):
        with self.assertRaises(ContractError) as caught:
            (action or self.validate)()
        self.assertEqual(caught.exception.code, code)
        self.assertNotIn(CSRF, str(caught.exception))
        self.assertNotIn(SID, str(caught.exception))
        self.assertFalse(self.native.db.committed)
        self.assertEqual(self.native.db.sql_calls, [])

    def test_exact_cookie_authenticated_json_parses_without_database_access(self):
        self.assertEqual(self.validate(), self.payload)
        self.assertEqual(self.native.db.sql_calls, [])
        self.assertFalse(self.native.db.committed)

    def test_binding_is_default_closed_and_requires_exact_server_configuration(self):
        for change in ({"enabled": False}, {"enabled": 1}, {"site_id": "other-site"},
                       {"database_sha256": "not-a-digest"}, {"approval_verifier": None},
                       {"clock": None}, {"origin": ORIGIN + "/path"}, {"origin": "https://u:p@site.invalid"}):
            with self.subTest(change=change):
                self.scope.binding = enabled_binding(**change)
                self.assert_code("HTTP_BINDING_REQUIRED")

    def test_guest_and_missing_native_user_are_unauthenticated(self):
        for user in ("Guest", "", None):
            with self.subTest(user=user):
                self.native.session.user = user
                self.assert_code("UNAUTHENTICATED")

    def test_cookie_must_equal_native_sid_and_token_auth_cannot_substitute(self):
        request = self.native.local.request
        for cookie in (None, "Guest", "other-session"):
            with self.subTest(cookie=cookie):
                request.cookies = {} if cookie is None else {"sid": cookie}
                self.assert_code("COOKIE_SESSION_REQUIRED")
        request.cookies = {"sid": SID}
        request.headers["Authorization"] = "token synthetic-api-key:synthetic-secret"
        self.assert_code("COOKIE_SESSION_REQUIRED")

    def test_native_csrf_token_is_required_and_not_replaced_by_body_data(self):
        request = self.native.local.request
        for token in (None, "", "stale-native-csrf"):
            with self.subTest(token=token):
                request.headers["X-Frappe-CSRF-Token"] = token
                self.assert_code("CSRF_REQUIRED")
        request.headers["X-Frappe-CSRF-Token"] = CSRF
        self.native.session.data["csrf_token"] = ""
        self.assert_code("CSRF_REQUIRED")

    def test_origin_and_transport_host_must_both_equal_configured_origin(self):
        request = self.native.local.request
        for origin in (None, "null", "https://other.invalid", ORIGIN + "/", "http://synthetic-site.invalid"):
            with self.subTest(origin=origin):
                request.headers["Origin"] = origin
                self.assert_code("INVALID_ORIGIN")
        request.headers["Origin"] = ORIGIN
        request.host = "other.invalid"
        self.assert_code("INVALID_ORIGIN")

    def test_post_and_exact_route_required_no_get_or_suffix_alias(self):
        request = self.native.local.request
        request.method = "GET"
        self.assert_code("METHOD_NOT_ALLOWED")
        request.method = "POST"
        request.path += "/"
        self.assert_code("METHOD_NOT_ALLOWED")

    def test_query_parameters_and_non_json_body_rejected(self):
        request = self.native.local.request
        request.args = {"cmd": "create_position"}
        self.assert_code("INVALID_REQUEST")
        request.args = {}
        request.is_json = False
        self.assert_code("INVALID_REQUEST")

    def test_duplicate_keys_at_any_depth_and_non_finite_json_are_invalid(self):
        request = self.native.local.request
        for raw in (b'{"payload":{},"payload":{}}',
                    b'{"payload":{"status":"active","status":"revoked"}}',
                    b'{"payload":NaN}', b'{"payload":Infinity}', b'{"payload":-Infinity}',
                    b'\xff', b'{invalid', b''):
            with self.subTest(raw=raw):
                request._data = raw
                self.assert_code("INVALID_JSON")

    def test_json_root_shape_unknown_fields_and_create_record_id_rejected(self):
        request = self.native.local.request
        for body in ([], None, "string", {**self.payload, "actor": ACTOR},
                     {**self.payload, "record_id": None}, {"payload": {}}):
            with self.subTest(body=body):
                request._data = json.dumps(body).encode()
                self.assert_code("INVALID_REQUEST")

    def test_actual_body_size_enforced_despite_declared_small_length(self):
        request = self.native.local.request
        request._data = b" " * (MAX_BODY + 1)
        request.content_length = 1
        self.assert_code("REQUEST_TOO_LARGE")
        request._data = b" " * MAX_BODY
        self.assert_code("INVALID_JSON")

    def test_update_requires_record_id_in_exact_top_level_shape(self):
        self.scope.command = "update_position"
        self.native.local.request.path = PREFIX + "update_position"
        self.assert_code("INVALID_REQUEST", lambda: self.validate("update_position"))
        self.payload.update(record_id=str(uuid4()), expected_revision=1)
        self.native.local.request._data = json.dumps(self.payload).encode()
        self.assertEqual(self.validate("update_position"), self.payload)


class CommitBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.native = fake_native()
        self.scope = _RequestScope(enabled_binding(), "create_position")
        self.repository = FakeRepository(self.native.events)
        self.proof = object()
        def recheck(service, proof):
            self.assertIs(service, self.service)
            self.assertIs(proof, self.proof)
            self.assertEqual(self.repository.depth, 1)
            self.native.events.append("final-policy-check")
        self.adapter = SimpleNamespace(recheck_pending=recheck,
            discard_pending=lambda: self.native.events.append("pending-discarded"))
        self.service = SimpleNamespace(repository=self.repository, management_adapter=self.adapter)
        self.result = RelationCommandResult(str(uuid4()), 1, 1)
        self.gate = _CommitGate(self.native, self.service, self.scope)
        self.scope.gate = self.gate
        self.gate.install()
        self.addCleanup(self.gate.restore)

    def pending(self):
        self.gate.set_pending(self.result, self.proof)

    def assert_aborted(self, code, action=None):
        with self.assertRaises(_RequestAborted):
            (action or self.native.db.commit)()
        self.assertEqual(self.scope.error.error.code, code)
        self.assertEqual(self.gate.phase, "aborted")

    def test_existing_and_added_before_hooks_run_before_final_policy_check(self):
        def hook():
            self.native.events.append("before-hook")
            self.native.db.before_commit.add(lambda: self.native.events.append("added-hook"))
        self.native.db.before_commit.add(hook)
        self.native.db.after_commit.add(lambda: self.native.events.append("after-hook"))
        self.pending()
        self.native.db.commit()
        self.assertEqual(self.native.events, ["before-hook", "added-hook", "root-begin", "root-lock",
            "final-policy-check", "root-end", "sql-commit", "after-hook"])
        self.assertEqual(self.gate.phase, "committed")
        self.assertTrue(self.native.db.committed)
        self.assertIs(self.gate.result, self.result)

    def test_early_commit_and_double_commit_never_reach_sql_twice(self):
        with self.assertRaises(_RequestAborted): self.native.db.commit()
        self.assertEqual(self.native.events, [])
        self.pending()
        self.native.db.commit()
        with self.assertRaises(_RequestAborted): self.native.db.commit()
        self.assertEqual(self.native.events.count("sql-commit"), 1)

    def test_pending_requires_one_nonempty_proof(self):
        with self.assertRaises(ContractError) as caught: self.gate.set_pending(self.result, None)
        self.assertEqual(caught.exception.code, "PENDING_PROOF_REQUIRED")
        self.pending()
        with self.assertRaises(ContractError) as caught: self.gate.set_pending(self.result, self.proof)
        self.assertEqual(caught.exception.code, "PENDING_PROOF_REQUIRED")

    def test_recursive_before_commit_is_rejected_without_sql_commit(self):
        self.native.db.before_commit.add(lambda: self.native.db.commit())
        self.pending()
        self.assert_aborted("SOURCE_UNAVAILABLE")
        self.assertNotIn("sql-commit", self.native.events)
        self.assertIn(("rollback", {}), self.native.events)

    def test_known_final_policy_rejection_rolls_back_whole_transaction(self):
        def reject(*args): raise ContractError("NO_MATCHING_POLICY", "management")
        self.adapter.recheck_pending = reject
        self.native.db.after_commit.add(lambda: self.fail("denied write cannot run after_commit"))
        self.pending()
        self.assert_aborted("FORBIDDEN")
        self.assertIn(("rollback", {}), self.native.events)
        self.assertNotIn("sql-commit", self.native.events)
        self.assertFalse(self.gate.poisoned)
        self.assertFalse(self.scope.error.error.retryable)

    def test_before_hook_domain_rejection_runs_before_recheck_and_rolls_back(self):
        def reject(): raise ContractError("PENDING_FACT_CHANGED", "synthetic")
        self.native.db.before_commit.add(reject)
        self.pending()
        self.assert_aborted("CONFLICT_RETRY_REQUIRED")
        self.assertNotIn("final-policy-check", self.native.events)
        self.assertNotIn("sql-commit", self.native.events)
        self.assertIn(("rollback", {}), self.native.events)

    def test_database_replacement_cannot_commit_against_a_different_connection(self):
        original = self.native.db
        self.native.db = FakeDB(self.native.events)
        self.native.local.db = self.native.db
        self.pending()
        self.assert_aborted("SOURCE_UNAVAILABLE", action=original.commit)
        self.assertNotIn("sql-commit", self.native.events)

    def test_sql_commit_failure_is_unknown_and_terminal_for_remaining_request(self):
        self.native.db.commit_error = RuntimeError("synthetic uncertain SQL COMMIT")
        self.pending()
        self.assert_aborted("SAVE_RESULT_UNKNOWN")
        self.assertTrue(self.gate.poisoned)
        self.assertTrue(self.native.db.closed)
        with self.assertRaises(_RequestAborted): self.native.db.sql("SELECT 1")
        with self.assertRaises(_RequestAborted): self.native.db.commit()
        self.assertEqual(self.native.db.sql_calls, [])
        self.assertTrue(self.scope.error.error.retryable)

    def test_after_commit_failure_does_not_claim_that_persisted_facts_rolled_back(self):
        def fail(): raise RuntimeError("synthetic after_commit failure")
        self.native.db.after_commit.add(fail)
        self.pending()
        self.assert_aborted("SAVE_RESULT_UNKNOWN")
        self.assertTrue(self.native.db.committed)
        self.assertTrue(self.gate.poisoned)
        self.assertTrue(self.native.db.closed)

    def test_rollback_failure_poisoning_blocks_sql_and_commit(self):
        self.native.db.rollback_error = RuntimeError("synthetic rollback failure")
        self.pending()
        self.assert_aborted("SOURCE_UNAVAILABLE", action=lambda: self.gate.abort(ContractError("NO_MATCHING_POLICY", "management")))
        self.assertTrue(self.gate.poisoned)
        self.assertTrue(self.native.db.closed)
        with self.assertRaises(_RequestAborted): self.native.db.sql("SELECT 1")
        with self.assertRaises(_RequestAborted): self.native.db.commit()
        self.assertNotIn("sql-commit", self.native.events)

    def test_abort_discards_commit_hooks_but_preserves_native_rollback_watchers(self):
        for name in ("before_commit", "after_commit"):
            getattr(self.native.db, name).add(lambda: self.fail("aborted callback must be discarded"))
        self.native.db.before_rollback.add(lambda: self.native.events.append("before-rollback"))
        self.native.db.after_rollback.add(lambda: self.native.events.append("after-rollback"))
        self.gate.abort(ContractError("NO_MATCHING_POLICY", "management"))
        self.assertEqual(self.native.events, ["pending-discarded", ("rollback", {}), "before-rollback", "after-rollback"])
        self.assertEqual(self.gate.phase, "aborted")

    def test_noop_native_commit_never_confirms_persisted_success(self):
        self.gate.original_commit = lambda *args, **kwargs: None
        self.pending()
        self.assert_aborted("FORBIDDEN")
        self.assertFalse(self.native.db.committed)
        self.assertNotIn("final-policy-check", self.native.events)
        self.assertNotIn("sql-commit", self.native.events)
        self.assertIn(("rollback", {}), self.native.events)
        self.assertFalse(self.gate.facts_committed)

    def test_abort_after_fact_commit_reports_unknown_even_for_known_domain_error(self):
        self.pending()
        self.native.db.commit()
        self.gate.abort(ContractError("MULTIPLE_COMMANDS", "request"))
        self.assertEqual(self.scope.error.error.code, "SAVE_RESULT_UNKNOWN")
        self.assertTrue(self.native.db.committed)
        self.assertTrue(self.gate.poisoned)
        self.assertTrue(self.native.db.closed)

    def test_validation_gate_without_service_can_abort_and_poison_failed_rollback(self):
        for rollback_fails in (False, True):
            with self.subTest(rollback_fails=rollback_fails):
                self.gate.restore()
                native = fake_native()
                scope = _RequestScope(enabled_binding(), "create_position")
                gate = _CommitGate(native, None, scope)
                gate.install()
                try:
                    if rollback_fails:
                        native.db.rollback_error = RuntimeError("synthetic early rollback error")
                        with self.assertRaises(_RequestAborted):
                            gate.abort(ContractError("INVALID_JSON", "request"))
                        self.assertEqual(scope.error.error.code, "SOURCE_UNAVAILABLE")
                        self.assertTrue(gate.poisoned)
                        with self.assertRaises(_RequestAborted): native.db.sql("SELECT 1")
                    else:
                        gate.abort(ContractError("INVALID_JSON", "request"))
                        self.assertEqual(scope.error.error.code, "INVALID_REQUEST")
                    self.assertFalse(native.db.committed)
                    self.assertIn(("rollback", {}), native.events)
                finally:
                    gate.restore()


class SessionTailBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.native = fake_native()
        self.session = FakeNativeSession(self.native)
        self.native.local.session_obj = self.session
        self.scope = _RequestScope(enabled_binding(), "create_position")
        repository = FakeRepository(self.native.events)
        adapter = SimpleNamespace(recheck_pending=lambda *args: self.native.events.append("final-policy-check"),
            discard_pending=lambda: self.native.events.append("pending-discarded"))
        service = SimpleNamespace(repository=repository, management_adapter=adapter)
        self.gate = _CommitGate(self.native, service, self.scope)
        self.gate.install()
        self.addCleanup(self.gate.restore)
        self.gate.set_pending(RelationCommandResult(str(uuid4()), 1, 1), object())
        self.native.db.commit()

    def queued_tail(self):
        self.native.local.request.after_response.add(self.session.update)
        self.gate.prepare_session_tail()

    def test_exact_bound_slot_session_refresh_may_commit_once_after_fact_commit(self):
        with self.assertRaises(AttributeError): self.session.update = lambda: None
        self.queued_tail()
        self.native.local.request.after_response.run()
        self.assertEqual(self.session.calls, 1)
        self.assertEqual(self.native.events.count("sql-commit"), 2)
        self.assertEqual(self.native.events.count("final-policy-check"), 1)
        self.assertTrue(self.gate.tail_started)
        self.assertTrue(self.gate.tail_commit_used)
        self.assertEqual(self.gate.phase, "committed")
        self.assertEqual(self.native.db.transaction_writes, 0)
        with self.assertRaises(_RequestAborted): self.native.db.commit()

    def test_false_native_update_does_not_commit_and_does_not_grant_later_capability(self):
        self.session.should_commit = False
        self.queued_tail()
        self.native.local.request.after_response.run()
        self.assertEqual(self.session.calls, 1)
        self.assertFalse(self.gate.tail_commit_used)
        self.assertEqual(self.native.events.count("sql-commit"), 1)
        with self.assertRaises(_RequestAborted): self.native.db.commit()

    def test_arbitrary_after_response_callback_never_receives_session_capability(self):
        self.native.local.request.after_response.add(lambda: self.session.update())
        self.gate.prepare_session_tail()
        with self.assertRaises(_RequestAborted): self.native.local.request.after_response.run()
        self.assertFalse(self.gate.tail_started)
        self.assertEqual(self.native.events.count("sql-commit"), 1)

    def test_third_commit_from_session_update_is_refused(self):
        self.session.double_commit = True
        self.queued_tail()
        with self.assertRaises(_RequestAborted): self.native.local.request.after_response.run()
        self.assertEqual(self.native.events.count("sql-commit"), 2)
        self.assertTrue(self.gate.tail_commit_used)

    def test_unrelated_callback_after_native_refresh_cannot_reuse_commit_capability(self):
        self.queued_tail()
        self.native.local.request.after_response.add(lambda: self.native.db.commit())
        with self.assertRaises(_RequestAborted): self.native.local.request.after_response.run()
        self.assertEqual(self.session.calls, 1)
        self.assertEqual(self.native.events.count("sql-commit"), 2)

    def test_preexisting_writes_or_queued_commit_hooks_prevent_session_refresh(self):
        for blocker in ("writes", "before-hook", "after-hook"):
            with self.subTest(blocker=blocker):
                self.setUp()
                self.queued_tail()
                if blocker == "writes": self.native.db.transaction_writes = 1
                elif blocker == "before-hook": self.native.db.before_commit.add(lambda: self.fail("must not execute"))
                else: self.native.db.after_commit.add(lambda: self.fail("must not execute"))
                with self.assertRaises(_RequestAborted): self.native.local.request.after_response.run()
                self.assertEqual(self.session.calls, 0)
                self.assertEqual(self.native.events.count("sql-commit"), 1)

    def test_changed_connection_session_state_sid_or_actor_prevents_tail(self):
        for change in ("database", "session-object", "session-state", "sid", "actor", "session-user"):
            with self.subTest(change=change):
                self.setUp()
                database = self.native.db
                self.queued_tail()
                if change == "database": self.native.local.db = FakeDB(self.native.events)
                elif change == "session-object": self.native.local.session_obj = FakeNativeSession(self.native)
                elif change == "session-state": self.native.local.session = SimpleNamespace(user=ACTOR, sid=SID)
                elif change == "sid": self.native.session.sid = "other-sid"
                elif change == "actor": self.native.session.user = "other-user"
                else: self.session.user = "other-user"
                with self.assertRaises(_RequestAborted): self.native.local.request.after_response.run()
                self.assertEqual(self.session.calls, 0)
                self.assertEqual(self.native.events.count("sql-commit"), 1)
                self.assertTrue(database.committed)

    def test_duplicate_bound_update_callback_cannot_refresh_twice(self):
        self.native.local.request.after_response.add(self.session.update)
        self.native.local.request.after_response.add(self.session.update)
        self.gate.prepare_session_tail()
        with self.assertRaises(_RequestAborted): self.native.local.request.after_response.run()
        self.assertEqual(self.session.calls, 1)
        self.assertEqual(self.native.events.count("sql-commit"), 2)

    def test_session_commit_sql_failure_is_unknown_and_poisoned(self):
        self.queued_tail()
        self.native.db.commit_error = RuntimeError("synthetic session SQL COMMIT")
        with self.assertRaises(_RequestAborted): self.native.local.request.after_response.run()
        self.assertEqual(self.scope.error.error.code, "SAVE_RESULT_UNKNOWN")
        self.assertTrue(self.gate.facts_committed)
        self.assertTrue(self.gate.poisoned)
        self.assertTrue(self.native.db.closed)


class WSGIBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.native = fake_native()
        self.capture = []
        self.module_patch = patch.dict(sys.modules, {"frappe": self.native})
        self.module_patch.start()
        self.addCleanup(self.module_patch.stop)

    def start_response(self, status, headers, exc_info=None):
        self.capture.append((status, headers))

    def managed_application(self, *, commit=True, rejection=None, sql_error=None, after_error=None,
                            close_error=None, status="200 OK"):
        native = self.native
        repository = FakeRepository(native.events)
        def recheck(service, proof):
            native.events.append("final-policy-check")
            if rejection is not None:
                raise rejection
        adapter = SimpleNamespace(recheck_pending=recheck,
            discard_pending=lambda: native.events.append("pending-discarded"))
        service = SimpleNamespace(repository=repository, management_adapter=adapter)
        result = RelationCommandResult(str(uuid4()), 1, 1)
        body = b'{"message":{"ok":true,"data":{"save_status":"committed"}}}'
        class ResponseIterator:
            def __iter__(self):
                return iter([body])
            def close(self):
                native.events.append("iterator-closed")
                if close_error is not None:
                    raise close_error
        def application(environ, start):
            scope = _request_scope.get()
            gate = _CommitGate(native, service, scope)
            scope.gate = gate
            gate.install()
            gate.set_pending(result, object())
            start(status, [("Content-Type", "application/json"), ("Cache-Control", "public, max-age=500")])
            native.db.commit_error = sql_error
            if after_error is not None:
                def fail(): raise after_error
                native.db.after_commit.add(fail)
            if commit:
                try:
                    native.db.commit()
                except _RequestAborted:
                    pass  # A framework handler can render a previously staged response.
            return ResponseIterator()
        return application

    def call_managed(self, application, *, command="create_position", binding=None):
        wrapper = ManagedHTTPApplication(application, binding=binding or enabled_binding())
        chunks = wrapper({"PATH_INFO": PREFIX + command}, self.start_response)
        return json.loads(b"".join(chunks))

    def test_nonmanaged_and_suffix_routes_are_forwarded_unchanged(self):
        for path in ("/api/method/frappe.auth.get_logged_user", PREFIX + "unknown", PREFIX + "create_position/"):
            with self.subTest(path=path):
                chunks = [b"ordinary"]
                def application(environ, start):
                    start("200 OK", [("X-Synthetic", "pass")])
                    return chunks
                wrapper = ManagedHTTPApplication(application)
                self.assertIs(wrapper({"PATH_INFO": path}, self.start_response), chunks)
        self.assertNotIn("request-destroyed", self.native.events)

    def test_exact_managed_route_cannot_release_success_without_commit_capability(self):
        def application(environ, start):
            start("200 OK", [("Content-Type", "application/json")])
            return [b'{"message":{"ok":true}}']
        wrapper = ManagedHTTPApplication(application)
        for command in COMMANDS:
            with self.subTest(command=command):
                body = b"".join(wrapper({"PATH_INFO": PREFIX + command}, self.start_response))
                self.assertNotEqual(self.capture[-1][0], "200 OK")
                self.assertFalse(json.loads(body)["message"]["ok"])
                self.assertIsNone(_request_scope.get())

    def test_success_response_is_buffered_until_actual_commit_and_closes_iterator(self):
        def start(status, headers, exc_info=None):
            self.assertTrue(self.native.db.committed)
            self.assertIn("iterator-closed", self.native.events)
            self.start_response(status, headers, exc_info)
        wrapper = ManagedHTTPApplication(self.managed_application(), enabled_binding())
        payload = json.loads(b"".join(wrapper({"PATH_INFO": PREFIX + "create_position"}, start)))
        self.assertTrue(payload["message"]["ok"])
        self.assertEqual(self.capture[-1][0], "200 OK")
        cache = [value for key, value in self.capture[-1][1] if key.lower() == "cache-control"]
        self.assertEqual(cache, ["private, no-store, max-age=0"])
        self.assertEqual(self.native.events.count("iterator-closed"), 1)
        self.assertIn("request-destroyed", self.native.events)
        self.assertIsNone(_request_scope.get())

    def test_pending_response_without_core_commit_is_rejected_and_rolled_back(self):
        payload = self.call_managed(self.managed_application(commit=False))
        self.assertFalse(payload["message"]["ok"])
        self.assertFalse(self.native.db.committed)
        self.assertIn(("rollback", {}), self.native.events)
        self.assertNotEqual(self.capture[-1][0], "200 OK")

    def test_final_policy_denial_replaces_staged_success_response(self):
        payload = self.call_managed(self.managed_application(rejection=ContractError("NO_MATCHING_POLICY", "management")))
        self.assertFalse(payload["message"]["ok"])
        self.assertEqual(payload["message"]["error"]["code"], "FORBIDDEN")
        self.assertFalse(self.native.db.committed)
        self.assertNotIn("sql-commit", self.native.events)
        self.assertIn("iterator-closed", self.native.events)

    def test_uncertain_sql_result_replaces_staged_success_with_same_key_recheck_message(self):
        payload = self.call_managed(self.managed_application(sql_error=RuntimeError("synthetic SQL failure")))
        self.assertFalse(payload["message"]["ok"])
        self.assertEqual(payload["message"]["error"]["code"], "SAVE_RESULT_UNKNOWN")
        self.assertEqual(self.capture[-1][0], "409 Conflict")
        self.assertTrue(self.native.db.closed)

    def test_after_commit_and_response_cleanup_errors_both_report_unknown_result(self):
        for failure in ("after-commit", "iterator-close"):
            with self.subTest(failure=failure):
                self.native = fake_native()
                with patch.dict(sys.modules, {"frappe": self.native}):
                    options = dict(after_error=RuntimeError("synthetic hook")) if failure == "after-commit" else dict(close_error=RuntimeError("synthetic iterator"))
                    payload = self.call_managed(self.managed_application(**options))
                self.assertEqual(payload["message"]["error"]["code"], "SAVE_RESULT_UNKNOWN")
                self.assertTrue(self.native.db.committed)
                self.assertTrue(self.native.db.closed)
                self.assertIsNone(_request_scope.get())

    def test_committed_non_success_core_response_is_conservatively_unknown(self):
        payload = self.call_managed(self.managed_application(status="500 Internal Server Error"))
        self.assertEqual(payload["message"]["error"]["code"], "SAVE_RESULT_UNKNOWN")
        self.assertTrue(self.native.db.committed)

    def test_outer_request_scope_restored_after_nested_wsgi_wrapper(self):
        outer = _RequestScope(None, "synthetic-outer")
        token = _request_scope.set(outer)
        try:
            self.call_managed(self.managed_application())
            self.assertIs(_request_scope.get(), outer)
        finally:
            _request_scope.reset(token)

    def test_native_rpc_without_wrapper_capability_returns_default_closed_error(self):
        self.assertIsNone(_request_scope.get())
        payload = execute_request("create_position")
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "NOT_SUPPORTED")
        self.assertFalse(self.native.db.committed)
        self.assertIn(("rollback", {}), self.native.events)
        self.assertEqual(self.native.db.sql_calls, [])

    def test_destroyed_native_db_proxy_does_not_break_terminal_gate_restore(self):
        database = self.native.local.db
        self.native.db = DynamicDBProxy(self.native)
        def destroy():
            self.native.events.append("request-destroyed")
            del self.native.local.db
        self.native.destroy = destroy
        application = self.managed_application()
        def native_closing_application(environ, start):
            iterator = application(environ, start)
            class NativeClosingIterator:
                def __iter__(self): return iter(iterator)
                def close(self):
                    iterator.close()
                    destroy()  # Native ClosingIterator destroys before wrapper finally.
            return NativeClosingIterator()
        payload = self.call_managed(native_closing_application)
        self.assertTrue(payload["message"]["ok"])
        self.assertTrue(database.committed)
        self.assertEqual(self.capture[-1][0], "200 OK")
        self.assertEqual(self.native.events.count("request-destroyed"), 1)
        self.assertIs(database.commit.__self__, database)
        self.assertIs(database.commit.__func__, FakeDB.commit)
        with self.assertRaisesRegex(RuntimeError, "proxy is unbound"):
            self.native.db.commit()
        self.assertIsNone(_request_scope.get())

    def test_api_reentry_after_fact_commit_cannot_release_staged_success(self):
        application = self.managed_application()
        def reenter(environ, start):
            iterator = application(environ, start)
            with self.assertRaises(self.native.PermissionError):
                execute_request("create_position")
            return iterator
        payload = self.call_managed(reenter)
        self.assertFalse(payload["message"]["ok"])
        self.assertEqual(payload["message"]["error"]["code"], "SAVE_RESULT_UNKNOWN")
        self.assertTrue(self.native.db.committed)
        self.assertTrue(self.native.db.closed)
        self.assertEqual(self.native.events.count("sql-commit"), 1)
        self.assertEqual(self.capture[-1][0], "409 Conflict")

    def test_early_request_validation_abort_cleans_without_service_or_releasing_body(self):
        for rollback_fails in (False, True):
            with self.subTest(rollback_fails=rollback_fails):
                self.native = fake_native(FakeRequest(raw=b'{"payload":'))
                self.native.local.form_dict = {"cmd": "create_position", "synthetic-sensitive": "body"}
                if rollback_fails:
                    self.native.db.rollback_error = RuntimeError("synthetic validation rollback")
                def application(environ, start):
                    try:
                        execute_request("create_position")
                    except RuntimeError:
                        start("200 OK", [("Content-Type", "application/json")])
                    return [b'{"message":{"ok":true}}']
                with patch.dict(sys.modules, {"frappe": self.native}):
                    payload = self.call_managed(application)
                self.assertFalse(payload["message"]["ok"])
                self.assertEqual(payload["message"]["error"]["code"],
                    "SOURCE_UNAVAILABLE" if rollback_fails else "INVALID_REQUEST")
                self.assertEqual(self.native.local.form_dict, {})
                self.assertFalse(self.native.db.committed)
                self.assertIn(("rollback", {}), self.native.events)
                self.assertTrue(self.native.db.closed)
                self.assertIn("request-destroyed", self.native.events)
                self.assertIsNone(_request_scope.get())

    def test_predispatch_native_errors_are_enveloped_without_raw_trace_or_personal_data(self):
        sensitive = "SYNTHETIC-EMP-PHONE-13800000000"
        for original_status, public_status, code in (
                ("400 Bad Request", "400 Bad Request", "INVALID_REQUEST"),
                ("401 Unauthorized", "401 Unauthorized", "UNAUTHENTICATED"),
                ("403 Forbidden", "403 Forbidden", "FORBIDDEN"),
                ("405 Method Not Allowed", "403 Forbidden", "FORBIDDEN"),
                ("500 Internal Server Error", "503 Service Unavailable", "SOURCE_UNAVAILABLE")):
            with self.subTest(original_status=original_status):
                raw = json.dumps({"exception": sensitive, "exc": "Traceback " + CSRF,
                    "_server_messages": SID, "user": ACTOR}).encode()
                def application(environ, start):
                    start(original_status, [("Content-Type", "application/json")])
                    return [raw]
                payload = self.call_managed(application)
                self.assertEqual(self.capture[-1][0], public_status)
                self.assertFalse(payload["message"]["ok"])
                self.assertEqual(payload["message"]["error"]["code"], code)
                self.assertTrue(payload["message"]["error"]["trace_id"])
                serialized = json.dumps(payload)
                for private in (sensitive, CSRF, SID, ACTOR, "Traceback", "_server_messages"):
                    self.assertNotIn(private, serialized)
                self.assertFalse(self.native.db.committed)
                self.assertNotIn("sql-commit", self.native.events)
                self.assertIsNone(_request_scope.get())

    def test_audit_logger_failure_cannot_turn_policy_denial_into_success(self):
        with patch("hbos_portal.organization.management_http.logging.getLogger") as logger:
            logger.return_value.warning.side_effect = RuntimeError("synthetic audit sink failure")
            payload = self.call_managed(self.managed_application(
                rejection=ContractError("NO_MATCHING_POLICY", "SYNTHETIC-PRIVATE-PERSON")))
            self.assertTrue(logger.return_value.warning.called)
            self.assertNotIn("SYNTHETIC-PRIVATE-PERSON", str(logger.return_value.warning.call_args))
        self.assertFalse(payload["message"]["ok"])
        self.assertEqual(payload["message"]["error"]["code"], "FORBIDDEN")
        self.assertEqual(self.capture[-1][0], "403 Forbidden")
        self.assertFalse(self.native.db.committed)
        self.assertNotIn("sql-commit", self.native.events)
        self.assertIn(("rollback", {}), self.native.events)
        self.assertTrue(self.native.db.closed)
        self.assertIsNone(_request_scope.get())


if __name__ == "__main__":
    unittest.main()
