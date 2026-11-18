"""Native user-owned activity, with bounded answer/preview snapshots for restoration."""
import hashlib,json,secrets
from .errors import KnowledgeError
from .r1_contract import normalize_search, ANSWER_MAX_CODEPOINTS
from .public_strings import safe_string, source_string
from .gateway import EvidenceRecord
from .service_http import canonical

DOCTYPE='HBOS Knowledge Activity'

def current(runtime):
    from .spaces import authorized_spaces
    from .execution_plan import validate_admission
    actor=runtime.actor();snapshot=runtime.provider._current(actor,runtime.client)
    allowed=authorized_spaces(snapshot,actions=('knowledge.search',));mapping={}
    for b in snapshot.bindings:
        if b.space_id not in allowed or b.dataset_id not in snapshot.allowed_datasets:continue
        try:validate_admission(b,runtime.profile,runtime.provider.clock())
        except KnowledgeError:continue
        mapping[(b.canonical_document_id,b.version_id)]=b
    return actor,mapping

def logical(records):
    return sorted({(r.binding.canonical_document_id,r.binding.version_id,r.binding.binding_ref,r.chunk_id) for r in records})

def save_bookmark(runtime,query,resolve):
    """One bounded transaction retry, reauthorizing the source every time.

    MariaDB snapshot isolation can reject a locking read of a concurrently
    committed bookmark with error 1020. Only this read-and-save endpoint retries;
    it has no model operation and must have no staged publication writes.
    """
    import frappe
    for attempt in range(2):
        try:
            record=resolve()
            return write('Bookmark',query,[record.space_id],[record],runtime)
        except frappe.QueryDeadlockError:
            publication=getattr(runtime,'publication',None)
            if (attempt or publication is None or any(getattr(publication,k,()) for k in ('references','audits','handles'))):
                raise KnowledgeError('SERVICE_ERROR') from None
            frappe.db.rollback()
    raise KnowledgeError('SERVICE_ERROR')

