"""Offline, deny-by-default policy for the proposed owned restore HTTP relay.

No listener, Docker invocation, socket, subprocess or HTTP transport exists in
this module. TRANSPORT_STATE remains NOT_IMPLEMENTED. The outer transport must
bind a freshly inspected VerifiedResource and invalidate old clone Sessions;
an ID-shaped string or a Cookie is not proof of resource/session ownership.
The native page outline is allowed, not complete login or business-page runtime.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from email.utils import parsedate_to_datetime
import json
import math
import re
from urllib.parse import parse_qsl

from .common import BENCH, DOCKER, HOST, ORIGIN, RestoreError


TRANSPORT_STATE = "NOT_IMPLEMENTED"
MAX_REQUEST_BODY_BYTES = 16 * 1024
MAX_RESPONSE_BODY_BYTES = 8 * 1024 * 1024
MAX_HEADERS = 32
MAX_HEADER_BYTES = 16 * 1024
MAX_HEADER_VALUE_BYTES = 4096
MAX_TARGET_BYTES = 2048
MAX_STATIC_PATHS = 256
CONNECT_TIMEOUT_SECONDS = 2
READ_TIMEOUT_SECONDS = 5
TOTAL_TIMEOUT_SECONDS = 10
MAX_CONCURRENT_REQUESTS = 1
# These timeout/concurrency values are transport requirements, not implemented
# timers or a running semaphore. An eventual transport must enforce them.

HTML_CSP = (
    "default-src 'none'; base-uri 'none'; object-src 'none'; "
    "frame-ancestors 'none'; frame-src 'none'; form-action 'self'; "
    "connect-src 'self'; script-src 'self'; style-src 'self'; "
    "img-src 'self' data:; font-src 'self'; worker-src 'none'; "
    "manifest-src 'none'; sandbox allow-forms allow-same-origin"
)

_READ_ROUTES = {
    "/api/method/frappe.ping": "native_ping",
    "/api/method/frappe.auth.get_logged_user": "native_identity",
    "/login": "native_login_outline",
    "/desk": "native_desk_outline",
}
_LOGIN_ROUTE = "/api/method/login"
_COOKIE_NAMES = frozenset({"sid", "system_user", "full_name", "user_id", "user_image", "user_lang"})
_REQUEST_HEADERS = frozenset({
    "host", "origin", "content-type", "content-length", "cookie", "accept",
    "accept-encoding", "accept-language", "user-agent", "referer",
    "x-frappe-csrf-token", "sec-fetch-site", "sec-fetch-mode", "sec-fetch-dest",
})
_RESPONSE_HEADERS = frozenset({
    "content-type", "content-length", "location", "set-cookie", "cache-control",
    "pragma", "content-security-policy", "x-content-type-options",
    "referrer-policy", "x-frame-options",
})
_CONTENT_TYPES = frozenset({
    "text/html", "application/json", "text/plain", "text/css",
    "application/javascript", "text/javascript", "image/png", "image/jpeg",
    "image/webp", "image/svg+xml", "image/x-icon", "font/woff", "font/woff2",
})
_RESPONSE_STATUSES = frozenset({
    200, 204, 301, 302, 303, 307, 308, 400, 401, 403, 404, 405, 409, 413,
    415, 429, 500, 502, 503,
})
_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
_TOKEN = re.compile(r"[!#$%&'*+.^_`|~0-9A-Za-z-]{1,64}\Z")
_ID = re.compile(r"[0-9a-f]{64}\Z")
_STATIC_SEGMENT = re.compile(r"[A-Za-z0-9._-]+\Z")
_STATIC_EXTENSIONS = frozenset({"css", "js", "woff", "woff2", "png", "jpg", "jpeg", "svg", "ico", "webp"})
_UPSTREAM_ERROR_BODY = b'{"error":"RESTORE_RELAY_UPSTREAM_REJECTED"}'


@dataclass(frozen=True, slots=True)
class AllowedRequest:
    method: str
    route_id: str
    target: str
    headers: tuple[tuple[str, str], ...] = field(repr=False)
    body: bytes = field(repr=False)


@dataclass(frozen=True, slots=True)
class AllowedResponse:
    status: int
    headers: tuple[tuple[str, str], ...] = field(repr=False)
    body: bytes = field(repr=False)


def _reject(code: str):
    raise RestoreError(code) from None


def _checked_headers(headers, code: str, *, response: bool = False):
    if type(headers) is not list or len(headers) > MAX_HEADERS:
        _reject(code)
    checked = []
    seen = set()
    byte_count = 0
    for pair in headers:
        if type(pair) is not tuple or len(pair) != 2:
            _reject(code)
        key, value = pair
        if type(key) is not str or type(value) is not str or not _TOKEN.fullmatch(key):
            _reject(code)
        if not value.isascii() or any(ord(char) < 32 or ord(char) == 127 for char in value):
            _reject(code)
        if len(value) > MAX_HEADER_VALUE_BYTES:
            _reject(code)
        byte_count += len(key) + len(value) + 4
        if byte_count > MAX_HEADER_BYTES:
            _reject(code)
        name = key.lower()
        if name in seen and not (response and name == "set-cookie"):
            _reject(code)
        seen.add(name)
        checked.append((name, value))
    return checked


def _content_length(value: str, body: bytes, code: str):
    if not re.fullmatch(r"0|[1-9][0-9]{0,8}", value) or int(value) != len(body):
        _reject(code)


def _safe_target(target: str, code: str):
    if type(target) is not str or not target.isascii() or not 1 <= len(target) <= MAX_TARGET_BYTES:
        _reject(code)
    if not target.startswith("/") or target.startswith("//"):
        _reject(code)
    if any(char in target for char in ("%", "?", "#", "\\", ":")):
        _reject(code)
    if any(ord(char) <= 32 or ord(char) == 127 for char in target) or "//" in target:
        _reject(code)
    if any(part in (".", "..") for part in target.split("/")):
        _reject(code)


def _static_manifest(paths, code: str):
    if type(paths) is not frozenset or len(paths) > MAX_STATIC_PATHS:
        _reject(code)
    for path in paths:
        _safe_target(path, code)
        if not path.startswith("/assets/") or path.endswith("/"):
            _reject(code)
        parts = path.split("/")[2:]
        if not parts or any(not _STATIC_SEGMENT.fullmatch(part) for part in parts):
            _reject(code)
        if path.rsplit(".", 1)[-1].lower() not in _STATIC_EXTENSIONS:
            _reject(code)


def _cookie_value(value: str, code: str):
    if not value or len(value) > 1024 or any(char.isspace() or char in ';,"\\' for char in value):
        _reject(code)


def _request_cookie(value: str, code: str):
    seen = set()
    sid = None
    for part in value.split(";"):
        name, equals, cookie = part.strip().partition("=")
        if not equals or name not in _COOKIE_NAMES or name in seen:
            _reject(code)
        if cookie or name != "user_image":
            _cookie_value(cookie, code)
        seen.add(name)
        if name == "sid":
            sid = "sid=" + cookie
    # Only the native session cookie is forwarded. The reviewed presentation
    # cookies may arrive from the browser but never become identity parameters.
    return sid


def _login_form(body: bytes, code: str):
    try:
        encoded = body.decode("utf-8", errors="strict")
    except UnicodeError:
        _reject(code)
    if not encoded or any(ord(char) < 32 or ord(char) == 127 for char in encoded):
        _reject(code)
    parts = encoded.split("&")
    if len(parts) != 2 or {part.partition("=")[0] for part in parts} != {"usr", "pwd"}:
        _reject(code)
    for match in re.finditer("%", encoded):
        if not re.fullmatch(r"[0-9A-Fa-f]{2}", encoded[match.start() + 1:match.start() + 3]):
            _reject(code)
    try:
        pairs = parse_qsl(encoded, keep_blank_values=True, strict_parsing=True, encoding="utf-8", errors="strict", max_num_fields=2)
    except (ValueError, UnicodeError):
        _reject(code)
    values = dict(pairs)
    if len(pairs) != 2 or set(values) != {"usr", "pwd"}:
        _reject(code)
    if not 1 <= len(values["usr"]) <= 254 or not 1 <= len(values["pwd"]) <= 1024:
        _reject(code)
    if any(ord(char) < 32 or ord(char) == 127 for value in values.values() for char in value):
        _reject(code)


def validate_request(method: str, target: str, headers: list[tuple[str, str]], body: bytes,
                     *, approved_static_paths: frozenset[str] = frozenset()) -> AllowedRequest:
    code = "RELAY_REQUEST_REJECTED"
    if type(method) is not str or method not in ("GET", "POST") or type(body) is not bytes:
        _reject(code)
    if len(body) > MAX_REQUEST_BODY_BYTES:
        _reject(code)
    _safe_target(target, code)
    _static_manifest(approved_static_paths, code)
    if method == "GET" and target in _READ_ROUTES:
        route = _READ_ROUTES[target]
    elif method == "GET" and target in approved_static_paths:
        route = "approved_static_asset"
    elif method == "POST" and target == _LOGIN_ROUTE:
        route = "native_password_login"
    else:
        _reject(code)
    values = _checked_headers(headers, code)
    if any(key not in _REQUEST_HEADERS for key, _ in values):
        _reject(code)
    by_name = dict(values)
    if by_name.get("host") != HOST:
        _reject(code)
    if "origin" in by_name and by_name["origin"] != ORIGIN:
        _reject(code)
    if by_name.get("sec-fetch-site") not in (None, "none", "same-origin"):
        _reject(code)
    if by_name.get("sec-fetch-mode") not in (None, "navigate", "same-origin", "cors", "no-cors"):
        _reject(code)
    if by_name.get("sec-fetch-dest") not in (None, "empty", "document", "script", "style", "image", "font"):
        _reject(code)
    if "referer" in by_name and by_name["referer"] not in (ORIGIN, ORIGIN + "/login", ORIGIN + "/desk"):
        _reject(code)
    if "content-length" in by_name:
        _content_length(by_name["content-length"], body, code)
    if method == "GET":
        if body or "content-type" in by_name:
            _reject(code)
    else:
        if by_name.get("origin") != ORIGIN:
            _reject(code)
        if by_name.get("content-type", "").lower() not in (
            "application/x-www-form-urlencoded", "application/x-www-form-urlencoded; charset=utf-8",
        ):
            _reject(code)
        _login_form(body, code)
    sid = _request_cookie(by_name["cookie"], code) if "cookie" in by_name else None
    forwarded = [(key, value) for key, value in values if key not in ("cookie", "content-length", "accept-encoding")]
    if sid is not None:
        forwarded.append(("cookie", sid))
    forwarded.extend((("accept-encoding", "identity"), ("content-length", str(len(body)))))
    return AllowedRequest(method, route, target, tuple(forwarded), body)


def _response_cookie(value: str, code: str):
    parts = value.split(";")
    name, equals, cookie = parts[0].strip().partition("=")
    if not equals or name not in _COOKIE_NAMES:
        _reject(code)
    if cookie:
        _cookie_value(cookie, code)
    attributes = {}
    for part in parts[1:]:
        key, equals, attribute = part.strip().partition("=")
        key = key.lower()
        if key in attributes or key not in {"path", "expires", "max-age", "httponly", "secure", "samesite"}:
            _reject(code)
        if key in {"httponly", "secure"}:
            if equals:
                _reject(code)
        elif not equals:
            _reject(code)
        attributes[key] = attribute
    if attributes.get("path") != "/" or (name == "sid" and "httponly" not in attributes):
        _reject(code)
    if "samesite" in attributes and attributes["samesite"].lower() not in {"lax", "strict"}:
        _reject(code)
    if "max-age" in attributes and not re.fullmatch(r"-?[0-9]{1,10}", attributes["max-age"]):
        _reject(code)
    if "expires" in attributes:
        try:
            if parsedate_to_datetime(attributes["expires"]).tzinfo is None:
                _reject(code)
        except (ValueError, TypeError, OverflowError):
            _reject(code)
    if not cookie and name != "user_image" and not (attributes.get("max-age") in {"0", "-1"} or "expires" in attributes):
        _reject(code)
    # Host-only cookies: Domain is never accepted, including a leading-dot or
    # exact-host Domain. Preserve each separate Set-Cookie; add a safe default.
    return name, value if "samesite" in attributes else value + "; SameSite=Lax"


def _json_redirects(body: bytes, code: str):
    """Native JSON redirects have the same finite boundary as Location.

    Validate the whole finite JSON structure iteratively; duplicate keys and
    non-finite numbers are rejected before a browser can choose another value.
    This does not admit password-reset or other authentication flows.
    """
    # Conservative lexical quota before allocating the parsed object graph.
    if body.count(b",") + body.count(b":") > 16384:
        _reject(code)

    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                _reject(code)
            result[key] = value
        return result

    def constant(_value):
        _reject(code)

    try:
        document = json.loads(body.decode("utf-8", errors="strict"),
                              object_pairs_hook=pairs, parse_constant=constant)
        stack = [(document, 0)]
        nodes = 0
        while stack:
            value, depth = stack.pop()
            nodes += 1
            if depth > 32 or nodes > 16384:
                _reject(code)
            if type(value) is dict:
                for key, child in value.items():
                    if key in {"home_page", "redirect_to"} and child not in (
                        "/login", "/desk", ORIGIN + "/login", ORIGIN + "/desk"
                    ):
                        _reject(code)
                    stack.append((child, depth + 1))
            elif type(value) is list:
                stack.extend((child, depth + 1) for child in value)
            elif type(value) is float and not math.isfinite(value):
                _reject(code)
    except (ValueError, UnicodeError, RecursionError, TypeError):
        _reject(code)


def validate_response(status: int, headers: list[tuple[str, str]], body: bytes) -> AllowedResponse:
    code = "RELAY_RESPONSE_REJECTED"
    if type(status) is not int or status not in _RESPONSE_STATUSES or type(body) is not bytes:
        _reject(code)
    if len(body) > MAX_RESPONSE_BODY_BYTES or (status == 204 and body):
        _reject(code)
    values = _checked_headers(headers, code, response=True)
    if any(key not in _RESPONSE_HEADERS for key, _ in values):
        _reject(code)
    singleton = {key: value for key, value in values if key != "set-cookie"}
    if "content-length" in singleton:
        _content_length(singleton["content-length"], body, code)
    content_type = singleton.get("content-type", "").lower()
    if body and content_type not in _CONTENT_TYPES and content_type not in {
        value + "; charset=utf-8" for value in _CONTENT_TYPES
    }:
        _reject(code)
    if body and status < 400 and content_type.split(";", 1)[0] == "application/json":
        _json_redirects(body, code)
    if status in _REDIRECT_STATUSES and "location" not in singleton:
        _reject(code)
    if "location" in singleton:
        location = singleton["location"]
        if status not in _REDIRECT_STATUSES or location not in ("/login", "/desk", ORIGIN + "/login", ORIGIN + "/desk"):
            _reject(code)
    forwarded = []
    cookies = set()
    for key, value in values:
        if key == "set-cookie":
            name, value = _response_cookie(value, code)
            if name in cookies:
                _reject(code)
            cookies.add(name)
            forwarded.append(("set-cookie", value))
        elif key in {"content-type", "location"} and not (status >= 400 and key == "content-type"):
            forwarded.append((key, value))
    if status >= 400:
        # Native debug/error bodies may contain traceback, SQL or credentials.
        # The policy never publishes those bodies or includes them in an error.
        body = _UPSTREAM_ERROR_BODY
        forwarded.append(("content-type", "application/json"))
    forwarded.extend((
        ("content-length", str(len(body))), ("cache-control", "no-store"),
        ("pragma", "no-cache"), ("content-security-policy", HTML_CSP),
        ("x-content-type-options", "nosniff"), ("referrer-policy", "no-referrer"),
        ("x-frame-options", "DENY"),
    ))
    return AllowedResponse(status, tuple(forwarded), body)


def build_exec_argv(new_backend_id: str, original_ids: tuple[str, ...] | frozenset[str]) -> tuple[str, ...]:
    """Return an unexecuted fixed argv; fresh owned-resource binding is external."""
    code = "RELAY_RESOURCE_REJECTED"
    if type(new_backend_id) is not str or not _ID.fullmatch(new_backend_id):
        _reject(code)
    if type(original_ids) not in (tuple, frozenset) or not original_ids:
        _reject(code)
    if any(type(value) is not str or not _ID.fullmatch(value) for value in original_ids):
        _reject(code)
    if len(set(original_ids)) != len(original_ids) or new_backend_id in original_ids:
        _reject(code)
    return (DOCKER, "exec", "-i", "--user", "1000:1000", new_backend_id,
            BENCH + "/env/bin/python", "-B", "/run/hbos-restore/forward.py")
