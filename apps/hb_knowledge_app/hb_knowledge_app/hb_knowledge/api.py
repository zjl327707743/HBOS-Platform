from __future__ import annotations
import secrets
import frappe
from .errors import KnowledgeError, error_payload
from .r1_contract import normalize_search, normalize_evidence, validate_structure
from .runtime import load_runtime
from .gateway import load_gateway_client
from .execution_plan import ServicePrincipal
from .evidence import issue_evidence, resolve_evidence as resolve_cached_evidence

_UNSET=object()

def _private_no_store():
    frappe.local.response_headers["Cache-Control"]="private, no-store, max-age=0"
    frappe.local.response_headers["Pragma"]="no-cache"

def _run(action):
    _private_no_store()
    request_id=secrets.token_urlsafe(18)
    try:
        request=getattr(frappe.local,"request",None)
        retry=request.headers.get("X-HBOS-Request-ID") if request else None
        if retry is not None:
            if not isinstance(retry,str) or not 8<=len(retry)<=128:
                raise KnowledgeError("INVALID_REQUEST")
            request_id=retry
        data=action(request_id)
        runtime=getattr(frappe.local,"hbos_knowledge_runtime",None)
        publication=getattr(runtime,"publication",None)
        if publication: publication.finish()
        return {"ok":True,"data":data}
    except KnowledgeError as error:
        _abort_publication()
        return error_payload(error,request_id)
    except Exception:
        _abort_publication()
        # Do not log traceback/arguments/remote exception. The safe audit port has no text channel.
        return error_payload(KnowledgeError("SERVICE_ERROR"),request_id)

def _abort_publication():
    publication=getattr(getattr(frappe.local,"hbos_knowledge_runtime",None),"publication",None)
    if publication: publication.abort()

def _framework_business(fields, method):
    fields=dict(fields)
    cmd=fields.pop("cmd",None)
    if cmd is not None and cmd!="hb_knowledge_app.hb_knowledge.api."+method:
        raise KnowledgeError("INVALID_REQUEST")
    # Frappe validates Session/CSRF BEFORE invoking a whitelisted method. This is
    # its reserved form field, not an identity/business field. Header flow unchanged.
    fields.pop("csrf_token",None)
    return fields

def _can_search(runtime,actor):
    try:
        runtime.provider.evaluate(actor,runtime.client,"knowledge.search",normalize_search({"query":"STATUS_LOOKUP"}),"STATUS_LOOKUP")
        return runtime.gateway.configured
    except KnowledgeError as error:
        if error.code in {"EMPTY_SCOPE","SCOPE_REJECTED"}: return False
        raise

def _availability(runtime,*,diagnostics=False):
    from knowledge_service.hbos_gateway.availability import unknown, PUBLIC_FIELDS
    fallback=unknown(runtime.gateway.configured)
    read=getattr(runtime.gateway,'availability',None)
    if not callable(read):return fallback
    try:
        value=read(diagnostics=diagnostics)
        if not isinstance(value,dict) or not PUBLIC_FIELDS.issubset(value):return fallback
        if value['status'] not in {'AVAILABLE','UNKNOWN','OBSERVED_ERROR','NOT_CONFIGURED'}:return fallback
        if value['observed_error'] not in {None,'UPSTREAM_UNAVAILABLE'}:return fallback
        if value['budget_status'] not in {'UNKNOWN','READY','ACCOUNTING_PENDING','EXPIRED','EXHAUSTED','UNAVAILABLE'}:return fallback
        # The signed service is trusted for the fixed projection, never raw errors.
        return value if diagnostics else {k:value[k] for k in PUBLIC_FIELDS}
    except KnowledgeError:return fallback

@frappe.whitelist(methods=["GET"])
def get_status():
    def current(request_id):
        runtime=load_runtime()
        actor=runtime.actor()
        return {"can_enter":bool(actor.enabled),"can_search":_can_search(runtime,actor),
                "policy_revision":None,"gateway_configured":runtime.gateway.configured,
                "ask_enabled":_ask_enabled(runtime),"mode":"retrieval","environment":runtime.profile,
                "retrieval_availability":_availability(runtime)}
    return _run(current)

