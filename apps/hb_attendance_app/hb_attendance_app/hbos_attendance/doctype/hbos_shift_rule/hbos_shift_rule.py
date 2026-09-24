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
        if before and before.rule_code and self.rule_code != before.rule_code:
            frappe.throw("规则族编码是稳定身份，创建后不可修改。")

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
