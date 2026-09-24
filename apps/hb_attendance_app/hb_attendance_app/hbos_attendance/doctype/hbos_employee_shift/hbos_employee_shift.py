import frappe
from frappe.model.document import Document


class HBOSEmployeeShift(Document):
    def validate(self):
        # Backward compatibility: old rows only stored a concrete Shift Rule version.
        if not self.rule_code and self.shift_rule:
            self.rule_code = frappe.db.get_value(
                "HBOS Shift Rule", self.shift_rule, "rule_code"
            ) or frappe.db.get_value("HBOS Shift Rule", self.shift_rule, "rule_name")

        if not self.rule_code:
            frappe.throw("员工班次绑定必须指向稳定的规则族编码。")

        if self.shift_rule:
            version_code = frappe.db.get_value(
                "HBOS Shift Rule", self.shift_rule, "rule_code"
            )
            if version_code and version_code != self.rule_code:
                frappe.throw("兼容版本指针与规则族编码不一致。")

        duplicate = frappe.db.get_value(
            "HBOS Employee Shift",
            {
                "employee": self.employee,
                "rule_code": self.rule_code,
                "name": ["!=", self.name],
            },
            "name",
        )
        if duplicate:
            frappe.throw(
                f"员工已绑定规则族 {self.rule_code}（{duplicate}），不可重复绑定。"
            )
