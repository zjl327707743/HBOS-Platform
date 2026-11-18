"""The signed lease check is observational and never authorizes execution."""
import json
import hashlib
import sys
import time
from types import ModuleType, SimpleNamespace

import pytest

from hb_knowledge_app.hb_knowledge.service_http import canonical


@pytest.fixture
def scenario(monkeypatch):
    monkeypatch.setitem(sys.modules, 'pymysql', ModuleType('pymysql'))
    cipher=ModuleType('cryptography.fernet');cipher.Fernet=lambda *a:SimpleNamespace()
    monkeypatch.setitem(sys.modules, 'cryptography', ModuleType('cryptography'))
    monkeypatch.setitem(sys.modules, 'cryptography.fernet', cipher)
    frappe=ModuleType('frappe');frappe.whitelist=lambda **kw:(lambda fn:fn)
    writes=[];frappe.db=SimpleNamespace(commit=lambda:None,set_value=lambda *a,**kw:writes.append(a),exists=lambda *a:False)
    frappe.session=SimpleNamespace(user='coordinator@example.test')
    monkeypatch.setitem(sys.modules,'frappe',frappe)
    from hb_knowledge_app.hb_knowledge import maintenance_api, maintenance_access
    monkeypatch.setattr(maintenance_api,'frappe',frappe)
    batch='IMP_'+'a'*32;doc='DOC_S3_'+'b'*24;version='VER_'+'b'*24;sha='c'*64
    item={'canonical_document_id':doc,'version_id':version,'sha256':sha,
          'dataset_id':'d'*32,'ragflow_document_id':'e'*32,
          'owner_inclusion_confirmed':True,'internal_sharing_confirmed':True}
    job={'id':'JOB_TEST','nonce':'f'*48,'status':'Running','lease_generation':7,
         'lease_expires_at':time.time()+120,'document_ids':[doc], 'requested_by':'maintainer@test'}
    raw={'action':'check_task_lease','batch_id':batch,'job_id':job['id'],'nonce':job['nonce'],
         'lease_generation':7,'document_id':doc,'version_id':version,'source_sha256':sha,
         'dataset_id':'d'*32,'native_document_id':'e'*32,'task_id':'1'*32}
    config={'portal_client_id':'PORTAL','maintenance_claim_scope_required':True,
            'maintenance_batch_permit':{'manifest_sha256':'9'*64,'expires_at':time.time()+120,
              'by_batch':{batch:{doc:{'version_id':version,'source_sha256':sha}}}}}
    authority={'allowed':True,'row_status':'Running'}
    principal=SimpleNamespace(client=SimpleNamespace(client_id='PORTAL'))
    monkeypatch.setattr(maintenance_api,'_service_request',lambda **kw:(raw,principal,None))
    monkeypatch.setattr(maintenance_api,'configuration',lambda:config)
    monkeypatch.setattr(maintenance_access,'permitted',lambda user:authority['allowed'])
    def row(_id, lock=False):
        assert lock is True
        return ({'name':batch,'status':authority['row_status'],'job_json':canonical(job)},
                {'items':[item]}, {'items':[item]})
    monkeypatch.setattr(maintenance_api.m,'_row',row)
    return SimpleNamespace(run=maintenance_api.controller,raw=raw,job=job,config=config,
                           item=item,authority=authority,principal=principal,writes=writes)


def test_valid_snapshot_is_not_send_or_ack_authority(scenario):
    result=scenario.run()
    assert result['ok'] is True
    data=result['data']
    assert data['lease_valid_now'] is True
    assert all(data[k] is False for k in ('native_task_membership_verified','authorizes_send',
                                          'authorizes_result_write','authorizes_ack'))
    assert scenario.writes == []


@pytest.mark.parametrize('change', ['nonce','generation','expired','nan','revoked','row_status','source','version','native_doc','task_shape','permit_expired','wrong_client'])
def test_invalid_or_revoked_scope_is_rejected_without_writes(scenario,change):
    if change=='nonce':scenario.raw['nonce']='1'*48
    elif change=='generation':scenario.raw['lease_generation']=6
    elif change=='expired':scenario.job['lease_expires_at']=time.time()-1
    elif change=='nan':scenario.job['lease_expires_at']=float('nan')
    elif change=='revoked':scenario.authority['allowed']=False
    elif change=='row_status':scenario.authority['row_status']='Failed'
    elif change=='source':scenario.raw['source_sha256']='2'*64
    elif change=='version':scenario.raw['version_id']='OTHER'
    elif change=='native_doc':scenario.raw['native_document_id']='3'*32
    elif change=='task_shape':scenario.raw['task_id']='bad'
    elif change=='permit_expired':scenario.config['maintenance_batch_permit']['expires_at']=time.time()-1
    elif change=='wrong_client':scenario.principal.client.client_id='OTHER'
    assert scenario.run()['ok'] is False
    assert scenario.writes == []


