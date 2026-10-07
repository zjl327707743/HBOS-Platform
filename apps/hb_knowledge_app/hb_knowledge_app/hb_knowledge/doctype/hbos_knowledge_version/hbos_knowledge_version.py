from frappe.model.document import Document

class HBOSKnowledgeVersion(Document):
    def validate(self):
        import frappe
        if not self.is_new() and self.has_value_changed("version_json"):
            frappe.throw("Knowledge versions are immutable", frappe.PermissionError)
        if not self.is_new() and self.has_value_changed("canonical_document_id"):
            frappe.throw("Knowledge version identity is immutable", frappe.PermissionError)
