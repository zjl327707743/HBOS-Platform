"""Native user-owned logical activity; no originals, full text or durable excerpts."""
import json,secrets
from .errors import KnowledgeError
from .r1_contract import normalize_search
from .public_strings import safe_string
from .gateway import EvidenceRecord
from .service_http import canonical

DOCTYPE='HBOS Knowledge Activity'

def current(runtime):
    actor=runtime.actor();snapshot=runtime.provider._current(actor,runtime.client)
    return actor,{(b.canonical_document_id,b.version_id):b for b in snapshot.bindings}

def logical(records):
    return sorted({(r.binding.canonical_document_id,r.binding.version_id,r.binding.binding_ref,r.chunk_id) for r in records})

def write(kind,query,spaces,records,runtime,*,conversation_id=None,category=None,note=None):
    import frappe
    actor,_=current(runtime)
    safe_string(query,500)
    data={'query':query,'space_ids':list(spaces or []),'references':logical(records)}
    if conversation_id:data['conversation_id']=conversation_id
    if category:data.update(category=category,note=safe_string(note or '',500))
    if kind=='Bookmark':
        fingerprint=canonical(data)
        old=frappe.db.get_value(DOCTYPE,{'owner_user':actor.user_ref,'kind':kind,'payload_json':fingerprint},'name')
        if old:return old
    name=secrets.token_urlsafe(24)
    frappe.get_doc({'doctype':DOCTYPE,'activity_id':name,'owner_user':actor.user_ref,'kind':kind,
        'payload_json':canonical(data),'status':'Pending' if kind=='Feedback' else 'Saved',
        'publication_id':runtime.publication.publication_id if kind=='History' else ''}).insert(ignore_permissions=True)
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
