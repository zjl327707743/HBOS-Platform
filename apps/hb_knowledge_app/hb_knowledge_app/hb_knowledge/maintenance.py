"""Native maintenance workflow; publication reuses the existing CAS publisher."""
import copy,hashlib,json,os,re,secrets,time
from pathlib import Path
import frappe
from .errors import KnowledgeError
from .maintenance_access import require
from .maintenance_contract import DEPARTMENTS,MAX_FILE,admit_file,registered,normalized_department,initial_state,configured_max_source_bytes
from .service_http import canonical
from .shared_reference import configuration
TABLE='HBOS Knowledge Import Batch'
SOURCE_DIRECTORIES={'production':('生产部门','无菌车间'),'hr':('人事部门',),'safety':('安全部门',),
                    'engineering':('设备部建模图',),'public_law':('法规文档',)}


def managed_relative_path(relative, department):
    from .source_directory import ALLOWED_ROOTS
    path = Path(relative)
    roots = SOURCE_DIRECTORIES[department]
    if len(path.parts)>1 and path.parts[0] in ALLOWED_ROOTS:
        if path.parts[0] not in roots:
            raise KnowledgeError('SCOPE_REJECTED')
        return path
    return Path(roots[0])/path

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

def upload(department,label,sharing,replace_document=None,expected_version=None,parse_template='auto',
           relative_path=None,auto_process=False,space_id=None):
    require()
    if department not in DEPARTMENTS or sharing not in (True,1,'1','true'):raise KnowledgeError('INVALID_REQUEST')
    request=frappe.local.request
    if len(request.files)!=1 or 'file' not in request.files:raise KnowledgeError('INVALID_REQUEST')
    cfg=configuration();limit=configured_max_source_bytes(cfg)
    uploaded=request.files['file'];name=uploaded.filename
    if auto_process not in (False,True,0,1,'0','1','true','false'):
        raise KnowledgeError('INVALID_REQUEST')
    auto_process=auto_process in (True,1,'1','true')
    if auto_process and cfg.get('maintenance_managed_policy') is None:
        raise KnowledgeError('POLICY_UNAVAILABLE')
    if relative_path is not None:
        from .maintenance_batch import _safe_relative_path
        relative_path=_safe_relative_path(relative_path)
        if (Path(relative_path).name!=name or len(Path(relative_path).parts)>29):
            raise KnowledgeError('INVALID_REQUEST')
    # Read one byte past the configured limit so oversized input fails on the
    # source-size code instead of being silently truncated. The web server's own
    # request-body limit is a separate deployment decision.
    data=uploaded.stream.read(limit+1)
    ext,sha=admit_file(name,data,max_bytes=limit)
    base=Path(cfg['maintenance_upload_root']);base.mkdir(parents=True,exist_ok=True,mode=0o700)
    if base.is_symlink():raise KnowledgeError('POLICY_UNAVAILABLE')
    directory=base/secrets.token_hex(16);directory.mkdir(mode=0o2770);source=directory/name
    with source.open('xb') as file:file.write(data)
    source.chmod(0o640)
    from knowledge_service.ingestion import save,plan,approve
    registry=_registry();save(directory/'registry.json',registry)
    prior=None
    if replace_document:
        matching=[i for i in registry['documents'] if i['canonical_document_id']==replace_document and i['department_key']==department]
        current=frappe.db.get_value('HBOS Knowledge Document',replace_document,
                                    ['current_version','withdrawn','source_hash'],as_dict=True)
        if (len(matching)!=1 or matching[0]['version_id']!=expected_version or not current
                or current.get('withdrawn') or current.get('current_version')!=expected_version
                or current.get('source_hash')!=matching[0]['sha256']):
            raise KnowledgeError('SOURCE_VERSION_STALE')
        prior=matching[0]
        if prior.get('relative_path') and relative_path is None:
            relative_path=(Path(prior['relative_path']).parent/name).as_posix()
        if prior.get('space_id'):
            if space_id is not None and space_id!=prior['space_id']:
                raise KnowledgeError('SCOPE_REJECTED')
            space_id=prior['space_id']
    # Metadata lives outside source_root, so planning never picks up its own JSON.
    source_root=directory/'source';source_root.mkdir(mode=0o2770)
    # Managed uploads carry their selected directory in the frozen source path.
    # The UUID storage directory remains private and is never a catalog folder.
    selected=Path(relative_path or name)
    relative=managed_relative_path(selected,department) if cfg.get('maintenance_source_registry_enabled') is True else selected
    target=source_root/relative
    if target.parent!=source_root:target.parent.mkdir(mode=0o2770,parents=True)
    source.rename(target)
    relation=None
    if prior is not None:
        relation={relative.as_posix():{'canonical_document_id':replace_document,'expected_current_version':expected_version,'approval_ref':'NATIVE_UPLOAD:'+frappe.session.user}}
        save(directory/'relations.json',relation)
    approval='NATIVE_UPLOAD:'+frappe.session.user+':'+sha
    planned=plan(source_root,department,DEPARTMENTS[department],directory/'planned.json',approval,
        directory/'registry.json',directory/'relations.json' if relation else None,retain_unreadable_source=auto_process)
    if any(i['disposition'] in {'CONFLICT','UPDATE_CANDIDATE'} for i in planned['items']):
        # An ambiguous relation cannot enqueue or publish. The maintainer selects
        # the logical current document in the UI and uploads an explicit revision.
        raise KnowledgeError('IDENTITY_CONFLICT')
    from .maintenance_native_upload import apply_profile
    apply_profile(planned,cfg,parse_template)
    if space_id is not None:
        from .maintenance_spaces import assign_space
        assign_space(planned,cfg,space_id,department)
    save(directory/'planned.json',planned)
    frozen=approve(directory/'planned.json',directory/'frozen.json',approval)
    if cfg.get('maintenance_source_registry_enabled') is True:
        from .managed_source_registry import register
        try:register(cfg,frozen)
        except (ValueError,OSError):raise KnowledgeError('POLICY_UNAVAILABLE') from None
    state=initial_state(frozen)
    batch_id=register_batch(frozen,state,label or name,frappe.session.user)
    duplicate=frozen['items'][0]['disposition']=='SAME_CONTENT_SKIP'
    if auto_process and not duplicate:
        frappe.db.set_value(TABLE,batch_id,'job_json',canonical({'managed_intake':True,
            'requested_by':frappe.session.user,'requested_at':time.time(),'status':'Imported'}))
    frappe.db.commit()
    queued=None
    queue_error=None
    if auto_process and not duplicate:
        if frozen['items'][0].get('native_profile'):
            try:queued=queue(batch_id,[frozen['items'][0]['canonical_document_id']])
            except KnowledgeError as error:
                frappe.db.rollback()
                queue_error=error.code
                frappe.db.set_value(TABLE,batch_id,{'last_error':queue_error})
                frappe.db.commit()
        else:
            # Unsupported conversions stay visible; they cannot hold up native
            # ordinary jobs or silently fall through to another parser/model.
            queue_error=frozen['items'][0].get('source_inspection_error') or 'SOURCE_CONVERSION_REQUIRED'
            frappe.db.set_value(TABLE,batch_id,{'last_error':queue_error})
            frappe.db.commit()
    return {'batch_id':batch_id,'sha256':sha,'relationship':frozen['items'][0]['disposition'],
            'status':'重复内容，保留原版本' if duplicate else 'Queued' if queued else '待解析',
            'job_id':queued['job_id'] if queued else None,'queue_error':queue_error}

