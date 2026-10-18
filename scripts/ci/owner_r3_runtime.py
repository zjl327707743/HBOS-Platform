"""R3 disposable-Site dispatcher; this module is never whitelisted."""

import importlib
import json
import os
from pathlib import Path
import re

import frappe


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
    elif domain == "inventory-transactions":
        result = importlib.import_module("hbos_portal._owner_inventory_transactions_runtime").run()
    else:
        raise AssertionError("Unsupported R3 domain")
    assert isinstance(result, dict) and result.get("ok") is True, "Incomplete domain runtime result"
    print("[OWNER-R3] result=" + json.dumps({"domain": domain, "result": result}, default=str))
    return {"ok": True, "domain": domain, "result": result}
