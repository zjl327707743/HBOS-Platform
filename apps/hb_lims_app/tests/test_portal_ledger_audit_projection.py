from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import patch

from hb_lims_app.hbos_lims.portal.audit import get_audit_projection
from hb_lims_app.hbos_lims.portal.ledger import get_ledger_projection


class PortalLedgerAuditProjectionTest(unittest.TestCase):
    def test_ledger_filters_samples_with_result_context_and_paginates(self):
        fake_frappe = types.SimpleNamespace(whitelist=lambda *args, **kwargs: (lambda fn: fn))
        ledger = {
            "samples": [
                {"name": "SAMPLE-001", "material_name": "阿莫西林", "batch_no": "B-001", "status": "检验中"},
                {"name": "SAMPLE-002", "material_name": "头孢原料", "batch_no": "B-002", "status": "已登记"},
            ],
            "results": [
                {"name": "RESULT-001", "sample": "SAMPLE-001", "item_name": "含量", "result_status": "已提交", "verdict": "合格", "display": "98.6%"},
                {"name": "RESULT-002", "sample": "SAMPLE-002", "item_name": "水分", "result_status": "草稿", "verdict": "", "display": ""},
            ],
            "revisions": [{"name": "REV-001", "result": "RESULT-001"}],
            "coas": {"SAMPLE-001": "2026-09-30"},
            "groups": [],
        }
        with patch.dict(sys.modules, {"frappe": fake_frappe}), patch(
            "hb_lims_app.hbos_lims.lims_service.get_result_ledger",
            return_value=ledger,
        ):
            payload = get_ledger_projection(status="已提交", limit=1)

        self.assertEqual(1, payload["total_samples"])
        self.assertEqual("SAMPLE-001", payload["samples"][0]["name"])
        self.assertEqual("RESULT-001", payload["results"][0]["result_name"])
        self.assertEqual("2026-09-30", payload["coas"]["SAMPLE-001"])
        self.assertIsNone(payload["next_cursor"])

    def test_audit_projection_preserves_cursor_and_targets(self):
        fake_frappe = types.SimpleNamespace(whitelist=lambda *args, **kwargs: (lambda fn: fn))
        with patch.dict(sys.modules, {"frappe": fake_frappe}), patch(
            "hb_lims_app.hbos_lims.lims_service.get_audit_log",
            return_value={
                "events": [{"name": "AUDIT-001", "log_type": "提交", "doc_name": "RESULT-001"}],
                "total": 2,
            },
        ), patch(
            "hb_lims_app.hbos_lims.lims_service.get_audit_targets",
            return_value=["HBOS Test Result"],
        ):
            payload = get_audit_projection(limit=1, cursor="1")

        self.assertEqual("AUDIT-001", payload["events"][0]["name"])
        self.assertEqual(["HBOS Test Result"], payload["targets"])
        self.assertIsNone(payload["next_cursor"])


if __name__ == "__main__":
    unittest.main()
