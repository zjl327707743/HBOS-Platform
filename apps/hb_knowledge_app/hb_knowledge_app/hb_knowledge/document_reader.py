"""Controlled document-body reader use case (BFF side).

Authorization is never taken from request-body identity. Each call issues a
fresh ``document.read`` plan narrowed to the one current binding of the logical
document the server snapshot authorizes, walks the authority phases, has the
service read one bounded ordered page of that already-proven document, and
revalidates the plan again after projection and before returning. Withdrawal,
version bump or role removal therefore fails the very next page.

Only display data leaves this module: title/version/space/status and inert body
text. Physical dataset/document ids, native chunk ids, paths, keys, tokens and
upstream addresses are never returned.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re

from .document_reader_contract import (
    BODY_ORIGIN, DISCLOSURE, MAX_BLOCK_CODEPOINTS, MAX_PAGE, MAX_PAGE_CODEPOINTS,
    MAX_SEARCH_BLOCKS, MAX_TOC_ENTRIES, PAGE_NUMBERING, PAGE_SIZE, TOC_SOURCE,
    normalize_document_read, normalize_page, normalize_search_limit,
    normalize_search_query,
)
from .errors import KnowledgeError
from .execution_plan import ServicePrincipal
from .gateway import document_call
from .public_strings import safe_string, source_display_string

_LOG = logging.getLogger("hbos.knowledge.document_reader")
_REQUEST_ID = re.compile(r"[A-Za-z0-9_-]{1,128}")

# Failures with their own public meaning. Everything else about a document
# body (scope, unpublished, withdrawn, stale version, ambiguous version) is
# reported as the single controlled DOCUMENT_READ_UNAVAILABLE code; its
# enumerated ``state`` is the only extra detail.
_PASSTHROUGH = frozenset({
    "INVALID_REQUEST", "DOCUMENT_READ_UNAVAILABLE", "DOCUMENT_READ_PAGE_OUT_OF_RANGE",
    "UPSTREAM_UNAVAILABLE", "UPSTREAM_INVALID_RESULT", "UPSTREAM_SCOPE_VIOLATION",
    "POLICY_UNAVAILABLE", "RATE_LIMITED", "EXTRACTION_LIMITED", "DECISION_EXPIRED",
    "REPLAY_REJECTED", "AUTHENTICATION_REQUIRED", "CLIENT_AUTH_FAILED", "SERVICE_ERROR",
})

_PAGE_KEYS = {"status", "page", "page_size", "page_count", "block_total",
              "blocks", "toc", "toc_source", "derived"}
_PAGE_OPTIONAL = {"toc_truncated"}
_SEARCH_KEYS = {"status", "matches", "searched_blocks", "capped"}


def open_document(runtime, document_id, version_id, request_id):
    """Open page 1 of an authorized current document body."""
    return _run(runtime, document_id, version_id, request_id, page=1)


def read_document_page(runtime, document_id, version_id, page, request_id):
    """Read one bounded page of the same authorized current document body."""
    return _run(runtime, document_id, version_id, request_id, page=page)


def search_document(runtime, document_id, version_id, query, limit, request_id):
    """Bounded in-document search for an authorized current document body."""
    return _run(runtime, document_id, version_id, request_id, query=query,
                limit=limit, search=True)


def _run(runtime, document_id, version_id, request_id, *, page=None, query=None,
         limit=None, search=False):
    raw = {"document_id": document_id}
    if version_id is not None:
        raw["version_id"] = version_id
    request = normalize_document_read(raw)
    if search:
        query = normalize_search_query(query)
        limit = normalize_search_limit(limit)
    else:
        page = normalize_page(page)
    try:
        actor = runtime.actor()
        if search:
            return _search(runtime, actor, request, query, limit, request_id)
        return _page(runtime, actor, request, page, request_id)
    except KnowledgeError as error:
        _log_failure(request, request_id, page=page, error=error)
        raise _document_error(error) from None


def _document_error(error):
    if error.code in _PASSTHROUGH:
        return error
    return KnowledgeError("DOCUMENT_READ_UNAVAILABLE")


def _log_failure(request, request_id, *, page=None, error=None):
    _log("DOCUMENT_BODY_READ_FAILED", request_id=request_id, page=page,
         result=getattr(error, "code", None),
         state=getattr(error, "state", None),
         document_sha256=hashlib.sha256(request.document_id.encode()).hexdigest())


def _log(event, *, request_id, page=None, result=None, state=None,
         document_sha256=None, bytes_returned=None, matches=None, capped=None):
    payload = {"event": event,
               "request_id": request_id if isinstance(request_id, str)
               and _REQUEST_ID.fullmatch(request_id) else "UNAVAILABLE",
               "result": result}
    if page is not None:
        payload["page"] = page
    if state is not None:
        payload["state"] = state
    if document_sha256 is not None:
        payload["document_sha256"] = document_sha256
    if bytes_returned is not None:
        payload["bytes"] = bytes_returned
    if matches is not None:
        payload["matches"] = matches
    if capped is not None:
        payload["capped"] = capped
    # Never logs body text, titles, tokens or physical identifiers.
    _LOG.info(json.dumps(payload, sort_keys=True))


def _principal(ticket):
    return ServicePrincipal(ticket.plan.client, True)


def _plan_binding(ticket, request):
    plan = ticket.plan
    if plan.action != "document.read" or len(plan.bindings) != 1:
        raise KnowledgeError("UPSTREAM_SCOPE_VIOLATION")
    binding = plan.bindings[0]
    if binding.canonical_document_id != request.document_id:
        raise KnowledgeError("UPSTREAM_SCOPE_VIOLATION")
    if request.version_id is not None and binding.version_id != request.version_id:
        raise KnowledgeError("UPSTREAM_SCOPE_VIOLATION")
    return binding


def _status_note(binding):
    if binding.source_type == "SYNTHETIC_TEST":
        return "SYNTHETIC_ONLY"
    if binding.authority_status in {"CONTROLLED_REFERENCE_REVIEWED",
                                    "INTERNAL_REFERENCE_REVIEWED"}:
        return "内部参考／有效性待核"
    return binding.authority_status


def _document_card(snapshot, binding):
    physical = (binding.dataset_id, binding.document_id)
    titles = dict(getattr(snapshot, "space_titles", ()) or ())
    return {
        "document_id": safe_string(binding.canonical_document_id, 120,
                                   physical_ids=physical),
        "version_id": safe_string(binding.version_id, 128, physical_ids=physical),
        "title": safe_string(binding.title, 240, nullable=True, physical_ids=physical),
        "document_number": safe_string(binding.document_number, 120, nullable=True,
                                       physical_ids=physical),
        "space_id": safe_string(binding.space_id, 120, physical_ids=physical),
        "space_title": safe_string(titles.get(binding.space_id, "知识空间"), 120,
                                   physical_ids=physical),
        "business_version": safe_string(binding.business_version, 80, nullable=True,
                                        physical_ids=physical),
        "status_note": safe_string(_status_note(binding), 320, physical_ids=physical),
        "reference_state": "CURRENT",
        "authorization": "AUTHORIZED",
        "source_type": binding.source_type,
    }


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def _page(runtime, actor, request, page, request_id):
    ticket = runtime.decisions.issue(actor, runtime.client, "document.read",
                                     request, request_id)
    binding = _plan_binding(ticket, request)
    snapshot = runtime.provider._current(actor, runtime.client)
    document = _document_card(snapshot, binding)
    principal = _principal(ticket)
    runtime.decisions.online(principal, ticket.call("introspect", "introspect"))
    runtime.decisions.online(principal, document_call(ticket))
    payload = runtime.gateway.document_page(ticket=ticket, page=page)
    body = _body(payload, page, binding)
    navigation = _navigation(payload, binding, body["block_total"])
    data = {"document": document, "body": body, "navigation": navigation,
            "disclosure": DISCLOSURE}
    # Actual consumer final check, after projection and before return: a
    # withdrawal/version bump/role removal during the read rejects the page.
    runtime.decisions.online(principal, ticket.call("revalidate", "final_publish"))
    _record_audit(runtime, actor, binding, page, body, request_id)
    return data


def _body(payload, page, binding):
    if (not isinstance(payload, dict) or set(payload) - _PAGE_KEYS - _PAGE_OPTIONAL
            or payload.get("status") != "SUCCESS"):
        raise KnowledgeError("UPSTREAM_INVALID_RESULT")
    if payload.get("page") != page or payload.get("page_size") != PAGE_SIZE:
        raise KnowledgeError("UPSTREAM_INVALID_RESULT")
    page_count, block_total = payload.get("page_count"), payload.get("block_total")
    if type(page_count) is not int or not 1 <= page_count <= MAX_PAGE:
        raise KnowledgeError("UPSTREAM_INVALID_RESULT")
    if type(block_total) is not int or not 1 <= block_total <= MAX_PAGE * PAGE_SIZE:
        raise KnowledgeError("UPSTREAM_INVALID_RESULT")
    if (block_total + PAGE_SIZE - 1) // PAGE_SIZE != page_count:
        raise KnowledgeError("UPSTREAM_INVALID_RESULT")
    if page > page_count:
        raise KnowledgeError("DOCUMENT_READ_PAGE_OUT_OF_RANGE")
    if payload.get("toc_source") != TOC_SOURCE or payload.get("derived") is not True:
        raise KnowledgeError("UPSTREAM_INVALID_RESULT")
    if "toc_truncated" in payload and type(payload["toc_truncated"]) is not bool:
        raise KnowledgeError("UPSTREAM_INVALID_RESULT")
    physical = (binding.dataset_id, binding.document_id)
    raw_blocks = payload.get("blocks")
    if not isinstance(raw_blocks, list) or len(raw_blocks) > PAGE_SIZE:
        raise KnowledgeError("UPSTREAM_INVALID_RESULT")
    blocks = []
    total = 0
    previous = 0
    for item in raw_blocks:
        if not isinstance(item, dict) or set(item) != {"ordinal", "section", "text"}:
            raise KnowledgeError("UPSTREAM_INVALID_RESULT")
        ordinal = item["ordinal"]
        if (type(ordinal) is not int
                or not (page - 1) * PAGE_SIZE < ordinal <= page * PAGE_SIZE
                or ordinal <= previous):
            raise KnowledgeError("UPSTREAM_INVALID_RESULT")
        previous = ordinal
        text = source_display_string(item["text"], MAX_BLOCK_CODEPOINTS,
                                     physical_ids=physical)
        if not text.strip():
            raise KnowledgeError("UPSTREAM_INVALID_RESULT")
        section = None
        if item["section"] is not None:
            section = source_display_string(item["section"], 240, physical_ids=physical)
        total += len(text)
        if total > MAX_PAGE_CODEPOINTS:
            raise KnowledgeError("UPSTREAM_INVALID_RESULT")
        blocks.append({"block_id": f"b{ordinal}", "ordinal": ordinal,
                       "page_number": None, "section": section, "text": text})
    return {"origin": BODY_ORIGIN, "page_numbering": PAGE_NUMBERING, "derived": True,
            "page": page, "page_count": page_count, "block_total": block_total,
            "blocks": blocks}


def _navigation(payload, binding, block_total):
    physical = (binding.dataset_id, binding.document_id)
    raw_toc = payload.get("toc")
    if not isinstance(raw_toc, list) or len(raw_toc) > MAX_TOC_ENTRIES:
        raise KnowledgeError("UPSTREAM_INVALID_RESULT")
    toc = []
    previous = 0
    for entry in raw_toc:
        if not isinstance(entry, dict) or set(entry) != {"title", "ordinal"}:
            raise KnowledgeError("UPSTREAM_INVALID_RESULT")
        ordinal = entry["ordinal"]
        if (type(ordinal) is not int or not 1 <= ordinal <= block_total
                or ordinal <= previous):
            raise KnowledgeError("UPSTREAM_INVALID_RESULT")
        previous = ordinal
        title = source_display_string(entry["title"], 120, physical_ids=physical)
        if not title.strip():
            raise KnowledgeError("UPSTREAM_INVALID_RESULT")
        toc.append({"title": title, "ordinal": ordinal, "page_number": None})
    navigation = {"toc": toc, "toc_source": TOC_SOURCE}
    if payload.get("toc_truncated") is True:
        navigation["toc_truncated"] = True
    return navigation


def _record_audit(runtime, actor, binding, page, body, request_id):
    bytes_returned = sum(len(block["text"].encode("utf-8")) for block in body["blocks"])
    runtime.audit.record(actor.user_ref, "document_read", "SUCCESS", bytes_returned)
    _log("DOCUMENT_BODY_READ", request_id=request_id, page=page, result="SUCCESS",
         document_sha256=hashlib.sha256(
             binding.canonical_document_id.encode()).hexdigest(),
         bytes_returned=bytes_returned)


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def _search(runtime, actor, request, query, limit, request_id):
    ticket = runtime.decisions.issue(actor, runtime.client, "document.read",
                                     request, request_id)
    binding = _plan_binding(ticket, request)
    principal = _principal(ticket)
    runtime.decisions.online(principal, ticket.call("introspect", "introspect"))
    runtime.decisions.online(principal, document_call(ticket))
    payload = runtime.gateway.document_search(ticket=ticket, query=query, limit=limit)
    matches, searched, capped = _matches(payload, binding, limit)
    data = {"matches": matches, "searched_blocks": searched, "capped": capped}
    runtime.decisions.online(principal, ticket.call("revalidate", "final_publish"))
    bytes_returned = sum(len(match["snippet"].encode("utf-8")) for match in matches)
    runtime.audit.record(actor.user_ref, "document_read", "SUCCESS", bytes_returned)
    _log("DOCUMENT_BODY_SEARCH", request_id=request_id, result="SUCCESS",
         document_sha256=hashlib.sha256(
             binding.canonical_document_id.encode()).hexdigest(),
         bytes_returned=bytes_returned, matches=len(matches), capped=capped)
    return data


def _matches(payload, binding, limit):
    if not isinstance(payload, dict) or set(payload) != _SEARCH_KEYS \
            or payload.get("status") != "SUCCESS":
        raise KnowledgeError("UPSTREAM_INVALID_RESULT")
    searched, capped = payload.get("searched_blocks"), payload.get("capped")
    if type(searched) is not int or not 0 <= searched <= MAX_SEARCH_BLOCKS:
        raise KnowledgeError("UPSTREAM_INVALID_RESULT")
    if type(capped) is not bool:
        raise KnowledgeError("UPSTREAM_INVALID_RESULT")
    raw_matches = payload.get("matches")
    if not isinstance(raw_matches, list) or len(raw_matches) > limit:
        raise KnowledgeError("UPSTREAM_INVALID_RESULT")
    physical = (binding.dataset_id, binding.document_id)
    matches = []
    previous = 0
    for item in raw_matches:
        if not isinstance(item, dict) or set(item) != {"ordinal", "page", "block_id",
                                                       "snippet"}:
            raise KnowledgeError("UPSTREAM_INVALID_RESULT")
        ordinal, page = item["ordinal"], item["page"]
        if (type(ordinal) is not int or not 1 <= ordinal <= MAX_PAGE * PAGE_SIZE
                or ordinal <= previous):
            raise KnowledgeError("UPSTREAM_INVALID_RESULT")
        previous = ordinal
        if type(page) is not int or page != (ordinal - 1) // PAGE_SIZE + 1:
            raise KnowledgeError("UPSTREAM_INVALID_RESULT")
        if item["block_id"] != f"b{ordinal}":
            raise KnowledgeError("UPSTREAM_INVALID_RESULT")
        snippet = source_display_string(item["snippet"], 240, physical_ids=physical)
        if not snippet.strip():
            raise KnowledgeError("UPSTREAM_INVALID_RESULT")
        matches.append({"ordinal": ordinal, "page": page,
                        "block_id": f"b{ordinal}", "snippet": snippet})
    return matches, searched, capped
