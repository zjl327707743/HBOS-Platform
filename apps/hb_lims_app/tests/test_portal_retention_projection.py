from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import patch

from hb_lims_app.hbos_lims.portal.retention import get_retention_projection


class PortalRetentionProjectionTest(unittest.TestCase):
    def test_projection_shapes_samples_products_and_workflow_reads(self):
        def get_list(doctype, **kwargs):
            if doctype == "HBOS Retention Sample":
                return [{
                    "name": "RET-001", "retention_product": "RP-001", "sample_name": "阿莫西林留样",
                    "batch_no": "B-001", "status": "在库", "retention_qty": 100,
                    "qty_uom": "g", "current_qty": 100, "reserved_qty": 20,
                    "retention_due_date": "2026-10-10", "observed_flag": 1,
                }]
            return [{
                "name": "RP-001", "product_code": "API-AMX-001", "product_name": "阿莫西林",
                "category": "关键物料", "is_active": 1, "default_uom": "g",
                "obs_rule": "每年选 3 批（原料药成品）",
            }]

        fake_frappe = types.SimpleNamespace(
            get_list=get_list,
            utils=types.SimpleNamespace(
                today=lambda: "2026-09-30",
                getdate=lambda value: __import__("datetime").date.fromisoformat(str(value)),
            ),
        )
        observation = {"rows": [{"name": "RET-001", "product": "阿莫西林", "due": "应观察"}], "completeness": []}
        usage = {"rows": [{"name": "USE-001", "status": "待QC批准"}], "total": 1}
        disposal = {"rows": [{"name": "DSP-001", "status": "待QA审核"}], "total": 1}
        fake_retention = types.ModuleType("hb_lims_app.hbos_lims.retention_service")
        fake_retention.get_observation_plan = lambda: observation
        fake_retention.list_usage_applies = lambda status=None: usage
        fake_retention.list_disposal_applies = lambda status=None: disposal
        with patch.dict(sys.modules, {
            "frappe": fake_frappe,
            "hb_lims_app.hbos_lims.retention_service": fake_retention,
        }):
            payload = get_retention_projection(limit=10)

        self.assertEqual("阿莫西林", payload["samples"][0]["product_name"])
        self.assertEqual(80, payload["samples"][0]["available_qty"])
        self.assertEqual("API-AMX-001", payload["products"][0]["product_code"])
        self.assertEqual(1, payload["summary"]["pending_usage"])
        self.assertEqual(1, payload["summary"]["pending_disposal"])
        self.assertEqual(1, payload["summary"]["due_observation"])

    def test_invalid_cursor_is_rejected(self):
        with self.assertRaises(ValueError):
            from hb_lims_app.hbos_lims.portal.retention import _cursor
            _cursor("bad")


if __name__ == "__main__":
    unittest.main()
