# -*- coding: utf-8 -*-
"""M2-R6D 合规审计日志契约测试（源码即文档，离线断言约定存在）。"""

import json
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
SERVICE = APP_ROOT / "hb_lims_app" / "hbos_lims" / "lims_service.py"
WORKFLOW = APP_ROOT / "hb_lims_app" / "hbos_lims" / "workflow_contract.py"
HOOKS = APP_ROOT / "hb_lims_app" / "hooks.py"
DOCTYPES = APP_ROOT / "hb_lims_app" / "hbos_lims" / "doctype"
AUDIT_DOCTYPE_DIR = DOCTYPES / "hbos_audit_log"


class TestAuditLogDoctype(unittest.TestCase):
    def test_audit_log_doctype_exists(self):
        path = AUDIT_DOCTYPE_DIR / "hbos_audit_log.json"
        self.assertTrue(path.exists(), "缺少 HBOS Audit Log DocType")
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["name"], "HBOS Audit Log")

    def test_audit_log_fields(self):
        payload = json.loads((AUDIT_DOCTYPE_DIR / "hbos_audit_log.json").read_text(encoding="utf-8"))
        fields = {f["fieldname"] for f in payload["fields"]}
        for f in ("log_type", "doctype_target", "doc_name", "action_text",
                  "field_changed", "old_value", "new_value", "reason",
                  "user", "created_at", "checksum"):
            self.assertIn(f, fields, f"缺少字段 {f}")

    def test_audit_log_write_once_permission(self):
        """合规日志 write-once：无 create/write/delete 的常规权限（仅 Reviewer/Manager/System 可读）。"""
        payload = json.loads((AUDIT_DOCTYPE_DIR / "hbos_audit_log.json").read_text(encoding="utf-8"))
        for perm in payload["permissions"]:
            role = perm["role"]
            self.assertEqual(perm["read"], 1, f"{role} 应可读审计日志")
            self.assertEqual(perm.get("create", 0), 0, f"{role} 不应能创建审计日志")
            self.assertEqual(perm.get("write", 0), 0, f"{role} 不应能写审计日志")
            self.assertEqual(perm.get("delete", 0), 0, f"{role} 不应能删除审计日志")


class TestAuditLogService(unittest.TestCase):
    def test_audit_log_internal_and_core(self):
        source = SERVICE.read_text(encoding="utf-8")
        idx = source.index("def audit_log")
        prefix = source[max(0, idx - 200):idx]
        self.assertNotIn("@frappe.whitelist()", prefix, "audit_log 不应暴露为 HTTP whitelist")
        self.assertIn("HBOS Audit Log", source)
        self.assertIn("_checksum", source, "缺少数据指纹函数")
        self.assertIn("hashlib.sha256", source, "完整性指纹必须使用 SHA-256")
        audit_start = source.index("def audit_log")
        audit_end = source.index("\n\n# ---- doc_events", audit_start)
        self.assertNotIn("frappe.db.commit()", source[audit_start:audit_end])

    def test_audit_query_whitelist(self):
        source = SERVICE.read_text(encoding="utf-8")
        idx = source.index("def get_audit_log")
        prefix = source[max(0, idx - 200):idx]
        self.assertIn("@frappe.whitelist()", prefix, "get_audit_log 缺少 whitelist")
        self.assertIn('_check_action("get_audit_log")', source, "get_audit_log 缺角色校验")

    def test_audit_action_registered(self):
        wf = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('"get_audit_log"', wf, "workflow ACTION_ROLES 未注册 get_audit_log")

    def test_doc_events_hooks(self):
        hooks = HOOKS.read_text(encoding="utf-8")
        self.assertIn("doc_events", hooks)
        for dt in ("HBOS Sample", "HBOS Test Result", "HBOS COA", "HBOS Specification"):
            self.assertIn(f'"{dt}"', hooks, f"doc_events 未注册 {dt}")
        for hook in ("audit_on_insert", "audit_on_update", "audit_on_trash"):
            self.assertIn(hook, hooks, f"缺少 {hook}")
            self.assertIn(hook, SERVICE.read_text(encoding="utf-8"), f"{hook} 未实现")

    def test_business_methods_emit_audit(self):
        source = SERVICE.read_text(encoding="utf-8")
        for marker in ('audit_log("提交"', 'audit_log("复核"', 'audit_log("批准"',
                       'audit_log("修订"', 'audit_log("放行"', 'audit_log("拒绝"',
                       'audit_log("OOS"', 'audit_log("仪器使用"', 'audit_log("规格生效"', 'audit_log("规格废止"'):
            self.assertIn(marker, source, f"缺少 {marker} 埋点")

    def test_audit_write_once_guard(self):
        py = (AUDIT_DOCTYPE_DIR / "hbos_audit_log.py").read_text(encoding="utf-8")
        self.assertIn("write-once", py)
        self.assertIn("frappe.throw", py)

    def test_audit_change_detection_uses_frappe_before_save(self):
        source = SERVICE.read_text(encoding="utf-8")
        self.assertIn("before = doc.get_doc_before_save()", source)
        self.assertNotIn("__saved", source)

    def test_audit_query_range_and_keyword_filters(self):
        source = SERVICE.read_text(encoding="utf-8")
        self.assertIn('filters.append(["created_at", ">=", from_date', source)
        self.assertIn('filters.append(["created_at", "<=", to_date', source)
        self.assertIn("or_filters.extend([", source)
        self.assertIn('["doc_name", "like", kw]', source)
        self.assertIn('["action_text", "like", kw]', source)
        self.assertIn('["checksum", "like", kw]', source)


if __name__ == "__main__":
    unittest.main()