@frappe.whitelist(methods=['GET'])
def get_retrieval_diagnostics(**business_fields):
    def current(request_id):
        if _framework_business(business_fields,'get_retrieval_diagnostics'):raise KnowledgeError('INVALID_REQUEST')
        runtime=load_runtime();actor=runtime.actor()
        if not actor.enabled or 'System Manager' not in frappe.get_roles(actor.user_ref):
            raise KnowledgeError('SCOPE_REJECTED')
        return _availability(runtime,diagnostics=True)
    return _run(current)

@frappe.whitelist(methods=["POST"])
def search(query=None, limit=_UNSET, equipment_id=_UNSET, asset_id=_UNSET, component_id=_UNSET,
           context=_UNSET, space_ids=_UNSET, **business_fields):
    def current(request_id):
        raw=_framework_business(business_fields,"search")
        raw["query"]=query
        if limit is not _UNSET: raw["limit"]=limit
        for key,value in (("equipment_id",equipment_id),("asset_id",asset_id),("component_id",component_id),
                          ("context",context),("space_ids",space_ids)):
            if value is not _UNSET: raw[key]=value
        request=normalize_search(raw,legacy=True)
        runtime=load_runtime(); actor=runtime.actor()
        ticket=runtime.decisions.issue(actor,runtime.client,"knowledge.search",request,request_id)
        if getattr(runtime,"publication",None): runtime.publication.plan=ticket.plan
        records=load_gateway_client().search(ticket=ticket)
        runtime.checkpoint("before_evidence_issue")
        if records:
            runtime.gateway.authorize_evidence(ticket,records,phase="pre_issue")
        runtime.provider.revalidate(ticket.plan)
        output=[]
        # Entire response quota reserved by HBOS once; Gateway never double charges.
        runtime.quota.reserve_output(actor.user_ref,sum(len(r.excerpt) for r in records))
        from knowledge_service.hbos_gateway.response_projection import public_evidence
        for record in records:
            evidence_id=issue_evidence(runtime.cache,ticket,record,runtime=runtime)
            output.append(public_evidence(record,evidence_id,environment=runtime.profile))
        runtime.checkpoint("before_search_publication")
        runtime.decisions.online(ServicePrincipal(runtime.client,True),ticket.call("revalidate","final_publish"))
        data={"request_id":request_id,"mode":"retrieval","results":output}
        if request.context: data["context"]=dict(request.context)
        validate_structure("SearchData",data)
        if runtime.profile=="production":
            from .activity import write
            write("History",request.query,request.space_ids,records,runtime,context=request.context)
        runtime.audit.record(actor.user_ref,"search","SUCCESS",len(output))
        return data
    return _run(current)

@frappe.whitelist(methods=["GET"])
def get_spaces(**business_fields):
    def current(request_id):
        if _framework_business(business_fields, 'get_spaces'):
            raise KnowledgeError('INVALID_REQUEST')
        from .spaces import list_spaces
        runtime=load_runtime()
        return list_spaces(runtime, runtime.actor())
    return _run(current)

@frappe.whitelist(methods=["POST"])
def resolve_evidence(evidence_id=None, **business_fields):
    def current(request_id):
        raw=_framework_business(business_fields,"resolve_evidence")
        raw["evidence_id"]=evidence_id
        value=normalize_evidence(raw)
        runtime=load_runtime(); actor=runtime.actor()
        record,ticket=resolve_cached_evidence(runtime.cache,actor,runtime.client,value,
                                             runtime=runtime,request_id=request_id)
        if getattr(runtime,"publication",None): runtime.publication.plan=ticket.plan
        from knowledge_service.hbos_gateway.response_projection import public_evidence
        data=public_evidence(record,value,environment=runtime.profile)
        runtime.quota.reserve_output(actor.user_ref,len(record.excerpt))
        # Actual consumer final check, after projection/quota and before return.
        runtime.checkpoint("before_resolve_return")
        runtime.decisions.online(ServicePrincipal(runtime.client,True),ticket.call("revalidate","final_publish"))
        runtime.audit.record(actor.user_ref,"evidence","SUCCESS",1)
        return data
    return _run(current)

