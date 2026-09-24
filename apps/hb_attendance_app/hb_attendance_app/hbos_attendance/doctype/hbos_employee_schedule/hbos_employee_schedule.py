import frappe
from frappe.model.document import Document

SCHEDULE_SOURCES = {"LEGACY", "ROTATION", "IMPORT", "MANUAL", "SWAP"}


class HBOSEmployeeSchedule(Document):
    def validate(self):
        self.source_type = self.source_type or "MANUAL"
        if self.source_type not in SCHEDULE_SOURCES:
            frappe.throw(f"不支持的排班来源：{self.source_type}")

        duplicate = frappe.db.get_value(
            "HBOS Employee Schedule",
            {
                "employee": self.employee,
                "schedule_date": self.schedule_date,
                "name": ["!=", self.name],
            },
            ["name", "source_type"],
            as_dict=True,
        )
        if duplicate:
            frappe.throw(
                f"员工 {self.employee} 在 {self.schedule_date} 已有排班 "
                f"{duplicate.name}（来源 {duplicate.source_type or 'LEGACY'}），"
                "同一员工同一天只能保留一条权威排班。"
            )
