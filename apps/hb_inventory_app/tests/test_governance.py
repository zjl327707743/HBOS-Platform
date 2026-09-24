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


if __name__ == "__main__":
    unittest.main()
