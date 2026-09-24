"""Stable Inventory-side contract for LIMS -> ERPNext Batch quality projection.

Warehouse never owns the quality decision.  Release fields on Batch are read-only
projections and may only be mutated through this module by trusted server-side code.
"""

from __future__ import annotations

import frappe
from frappe import _

PROJECTION_FIELDS = (
    "hbos_release_status",
    "hbos_release_date",
    "hbos_certificate_no",
    "hbos_certificate_file",
    "hbos_lims_reference",
    "hbos_release_source",
)
ALLOWED_STATUS = {"待检", "已放行", "不放行"}


def guard_batch_projection(doc, method=None):
    """Reject direct/user mutation of LIMS-owned release projection fields."""
    before = None if doc.is_new() else doc.get_doc_before_save()
    if doc.flags.get("hbos_quality_projection_write"):
        return

    if doc.is_new():
        changed = [
            field for field in PROJECTION_FIELDS
            if field != "hbos_release_status" and doc.get(field)
        ]
        status = (doc.get("hbos_release_status") or "待检").strip()
        if status not in ("", "待检"):
            changed.append("hbos_release_status")
    else:
        changed = [
            field for field in PROJECTION_FIELDS
            if (doc.get(field) or "") != (before.get(field) or "")
        ]

    if changed:
        frappe.throw(
            _("质量放行字段由 LIMS 投影维护，不能在 Batch 中直接修改：{0}").format(
                "、".join(changed)
            ),
            frappe.PermissionError,
        )


def project_release(
    batch_no,
    *,
    status,
    release_date=None,
    certificate_no=None,
    certificate_file=None,
    lims_reference,
):
    """Apply the authoritative LIMS release result to ERPNext Batch.

    Deliberately not whitelisted.  LIMS calls this stable integration contract
    server-side after its own workflow/SoD/COA rules have succeeded.
    """
    status = str(status or "").strip()
    lims_reference = str(lims_reference or "").strip()
    if status not in ALLOWED_STATUS:
        frappe.throw(_("不支持的质量放行状态：{0}").format(status))
    if not lims_reference:
        frappe.throw(_("LIMS 放行投影必须提供稳定引用。"))
    if status == "已放行":
        missing = []
        if not release_date:
            missing.append(_("放行日期"))
        if not certificate_no:
            missing.append(_("合格证编号"))
        if not certificate_file:
            missing.append(_("合格证附件"))
        if missing:
            frappe.throw(_("已放行投影缺少：{0}").format("、".join(missing)))

    batch = frappe.get_doc("Batch", batch_no)
    batch.flags.hbos_quality_projection_write = True
    batch.hbos_release_status = status
    batch.hbos_release_date = release_date or None
    batch.hbos_certificate_no = certificate_no or None
    batch.hbos_certificate_file = certificate_file or None
    batch.hbos_lims_reference = lims_reference
    batch.hbos_release_source = "LIMS"
    batch.save(ignore_permissions=True)
    return batch.name
