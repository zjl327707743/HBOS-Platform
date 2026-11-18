from frappe.model.document import Document


class HBOSKnowledgeParseRevision(Document):
    def validate(self):
        import frappe
        if not self.is_new():
            frappe.throw('Parse revision receipts are immutable', frappe.PermissionError)
        import json
        evidence=json.loads(self.receipt_json)
        if (not isinstance(evidence,dict)
                or evidence.get('schema') not in {'hbos.parse-revision.v1','hbos.parse-rollback.v1'}
                or evidence.get('canonical_document_id')!=self.canonical_document_id
                or evidence.get('version_id')!=self.version_id
                or evidence.get('parent_binding_ref')!=self.parent_binding_ref
                or evidence.get('new_binding_ref')!=self.target_binding_ref
                or evidence.get('profile_hash')!=self.profile_sha256
                or evidence.get('business_version_changed') is not False):
            frappe.throw('Parse revision evidence identity drift', frappe.ValidationError)
        if evidence['schema']=='hbos.parse-rollback.v1' and (
                evidence.get('current_binding_ref')!=self.parent_binding_ref
                or evidence.get('return_binding_ref')!=self.target_binding_ref
                or evidence.get('old_authorization_snapshot_restored') is not False
                or evidence.get('both_backend_indexes_retained') is not True):
            frappe.throw('Parse rollback evidence identity drift', frappe.ValidationError)
