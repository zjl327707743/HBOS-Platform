"""Destructive LIMS/Inventory integration checks for an isolated CI site only."""

from __future__ import annotations

import os
from contextlib import suppress

import frappe

ITEM = "HBOS-G3-SMOKE-ITEM"
BATCH = "HBOS-G3-SMOKE-BATCH"
SAMPLE = "HBOS-G3-SMOKE-SAMPLE"
COA = "HBOS-G3-SMOKE-COA"
SAMPLE_TYPE = "G3-SMOKE-TYPE"
TEST_ITEM = "G3-SMOKE-TEST"
SPEC = "G3-SMOKE-SPEC"
SAMPLE_ITEM = "G3-SMOKE-SAMPLE-ITEM"


def _guard():
    if os.environ.get("HBOS_G3_INTEGRATION_CHECKS") != "1":
        raise RuntimeError("G3 checks may run only on an isolated CI site")


def _cleanup():
    # Raw SQL cleanup is deliberate: this module only runs on an isolated CI site
    # and must be able to remove terminal-state quality records after the smoke test.
    for table, name in (
        ("tabHBOS COA", COA),
        ("tabHBOS Sample Item", SAMPLE_ITEM),
        ("tabHBOS Sample", SAMPLE),
        ("tabHBOS Specification", SPEC),
        ("tabHBOS Test Item", TEST_ITEM),
        ("tabHBOS Sample Type", SAMPLE_TYPE),
    ):
        with suppress(Exception):
            frappe.db.sql(f"DELETE FROM `{table}` WHERE name = %s", (name,))
    with suppress(Exception):
        if frappe.db.exists("Batch", BATCH):
            frappe.delete_doc("Batch", BATCH, force=True, ignore_permissions=True)
    with suppress(Exception):
        if frappe.db.exists("Item", ITEM):
            frappe.delete_doc("Item", ITEM, force=True, ignore_permissions=True)
    frappe.db.commit()


def _check_audit_does_not_commit_business_transaction():
    from hb_lims_app.hbos_lims.lims_service import audit_log

    todo = frappe.get_doc({
        "doctype": "ToDo",
        "description": "HBOS G3 audit baseline",
        "allocated_to": "Administrator",
    }).insert(ignore_permissions=True)
    frappe.db.commit()

    sp = "hbos_g3_audit_txn"
    frappe.db.savepoint(sp)
    frappe.db.set_value("ToDo", todo.name, "description", "HBOS G3 mutated", update_modified=False)
    audit_log(
        "修改",
        "ToDo",
        todo.name,
        action_text="G3 audit transaction check",
        field_changed="description",
        old_value="HBOS G3 audit baseline",
        new_value="HBOS G3 mutated",
        commit=True,
    )
    frappe.db.rollback(save_point=sp)

    current = frappe.db.get_value("ToDo", todo.name, "description")
    if current != "HBOS G3 audit baseline":
        raise AssertionError("audit_log committed unrelated business mutation")

    frappe.delete_doc("ToDo", todo.name, force=True, ignore_permissions=True)
    frappe.db.commit()


def _create_batch():
    item = frappe.get_doc({
        "doctype": "Item",
        "item_code": ITEM,
        "item_name": "HBOS G3 Smoke Item",
        "item_group": "All Item Groups",
        "stock_uom": "Nos",
        "is_stock_item": 1,
        "has_batch_no": 1,
    }).insert(ignore_permissions=True)

    batch = frappe.get_doc({
        "doctype": "Batch",
        "batch_id": BATCH,
        "item": item.name,
    }).insert(ignore_permissions=True)
    frappe.db.commit()
    return batch.name