def is_published_target(item,current):
    if not (current and not current.get('withdrawn') and current.get('ingestion_status')=='published'
            and current.get('current_version')==item['version_id']):return False
    if not item.get('native_profile'):return True
    return bool(frappe.db.exists('HBOS Knowledge Backend Binding',{
        'canonical_document_id':item['canonical_document_id'],'version_id':item['version_id'],
        'dataset_id':item['dataset_id'],'document_id':item.get('ragflow_document_id'),
        'binding_revision':item['binding_revision'],'enabled':1}))


def _projection(row,frozen,state,page,page_size,locate=None):
    from .publication import UNRECORDED_ACTIVATION, latest_lifecycle_receipt
    quality=_json(row,'quality_json',{});items=[]
    window=state['items']
    if locate:
        # A detail request names one logical document. Locating it here keeps the
        # page it happens to sit on, so the caller learns the page instead of
        # walking every page of every batch through the whole dashboard.
        index=next((n for n,item in enumerate(window)
                    if item['canonical_document_id']==locate
                    and item['disposition']!='SAME_CONTENT_SKIP'),None)
        if index is not None:
            page=index//page_size+1
    for item in window[(page-1)*page_size:page*page_size]:
        doc=item['canonical_document_id'];published=frappe.db.get_value('HBOS Knowledge Document',doc,['current_version','withdrawn','ingestion_status'],as_dict=True)
        review=quality.get(item['version_id'],{})
        from .maintenance_managed import public_template
        publication_status='Withdrawn' if published and published['withdrawn'] else ('Published' if is_published_target(item,published) else 'Unpublished')
        lifecycle_receipt=None
        if publication_status in ('Published','Withdrawn') and published['current_version']==item['version_id']:
            withdrawn=publication_status=='Withdrawn'
            lifecycle_receipt=latest_lifecycle_receipt(doc,item['version_id'],withdrawn=withdrawn)
            if not withdrawn and lifecycle_receipt is None:lifecycle_receipt=UNRECORDED_ACTIVATION
        items.append({'document_id':doc,'version_id':item['version_id'],'title':item['title'][:240],
            'filename':Path(item['relative_path']).name,'sha256':item['sha256'],
            'relationship':item['disposition'],'expected_version':item.get('expected_current_version'),
            'parse_status':'original_stored' if item.get('original_asset_only') else item['status'],
            'progress':max(0,min(1,float(item.get('progress') or 0))),
            'chunk_count':int(item.get('chunk_count') or 0),'quality_status':review.get('status','Pending'),
            'shared_approved':bool(item.get('internal_sharing_confirmed') and item.get('owner_inclusion_confirmed')),
            'quality_note':review.get('note',''),'current_version':published.get('current_version') if published else None,
            'retrieval_verified':review.get('retrieval_verified'),
            'effective_template':public_template(item),
            'automatic_quality':item.get('automatic_quality'),
            'publication_status':publication_status,'lifecycle_receipt_id':lifecycle_receipt})
    return {'batch_id':row['name'],'label':row['label'],'department':row['department_key'],'status':row['status'],
        'last_error':row.get('last_error'),'items':items,'total':len(state['items']),'page':page,'page_size':page_size,
        'counts':{'parsed':sum(i['status']=='parsed/indexed' for i in state['items']),
            'failed':sum(i['status']=='parse_failed' for i in state['items']),
            'quality_passed':sum(v.get('status')=='Passed' for v in quality.values())}}

# Server-side maintenance lookup bounds. The dashboard must stay a bounded
# projection for a corpus far larger than one page: search/pagination/locate are
# computed over the already-loaded published snapshot or a bounded batch scan,
# never by walking the whole corpus from the browser or by unbounded DB scans.
PUBLISHED_LIMIT=1000
PUBLISHED_PAGE_SIZE=50
MAX_PUBLISHED_PAGE_SIZE=50
BATCH_PAGE_SIZE=100
MAX_BATCH_PAGE_SIZE=100
BATCH_SCAN_MAX=1000
_BATCH_QUERY_FIELDS=('name','label','department_key')
_DOCUMENT_ID=re.compile(r'(?:DOC_[A-Za-z0-9_-]{1,96}|N1DOC-[0-9a-f]{24})')

def _lookup_query(value):
    """Optional bounded free-text filter; malformed input is INVALID_REQUEST."""
    if value is None:return None
    from .public_strings import safe_string
    if not isinstance(value,str):raise KnowledgeError('INVALID_REQUEST')
    try:safe_string(value,120)
    except KnowledgeError:raise KnowledgeError('INVALID_REQUEST') from None
    value=value.strip()
    return value or None

def _lookup_document_id(value):
    if value is None:return None
    if not isinstance(value,str) or not _DOCUMENT_ID.fullmatch(value):
        raise KnowledgeError('INVALID_REQUEST')
    return value

