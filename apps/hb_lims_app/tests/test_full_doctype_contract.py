# -*- coding: utf-8 -*-
"""M2-R5 全量 DocType 契约测试：13 个 DocType 通用约定 + 入口收敛断言（源码即文档）。"""

import json
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
HBOS_LIMS = APP_ROOT / "hb_lims_app" / "hbos_lims"
DOCTYPES = HBOS_LIMS / "doctype"

EXPECTED_DOCTYPES = {
    "hbos_sample_type": "HBOS Sample Type",
    "hbos_lab_department": "HBOS Lab Department",
    "hbos_test_item": "HBOS Test Item",
    "hbos_calculation": "HBOS Calculation",
    "hbos_specification": "HBOS Specification",
    "hbos_specification_item": "HBOS Specification Item",
    "hbos_sample": "HBOS Sample",
    "hbos_sample_item": "HBOS Sample Item",
    "hbos_sample_task": "HBOS Sample Task",
    "hbos_test_result": "HBOS Test Result",
    "hbos_result_revision": "HBOS Result Revision",
    "hbos_coa": "HBOS COA",
    "hbos_coa_item": "HBOS COA Item",
}

CHILD_DOCTYPES = {"hbos_specification_item", "hbos_sample_item", "hbos_coa_item"}


class TestAllDoctypeContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doctypes = {}
        for dirname, expected in EXPECTED_DOCTYPES.items():
            path = DOCTYPES / dirname / f"{dirname}.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            assert payload["name"] == expected, dirname
            cls.doctypes[dirname] = payload

    def test_all_13_doctypes_present(self):
        self.assertEqual(len(self.doctypes), 13)

    def test_module_and_track_changes(self):
        for dirname, payload in self.doctypes.items():
            self.assertEqual(payload["module"], "HBOS LIMS", dirname)
            self.assertEqual(payload["track_changes"], 1, dirname)
            self.assertEqual(payload["allow_rename"], 0, dirname)

    def test_tri_role_permissions_everywhere(self):
        for dirname, payload in self.doctypes.items():
            roles = {p["role"] for p in payload["permissions"]}
            self.assertIn("System Manager", roles, dirname)
            self.assertIn("LIMS Manager", roles, dirname)
            self.assertIn("LIMS Analyst", roles, dirname)
            self.assertIn("LIMS Reviewer", roles, dirname)

    def test_child_tables_have_istable(self):
        for dirname in CHILD_DOCTYPES:
            self.assertEqual(self.doctypes[dirname]["istable"], 1, dirname)
            self.assertEqual(self.doctypes[dirname]["autoname"], "hash", dirname)

    def test_transactional_naming_series(self):
        expected = {
            "hbos_sample": "HBOS-SMP-.YYYY.-",
            "hbos_sample_task": "HBOS-TSK-.YYYY.-",
            "hbos_test_result": "HBOS-TR-.YYYY.-",
            "hbos_result_revision": "HBOS-REV-.YYYY.-",
            "hbos_coa": "HBOS-COA-.YYYY.-",
        }
        for dirname, series in expected.items():
            fields = {f["fieldname"]: f for f in self.doctypes[dirname]["fields"]}
            self.assertEqual(fields["naming_series"]["options"], series, dirname)

    def test_all_fields_have_chinese_labels(self):
        """所有字段 label 必须为中文（无 label 的 section/列字段除外）。"""
        no_label_fieldtypes = {"Section Break", "Column Break", "Tab Break"}
        for dirname, payload in self.doctypes.items():
            for f in payload["fields"]:
                if f["fieldtype"] in no_label_fieldtypes:
                    continue
                label = f.get("label") or ""
                # 允许 Series/工程字段保留英文
                if f["fieldname"] == "naming_series" or label.startswith("Series"):
                    continue
                self.assertTrue(label, f"{dirname}.{f['fieldname']} 缺少中文 label")
                self.assertRegex(label, r"[一-鿿]", f"{dirname}.{f['fieldname']} label 非中文: {label}")


class TestReportDirNamingContract(unittest.TestCase):
    """报表目录名必须等于 frappe.scrub(report_name)（ASCII 小写、空格转下划线），否则浏览器路径解析失败。"""

    def test_report_dirs_match_scrub(self):
        report_dir = HBOS_LIMS / "report"
        report_names = ("待检任务看板", "检验结果清单", "样品台账", "审计追踪查询", "COA 发布记录")
        for name in report_names:
            expected_dir = name.lower().replace(" ", "_")
            self.assertTrue((report_dir / expected_dir).exists(), f"{name} -> {expected_dir}")
            self.assertTrue((report_dir / expected_dir / f"{expected_dir}.json").exists(), name)
            self.assertTrue((report_dir / expected_dir / f"{expected_dir}.py").exists(), name)
            self.assertTrue((report_dir / expected_dir / f"{expected_dir}.js").exists(), name)


class TestEntryPointsContract(unittest.TestCase):
    def test_workspace_links_cover_all_routes(self):
        payload = json.loads((HBOS_LIMS / "workspace" / "海滨LIMS工作台" / "海滨LIMS工作台.json").read_text(encoding="utf-8"))
        links = [l for l in payload["links"] if l.get("link_to")]
        targets = {l["link_to"] for l in links}
        # 4 个卡片分区 + 13 个业务链接（3 录入 + 3 查询 + 2 报告 + 5 主数据）
        self.assertEqual(len(links), 13)
        for doctype in ("HBOS Sample", "HBOS Test Result", "HBOS COA",
                        "HBOS Specification", "HBOS Test Item", "HBOS Calculation",
                        "HBOS Sample Type", "HBOS Lab Department"):
            self.assertIn(doctype, targets)
        for report in ("待检任务看板", "样品台账", "检验结果清单", "审计追踪查询", "COA 发布记录"):
            self.assertIn(report, targets)
        # 报表链接必须标记 is_query_report
        for l in payload["links"]:
            if l.get("link_type") == "Report":
                self.assertEqual(l["is_query_report"], 1, l["label"])
            if l.get("label") == "COA 发布记录":
                # 链接指向报表名，报表模块目录为 scrub 形式
                self.assertTrue((HBOS_LIMS / "report" / "coa_发布记录" / "coa_发布记录.json").exists())

    def test_workspace_shortcuts(self):
        payload = json.loads((HBOS_LIMS / "workspace" / "海滨LIMS工作台" / "海滨LIMS工作台.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(payload["shortcuts"]), 5)
        shortcut_labels = {s["label"] for s in payload["shortcuts"]}
        self.assertIn("新建样品登记", shortcut_labels)
        self.assertIn("待检任务看板", shortcut_labels)
        self.assertIn("质量标准", shortcut_labels)

    def test_sidebar_items_populated(self):
        setup = (HBOS_LIMS / "setup.py").read_text(encoding="utf-8")
        self.assertIn('{"label": "新建样品登记", "link_type": "DocType", "link_to": "HBOS Sample"', setup)
        self.assertIn('"link_to": "待检任务看板"', setup)
        self.assertIn('"link_to": "COA 发布记录"', setup)
        self.assertIn('"link_to": "HBOS Specification"', setup)

    def test_desktop_icon_and_logo(self):
        setup = (HBOS_LIMS / "setup.py").read_text(encoding="utf-8")
        self.assertIn('DESKTOP_LABEL = "海滨LIMS"', setup)
        self.assertIn("restrict_removal = 1", setup)
        logo = APP_ROOT / "hb_lims_app" / "public" / "hbos-lims-logo.svg"
        self.assertTrue(logo.exists())


if __name__ == "__main__":
    unittest.main()
