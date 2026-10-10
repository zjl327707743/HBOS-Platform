"""Explicit private configuration and query-only WSGI assembly.

No Frappe import, Site discovery, schema bootstrap, policy write or cached
last-known-good binding. A valid file is deployment input, not human approval.
"""
from dataclasses import dataclass
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import stat
from urllib.parse import urlsplit

from hbos_portal.authorization.errors import ContractError
from hbos_portal.contracts.errors import PortalException, error_response
from .management_http import ManagedHTTPBinding
from .management_query_http import ManagedQueryHTTPApplication, QUERY_PREFIX, QUERIES
from .management_storage import PolicyApprovalPin, PinnedPolicyApprovalVerifier
from .source_adapter import parse_rfc3339_utc
from .storage_schema import canonical_json, require_uuid

MAX_CONFIG_BYTES = 128 * 1024
MAX_RESPONSE_BYTES = 1024 * 1024
_PIN_KEYS = frozenset(PolicyApprovalPin.__dataclass_fields__)
_APPROVAL_KEYS = frozenset(('approval_ref', 'approved_by', 'approved_at_utc',
    'approved_revision', 'approved_authority_generation', 'content_digest'))


@dataclass(frozen=True, slots=True)
class ManagementSiteConfiguration:
    site_id: str
    database_sha256: str
    origin: str
    enabled: bool
    approval_pins: tuple

    def binding(self):
        # Default UTC clock is deliberately not a configurable dependency.
        return ManagedHTTPBinding(self.site_id, self.database_sha256, self.origin,
            PinnedPolicyApprovalVerifier(self.approval_pins), enabled=self.enabled)


@dataclass(frozen=True, slots=True)
class ManagementRuntimeConfiguration:
    enabled: bool = False
    sites: tuple = ()
    source_sha256: str = ''


def _fail(code='RUNTIME_CONFIG_INVALID'):
    raise ContractError(code, 'management.runtime')


def _fields(row, required, optional=()):
    if type(row) is not dict or set(row) - set(required) - set(optional) or not set(required) <= set(row):
        _fail()
    return row


def _text(value, maximum=140):
    if (type(value) is not str or not value or value != value.strip() or len(value) > maximum
            or value.upper() == 'ALL' or '*' in value
            or any(ord(char) < 32 or ord(char) == 127 or 0xd800 <= ord(char) <= 0xdfff for char in value)):
        _fail()
    return value


def _boolean(value):
    if type(value) is not bool:
        _fail()
    return value


def _version(value):
    if type(value) is not int or not 1 <= value <= 2147483647:
        _fail()
    return value


def _hash(value):
    if type(value) is not str or not re.fullmatch(r'[0-9a-f]{64}', value):
        _fail()
    return value


def _origin(value):
    value = _text(value, 255)
    parsed = urlsplit(value)
    if (parsed.scheme not in ('http', 'https') or parsed.path or parsed.query or parsed.fragment
            or parsed.username or parsed.password or not parsed.hostname
            or value != parsed.scheme + '://' + parsed.netloc or parsed.netloc != parsed.netloc.lower()):
        _fail()
    host = parsed.hostname
    if ':' in host:
        ipaddress.IPv6Address(host)
        authority = '[' + host + ']'
    else:
        if not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?', host) or '..' in host:
            _fail()
        authority = host
    port = parsed.port
    if port is not None:
        if not 1 <= port <= 65535:
            _fail()
        authority += ':' + str(port)
    if parsed.netloc != authority:
        _fail()
    return value


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail()
        result[key] = value
    return result


def _json(raw):
    return json.loads(raw, object_pairs_hook=_pairs,
        parse_constant=lambda value: _fail())


