"""Document bookmarks do no vector/model work and retain current authorization."""
import sys
from dataclasses import replace
from types import SimpleNamespace
import pytest
from hb_knowledge_app.hb_knowledge import activity
from hb_knowledge_app.hb_knowledge.errors import KnowledgeError
from .test_catalog_page import catalog_runtime

class Deadlock(Exception):pass

def setup(monkeypatch):
    app,actor,repo,binding=catalog_runtime();app.actor=lambda:actor
    monkeypatch.setitem(sys.modules,'frappe',SimpleNamespace(QueryDeadlockError=Deadlock,db=SimpleNamespace(rollback=lambda:None)))
    authorized=[];written=[]
    monkeypatch.setattr(activity,'authorize_document',lambda r,a,b,q:authorized.append((a,b)) or SimpleNamespace(space_id=b.space_id))
    monkeypatch.setattr(activity,'write',lambda *a,**k:written.append((a,k)) or 'opaque-saved')
    return app,actor,repo,binding,authorized,written

@pytest.mark.parametrize('document,version',[('UNAUTHORIZED','VERSION_TEST'),('DOC_TEST','OLD_VERSION')])
def test_unknown_or_previous_version_cannot_create_a_bookmark(monkeypatch,document,version):
    app,_,_,_,authorized,written=setup(monkeypatch)
    with pytest.raises(KnowledgeError):activity.save_document(app,document,version,'request')
    assert not authorized and not written

def test_catalog_save_selects_exact_current_binding_and_has_no_preview(monkeypatch):
    app,actor,_,b,authorized,written=setup(monkeypatch)
    assert activity.save_document(app,b.canonical_document_id,b.version_id,'request')=='opaque-saved'
    assert authorized==[(actor,b)] and written[0][1]=={'document_bookmark':True}
    assert written[0][0][1]==b.title

def test_revoke_after_write_prevents_return_of_stale_saved_reference(monkeypatch):
    app,_,repo,b,_,written=setup(monkeypatch)
    def write(*a,**k):
        repo.snapshot=replace(repo.snapshot,bindings=(replace(b,withdrawn=True),))
        return 'stale-reference'
    monkeypatch.setattr(activity,'write',write)
    with pytest.raises(KnowledgeError) as failure:activity.save_document(app,b.canonical_document_id,b.version_id,'request')
    assert failure.value.code=='SCOPE_REJECTED'

def test_catalog_explicitly_requires_future_download_permission():
    from hb_knowledge_app.hb_knowledge.reference_admin import get_catalog_page
    app,actor,_,_=catalog_runtime();doc=get_catalog_page(app,actor)['documents'][0]
    assert doc['download_state']=='permission_required' and doc['version_id']=='VERSION_TEST'
    assert not any(key in doc for key in ('url','get_source','download_url','original'))
