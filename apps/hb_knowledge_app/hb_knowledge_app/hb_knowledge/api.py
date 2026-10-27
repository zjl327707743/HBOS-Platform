from __future__ import annotations
import hashlib,json,logging
import secrets,re
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

def _omit_diagnostic(request_id,omitted,total,documents):
    """Private metadata only: counts, reason and hashed logical document ids.

    Never logs the excerpt, a title, a physical id or an upstream detail.
    """
    if type(omitted) is not int or omitted<=0:return
    safe_request=request_id if isinstance(request_id,str) and re.fullmatch(r'[A-Za-z0-9_-]{1,128}',request_id) else 'UNAVAILABLE'
    document_hashes=sorted({hashlib.sha256(str(value).encode()).hexdigest()
                            for value in documents if isinstance(value,str)})[:5]
    row={'event':'SEARCH_RESULT_OMITTED','request_id':safe_request,
         'reason':'CONTENT_SAFETY_REJECTED','omitted':omitted,'total':total,
         'document_sha256':document_hashes}
    logging.getLogger('hbos.knowledge.source_diagnostics').warning(json.dumps(row,sort_keys=True))
    try:
        from knowledge_service.hbos_gateway.diagnostics import persist_diagnostic
        persist_diagnostic({'stage':'SEARCH_RESULT_OMITTED','request_id':safe_request,
            'reason':'CONTENT_SAFETY_REJECTED','counts':{'omitted':omitted,'total':total},
            'document_hashes':document_hashes})
    except Exception:
        # Diagnostics are best-effort; the search result is unaffected.
        pass

def _run(action):
    _private_no_store()
    request_id=secrets.token_urlsafe(18)
    try:
        request=getattr(frappe.local,"request",None)
        retry=request.headers.get("X-HBOS-Request-ID") if request else None
        if retry is not None:
            if not isinstance(retry,str) or not 8<=len(retry)<=128 or not re.fullmatch(r'[A-Za-z0-9_-]+',retry):
                raise KnowledgeError("INVALID_REQUEST")
            request_id=retry
        frappe.local.hbos_knowledge_request_id=request_id
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
    # Frappe forwards the dispatched method path as ``cmd``. The maintenance
    # batch module ships its own whitelisted entry points, so the guard must
    # accept any module inside this app whose final segment is exactly the
    # called method, not only the historical ``api.`` prefix.
    if cmd is not None:
        if (not isinstance(cmd,str)
                or not cmd.startswith('hb_knowledge_app.hb_knowledge.')
                or not cmd.endswith('.'+method)):
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
    # Financial facts belong to the role-protected diagnostic endpoint. Older
    # Portal clients treat these codes as hard stops even when blocked=False.
    employee_fields=PUBLIC_FIELDS-{'budget_status'}
    fallback=unknown(runtime.gateway.configured)
    if not diagnostics:fallback={k:fallback[k] for k in employee_fields}
    read=getattr(runtime.gateway,'availability',None)
    if not callable(read):return fallback
    try:
        value=read(diagnostics=diagnostics)
        if not isinstance(value,dict) or not PUBLIC_FIELDS.issubset(value):return fallback
        if value['status'] not in {'AVAILABLE','UNKNOWN','OBSERVED_ERROR','NOT_CONFIGURED'}:return fallback
        if value['observed_error'] not in {None,'UPSTREAM_UNAVAILABLE'}:return fallback
        if value['budget_status'] not in {'UNKNOWN','READY','ACCOUNTING_PENDING','EXPIRED','EXHAUSTED','UNAVAILABLE'}:return fallback
        # The signed service is trusted for the fixed projection, never raw errors.
        return value if diagnostics else {k:value[k] for k in employee_fields}
    except KnowledgeError:return fallback

