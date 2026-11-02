"""Metadata retries cannot turn unfinished or wrong physical sources into grants."""
import hashlib,json
from types import SimpleNamespace
import pytest
from hb_knowledge_app.hb_knowledge import reference_admin as admin
from hb_knowledge_app.hb_knowledge.publication import PublicationConflict

def setup(monkeypatch,tmp_path,metadata,run='DONE',source=b'approved synthetic bytes'):
    import requests
    auth=tmp_path/'auth.json';auth.write_text(json.dumps({'base_url':'http://127.0.0.1:9380','token':'synthetic','tenant_id':'a'*32}))
    monkeypatch.setattr('knowledge_service.ingestion.validate_admin_base',lambda *a,**kw:'http://127.0.0.1:9380')
    reads=[];downloads=[];expected={'version_id':'VER_SYNTHETIC','canonical_document_id':'DOC_SYNTHETIC','binding_revision':'BR_SYNTHETIC'}
    item={**expected,'dataset_id':'b'*32,'ragflow_document_id':'c'*32,'upload_sha256':hashlib.sha256(source).hexdigest()}
    class Response:
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def raise_for_status(self):pass
        def iter_content(self,*a):yield source
        def json(self):
            meta=metadata[min(len(reads)-1,len(metadata)-1)]
            return {'code':0,'data':{'docs':[{'id':item['ragflow_document_id'],'meta_fields':meta,'chunk_count':3,'run':run}]}}
    class Session:
        headers={}
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def get(self,url,**kw):
            (reads if 'params' in kw else downloads).append(kw)
            assert kw.get('allow_redirects') is False
            return Response()
    monkeypatch.setattr(requests,'Session',Session);monkeypatch.setattr(admin.time,'sleep',lambda *a:None)
    return {'publication_ragflow_auth_file':str(auth)},item,expected,reads,downloads

def test_settled_identity_then_exact_source_hash(monkeypatch,tmp_path):
    expected={'version_id':'VER_SYNTHETIC','canonical_document_id':'DOC_SYNTHETIC','binding_revision':'BR_SYNTHETIC'}
    cfg,item,_,reads,downloads=setup(monkeypatch,tmp_path,[{},expected]);admin._verify_backend(cfg,item)
    assert len(reads)==2 and len(downloads)==1

def test_permanent_wrong_identity_is_bounded_and_never_downloaded(monkeypatch,tmp_path):
    cfg,item,_,reads,downloads=setup(monkeypatch,tmp_path,[{}])
    with pytest.raises(PublicationConflict):admin._verify_backend(cfg,item)
    assert len(reads)==3 and not downloads

@pytest.mark.parametrize('run',['RUNNING','FAIL'])
def test_unfinished_or_failed_index_cannot_settle_to_publication(monkeypatch,tmp_path,run):
    cfg,item,_,reads,downloads=setup(monkeypatch,tmp_path,[{}],run)
    with pytest.raises(PublicationConflict):admin._verify_backend(cfg,item)
    assert len(reads)==1 and not downloads
