"""R3 disposable-Site dispatcher; this module is never whitelisted."""

import importlib
import json
import os
from pathlib import Path
import re
import time

import frappe


def inventory_reports():
    """SQL report fixtures and export negatives run on their own disposable Site."""
    legacy = importlib.import_module("hbos_portal._owner_r3_legacy_runtime")
    assert frappe.db.count("Stock Ledger Entry") == 0, "Report fixtures require an empty ledger"
    result = legacy.inventory()
    assert result.get("ok") is True, "Native warehouse report checks did not complete"
    assert frappe.db.count("Stock Ledger Entry") == 0, "Report fixtures posted stock"

    # The pinned legacy function explicitly did not test exports. Use another
    # real synthetic session with ordinary roles and a native Warehouse scope;
    # do not inject a cookie, token, export grant, or an authorization override.
    frappe.set_user("Administrator")
    user = "cloud-stock-export@example.invalid"
    time.sleep(8)  # Preserve native User-creation throttling after the legacy users.
    password = legacy.make_user(user, ["Stock User", "Item Manager"])
    frappe.get_doc({
        "doctype": "User Permission", "user": user, "allow": "Warehouse",
        "for_value": "CLOUD-WH-A", "apply_to_all_doctypes": 1,
    }).insert(ignore_permissions=True)
    frappe.db.commit()
    frappe.clear_cache(user=user)
    client = legacy.Client(str(frappe.conf.hbos_portal_origin)).login(user, password)
    status, payload, _ = client.call("frappe.auth.get_logged_user")
    assert status == 200 and payload.get("message") == user, "Export checks require an authenticated session"
    status, _, body = client.call("frappe.client.get_list", {
        "doctype": "Warehouse", "fields": json.dumps(["name"]), "limit_page_length": 200,
    })
    assert status == 200 and "CLOUD-WH-A" in body and "CLOUD-WH-B" not in body, "Export user's native Warehouse scope is invalid"
    frappe.set_user(user)
    checks = []
    for report in ("货位明细表", "库级盘点三对账", "按批号查货位", "效期预警"):
        ref_doctype = frappe.get_cached_value("Report", report, "ref_doctype")
        native_export_granted = bool(frappe.permissions.can_export(ref_doctype))
        for include_children in (0, 1):
            status, payload, body = client.call("frappe.desk.query_report.export_query", {
                "report_name": report,
                "filters": json.dumps({"warehouse": "CLOUD-WH-B", "include_children": include_children}),
                "file_format_type": "CSV", "export_in_background": 0,
            }, post=True)
            leaked = any(marker in body for marker in ("CLOUD-BATCH-B", "CLOUD-SUPPLIER-B"))
            row = {"report": report, "include_children": include_children, "http": status, "leaked": leaked, "native_export_granted": native_export_granted}
            print("[OWNER-R3] inventory-export=" + json.dumps(row, ensure_ascii=False))
            assert status == 403 and not leaked, "Native cross-Warehouse export was not denied: " + json.dumps(row)
            assert payload.get("exc_type") == "PermissionError", "Export rejection must be a native permission denial, not a failed session or CSRF precondition"
            checks.append(row)
    assert frappe.db.count("Stock Ledger Entry") == 0, "Report/export checks posted stock"
    permissions = importlib.import_module("hbos_portal._owner_r3_inventory_permissions").run()
    assert permissions.get("ok") is True, "Native QR/card/private-file checks did not complete"
    assert frappe.db.count("Stock Ledger Entry") == 0, "QR/card permission audit posted stock"
    return {**result, "export": {"ok": True, "checks": checks},
            "permissions": permissions, "site_purpose": "report_fixtures_only"}


def run():
    marker = os.environ.get("HBOS_REPORT_SCOPE_TEST_ID", "")
    assert os.environ.get("GITHUB_ACTIONS") == "true" and re.fullmatch(r"[0-9]+-[0-9]+", marker)
    assert frappe.local.site == "report-scope-" + marker + ".localhost"
    assert str(frappe.conf.hbos_report_scope_ci) == marker
    assert os.environ.get("HBOS_FRAPPE_SMOKE") == "1"
    assert all(os.environ.get(key) == "0" for key in (
        "HBOS_AI_ENABLED", "HBOS_AI_ALLOW_PII", "HBOS_FEISHU_SYNC_ENABLED", "HBOS_DELICLOUD_SYNC_ENABLED"
    ))
    data = json.loads(Path(__file__).with_name("_owner_r3_manifest.json").read_text(encoding="utf-8"))
    domain = os.environ["OWNER_AUDIT_DOMAIN"]
    assert domain in data["candidates"], "Native domain is not enabled in the frozen manifest"
    frappe.set_user("Administrator")
    import erpnext
    import hrms
    versions = {"frappe": frappe.__version__, "erpnext": erpnext.__version__, "hrms": hrms.__version__}
    assert versions["frappe"] == data["upstream"]["frappe_version"], versions
    assert versions["erpnext"] == data["upstream"]["erpnext_version"], versions
    assert {"frappe", "erpnext", "hrms", "hb_attendance_app", "hb_lims_app", "hb_inventory_app", "hbos_portal"}.issubset(frappe.get_installed_apps())
    print("[OWNER-R3] runtime=" + json.dumps({
        "domain": domain, "base": data["base"], "candidate": data["candidates"][domain],
        "versions": versions, "hrms_sha": data["upstream"]["hrms_sha"],
        "installed_apps": frappe.get_installed_apps(), "owner_environment": "NOT_TOUCHED",
    }))
    if domain == "attendance":
        # Preserve the R2 real export and Prepared Report checks after running
        # the current candidate's report_scope_runtime_checks.run(). The legacy
        # LIMS run() references unmerged #43 modules and is deliberately unused.
        result = importlib.import_module("hbos_portal._owner_r3_legacy_runtime").attendance()
    elif domain == "production":
        result = importlib.import_module("hbos_portal._owner_production_audit").run()
    elif domain == "inventory-reports":
        result = inventory_reports()
    elif domain == "inventory-transactions":
        result = importlib.import_module("hbos_portal._owner_inventory_transactions_runtime").run()
    elif domain == "lims":
        result = importlib.import_module("hbos_portal._owner_r3_lims_runtime").run()
    else:
        raise AssertionError("Unsupported R3 domain")
    assert isinstance(result, dict) and result.get("ok") is True, "Incomplete domain runtime result"
    print("[OWNER-R3] result=" + json.dumps({"domain": domain, "result": result}, default=str))
    return {"ok": True, "domain": domain, "result": result}