@frappe.whitelist(methods=["GET"])
def get_status():
    def current(request_id):
        runtime=load_runtime()
        actor=runtime.actor()
        from .maintenance_access import permitted
        answer_status=runtime.gateway.answer_status() if hasattr(runtime.gateway,'answer_status') else {'configured':False,'available':False,'budget_status':'UNAVAILABLE'}
        return {"can_enter":bool(actor.enabled),"can_search":_can_search(runtime,actor),
                "policy_revision":None,"gateway_configured":runtime.gateway.configured,
                "ask_enabled":_ask_enabled(runtime),"can_maintain":permitted(),"mode":"retrieval","environment":runtime.profile,
                "answer_availability":{k:answer_status[k] for k in ('configured','available')},
                "retrieval_availability":_availability(runtime),
                **({'model_catalog':_personal_models(runtime,actor)} if hasattr(runtime.gateway,'models') else {})}
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
           context=_UNSET, space_ids=_UNSET, search_mode=_UNSET, **business_fields):
    def current(request_id):
        phase,flush=_ask_marks(request_id)
        try:
            return _search_current(business_fields,query,limit,equipment_id,asset_id,component_id,
                                   context,space_ids,search_mode,request_id,phase)
        finally:
            flush()

    def _search_current(business_fields,query,limit,equipment_id,asset_id,component_id,
                        context,space_ids,search_mode,request_id,phase):
        raw=_framework_business(business_fields,"search")
        raw["query"]=query
        if limit is not _UNSET: raw["limit"]=limit
        for key,value in (("equipment_id",equipment_id),("asset_id",asset_id),("component_id",component_id),
                          ("context",context),("space_ids",space_ids),("search_mode",search_mode)):
            if value is not _UNSET: raw[key]=value
        with phase('normalize_search'):
            request=normalize_search(raw,legacy=True)
        with phase('load_runtime_actor'):
            runtime=load_runtime(); actor=runtime.actor()
        # Caller attribution is derived from the authenticated server connection.
        # Browsers cannot nominate another caller or a model for retrieval.
        if any(k in raw for k in ('model_alias','knowledge_only','answer_caller')):
            raise KnowledgeError('INVALID_REQUEST')
        from dataclasses import replace
        request=replace(request,answer_caller='MCP' if getattr(frappe.local,'hbos_mcp_connection',None) else 'PORTAL')
        with phase('plan_issue'):
            ticket=runtime.decisions.issue(actor,runtime.client,"knowledge.search",request,request_id)
        if getattr(runtime,"publication",None): runtime.publication.plan=ticket.plan
        with phase('service_search'):
            records=load_gateway_client().search(ticket=ticket)
        runtime.checkpoint("before_evidence_issue")
        with phase('authorize_evidence'):
            if records:
                runtime.gateway.authorize_evidence(ticket,records,phase="pre_issue")
        with phase('provider_revalidate'):
            runtime.provider.revalidate(ticket.plan)
        from knowledge_service.hbos_gateway.response_projection import public_evidence
        # Per-record projection isolation (RC13 b07 defect): one authorized
        # excerpt that cannot be displayed safely is skipped and counted; it
        # must not fail the other returned sources. ONLY the content-hygiene
        # rejection is isolated - scope, currency, revocation and protocol
        # errors still abort the whole search in the same phase.
        safe_records=[]; omitted=0; omitted_documents=[]
        for record in records:
            try:
                public_evidence(record,"PROJECTION_GATE",environment=runtime.profile)
            except KnowledgeError as error:
                if error.code!="UPSTREAM_INVALID_RESULT":raise
                omitted+=1;omitted_documents.append(record.binding.canonical_document_id)
                continue
            safe_records.append(record)
        if records and not safe_records:
            _omit_diagnostic(request_id,omitted,len(records),omitted_documents)
            raise KnowledgeError("SOURCE_CONTENT_UNSAFE")
        output=[]; issued_records=[]
        # Entire response quota reserved by HBOS once; Gateway never double charges.
        runtime.quota.reserve_output(actor.user_ref,sum(len(r.excerpt) for r in safe_records))
        with phase('issue_evidence'):
            for record in safe_records:
                try:
                    evidence_id=issue_evidence(runtime.cache,ticket,record,runtime=runtime)
                    card=public_evidence(record,evidence_id,environment=runtime.profile)
                except KnowledgeError as error:
                    if error.code!="UPSTREAM_INVALID_RESULT":raise
                    omitted+=1;omitted_documents.append(record.binding.canonical_document_id)
                    continue
                output.append(card);issued_records.append(record)
        if records and not output:
            _omit_diagnostic(request_id,omitted,len(records),omitted_documents)
            raise KnowledgeError("SOURCE_CONTENT_UNSAFE")
        if omitted:_omit_diagnostic(request_id,omitted,len(records),omitted_documents)
        runtime.checkpoint("before_search_publication")
        with phase('final_online'):
            runtime.decisions.online(ServicePrincipal(runtime.client,True),ticket.call("revalidate","final_publish"))
        data={"request_id":request_id,"mode":"retrieval","search_mode":request.search_mode,"results":output}
        if omitted: data["omitted_results"]=omitted
        if request.context: data["context"]=dict(request.context)
        validate_structure("SearchData",data)
        if runtime.profile=="production":
            from .activity import write
            write("History",request.query,request.space_ids,issued_records,runtime,context=request.context,search_mode=request.search_mode)
        runtime.audit.record(actor.user_ref,"search","SUCCESS",len(output))
        return data
    return _run(current)

