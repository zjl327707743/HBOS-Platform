"""Bounded signed service HTTP. Only synthetic internal-network HTTP is admitted."""
from __future__ import annotations
import hashlib, hmac, json, secrets, time
import requests
from .errors import KnowledgeError
from .execution_plan import Client, ServicePrincipal

MAX_BODY = 1048576  # Bounded for at most 512 explicitly authorized bindings.

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

def authenticate(headers, body, path, config, state):
    if len(body) > MAX_BODY:
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
    def post(self, path, payload, origin):
        body = canonical(payload).encode()
        if len(body) > MAX_BODY:
            raise KnowledgeError('INVALID_REQUEST')
        try:
            with requests.Session() as session:
                session.trust_env = False
                headers=sign(self.key,self.caller,path,origin,body)
                if getattr(self,'site',None): headers['X-Frappe-Site-Name']=self.site
                with session.post(self.url+path, data=body,
                     headers=headers,timeout=(2,getattr(self,"read_timeout",6)),stream=True,
                     allow_redirects=False) as response:
                    data=bytearray()
                    for part in response.iter_content(8192):
                        data.extend(part)
                        if len(data)>MAX_BODY: raise ValueError()
                    raw=json.loads(data)
                    if response.status_code != 200:
                        if isinstance(raw,dict) and isinstance(raw.get('error'),dict):
                            raise KnowledgeError(raw['error'].get('code','UPSTREAM_UNAVAILABLE'))
                        raise ValueError()
                    return raw
        except KnowledgeError: raise
        except Exception: raise KnowledgeError('UPSTREAM_UNAVAILABLE') from None