def test_service_auth_failure_blocks_before_batch_read(scenario,monkeypatch):
    from hb_knowledge_app.hb_knowledge import maintenance_api
    from hb_knowledge_app.hb_knowledge.errors import KnowledgeError
    monkeypatch.setattr(maintenance_api,'_service_request',
                        lambda **kw: (_ for _ in ()).throw(KnowledgeError('CLIENT_AUTH_FAILED')))
    monkeypatch.setattr(maintenance_api.m,'_row',lambda *a,**kw:pytest.fail('read before authentication'))
    assert scenario.run()['ok'] is False
    assert scenario.writes == []


def _task_manifest(scenario, tmp_path):
    from hb_knowledge_app.hb_knowledge.maintenance_task_facts import planned_shard
    scenario.item.update(binding_revision='BINDING-1', native_profile={'profile_sha256': '8' * 64},
                         upload_sha256='9' * 64)
    task_id, entry = planned_shard(scenario.raw['batch_id'], scenario.item, 0, 1)
    scenario.raw['task_id'] = task_id
    path = tmp_path / 'exact-task-manifest.json'
    path.write_text(json.dumps({'schema': 'hbos.native-task-admission.v1',
                                'tasks': {scenario.raw['task_id']: entry}}))
    scenario.config['maintenance_task_manifest_file'] = str(path)
    scenario.config['maintenance_batch_permit']['task_manifest_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    scenario.job.update(r2_task_manifest_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                        r2_task_ids=[scenario.raw['task_id']])
    return path


def _checkpoint(scenario, operation, **details):
    scenario.raw.update(action='task_checkpoint', operation=operation, details=details)
    before = len(scenario.writes)
    result = scenario.run()
    if result['ok']:
        if operation in ('inspect','authorize_ack'):
            assert len(scenario.writes) == before
        else:
            assert len(scenario.writes) == before + 1
            saved = json.loads(scenario.writes[-1][-1])
            scenario.job.clear()
            scenario.job.update(saved)
        return result['data']
    assert len(scenario.writes) == before
    return None


def test_result_is_durable_before_ack_and_new_generation_only_reconciles_ack(scenario, tmp_path):
    _task_manifest(scenario, tmp_path)
    assert _checkpoint(scenario, 'claim')['execute'] is True
    assert _checkpoint(scenario, 'claim') is None
    assert _checkpoint(scenario, 'ack_result', ack_count=1, result_sha256='4' * 64) is None
    assert _checkpoint(scenario, 'send_intent', attempt_id='try-1', operation_id='embed-1')['state'] == 'SEND_INTENT'
    assert _checkpoint(scenario, 'result_durable', result_sha256='4' * 64) is None
    assert _checkpoint(scenario, 'provider_outcome', attempt_id='try-1', outcome='SUCCESS',
                       receipt_sha256='5' * 64, provider_request_id='provider-123')['state'] == 'PROVIDER_DONE'
    assert _checkpoint(scenario, 'index_write')['state'] == 'INDEX_WRITING'
    assert _checkpoint(scenario, 'result_durable', result_sha256='4' * 64)['state'] == 'RESULT_DURABLE'
    assert _checkpoint(scenario, 'ack_result', ack_count=0, result_sha256='4' * 64)['state'] == 'ACK_UNCERTAIN'
    scenario.job.update(lease_generation=8, nonce='7' * 48)
    assert _checkpoint(scenario, 'claim') is None  # old nonce/generation
    scenario.raw.update(lease_generation=8, nonce=scenario.job['nonce'])
    claim = _checkpoint(scenario, 'claim')
    assert claim == {'state': 'ACK_UNCERTAIN', 'execute': False,
                     'stream': 'hbos:r2:parse:' + scenario.raw['task_id'],
                     'group': 'hbos_r2_native_parse', 'message_id': '1-0'}
    assert _checkpoint(scenario, 'ack_result', ack_count=1, result_sha256='4' * 64)['state'] == 'ACKED'
    assert _checkpoint(scenario, 'claim')['execute'] is False


def test_unknown_send_cannot_be_reclaimed_and_manifest_edits_fail_closed(scenario, tmp_path):
    path = _task_manifest(scenario, tmp_path)
    assert _checkpoint(scenario, 'claim')
    assert _checkpoint(scenario, 'send_intent', attempt_id='try-1', operation_id='embed-1')
    assert _checkpoint(scenario, 'provider_outcome', attempt_id='try-1', outcome='UNKNOWN_EXTERNAL',
                       receipt_sha256='5' * 64, provider_request_id=None)['state'] == 'UNKNOWN_EXTERNAL'
    scenario.job.update(lease_generation=8, nonce='7' * 48)
    scenario.raw.update(lease_generation=8, nonce=scenario.job['nonce'])
    assert _checkpoint(scenario, 'claim') is None
    path.write_bytes(path.read_bytes() + b'\n')
    assert _checkpoint(scenario, 'claim') is None


@pytest.mark.parametrize('preclaim_stops,postclaim_stop',[(0,False),(1,False),(2,False),(2,True)])
def test_only_proven_before_wire_title_can_resume_without_replaying_probe(
        scenario, tmp_path, monkeypatch, preclaim_stops, postclaim_stop):
    from hb_knowledge_app.hb_knowledge import maintenance_api, maintenance_no_wire
    service = ModuleType('knowledge_service')
    service.__path__ = []
    provider_epoch = ModuleType('knowledge_service.provider_epoch')
    provider_epoch.local_epoch = lambda: SimpleNamespace()
    provider_budget = ModuleType('knowledge_service.provider_budget')
    provider_budget.BudgetStopped = type('BudgetStopped', (Exception,), {})
    monkeypatch.setitem(sys.modules, 'knowledge_service', service)
    monkeypatch.setitem(sys.modules, 'knowledge_service.provider_epoch', provider_epoch)
    monkeypatch.setitem(sys.modules, 'knowledge_service.provider_budget', provider_budget)
    from knowledge_service import provider_epoch

    path = _task_manifest(scenario, tmp_path)
    assert _checkpoint(scenario, 'claim')
    assert _checkpoint(scenario, 'send_intent', attempt_id='probe', operation_id='probe-op')
    assert _checkpoint(scenario, 'provider_outcome', attempt_id='probe', outcome='SUCCESS',
                       receipt_sha256='5'*64, provider_request_id='provider-probe')
    raw_lease = dict(scenario.raw)
    task = raw_lease['task_id']
    batch = raw_lease['batch_id']
    old_fact = scenario.job['task_facts'][task]
    scenario.item.update(status='parse_failed', upload_name='frozen.pdf')
    scenario.item['native_profile']['embedding_dimensions']=1024
    scenario.job.update(status='Blocked', nonce=None, lease_generation=8)
    scenario.authority['row_status']='Blocked'
    probe={'attempt_id':'probe','operation_id':'probe-op','request_sha256':maintenance_no_wire._request_sha256('ok')}
    cancelled={'attempt_id':'cancelled-title','operation_id':'title-op',
               'request_sha256':maintenance_no_wire._request_sha256('frozen.pdf')}
    proof=tmp_path/'proof.json'
    proof.write_text(canonical(dict(task_id=task,batch_id=batch,body_embedding_sent=False,
        retry_parent_available=True,redis_notification=dict(pending=True,marker=None,
            consumer='task_executor_common_r2',native_cancelled=False),native_document_sql=dict(run='4',progress=-1),
        settled_dimension_probe=probe,cancelled_filename_embedding=cancelled,terminal_job_id=scenario.job['id'],
        terminal_job_generation=8,task_fact_generation=7,task_identity_sha256=old_fact['identity_sha256'],
        task_manifest_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),original_fact=old_fact)))
    digest=hashlib.sha256(proof.read_bytes()).hexdigest()
    scenario.config['maintenance_no_wire_recovery']=dict(task_id=task,proof_sha256=digest,expires_at=time.time()+120)
    monkeypatch.setattr(maintenance_no_wire,'PROOF',proof)
    monkeypatch.setattr(maintenance_api.m,'registered',lambda *_:None)
    checks=[]
    def ledger(task_id, previous, parent):
        checks.append((task_id,previous,parent))
        return len(checks)>1
    monkeypatch.setattr(provider_epoch,'local_epoch',lambda:SimpleNamespace(confirmed_native_no_wire=ledger))
    scenario.raw.clear()
    scenario.raw.update(action='reconcile_no_wire',batch_id=batch,task_id=task,proof_sha256=digest)
    before=len(scenario.writes)
    assert scenario.run()['ok'] is False and len(scenario.writes)==before
    assert scenario.run()['data']['provider_send_authorized'] is False
    saved=scenario.writes[-1][-1]
    assert json.loads(saved['state_json'])['items'][0]['status']=='parse_queued'
    assert checks==[(task,probe,cancelled)]*2
    scenario.job.update(json.loads(saved['job_json']))
    generation=9
    for number in range(preclaim_stops):
        scenario.job.update(id='STOPPED_BEFORE_CLAIM_'+str(number),status='Blocked',operation='resume',
                            nonce=None,lease_generation=generation)
        scenario.item['status']='parse_failed'
        record=json.loads(proof.read_bytes())
        record.update(terminal_job_id=scenario.job['id'],terminal_job_generation=generation,
                      original_fact=scenario.job['task_facts'][task])
        previous_stop=record.pop('preclaim_stop_sha256',None)
        if previous_stop is not None:
            record.update(original_cancel_proof_sha256=digest,prior_verified_preclaim_stop_sha256=previous_stop)
        for stop_sha in (None,str(8+number)*64):
            if stop_sha is not None:
                record['preclaim_stop_sha256']=stop_sha
            proof.write_text(canonical(record))
            proof_sha=hashlib.sha256(proof.read_bytes()).hexdigest()
            scenario.raw['proof_sha256']=proof_sha
            scenario.config['maintenance_no_wire_recovery']['proof_sha256']=proof_sha
            result=scenario.run()
            assert result['ok'] is (stop_sha is not None)
        scenario.job.update(json.loads(scenario.writes[-1][-1]['job_json']))
        assert scenario.job['task_facts'][task]['attempts']['cancelled-title']['receipt_sha256']==digest
        generation+=1
    scenario.job.update(status='Running',nonce='7'*48,lease_generation=generation)
    scenario.authority['row_status']='Running'
    scenario.raw.clear()
    scenario.raw.update(dict(raw_lease,job_id=scenario.job['id'],nonce='7'*48,lease_generation=generation))
    grant=scenario.config.pop('maintenance_no_wire_recovery')
    assert _checkpoint(scenario,'claim') is None
    scenario.config['maintenance_no_wire_recovery']=grant
    assert _checkpoint(scenario,'claim')['confirmed_no_wire']['parent_attempt_id']=='cancelled-title'
    if postclaim_stop:
        stopped=scenario.job['task_facts'][task]
        assert stopped['status']=='CLAIMED' and stopped['generation']==generation
        scenario.job.update(status='Blocked',nonce=None,operation='resume')
        scenario.authority['row_status']='Blocked'
        scenario.item['status']='parse_failed'
        record=json.loads(proof.read_bytes())
        record.pop('preclaim_stop_sha256')
        entry=json.loads(path.read_bytes())['tasks'][task]
        record.update(terminal_job_generation=generation,task_fact_generation=generation,
            terminal_job_id=scenario.job['id'],original_fact=stopped,
            after_claim_stop_sha256='a'*64,prior_recovery_proof_sha256=grant['proof_sha256'],
            native_task_sql={'retry':3,'progress':-1,'chunks':[],
                             'pages':[entry['from_page'],entry['to_page']]})
        scenario.raw.clear()
        for retry in (3,2):
            record['native_task_sql']['retry']=retry
            proof.write_text(canonical(record))
            new_digest=hashlib.sha256(proof.read_bytes()).hexdigest()
            grant['proof_sha256']=new_digest
            scenario.raw.update(action='reconcile_no_wire',batch_id=batch,task_id=task,proof_sha256=new_digest)
            assert scenario.run()['ok'] is (retry==2)
        scenario.job.update(json.loads(scenario.writes[-1][-1]['job_json']))
        retained=scenario.job['task_facts'][task]
        assert retained['attempts']==stopped['attempts']
        assert retained['generation']==stopped['generation']
        assert retained['verified_no_wire_claim']['fact_sha256']==hashlib.sha256(canonical(stopped).encode()).hexdigest()
        generation+=1
        scenario.job.update(status='Running',nonce='7'*48,lease_generation=generation)
        scenario.authority['row_status']='Running'
        scenario.raw.clear()
        scenario.raw.update(dict(raw_lease,job_id=scenario.job['id'],nonce='7'*48,lease_generation=generation))
        assert _checkpoint(scenario,'claim')['confirmed_no_wire']['native_retry_count']==2
    assert _checkpoint(scenario,'send_intent',attempt_id='repeated-probe',operation_id='probe-op') is None
    assert _checkpoint(scenario,'send_intent',attempt_id='bad-title',operation_id='wrong',
                       parent_attempt_id='cancelled-title') is None
    assert _checkpoint(scenario,'send_intent',attempt_id='new-title',operation_id='title-op',
                       parent_attempt_id='cancelled-title')
    assert _checkpoint(scenario,'send_intent',attempt_id='body',operation_id='body-op') is None
    assert _checkpoint(scenario,'provider_outcome',attempt_id='new-title',outcome='SUCCESS',
                       receipt_sha256='6'*64,provider_request_id='provider-title')
    assert _checkpoint(scenario,'index_write') is None
    assert _checkpoint(scenario,'send_intent',attempt_id='body',operation_id='body-op')
    assert _checkpoint(scenario,'provider_outcome',attempt_id='body',outcome='SUCCESS',
                       receipt_sha256='7'*64,provider_request_id='provider-body')
    assert _checkpoint(scenario,'index_write')['state']=='INDEX_WRITING'
    assert _checkpoint(scenario,'result_durable',result_sha256='4'*64)['state']=='RESULT_DURABLE'
    assert _checkpoint(scenario,'ack_result',ack_count=1,result_sha256='4'*64)['state']=='ACKED'
    attempts=scenario.job['task_facts'][task]['attempts']
    assert attempts['probe']==old_fact['attempts']['probe']
    assert attempts['cancelled-title']['outcome']=='CANCELLED_BEFORE_WIRE'
    assert attempts['new-title']['parent_attempt_id']=='cancelled-title'


