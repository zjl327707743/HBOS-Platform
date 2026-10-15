"""Default-closed WSGI boundary for four managed relation POST operations.

The wrapper must be explicitly installed with reviewed server-side bindings.
Native Frappe routes without this request-local capability remain closed.
No Site configuration, real approval, schema or business grant is created here.
"""
from contextvars import ContextVar
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import logging
import re
import secrets
from urllib.parse import urlsplit

from hbos_portal.authorization.errors import ContractError
from hbos_portal.contracts.errors import PortalException, error_response, new_trace_id
from .frappe_management_repository import FrappeManagementPolicyRepository
from .frappe_repository import FrappeRelationRepository
from .frappe_source_loader import FrappeLockedSourceLoader
from .managed_relations import ManagedRelationAdapter
from .management_storage import PinnedPolicyApprovalVerifier
from .relation_service import RelationService

PREFIX = "/api/method/hbos_portal.api.organization_relations."
COMMANDS = ("create_position", "update_position", "create_assignment", "update_assignment")
MAX_BODY = 16 * 1024
_request_scope = ContextVar("hbos_managed_http_request", default=None)


def _utc_now():
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class ManagedHTTPBinding:
    site_id: str
    database_sha256: str
    origin: str
    approval_verifier: object
    clock: object = _utc_now
    enabled: bool = False


@dataclass
class _RequestScope:
    binding: object
    command: str
    gate: object = None
    error: object = None


class _RequestAborted(RuntimeError):
    """No payload is included in transport or lifecycle exceptions."""


def _portal_error(error, *, unknown=False):
    if unknown:
        return PortalException("SAVE_RESULT_UNKNOWN",
            "保存结果待确认，请使用原幂等键和相同内容重新核对。",
            retryable=True, trace_id=new_trace_id())
    code = getattr(error, "code", None)
    if code in {"QUERY_BINDING_REQUIRED", "QUERY_READS_DISABLED"}:
        public, message, retry = "NOT_SUPPORTED", "管理查询尚未启用。", False
    elif code in {"WRITES_DISABLED", "MANAGEMENT_ADAPTER_DISABLED", "HTTP_BINDING_REQUIRED"}:
        public, message, retry = "NOT_SUPPORTED", "人员事实写入尚未启用。", False
    elif code in {"IDEMPOTENCY_CONFLICT", "REVISION_CONFLICT"}:
        public, message, retry = "CONFLICT", "记录或幂等请求已变化，请核对后重新发起。", False
    elif code in {"RELATION_TRANSACTION_RETRY_REQUIRED", "SOURCE_CHANGED_RETRY",
                  "MANAGEMENT_CHANGED_RETRY", "PENDING_FACT_CHANGED"}:
        public, message, retry = "CONFLICT_RETRY_REQUIRED", "事务上下文已变化，请重新发起完整请求。", True
    elif code in {"INVALID_REQUEST", "INVALID_VERSION", "INVALID_TEXT", "INVALID_UUID",
                  "INVALID_JSON", "REQUEST_TOO_LARGE", "UNKNOWN_COMMAND", "INVALID_UTC"}:
        public, message, retry = "INVALID_REQUEST", "请求字段或格式无效。", False
    elif code in {"UNAUTHENTICATED"}:
        public, message, retry = "UNAUTHENTICATED", "请先登录。", False
    elif code in {"CSRF_REQUIRED", "INVALID_ORIGIN", "COOKIE_SESSION_REQUIRED", "METHOD_NOT_ALLOWED"}:
        public, message, retry = "FORBIDDEN", "请求会话、来源或方法校验未通过。", False
    elif isinstance(error, ContractError) and not code.startswith(("SOURCE_", "UNSUPPORTED_SOURCE",
            "STORAGE_", "INCOMPLETE_", "HISTORY_", "PENDING_PROOF_")):
        public, message, retry = "FORBIDDEN", "你没有维护这些人员事实的权限。", False
    else:
        public, message, retry = "SOURCE_UNAVAILABLE", "人员事实服务暂时不可用。", True
    return PortalException(public, message, retryable=retry, trace_id=new_trace_id())