@frappe.whitelist(methods=["POST"])
def document_capabilities(document_id=None, version_id=None, **business_fields):
    def current(request_id):
        if _framework_business(business_fields, 'document_capabilities'):
            raise KnowledgeError('INVALID_REQUEST')
        runtime = load_runtime()
        return runtime.delivery.capabilities(document_id, version_id, request_id)
    return _run(current)


@frappe.whitelist(methods=["POST"])
def create_document_delivery(document_id=None, version_id=None, purpose=None, **business_fields):
    def current(request_id):
        if _framework_business(business_fields, 'create_document_delivery'):
            raise KnowledgeError('INVALID_REQUEST')
        runtime = load_runtime()
        return runtime.delivery.prepare(document_id, version_id, purpose, request_id)
    return _run(current)


@frappe.whitelist(methods=["GET"])
def document_content(ticket=None, **business_fields):
    """A native-session binary endpoint; every range reauthorizes the ticket."""
    from werkzeug.wrappers import Response
    request_id = secrets.token_urlsafe(18)
    _private_no_store()
    try:
        if _framework_business(business_fields, 'document_content'):
            raise KnowledgeError('INVALID_REQUEST')
        request = frappe.local.request
        if request.headers.get('Sec-Fetch-Site') not in {None, 'same-origin', 'none'}:
            raise KnowledgeError('SCOPE_REJECTED')
        origin = request.headers.get('Origin')
        if origin and origin != request.host_url.rstrip('/'):
            raise KnowledgeError('SCOPE_REJECTED')
        runtime = load_runtime()
        result = runtime.delivery.content(ticket, request.headers.get('Range'), request_id)
        publication = getattr(runtime, 'publication', None)
        if publication:
            publication.finish()
        return Response(result.body, status=result.status, headers=result.headers)
    except KnowledgeError as error:
        _abort_publication()
        return Response(json.dumps(error_payload(error, request_id)), status=error.status,
                        content_type='application/json', headers={
                            'Cache-Control':'private, no-store, max-age=0',
                            'X-Content-Type-Options':'nosniff'})
    except Exception:
        _abort_publication()
        return Response(json.dumps(error_payload(KnowledgeError('SERVICE_ERROR'), request_id)),
                        status=503, content_type='application/json',
                        headers={'Cache-Control':'private, no-store, max-age=0',
                                 'X-Content-Type-Options':'nosniff'})


@frappe.whitelist(methods=["POST"])
def open_document(document_id=None, version_id=None, **business_fields):
    """Open the controlled reader on a current authorized document body.

    ``version_id`` is optional: the citation/search/catalog DTOs only carry the
    logical document id. The server resolves the one current published binding
    in the same authorization snapshot; a supplied stale version is refused.
    """
    def current(request_id):
        if _framework_business(business_fields, "open_document"):
            raise KnowledgeError("INVALID_REQUEST")
        from .document_reader import open_document as open_current
        return open_current(load_runtime(), document_id, version_id, request_id)
    return _run(current)


@frappe.whitelist(methods=["POST"])
def read_document_page(document_id=None, version_id=None, page=None, **business_fields):
    def current(request_id):
        if _framework_business(business_fields, "read_document_page"):
            raise KnowledgeError("INVALID_REQUEST")
        from .document_reader import read_document_page as read_page
        return read_page(load_runtime(), document_id, version_id, page, request_id)
    return _run(current)


@frappe.whitelist(methods=["POST"])
def search_document(document_id=None, version_id=None, query=None, limit=None,
                    **business_fields):
    def current(request_id):
        if _framework_business(business_fields, "search_document"):
            raise KnowledgeError("INVALID_REQUEST")
        from .document_reader import search_document as search_current
        return search_current(load_runtime(), document_id, version_id, query, limit,
                              request_id)
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

def _ask_timing_enabled():
    import os
    return os.environ.get('HBOS_ASK_TIMING')=='1'