def _published_projection(published,*,query=None,document_id=None,page=1,page_size=None,limit=PUBLISHED_LIMIT):
    values=sorted(published.values(),key=lambda i:i['title'])
    total=len(values)
    filtered=values
    if document_id is not None:
        filtered=[item for item in filtered if item['document_id']==document_id]
    elif query is not None:
        needle=query.casefold()
        filtered=[item for item in filtered
                  if needle in (item.get('title') or '').casefold()
                  or needle in (item.get('document_number') or '').casefold()
                  or needle in (item.get('document_id') or '').casefold()
                  or needle in (item.get('department') or '').casefold()]
    matched=len(filtered)
    paging=document_id is not None or query is not None or page!=1 or page_size is not None
    size=page_size if page_size is not None else (PUBLISHED_PAGE_SIZE if paging else limit)
    if not paging:
        start=0;documents=filtered[:limit];size=limit
    else:
        start=(page-1)*size;documents=filtered[start:start+size]
    return {'documents':documents,'total':total,'matched':matched,'page':page,'page_size':size,
            'has_more':start+len(documents)<matched,'query':query,'document_id':document_id,
            'lookup_state':None if document_id is None else ('FOUND' if matched else 'NOT_FOUND')}

def _batch_rows(fields,*,limit=None,start=0):
    kwargs={'fields':fields,'order_by':'modified desc'}
    if limit is not None:kwargs['limit_page_length']=limit
    if start:kwargs['limit_start']=start
    return frappe.get_all(TABLE,**kwargs)

def _batch_projection(*,query=None,document_id=None,page=1,page_size=BATCH_PAGE_SIZE,detail_page_size=12):
    total=frappe.db.count(TABLE)
    scan_truncated=total>BATCH_SCAN_MAX
    if document_id is not None or query is not None:
        rows=_batch_rows(['name','label','department_key','status','modified','state_json'],
                         limit=BATCH_SCAN_MAX)
        matches=[]
        for row in rows:
            if document_id is not None:
                try:state=json.loads(row.get('state_json') or '{}')
                except (ValueError,TypeError):continue
                found=None
                for index,item in enumerate(state.get('items') or []):
                    if (item.get('canonical_document_id')==document_id
                            and item.get('disposition') not in ('SAME_CONTENT_SKIP','ALIAS')):
                        found=index;break
                if found is None:continue
                entry={key:row.get(key) for key in ('name','label','department_key','status','modified')}
                entry['document_page']=found//detail_page_size+1
                matches.append(entry)
            else:
                needle=query.casefold()
                if any(needle in (row.get(key) or '').casefold() for key in _BATCH_QUERY_FIELDS):
                    matches.append({key:row.get(key) for key in ('name','label','department_key','status','modified')})
        matched=len(matches)
        start=(page-1)*page_size
        return {'batches':matches[start:start+page_size],'total':total,'matched':matched,
                'page':page,'page_size':page_size,'has_more':start+page_size<matched,
                'query':query,'document_id':document_id,
                'lookup_state':None if document_id is None else ('FOUND' if matched else 'NOT_FOUND'),
                'scan_truncated':scan_truncated}
    start=(page-1)*page_size
    rows=_batch_rows(['name','label','department_key','status','modified'],
                     limit=page_size,start=start)
    return {'batches':rows,'total':total,'matched':total,'page':page,'page_size':page_size,
            'has_more':start+len(rows)<total,'query':None,'document_id':None,
            'lookup_state':None,'scan_truncated':scan_truncated}

def dashboard(batch_id=None,page=1,page_size=12,locate=None,*,published_query=None,
              published_document_id=None,published_page=1,published_page_size=None,
              batch_query=None,batch_page=1,batch_page_size=None,batch_document_id=None):
    require()
    from .reference_admin import _page_number
    page=_page_number(page,100000);page_size=_page_number(page_size,50)
    published_page=_page_number(published_page,100000)
    published_page_size=(_page_number(published_page_size,MAX_PUBLISHED_PAGE_SIZE)
                         if published_page_size is not None else None)
    batch_page=_page_number(batch_page,100000)
    batch_page_size=_page_number(batch_page_size,MAX_BATCH_PAGE_SIZE) if batch_page_size is not None else BATCH_PAGE_SIZE
    published_query=_lookup_query(published_query)
    published_document_id=_lookup_document_id(published_document_id)
    batch_query=_lookup_query(batch_query)
    batch_document_id=_lookup_document_id(batch_document_id)
    if published_query is not None and published_document_id is not None:
        raise KnowledgeError('INVALID_REQUEST')
    if batch_query is not None and batch_document_id is not None:
        raise KnowledgeError('INVALID_REQUEST')
    if locate is not None:
        from .public_strings import safe_string
        locate=safe_string(locate,120)
    batch_view=_batch_projection(query=batch_query,document_id=batch_document_id,
                                 page=batch_page,page_size=batch_page_size,detail_page_size=page_size)
    selected=None
    if batch_id:
        row,frozen,state=_row(batch_id);selected=_projection(row,frozen,state,page,page_size,locate)
    from .activity import feedback_queue
    from .runtime import load_runtime
    runtime=load_runtime()
    snapshot=runtime.provider._current(runtime.actor(),runtime.client)
    published={b.canonical_document_id:{'document_id':b.canonical_document_id,'version_id':b.version_id,
        'current_version':b.version_id,'title':b.title or b.canonical_document_id,
        'document_number':getattr(b,'document_number',None),
        'department':normalized_department(b.space_id.removeprefix('DEPT_')).lower()}
        for b in snapshot.bindings if b.dataset_id in snapshot.allowed_datasets}
    published_view=_published_projection(published,query=published_query,
        document_id=published_document_id,page=published_page,page_size=published_page_size)
    availability=__import__(__package__+'.api',fromlist=['_availability'])._availability(runtime)
    availability['can_parse']=bool(availability['configured'] and not availability['blocked'])
    try:
        from .maintenance_batch import batch_available
        availability['can_batch']=batch_available()
    except Exception:
        availability['can_batch']=False
    return {'departments':[{'key':k,'title':v} for k,v in DEPARTMENTS.items()],
            'batches':batch_view['batches'],'selected':selected,
            'batches_total':batch_view['total'],'batches_matched':batch_view['matched'],
            'batches_page':batch_view['page'],'batches_page_size':batch_view['page_size'],
            'batches_has_more':batch_view['has_more'],
            'batch_query':batch_view['query'],'batch_document_id':batch_view['document_id'],
            'batch_lookup_state':batch_view['lookup_state'],
            'batch_scan_truncated':batch_view['scan_truncated'],
            'feedback':feedback_queue(load_runtime()),
            'published_documents':published_view['documents'],
            'published_total':published_view['total'],
            'published_matched':published_view['matched'],
            'published_truncated':published_view['has_more'],
            'published_page':published_view['page'],
            'published_page_size':published_view['page_size'],
            'published_has_more':published_view['has_more'],
            'published_query':published_view['query'],
            'published_document_id':published_view['document_id'],
            'published_lookup_state':published_view['lookup_state'],
            'import_availability':availability,
            'upload_policy':__import__(__package__+'.maintenance_native_upload',fromlist=['upload_policy']).upload_policy(configuration()),
            'department_funnel':department_funnel(published)}

