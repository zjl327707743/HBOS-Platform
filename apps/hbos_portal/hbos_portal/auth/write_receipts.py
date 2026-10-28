"""Durable, transaction-bound receipts for account security writes.

Why this module exists
----------------------
The merged baseline stored a completed-write receipt only in Redis with a
900 s TTL.  After that window a browser that lost the response could no longer
prove whether the write had committed, while the client-side pending marker
(fail-closed by design) blocked every later attempt.  The shared TTL also
guards password-recovery links, so it must not be extended for receipts.

Contract implemented here
-------------------------
* The database row is the authority.  A row is claimed before any side effect,
  so two concurrent requests with the same caller-bound identifier cannot both
  execute.  The same transaction that performs the business mutation settles
  the row to COMMITTED; a rollback therefore leaves no success receipt.
* Redis remains an accelerator only.  It is written after the SQL commit; a
  cache failure degrades to the database and never causes a re-run.  Legacy
  version-1 cache entries are still readable as committed results.
* Replays return the original, non-sensitive outcome.  A conflicting action,
  target or password fingerprint is rejected and never re-executed.
* A request whose outcome can no longer be proven can be explicitly sealed by
  the authenticated caller after a fresh proof.  Sealing records "unknown,
  ended" and permanently refuses the old identifier; it never claims success.
* The namespace is bound to the site, the caller and the request identifier.
  Different callers reusing one UUID cannot read or block each other.  For the
  Guest recovery branch the namespace is bound to the caller-issued recovery
  context instead of a session.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from datetime import datetime, timezone
from typing import Any

import frappe

DOCTYPE = "HBOS Account Write Receipt"
ACTIONS = ("password", "unlink", "recovery_issue", "recovery")
CHANNELS = ("session", "guest_recovery")
PENDING, COMMITTED, ABORTED, SEALED = "PENDING", "COMMITTED", "ABORTED", "SEALED"
STATES = (PENDING, COMMITTED, ABORTED, SEALED)
#: A claim older than this can no longer belong to a live request (the four
#: affected writes are short transactions).  Such a row is "unknown", not
#: "processing"; it can only be sealed, never re-executed automatically.
CLAIM_LEASE_SECONDS = 120
#: Legacy Redis key retained for the browser compatibility window.  The cache
#: payload version distinguishes the durable contract from the old one.
LEGACY_CACHE_PREFIX = "hbos:account:write-result:"
CACHE_VERSION = 2
RECEIPT_DURABLE_RETENTION = "retained (no automatic purge in this round)"
REQUEST_UUID = re.compile(r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}", re.I)
_SIGNING_DOMAIN = b"hbos-account-write-receipt-v1"


class ReceiptError(Exception):
    """Base failure.  Frappe maps ``http_status_code`` on the JSON response."""

    http_status_code = 409


class ReceiptConflict(ReceiptError):
    pass


class ReceiptProcessing(ReceiptError):
    http_status_code = 409


class ReceiptSealed(ReceiptError):
    http_status_code = 409


class ReceiptUnknown(ReceiptError):
    http_status_code = 409


def _reject(error: ReceiptError) -> None:
    """Raise as a Frappe ValidationError so existing account error mapping applies."""
    message = str(error)
    validation_error = getattr(frappe, "ValidationError", None)
    throw = getattr(frappe, "throw", None)
    if throw is not None and validation_error is not None:
        throw(message, validation_error)
    raise error


def request_id_valid(value: Any) -> bool:
    return isinstance(value, str) and bool(REQUEST_UUID.fullmatch(value))


def _require_request_id(request_id: Any) -> str:
    if not request_id_valid(request_id):
        _reject(ReceiptConflict("提交编号无效，请重新打开安全操作。"))
    return request_id


def sha256(value: str) -> str:
    return hashlib.sha256(str(value).encode()).hexdigest()


def _signing_key(secret: Any = None) -> bytes:
    if secret:
        return secret if isinstance(secret, bytes) else str(secret).encode()
    conf = getattr(getattr(frappe, "local", None), "conf", None)
    key = None
    try:
        key = conf.get("encryption_key") if conf is not None else None
    except Exception:
        key = None
    if not key:
        _reject(ReceiptConflict("站点缺少安全签名配置，安全操作暂不可用。"))
    return str(key).encode()


def hmac_hex(secret: Any, *parts: str) -> str:
    """Keyed fingerprint.  Plain digests are never enough for password intent."""
    digest = hmac.new(_signing_key(secret), _SIGNING_DOMAIN, hashlib.sha256)
    for part in parts:
        digest.update(b"\x1f")
        digest.update(str(part).encode())
    return digest.hexdigest()


def context_handle(secret: Any, context: str) -> str:
    """Opaque, non-reversible handle for a Guest recovery context."""
    if not isinstance(context, str) or len(context) < 16 or len(context) > 512:
        _reject(ReceiptConflict("恢复验证上下文无效，请重新打开恢复入口。"))
    return hmac_hex(secret, "guest-recovery-context", context)


def session_request_key(secret: Any, *, site: str, actor: str, request_id: str) -> str:
    return hmac_hex(secret, "session", site, actor, _require_request_id(request_id))


def guest_request_key(secret: Any, *, site: str, request_id: str, context: str) -> str:
    return hmac_hex(secret, "guest", site, _require_request_id(request_id), context_handle(secret, context))


def legacy_cache_key(actor: str, request_id: str) -> str:
    return LEGACY_CACHE_PREFIX + sha256(actor + ":" + request_id)


def intent_digest(
    secret: Any,
    *,
    site: str,
    actor: str,
    subject: str,
    action: str,
    payload_digest: str = "",
) -> str:
    action = str(action or "")
    if action not in ACTIONS:
        _reject(ReceiptConflict("安全操作类型无效。"))
    return hmac_hex(secret, "intent", site, actor, subject, action, payload_digest)


def password_payload_digest(new_password: str) -> str:
    """Second-stage digest; the raw password is never stored or logged."""
    return sha256("hbos-account-password-intent\x1f" + str(new_password or ""))


def as_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    try:
        return frappe.utils.get_datetime(value)
    except Exception:
        try:
            return datetime.fromisoformat(str(value))
        except ValueError:
            return None


def _iso(value: Any) -> str | None:
    parsed = as_datetime(value)
    return parsed.isoformat() if parsed else None


def evaluate_claim(
    row: dict | None,
    *,
    action: str,
    subject: str,
    intent: str,
    now: datetime,
    lease_seconds: int = CLAIM_LEASE_SECONDS,
) -> dict:
    """Pure decision for an existing claim row.

    Returns one of: new, conflict, replayed, processing, unknown, retry, sealed.
    It never performs I/O so the whole state machine is unit-testable.
    """
    if not row:
        return {"status": "new"}
    stored_action = str(row.get("action") or "")
    stored_subject = str(row.get("subject") or "")
    stored_intent = str(row.get("intent_digest") or "")
    if stored_action != action or stored_subject != subject or (stored_intent and stored_intent != intent):
        return {"status": "conflict"}
    state = str(row.get("state") or "")
    if state == COMMITTED:
        return {"status": "replayed"}
    if state == ABORTED:
        return {"status": "retry"}
    if state == SEALED:
        return {"status": "sealed"}
    if state == PENDING:
        claimed = as_datetime(row.get("claimed_at"))
        age = (now - claimed).total_seconds() if claimed else lease_seconds + 1
        return {"status": "processing" if age < lease_seconds else "unknown"}
    # Unknown/corrupt state: never re-execute, never claim success.
    return {"status": "unknown"}


def public_state(row: dict | None, *, now: datetime | None = None, lease_seconds: int = CLAIM_LEASE_SECONDS) -> dict | None:
    """Browser-facing receipt shape.  Only non-sensitive state is exposed."""
    if not row:
        return None
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    state = str(row.get("state") or "")
    action = str(row.get("action") or "")
    if state == COMMITTED:
        return {
            "completed": True, "state": COMMITTED, "action": action,
            "committed_at": _iso(row.get("committed_at")), "legacy": False,
            "processing": False, "retryable": False, "sealed": False, "unknown": False,
        }
    if state == PENDING:
        claimed = as_datetime(row.get("claimed_at"))
        stale = bool(claimed and (now - claimed).total_seconds() >= lease_seconds)
        return {
            "completed": False, "state": PENDING, "action": action, "committed_at": None,
            "legacy": False, "processing": not stale, "retryable": False,
            "sealed": False, "unknown": stale,
        }
    if state == ABORTED:
        return {
            "completed": False, "state": ABORTED, "action": action, "committed_at": None,
            "legacy": False, "processing": False, "retryable": True, "sealed": False, "unknown": False,
        }
    if state == SEALED:
        return {
            "completed": False, "state": SEALED, "action": action, "committed_at": None,
            "legacy": False, "processing": False, "retryable": False, "sealed": True, "unknown": True,
        }
    return {
        "completed": False, "state": "UNKNOWN", "action": action, "committed_at": None,
        "legacy": False, "processing": False, "retryable": False, "sealed": False, "unknown": True,
    }


def legacy_public_state(payload: dict) -> dict:
    """Version-1 cache entries only ever meant "the write completed"."""
    return {
        "completed": True, "state": COMMITTED, "action": str(payload.get("action") or ""),
        "committed_at": None, "legacy": True, "processing": False,
        "retryable": False, "sealed": False, "unknown": False,
    }


def cache_payload(row: dict) -> dict:
    state = public_state(row) or {}
    state.update({"version": CACHE_VERSION, "request_id": row.get("request_id")})
    return state


def parse_cache_payload(payload: Any) -> dict | None:
    if not isinstance(payload, dict):
        return None
    if payload.get("version") == CACHE_VERSION and payload.get("state") in STATES:
        return {key: payload.get(key) for key in (
            "completed", "state", "action", "committed_at", "legacy",
            "processing", "retryable", "sealed", "unknown")}
    if payload.get("completed") is True and isinstance(payload.get("action"), str):
        return legacy_public_state(payload)
    return None


# ---------------------------------------------------------------------------
# Database/cache orchestration
# ---------------------------------------------------------------------------


def _fields() -> list[str]:
    return [
        "name", "request_key", "channel", "request_id", "site_name", "actor", "subject",
        "action", "state", "intent_digest", "claimed_at", "committed_at", "failed_at",
        "sealed_at", "sealed_by", "failure_code", "attempt_count", "outcome_json",
    ]


def _get_by_key(request_key: str) -> dict | None:
    row = frappe.db.get_value(DOCTYPE, {"request_key": request_key}, _fields(), as_dict=True)
    return dict(row) if row else None


def _update(name: str, values: dict) -> None:
    frappe.db.set_value(DOCTYPE, name, values, update_modified=False)


def _now() -> datetime:
    return frappe.utils.now_datetime()


def _site() -> str:
    return str(getattr(frappe.local, "site", "") or "")


def _create_claim(values: dict) -> dict | None:
    """Insert the claim row and commit it before any side effect.

    Returns ``None`` when the unique key already exists (another request won).
    Any other database error propagates: without a durable claim the write must
    not proceed.
    """
    frappe.flags.hbos_account_write_receipt_authority = True
    try:
        doc = frappe.get_doc({"doctype": DOCTYPE, **values})
        doc.insert(ignore_permissions=True)
        name = doc.name
        frappe.db.commit()
        return _get_by_key(values["request_key"]) or {"name": name, **values}
    except Exception:
        frappe.db.rollback()
        row = _get_by_key(values["request_key"])
        if row:
            return None
        raise
    finally:
        try:
            del frappe.flags.hbos_account_write_receipt_authority
        except Exception:
            pass


def claim(
    *,
    actor: str,
    subject: str,
    action: str,
    request_id: str,
    layer: str = "session",
    payload_digest: str = "",
    secret: Any = None,
) -> dict:
    """Claim (or replay) one caller-bound request before any side effect.

    ``layer`` 0 for a session write, 1 for the Guest recovery branch; it is
    reported back so callers can decide which recovery semantics apply.
    """
    if action not in ACTIONS:
        _reject(ReceiptConflict("安全操作类型无效。"))
    request_id = _require_request_id(request_id)
    site = _site()
    if not actor or not subject:
        _reject(ReceiptConflict("无法确认安全操作主体，请重新登录。"))
    intent = intent_digest(secret, site=site, actor=actor, subject=subject, action=action,
                           payload_digest=payload_digest)
    request_key = session_request_key(secret, site=site, actor=actor, request_id=request_id)
    existing = _get_by_key(request_key)
    decision = evaluate_claim(existing, action=action, subject=subject, intent=intent, now=_now())
    status = decision["status"]
    if status == "replayed":
        return {"status": "replayed", "request_key": request_key, "row": existing,
                "public": public_state(existing), "attempt": existing.get("attempt_count")}
    if status == "conflict":
        _reject(ReceiptConflict("此提交编号已用于另一项安全操作，请先查询原提交结果。"))
    if status == "processing":
        _reject(ReceiptProcessing("上次提交仍在处理中，请稍后再次查询；不要重复提交。"))
    if status == "unknown":
        _reject(ReceiptUnknown("上次提交结果未知，请核对后安全结束该未决请求。"))
    if status == "sealed":
        _reject(ReceiptSealed("该提交编号已按未知结果封存，不会再次执行。"))
    if status == "retry":
        attempt = int(existing.get("attempt_count") or 1) + 1
        _update(existing["name"], {
            "state": PENDING, "claimed_at": _now(), "failed_at": None,
            "failure_code": None, "attempt_count": attempt,
        })
        frappe.db.commit()
        row = _get_by_key(request_key) or existing
        return {"status": "claimed", "request_key": request_key, "row": row,
                "public": None, "attempt": attempt}
    created = _create_claim({
        "request_key": request_key, "channel": "session", "request_id": request_id,
        "site_name": site, "actor": actor, "subject": subject, "action": action,
        "state": PENDING, "intent_digest": intent, "claimed_at": _now(),
        "attempt_count": 1,
    })
    if created is None:
        # Lost the unique-key race: evaluate the winner's row exactly once.
        winner = _get_by_key(request_key)
        decision = evaluate_claim(winner, action=action, subject=subject, intent=intent, now=_now())
        if decision["status"] == "replayed":
            return {"status": "replayed", "request_key": request_key, "row": winner,
                    "public": public_state(winner), "attempt": winner.get("attempt_count")}
        if decision["status"] in ("conflict",):
            _reject(ReceiptConflict("此提交编号已用于另一项安全操作，请先查询原提交结果。"))
        if decision["status"] == "sealed":
            _reject(ReceiptSealed("该提交编号已按未知结果封存，不会再次执行。"))
        if decision["status"] == "unknown":
            _reject(ReceiptUnknown("上次提交结果未知，请核对后安全结束该未决请求。"))
        _reject(ReceiptProcessing("上次提交仍在处理中，请稍后再次查询；不要重复提交。"))
    return {"status": "claimed", "request_key": request_key, "row": created,
            "public": None, "attempt": 1}


def claim_guest_recovery(
    *,
    actor: str,
    action: str,
    request_id: str,
    context: str,
    payload_digest: str,
    secret: Any = None,
) -> dict:
    """Guest recovery claim bound to the caller-issued recovery context."""
    if action != "recovery":
        _reject(ReceiptConflict("恢复入口只能提交通用恢复操作。"))
    request_id = _require_request_id(request_id)
    site = _site()
    key = guest_request_key(secret, site=site, request_id=request_id, context=context)
    intent = intent_digest(secret, site=site, actor=actor, subject=actor, action=action,
                           payload_digest=payload_digest)
    existing = _get_by_key(key)
    decision = evaluate_claim(existing, action=action, subject=actor, intent=intent, now=_now())
    status = decision["status"]
    if status == "replayed":
        return {"status": "replayed", "request_key": key, "row": existing,
                "public": public_state(existing), "attempt": existing.get("attempt_count")}
    if status == "conflict":
        _reject(ReceiptConflict("此提交编号已提交过另一组恢复信息，请先核对原提交结果。"))
    if status == "processing":
        _reject(ReceiptProcessing("上次提交仍在处理中，请稍后再次查询；不要重复提交。"))
    if status == "unknown":
        _reject(ReceiptUnknown("上次提交结果未知，请重新打开有效的恢复入口后再核对。"))
    if status == "sealed":
        _reject(ReceiptSealed("该提交编号已按未知结果封存，不会再次执行。"))
    if status == "retry":
        attempt = int(existing.get("attempt_count") or 1) + 1
        _update(existing["name"], {"state": PENDING, "claimed_at": _now(), "failed_at": None,
                                   "failure_code": None, "attempt_count": attempt})
        frappe.db.commit()
        row = _get_by_key(key) or existing
        return {"status": "claimed", "request_key": key, "row": row, "public": None, "attempt": attempt}
    created = _create_claim({
        "request_key": key, "channel": "guest_recovery", "request_id": request_id,
        "site_name": site, "actor": actor, "subject": actor, "action": action,
        "state": PENDING, "intent_digest": intent, "claimed_at": _now(), "attempt_count": 1,
    })
    if created is None:
        winner = _get_by_key(key)
        decision = evaluate_claim(winner, action=action, subject=actor, intent=intent, now=_now())
        if decision["status"] == "replayed":
            return {"status": "replayed", "request_key": key, "row": winner,
                    "public": public_state(winner), "attempt": winner.get("attempt_count")}
        if decision["status"] == "conflict":
            _reject(ReceiptConflict("此提交编号已提交过另一组恢复信息，请先核对原提交结果。"))
        if decision["status"] == "sealed":
            _reject(ReceiptSealed("该提交编号已按未知结果封存，不会再次执行。"))
        _reject(ReceiptProcessing("上次提交仍在处理中，请稍后再次查询；不要重复提交。"))
    return {"status": "claimed", "request_key": key, "row": created, "public": None, "attempt": 1}


def read_guest_recovery(
    *, request_id: str, context: str, payload_digest: str, action: str = "recovery", secret: Any = None
) -> dict | None:
    """Reconcile a Guest recovery request that lost its HTTP response.

    The caller must still possess the original one-time recovery context, so a
    bare request identifier is never treated as a credential.
    """
    request_id = _require_request_id(request_id)
    if not isinstance(context, str) or not context:
        return None
    site = _site()
    key = guest_request_key(secret, site=site, request_id=request_id, context=context)
    row = _get_by_key(key)
    if not row:
        return None
    expected = intent_digest(secret, site=site, actor=row.get("actor") or "", subject=row.get("subject") or "",
                             action=action, payload_digest=payload_digest)
    decision = evaluate_claim(row, action=action, subject=str(row.get("subject") or ""),
                              intent=expected, now=_now())
    if decision["status"] == "conflict":
        _reject(ReceiptConflict("此提交编号已提交过另一组恢复信息，请先核对原提交结果。"))
    return public_state(row)


def mark_committed(token: dict, outcome: dict | None = None) -> None:
    """Settle a claim inside the caller's business transaction (no commit here).

    The row is locked and re-read first: if the caller sealed or settled this
    identifier in the meantime, the business transaction must roll back rather
    than commit behind a receipt that says the result is unknown.
    """
    if not token or not token.get("row"):
        return
    name = token["row"]["name"]
    locked = frappe.db.sql(
        "SELECT state FROM `tabHBOS Account Write Receipt` WHERE name=%s FOR UPDATE",
        (name,), as_dict=True,
    )
    if not locked or str(locked[0].get("state") or "") != PENDING:
        _reject(ReceiptSealed("该提交在处理期间已被结束或确认，本次未写入，请重新核对。"))
    _update(name, {
        "state": COMMITTED, "committed_at": _now(),
        "outcome_json": json.dumps(outcome or {}, ensure_ascii=False, sort_keys=True)[:2000],
    })


def abort(token: dict, failure_code: str = "") -> None:
    """Record a definitively failed claim without ever overwriting COMMITTED.

    The conditional UPDATE is the guard: an exception raised after the business
    transaction committed (for example while rotating the session) must leave
    the committed row untouched.
    """
    if not token or not token.get("request_key"):
        return
    name = (token.get("row") or {}).get("name")
    try:
        if name:
            frappe.db.sql(
                "UPDATE `tabHBOS Account Write Receipt` SET state=%s, failed_at=%s, failure_code=%s "
                "WHERE name=%s AND state=%s AND committed_at IS NULL",
                (ABORTED, _now(), str(failure_code or "")[:140], name, PENDING),
            )
        else:
            frappe.db.sql(
                "UPDATE `tabHBOS Account Write Receipt` SET state=%s, failed_at=%s, failure_code=%s "
                "WHERE request_key=%s AND state=%s AND committed_at IS NULL",
                (ABORTED, _now(), str(failure_code or "")[:140], token["request_key"], PENDING),
            )
        frappe.db.commit()
    except Exception:
        frappe.db.rollback()


def publish_cache(token: dict, ttl_seconds: int = 900) -> None:
    """Best-effort accelerator, only after the SQL transaction committed."""
    if not token or not token.get("row"):
        return
    row = _get_by_key(token["request_key"]) or token["row"]
    payload = cache_payload(row)
    try:
        frappe.cache.set_value(legacy_cache_key(str(row.get("actor") or ""), str(row.get("request_id") or "")),
                               payload, expires_in_sec=ttl_seconds)
    except Exception:
        # Database is authoritative; losing the accelerator cannot lose a result.
        pass


def read_receipt(actor: str, request_id: str, action: str = "", *, secret: Any = None) -> dict | None:
    """Authoritative read: Redis fast path (legacy compatible) then database."""
    if not request_id:
        return None
    request_id = _require_request_id(request_id)
    cached = None
    try:
        cached = frappe.cache.get_value(legacy_cache_key(actor, request_id))
    except Exception:
        cached = None
    cached_state = parse_cache_payload(cached)
    key = session_request_key(secret, site=_site(), actor=actor, request_id=request_id)
    row = _get_by_key(key)
    if row:
        if action and str(row.get("action") or "") != action:
            _reject(ReceiptConflict("此提交编号已用于另一项安全操作。"))
        return public_state(row)
    if action and cached_state and cached_state.get("action") != action:
        _reject(ReceiptConflict("此提交编号已用于另一项安全操作。"))
    return cached_state


def seal(actor: str, request_id: str, action: str = "", *, secret: Any = None) -> dict:
    """Explicitly end an unresolved request without claiming it succeeded."""
    request_id = _require_request_id(request_id)
    if action and action not in ACTIONS:
        _reject(ReceiptConflict("安全操作类型无效。"))
    site = _site()
    key = session_request_key(secret, site=site, actor=actor, request_id=request_id)
    row = _get_by_key(key)
    if row:
        state = str(row.get("state") or "")
        if state == COMMITTED:
            return {"sealed": False, "state": COMMITTED, "completed": True,
                    "alreadysettled": True, "message": "原提交已确认完成，无需封存。"}
        if state == ABORTED:
            return {"sealed": False, "state": ABORTED, "retryable": True,
                    "message": "原提交确认未执行，可以重新发起新的安全操作。"}
        if state == SEALED:
            return {"sealed": True, "state": SEALED, "alreadysealed": True,
                    "message": "该未决请求此前已封存。"}
        claimed = as_datetime(row.get("claimed_at"))
        age = (_now() - claimed).total_seconds() if claimed else CLAIM_LEASE_SECONDS + 1
        if state == PENDING and age < CLAIM_LEASE_SECONDS:
            _reject(ReceiptProcessing("上次提交仍在处理中，请稍后再次查询；暂不能封存。"))
        payload_action = str(row.get("action") or action or "password")
        if action and payload_action != action:
            _reject(ReceiptConflict("此提交编号已用于另一项安全操作，不能按当前操作封存。"))
        locked = frappe.db.sql(
            "SELECT state FROM `tabHBOS Account Write Receipt` WHERE name=%s FOR UPDATE",
            (row["name"],), as_dict=True,
        )
        locked_state = str((locked[0].get("state") if locked else "") or "")
        if locked_state == COMMITTED:
            return {"sealed": False, "state": COMMITTED, "completed": True,
                    "alreadysettled": True, "message": "原提交已确认完成，无需封存。"}
        if locked_state == SEALED:
            return {"sealed": True, "state": SEALED, "alreadysealed": True,
                    "message": "该未决请求此前已封存。"}
        if locked_state != PENDING:
            _reject(ReceiptProcessing("该提交状态正在变化，请稍后再次查询。"))
        _update(row["name"], {"state": SEALED, "sealed_at": _now(), "sealed_by": actor})
        frappe.db.commit()
        return {"sealed": True, "state": SEALED, "message": "已记录原结果未知并安全结束该请求；未声称原操作成功。"}
    # No durable row (pre-upgrade request or a response lost before the claim):
    # create a tombstone so the old identifier can never dispatch later.
    created = _create_claim({
        "request_key": key, "channel": "session", "request_id": request_id, "site_name": site,
        "actor": actor, "subject": actor, "action": action or "unknown",
        "state": SEALED, "sealed_at": _now(), "sealed_by": actor,
        "intent_digest": "", "attempt_count": 0,
    })
    if created is None:
        row = _get_by_key(key)
        state = str((row or {}).get("state") or "")
        if state == SEALED:
            return {"sealed": True, "state": SEALED, "alreadysealed": True,
                    "message": "该未决请求此前已封存。"}
        if state == COMMITTED:
            return {"sealed": False, "state": COMMITTED, "completed": True,
                    "message": "原提交已确认完成，无需封存。"}
        _reject(ReceiptProcessing("该提交正在被处理，请稍后再次查询。"))
    return {"sealed": True, "state": SEALED,
            "message": "已记录原结果未知并安全结束该请求；未声称原操作成功。"}


# ---------------------------------------------------------------------------
# Migration / model boundary
# ---------------------------------------------------------------------------


def migrate() -> None:
    """Idempotent model sync used by hooks.after_migrate/after_install."""
    if not frappe.db.exists("DocType", DOCTYPE):
        return
    try:
        frappe.reload_doc("hbos_portal", "doctype", "hbos_account_write_receipt")
    except Exception:
        # bench migrate already ran frappe.model.sync.sync_all(); a failed
        # reload must not abort unrelated migrations.
        pass
    if not frappe.db.table_exists(DOCTYPE):
        return
    if not frappe.db.get_column_index(DOCTYPE, "request_key", unique=True):
        # The DocType field already declares unique=1; this is the explicit
        # database guarantee for a Site migrated from an earlier candidate.
        frappe.db.add_unique(DOCTYPE, ["request_key"], constraint_name="request_key")
    frappe.db.add_index(DOCTYPE, ["actor", "request_id"], index_name="hbos_account_write_receipt_actor")
    frappe.db.add_index(DOCTYPE, ["subject", "state"], index_name="hbos_account_write_receipt_subject")
