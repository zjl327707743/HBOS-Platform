"""Content, scope and version boundaries using invented triangle fixtures only."""
from __future__ import annotations

import copy
import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hb_twin_app.hb_twin import catalog as api
from hb_twin_app.hb_twin.errors import TwinError
from hb_twin_app.hb_twin.model_members import inspect_model
from hb_twin_app.hb_twin.policy import TwinPolicy


def glb(path, *, duplicate=False, opaque_tail=False, hidden_view_bytes=False):
    body = struct.pack("<9f", 0, 0, 0, 1, 0, 0, 0, 1, 0)
    if hidden_view_bytes:
        body += b"HIDE"
    doc = {"asset": {"version": "2.0"}, "scene": 0, "scenes": [{"nodes": list(range(5))}],
           "nodes": [{"extras": {"asset_id": f"fixture-{i}"}, "mesh": 0} for i in range(5)],
           "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "material": 0}]}],
           "materials": [{}], "accessors": [{"bufferView": 0, "componentType": 5126, "count": 3, "type": "VEC3", "min": [0, 0, 0], "max": [1, 1, 0]}],
           "bufferViews": [{"buffer": 0, "byteLength": len(body)}], "buffers": [{"byteLength": len(body)}]}
    if duplicate:
        doc["meshes"].append(copy.deepcopy(doc["meshes"][0]))
    if opaque_tail:
        body += b"HIDE"
        doc["buffers"][0]["byteLength"] = len(body)
    encoded = json.dumps(doc).encode()
    encoded += b" " * (-len(encoded) % 4)
    path.write_bytes(struct.pack("<4sIII4s", b"glTF", 2, 28 + len(encoded) + len(body), len(encoded), b"JSON")
                     + encoded + struct.pack("<I4s", len(body), b"BIN\0") + body)


def write(path, value):
    path.write_text(json.dumps(value))


