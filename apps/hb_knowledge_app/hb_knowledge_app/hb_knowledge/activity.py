"""Native user-owned activity, with bounded answer/preview snapshots for restoration."""
import hashlib,json,secrets
from .errors import KnowledgeError
from .r1_contract import normalize_search
from .public_strings import safe_string
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
          answer=None,labels=None,question=None,search_mode='STANDARD'):
    import frappe
    actor,_=current(runtime)
    safe_string(query,500)
    data={'query':query,'space_ids':sorted(set(spaces or [])),'references':logical(records)}
    if kind in ('History','Bookmark'):
        # Only the finite previews already authorized for this response. Never
        # store native full chunks, files, service tokens or evidence handles.
        data['previews']=[{'reference':[r.binding.canonical_document_id,r.binding.version_id,r.binding.binding_ref,r.chunk_id],
                          'excerpt':safe_string(r.excerpt,500),'page_number':r.page_number} for r in records]
        if len(data['previews'])>5:raise KnowledgeError('INVALID_REQUEST')
        data['search_mode']=search_mode
    if answer is not None:
        data['answer']=safe_string(answer,2000)
        data['labels']=list(labels or [])
        data['question']=safe_string(question or query,500)
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

def bindings_for(data,mapping):
    selected=[]
    for document,version,reference,chunk in data['references']:
        b=mapping.get((document,version))
        if not b or b.binding_ref!=reference:raise KnowledgeError('EVIDENCE_UNAVAILABLE')
        selected.append(b)
    return selected

def list_activity(runtime,kind):
    import frappe
    if kind not in ('History','Bookmark'):raise KnowledgeError('INVALID_REQUEST')
    actor,mapping=current(runtime)
    rows=frappe.get_all(DOCTYPE,filters={'owner_user':actor.user_ref,'kind':kind},fields=['name','payload_json','creation','publication_id'],order_by='creation desc',limit_page_length=30)
    def project(current_mapping):
        out=[]
        for row in rows:
            if row.publication_id and not frappe.db.exists('HBOS Knowledge Audit',{'publication_id':row.publication_id,'publication_state':'Complete'}):continue
            data=json.loads(row.payload_json)
            try:
                bindings=bindings_for(data,current_mapping);available=True
            except KnowledgeError:bindings=[];available=False
            out.append({'id':row.name,'query':safe_string(data.get('question',data['query']),500),'created_at':str(row.creation),
                'available':available,'titles':[safe_string(b.title,240,nullable=True) for b in bindings]})
        return out
    out=project(mapping)
    final_actor,final_mapping=current(runtime)
    if final_actor!=actor or out!=project(final_mapping):raise KnowledgeError('SCOPE_REJECTED')
    return {'items':out}

def reopen(runtime,name,request_id):
    actor,mapping=current(runtime);row,data=owned(name,actor)
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

def restore(runtime,row,data,actor,mapping,request_id):
    """A fresh session gets fresh handles only after present source authorization.

    Opening a saved conversation does no vector search and no model generation.
    A missing/changed publication fails closed before restoring its answer.
    """
    from .evidence import issue_evidence
    from knowledge_service.hbos_gateway.response_projection import public_evidence
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
    for _,item in chain:bindings_for(item,mapping)
    turns=[];results=[]
    for index,(turn,item) in enumerate(chain):
        request=normalize_search({'query':item['query'],**({'space_ids':item['space_ids']} if item['space_ids'] else {}),
            **({'context':item['context']} if item.get('context') else {}),'search_mode':item.get('search_mode','STANDARD')})
        ticket=runtime.decisions.issue(actor,runtime.client,'knowledge.search',request,request_id+'_'+str(index))
        runtime.publication.plan=ticket.plan
        previews=item['previews'];records=[]
        if not isinstance(previews,list) or len(previews)>5:raise KnowledgeError('EVIDENCE_UNAVAILABLE')
        for preview in previews:
            document,version,reference,chunk=preview['reference'];b=mapping.get((document,version))
            if not b or b.binding_ref!=reference:raise KnowledgeError('EVIDENCE_UNAVAILABLE')
            records.append(EvidenceRecord(document,b.title,b.business_version,'内部参考／有效性待核',b.section,
                preview['page_number'],safe_string(preview['excerpt'],500),chunk,b.dataset_alias,b.space_id,b.version_id,reference,b))
        if records:
            runtime.decisions.online(__principal(runtime),ticket.call('introspect','introspect'))
            runtime.gateway.authorize_evidence(ticket,records,phase='evidence_read')
        runtime.provider.revalidate(ticket.plan)
        runtime.quota.reserve_output(actor.user_ref,sum(len(r.excerpt) for r in records)+len(item.get('answer','')))
        output=[public_evidence(r,issue_evidence(runtime.cache,ticket,r,runtime=runtime),environment=runtime.profile) for r in records]
        if 'answer' in item:
            labels=item.get('labels',[])
            if len(labels)!=len(output):raise KnowledgeError('EVIDENCE_UNAVAILABLE')
            citations=[dict(source,citation_label=label) for source,label in zip(output,labels)]
            turns.append({'request_id':request_id,'turn_id':turn,'conversation_id':turn,'mode':'internal_reference_generation' if citations else 'authorized_generation',
                'answer_status':'REFERENCE_ANSWERED' if citations else 'INSUFFICIENT_EVIDENCE','answerable':bool(citations),
                'answer':item['answer'],'citations':citations,'question':item.get('question',item['query'])})
        else:results=output
        runtime.decisions.online(__principal(runtime),ticket.call('revalidate','final_publish'))
    final_actor,final_mapping=current(runtime)
    if final_actor!=actor:raise KnowledgeError('SCOPE_REJECTED')
    for _,item in chain:bindings_for(item,final_mapping)
    # Persistent handles require a Complete audit from the same publication.
    # Restoring issues fresh handles without doing a new search/model call.
    runtime.audit.record(actor.user_ref,'restore','SUCCESS',len(turns) or len(results))
    return {'query':data.get('question',data['query']),'space_ids':data['space_ids'],
        **({'context':data['context']} if data.get('context') else {}),
        'restored':{'mode':'ask' if turns else 'search','search_mode':data.get('search_mode','STANDARD'),'turns':turns,'results':results}}

def remove(runtime,name):
    import frappe
    actor,_=current(runtime);owned(name,actor)
    frappe.delete_doc(DOCTYPE,name,ignore_permissions=True)
    return {'removed':True}


def list_feedback(runtime):
    """Employee-owned notes/status only; no source handles or maintenance queue."""
    import frappe
    actor,_=current(runtime);out=[]
    rows=frappe.get_all(DOCTYPE,filters={'owner_user':actor.user_ref,'kind':'Feedback'},
        fields=['name','payload_json','status','creation','modified'],order_by='creation desc',limit_page_length=100)
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
    return {'items':out}

def feedback_queue(runtime):
    import frappe
    from .maintenance_access import require
    require()
    rows=frappe.get_all(DOCTYPE,filters={'kind':'Feedback'},fields=['name','payload_json','status','creation'],order_by='creation desc',limit_page_length=100)
    return {'items':[{'id':r.name,'status':r.status,'created_at':str(r.creation),**json.loads(r.payload_json)} for r in rows]}

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
