from __future__ import annotations

import frappe
from frappe.model.document import Document


class HBOSAccountWriteReceipt(Document):
    """Durable account-write receipt. Written only through the receipt module."""

    def validate(self):
        if not frappe.flags.get("hbos_account_write_receipt_authority"):
            frappe.throw("请使用受控账号安全操作；不能直接改写安全收据。", frappe.PermissionError)
        if not self.is_new():
            frappe.throw("账号安全收据只能由受控操作推进状态。", frappe.PermissionError)

    def on_trash(self):
        if not (frappe.conf.get("hbos_account_test_site") and frappe.flags.get("hbos_owned_test_cleanup")):
            frappe.throw("账号安全收据不得删除。", frappe.PermissionError)