def _remember_error(scope, error, *, unknown=False):
    if scope.error is None:
        scope.error = _portal_error(error, unknown=unknown)
        try:
            # No request body, personnel ID, raw traceback or DB audit write.
            logging.getLogger("hbos_portal.organization").warning(
                "managed request rejected code=%s trace=%s",
                scope.error.error.code, scope.error.error.trace_id)
        except Exception:
            # Audit failure never converts a denied operation into permission.
            pass


def _duplicate_safe(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ContractError("INVALID_JSON", "request")
        result[key] = value
    return result


def _validate_request(native, scope, command):
    binding = scope.binding
    if (type(binding) is not ManagedHTTPBinding or binding.enabled is not True
            or type(binding.approval_verifier) is not PinnedPolicyApprovalVerifier
            or not callable(binding.clock) or command not in COMMANDS or scope.command != command):
        raise ContractError("HTTP_BINDING_REQUIRED", "request")
    origin = urlsplit(binding.origin)
    if (not binding.site_id or native.local.site != binding.site_id
            or not re.fullmatch(r"[0-9a-f]{64}", binding.database_sha256)
            or origin.scheme not in ("http", "https") or not origin.netloc
            or origin.path or origin.query or origin.fragment or origin.username or origin.password):
        raise ContractError("HTTP_BINDING_REQUIRED", "request")
    request = native.local.request
    if request.method != "POST" or request.path != PREFIX + command:
        raise ContractError("METHOD_NOT_ALLOWED", "request")
    user = native.session.user
    if not user or user == "Guest":
        raise ContractError("UNAUTHENTICATED", "request")
    sid = str(getattr(native.session, "sid", "") or "")
    if (not sid or sid == "Guest" or request.cookies.get("sid") != sid
            or request.headers.get("Authorization")):
        raise ContractError("COOKIE_SESSION_REQUIRED", "request")
    if (request.headers.get("Origin") != binding.origin
            or request.scheme + "://" + request.host != binding.origin):
        raise ContractError("INVALID_ORIGIN", "request")
    expected = str(native.session.data.get("csrf_token") or "")
    actual = request.headers.get("X-Frappe-CSRF-Token") or ""
    if not expected or not secrets.compare_digest(expected, actual):
        raise ContractError("CSRF_REQUIRED", "request")
    if not request.is_json or request.args:
        raise ContractError("INVALID_REQUEST", "request")
    raw = request.get_data(cache=True)
    if len(raw) > MAX_BODY:
        raise ContractError("REQUEST_TOO_LARGE", "request")
    try:
        body = json.loads(raw, object_pairs_hook=_duplicate_safe,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError()))
    except (ValueError, TypeError, UnicodeDecodeError):
        raise ContractError("INVALID_JSON", "request") from None
    expected_fields = {"payload", "idempotency_key", "expected_revision", "reason"}
    if command.startswith("update_"):
        expected_fields.add("record_id")
    if not isinstance(body, dict) or set(body) != expected_fields:
        raise ContractError("INVALID_REQUEST", "request")
    return body


def _make_service(native, binding, observer):
    relations = FrappeRelationRepository(native=native, enabled=True)
    policies = FrappeManagementPolicyRepository(relations, enabled=True,
        expected_site=binding.site_id, expected_database_sha256=binding.database_sha256)
    adapter = ManagedRelationAdapter(policies, approval_verifier=binding.approval_verifier,
        pending_observer=observer, enabled=True)
    sources = FrappeLockedSourceLoader(relations, expected_site=binding.site_id,
        expected_database_sha256=binding.database_sha256, enabled=True)
    return RelationService(relations, actor_resolver=lambda: native.session.user,
        source_loader=sources, clock=binding.clock, management_adapter=adapter, enabled=True)


