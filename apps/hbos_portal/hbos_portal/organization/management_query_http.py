"""Default-closed GET projections with fresh authority checks before release.

The native GET rollback completes before final revalidation. Both checkpoints
use the same real request DB/session, current root-locked policy/source reads.
No relation write, permission grant, production binding or schema is installed.
"""
from contextvars import ContextVar
import json
import re
import secrets
from urllib.parse import urlsplit

from hbos_portal.authorization.errors import ContractError
from hbos_portal.contracts.errors import PortalException, error_response, new_trace_id
from .frappe_management_repository import FrappeManagementPolicyRepository
from .frappe_repository import FrappeRelationRepository
from .frappe_source_loader import FrappeLockedSourceLoader
from .management_http import (
    PREFIX, ManagedHTTPBinding, _CommitGate, _RequestAborted, _RequestScope,
    _error_http, _portal_error, _remember_error,
)
from .management_queries import ManagementQueryService
from .management_storage import PinnedPolicyApprovalVerifier

QUERY_PREFIX = PREFIX
QUERIES = ("get_management_context", "list_positions", "get_person_assignments", "lookup_people")
_QueryScope = _RequestScope
_query_scope = ContextVar("hbos_managed_query_request", default=None)
_structure_preflight_required = ContextVar("hbos_managed_query_structure_preflight", default=False)
_PARAMETERS = {
    "get_management_context": frozenset(),
    "list_positions": frozenset(("page", "page_size", "company_id", "department_id", "q")),
    "get_person_assignments": frozenset(("employee_id", "page", "page_size")),
    "lookup_people": frozenset(("page", "page_size", "company_id", "department_id", "q")),
}


def _validate_query(native, scope, query):
    binding = scope.binding
    if (type(binding) is not ManagedHTTPBinding or binding.enabled is not True
            or type(binding.approval_verifier) is not PinnedPolicyApprovalVerifier
            or not callable(binding.clock) or query not in QUERIES or scope.command != query):
        raise ContractError("QUERY_BINDING_REQUIRED", "query")
    origin = urlsplit(binding.origin)
    if (not binding.site_id or native.local.site != binding.site_id
            or not re.fullmatch(r"[0-9a-f]{64}", binding.database_sha256)
            or origin.scheme not in ("http", "https") or not origin.netloc
            or origin.path or origin.query or origin.fragment or origin.username or origin.password):
        raise ContractError("QUERY_BINDING_REQUIRED", "query")
    request = native.local.request
    if request.method != "GET" or request.path != QUERY_PREFIX + query:
        raise ContractError("METHOD_NOT_ALLOWED", "query")
    if not native.session.user or native.session.user == "Guest":
        raise ContractError("UNAUTHENTICATED", "query")
    sid = str(getattr(native.session, "sid", "") or "")
    if (not sid or sid == "Guest" or request.cookies.get("sid") != sid
            or request.headers.get("Authorization")):
        raise ContractError("COOKIE_SESSION_REQUIRED", "query")
    # Browsers can omit Origin on same-origin GET. A present Origin must match;
    # the fixed actual host and mandatory saved-session CSRF token still apply.
    request_origin = request.headers.get("Origin")
    if ((request_origin is not None and request_origin != binding.origin)
            or request.headers.get("Sec-Fetch-Site") == "cross-site"
            or request.scheme + "://" + request.host != binding.origin):
        raise ContractError("INVALID_ORIGIN", "query")
    expected = str(native.session.data.get("csrf_token") or "")
    actual = request.headers.get("X-Frappe-CSRF-Token") or ""
    if not expected or not secrets.compare_digest(expected, actual):
        raise ContractError("CSRF_REQUIRED", "query")
    if request.get_data(cache=True) or set(request.args) - _PARAMETERS[query]:
        raise ContractError("INVALID_REQUEST", "query")
    params = {}
    for key in request.args:
        values = request.args.getlist(key)
        if len(values) != 1 or not isinstance(values[0], str):
            raise ContractError("INVALID_REQUEST", "query")
        value = values[0]
        if key in ("page", "page_size"):
            if not re.fullmatch(r"[0-9]{1,5}", value):
                raise ContractError("INVALID_REQUEST", "query")
            value = int(value)
        params[key] = value
    return params


def _make_query_service(native, binding):
    relations = FrappeRelationRepository(native=native, enabled=True)
    policies = FrappeManagementPolicyRepository(relations, enabled=True,
        expected_site=binding.site_id, expected_database_sha256=binding.database_sha256)
    sources = FrappeLockedSourceLoader(relations, expected_site=binding.site_id,
        expected_database_sha256=binding.database_sha256, enabled=True)
    return ManagementQueryService(relations, policies, source_loader=sources,
        clock=binding.clock, approval_verifier=binding.approval_verifier, enabled=True)


