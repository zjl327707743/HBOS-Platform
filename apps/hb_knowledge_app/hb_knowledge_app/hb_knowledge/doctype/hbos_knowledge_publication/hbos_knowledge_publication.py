from frappe.model.document import Document


class HBOSKnowledgePublication(Document):
    def validate(self):
        import frappe
        if not self.is_new():
            frappe.throw("Publication receipts are immutable", frappe.PermissionError)
