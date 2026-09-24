"""Explicit company-specific Inventory business seed.

Schema migration must not mutate enterprise master data.  Administrators provide a
private JSON profile and run this helper explicitly with bench execute.

Example profile:
{
  "company": "Example Company",
  "warehouse_root": "All Warehouses - EX",
  "uoms": ["件"],
  "item_groups": [{"name": "原料药", "is_group": 0}],
  "warehouses": [
    {"warehouse_name": "3904 中间库", "is_group": 1, "parent_warehouse": "All Warehouses - EX"}
  ]
}

Production warehouse layouts may be kept outside the public repository.
"""

from __future__ import annotations

import json
from pathlib import Path

import frappe


def _load_profile(path):
    profile_path = Path(path).expanduser().resolve()
    payload = json.loads(profile_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("inventory business seed profile must be a JSON object")
    return payload


def _require_company(payload):
    company = str(payload.get("company") or "").strip()
    root = str(payload.get("warehouse_root") or "").strip()
    if not company or not root:
        raise ValueError("profile requires company and warehouse_root")
    if not frappe.db.exists("Company", company):
        raise ValueError(f"company does not exist: {company}")
    if not frappe.db.exists("Warehouse", root):
        raise ValueError(f"warehouse_root does not exist: {root}")
    return company, root


def _sync_uoms(rows):
    created = 0
    for raw in rows or []:
        name = str(raw or "").strip()
        if not name or frappe.db.exists("UOM", name):
            continue
        frappe.get_doc({"doctype": "UOM", "uom_name": name}).insert(ignore_permissions=True)
        created += 1
    return created


def _sync_item_groups(rows):
    created = updated = 0
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        is_group = 1 if row.get("is_group") else 0
        parent = str(row.get("parent_item_group") or "All Item Groups").strip()
        existing = frappe.db.exists("Item Group", name)
        if not existing:
            frappe.get_doc(
                {
                    "doctype": "Item Group",
                    "item_group_name": name,
                    "parent_item_group": parent,
                    "is_group": is_group,
                }
            ).insert(ignore_permissions=True)
            created += 1
            continue
        doc = frappe.get_doc("Item Group", name)
        changed = False
        if doc.parent_item_group != parent:
            doc.parent_item_group = parent
            changed = True
        if int(doc.is_group or 0) != is_group:
            if frappe.db.exists("Item Group", {"parent_item_group": name}):
                raise ValueError(f"cannot change is_group for item group with children: {name}")
            doc.is_group = is_group
            changed = True
        if changed:
            doc.save(ignore_permissions=True)
            updated += 1
    return created, updated


def _sync_warehouses(company, default_root, rows):
    created = 0
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        short = str(row.get("warehouse_name") or "").strip()
        if not short:
            continue
        parent = str(row.get("parent_warehouse") or default_root).strip()
        if not frappe.db.exists("Warehouse", parent):
            raise ValueError(f"parent warehouse does not exist: {parent}")
        existing = frappe.db.get_value(
            "Warehouse",
            {"warehouse_name": short, "company": company},
            "name",
        )
        if existing:
            continue
        frappe.get_doc(
            {
                "doctype": "Warehouse",
                "warehouse_name": short,
                "company": company,
                "parent_warehouse": parent,
                "is_group": 1 if row.get("is_group") else 0,
            }
        ).insert(ignore_permissions=True)
        created += 1
    return created


def apply_profile(path):
    """Apply a private business-master profile idempotently.

    Deliberately not whitelisted.  Run as an administrator:
      bench --site <site> execute hb_inventory_app.hbos_inventory.business_seed.apply_profile --args '["/secure/profile.json"]'
    """
    payload = _load_profile(path)
    company, root = _require_company(payload)
    summary = {
        "company": company,
        "uoms_created": _sync_uoms(payload.get("uoms")),
        "warehouses_created": _sync_warehouses(company, root, payload.get("warehouses")),
    }
    groups_created, groups_updated = _sync_item_groups(payload.get("item_groups"))
    summary["item_groups_created"] = groups_created
    summary["item_groups_updated"] = groups_updated
    frappe.db.commit()
    return summary
