import frappe
from frappe.model.document import Document
class HBOSKnowledgeImportBatch(Document):
    def validate(self):
        if not self.is_new() and self.has_value_changed('frozen_json'):
            frappe.throw('Frozen import identity cannot be changed')
