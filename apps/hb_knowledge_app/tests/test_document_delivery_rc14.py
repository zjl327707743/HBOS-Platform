"""Synthetic byte/authority tests. Real browser and real-source QA are separate."""
from dataclasses import replace
import hashlib
import json
from types import SimpleNamespace, ModuleType
import sys

import pytest

from hb_knowledge_app.hb_knowledge.document_assets import (
    MAX_FILE_BYTES, MAX_RANGE_BYTES, LocalDocumentAssets, byte_range,
)
from hb_knowledge_app.hb_knowledge.document_delivery import DocumentDelivery
from hb_knowledge_app.hb_knowledge.download_policy import document_download_decision
from hb_knowledge_app.hb_knowledge.errors import KnowledgeError
from hb_knowledge_app.hb_knowledge.execution_plan import Actor, GrantPair, ProviderStamp
from hb_knowledge_app.hb_knowledge.repositories import ActorState
from .test_spaces import runtime as policy_fixture


@pytest.fixture
def setup(tmp_path):
    app, actor, repo, binding = policy_fixture()
    repo.snapshot = replace(repo.snapshot, grants=repo.snapshot.grants + (
        GrantPair('ROLE_QA', binding.space_id, 'document.read', 'GRANT_READ'),))
    app.actor = lambda: actor
    app.audit = SimpleNamespace(record=lambda *args: None)
    permission = [False]
    app.provider.authorize_download = lambda *args: permission[0]
    original = tmp_path/'中文资料.pdf'
    body = b'%PDF-1.4\nSYNTHETIC SAFE LAYOUT\n%%EOF\n'
    original.write_bytes(body)
    sha = hashlib.sha256(body).hexdigest()
    row = {'document_id':binding.canonical_document_id, 'source_sha256':sha,
           'original':{'root_id':'source', 'relative_path':original.name,
                       'filename':'中文资料\r\nInjected: bad.pdf'},
           'preview':{'root_id':'source', 'relative_path':original.name,
                      'filename':'中文资料.pdf','sha256':sha,'kind':'ORIGINAL_PDF'}}
    mapping = tmp_path/'assets.json'
    mapping.write_text(json.dumps({'schema':'hbos-document-assets-v1',
                                   'by_version':{binding.version_id:row}}))
    assets = LocalDocumentAssets(mapping, {'source':tmp_path}, lambda b:sha)
    store = {}
    def set_value(k, v, **options):
        if options.get('nx') and k in store:
            return False
        store[k] = v
        return True
    state = SimpleNamespace(set=set_value, get=store.get)
    clock = [100.0]
    delivery = DocumentDelivery(app, assets, state, clock=lambda:clock[0])
    return SimpleNamespace(app=app, actor=actor, repo=repo, binding=binding, body=body,
                           original=original, sha=sha, mapping=mapping, row=row,
                           assets=assets, delivery=delivery, permission=permission, clock=clock)


def ticket(s, purpose='preview'):
    return s.delivery.prepare(s.binding.canonical_document_id, s.binding.version_id,
                              purpose, 'REQ_PREPARE')['content_url'].split('ticket=')[1]


def assert_code(call, code, state=None):
    with pytest.raises(KnowledgeError) as error:
        call()
    assert error.value.code == code
    if state:
        assert error.value.state == state


def test_read_permission_allows_preview_but_download_is_independent(setup):
    s=setup
    data=s.delivery.capabilities(s.binding.canonical_document_id,None,'REQ_CAPS')
    assert data['can_read'] and data['can_preview'] and not data['can_download']
    assert data['download_reason']=='DOWNLOAD_NOT_AUTHORIZED'
    assert_code(lambda:ticket(s,'download'),'DOCUMENT_DELIVERY_UNAVAILABLE','DOWNLOAD_NOT_AUTHORIZED')


def test_authorized_original_is_exact_and_chinese_headers_are_inert(setup):
    s=setup;s.permission[0]=True
    result=s.delivery.content(ticket(s,'download'),None,'REQ_GET')
    assert result.status==200 and result.body==s.body
    assert hashlib.sha256(result.body).hexdigest()==s.sha
    assert result.headers['Content-Type']=='application/octet-stream'
    assert result.headers['Content-Disposition'].startswith('attachment;')
    assert 'filename*=UTF-8' in result.headers['Content-Disposition']
    assert '\r' not in result.headers['Content-Disposition'] and '\n' not in result.headers['Content-Disposition']
    assert 'no-store' in result.headers['Cache-Control']
    assert result.headers['X-Content-Type-Options']=='nosniff'
    assert result.headers['Cross-Origin-Resource-Policy']=='same-origin'


def test_preview_returns_verified_pdf_and_does_not_call_download(setup):
    s=setup
    result=s.delivery.content(ticket(s),None,'REQ_PREVIEW')
    assert result.body==s.body and result.headers['Content-Type']=='application/pdf'
    assert result.headers['Content-Disposition'].startswith('inline;')
    assert 'sandbox' in result.headers['Content-Security-Policy']


