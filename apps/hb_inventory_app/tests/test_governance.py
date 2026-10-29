import ast
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
APP = ROOT / "hb_inventory_app" / "hbos_inventory"
API = APP / "api.py"
SETUP = APP / "setup.py"
HOOKS = ROOT / "hb_inventory_app" / "hooks.py"
RELEASE = APP / "release_gate.py"
PROJECTION = APP / "quality_projection.py"
SEED = APP / "business_seed.py"
OCR_CLIENT = APP / "ocr_client.py"
REPO = Path(__file__).parents[3]
OCR_MAIN = REPO / "services" / "hbos_ocr" / "app" / "main.py"
OCR_CONFIG = REPO / "services" / "hbos_ocr" / "app" / "config.py"
INVENTORY_SMOKE_COMPOSE = REPO / "scripts" / "ci" / "docker-compose.inventory-smoke.yml"


class InventoryGovernanceTest(unittest.TestCase):
    def test_warehouse_queries_and_create_use_permission_checks(self):
        src = API.read_text()
        self.assertIn("rows = frappe.get_list(", src)
        self.assertIn('warehouse_obj.check_permission("read")', src)
        self.assertIn('frappe.get_doc("Company", company).check_permission("read")', src)
        self.assertIn('frappe.has_permission("Stock Entry", "create")', src)
        self.assertNotIn("entry.flags.ignore_permissions = True", src)

    def test_file_read_and_attachment_are_permission_aware(self):
        src = API.read_text()
        self.assertIn('doc.check_permission("read")', src)
        self.assertIn("def _validate_intake_file", src)
        self.assertIn('doc.check_permission("read")', src)
        self.assertIn("doc.owner != frappe.session.user", src)
        self.assertIn("doc.attached_to_doctype or doc.attached_to_name", src)
        self.assertIn("_validate_intake_file(source)", src)
        self.assertIn('"is_private": 1', src)
        self.assertNotIn("source.attached_to_doctype = doctype", src)
        self.assertIn("IMAGE_EXTENSIONS", src)
        self.assertIn("MAX_UPLOAD_BYTES", src)

    def test_stock_user_cannot_govern_item_quality_master(self):
        src = API.read_text()
        self.assertIn("MASTER_DATA_WRITE_ROLES", src)
        self.assertIn("Item Manager", src)
        self.assertIn("属于 Item 主数据", src)

    def test_existing_batch_must_match_item(self):
        src = API.read_text()
        self.assertIn('"item",', src)
        self.assertIn("existing.item", src)
        self.assertIn("不能用于物料", src)

    def test_after_migrate_is_schema_only(self):
        src = SETUP.read_text()
        start = src.index("def after_migrate(")
        body = src[start:]
        self.assertNotIn("sync_uoms(", body)
        self.assertNotIn("sync_warehouses(", body)
        self.assertNotIn("sync_item_groups(", body)
        self.assertIn("sync_custom_fields()", body)
        self.assertNotIn('COMPANY = "hb"', src)
        self.assertNotIn('WAREHOUSE_ROOT = "All Warehouses - HB"', src)
        self.assertIn("apply_profile", SEED.read_text())

    def test_release_fields_are_lims_owned_read_only_projection(self):
        src = SETUP.read_text()
        for field in (
            "hbos_release_status",
            "hbos_release_date",
            "hbos_certificate_no",
            "hbos_certificate_file",
            "hbos_lims_reference",
            "hbos_release_source",
        ):
            self.assertIn(f'"fieldname": "{field}"', src)
        self.assertIn("guard_batch_projection", HOOKS.read_text())
        projection = PROJECTION.read_text()
        self.assertIn("hbos_quality_projection_write", projection)
        self.assertIn('batch.hbos_release_source = "LIMS"', projection)

    def test_outbound_gate_requires_complete_lims_projection(self):
        src = RELEASE.read_text()
        for token in (
            "hbos_release_date",
            "hbos_certificate_file",
            "hbos_lims_reference",
            "hbos_release_source",
            'source != "LIMS"',
        ):
            self.assertIn(token, src)

    def test_ocr_recognize_requires_internal_bearer_token(self):
        main = OCR_MAIN.read_text()
        cfg = OCR_CONFIG.read_text()
        client = OCR_CLIENT.read_text()
        smoke = INVENTORY_SMOKE_COMPOSE.read_text()
        self.assertIn("def _require_internal_auth", main)
        self.assertIn("Header(default=None)", main)
        self.assertIn("secrets.compare_digest", main)
        self.assertIn("SHARED_TOKEN", cfg)
        self.assertIn('headers["Authorization"] = f"Bearer {token}"', client)
        self.assertIn("HBOS_OCR_SHARED_TOKEN", smoke)

    def _csrf_helper(self) -> tuple[ast.FunctionDef, str]:
        """取 `get_csrf_token` 的 AST 节点与其**代码体**（不含 docstring）源码。

        必须排除 docstring：那里的散文正是在解释「为什么**不**做某件事」，
        直接对整段文本做 assertNotIn 会把说明本身当成违规命中。
        """
        tree = ast.parse(API.read_text())
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == "get_csrf_token":
                body = node.body
                if (
                    body
                    and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)
                ):
                    body = body[1:]
                code = "\n".join(ast.unparse(stmt) for stmt in body)
                return node, code
        raise AssertionError("api.py 中找不到 get_csrf_token")

    def test_csrf_helper_delegates_to_frappe_and_invents_no_token(self):
        """CSRF helper 必须**转发框架的 canonical 实现**，不得自造 token。

        自造 token 会与 session 里存的那份对不上，POST 依然 400；更糟的是看起来
        「已经修好了」。故此处钉死「只转发」这一条。
        """
        _node, code = self._csrf_helper()
        self.assertIn("frappe.sessions", code)
        self.assertIn("_issue_token()", code)
        # 不得自己生成 token
        self.assertNotIn("generate_hash", code)
        self.assertNotIn("secrets.", code)

    def test_csrf_helper_does_not_gate_on_inventory_roles(self):
        """CSRF helper **刻意不做** _require_permission()。

        token 是会话级的、不携带业务数据；调用者能拿到它，前提是已持有该会话的
        有效 cookie，因此不构成提权。若在此校验库存角色，只会给「有 Portal 访问权
        但无库存权限」的用户多一个无意义的失败面，而真正的权限校验在
        recognize_label / create_intake_draft 里逐条把关。

        这条测试是**行为契约**：将来若有人「顺手」给这个 helper 加上权限校验，
        会被这里挡住，从而必须显式讨论而不是默默改掉。
        """
        _node, code = self._csrf_helper()
        self.assertNotIn("_require_permission", code)

    def test_csrf_helper_is_whitelisted_and_documents_itself(self):
        src = API.read_text()
        node, _code = self._csrf_helper()
        decorators = [ast.unparse(d) for d in node.decorator_list]
        self.assertIn("frappe.whitelist()", decorators)
        docstring = ast.get_docstring(node) or ""
        self.assertIn("CSRF", docstring)
        self.assertIn("X-Frappe-CSRF-Token", docstring)
        # 说明必须点出安全边界，而不是只写「给前端用」
        self.assertIn("安全边界", docstring)
        # 只有一处定义，避免将来复制粘贴出第二个同名 helper
        self.assertEqual(1, src.count("def get_csrf_token"))


if __name__ == "__main__":
    unittest.main()
