"""Main-locked native jobs admitted by the existing plan/submit controller.

This is a new input variant, not another queue. The employee cannot supply a
parser, model, physical destination or prepared file path. Those come from the
private hash-locked execution manifest approved by Main.
"""
from __future__ import annotations
import copy,hashlib,json,re
from pathlib import Path
from .errors import KnowledgeError
from .service_http import canonical
from .maintenance_contract import DEPARTMENTS

SCOPE='EXACT_SHA_MAIN_LOCKED_NATIVE_V1'

def require(value,code='INVALID_REQUEST'):
    if not value:raise KnowledgeError(code)

def _file_sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for part in iter(lambda:f.read(1024*1024),b''):h.update(part)
    return h.hexdigest()

def _locked(cfg):
    require(cfg.get('native_import_enabled') is True,'POLICY_UNAVAILABLE')
    p=Path(cfg.get('native_execution_manifest_file',''))
    require(p.is_absolute() and p.is_file() and not p.is_symlink(),'POLICY_UNAVAILABLE')
    require(not p.stat().st_mode&0o022,'POLICY_UNAVAILABLE')
    require(_file_sha(p)==cfg.get('native_execution_manifest_sha256'),'POLICY_UNAVAILABLE')
    data=json.loads(p.read_text());require(data.get('schema')=='hbos.native-execution-manifest.v1','POLICY_UNAVAILABLE')
    return data

def normalize(raw,cfg):
    from .maintenance_batch import _approved_roots,_safe_relative_path,_bounded_text
    from knowledge_service.native_job_contract import validate_native_item
    require(set(raw)<={'schema_version','label','sharing_confirmed','job_manifest_sha256','items'})
    require(raw.get('schema_version')==3 and type(raw['schema_version']) is int and raw.get('sharing_confirmed') is True)
    locked=_locked(cfg);require(raw.get('job_manifest_sha256')==cfg['native_execution_manifest_sha256'])
    ids=raw.get('items');require(isinstance(ids,list) and 1<=len(ids)<=64)
    require(all(isinstance(i,dict) and set(i)=={'job_id'} and isinstance(i['job_id'],str) for i in ids))
    jobids=[x['job_id'] for x in ids];require(len(set(jobids))==len(jobids))
    jobs={j['job_id']:j for j in locked['jobs']};require(len(jobs)==len(locked['jobs']) and set(jobids)<=set(jobs))
    roots=_approved_roots(cfg);runtime=[];total=0
    for index,jid in enumerate(jobids):
        job=copy.deepcopy(jobs[jid]);item=job['item'];validate_native_item(item)
        root=Path(job['source_root']);require(root in roots,'SOURCE_CHANGED')
        relative=_safe_relative_path(item['relative_path']);p=root/relative
        require(not p.is_symlink() and p.resolve(strict=True).is_relative_to(root),'SOURCE_CHANGED')
        require(not any(parent.is_symlink() for parent in p.parents if parent!=root.parent),'SOURCE_CHANGED')
        require(p.stat().st_size==item['size_bytes'] and _file_sha(p)==item['sha256'],'SOURCE_CHANGED')
        require(0<item['size_bytes']<=job.get('approved_max_source_bytes',64*1024*1024)<=600*1024*1024)
        require(item['department_key'] in DEPARTMENTS and re.fullmatch('[a-f0-9]{32}',job['candidate_dataset_id']))
        total+=item['size_bytes'];require(total<=4*600*1024*1024,'BATCH_SOURCE_SIZE_LIMIT_EXCEEDED')
        # Binding revision differentiates B/C while business version is retained.
        runtime.append({'index':index,'source_sha256':item['sha256'],'source_ref':'NATIVE:'+jid,
            'source_path':str(p),'source_root':str(root),'source_size':item['size_bytes'],
            'relative_path':relative,'department':item['department_key'],
            'text_sha256':None,'version_id':item['version_id'],'pages':[],'page_methods':[],
            'page_checks':{},'hint':'NATIVE','replace':None,'repair':None,'native_job':job})
    normalized={'schema_version':3,'sharing_confirmed':True,'label':raw.get('label'),
        'job_manifest_sha256':cfg['native_execution_manifest_sha256'],'items':[{'job_id':i} for i in jobids]}
    label=raw.get('label')
    if label is not None:label=_bounded_text(label,160)
    return {'plan_sha256':hashlib.sha256(canonical(normalized).encode()).hexdigest(),'normalized':normalized,
        'items':runtime,'label':label,'departments':sorted({i['department'] for i in runtime})}

def classify(item,index):
    from .maintenance_batch import _result,_publication
    job=item['native_job'];source=job['item'];doc=source['canonical_document_id']
    import frappe
    current=frappe.db.get_value('HBOS Knowledge Document',doc,['current_version','withdrawn','ingestion_status','source_hash'],as_dict=True)
    if source['disposition']=='TECHNICAL_REINDEX':
        valid=(current and not current.get('withdrawn') and current.get('ingestion_status')=='published'
               and current.get('current_version')==source['version_id']
               and current.get('source_hash')==source['sha256'])
        if not valid:return _result(item,'ANOMALY',submittable=False,reason='CURRENT_VERSION_CHANGED',page_methods=[])
    else:
        if current:return _result(item,'ANOMALY',submittable=False,reason='RELATION_NOT_TRACEABLE',page_methods=[])
    # This destination is isolated and Main-locked; never use the old asset's dataset.
    candidate={**copy.deepcopy(source),'document_id':doc,'dataset_id':job['candidate_dataset_id']}
    return _result(item,'NEW',submittable=True,page_methods=[],document_id=doc,
                   version_id=source['version_id'],expected_current_version=source.get('expected_current_version'),
                   candidate=candidate,detail='已冻结原件与原生模板；技术解析不改变业务版本，候选处理后另行验收。')

def frozen_item(item,classification,approval_ref):
    from knowledge_service.native_job_contract import validate_native_item
    out=copy.deepcopy(item['native_job']['item']);out.update(approval_ref=approval_ref,
        dataset_id=item['native_job']['candidate_dataset_id'],ragflow_document_id=None,status='planned')
    validate_native_item(out)
    return out
