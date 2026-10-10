"""Native maintenance workflow; publication reuses the existing CAS publisher."""
import hashlib,json,os,secrets,time
from pathlib import Path
import frappe
from .errors import KnowledgeError
from .maintenance_access import require
from .maintenance_contract import DEPARTMENTS,MAX_FILE,admit_file,registered,normalized_department,initial_state
from .service_http import canonical
from .shared_reference import configuration
TABLE='HBOS Knowledge Import Batch'

def _json(row,key,default):
    try:return json.loads(row.get(key) or json.dumps(default))
    except (ValueError,TypeError):raise KnowledgeError('POLICY_UNAVAILABLE') from None

def _row(batch_id,lock=False):
    if not isinstance(batch_id,str) or not batch_id.startswith('IMP_') or len(batch_id)!=36:raise KnowledgeError('INVALID_REQUEST')
    rows=frappe.db.sql('SELECT * FROM `tabHBOS Knowledge Import Batch` WHERE name=%s'+(' FOR UPDATE' if lock else ''),(batch_id,),as_dict=True)
    if len(rows)!=1:raise KnowledgeError('INVALID_REQUEST')
    row=rows[0];frozen=_json(row,'frozen_json',{});state=_json(row,'state_json',{})
    registered(frozen,state)
    return row,frozen,state

def register_batch(frozen,state,label,creator):
    sha=registered(frozen,state);batch_id='IMP_'+sha[:32]
    if frappe.db.exists(TABLE,batch_id):
        _,old,_=_row(batch_id)
        if old!=frozen:raise KnowledgeError('INVALID_REQUEST')
        return batch_id
    frappe.get_doc({'doctype':TABLE,'batch_id':batch_id,'label':str(label)[:160],
        'department_key':frozen['department_key'],'creator_user':creator,
        'frozen_json':canonical(frozen),'state_json':canonical(state),
        'quality_json':'{}','job_json':'{}','status':'Imported'}).insert(ignore_permissions=True)
    return batch_id

def _registry():
    documents={}
    for row in frappe.get_all(TABLE,fields=['state_json'],limit_page_length=1000):
        for item in _json(row,'state_json',{}).get('items',[]):
            if item.get('disposition')=='SAME_CONTENT_SKIP':continue
            doc=item['canonical_document_id'];prior=documents.get(doc)
            current=frappe.db.get_value('HBOS Knowledge Document',doc,'current_version')
            if not prior or item['version_id']==current:documents[doc]={**item,'department_key':normalized_department(item['department_key'])}
    # Preserve duplicate identity for the original published corpus even when
    # its historical manifest predates registered import batches.
    current_rows=frappe.db.sql('SELECT d.name,d.current_version,d.source_hash,b.binding_json,b.space_id '
        'FROM `tabHBOS Knowledge Document` d JOIN `tabHBOS Knowledge Backend Binding` b '
        'ON b.canonical_document_id=d.name AND b.version_id=d.current_version WHERE b.enabled=1',as_dict=True)
    for item in current_rows:
        payload=json.loads(item['binding_json'])
        title=payload.get('title') or item['name']
        department=normalized_department(item['space_id'].removeprefix('DEPT_'))
        if department not in DEPARTMENTS:department=department.lower()
        if department in DEPARTMENTS and item['name'] not in documents:
            documents[item['name']]={'canonical_document_id':item['name'],'version_id':item['current_version'],
                'sha256':item['source_hash'],'department_key':department,'title':title}
    return {'documents':list(documents.values())}

