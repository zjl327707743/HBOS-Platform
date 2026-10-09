import json,sys
from types import SimpleNamespace
import pytest
from hb_knowledge_app.hb_knowledge import activity
from hb_knowledge_app.hb_knowledge.errors import KnowledgeError


def subject(user='synthetic-owner'):return SimpleNamespace(user_ref=user)
def mapping():return {('synthetic-doc','synthetic-version'):SimpleNamespace(binding_ref='synthetic-binding',title='Synthetic reference')}


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