def test_derived_preview_is_labeled_and_original_hash_is_also_checked(setup):
    s=setup
    preview=s.original.parent/'preview.pdf';preview.write_bytes(s.body+b'DERIVED')
    data=json.loads(s.mapping.read_text())
    data['by_version'][s.binding.version_id]['preview'].update(
        relative_path=preview.name,sha256=hashlib.sha256(preview.read_bytes()).hexdigest(),kind='DERIVED_PDF')
    s.mapping.write_text(json.dumps(data))
    prepared=s.delivery.prepare(s.binding.canonical_document_id,s.binding.version_id,'preview','REQ_DERIVED')
    assert prepared['kind']=='DERIVED_PDF' and prepared['sha256']!=s.sha
    s.original.write_bytes(b'CORRUPT ORIGINAL')
    assert_code(lambda:s.delivery.content(prepared['content_url'].split('ticket=')[1],None,'REQ_DERIVED_GET'),
                'DOCUMENT_DELIVERY_UNAVAILABLE','ASSET_HASH_MISMATCH')


def test_other_account_cannot_use_ticket(setup):
    s=setup;t=ticket(s)
    s.app.actor=lambda:Actor('OTHER','OTHER_SESSION','g2')
    assert_code(lambda:s.delivery.content(t,None,'REQ_OTHER'),'SCOPE_REJECTED')


def test_new_session_and_disabled_session_do_not_inherit_ticket(setup):
    s=setup;t=ticket(s)
    s.app.actor=lambda:replace(s.actor,session_revision='NEW')
    assert_code(lambda:s.delivery.content(t,None,'REQ_NEW_SESSION'),'SCOPE_REJECTED')
    def denied():raise KnowledgeError('AUTHENTICATION_REQUIRED')
    s.app.actor=denied
    assert_code(lambda:s.delivery.content(t,None,'REQ_DISABLED'),'AUTHENTICATION_REQUIRED')


def test_expired_and_missing_ticket(setup):
    s=setup;t=ticket(s);s.clock[0]+=61
    assert_code(lambda:s.delivery.content(t,None,'REQ_EXPIRED'),'DOCUMENT_DELIVERY_UNAVAILABLE','TICKET_EXPIRED')
    assert_code(lambda:s.delivery.content('a'*43,None,'REQ_MISSING'),'DOCUMENT_DELIVERY_UNAVAILABLE','TICKET_EXPIRED')


@pytest.mark.parametrize('fault',['withdraw','version','read_role'])
def test_ticket_is_not_authorization_after_current_state_changes(setup,fault):
    s=setup;t=ticket(s)
    if fault=='withdraw':s.repo.snapshot=replace(s.repo.snapshot,bindings=(replace(s.binding,withdrawn=True),))
    if fault=='version':s.repo.snapshot=replace(s.repo.snapshot,bindings=(replace(s.binding,version_id='NEXT'),))
    if fault=='read_role':s.repo.snapshot=replace(s.repo.snapshot,actor_state=ActorState(s.actor,(),True))
    assert_code(lambda:s.delivery.content(t,'bytes=0-3','REQ_CHANGED'),'DOCUMENT_READ_UNAVAILABLE')


def test_download_grant_revocation_blocks_previously_issued_link(setup):
    s=setup;s.permission[0]=True;t=ticket(s,'download');s.permission[0]=False
    assert_code(lambda:s.delivery.content(t,None,'REQ_REVOKED'),'DOCUMENT_DELIVERY_UNAVAILABLE','DOWNLOAD_NOT_AUTHORIZED')


def test_revocation_during_read_is_checked_before_bytes_leave(setup):
    s=setup;t=ticket(s)
    s.app.checkpoint=lambda phase:setattr(s.repo,'snapshot',replace(s.repo.snapshot,
                bindings=(replace(s.binding,withdrawn=True),)))
    assert_code(lambda:s.delivery.content(t,None,'REQ_RACE'),'DOCUMENT_READ_UNAVAILABLE')


def test_single_range_and_next_range_after_withdrawal(setup):
    s=setup;t=ticket(s)
    result=s.delivery.content(t,'bytes=5-9','REQ_RANGE')
    assert result.status==206 and result.body==s.body[5:10]
    assert result.headers['Content-Range']==f'bytes 5-9/{len(s.body)}'
    s.repo.snapshot=replace(s.repo.snapshot,bindings=(replace(s.binding,withdrawn=True),))
    assert_code(lambda:s.delivery.content(t,'bytes=10-15','REQ_RANGE_REVOKED'),'DOCUMENT_READ_UNAVAILABLE')


