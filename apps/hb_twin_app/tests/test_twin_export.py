from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

from test_twin_bundles import glb
from hb_twin_app.hb_twin.model_members import inspect_model

spec = importlib.util.spec_from_file_location("twin_subset", Path(__file__).resolve().parents[3] / "scripts/twin/subset_glb.py")
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)


class ExportBoundary(unittest.TestCase):
    def test_explicit_root_repack_retains_identity_and_numerical_transform(self):
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            source = root / "source.glb"
            glb(source, duplicate=True)
            before = source.read_bytes()
            result = exporter.subset(source, ["fixture-0"], root / "candidate.glb", root / "evidence.json")
            checked = inspect_model(root / "candidate.glb")
            self.assertEqual(["fixture-0"], checked["node_ids"])
            self.assertEqual([], checked["unreferenced_meshes"])
            self.assertEqual(result["source_subtree_bbox"], result["candidate_bbox"])
            self.assertEqual(before, source.read_bytes())

    def test_source_and_existing_deliverables_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            source = root / "source.glb"
            glb(source)
            before = source.read_bytes()
            with self.assertRaisesRegex(ValueError, "overwrite"):
                exporter.subset(source, ["fixture-0"], source, root / "evidence.json")
            self.assertEqual(before, source.read_bytes())

    def test_private_output_and_evidence_cannot_be_written_inside_git(self):
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            source = root / "source.glb"
            glb(source)
            repository = root / "repository"
            repository.mkdir()
            (repository / ".git").write_text("gitdir: test-worktree")
            with self.assertRaisesRegex(ValueError, "outside Git"):
                exporter.subset(source, ["fixture-0"], repository / "private.glb", root / "evidence.json")
            self.assertFalse((repository / "private.glb").exists())


if __name__ == "__main__":
    unittest.main()
