"""Native marker isolation and compatibility feature gate; no real login."""
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace, ModuleType

import pytest


@pytest.fixture
def session(monkeypatch):
    class Denied(Exception): pass
    def throw(message, kind): raise kind(message)
    native = SimpleNamespace(user='reader@example.test', sid='PRIVATE_NATIVE_SID')
    flags = {'knowledge_native_session_compat': True, 'enabled': 1, 'proof_key': 'PRIVATE_KNOWLEDGE_KEY'}
    f = SimpleNamespace(session=native, conf={'encryption_key': 'PRIVATE_SITE_KEY'},
        local=SimpleNamespace(site='test.local', response_headers={}),
        db=SimpleNamespace(get_value=lambda *a: flags['enabled']),
        sessions=SimpleNamespace(get_csrf_token=lambda: 'NATIVE_CSRF'),
        throw=throw, PermissionError=Denied, AuthenticationError=Denied,
        whitelist=lambda **kw: lambda fn: fn)
    monkeypatch.setitem(sys.modules, 'frappe', f)
    shared=ModuleType('hb_knowledge_app.hb_knowledge.shared_reference')
    shared.configuration=lambda: flags
    monkeypatch.setitem(sys.modules, shared.__name__, shared)
    accounts=ModuleType('hbos_portal.auth.accounts')
    accounts.get_security=lambda: {'user': native.user, 'has_password': True}
    monkeypatch.setitem(sys.modules, accounts.__name__, accounts)
    path=Path(__file__).parents[1]/'hb_knowledge_app/hb_knowledge/native_session.py'
    spec=importlib.util.spec_from_file_location('hb_knowledge_app.hb_knowledge._native_session_test',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module,f,native,flags,Denied


def test_marker_changes_on_native_session_user_and_site_boundaries(session):
    m,f,n,flags,_=session
    first=m.get_request_security()
    assert first['authenticated'] and len(first['session_context'])==64
    assert n.sid not in str(first) and f.conf['encryption_key'] not in str(first)
    assert m.get_request_security()==first
    n.sid='ANOTHER_SESSION';assert m.get_request_security()['session_context']!=first['session_context']
    n.sid='PRIVATE_NATIVE_SID';n.user='other@example.test';assert m.get_request_security()['session_context']!=first['session_context']
    n.user='reader@example.test';f.local.site='another.local';assert m.get_request_security()['session_context']!=first['session_context']


def test_guest_disabled_and_feature_off_fail_closed(session):
    m,f,n,flags,Denied=session
    for user,enabled in [('Guest',1),('reader@example.test',0)]:
        n.user=user;flags['enabled']=enabled
        assert m.get_request_security()=={'authenticated':False,'session_context':None,'csrf_token':None}
        with pytest.raises(Denied):m.get_security()
    flags['knowledge_native_session_compat']=False
    with pytest.raises(Denied):m.get_request_security()


def test_account_view_contains_no_new_roles_or_privileges(session):
    m,f,n,flags,_=session
    result=m.get_security()
    assert result['knowledge_session_contract']=='native-v4-v1'
    assert set(result)=={'user','has_password','session_context','knowledge_session_contract'}
    assert f.local.response_headers['Cache-Control'].startswith('private, no-store')
