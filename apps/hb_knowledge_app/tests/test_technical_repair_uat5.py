"""Explicit same-source recovery never transiently restores the bad version."""
import copy,hashlib,importlib,json,sys
from types import SimpleNamespace
import pytest
from hb_knowledge_app.hb_knowledge.publication import decide,PublicationConflict,validate_technical_repair,FROZEN_PUBLICATION_FIELDS
from hb_knowledge_app.hb_knowledge.service_http import canonical


# Public domain CI does not install the independently shipped service. This is
# its explicit parser-profile port; real PDF/profile validation is covered by
# the companion service suite and the joint candidate checks.
NATIVE_TEXT_NEWLINE_PROFILE='VERIFIED_NATIVE_TEXT_NEWLINE_V1'

def parser_config_for_profile(profile):
    assert profile==NATIVE_TEXT_NEWLINE_PROFILE
    return {'synthetic_parser_contract':True,'delimiter':'\n'}

@pytest.fixture(autouse=True)
def separate_parser_profile_port(monkeypatch):
    from types import ModuleType
    def approved(item):
        if item.get('parser_config')!=parser_config_for_profile(NATIVE_TEXT_NEWLINE_PROFILE):
            raise ValueError('Synthetic parser profile rejected')
        return NATIVE_TEXT_NEWLINE_PROFILE
    port=ModuleType('knowledge_service.ingestion')
    port.approved_parser_profile=approved;port.NATIVE_TEXT_NEWLINE_PROFILE=NATIVE_TEXT_NEWLINE_PROFILE;port.LOCAL_FULLTEXT_NEWLINE_PROFILE='VERIFIED_LOCAL_FULLTEXT_NEWLINE_V1'
    monkeypatch.setitem(sys.modules,'knowledge_service.ingestion',port)


def items():
    parent={'canonical_document_id':'DOC_SYNTHETIC','version_id':'VER_OLD','sha256':'a'*64,
        'upload_sha256':'b'*64,'binding_revision':'BR_OLD','department_key':'production',
        'business_version':None,'document_number':None,'source_type':'ORDINARY_INTERNAL_KNOWLEDGE',
        'authority_status':'INTERNAL_REFERENCE_REVIEWED','owner_inclusion_confirmed':True,
        'internal_sharing_confirmed':True,'approval_ref':'SYNTHETIC_OWNER_OLD','dataset_id':'1'*32,
        'ragflow_document_id':'2'*32,'title':'合成参考','status':'parsed/indexed','disposition':'NEW'}
    proof={'parent_version_id':'VER_OLD','parent_batch_sha256':'c'*64,'parent_source_sha256':'a'*64,
        'withdrawal_receipt_id':'PUB_SYNTHETIC_WITHDRAW','withdrawal_reason_sha256':hashlib.sha256(b'synthetic quality hold').hexdigest(),
        'approval_ref':'SYNTHETIC_OWNER_TECHNICAL_REPAIR','reason_code':'PARSE_DELIMITER_PRESERVATION'}
    target={**parent,'version_id':'VER_NEW','upload_sha256':'d'*64,'binding_revision':'BR_NEW','ragflow_document_id':'3'*32,
        'approval_ref':'SYNTHETIC_OWNER_NEW','extension':'.pdf','parser_input':'VERIFIED_NATIVE_TEXT',
        'parser_config':parser_config_for_profile(NATIVE_TEXT_NEWLINE_PROFILE),
        'native_text_preflight':{'method':'pypdf-native-v1','source_sha256':'a'*64,'all_pages_have_text':True,'page_count':2,'text_sha256':'e'*64},
        'technical_correction':proof}
    return parent,target


