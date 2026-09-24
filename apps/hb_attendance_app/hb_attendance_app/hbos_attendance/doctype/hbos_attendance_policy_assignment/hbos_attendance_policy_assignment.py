import frappe
from frappe.model.document import Document

from hb_attendance_app.hbos_attendance.policy_registry import (
    POLICY_ROTATION_3DAY,
    POLICY_TYPES,
    clear_policy_cache,
)


class HBOSAttendancePolicyAssignment(Document):
    def validate(self):
        if self.policy_type not in POLICY_TYPES:
            frappe.throw("不支持的考勤策略类型：%s" % self.policy_type)

        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            frappe.throw("失效日期不能早于生效日期。")

        if self.policy_type == POLICY_ROTATION_3DAY:
            if not self.effective_from:
                frappe.throw("三日轮转策略必须填写生效日期。")
            if self.anchor_shift not in {"早班", "晚班", "休息"}:
                frappe.throw("三日轮转策略必须填写锚点班次。")

        # Same employee/policy/date version must be unique. Historical versions are
        # allowed when effective_from differs.
        duplicate = frappe.db.get_value(
            "HBOS Attendance Policy Assignment",
            {
                "employee": self.employee,
                "policy_type": self.policy_type,
                "effective_from": self.effective_from,
                "name": ["!=", self.name],
            },
            "name",
        )
        if duplicate:
            frappe.throw(
                "该员工在同一生效日期已存在同类型策略：%s" % duplicate
            )

    def on_update(self):
        clear_policy_cache()

    def on_trash(self):
        clear_policy_cache()