def _ask_marks(request_id):
    """Phase marks for one real ask request, written only when enabled.

    The in-process profile cannot represent a request: it returns early with no
    answer, so its timings are void. These marks are taken in the actual HTTP
    handler so the numbers describe the path a user waits on.
    """
    import contextlib, json, os, time, pathlib
    started=time.perf_counter(); marks=[]
    @contextlib.contextmanager
    def phase(label):
        t0=time.perf_counter()
        try:
            yield
        finally:
            marks.append({'phase':label,'ms':round((time.perf_counter()-t0)*1000)})
    def flush():
        if not _ask_timing_enabled():return
        try:
            path=pathlib.Path(os.environ.get('HBOS_ASK_TIMING_FILE','/tmp/hbos-ask-timing.jsonl'))
            total=round((time.perf_counter()-started)*1000)
            path.open('a').write(json.dumps({'request_id':request_id,'total_ms':total,'marks':marks})+ '\n')
        except Exception:
            pass
    return phase,flush

def _ask_diag(request_id,stage,*,code=None,error_type=None):
    """Sanitized ask-stage diagnostic: stage/code/type only, never content."""
    import json as _json,sys as _sys
    _sys.stdout.write(_json.dumps({'hbos_ask_diag':True,'request_id':request_id,'stage':stage,
                                   'code':code,'error_type':error_type})+ '\n')
    _sys.stdout.flush()


