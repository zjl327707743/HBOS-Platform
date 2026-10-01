from __future__ import annotations

import frappe
from frappe.model.document import Document


class HBOSAccountOperation(Document):
    def validate(self):
        if not (frappe.flags.get('hbos_operation_authority') == (self.operation if self.doctype == 'HBOS Account Change Event' else self.name)):
            frappe.throw('请使用受控账号变更流程，不能直接修改安全记录。', frappe.PermissionError)

    def on_trash(self):
        if not (frappe.conf.get('hbos_account_test_site') and frappe.flags.get('hbos_owned_test_cleanup')):
            frappe.throw('账号安全与变更历史不得删除。', frappe.PermissionError)
