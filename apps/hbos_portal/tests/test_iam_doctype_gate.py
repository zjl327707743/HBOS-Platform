from __future__ import annotations

import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ALLOWED = {"hbos_external_identity.json", "hbos_account_operation.json", "hbos_account_change_event.json", "hbos_account_security.json", "hbos_iam_policy.json", "hbos_iam_rule.json", "hbos_iam_change_event.json"}
MODEL_NAMES = {"hbos_external_identity": "HBOS External Identity", "hbos_account_operation": "HBOS Account Operation", "hbos_account_change_event": "HBOS Account Change Event", "hbos_account_security": "HBOS Account Security", "hbos_iam_policy": "HBOS IAM Policy", "hbos_iam_rule": "HBOS IAM Rule", "hbos_iam_change_event": "HBOS IAM Change Event"}


class IAMDocTypeGateTest(unittest.TestCase):
    def command(self):
        text = (ROOT / ".github/workflows/hbos-portal-backend.yml").read_text()
        match = re.search(r"(if find apps/hbos_portal[^\n]+\| grep -q \.; then\n.*?\n\s+fi)", text, re.S)
        self.assertIsNotNone(match)
        command = match.group(1)
        names = set(re.findall(r"! -name ([a-z_]+\.json)", command))
        self.assertEqual(names, ALLOWED)
        self.assertNotIn("HBOS*", command)
        self.assertIn("exit 1", command)
        return command

    def run_gate(self, extra=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "apps/hbos_portal/hbos_portal/hbos_portal/doctype"
            for name in ALLOWED | ({extra} if extra else set()):
                path = root / name.removesuffix(".json") / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('{}')
            return subprocess.run(["bash", "-euo", "pipefail", "-c", self.command()], cwd=directory, capture_output=True).returncode

    def test_exact_seven_approved_model_names_pass_the_actual_shell_gate(self):
        self.assertEqual(self.run_gate(), 0)

    def test_unknown_hbos_model_and_arbitrary_json_still_fail(self):
        for name in ("hbos_iam_arbitrary.json", "unexpected.json"):
            with self.subTest(name=name):
                self.assertNotEqual(self.run_gate(name), 0)

    def test_models_have_no_native_role_permission_fallback(self):
        for slug in ("policy", "rule", "change_event"):
            import json
            path = ROOT / f"apps/hbos_portal/hbos_portal/hbos_portal/doctype/hbos_iam_{slug}/hbos_iam_{slug}.json"
            data = json.loads(path.read_text())
            self.assertEqual(data["permissions"], [])
            self.assertEqual(data["allow_rename"], 0)
            if slug == "rule":
                self.assertEqual(data["istable"], 1)

    def test_model_locations_and_declared_names_cannot_smuggle_an_extra_doctype(self):
        import json
        app = ROOT / "apps/hbos_portal"
        expected = {app / f"hbos_portal/hbos_portal/doctype/{slug}/{slug}.json" for slug in MODEL_NAMES}
        actual = {path for path in app.rglob("*.json") if "/doctype/" in str(path)}
        self.assertEqual(actual, expected)
        for path in actual:
            data = json.loads(path.read_text())
            self.assertEqual(data["name"], MODEL_NAMES[path.stem])
            self.assertEqual(data["module"], "HBOS Portal")
