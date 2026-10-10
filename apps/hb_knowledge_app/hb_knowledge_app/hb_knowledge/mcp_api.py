"""Signed MCP-to-HBOS boundary. The connection determines the final user."""
import frappe
from .errors import KnowledgeError
from .frappe_factory import _service_request, _authority_envelope, components, build_runtime
from . import connections

def _bound(raw,principal):
    cfg,state,*_=components()
    if principal.client.client_id!=cfg['portal_client_id']:raise KnowledgeError('CLIENT_AUTH_FAILED')
    actor=connections.issue_actor(raw.get('token'),cfg,state)
    runtime=build_runtime(actor_resolver=lambda:actor)
    frappe.local.hbos_knowledge_runtime=runtime
    runtime.provider._current(actor,runtime.client)
    return runtime,raw['token'].removeprefix('hbos_mcp_').split('.')[0]

@frappe.whitelist(allow_guest=True,methods=['POST'])
def authenticate_connection(**ignored):
    def run():
        raw,principal,_=_service_request()
        if set(raw)-{'token','stage'}:raise KnowledgeError('INVALID_REQUEST')
        if raw.get('stage','Authenticated') not in ('Authenticated','Tools Discovered'):raise KnowledgeError('INVALID_REQUEST')
        _,name=_bound(raw,principal)
        connections.observe(name,raw.get('stage','Authenticated'))
        return {'authenticated':True}
    return _authority_envelope(run)

@frappe.whitelist(allow_guest=True,methods=['POST'])
def dispatch(**ignored):
    from .errors import error_payload
    try:
        raw,principal,_=_service_request()
        if set(raw)!={'token','tool','arguments'}:raise KnowledgeError('INVALID_REQUEST')
        from knowledge_service.hbos_gateway.closed_tools import TOOLS
        from .r1_contract import validate_structure
        name=raw['tool'];arguments=raw['arguments']
        if name not in TOOLS:raise KnowledgeError('INVALID_REQUEST')
        validate_structure(TOOLS[name],arguments)
        _,connection=_bound(raw,principal)
        from . import api
        handlers={'list_knowledge_spaces':api.get_spaces,'search_knowledge':api.search,
                  'get_evidence':api.resolve_evidence,'ask_knowledge':api.ask}
        result=handlers[name](**arguments)
        if result.get('ok'):
            if name=='search_knowledge' and result.get('data',{}).get('results'):connections.observe(connection,'Search Passed')
            elif name=='get_evidence':connections.observe(connection,'Evidence Opened')
            elif name=='ask_knowledge' and result.get('data',{}).get('answer_status')=='REFERENCE_ANSWERED':connections.observe(connection,'Answer Generated')
        return result
    except KnowledgeError as error:return error_payload(error)
    except Exception:return error_payload(KnowledgeError('SERVICE_ERROR'))
