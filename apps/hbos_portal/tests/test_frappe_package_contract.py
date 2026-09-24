from __future__ import annotations

from pathlib import Path
import unittest


APP_ROOT = Path(__file__).resolve().parents[1]
PYTHON_PACKAGE = APP_ROOT / "hbos_portal"


def scrub_module_name(value: str) -> str:
    return "_".join(value.strip().lower().split())


class FrappePackageContractTest(unittest.TestCase):
    def test_every_declared_frappe_module_has_python_package(self):
        modules_file = PYTHON_PACKAGE / "modules.txt"
        self.assertTrue(modules_file.is_file())

        modules = [
            line.strip()
            for line in modules_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertTrue(modules)

        for module in modules:
            package = PYTHON_PACKAGE / scrub_module_name(module)
            self.assertTrue(
                (package / "__init__.py").is_file(),
                f"Frappe module {module!r} requires package {package}",
            )


if __name__ == "__main__":
    unittest.main()
