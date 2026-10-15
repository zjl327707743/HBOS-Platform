"""Exact source-scope contracts; fixtures never touch installed DocTypes/Sites."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPOSITORY = Path(__file__).resolve().parents[3]
SCRIPT = REPOSITORY / "scripts/portal/check_doctype_scope.py"
SPEC = importlib.util.spec_from_file_location("portal_doctype_scope", SCRIPT)
scope = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scope)

# Deliberately independent of the implementation registry: replacing the
# registry must not also redefine what a positive fixture considers approved.
EXPECTED_MODELS = {
    "apps/hbos_portal/hbos_portal/hbos_portal/doctype/hbos_external_identity/hbos_external_identity.json":
        ("DocType", "HBOS External Identity", "HBOS Portal"),
    "apps/hbos_portal/hbos_portal/hbos_portal/doctype/hbos_account_operation/hbos_account_operation.json":
        ("DocType", "HBOS Account Operation", "HBOS Portal"),
    "apps/hbos_portal/hbos_portal/hbos_portal/doctype/hbos_account_change_event/hbos_account_change_event.json":
        ("DocType", "HBOS Account Change Event", "HBOS Portal"),
    "apps/hbos_portal/hbos_portal/hbos_portal/doctype/hbos_account_security/hbos_account_security.json":
        ("DocType", "HBOS Account Security", "HBOS Portal"),
    "apps/hbos_portal/hbos_portal/hbos_portal/doctype/hbos_position/hbos_position.json":
        ("DocType", "HBOS Position", "HBOS Portal"),
    "apps/hbos_portal/hbos_portal/hbos_portal/doctype/hbos_position_revision/hbos_position_revision.json":
        ("DocType", "HBOS Position Revision", "HBOS Portal"),
    "apps/hbos_portal/hbos_portal/hbos_portal/doctype/hbos_personnel_assignment/hbos_personnel_assignment.json":
        ("DocType", "HBOS Personnel Assignment", "HBOS Portal"),
    "apps/hbos_portal/hbos_portal/hbos_portal/doctype/hbos_personnel_assignment_revision/hbos_personnel_assignment_revision.json":
        ("DocType", "HBOS Personnel Assignment Revision", "HBOS Portal"),
    "apps/hbos_portal/hbos_portal/hbos_portal/doctype/hbos_organization_command_receipt/hbos_organization_command_receipt.json":
        ("DocType", "HBOS Organization Command Receipt", "HBOS Portal"),
    "apps/hbos_portal/hbos_portal/hbos_portal/doctype/hbos_organization_write_lock/hbos_organization_write_lock.json":
        ("DocType", "HBOS Organization Write Lock", "HBOS Portal"),
    "apps/hbos_portal/hbos_portal/hbos_portal/doctype/hbos_organization_management_policy/hbos_organization_management_policy.json":
        ("DocType", "HBOS Organization Management Policy", "HBOS Portal"),
    "apps/hbos_portal/hbos_portal/hbos_portal/doctype/hbos_organization_management_policy_revision/hbos_organization_management_policy_revision.json":
        ("DocType", "HBOS Organization Management Policy Revision", "HBOS Portal"),
}


class RegisteredModelContracts(unittest.TestCase):
    def test_exact_twelve_paths_and_actual_json_identities(self):
        self.assertEqual(scope.APPROVED_DOCTYPES, EXPECTED_MODELS)
        for relative, expected in EXPECTED_MODELS.items():
            with self.subTest(path=relative):
                metadata = json.loads((REPOSITORY / relative).read_text(encoding="utf-8"))
                self.assertEqual(tuple(metadata.get(key) for key in ("doctype", "name", "module")), expected)
        self.assertEqual(scope.check_doctype_scope(REPOSITORY), [])

    def test_four_existing_account_models_retain_native_permission_contracts(self):
        read_only = [{"role": "HBOS Account Handover Manager", "read": 1}]
        system_manager = [{"create": 1, "delete": 1, "email": 1, "export": 1,
                           "print": 1, "read": 1, "report": 1, "role": "System Manager",
                           "share": 1, "write": 1}]
        for relative, (_, name, _) in EXPECTED_MODELS.items():
            if name not in ("HBOS External Identity", "HBOS Account Operation",
                            "HBOS Account Change Event", "HBOS Account Security"):
                continue
            with self.subTest(model=name):
                metadata = json.loads((REPOSITORY / relative).read_text(encoding="utf-8"))
                self.assertEqual(metadata["allow_rename"], 0)
                self.assertFalse(metadata.get("allow_import", 0))
                self.assertEqual(metadata["permissions"], system_manager if name == "HBOS External Identity" else read_only)


class TemporaryScopeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="portal-doctype-scope-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        for relative, identity in EXPECTED_MODELS.items():
            self.write(relative, dict(zip(("doctype", "name", "module"), identity)))
        self.position_path = "apps/hbos_portal/hbos_portal/hbos_portal/doctype/hbos_position/hbos_position.json"
        self.position = dict(doctype="DocType", name="HBOS Position", module="HBOS Portal")

    def write(self, relative, payload):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def assert_refused(self, relative, reason):
        failures = scope.check_doctype_scope(self.root)
        self.assertTrue(any(relative in failure and reason in failure for failure in failures), failures)
        return failures

    def test_all_twelve_registered_models_pass(self):
        self.assertEqual(scope.check_doctype_scope(self.root), [])

    def test_unknown_model_in_doctype_tree_is_rejected(self):
        relative = "apps/hbos_portal/hbos_portal/hbos_portal/doctype/rogue/rogue.json"
        self.write(relative, dict(doctype="DocType", name="Rogue", module="HBOS Portal"))
        self.assert_refused(relative, "unapproved DocType path")

    def test_unknown_json_in_doctype_tree_cannot_hide_its_identity(self):
        relative = "apps/hbos_portal/hbos_portal/hbos_portal/doctype/rogue/arbitrary.json"
        self.write(relative, {})
        self.assert_refused(relative, "unapproved DocType path")

    def test_every_approved_filename_is_rejected_in_other_paths(self):
        for relative, identity in EXPECTED_MODELS.items():
            wrong = "apps/hbos_portal/rogue/" + Path(relative).name
            with self.subTest(path=wrong):
                path = self.write(wrong, dict(zip(("doctype", "name", "module"), identity)))
                self.assert_refused(wrong, "unapproved DocType path")
                path.unlink()

    def test_doc_type_declaration_outside_doctype_tree_is_rejected(self):
        relative = "apps/hbos_portal/fixtures/unapproved.json"
        self.write(relative, dict(doctype="DocType", name="Hidden Model", module="Other Module"))
        self.assert_refused(relative, "unapproved DocType path")

    def test_fixture_array_cannot_hide_unapproved_doc_type_declarations(self):
        relative = "apps/hbos_portal/fixtures/unapproved.json"
        self.write(relative, [{"doctype": "DocType", "name": "Hidden Model", "module": "HBOS Portal"}])
        self.assert_refused(relative, "embedded DocType declarations are not allowed")
        self.assert_refused(relative, "unapproved DocType path")

    def test_embedded_model_in_registered_file_is_rejected(self):
        self.write(self.position_path, {**self.position, "extra": [self.position]})
        self.assert_refused(self.position_path, "embedded DocType declarations are not allowed")
        self.assert_refused(self.position_path, "duplicate model identity")

    def test_registered_model_moved_to_wrong_path_is_rejected(self):
        (self.root / self.position_path).unlink()
        relative = "apps/hbos_portal/other/doctype/hbos_position/hbos_position.json"
        self.write(relative, self.position)
        self.assert_refused(relative, "unapproved DocType path")
        self.assert_refused(self.position_path, "required registered DocType file is missing")

    def test_each_registered_model_rejects_identity_field_tampering(self):
        for relative, identity in EXPECTED_MODELS.items():
            original = dict(zip(("doctype", "name", "module"), identity))
            for field in ("doctype", "name", "module"):
                with self.subTest(path=relative, field=field):
                    self.write(relative, {**original, field: "Unapproved"})
                    self.assert_refused(relative, "identity mismatch for " + field)
            self.write(relative, original)

    def test_duplicate_model_identity_reports_both_paths(self):
        relative = "apps/hbos_portal/z_rogue/hbos_position.json"
        self.write(relative, self.position)
        failures = self.assert_refused(relative, "duplicate model identity 'HBOS Position'")
        self.assertTrue(any(relative in failure and self.position_path in failure for failure in failures), failures)

    def test_duplicate_name_is_rejected_even_with_a_different_module(self):
        relative = "apps/hbos_portal/z_rogue/model.json"
        self.write(relative, {**self.position, "module": "Another Module"})
        self.assert_refused(relative, "duplicate model identity")

    def test_missing_existing_account_model_is_rejected(self):
        relative = next(path for path in EXPECTED_MODELS if path.endswith("hbos_account_security.json"))
        (self.root / relative).unlink()
        self.assert_refused(relative, "required registered DocType file is missing")

    def test_malformed_json_reports_file_and_location(self):
        (self.root / self.position_path).write_text('{"doctype":\n', encoding="utf-8")
        self.assert_refused(self.position_path, "invalid JSON at line 2, column 1")

    def test_duplicate_json_key_cannot_shadow_model_identity(self):
        (self.root / self.position_path).write_text(
            '{"doctype":"DocType","name":"Rogue","name":"HBOS Position","module":"HBOS Portal"}',
            encoding="utf-8")
        self.assert_refused(self.position_path, "duplicate JSON key 'name'")

    def test_excessive_json_nesting_reports_file_and_refusal_reason(self):
        depth = sys.getrecursionlimit() + 50
        (self.root / self.position_path).write_text("[" * depth + "0" + "]" * depth, encoding="utf-8")
        self.assert_refused(self.position_path, "recursion")

    def test_registered_file_requires_json_object(self):
        self.write(self.position_path, [self.position])
        self.assert_refused(self.position_path, "DocType JSON must be an object")

    def test_ordinary_non_model_json_outside_doctype_tree_is_allowed(self):
        self.write("apps/hbos_portal/fixtures/non_model.json", {"doctype": "Role", "name": "Synthetic Role"})
        self.write("apps/hbos_portal/fixtures/list.json", [{"label": "Synthetic"}])
        self.assertEqual(scope.check_doctype_scope(self.root), [])

    def test_malformed_json_outside_doctype_tree_is_not_silently_skipped(self):
        relative = "apps/hbos_portal/fixtures/hidden.json"
        self.write(relative, {}).write_text("{", encoding="utf-8")
        self.assert_refused(relative, "invalid JSON")

    def test_symbolic_link_cannot_redirect_a_registered_json(self):
        original = self.root / self.position_path
        original.unlink()
        outside = self.write("outside/position.json", self.position)
        original.symlink_to(outside)
        self.assert_refused(self.position_path, "symbolic links are not allowed")

    def test_symbolic_link_directory_cannot_hide_additional_models(self):
        outside = self.write("outside/hidden.json", {**self.position, "name": "Hidden Model"})
        relative = "apps/hbos_portal/hidden"
        (self.root / relative).symlink_to(outside.parent, target_is_directory=True)
        self.assert_refused(relative, "symbolic links are not allowed")

    def test_cli_failure_has_nonzero_exit_and_actionable_file_reason(self):
        relative = "apps/hbos_portal/rogue/hbos_position.json"
        self.write(relative, self.position)
        result = subprocess.run([sys.executable, str(SCRIPT), "--root", str(self.root)],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Portal DocType scope FAIL", result.stderr)
        self.assertIn(relative + ": unapproved DocType path", result.stderr)

    def test_cli_success_reports_complete_registry(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--root", str(self.root)],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("12 exact model paths and JSON identities", result.stdout)


if __name__ == "__main__":
    unittest.main()
