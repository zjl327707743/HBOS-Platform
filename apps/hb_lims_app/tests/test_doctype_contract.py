# -*- coding: utf-8 -*-
"""M2-R2 DocType 契约测试：6 个主数据 DocType JSON 关键约定 + 规格生效校验函数（源码即文档）。"""

import json
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
DOCTYPES = APP_ROOT / "hb_lims_app" / "hbos_lims" / "doctype"

MASTER_DOCTYPES = [
    "hbos_sample_type",
    "hbos_lab_department",
    "hbos_test_item",
    "hbos_calculation",
    "hbos_specification",
    "hbos_specification_item",
]


def _load_doctype(dirname):
    # 显式映射目录名 -> DocType 名
    mapping = {
        "hbos_sample_type": "HBOS Sample Type",
        "hbos_lab_department": "HBOS Lab Department",
        "hbos_test_item": "HBOS Test Item",
        "hbos_calculation": "HBOS Calculation",
        "hbos_specification": "HBOS Specification",
        "hbos_specification_item": "HBOS Specification Item",
    }
    json_path = DOCTYPES / dirname / f"{dirname}.json"
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    payload["_json_path"] = json_path
    payload["_expected_name"] = mapping[dirname]
    return payload


class TestMasterDoctypeContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doctypes = {d: _load_doctype(d) for d in MASTER_DOCTYPES}

    def test_all_doctypes_exist_and_named(self):
        for dirname, payload in self.doctypes.items():
            self.assertEqual(payload["name"], payload["_expected_name"], dirname)
            self.assertEqual(payload["module"], "HBOS LIMS", dirname)
            self.assertTrue((DOCTYPES / dirname / f"{dirname}.py").exists(), dirname)
            self.assertTrue((DOCTYPES / dirname / "__init__.py").exists(), dirname)

    def test_autoname_conventions(self):
        # 主数据按字段命名，规格按 规格ID-版本号 组合命名（版本控制），子表按 hash
        for dirname in ("hbos_sample_type", "hbos_lab_department", "hbos_test_item",
                        "hbos_calculation"):
            self.assertEqual(self.doctypes[dirname]["autoname"], "field:" + {
                "hbos_sample_type": "sample_type_code",
                "hbos_lab_department": "department_code",
                "hbos_test_item": "item_code",
                "hbos_calculation": "calc_code",
            }[dirname], dirname)
        self.assertEqual(self.doctypes["hbos_specification"]["autoname"],
                         "format:{spec_code}-V{version}")
        self.assertEqual(self.doctypes["hbos_specification_item"]["autoname"], "hash")

    def test_track_changes_and_icon(self):
        for dirname, payload in self.doctypes.items():
            self.assertEqual(payload["track_changes"], 1, dirname)
            self.assertTrue(payload.get("icon"), dirname)

    def test_roles_permissions(self):
        for dirname, payload in self.doctypes.items():
            roles = {p["role"] for p in payload["permissions"]}
            self.assertIn("System Manager", roles, dirname)
            self.assertIn("LIMS Manager", roles, dirname)
            self.assertIn("LIMS Analyst", roles, dirname)
            self.assertIn("LIMS Reviewer", roles, dirname)
            # 主数据：LIMS Analyst / Reviewer 只读（无 create/write/delete）
            for p in payload["permissions"]:
                if p["role"] in ("LIMS Analyst", "LIMS Reviewer"):
                    self.assertNotIn("create", p, dirname)
                    self.assertNotIn("write", p, dirname)
                    self.assertNotIn("delete", p, dirname)
                    self.assertEqual(p.get("read"), 1, dirname)

    def test_chinese_labels(self):
        spec = self.doctypes["hbos_specification"]
        labels = [f["label"] for f in spec["fields"]]
        self.assertIn("规格ID", labels)
        self.assertIn("版本号", labels)
        self.assertIn("生效日期", labels)
        self.assertIn("状态", labels)
        self.assertIn("检验项目明细", labels)
        item = self.doctypes["hbos_specification_item"]
        item_labels = [f["label"] for f in item["fields"]]
        self.assertIn("限度模式", item_labels)
        self.assertIn("限度下限", item_labels)
        self.assertIn("限度上限", item_labels)

    def test_spec_item_fetch_from(self):
        item = self.doctypes["hbos_specification_item"]
        fetch = {f["fieldname"]: f.get("fetch_from") for f in item["fields"]}
        self.assertEqual(fetch["item_name"], "item.item_name")
        self.assertEqual(fetch["method_sop"], "item.method_sop")
        self.assertEqual(fetch["unit"], "item.test_unit")
        self.assertEqual(fetch["significant_digits"], "item.significant_digits")

    def test_spec_validation_functions_exist(self):
        source = (DOCTYPES / "hbos_specification" / "hbos_specification.py").read_text(encoding="utf-8")
        self.assertIn("def validate(self):", source)
        self.assertIn("def _validate_unique_version(self):", source)
        self.assertIn("def _validate_limits(self):", source)
        self.assertIn("def is_spec_active(spec_name):", source)
        self.assertIn('doc.status == SPEC_STATUS_ACTIVE', source)
        self.assertIn("def get_active_specifications():", source)
        self.assertIn('"status": SPEC_STATUS_ACTIVE', source)

    def test_spec_status_options(self):
        spec = self.doctypes["hbos_specification"]
        status_field = next(f for f in spec["fields"] if f["fieldname"] == "status")
        self.assertEqual(status_field["options"], "草稿\n已生效\n已废止")


if __name__ == "__main__":
    unittest.main()