@frappe.whitelist(methods=['POST'])
def ask(**business_fields):
    def current(request_id):
        phase,flush=_ask_marks(request_id)
        try:
            return _current_body(request_id,phase)
        finally:
            flush()

    def _current_body(request_id,phase):
        with phase('validate_structure'):
            raw=_framework_business(business_fields,'ask');validate_structure('AskRequest',raw)
        with phase('load_runtime_actor'):
            runtime=load_runtime();actor=runtime.actor()
        from .answer_policy import model_alias,DEFAULT_MODEL
        import frappe
        from .catalog_direct import is_catalog_question
        with phase('personal_models'):
            # A directory question needs no generation, so an unverified model
            # must not block it. It is still recorded as the plan's alias when
            # one is known; a null alias is refused by the phase store for the
            # generation phases, which this path never reaches.
            if isinstance(raw.get('question'),str) and is_catalog_question(
                    raw['question'],knowledge_only=bool(raw.get('knowledge_only')),
                    context=raw.get('context') or (),history=()):
                try:selected=model_alias(raw.get('model_alias') or (DEFAULT_MODEL if getattr(frappe.local,'hbos_mcp_connection',None) else _personal_models(runtime,actor)['selected_alias']))
                except KnowledgeError as error:
                    if error.code not in {'MODEL_UNAVAILABLE','UPSTREAM_INVALID_RESULT'}:raise
                    selected=None
            else:
                selected=model_alias(raw.get('model_alias') or (DEFAULT_MODEL if getattr(frappe.local,'hbos_mcp_connection',None) else _personal_models(runtime,actor)['selected_alias']))
        options={'model_alias':selected,'knowledge_only':raw.get('knowledge_only',False),
                 'answer_caller':'MCP' if getattr(frappe.local,'hbos_mcp_connection',None) else 'PORTAL'}
        if not _ask_enabled(runtime):raise KnowledgeError('MODEL_NOT_APPROVED')
        from .activity import owned,current as activity_current,bindings_for,write
        from .public_strings import safe_string
        question=safe_string(raw['question'].strip(),500)
        from .answer_policy import guard_restricted_request
        guard_restricted_request(question)
        if raw.get('conversation_id'):
            _,mapping=activity_current(runtime)
            _,previous=owned(raw['conversation_id'],actor,kinds=('History',))
            bindings_for(previous,mapping)
            from .spaces import list_spaces
            spaces=list_spaces(runtime,actor)['spaces']
            titles=_space_titles(spaces,raw.get('space_ids'))
            requested=normalize_search({'query':question,**{k:v for k,v in raw.items() if k in ('space_ids','context','search_mode')},**options})
            from .followup import validate_followup_scope
            validate_followup_scope(previous,requested.space_ids,requested.context)
            # Generation gets the real turns; retrieval gets a query that
            # names the topic. A bare "上一条是什么意思" has no topic words, so
            # using it verbatim retrieved unrelated documents.
            from .followup import conversation_history,retrieval_query
            older=None
            if previous.get('conversation_id'):
                _,candidate=owned(previous['conversation_id'],actor,kinds=('History',))
                bindings_for(candidate,mapping)
                older=candidate
            history=conversation_history(previous,older=older)
            question=raw['question'].strip()[:500]
            search_query=retrieval_query(question,previous)
            request=normalize_search({'query':search_query,'history':list(history),**_with_titles(titles),
                **{k:v for k,v in raw.items() if k in ('space_ids','context','search_mode')},**options})
            ticket=runtime.decisions.issue(actor,runtime.client,'knowledge.search',request,request_id)
            runtime.publication.plan=ticket.plan
            answer,labels,records,origin,actual_alias,answer_status=runtime.gateway.ask(ticket=ticket)
            if records:runtime.gateway.authorize_evidence(ticket,records,phase='pre_issue')
            runtime.provider.revalidate(ticket.plan)
            from knowledge_service.hbos_gateway.response_projection import public_evidence
            citations=[]
            runtime.quota.reserve_output(actor.user_ref,len(answer)+sum(len(r.excerpt) for r in records))
            for label,record in zip(labels,records):
                try:
                    handle=issue_evidence(runtime.cache,ticket,record,runtime=runtime)
                    citations.append(dict(public_evidence(record,handle,environment=runtime.profile),citation_label=label))
                except KnowledgeError as error:
                    _ask_diag(request_id,'ASK_CITATION_PROJECTION',code=error.code);raise
            from .r1_contract import validate_ask_data
            from .answer_policy import answer_presentation
            data={'request_id':request_id,'turn_id':request_id,**answer_presentation(answer,bool(citations),origin=='GENERAL',state=answer_status),
                'answer':answer,'citations':citations,
                'answer_origin':origin,'model_alias':actual_alias}
            try:
                validate_ask_data(data,environment=runtime.profile)
            except Exception as error:
                _ask_diag(request_id,'ASK_VALIDATE',error_type=type(error).__name__);raise
            turn=write('History',request.query,request.space_ids,records,runtime,conversation_id=raw.get('conversation_id'),context=request.context,
                answer=answer,labels=labels,question=raw['question'],search_mode=request.search_mode,
                answer_origin=origin,model_alias=actual_alias)
            data['turn_id']=turn;data['conversation_id']=turn
            runtime.decisions.online(ServicePrincipal(runtime.client,True),ticket.call('revalidate','final_publish'))
            runtime.audit.record(actor.user_ref,'ask','SUCCESS',len(citations))
            return data
        from .spaces import list_spaces
        with phase('list_spaces'):
            titles=_space_titles(list_spaces(runtime,actor)['spaces'],raw.get('space_ids'))
        request=normalize_search({'query':question,**_with_titles(titles),
            **{k:v for k,v in raw.items() if k in ('space_ids','context','search_mode')},**options})
        with phase('plan_issue'):
            ticket=runtime.decisions.issue(actor,runtime.client,'knowledge.search',request,request_id)
        runtime.publication.plan=ticket.plan
        direct=_catalog_direct(runtime,phase,ticket,titles,question,request,options,request_id)
        if direct is not None:return direct
        with phase('gateway_ask'):
            answer,labels,records,origin,actual_alias,answer_status=runtime.gateway.ask(ticket=ticket)
        with phase('authorize_evidence'):
            if records:runtime.gateway.authorize_evidence(ticket,records,phase='pre_issue')
        with phase('provider_revalidate'):
            runtime.provider.revalidate(ticket.plan)
        from knowledge_service.hbos_gateway.response_projection import public_evidence
        citations=[]
        runtime.quota.reserve_output(actor.user_ref,len(answer)+sum(len(r.excerpt) for r in records))
        for label,record in zip(labels,records):
            handle=issue_evidence(runtime.cache,ticket,record,runtime=runtime)
            citations.append(dict(public_evidence(record,handle,environment=runtime.profile),citation_label=label))
        from .r1_contract import validate_ask_data
        from .answer_policy import answer_presentation
        data={'request_id':request_id,'turn_id':request_id,**answer_presentation(answer,bool(citations),origin=='GENERAL',state=answer_status),
            'answer':answer,'citations':citations,
            'answer_origin':origin,'model_alias':actual_alias}
        with phase('validate_ask_data'):
            validate_ask_data(data,environment=runtime.profile)
        with phase('write_history'):
            turn=write('History',request.query,request.space_ids,records,runtime,conversation_id=raw.get('conversation_id'),context=request.context,
            answer=answer,labels=labels,question=raw['question'],search_mode=request.search_mode,
            answer_origin=origin,model_alias=actual_alias)
        data['turn_id']=turn;data['conversation_id']=turn
        with phase('final_online'):
            runtime.decisions.online(ServicePrincipal(runtime.client,True),ticket.call('revalidate','final_publish'))
        with phase('audit'):
            runtime.audit.record(actor.user_ref,'ask','SUCCESS',len(citations))
        return data
    return _run(current)


