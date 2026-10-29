import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("local_manage", Path(__file__).parents[1] / "manage.py")
manage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manage)


class LocalBoundaryTests(unittest.TestCase):
    def configured(self, root, origin="http://test.localhost:5188"):
        p = root / "config.json"
        p.write_text(json.dumps({"project": "hbos-local", "site": "test.localhost", "origin": origin, "base_compose": str(root / "docker-compose.yml"), "env_file": str(root / "private.env"), "runtime_root": str(root), "release_root": str(root / "release")}))
        p.chmod(0o600)
        return p

    def test_only_fixed_loopback_http(self):
        with tempfile.TemporaryDirectory() as d:
            p = self.configured(Path(d))
            with patch.object(manage.socket, "getaddrinfo", return_value=[(0, 0, 0, "", ("127.0.0.1", 5188))]):
                self.assertEqual(manage.config(p)["port"], 5188)
            for origin in ["http://192.168.1.2:5188", "http://example.com:5188", "https://test.localhost:5188", "http://test.localhost:5188/other", "http://user@test.localhost:5188"]:
                with self.subTest(origin=origin), self.assertRaises(ValueError):
                    manage.config(self.configured(Path(d), origin))

    def test_localhost_resolving_to_external_address_rejected(self):
        with tempfile.TemporaryDirectory() as d, patch.object(manage.socket, "getaddrinfo", return_value=[(0, 0, 0, "", ("192.168.1.2", 5188))]):
            with self.assertRaisesRegex(ValueError, "NOT_LOOPBACK"):
                manage.config(self.configured(Path(d)))

    def test_unknown_database_refused(self):
        c = {"site": "test.localhost", "expected_database": "other"}
        with patch.object(manage, "backend", return_value="target"), patch.object(manage, "run"), patch.object(manage, "capture", return_value='{"db_name":"existing"}'):
            with self.assertRaisesRegex(ValueError, "TARGET_MISMATCH"):
                manage.require_site(c)

    def test_absent_project_never_creates_site(self):
        with patch.object(manage, "release", return_value={}), patch.object(manage, "containers", return_value=[]), patch.object(manage, "compose") as compose:
            with self.assertRaisesRegex(ValueError, "EXISTING_SERVICE_REQUIRED"):
                manage.start({"project": "missing"}, False)
            compose.assert_not_called()

    def test_no_noninteractive_password_reset(self):
        with patch.object(manage, "require_site"), patch.object(manage.sys.stdin, "isatty", return_value=False):
            with self.assertRaisesRegex(ValueError, "INTERACTIVE_TERMINAL_REQUIRED"):
                manage.administrator_password({})


if __name__ == "__main__":
    unittest.main()
