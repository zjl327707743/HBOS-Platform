# -*- coding: utf-8 -*-
"""M2-R4 COA 与报表契约测试：COA DocType / Print Format / 4 个报表 / COA 服务方法（源码即文档）。"""

import json
import sys
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

HBOS_LIMS = APP_ROOT / "hb_lims_app" / "hbos_lims"
SERVICE = HBOS_LIMS / "lims_service.py"
REPORT_DIR = HBOS_LIMS / "report"

from hb_lims_app.hbos_lims import workflow_contract as wf


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


def _function_body(source, name):
    """取某个顶层函数的源码片段（从 `def name(` 到下一个顶层 `def`）。"""
    start = source.index(f"def {name}(")
    end = source.find("\ndef ", start + 10)
    return source[start:end if end != -1 else len(source)]


class TestCoaActionMatrixContract(unittest.TestCase):
    """L10-P0-11：COA 拥有独立动作，不再借用 Sample / Result 的动作名。

    角色口径对齐稳定性「报告」：复核可由 Reviewer，**发布归 QA 线**（且不得自审自发）。
    """

    def test_coa_actions_registered_with_qa_publish_line(self):
        self.assertEqual(wf.ACTION_ROLES["create_coa"],
                         {wf.ROLE_ANALYST, wf.ROLE_REVIEWER, wf.ROLE_MANAGER, wf.ROLE_SYSTEM})
        self.assertEqual(wf.ACTION_ROLES["review_coa"],
                         {wf.ROLE_REVIEWER, wf.ROLE_LIMS_QA, wf.ROLE_LIMS_QA_MANAGER,
                          wf.ROLE_MANAGER, wf.ROLE_SYSTEM})
        self.assertEqual(wf.ACTION_ROLES["publish_coa"],
                         {wf.ROLE_LIMS_QA, wf.ROLE_LIMS_QA_MANAGER, wf.ROLE_MANAGER,
                          wf.ROLE_SYSTEM})
        # 报告书是对外质量凭证：发布归 QA 线，Reviewer / Analyst 均不得发布
        for role in (wf.ROLE_REVIEWER, wf.ROLE_ANALYST):
            self.assertNotIn(role, wf.ACTION_ROLES["publish_coa"])

    def test_service_does_not_borrow_foreign_actions(self):
        source = SERVICE.read_text(encoding="utf-8")
        for fn, borrowed in (("create_coa", "release_sample"),
                             ("review_coa", "review_result"),
                             ("publish_coa", "review_result")):
            body = _function_body(source, fn)
            self.assertNotIn(f'_check_action("{borrowed}")', body,
                             f"{fn} 仍在借用 {borrowed}")
            self.assertIn(f'_check_action("{fn}")', body, f"{fn} 未用独立动作校验")

    def test_publish_requires_separation_of_duties(self):
        body = _function_body(SERVICE.read_text(encoding="utf-8"), "publish_coa")
        self.assertIn("发布人不得为审核人", body)
        self.assertIn("_sod_reject(", body, "SoD 拦截须复用 P0-01 的留痕助手")


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

    def test_coa_content_fingerprint_field(self):
        """内容指纹：只读，由服务在发布时固化（L10-P0-05）。"""
        fields = self._fields(self.coa)
        self.assertEqual(fields["content_fingerprint"]["fieldtype"], "Data")
        self.assertEqual(fields["content_fingerprint"]["read_only"], 1)

    def test_coa_validate_locks_snapshot(self):
        """审核/发布后整份快照冻结：头字段 + 备注 + items 每行内容与行序（L10-P0-05）。"""
        source = (HBOS_LIMS / "doctype" / "hbos_coa" / "hbos_coa.py").read_text(encoding="utf-8")
        self.assertIn("def _validate_locked_after_review(self):", source)
        self.assertIn("COA_LOCKED_FIELDS", source)
        self.assertIn("guard_content_frozen(self, COA_LOCKED_FIELDS, COA_FROZEN_STATUSES", source)
        self.assertIn("ordered_table_fields=COA_ITEM_TABLE_FIELDS", source)
        # 受控状态须同时覆盖审核与发布两个终态
        self.assertIn("COA_FROZEN_STATUSES = (COA_STATUS_REVIEWED, COA_STATUS_PUBLISHED)", source)

    def test_coa_snapshot_covers_all_business_content(self):
        """冻结集覆盖报告头与备注；判据为保存前状态（原实现判当前状态，状态回退即可绕过）。"""
        source = (HBOS_LIMS / "doctype" / "hbos_coa" / "hbos_coa.py").read_text(encoding="utf-8")
        self.assertIn('"sample", "batch_no", "material_code", "material_name"', source)
        self.assertIn('"spec_version", "remarks"', source)
        self.assertIn('status_field="report_status"', source)

    def test_coa_content_fingerprint_recorded_and_verifiable(self):
        """发布时固化内容指纹，并提供只读校验接口（L10-P0-05）。"""
        source = SERVICE.read_text(encoding="utf-8")
        self.assertIn("def _coa_content_fingerprint(coa):", source)
        self.assertIn("hashlib.sha256", source)
        self.assertIn("coa.content_fingerprint = _coa_content_fingerprint(coa)", source)
        self.assertIn("def verify_coa_content(coa_name):", source)
        idx = source.index("def verify_coa_content")
        self.assertIn("@frappe.whitelist()", source[max(0, idx - 200):idx])
        self.assertIn('_check_action("verify_coa_content")', source)
        # 指纹字段属系统字段：只能由服务写入，不随内容一起被改
        self.assertIn("content_fingerprint", wf.HBOS_COA_SYSTEM_FIELDS)
        self.assertIn("verify_coa_content", wf.ACTION_ROLES)


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
