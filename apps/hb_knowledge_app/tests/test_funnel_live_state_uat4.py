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
