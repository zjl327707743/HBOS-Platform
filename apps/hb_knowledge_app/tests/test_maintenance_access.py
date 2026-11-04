from contextlib import contextmanager
from types import SimpleNamespace
import sys,pytest
from hb_knowledge_app.hb_knowledge import maintenance_access as access,connections
from hb_knowledge_app.hb_knowledge.errors import KnowledgeError

@pytest.mark.parametrize('roles,blocked,expected',[(('HBOS Knowledge Reader','HBOS Knowledge Maintainer'),False,True),(('HBOS Knowledge Reader',),False,False),(('HBOS Knowledge Reader','HBOS Knowledge Maintainer'),True,False)])
def test_maintenance_permission_rechecks_native_account_and_roles(monkeypatch,roles,blocked,expected):
    monkeypatch.setitem(sys.modules,'frappe',SimpleNamespace(session=SimpleNamespace(user='SYNTHETIC_USER'),whitelist=lambda **kwargs:lambda fn:fn))
    @contextmanager
    def view():yield object()
    monkeypatch.setitem(sys.modules,'hb_knowledge_app.hb_knowledge.frappe_authority',SimpleNamespace(committed_view=view))
    monkeypatch.setitem(sys.modules,'hb_knowledge_app.hb_knowledge.shared_reference',SimpleNamespace(configuration=lambda:{}))
    def user(cur,name,cfg):
        assert name=='SYNTHETIC_USER'
        if blocked:raise KnowledgeError('AUTHENTICATION_REQUIRED')
        return roles,0
    monkeypatch.setattr(connections,'_user',user)
    assert access.permitted()==expected
