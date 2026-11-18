"""Browser jobs cannot mint arbitrary source, template, space or task authority."""
import copy
import hashlib
import importlib.util
import json

import pytest

from hb_knowledge_app.hb_knowledge.errors import KnowledgeError
from hb_knowledge_app.hb_knowledge import maintenance_managed as managed


def _module_available(name):
    try:
        return importlib.util.find_spec(name) is not None
    except (ModuleNotFoundError, ValueError):
        return False


_JOINT_SERVICE_AVAILABLE = all(_module_available(name) for name in (
    'knowledge_service.native_job_contract', 'knowledge_service.ingestion'))

if _JOINT_SERVICE_AVAILABLE:
    from knowledge_service.native_job_contract import build_profile, binding_revision_for
else:
    # The public app-only CI has no private service wheel. Keep claim-selector
    # unit fixtures self-contained; service-backed admission tests skip below.
    def _canonical(value):
        return json.dumps(value, sort_keys=True, ensure_ascii=True,
                          separators=(',', ':'), allow_nan=False)

    def _sha(value):
        return hashlib.sha256(_canonical(value).encode()).hexdigest()

    def build_profile(parser_id, config, candidate_patch_sha256):
        profile = {'schema': 'hbos.native-execution-profile.v1',
            'ragflow_base_commit': 'ec9c08d809f63ba2815090182fa225899d2437d5',
            'candidate_patch_sha256': candidate_patch_sha256, 'parser_id': parser_id,
            'parser_config': config, 'embedding_model': 'qwen3.7-text-embedding',
            'embedding_dimensions': 1024}
        profile['profile_sha256'] = _sha(profile)
        return profile

    def binding_revision_for(item):
        return 'BR_' + _sha([item.get('version_id'),
                             item['native_profile']['profile_sha256']])[:24]


def _require_joint_service():
    if not _JOINT_SERVICE_AVAILABLE:
        pytest.skip('requires hbos_knowledge_service; covered by the joint service integration run')


def sample(tmp_path,monkeypatch):
    uploads=tmp_path/'uploads';root=uploads/'sample'/'source';root.mkdir(parents=True)
    from hb_knowledge_app.hb_knowledge import maintenance_access
    monkeypatch.setattr(maintenance_access,'permitted',lambda user: user=='qa-maintainer')
    parser={'chunk_token_num':512,'delimiter':'\n','layout_recognize':'Plain Text','html4excel':False,
        'auto_keywords':0,'auto_questions':0,'raptor':{'use_raptor':False},'graphrag':{'use_graphrag':False},
        'filename_embd_weight':.1,'overlapped_percent':0,'table_context_size':0,'image_context_size':0,
        'enable_children':False,'children_delimiter':''}
    profile=build_profile('naive',parser,'a'*64)
    item={'extension':'.txt','canonical_document_id':'DOC_QA','version_id':'VER_QA',
        'sha256':'b'*64,'relative_path':'生产部门/组/普通.txt','disposition':'NEW',
        'owner_inclusion_confirmed':True,'internal_sharing_confirmed':True,'approval_ref':'QA_APPROVED',
        'parser_input':'VERIFIED_ORIGINAL_NATIVE','native_profile':profile,'parser_config':parser,
        'native_source_proof':{'source_sha256':'b'*64,'original_page_count':None,'covered_pages':[],
                               'full_source_requested':True,'prepared_asset':None}}
    item['binding_revision']=binding_revision_for(item)
    frozen={'source_root':str(root),'department_key':'production','batch_sha256':'c'*64,
            'approval_status':'OWNER_APPROVED','items':[item]}
    cfg={'maintenance_upload_root':str(uploads),'maintenance_task_checkpoint_required':True,
         'maintenance_source_registry_enabled':True,'maintenance_managed_policy':{
            'schema':managed.SCHEMA,'enabled':True,'approval_ref':'OWNER_R2_APPROVAL','expires_at':200,
            'profile_sha256':[profile['profile_sha256']],'departments':['production'],
            'write_datasets':{'production':'d'*32}}}
    job={'document_ids':['DOC_QA'],'requested_by':'qa-maintainer'}
    return cfg,frozen,job


def test_exact_browser_admission_creates_its_own_bounded_prepare_permit(tmp_path,monkeypatch):
    _require_joint_service()
    cfg,frozen,job=sample(tmp_path,monkeypatch)
    managed.admit(cfg,frozen,job,now=100)
    permit=managed.batch_permit(cfg,'IMP_'+'e'*32,frozen,job,now=101)
    assert permit['managed'] and permit['prepare_only']
    assert job['managed_admission']['write_dataset_id']=='d'*32
    assert list(permit['by_batch'].values())==[{'DOC_QA':{'version_id':'VER_QA','source_sha256':'b'*64}}]


