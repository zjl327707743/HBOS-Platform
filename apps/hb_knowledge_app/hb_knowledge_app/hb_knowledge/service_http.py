"""Bounded signed service HTTP. Only synthetic internal-network HTTP is admitted."""
from __future__ import annotations
import hashlib, hmac, json, logging, math, re, secrets, time
import requests
from .errors import KnowledgeError
from .execution_plan import Client, ServicePrincipal

MAX_BODY = 4*1048576  # Bounded for at most 1024 explicitly authorized bindings.

LOGGER = logging.getLogger(__name__)
# These are the actual signed wire paths; an unknown path maps to OTHER.
OPERATIONS = {
    '/api/method/hb_knowledge_app.hb_knowledge.frappe_factory.'+name: name
    for name in ('authority_call','authority_search','authority_revalidate')
}
OPERATIONS.update({'/v1/knowledge/'+path:operation for path,operation in (
    ('search','knowledge_search'),('ask','knowledge_ask'),
    ('authorize-evidence','authorize_evidence'),('document-page','document_page'),
    ('document-search','document_search'),('models','models'),
    ('answer-status','answer_status'),('availability','availability'))})
_REQUEST_ID = re.compile(r'[A-Za-z0-9_-]{1,128}')

class _BodyLimit(Exception):
    pass

class _UnexpectedResponse(Exception):
    pass

def _safe_request_id(payload):
    value = payload.get('request_id') if isinstance(payload, dict) else None
    return value if isinstance(value, str) and _REQUEST_ID.fullmatch(value) else None

def _declared_phase(payload):
    from .internal_contract import PHASES
    value = payload.get('phase') if isinstance(payload, dict) else None
    return value if isinstance(value, str) and value in PHASES else None

def _exception_class(error):
    # Arbitrary class names can themselves contain secrets. Only fixed types
    # are named, even if an unknown class happens to look like an identifier.
    for cls,name in ((requests.exceptions.ConnectTimeout,'ConnectTimeout'),
                     (requests.exceptions.ReadTimeout,'ReadTimeout'),
                     (requests.exceptions.ConnectionError,'ConnectionError'),
                     (requests.exceptions.ChunkedEncodingError,'ChunkedEncodingError'),
                     (requests.exceptions.ContentDecodingError,'ContentDecodingError'),
                     (json.JSONDecodeError,'JSONDecodeError'),
                     (UnicodeDecodeError,'UnicodeDecodeError'),
                     (_BodyLimit,'BodyLimit'),(_UnexpectedResponse,'UnexpectedResponse'),
                     (KnowledgeError,'KnowledgeError')):
        if isinstance(error,cls):return name
    return 'Exception'

def _failure_category(error):
    if isinstance(error, requests.exceptions.ConnectTimeout):
        return 'CONNECT_TIMEOUT'
    if isinstance(error, requests.exceptions.ReadTimeout):
        return 'READ_TIMEOUT'
    if isinstance(error, (requests.exceptions.ConnectionError,
                          requests.exceptions.ChunkedEncodingError,
                          requests.exceptions.ContentDecodingError)):
        return 'CONNECTION_ERROR'
    if isinstance(error, _BodyLimit):
        return 'BODY_LIMIT'
    if isinstance(error, (json.JSONDecodeError, UnicodeDecodeError)):
        return 'INVALID_JSON'
    if isinstance(error, _UnexpectedResponse):
        return 'UNEXPECTED_HTTP'
    if isinstance(error, KnowledgeError):
        return 'UPSTREAM_ERROR'
    return 'UNKNOWN_ERROR'

def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':'))

def signature(key, method, path, origin, stamp, nonce, body):
    value = '\n'.join((method, path, origin, stamp, nonce, hashlib.sha256(body).hexdigest()))
    return hmac.new(key.encode(), value.encode(), hashlib.sha256).hexdigest()

def sign(key, caller, path, origin, body):
    stamp, nonce = str(int(time.time())), secrets.token_hex(16)
    return {'Content-Type': 'application/json', 'X-HBOS-Caller': caller,
            'X-HBOS-Origin-Client': origin, 'X-HBOS-Time': stamp, 'X-HBOS-Nonce': nonce,
            'X-HBOS-Signature': signature(key, 'POST', path, origin, stamp, nonce, body)}