def _published_documents_for_dashboard(published,limit=1000):
    """Bounded catalogue for the maintenance picker; the corpus may exceed 1000.

    The dashboard previously raised POLICY_UNAVAILABLE once more than 1000
    documents were published, which made the whole maintenance page unusable as
    the corpus grew. The picker is a bounded projection: return the first 1000
    by title together with the real total and an explicit truncation flag.
    """
    values=sorted(published.values(),key=lambda i:i['title'])
    return values[:limit],len(values)


def department_funnel(published):
    """Counts only, with a private discovery baseline and live native states."""
    cfg=configuration();outside={};baseline_batches=set();excluded=set()
    path=cfg.get('corpus_funnel_snapshot_file')
    if path:
        try:
            value=json.loads(Path(path).read_text())
            outside=value.get('outside_registered',{});baseline_batches=set(value.get('registered_batch_ids',[]))
            excluded=set(value.get('excluded_batch_ids',[]))
        except (ValueError,TypeError,OSError):raise KnowledgeError('POLICY_UNAVAILABLE') from None
    fields=('discovered','shared_approved','uploaded','parsed','validated','published','pending_review','isolated','sensitive','failed','sharing_pending')
    counts={d:{key:0 for key in fields} for d in DEPARTMENTS};seen={};known=set()
    for row in frappe.get_all(TABLE,fields=['name','frozen_json','state_json','quality_json'],
                              order_by='modified asc',limit_page_length=1000):
        if row['name'] in excluded:continue
        state=_json(row,'state_json',{});quality=_json(row,'quality_json',{});dept=normalized_department(state.get('department_key'))
        if dept not in counts:continue
        for item in state.get('items',[]):
            if item.get('disposition') in ('SAME_CONTENT_SKIP','ALIAS'):continue
            doc=item['canonical_document_id'];known.add(doc)
            current=published.get(doc,{}).get('version_id')
            source_key=item.get('sha256') or doc
            prior=seen.get((dept,source_key))
            if prior:
                previous=prior['item']
                if current and previous['version_id']==current and item['version_id']!=current:continue
                if previous['version_id']==item['version_id']:
                    # An approved derivative retains the same logical/physical
                    # identity as its processing-only parent. Prefer the sharing
                    # confirmation when counting that single document.
                    before=bool(previous.get('internal_sharing_confirmed') and previous.get('owner_inclusion_confirmed'))
                    after=bool(item.get('internal_sharing_confirmed') and item.get('owner_inclusion_confirmed'))
                    if before and not after and prior['explicit_sharing_confirmation']:continue
                elif item['version_id']!=current:
                    if current or not previous.get('sha256') or previous.get('sha256')!=item.get('sha256'):continue
                    # An original asset and its verified full-text derivative
                    # are one source, even before a version is published. Keep
                    # the original's upload until the derivative has a real ID;
                    # then report the best completed processing evidence.
                    if item.get('original_asset_only') and not previous.get('original_asset_only'):continue
                    if previous.get('original_asset_only') and not item.get('ragflow_document_id'):continue
                    rank={'planned':0,'upload_intent':0,'uploaded':1,'parse_intent':2,
                          'parse_queued':2,'parse_failed':2,'quarantined':0,'parsed/indexed':3}
                    if not previous.get('original_asset_only') and rank.get(item.get('status'),0)<rank.get(previous.get('status'),0):continue
            explicit=(state.get('approval_status')=='OWNER_APPROVED' and bool(state.get('parent_processing_batch'))
                      and str(item.get('approval_ref','')).startswith('NATIVE_SHARED_APPROVAL:'))
            seen[(dept,source_key)]={'item':item,'quality':quality.get(item['version_id'],{}),
                             'new_batch':row['name'] not in baseline_batches,'explicit_sharing_confirmation':explicit}
    for (dept,doc),record in seen.items():
        item=record['item'];q=record['quality'];c=counts[dept]
        if record['new_batch']:c['discovered']+=1
        c['shared_approved']+=bool(item.get('internal_sharing_confirmed') and item.get('owner_inclusion_confirmed'))
        c['sharing_pending']+=not bool(item.get('internal_sharing_confirmed') and item.get('owner_inclusion_confirmed'))
        c['uploaded']+=bool(item.get('ragflow_document_id'))
        c['parsed']+=item.get('status')=='parsed/indexed'
        passed=q.get('status')=='Passed' and q.get('source_sha256')==item.get('sha256') and q.get('upload_sha256')==item.get('upload_sha256')
        c['validated']+=passed
        c['pending_review']+=item.get('status')=='parsed/indexed' and not passed
        c['failed']+=item.get('status')=='parse_failed'
        c['isolated']+=item.get('status')=='quarantined'
    for doc,item in published.items():
        dept=item['department'];c=counts.get(dept)
        if c is None:continue
        c['published']+=1
        if doc not in known:
            for key in ('shared_approved','uploaded','parsed','validated'):c[key]+=1
            if not path:c['discovered']+=1
    for dept,c in counts.items():
        extra=outside.get(dept,{})
        for key in fields:
            if key=='published':continue
            number=extra.get(key,0)
            if type(number) is not int or not 0<=number<=100000:raise KnowledgeError('POLICY_UNAVAILABLE')
            c[key]+=number
    return [{'department':dept,'title':DEPARTMENTS[dept],**c} for dept,c in counts.items()]

