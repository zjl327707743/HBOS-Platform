"""Access to inventory cards that contain a complete batch / warehouse snapshot.

Cards retain their full-batch accounting semantics. A restricted warehouse view
cannot safely reuse a PDF created by another user, or filter half of an internal
transfer out of its movement table. The current user must therefore be able to
read every Warehouse before rendering or reading these particular snapshots.
The receipt submit hook may create its own derived artifact in a tightly bound
context; it does not grant the submitting user permission to read that PDF.

Recognition uses the existing inventory-card filename, including Frappe's six
character collision suffix and the stored URL. It deliberately does not claim
to identify historical files whose filename AND URL were both changed earlier.
No Batch / LIMS / generic-attachment permission is granted by this module.
"""

from __future__ import annotations

import re
from contextlib import contextmanager
from contextvars import ContextVar
from urllib.parse import unquote, urlsplit

import frappe


_CARD_NAME = re.compile(r"^HBOS-.+-待检证\+货位卡(?:[A-Za-z0-9]{6})?\.pdf$")
_IDENTITY_FIELDS = ("file_name", "file_url", "attached_to_doctype", "attached_to_name")
CARD_PRINT_FORMATS = frozenset({"HBOS 待检证", "HBOS 自产货位卡", "HBOS 外购货位卡"})
# Never derive this capability from form_dict or doc.flags. It exists only
# during the non-whitelisted on_submit hook, then is reset even on failure.
_AUTOMATIC_CARD = ContextVar("hbos_automatic_receipt_card", default=None)


def _is_automatic_batch(batch_name, user=None) -> bool:
    context = _AUTOMATIC_CARD.get()
    user = user or frappe.session.user
    return bool(context and context[0] == user == frappe.session.user and context[2] == batch_name)


@contextmanager
def _automatic_receipt_card(doc, batch_name):
    """Authorize a derived card only for a real, authorized receipt transition."""
    previous = doc.get_doc_before_save()
    actor = frappe.session.user
    if not (
        doc.get("doctype") == "Stock Entry"
        and doc.get("purpose") == "Material Receipt"
        and doc.get("docstatus") == 1
        and getattr(doc, "_action", None) == "submit"
        and previous and previous.get("docstatus") == 0
        and actor != "Guest"
        and frappe.has_permission("Stock Entry", "submit", doc=doc, user=actor)
    ):
        frappe.throw(frappe._("自动卡证只能由获授权的入库提交触发。"), frappe.PermissionError)

    persisted = frappe.db.get_value("Stock Entry", doc.name, ["docstatus", "purpose"], as_dict=True)
    if not persisted or persisted.get("docstatus") != 1 or persisted.get("purpose") != "Material Receipt":
        frappe.throw(frappe._("自动卡证缺少已提交的入库来源。"), frappe.PermissionError)
    batches = frappe.db.sql(
        """select distinct sbe.batch_no
        from `tabSerial and Batch Entry` sbe
        join `tabSerial and Batch Bundle` sbb on sbb.name = sbe.parent
        join `tabStock Ledger Entry` sle on sle.serial_and_batch_bundle = sbb.name
        where sbb.voucher_type = 'Stock Entry' and sbb.voucher_no = %(entry)s
            and sle.voucher_type = 'Stock Entry' and sle.voucher_no = %(entry)s
            and sbb.docstatus = 1 and sbb.is_cancelled = 0 and sbe.is_cancelled = 0
            and sle.is_cancelled = 0 and sbe.qty > 0 and sle.actual_qty > 0
        """,
        {"entry": doc.name},
        pluck=True,
    )
    if batch_name not in batches:
        frappe.throw(frappe._("自动卡证批次必须来自本次入库的真实正向流水。"), frappe.PermissionError)

    token = _AUTOMATIC_CARD.set((actor, doc.name, batch_name))
    try:
        yield
    finally:
        _AUTOMATIC_CARD.reset(token)


@contextmanager
def _automatic_print_permission(doctype, name, print_format):
    """Temporarily allow only the bound receipt's three controlled templates."""
    if doctype != "Batch" or print_format not in CARD_PRINT_FORMATS or not _is_automatic_batch(name):
        yield
        return
    existed = "ignore_print_permissions" in frappe.flags
    previous = frappe.flags.get("ignore_print_permissions")
    frappe.flags.ignore_print_permissions = True
    try:
        yield
    finally:
        if existed:
            frappe.flags.ignore_print_permissions = previous
        else:
            frappe.flags.pop("ignore_print_permissions", None)


def has_unrestricted_warehouse_read(user=None) -> bool:
    """Use current native role + User Permission scope, including historical bins."""
    user = user or frappe.session.user
    if user == "Guest":
        return False
    if user == "Administrator":
        return True
    if not frappe.has_permission("Warehouse", "read", user=user):
        return False
    # No disabled/group filter: an older PDF may contain a warehouse that has
    # since been disabled. Comparing only active leaves would reopen that file.
    visible = set(frappe.get_list("Warehouse", pluck="name", limit_page_length=0, user=user))
    all_warehouses = set(frappe.get_all("Warehouse", pluck="name", limit_page_length=0))
    return all_warehouses.issubset(visible)


def require_full_card_scope(user=None, *, batch_name=None) -> None:
    if not _is_automatic_batch(batch_name, user) and not has_unrestricted_warehouse_read(user):
        frappe.throw(
            frappe._("货位卡包含完整批次的跨仓数量与流水，仅拥有全部仓库读取权限的用户可查看或生成。请使用获授权货位的扫码页或库存报表。"),
            frappe.PermissionError,
        )


