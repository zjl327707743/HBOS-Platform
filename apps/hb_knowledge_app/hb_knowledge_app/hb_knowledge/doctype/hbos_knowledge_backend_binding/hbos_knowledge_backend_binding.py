from frappe.model.document import Document
import frappe
from ...metadata_integrity import IDENTITY_FIELDS, binding_from_row
from ...errors import KnowledgeError

class HBOSKnowledgeBackendBinding(Document):
    def validate(self):
        if not self.is_new() and any(self.has_value_changed(field) for field in IDENTITY_FIELDS + ('pair_key', 'binding_json')):
            frappe.throw('Knowledge binding identity and projection are immutable', frappe.PermissionError)
        row = self.as_dict()
        space = frappe.db.get_value('HBOS Knowledge Space', self.space_id, ['name', 'enabled'], as_dict=True) or {}
        version = frappe.db.get_value('HBOS Knowledge Version', self.version_id,
                                     ['name', 'version_id', 'canonical_document_id'], as_dict=True) or {}
        document = frappe.db.get_value('HBOS Knowledge Document', self.canonical_document_id,
                                      ['name', 'document_id', 'current_version', 'withdrawn', 'ingestion_status'], as_dict=True) or {}
        row.update(space_record_id=space.get('name'), space_enabled=space.get('enabled'),
                   version_record_id=version.get('name'), version_record_identity=version.get('version_id'),
                   version_document_id=version.get('canonical_document_id'),
                   document_record_id=document.get('name'), document_record_identity=document.get('document_id'),
                   current_version=document.get('current_version'), withdrawn=document.get('withdrawn'),
                   ingestion_status=document.get('ingestion_status'))
        try:
            binding_from_row(row)
        except KnowledgeError:
            frappe.throw('Knowledge metadata is inconsistent', frappe.ValidationError)