def _catalog_direct(runtime,phase,ticket,titles,question,request,options,request_id):
    """Answer a directory question from the authorized plan, or return None.

    The plan this request already holds is the authorization: same ticket,
    same fingerprint, same identity, same bindings as the gateway path. What
    is skipped is only the round trip and the generation, which a count does
    not need. Every phase still goes through the decision store, in the same
    order ``activity.restore`` uses for its metadata reads, and the same
    history, quota and audit calls run as on the normal path.
    """
    from .catalog_direct import is_catalog_question, render
    if not is_catalog_question(question,knowledge_only=options.get('knowledge_only',False),
                               context=request.context,history=request.history or ()):
        return None
    with phase('catalog_direct'):
        answer,found=render(ticket.plan,titles,question)
    if not found:
        # Nothing matched inside this scope. The catalogue gateway would say the
        # same thing in a full round trip; returning None keeps that single
        # wording rather than growing a second one.
        return None
    from .activity import write
    principal=ServicePrincipal(runtime.client,True)
    with phase('metadata_phases'):
        # Same sequence as activity.restore: cache_read needs introspect first,
        # and final_publish needs pre_projection. Each call revalidates.
        runtime.decisions.online(principal,ticket.call('introspect','introspect'))
        runtime.decisions.online(principal,ticket.call('introspect','cache_read'))
        runtime.decisions.online(principal,ticket.call('revalidate','pre_projection'))
    from .r1_contract import validate_ask_data
    from .answer_policy import answer_presentation
    alias=ticket.plan.model_alias
    data={'request_id':request_id,'turn_id':request_id,
        **answer_presentation(answer,False,state='CATALOG_RESULTS'),
        'answer':answer,'citations':[],'answer_origin':'KNOWLEDGE'}
    if alias:data['model_alias']=alias
    with phase('validate_ask_data'):
        validate_ask_data(data,environment=runtime.profile)
    with phase('write_history'):
        turn=write('History',request.query,request.space_ids,(),runtime,
            conversation_id=None,context=request.context,answer=answer,labels=(),question=question,
            search_mode=request.search_mode,answer_origin='KNOWLEDGE',model_alias=alias)
    data['turn_id']=turn;data['conversation_id']=turn
    with phase('final_online'):
        runtime.decisions.online(principal,ticket.call('revalidate','final_publish'))
    with phase('audit'):
        runtime.audit.record(ticket.plan.subject.user_ref,'ask','SUCCESS',0)
    return data


def _with_titles(titles):
    """``space_titles`` for a request, omitted entirely when there are none.

    Passing ``space_titles=None`` would still be a present key, and the
    contract rejects a present-but-empty map.
    """
    return {'space_titles': titles} if titles else {}


def _space_titles(spaces, requested=None):
    """Display names for the spaces this request may name, or None.

    The SearchRequest contract admits 1..20 titles, but ``list_spaces`` may
    return up to 100 authorized spaces. Sending the whole map made every ask
    fail with INVALID_REQUEST for a caller with 21+ spaces, and sending an
    empty one made a caller with no grants fail the same way instead of
    reaching EMPTY_SCOPE. The map is display data only: it never widens the
    grant set, so narrowing it to the requested spaces (when the caller named
    some) and omitting it when there are none is exact.
    """
    known = {s['space_id']: s['title'] for s in spaces or () if s.get('space_id')}
    if requested is not None:
        known = {k: v for k, v in known.items() if k in set(requested)}
    if not known:
        return None
    # Deterministic order keeps the signed request fingerprint stable.
    return dict(sorted(known.items())[:20])


def _personal_models(runtime,actor):
    import frappe
    from .answer_policy import ALIASES,DEFAULT_MODEL
    runtime.provider._current(actor,runtime.client)
    data=runtime.gateway.models()
    if (not isinstance(data,dict) or set(data)!={'default','models'} or data['default']!=DEFAULT_MODEL
        or not isinstance(data['models'],list) or [m.get('alias') for m in data['models']]!=list(ALIASES)
        or any(set(m)!={'alias','available','reason'} or type(m['available']) is not bool or m['reason'] not in (None,'CONFIGURATION_NOT_VERIFIED') for m in data['models'])):
        raise KnowledgeError('UPSTREAM_INVALID_RESULT')
    selected=frappe.defaults.get_user_default('hbos_knowledge_model',user=actor.user_ref)
    available={m['alias'] for m in data['models'] if m['available']}
    if selected not in available:
        # The default is only a fallback when it is itself verified. Picking it
        # blindly made every ask fail with MODEL_UNAVAILABLE on a deployment
        # where only another alias had been verified. The stored user
        # preference is never rewritten here.
        if DEFAULT_MODEL in available:selected=DEFAULT_MODEL
        else:selected=next((m['alias'] for m in data['models'] if m['available']),None)
        if selected is None:raise KnowledgeError('MODEL_UNAVAILABLE')
    runtime.provider._current(actor,runtime.client)
    return {**data,'selected_alias':selected}


