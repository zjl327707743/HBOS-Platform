from __future__ import annotations

import frappe
from frappe.model.document import Document

from hbos_portal.iam import guards, policy


class HBOSIAMRule(Document):
    def validate(self):
        guards.require_controlled_write()
        if self.parenttype != policy.POLICY or self.parentfield != "rules":
            frappe.throw("规则只能作为受控策略子表保存。", frappe.PermissionError)

    def on_trash(self):
        guards.require_controlled_write()