def _pin(row, site, database):
    _fields(row, _PIN_KEYS)
    if row['site_id'] != site or row['database_sha256'] != database:
        _fail()
    require_uuid(row['policy_id'], 'management.runtime')
    _version(row['revision']); _version(row['authority_generation'])
    subject = _text(row['subject_user'])
    if subject == 'Guest':
        _fail()
    digest = _hash(row['content_digest'])
    _text(row['source_ref'])
    raw = _text(row['approval_json'], 4096)
    approval = _fields(_json(raw), _APPROVAL_KEYS)
    if canonical_json(approval) != raw:
        _fail()
    _text(approval['approval_ref'])
    actor = _text(approval['approved_by'])
    if actor in ('Guest', subject):
        _fail()
    approved_at = parse_rfc3339_utc(approval['approved_at_utc'])
    if approval['approved_at_utc'] != approved_at.isoformat():
        _fail()
    if (_version(approval['approved_revision']) != row['revision']
            or _version(approval['approved_authority_generation']) != row['authority_generation']
            or _hash(approval['content_digest']) != digest):
        _fail()
    return PolicyApprovalPin(**row)


def parse_management_runtime_config(raw):
    """Strict immutable syntax only; current policy/source checks remain native."""
    try:
        if type(raw) is not bytes or len(raw) > MAX_CONFIG_BYTES:
            _fail()
        row = _fields(_json(raw.decode('utf-8')), ('schema_version',), ('enabled', 'sites'))
        if type(row['schema_version']) is not int or row['schema_version'] != 1:
            _fail()
        enabled = _boolean(row.get('enabled', False))
        items = row.get('sites', [])
        if type(items) is not list or len(items) > 16:
            _fail()
        sites = []
        for item in items:
            _fields(item, ('site_id', 'database_sha256', 'origin'), ('enabled', 'approval_pins'))
            site, database, origin = _text(item['site_id']), _hash(item['database_sha256']), _origin(item['origin'])
            active = _boolean(item.get('enabled', False))
            rows = item.get('approval_pins', [])
            if type(rows) is not list or len(rows) > 128 or (active and not rows):
                _fail()
            pins = tuple(_pin(pin, site, database) for pin in rows)
            if len({pin.policy_id for pin in pins}) != len(pins):
                _fail()
            sites.append(ManagementSiteConfiguration(site, database, origin, active, pins))
        if (len({site.site_id for site in sites}) != len(sites)
                or len({site.origin for site in sites}) != len(sites)
                or (enabled and not any(site.enabled for site in sites))):
            _fail()
        return ManagementRuntimeConfiguration(enabled, tuple(sites), hashlib.sha256(raw).hexdigest())
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError, ContractError):
        _fail()


def load_management_runtime_config(path=None):
    """Read one owned private regular file, never an HTTP-selected path.

    A protected immediate directory and no symlink anywhere in the canonical
    path are required. Atomic replacement is supported; an in-read replacement
    or mutation is rejected. No fallback copy or binding is retained.
    """
    if path is None:
        return ManagementRuntimeConfiguration()
    fd = None
    try:
        if type(path) is not str or not Path(path).is_absolute() or Path(path).suffix != '.json':
            _fail('RUNTIME_CONFIG_UNAVAILABLE')
        file = Path(path)
        if str(file) != path or file.resolve(strict=True) != file or any(p.is_symlink() for p in (file, *file.parents)):
            _fail('RUNTIME_CONFIG_UNAVAILABLE')
        parent = file.parent.stat()
        if parent.st_uid != os.geteuid() or stat.S_IMODE(parent.st_mode) != 0o700:
            _fail('RUNTIME_CONFIG_UNAVAILABLE')
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != os.geteuid()
                or stat.S_IMODE(before.st_mode) != 0o600 or before.st_nlink != 1
                or before.st_size > MAX_CONFIG_BYTES):
            _fail('RUNTIME_CONFIG_UNAVAILABLE')
        with os.fdopen(fd, 'rb') as handle:
            fd = None
            raw = handle.read(MAX_CONFIG_BYTES + 1)
            after = os.fstat(handle.fileno())
            current = file.stat(follow_symlinks=False)
        signature = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
                                  info.st_ctime_ns, info.st_uid, info.st_mode, info.st_nlink)
        if signature(before) != signature(after) or signature(after) != signature(current):
            _fail('RUNTIME_CONFIG_UNAVAILABLE')
        return parse_management_runtime_config(raw)
    except (OSError, ValueError, TypeError, RuntimeError, ContractError):
        _fail('RUNTIME_CONFIG_UNAVAILABLE')
    finally:
        if fd is not None:
            os.close(fd)


