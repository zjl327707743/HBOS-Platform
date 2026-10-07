from frappe.model.document import Document

class HBOSKnowledgeVersion(Document):
    def validate(self):
        import frappe
        if self.name and self.version_id and self.name != self.version_id:
            frappe.throw('Knowledge version identity is inconsistent', frappe.ValidationError)
        if not self.is_new() and self.has_value_changed('version_id'):
            frappe.throw('Knowledge version identity is immutable', frappe.PermissionError)
        if not self.is_new() and self.has_value_changed("version_json"):
            frappe.throw("Knowledge versions are immutable", frappe.PermissionError)
        if not self.is_new() and self.has_value_changed("canonical_document_id"):
            frappe.throw("Knowledge version identity is immutable", frappe.PermissionError)