def authenticate(headers, body, path, config, state, *, max_body=MAX_BODY):
    if len(body) > max_body:
        raise KnowledgeError('INVALID_REQUEST')
    caller, origin = headers.get('X-HBOS-Caller'), headers.get('X-HBOS-Origin-Client')
    row = config.get('callers', {}).get(caller)
    stamp, nonce, sig = (headers.get(x, '') for x in ('X-HBOS-Time', 'X-HBOS-Nonce', 'X-HBOS-Signature'))
    try:
        if not row or origin not in row['origins'] or abs(time.time()-int(stamp)) > 30:
            raise ValueError()
        if len(nonce) != 32 or any(c not in '0123456789abcdef' for c in nonce):
            raise ValueError()
        expected = signature(row['key'], 'POST', path, origin, stamp, nonce, body)
        if not hmac.compare_digest(expected, sig):
            raise ValueError()
        # Authentication material identifies the service; origin is separately mapped.
        if not state.set('auth:'+caller+':'+nonce, 'used', ex=65, nx=True):
            raise ValueError()
    except KnowledgeError:
        raise
    except Exception:
        raise KnowledgeError('CLIENT_AUTH_FAILED') from None
    return ServicePrincipal(Client(origin), True)

class SignedHttp:
    test_only = False
    def __init__(self, url, key, caller):
        if not url.startswith('http://') or 'host.docker.internal' in url:
            raise KnowledgeError('POLICY_UNAVAILABLE')
        self.url, self.key, self.caller = url.rstrip('/'), key, caller
    def _receipt(self, payload, path, status, started, read_timeout, error=None,
                 category='UNKNOWN_ERROR', observed_bytes=None):
        try:
            receipt = {
                'event': 'signed_http_failure',
                'request_id': _safe_request_id(payload),
                'operation': OPERATIONS.get(path, 'OTHER'),
                'phase': _declared_phase(payload),
                'failure_category': category,
                'exception_class': _exception_class(error) if error is not None else None,
                'http_status': status if type(status) is int and 100<=status<=599 else None,
                'elapsed_ms': max(0, int((time.monotonic()-started)*1000)),
                'read_timeout': read_timeout if type(read_timeout) in (int,float) and math.isfinite(read_timeout) and 0<read_timeout<=600 else None,
                'response_bytes': observed_bytes if type(observed_bytes) is int and 0<=observed_bytes<=MAX_BODY+8192 else None,
            }
            if isinstance(error, KnowledgeError):
                receipt['error_code'] = error.code
            LOGGER.warning(json.dumps(receipt, sort_keys=True, separators=(',', ':')))
        except Exception:
            pass
    def post(self, path, payload, origin):
        body = canonical(payload).encode()
        bound=getattr(self,'max_body',MAX_BODY)
        if len(body) > bound:
            raise KnowledgeError('INVALID_REQUEST')
        started = time.monotonic()
        status, observed = None, None
        read_timeout = getattr(self, 'read_timeout', 6)
        try:
            with requests.Session() as session:
                session.trust_env = False
                headers=sign(self.key,self.caller,path,origin,body)
                request_id=_safe_request_id(payload)
                if request_id:
                    headers['X-HBOS-Request-ID']=request_id
                if getattr(self,'site',None): headers['X-Frappe-Site-Name']=self.site
                with session.post(self.url+path, data=body,
                     headers=headers,timeout=(2,read_timeout),stream=True,
                     allow_redirects=False) as response:
                    status = response.status_code
                    data=bytearray()
                    observed = 0
                    for part in response.iter_content(8192):
                        data.extend(part)
                        observed = len(data)
                        if len(data)>bound: raise _BodyLimit()
                    raw=json.loads(data)
                    if status != 200:
                        if isinstance(raw,dict) and isinstance(raw.get('error'),dict):
                            from .document_reader_contract import READ_STATES
                            state=raw['error'].get('state')
                            raise KnowledgeError(raw['error'].get('code','UPSTREAM_UNAVAILABLE'),
                                state=state if state in READ_STATES else None)
                        raise _UnexpectedResponse()
                    return raw
        except KnowledgeError as error:
            self._receipt(payload, path, status, started, read_timeout, error=error,
                          category='UPSTREAM_ERROR', observed_bytes=observed)
            raise
        except Exception as error:
            self._receipt(payload, path, status, started, read_timeout, error=error,
                          category=_failure_category(error), observed_bytes=observed)
            raise KnowledgeError('UPSTREAM_UNAVAILABLE') from None
