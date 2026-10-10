"""Policy ORM protection, independent of permissions and client flags."""
import frappe
from frappe.model.document import Document

from .management_storage import POLICY_REVISION, validate_policy_record
from .write_guard import is_controlled_write
from .native_read_boundary import NativeReadProtectedDocument


class ProtectedPolicyDocument(NativeReadProtectedDocument, Document):
    def _check_write(self, *, inserting):
        if not is_controlled_write(self.doctype, self.name):
            frappe.throw("管理政策只能通过受控运维服务维护。", frappe.PermissionError)
        if not inserting and self.doctype == POLICY_REVISION:
            frappe.throw("管理政策修订不可覆盖。", frappe.PermissionError)
        validate_policy_record(self.doctype, self.name, self.get)

    def validate(self):
        self._check_write(inserting=self.is_new())

    def db_insert(self, *args, **kwargs):
        self._check_write(inserting=True)
        return super().db_insert(*args, **kwargs)

    def db_update(self, *args, **kwargs):
        self._check_write(inserting=False)
        return super().db_update(*args, **kwargs)

    def db_set(self, *args, **kwargs):
        frappe.throw("管理政策不允许单字段直写。", frappe.PermissionError)

    def on_trash(self):
        frappe.throw("管理政策及其修订必须保留，请办理撤销。", frappe.PermissionError)

    def before_rename(self, *args, **kwargs):
        frappe.throw("管理政策稳定标识不可更名。", frappe.PermissionError)
