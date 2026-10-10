from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import patch

from hb_lims_app.hbos_lims.portal.coa import get_coa_projection
from hb_lims_app.hbos_lims.portal.specifications import get_specification_projection


class PortalCoaSpecificationProjectionTest(unittest.TestCase):
    def test_coa_projection_filters_and_paginates_permission_list(self):
        fake_frappe = types.SimpleNamespace(
            get_list=lambda doctype, **kwargs: [
                {
                    "name": "COA-001", "sample": "SAMPLE-001", "batch_no": "B-001",
                    "material_name": "阿莫西林", "spec_version": "V3.1", "report_status": "已发布",
                },
                {
                    "name": "COA-002", "sample": "SAMPLE-002", "batch_no": "B-002",
                    "material_name": "头孢原料", "spec_version": "V2.4", "report_status": "草稿",
                },
            ],
        )
        with patch.dict(sys.modules, {"frappe": fake_frappe}):
            payload = get_coa_projection(keyword="阿莫西林", limit=1)

        self.assertEqual(1, payload["total"])
        self.assertEqual("COA-001", payload["coas"][0]["coa_id"])
        self.assertEqual("已发布", payload["coas"][0]["report_status"])
        self.assertIsNone(payload["next_cursor"])

    def test_coa_detail_projects_controlled_items(self):
        fake_frappe = types.SimpleNamespace(
            get_list=lambda doctype, **kwargs: [{"name": "COA-001"}],
            get_doc=lambda doctype, name: {
                "name": name,
                "sample": "SAMPLE-001",
                "report_status": "已审核",
                "items": [{
                    "test_item": "ASSAY", "item_name": "含量", "method_sop": "SOP-QC-001",
                    "standard": "95 - 105 %", "result": "98.6 %", "verdict": "合格",
                }],
            },
        )
        with patch.dict(sys.modules, {"frappe": fake_frappe}):
            payload = get_coa_projection(coa_id="COA-001")

        self.assertEqual("COA-001", payload["detail"]["coa_id"])
        self.assertEqual("含量", payload["detail"]["items"][0]["item_name"])
        self.assertEqual("合格", payload["detail"]["items"][0]["verdict"])

    def test_specification_projection_builds_limits_text(self):
        fake_frappe = types.SimpleNamespace(
            get_list=lambda doctype, **kwargs: [
                {
                    "name": "SPEC-001", "spec_code": "SPEC-AMX", "spec_name": "阿莫西林质量标准",
                    "material_code": "API-AMX-001", "material_name": "阿莫西林", "version": "3.1",
                    "status": "已生效", "standard_source": "中国药典",
                },
            ],
        )
        with patch.dict(sys.modules, {"frappe": fake_frappe}):
            payload = get_specification_projection(status="已生效")

        self.assertEqual(1, payload["total"])
        self.assertEqual("SPEC-AMX", payload["specifications"][0]["spec_code"])
        self.assertEqual("已生效", payload["specifications"][0]["status"])

    def test_specification_detail_projects_read_only_item_limits(self):
        fake_frappe = types.SimpleNamespace(
            get_list=lambda doctype, **kwargs: [{"name": "SPEC-001"}],
            get_doc=lambda doctype, name: {
                "name": name,
                "spec_code": "SPEC-AMX",
                "spec_name": "阿莫西林质量标准",
                "status": "已生效",
                "items": [{
                    "item": "ASSAY", "item_name": "含量", "method_sop": "SOP-QC-001",
                    "limits_type": "区间", "lower_limit": 95, "upper_limit": 105, "unit": "%",
                }],
            },
        )
        with patch.dict(sys.modules, {"frappe": fake_frappe}):
            payload = get_specification_projection(specification_id="SPEC-001")

        self.assertEqual("SPEC-001", payload["detail"]["specification_id"])
        self.assertEqual("95 - 105", payload["detail"]["items"][0]["limits_text"])


if __name__ == "__main__":
    unittest.main()