class _CommitGate:
    """Own one native request's actual commit; never retry a failed transaction."""
    def __init__(self, native, service, scope):
        self.native, self.service, self.scope = native, service, scope
        # Frappe.db is a LocalProxy which becomes unbound during destroy().
        # Retain the actual per-request connection for terminal cleanup/restore.
        self.database = native.local.db
        self.original_commit = self.database.commit
        self.original_sql = self.database.sql
        self.phase = "executing"
        self.proof = None
        self.result = None
        self.installed = False
        self.poisoned = False
        self.session_object = getattr(native.local, "session_obj", None)
        self.session_update = getattr(self.session_object, "update", None)
        self.session_actor = native.session.user
        self.session_state = native.local.session
        self.session_sid = getattr(native.session, "sid", None)
        self.tail_started = False
        self.tail_commit_used = False
        self.facts_committed = False

    def install(self):
        self.database.commit = self.commit
        self.installed = True

    def set_pending(self, result, proof):
        if self.phase != "executing" or proof is None or self.proof is not None:
            raise ContractError("PENDING_PROOF_REQUIRED", "transaction")
        self.proof, self.result, self.phase = proof, result, "pending"

    def _reset_callbacks(self):
        for name in ("before_commit", "after_commit", "before_rollback", "after_rollback"):
            callbacks = getattr(self.database, name, None)
            if callbacks is not None:
                callbacks.reset()

    def _poison(self):
        self.poisoned = True
        self._reset_callbacks()
        try:
            self.database.close()
        finally:
            # close() alone permits native lazy reconnect; prohibit it in this request.
            self.database.sql = self._terminal_sql

    @staticmethod
    def _terminal_sql(*args, **kwargs):
        raise _RequestAborted("managed transaction is terminal")

    def abort(self, error, *, unknown=False):
        unknown = unknown or self.facts_committed or self.phase in (
            "commit_may_have_run", "committed", "session_tail")
        if unknown and self.scope.error is not None and self.scope.error.error.code != "SAVE_RESULT_UNKNOWN":
            self.scope.error = None
        _remember_error(self.scope, error, unknown=unknown)
        self.phase = "aborted"
        if self.service is not None:
            self.service.management_adapter.discard_pending()
        # Keep rollback watchers for native cleanup. Failed commit watchers must
        # not survive into a clean transaction or the core's error processing.
        self.database.before_commit.reset()
        self.database.after_commit.reset()
        try:
            self.database.rollback()
        except BaseException:
            if not unknown:
                self.scope.error = PortalException("SOURCE_UNAVAILABLE",
                    "事务回滚未确认，请保留原幂等键并在服务恢复后核对。",
                    retryable=True, trace_id=new_trace_id())
            self._poison()
            raise _RequestAborted("managed rollback failed") from None
        if unknown:
            self._poison()

    def _guard(self):
        if self.native.local.db is not self.database:
            raise ContractError("PENDING_PROOF_MISMATCH", "transaction")
        with self.service.repository.transaction():
            self.service.repository.lock_writer()
            self.service.management_adapter.recheck_pending(self.service, self.proof)
        # Any exception after this guard may be SQL COMMIT or post-commit failure.
        self.phase = "commit_may_have_run"

    def _empty_commit_callbacks(self):
        # Exact ABI of the locally verified Frappe CallbackManager. If this
        # changes, session maintenance must fail closed until revalidated.
        for name in ("before_commit", "after_commit"):
            functions = getattr(getattr(self.database, name), "_functions", None)
            if functions is None or functions:
                raise _RequestAborted("session maintenance callbacks unavailable")

    def prepare_session_tail(self):
        """Wrap only the native bound Session.update in this request's queue.

        Native Session has slots, so its method cannot be overwritten. The core
        queues update after the fact commit and runs it at ClosingIterator.close.
        No other after_response callback gets a second-commit capability.
        """
        if self.phase != "committed" or not callable(self.session_update):
            return
        request = self.native.local.request
        functions = getattr(getattr(request, "after_response", None), "_functions", None)
        if functions is None:
            raise _RequestAborted("native response callbacks unavailable")
        for index, callback in enumerate(functions):
            if (getattr(callback, "__self__", None) is self.session_object
                    and getattr(callback, "__func__", None) is getattr(self.session_update, "__func__", None)):
                functions[index] = self._session_tail

    def _session_tail(self):
        if (self.phase != "committed" or self.tail_started
                or self.native.local.db is not self.database
                or self.native.local.session_obj is not self.session_object
                or self.native.local.session is not self.session_state
                or getattr(self.native.session, "sid", None) != self.session_sid
                or self.native.session.user != self.session_actor
                or self.session_object.user != self.session_actor
                or self.database.transaction_writes != 0):
            raise _RequestAborted("session maintenance context changed")
        self._empty_commit_callbacks()
        self.tail_started = True
        self.phase = "session_tail"
        try:
            # This is the reviewed native method, not an app-supplied callback.
            # It may update tabSessions/User metadata and commit internally once.
            return self.session_update()
        finally:
            if self.phase == "session_tail":
                self.phase = "committed"

    def _commit_session_tail(self, *args, **kwargs):
        if (self.tail_commit_used or self.native.local.db is not self.database
                or self.native.local.session_obj is not self.session_object
                or self.native.local.session is not self.session_state
                or getattr(self.native.session, "sid", None) != self.session_sid
                or self.native.session.user != self.session_actor
                or self.session_object.user != self.session_actor):
            raise _RequestAborted("session maintenance commit refused")
        self._empty_commit_callbacks()
        self.tail_commit_used = True
        try:
            return self.original_commit(*args, **kwargs)
        except BaseException as error:
            self.abort(error, unknown=True)
            raise _RequestAborted("session maintenance commit failed") from None

    def commit(self, *args, **kwargs):
        if self.phase == "session_tail":
            return self._commit_session_tail(*args, **kwargs)
        if self.phase != "pending":
            raise _RequestAborted("managed commit is not ready")
        self.phase = "finalizing"
        try:
            # Drain existing hooks first. They may add further hooks or mutate facts.
            # Recursive/early commit is blocked by this same request-local gate.
            self.database.before_commit.run()
            self.database.before_commit.add(self._guard)
            self.original_commit(*args, **kwargs)
            if self.phase != "commit_may_have_run":
                # Native transaction-control suppression must never turn a
                # skipped COMMIT/guard into an acknowledged saved result.
                raise ContractError("COMMIT_NOT_COMPLETED", "transaction")
        except BaseException as error:
            unknown = self.phase == "commit_may_have_run"
            self.abort(error, unknown=unknown)
            raise _RequestAborted("managed commit failed") from None
        self.phase = "committed"
        self.facts_committed = True

    def restore(self):
        if self.installed:
            self.database.commit = self.original_commit
        if self.poisoned:
            self.database.sql = self.original_sql


