from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import patch

from hb_lims_app.hbos_lims.portal.results import get_result_projection


class PortalResultProjectionTest(unittest.TestCase):
    def test_result_list_filters_and_paginates_ledger_rows(self):
        fake_frappe = types.SimpleNamespace(whitelist=lambda *args, **kwargs: (lambda fn: fn))
        ledger = {
            "samples": [
                {"name": "SAMPLE-001", "batch_no": "B-001", "material_name": "阿莫西林"},
            ],
            "results": [
                {
                    "name": "RESULT-001", "sample": "SAMPLE-001", "item_name": "含量",
                    "result_value": 98.6, "unit": "%", "verdict": "合格", "result_status": "已提交",
                    "display": "98.6%", "limits_text": "95 - 105 %",
                },
                {
                    "name": "RESULT-002", "sample": "SAMPLE-001", "item_name": "水分",
                    "result_value": None, "unit": "%", "verdict": "", "result_status": "草稿",
                    "display": "", "limits_text": "≤ 3 %",
                },
            ],
            "revisions": [],
        }
        with patch.dict(sys.modules, {"frappe": fake_frappe}), patch(
            "hb_lims_app.hbos_lims.lims_service.get_result_ledger",
            return_value=ledger,
        ):
            payload = get_result_projection(keyword="含量", limit=1)

        self.assertEqual(1, payload["total"])
        self.assertEqual("RESULT-001", payload["results"][0]["result_name"])
        self.assertEqual("B-001", payload["results"][0]["batch_no"])
        self.assertIsNone(payload["next_cursor"])

    def test_result_detail_keeps_signature_and_revision_context(self):
        fake_frappe = types.SimpleNamespace(whitelist=lambda *args, **kwargs: (lambda fn: fn))
        ledger = {
            "samples": [{"name": "SAMPLE-001", "batch_no": "B-001", "material_name": "阿莫西林"}],
            "results": [{
                "name": "RESULT-001", "sample": "SAMPLE-001", "item_name": "含量",
                "result_status": "已复核", "analyst": "analyst", "reviewer": "reviewer",
                "reviewed_at": "2026-09-30 10:00:00", "display": "98.6%",
            }],
            "revisions": [{"name": "REV-001", "result": "RESULT-001", "field_changed": "result_value"}],
        }
        with patch.dict(sys.modules, {"frappe": fake_frappe}), patch(
            "hb_lims_app.hbos_lims.lims_service.get_result_ledger",
            return_value=ledger,
        ):
            payload = get_result_projection(result_id="RESULT-001")

        detail = payload["detail"]
        self.assertEqual("analyst", detail["signature_chain"]["analyst"])
        self.assertEqual("reviewer", detail["signature_chain"]["reviewer"])
        self.assertEqual(["REV-001"], [item["name"] for item in detail["revisions"]])


if __name__ == "__main__":
    unittest.main()