def _ask_enabled(runtime):
    if runtime.profile!='production':return False
    from .shared_reference import configuration
    return configuration().get('ask_enabled') is True

@frappe.whitelist(methods=['POST'])
def ask(**business_fields):
    def current(request_id):
        raw=_framework_business(business_fields,'ask');validate_structure('AskRequest',raw)
        runtime=load_runtime();actor=runtime.actor()
        if not _ask_enabled(runtime):raise KnowledgeError('MODEL_NOT_APPROVED')
        from .activity import owned,current as activity_current,bindings_for,write
        from .public_strings import safe_string
        question=safe_string(raw['question'].strip(),500)
        if raw.get('conversation_id'):
            _,mapping=activity_current(runtime)
            _,previous=owned(raw['conversation_id'],actor,kinds=('History',))
            bindings_for(previous,mapping)
            requested=normalize_search({'query':question,**{k:v for k,v in raw.items() if k in ('space_ids','context')}})
            from .followup import validate_followup_scope
            validate_followup_scope(previous,requested.space_ids,requested.context)
            from .followup import followup_query, UNRESOLVED_FOLLOWUP
            followup=followup_query(previous['query'],question)
            if followup is None:
                # We do not persist answer structure or copy old answer text as facts.
                # Ownership and current versions above are still mandatory.
                request=normalize_search({'query':question,**{k:v for k,v in raw.items() if k in ('space_ids','context')}})
                ticket=runtime.decisions.issue(actor,runtime.client,'knowledge.search',request,request_id)
                runtime.publication.plan=ticket.plan
                runtime.quota.reserve_output(actor.user_ref,len(UNRESOLVED_FOLLOWUP))
                turn=write('History',question,request.space_ids,[],runtime,conversation_id=raw['conversation_id'],context=request.context)
                activity_current(runtime)
                runtime.audit.record(actor.user_ref,'ask','INSUFFICIENT_EVIDENCE',0)
                return {'request_id':request_id,'turn_id':turn,'conversation_id':turn,'mode':'authorized_generation',
                        'answer_status':'INSUFFICIENT_EVIDENCE','answerable':False,
                        'answer':UNRESOLVED_FOLLOWUP,'citations':[]}
            question=followup
        request=normalize_search({'query':question,**{k:v for k,v in raw.items() if k in ('space_ids','context')}})
        ticket=runtime.decisions.issue(actor,runtime.client,'knowledge.search',request,request_id)
        runtime.publication.plan=ticket.plan
        answer,labels,records=runtime.gateway.ask(ticket=ticket)
        if records:runtime.gateway.authorize_evidence(ticket,records,phase='pre_issue')
        runtime.provider.revalidate(ticket.plan)
        from knowledge_service.hbos_gateway.response_projection import public_evidence
        citations=[]
        runtime.quota.reserve_output(actor.user_ref,len(answer)+sum(len(r.excerpt) for r in records))
        for label,record in zip(labels,records):
            handle=issue_evidence(runtime.cache,ticket,record,runtime=runtime)
            citations.append(dict(public_evidence(record,handle,environment=runtime.profile),citation_label=label))
        from .r1_contract import validate_ask_data
        data={'request_id':request_id,'turn_id':request_id,'mode':'internal_reference_generation',
            'answer_status':'REFERENCE_ANSWERED' if citations else 'INSUFFICIENT_EVIDENCE',
            'answerable':bool(citations),'answer':answer,'citations':citations}
        if not citations:data['mode']='authorized_generation'
        validate_ask_data(data,environment=runtime.profile)
        turn=write('History',request.query,request.space_ids,records,runtime,conversation_id=raw.get('conversation_id'),context=request.context)
        data['turn_id']=turn;data['conversation_id']=turn
        runtime.decisions.online(ServicePrincipal(runtime.client,True),ticket.call('revalidate','final_publish'))
        runtime.audit.record(actor.user_ref,'ask','SUCCESS',len(citations))
        return data
    return _run(current)