def test_preparation_requires_fresh_exact_admission_and_execution_permit(scenario, monkeypatch):
    from hb_knowledge_app.hb_knowledge import maintenance_api
    from hb_knowledge_app.hb_knowledge.maintenance_task_facts import planned_shard, preparation_document
    scenario.item.update(status='uploaded', binding_revision='BINDING-1',
                         native_profile={'profile_sha256':'8' * 64}, upload_sha256='9' * 64)
    batch=scenario.raw['batch_id']
    scenario.config['maintenance_task_checkpoint_required']=True
    scenario.config['maintenance_batch_permit']['prepare_only']=True
    scenario.job['r2_preparation']=True
    fixed={'batch_id':batch,'job_id':scenario.job['id'],'nonce':scenario.job['nonce'],'lease_generation':7}
    task, entry=planned_shard(batch, scenario.item, 0, 2)
    manifest={'schema':'hbos.native-task-admission.v1','tasks':{task:entry}}
    state={'items':[dict(scenario.item,status='parse_queued')]}
    monkeypatch.setattr(maintenance_api.m,'registered',lambda *args:None)
    scenario.raw.clear()
    scenario.raw.update(action='progress',state=state,outcome='Prepared',error=None,prepared_manifest=manifest,**fixed)
    assert scenario.run()['ok'] is False  # no durable preparation grant
    assert not scenario.writes

    scenario.raw.clear()
    scenario.raw.update(action='authorize_preparation',
                        **dict(fixed,**preparation_document(batch,scenario.item)))
    scenario.raw['upload_sha256']='7'*64
    assert scenario.run()['ok'] is False
    scenario.raw['upload_sha256']=scenario.item['upload_sha256']
    monkeypatch.setattr(maintenance_api,'_protected_physical',lambda *args:True)
    assert scenario.run()['ok'] is False
    monkeypatch.setattr(maintenance_api,'_protected_physical',lambda *args:False)
    result=scenario.run()
    assert result['data']['authorizes_preparation'] is True and result['data']['authorizes_send'] is False
    saved=json.loads(scenario.writes[-1][-1])
    scenario.job.update(saved)

    scenario.raw.clear()
    scenario.raw.update(action='progress',state=state,outcome='Completed',error=None,**fixed)
    assert scenario.run()['ok'] is False
    scenario.raw.update(outcome='Prepared',prepared_manifest=manifest)
    result=scenario.run()
    assert result['data']['r2_prepared_sha256']==hashlib.sha256(canonical(manifest).encode()).hexdigest()
    persisted=scenario.writes[-1][-1]
    job=json.loads(persisted['job_json'])
    assert persisted['status']=='Queued' and job['nonce'] is None
    assert job['r2_prepared_tasks_by_document']=={scenario.item['canonical_document_id']:[task]}
    assert 'task_facts' not in job
