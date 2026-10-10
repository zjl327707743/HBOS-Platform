"""Synthetic tests only: no Frappe, database, network or real identities."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("iam_source_inventory", Path(__file__).parents[1] / "iam_source_inventory.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
SHA = "a" * 40


class SourceInventoryTests(unittest.TestCase):
    def test_whitelist_and_guards(self):
        rows = MODULE.inspect_source('@frappe.whitelist()\ndef read():\n frappe.only_for(["Synthetic Role"])\n frappe.get_all("Example")\n', "x.py")
        self.assertEqual(rows[0]["guard_calls_observed"], ["frappe.only_for"])
        self.assertEqual(rows[0]["review_markers"], ["GET_ALL"])
        self.assertEqual(rows[0]["authorization_verdict"], "NOT_EVALUATED")

    def test_guests_and_dynamic_values(self):
        for expression, expected in (("True", True), ("False", False), ("setting", "UNKNOWN")):
            rows = MODULE.inspect_source(f'@frappe.whitelist(allow_guest={expression})\ndef read():\n pass\n', "x.py")
            self.assertEqual(rows[0]["decorator_allow_guest"], expected)

    def test_kwargs_unknown(self):
        rows = MODULE.inspect_source('@frappe.whitelist(**options)\ndef read():\n pass\n', "x.py")
        self.assertEqual(rows[0]["decorator_allow_guest"], "UNKNOWN")

    def test_nested_guard_not_attributed_to_parent(self):
        rows = MODULE.inspect_source('@frappe.whitelist()\ndef read():\n def unused():\n  frappe.only_for([])\n pass\n', "x.py")
        self.assertEqual(rows[0]["guard_calls_observed"], [])

    def test_source_literals_not_exported(self):
        rows = MODULE.inspect_source('@frappe.whitelist()\ndef read(value="SYNTHETIC_SECRET"): \n frappe.db.sql("SYNTHETIC_SQL")\n doc.save(ignore_permissions=True)\n', "x.py")
        payload = json.dumps(rows)
        self.assertNotIn("SYNTHETIC_SECRET", payload)
        self.assertNotIn("SYNTHETIC_SQL", payload)
        self.assertIn("IGNORE_PERMISSIONS_ARGUMENT", payload)

    def test_async_endpoint(self):
        rows = MODULE.inspect_source('@frappe.whitelist\nasync def read():\n pass\n', "x.py")
        self.assertEqual(rows[0]["function"], "read")

    def test_unlisted_function_not_endpoint(self):
        self.assertEqual(MODULE.inspect_source('def helper():\n frappe.get_all("Example")\n', "x.py"), [])

    def test_missing_roots_partial(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = MODULE.scan_repository(Path(tmp), SHA)
            self.assertEqual(report["coverage_status"], "PARTIAL")
            self.assertEqual(len(report["gaps"]), len(MODULE.APPS))

    def test_all_roots_scanned_without_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for app in MODULE.APPS:
                folder = root / "apps" / app / app
                folder.mkdir(parents=True)
                (folder / "api.py").write_text('raise RuntimeError("MUST_NOT_EXECUTE")\n@frappe.whitelist()\ndef read():\n pass\n')
            before = sorted(str(p.relative_to(root)) for p in root.rglob("*"))
            report = MODULE.scan_repository(root, SHA)
            after = sorted(str(p.relative_to(root)) for p in root.rglob("*"))
            self.assertEqual(before, after)
            self.assertEqual(len(report["endpoints"]), len(MODULE.APPS))
            self.assertEqual(report["coverage_status"], "DECLARED_PYTHON_ROOTS_SCANNED")
            self.assertEqual(report["runtime_inventory"], "NOT_RUN")

    def test_symlink_and_parse_error_are_gaps(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "apps" / MODULE.APPS[0] / MODULE.APPS[0]
            folder.mkdir(parents=True)
            target = root / "outside.py"
            target.write_text("PRIVATE_SYNTHETIC_VALUE")
            (folder / "link.py").symlink_to(target)
            (folder / "bad.py").write_text("def broken(")
            report = MODULE.scan_repository(root, SHA)
            self.assertNotIn("PRIVATE_SYNTHETIC_VALUE", json.dumps(report))
            reasons = {row["reason"] for row in report["gaps"]}
            self.assertIn("SYMLINK_FILE", reasons)
            self.assertIn("READ_OR_PARSE_ERROR", reasons)

    def test_invalid_commit_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                MODULE.scan_repository(Path(tmp), "main")


if __name__ == "__main__":
    unittest.main()
