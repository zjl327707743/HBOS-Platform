import unittest

from hbos_portal.contracts.errors import PortalException
from hbos_portal.services.access import (
    SEMANTIC_ACCESS_REQUIREMENTS,
    require_provider_capability,
)
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

    def test_lims_semantic_capability_gates_are_explicit(self):
        self.assertEqual(
            {
                ("lims", "results"): "lims.results.read",
                ("lims", "ledger"): "lims.ledger.read",
                ("lims", "retains"): "lims.retention.read",
            },
            SEMANTIC_ACCESS_REQUIREMENTS,
        )

        class _Provider:
            def access_context(self):
                return {
                    "app_id": "lims",
                    "can_enter": True,
                    "capabilities": [
                        "lims.results.read",
                        "lims.ledger.read",
                        "lims.retention.read",
                    ],
                    "scopes": {},
                }

        class _Manifest:
            id = "lims"

        entry = type("Entry", (), {
            "manifest": _Manifest(),
            "provider": _Provider(),
        })()

        for capability in ("results", "ledger", "retains"):
            with self.subTest(capability=capability):
                self.assertTrue(require_provider_capability(entry, capability).can_enter)

        entry.provider = type("Provider", (), {
            "access_context": lambda self: {
                "app_id": "lims",
                "can_enter": True,
                "capabilities": [],
                "scopes": {},
            }
        })()
        with self.assertRaises(PortalException) as raised:
            require_provider_capability(entry, "ledger")
        self.assertEqual("FORBIDDEN", raised.exception.error.code)

        entry.provider = type("Provider", (), {
            "access_context": lambda self: {
                "app_id": "lims",
                "can_enter": False,
                "capabilities": [],
                "scopes": {},
            }
        })()
        with self.assertRaises(PortalException) as raised:
            require_provider_capability(entry, "results")
        self.assertEqual("FORBIDDEN", raised.exception.error.code)


if __name__ == "__main__":
    unittest.main()
