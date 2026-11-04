from frappe.model.document import Document
import frappe
from hbos_portal.iam import guards, role_models


class HBOSIAMRoleAssignment(Document):
    def validate(self):
        role_models.validate_assignment(self)

    def on_trash(self):
        guards.require_controlled_write()
