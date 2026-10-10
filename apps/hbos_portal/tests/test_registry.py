import unittest

from hbos_portal.services.registry import build_registry

from .fake_providers import (
    BrokenCapabilityProvider,
    DuplicateProvider,
    UnsupportedProvider,
    VisibleProvider,
)


class RegistryTests(unittest.TestCase):
    def test_loads_valid_provider(self):
        factories = {"visible": VisibleProvider}
        registry = build_registry(
            ["visible"],
            resolver=lambda path: factories[path],
        )
        self.assertIn("visible", registry.entries)
        self.assertEqual([], registry.failures)

    def test_duplicate_app_id_is_removed(self):
        factories = {
            "one": VisibleProvider,
            "two": DuplicateProvider,
        }
        registry = build_registry(
            ["one", "two"],
            resolver=lambda path: factories[path],
        )
        self.assertNotIn("visible", registry.entries)
        self.assertTrue(
            any(x.code == "DUPLICATE_APP_ID" for x in registry.failures)
        )

    def test_unsupported_contract_is_isolated(self):
        registry = build_registry(
            ["unsupported"],
            resolver=lambda _: UnsupportedProvider,
        )
        self.assertEqual({}, registry.entries)
        self.assertEqual(1, len(registry.failures))

    def test_declared_capability_requires_method(self):
        registry = build_registry(
            ["broken"],
            resolver=lambda _: BrokenCapabilityProvider,
        )
        self.assertEqual({}, registry.entries)
        self.assertEqual(1, len(registry.failures))


if __name__ == "__main__":
    unittest.main()