def execute_request(command):
    """Only the wrapper's trusted, request-local binding can enable this function."""
    import frappe
    scope = _request_scope.get()
    frappe.flags.disable_traceback = True
    frappe.local.response_headers["Cache-Control"] = "private, no-store, max-age=0"
    frappe.local.form_dict.clear()
    if scope is None:
        # Native application, cmd aliases and background calls have no capability.
        frappe.db.rollback()
        frappe.local.response["http_status_code"] = 503
        return error_response(_portal_error(ContractError("HTTP_BINDING_REQUIRED", "request")))
    try:
        if scope.gate is not None:
            raise ContractError("MULTIPLE_COMMANDS", "request")
        # Cover validation failures and early framework work with the same
        # full-request rollback/terminal-connection handling as fact writes.
        gate = _CommitGate(frappe, None, scope)
        scope.gate = gate
        gate.install()
        body = _validate_request(frappe, scope, command)
        # Avoid personnel and request content appearing in framework diagnostics.
        proofs = []
        service = _make_service(frappe, scope.binding, proofs.append)
        gate.service = service
        options = {key: body[key] for key in body if key != "payload"}
        result = service.execute(command, body["payload"], **options)
        if len(proofs) != 1:
            raise ContractError("PENDING_PROOF_REQUIRED", "transaction")
        gate.set_pending(result, proofs[0])
        data = asdict(result)
        data.update(transaction_pending=False, position_authorization_connected=False,
                    save_status="committed")
        # Native Frappe serializes this before sync_database. The wrapper buffers
        # it and releases it only after the real commit succeeds.
        return {"ok": True, "data": data}
    except BaseException as error:
        if scope.gate is not None:
            scope.gate.abort(error)
        else:
            _remember_error(scope, error)
            frappe.db.rollback()
        raise frappe.PermissionError("人员事实请求未完成。") from None