@pytest.mark.parametrize('value',['bytes=1-2,4-5','bytes=-0','bytes=9999-','bytes=3-1','bytes=-','bytes=1.0-2','x'*101])
def test_invalid_ranges_are_bounded_and_rejected(setup,value):
    s=setup
    assert_code(lambda:s.delivery.content(ticket(s),value,'REQ_BAD_RANGE'),'DOCUMENT_RANGE_NOT_SATISFIABLE')


def test_range_length_bound_and_suffixes():
    assert byte_range('bytes=-3',10)==(7,9,206)
    assert byte_range('bytes=7-',10)==(7,9,206)
    assert_code(lambda:byte_range(f'bytes=0-{MAX_RANGE_BYTES}',MAX_RANGE_BYTES+2),'DOCUMENT_RANGE_NOT_SATISFIABLE')


@pytest.mark.parametrize('path',['../secret.pdf','/etc/passwd','https://example.test/x','a\\b.pdf','a/../b.pdf'])
def test_server_mapping_rejects_traversal_urls_and_absolute_paths(setup,path):
    s=setup;data=json.loads(s.mapping.read_text());data['by_version'][s.binding.version_id]['original']['relative_path']=path
    s.mapping.write_text(json.dumps(data))
    assert_code(lambda:ticket(s),'DOCUMENT_DELIVERY_UNAVAILABLE','ASSET_UNAVAILABLE')


def test_symlink_and_hash_mismatch_are_refused(setup):
    s=setup;t=ticket(s)
    other=s.original.parent/'other.pdf';other.write_bytes(s.body)
    s.original.unlink();s.original.symlink_to(other)
    assert_code(lambda:s.delivery.content(t,None,'REQ_SYMLINK'),'DOCUMENT_DELIVERY_UNAVAILABLE','ASSET_UNAVAILABLE')
    s.original.unlink();s.original.write_bytes(b'%PDF-1.4\nDIFFERENT')
    assert_code(lambda:s.delivery.content(t,None,'REQ_HASH'),'DOCUMENT_DELIVERY_UNAVAILABLE','ASSET_HASH_MISMATCH')


def test_large_source_is_refused_before_read(setup):
    s=setup
    with s.original.open('wb') as f:f.truncate(MAX_FILE_BYTES+1)
    assert_code(lambda:ticket(s),'DOCUMENT_DELIVERY_UNAVAILABLE','ASSET_TOO_LARGE')


def test_capabilities_keep_text_reading_when_preview_or_original_missing(setup):
    s=setup;s.original.unlink()
    value=s.delivery.capabilities(s.binding.canonical_document_id,None,'REQ_MISSING_ASSET')
    assert value['can_read'] and not value['can_preview'] and not value['can_download']


@pytest.mark.parametrize('field',['action','role_ref','subject_refs','space_id','document_id','version_id','source_sha256'])
def test_real_provider_requires_every_independent_download_dimension(setup,field,monkeypatch):
    # Only the production import surface is stubbed; the policy decision itself
    # below is the real provider method and uses the real authority snapshot.
    monkeypatch.setitem(sys.modules,'pymysql',ModuleType('pymysql'))
    cipher=ModuleType('cryptography.fernet');cipher.Fernet=lambda *a:None
    monkeypatch.setitem(sys.modules,'cryptography.fernet',cipher)
    from hb_knowledge_app.hb_knowledge.shared_reference import InternalSharedReferenceProvider
    s=setup
    binding=replace(s.binding,source_type='ORDINARY_INTERNAL_KNOWLEDGE',authority_status='INTERNAL_REFERENCE_REVIEWED')
    s.repo.test_only=False
    s.repo.snapshot=replace(s.repo.snapshot,bindings=(binding,),provider=ProviderStamp('INTERNAL_SHARED_REFERENCE','P',None))
    grant={'action':'document.download','role_ref':'ROLE_QA','subject_refs':[s.actor.user_ref],
           'space_id':binding.space_id,'document_id':binding.canonical_document_id,
           'version_id':binding.version_id,'source_sha256':s.sha}
    s.repo.config={'document_delivery_enabled':True,'document_download_grants':[grant]}
    provider=InternalSharedReferenceProvider(s.repo,environment='production',clock=s.app.provider.clock)
    assert provider.authorize_download(s.actor,s.app.client,binding,s.sha)
    grant[field]=['OTHER'] if field=='subject_refs' else 'OTHER'
    assert not provider.authorize_download(s.actor,s.app.client,binding,s.sha)


def test_unknown_download_permissions_and_feature_default_deny():
    assert not document_download_decision(subject_enabled=True,version_current=True).allowed
    assert not document_download_decision(subject_enabled=True,version_current=True,iam_allowed=True,department_allowed=True).allowed
    assert document_download_decision(subject_enabled=True,version_current=True,iam_allowed=True,department_allowed=True,delivery_enabled=True).allowed