def require_current_technical_sources(items):
    for item in sorted(items,key=lambda row:row['canonical_document_id']):
        source = frappe.db.get_value('HBOS Knowledge Document', item['canonical_document_id'],
                                     ['current_version','withdrawn','source_hash','ingestion_status'], as_dict=True)
        parent = item.get('native_parent_binding') or {}
        fields = ('canonical_document_id','version_id','space_id','dataset_id','document_id','binding_revision')
        binding = frappe.db.get_value('HBOS Knowledge Backend Binding',parent.get('binding_ref'),
                                      [*fields,'enabled'],as_dict=True) if parent.get('binding_ref') else None
        if (not source or source['withdrawn'] or source['ingestion_status'] != 'published'
                or source['current_version'] != item['version_id'] or source['source_hash'] != item['sha256']
                or not binding or not binding['enabled'] or any(binding[key] != parent.get(key) for key in fields)):
            raise KnowledgeError('IDENTITY_CONFLICT')


def queue(batch_id,document_ids,operation='parse'):
    require();row,frozen,state=_row(batch_id,True)
    if operation not in ('parse','retry','resume','continue') or not isinstance(document_ids,list) or not 1<=len(document_ids)<=4 or len(set(document_ids))!=len(document_ids):raise KnowledgeError('INVALID_REQUEST')
    items=[i for i in state['items'] if i['canonical_document_id'] in document_ids
           and i.get('disposition') not in ('SAME_CONTENT_SKIP','ALIAS')]
    allowed={'planned','uploaded'} if operation=='parse' else ({'parse_queued'} if operation in ('resume','continue') else {'parse_failed'})
    if len(items)!=len(document_ids) or any(i['status'] not in allowed or i['disposition']=='SAME_CONTENT_SKIP'
                                         or i.get('original_asset_only') for i in items):raise KnowledgeError('INVALID_REQUEST')
    from .api import _availability
    from .runtime import load_runtime
    if _availability(load_runtime()).get('blocked'):raise KnowledgeError('UPSTREAM_UNAVAILABLE')
    current=_json(row,'job_json',{})
    if current.get('status') in ('Queued','Running'):raise KnowledgeError('IMPORT_BUSY')
    job={'id':secrets.token_hex(16),'status':'Queued','operation':operation,'document_ids':document_ids,
         'requested_by':frappe.session.user,'requested_at':time.time()}
    cfg=configuration()
    if cfg.get('maintenance_managed_policy') is not None and not current.get('id'):
        if all(item['disposition']=='TECHNICAL_REINDEX' for item in items):
            from .maintenance_permit import require_technical_preparation
            require_technical_preparation(cfg,batch_id,job,frozen,items)
            require_current_technical_sources(items)
            job['technical_preparation'] = True
        else:
            from .maintenance_managed import admit
            admit(cfg,frozen,job)
    if current:
        for key in ('managed_admission','managed_intake','manual_events','technical_preparation'):
            if key in current:job[key]=current[key]
        if job.get('managed_admission'):job['requested_by']=current['requested_by']
        # Retrying a registered batch must retain the prior attempt and its
        # fence. It never clears a successful item or allocates a third target.
        if current.get('r2_task_manifest_sha256') or current.get('r2_preparation'):
            if set(document_ids)!=set(current['document_ids']):
                raise KnowledgeError('IMPORT_BUSY')
            for key in ('r2_task_manifest_sha256','r2_task_ids','r2_tasks_by_document','task_facts',
                        'r2_preparation','r2_preparation_admissions','r2_prepared_tasks_by_document','r2_prepared_sha256',
                        'r2_prepared_manifest','managed_admission'):
                if key in current:job[key]=current[key]
            if job.get('managed_admission'):
                # An explicit resume is still the same authority-bound actor.
                job['requested_by']=current['requested_by']
        if current.get('id'):
            job['lease_generation']=int(current.get('lease_generation') or 0)
            history=list(current.get('recoveries') or [])
            history.append({'kind':'EXPLICIT_REQUEUE','at':time.time(),'operation':operation,
                'previous_job_id':current['id'],'previous_job_status':current.get('status'),
                'previous_lease_generation':int(current.get('lease_generation') or 0),
                'document_ids':list(document_ids),
                'actor_hash':hashlib.sha256(str(frappe.session.user).encode()).hexdigest()[:16]})
            job['recoveries']=history[-20:]
    frappe.db.set_value(TABLE,batch_id,{'job_json':canonical(job),'status':'Queued','last_error':None})
    from .maintenance_browser import record_manual_action
    record_manual_action(batch_id,'SUBMIT' if operation=='parse' else operation.upper())
    frappe.db.commit()
    return {'job_id':job['id'],'status':'Queued'}

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
    from .public_strings import source_string
    chunks=value.get('data',{}).get('chunks',[])
    from knowledge_service.hbos_gateway.native_text import native_text
    def inert_preview(chunk):
        content=chunk.get('content','')
        if not isinstance(content,str) or len(content)>131072:raise KnowledgeError('UPSTREAM_INVALID_RESULT')
        return source_string(native_text(content)[:800],800,
                             physical_ids=(item['dataset_id'],item['ragflow_document_id']))
    return {'document_id':document_id,'version_id':item['version_id'],'title':item['title'],
        'fragments':[{'text':inert_preview(c),'location':'解析片段；页码未核验'} for c in chunks[:5]],
        'page':page,'page_size':5,'has_more':page*5<int(item.get('chunk_count',0)),
        'chunk_count':item.get('chunk_count',0),'source_sha256':item['sha256']}

def review(batch_id,document_id,checks,note):
    return review_batch(batch_id,[document_id],checks,note)

