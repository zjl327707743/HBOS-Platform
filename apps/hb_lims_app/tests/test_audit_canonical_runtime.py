"""Nine native audit/anchor checks for the disposable Owner CI Site.

No quality controller or authorization check is mocked. Labelled synthetic
audit rows are created through audit_log; legacy encodings are fixture-only
assignments before their first commit. Each DB fault is restored to a savepoint,
with the complete audit table and temporary anchor bytes checked in finally.
These tests never rewrite historical business rows or the real anchor path.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path

try:
    import frappe
except ImportError:  # The offline gate must report these as NOT_RUN.
    frappe = None


_SMOKE_READY = frappe is not None and os.environ.get("HBOS_FRAPPE_SMOKE") == "1"
_APP_DIR = str(Path(__file__).resolve().parents[1])
MGR = "r7c-mgr@test.local"
DOCTYPE = "HBOS Audit Log"


def _ensure_app_on_path():
    loaded = sys.modules.get("hb_lims_app.hbos_lims.lims_service")
    if loaded and getattr(loaded, "__file__", "").startswith(_APP_DIR):
        return
    for name in list(sys.modules):
        if name == "hb_lims_app" or name.startswith("hb_lims_app."):
            sys.modules.pop(name, None)
    while _APP_DIR in sys.path:
        sys.path.remove(_APP_DIR)
    sys.path.insert(0, _APP_DIR)


@unittest.skipUnless(_SMOKE_READY, "需要隔离 Frappe Site 且 HBOS_FRAPPE_SMOKE=1")
class TestAuditCanonicalRuntime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.initialized_here = not getattr(getattr(frappe, "local", None), "site", None)
        if cls.initialized_here:
            frappe.init(site=os.environ.get("FRAPPE_SITE", "frontend"),
                        sites_path=os.environ.get("FRAPPE_SITES_PATH", "/home/frappe/frappe-bench/sites"))
            frappe.connect()
        _ensure_app_on_path()
        from hb_lims_app.hbos_lims import audit_anchor_service, lims_service
        cls.svc, cls.anchor = lims_service, audit_anchor_service
        cls.original_user = frappe.session.user
        frappe.set_user("Administrator")
        if not frappe.db.exists("User", MGR) or "LIMS Manager" not in frappe.get_roles(MGR):
            raise AssertionError("缺少原生32项运行器建立的 LIMS Manager：" + MGR)

    @classmethod
    def tearDownClass(cls):
        frappe.db.rollback()
        frappe.set_user(cls.original_user)
        if cls.initialized_here:
            frappe.destroy()

    def setUp(self):
        frappe.db.rollback()
        frappe.set_user("Administrator")
        self.temp = tempfile.TemporaryDirectory(prefix="hbos-audit-v3-native-")
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "anchor.log"
        self.marker = "TEST-HBOS-AUDIT-V3-" + uuid.uuid4().hex[:16]
        self.names = {"1": self._new_row(""), "2": self._new_row("2"), "3": self._new_row("3")}
        # Explicit fixture commit, outside audit_log. Synthetic events remain
        # append-only until the disposable Site is destroyed by the runner.
        frappe.db.commit()
        self.anchor.write_anchor_at(str(self.path), source=self.marker)
        self.assertTrue(self.anchor.verify_anchor_at(str(self.path))["ok"])

    def tearDown(self):
        frappe.db.rollback()
        frappe.set_user("Administrator")

    def _new_row(self, version="3", **changes):
        values = dict(action_text="action|qualifier", field_changed="result",
                      old_value="旧值\nA|B", new_value="新值\nC|D", reason="native-audit-proof")
        values.update(changes)
        name = self.svc.audit_log("修改", "HBOS Sample", self.marker, **values)
        if version != "3":
            # New synthetic fixture only, never a migration of an existing row.
            row = self._row(name)
            frappe.db.set_value(DOCTYPE, name, {
                "checksum_version": version,
                "checksum": self.svc._checksum(row, "1" if version == "" else version),
            }, update_modified=False)
        return name

    def _row(self, name):
        fields = list(dict.fromkeys(["name", "checksum", "checksum_version"] + list(self.svc.CHECKSUM_V2_FIELDS)))
        row = frappe.db.get_value(DOCTYPE, name, fields, as_dict=True)
        self.assertIsNotNone(row, name)
        return row

    def _all_rows(self):
        rows, offset = [], 0
        while True:
            page = frappe.get_all(DOCTYPE, fields=["*"], order_by="created_at asc, name asc",
                                  limit_start=offset, limit_page_length=500)
            rows.extend(dict(row) for row in page)
            if len(page) < 500:
                return rows
            offset += len(page)

    def _database_bytes(self):
        return json.dumps(self._all_rows(), default=str, ensure_ascii=False,
                          sort_keys=True, separators=(",", ":")).encode("utf-8")

    def _verify(self, name):
        previous = frappe.session.user
        frappe.set_user(MGR)
        try:
            return self.svc.verify_audit_integrity(name=name)
        finally:
            frappe.set_user(previous)

    @contextmanager
    def _fault(self, *, restore_file=False):
        """Real DB fault sandbox; all rows and file bytes must be restored."""
        before_db, before_file = self._database_bytes(), self.path.read_bytes()
        savepoint = "audit_v3_" + uuid.uuid4().hex
        frappe.db.savepoint(savepoint)
        try:
            yield
        finally:
            frappe.set_user("Administrator")
            frappe.db.rollback(save_point=savepoint)
            if restore_file:
                self.path.write_bytes(before_file)
            self.assertEqual(before_db, self._database_bytes(), "故障回滚必须恢复全部审计字段/行/顺序")
            self.assertEqual(before_file, self.path.read_bytes(), "故障或拒绝追加不得改变已有锚文件字节")
            self.assertTrue(self.anchor.verify_anchor_at(str(self.path))["ok"], "恢复后原锚必须仍通过")

    def _write_legacy_fixture(self):
        rows = self._all_rows()
        digest = hashlib.sha256(b"hbos-audit-history-v1")
        for row in rows:
            digest.update("{}|{}|{}".format(row["name"], row.get("created_at") or "",
                                          row.get("checksum") or "").encode("utf-8"))
        line = {"at": "2026-10-18 08:30:00", "source": "native-legacy-fixture", "rows": len(rows),
                "digest": digest.hexdigest(), "prev": "genesis"}
        line["anchor"] = hashlib.sha256("|".join([
            line["prev"], str(line["rows"]), line["digest"], line["source"],
        ]).encode("utf-8")).hexdigest()
        self.path.write_text(json.dumps(line, sort_keys=True) + "\n", encoding="utf-8")
        return self.path.read_bytes()

    def test_01_v3_native_roundtrip_and_unchanged_commit_semantics(self):
        row = self._row(self.names["3"])
        self.assertEqual("3", row.checksum_version)
        self.assertEqual("旧值\nA|B", row.old_value)
        self.assertEqual("新值\nC|D", row.new_value)
        self.assertEqual("action|qualifier", row.action_text)
        self.assertTrue(hasattr(row.created_at, "microsecond"), "须读取实际 MariaDB Datetime")
        self.assertEqual(row.checksum, self.svc._checksum(row, "3"))
        verdict = self._verify(row.name)
        self.assertEqual([], verdict["mismatched"])
        self.assertEqual({"1": 0, "2": 0, "3": 1}, verdict["versions"])
        self.assertEqual(0, verdict["weak_legacy"])
        with self._fault():
            transient = self._new_row(commit=True)
            self.assertTrue(frappe.db.exists(DOCTYPE, transient))
            self.assertEqual([], self._verify(transient)["mismatched"])
        self.assertFalse(frappe.db.exists(DOCTYPE, transient), "历史 commit=True 参数仍不得提交业务事务")

    def test_02_legacy_vectors_and_mixed_native_rows_remain_unchanged(self):
        payload = {"log_type": "修改", "doctype_target": "HBOS Sample", "doc_name": "AUDIT-TARGET",
                   "action_text": "action|qualifier", "field_changed": "result", "old_value": "旧值\nA|B",
                   "new_value": "new|value", "reason": "native-proof", "user": "audit-manager@test.local",
                   "created_at": "2026-10-18 08:00:00.123456"}
        self.assertEqual("77f9563da4eb7a2d8f4d0321185cff938539c699", self.svc._checksum(payload, "1"))
        self.assertEqual("31b3c15513ccbdcb10c633848112a8d1b62910dcab6963316ee91300d68d93b1",
                         self.svc._checksum(payload, "2"))
        before_db, before_file = self._database_bytes(), self.path.read_bytes()
        for version, name in self.names.items():
            with self.subTest(version=version):
                verdict = self._verify(name)
                self.assertEqual([], verdict["mismatched"])
                self.assertEqual(1, verdict["checked"])
                self.assertEqual(int(version == "1"), verdict["legacy"])
                self.assertEqual(int(version in {"1", "2"}), verdict["weak_legacy"])
                self.assertEqual({key: int(key == version) for key in ("1", "2", "3")}, verdict["versions"])
        self.assertEqual(before_db, self._database_bytes())
        self.assertEqual(before_file, self.path.read_bytes())

    def test_03_v3_field_boundary_collision_is_detected_after_native_write(self):
        name = self.names["3"]
        before = self._row(name)
        with self._fault():
            frappe.db.set_value(DOCTYPE, name, {"action_text": "action", "field_changed": "qualifier|result"},
                                update_modified=False)
            after = self._row(name)
            self.assertEqual(self.svc._checksum(before, "2"), self.svc._checksum(after, "2"))
            self.assertNotEqual(self.svc._checksum(before, "3"), self.svc._checksum(after, "3"))
            self.assertEqual([name], self._verify(name)["mismatched"])
            self.assertFalse(self.anchor.verify_anchor_at(str(self.path))["ok"])

    def test_04_v2_collision_is_weak_but_new_snapshot_binds_observed_payload(self):
        name = self.names["2"]
        with self._fault():
            before_checksum = self._row(name).checksum
            frappe.db.set_value(DOCTYPE, name, {"action_text": "action", "field_changed": "qualifier|result"},
                                update_modified=False)
            self.assertEqual(before_checksum, self.svc._checksum(self._row(name), "2"))
            self.assertEqual([], self._verify(name)["mismatched"], "旧编码的边界碰撞仍须如实保留")
            self.assertEqual(1, self._verify(name)["weak_legacy"])
            self.assertFalse(self.anchor.verify_anchor_at(str(self.path))["ok"])
        with self._fault(restore_file=True):
            old_bytes = self._write_legacy_fixture()
            frappe.db.set_value(DOCTYPE, name, {"action_text": "action", "field_changed": "qualifier|result"},
                                update_modified=False)
            self.assertTrue(self.anchor.verify_anchor_at(str(self.path))["ok"], "旧锚不应伪称完整载荷覆盖")
            self.anchor.write_anchor_at(str(self.path), source="first-observed-payload-snapshot")
            verdict = self.anchor.verify_anchor_at(str(self.path))
            self.assertTrue(verdict["ok"])
            self.assertIn("建立时点", verdict["coverage_note"])
            self.assertGreaterEqual(verdict["weak_legacy"], 2)
            self.assertTrue(self.path.read_bytes().startswith(old_bytes))
            frappe.db.set_value(DOCTYPE, name, {"action_text": "action|qualifier", "field_changed": "result"},
                                update_modified=False)
            self.assertFalse(self.anchor.verify_anchor_at(str(self.path))["ok"])

    def test_05_payload_and_matching_checksum_rewrite_is_detected_by_anchor(self):
        name = self.names["3"]
        with self._fault():
            changed = dict(self._row(name), reason="DB content and checksum changed together")
            frappe.db.set_value(DOCTYPE, name, {"reason": changed["reason"],
                                "checksum": self.svc._checksum(changed, "3")}, update_modified=False)
            self.assertEqual([], self._verify(name)["mismatched"])
            self.assertFalse(self.anchor.verify_anchor_at(str(self.path))["ok"])

    def test_06_delete_insert_and_reorder_are_detected_and_rolled_back(self):
        for kind in ("delete", "insert", "reorder"):
            with self.subTest(kind=kind), self._fault():
                if kind == "delete":
                    frappe.db.sql("delete from `tabHBOS Audit Log` where name=%s", (self.names["3"],))
                elif kind == "insert":
                    self._new_row(created_at=frappe.utils.get_datetime("1900-01-01 00:00:00"))
                else:
                    changed = dict(self._row(self.names["3"]), created_at=frappe.utils.get_datetime("1900-01-01 00:00:00"))
                    frappe.db.set_value(DOCTYPE, self.names["3"], {"created_at": changed["created_at"],
                                        "checksum": self.svc._checksum(changed, "3")}, update_modified=False)
                    self.assertEqual([], self._verify(self.names["3"])["mismatched"])
                self.assertFalse(self.anchor.verify_anchor_at(str(self.path))["ok"], kind)

    def test_07_old_anchor_upgrade_and_valid_append_preserve_history(self):
        with self._fault(restore_file=True):
            before_db = self._database_bytes()
            old_bytes = self._write_legacy_fixture()
            legacy = self.anchor.verify_anchor_at(str(self.path))
            self.assertTrue(legacy["ok"])
            self.assertEqual("legacy_checksum_only", legacy["payload_coverage"])
            line = self.anchor.write_anchor_at(str(self.path), source="upgrade-without-rewrite")
            self.assertEqual(2, line["version"])
            self.assertEqual(before_db, self._database_bytes())
            self.assertTrue(self.path.read_bytes().startswith(old_bytes))
            current = self.anchor.verify_anchor_at(str(self.path))
            self.assertTrue(current["ok"])
            self.assertEqual("snapshot_v2", current["payload_coverage"])
            self.assertIn("旧 v1/v2 行未重算", current["coverage_note"])
            appended = self._new_row(action_text="ordinary later audit append")
            self.assertEqual([], self._verify(appended)["mismatched"])
            self.assertTrue(self.anchor.verify_anchor_at(str(self.path))["ok"], "新增行不应破坏已锚前缀")
            later = self.anchor.write_anchor_at(str(self.path), source="legal-append")
            self.assertEqual(line["rows"] + 1, later["rows"])
            self.assertTrue(self.anchor.verify_anchor_at(str(self.path))["ok"])

    def test_08_writer_refuses_bad_prefix_and_bad_file_without_appending(self):
        with self._fault():
            frappe.db.set_value(DOCTYPE, self.names["3"], "reason", "untrusted history", update_modified=False)
            before_file = self.path.read_bytes()
            with self.assertRaises(ValueError):
                self.anchor.write_anchor_at(str(self.path), source="must-not-launder-history")
            self.assertEqual(before_file, self.path.read_bytes())
        with self._fault(restore_file=True):
            line = json.loads(self.path.read_text())
            line["at"] = "1900-01-01 00:00:00"
            self.path.write_text(json.dumps(line) + "\n", encoding="utf-8")
            before_file = self.path.read_bytes()
            self.assertFalse(self.anchor.verify_anchor_at(str(self.path))["ok"])
            with self.assertRaises(ValueError):
                self.anchor.write_anchor_at(str(self.path), source="must-not-launder-anchor")
            self.assertEqual(before_file, self.path.read_bytes())
        with self._fault(restore_file=True):
            first = json.loads(self.path.read_text())
            stale = {"version": 2, "at": "2026-10-18 09:30:00", "source": "stale-snapshot",
                     "rows": first["rows"] - 1, "prev": first["anchor"]}
            stale["digest"] = self.anchor.history_digest(limit=stale["rows"], version=2)
            stale["anchor"] = self.anchor._anchor_hash(stale["prev"], stale["rows"], stale["digest"],
                stale["source"], version=2, at=stale["at"])
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(stale) + "\n")
            before_file = self.path.read_bytes()
            verdict = self.anchor.verify_anchor_at(str(self.path))
            self.assertFalse(verdict["ok"], "有正确哈希的较小快照也不得缩小先前覆盖范围")
            self.assertIn("倒退", verdict["reason"])
            with self.assertRaises(ValueError):
                self.anchor.write_anchor_at(str(self.path), source="must-not-launder-stale-prefix")
            self.assertEqual(before_file, self.path.read_bytes())

    def test_09_unknown_row_and_anchor_versions_fail_closed_without_byte_change(self):
        for version in (0, False, "4", "unknown"):
            with self.subTest(row_version=version), self._fault():
                frappe.db.set_value(DOCTYPE, self.names["3"], "checksum_version", version, update_modified=False)
                verdict = self._verify(self.names["3"])
                self.assertEqual([self.names["3"]], verdict["unknown"])
                self.assertEqual([self.names["3"]], verdict["mismatched"])
                self.assertFalse(self.anchor.verify_anchor_at(str(self.path))["ok"])
                before_file = self.path.read_bytes()
                with self.assertRaises(ValueError):
                    self.anchor.write_anchor_at(str(self.path), source="unknown-row")
                self.assertEqual(before_file, self.path.read_bytes())
        for version in (None, False, 0, 99):
            with self.subTest(anchor_version=version), self._fault(restore_file=True):
                line = json.loads(self.path.read_text())
                line["version"] = version
                self.path.write_text(json.dumps(line) + "\n", encoding="utf-8")
                before_file = self.path.read_bytes()
                verdict = self.anchor.verify_anchor_at(str(self.path))
                self.assertFalse(verdict["ok"])
                self.assertIn("未知锚定版本", verdict["reason"])
                with self.assertRaises(ValueError):
                    self.anchor.write_anchor_at(str(self.path), source="unknown-anchor")
                self.assertEqual(before_file, self.path.read_bytes())


if __name__ == "__main__":
    unittest.main()