def validate_inventory_card_print(doc, method=None, *args, **kwargs):
    """Known inventory formats fail before Jinja wraps errors as PrintFormatError."""
    requested = {frappe.form_dict.get("format"), frappe.form_dict.get("print_format")} - {None, ""}
    if not requested:
        requested = {doc.meta.default_print_format}
    if requested & CARD_PRINT_FORMATS:
        require_full_card_scope(batch_name=doc.name)


def _is_card_record(record) -> bool:
    if not record:
        return False
    filename = str(record.get("file_name") or "")
    url = str(record.get("file_url") or "")
    url_name = unquote(urlsplit(url).path.rsplit("/", 1)[-1])
    named_card = bool(_CARD_NAME.fullmatch(filename))
    url_card = bool(_CARD_NAME.fullmatch(url_name))
    # URL recognition also blocks a second File record that tries to relink the
    # same private blob to an unrelated document or use an innocuous filename.
    return bool(
        (record.get("attached_to_doctype") == "Batch" and (named_card or url_card))
        or (url.startswith("/private/files/") and url_card)
    )


def _stored_record(doc):
    if name := doc.get("name"):
        return frappe.db.get_value("File", name, list(_IDENTITY_FIELDS) + ["is_private"], as_dict=True)
    return None


def is_inventory_card(doc) -> bool:
    return _is_card_record(doc) or _is_card_record(_stored_record(doc))


def _is_new_automatic_file(doc) -> bool:
    """The receipt capability can create its private artifact, not read old PDFs."""
    return bool(
        _is_automatic_batch(doc.get("attached_to_name"))
        and doc.get("attached_to_doctype") == "Batch"
        and frappe.utils.cint(doc.get("is_private"))
        and _is_card_record(doc)
        and not _stored_record(doc)
    )


def inventory_file_has_permission(doc, ptype=None, user=None, debug=False) -> bool:
    """Additional deny-only hook; Frappe's existing File hook still applies."""
    if ptype == "create" and (user or frappe.session.user) == frappe.session.user and _is_new_automatic_file(doc):
        return True
    return not is_inventory_card(doc) or has_unrestricted_warehouse_read(user)


def inventory_file_query_conditions(user=None) -> str:
    """Keep recognised snapshot names/URLs out of a restricted native File list."""
    if has_unrestricted_warehouse_read(user):
        return ""
    return """not (
        (ifnull(`tabFile`.`attached_to_doctype`, '') = 'Batch' and
            (ifnull(`tabFile`.`file_name`, '') like 'HBOS-%-待检证+货位卡%.pdf'
             or ifnull(`tabFile`.`file_url`, '') like '%/HBOS-%-待检证+货位卡%.pdf'))
        or ifnull(`tabFile`.`file_url`, '') like '/private/files/HBOS-%-待检证+货位卡%.pdf'
    )"""


def _validate_inventory_file_write(doc):
    stored = _stored_record(doc)
    if not (_is_card_record(doc) or _is_card_record(stored)):
        return
    automatic = _is_new_automatic_file(doc)
    if not automatic:
        require_full_card_scope()
    if not frappe.utils.cint(doc.get("is_private")):
        frappe.throw(frappe._("库存货位卡必须保留为私有附件。"), frappe.PermissionError)
    if doc.get("attached_to_doctype") != "Batch" or not doc.get("attached_to_name"):
        frappe.throw(frappe._("库存货位卡必须保留在原批次附件中。"), frappe.PermissionError)
    if _is_card_record(stored) and any(doc.get(field) != stored.get(field) for field in _IDENTITY_FIELDS):
        frappe.throw(frappe._("库存货位卡的文件名、地址与批次归属不可改写；请使用重新生成。"), frappe.PermissionError)
    # File ownership does not grant write permission on the attached Batch.
    if not automatic:
        frappe.get_doc("Batch", doc.get("attached_to_name")).check_permission("write")


class InventoryCardFileMixin:
    """Precede File owner/share shortcuts using Frappe v16's additive extension.

    Native private URLs call File.is_downloadable() directly; download_file and
    zip_files read File.get_content(). A has_permission hook alone misses those
    paths, and explicit DocShare can override that hook in generic checks.
    """

    def has_permission(self, permtype="read", *, debug=False, user=None):
        if not inventory_file_has_permission(self, ptype=permtype, user=user, debug=debug):
            return False
        return super().has_permission(permtype, debug=debug, user=user)

    def is_downloadable(self):
        if not inventory_file_has_permission(self, ptype="read"):
            return False
        return super().is_downloadable()

    def get_content(self, *args, **kwargs):
        # File.before_insert reads the newly rendered bytes to save them. This
        # exception is not available for stored files or download/list methods.
        automatic_bytes = _is_new_automatic_file(self) and bool(self.get("content"))
        if is_inventory_card(self) and not automatic_bytes:
            require_full_card_scope()
        return super().get_content(*args, **kwargs)

    def before_insert(self):
        # Native File.before_insert writes/copies bytes before validate runs.
        # Reject an unauthorized artifact before that first physical write.
        _validate_inventory_file_write(self)
        return super().before_insert()

    def validate(self):
        _validate_inventory_file_write(self)
        return super().validate()