def upload(department,label,sharing,replace_document=None,expected_version=None):
    require()
    if department not in DEPARTMENTS or sharing not in (True,1,'1','true'):raise KnowledgeError('INVALID_REQUEST')
    request=frappe.local.request
    if len(request.files)!=1 or 'file' not in request.files:raise KnowledgeError('INVALID_REQUEST')
    uploaded=request.files['file'];name=uploaded.filename;data=uploaded.stream.read(MAX_FILE+1)
    ext,sha=admit_file(name,data)
    cfg=configuration();base=Path(cfg['maintenance_upload_root']);base.mkdir(parents=True,exist_ok=True,mode=0o700)
    if base.is_symlink():raise KnowledgeError('POLICY_UNAVAILABLE')
    directory=base/secrets.token_hex(16);directory.mkdir(mode=0o2770);source=directory/name
    with source.open('xb') as file:file.write(data)
    source.chmod(0o640)
    from knowledge_service.ingestion import save,plan,approve
    registry=_registry();save(directory/'registry.json',registry)
    # Metadata lives outside source_root, so planning never picks up its own JSON.
    source_root=directory/'source';source_root.mkdir(mode=0o2770);source.rename(source_root/name)
    relation=None
    if replace_document:
        matching=[i for i in registry['documents'] if i['canonical_document_id']==replace_document and i['department_key']==department]
        if len(matching)!=1 or matching[0]['version_id']!=expected_version:raise KnowledgeError('INVALID_REQUEST')
        relation={name:{'canonical_document_id':replace_document,'expected_current_version':expected_version,'approval_ref':'NATIVE_UPLOAD:'+frappe.session.user}}
        save(directory/'relations.json',relation)
    approval='NATIVE_UPLOAD:'+frappe.session.user+':'+sha
    planned=plan(source_root,department,DEPARTMENTS[department],directory/'planned.json',approval,
        directory/'registry.json',directory/'relations.json' if relation else None)
    if any(i['disposition'] in {'CONFLICT','UPDATE_CANDIDATE'} for i in planned['items']):
        # An ambiguous relation cannot enqueue or publish. The maintainer selects
        # the logical current document in the UI and uploads an explicit revision.
        raise KnowledgeError('IDENTITY_CONFLICT')
    frozen=approve(directory/'planned.json',directory/'frozen.json',approval)
    state=initial_state(frozen)
    batch_id=register_batch(frozen,state,label or name,frappe.session.user)
    frappe.db.commit()
    return {'batch_id':batch_id,'sha256':sha,'relationship':frozen['items'][0]['disposition'],'status':'待解析' if frozen['items'][0]['disposition']!='SAME_CONTENT_SKIP' else '重复内容，保留原版本'}

def _projection(row,frozen,state,page,page_size):
    quality=_json(row,'quality_json',{});items=[]
    for item in state['items'][(page-1)*page_size:page*page_size]:
        doc=item['canonical_document_id'];published=frappe.db.get_value('HBOS Knowledge Document',doc,['current_version','withdrawn','ingestion_status'],as_dict=True)
        review=quality.get(item['version_id'],{})
        items.append({'document_id':doc,'version_id':item['version_id'],'title':item['title'][:240],
            'filename':Path(item['relative_path']).name,'sha256':item['sha256'],
            'relationship':item['disposition'],'expected_version':item.get('expected_current_version'),
            'parse_status':item['status'],'progress':max(0,min(1,float(item.get('progress') or 0))),
            'chunk_count':int(item.get('chunk_count') or 0),'quality_status':review.get('status','Pending'),
            'quality_note':review.get('note',''),'current_version':published.get('current_version') if published else None,
            'publication_status':'Withdrawn' if published and published['withdrawn'] else ('Published' if published and published['current_version']==item['version_id'] and published['ingestion_status']=='published' else 'Unpublished')})
    return {'batch_id':row['name'],'label':row['label'],'department':row['department_key'],'status':row['status'],
        'last_error':row.get('last_error'),'items':items,'total':len(state['items']),'page':page,'page_size':page_size,
        'counts':{'parsed':sum(i['status']=='parsed/indexed' for i in state['items']),
            'failed':sum(i['status']=='parse_failed' for i in state['items']),
            'quality_passed':sum(v.get('status')=='Passed' for v in quality.values())}}

