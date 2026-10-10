"""Offline private-config and buffered WSGI assembly checks, never Site acceptance."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import timedelta
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from types import ModuleType
import unittest
from unittest.mock import patch

from hbos_portal.authorization.errors import ContractError
from hbos_portal.organization.management_http import ManagedHTTPBinding
from hbos_portal.organization.management_storage import PolicyApprovalPin, PinnedPolicyApprovalVerifier
from hbos_portal.organization.storage_schema import canonical_json
from hbos_portal.organization import management_runtime as runtime


SITE = "synthetic-runtime-site"
ORIGIN = "https://runtime.invalid"
DB_HASH = hashlib.sha256(b"synthetic-runtime-database").hexdigest()
POLICY_ID = "00000000-0000-4000-8000-000000000001"
SUBJECT = "SYNTHETIC-RUNTIME-MANAGER"
PRIVATE_MARKER = "SYNTHETIC-CONFIG-PRIVATE-DO-NOT-RELEASE"
PREFIX = "/api/method/hbos_portal.api.organization_relations."
QUERIES = ("get_management_context", "list_positions", "get_person_assignments", "lookup_people")


def pin(**changes):
    content = hashlib.sha256(b"synthetic-runtime-policy").hexdigest()
    approval = dict(approval_ref="SYNTHETIC-APPROVAL", approved_by="SYNTHETIC-APPROVER",
        approved_at_utc="2026-10-09T00:00:00+00:00", approved_revision=1,
        approved_authority_generation=1, content_digest=content)
    row = dict(site_id=SITE, database_sha256=DB_HASH, policy_id=POLICY_ID,
        revision=1, authority_generation=1, subject_user=SUBJECT, content_digest=content,
        approval_json=canonical_json(approval), source_ref="SYNTHETIC-APPROVAL-EVIDENCE")
    row.update(changes)
    return row


def payload(*, enabled=True, site_enabled=True):
    return dict(schema_version=1, enabled=enabled, sites=[dict(site_id=SITE,
        database_sha256=DB_HASH, origin=ORIGIN, enabled=site_enabled,
        approval_pins=[pin()])])


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


class ConfigParsingTests(unittest.TestCase):
    def parse(self, value):
        return runtime.parse_management_runtime_config(encoded(value))

    def reject(self, action):
        with self.assertRaises(ContractError) as caught:
            action()
        self.assertTrue(caught.exception.code.startswith("RUNTIME_CONFIG_"), caught.exception.code)
        self.assertNotIn(PRIVATE_MARKER, str(caught.exception))
        self.assertNotIn(SUBJECT, str(caught.exception))
        return caught.exception

    def test_defaults_are_closed_and_raw_bytes_hash_is_preserved(self):
        config = self.parse(dict(schema_version=1))
        self.assertIs(config.enabled, False)
        self.assertEqual(config.sites, ())
        self.assertEqual(config.source_sha256, hashlib.sha256(encoded(dict(schema_version=1))).hexdigest())
        missing = runtime.load_management_runtime_config(None)
        self.assertIs(missing.enabled, False)
        self.assertEqual(missing.sites, ())

    def test_valid_private_pin_configuration_is_frozen_and_exact(self):
        config = self.parse(payload())
        self.assertIs(config.enabled, True)
        self.assertIsInstance(config.sites, tuple)
        site = config.sites[0]
        self.assertEqual((site.site_id, site.database_sha256, site.origin), (SITE, DB_HASH, ORIGIN))
        self.assertIs(site.enabled, True)
        self.assertIsInstance(site.approval_pins, tuple)
        self.assertEqual(site.approval_pins, (PolicyApprovalPin(**pin()),))
        for value, name in ((config, "enabled"), (site, "origin"), (site.approval_pins[0], "source_ref")):
            with self.subTest(name=name), self.assertRaises((FrozenInstanceError, AttributeError)):
                setattr(value, name, PRIVATE_MARKER)

    def test_site_defaults_are_closed_without_implicit_pins_or_global_enable(self):
        value = dict(schema_version=1, sites=[dict(site_id=SITE, database_sha256=DB_HASH, origin=ORIGIN)])
        config = self.parse(value)
        self.assertIs(config.enabled, False)
        self.assertIs(config.sites[0].enabled, False)
        self.assertEqual(config.sites[0].approval_pins, ())

    def test_schema_unknown_fields_and_boolean_integer_aliases_are_rejected(self):
        for value in ({}, [], {"schema_version": True}, {"schema_version": 2},
                      {"schema_version": 1, "enabled": 1}, {"schema_version": 1, "sites": {}},
                      {"schema_version": 1, PRIVATE_MARKER: True}):
            with self.subTest(value=value):
                self.reject(lambda: self.parse(value))
        for extra in ({"enabled": 1}, {"clock": PRIVATE_MARKER}, {"database_sha256": "f" * 63}):
            value = payload()
            value["sites"][0].update(extra)
            self.reject(lambda: self.parse(value))

    def test_duplicate_json_keys_invalid_utf8_nonbytes_and_nan_are_rejected(self):
        raw_values = (b'{"schema_version":1,"schema_version":1}',
            b'{"schema_version":1,"enabled":false,"sites":[{"site_id":"a","site_id":"b"}]}',
            b'{"schema_version":1,"enabled":NaN}', b'{"schema_version":1,"enabled":Infinity}',
            b"\xff", b"{} trailing", "{}", b"[1]")
        for raw in raw_values:
            with self.subTest(raw=raw):
                self.reject(lambda: runtime.parse_management_runtime_config(raw))

    def test_enabled_configuration_requires_enabled_target_with_pins(self):
        values = [dict(schema_version=1, enabled=True), payload(site_enabled=False)]
        no_pins = payload()
        no_pins["sites"][0]["approval_pins"] = []
        values.append(no_pins)
        # A locally enabled Site cannot claim readiness without pins even when globally off.
        globally_off = payload(enabled=False)
        globally_off["sites"][0]["approval_pins"] = []
        values.append(globally_off)
        for value in values:
            with self.subTest(value=value):
                self.reject(lambda: self.parse(value))

    def test_duplicate_sites_origins_and_policy_ids_are_rejected(self):
        for duplicate in ("site", "origin", "policy"):
            value = payload()
            if duplicate == "policy":
                value["sites"][0]["approval_pins"].append(pin(revision=2))
            else:
                second = deepcopy(value["sites"][0])
                if duplicate == "site":
                    second["origin"] = "https://second.invalid"
                else:
                    second["site_id"] = "second-site"
                    second["approval_pins"][0]["site_id"] = "second-site"
                value["sites"].append(second)
            self.reject(lambda: self.parse(value))

    def test_origin_must_be_exact_http_authority_without_credentials_path_or_spoofing(self):
        for origin in ("https://runtime.invalid/", "https://user:password@runtime.invalid", "https://runtime.invalid?q=1",
                       "https://runtime.invalid#fragment", "ftp://runtime.invalid", "https://runtime.invalid:bad",
                       "https://runtime.invalid\n", "https://runtime.invalid/private", "null"):
            value = payload()
            value["sites"][0]["origin"] = origin
            self.reject(lambda: self.parse(value))
        value = payload()
        value["sites"][0]["origin"] = "http://127.0.0.1:5178"
        self.assertEqual(self.parse(value).sites[0].origin, "http://127.0.0.1:5178")

    def test_pin_exact_fields_site_database_uuid_digest_and_versions_are_required(self):
        changes = ({"site_id": "other-site"}, {"database_sha256": "0" * 64}, {"policy_id": "not-a-uuid"},
            {"revision": True}, {"authority_generation": 0}, {"content_digest": "A" * 64},
            {"source_ref": ""}, {"subject_user": "Guest"}, {"subject_user": " " + SUBJECT}, {"extra": PRIVATE_MARKER})
        for change in changes:
            value = payload()
            value["sites"][0]["approval_pins"][0].update(change)
            self.reject(lambda: self.parse(value))
        value = payload()
        del value["sites"][0]["approval_pins"][0]["source_ref"]
        self.reject(lambda: self.parse(value))

    def test_approval_must_be_canonical_complete_independent_and_bound_to_pin(self):
        changes = ({"approved_by": "Guest"}, {"approved_by": SUBJECT}, {"approved_revision": 2},
            {"approved_authority_generation": True}, {"content_digest": "0" * 64},
            {"approved_at_utc": "2026-10-09T00:00:00+08:00"}, {"approval_ref": ""}, {"extra": PRIVATE_MARKER})
        for change in changes:
            value = payload()
            approval = json.loads(value["sites"][0]["approval_pins"][0]["approval_json"])
            approval.update(change)
            value["sites"][0]["approval_pins"][0]["approval_json"] = canonical_json(approval)
            self.reject(lambda: self.parse(value))
        for raw in ("{}", json.dumps(json.loads(pin()["approval_json"]), indent=2),
                    '{"approved_revision":1,"approved_revision":1}', '{"content_digest":NaN}'):
            value = payload()
            value["sites"][0]["approval_pins"][0]["approval_json"] = raw
            self.reject(lambda: self.parse(value))

    def test_raw_byte_limit_is_enforced_before_parse(self):
        self.reject(lambda: runtime.parse_management_runtime_config(b" " * (128 * 1024 + 1)))


class PrivateFileTests(unittest.TestCase):
    reject = ConfigParsingTests.reject
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="hbos-runtime-offline-", dir="/private/tmp")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        os.chmod(self.root, 0o700)
        self.path = self.root / "runtime.json"
        self.write(payload())

    def write(self, value):
        self.path.write_bytes(encoded(value))
        os.chmod(self.path, 0o600)

    def test_absolute_private_regular_file_loads_without_mutation(self):
        before = self.path.read_bytes()
        before_mode = self.path.stat().st_mode
        config = runtime.load_management_runtime_config(str(self.path))
        self.assertTrue(config.enabled)
        self.assertEqual(config.source_sha256, hashlib.sha256(before).hexdigest())
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.path.stat().st_mode, before_mode)

    def test_relative_wrong_extension_and_missing_files_fail_closed(self):
        for path in ("runtime.json", str(self.root / "runtime.txt"), str(self.root / "missing.json"), ""):
            self.reject(lambda: runtime.load_management_runtime_config(path))

    def test_nonprivate_file_or_parent_directory_is_rejected(self):
        for mode in (0o640, 0o644, 0o660, 0o400, 0o700):
            os.chmod(self.path, mode)
            self.reject(lambda: runtime.load_management_runtime_config(str(self.path)))
        os.chmod(self.path, 0o600)
        os.chmod(self.root, 0o755)
        self.reject(lambda: runtime.load_management_runtime_config(str(self.path)))

    def test_symlink_directory_file_directory_target_and_hardlink_are_rejected(self):
        link = self.root / "linked.json"
        link.symlink_to(self.path)
        self.reject(lambda: runtime.load_management_runtime_config(str(link)))
        nested = self.root / "nested"
        nested.mkdir(mode=0o700)
        child = nested / "runtime.json"
        child.write_bytes(encoded(payload()))
        os.chmod(child, 0o600)
        directory_link = self.root / "linked-directory"
        directory_link.symlink_to(nested, target_is_directory=True)
        self.reject(lambda: runtime.load_management_runtime_config(str(directory_link / "runtime.json")))
        wrong_target = self.root / "directory.json"
        wrong_target.mkdir(mode=0o700)
        self.reject(lambda: runtime.load_management_runtime_config(str(wrong_target)))
        os.link(self.path, self.root / "hardlink.json")
        self.reject(lambda: runtime.load_management_runtime_config(str(self.path)))

    def test_wrong_owner_and_io_error_are_sanitized(self):
        with patch.object(runtime.os, "geteuid", return_value=os.geteuid() + 1):
            self.reject(lambda: runtime.load_management_runtime_config(str(self.path)))
        with patch.object(runtime.os, "open", side_effect=OSError(PRIVATE_MARKER)):
            self.reject(lambda: runtime.load_management_runtime_config(str(self.path)))

    def test_in_read_mutation_and_atomic_replacement_are_not_accepted_as_stable_file(self):
        for mutation in ("in-place", "replace"):
            self.write(payload())
            real_fstat = runtime.os.fstat
            calls = 0
            def changed_fstat(fd):
                nonlocal calls
                calls += 1
                if calls == 2:
                    if mutation == "in-place":
                        self.write(payload(enabled=False))
                    else:
                        replacement = self.root / "replacement.json"
                        replacement.write_bytes(encoded(payload(enabled=False)))
                        os.chmod(replacement, 0o600)
                        replacement.replace(self.path)
                return real_fstat(fd)
            with self.subTest(mutation=mutation), patch.object(runtime.os, "fstat", side_effect=changed_fstat):
                self.reject(lambda: runtime.load_management_runtime_config(str(self.path)))


class RuntimeApplicationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="hbos-runtime-wsgi-offline-", dir="/private/tmp")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        os.chmod(self.root, 0o700)
        self.path = self.root / "runtime.json"
        self.write(payload())
        self.events = []
        self.bindings = []
        self.chunk = encoded(dict(message=dict(ok=True, data=dict(items=[PRIVATE_MARKER], read_only=True))))

    def write(self, value):
        self.path.write_bytes(encoded(value))
        os.chmod(self.path, 0o600)

    def environ(self, query="list_positions", **changes):
        value = dict(PATH_INFO=PREFIX + query, REQUEST_METHOD="GET", **{"wsgi.url_scheme": "https", "HTTP_HOST": "runtime.invalid"})
        value.update(changes)
        return value

    def wrapper(self, native=None, path=True):
        def application(environ, start):
            self.events.append("native")
            start("200 OK", [("Content-Type", "application/json")])
            return [self.chunk]
        return runtime.create_management_query_application(native or application,
            configuration_path=str(self.path) if path else None)

    def spy(self, app, *, binding, require_structure_preflight=False):
        self.bindings.append(binding)
        self.assertIs(require_structure_preflight, True)
        self.assertIs(type(binding), ManagedHTTPBinding)
        self.assertIs(type(binding.approval_verifier), PinnedPolicyApprovalVerifier)
        self.assertIs(binding.enabled, True)
        self.assertEqual(binding.clock().utcoffset(), timedelta(0))
        return app

    def call(self, wrapper, environ=None):
        captured = {}
        writes = []
        def start(status, headers, exc_info=None):
            captured.update(status=status, headers=dict(headers))
            self.events.append("outer-start")
            return writes.append
        result = wrapper(environ or self.environ(), start)
        try:
            body = b"".join(writes + list(result))
        finally:
            close = getattr(result, "close", None)
            if close:
                close()
        return captured, body

    def denied(self, wrapper, *, status, code, environ=None):
        captured, body = self.call(wrapper, environ)
        self.assertTrue(captured["status"].startswith(str(status)), captured)
        value = json.loads(body)
        envelope = value.get("message", value)
        self.assertIs(envelope["ok"], False)
        self.assertEqual(envelope["error"]["code"], code)
        self.assertNotIn(PRIVATE_MARKER.encode(), body)
        self.assertIn("no-store", captured["headers"].get("Cache-Control", ""))
        return captured, body

    def test_all_four_exact_queries_without_configuration_are_closed_before_native(self):
        for query in QUERIES:
            self.denied(self.wrapper(path=False), status=501, code="NOT_SUPPORTED", environ=self.environ(query))
        self.assertNotIn("native", self.events)

    def test_opt_in_entry_factory_keeps_native_global_and_does_not_initialize_a_site(self):
        from hbos_portal.organization import management_wsgi
        fake_frappe = ModuleType("frappe")
        fake_application = ModuleType("frappe.app")
        native_calls = []
        def native(environ, start):
            native_calls.append(environ)
            start("200 OK", [])
            return [b"native-own-boundary"]
        fake_application.application = native
        fake_frappe.app = fake_application
        def forbidden_init(*args, **kwargs):
            raise AssertionError("factory must not initialize a Site")
        fake_frappe.init = forbidden_init
        fake_frappe.connect = forbidden_init
        with patch.dict(sys.modules, {"frappe": fake_frappe, "frappe.app": fake_application}), \
                patch.object(runtime.os, "open", side_effect=AssertionError("default factory must not read files")):
            wrapper = management_wsgi.create_application()
            self.assertIs(type(wrapper), runtime.QueryRuntimeApplication)
            self.assertIs(wrapper.application, native)
            self.assertIsNone(wrapper.configuration_path)
            self.assertIs(fake_application.application, native)
            self.denied(wrapper, status=501, code="NOT_SUPPORTED")
            self.assertEqual(native_calls, [])
            _, body = self.call(wrapper, self.environ("create_position"))
            self.assertEqual(body, b"native-own-boundary")
            explicit = management_wsgi.create_application(configuration_path=str(self.path))
            self.assertEqual(explicit.configuration_path, str(self.path))
            self.assertIs(fake_application.application, native)

    def test_disabled_missing_bad_and_nonprivate_configuration_are_closed(self):
        for failure in ("disabled", "missing", "invalid", "mode"):
            with self.subTest(failure=failure):
                self.write(payload())
                if failure == "disabled":
                    self.write(payload(enabled=False))
                elif failure == "missing":
                    self.path.unlink()
                elif failure == "invalid":
                    self.path.write_bytes(PRIVATE_MARKER.encode())
                else:
                    os.chmod(self.path, 0o644)
                self.denied(self.wrapper(), status=501, code="NOT_SUPPORTED")
        self.assertNotIn("native", self.events)

    def test_nonquery_write_suffix_and_unknown_paths_pass_the_exact_native_iterable(self):
        chunks = [b"native-own-boundary"]
        def application(environ, start):
            self.events.append("native")
            start("200 OK", [])
            return chunks
        wrapper = self.wrapper(application)
        with patch.object(runtime, "load_management_runtime_config", side_effect=AssertionError("nonquery config access")):
            for query in ("create_position", "update_assignment", "unknown_query", "list_positions/", "list_positions.extra"):
                self.assertIs(wrapper(self.environ(query), lambda *args: None), chunks)

    def test_valid_exact_query_assembles_query_only_binding_and_defers_outer_response(self):
        with patch.object(runtime, "ManagedQueryHTTPApplication", side_effect=self.spy):
            captured, body = self.call(self.wrapper())
        self.assertEqual(body, self.chunk)
        self.assertTrue(captured["status"].startswith("200"))
        self.assertEqual((self.bindings[0].site_id, self.bindings[0].database_sha256, self.bindings[0].origin), (SITE, DB_HASH, ORIGIN))
        self.assertEqual(self.bindings[0].approval_verifier._pins, (PolicyApprovalPin(**pin()),))
        self.assertEqual(self.events, ["native", "outer-start"])

    def test_wsgi_write_callback_is_buffered_with_iterated_bytes_until_final_check(self):
        def application(environ, start):
            self.events.append("native")
            write = start("200 OK", [])
            write(b"prefix-")
            self.assertNotIn("outer-start", self.events)
            return [b"suffix"]
        with patch.object(runtime, "ManagedQueryHTTPApplication", side_effect=self.spy):
            captured, body = self.call(self.wrapper(application))
        self.assertTrue(captured["status"].startswith("200"))
        self.assertEqual(body, b"prefix-suffix")
        self.assertEqual(self.events, ["native", "outer-start"])

    def test_post_put_head_and_options_never_enter_query_wrapper(self):
        with patch.object(runtime, "ManagedQueryHTTPApplication", side_effect=self.spy):
            for method in ("POST", "PUT", "HEAD", "OPTIONS", "get"):
                captured, body = self.call(self.wrapper(), self.environ(REQUEST_METHOD=method))
                self.assertFalse(captured["status"].startswith("2"))
                self.assertNotIn(PRIVATE_MARKER.encode(), body)
        self.assertEqual(self.bindings, [])
        self.assertNotIn("native", self.events)

    def test_unknown_origin_and_forwarded_host_spoofing_cannot_select_a_target(self):
        for changes in ({"HTTP_HOST": "attacker.invalid"}, {"wsgi.url_scheme": "http"},
                        {"HTTP_HOST": "runtime.invalid:443"},
                        {"HTTP_HOST": "attacker.invalid", "HTTP_X_FORWARDED_HOST": "runtime.invalid", "HTTP_X_FORWARDED_PROTO": "https", "HTTP_X_FRAPPE_SITE_NAME": SITE}):
            self.denied(self.wrapper(), status=403, code="FORBIDDEN", environ=self.environ(**changes))
        self.assertNotIn("native", self.events)

    def test_actual_transport_selects_target_and_untrusted_site_headers_do_not_override(self):
        with patch.object(runtime, "ManagedQueryHTTPApplication", side_effect=self.spy):
            captured, _ = self.call(self.wrapper(), self.environ(HTTP_X_FRAPPE_SITE_NAME="attacker-site", HTTP_X_FORWARDED_HOST="attacker.invalid", HTTP_X_FORWARDED_PROTO="http"))
        self.assertTrue(captured["status"].startswith("200"))
        self.assertEqual(self.bindings[0].site_id, SITE)

    def test_multi_site_selects_only_matching_origin_pin_and_database(self):
        value = payload()
        second = deepcopy(value["sites"][0])
        second.update(site_id="second-site", origin="https://second.invalid", database_sha256="1" * 64)
        second["approval_pins"] = [pin(site_id="second-site", database_sha256="1" * 64, policy_id="00000000-0000-4000-8000-000000000002")]
        value["sites"].append(second)
        self.write(value)
        with patch.object(runtime, "ManagedQueryHTTPApplication", side_effect=self.spy):
            self.call(self.wrapper(), self.environ(HTTP_HOST="second.invalid"))
        binding = self.bindings[0]
        self.assertEqual((binding.site_id, binding.database_sha256, binding.origin), ("second-site", "1" * 64, "https://second.invalid"))
        self.assertEqual(tuple(item.site_id for item in binding.approval_verifier._pins), ("second-site",))

    def test_valid_byte_change_during_response_withholds_old_data_and_requires_full_retry(self):
        def application(environ, start):
            self.events.append("native")
            start("200 OK", [])
            self.path.write_bytes(self.path.read_bytes() + b"\n")
            return [self.chunk]
        with patch.object(runtime, "ManagedQueryHTTPApplication", side_effect=self.spy):
            self.denied(self.wrapper(application), status=409, code="CONFLICT_RETRY_REQUIRED")
        self.assertEqual(self.events.count("native"), 1)

    def test_disable_delete_corrupt_and_permission_change_during_response_withhold_data(self):
        for mutation in ("disable", "delete", "corrupt", "mode"):
            self.write(payload())
            def application(environ, start):
                self.events.append("native")
                start("200 OK", [])
                if mutation == "disable": self.write(payload(enabled=False))
                elif mutation == "delete": self.path.unlink()
                elif mutation == "corrupt": self.path.write_bytes(PRIVATE_MARKER.encode())
                else: os.chmod(self.path, 0o644)
                return [self.chunk]
            with self.subTest(mutation=mutation), patch.object(runtime, "ManagedQueryHTTPApplication", side_effect=self.spy):
                self.denied(self.wrapper(application), status=501, code="NOT_SUPPORTED")
        self.assertEqual(self.events.count("native"), 4)

    def test_response_iterator_closes_before_configuration_recheck_and_outer_start(self):
        owner = self
        class Iterator:
            def __iter__(self):
                yield owner.chunk
            def close(self):
                owner.events.append("inner-close")
                owner.path.write_bytes(owner.path.read_bytes() + b"\n")
        def application(environ, start):
            self.events.append("native")
            start("200 OK", [])
            return Iterator()
        with patch.object(runtime, "ManagedQueryHTTPApplication", side_effect=self.spy):
            self.denied(self.wrapper(application), status=409, code="CONFLICT_RETRY_REQUIRED")
        self.assertEqual(self.events, ["native", "inner-close", "outer-start"])

    def test_inner_exception_close_failure_and_oversized_result_do_not_release_chunks(self):
        owner = self
        for failure in ("iteration", "close", "oversize"):
            class Iterator:
                def __iter__(self):
                    yield owner.chunk
                    if failure == "iteration": raise RuntimeError(PRIVATE_MARKER)
                    if failure == "oversize": yield b"X" * (1024 * 1024 + 1)
                def close(self):
                    owner.events.append("inner-close")
                    if failure == "close": raise RuntimeError(PRIVATE_MARKER)
            def application(environ, start):
                start("200 OK", [])
                return Iterator()
            with self.subTest(failure=failure), patch.object(runtime, "ManagedQueryHTTPApplication", side_effect=self.spy):
                captured, body = self.call(self.wrapper(application))
                self.assertFalse(captured["status"].startswith("2"))
                self.assertNotIn(PRIVATE_MARKER.encode(), body)
        self.assertEqual(self.events.count("inner-close"), 3)


if __name__ == "__main__":
    unittest.main()