def _error_http(scope):
    payload = {"message": error_response(scope.error)}
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    code = scope.error.error.code
    status = ("400 Bad Request" if code == "INVALID_REQUEST" else
              "401 Unauthorized" if code == "UNAUTHENTICATED" else
              "409 Conflict" if code in ("CONFLICT", "CONFLICT_RETRY_REQUIRED", "SAVE_RESULT_UNKNOWN") else
              "503 Service Unavailable" if code in ("SOURCE_UNAVAILABLE", "NOT_SUPPORTED") else
              "403 Forbidden")
    return status, [("Content-Type", "application/json; charset=utf-8"),
                    ("Content-Length", str(len(body)))], [body]


class ManagedHTTPApplication:
    """Wrap native Frappe WSGI, buffering only the four exact managed write routes."""
    def __init__(self, application, binding=None):
        self.application, self.binding = application, binding

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")
        command = path[len(PREFIX):] if path.startswith(PREFIX) else None
        if command not in COMMANDS:
            return self.application(environ, start_response)
        scope = _RequestScope(self.binding, command)
        token = _request_scope.set(scope)
        captured, chunks = {}, []
        iterator = None

        def buffered_start(status, headers, exc_info=None):
            captured.update(status=status, headers=list(headers))
            return chunks.append

        try:
            iterator = self.application(environ, buffered_start)
            chunks.extend(iterator)
            # Abort any pending transaction while the native request/connection
            # is still bound; ClosingIterator.close() calls frappe.destroy().
            if scope.gate is not None and scope.gate.phase != "committed" and scope.error is None:
                scope.gate.abort(ContractError("PENDING_PROOF_REQUIRED", "transaction"))
            if not captured:
                raise _RequestAborted("managed response missing")
            if scope.error is None and captured["status"].startswith("2") and scope.gate is None:
                _remember_error(scope, ContractError("HTTP_BINDING_REQUIRED", "request"))
            if scope.error is None and scope.gate is None and not captured["status"].startswith("2"):
                # Authentication, native CSRF and whitelist method checks may
                # reject before execute_request installs its gate. Do not expose
                # the framework's raw exception/traceback response to this API.
                status_code = captured["status"].split(" ", 1)[0]
                code = {"400": "INVALID_REQUEST", "401": "UNAUTHENTICATED",
                        "403": "METHOD_NOT_ALLOWED", "405": "METHOD_NOT_ALLOWED"}.get(
                            status_code, "SOURCE_NATIVE_REQUEST_FAILED")
                _remember_error(scope, ContractError(code, "request"))
            if (scope.error is None and scope.gate is not None and scope.gate.phase == "committed"
                    and not captured["status"].startswith("2")):
                _remember_error(scope, _RequestAborted("post-commit response failed"), unknown=True)
            if scope.gate is not None and scope.error is None:
                scope.gate.prepare_session_tail()
            close = getattr(iterator, "close", None)
            if close is not None:
                close()
            iterator = None
        except BaseException as error:
            if scope.error is None:
                unknown = scope.gate is not None and scope.gate.phase in ("commit_may_have_run", "committed")
                if scope.gate is not None:
                    try:
                        scope.gate.abort(error, unknown=unknown)
                    except BaseException:
                        # abort already recorded the terminal failure and poisoned
                        # the connection; never release the staged success body.
                        pass
                else:
                    _remember_error(scope, error)
        finally:
            try:
                if iterator is not None and getattr(iterator, "close", None) is not None:
                    iterator.close()
            except BaseException as error:
                _remember_error(scope, error, unknown=scope.gate is not None
                    and scope.gate.phase in ("commit_may_have_run", "committed"))
            # Core sync exceptions happen before native ClosingIterator exists.
            # Explicitly destroy that request too, without opening a new transaction.
            try:
                import frappe
                if getattr(frappe.local, "db", None) is not None:
                    try:
                        if scope.error is not None:
                            frappe.db.close()
                    finally:
                        frappe.destroy()
            except BaseException as error:
                _remember_error(scope, error, unknown=scope.gate is not None
                    and scope.gate.phase in ("commit_may_have_run", "committed"))
            finally:
                if scope.gate is not None:
                    scope.gate.restore()
                _request_scope.reset(token)
        if scope.error is not None:
            status, headers, chunks = _error_http(scope)
        else:
            status, headers = captured["status"], captured["headers"]
        headers = [(key, value) for key, value in headers if key.lower() != "cache-control"]
        headers.append(("Cache-Control", "private, no-store, max-age=0"))
        start_response(status, headers)
        return chunks