def write(kind,query,spaces,records,runtime,*,conversation_id=None,category=None,note=None,context=None,
          answer=None,labels=None,question=None,search_mode='STANDARD',document_bookmark=False,answer_origin=None,model_alias=None):
    import frappe
    actor,_=current(runtime)
    safe_string(query,500)
    data={'query':query,'space_ids':sorted(set(spaces or [])),'references':logical(records)}
    if document_bookmark:
        if kind!='Bookmark' or len(records)!=1:raise KnowledgeError('INVALID_REQUEST')
        data['bookmark_type']='Document'
    if kind in ('History','Bookmark') and not document_bookmark:
        # Only the finite previews already authorized for this response. Never
        # store native full chunks, files, service tokens or evidence handles.
        # The excerpt is the document's own text and has already passed the
        # citation display gate (source_string) in this same response. Re-running
        # the *model-output* gate here rejected a regulation that prints a URL or
        # an absolute path and failed the whole search with
        # UPSTREAM_INVALID_RESULT, so the same source gate is applied instead.
        data['previews']=[{'reference':[r.binding.canonical_document_id,r.binding.version_id,r.binding.binding_ref,r.chunk_id],
                          'excerpt':source_string(r.excerpt,500),'page_number':r.page_number} for r in records]
        if len(data['previews'])>5:raise KnowledgeError('INVALID_REQUEST')
        data['search_mode']=search_mode
    if answer is not None:
        data['answer']=safe_string(answer,ANSWER_MAX_CODEPOINTS)
        data['labels']=list(labels or [])
        data['question']=safe_string(question or query,500)
        if answer_origin is not None:
            from .answer_policy import model_alias as validate
            if (answer_origin not in ('GENERAL','KNOWLEDGE')
                    or (answer_origin=='GENERAL' and (records or labels or model_alias is None))):
                raise KnowledgeError('INVALID_REQUEST')
            data.update(answer_origin=answer_origin,model_alias=None if model_alias is None else validate(model_alias))
    if context:data['context']=dict(context)
    if conversation_id:data['conversation_id']=conversation_id
    if category:data.update(category=category,note=safe_string(note or '',500))
    if kind=='Bookmark':
        # Preview formatting must not turn an existing bookmark into a duplicate.
        fingerprint=canonical({k:v for k,v in data.items() if k not in ('previews','search_mode')})
    name=('BOOKMARK_'+hashlib.sha256((actor.user_ref+'\0'+fingerprint).encode()).hexdigest()
          if kind=='Bookmark' else secrets.token_urlsafe(24))
    doc={'doctype':DOCTYPE,'activity_id':name,'owner_user':actor.user_ref,'kind':kind,
        'payload_json':canonical(data),'status':'Pending' if kind=='Feedback' else 'Saved',
        'publication_id':runtime.publication.publication_id if kind=='History' else ''}
    if kind=='Bookmark':
        # Lock an existing native row, rather than competing for the absent
        # bookmark's index gap. MariaDB may otherwise raise a transaction
        # deadlock before it can report a duplicate insert. The user row remains
        # locked until Frappe commits the whole request, serializing this owner's
        # saves across processes without a separate lock service or new table.
        users=frappe.db.sql('SELECT name,enabled FROM `tabUser` WHERE name=%s FOR UPDATE',
                           (actor.user_ref,),as_dict=True)
        if len(users)!=1 or not users[0]['enabled']:raise KnowledgeError('AUTHENTICATION_REQUIRED')
        found=frappe.db.sql('SELECT name,payload_json FROM `tabHBOS Knowledge Activity` '
            'WHERE name=%s AND owner_user=%s AND kind=%s FOR UPDATE',
            (name,actor.user_ref,'Bookmark'),as_dict=True)
        if found:
            if len(found)!=1:raise KnowledgeError('SERVICE_ERROR')
            try:existing=json.loads(found[0]['payload_json'])
            except (ValueError,TypeError):raise KnowledgeError('SERVICE_ERROR') from None
            if not isinstance(existing,dict):raise KnowledgeError('SERVICE_ERROR')
            if canonical({k:v for k,v in existing.items() if k not in ('previews','search_mode')})!=fingerprint:raise KnowledgeError('SERVICE_ERROR')
            return found[0]['name']
        # Keep previously saved random IDs; a locking read also sees a save
        # committed after this request's earlier consistent reads.
        old=frappe.db.sql('SELECT name FROM `tabHBOS Knowledge Activity` '
            'WHERE owner_user=%s AND kind=%s AND payload_json=%s LIMIT 1 FOR UPDATE',
            (actor.user_ref,'Bookmark',fingerprint),as_dict=True)
        if old:return old[0]['name']
        frappe.db.savepoint('knowledge_bookmark_insert')
        try:frappe.get_doc(doc).insert(ignore_permissions=True)
        except frappe.DuplicateEntryError:
            frappe.db.rollback(save_point='knowledge_bookmark_insert')
            found=frappe.db.sql('SELECT name,payload_json FROM `tabHBOS Knowledge Activity` '
                'WHERE name=%s AND owner_user=%s AND kind=%s FOR UPDATE',
                (name,actor.user_ref,'Bookmark'),as_dict=True)
            if len(found)!=1:raise KnowledgeError('SERVICE_ERROR')
    else:frappe.get_doc(doc).insert(ignore_permissions=True)
    return name

def owned(name,actor,kinds=('History','Bookmark')):
    import frappe
    if not isinstance(name,str) or not 1<=len(name)<=128:raise KnowledgeError('INVALID_REQUEST')
    row=frappe.db.get_value(DOCTYPE,{'name':name,'owner_user':actor.user_ref},['name','kind','payload_json','publication_id'],as_dict=True)
    if not row or row.kind not in kinds:raise KnowledgeError('EVIDENCE_UNAVAILABLE')
    if row.publication_id and not frappe.db.exists('HBOS Knowledge Audit',{'publication_id':row.publication_id,'publication_state':'Complete'}):
        raise KnowledgeError('EVIDENCE_UNAVAILABLE')
    return row,json.loads(row.payload_json)

