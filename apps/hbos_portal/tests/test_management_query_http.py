"""Synthetic GET query and response-finalization boundaries, without a Site."""
import json
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from hbos_portal.authorization.errors import ContractError
from tests import test_management_http as write_http_fixture
from hbos_portal.organization.management_query_http import (
    QUERIES, QUERY_PREFIX, ManagedQueryHTTPApplication, _QueryScope, _ReadGate,
    _query_scope, _structure_preflight_required, _validate_query, execute_query,
)


class QueryArguments:
    """The MultiDict getlist/lists surface; duplicate values remain visible."""
    def __init__(self, pairs=()):
        self.pairs = list(pairs)

    def keys(self):
        return dict(self.pairs).keys()

    def __iter__(self):
        return iter(self.keys())

    def __len__(self):
        return len(set(key for key, _ in self.pairs))

    def getlist(self, key):
        return [value for field, value in self.pairs if field == key]

    def get(self, key, default=None):
        values = self.getlist(key)
        return default if not values else values[0]

    def __getitem__(self, key):
        values = self.getlist(key)
        if not values:
            raise KeyError(key)
        return values[0]

    def items(self, multi=False):
        return iter(self.pairs) if multi else iter((key, self[key]) for key in self)

    def lists(self):
        return iter((key, self.getlist(key)) for key in self)


def query_native(query="list_positions", args=()):
    request = write_http_fixture.FakeRequest(raw=b"")
    request.method = "GET"
    request.path = write_http_fixture.PREFIX + query
    request.args = QueryArguments(args)
    return write_http_fixture.fake_native(request)


READ_RESULT = dict(items=[], total=0, page=1, page_size=10, read_only=True,
    authorization_effect="none", runtime_verified=False, position_authorization_connected=False)


class QueryRequestTests(unittest.TestCase):
    def setUp(self):
        self.native = query_native()
        self.scope = _QueryScope(write_http_fixture.enabled_binding(), "list_positions")

    def validate(self, query="list_positions"):
        return _validate_query(self.native, self.scope, query)

    def assert_code(self, code, action=None):
        with self.assertRaises(ContractError) as caught: (action or self.validate)()
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(self.native.db.sql_calls, [])
        self.assertFalse(self.native.db.committed)

    def test_authenticated_same_origin_get_parses_decimal_page_strings(self):
        self.native.local.request.args = QueryArguments([("page", "2"), ("page_size", "50"), ("q", "合成")])
        self.assertEqual(self.validate(), {"page": 2, "page_size": 50, "q": "合成"})
        del self.native.local.request.headers["Origin"]
        self.assertEqual(self.validate()["page"], 2)  # Browsers may omit Origin on same-origin GET.

    def test_cookie_session_native_csrf_and_fixed_transport_origin_are_required(self):
        for flaw, expected in (("guest", "UNAUTHENTICATED"), ("cookie", "COOKIE_SESSION_REQUIRED"),
                               ("token-auth", "COOKIE_SESSION_REQUIRED"), ("csrf", "CSRF_REQUIRED"),
                               ("origin", "INVALID_ORIGIN"), ("null-origin", "INVALID_ORIGIN"),
                               ("host", "INVALID_ORIGIN"), ("fetch-site", "INVALID_ORIGIN")):
            with self.subTest(flaw=flaw):
                self.setUp()
                request = self.native.local.request
                if flaw == "guest": self.native.session.user = "Guest"
                elif flaw == "cookie": request.cookies = {}
                elif flaw == "token-auth": request.headers["Authorization"] = "token synthetic:key"
                elif flaw == "csrf": request.headers["X-Frappe-CSRF-Token"] = "stale"
                elif flaw == "origin": request.headers["Origin"] = "https://other.invalid"
                elif flaw == "null-origin": request.headers["Origin"] = "null"
                elif flaw == "host": request.host = "other.invalid"
                else: request.headers["Sec-Fetch-Site"] = "cross-site"
                self.assert_code(expected)

    def test_default_closed_binding_cannot_be_replaced_by_request_data(self):
        self.scope.binding = write_http_fixture.enabled_binding(enabled=False)
        self.assert_code("QUERY_BINDING_REQUIRED")

    def test_get_exact_path_and_empty_request_body_are_mandatory(self):
        request = self.native.local.request
        request.method = "POST"
        self.assert_code("METHOD_NOT_ALLOWED")
        request.method = "GET"
        request.path += "/"
        self.assert_code("METHOD_NOT_ALLOWED")
        request.path = QUERY_PREFIX + "list_positions"
        request._data = b"{}"
        self.assert_code("INVALID_REQUEST")

    def test_query_multidict_preserves_and_rejects_duplicates_and_unknowns(self):
        for pairs in (("duplicate", [("page", "1"), ("page", "2")]),
                      ("unknown", [("actor", write_http_fixture.ACTOR)]),
                      ("policy", [("policy_id", "client-policy")])):
            with self.subTest(mode=pairs[0]):
                self.native.local.request.args = QueryArguments(pairs[1])
                self.assert_code("INVALID_REQUEST")

    def test_page_strings_must_be_ascii_digits_without_sign_space_or_decimal(self):
        for value in ("+1", "-1", "1.0", " 1", "1 ", "１", "١", "1e2", "100000", ""):
            with self.subTest(value=value):
                self.native.local.request.args = QueryArguments([("page", value)])
                self.assert_code("INVALID_REQUEST")

    def test_context_has_no_parameters_and_assignment_accepts_only_person_paging(self):
        self.scope.command = "get_management_context"
        self.native.local.request.path = QUERY_PREFIX + "get_management_context"
        self.native.local.request.args = QueryArguments([("page", "1")])
        self.assert_code("INVALID_REQUEST", lambda: self.validate("get_management_context"))
        self.scope.command = "get_person_assignments"
        self.native.local.request.path = QUERY_PREFIX + "get_person_assignments"
        self.native.local.request.args = QueryArguments([("employee_id", "SYNTHETIC-EMP"), ("page_size", "1")])
        self.assertEqual(self.validate("get_person_assignments"), {"employee_id": "SYNTHETIC-EMP", "page_size": 1})