def specification(path):
    return {"filename": path.name, "size_bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def policy(scopes=("M606B", "M607B", "M660B"), subject="synthetic", capabilities=("twin.view",)):
    return TwinPolicy(subject, True, capabilities, scopes, "fixture")


def make_bundle(root, entry="M607B", duplicate=False):
    folder = root / entry
    folder.mkdir()
    glb(folder / "model.glb", duplicate=duplicate)
    inspected = inspect_model(folder / "model.glb")
    model = specification(folder / "model.glb")
    scopes = ["M606B", "M607B", "M660B"] if entry == "DUAL" else [entry, "M660B"]
    equipment = ["M606B", "M607B"] if entry == "DUAL" else [entry]
    members = {"entry_id": entry, "model_sha256": model["sha256"], "closure_sha256": inspected["closure_sha256"],
               "members": [{"asset_id": a, "proposed_required_equipment_ids": [equipment[0]]} for a in inspected["node_ids"]],
               "unreferenced_meshes": [{**m, "proposed_required_equipment_ids": scopes} for m in inspected["unreferenced_meshes"]]}
    common = {"entry_id": entry, "model_sha256": model["sha256"], "mapping_revision": "parts-1"}
    write(folder / "membership.json", members)
    write(folder / "parts.json", {**common, "groups": [], "items": {}})
    write(folder / "process.json", {**common, "process_revision": "process-1", "binding_revision": "binding-1", "modes": ["production"],
                                    "bindings": {equipment[0]: {"ids": inspected["node_ids"], "anchor": inspected["node_ids"][0]}}})
    manifest = {"schema": "twin.bundle.v1", "entry_id": entry, "required_equipment_ids": scopes,
                "model_revision": "model-1", "mapping_revision": "parts-1", "process_revision": "process-1", "binding_revision": "binding-1",
                "camera_revision": "camera-1", "demo_revision": "demo-1", "demo_seed": 102,
                "model": model, "members": specification(folder / "membership.json"), "parts": specification(folder / "parts.json"),
                "process": specification(folder / "process.json")}
    write(folder / "bundle.json", manifest)
    write(root / "catalog.json", {"schema": "twin.catalog.v1", "revision": "fixture", "entries": [{"entry_id": entry, "label": entry,
          "entity_type": "scene" if entry == "DUAL" else "device", "equipment_ids": equipment, "required_equipment_ids": scopes}]})
    approve(folder)
    return folder


def approve(folder):
    manifest = json.loads((folder / "bundle.json").read_text())
    write(folder / "approval.json", {"status": "OWNER_PRIVATE_REVIEW_APPROVED", "approval_reference": "unit-test fixture only",
          "subjects": ["synthetic"], "model_sha256": manifest["model"]["sha256"], "members_sha256": manifest["members"]["sha256"]})


def change_resource(folder, kind, mutate):
    manifest = json.loads((folder / "bundle.json").read_text())
    path = folder / manifest[kind]["filename"]
    document = json.loads(path.read_text())
    mutate(document)
    write(path, document)
    manifest[kind] = specification(path)
    write(folder / "bundle.json", manifest)
    approve(folder)


class BundleBoundaries(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.folder = make_bundle(self.root, duplicate=True)

    def denied(self, call, code):
        with self.assertRaises(TwinError) as raised:
            call()
        self.assertEqual(code, raised.exception.code)

    def test_complete_fixture_and_private_manifest(self):
        bundle = api.load_bundle(self.root, "M607B", policy())
        public = bundle.browser_manifest()
        self.assertNotIn(str(self.root), str(public))
        self.assertNotIn("fixture-", str(public))
        self.assertIn("expected_model_sha256=", public["model_url"])
        self.assertEqual("not_connected", public["truth"]["data"])
        self.assertEqual(5, len(api.process_config(bundle)["bindings"]["M607B"]["ids"]))

    def test_missing_accessory_is_denied_before_any_asset_read(self):
        with patch.object(api, "_hashed", side_effect=AssertionError("asset read before scope check")):
            self.denied(lambda: api.load_bundle(self.root, "M607B", policy(("M607B",))), "FORBIDDEN")

    def test_directory_hides_other_machine_and_scene_without_enumeration(self):
        self.assertEqual([], api.catalog(self.root, policy(("M606B",)))["entries"])
        entry = api.catalog(self.root, policy(("M607B",)))["entries"][0]
        self.assertEqual("SCOPE_NOT_READY", entry["availability"])
        self.assertNotIn("M660B", json.dumps(entry))
        with tempfile.TemporaryDirectory() as value:
            make_bundle(Path(value), "DUAL")
            self.assertEqual([], api.catalog(value, policy(("M606B", "M607B")))["entries"])

    def test_guest_missing_capability_and_different_subject_fail(self):
        for p in [policy(subject="Guest"), policy(capabilities=())]:
            self.denied(lambda: api.catalog(self.root, p), "FORBIDDEN")
        self.denied(lambda: api.load_bundle(self.root, "M607B", policy(subject="not-approved")), "MEMBERS_PENDING")

    def test_approval_removal_and_membership_change_revoke_access(self):
        (self.folder / "approval.json").unlink()
        self.denied(lambda: api.load_bundle(self.root, "M607B", policy()), "MEMBERS_PENDING")
        approve(self.folder)
        (self.folder / "membership.json").write_text("{}")
        self.denied(lambda: api.load_bundle(self.root, "M607B", policy()), "ASSET_INTEGRITY_FAILED")

    def test_old_model_mapping_and_process_versions_are_rejected(self):
        for name in ["expected_model_sha256", "expected_mapping_revision", "expected_process_revision"]:
            self.denied(lambda: api.load_bundle(self.root, "M607B", policy(), **{name: "old"}), "ASSET_REVISION_MISMATCH")

    def test_model_tamper_and_symlink_fail_closed(self):
        model = self.folder / "model.glb"
        original = model.read_bytes()
        model.write_bytes(original + b"tamper")
        self.denied(lambda: api.load_bundle(self.root, "M607B", policy()), "ASSET_INTEGRITY_FAILED")
        model.unlink()
        model.symlink_to(self.folder / "parts.json")
        self.denied(lambda: api.load_bundle(self.root, "M607B", policy()), "ASSET_INVALID")

    def test_unreferenced_mesh_cannot_be_omitted_or_assigned_extra_scope(self):
        change_resource(self.folder, "members", lambda d: d["unreferenced_meshes"][0].update(proposed_required_equipment_ids=["M606B"]))
        self.denied(lambda: api.load_bundle(self.root, "M607B", policy()), "ASSET_INVALID")
        change_resource(self.folder, "members", lambda d: d.update(unreferenced_meshes=[]))
        self.denied(lambda: api.load_bundle(self.root, "M607B", policy()), "ASSET_INVALID")

    def test_closure_fingerprint_and_per_member_scope_are_required(self):
        change_resource(self.folder, "members", lambda d: d["members"][0].update(proposed_required_equipment_ids=["M606B"]))
        self.denied(lambda: api.load_bundle(self.root, "M607B", policy()), "ASSET_INVALID")
        change_resource(self.folder, "members", lambda d: d["members"][0].update(proposed_required_equipment_ids=["M607B"]))
        change_resource(self.folder, "members", lambda d: d.update(closure_sha256="old"))
        self.denied(lambda: api.load_bundle(self.root, "M607B", policy()), "ASSET_INVALID")

    def test_cross_model_parts_and_cross_device_mapping_are_rejected(self):
        change_resource(self.folder, "parts", lambda d: d.update(groups=[{"asset_ids": ["other-model"], "equipment_id": "M607B"}]))
        self.denied(lambda: api.load_bundle(self.root, "M607B", policy()), "MAPPING_INVALID")
        change_resource(self.folder, "parts", lambda d: d.update(groups=[]))
        bundle = api.load_bundle(self.root, "M607B", policy())
        for asset, equipment in [("fixture-0", "M606B"), ("other-model", "M607B")]:
            self.denied(lambda: api.component_mapping(bundle, asset, equipment), "MAPPING_INVALID")
        self.assertEqual("unverified", api.component_mapping(bundle, "fixture-0", "M607B")["status"])

    def test_candidate_cannot_become_business_id_and_bad_binding_is_local(self):
        change_resource(self.folder, "parts", lambda d: d.update(items={"fixture-0": {"equipment_id": "M607B", "status": "candidate", "component_id": "guessed", "knowledge_link_available": True}}))
        bundle = api.load_bundle(self.root, "M607B", policy())
        result = api.component_mapping(bundle, "fixture-0", "M607B")
        self.assertIsNone(result["component_id"])
        self.assertFalse(result["knowledge_link_available"])
        change_resource(self.folder, "process", lambda d: d["bindings"]["M607B"]["ids"].__setitem__(0, "other-model"))
        bundle = api.load_bundle(self.root, "M607B", policy())
        self.denied(lambda: api.process_config(bundle), "PROCESS_INCOMPATIBLE")
        self.assertEqual("M607B", bundle.browser_manifest()["entry_id"])

    def test_dual_membership_does_not_make_other_machine_a_valid_target(self):
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            folder = make_bundle(root, "DUAL")
            change_resource(folder, "members", lambda d: d["members"][1].update(proposed_required_equipment_ids=["M607B"]))
            bundle = api.load_bundle(root, "DUAL", policy())
            self.denied(lambda: api.component_mapping(bundle, "fixture-1", "M606B"), "MAPPING_INVALID")
            self.denied(lambda: api.process_config(bundle), "PROCESS_INCOMPATIBLE")

    def test_whole_bin_and_accessor_coverage_are_checked(self):
        for name, options in [("tail", {"opaque_tail": True}), ("view", {"hidden_view_bytes": True})]:
            path = self.root / f"{name}.glb"
            glb(path, **options)
            self.denied(lambda: inspect_model(path), "ASSET_INVALID")


if __name__ == "__main__":
    unittest.main()