def test_repair_is_distinct_atomic_cas_not_ordinary_restore_or_publish():
    current={'current_version':'VER_OLD','withdrawn':1,'ingestion_status':'retired'}
    assert decide(current,'VER_NEW','repair','VER_OLD')=='REPAIRED'
    assert decide(current,'VER_NEW','publish')=='SKIPPED_WITHDRAWN'
    assert decide(current,'VER_NEW','replace','VER_OLD')=='SKIPPED_WITHDRAWN'
    with pytest.raises(PublicationConflict):decide(current,'VER_NEW','restore','VER_OLD')
    for changed in ({**current,'current_version':'OTHER'},{**current,'withdrawn':0,'ingestion_status':'published'}):
        with pytest.raises(PublicationConflict):decide(changed,'VER_NEW','repair','VER_OLD')
    done={'current_version':'VER_NEW','withdrawn':0,'ingestion_status':'published'}
    assert decide(done,'VER_NEW','repair','VER_OLD')=='RECEIPT_REQUIRED'
    with pytest.raises(PublicationConflict):decide({**done,'withdrawn':1},'VER_NEW','repair','VER_OLD')


@pytest.mark.parametrize('field,value',[
    ('sha256','f'*64),('canonical_document_id','OTHER'),('department_key','safety'),
    ('business_version','invented'),('source_type','COMPANY_CONTROLLED'),('authority_status','CONTROLLED_APPROVED'),
    ('internal_sharing_confirmed',False),('owner_inclusion_confirmed',False),('parser_config',{}),
])
def test_repair_cannot_expand_original_authority_or_change_facts(field,value):
    parent,target=items();target[field]=value
    with pytest.raises(PublicationConflict):validate_technical_repair(target,parent,'VER_OLD')


def publisher(monkeypatch,backend_fails=False):
    parent,item=items();current={'name':parent['canonical_document_id'],'document_id':parent['canonical_document_id'],
        'current_version':'VER_OLD','source_hash':'a'*64,'withdrawn':1,'ingestion_status':'retired','dataset_id':'1'*32}
    original=copy.deepcopy(current);writes=[];commits=[];created={};rolled=[];snapshot={}
    withdrawal={'receipt_id':'PUB_SYNTHETIC_WITHDRAW','canonical_document_id':item['canonical_document_id'],
        'target_version':'VER_OLD','source_hash':'a'*64,'batch_sha256':'c'*64,'reason':'synthetic quality hold'}
    oldmeta={k:parent.get(k) for k in ('sha256','upload_sha256','business_version','document_number','source_type','authority_status')}
    oldbinding={'space_id':'DEPT_PRODUCTION','version_id':'VER_OLD','dataset_id':'1'*32,
        'binding_json':canonical({'canonical_document_id':item['canonical_document_id'],'version_id':'VER_OLD'})}
    def sql(query,*a,**kw):
        if 'Knowledge Space' in query:
            snapshot.update(current=copy.deepcopy(current),created=copy.deepcopy(created))
            return [{'enabled':1,'required_role':'SYN_READER'}]
        if 'Knowledge Publication' in query:return [withdrawal]
        if 'Knowledge Document' in query:return [dict(current)]
        raise AssertionError('Unexpected SQL')
    def get_value(table,name,*a,**kw):
        if table=='HBOS Knowledge Version' and name=='VER_OLD':return {'canonical_document_id':item['canonical_document_id'],'version_json':canonical(oldmeta)}
        if table=='HBOS Knowledge Backend Binding' and name=='BIND_OLD':return oldbinding
        value=created.get((table,name))
        return {**value,'name':name} if value else None
    def set_value(table,name,value,*a,**kw):
        assert table=='HBOS Knowledge Document';writes.append(dict(value));current.update(value)
    def rollback():
        current.clear();current.update(snapshot.get('current',original));created.clear();created.update(snapshot.get('created',{}));rolled.append(True)
    def get_doc(value):
        def insert(**kw):
            name=value.get('receipt_id') or (value.get('binding_ref') if value['doctype']=='HBOS Knowledge Backend Binding' else value.get('version_id'))
            created[(value['doctype'],name)]=value;return value
        return SimpleNamespace(insert=insert)
    db=SimpleNamespace(sql=sql,get_value=get_value,set_value=set_value,commit=lambda:commits.append(dict(current)),rollback=rollback,
        exists=lambda table,name:table=='HBOS Knowledge Space' or (table,name) in created)
    fake=SimpleNamespace(db=db,get_doc=get_doc,QueryDeadlockError=type('SyntheticDeadlock',(Exception,),{}))
    monkeypatch.setitem(sys.modules,'frappe',fake)
    cfg={'approved_batch_sha256s':['f'*64],'approved_space_ids':['DEPT_PRODUCTION'],'reader_role':'SYN_READER',
        'approved_dataset_ids':['1'*32],'approved_document_ids':[item['canonical_document_id']],
        'approved_publication_items':{'f'*64:{item['canonical_document_id']:{k:item.get(k) for k in FROZEN_PUBLICATION_FIELDS}}},
        'approved_technical_repairs':{item['canonical_document_id']:{'proof':item['technical_correction'],'parent_item':parent,'parent_quality_sha256':'9'*64}},
        'approved_publication_intents':[{'batch_sha256':'f'*64,'canonical_document_id':item['canonical_document_id'],'operation':'repair',
            'expected_current_version':'VER_OLD','version_id':'VER_NEW','sha256':'a'*64,'approval_ref':'SYN_INTENT','reason':'Synthetic repair approved'}]}
    state={'batch_sha256':'f'*64,'department_key':'production','department_title':'合成部门','run_id':'SYN_RUN','items':[item]}
    monkeypatch.setitem(sys.modules,'hb_knowledge_app.hb_knowledge.shared_reference',SimpleNamespace(configuration=lambda:cfg))
    maintenance=importlib.import_module('hb_knowledge_app.hb_knowledge.maintenance')
    monkeypatch.setattr(maintenance,'publication_config',lambda *a:(cfg,state))
    admin=importlib.import_module('hb_knowledge_app.hb_knowledge.reference_admin')
    def backend(*a):
        if backend_fails:raise PublicationConflict('New physical source changed')
    monkeypatch.setattr(admin,'_verify_backend',backend)
    return admin,item,current,writes,commits,created,rolled,withdrawal