class ReadGateTests(unittest.TestCase):
    def setUp(self):
        self.native = query_native()
        self.scope = _QueryScope(write_http_fixture.enabled_binding(), "list_positions")
        self.proof = object()
        def recheck(proof):
            self.assertIs(proof, self.proof)
            self.native.events.append("fresh-query-proof")
            return dict(READ_RESULT)
        self.service = SimpleNamespace(recheck_pending=recheck,
            discard_pending=lambda: self.native.events.append("read-proof-discarded"))
        self.gate = _ReadGate(self.native, self.service, self.scope)
        self.scope.gate = self.gate
        self.gate.install()
        self.addCleanup(self.gate.restore)

    def pending(self):
        self.gate.set_pending(dict(READ_RESULT), self.proof)

    def test_queries_cannot_commit_before_or_after_staging_or_finalization(self):
        with self.assertRaises(write_http_fixture._RequestAborted): self.native.db.commit()
        self.pending()
        with self.assertRaises(write_http_fixture._RequestAborted): self.native.db.commit()
        self.native.db.rollback()  # Native GET synchronization precedes wrapper finalize.
        self.gate.finalize()
        with self.assertRaises(write_http_fixture._RequestAborted): self.native.db.commit()
        self.assertEqual(self.native.events, [("rollback", {}), "fresh-query-proof", ("rollback", {})])
        self.assertFalse(self.native.db.committed)
        self.assertFalse(self.gate.facts_committed)

    def test_final_result_mismatch_is_not_released_as_success(self):
        self.pending()
        self.service.recheck_pending = lambda proof: {**READ_RESULT, "total": 1}
        with self.assertRaises(ContractError) as caught: self.gate.finalize()
        self.assertEqual(caught.exception.code, "SOURCE_CHANGED_RETRY")
        self.assertFalse(self.native.db.committed)

    def test_query_domain_error_full_rollback_and_failed_rollback_remain_read_errors(self):
        for fails in (False, True):
            with self.subTest(rollback_fails=fails):
                self.setUp()
                self.pending()
                if fails: self.native.db.rollback_error = RuntimeError("synthetic query rollback")
                if fails:
                    with self.assertRaises(write_http_fixture._RequestAborted):
                        self.gate.abort(ContractError("NO_MATCHING_POLICY", "query"))
                    self.assertEqual(self.scope.error.error.code, "SOURCE_UNAVAILABLE")
                    with self.assertRaises(write_http_fixture._RequestAborted): self.native.db.sql("SELECT 1")
                else:
                    self.gate.abort(ContractError("NO_MATCHING_POLICY", "query"))
                    self.assertEqual(self.scope.error.error.code, "FORBIDDEN")
                self.assertNotEqual(self.scope.error.error.code, "SAVE_RESULT_UNKNOWN")
                self.assertFalse(self.native.db.committed)
                self.assertIn(("rollback", {}), self.native.events)

    def test_only_native_session_update_may_commit_metadata_after_read_release_check(self):
        self.gate.restore()
        session = write_http_fixture.FakeNativeSession(self.native)
        self.native.local.session_obj = session
        self.gate = _ReadGate(self.native, self.service, self.scope)
        self.gate.install()
        self.pending()
        self.native.db.rollback()
        self.gate.finalize()
        self.native.local.request.after_response.add(session.update)
        self.gate.prepare_session_tail()
        self.native.local.request.after_response.run()
        self.assertEqual(session.calls, 1)
        self.assertEqual(self.native.events.count("sql-commit"), 1)
        self.assertFalse(self.gate.facts_committed)
        with self.assertRaises(write_http_fixture._RequestAborted): self.native.db.commit()