def dashboard(batch_id=None,page=1,page_size=12):
    require()
    from .reference_admin import _page_number
    page=_page_number(page,100000);page_size=_page_number(page_size,50)
    batches=frappe.get_all(TABLE,fields=['name','label','department_key','status','modified'],order_by='modified desc',limit_page_length=100)
    selected=None
    if batch_id:
        row,frozen,state=_row(batch_id);selected=_projection(row,frozen,state,page,page_size)
    from .activity import feedback_queue
    from .runtime import load_runtime
    runtime=load_runtime()
    snapshot=runtime.provider._current(runtime.actor(),runtime.client)
    published={b.canonical_document_id:{'document_id':b.canonical_document_id,'version_id':b.version_id,
        'current_version':b.version_id,'title':b.title or b.canonical_document_id,
        'department':normalized_department(b.space_id.removeprefix('DEPT_')).lower()}
        for b in snapshot.bindings if b.dataset_id in snapshot.allowed_datasets}
    if len(published)>1000:raise KnowledgeError('POLICY_UNAVAILABLE')
    availability=__import__(__package__+'.api',fromlist=['_availability'])._availability(runtime)
    availability['can_parse']=bool(availability['configured'] and not availability['blocked'])
    return {'departments':[{'key':k,'title':v} for k,v in DEPARTMENTS.items()],
            'batches':batches,'selected':selected,'feedback':feedback_queue(load_runtime()),
            'published_documents':sorted(published.values(),key=lambda i:i['title']),
            'import_availability':availability}

def queue(batch_id,document_ids,operation='parse'):
    require();row,frozen,state=_row(batch_id,True)
    if operation not in ('parse','retry','resume','continue') or not isinstance(document_ids,list) or not 1<=len(document_ids)<=4 or len(set(document_ids))!=len(document_ids):raise KnowledgeError('INVALID_REQUEST')
    items=[i for i in state['items'] if i['canonical_document_id'] in document_ids]
    allowed={'planned','uploaded'} if operation=='parse' else ({'parse_queued'} if operation in ('resume','continue') else {'parse_failed'})
    if len(items)!=len(document_ids) or any(i['status'] not in allowed or i['disposition']=='SAME_CONTENT_SKIP' for i in items):raise KnowledgeError('INVALID_REQUEST')
    from .api import _availability
    from .runtime import load_runtime
    if _availability(load_runtime()).get('blocked'):raise KnowledgeError('UPSTREAM_UNAVAILABLE')
    current=_json(row,'job_json',{})
    if current.get('status') in ('Queued','Running'):raise KnowledgeError('IMPORT_BUSY')
    job={'id':secrets.token_hex(16),'status':'Queued','operation':operation,'document_ids':document_ids,
         'requested_by':frappe.session.user,'requested_at':time.time()}
    frappe.db.set_value(TABLE,batch_id,{'job_json':canonical(job),'status':'Queued','last_error':None})
    frappe.db.commit();return {'job_id':job['id'],'status':'Queued'}

