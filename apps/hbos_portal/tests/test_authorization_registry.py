import dataclasses
import json
from pathlib import Path
import subprocess
import sys
import unittest

from hbos_portal.authorization.contracts import RegistrationInput
from hbos_portal.authorization.errors import ContractError
from hbos_portal.authorization.registry import build_definition_registry
from hbos_portal.authorization.validation import validate_template_version
from tests.authorization_fixtures import definition, registration, template


class AuthorizationRegistryTests(unittest.TestCase):
    def test_off01_valid_definition_is_only_structural(self):
        snapshot = build_definition_registry([registration()])
        self.assertEqual(tuple(snapshot.apps), ("demo_lab",))
        self.assertEqual(snapshot.failures, ())
        self.assertTrue(snapshot.validation_only)
        self.assertFalse(snapshot.runtime_verified)
        self.assertFalse(hasattr(snapshot, "grants"))

    def test_off02_extensible_apps_and_invalid_isolation(self):
        bad = definition("bad_app")
        bad["contract_version"] = 42
        result = build_definition_registry([registration(), registration(app="new_app"), registration(bad, "bad_app")])
        self.assertEqual(set(result.apps), {"demo_lab", "new_app"})
        self.assertEqual(result.failures[0].code, "UNSUPPORTED_VERSION")

    def test_off03_duplicate_apps_all_quarantined_in_either_order(self):
        for candidates in ([registration(source="a"), registration(source="b")], [registration(source="b"), registration(source="a")]):
            result = build_definition_registry(candidates + [registration(app="healthy")])
            self.assertEqual(set(result.apps), {"healthy"})
            self.assertEqual([f.code for f in result.failures], ["DUPLICATE_APP"] * 2)

    def test_off04_duplicate_actions_and_namespace_intrusion(self):
        for mode in ("duplicate", "foreign", "wildcard", "invalid_segment"):
            with self.subTest(mode=mode):
                bad = definition()
                if mode == "duplicate":
                    bad["actions"].append(dict(bad["actions"][0]))
                else:
                    bad["actions"][0]["action_id"] = {"foreign": "other.results.read", "wildcard": "demo_lab.results.*", "invalid_segment": "demo_lab.1read"}[mode]
                self.assertFalse(build_definition_registry([registration(bad)]).apps)

    def test_duplicate_app_still_quarantines_both_when_one_payload_is_invalid(self):
        invalid = definition()
        invalid["resolver"] = "arbitrary.path"
        for entries in ([registration(invalid), registration()], [registration(), registration(invalid)]):
            result = build_definition_registry(entries)
            self.assertFalse(result.apps)
            self.assertEqual([f.code for f in result.failures], ["DUPLICATE_APP"] * 2)

    def test_off05_versions_are_positive_integers_and_supported(self):
        for value in (True, False, -1, 0, "1", 2):
            for section, key in ((None, "contract_version"), ("scopes", "schema_version")):
                bad = definition()
                (bad if section is None else bad[section][0])[key] = value
                self.assertFalse(build_definition_registry([registration(bad)]).apps)

    def test_off06_missing_or_incompatible_references(self):
        for mode in ("resource", "scope", "action", "binding", "incompatible"):
            bad = definition()
            if mode == "resource":
                bad["actions"][0]["resource_id"] = "demo_lab.missing"
            elif mode == "scope":
                bad["actions"][0]["scope_types"] = ["demo_lab.missing"]
            elif mode == "action":
                bad["bindings"][0]["action_id"] = "demo_lab.missing"
            elif mode == "binding":
                bad["bindings"].pop()
            else:
                bad["bindings"][0]["resource_id"] = "demo_lab.missing"
            self.assertFalse(build_definition_registry([registration(bad)]).apps, mode)

    def test_off07_untrusted_claim_and_executable_fields_rejected(self):
        mismatch = RegistrationInput("synthetic", "other", definition())
        result = build_definition_registry([mismatch, registration()])
        self.assertEqual(set(result.apps), {"demo_lab"})
        self.assertEqual(result.failures[0].code, "SOURCE_MISMATCH")
        for key, value in (("resolver", "os.system"), ("sql", "select * from secret"), ("binding_key", "module.run()")):
            bad = definition()
            bad["bindings"][0][key] = value
            self.assertFalse(build_definition_registry([registration(bad)]).apps)

    def test_off08_manifest_claims_never_become_runtime_proof(self):
        app = build_definition_registry([registration()]).apps["demo_lab"]
        self.assertTrue(app.actions[0].declared_available)
        self.assertTrue(app.validation_only)
        self.assertFalse(app.runtime_verified)
        self.assertFalse(hasattr(app, "grantable"))

    def test_off09_new_directory_actions_do_not_expand_fixed_template(self):
        old = build_definition_registry([registration()])
        fixed = validate_template_version(template(), old)
        changed = definition()
        changed["definition_revision"] = "opaque-next"
        changed["actions"][1]["label"] = "改显示名"
        changed["actions"].append({**changed["actions"][0], "action_id": "demo_lab.results.export"})
        changed["bindings"].append({**changed["bindings"][0], "binding_key": "provider:export", "action_id": "demo_lab.results.export"})
        updated = build_definition_registry([registration(changed)])
        same = validate_template_version(template(), updated, [fixed])
        self.assertEqual(fixed, same)
        self.assertEqual(fixed.action_ids, ("demo_lab.results.review",))
        self.assertEqual(len(old.apps["demo_lab"].actions), 3)

    def test_off10_template_fixed_version_conflict(self):
        registry = build_definition_registry([registration()])
        original = validate_template_version(template(), registry)
        changed = template()
        changed["action_ids"].append("demo_lab.results.read")
        with self.assertRaises(ContractError) as error:
            validate_template_version(changed, registry, [original])
        self.assertEqual(error.exception.code, "VERSION_CONFLICT")
        changed["version"] = 2
        self.assertEqual(validate_template_version(changed, registry, [original]).version, 2)

    def test_historical_retired_action_preserved_but_new_template_rejected(self):
        bad = definition()
        bad["actions"][1]["status"] = "retired"
        registry = build_definition_registry([registration(bad)])
        with self.assertRaises(ContractError):
            validate_template_version(template(), registry)
        historical = validate_template_version(template(), registry, historical=True)
        self.assertEqual(historical.unavailable_action_ids, historical.action_ids)
        self.assertFalse(historical.runtime_verified)

    def test_off11_nested_input_mutations_do_not_change_snapshot(self):
        payload = definition()
        result = build_definition_registry([RegistrationInput("synthetic", "demo_lab", payload)])
        payload["actions"][0]["scope_types"].append("secret")
        payload["scopes"][0]["dimension"] = "changed"
        self.assertEqual(result.apps["demo_lab"].actions[0].scope_types, ("demo_lab.lab_group",))
        self.assertEqual(result.apps["demo_lab"].scopes[0].dimension, "lab_group")
        with self.assertRaises(TypeError):
            result.apps["other"] = result.apps["demo_lab"]
        with self.assertRaises(dataclasses.FrozenInstanceError):
            result.apps["demo_lab"].app_id = "other"

    def test_off19_fresh_process_no_runtime_io_or_frappe(self):
        source = r'''
import builtins, os, sys
def blocked(*args, **kwargs):
    raise AssertionError("runtime side effect")
class BlockEnvironment(dict):
    __getitem__ = get = __iter__ = __contains__ = blocked
os.environ = BlockEnvironment()
os.getenv = blocked
original_import = builtins.__import__
def guarded_import(name, *args, **kwargs):
    if name.split(".")[0] in {"frappe", "socket", "sqlite3", "pymysql"}:
        blocked()
    return original_import(name, *args, **kwargs)
builtins.__import__ = guarded_import
def audit(event, args):
    if event.startswith(("socket.", "subprocess.", "os.mkdir", "os.remove", "os.rename")):
        blocked()
    if event == "open":
        path, mode, flags = args
        if (mode and any(c in mode for c in "wa+")) or (isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT)):
            blocked()
        if not str(path).endswith((".py", ".pyc")):
            blocked()
sys.addaudithook(audit)
from hbos_portal.authorization.registry import build_definition_registry
from hbos_portal.authorization.validation import validate_template_version
from tests.authorization_fixtures import registration, template
registry = build_definition_registry([registration()])
assert validate_template_version(template(), registry).runtime_verified is False
assert "frappe" not in sys.modules
print("OFF19 PASS")
'''
        result = subprocess.run([sys.executable, "-B", "-c", source], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "OFF19 PASS")

    def test_off20_payload_safe_stable_errors_with_healthy_app(self):
        phone = "18812345678"
        bad = definition()
        bad["bindings"][0][phone] = {"credential": phone}
        registry = build_definition_registry([registration(bad), registration(app="healthy")])
        serialized = json.dumps([dataclasses.asdict(f) for f in registry.failures])
        self.assertNotIn(phone, serialized)
        self.assertEqual(registry.failures[0].code, "UNKNOWN_FIELD")
        self.assertEqual(set(registry.apps), {"healthy"})


if __name__ == "__main__":
    unittest.main()
