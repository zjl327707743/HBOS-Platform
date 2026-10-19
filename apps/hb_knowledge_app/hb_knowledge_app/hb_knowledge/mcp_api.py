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
    frappe.local.hbos_mcp_connection=raw['token'].removeprefix('hbos_mcp_').split('.')[0]
    runtime.provider._current(actor,runtime.client)
    return runtime,raw['token'].removeprefix('hbos_mcp_').split('.')[0]

@frappe.whitelist(allow_guest=True,methods=['POST'])
def authenticate_connection(**ignored):
    def run():
        raw,principal,_=_service_request()
        if set(raw)-{'token','stage','observation'}:raise KnowledgeError('INVALID_REQUEST')
        if raw.get('stage','Authenticated') not in ('Authenticated','Tools Discovered'):raise KnowledgeError('INVALID_REQUEST')
        _,name=_bound(raw,principal)
        connections.observe(name,raw.get('stage','Authenticated'),raw.get('observation'))
        return {'authenticated':True}
    return _authority_envelope(run)

@frappe.whitelist(allow_guest=True,methods=['POST'])
def dispatch(**ignored):
    from .errors import error_payload
    try:
        raw,principal,_=_service_request()
        if set(raw)-{'token','tool','arguments','observation'} or not {'token','tool','arguments'}<=set(raw):raise KnowledgeError('INVALID_REQUEST')
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
            if name=='search_knowledge' and result.get('data',{}).get('results'):connections.observe(connection,'Search Passed',raw.get('observation'),result=result['data'],arguments=arguments)
            elif name=='get_evidence':
                receipt=dict(result['data'],request_id=getattr(frappe.local,'hbos_knowledge_request_id',None))
                connections.observe(connection,'Evidence Opened',raw.get('observation'),result=receipt,arguments=arguments)
            elif name=='ask_knowledge' and result.get('data',{}).get('answer_status') in {'GENERATED_WITH_SOURCES','CATALOG_RESULTS','REFERENCE_ANSWERED'}:connections.observe(connection,'Answer Generated',raw.get('observation'))
        return result
    except KnowledgeError as error:return error_payload(error)
    except Exception:return error_payload(KnowledgeError('SERVICE_ERROR'))