def hold_quality(batch_id,document_ids,note):
    """Keep an exact unpublished subset pending after a stronger quality check."""
    require();row,frozen,state=_row(batch_id,True)
    if (not isinstance(document_ids,list) or not 1<=len(document_ids)<=50
            or len(set(document_ids))!=len(document_ids) or not isinstance(note,str)
            or not 3<=len(note.strip())<=500):raise KnowledgeError('INVALID_REQUEST')
    items=[i for i in state['items'] if i['canonical_document_id'] in document_ids
           and i.get('disposition') not in ('SAME_CONTENT_SKIP','ALIAS')]
    if len(items)!=len(document_ids):raise KnowledgeError('INVALID_REQUEST')
    for item in items:
        current=frappe.db.get_value('HBOS Knowledge Document',item['canonical_document_id'],
                                   ['current_version','withdrawn','ingestion_status'],as_dict=True)
        if is_published_target(item,current):
            raise KnowledgeError('INVALID_REQUEST')
    from .public_strings import safe_string
    quality=_json(row,'quality_json',{})
    for item in items:
        record={'status':'Pending','note':safe_string(note.strip(),500),'source_sha256':item['sha256'],
                'upload_sha256':item.get('upload_sha256'),'version_id':item['version_id'],
                'reviewed_by':frappe.session.user,'reviewed_at':time.time()}
        prior=quality.get(item['version_id'],{})
        if isinstance(prior.get('retrieval_verified'),dict):record['retrieval_verified']=prior['retrieval_verified']
        record['evidence_sha256']=hashlib.sha256(canonical(record).encode()).hexdigest()
        quality[item['version_id']]=record
    frappe.db.set_value(TABLE,batch_id,'quality_json',canonical(quality));frappe.db.commit()
    return {'status':'Pending','held_documents':len(items)}

def review_batch(batch_id,document_ids,checks,note):
    require();row,frozen,state=_row(batch_id,True)
    if not isinstance(document_ids,list) or not 1<=len(document_ids)<=50 or len(set(document_ids))!=len(document_ids):raise KnowledgeError('INVALID_REQUEST')
    if not isinstance(checks,list) or set(checks)!={'text','numbers','tables','identity'} or not isinstance(note,str) or not 3<=len(note.strip())<=500:raise KnowledgeError('INVALID_REQUEST')
    from .public_strings import safe_string
    note=safe_string(note.strip(),500)
    items=[i for i in state['items'] if i['canonical_document_id'] in document_ids and i.get('disposition') not in ('SAME_CONTENT_SKIP','ALIAS')]
    from knowledge_service.ingestion import processing_approved
    if len(items)!=len(document_ids) or any(i['status']!='parsed/indexed' or not processing_approved(frozen,i) for i in items):raise KnowledgeError('INVALID_REQUEST')
    from .maintenance_task_facts import require_durable_task_acks
    require_durable_task_acks(_json(row,'job_json',{}),items)
    if _json(row,'job_json',{}).get('managed_admission'):
        if any((item.get('automatic_quality') or {}).get('status')!='AUTO_VERIFIED_PENDING_REVIEW'
               or not item.get('parse_provenance') for item in items):
            raise KnowledgeError('QUALITY_REQUIRED')
    from .reference_admin import _verify_backend
    # Verify the entire exact selection before changing any review record.
    for item in items:_verify_backend(configuration(),item)
    quality=_json(row,'quality_json',{});records=[]
    for item in items:
        record={'status':'Passed','note':note.strip(),'checks':sorted(checks),
            'source_sha256':item['sha256'],'upload_sha256':item['upload_sha256'],'version_id':item['version_id'],
            'reviewed_by':frappe.session.user,'reviewed_at':time.time()}
        prior=quality.get(item['version_id'],{})
        if isinstance(prior.get('retrieval_verified'),dict):record['retrieval_verified']=prior['retrieval_verified']
        record['evidence_sha256']=hashlib.sha256(canonical(record).encode()).hexdigest()
        quality[item['version_id']]=record;records.append(record)
    frappe.db.set_value(TABLE,batch_id,'quality_json',canonical(quality))
    from .maintenance_browser import record_manual_action
    record_manual_action(batch_id,'REVIEW')
    frappe.db.commit()
    return {'status':'Passed','reviewed_documents':len(items),'evidence_sha256':records[0]['evidence_sha256'] if len(records)==1 else hashlib.sha256(canonical(records).encode()).hexdigest()}

def approve_sharing(batch_id,document_ids,note):
    """An explicit maintainer confirmation creates a new immutable sharing batch."""
    require();row,frozen,state=_row(batch_id,True)
    if (frozen.get('approval_status')!='OWNER_PROCESSING_ONLY' or not isinstance(document_ids,list)
            or not 1<=len(document_ids)<=50 or len(set(document_ids))!=len(document_ids)
            or not isinstance(note,str) or not 3<=len(note.strip())<=500):raise KnowledgeError('INVALID_REQUEST')
    items=[i for i in state['items'] if i['canonical_document_id'] in document_ids
           and i.get('disposition') not in ('SAME_CONTENT_SKIP','ALIAS')]
    quality=_json(row,'quality_json',{})
    if len(items)!=len(document_ids):raise KnowledgeError('INVALID_REQUEST')
    for item in items:
        q=quality.get(item['version_id'],{})
        if (item['status']!='parsed/indexed' or item.get('technical_admission')!='ADMIT_INTERNAL_REFERENCE'
                or item.get('internal_sharing_confirmed') is not False or item.get('owner_inclusion_confirmed') is not False
                or q.get('status')!='Passed' or q.get('source_sha256')!=item['sha256']
                or q.get('upload_sha256')!=item.get('upload_sha256')):raise KnowledgeError('QUALITY_REQUIRED')
    from .public_strings import safe_string
    from .reference_admin import _verify_backend
    for item in items:_verify_backend(configuration(),item)
    approval='NATIVE_SHARED_APPROVAL:'+hashlib.sha256(canonical([frappe.session.user,batch_id,sorted(document_ids),note.strip()]).encode()).hexdigest()
    new_frozen=copy.deepcopy(frozen);new_frozen.pop('batch_sha256')
    new_frozen.update(approval_status='OWNER_APPROVED',approval_ref=approval,
        parent_processing_batch=batch_id,sharing_review_note=safe_string(note.strip(),500))
    new_frozen['items']=[copy.deepcopy(i) for i in frozen['items'] if i['canonical_document_id'] in document_ids]
    for item in new_frozen['items']:item.update(owner_inclusion_confirmed=True,internal_sharing_confirmed=True,approval_ref=approval)
    new_frozen['batch_sha256']=hashlib.sha256(canonical(new_frozen).encode()).hexdigest()
    new_state=copy.deepcopy(new_frozen)
    from knowledge_service.ingestion import RUNTIME_STATE_FIELDS,RUNTIME_ITEM_FIELDS
    new_state.update({k:v for k,v in state.items() if k in RUNTIME_STATE_FIELDS})
    by_version={i['version_id']:i for i in items}
    for item in new_state['items']:item.update({k:v for k,v in by_version[item['version_id']].items() if k in RUNTIME_ITEM_FIELDS})
    new_id='IMP_'+new_frozen['batch_sha256'][:32];exists=frappe.db.exists(TABLE,new_id)
    register_batch(new_frozen,new_state,'已确认共享的资料批次',frappe.session.user)
    if not exists:frappe.db.set_value(TABLE,new_id,'quality_json',canonical({i['version_id']:quality[i['version_id']] for i in items}))
    frappe.db.commit();return {'batch_id':new_id,'approved_documents':len(items),'status':'Sharing approved; publication required'}

