"""Synthetic active-session TTL boundary; no database, login or provider calls."""
import base64
from contextlib import contextmanager
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType,SimpleNamespace
import pytest
from hb_knowledge_app.hb_knowledge.errors import KnowledgeError
from hb_knowledge_app.hb_knowledge.execution_plan import Client


class Clock:
    now=1000
    def time(self):return self.now


class ExpiringState:
    def __init__(self,clock):self.clock=clock;self.rows={};self.writes=[]
    def get(self,key):
        if key in self.rows and self.rows[key][1]<=self.clock.now:del self.rows[key]
        return self.rows.get(key,(None,0))[0]
    def set(self,key,value,*,ex,nx=False):
        if nx and self.get(key) is not None:return False
        self.rows[key]=(value,self.clock.now+ex);self.writes.append((key,self.clock.now))
        return True


class SyntheticFernet:
    """Only replaces the cipher dependency; crypto behavior is not under test."""
    def __init__(self,*args):pass
    def encrypt(self,value):return base64.b64encode(value)
    def decrypt(self,value):return base64.b64decode(value)


@pytest.fixture
def runtime(monkeypatch):
    # Load the real module under a separate package name so dependency stubs
    # cannot leak a patched authority class into other domain tests.
    monkeypatch.setitem(sys.modules,'pymysql',ModuleType('pymysql'))
    cipher=ModuleType('cryptography.fernet');cipher.Fernet=SyntheticFernet
    monkeypatch.setitem(sys.modules,'cryptography',ModuleType('cryptography'))
    monkeypatch.setitem(sys.modules,'cryptography.fernet',cipher)
    monkeypatch.setitem(sys.modules,'frappe',SimpleNamespace(session=SimpleNamespace(
        user='synthetic@example.test',sid='SYNTHETIC_SESSION')))
    path=Path(__file__).parents[1]/'hb_knowledge_app/hb_knowledge/frappe_authority.py'
    name='hb_knowledge_app.hb_knowledge._uat5_ttl_authority'
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    clock=Clock();state=ExpiringState(clock);native=SimpleNamespace(valid=True,generation='SYNTHETIC_GENERATION',calls=0)
    @contextmanager
    def committed_view():yield object()
    monkeypatch.setattr(module,'committed_view',committed_view)
    monkeypatch.setattr(module,'time',clock)
    def verify_native(*args):
        native.calls+=1
        if not native.valid:raise KnowledgeError('AUTHENTICATION_REQUIRED')
        return ('SYNTHETIC_READER',),native.generation
    monkeypatch.setattr(module.SessionProofs,'_native',verify_native)
    cfg={'site':'synthetic.local','run_id':'SYNTHETIC','proof_key':'SYNTHETIC_KEY',
        'sid_encryption_key':'SYNTHETIC_KEY'}
    proof=module.SessionProofs(state,cfg)
    return SimpleNamespace(proof=proof,clock=clock,state=state,native=native,client=Client('SYNTHETIC_PORTAL'))


def test_activity_renews_after_native_validation_and_crosses_old_ttl_safely(runtime):
    r=runtime;first=r.proof.from_native_request(r.client)
    key='private-proof:'+first.session_ref
    assert json.loads(r.state.get(key))['expires']==1600
    r.clock.now=1598;second=r.proof.from_native_request(r.client)
    assert second==first and r.native.calls==4
    assert json.loads(r.state.get(key))['expires']==2198
    r.clock.now=1601
    assert r.proof.resolve(first,r.client).session_valid


def test_revoked_or_disabled_native_session_cannot_renew_or_reuse_existing_proof(runtime):
    r=runtime;actor=r.proof.from_native_request(r.client)
    r.clock.now=1598;r.native.valid=False;before=list(r.state.writes)
    with pytest.raises(KnowledgeError) as failure:r.proof.from_native_request(r.client)
    assert failure.value.code=='AUTHENTICATION_REQUIRED' and r.state.writes==before
    assert json.loads(r.state.get('private-proof:'+actor.session_ref))['expires']==1600
    with pytest.raises(KnowledgeError) as failure:r.proof.resolve(actor,r.client)
    assert failure.value.code=='AUTHENTICATION_REQUIRED'


def test_security_generation_change_does_not_renew_the_old_actor(runtime):
    r=runtime;old=r.proof.from_native_request(r.client)
    r.clock.now=1598;r.native.generation='SYNTHETIC_NEW_GENERATION'
    current=r.proof.from_native_request(r.client)
    assert current.session_ref!=old.session_ref
    assert json.loads(r.state.get('private-proof:'+old.session_ref))['expires']==1600
    with pytest.raises(KnowledgeError) as failure:r.proof.resolve(old,r.client)
    assert failure.value.code=='AUTHENTICATION_REQUIRED'
    assert r.proof.resolve(current,r.client).session_valid


def test_idle_expired_proof_still_requires_a_new_valid_native_request(runtime):
    r=runtime;actor=r.proof.from_native_request(r.client)
    r.clock.now=1601
    with pytest.raises(KnowledgeError) as failure:r.proof.resolve(actor,r.client)
    assert failure.value.code=='AUTHENTICATION_REQUIRED'
    assert r.proof.from_native_request(r.client)==actor
