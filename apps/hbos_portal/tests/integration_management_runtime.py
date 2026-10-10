"""Explicit native acceptance of the query-only opt-in runtime factory.

Run with the existing bench Python from frappe-bench/sites. Only the exact
already verified empty Preview is accepted. No new Site, schema, service,
production file, persisted runtime configuration or real management approval.
The test phase creates private temporary configuration and synthetic records,
then removes exact IDs; the preflight phase never initializes a root lock.
"""
import argparse
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from hbos_portal.authorization.errors import ContractError
from hbos_portal.organization import management_preflight, management_wsgi
from hbos_portal.organization.management_policy import management_policy_digest
from hbos_portal.organization.native_read_boundary import PROTECTED_DOCTYPES
from hbos_portal.organization.storage_schema import LOCK_KEY

if __package__:
    from .integration_management_http import ORIGIN, find_field
    from .integration_management_queries import NativeManagementQueryCases, QUERIES, QUERY_PREFIX, READ_OPERATIONS
    from .integration_management_relations import NOW, POLICY_KINDS
    from .integration_management_storage import policy_presence
    from .integration_organization_storage import SITE, DB_HASH, KINDS, check_target, native_fingerprints, preflight
else:
    from integration_management_http import ORIGIN, find_field
    from integration_management_queries import NativeManagementQueryCases, QUERIES, QUERY_PREFIX, READ_OPERATIONS
    from integration_management_relations import NOW, POLICY_KINDS
    from integration_management_storage import policy_presence
    from integration_organization_storage import SITE, DB_HASH, KINDS, check_target, native_fingerprints, preflight


def loaded_protection_hooks(native):
    """Observe the actually loaded hooks, without clear_cache/reload/refresh."""
    before = native.get_hooks("before_request")
    permission = native.get_hooks("has_permission")
    condition = native.get_hooks("permission_query_conditions")
    if not isinstance(permission, dict) or not isinstance(condition, dict):
        raise RuntimeError("NATIVE_PROTECTION_HOOKS_NOT_LOADED")

    def paths(value):
        return (value,) if isinstance(value, str) else tuple(value or ())

    prefix = "hbos_portal.organization.native_read_boundary."
    before_ok = prefix + "before_request" in paths(before)
    permission_ok = all(prefix + "deny_native_permission" in paths(permission.get(kind)) for kind in PROTECTED_DOCTYPES)
    condition_ok = all(prefix + "deny_native_query" in paths(condition.get(kind)) for kind in PROTECTED_DOCTYPES)
    if not (before_ok and permission_ok and condition_ok):
        raise RuntimeError("NATIVE_PROTECTION_HOOKS_NOT_LOADED")
    return dict(before_request=True, has_permission_doctypes=8, permission_query_doctypes=8,
                refresh_performed=False)


@contextmanager
def select_trace(native):
    """Observe real structural SQL only, without recording substituted values."""
    calls = []
    database_class = type(native.local.db)
    original = database_class.sql

    def sql(database, statement, *args, **kwargs):
        if not isinstance(statement, str) or not statement.startswith("SELECT "):
            raise AssertionError("structure preflight must issue fixed SELECT only")
        if "FOR UPDATE" in statement.upper():
            raise AssertionError("structure preflight must not acquire row locks")
        calls.append(statement)
        return original(database, statement, *args, **kwargs)

    with patch.object(database_class, "sql", sql):
        yield calls


def assert_structure_trace(case, calls):
    case.assertEqual(len(calls), 10)
    case.assertEqual(calls[0], "SELECT DATABASE(), @@tx_isolation")
    case.assertTrue(all(statement.startswith("SELECT ") for statement in calls))
    case.assertTrue(all("FOR UPDATE" not in statement.upper() for statement in calls))
    # No personnel/policy facts are loaded by the structural diagnostic.
    case.assertFalse(any("FROM `tabUser`" in statement or "FROM `tabEmployee`" in statement
        or "FROM `tabHBOS Organization Management Policy`" in statement for statement in calls))