def publication_config(batch_id,selected,operation,expected,reason,approval):
    # Called only after the public native handler checked the maintenance role,
    # or by a signed registered coordinator. The frozen record is authoritative.
    row,frozen,state=_row(batch_id,True);quality=_json(row,'quality_json',{})
    from .publication import select_publication_items,FROZEN_PUBLICATION_FIELDS
    items=select_publication_items(state,selected)
    from .maintenance_task_facts import require_durable_task_acks
    require_durable_task_acks(_json(row,'job_json',{}),items)
    for item in items:
        q=quality.get(item['version_id'],{})
        if q.get('status')!='Passed' or q.get('source_sha256')!=item['sha256'] or q.get('upload_sha256')!=item['upload_sha256']:raise KnowledgeError('QUALITY_REQUIRED')
    cfg=dict(configuration());sha=state['batch_sha256'];selection=hashlib.sha256(canonical(sorted(selected)).encode()).hexdigest()
    cfg['approved_batch_sha256s']=[sha];cfg['approved_space_ids']=[cfg.get('department_space_map',{}).get(frozen['department_key'],'DEPT_'+frozen['department_key'].upper())]
    cfg['approved_dataset_ids']=sorted({i['dataset_id'] for i in items});cfg['approved_document_ids']=selected
    cfg['approved_publication_items']={sha:{i['canonical_document_id']:{k:i.get(k) for k in FROZEN_PUBLICATION_FIELDS} for i in items}}
    cfg['approved_publication_subsets']={selection:{'batch_sha256':sha,'canonical_document_ids':sorted(selected),'approval_ref':approval,
        'quality_evidence_sha256':hashlib.sha256(canonical(quality).encode()).hexdigest()}}
    if operation=='repair':
        if len(items)!=1:raise KnowledgeError('INVALID_REQUEST')
        item=items[0];proof=item.get('technical_correction')
        from .publication import validate_technical_repair
        if not isinstance(proof,dict):raise KnowledgeError('INVALID_REQUEST')
        parent_sha=proof.get('parent_batch_sha256')
        if not isinstance(parent_sha,str) or not re.fullmatch(r'[0-9a-f]{64}',parent_sha):raise KnowledgeError('INVALID_REQUEST')
        parent_row,parent_frozen,parent_state=_row('IMP_'+parent_sha[:32],True)
        if parent_frozen['batch_sha256']!=parent_sha:raise KnowledgeError('INVALID_REQUEST')
        parents=[i for i in parent_state['items'] if i['canonical_document_id']==item['canonical_document_id']
                 and i['version_id']==expected and i.get('disposition') not in ('SAME_CONTENT_SKIP','ALIAS')]
        if len(parents)!=1:raise KnowledgeError('INVALID_REQUEST')
        validate_technical_repair(item,parents[0],expected)
        parent_quality=_json(parent_row,'quality_json',{}).get(expected,{})
        if (parent_quality.get('status')!='Pending' or parent_quality.get('version_id')!=expected
            or parent_quality.get('source_sha256')!=item['sha256']):raise KnowledgeError('QUALITY_REQUIRED')
        cfg['approved_technical_repairs']={item['canonical_document_id']:{'proof':copy.deepcopy(proof),
            'parent_item':copy.deepcopy(parents[0]),'parent_quality_sha256':hashlib.sha256(canonical(parent_quality).encode()).hexdigest()}}
    cfg['approved_publication_intents']=[{'batch_sha256':sha,'canonical_document_id':i['canonical_document_id'],'operation':operation,
        'expected_current_version':expected,'version_id':i['version_id'],'sha256':i['sha256'],'approval_ref':approval,'reason':reason} for i in items]
    return cfg,state