def test_actual_publisher_commits_new_version_without_restoring_bad_parent(monkeypatch):
    admin,item,current,writes,commits,created,rolled,withdrawal=publisher(monkeypatch)
    result=admin.publish(None,'repair','VER_OLD','Synthetic repair approved','SYN_INTENT',None,registered_batch_id='SYN_BATCH')
    assert result['published_documents']==1 and result['results'][0]['outcome']=='REPAIRED'
    assert len(writes)==1 and writes[0]['current_version']=='VER_NEW' and writes[0]['withdrawn']==0
    assert len(commits)==1 and commits[0]['current_version']=='VER_NEW' and not rolled
    receipts=[v for (table,name),v in created.items() if table=='HBOS Knowledge Publication']
    assert len(receipts)==1 and receipts[0]['operation']=='replace' and receipts[0]['outcome']=='REPAIRED'


def test_new_backend_or_withdrawal_mismatch_keeps_parent_withdrawn(monkeypatch):
    admin,item,current,writes,commits,created,rolled,withdrawal=publisher(monkeypatch,True)
    with pytest.raises(PublicationConflict):admin.publish(None,'repair','VER_OLD','Synthetic repair approved','SYN_INTENT',None,registered_batch_id='SYN_BATCH')
    assert current['withdrawn']==1 and current['current_version']=='VER_OLD' and not writes and not commits and rolled
    admin,item,current,writes,commits,created,rolled,withdrawal=publisher(monkeypatch)
    withdrawal['reason']='later privacy revocation'
    with pytest.raises(PublicationConflict):admin.publish(None,'repair','VER_OLD','Synthetic repair approved','SYN_INTENT',None,registered_batch_id='SYN_BATCH')
    assert current['withdrawn']==1 and not writes and not commits


def test_repair_retry_keeps_one_receipt_and_later_withdrawal_never_reactivates(monkeypatch):
    admin,item,current,writes,commits,created,rolled,withdrawal=publisher(monkeypatch)
    one=admin.publish(None,'repair','VER_OLD','Synthetic repair approved','SYN_INTENT',None,registered_batch_id='SYN_BATCH')
    two=admin.publish(None,'repair','VER_OLD','Synthetic repair approved','SYN_INTENT',None,registered_batch_id='SYN_BATCH')
    assert two['results'][0]['outcome']=='NOOP' and two['results'][0]['receipt_id']==one['results'][0]['receipt_id']
    assert len(writes)==1
    current['withdrawn']=1;current['ingestion_status']='retired'
    with pytest.raises(PublicationConflict):admin.publish(None,'repair','VER_OLD','Synthetic repair approved','SYN_INTENT',None,registered_batch_id='SYN_BATCH')
    assert len(writes)==1 and current['current_version']=='VER_NEW' and current['withdrawn']==1


