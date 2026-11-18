import json,sys
from types import SimpleNamespace
import pytest
from hb_knowledge_app.hb_knowledge import activity
from hb_knowledge_app.hb_knowledge.errors import KnowledgeError


def subject(user='synthetic-owner'):return SimpleNamespace(user_ref=user)
def mapping():return {('synthetic-doc','synthetic-version'):SimpleNamespace(binding_ref='synthetic-binding',title='Synthetic reference',canonical_document_id='synthetic-doc',version_id='synthetic-version')}


def configure(monkeypatch,reads):
    row=SimpleNamespace(name='synthetic-activity',publication_id='',creation='2026-01-01',payload_json=json.dumps({'query':'synthetic query','references':[['synthetic-doc','synthetic-version','synthetic-binding','synthetic-chunk']]}))
    monkeypatch.setitem(sys.modules,'frappe',SimpleNamespace(get_all=lambda *a,**k:[row]))
    iterator=iter(reads);monkeypatch.setattr(activity,'current',lambda runtime:next(iterator))


@pytest.mark.parametrize('kind',['History','Bookmark'])
def test_same_actor_same_revision_binding_revocation_cannot_return_old_title(monkeypatch,kind):
    configure(monkeypatch,[(subject(),mapping()),(subject(),{})])
    with pytest.raises(KnowledgeError) as failure:activity.list_activity(object(),kind)
    assert failure.value.code=='SCOPE_REJECTED'


def test_current_actor_change_cannot_return_another_owner_activity(monkeypatch):
    configure(monkeypatch,[(subject(),mapping()),(subject('another-owner'),mapping())])
    with pytest.raises(KnowledgeError) as failure:activity.list_activity(object(),'Bookmark')
    assert failure.value.code=='SCOPE_REJECTED'


def test_already_invalid_saved_item_stays_removable_without_old_source_title(monkeypatch):
    configure(monkeypatch,[(subject(),{}),(subject(),{})])
    assert activity.list_activity(object(),'Bookmark')['items'][0]['titles']==[]
    configure(monkeypatch,[(subject(),{}),(subject(),{})])
    assert activity.list_activity(object(),'Bookmark')['items'][0]['available'] is False


def test_reindex_requires_current_source_hash_and_a_matching_adoption_receipt(monkeypatch):
    source = 'a' * 64
    new = SimpleNamespace(binding_ref='new-binding')
    doc = SimpleNamespace(current_version='version', source_hash=source, withdrawn=0,
                          ingestion_status='published')
    receipt = dict(schema='hbos.parse-revision.v1', business_version_changed=False,
                   canonical_document_id='document', version_id='version',
                   parent_binding_ref='old-binding', new_binding_ref='new-binding',
                   source_sha256=source)
    db = SimpleNamespace(get_value=lambda *a, **k: doc)
    monkeypatch.setitem(sys.modules, 'frappe', SimpleNamespace(
        db=db, get_all=lambda *a, **k: [SimpleNamespace(receipt_json=json.dumps(receipt))],
    ))
    data = {'references': [('document', 'version', 'old-binding', 'old-chunk')]}
    mapping = {('document', 'version'): new}
    assert activity.bindings_for(data, mapping, allow_reindex=True) == [new]
    receipt.update(schema='hbos.parse-rollback.v1', old_authorization_snapshot_restored=False,
                   current_binding_ref='old-binding', return_binding_ref='new-binding')
    assert activity.bindings_for(data, mapping, allow_reindex=True) == [new]
    receipt['old_authorization_snapshot_restored'] = True
    with pytest.raises(KnowledgeError, match='证据不可用'):
        activity.bindings_for(data, mapping, allow_reindex=True)
    receipt['old_authorization_snapshot_restored'] = False
    with pytest.raises(KnowledgeError, match='证据不可用'):
        activity.bindings_for(data, {}, allow_reindex=True)
    doc.source_hash = 'b' * 64
    with pytest.raises(KnowledgeError, match='证据不可用'):
        activity.bindings_for(data, mapping, allow_reindex=True)
    doc.source_hash = source
    doc.withdrawn = 1
    with pytest.raises(KnowledgeError, match='证据不可用'):
        activity.bindings_for(data, mapping, allow_reindex=True)
