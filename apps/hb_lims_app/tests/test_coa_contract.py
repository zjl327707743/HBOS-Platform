# -*- coding: utf-8 -*-
"""M2-R4 COA 与报表契约测试：COA DocType / Print Format / 4 个报表 / COA 服务方法（源码即文档）。"""

import json
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
HBOS_LIMS = APP_ROOT / "hb_lims_app" / "hbos_lims"
SERVICE = HBOS_LIMS / "lims_service.py"
REPORT_DIR = HBOS_LIMS / "report"


class TestCOAServiceContract(unittest.TestCase):
    def test_coa_methods_exist_with_whitelist(self):
        source = SERVICE.read_text(encoding="utf-8")
        for fn in ("create_coa", "review_coa", "publish_coa"):
            idx = source.index(f"def {fn}")
            self.assertIn("@frappe.whitelist()", source[max(0, idx - 200):idx], fn)
            body = source[idx:source.find("\ndef ", idx + 10)]
            self.assertIn("_check_action", body, f"{fn} 缺少角色校验")
            self.assertIn("_commit()", body, f"{fn} 缺少显式提交")

    def test_coa_item_from_result(self):
        source = SERVICE.read_text(encoding="utf-8")
        self.assertIn("def _coa_item_from_result(result_name):", source)
        self.assertIn('"verdict": result.verdict', source)

    def test_publish_generates_pdf(self):
        source = SERVICE.read_text(encoding="utf-8")
        self.assertIn("def _coa_print_html(coa):", source)
        self.assertIn("fixture.read_text(encoding=\"utf-8\")", source)
        self.assertIn("render_template(template, {\"doc\": coa})", source)
        self.assertIn("frappe.utils.pdf.get_pdf(html)", source)
        self.assertIn('"doctype": "File"', source)
        self.assertIn("file_doc.insert(ignore_permissions=True)", source)
        self.assertIn("coa.pdf_attachment = file_doc.file_url", source)
        self.assertIn("coa.report_status = \"已发布\"", source)

    def test_create_coa_guards(self):
        source = SERVICE.read_text(encoding="utf-8")
        self.assertIn("仅检验完成且无 OOS 锁定的样品可生成 COA", source)
        self.assertIn("没有已批准且非 OOS 的检验结果", source)
        self.assertIn("已存在未发布 COA", source)


class TestCOADoctypeContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        coa = json.loads((HBOS_LIMS / "doctype" / "hbos_coa" / "hbos_coa.json").read_text(encoding="utf-8"))
        coa_item = json.loads((HBOS_LIMS / "doctype" / "hbos_coa_item" / "hbos_coa_item.json").read_text(encoding="utf-8"))
        cls.coa = coa
        cls.coa_item = coa_item

    def _fields(self, payload):
        return {f["fieldname"]: f for f in payload["fields"]}

    def test_coa_meta(self):
        self.assertEqual(self.coa["name"], "HBOS COA")
        self.assertEqual(self.coa["autoname"], "naming_series:")
        self.assertEqual(self._fields(self.coa)["naming_series"]["options"], "HBOS-COA-.YYYY.-")
        self.assertEqual(self.coa["module"], "HBOS LIMS")
        self.assertEqual(self.coa["track_changes"], 1)

    def test_coa_item_is_child(self):
        self.assertEqual(self.coa_item["istable"], 1)
        self.assertEqual(self.coa_item["name"], "HBOS COA Item")

    def test_coa_status_options(self):
        status = self._fields(self.coa)["report_status"]
        self.assertEqual(status["options"], "草稿\n已审核\n已发布")

    def test_coa_fetch_and_attach(self):
        fields = self._fields(self.coa)
        self.assertEqual(fields["batch_no"]["fetch_from"], "sample.batch_no")
        self.assertEqual(fields["material_name"]["fetch_from"], "sample.material_name")
        self.assertEqual(fields["spec_version"]["fetch_from"], "sample.spec_version")
        self.assertEqual(fields["pdf_attachment"]["fieldtype"], "Attach")
        self.assertEqual(fields["pdf_attachment"]["read_only"], 1)

    def test_coa_validate_locks_snapshot(self):
        source = (HBOS_LIMS / "doctype" / "hbos_coa" / "hbos_coa.py").read_text(encoding="utf-8")
        self.assertIn("def _validate_locked_after_review(self):", source)
        self.assertIn("COA_LOCKED_FIELDS", source)
        self.assertIn("item_signature(self.items)", source)
        self.assertIn("检验项目明细内容不可增删改", source)


class TestPrintFormatContract(unittest.TestCase):
    def test_print_format_files_exist(self):
        pf_dir = HBOS_LIMS / "print_format" / "hbos_coa"
        self.assertTrue((pf_dir / "hbos_coa.json").exists())
        self.assertTrue((pf_dir / "hbos_coa.html").exists())

    def test_print_format_meta(self):
        payload = json.loads((HBOS_LIMS / "print_format" / "hbos_coa" / "hbos_coa.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["name"], "HBOS COA")
        self.assertEqual(payload["doc_type"], "HBOS COA")
        self.assertEqual(payload["print_format_type"], "Jinja")
        self.assertEqual(payload["standard"], "Yes")
        self.assertEqual(payload["module"], "HBOS LIMS")

    def test_print_format_html_chinese(self):
        html = (HBOS_LIMS / "print_format" / "hbos_coa" / "hbos_coa.html").read_text(encoding="utf-8")
        for token in ("检验报告书", "标准限度", "检验结果", "判定", "QA批准人", "本报告仅对来样负责",
                      "{{ doc.material_name }}", "{% for item in doc.items %}"):
            self.assertIn(token, html)


class TestReportsContract(unittest.TestCase):
    # 目录名遵循 Frappe scrub(report_name) 约定：ASCII 小写、空格转下划线
    REPORTS = ("检验结果清单", "样品台账", "审计追踪查询", "coa_发布记录")

    def test_report_files_exist(self):
        for name in self.REPORTS:
            d = REPORT_DIR / name
            self.assertTrue((d / f"{name}.json").exists(), name)
            self.assertTrue((d / f"{name}.py").exists(), name)
            self.assertTrue((d / f"{name}.js").exists(), name)

    def test_report_meta(self):
        for name in self.REPORTS:
            payload = json.loads((REPORT_DIR / name / f"{name}.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["report_type"], "Script Report", name)
            self.assertEqual(payload["is_standard"], "Yes", name)
            self.assertIn("LIMS Manager", {r["role"] for r in payload["roles"]}, name)

    def test_report_python_contract(self):
        for name in self.REPORTS:
            source = (REPORT_DIR / name / f"{name}.py").read_text(encoding="utf-8")
            self.assertIn("def execute(filters=None):", source, name)
            self.assertIn('"label": _("', source, name)
            # SQL 参数化（防注入）：至少存在一个 %(xxx)s 占位符
            self.assertRegex(source, r"%\(\w+\)s", name)
            self.assertIn("ORDER BY", source, name)

    def test_report_js_filters(self):
        for name in self.REPORTS:
            source = (REPORT_DIR / name / f"{name}.js").read_text(encoding="utf-8")
            self.assertIn("frappe.query_reports", source, name)
            self.assertIn('"filters"', source, name)
            self.assertIn("__(", source, name)


if __name__ == "__main__":
    unittest.main()