def _same_source_revision(document, version, reference, binding):
    """Require an immutable adoption receipt for this exact authorized pair."""
    import frappe
    import re

    current = frappe.db.get_value('HBOS Knowledge Document', document,
                                  ['current_version', 'source_hash', 'withdrawn', 'ingestion_status'],
                                  as_dict=True)
    if (not current or current.current_version != version or current.withdrawn
            or current.ingestion_status != 'published'
            or not re.fullmatch('[0-9a-f]{64}', current.source_hash or '')):
        return False
    rows = frappe.get_all('HBOS Knowledge Parse Revision', filters={
        'canonical_document_id': document, 'version_id': version,
        'parent_binding_ref': reference, 'target_binding_ref': binding.binding_ref,
    }, fields=['receipt_json'], limit_page_length=2)
    if len(rows) != 1:
        return False
    receipt = json.loads(rows[0].receipt_json)
    schema = receipt.get('schema')
    approved_direction = schema == 'hbos.parse-revision.v1' or (
        schema == 'hbos.parse-rollback.v1'
        and receipt.get('old_authorization_snapshot_restored') is False
        and receipt.get('current_binding_ref') == reference
        and receipt.get('return_binding_ref') == binding.binding_ref
    )
    return (approved_direction
            and receipt.get('business_version_changed') is False
            and receipt.get('canonical_document_id') == document
            and receipt.get('version_id') == version
            and receipt.get('parent_binding_ref') == reference
            and receipt.get('new_binding_ref') == binding.binding_ref
            and receipt.get('source_sha256') == current.source_hash)


def bindings_for(data,mapping,*,allow_reindex=False):
    selected=[]
    for document,version,reference,chunk in data['references']:
        b=mapping.get((document,version))
        if not b:
            raise KnowledgeError('EVIDENCE_UNAVAILABLE')
        if b.binding_ref != reference:
            if not allow_reindex or not _same_source_revision(document, version, reference, b):
                raise KnowledgeError('EVIDENCE_UNAVAILABLE')
        selected.append(b)
    return selected

def list_activity(runtime,kind,page=1,page_size=12):
    import frappe
    if kind not in ('History','Bookmark'):raise KnowledgeError('INVALID_REQUEST')
    from .reference_admin import _page_number
    page=_page_number(page,100000);page_size=_page_number(page_size,50)
    actor,mapping=current(runtime)
    rows=frappe.get_all(DOCTYPE,filters={'owner_user':actor.user_ref,'kind':kind},fields=['name','payload_json','creation','publication_id'],order_by='creation desc,name desc',limit_start=(page-1)*page_size,limit_page_length=page_size+1)
    def project(current_mapping):
        out=[]
        for row in rows:
            if row.publication_id and not frappe.db.exists('HBOS Knowledge Audit',{'publication_id':row.publication_id,'publication_state':'Complete'}):continue
            data=json.loads(row.payload_json)
            try:
                bindings=bindings_for(data,current_mapping,allow_reindex='previews' in data);available=True
            except KnowledgeError:bindings=[];available=False
            out.append({'id':row.name,'query':safe_string(data.get('question',data['query']),500),'created_at':str(row.creation),
                'available':available,'titles':[safe_string(b.title,240,nullable=True) for b in bindings],
                'document_ids':[b.canonical_document_id for b in bindings],
                'version_ids':[b.version_id for b in bindings],
                'bookmark_type':data.get('bookmark_type','Evidence'),
                'answer_origin':data.get('answer_origin','KNOWLEDGE') if 'answer' in data else None,
                'model_alias':data.get('model_alias') if 'answer' in data else None})
        return out
    out=project(mapping)
    final_actor,final_mapping=current(runtime)
    if final_actor!=actor or out!=project(final_mapping):raise KnowledgeError('SCOPE_REJECTED')
    return {'items':out[:page_size],'page':page,'page_size':page_size,'has_more':len(rows)>page_size}

