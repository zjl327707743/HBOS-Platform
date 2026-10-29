from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from hb_twin_app.hb_twin.assets import load_asset, load_component_mapping
from hb_twin_app.hb_twin.errors import TwinError
from hb_twin_app.hb_twin.policy import policy_for_subject
from hb_twin_app.hb_twin.portal.manifest import get_manifest


POLICY = {
    "subjects": {
        "pilot@example.test": {
            "enabled": True,
            "capabilities": ["twin.view"],
            "equipment_ids": ["M607B"],
            "policy_revision": "twin-policy-test-1",
        }
    }
}


def make_asset(root: Path) -> tuple[Path, str]:
    equipment_root = root / "M607B"
    equipment_root.mkdir()
    model = equipment_root / "model.glb"
    model.write_bytes(b"glTF-test-model")
    digest = hashlib.sha256(model.read_bytes()).hexdigest()
    (equipment_root / "model_manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "equipment_id": "M607B",
                "label": "M607B",
                "site_identity": "WD102=M607B",
                "model_revision": "fixture-1",
                "viewer_revision": "viewer-test-1",
                "mapping_revision": "mapping-test-1",
                "fit_disclaimer": "展示拟合·非实测",
                "connection_state": "not_connected",
                "model": {
                    "filename": "model.glb",
                    "sha256": digest,
                    "size_bytes": model.stat().st_size,
                },
            }
        ),
        encoding="utf-8",
    )
    (equipment_root / "component_mappings.json").write_text(
        json.dumps(
            {
                "mapping_revision": "mapping-test-1",
                "items": {
                    "asset-1": {
                        "status": "verified",
                        "display_name": "主罐体",
                        "component_id": "component-vessel",
                        "knowledge_link_available": False,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    return model, digest


class TwinPolicyTest(unittest.TestCase):
    def test_guest_unknown_and_unlisted_equipment_are_denied(self):
        self.assertFalse(policy_for_subject(POLICY, "Guest").can_enter)
        self.assertFalse(policy_for_subject(POLICY, "unknown@example.test").can_enter)
        policy = policy_for_subject(POLICY, "pilot@example.test")
        with self.assertRaises(TwinError):
            policy.require_equipment("M660B")

    def test_manifest_registers_native_stable_route(self):
        manifest = get_manifest()
        self.assertEqual("/hbos/twin", manifest["route"])
        self.assertEqual("native", manifest["migration_mode"])

    def test_default_internal_policy_allows_non_pilot_only_when_eligible(self):
        config = {
            "default_internal": {
                "enabled": True,
                "capabilities": ["twin.view"],
                "equipment_ids": ["M607B"],
                "policy_revision": "internal-v1",
            },
            "subjects": {},
        }
        policy_for_subject(
            config,
            "employee@example.test",
            internal_user=True,
        ).require_equipment("M607B")
        self.assertFalse(
            policy_for_subject(
                config,
                "external@example.test",
                internal_user=False,
            ).can_enter
        )

    def test_explicit_administrator_scope_is_supported(self):
        config = {
            "default_internal": {"enabled": False},
            "subjects": {
                "Administrator": {
                    "enabled": True,
                    "capabilities": ["twin.view"],
                    "equipment_ids": ["M607B"],
                }
            },
        }
        policy_for_subject(
            config,
            "Administrator",
            internal_user=False,
        ).require_equipment("M607B")


class TwinAssetTest(unittest.TestCase):
    def test_realized_manifest_validates_hash_and_hides_server_path(self):
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            _, digest = make_asset(root)
            asset = load_asset(root, "M607B")
            browser = asset.browser_manifest()

            self.assertEqual(digest, browser["model_sha256"])
            self.assertNotIn(str(root), str(browser))
            self.assertIn("equipment_id=M607B", browser["model_url"])

    def test_hash_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            model, _ = make_asset(root)
            model.write_bytes(b"tampered")
            with self.assertRaisesRegex(TwinError, "完整性"):
                load_asset(root, "M607B")

    def test_symlinked_model_is_rejected(self):
        with tempfile.TemporaryDirectory() as value, tempfile.TemporaryDirectory() as outside:
            root = Path(value)
            model, _ = make_asset(root)
            external = Path(outside) / "external.glb"
            external.write_bytes(model.read_bytes())
            model.unlink()
            model.symlink_to(external)
            with self.assertRaisesRegex(TwinError, "符号链接"):
                load_asset(root, "M607B")

    def test_unsafe_equipment_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as value:
            with self.assertRaisesRegex(TwinError, "设备标识"):
                load_asset(value, "../M607B")

    def test_unknown_asset_id_returns_unverified_not_guessed_mapping(self):
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            make_asset(root)
            mapping = load_component_mapping(root, "M607B", "unknown", "mapping-test-1")
            self.assertEqual("unverified", mapping["status"])
            self.assertEqual("待核部件", mapping["display_name"])
            self.assertFalse(mapping["knowledge_link_available"])


if __name__ == "__main__":
    unittest.main()
