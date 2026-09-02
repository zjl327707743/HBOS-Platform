# -*- coding: utf-8 -*-
"""M2-R3 lims_service 与事务 DocType 契约测试（源码即文档，离线断言约定存在）。"""

import json
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
SERVICE = APP_ROOT / "hb_lims_app" / "hbos_lims" / "lims_service.py"
WORKFLOW = APP_ROOT / "hb_lims_app" / "hbos_lims" / "workflow_contract.py"
DOCTYPES = APP_ROOT / "hb_lims_app" / "hbos_lims" / "doctype"

TRANSACTIONAL_DOCTYPES = {
    "hbos_sample": "HBOS Sample",
    "hbos_sample_item": "HBOS Sample Item",
    "hbos_sample_task": "HBOS Sample Task",
    "hbos_test_result": "HBOS Test Result",
    "hbos_result_revision": "HBOS Result Revision",
}


class TestLimsServiceContract(unittest.TestCase):
    def test_whitelist_methods_exist(self):
        source = SERVICE.read_text(encoding="utf-8")
        for fn in ("register_sample", "generate_tasks", "assign_task", "start_task",
                   "submit_result", "review_result", "approve_result",
                   "revise_result", "release_sample", "reject_sample"):
            self.assertIn(f"def {fn}", source, f"缺少 {fn}")
            # 每个方法前必须有 whitelist 装饰器
            idx = source.index(f"def {fn}")
            prefix = source[max(0, idx - 200):idx]
            self.assertIn("@frappe.whitelist()", prefix, f"{fn} 缺少 whitelist")

    def test_every_method_checks_action(self):
        source = SERVICE.read_text(encoding="utf-8")
        for fn in ("register_sample", "generate_tasks", "assign_task", "start_task",
                   "submit_result", "review_result", "approve_result",
                   "revise_result", "release_sample", "reject_sample"):
            idx = source.index(f"def {fn}")
            body = source[idx:source.find("\ndef ", idx + 10)]
            self.assertIn("_check_action", body, f"{fn} 缺少角色校验")
            self.assertIn("_commit()", body, f"{fn} 缺少显式提交")

    def test_start_task_creates_result(self):
        source = SERVICE.read_text(encoding="utf-8")
        self.assertIn("def _create_result_for_task(task):", source)
        self.assertIn("_create_result_for_task(task)", source)
        self.assertIn("limits_type", source)
        self.assertIn('"result_status": "草稿"', source)

    def test_whitelist_signature_fields(self):
        source = SERVICE.read_text(encoding="utf-8")
        self.assertIn('SIGN_ANALYST = "检验人"', source)
        self.assertIn('SIGN_REVIEWER = "复核人"', source)
        self.assertIn('SIGN_APPROVER = "批准人"', source)
        self.assertIn("submitted_signature = _signature(SIGN_ANALYST)", source)
        self.assertIn("reviewed_signature = _signature(SIGN_REVIEWER)", source)
        self.assertIn("approved_signature = _signature(SIGN_APPROVER)", source)

    def test_revision_requires_reason(self):
        source = SERVICE.read_text(encoding="utf-8")
        self.assertIn("修改原因必填", source)
        self.assertIn('frappe.get_doc({\n\t\t\t"doctype": "HBOS Result Revision"', source)

    def test_oos_lock_sample(self):
        source = SERVICE.read_text(encoding="utf-8")
        self.assertIn("def _lock_sample_oos(sample_name):", source)
        self.assertIn("sample.oos_locked = 1", source)
        self.assertIn('"OOS锁定"', source)

    def test_approve_blocks_oos(self):
        source = SERVICE.read_text(encoding="utf-8")
        self.assertIn("OOS 候选结果不允许批准放行", source)


class TestLedgerContract(unittest.TestCase):
    """M2-R6C 检验结果台账聚合查询契约（get_result_ledger 对齐前端 ResultLedgerView）。"""

    def test_get_result_ledger_whitelist(self):
        source = SERVICE.read_text(encoding="utf-8")
        idx = source.index("def get_result_ledger")
        prefix = source[max(0, idx - 200):idx]
        self.assertIn("@frappe.whitelist()", prefix, "get_result_ledger 缺少 whitelist")
        self.assertIn("_check_action(\"get_result_ledger\")", source, "缺少角色校验")

    def test_ledger_action_registered(self):
        wf = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('"get_result_ledger"', wf, "workflow_contract ACTION_ROLES 未注册 get_result_ledger")
        self.assertIn("ROLE_ANALYST", wf)
        self.assertIn("ROLE_REVIEWER", wf)

    def test_ledger_field_contract(self):
        """聚合字段覆盖前端 ResultLedgerView 渲染所需全部字段。"""
        source = SERVICE.read_text(encoding="utf-8")
        for field in ("material_name", "batch_no", "sample_type", "spec_version", "status",
                      "test_due_date", "oos_locked"):
            self.assertIn(f'"{field}"', source, f"samples 缺少字段 {field}")
        for field in ("item_name", "result_value", "result_text", "unit", "verdict",
                      "result_status", "limits_type", "lower_limit", "upper_limit",
                      "analyst", "submitted_at", "reviewer", "reviewed_at", "approver",
                      "approved_at", "superseded_by"):
            self.assertIn(f'"{field}"', source, f"results 缺少字段 {field}")
        for field in ("field_changed", "old_value", "new_value", "changed_by", "changed_at", "change_reason"):
            self.assertIn(f'"{field}"', source, f"revisions 缺少字段 {field}")

    def test_ledger_derived_fields(self):
        source = SERVICE.read_text(encoding="utf-8")
        self.assertIn("report_date", source, "samples 缺 report_date 派生")
        self.assertIn("limits_text", source, "results 缺 limits_text 派生")
        self.assertIn('"display"', source, "results 缺 display 派生")
        self.assertIn('"coas"', source, "返回缺 coas")
        self.assertIn('"groups"', source, "返回缺 groups")

    def test_ledger_groups_helper(self):
        source = SERVICE.read_text(encoding="utf-8")
        self.assertIn("def _ledger_groups(samples):", source)
        self.assertIn("sample_type", source)
        self.assertIn("material_name", source)
        self.assertIn('"count"', source)


class TestTransactionalDoctypeContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doctypes = {}
        for dirname, expected in TRANSACTIONAL_DOCTYPES.items():
            path = DOCTYPES / dirname / f"{dirname}.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["_dir"] = dirname
            cls.doctypes[dirname] = payload
            assert payload["name"] == expected, dirname

    def _fields(self, dirname):
        return {f["fieldname"]: f for f in self.doctypes[dirname]["fields"]}

    def test_naming_series(self):
        expected_series = {
            "hbos_sample": "HBOS-SMP-.YYYY.-",
            "hbos_sample_task": "HBOS-TSK-.YYYY.-",
            "hbos_test_result": "HBOS-TR-.YYYY.-",
            "hbos_result_revision": "HBOS-REV-.YYYY.-",
        }
        for dirname, series_value in expected_series.items():
            payload = self.doctypes[dirname]
            self.assertEqual(payload["autoname"], "naming_series:", dirname)
            series = self._fields(dirname)["naming_series"]
            self.assertEqual(series["fieldtype"], "Select", dirname)
            self.assertEqual(series["options"], series_value, dirname)

    def test_sample_locks_after_register(self):
        source = (DOCTYPES / "hbos_sample" / "hbos_sample.py").read_text(encoding="utf-8")
        self.assertIn("def _validate_locked_after_register(self):", source)
        self.assertIn("is_spec_active", source)

    def test_result_locks_after_submit(self):
        source = (DOCTYPES / "hbos_test_result" / "hbos_test_result.py").read_text(encoding="utf-8")
        self.assertIn("def _validate_locked_after_submit(self):", source)
        self.assertIn("RESULT_LOCKED_FIELDS", source)
        for field in ("raw_value", "result_value", "limits_type", "analyst", "verdict"):
            self.assertIn(field, source)

    def test_result_frozen_spec_fields_read_only(self):
        fields = self._fields("hbos_test_result")
        for field in ("limits_type", "lower_limit", "upper_limit", "unit", "significant_digits",
                      "verdict", "is_oos_candidate", "submitted_signature", "reviewed_signature",
                      "superseded_by", "sample", "test_item"):
            self.assertEqual(fields[field]["read_only"], 1, field)

    def test_revision_required_reason_field(self):
        fields = self._fields("hbos_result_revision")
        for field in ("result", "field_changed", "old_value", "new_value",
                      "changed_by", "changed_at", "change_reason"):
            self.assertEqual(fields[field]["reqd"], 1, field)

    def test_result_signature_fields(self):
        fields = self._fields("hbos_test_result")
        for field in ("analyst", "reviewer", "approver"):
            self.assertEqual(fields[field]["fieldtype"], "Link", field)
            self.assertEqual(fields[field]["options"], "User", field)

    def test_status_options(self):
        sample = self._fields("hbos_sample")["status"]
        self.assertEqual(sample["options"], "草稿\n已登记\n检验中\n检验完成\n已放行\n已拒绝\nOOS锁定")
        task = self._fields("hbos_sample_task")["status"]
        self.assertEqual(task["options"], "待分配\n已分配\n检验中\n已提交\n已复核\n已批准\nOOS候选\nOOS锁定")
        result = self._fields("hbos_test_result")["result_status"]
        self.assertEqual(result["options"], "草稿\n已提交\n已复核\n已批准\n已修订")


class TestTaskBoardReportContract(unittest.TestCase):
    def test_report_files_exist(self):
        report_dir = APP_ROOT / "hb_lims_app" / "hbos_lims" / "report" / "待检任务看板"
        self.assertTrue((report_dir / "待检任务看板.json").exists())
        self.assertTrue((report_dir / "待检任务看板.py").exists())
        self.assertTrue((report_dir / "待检任务看板.js").exists())

    def test_report_meta(self):
        payload = json.loads((APP_ROOT / "hb_lims_app" / "hbos_lims" / "report" / "待检任务看板" / "待检任务看板.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["report_type"], "Script Report")
        self.assertEqual(payload["ref_doctype"], "HBOS Sample Task")
        self.assertEqual(payload["is_standard"], "Yes")
        roles = {r["role"] for r in payload["roles"]}
        self.assertIn("LIMS Analyst", roles)

    def test_report_python_contract(self):
        source = (APP_ROOT / "hb_lims_app" / "hbos_lims" / "report" / "待检任务看板" / "待检任务看板.py").read_text(encoding="utf-8")
        self.assertIn("def execute(filters=None):", source)
        self.assertIn('"label": _("任务号")', source)
        self.assertIn('"label": _("检验项目")', source)
        self.assertIn('"label": _("超时")', source)
        self.assertIn("TASK_STATUS_LABELS", source)
        # SQL 参数化，无字符串注入
        self.assertIn("%(lab_department)s", source)
        self.assertIn("ORDER BY t.creation DESC", source)


if __name__ == "__main__":
    unittest.main()