def reopen(runtime,name,request_id):
    actor,mapping=current(runtime);row,data=owned(name,actor)
    if data.get('bookmark_type')=='Document':
        bindings=bindings_for(data,mapping)
        if len(bindings)!=1:raise KnowledgeError('EVIDENCE_UNAVAILABLE')
        binding=bindings[0]
        authorize_document(runtime,actor,binding,request_id)
        from .reference_admin import _catalog_projection
        documents=_catalog_projection(runtime,runtime.provider._current(actor,runtime.client))
        selected=[d for d in documents if d['document_id']==binding.canonical_document_id and d['version_id']==binding.version_id]
        if len(selected)!=1:raise KnowledgeError('EVIDENCE_UNAVAILABLE')
        final_actor,final_mapping=current(runtime)
        if final_actor!=actor:raise KnowledgeError('SCOPE_REJECTED')
        bindings_for(data,final_mapping)
        return {'query':binding.title or data['query'],'space_ids':[binding.space_id],
                'document':selected[0],'bookmark_type':'Document'}
    if 'previews' in data:
        return restore(runtime,row,data,actor,mapping,request_id)
    bindings=bindings_for(data,mapping)
    request=normalize_search({'query':data['query'],**({'space_ids':data['space_ids']} if data['space_ids'] else {}),
                              **({'context':data['context']} if data.get('context') else {})})
    ticket=runtime.decisions.issue(actor,runtime.client,'knowledge.search',request,request_id)
    # Revalidate native RAGFlow metadata, not only the saved title or HBOS cache.
    records=[EvidenceRecord(b.canonical_document_id,b.title,b.business_version,None,b.section,None,'',reference[3],b.dataset_alias,b.space_id,b.version_id,b.binding_ref,b) for b,reference in zip(bindings,data['references'])]
    if records:
        runtime.decisions.online(__principal(runtime),ticket.call('introspect','introspect'))
        runtime.gateway.authorize_evidence(ticket,records,phase='evidence_read')
    runtime.provider.revalidate(ticket.plan)
    return {'query':data['query'],'space_ids':data['space_ids'],**({'context':dict(request.context)} if request.context else {})}

def authorize_document(runtime,actor,binding,request_id):
    """Verify current authorization and native indexed metadata; issue no chunk handle."""
    query=safe_string(binding.title or binding.canonical_document_id,240)
    request=normalize_search({'query':query,'space_ids':[binding.space_id]})
    ticket=runtime.decisions.issue(actor,runtime.client,'knowledge.search',request,request_id)
    record=EvidenceRecord(binding.canonical_document_id,binding.title,binding.business_version,None,
        binding.section,None,'','CATALOG_METADATA_ONLY',binding.dataset_alias,binding.space_id,
        binding.version_id,binding.binding_ref,binding)
    runtime.decisions.online(__principal(runtime),ticket.call('introspect','introspect'))
    runtime.gateway.authorize_evidence(ticket,[record],phase='document_read')
    runtime.decisions.online(__principal(runtime),ticket.call('revalidate','final_publish'))
    return record

def save_document(runtime,document_id,version_id,request_id):
    """A client logical ID selects a current authorized binding, never grants reading."""
    import frappe
    safe_string(document_id,120);safe_string(version_id,120)
    for attempt in range(2):
        try:
            actor,mapping=current(runtime);binding=mapping.get((document_id,version_id))
            if not binding:raise KnowledgeError('EVIDENCE_UNAVAILABLE')
            record=authorize_document(runtime,actor,binding,request_id+'_'+str(attempt))
            name=write('Bookmark',binding.title or document_id,[binding.space_id],[record],runtime,document_bookmark=True)
            final_actor,final_mapping=current(runtime)
            if final_actor!=actor or final_mapping.get((document_id,version_id))!=binding:raise KnowledgeError('SCOPE_REJECTED')
            return name
        except frappe.QueryDeadlockError:
            if attempt:raise KnowledgeError('SERVICE_ERROR') from None
            frappe.db.rollback()
    raise KnowledgeError('SERVICE_ERROR')

