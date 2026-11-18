import importlib,sys
from types import SimpleNamespace


def test_equal_business_version_does_not_publish_a_new_parse_candidate(monkeypatch):
    fake=SimpleNamespace(whitelist=lambda **kw:(lambda fn:fn),db=SimpleNamespace(exists=lambda *args:False))
    monkeypatch.setitem(sys.modules,'frappe',fake)
    monkeypatch.setitem(sys.modules,'hb_knowledge_app.hb_knowledge.shared_reference',SimpleNamespace(configuration=lambda:{}))
    m=importlib.import_module('hb_knowledge_app.hb_knowledge.maintenance');monkeypatch.setattr(m,'frappe',fake)
    item={'canonical_document_id':'DOC','version_id':'VER','native_profile':{'profile_sha256':'a'*64},
        'dataset_id':'NEW_DATASET','ragflow_document_id':'NEW_PHYSICAL','binding_revision':'NEW_REV'}
    current={'current_version':'VER','withdrawn':0,'ingestion_status':'published'}
    assert m.is_published_target(item,current) is False
    calls=[]
    fake.db.exists=lambda table,filters:(calls.append((table,filters)) or True)
    assert m.is_published_target(item,current) is True
    assert calls[-1][1]['binding_revision']=='NEW_REV' and calls[-1][1]['document_id']=='NEW_PHYSICAL'
    current['withdrawn']=1
    assert m.is_published_target(item,current) is False
