# -*- coding: utf-8 -*-
"""M2-R6D 合规审计日志契约测试（源码即文档，离线断言约定存在）。"""

import ast
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
        self.assertIn("hashlib.sha1", source, "指纹未用 sha1")

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


def _tuple_literal(source, name):
    """取源码里某个 `X = (…)` 的字符串字面量集合（离线、不导入模块）。"""
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Assign) and any(
                getattr(target, "id", None) == name for target in node.targets):
            return {element.value for element in node.value.elts}
    raise AssertionError("未找到常量 " + name)


class TestAuditIntegrityContract(unittest.TestCase):
    """L10-P0-02：指纹语义与版本、锚定接线、以及不得再宣称「防篡改」。"""

    def test_v2_checksum_covers_the_fields_v1_missed(self):
        """v2 必须覆盖 action_text / field_changed / reason —— v1 正是漏了这三个。"""
        source = SERVICE.read_text(encoding="utf-8")
        self.assertIn("hashlib.sha256", source)
        v2 = _tuple_literal(source, "CHECKSUM_V2_FIELDS")
        v1 = _tuple_literal(source, "CHECKSUM_V1_FIELDS")
        for field in ("action_text", "field_changed", "reason"):
            self.assertIn(field, v2, f"v2 必须覆盖 {field}")
            self.assertNotIn(field, v1, f"v1 是历史算法，不应改动（{field}）")
        # v1 的原覆盖字段须保留，历史行才仍可按旧算法校验
        for field in ("doctype_target", "doc_name", "log_type", "user", "created_at",
                      "old_value", "new_value"):
            self.assertIn(field, v1)

    def test_rows_record_checksum_version(self):
        source = SERVICE.read_text(encoding="utf-8")
        self.assertIn('CHECKSUM_VERSION_CURRENT = "2"', source)
        self.assertIn('payload["checksum_version"] = CHECKSUM_VERSION_CURRENT', source)
        self.assertIn("def verify_audit_integrity(name=None, limit=200):", source)

    def test_no_tamper_proof_claim_in_code(self):
        source = SERVICE.read_text(encoding="utf-8")
        self.assertNotIn("防篡改标记", source)
        self.assertIn("不是防篡改证据", source)

    def test_no_tamper_proof_claim_in_entry_docs_and_ui(self):
        """公共入口与用户可见文案不得再把审计机制说成防篡改（逐条点名，避免再漂）。"""
        repo = APP_ROOT.parents[1]
        targets = [(repo / rel) for rel in (
            "README.md", "docs/AI_CONTEXT.md", "docs/CURRENT_MILESTONE.md",
            "docs/milestones/README.md", "frontend/hbos-lims-web/src/views/AuditLogView.vue")]
        if not all(path.exists() for path in targets):
            self.skipTest("仓库根未挂载（容器内只挂 apps/），该检查仅在宿主机生效")
        for path in targets:
            self.assertNotIn("防篡改", path.read_text(encoding="utf-8"),
                             f"{path.relative_to(repo)} 仍宣称防篡改")

    def test_anchor_module_wired_and_disclaims(self):
        anchor = APP_ROOT / "hb_lims_app" / "hbos_lims" / "audit_anchor_service.py"
        self.assertTrue(anchor.exists(), "缺少审计锚定模块")
        src = anchor.read_text(encoding="utf-8")
        self.assertIn("def verify_anchor_at(", src)
        self.assertIn("不得据此宣称强防篡改", src)
        self.assertIn("hb_lims_app.hbos_lims.audit_anchor_service.scheduler_scan",
                      HOOKS.read_text(encoding="utf-8"))

    def test_verify_actions_registered(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('"verify_audit_integrity"', workflow)
        self.assertIn('"verify_audit_anchor"', workflow)


if __name__ == "__main__":
    unittest.main()
