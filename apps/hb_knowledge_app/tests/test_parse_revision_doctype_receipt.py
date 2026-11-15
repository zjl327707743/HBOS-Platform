"""Exercise the actual immutable DocType hook with real forward/rollback proofs."""
import importlib,json,sys,hashlib
from types import ModuleType,SimpleNamespace
import pytest
from .test_parse_revision import case,rollback_case
from hb_knowledge_app.hb_knowledge.parse_revision import replacement,rollback_admission
from hb_knowledge_app.hb_knowledge.service_http import canonical

def validator(monkeypatch):
    frappe=ModuleType('frappe')
    def throw(message,*a):raise ValueError(message)
    frappe.throw=throw;frappe.ValidationError=ValueError;frappe.PermissionError=PermissionError
    model=ModuleType('frappe.model');document=ModuleType('frappe.model.document');document.Document=object
    monkeypatch.setitem(sys.modules,'frappe',frappe)
    monkeypatch.setitem(sys.modules,'frappe.model',model)
    monkeypatch.setitem(sys.modules,'frappe.model.document',document)
    return importlib.import_module('hb_knowledge_app.hb_knowledge.doctype.hbos_knowledge_parse_revision.hbos_knowledge_parse_revision').HBOSKnowledgeParseRevision.validate

def rollback_row():
    args=rollback_case();proof=rollback_admission(*args)
    profile=hashlib.sha256(canonical(args[0]['old_document_technical_metadata']).encode()).hexdigest()
    row=SimpleNamespace(is_new=lambda:True,canonical_document_id=args[3].canonical_document_id,
        version_id=args[3].version_id,parent_binding_ref=args[3].binding_ref,
        target_binding_ref=args[4].binding_ref,profile_sha256=profile,receipt_json=canonical(proof))
    return row,proof

def test_actual_forward_proof_passes_immutable_hook(monkeypatch):
    args=case();new,proof=replacement(*args)
    row=SimpleNamespace(is_new=lambda:True,canonical_document_id=new.canonical_document_id,
        version_id=new.version_id,parent_binding_ref=args[3].binding_ref,
        target_binding_ref=new.binding_ref,profile_sha256=args[0]['native_profile']['profile_sha256'],receipt_json=canonical(proof))
    validator(monkeypatch)(row)

def test_actual_rollback_proof_passes_the_same_persisted_row_hook(monkeypatch):
    row,proof=rollback_row();validator(monkeypatch)(row)

@pytest.mark.parametrize('field',['parent_binding_ref','target_binding_ref','profile_sha256'])
def test_reversed_binding_or_return_profile_drift_is_rejected(monkeypatch,field):
    row,proof=rollback_row();setattr(row,field,'DRIFT')
    with pytest.raises(ValueError):validator(monkeypatch)(row)

def test_existing_receipts_stay_immutable(monkeypatch):
    row,proof=rollback_row();row.is_new=lambda:False
    with pytest.raises(ValueError):validator(monkeypatch)(row)

@pytest.mark.parametrize('field,value',[
    ('schema','unknown'),('current_binding_ref','OTHER'),('return_binding_ref','OTHER'),
    ('old_authorization_snapshot_restored',True),('both_backend_indexes_retained',False)])
def test_rollback_cannot_disguise_direction_or_restore_old_authority(monkeypatch,field,value):
    row,proof=rollback_row();proof[field]=value;row.receipt_json=canonical(proof)
    with pytest.raises(ValueError):validator(monkeypatch)(row)
