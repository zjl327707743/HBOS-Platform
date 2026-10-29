from frappe.model.document import Document
import frappe
from hbos_portal.iam import guards, role_models


class HBOSIAMRoleRelease(Document):
    def validate(self):
        role_models.validate_release(self)

    def on_trash(self):
        frappe.throw('已发布版本不可删除。', frappe.PermissionError)
