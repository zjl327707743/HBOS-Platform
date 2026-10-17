import unittest

from hbos_portal.contracts.access import AccessContext, AccessValidationError
from hbos_portal.contracts.manifest import AppManifest, ManifestValidationError

from .fake_providers import manifest_for


class ContractTests(unittest.TestCase):
    def test_manifest_accepts_contract_v1(self):
        manifest = AppManifest.from_mapping(manifest_for("demo"))
        self.assertEqual("demo", manifest.id)
        self.assertEqual("/hbos/demo", manifest.route)

    def test_manifest_rejects_non_hbos_route(self):
        value = manifest_for("demo")
        value["route"] = "/app/demo"
        with self.assertRaises(ManifestValidationError):
            AppManifest.from_mapping(value)

    def test_access_context_requires_matching_app_id(self):
        with self.assertRaises(AccessValidationError):
            AccessContext.from_mapping(
                {
                    "app_id": "other",
                    "can_enter": True,
                },
                expected_app_id="demo",
            )


if __name__ == "__main__":
    unittest.main()