class _ReadGate(_CommitGate):
    """Reject all relation commits, allowing only exact native session upkeep."""
    def commit(self, *args, **kwargs):
        if self.phase == "session_tail":
            return self._commit_session_tail(*args, **kwargs)
        raise _RequestAborted("management queries cannot commit relation facts")

    def abort(self, error, *, unknown=False):
        # A query has no fact-save result. Even session-maintenance failure must
        # withhold its data, without suggesting that a relation was saved.
        _remember_error(self.scope, error)
        self.phase = "aborted"
        if self.service is not None:
            self.service.discard_pending()
        self.database.before_commit.reset()
        self.database.after_commit.reset()
        if getattr(self.native.local, "db", None) is not self.database:
            # Native response cleanup may already have closed/unbound this DB.
            # rollback() could lazily reopen it outside the destroyed request.
            self._poison()
            return
        try:
            self.database.rollback()
        except BaseException:
            self.scope.error = PortalException("SOURCE_UNAVAILABLE", "查询事务未能安全结束，请稍后重试。",
                retryable=True, trace_id=new_trace_id())
            self._poison()
            raise _RequestAborted("management query rollback failed") from None
        if unknown:
            self._poison()

    def finalize(self):
        if (self.phase != "pending" or self.native.local.db is not self.database
                or self.native.local.session is not self.session_state
                or getattr(self.native.session, "sid", None) != self.session_sid
                or self.native.session.user != self.session_actor):
            raise ContractError("MANAGEMENT_CONTEXT_MISMATCH", "query")
        # Native sync_database has already rolled back this GET. This fresh
        # checkpoint reacquires the root and reads current state, never old RR.
        checked = self.service.recheck_pending(self.proof)
        if checked != self.result:
            raise ContractError("SOURCE_CHANGED_RETRY", "query")
        self.database.rollback()
        # This phase is only compatibility with exact native Session.update;
        # facts_committed remains False, and no saved/committed flag is returned.
        self.phase = "committed"


def execute_query(query):
    import frappe
    scope = _query_scope.get()
    frappe.flags.disable_traceback = True
    frappe.local.response_headers["Cache-Control"] = "private, no-store, max-age=0"
    frappe.local.form_dict.clear()
    if scope is None:
        frappe.db.rollback()
        frappe.local.response["http_status_code"] = 503
        return error_response(_portal_error(ContractError("QUERY_BINDING_REQUIRED", "query")))
    try:
        if scope.gate is not None:
            raise ContractError("MULTIPLE_COMMANDS", "query")
        gate = _ReadGate(frappe, None, scope)
        scope.gate = gate
        gate.install()
        params = _validate_query(frappe, scope, query)
        if _structure_preflight_required.get():
            from .management_preflight import preflight_management_structure
            preflight_management_structure(frappe, expected_site=scope.binding.site_id,
                expected_database_sha256=scope.binding.database_sha256)
        service = _make_query_service(frappe, scope.binding)
        gate.service = service
        data = service.execute(query, params)
        gate.set_pending(data, service.pending_proof)
        return {"ok": True, "data": data}
    except BaseException as error:
        if scope.gate is not None:
            scope.gate.abort(error)
        else:
            _remember_error(scope, error)
            frappe.db.rollback()
        raise frappe.PermissionError("管理查询未完成。") from None


class ManagedQueryHTTPApplication:
    """Buffer only exact management GET routes; unrelated requests pass through."""
    def __init__(self, application, binding=None, *, require_structure_preflight=False):
        if type(require_structure_preflight) is not bool:
            raise ValueError("invalid query preflight configuration")
        self.application, self.binding = application, binding
        self.require_structure_preflight = require_structure_preflight

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")
        query = path[len(QUERY_PREFIX):] if path.startswith(QUERY_PREFIX) else None
        if query not in QUERIES:
            return self.application(environ, start_response)
        scope = _QueryScope(self.binding, query)
        token = _query_scope.set(scope)
        preflight_token = _structure_preflight_required.set(self.require_structure_preflight)
        captured, chunks = {}, []
        iterator = None

        def buffered_start(status, headers, exc_info=None):
            captured.update(status=status, headers=list(headers))
            return chunks.append

        try:
            iterator = self.application(environ, buffered_start)
            chunks.extend(iterator)
            if not captured:
                raise _RequestAborted("management query response missing")
            if scope.error is None and scope.gate is None:
                code = ("QUERY_BINDING_REQUIRED" if captured["status"].startswith("2") else
                        {"400": "INVALID_REQUEST", "401": "UNAUTHENTICATED", "403": "METHOD_NOT_ALLOWED",
                         "405": "METHOD_NOT_ALLOWED"}.get(captured["status"].split(" ", 1)[0],
                                                           "SOURCE_NATIVE_REQUEST_FAILED"))
                _remember_error(scope, ContractError(code, "query"))
            if scope.error is None and scope.gate is not None:
                if not captured["status"].startswith("2"):
                    raise _RequestAborted("management query serialization failed")
                scope.gate.finalize()
                scope.gate.prepare_session_tail()
            close = getattr(iterator, "close", None)
            if close is not None:
                close()
            iterator = None
        except BaseException as error:
            if scope.error is None:
                if scope.gate is not None:
                    try:
                        scope.gate.abort(error)
                    except BaseException:
                        pass  # Recorded terminal rollback failure; no data release.
                else:
                    _remember_error(scope, error)
        finally:
            try:
                if iterator is not None and getattr(iterator, "close", None) is not None:
                    iterator.close()
            except BaseException as error:
                _remember_error(scope, error)
            try:
                import frappe
                if getattr(frappe.local, "db", None) is not None:
                    try:
                        if scope.error is not None:
                            frappe.db.close()
                    finally:
                        frappe.destroy()
            except BaseException as error:
                _remember_error(scope, error)
            finally:
                try:
                    if scope.gate is not None:
                        scope.gate.restore()
                finally:
                    _query_scope.reset(token)
                    _structure_preflight_required.reset(preflight_token)
        if scope.error is not None:
            status, headers, chunks = _error_http(scope)
        else:
            status, headers = captured["status"], captured["headers"]
        headers = [(key, value) for key, value in headers if key.lower() != "cache-control"]
        headers.append(("Cache-Control", "private, no-store, max-age=0"))
        start_response(status, headers)
        return chunks
