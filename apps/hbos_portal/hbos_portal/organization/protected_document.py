"""Framework guards for relationship records. No public write entry point."""
import frappe
from frappe.model.document import Document

from .storage_schema import IMMUTABLE, validate_storage_record
from .write_guard import is_controlled_write
from .native_read_boundary import NativeReadProtectedDocument


class ProtectedRelationDocument(NativeReadProtectedDocument, Document):
    def _check_write(self, *, inserting):
        if not is_controlled_write(self.doctype, self.name):
            frappe.throw("请使用受控岗位任职服务，不能直接修改关系记录。", frappe.PermissionError)
        if not inserting and self.doctype in IMMUTABLE:
            frappe.throw("关系历史与命令收据不可改写。", frappe.PermissionError)
        validate_storage_record(self.doctype, self.name, self.get)

    def validate(self):
        self._check_write(inserting=self.is_new())

    def db_insert(self, *args, **kwargs):
        self._check_write(inserting=True)
        return super().db_insert(*args, **kwargs)

    def db_update(self, *args, **kwargs):
        self._check_write(inserting=False)
        return super().db_update(*args, **kwargs)

    def db_set(self, *args, **kwargs):
        # Partial updates would omit the revision, snapshot and receipt transaction.
        frappe.throw("关系记录不允许单字段直写，请使用受控服务。", frappe.PermissionError)

    def on_trash(self):
        frappe.throw("岗位、任职及其历史必须保留，请办理停用。", frappe.PermissionError)

    def before_rename(self, *args, **kwargs):
        frappe.throw("岗位任职的稳定标识不可更名。", frappe.PermissionError)
