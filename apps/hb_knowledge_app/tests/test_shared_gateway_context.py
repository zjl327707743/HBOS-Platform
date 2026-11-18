import copy
import pytest
from hb_knowledge_app.hb_knowledge.shared_gateway import issue_actor_context,verify_actor_context,actor_binding
from hb_knowledge_app.hb_knowledge.errors import KnowledgeError

@pytest.fixture
def cfg(tmp_path):
 p=tmp_path/'bridge-key';p.write_bytes(b'private-test-key-not-for-deployment'*2);p.chmod(0o600)
 return {'site':'kb.test','proof_key':'test-only-authority-key','mcp_public_url':'http://127.0.0.1:18550/mcp','shared_gateway_bridge':{'enabled':True,'key_file':str(p),'resource':'http://127.0.0.1:18550/mcp'}}

def test_context_is_bound_to_current_user_and_never_an_oauth_credential(cfg):
 p=issue_actor_context('alice@example.invalid',cfg,'a'*32,now=100)
 fp=actor_binding('alice@example.invalid',cfg)
 assert verify_actor_context(p['proof'],cfg,fp,now=110)['actor_binding']==fp
 assert p['purpose']=='SHARED_GATEWAY_ACTOR_CONTEXT_NOT_A_CREDENTIAL'
 with pytest.raises(KnowledgeError):verify_actor_context(p['proof'],cfg,actor_binding('bob@example.invalid',cfg),now=110)
 with pytest.raises(KnowledgeError):verify_actor_context(p['proof'],cfg,None,now=110)

@pytest.mark.parametrize('now',[96,130,500])
def test_future_and_expired_context_fail_closed(cfg,now):
 proof=issue_actor_context('alice',cfg,'a'*32,now=100)['proof']
 with pytest.raises(KnowledgeError):verify_actor_context(proof,cfg,actor_binding('alice',cfg),now=now)

def test_forgery_site_resource_and_feature_default_off(cfg):
 proof=issue_actor_context('alice',cfg,'a'*32,now=100)['proof'];fp=actor_binding('alice',cfg)
 with pytest.raises(KnowledgeError):verify_actor_context(proof[:-1]+('a' if proof[-1]!='a' else 'b'),cfg,fp,now=110)
 other=copy.deepcopy(cfg);other['site']='another-site'
 with pytest.raises(KnowledgeError):verify_actor_context(proof,other,fp,now=110)
 other=copy.deepcopy(cfg);other['mcp_public_url']=other['shared_gateway_bridge']['resource']='http://127.0.0.1:9999/mcp'
 with pytest.raises(KnowledgeError):verify_actor_context(proof,other,fp,now=110)
 with pytest.raises(KnowledgeError):issue_actor_context('alice',{},'a'*32,now=100)
 for nonce in ['bob',{'actor':'bob'},'a'*33]:
  with pytest.raises(KnowledgeError):issue_actor_context('alice',cfg,nonce,now=100)

def test_context_key_cannot_be_world_or_group_readable(cfg):
 from pathlib import Path
 p=Path(cfg['shared_gateway_bridge']['key_file']);p.chmod(0o644)
 with pytest.raises(KnowledgeError):issue_actor_context('alice',cfg,'a'*32)
