"""Real audit functions against bounded in-memory rows and real temporary files.

Database fault injection is a test fixture, not an authorization substitute.
The immutable legacy vectors were captured from the original v1/v2 source.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from hb_lims_app.hbos_lims import workflow_contract  # Load real package parents before the isolated service.


APP = Path(__file__).resolve().parents[1] / "hb_lims_app" / "hbos_lims"
PAYLOAD = {
    "name": "AUDIT-0001", "log_type": "修改", "doctype_target": "HBOS Sample",
    "doc_name": "AUDIT-TARGET", "action_text": "action|qualifier", "field_changed": "result",
    "old_value": "旧值\nA|B", "new_value": "new|value", "reason": "native-proof",
    "user": "audit-manager@test.local", "created_at": "2026-10-18 08:00:00.123456",
}
LEGACY_VECTORS = {
    "1": "77f9563da4eb7a2d8f4d0321185cff938539c699",
    "2": "31b3c15513ccbdcb10c633848112a8d1b62910dcab6963316ee91300d68d93b1",
}


class Row(dict):
    def __getattr__(self, name):
        # copy/pickle probes missing protocol hooks on Python 3.10.
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        return self.get(name)


class AuditDatabase(types.ModuleType):
    def __init__(self):
        super().__init__("frappe")
        self.rows = []
        self.calls = []
        self.session = types.SimpleNamespace(user="audit-manager@test.local")
        self.utils = types.SimpleNamespace(now=lambda: "2026-10-18 09:00:00.123456")
        self.db = types.SimpleNamespace(count=lambda doctype: len(self.rows), get_value=self.get_value)
        self.whitelist = lambda *args, **kwargs: lambda fn: fn

    def get_all(self, doctype, *, fields, order_by, limit_page_length, limit_start=0):
        assert doctype == "HBOS Audit Log"
        self.calls.append((fields, limit_start, limit_page_length))
        rows = sorted(self.rows, key=lambda row: (str(row["created_at"]), row["name"]),
                      reverse="desc" in order_by)
        return [Row({field: row.get(field) for field in fields})
                for row in rows[limit_start:limit_start + limit_page_length]]

    def get_value(self, doctype, name, fields, as_dict=False):
        assert doctype == "HBOS Audit Log" and as_dict
        row = next((row for row in self.rows if row["name"] == name), None)
        return Row({field: row.get(field) for field in fields}) if row else None


def load_real_services(database):
    # Only unrelated imports/quality methods are omitted. All tested audit
    # function bodies and checksum constants are compiled from the actual file.
    source = APP / "lims_service.py"
    tree = ast.parse(source.read_text())
    wanted = {"_checksum", "_audit_checksum_version", "_canonical_audit_payload", "verify_audit_integrity"}
    nodes = [node for node in tree.body if (
        isinstance(node, ast.Assign)
        and any(getattr(target, "id", "").startswith("CHECKSUM_") for target in node.targets)
    ) or (isinstance(node, ast.FunctionDef) and node.name in wanted)]
    service = types.ModuleType("hb_lims_app.hbos_lims.lims_service")
    service.__dict__.update(frappe=database, hashlib=hashlib, json=json,
                            _check_action=lambda action: None)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), "exec"), service.__dict__)
    spec = importlib.util.spec_from_file_location("audit_anchor_canonical_under_test", APP / "audit_anchor_service.py")
    anchor = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"frappe": database, service.__name__: service}):
        spec.loader.exec_module(anchor)
    return service, anchor


class AuditCanonicalTest(unittest.TestCase):
    def setUp(self):
        self.database = AuditDatabase()
        self.service, self.anchor = load_real_services(self.database)
        self.temp = tempfile.TemporaryDirectory(prefix="hbos-audit-canonical-")
        self.path = str(Path(self.temp.name) / "anchor.log")

    def tearDown(self):
        self.temp.cleanup()

    def row(self, version="3", **changes):
        row = Row({**PAYLOAD, **changes, "checksum_version": version})
        row["checksum"] = self.service._checksum(row, version)
        self.database.rows.append(row)
        return row

    def legacy_anchor(self):
        # Historical file fixture uses the original byte format; not the new
        # writer, and never an in-place migration of a real historical file.
        rows = sorted(self.database.rows, key=lambda row: (row["created_at"], row["name"]))
        digest = hashlib.sha256(b"hbos-audit-history-v1")
        for row in rows:
            digest.update(f"{row['name']}|{row['created_at']}|{row['checksum']}".encode())
        line = {"at": "2026-10-18 08:30:00", "source": "legacy-fixture", "rows": len(rows),
                "digest": digest.hexdigest(), "prev": "genesis"}
        line["anchor"] = hashlib.sha256("|".join([
            line["prev"], str(line["rows"]), line["digest"], line["source"],
        ]).encode()).hexdigest()
        Path(self.path).write_text(json.dumps(line, ensure_ascii=False, sort_keys=True) + "\n")
        return Path(self.path).read_bytes()

    def test_v1_v2_known_vectors_remain_byte_identical(self):
        for version, expected in LEGACY_VECTORS.items():
            with self.subTest(version=version):
                self.assertEqual(expected, self.service._checksum(PAYLOAD, version))

    def test_current_checksum_version_is_three(self):
        self.assertEqual("3", self.service.CHECKSUM_VERSION_CURRENT)

    def test_v3_rejects_the_actual_v2_field_separator_collision(self):
        changed = {**PAYLOAD, "action_text": "action", "field_changed": "qualifier|result"}
        self.assertEqual(self.service._checksum(PAYLOAD, "2"), self.service._checksum(changed, "2"))
        self.assertNotEqual(self.service._checksum(PAYLOAD, "3"), self.service._checksum(changed, "3"))

    def test_v3_preserves_nonempty_falsy_values(self):
        empty = self.service._checksum({**PAYLOAD, "reason": ""}, "3")
        for value in (0, False):
            with self.subTest(value=value):
                self.assertNotEqual(empty, self.service._checksum({**PAYLOAD, "reason": value}, "3"))

    def test_unknown_checksum_versions_do_not_fall_back(self):
        for version in (0, False, "4", "garbage"):
            with self.subTest(version=version):
                with self.assertRaises(ValueError):
                    self.service._checksum(PAYLOAD, version)

    def test_verify_preserves_legacy_count_and_exposes_v2_weak_coverage(self):
        for index, version in enumerate(("", "2", "3")):
            self.row(version or "1", name=f"AUDIT-{index:04d}")["checksum_version"] = version
        before = copy.deepcopy(self.database.rows)
        verdict = self.service.verify_audit_integrity()
        self.assertEqual(3, verdict["checked"])
        self.assertEqual([], verdict["mismatched"])
        self.assertEqual(1, verdict["legacy"])
        self.assertEqual({"1": 1, "2": 1, "3": 1}, verdict.get("versions"))
        self.assertEqual(2, verdict.get("weak_legacy"))
        self.assertEqual(before, self.database.rows)

    def test_verify_lists_unknown_rows_as_unverified_without_mutation(self):
        row = self.row("2")
        row["checksum_version"] = "unknown"
        before = copy.deepcopy(row)
        verdict = self.service.verify_audit_integrity(name=row["name"])
        self.assertEqual([row["name"]], verdict["mismatched"])
        self.assertEqual([row["name"]], verdict.get("unknown"))
        self.assertEqual(before, row)

    def test_new_anchor_has_explicit_version_and_payload_coverage(self):
        self.row()
        line = self.anchor.write_anchor_at(self.path, source="test")
        verdict = self.anchor.verify_anchor_at(self.path)
        self.assertEqual(2, line.get("version"))
        self.assertTrue(verdict["ok"])
        self.assertEqual("snapshot_v2", verdict.get("payload_coverage"))

    def test_new_anchor_detects_legacy_collision_even_when_checksum_is_unchanged(self):
        row = self.row("2")
        self.anchor.write_anchor_at(self.path, source="test")
        row.update(action_text="action", field_changed="qualifier|result")
        self.assertEqual(row["checksum"], self.service._checksum(row, "2"))
        self.assertFalse(self.anchor.verify_anchor_at(self.path)["ok"])

    def test_new_anchor_detects_payload_and_checksum_both_changed(self):
        row = self.row()
        self.anchor.write_anchor_at(self.path, source="test")
        row["reason"] = "rewritten with a matching new checksum"
        row["checksum"] = self.service._checksum(row, "3")
        self.assertEqual([], self.service.verify_audit_integrity()["mismatched"])
        self.assertFalse(self.anchor.verify_anchor_at(self.path)["ok"])

    def test_delete_insert_reorder_are_detected_and_ordinary_append_is_allowed(self):
        self.row(name="AUDIT-0001")
        self.row(name="AUDIT-0002", created_at="2026-10-18 08:01:00")
        self.anchor.write_anchor_at(self.path, source="test")
        baseline = copy.deepcopy(self.database.rows)
        for kind in ("delete", "insert", "reorder"):
            with self.subTest(kind=kind):
                self.database.rows[:] = copy.deepcopy(baseline)
                if kind == "delete":
                    self.database.rows.pop()
                elif kind == "insert":
                    self.row(name="AUDIT-0000", created_at="2026-10-18 07:00:00")
                else:
                    self.database.rows[1]["created_at"] = "2026-10-18 07:00:00"
                self.assertFalse(self.anchor.verify_anchor_at(self.path)["ok"])
        self.database.rows[:] = copy.deepcopy(baseline)
        self.row(name="AUDIT-0003", created_at="2026-10-18 10:00:00")
        self.assertTrue(self.anchor.verify_anchor_at(self.path)["ok"])

    def test_writer_refuses_inconsistent_prefix_without_changing_file_bytes(self):
        row = self.row()
        self.anchor.write_anchor_at(self.path, source="first")
        before = Path(self.path).read_bytes()
        row["checksum"] = "0" * 64
        self.assertFalse(self.anchor.verify_anchor_at(self.path)["ok"])
        with self.assertRaises(ValueError):
            self.anchor.write_anchor_at(self.path, source="must-not-reanchor")
        self.assertEqual(before, Path(self.path).read_bytes())

    def test_mixed_legacy_anchor_upgrade_preserves_old_bytes_rows_and_weakness_labels(self):
        self.row("1", name="AUDIT-0001")
        self.row("2", name="AUDIT-0002")
        before_rows = copy.deepcopy(self.database.rows)
        old_bytes = self.legacy_anchor()
        legacy = self.anchor.verify_anchor_at(self.path)
        self.assertTrue(legacy["ok"])
        self.assertEqual("legacy_checksum_only", legacy.get("payload_coverage"))
        self.anchor.write_anchor_at(self.path, source="first-payload-snapshot")
        current = self.anchor.verify_anchor_at(self.path)
        self.assertTrue(current["ok"])
        self.assertTrue(Path(self.path).read_bytes().startswith(old_bytes))
        self.assertEqual(before_rows, self.database.rows)
        self.assertEqual(2, current.get("weak_legacy"))
        self.assertEqual("snapshot_v2", current.get("payload_coverage"))

    def test_legacy_coverage_is_not_retroactively_upgraded(self):
        row = self.row("2")
        self.legacy_anchor()
        row.update(action_text="action", field_changed="qualifier|result")
        # The old format cannot expose this collision; upgrading must neither
        # lie about that fact nor permanently block a new observed snapshot.
        self.assertTrue(self.anchor.verify_anchor_at(self.path)["ok"])
        self.anchor.write_anchor_at(self.path, source="first-payload-snapshot")
        verdict = self.anchor.verify_anchor_at(self.path)
        self.assertTrue(verdict["ok"])
        self.assertEqual(1, verdict.get("weak_legacy"))
        self.assertIn("建立时点", verdict.get("coverage_note", ""))
        row.update(action_text=PAYLOAD["action_text"], field_changed=PAYLOAD["field_changed"])
        self.assertFalse(self.anchor.verify_anchor_at(self.path)["ok"])

    def test_unknown_anchor_version_fails_closed_and_writer_keeps_bytes(self):
        self.row()
        self.legacy_anchor()
        line = json.loads(Path(self.path).read_text())
        line["version"] = 99
        Path(self.path).write_text(json.dumps(line) + "\n")
        before = Path(self.path).read_bytes()
        self.assertFalse(self.anchor.verify_anchor_at(self.path)["ok"])
        with self.assertRaises(ValueError):
            self.anchor.write_anchor_at(self.path, source="unknown-version")
        self.assertEqual(before, Path(self.path).read_bytes())

    def test_new_anchor_binds_timestamp_and_unknown_row_versions_cannot_be_anchored(self):
        row = self.row()
        self.anchor.write_anchor_at(self.path, source="test")
        original = Path(self.path).read_bytes()
        line = json.loads(original)
        line["at"] = "1900-01-01 00:00:00"
        Path(self.path).write_text(json.dumps(line) + "\n")
        self.assertFalse(self.anchor.verify_anchor_at(self.path)["ok"])
        Path(self.path).write_bytes(original)
        row["checksum_version"] = 0
        self.assertFalse(self.anchor.verify_anchor_at(self.path)["ok"])
        with self.assertRaises(ValueError):
            self.anchor.write_anchor_at(self.path, source="unknown-row")
        self.assertEqual(original, Path(self.path).read_bytes())

    def test_history_chunk_size_does_not_change_the_payload_digest(self):
        for index in range(5):
            self.row(name=f"AUDIT-{index:04d}")
        with patch.object(self.anchor, "_CHUNK", 1):
            first = self.anchor.write_anchor_at(self.path, source="one")
        with patch.object(self.anchor, "_CHUNK", 3):
            second = self.anchor.write_anchor_at(self.path, source="three")
        self.assertEqual(first["digest"], second["digest"])
        self.assertTrue(self.anchor.verify_anchor_at(self.path)["ok"])

    def test_writer_reads_snapshot_after_acquiring_the_append_lock(self):
        self.row(name="AUDIT-0001")
        actual_flock = self.anchor.fcntl.flock
        interleaved = False

        def writer_b_first(fd, operation):
            nonlocal interleaved
            if operation == self.anchor.fcntl.LOCK_EX and not interleaved:
                interleaved = True
                self.row(name="AUDIT-0002", created_at="2026-10-18 08:01:00")
                self.anchor.write_anchor_at(self.path, source="writer-b-first-lock")
            return actual_flock(fd, operation)

        # B legitimately acquires the real file lock before A. Only scheduling
        # is injected; both writers execute the actual persistence functions.
        with patch.object(self.anchor.fcntl, "flock", writer_b_first):
            self.anchor.write_anchor_at(self.path, source="writer-a-delayed-lock")
        lines = [json.loads(line) for line in Path(self.path).read_text().splitlines()]
        self.assertEqual([2, 2], [line["rows"] for line in lines])
        self.database.rows.pop()
        self.assertFalse(self.anchor.verify_anchor_at(self.path)["ok"],
                         "删除曾被任一锚覆盖的尾行不能因快照倒退而消失")

    def test_validly_hashed_decreasing_history_cannot_hide_an_earlier_prefix(self):
        self.row(name="AUDIT-0001")
        self.row(name="AUDIT-0002", created_at="2026-10-18 08:01:00")
        for earlier_version in (1, 2):
            with self.subTest(earlier_version=earlier_version):
                Path(self.path).unlink(missing_ok=True)
                if earlier_version == 1:
                    self.legacy_anchor()
                    first = json.loads(Path(self.path).read_text())
                else:
                    first = self.anchor.write_anchor_at(self.path, source="first")
                invalid = {"version": 2, "at": "2026-10-18 09:30:00", "source": "stale-snapshot",
                           "rows": 1, "digest": self.anchor.history_digest(limit=1, version=2),
                           "prev": first["anchor"]}
                invalid["anchor"] = self.anchor._anchor_hash(invalid["prev"], invalid["rows"],
                    invalid["digest"], invalid["source"], version=2, at=invalid["at"])
                with open(self.path, "a", encoding="utf-8") as handle:
                    handle.write(json.dumps(invalid) + "\n")
                before = Path(self.path).read_bytes()
                self.assertFalse(self.anchor.verify_anchor_at(self.path)["ok"])
                with self.assertRaises(ValueError):
                    self.anchor.write_anchor_at(self.path, source="must-not-launder-decreasing-prefix")
                self.assertEqual(before, Path(self.path).read_bytes())


if __name__ == "__main__":
    unittest.main()