def restore(runtime,row,data,actor,mapping,request_id):
    """A fresh session gets fresh handles only after present source authorization.

    Unchanged bindings are reauthorized directly. A technical successor must
    also return a matching excerpt under the new binding before any old answer
    can be displayed. No model generation is used.
    """
    from .evidence import issue_evidence
    from .employee_evidence import public_evidence
    chain=[(row.name,data)]
    if 'answer' in data:
        seen={row.name}
        while chain[-1][1].get('conversation_id') and len(chain)<10:
            parent=chain[-1][1]['conversation_id']
            if parent in seen:raise KnowledgeError('EVIDENCE_UNAVAILABLE')
            parent_row,parent_data=owned(parent,actor,kinds=('History',))
            if 'answer' not in parent_data:break
            seen.add(parent);chain.append((parent_row.name,parent_data))
        chain.reverse()
    # Validate the complete chain before issuing any handle or answer.
    for _,item in chain:bindings_for(item,mapping,allow_reindex=True)
    turns=[];results=[]
    for index,(turn,item) in enumerate(chain):
        request=normalize_search({'query':item['query'],**({'space_ids':item['space_ids']} if item['space_ids'] else {}),
            **({'context':item['context']} if item.get('context') else {}),'search_mode':item.get('search_mode','STANDARD')})
        ticket=runtime.decisions.issue(actor,runtime.client,'knowledge.search',request,request_id+'_'+str(index))
        runtime.publication.plan=ticket.plan
        previews=item['previews'];records=[]
        if not isinstance(previews,list) or len(previews)>5:raise KnowledgeError('EVIDENCE_UNAVAILABLE')
        fresh = None
        for preview in previews:
            document,version,reference,chunk=preview['reference']
            b=mapping.get((document,version))
            if not b:
                raise KnowledgeError('EVIDENCE_UNAVAILABLE')
            excerpt = source_string(preview['excerpt'],500)
            if b.binding_ref != reference:
                if not _same_source_revision(document, version, reference, b):
                    raise KnowledgeError('EVIDENCE_UNAVAILABLE')
                if fresh is None:
                    fresh = runtime.gateway.search(ticket=ticket)
                expected = ' '.join(excerpt.split())
                matches = [r for r in fresh if r.binding == b
                           and expected and expected in ' '.join(r.excerpt.split())]
                if len(matches) != 1:
                    raise KnowledgeError('HISTORY_REINDEX_REVIEW_REQUIRED')
                records.append(matches[0])
            else:
                records.append(EvidenceRecord(document,b.title,b.business_version,'内部参考／有效性待核',b.section,
                    preview['page_number'],excerpt,chunk,b.dataset_alias,b.space_id,b.version_id,reference,b))
        if fresh is None:
            runtime.decisions.online(__principal(runtime),ticket.call('introspect','introspect'))
            runtime.decisions.online(__principal(runtime),ticket.call('introspect','cache_read'))
            runtime.decisions.online(__principal(runtime),ticket.call('revalidate','pre_projection'))
        if records:
            runtime.gateway.authorize_evidence(ticket,records,phase='evidence_read')
        runtime.provider.revalidate(ticket.plan)
        answer=item.get('answer')
        alias=item.get('model_alias')
        general=item.get('answer_origin')=='GENERAL'
        presentation=None
        if answer is not None and not records and not general:
            from .followup import historical_catalogue, HISTORY_ANSWER_HIDDEN
            alias=None
            if historical_catalogue(item):
                from .catalog_direct import render
                from .spaces import list_spaces
                titles={space['space_id']:space['title'] for space in list_spaces(runtime,actor)['spaces']}
                answer, found = render(ticket.plan, titles, item.get('question') or item['query'])
                presentation='CATALOG_RESULTS' if found else 'INSUFFICIENT_EVIDENCE'
            else:
                answer=HISTORY_ANSWER_HIDDEN
                presentation='INSUFFICIENT_EVIDENCE'
        runtime.quota.reserve_output(actor.user_ref,sum(len(r.excerpt) for r in records)+len(answer or ''))
        output=[public_evidence(r,issue_evidence(runtime.cache,ticket,r,runtime=runtime),environment=runtime.profile) for r in records]
        if 'answer' in item:
            labels=item.get('labels',[])
            if len(labels)!=len(output):raise KnowledgeError('EVIDENCE_UNAVAILABLE')
            citations=[dict(source,citation_label=label) for source,label in zip(output,labels)]
            if general and (records or citations):raise KnowledgeError('EVIDENCE_UNAVAILABLE')
            from .answer_policy import answer_presentation
            turns.append({'request_id':request_id,'turn_id':turn,'conversation_id':turn,
                **answer_presentation(answer,bool(citations),general,state=presentation),
                'answer':answer,'citations':citations,'question':item.get('question',item['query']),
                'answer_origin':item.get('answer_origin','KNOWLEDGE'),'model_alias':alias})
        else:results=output
        runtime.decisions.online(__principal(runtime),ticket.call('revalidate','final_publish'))
    final_actor,final_mapping=current(runtime)
    if final_actor!=actor:raise KnowledgeError('SCOPE_REJECTED')
    for _,item in chain:
        if (bindings_for(item,final_mapping,allow_reindex=True)
                != bindings_for(item,mapping,allow_reindex=True)):
            raise KnowledgeError('SCOPE_REJECTED')
    # Persistent handles require a Complete audit from the same publication.
    # All returned handles were issued against authorized current bindings.
    runtime.audit.record(actor.user_ref,'restore','SUCCESS',len(turns) or len(results))
    return {'query':data.get('question',data['query']),'space_ids':data['space_ids'],
        **({'context':data['context']} if data.get('context') else {}),
        'restored':{'mode':'ask' if turns else 'search','search_mode':data.get('search_mode','STANDARD'),'turns':turns,'results':results}}