@frappe.whitelist(methods=['GET'])
def get_models(**business_fields):
    def current(request_id):
        if _framework_business(business_fields,'get_models'):raise KnowledgeError('INVALID_REQUEST')
        runtime=load_runtime();return _personal_models(runtime,runtime.actor())
    return _run(current)


@frappe.whitelist(methods=['POST'])
def set_model_preference(model_alias=None,**business_fields):
    def current(request_id):
        if _framework_business(business_fields,'set_model_preference'):raise KnowledgeError('INVALID_REQUEST')
        from .answer_policy import model_alias as validate
        import frappe
        selected=validate(model_alias);runtime=load_runtime();actor=runtime.actor()
        catalog=_personal_models(runtime,actor)
        if not any(m['alias']==selected and m['available'] for m in catalog['models']):raise KnowledgeError('MODEL_UNAVAILABLE')
        frappe.defaults.set_user_default('hbos_knowledge_model',selected,user=actor.user_ref)
        runtime.provider._current(actor,runtime.client)
        return {'selected_alias':selected}
    return _run(current)


@frappe.whitelist(methods=["GET"])
def get_documents(**business_fields):
    def current(request_id):
        if _framework_business(business_fields,'get_documents'):raise KnowledgeError('INVALID_REQUEST')
        from .reference_admin import get_catalog
        runtime=load_runtime();return get_catalog(runtime,runtime.actor())
    return _run(current)


@frappe.whitelist(methods=['GET'])
def get_documents_page(query=None,space_id=None,page=1,page_size=12,law_category=None,folder_id=None,**business_fields):
    def current(request_id):
        if _framework_business(business_fields,'get_documents_page'):raise KnowledgeError('INVALID_REQUEST')
        from .reference_admin import get_catalog_page
        runtime=load_runtime()
        return get_catalog_page(runtime,runtime.actor(),query=query,space_id=space_id,page=page,page_size=page_size,law_category=law_category,folder_id=folder_id)
    return _run(current)

@frappe.whitelist(methods=['GET'])
def get_activity(kind=None,page=1,page_size=12,**business_fields):
    def current(request_id):
        if _framework_business(business_fields,'get_activity'):raise KnowledgeError('INVALID_REQUEST')
        from .activity import list_activity
        return list_activity(load_runtime(),kind,page,page_size)
    return _run(current)


@frappe.whitelist(methods=['GET'])
def get_feedback(page=1,page_size=12,status=None,**business_fields):
    def current(request_id):
        if _framework_business(business_fields,'get_feedback'):raise KnowledgeError('INVALID_REQUEST')
        from .activity import list_feedback
        return list_feedback(load_runtime(),page,page_size,status)
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
        from .activity import save_document
        value=normalize_evidence({'evidence_id':evidence_id})
        record=resolve_cached_evidence(runtime.cache,runtime.actor(),runtime.client,value,runtime=runtime,request_id=request_id)[0]
        return {'id':save_document(runtime,record.binding.canonical_document_id,record.binding.version_id,request_id+'_bookmark')}
    return _run(current)

@frappe.whitelist(methods=['POST'])
def save_document_bookmark(document_id=None,version_id=None,**business_fields):
    def current(request_id):
        if _framework_business(business_fields,'save_document_bookmark'):raise KnowledgeError('INVALID_REQUEST')
        from .activity import save_document
        return {'id':save_document(load_runtime(),document_id,version_id,request_id)}
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
def get_feedback_queue(page=1,page_size=12,status=None,**business_fields):
    def current(request_id):
        if _framework_business(business_fields,'get_feedback_queue'):raise KnowledgeError('INVALID_REQUEST')
        from .activity import feedback_queue
        return feedback_queue(load_runtime(),page,page_size,status)
    return _run(current)

@frappe.whitelist(methods=['POST'])
def review_feedback(activity_id=None,status=None,reply='',**business_fields):
    def current(request_id):
        if _framework_business(business_fields,'review_feedback'):raise KnowledgeError('INVALID_REQUEST')
        from .activity import review_feedback as update
        return update(load_runtime(),activity_id,status,reply)
    return _run(current)

@frappe.whitelist(methods=['GET'])
def get_connections(**business_fields):
    def current(request_id):
        if _framework_business(business_fields,'get_connections'):raise KnowledgeError('INVALID_REQUEST')
        from .connections import list_owned
        return list_owned(load_runtime())
    return _run(current)

