import hashlib

import frappe
from frappe.model.document import Document


def make_rule_code(department, rule_name, shift_type):
    """Create a deterministic identity shared by all versions of one shift rule."""
    raw = "|".join(str(v or "").strip() for v in (department, rule_name, shift_type))
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16].upper()
    return f"HBOS-RULE-{digest}"


class HBOSShiftRule(Document):
    def validate(self):
        if not self.rule_code:
            self.rule_code = make_rule_code(self.department, self.rule_name, self.shift_type)

        before = None if self.is_new() else self.get_doc_before_save()
        if before:
            immutable = (
                "rule_code", "rule_name", "department", "shift_type",
                "start_time", "end_time", "late_after", "min_hours",
                "effective_from", "supersedes", "status",
            )
            changed = [
                field for field in immutable
                if str(before.get(field) or "") != str(self.get(field) or "")
            ]
            if changed:
                frappe.throw(
                    "已保存的班次规则是历史版本，不允许原地修改：{}。"
                    "请通过班次管理创建新版本。".format("、".join(changed))
                )

        # One family can have many versions, but never two versions for the same effective date.
        duplicate = frappe.db.get_value(
            "HBOS Shift Rule",
            {
                "rule_code": self.rule_code,
                "effective_from": self.effective_from,
                "name": ["!=", self.name],
            },
            "name",
        )
        if duplicate:
            frappe.throw(
                f"规则族 {self.rule_code} 在 {self.effective_from} 已存在版本 {duplicate}，"
                "同一天只能有一个版本。"
            )

        # Identity attributes are immutable across versions. Times/min_hours/status may version.
        sibling = frappe.db.get_value(
            "HBOS Shift Rule",
            {"rule_code": self.rule_code, "name": ["!=", self.name]},
            ["rule_name", "department", "shift_type"],
            as_dict=True,
        )
        if sibling:
            current = (
                str(self.rule_name or ""),
                str(self.department or ""),
                str(self.shift_type or ""),
            )
            expected = (
                str(sibling.rule_name or ""),
                str(sibling.department or ""),
                str(sibling.shift_type or ""),
            )
            if current != expected:
                frappe.throw(
                    "同一规则族的名称、部门和班次类型不可随版本变化；"
                    "如需改变这些身份字段，请新建规则族。"
                )
