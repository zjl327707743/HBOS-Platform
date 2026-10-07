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

@frappe.whitelist(methods=["GET"])
def get_status():
    def current(request_id):
        runtime=load_runtime()
        actor=runtime.actor()
        return {"can_enter":bool(actor.enabled),"can_search":_can_search(runtime,actor),
                "policy_revision":None,"gateway_configured":runtime.gateway.configured,
                "ask_enabled":False,"mode":"retrieval","environment":runtime.profile}
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

@frappe.whitelist(methods=["POST"])
def ask(**business_fields):
    def current(request_id):
        raw=_framework_business(business_fields,"ask")
        validate_structure("AskRequest",raw)
        runtime=load_runtime(); actor=runtime.actor()
        runtime.provider._current(actor,runtime.client)
        return _disabled()
    return _run(current)

def _disabled():
    raise KnowledgeError("MODEL_NOT_APPROVED")
