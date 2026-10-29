from __future__ import annotations

import json
import re

import frappe
from frappe.model.document import Document

from hbos_portal.iam import audit, guards


class HBOSIAMChangeEvent(Document):
    def validate(self):
        guards.require_controlled_write()
        if not self.is_new():
            frappe.throw("权限变更历史不可改写。", frappe.PermissionError)
        if self.actor != frappe.session.user or not re.fullmatch(r"[a-f0-9]{64}", self.request_hash or ""):
            frappe.throw("审计主体或请求指纹无效。", frappe.ValidationError)
        audit._request_id(self.request_id)
        for field in ("before_json", "after_json"):
            try:
                data = json.loads(self.get(field) or "{}")
            except (ValueError, TypeError):
                frappe.throw("审计快照不是有效JSON。", frappe.ValidationError)
            if data != audit.safe_snapshot(data):
                frappe.throw("审计快照包含未允许字段。", frappe.ValidationError)

    def on_trash(self):
        frappe.throw("权限变更历史不得删除。", frappe.PermissionError)
