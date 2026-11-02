from __future__ import annotations

from frappe.model.document import Document


class HBOSKnowledgeDocument(Document):
    """Metadata and publication state only; never stores source text or chunks."""

    def validate(self):
        import frappe
        if not self.is_new() and self.has_value_changed('document_id'):
            frappe.throw('Knowledge document identity is immutable', frappe.PermissionError)
        if self.name and self.document_id and self.name != self.document_id:
            frappe.throw('Knowledge document identity is inconsistent', frappe.ValidationError)
        if self.current_version:
            parent=frappe.db.get_value('HBOS Knowledge Version',self.current_version,'canonical_document_id')
            if parent != self.document_id:
                frappe.throw('Current version belongs to another document', frappe.ValidationError)