def remove(runtime,name):
    import frappe
    actor,_=current(runtime);owned(name,actor)
    frappe.delete_doc(DOCTYPE,name,ignore_permissions=True)
    return {'removed':True}


def list_feedback(runtime,page=1,page_size=12,status=None):
    """Employee-owned notes/status only; no source handles or maintenance queue."""
    import frappe
    from .reference_admin import _page_number
    page=_page_number(page,100000);page_size=_page_number(page_size,50)
    if status not in (None,'','Pending','In Review','Resolved'):raise KnowledgeError('INVALID_REQUEST')
    actor,_=current(runtime);out=[]
    filters={'owner_user':actor.user_ref,'kind':'Feedback'}
    if status:filters['status']=status
    rows=frappe.get_all(DOCTYPE,filters=filters,
        fields=['name','payload_json','status','creation','modified'],order_by='creation desc,name desc',limit_start=(page-1)*page_size,limit_page_length=page_size+1)
    for row in rows:
        if row.status not in ('Pending','In Review','Resolved'):raise KnowledgeError('SERVICE_ERROR')
        data=json.loads(row.payload_json)
        out.append({'id':row.name,'category':safe_string(data.get('category'),120),
            'note':safe_string(data.get('note',''),500),'status':row.status,
            'created_at':str(row.creation),'updated_at':str(row.modified)})
        if data.get('maintenance_reply'):
            out[-1]['reply']=safe_string(data['maintenance_reply'],500)
    final_actor,_=current(runtime)
    if final_actor!=actor:raise KnowledgeError('SCOPE_REJECTED')
    return {'items':out[:page_size],'page':page,'page_size':page_size,'has_more':len(rows)>page_size}

