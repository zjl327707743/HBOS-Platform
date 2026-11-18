"""Fresh quality preselection must avoid unqualified bodies and retain fences."""
import importlib,json,sys
from types import ModuleType,SimpleNamespace
import pytest

def fixture(monkeypatch,qualities,final=None):
 monkeypatch.setitem(sys.modules,'pymysql',ModuleType('pymysql'))
 cipher=ModuleType('cryptography.fernet');cipher.Fernet=lambda *a:None
 monkeypatch.setitem(sys.modules,'cryptography.fernet',cipher)
 frappe=SimpleNamespace(local=SimpleNamespace());monkeypatch.setitem(sys.modules,'frappe',frappe)
 shared=importlib.import_module('hb_knowledge_app.hb_knowledge.shared_reference')
 shared._cached_registry_row.cache_clear()
 shared._large_registry_rows.clear()
 contract=importlib.import_module('hb_knowledge_app.hb_knowledge.maintenance_contract')
 validated=[];monkeypatch.setattr(contract,'registered',lambda f,s:validated.append(f['id']))
 item={'canonical_document_id':'D','version_id':'V','dataset_id':'DS','ragflow_document_id':'RD','binding_revision':'BR','status':'parsed/indexed','internal_sharing_confirmed':True,'owner_inclusion_confirmed':True,'sha256':'source','upload_sha256':'upload'}
 allrows=[{'name':name,'quality_json':q,'frozen_json':json.dumps({'id':name}),'state_json':json.dumps({'items':[item]})} for name,q in qualities.items()]
 queries=[]
 def rows(cur,sql,args=()):
  queries.append((sql,tuple(args)))
  if sql.startswith('SELECT name,quality_json'):
   return [{'name':r['name'],'quality_json':r['quality_json']} for r in allrows]
  selected=[dict(r) for r in allrows if not args or r['name'] in args]
  for r in selected:
   if final and r['name'] in final:r['quality_json']=final[r['name']]
  return selected
 return shared,frappe,rows,queries,validated,item

def passed():return json.dumps({'V':{'status':'Passed','source_sha256':'source','upload_sha256':'upload'}})

def test_unqualified_candidates_never_load_or_validate_full_manifest(monkeypatch):
 shared,f,rows,queries,validated,item=fixture(monkeypatch,{'queued':'{}','held':'{"V":{"status":"Held"}}'})
 assert shared._registry_pairs(None,{},rows)==(set(),set())
 assert not validated
 assert all('frozen_json' not in sql for sql,args in queries)

def test_only_qualified_batches_keep_all_final_item_checks(monkeypatch):
 shared,f,rows,queries,validated,item=fixture(monkeypatch,{'good':passed(),'pending':'{}'})
 pairs,datasets=shared._registry_pairs(None,{},rows)
 assert pairs=={('D','V','DS','RD','BR')} and datasets=={'DS'}
 assert validated==['good']

def test_final_quality_downgrade_cannot_be_approved_by_preselection(monkeypatch):
 shared,f,rows,queries,validated,item=fixture(monkeypatch,{'good':passed()},final={'good':'{"V":{"status":"Rejected"}}'})
 assert shared._registry_pairs(None,{},rows)==(set(),set())

def test_same_aggregates_do_not_cache_quality_between_requests(monkeypatch):
 shared,f,rows,queries,validated,item=fixture(monkeypatch,{'good':passed()})
 assert shared._registry_pairs(None,{},rows)[0]
 shared,f,rows,queries,validated,item=fixture(monkeypatch,{'good':'{"V":{"status":"Rejected"}}'})
 assert shared._registry_pairs(None,{},rows)==(set(),set())

def test_projection_only_reuses_identical_rows_and_keeps_sharing_fresh(monkeypatch):
    shared, frappe, rows, queries, validated, _ = fixture(monkeypatch, {'good': passed()})
    for _ in range(2):
        frappe.local = SimpleNamespace()
        assert shared._registry_pairs(None, {}, rows)[0] == {('D', 'V', 'DS', 'RD', 'BR')}
    assert validated == ['good']
    assert len(queries) == 4

    def sharing_revoked(cur, sql, args=()):
        result = rows(cur, sql, args)
        for entry in result:
            if 'state_json' in entry:
                entry['state_json'] = entry['state_json'].replace(
                    '"internal_sharing_confirmed": true', '"internal_sharing_confirmed": false')
        return result

    frappe.local = SimpleNamespace()
    assert shared._registry_pairs(None, {}, sharing_revoked) == (set(), set())
    assert validated == ['good', 'good']


def test_large_projection_recomputes_on_same_length_authorization_edit(monkeypatch):
    shared, frappe, rows, _, validated, _ = fixture(monkeypatch, {'good': passed()})
    revoked = False

    def padded(cur, sql, args=()):
        result = rows(cur, sql, args)
        for entry in result:
            if 'state_json' not in entry:
                continue
            entry['frozen_json'] += ' ' * 33000
            if revoked:
                entry['state_json'] = entry['state_json'].replace(
                    '"owner_inclusion_confirmed": true,', '"owner_inclusion_confirmed":false,')
        return result

    for _ in range(2):
        frappe.local = SimpleNamespace()
        assert shared._registry_pairs(None, {}, padded)[0] == {('D', 'V', 'DS', 'RD', 'BR')}
    assert validated == ['good']
    revoked = True
    frappe.local = SimpleNamespace()
    assert shared._registry_pairs(None, {}, padded) == (set(), set())
    assert validated == ['good', 'good']

def test_escaped_passed_value_is_decoded_and_corrupt_other_rows_are_isolated(monkeypatch):
 escaped=passed().replace('Passed',r'\u0050assed')
 shared,f,rows,queries,validated,item=fixture(monkeypatch,{'good':escaped,'corrupt':'null','array':'[]'})
 assert shared._registry_pairs(None,{},rows)[0]=={('D','V','DS','RD','BR')}
 assert validated==['good']

def test_full_registered_identity_gate_is_still_required(monkeypatch):
 from hb_knowledge_app.hb_knowledge.errors import KnowledgeError
 shared,f,rows,queries,validated,item=fixture(monkeypatch,{'good':passed()})
 contract=importlib.import_module('hb_knowledge_app.hb_knowledge.maintenance_contract')
 def corrupt(*a):raise KnowledgeError('INVALID_REQUEST')
 monkeypatch.setattr(contract,'registered',corrupt)
 assert shared._registry_pairs(None,{},rows)==(set(),set())
