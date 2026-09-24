"""Destructive LIMS/Inventory integration checks for an isolated CI site only."""

from __future__ import annotations

import os
from contextlib import suppress

import frappe

ITEM = "HBOS-G3-SMOKE-ITEM"
BATCH = "HBOS-G3-SMOKE-BATCH"


def _guard():
    if os.environ.get("HBOS_G3_INTEGRATION_CHECKS") != "1":
        raise RuntimeError("G3 checks may run only on an isolated CI site")


def _cleanup():
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


def _check_lims_projection_unlocks_warehouse_gate():
    from hb_inventory_app.hbos_inventory.quality_projection import project_release
    from hb_inventory_app.hbos_inventory.release_gate import validate_release

    batch_name = _create_batch()
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

    project_release(
        batch_name,
        status="已放行",
        release_date=frappe.utils.today(),
        certificate_no="HBOS-G3-COA",
        certificate_file="/private/files/hbos-g3-smoke.pdf",
        lims_reference="HBOS-G3-SAMPLE",
    )

    validate_release(outward)
    state = frappe.db.get_value(
        "Batch",
        batch_name,
        ["hbos_release_status", "hbos_release_source", "hbos_lims_reference"],
        as_dict=True,
    )
    if state.hbos_release_status != "已放行" or state.hbos_release_source != "LIMS":
        raise AssertionError("LIMS quality projection did not persist authoritative release state")



def schema_columns(doctype):
    """Return the physical DB columns for one DocType on the active site."""
    _guard()
    return sorted(frappe.db.get_table_columns(doctype))


def verify_schema():
    """Verify the critical LIMS/Inventory integration columns on the real DB schema."""
    _guard()
    required = {
        "HBOS Sample": {"item_ref", "batch_ref"},
        "HBOS Test Result": {"approved_signature"},
        "Batch": {"hbos_lims_reference", "hbos_release_source"},
    }
    missing = {}
    for doctype, fields in required.items():
        columns = set(frappe.db.get_table_columns(doctype))
        absent = sorted(fields - columns)
        if absent:
            missing[doctype] = absent
    if missing:
        raise AssertionError(f"missing integration columns: {missing}")
    return {"ok": True, "required": {k: sorted(v) for k, v in required.items()}}


def run():
    _guard()
    frappe.set_user("Administrator")
    _cleanup()
    try:
        _check_audit_does_not_commit_business_transaction()
        _check_lims_projection_unlocks_warehouse_gate()
        return {
            "ok": True,
            "audit_transaction": "pass",
            "lims_inventory_projection": "pass",
        }
    finally:
        _cleanup()
