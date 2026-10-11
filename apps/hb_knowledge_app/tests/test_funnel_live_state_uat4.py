"""A later processing record must replace its older planned copy in counts."""
import importlib,json,sys
from types import SimpleNamespace

def test_counts_latest_processing_state_once_and_keeps_sharing_pending(monkeypatch):
    item={'canonical_document_id':'DOC_SYNTHETIC','version_id':'VER_SYNTHETIC','disposition':'NEW',
          'status':'planned','internal_sharing_confirmed':False,'owner_inclusion_confirmed':False,
          'sha256':'a'*64,'upload_sha256':'b'*64}
    newer={**item,'status':'parsed/indexed','ragflow_document_id':'c'*32}
    rows=[{'name':'OLD','state_json':json.dumps({'department_key':'safety','items':[item]}),'quality_json':'{}'},
          {'name':'NEW','state_json':json.dumps({'department_key':'safety','items':[newer]}),
           'quality_json':json.dumps({'VER_SYNTHETIC':{'status':'Passed','source_sha256':'a'*64,'upload_sha256':'b'*64}})}]
    def get_all(*a,**kw):
        assert kw['order_by']=='modified asc'
        return rows
    fake=SimpleNamespace(get_all=get_all)
    monkeypatch.setitem(sys.modules,'frappe',fake)
    monkeypatch.setitem(sys.modules,'hb_knowledge_app.hb_knowledge.shared_reference',SimpleNamespace(configuration=lambda:{}))
    m=importlib.import_module('hb_knowledge_app.hb_knowledge.maintenance')
    monkeypatch.setattr(m,'frappe',fake);monkeypatch.setattr(m,'configuration',lambda:{})
    counts=next(row for row in m.department_funnel({}) if row['department']=='safety')
    assert counts['discovered']==counts['uploaded']==counts['parsed']==counts['validated']==1
    assert counts['sharing_pending']==1 and counts['shared_approved']==counts['published']==0

def test_historical_plan_flags_do_not_shadow_current_processing_only_evidence(monkeypatch):
    import hb_knowledge_app.hb_knowledge.maintenance as m
    old={'canonical_document_id':'DOC','version_id':'VER','disposition':'NEW','status':'planned','internal_sharing_confirmed':True,'owner_inclusion_confirmed':True}
    current={**old,'status':'parsed/indexed','ragflow_document_id':'physical','internal_sharing_confirmed':False,'owner_inclusion_confirmed':False}
    rows=[{'name':'OLD','state_json':json.dumps({'department_key':'safety','items':[old]}),'quality_json':'{}'},
          {'name':'NEW','state_json':json.dumps({'department_key':'safety','approval_status':'OWNER_PROCESSING_ONLY','items':[current]}),'quality_json':'{}'}]
    monkeypatch.setattr(m,'frappe',SimpleNamespace(get_all=lambda *a,**k:rows));monkeypatch.setattr(m,'configuration',lambda:{})
    c=next(c for c in m.department_funnel({}) if c['department']=='safety')
    assert c['shared_approved']==0 and c['sharing_pending']==c['uploaded']==c['parsed']==1

def test_explicit_immutable_shared_subset_survives_later_parent_processing_refresh(monkeypatch):
    import hb_knowledge_app.hb_knowledge.maintenance as m
    shared={'canonical_document_id':'DOC','version_id':'VER','disposition':'NEW','status':'parsed/indexed','internal_sharing_confirmed':True,'owner_inclusion_confirmed':True,'approval_ref':'NATIVE_SHARED_APPROVAL:SYNTHETIC'}
    parent={**shared,'internal_sharing_confirmed':False,'owner_inclusion_confirmed':False}
    rows=[{'name':'SHARED','state_json':json.dumps({'department_key':'safety','approval_status':'OWNER_APPROVED','parent_processing_batch':'PARENT','items':[shared]}),'quality_json':'{}'},
          {'name':'PARENT','state_json':json.dumps({'department_key':'safety','approval_status':'OWNER_PROCESSING_ONLY','items':[parent]}),'quality_json':'{}'}]
    monkeypatch.setattr(m,'frappe',SimpleNamespace(get_all=lambda *a,**k:rows));monkeypatch.setattr(m,'configuration',lambda:{})
    c=next(c for c in m.department_funnel({}) if c['department']=='safety')
    assert c['shared_approved']==1 and c['sharing_pending']==0