def _insert_release_fixture(batch_name):
    now = frappe.utils.now_datetime()
    today = frappe.utils.today()

    frappe.db.sql(
        """INSERT INTO `tabHBOS Sample Type`
           (name, sample_type_code, sample_type_name,
            owner, modified_by, creation, modified, docstatus)
           VALUES (%s,%s,'G3 Smoke Type',
                   'Administrator','Administrator',%s,%s,0)""",
        (SAMPLE_TYPE, SAMPLE_TYPE, now, now),
    )
    frappe.db.sql(
        """INSERT INTO `tabHBOS Test Item`
           (name, item_code, item_name, item_category, significant_digits, limits_type,
            owner, modified_by, creation, modified, docstatus)
           VALUES (%s,%s,'G3 Smoke Test','记录型',2,'记录型',
                   'Administrator','Administrator',%s,%s,0)""",
        (TEST_ITEM, TEST_ITEM, now, now),
    )
    frappe.db.sql(
        """INSERT INTO `tabHBOS Specification`
           (name, spec_code, spec_name, item_ref, material_code, material_name,
            version, effective_date, status,
            owner, modified_by, creation, modified, docstatus)
           VALUES (%s,%s,'G3 Smoke Spec',%s,%s,'HBOS G3 Smoke Item',
                   '1.0',%s,'已生效',
                   'Administrator','Administrator',%s,%s,0)""",
        (SPEC, SPEC, ITEM, ITEM, today, now, now),
    )
    frappe.db.sql(
        """INSERT INTO `tabHBOS Sample`
           (name, naming_series, sample_type, item_ref, material_code, material_name,
            batch_ref, batch_no, sample_source, specification, spec_version,
            priority, status, oos_locked,
            owner, modified_by, creation, modified, docstatus)
           VALUES (%s,'HBOS-SMP-.YYYY.-',%s,%s,%s,%s,%s,%s,
                   '生产取样',%s,'1.0','常规','检验完成',0,
                   'Administrator','Administrator',%s,%s,0)""",
        (
            SAMPLE,
            SAMPLE_TYPE,
            ITEM,
            ITEM,
            "HBOS G3 Smoke Item",
            batch_name,
            batch_name,
            SPEC,
            now,
            now,
        ),
    )
    frappe.db.sql(
        """INSERT INTO `tabHBOS Sample Item`
           (name, parent, parenttype, parentfield, idx, test_item, item_name, limits_type,
            owner, modified_by, creation, modified, docstatus)
           VALUES (%s,%s,'HBOS Sample','items',1,%s,'G3 Smoke Test','记录型',
                   'Administrator','Administrator',%s,%s,0)""",
        (SAMPLE_ITEM, SAMPLE, TEST_ITEM, now, now),
    )
    frappe.db.sql(
        """INSERT INTO `tabHBOS COA`
           (name, naming_series, sample, report_status, pdf_attachment,
            owner, modified_by, creation, modified, docstatus)
           VALUES (%s,'HBOS-COA-.YYYY.-',%s,'已发布',
                   '/private/files/hbos-g3-smoke.pdf',
                   'Administrator','Administrator',%s,%s,0)""",
        (COA, SAMPLE, now, now),
    )
    frappe.db.commit()


def _check_lims_release_unlocks_warehouse_gate():
    from unittest.mock import patch

    from hb_inventory_app.hbos_inventory.release_gate import validate_release
    from hb_lims_app.hbos_lims import lims_service

    batch_name = _create_batch()
    _insert_release_fixture(batch_name)

    outward = frappe._dict({
        "doctype": "Stock Entry",
        "purpose": "Material Issue",
        "items": [
            frappe._dict({
                "batch_no": batch_name,
                "s_warehouse": "CI-SMOKE",
            })
        ],
    })

    blocked = False
    try:
        validate_release(outward)
    except Exception:
        blocked = True
    if not blocked:
        raise AssertionError("unreleased Batch incorrectly passed Warehouse release gate")

    # RBAC/SoD are verified independently by the LIMS runtime tests.  This isolated
    # chain focuses on the business integration contract after authorization succeeds.
    with patch.object(lims_service, "_check_action", lambda *args, **kwargs: None):
        result = lims_service.release_sample(SAMPLE)

    if result.get("batch") != batch_name or result.get("coa") != COA:
        raise AssertionError(f"release_sample returned unexpected projection refs: {result}")

    validate_release(outward)
    state = frappe.db.get_value(
        "Batch",
        batch_name,
        [
            "hbos_release_status",
            "hbos_release_source",
            "hbos_lims_reference",
            "hbos_certificate_no",
            "hbos_certificate_file",
        ],
        as_dict=True,
    )
    if (
        state.hbos_release_status != "已放行"
        or state.hbos_release_source != "LIMS"
        or state.hbos_lims_reference != SAMPLE
        or state.hbos_certificate_no != COA
        or not state.hbos_certificate_file
    ):
        raise AssertionError(
            "LIMS release_sample did not persist the authoritative Batch release projection"
        )



def verify_schema():
    """Verify G3 physical schema on an isolated clean site.

    This is intentionally narrow: it checks the cross-domain columns required by
    the LIMS → ERP Batch → Inventory release contract plus the new Item/Batch
    references that prevent LIMS from becoming a second master-data system.
    """
    _guard()
    required_columns = {
        "HBOS Sample": (
            "item_ref",
            "batch_ref",
            "material_code",
            "material_name",
            "batch_no",
        ),
        "HBOS Specification": (
            "item_ref",
            "material_code",
            "material_name",
        ),
        "Batch": (
            "hbos_release_status",
            "hbos_release_date",
            "hbos_certificate_no",
            "hbos_certificate_file",
            "hbos_lims_reference",
            "hbos_release_source",
        ),
    }

    missing = []
    for doctype, fields in required_columns.items():
        if not frappe.db.table_exists(doctype):
            missing.append(f"{doctype}::<table>")
            continue
        for fieldname in fields:
            if not frappe.db.has_column(doctype, fieldname):
                missing.append(f"{doctype}.{fieldname}")

    if missing:
        raise AssertionError("G3 clean-site schema missing: " + ", ".join(missing))

    return {
        "ok": True,
        "checked_doctypes": sorted(required_columns),
        "checked_columns": sum(len(v) for v in required_columns.values()),
    }

def run():
    _guard()
    frappe.set_user("Administrator")
    _cleanup()
    try:
        _check_audit_does_not_commit_business_transaction()
        _check_lims_release_unlocks_warehouse_gate()
        return {
            "ok": True,
            "audit_transaction": "pass",
            "lims_release_to_inventory": "pass",
        }
    finally:
        _cleanup()
