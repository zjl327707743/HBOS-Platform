"""Browser-owned consent, using native Frappe sessions and CSRF processing."""
from datetime import datetime
from functools import wraps
from html import escape
import re
from urllib.parse import quote, urlsplit

import frappe

from .errors import KnowledgeError
from .runtime import load_runtime
from .shared_reference import configuration
from .service_http import SignedHttp


def _friendly_error(function):
    @wraps(function)
    def safe(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except KnowledgeError:
            # Expired/denied consent is an expected browser result. Optional
            # website asset bundles must not turn it into a Frappe error page.
            from werkzeug.wrappers import Response
            return Response('<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                '<title>连接未完成 · HBOS</title><h1>连接未完成</h1>'
                '<p>授权请求已失效，或当前账号无法授权。请返回助手重新发起连接。</p>'
                '<a href="/hbos/knowledge">返回知识库</a></html>',status=400,mimetype='text/html',
                headers={'Cache-Control':'private, no-store','Referrer-Policy':'no-referrer',
                    'Content-Security-Policy':"default-src 'none'; base-uri 'none'; frame-ancestors 'none'"})
    return safe


def _context(request_id, fields):
    if (set(fields) - {'cmd', 'csrf_token'} or not isinstance(request_id, str)
            or not re.fullmatch(r'[A-Za-z0-9_-]{43}', request_id)):
        raise KnowledgeError('INVALID_REQUEST')
    cfg = configuration()
    if not cfg.get('mcp_oauth_enabled'):
        raise KnowledgeError('POLICY_UNAVAILABLE')
    runtime = load_runtime()
    actor = runtime.actor()
    runtime.provider._current(actor, runtime.client)
    http = SignedHttp(cfg['gateway_url'], cfg['bff_key'], 'hbos-bff')
    return runtime, actor, cfg, http


def _call(http, cfg, action, body):
    result = http.post('/v1/knowledge/oauth/' + action, body, cfg['portal_client_id'])
    if not isinstance(result, dict) or not result.get('ok'):
        raise KnowledgeError('AUTHENTICATION_REQUIRED')
    return result['data']


def _consent_csp(details):
    # Chrome applies form-action to the subsequent OAuth redirect as well.
    # Permit only this server-validated registered callback's exact origin;
    # never use a wildcard or a redirect supplied by the browser form.
    try:
        target=urlsplit(details['redirect_uri']);host=target.hostname
        if (target.username or target.password or not host
            or not (re.fullmatch(r'[A-Za-z0-9.-]+',host) or host=='::1')
            or target.scheme not in ('http','https')
            or target.scheme=='http' and host not in ('localhost','127.0.0.1','::1')):
            raise ValueError()
        authority=('['+host+']') if ':' in host else host
        if target.port is not None:authority+=':'+str(target.port)
        origin=target.scheme+'://'+authority
    except (KeyError,TypeError,ValueError):raise KnowledgeError('INVALID_REQUEST') from None
    return "default-src 'none'; style-src 'unsafe-inline'; form-action 'self' "+origin+"; base-uri 'none'; frame-ancestors 'none'"


@frappe.whitelist(allow_guest=True, methods=['GET'])
@_friendly_error
def begin(request_id=None, **fields):
    if frappe.session.user == 'Guest':
        if not isinstance(request_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', request_id):
            raise KnowledgeError('INVALID_REQUEST')
        target = '/hbos/knowledge/oauth?request_id=' + request_id
        frappe.local.response['type'] = 'redirect'
        frappe.local.response['http_status_code'] = 302
        frappe.local.response['location'] = '/hbos/login?redirect_to=' + quote(target, safe='')
        return
    runtime, actor, cfg, http = _context(request_id, fields)
    details = _call(http, cfg, 'consent', {'request_id': request_id, 'owner': actor.user_ref})
    from frappe.sessions import get_csrf_token
    scopes = {'knowledge.search': '查找本人有权访问的资料',
              'knowledge.read': '读取有限依据并核对来源',
              'knowledge.ask': '调用已批准模型回答知识问题'}
    if set(details.get('scopes', [])) - set(scopes):
        raise KnowledgeError('INVALID_REQUEST')
    items = ''.join('<li>' + escape(scopes[s]) + '</li>' for s in details['scopes'])
    page = ('<p>助手：<strong>' + escape(details['client_name']) + '</strong></p>'
        '<p>本人：' + escape(actor.user_ref) + '</p><ul>' + items + '</ul>'
        '<p>仅能使用你当前可访问的已发布资料。可以随时在知识库撤销连接。</p>'
        '<form method="post" action="/api/method/hb_knowledge_app.hb_knowledge.oauth_api.approve">'
        '<input type="hidden" name="request_id" value="' + request_id + '">'
        '<input type="hidden" name="csrf_token" value="' + escape(get_csrf_token(), quote=True) + '">'
        '<button type="submit" name="consent" value="approve">授权此助手</button></form>')
    # A native authenticated response needs no optional Frappe website asset
    # bundle. Session and CSRF checks are still performed by Frappe itself.
    from werkzeug.wrappers import Response
    document = ('<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>连接我的助手 · HBOS</title><style>'
        'body{font:17px/1.7 system-ui,sans-serif;color:#213547;background:#f4f6f8;margin:0}'
        'main{max-width:38rem;margin:6vh auto;background:white;padding:2rem;border-radius:16px}'
        'button{font:inherit;padding:.7rem 1.2rem;border:0;border-radius:8px;background:#175d67;color:white;cursor:pointer}'
        'a{display:inline-block;margin-top:1rem;color:#175d67}strong{overflow-wrap:anywhere}'
        '@media(max-width:600px){main{margin:0;padding:1.2rem;border-radius:0}}'
        '</style><main><h1>连接我的助手</h1>' + page
        + '<a href="/hbos/knowledge">暂不授权，返回知识库</a></main></html>')
    return Response(document,mimetype='text/html',headers={
        'Cache-Control':'private, no-store','Referrer-Policy':'no-referrer',
        'Content-Security-Policy':_consent_csp(details)})


@frappe.whitelist(methods=['POST'])
@_friendly_error
def approve(request_id=None, consent=None, **fields):
    # Frappe validates the browser session and CSRF before invoking this method.
    if consent != 'approve':
        raise KnowledgeError('INVALID_REQUEST')
    runtime, actor, cfg, http = _context(request_id, fields)
    details = _call(http, cfg, 'consent', {'request_id': request_id, 'owner': actor.user_ref})
    from .connections import create
    try:
        connection = create(runtime, 'OAuth · ' + details['client_name'], 'MCP Client')
        expires = datetime.fromisoformat(connection['expires_at'].replace('Z', '+00:00')).timestamp()
        result = _call(http, cfg, 'approve', {'request_id': request_id,
            'owner': actor.user_ref, 'connection': connection['token'], 'expires': expires})
        runtime.provider._current(actor, runtime.client)
    except Exception:
        frappe.db.rollback()
        raise KnowledgeError('AUTHENTICATION_REQUIRED') from None
    frappe.local.response_headers['Cache-Control'] = 'private, no-store'
    frappe.local.response_headers['Referrer-Policy'] = 'no-referrer'
    frappe.local.response['type'] = 'redirect'
    frappe.local.response['http_status_code'] = 302
    frappe.local.response['location'] = result['redirect']
