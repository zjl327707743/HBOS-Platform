import frappe
from frappe.model.document import Document

from hbos_portal.iam import guards, role_models


class HBOSIAMDepartmentAdmission(Document):
    def validate(self):
        role_models.validate_department_admission(self)

    def on_trash(self):
        guards.require_controlled_write()
