"""Native user-owned logical activity; no originals, full text or durable excerpts."""
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

def write(kind,query,spaces,records,runtime,*,conversation_id=None,category=None,note=None,context=None):
    import frappe
    actor,_=current(runtime)
    safe_string(query,500)
    data={'query':query,'space_ids':sorted(set(spaces or [])),'references':logical(records)}
    if context:data['context']=dict(context)
    if conversation_id:data['conversation_id']=conversation_id
    if category:data.update(category=category,note=safe_string(note or '',500))
    if kind=='Bookmark':
        fingerprint=canonical(data)
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
            if len(found)!=1 or found[0]['payload_json']!=fingerprint:raise KnowledgeError('SERVICE_ERROR')
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
            if len(found)!=1 or found[0]['payload_json']!=fingerprint:raise KnowledgeError('SERVICE_ERROR')
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
    actor,mapping=current(runtime);out=[]
    rows=frappe.get_all(DOCTYPE,filters={'owner_user':actor.user_ref,'kind':kind},fields=['name','payload_json','creation','publication_id'],order_by='creation desc',limit_page_length=30)
    for row in rows:
        if row.publication_id and not frappe.db.exists('HBOS Knowledge Audit',{'publication_id':row.publication_id,'publication_state':'Complete'}):continue
        data=json.loads(row.payload_json)
        try:
            bindings=bindings_for(data,mapping);available=True
        except KnowledgeError:bindings=[];available=False
        out.append({'id':row.name,'query':safe_string(data['query'],500),'created_at':str(row.creation),
            'available':available,'titles':[safe_string(b.title,240,nullable=True) for b in bindings]})
    current(runtime)  # Native eligibility is read again immediately before return.
    return {'items':out}

def reopen(runtime,name,request_id):
    actor,mapping=current(runtime);_,data=owned(name,actor)
    bindings=bindings_for(data,mapping)
    request=normalize_search({'query':data['query'],**({'space_ids':data['space_ids']} if data['space_ids'] else {})})
    ticket=runtime.decisions.issue(actor,runtime.client,'knowledge.search',request,request_id)
    # Revalidate native RAGFlow metadata, not only the saved title or HBOS cache.
    records=[EvidenceRecord(b.canonical_document_id,b.title,b.business_version,None,b.section,None,'',reference[3],b.dataset_alias,b.space_id,b.version_id,b.binding_ref,b) for b,reference in zip(bindings,data['references'])]
    if records:
        runtime.decisions.online(__principal(runtime),ticket.call('introspect','introspect'))
        runtime.gateway.authorize_evidence(ticket,records,phase='evidence_read')
    runtime.provider.revalidate(ticket.plan)
    return {'query':data['query'],'space_ids':data['space_ids']}

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
    final_actor,_=current(runtime)
    if final_actor!=actor:raise KnowledgeError('SCOPE_REJECTED')
    return {'items':out}

def feedback_queue(runtime):
    import frappe
    # Maintenance uses the native Frappe System Manager gate. Privileged users
    # remain excluded from the ordinary employee Portal and knowledge scope.
    frappe.only_for('System Manager')
    if not frappe.db.get_value('User',frappe.session.user,'enabled'):raise KnowledgeError('AUTHENTICATION_REQUIRED')
    rows=frappe.get_all(DOCTYPE,filters={'kind':'Feedback'},fields=['name','payload_json','status','creation'],order_by='creation desc',limit_page_length=100)
    return {'items':[{'id':r.name,'status':r.status,'created_at':str(r.creation),**json.loads(r.payload_json)} for r in rows]}

def review_feedback(runtime,name,status):
    import frappe
    # Maintenance uses the native Frappe System Manager gate. Privileged users
    # remain excluded from the ordinary employee Portal and knowledge scope.
    frappe.only_for('System Manager')
    if not frappe.db.get_value('User',frappe.session.user,'enabled'):raise KnowledgeError('AUTHENTICATION_REQUIRED')
    if status not in ('Pending','In Review','Resolved') or not frappe.db.exists(DOCTYPE,{'name':name,'kind':'Feedback'}):raise KnowledgeError('INVALID_REQUEST')
    frappe.db.set_value(DOCTYPE,name,'status',status)
    return {'id':name,'status':status}

def __principal(runtime):
    from .execution_plan import ServicePrincipal
    return ServicePrincipal(runtime.client,True)