@pytest.mark.parametrize('field,value',[('source_sha256','0'*64),('requested_by','other'),('write_dataset_id','f'*32)])
def test_client_cannot_change_a_stored_admission(tmp_path,monkeypatch,field,value):
    _require_joint_service()
    cfg,frozen,job=sample(tmp_path,monkeypatch);managed.admit(cfg,frozen,job,now=100)
    if field=='source_sha256':job['managed_admission']['identities'][0]['sha256']=value
    else:job['managed_admission'][field]=value
    with pytest.raises(KnowledgeError):managed.batch_permit(cfg,'IMP_'+'e'*32,frozen,job,now=101)


def test_withdrawn_authority_template_drift_and_budget_expiry_fail_closed(tmp_path,monkeypatch):
    _require_joint_service()
    cfg,frozen,job=sample(tmp_path,monkeypatch);managed.admit(cfg,frozen,job,now=100)
    changed=copy.deepcopy(frozen);changed['items'][0]['internal_sharing_confirmed']=False
    with pytest.raises(KnowledgeError):managed.batch_permit(cfg,'IMP_'+'e'*32,changed,job,now=101)
    with pytest.raises(KnowledgeError):managed.batch_permit(cfg,'IMP_'+'e'*32,frozen,job,now=201)
    altered=copy.deepcopy(cfg);altered['maintenance_managed_policy']['write_datasets']['production']='0'*32
    with pytest.raises(KnowledgeError):managed.batch_permit(altered,'IMP_'+'e'*32,frozen,job,now=101)


def test_a_clone_cannot_expand_roles_or_bypass_its_approved_parent():
    import sys
    from types import ModuleType, SimpleNamespace

    # The assertion is over pure scope projection. Do not make the app-only
    # contract suite install database/crypto runtime clients just to import it.
    sys.modules.setdefault('pymysql', ModuleType('pymysql'))
    crypto = ModuleType('cryptography')
    fernet = ModuleType('cryptography.fernet')
    fernet.Fernet = lambda *args, **kwargs: SimpleNamespace()
    crypto.fernet = fernet
    sys.modules.setdefault('cryptography', crypto)
    sys.modules.setdefault('cryptography.fernet', fernet)
    sys.modules.setdefault('frappe',SimpleNamespace(whitelist=lambda **kwargs:lambda function:function))
    from hb_knowledge_app.hb_knowledge.maintenance_spaces import approved_child_spaces,can_manage_spaces,space_admission
    cfg={'approved_space_ids':['DEPT_PRODUCTION'],'reader_role':'Reader','maintenance_space_creation_enabled':True,
         'maintenance_native_upload_profiles':{'plain':{'profile_sha256':'a'*64}},'fingerprint_key':'test-only-key-xxxxxxxx'}
    row={'name':'KBSPACE_QA','parent_space':'DEPT_PRODUCTION','required_role':'Reader',
         'maintenance_department':'production','template_json':json.dumps(cfg['maintenance_native_upload_profiles'])}
    row['space_admission_json']=json.dumps(space_admission(row,cfg))
    assert approved_child_spaces([row],cfg)=={'DEPT_PRODUCTION','KBSPACE_QA'}
    for change in ({'required_role':'System Manager'},{'parent_space':'UNAPPROVED'}, {'space_admission_json':'{}'}):
        assert approved_child_spaces([{**row,**change}],cfg)=={'DEPT_PRODUCTION'}
    # Updating a parsing default cannot revoke existing published-reader ACLs.
    assert approved_child_spaces([{**row,'template_json':'{}'}],cfg)=={'DEPT_PRODUCTION','KBSPACE_QA'}
    maintainer={'Reader','HBOS Knowledge Maintainer'}
    assert not can_manage_spaces(cfg,'qa-maintainer',maintainer)
    cfg['maintenance_space_manager_users']=['approved-space-manager']
    assert can_manage_spaces(cfg,'approved-space-manager',maintainer)
    assert not can_manage_spaces(cfg,'qa-maintainer',maintainer|{'System Manager'})


def test_resume_allows_durable_ack_or_untouched_shards_but_never_uncertain_send():
    state={'items':[{'canonical_document_id':'DOC_QA','status':'parse_queued'}]}
    job={'document_ids':['DOC_QA'],'task_facts':{'a':{'status':'ACKED','attempts':{'1':{'outcome':'SUCCESS'}}},
          'b':{'status':'CLAIMED','attempts':{}}}}
    assert managed.safe_resume(state,job)
    for status in ('SEND_INTENT','UNKNOWN_EXTERNAL','PROVIDER_DONE','INDEX_WRITING'):
        changed=copy.deepcopy(job);changed['task_facts']['b']['status']=status
        assert not managed.safe_resume(state,changed)
    assert not managed.safe_resume({'items':[{'canonical_document_id':'DOC_QA','status':'upload_intent'}]},job)