@frappe.whitelist(methods=['POST'])
def create_connection(label=None,client_name=None,**business_fields):
    def current(request_id):
        if _framework_business(business_fields,'create_connection'):raise KnowledgeError('INVALID_REQUEST')
        from .connections import create
        return create(load_runtime(),label,client_name)
    return _run(current)

@frappe.whitelist(methods=['POST'])
def revoke_connection(connection_id=None,**business_fields):
    def current(request_id):
        if _framework_business(business_fields,'revoke_connection'):raise KnowledgeError('INVALID_REQUEST')
        from .connections import revoke
        return revoke(load_runtime(),connection_id)
    return _run(current)

# Maintenance mutations retain native Session/CSRF processing before this module.
def _maintenance_action(method,fields,fn):
    def current(request_id):
        if _framework_business(fields,method):raise KnowledgeError('INVALID_REQUEST')
        from .maintenance_access import require
        require()
        try:return fn()
        except Exception as exc:
            # _run returns a safe envelope, so Frappe would otherwise commit
            # partial writes as a successful HTTP request.
            frappe.db.rollback()
            from .publication import PublicationConflict
            if isinstance(exc,PublicationConflict):raise KnowledgeError('IDENTITY_CONFLICT') from None
            raise
    return _run(current)

@frappe.whitelist(methods=['GET'])
def get_maintenance(batch_id=None,page=1,page_size=12,locate=None,
                    published_query=None,published_document_id=None,published_page=1,
                    published_page_size=None,batch_query=None,batch_page=1,
                    batch_page_size=None,batch_document_id=None,**fields):
    from .maintenance import dashboard
    return _maintenance_action('get_maintenance',fields,lambda:dashboard(
        batch_id,page,page_size,locate,published_query=published_query,
        published_document_id=published_document_id,published_page=published_page,
        published_page_size=published_page_size,batch_query=batch_query,
        batch_page=batch_page,batch_page_size=batch_page_size,
        batch_document_id=batch_document_id))

@frappe.whitelist(methods=['POST'])
def upload_knowledge(department=None,label=None,sharing=None,replace_document=None,expected_version=None,**fields):
    from .maintenance import upload
    return _maintenance_action('upload_knowledge',fields,lambda:upload(department,label,sharing,replace_document,expected_version))

@frappe.whitelist(methods=['POST'])
def queue_import(batch_id=None,document_ids=None,operation='parse',**fields):
    from .maintenance import queue
    return _maintenance_action('queue_import',fields,lambda:queue(batch_id,document_ids,operation))

@frappe.whitelist(methods=['POST'])
def preview_import(batch_id=None,document_id=None,page=1,**fields):
    from .maintenance import preview
    return _maintenance_action('preview_import',fields,lambda:preview(batch_id,document_id,page))

@frappe.whitelist(methods=['POST'])
def review_import(batch_id=None,document_id=None,checks=None,note=None,**fields):
    from .maintenance import review
    return _maintenance_action('review_import',fields,lambda:review(batch_id,document_id,checks,note))

@frappe.whitelist(methods=['POST'])
def review_import_batch(batch_id=None,document_ids=None,checks=None,note=None,**fields):
    from .maintenance import review_batch
    return _maintenance_action('review_import_batch',fields,lambda:review_batch(batch_id,document_ids,checks,note))

@frappe.whitelist(methods=['POST'])
def hold_import_quality(batch_id=None,document_ids=None,note=None,**fields):
    from .maintenance import hold_quality
    return _maintenance_action('hold_import_quality',fields,lambda:hold_quality(batch_id,document_ids,note))

@frappe.whitelist(methods=['POST'])
def approve_import_sharing(batch_id=None,document_ids=None,note=None,**fields):
    from .maintenance import approve_sharing
    return _maintenance_action('approve_import_sharing',fields,lambda:approve_sharing(batch_id,document_ids,note))

@frappe.whitelist(methods=['POST'])
def publish_import(batch_id=None,document_ids=None,operation='publish',expected_version=None,reason=None,**fields):
    from .maintenance import publish
    return _maintenance_action('publish_import',fields,lambda:publish(batch_id,document_ids,operation,expected_version,reason))

@frappe.whitelist(methods=['POST'])
def withdraw_import(batch_id=None,document_id=None,expected_version=None,reason=None,**fields):
    from .maintenance import withdraw
    return _maintenance_action('withdraw_import',fields,lambda:withdraw(batch_id,document_id,expected_version,reason))