def _feedback_payload_text(row):
    raw=row['payload_json'] if isinstance(row,dict) else row.payload_json
    try:data=json.loads(raw)
    except (ValueError,TypeError):return None
    # Match the decoded JSON text so non-ASCII values (stored with
    # ensure_ascii=True by service_http.canonical) are searchable, while ASCII
    # keys/values keep the same substring semantics as the previous raw LIKE.
    return json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':'))

def feedback_queue(runtime,page=1,page_size=12,status=None,query=None):
    """Maintenance feedback queue. Optional page-bounded substring filter over
    the decoded stored feedback payload (read-only; same maintainer scope).

    payload_json is stored with ensure_ascii=True, so a SQL LIKE on the raw
    column cannot match non-ASCII input. The feedback queue is small and
    maintenance-scoped, so the filter scans at most MAX_SCAN rows in the stable
    creation order, decodes each payload and pages the exact matches. Output is
    still bounded to page_size items. scan_truncated is True only when the
    safety cap was reached before the whole queue could be examined.
    """
    import frappe
    from .maintenance_access import require
    require()
    from .reference_admin import _page_number
    page=_page_number(page,100000);page_size=_page_number(page_size,50)
    if status not in (None,'','Pending','In Review','Resolved'):raise KnowledgeError('INVALID_REQUEST')
    needle=None
    if query not in (None,''):
        if not isinstance(query,str):raise KnowledgeError('INVALID_REQUEST')
        needle=query.strip()
        if not 1<=len(needle)<=120:raise KnowledgeError('INVALID_REQUEST')
    filters={'kind':'Feedback'}
    if status:filters['status']=status
    fields=['name','payload_json','status','creation']
    order='creation desc,name desc'
    if needle is None:
        rows=frappe.get_all(DOCTYPE,filters=filters,fields=fields,order_by=order,
                            limit_start=(page-1)*page_size,limit_page_length=page_size+1)
        matches=None
    else:
        MAX_SCAN=5000;CHUNK=500;need=(page-1)*page_size+page_size+1
        matches=[];start=0
        while start<MAX_SCAN and len(matches)<need:
            batch=frappe.get_all(DOCTYPE,filters=filters,fields=fields,order_by=order,
                                 limit_start=start,limit_page_length=CHUNK)
            if not batch:break
            for row in batch:
                text=_feedback_payload_text(row)
                if text is not None and needle.casefold() in text.casefold():matches.append(row)
            start+=len(batch)
            if len(batch)<CHUNK:break
        scan_truncated=start>=MAX_SCAN and len(matches)<need
        rows=matches[(page-1)*page_size:(page-1)*page_size+page_size+1]
    items=[{'id':r['name'] if isinstance(r,dict) else r.name,'status':r['status'] if isinstance(r,dict) else r.status,
            'created_at':str(r['creation'] if isinstance(r,dict) else r.creation),**(json.loads(r['payload_json'] if isinstance(r,dict) else r.payload_json))}
           for r in rows[:page_size]]
    response={'items':items,'page':page,'page_size':page_size,'has_more':len(rows)>page_size}
    if matches is not None:response['scan_truncated']=scan_truncated
    return response

def review_feedback(runtime,name,status,reply=''):
    import frappe
    from .maintenance_access import require
    require()
    if status not in ('Pending','In Review','Resolved') or not frappe.db.exists(DOCTYPE,{'name':name,'kind':'Feedback'}):raise KnowledgeError('INVALID_REQUEST')
    rows=frappe.db.sql('SELECT payload_json FROM `tabHBOS Knowledge Activity` WHERE name=%s AND kind=%s FOR UPDATE',(name,'Feedback'),as_dict=True)
    if len(rows)!=1:raise KnowledgeError('INVALID_REQUEST')
    data=json.loads(rows[0]['payload_json'])
    data['maintenance_reply']=safe_string(reply,500)
    data['reviewer']=frappe.session.user
    frappe.db.set_value(DOCTYPE,name,{'status':status,'payload_json':canonical(data)})
    return {'id':name,'status':status}

def __principal(runtime):
    from .execution_plan import ServicePrincipal
    return ServicePrincipal(runtime.client,True)