def test_historical_department_alias_must_still_resolve_to_same_actual_space():
    parent,target=items();parent['department_key']='ASEPTIC_WORKSHOP'
    assert validate_technical_repair(target,parent,'VER_OLD')==target['technical_correction']


@pytest.mark.parametrize('fault',[None,'new_quality','old_quality','sharing','source','parent_batch'])
def test_registered_repair_requires_new_passed_and_exact_old_pending_quality(monkeypatch,fault):
    parent,target=items();proof=target['technical_correction'];parent_sha=proof['parent_batch_sha256']
    quality={'VER_NEW':{'status':'Passed','source_sha256':target['sha256'],'upload_sha256':target['upload_sha256']}}
    old_quality={'VER_OLD':{'status':'Pending','source_sha256':parent['sha256'],'version_id':'VER_OLD'}}
    if fault=='new_quality':quality['VER_NEW']['status']='Pending'
    if fault=='old_quality':old_quality['VER_OLD']['status']='Passed'
    if fault=='sharing':parent['internal_sharing_confirmed']=False
    if fault=='source':old_quality['VER_OLD']['source_sha256']='f'*64
    old_frozen={'batch_sha256':parent_sha if fault!='parent_batch' else '0'*64}
    state={'batch_sha256':'f'*64,'items':[target]};frozen={'department_key':'production'}
    maintenance=importlib.import_module('hb_knowledge_app.hb_knowledge.maintenance')
    monkeypatch.setattr(maintenance,'configuration',lambda:{})
    def row(batch,*a):
        if batch=='SYN_NEW':return {'quality_json':json.dumps(quality)},frozen,state
        assert batch=='IMP_'+parent_sha[:32]
        return {'quality_json':json.dumps(old_quality)},old_frozen,{'items':[parent]}
    monkeypatch.setattr(maintenance,'_row',row)
    if fault:
        from hb_knowledge_app.hb_knowledge.errors import KnowledgeError
        with pytest.raises((KnowledgeError,PublicationConflict)):
            maintenance.publication_config('SYN_NEW',[target['canonical_document_id']],'repair','VER_OLD','Synthetic repair','SYN_INTENT')
    else:
        cfg,_=maintenance.publication_config('SYN_NEW',[target['canonical_document_id']],'repair','VER_OLD','Synthetic repair','SYN_INTENT')
        assert cfg['approved_technical_repairs'][target['canonical_document_id']]['proof']==proof


def test_image_body_repair_requires_local_full_source_profile_and_same_original(monkeypatch):
 parent,target=items();port=sys.modules['knowledge_service.ingestion'];local=port.LOCAL_FULLTEXT_NEWLINE_PROFILE
 target['technical_correction']['reason_code']='MISSING_IMAGE_BODY_RECOVERY'
 # A new reason does not admit the old/native profile by itself.
 with pytest.raises(PublicationConflict):validate_technical_repair(target,parent,'VER_OLD')
 monkeypatch.setattr(port,'approved_parser_profile',lambda item:local)
 assert validate_technical_repair(target,parent,'VER_OLD')['parent_source_sha256']==parent['sha256']
 for mutation in ['source','authority','department','identity','reason']:
  trial=copy.deepcopy(target)
  if mutation=='source':trial['sha256']='f'*64
  if mutation=='authority':trial['authority_status']='CONTROLLED_APPROVED'
  if mutation=='department':trial['department_key']='safety'
  if mutation=='identity':trial['canonical_document_id']='OTHER'
  if mutation=='reason':trial['technical_correction']['reason_code']='UNBOUNDED_REPLACEMENT'
  with pytest.raises(PublicationConflict):validate_technical_repair(trial,parent,'VER_OLD')
