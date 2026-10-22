from __future__ import annotations

import json

import frappe
from frappe.model.document import Document

from hbos_portal.iam import guards, policy


class HBOSIAMPolicy(Document):
    def validate(self):
        guards.require_controlled_write()
        if self.subject_type not in {"User", "Department"} or not frappe.db.exists(self.subject_type, self.subject_name):
            frappe.throw("策略必须关联已有账号或部门。", frappe.ValidationError)
        duplicate = frappe.db.get_value(policy.POLICY, {"subject_type": self.subject_type, "subject_name": self.subject_name}, "name")
        if duplicate and duplicate != self.name:
            frappe.throw("同一对象只能有一份有效授权策略。", frappe.ValidationError)
        if int(self.version or 0) < 1:
            frappe.throw("策略版本无效。", frappe.ValidationError)
        previous = self.get_doc_before_save()
        if previous and (previous.subject_type != self.subject_type or previous.subject_name != self.subject_name):
            frappe.throw("策略对象不可改名或替换。", frappe.PermissionError)
        if previous and int(self.version) != int(previous.version) + 1:
            frappe.throw("策略必须在受控事务中递增版本。", frappe.ValidationError)
        seen = set()
        prior_rules = {json.dumps(policy.rule_dict(row), sort_keys=True, default=str) for row in (previous.rules if previous else [])}
        for row in self.rules or []:
            try:
                unchanged = json.dumps(policy.rule_dict(row), sort_keys=True, default=str) in prior_rules
                # Turning off an integration must not force commands for a
                # different app to delete its untouched stored arrangements.
                # Such rows remain unavailable to evaluation; only an exact
                # pre-existing row is preserved, never a new unknown grant.
                try:
                    normalized = policy.validate_rule(row, root=guards.platform_root() or unchanged)
                except ValueError:
                    if not unchanged:
                        raise
                    key = json.dumps(policy.rule_dict(row), sort_keys=True, default=str)
                    if key in seen:
                        frappe.throw("同一规则不能重复保存。", frappe.ValidationError)
                    seen.add(key)
                    continue
            except ValueError as exc:
                frappe.throw(str(exc), frappe.ValidationError)
            meta = policy.registration(normalized["app_id"], normalized["operation_id"])
            if self.subject_type == "Department" and normalized["operation_id"] != "app.enter" and not meta["ordinary"]:
                frappe.throw("部门普通安排不能授予管理或重要操作。", frappe.PermissionError)
            key = json.dumps(normalized, sort_keys=True, default=str)
            if key in seen:
                frappe.throw("同一规则不能重复保存。", frappe.ValidationError)
            seen.add(key)
            for field, item in normalized.items():
                row.set(field, item)

    def on_trash(self):
        guards.require_controlled_write()