def _closed(start_response, code='NOT_SUPPORTED'):
    status = {'NOT_SUPPORTED': '501 Not Implemented', 'FORBIDDEN': '403 Forbidden',
              'CONFLICT_RETRY_REQUIRED': '409 Conflict', 'SOURCE_UNAVAILABLE': '503 Service Unavailable'}[code]
    messages = {'NOT_SUPPORTED': '管理查询尚未启用。', 'FORBIDDEN': '请求来源或方法校验未通过。',
                'CONFLICT_RETRY_REQUIRED': '查询配置已变化，请重新发起查询。',
                'SOURCE_UNAVAILABLE': '管理查询暂时无法完成。'}
    payload = json.dumps(error_response(PortalException(code, messages[code],
        retryable=code in ('CONFLICT_RETRY_REQUIRED', 'SOURCE_UNAVAILABLE'))), ensure_ascii=False).encode('utf-8')
    start_response(status, [('Content-Type', 'application/json; charset=utf-8'),
        ('Cache-Control', 'private, no-store, max-age=0'), ('Content-Length', str(len(payload)))])
    return [payload]


class QueryRuntimeApplication:
    """Only four exact routes receive freshly checked private query capability."""
    def __init__(self, application, configuration_path=None):
        if not callable(application):
            _fail()
        self.application = application
        self.configuration_path = configuration_path

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        if path not in tuple(QUERY_PREFIX + query for query in QUERIES):
            return self.application(environ, start_response)
        try:
            config = load_management_runtime_config(self.configuration_path)
        except ContractError:
            return _closed(start_response)
        if not config.enabled:
            return _closed(start_response)
        if environ.get('REQUEST_METHOD') != 'GET':
            return _closed(start_response, 'FORBIDDEN')
        # Forwarded host/scheme and client Site headers never establish trust.
        origin = str(environ.get('wsgi.url_scheme', '')) + '://' + str(environ.get('HTTP_HOST', ''))
        matches = tuple(site for site in config.sites if site.enabled and site.origin == origin)
        if len(matches) != 1:
            return _closed(start_response, 'FORBIDDEN')
        application = ManagedQueryHTTPApplication(self.application, binding=matches[0].binding(),
            require_structure_preflight=True)
        captured, chunks, size = {}, [], 0
        iterator = None
        def append(chunk):
            nonlocal size
            if type(chunk) is not bytes:
                _fail()
            size += len(chunk)
            if size > MAX_RESPONSE_BYTES:
                _fail()
            chunks.append(chunk)
        def buffered_start(status, headers, exc_info=None):
            captured.update(status=status, headers=list(headers))
            return append
        try:
            iterator = application(environ, buffered_start)
            for chunk in iterator:
                append(chunk)
            closing, iterator = iterator, None
            if hasattr(closing, 'close'):
                closing.close()
            if not captured:
                _fail()
        except BaseException:
            return _closed(start_response, 'SOURCE_UNAVAILABLE')
        finally:
            if iterator is not None and hasattr(iterator, 'close'):
                try:
                    iterator.close()
                except BaseException:
                    # Body is already withheld after an iteration/close failure.
                    pass
        try:
            current = load_management_runtime_config(self.configuration_path)
        except ContractError:
            return _closed(start_response)
        if not current.enabled:
            return _closed(start_response)
        if current.source_sha256 != config.source_sha256:
            return _closed(start_response, 'CONFLICT_RETRY_REQUIRED')
        start_response(captured['status'], captured['headers'])
        return chunks


def create_management_query_application(application, *, configuration_path=None):
    """Explicit server assembly; never replace frappe.app.application globally."""
    return QueryRuntimeApplication(application, configuration_path)