def publish(batch_id,document_ids,operation='publish',expected_version=None,reason=None,*,expected_lifecycle_receipt=None):
    require()
    if operation=='technical_reindex':
        from .parse_revision import promote
        return promote(batch_id,document_ids,expected_version,reason)
    if operation=='technical_rollback':
        from .parse_revision import rollback
        return rollback(batch_id,document_ids,expected_version,reason)
    if operation not in ('publish','replace','restore','repair') or not isinstance(document_ids,list):raise KnowledgeError('INVALID_REQUEST')
    if operation!='publish' and (len(document_ids)!=1 or not isinstance(reason,str) or not 3<=len(reason.strip())<=500):raise KnowledgeError('INVALID_REQUEST')
    from .reference_admin import publish as existing
    from .publication import UNRECORDED_ACTIVATION, latest_lifecycle_receipt, valid_lifecycle_receipt
    if expected_lifecycle_receipt is not None and (operation!='restore'
            or expected_lifecycle_receipt==UNRECORDED_ACTIVATION or not valid_lifecycle_receipt(expected_lifecycle_receipt)):
        raise KnowledgeError('INVALID_REQUEST')
    # A restore belongs to a specific withdrawal. Reuse the approval only for
    # a retry of that withdrawal, even when the maintainer uses the same reason.
    actor=frappe.session.user
    intent=[actor,batch_id,sorted(document_ids),operation,expected_version,reason]
    legacy_approval='NATIVE_MAINTENANCE:'+hashlib.sha256(canonical(intent).encode()).hexdigest()
    approval=legacy_approval
    withdrawal=None
    if operation!='publish' and len(document_ids)==1:
        _,_,state=_row(batch_id)
        # A batch may hold a second item for the same document recorded as
        # SAME_CONTENT_SKIP when identical content was seen again. That item is a
        # duplicate record, not an alternative target, so counting it made
        # restore/replace fail with INVALID_REQUEST for such documents.
        targets=[i['version_id'] for i in state['items'] if i['canonical_document_id']==document_ids[0]
                 and i.get('disposition') not in ('ALIAS','SAME_CONTENT_SKIP')]
        if len(targets)!=1:raise KnowledgeError('INVALID_REQUEST')
        if operation=='restore':
            if targets[0]!=expected_version:raise KnowledgeError('IDENTITY_CONFLICT')
            withdrawal=expected_lifecycle_receipt or latest_lifecycle_receipt(document_ids[0],expected_version,withdrawn=True)
            if withdrawal is None:raise KnowledgeError('IDENTITY_CONFLICT')
            approval='NATIVE_MAINTENANCE:'+hashlib.sha256(canonical([*intent,withdrawal]).encode()).hexdigest()
        committed=[]
        if operation!='restore' or expected_lifecycle_receipt is None:
            committed=frappe.get_all('HBOS Knowledge Publication',filters={
                'canonical_document_id':document_ids[0],'target_version':targets[0],
                'batch_sha256':state['batch_sha256'],'operation':'replace' if operation=='repair' else operation,
                'expected_current_version':expected_version,'reason':reason},
                fields=['approval_ref','receipt_id'],order_by='creation asc',limit_page_length=0)
        if operation!='restore':
            owned=[r['approval_ref'] for r in committed if r['approval_ref']==approval
                   or (r.get('approval_ref') or '').startswith('NATIVE_MAINTENANCE:'+actor+':')]
            if owned:approval=owned[0]
        elif committed and expected_lifecycle_receipt is None:
            current=frappe.db.get_value('HBOS Knowledge Document',document_ids[0],
                ['current_version','withdrawn'],as_dict=True)
            if current and current['current_version']==expected_version and not current['withdrawn']:
                active=latest_lifecycle_receipt(document_ids[0],expected_version,withdrawn=False)
                for row in committed:
                    previous=row.get('approval_ref') or ''
                    if row.get('receipt_id')==active and (previous==legacy_approval
                            or previous.startswith('NATIVE_MAINTENANCE:'+actor+':')):
                        approval=previous
                        break
    from .maintenance_browser import record_manual_action
    record_manual_action(batch_id,'PUBLISH' if operation=='publish' else operation.upper())
    frappe.db.commit()
    result=existing(None,operation,expected_version,reason,approval,document_ids,
        registered_batch_id=batch_id,expected_withdrawal_receipt=withdrawal)
    # Publication alone is not employee retrieval verification. Keep a durable
    # PENDING marker (best effort: the publication already committed) so the
    # maintainer UI can show an honest badge until a real employee search and
    # evidence resolution receipt arrives.
    try:
        from .maintenance_batch import mark_retrieval_pending
        mark_retrieval_pending(batch_id,result)
    except Exception:
        # Best-effort post-publication marker: the publication already committed
        # and must not be reported as failed. Roll back only the marker write.
        rollback=getattr(getattr(frappe,'db',None),'rollback',None)
        if callable(rollback):
            try:rollback()
            except Exception:pass
    return result

def withdraw(batch_id,document_id,expected_version,reason,*,expected_lifecycle_receipt=None):
    from .publication import UNRECORDED_ACTIVATION, latest_lifecycle_receipt, valid_lifecycle_receipt
    require();row,frozen,state=_row(batch_id,True)
    if not isinstance(reason,str) or not 3<=len(reason.strip())<=500:raise KnowledgeError('INVALID_REQUEST')
    if expected_lifecycle_receipt is not None and not valid_lifecycle_receipt(expected_lifecycle_receipt):
        raise KnowledgeError('INVALID_REQUEST')
    items=[i for i in state['items'] if i['canonical_document_id']==document_id and i['version_id']==expected_version
           and i.get('disposition') not in ('SAME_CONTENT_SKIP','ALIAS')]
    if len(items)!=1:raise KnowledgeError('INVALID_REQUEST')
    rows=frappe.db.sql('SELECT current_version,withdrawn,source_hash FROM `tabHBOS Knowledge Document` WHERE name=%s FOR UPDATE',(document_id,),as_dict=True)
    if len(rows)!=1 or rows[0]['current_version']!=expected_version:raise KnowledgeError('IDENTITY_CONFLICT')
    withdrawn=bool(rows[0]['withdrawn'])
    current_receipt=latest_lifecycle_receipt(document_id,expected_version,withdrawn=withdrawn,lock=True)
    if withdrawn and not current_receipt:raise KnowledgeError('IDENTITY_CONFLICT')
    activation=expected_lifecycle_receipt or current_receipt or UNRECORDED_ACTIVATION
    receipt='PUB_'+hashlib.sha256(canonical(
        [batch_id,document_id,expected_version,'withdraw',reason,frappe.session.user,activation]).encode()).hexdigest()
    if withdrawn:
        if expected_lifecycle_receipt is not None and receipt!=current_receipt:raise KnowledgeError('IDENTITY_CONFLICT')
        return {'outcome':'NOOP','receipt_id':current_receipt}
    if activation!=(current_receipt or UNRECORDED_ACTIVATION):raise KnowledgeError('IDENTITY_CONFLICT')
    frappe.db.set_value('HBOS Knowledge Document',document_id,{'withdrawn':1,'ingestion_status':'retired'})
    frappe.get_doc({'doctype':'HBOS Knowledge Publication','receipt_id':receipt,'canonical_document_id':document_id,
        'target_version':expected_version,'batch_sha256':state['batch_sha256'],'operation':'withdraw',
        'expected_current_version':expected_version,'source_hash':rows[0]['source_hash'],'reason':reason,
        'approval_ref':'NATIVE_WITHDRAW:'+frappe.session.user,'outcome':'WITHDRAWN'}).insert(ignore_permissions=True)
    from .maintenance_browser import record_manual_action
    record_manual_action(batch_id,'WITHDRAW')
    frappe.db.commit()
    return {'outcome':'WITHDRAWN','receipt_id':receipt}