class NativeManagementRuntimeCases(unittest.TestCase):
    """Composition avoids inheriting or rerunning the 16 query scenarios."""
    native = None
    synthetic_users = set()
    synthetic_employees = set()
    session_ids = set()
    private_roots = set()
    unrelated_log_ids = {"Activity Log": set(), "Error Log": set()}

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="hbos-management-runtime-")
        self.root = Path(self.directory.name).resolve(strict=True)
        type(self).private_roots.add(str(self.root))
        self.addCleanup(self.cleanup_private_configuration)
        os.chmod(self.root, 0o700)
        self.path = self.root / "synthetic-management-query.json"
        self.query = NativeManagementQueryCases()
        self.query.native = self.native
        self.addCleanup(self.cleanup)
        self.query.setUp()
        self.query._cleanups.clear()  # This test owns the exact composed cleanup.
        self.fixture = self.query.fixture
        self.record_fixture_ids()
        self.hook_report = loaded_protection_hooks(self.native)
        self.extend_read_policy_for_real_utc()
        pins = [pin for pin in self.fixture.pins if pin.policy_id == self.fixture.policy.policy_id
                and pin.revision == self.fixture.policy.revision
                and pin.authority_generation == self.fixture.policy.authority_generation]
        self.assertEqual(len(pins), 1)  # Never export historical pins with duplicate policy IDs.
        self.configuration = dict(schema_version=1, enabled=True, sites=[dict(
            site_id=SITE, database_sha256=DB_HASH, origin=ORIGIN, enabled=True,
            approval_pins=[asdict(pins[0])])])
        self.write_configuration()
        self.application = management_wsgi.create_application(configuration_path=str(self.path))
        self.client = self.query.query_client(self.application)

    def extend_read_policy_for_real_utc(self):
        """Actual approved synthetic policy; no runtime clock injection."""
        now = datetime.now(timezone.utc)
        earlier, later = min(now, NOW), max(now, NOW)
        old = self.fixture.policy
        rules = tuple(replace(rule, operation_ids=tuple(sorted(READ_OPERATIONS)),
                              assignment_until_limit_utc=None) for rule in old.rules)
        policy = replace(old, revision=old.revision + 1, authority_generation=old.authority_generation + 1,
            valid_from_utc=earlier - timedelta(days=1), valid_until_utc=later + timedelta(days=365),
            rules=rules, approval=None)
        approval = replace(old.approval, approved_at_utc=earlier - timedelta(days=1),
            approved_revision=policy.revision, approved_authority_generation=policy.authority_generation,
            content_digest=management_policy_digest(policy))
        policy = replace(policy, approval=approval)
        f = self.query.http.reconnect()
        self.fixture.install(policy, expected=old.revision)
        f.db.commit()
        self.fixture.policy = policy
        self.assertLess(policy.valid_from_utc, now)
        self.assertGreater(policy.valid_until_utc, now)

    def record_fixture_ids(self):
        http = getattr(self.query, "http", None)
        fixture = getattr(http, "fixture", None)
        for field in ("manager", "beneficiary", "approver"):
            value = getattr(fixture, field, None)
            if value:
                type(self).synthetic_users.add(value)
        for field in ("employee", "manager_employee"):
            value = getattr(fixture, field, None)
            if value:
                type(self).synthetic_employees.add(value)
        type(self).synthetic_users.update(getattr(self.query, "extra_users", ()))
        type(self).synthetic_employees.update(getattr(self.query, "extra_employees", ()))
        type(self).session_ids.update(getattr(http, "session_ids", ()))

    def cleanup_owned_logs(self, baseline):
        """Delete only exact new IDs still owned by this fixture's subjects.

        The old all-new-ID cleanup is disabled, so a foreign log arriving after
        this SELECT cannot be accidentally deleted by a later ID difference.
        Guest/Administrator logs with unproved ownership are preserved.
        """
        http = self.query.http
        if not baseline or not hasattr(http, "fixture"):
            return
        f = http.reconnect()
        users = tuple(sorted({http.fixture.manager, http.fixture.beneficiary, http.fixture.approver,
                              *getattr(self.query, "extra_users", ())}))
        markers = ",".join(("%s",) * len(users))
        for kind, previous in baseline.items():
            predicate = "owner IN (" + markers + ")"
            values = users
            if kind == "Activity Log":
                predicate += " OR user IN (" + markers + ")"
                values += users
            rows = f.db.sql(f"SELECT name FROM `tab{kind}` WHERE ({predicate})", values, as_dict=True)
            current_ids = {row[0] for row in f.db.sql(f"SELECT name FROM `tab{kind}`")}
            owned_ids = {row["name"] for row in rows}
            type(self).unrelated_log_ids[kind].update(current_ids - previous - owned_ids)
            for row in rows:
                key = row["name"]
                if key not in previous:
                    f.db.sql(f"DELETE FROM `tab{kind}` WHERE name=%s AND ({predicate})", (key, *values))
        f.db.commit()

    def cleanup_private_configuration(self):
        self.directory.cleanup()
        self.assertFalse(self.root.exists())

    def cleanup(self):
        os.chmod(self.root, 0o700)
        if hasattr(self, "query"):
            self.record_fixture_ids()
            http = getattr(self.query, "http", None)
            baseline = getattr(http, "log_tables", {})
            if http is not None:
                http.log_tables = {}  # Do not delegate its broad new-log-ID deletion.
            try:
                self.query.cleanup()
            finally:
                if http is not None:
                    http.log_tables = baseline
                self.record_fixture_ids()
                self.cleanup_owned_logs(baseline)

    def write_configuration(self, value=None):
        value = self.configuration if value is None else value
        os.chmod(self.root, 0o700)
        staging = self.root / "replacement.json"
        descriptor = os.open(staging, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                   separators=(",", ":")).encode("utf-8"))
        os.chmod(staging, 0o600)
        os.replace(staging, self.path)

    def counts(self):
        f = self.query.http.reconnect()
        return tuple(f.db.count(kind) for kind in (*KINDS, *POLICY_KINDS))

    def request(self, query="list_positions", params=None, *, client=None, method="GET",
                origin=ORIGIN, token=None, headers=None, base_url=ORIGIN):
        request_headers = {"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"}
        if origin is not None:
            request_headers["Origin"] = origin
        if token is not False:
            request_headers["X-Frappe-CSRF-Token"] = self.query.http.token if token is None else token
        request_headers.update(headers or {})
        response = (client or self.client).open(QUERY_PREFIX + query, method=method, base_url=base_url,
            query_string=params or {}, headers=request_headers, buffered=True)
        try:
            return response.status_code, response.get_json(), response.get_data(as_text=True), dict(response.headers)
        finally:
            response.close()

    def denied(self, response, before, *, code=None, status=None):
        self.assertGreaterEqual(response[0], 400)
        if status is not None:
            self.assertEqual(response[0], status)
        self.assertIsInstance(response[1], dict)
        envelope = response[1].get("message", response[1])
        self.assertIs(envelope.get("ok"), False)
        if code is not None:
            self.assertEqual(envelope.get("error", {}).get("code"), code)
        self.assertIn("no-store", response[3].get("Cache-Control", ""))
        for field in ("items", "total", "exc", "exc_type", "exception", "traceback", "_server_messages", "_exc_source"):
            self.assertIsNone(find_field(response[1], field))
        for secret in (str(self.root), str(self.path), self.fixture.manager, self.fixture.approver,
                       "SYNTH-PRIVATE", "SYNTHETIC-PREVIEW-ONLY", "SAVE_RESULT_UNKNOWN"):
            self.assertNotIn(secret, response[2])
        self.assertEqual(self.counts(), before)

    def successful(self, response, before):
        data = self.query.data(response)
        self.assertIn("no-store", response[3].get("Cache-Control", ""))
        self.assertEqual(self.counts(), before)
        return data

    def test_actual_factory_preserves_native_global_and_serves_four_get_routes(self):
        import frappe.app
        before = self.counts()
        native_application = frappe.app.application
        with patch.object(self.native, "init", side_effect=AssertionError("factory initialized Site")), \
                patch.object(self.native, "connect", side_effect=AssertionError("factory connected DB")):
            application = management_wsgi.create_application(configuration_path=str(self.path))
        self.assertIs(frappe.app.application, native_application)
        self.assertIs(application.application, native_application)
        client = self.query.query_client(application)
        context = self.successful(self.request("get_management_context", client=client), before)
        self.assertEqual(set(context["operation_ids"]), READ_OPERATIONS)
        for query, params, total in (("list_positions", None, 3),
                ("get_person_assignments", {"employee_id": self.fixture.employee}, 2), ("lookup_people", None, 2)):
            self.assertEqual(self.successful(self.request(query, params, client=client), before)["total"], total)

    def test_real_structure_preflight_uses_ten_selects_without_commit_or_rollback(self):
        before = self.counts()
        f = self.query.http.reconnect()
        database = f.local.db
        initial_writes = database.transaction_writes
        with select_trace(f) as calls, \
                patch.object(type(database), "commit", side_effect=AssertionError("preflight committed")), \
                patch.object(type(database), "rollback", side_effect=AssertionError("preflight rolled back")):
            report = management_preflight.preflight_management_structure(f,
                expected_site=SITE, expected_database_sha256=DB_HASH)
        assert_structure_trace(self, calls)
        self.assertEqual(database.transaction_writes, initial_writes)
        self.assertIs(report["structure_validated"], True)
        self.assertIs(report["production_ready"], False)
        self.assertEqual((report["managed_tables_checked"], report["native_tables_checked"]), (8, 5))
        self.assertEqual(self.counts(), before)

    def test_each_factory_query_checks_real_structure_before_service_with_real_utc(self):
        from hbos_portal.organization.management_queries import ManagementQueryService
        before = self.counts()
        events, traces, clocks = [], [], []
        original_preflight = management_preflight.preflight_management_structure
        original_execute = ManagementQueryService.execute

        def structure(native, **kwargs):
            events.append("preflight")
            with select_trace(native) as calls:
                result = original_preflight(native, **kwargs)
            traces.append(calls)
            return result

        def execute(service, query, params):
            events.append("service")
            self.assertEqual(self.native.local.site, SITE)
            self.assertEqual(self.native.session.user, self.fixture.manager)
            clocks.append(service.clock())
            return original_execute(service, query, params)

        start = datetime.now(timezone.utc)
        with patch.object(management_preflight, "preflight_management_structure", structure), \
                patch.object(ManagementQueryService, "execute", execute):
            for query in QUERIES:
                params = {"employee_id": self.fixture.employee} if query == "get_person_assignments" else None
                self.successful(self.request(query, params), before)
        end = datetime.now(timezone.utc)
        self.assertEqual(events, ["preflight", "service"] * 4)
        self.assertEqual(len(traces), 4)
        for calls in traces:
            assert_structure_trace(self, calls)
        self.assertTrue(all(start <= clock <= end for clock in clocks))

    def test_wrong_host_or_scheme_and_forwarded_spoofing_never_dispatch_native(self):
        before = self.counts()
        with patch.object(self.application, "application", side_effect=AssertionError("wrong Host reached native")) as native:
            for options in ({"headers": {"Host": "runtime-host-spoof.invalid"}},
                    {"base_url": "https://" + SITE},
                    {"headers": {"Host": "runtime-host-spoof.invalid", "X-Forwarded-Host": SITE,
                                 "X-Forwarded-Proto": "http", "X-Frappe-Site-Name": SITE}}):
                self.denied(self.request(**options), before, code="FORBIDDEN", status=403)
            native.assert_not_called()
        # The native core uses this header as its Site selector. The generated
        # nonexistent name is confirmed absent in this fixed Preview bench;
        # no other real Site, service or configuration is accessed.
        missing_site = self.fixture.prefix.lower() + "-not-created.invalid"
        self.assertFalse((Path.cwd() / missing_site).exists())
        observed_sites = []
        original_init = self.native.init

        def init(*args, **kwargs):
            observed_sites.append(kwargs.get("site", args[0] if args else None))
            return original_init(*args, **kwargs)

        with patch.object(self.native, "init", init):
            response = self.request(headers={"X-Frappe-Site-Name": missing_site})
        self.denied(response, before)
        self.assertIn(missing_site, observed_sites)
        self.assertNotIn(SITE, observed_sites)  # No fallback to the real bound Site.

    def test_actual_loaded_native_protection_hooks_are_present_without_refresh(self):
        f = self.query.http.reconnect()
        before = self.counts()
        report = loaded_protection_hooks(f)
        self.assertEqual(report, self.hook_report)
        self.assertEqual(report, dict(before_request=True, has_permission_doctypes=8,
            permission_query_doctypes=8, refresh_performed=False))
        self.assertEqual(self.counts(), before)

    def test_default_factory_disabled_missing_and_malformed_config_remain_closed(self):
        before = self.counts()
        default = management_wsgi.create_application()
        client = self.query.query_client(default)
        with patch.object(default, "application", side_effect=AssertionError("default factory reached native")) as native:
            for query in QUERIES:
                self.denied(self.request(query, client=client), before, code="NOT_SUPPORTED", status=501)
            native.assert_not_called()
        for failure in ("disabled", "missing", "invalid"):
            self.write_configuration()
            if failure == "disabled":
                value = deepcopy(self.configuration)
                value["enabled"] = False
                self.write_configuration(value)
            elif failure == "missing":
                self.path.unlink()
            else:
                self.path.write_bytes(b"SYNTH-PRIVATE-INVALID-CONFIG")
            with patch.object(self.application, "application", side_effect=AssertionError("closed config reached native")) as native:
                self.denied(self.request(), before, code="NOT_SUPPORTED", status=501)
                native.assert_not_called()

    def test_private_file_and_parent_permissions_symlink_and_hardlink_are_enforced(self):
        before = self.counts()
        for failure in ("file_mode", "parent_mode", "symlink", "hardlink"):
            self.write_configuration()
            alias = self.root / "config-alias.json"
            if alias.exists() or alias.is_symlink():
                alias.unlink()
            if failure == "file_mode":
                os.chmod(self.path, 0o644)
            elif failure == "parent_mode":
                os.chmod(self.root, 0o755)
            elif failure == "symlink":
                os.symlink(self.path, alias)
            else:
                os.link(self.path, alias)
            path = alias if failure == "symlink" else self.path
            application = management_wsgi.create_application(configuration_path=str(path))
            client = self.query.query_client(application)
            with patch.object(application, "application", side_effect=AssertionError("unsafe file reached native")) as native:
                self.denied(self.request(client=client), before, code="NOT_SUPPORTED", status=501)
                native.assert_not_called()
            os.chmod(self.root, 0o700)
            if alias.exists() or alias.is_symlink():
                alias.unlink()
        self.write_configuration()
        self.assertEqual(self.successful(self.request(), before)["total"], 3)

    def test_withdrawal_between_requests_has_no_last_known_good_binding(self):
        before = self.counts()
        self.assertEqual(self.successful(self.request(), before)["total"], 3)
        disabled = deepcopy(self.configuration)
        disabled["enabled"] = False
        self.write_configuration(disabled)
        self.denied(self.request(), before, code="NOT_SUPPORTED", status=501)
        self.path.unlink()
        self.denied(self.request(), before, code="NOT_SUPPORTED", status=501)
        self.write_configuration()
        self.assertEqual(self.successful(self.request(), before)["total"], 3)

    def test_withdrawal_during_real_query_withholds_selected_data_before_release(self):
        before = self.counts()
        for failure in ("disable", "delete", "corrupt", "mode"):
            self.write_configuration()

            def withdraw(service, failure=failure):
                if failure == "disable":
                    disabled = deepcopy(self.configuration)
                    disabled["enabled"] = False
                    self.write_configuration(disabled)
                elif failure == "delete":
                    self.path.unlink()
                elif failure == "corrupt":
                    self.path.write_bytes(b"SYNTH-PRIVATE-INVALID-CONFIG")
                else:
                    os.chmod(self.path, 0o644)

            with self.query.after_query(withdraw):
                self.denied(self.request(), before, code="NOT_SUPPORTED", status=501)

    def test_valid_config_byte_change_requires_retry_and_never_releases_old_body(self):
        before = self.counts()
        changed = deepcopy(self.configuration)
        changed["sites"][0]["approval_pins"][0]["source_ref"] = "SYNTHETIC-RUNTIME-PIN-REPLACED"
        with self.query.after_query(lambda service: self.write_configuration(changed)):
            self.denied(self.request(), before, code="CONFLICT_RETRY_REQUIRED", status=409)
        self.assertEqual(self.successful(self.request(), before)["total"], 3)

    def test_current_unique_pin_is_required_and_config_cannot_approve_new_revision(self):
        before = self.counts()
        wrong = deepcopy(self.configuration)
        row = wrong["sites"][0]["approval_pins"][0]
        row["content_digest"] = "0" * 64
        approval = json.loads(row["approval_json"])
        approval["content_digest"] = row["content_digest"]
        from hbos_portal.organization.storage_schema import canonical_json
        row["approval_json"] = canonical_json(approval)
        self.write_configuration(wrong)
        self.denied(self.request(), before)
        old = self.fixture.policy
        newer = replace(old, revision=old.revision + 1,
                        authority_generation=old.authority_generation + 1, approval=None)
        newer = replace(newer, approval=replace(old.approval, approved_revision=newer.revision,
            approved_authority_generation=newer.authority_generation,
            content_digest=management_policy_digest(newer)))
        f = self.query.http.reconnect()
        self.fixture.install(newer, expected=old.revision)
        f.db.commit()
        self.fixture.policy = newer
        before = self.counts()  # Only the explicit fixture-policy revision changed.
        self.write_configuration()  # Syntactically valid stale revision-2 pin.
        self.denied(self.request(), before)
        empty = deepcopy(self.configuration)
        empty["sites"][0]["approval_pins"] = []
        self.write_configuration(empty)
        self.denied(self.request(), before, code="NOT_SUPPORTED", status=501)
        current = [pin for pin in self.fixture.pins if pin.policy_id == newer.policy_id
                   and pin.revision == newer.revision and pin.authority_generation == newer.authority_generation]
        self.assertEqual(len(current), 1)
        self.configuration["sites"][0]["approval_pins"] = [asdict(current[0])]
        self.write_configuration()
        self.assertEqual(self.successful(self.request(), before)["total"], 3)

    def test_native_session_and_saved_csrf_validation_precede_structure_reads(self):
        from werkzeug.test import Client
        from werkzeug.wrappers import Response
        before = self.counts()
        guest = Client(self.application, Response, use_cookies=True)
        self.query.http.clients.append(guest)
        with patch.object(management_preflight, "preflight_management_structure",
                          side_effect=AssertionError("bad session reached structure")) as structure:
            for options in ({"client": guest}, {"token": False}, {"token": "SYNTHETIC-WRONG-CSRF"},
                            {"origin": "https://runtime-host-spoof.invalid"}):
                self.denied(self.request(**options), before)
            structure.assert_not_called()

    def test_query_factory_does_not_install_the_write_wrapper(self):
        before = self.counts()
        body = self.query.http.args("create_position", self.fixture.position_payload())
        response = self.query.http.request("create_position", body, client=self.client)
        # This endpoint passes to its real native default-closed boundary.
        self.assertGreaterEqual(response[0], 400)
        self.assertIs(find_field(response[1], "ok"), False)
        self.assertEqual(find_field(response[1], "code"), "NOT_SUPPORTED")
        self.assertIsNone(find_field(response[1], "record_id"))
        self.assertEqual(self.counts(), before)

    def test_missing_exact_fixture_root_blocks_structure_before_query_service(self):
        from hbos_portal.organization.management_queries import ManagementQueryService
        f = self.query.http.reconnect()
        f.db.sql("DELETE FROM `tabHBOS Organization Write Lock` WHERE name=%s AND record_key=%s", (LOCK_KEY, LOCK_KEY))
        f.db.commit()
        before = self.counts()
        with patch.object(ManagementQueryService, "execute", side_effect=AssertionError("missing root reached service")) as execute:
            self.denied(self.request(), before)
            execute.assert_not_called()


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
        report["loaded_protection_hooks"] = loaded_protection_hooks(frappe)
        with select_trace(frappe) as calls:
            try:
                report["structure"] = management_preflight.preflight_management_structure(frappe,
                    expected_site=SITE, expected_database_sha256=DB_HASH)
            except ContractError as error:
                if error.code != "STORAGE_PREFLIGHT_ROOT_LOCK_REQUIRED":
                    raise
                report["structure"] = dict(structure_validated=False, production_ready=False,
                    status="SYNTHETIC_FIXTURE_ROOT_REQUIRED", error_code=error.code, root_initialized=False)
        if len(calls) != 10:
            raise RuntimeError("STRUCTURE_PREFLIGHT_SELECT_COUNT_MISMATCH")
        report["structure_selects"] = len(calls)
        frappe.db.rollback()
        if args.phase == "test":
            before = native_fingerprints(frappe)
            NativeManagementRuntimeCases.native = frappe
            suite = unittest.defaultTestLoader.loadTestsFromTestCase(NativeManagementRuntimeCases)
            names = [test.id().rsplit(".", 1)[1] for test in suite]
            if len(names) < 12:
                raise RuntimeError("RUNTIME_ACCEPTANCE_CASES_INCOMPLETE")
            NativeManagementRuntimeCases.synthetic_users.clear()
            NativeManagementRuntimeCases.synthetic_employees.clear()
            NativeManagementRuntimeCases.session_ids.clear()
            NativeManagementRuntimeCases.private_roots.clear()
            NativeManagementRuntimeCases.unrelated_log_ids = {"Activity Log": set(), "Error Log": set()}
            original_logs = {kind: {row[0] for row in frappe.db.sql(f"SELECT name FROM `tab{kind}`")}
                             for kind in ("Activity Log", "Error Log")}
            result = unittest.TextTestRunner(verbosity=2).run(suite)
            frappe.init(site=SITE, sites_path=".", force=True)
            frappe.connect()
            frappe.set_user("Administrator")
            report["tests_run"] = result.testsRun
            report["failures"] = len(result.failures)
            report["errors"] = len(result.errors)
            report["skipped"] = len(result.skipped)
            report["test_names"] = names
            report["test_status"] = "PASS" if result.wasSuccessful() else "FAIL"
            report["native_preservation"] = "PASS" if native_fingerprints(frappe) == before else "FAIL"
            report["final_native_counts"] = preflight(frappe)["native_counts"]
            report["final_managed_counts"] = {kind: frappe.db.count(kind) for kind in (*KINDS, *POLICY_KINDS)}
            report["tables_empty"] = not any(report["final_managed_counts"].values())
            report["loaded_protection_hooks_after"] = loaded_protection_hooks(frappe)
            users = tuple(sorted(NativeManagementRuntimeCases.synthetic_users))
            employees = tuple(sorted(NativeManagementRuntimeCases.synthetic_employees))
            user_markers = ",".join(("%s",) * len(users))
            employee_markers = ",".join(("%s",) * len(employees))
            residue = {}
            if users:
                for table, predicate in (("tabUser", "name"), ("__Auth", "name"),
                        ("tabHas Role", "parent"), ("tabSessions", "user")):
                    residue[table] = frappe.db.sql(f"SELECT COUNT(*) FROM `{table}` WHERE {predicate} IN ({user_markers})", users)[0][0]
                residue["tabActivity Log"] = frappe.db.sql(
                    f"SELECT COUNT(*) FROM `tabActivity Log` WHERE user IN ({user_markers}) OR owner IN ({user_markers})",
                    users + users)[0][0]
                residue["tabError Log"] = frappe.db.sql(
                    f"SELECT COUNT(*) FROM `tabError Log` WHERE owner IN ({user_markers})", users)[0][0]
            if employees:
                residue["tabEmployee"] = frappe.db.sql(
                    f"SELECT COUNT(*) FROM `tabEmployee` WHERE name IN ({employee_markers})", employees)[0][0]
            residue["session_cache"] = sum(frappe.cache.hget("session", sid) is not None
                for sid in NativeManagementRuntimeCases.session_ids)
            residue["login_failed_count_cache"] = sum(frappe.cache.hget("login_failed_count", user) is not None for user in users)
            residue["redirect_after_login_cache"] = sum(frappe.cache.hget("redirect_after_login", user) is not None for user in users)
            report["synthetic_residue"] = residue
            report["synthetic_cleanup_verified"] = not any(residue.values())
            report["temporary_directories_created"] = len(NativeManagementRuntimeCases.private_roots)
            report["temporary_directories_removed"] = all(not Path(path).exists() for path in NativeManagementRuntimeCases.private_roots)
            report["log_preservation"] = {}
            for kind, baseline in original_logs.items():
                current = {row[0] for row in frappe.db.sql(f"SELECT name FROM `tab{kind}`")}
                unrelated = NativeManagementRuntimeCases.unrelated_log_ids[kind]
                report["log_preservation"][kind] = dict(original_ids_retained=baseline <= current,
                    unrelated_new_ids_seen=len(unrelated), unrelated_new_ids_retained=unrelated <= current,
                    unattributed_new_rows_retained=len(current - baseline))
            logs_preserved = all(row["original_ids_retained"] and row["unrelated_new_ids_retained"]
                                 for row in report["log_preservation"].values())
            report["real_native_password_session"] = True
            report["runtime_clock"] = "REAL_UTC"
            report["private_configuration"] = "TEMPORARY_0700_0600_EXACT_CURRENT_PIN_REMOVED"
            report["limits"] = "No production activation, schema/config/service change, Administrator password, human approval or full restore."
            print(json.dumps(report, ensure_ascii=False, default=str))
            if (not result.wasSuccessful() or not report["tables_empty"] or report["native_preservation"] != "PASS"
                    or not report["synthetic_cleanup_verified"] or not report["temporary_directories_removed"]
                    or not logs_preserved):
                raise SystemExit(1)
        else:
            print(json.dumps(report, ensure_ascii=False, default=str))
    finally:
        if getattr(frappe.local, "db", None):
            frappe.db.rollback()
        frappe.destroy()


if __name__ == "__main__":
    main()