class QueryWSGITests(unittest.TestCase):
    def setUp(self):
        self.native = query_native()
        self.capture = []
        self.module_patch = patch.dict(sys.modules, {"frappe": self.native})
        self.module_patch.start()
        self.addCleanup(self.module_patch.stop)

    def start(self, status, headers, exc_info=None):
        self.capture.append((status, headers))

    def call(self, application, *, query="list_positions", binding=None):
        wrapper = ManagedQueryHTTPApplication(application, binding=binding or write_http_fixture.enabled_binding())
        return json.loads(b"".join(wrapper({"PATH_INFO": QUERY_PREFIX + query}, self.start)))

    def application(self, *, rejection=None, metadata_tail=False):
        native = self.native
        def recheck(proof):
            native.events.append("fresh-query-proof")
            if rejection is not None: raise rejection
            return dict(READ_RESULT)
        service = SimpleNamespace(recheck_pending=recheck,
            discard_pending=lambda: native.events.append("read-proof-discarded"))
        if metadata_tail:
            session = write_http_fixture.FakeNativeSession(native)
            native.local.session_obj = session
            native.local.request.after_response.add(session.update)
        class ClosingIterator:
            def __iter__(self): return iter([json.dumps({"message": {"ok": True, "data": READ_RESULT}}).encode()])
            def close(self):
                native.events.append("query-iterator-closed")
                native.local.request.after_response.run()
        def application(environ, start):
            scope = _query_scope.get()
            gate = _ReadGate(native, service, scope)
            scope.gate = gate
            gate.install()
            gate.set_pending(dict(READ_RESULT), object())
            start("200 OK", [("Content-Type", "application/json"), ("Cache-Control", "public")])
            native.db.rollback()  # Native sync_database(GET) before response iterator release.
            return ClosingIterator()
        return application

    def test_success_query_is_revalidated_and_rolled_back_before_response_release(self):
        payload = self.call(self.application())
        self.assertTrue(payload["message"]["ok"])
        self.assertEqual(self.native.events[:4], [("rollback", {}), "fresh-query-proof", ("rollback", {}), "query-iterator-closed"])
        self.assertFalse(self.native.db.committed)
        self.assertEqual([value for key, value in self.capture[-1][1] if key.lower() == "cache-control"], ["private, no-store, max-age=0"])
        self.assertIsNone(_query_scope.get())

    def test_final_denial_discards_staged_rows_and_performs_full_rollback(self):
        payload = self.call(self.application(rejection=ContractError("MANAGEMENT_CHANGED_RETRY", "query")))
        self.assertFalse(payload["message"]["ok"])
        self.assertEqual(payload["message"]["error"]["code"], "CONFLICT_RETRY_REQUIRED")
        self.assertNotIn("items", canonical_payload(payload))
        self.assertFalse(self.native.db.committed)
        self.assertGreaterEqual(self.native.events.count(("rollback", {})), 2)

    def test_default_closed_short_circuit_and_native_raw_errors_never_leak_payload(self):
        for status in ("200 OK", "400 Bad Request", "401 Unauthorized", "403 Forbidden", "405 Method Not Allowed", "500 Internal Server Error"):
            with self.subTest(status=status):
                def application(environ, start):
                    start(status, [("Content-Type", "application/json")])
                    return [b'{"exception":"SYNTHETIC-EMP-PHONE-13800000000","exc":"Traceback"}']
                payload = self.call(application)
                self.assertFalse(payload["message"]["ok"])
                self.assertNotIn("13800000000", canonical_payload(payload))
                self.assertNotIn("Traceback", canonical_payload(payload))
                self.assertFalse(self.native.db.committed)

    def test_query_logging_failure_keeps_denial_and_no_commit(self):
        with patch("hbos_portal.organization.management_http.logging.getLogger") as logger:
            logger.return_value.warning.side_effect = RuntimeError("synthetic query audit failure")
            payload = self.call(self.application(rejection=ContractError("NO_MATCHING_POLICY", "query")))
        self.assertFalse(payload["message"]["ok"])
        self.assertEqual(payload["message"]["error"]["code"], "FORBIDDEN")
        self.assertFalse(self.native.db.committed)

    def test_native_session_upkeep_commit_does_not_claim_fact_write_or_grant(self):
        payload = self.call(self.application(metadata_tail=True))
        self.assertTrue(payload["message"]["ok"])
        self.assertEqual(self.native.events.count("sql-commit"), 1)
        self.assertTrue(payload["message"]["data"]["read_only"])
        self.assertEqual(payload["message"]["data"]["authorization_effect"], "none")
        self.assertNotIn("save_status", payload["message"]["data"])

    def test_query_rpc_without_trusted_wrapper_capability_remains_closed(self):
        payload = execute_query("list_positions")
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "NOT_SUPPORTED")
        self.assertFalse(self.native.db.committed)
        self.assertIn(("rollback", {}), self.native.events)

    def test_production_preflight_runs_after_request_validation_and_before_service(self):
        scope = _QueryScope(write_http_fixture.enabled_binding(), "list_positions")
        scope_token = _query_scope.set(scope)
        flag_token = _structure_preflight_required.set(True)
        self.addCleanup(_query_scope.reset, scope_token)
        self.addCleanup(_structure_preflight_required.reset, flag_token)
        service = SimpleNamespace(execute=lambda *args: dict(READ_RESULT), pending_proof=object())
        order = []
        def preflight(native, **binding):
            self.assertIs(native, self.native)
            self.assertEqual(binding, {"expected_site": scope.binding.site_id,
                "expected_database_sha256": scope.binding.database_sha256})
            order.append("preflight")
        def construct(*args):
            order.append("service")
            return service
        with patch("hbos_portal.organization.management_preflight.preflight_management_structure", side_effect=preflight), \
             patch("hbos_portal.organization.management_query_http._make_query_service", side_effect=construct):
            self.assertTrue(execute_query("list_positions")["ok"])
        self.assertEqual(order, ["preflight", "service"])
        self.assertFalse(self.native.db.committed)
        scope.gate.restore()

    def test_bad_session_cannot_probe_schema_and_bad_structure_cannot_construct_service(self):
        for bad_session in (True, False):
            with self.subTest(bad_session=bad_session):
                self.setUp()
                scope = _QueryScope(write_http_fixture.enabled_binding(), "list_positions")
                scope_token = _query_scope.set(scope)
                flag_token = _structure_preflight_required.set(True)
                if bad_session:
                    self.native.local.request.headers["X-Frappe-CSRF-Token"] = "invalid"
                try:
                    with patch("hbos_portal.organization.management_preflight.preflight_management_structure", side_effect=ContractError("STORAGE_PREFLIGHT_NOT_READY", "runtime")) as preflight, \
                         patch("hbos_portal.organization.management_query_http._make_query_service") as construct:
                        with self.assertRaises(self.native.PermissionError): execute_query("list_positions")
                        self.assertEqual(preflight.call_count, 0 if bad_session else 1)
                        construct.assert_not_called()
                    self.assertFalse(self.native.db.committed)
                    self.assertEqual(scope.error.error.code, "FORBIDDEN" if bad_session else "SOURCE_UNAVAILABLE")
                finally:
                    if scope.gate is not None: scope.gate.restore()
                    _structure_preflight_required.reset(flag_token)
                    _query_scope.reset(scope_token)

    def test_preflight_flag_is_explicit_private_boolean_and_resets_after_each_route(self):
        for invalid in (1, "true", None):
            with self.assertRaises(ValueError):
                ManagedQueryHTTPApplication(self.application(), require_structure_preflight=invalid)
        seen = []
        def application(environ, start):
            seen.append(_structure_preflight_required.get())
            start("200 OK", [])
            return [b"synthetic"]
        for required in (True, False):
            wrapper = ManagedQueryHTTPApplication(application, require_structure_preflight=required)
            wrapper({"PATH_INFO": QUERY_PREFIX + "list_positions", "require_structure_preflight": not required}, self.start)
            self.assertFalse(_structure_preflight_required.get())
            self.assertIsNone(_query_scope.get())
        self.assertEqual(seen, [True, False])

    def test_all_four_exact_query_routes_require_trusted_handler_capability(self):
        def application(environ, start):
            start("200 OK", [("Content-Type", "application/json")])
            return [b'{"message":{"ok":true}}']
        for query in QUERIES:
            with self.subTest(query=query):
                payload = self.call(application, query=query)
                self.assertFalse(payload["message"]["ok"])
                self.assertEqual(payload["message"]["error"]["code"], "NOT_SUPPORTED")
                self.assertFalse(self.native.db.committed)
                self.assertIsNone(_query_scope.get())

    def test_write_unknown_and_suffix_routes_pass_through_to_their_own_boundaries(self):
        chunks = [b"separate-boundary"]
        def application(environ, start):
            start("200 OK", [("X-Synthetic", "pass")])
            return chunks
        wrapper = ManagedQueryHTTPApplication(application)
        for query in ("create_position", "unknown_query", "list_positions/"):
            with self.subTest(query=query):
                self.assertIs(wrapper({"PATH_INFO": QUERY_PREFIX + query}, self.start), chunks)
        self.assertNotIn("request-destroyed", self.native.events)

    def test_session_metadata_commit_failure_withholds_read_data_without_fact_save_status(self):
        self.native.db.commit_error = RuntimeError("synthetic GET session SQL failure")
        payload = self.call(self.application(metadata_tail=True))
        self.assertFalse(payload["message"]["ok"])
        self.assertEqual(payload["message"]["error"]["code"], "SOURCE_UNAVAILABLE")
        self.assertNotIn("SAVE_RESULT_UNKNOWN", canonical_payload(payload))
        self.assertNotIn("items", canonical_payload(payload))
        self.assertFalse(self.native.db.committed)
        self.assertTrue(self.native.db.closed)
        self.assertIsNone(_query_scope.get())

    def test_destroyed_closed_request_error_never_rolls_back_a_lazy_reconnected_database(self):
        class LazyReconnectDB(write_http_fixture.FakeDB):
            def __init__(self, events):
                super().__init__(events)
                self.reconnects = 0
            def rollback(self, **kwargs):
                if self.closed:
                    self.reconnects += 1
                    self.closed = False
                return super().rollback(**kwargs)
        database = LazyReconnectDB(self.native.events)
        self.native.local.db = database
        self.native.db = write_http_fixture.DynamicDBProxy(self.native)
        def destroy():
            self.native.events.append("request-destroyed")
            del self.native.local.db
        self.native.destroy = destroy
        application = self.application()
        def native_closing_application(environ, start):
            inner = application(environ, start)
            class ClosingIterator:
                closed = False
                def __iter__(self): return iter(inner)
                def close(self):
                    if self.closed:
                        return
                    self.closed = True
                    inner.close()
                    database.close()
                    destroy()
                    raise RuntimeError("synthetic post-destroy cleanup failure")
            return ClosingIterator()
        payload = self.call(native_closing_application)
        self.assertFalse(payload["message"]["ok"])
        self.assertEqual(payload["message"]["error"]["code"], "SOURCE_UNAVAILABLE")
        self.assertNotIn("items", canonical_payload(payload))
        self.assertEqual(database.reconnects, 0)
        self.assertEqual(self.native.events.count(("rollback", {})), 2)
        self.assertTrue(database.closed)
        self.assertFalse(database.committed)
        self.assertIs(database.commit.__self__, database)
        self.assertIs(database.commit.__func__, write_http_fixture.FakeDB.commit)
        self.assertIs(database.sql.__self__, database)
        self.assertIs(database.sql.__func__, write_http_fixture.FakeDB.sql)
        self.assertIsNone(_query_scope.get())


def canonical_payload(payload):
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)