def preview(batch_id,document_id,page=1):
    require();row,frozen,state=_row(batch_id)
    items=[i for i in state['items'] if i['canonical_document_id']==document_id and i['status']=='parsed/indexed']
    if len(items)!=1:raise KnowledgeError('INVALID_REQUEST')
    item=items[0]
    from .reference_admin import _verify_backend,_page_number
    page=_page_number(page,max(1,(int(item.get('chunk_count',0))+4)//5))
    cfg=configuration();_verify_backend(cfg,item)
    auth=json.loads(Path(cfg['publication_ragflow_auth_file']).read_text())
    import requests
    with requests.Session() as session:
        session.trust_env=False;session.headers['Authorization']='Bearer '+auth['token']
        r=session.get(auth['base_url'].rstrip('/')+'/api/v1/datasets/'+item['dataset_id']+'/documents/'+item['ragflow_document_id']+'/chunks',params={'page':page,'page_size':5},timeout=(3,30),allow_redirects=False);r.raise_for_status();value=r.json()
    if value.get('code')!=0:raise KnowledgeError('SERVICE_ERROR')
    from .public_strings import safe_string
    chunks=value.get('data',{}).get('chunks',[])
    from knowledge_service.hbos_gateway.native_text import native_text
    def inert_preview(chunk):
        content=chunk.get('content','')
        if not isinstance(content,str) or len(content)>131072:raise KnowledgeError('UPSTREAM_INVALID_RESULT')
        return safe_string(native_text(content)[:800],800)
    return {'document_id':document_id,'version_id':item['version_id'],'title':item['title'],
        'fragments':[{'text':inert_preview(c),'location':'解析片段；页码未核验'} for c in chunks[:5]],
        'page':page,'page_size':5,'has_more':page*5<int(item.get('chunk_count',0)),
        'chunk_count':item.get('chunk_count',0),'source_sha256':item['sha256']}

def review(batch_id,document_id,checks,note):
    require();row,frozen,state=_row(batch_id,True)
    if not isinstance(checks,list) or set(checks)!={'text','numbers','tables','identity'} or not isinstance(note,str) or not 3<=len(note.strip())<=500:raise KnowledgeError('INVALID_REQUEST')
    from .public_strings import safe_string
    note=safe_string(note.strip(),500)
    items=[i for i in state['items'] if i['canonical_document_id']==document_id and i['status']=='parsed/indexed']
    if len(items)!=1:raise KnowledgeError('INVALID_REQUEST')
    item=items[0]
    from .reference_admin import _verify_backend
    _verify_backend(configuration(),item)
    quality=_json(row,'quality_json',{});record={'status':'Passed','note':note.strip(),'checks':sorted(checks),
        'source_sha256':item['sha256'],'upload_sha256':item['upload_sha256'],'version_id':item['version_id'],
        'reviewed_by':frappe.session.user,'reviewed_at':time.time()}
    record['evidence_sha256']=hashlib.sha256(canonical(record).encode()).hexdigest()
    quality[item['version_id']]=record
    frappe.db.set_value(TABLE,batch_id,'quality_json',canonical(quality));frappe.db.commit()
    return {'status':'Passed','evidence_sha256':record['evidence_sha256']}

def publication_config(batch_id,selected,operation,expected,reason,approval):
    # Called only after the public native handler checked the maintenance role,
    # or by a signed registered coordinator. The frozen record is authoritative.
    row,frozen,state=_row(batch_id,True);quality=_json(row,'quality_json',{})
    from .publication import select_publication_items,FROZEN_PUBLICATION_FIELDS
    items=select_publication_items(state,selected)
    for item in items:
        q=quality.get(item['version_id'],{})
        if q.get('status')!='Passed' or q.get('source_sha256')!=item['sha256'] or q.get('upload_sha256')!=item['upload_sha256']:raise KnowledgeError('QUALITY_REQUIRED')
    cfg=dict(configuration());sha=state['batch_sha256'];selection=hashlib.sha256(canonical(sorted(selected)).encode()).hexdigest()
    cfg['approved_batch_sha256s']=[sha];cfg['approved_space_ids']=[cfg.get('department_space_map',{}).get(frozen['department_key'],'DEPT_'+frozen['department_key'].upper())]
    cfg['approved_dataset_ids']=sorted({i['dataset_id'] for i in items});cfg['approved_document_ids']=selected
    cfg['approved_publication_items']={sha:{i['canonical_document_id']:{k:i.get(k) for k in FROZEN_PUBLICATION_FIELDS} for i in items}}
    cfg['approved_publication_subsets']={selection:{'batch_sha256':sha,'canonical_document_ids':sorted(selected),'approval_ref':approval,
        'quality_evidence_sha256':hashlib.sha256(canonical(quality).encode()).hexdigest()}}
    cfg['approved_publication_intents']=[{'batch_sha256':sha,'canonical_document_id':i['canonical_document_id'],'operation':operation,
        'expected_current_version':expected,'version_id':i['version_id'],'sha256':i['sha256'],'approval_ref':approval,'reason':reason} for i in items]
    return cfg,state

def publish(batch_id,document_ids,operation='publish',expected_version=None,reason=None):
    require()
    if operation not in ('publish','replace','restore') or not isinstance(document_ids,list):raise KnowledgeError('INVALID_REQUEST')
    if operation!='publish' and (len(document_ids)!=1 or not isinstance(reason,str) or not 3<=len(reason.strip())<=500):raise KnowledgeError('INVALID_REQUEST')
    from .reference_admin import publish as existing
    # Same authenticated operation retains one durable intent and receipt. Older
    # random references are reused without rewriting their immutable audit rows.
    actor=frappe.session.user
    approval='NATIVE_MAINTENANCE:'+hashlib.sha256(canonical(
        [actor,batch_id,sorted(document_ids),operation,expected_version,reason]).encode()).hexdigest()
    if operation!='publish' and len(document_ids)==1:
        _,_,state=_row(batch_id)
        targets=[i['version_id'] for i in state['items'] if i['canonical_document_id']==document_ids[0]
                 and i.get('disposition')!='ALIAS']
        if len(targets)!=1:raise KnowledgeError('INVALID_REQUEST')
        committed=frappe.get_all('HBOS Knowledge Publication',filters={
            'canonical_document_id':document_ids[0],'target_version':targets[0],
            'batch_sha256':state['batch_sha256'],'operation':operation,
            'expected_current_version':expected_version,'reason':reason},
            fields=['approval_ref'],order_by='creation asc',limit_page_length=0)
        owned=[r['approval_ref'] for r in committed if r['approval_ref']==approval
               or (r.get('approval_ref') or '').startswith('NATIVE_MAINTENANCE:'+actor+':')]
        if owned:approval=owned[0]
    return existing(None,operation,expected_version,reason,approval,document_ids,registered_batch_id=batch_id)

def withdraw(batch_id,document_id,expected_version,reason):
    require();row,frozen,state=_row(batch_id,True)
    if not isinstance(reason,str) or not 3<=len(reason.strip())<=500:raise KnowledgeError('INVALID_REQUEST')
    items=[i for i in state['items'] if i['canonical_document_id']==document_id and i['version_id']==expected_version]
    if len(items)!=1:raise KnowledgeError('INVALID_REQUEST')
    rows=frappe.db.sql('SELECT current_version,withdrawn,source_hash FROM `tabHBOS Knowledge Document` WHERE name=%s FOR UPDATE',(document_id,),as_dict=True)
    if len(rows)!=1 or rows[0]['current_version']!=expected_version:raise KnowledgeError('IDENTITY_CONFLICT')
    if rows[0]['withdrawn']:
        prior=frappe.get_all('HBOS Knowledge Publication',filters={'canonical_document_id':document_id,
            'target_version':expected_version,'operation':'withdraw'},fields=['receipt_id'],
            order_by='creation desc',limit_page_length=1)
        if not prior:raise KnowledgeError('IDENTITY_CONFLICT')
        return {'outcome':'NOOP','receipt_id':prior[0]['receipt_id']}
    receipt='PUB_'+hashlib.sha256(canonical([batch_id,document_id,expected_version,'withdraw',reason,frappe.session.user]).encode()).hexdigest()
    frappe.db.set_value('HBOS Knowledge Document',document_id,{'withdrawn':1,'ingestion_status':'retired'})
    frappe.get_doc({'doctype':'HBOS Knowledge Publication','receipt_id':receipt,'canonical_document_id':document_id,
        'target_version':expected_version,'batch_sha256':state['batch_sha256'],'operation':'withdraw',
        'expected_current_version':expected_version,'source_hash':rows[0]['source_hash'],'reason':reason,
        'approval_ref':'NATIVE_WITHDRAW:'+frappe.session.user,'outcome':'WITHDRAWN'}).insert(ignore_permissions=True)
    frappe.db.commit();return {'outcome':'WITHDRAWN','receipt_id':receipt}