@frappe.whitelist(methods=["GET"])
def get_documents(**business_fields):
    def current(request_id):
        if _framework_business(business_fields,'get_documents'):raise KnowledgeError('INVALID_REQUEST')
        from .reference_admin import get_catalog
        runtime=load_runtime();return get_catalog(runtime,runtime.actor())
    return _run(current)


@frappe.whitelist(methods=['GET'])
def get_documents_page(query=None,space_id=None,page=1,page_size=12,**business_fields):
    def current(request_id):
        if _framework_business(business_fields,'get_documents_page'):raise KnowledgeError('INVALID_REQUEST')
        from .reference_admin import get_catalog_page
        runtime=load_runtime()
        return get_catalog_page(runtime,runtime.actor(),query=query,space_id=space_id,page=page,page_size=page_size)
    return _run(current)

@frappe.whitelist(methods=['GET'])
def get_activity(kind=None,**business_fields):
    def current(request_id):
        if _framework_business(business_fields,'get_activity'):raise KnowledgeError('INVALID_REQUEST')
        from .activity import list_activity
        return list_activity(load_runtime(),kind)
    return _run(current)


@frappe.whitelist(methods=['GET'])
def get_feedback(**business_fields):
    def current(request_id):
        if _framework_business(business_fields,'get_feedback'):raise KnowledgeError('INVALID_REQUEST')
        from .activity import list_feedback
        return list_feedback(load_runtime())
    return _run(current)

@frappe.whitelist(methods=['POST'])
def open_saved(activity_id=None,**business_fields):
    def current(request_id):
        if _framework_business(business_fields,'open_saved'):raise KnowledgeError('INVALID_REQUEST')
        from .activity import reopen
        return reopen(load_runtime(),activity_id,request_id)
    return _run(current)

@frappe.whitelist(methods=['POST'])
def remove_saved(activity_id=None,**business_fields):
    def current(request_id):
        if _framework_business(business_fields,'remove_saved'):raise KnowledgeError('INVALID_REQUEST')
        from .activity import remove
        return remove(load_runtime(),activity_id)
    return _run(current)

@frappe.whitelist(methods=['POST'])
def save_bookmark(evidence_id=None,query=None,**business_fields):
    def current(request_id):
        if _framework_business(business_fields,'save_bookmark'):raise KnowledgeError('INVALID_REQUEST')
        runtime=load_runtime();actor=runtime.actor()
        record,ticket=resolve_cached_evidence(runtime.cache,actor,runtime.client,normalize_evidence({'evidence_id':evidence_id}),runtime=runtime,request_id=request_id)
        from .activity import write
        return {'id':write('Bookmark',normalize_search({'query':query}).query,[record.space_id],[record],runtime)}
    return _run(current)

@frappe.whitelist(methods=['POST'])
def submit_feedback(evidence_id=None,category=None,note='',**business_fields):
    def current(request_id):
        if _framework_business(business_fields,'submit_feedback') or category not in ('内容疑问','版本疑问','检索不相关','其他'):raise KnowledgeError('INVALID_REQUEST')
        runtime=load_runtime();actor=runtime.actor();records=[]
        if evidence_id:
            record,ticket=resolve_cached_evidence(runtime.cache,actor,runtime.client,normalize_evidence({'evidence_id':evidence_id}),runtime=runtime,request_id=request_id)
            records=[record]
        from .activity import write
        return {'id':write('Feedback','反馈',[],records,runtime,category=category,note=note),'status':'Pending'}
    return _run(current)

@frappe.whitelist(methods=['GET'])
def get_feedback_queue(**business_fields):
    def current(request_id):
        if _framework_business(business_fields,'get_feedback_queue'):raise KnowledgeError('INVALID_REQUEST')
        from .activity import feedback_queue
        return feedback_queue(load_runtime())
    return _run(current)

@frappe.whitelist(methods=['POST'])
def review_feedback(activity_id=None,status=None,**business_fields):
    def current(request_id):
        if _framework_business(business_fields,'review_feedback'):raise KnowledgeError('INVALID_REQUEST')
        from .activity import review_feedback as update
        return update(load_runtime(),activity_id,status)
    return _run(current)