def test_validation_requires_exact_acknowledged_native_results():
    state={'items':[{'canonical_document_id':'DOC_QA','status':'parsed/indexed',
        'automatic_quality':{'status':'REPAIR_REQUIRED','reasons':['AUTOMATIC_VALIDATION_UNAVAILABLE']}}]}
    job={'managed_admission':{'sha256':'a'*64},'r2_task_manifest_sha256':'b'*64,'document_ids':['DOC_QA'],
         'r2_task_ids':['task'],'r2_tasks_by_document':{'DOC_QA':['task']},'task_facts':{'task':{'status':'ACKED'}}}
    assert managed.can_validate_existing_result(state,job) and managed.should_revalidate(state['items'][0])
    for changed in ({'r2_tasks_by_document':{}},{'task_facts':{'task':{'status':'UNKNOWN_EXTERNAL'}}},
                    {'task_facts':{'task':{'status':'SEND_INTENT'}}}):
        assert not managed.can_validate_existing_result(state,{**job,**changed})
    state['items'][0]['automatic_quality']['reasons']=['ORIGINAL_TABLE_RELATION_REVIEW']
    assert not managed.should_revalidate(state['items'][0])


def test_one_upload_packet_queues_normal_files_together_and_isolates_a_broken_pdf(tmp_path,monkeypatch):
    _require_joint_service()
    if not _module_available('werkzeug.datastructures'):
        pytest.skip('requires the Frappe/Werkzeug runtime; covered by the joint service integration run')
    from io import BytesIO
    from types import SimpleNamespace
    import time
    from werkzeug.datastructures import FileStorage,MultiDict
    from hb_knowledge_app.hb_knowledge import maintenance_upload_group as group
    from hb_knowledge_app.hb_knowledge import managed_source_registry,maintenance_spaces

    cfg,frozen,_=sample(tmp_path,monkeypatch)
    cfg['maintenance_managed_policy']['expires_at']=time.time()+300
    plain=frozen['items'][0]['native_profile']
    deepdoc=build_profile('naive',{**plain['parser_config'],'layout_recognize':'DeepDOC'},'a'*64)
    cfg['maintenance_native_upload_profiles']={'plain':plain,'deepdoc':deepdoc}
    paths=['无菌车间/一组/one.txt','无菌车间/一组/two.txt','无菌车间/一组/broken.pdf']
    files=MultiDict([('file',FileStorage(stream=BytesIO(raw),filename=path.rsplit('/',1)[-1]))
                    for path,raw in zip(paths,(b'Ordinary witness 17',b'Distinct witness 29',b'%PDF-1.7\n'))])
    monkeypatch.setattr(group,'frappe',SimpleNamespace(
        session=SimpleNamespace(user='qa-maintainer'),local=SimpleNamespace(request=SimpleNamespace(files=files)),
        db=SimpleNamespace(set_value=lambda *args:None,commit=lambda:None,rollback=lambda:None)))
    monkeypatch.setattr(group,'configuration',lambda:cfg)
    monkeypatch.setattr(group,'require',lambda:None)
    monkeypatch.setattr(maintenance_spaces,'intake_space',lambda *args:{'maintenance_template':'auto'})
    monkeypatch.setattr(managed_source_registry,'register',lambda *args:None)
    monkeypatch.setattr(group.m,'_registry',lambda:{'documents':[]})
    persisted={}
    def register(manifest,state,label,user):
        batch='IMP_'+manifest['batch_sha256'][:32]
        persisted[batch]=manifest
        return batch
    monkeypatch.setattr(group.m,'register_batch',register)
    queued=[]
    def queue(batch,doc_ids):
        queued.append((batch,doc_ids))
        return {'job_id':'test-native-job'}
    monkeypatch.setattr(group.m,'queue',queue)
    result=group.upload_group('production','1',json.dumps(paths),'DEPT_PRODUCTION')
    assert result['queued_jobs']==1 and len(queued)==1 and len(queued[0][1])==2
    normal,broken=persisted[result['items'][0]['batch_id']],persisted[result['items'][2]['batch_id']]
    assert {i['relative_path'] for i in normal['items']}==set(paths[:2])
    assert all(i['native_profile']==plain for i in normal['items'])
    assert broken['items'][0]['source_inspection_error']=='PDF_TEXT_OR_PAGE_METADATA_UNAVAILABLE'
    assert managed.queue_kind(broken['items'][0])=='COMPLEX'
    assert result['items'][2]['status']=='REPAIR_REQUIRED'
