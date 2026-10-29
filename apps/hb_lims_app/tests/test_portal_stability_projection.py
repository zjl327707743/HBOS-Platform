from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import patch

from hb_lims_app.hbos_lims.portal.stability import get_stability_projection


class PortalStabilityProjectionTest(unittest.TestCase):
    def test_workbench_keeps_schedule_summary_and_scope(self):
        service = types.ModuleType("hb_lims_app.hbos_lims.stability_service")
        service.get_stability_dashboard = lambda: {
            "sample_count": 4, "timepoint_count": 8, "scope": "质量控制部 · 稳定性数据",
            "timepoint_by_status": {"wait_sample": 2}, "master": {"room": 1},
        }
        service.get_stability_schedule = lambda **kwargs: {
            "rows": [{"name": "TP-001", "status": "待取样"}],
            "summary": {"total": 1, "sample_overdue": 0},
        }
        with patch.dict(sys.modules, {"hb_lims_app.hbos_lims.stability_service": service}):
            payload = get_stability_projection(section="workbench")

        self.assertEqual("质量控制部 · 稳定性数据", payload["scope"])
        self.assertEqual("TP-001", payload["schedule"]["rows"][0]["name"])
        self.assertEqual(1, payload["schedule"]["summary"]["total"])

    def test_trend_does_not_call_trend_service_without_two_selections(self):
        service = types.ModuleType("hb_lims_app.hbos_lims.stability_service")
        service.get_stability_products = lambda **kwargs: {"rows": [{"name": "STB-P-1"}]}
        service.get_stability_master = lambda *args, **kwargs: {"rows": [{"name": "STB-I-1"}]}
        service.get_stability_trend = lambda **kwargs: (_ for _ in ()).throw(AssertionError("trend must be gated"))
        with patch.dict(sys.modules, {"hb_lims_app.hbos_lims.stability_service": service}):
            payload = get_stability_projection(section="trend", stability_product="STB-P-1")

        self.assertIsNone(payload["trend"])
        self.assertEqual(1, payload["products"]["total"])
        self.assertEqual(1, payload["test_items"]["total"])


if __name__ == "__main__":
    unittest.main()
