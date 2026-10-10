from __future__ import annotations

import hashlib
import re
import secrets
from dataclasses import asdict
from typing import Callable

import frappe

from hb_knowledge_app.hb_knowledge.errors import KnowledgeError, error_payload
from hb_knowledge_app.hb_knowledge.evidence import (
    consume_excerpt_budget,
    consume_request_budget,
    issue_evidence,
    resolve_evidence as resolve_cached_evidence,
)
from hb_knowledge_app.hb_knowledge.gateway import load_gateway_client
from hb_knowledge_app.hb_knowledge.policy import MAX_RESULTS_HARD_LIMIT, load_current_policy


EQUIPMENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def _private_no_store() -> None:
    frappe.local.response_headers["Cache-Control"] = "private, no-store, max-age=0"
    frappe.local.response_headers["Pragma"] = "no-cache"


def _subject_fingerprint(subject: str) -> str:
    """Return a stable audit key without writing the account identifier to logs."""
    return hashlib.sha256(subject.encode("utf-8")).hexdigest()[:16]


def _run(action: Callable[[], dict[str, object]]) -> dict[str, object]:
    _private_no_store()
    try:
        return {"ok": True, "data": action()}
    except KnowledgeError as exc:
        return error_payload(exc)
    except Exception:
        request_id = secrets.token_hex(8)
        frappe.log_error(
            title=f"HBOS Knowledge API error [{request_id}]",
            message=frappe.get_traceback(),
        )
        return error_payload(
            KnowledgeError(
                "SERVICE_ERROR",
                "知识服务暂时不可用。",
                retryable=True,
            )
        )


@frappe.whitelist(methods=["GET"])
def get_status() -> dict[str, object]:
    def _load() -> dict[str, object]:
        policy = load_current_policy()
        client = load_gateway_client()
        return {
            "can_enter": policy.can_enter,
            "can_search": policy.can_search,
            "policy_revision": policy.policy_revision if policy.can_enter else None,
            "gateway_configured": client.configured,
            "ask_enabled": False,
            "mode": "retrieval",
        }

    return _run(_load)


def _search_context(
    equipment_id: str | None,
    asset_id: str | None,
    component_id: str | None,
) -> dict[str, str]:
    equipment = str(equipment_id or "").strip()
    asset = str(asset_id or "").strip()
    component = str(component_id or "").strip()
    if not equipment:
        if asset or component:
            raise KnowledgeError("INVALID_REQUEST", "部件检索必须包含设备标识。")
        return {}
    if not EQUIPMENT_ID_PATTERN.fullmatch(equipment):
        raise KnowledgeError("INVALID_REQUEST", "设备标识无效。")
    if len(asset) > 200 or len(component) > 200:
        raise KnowledgeError("INVALID_REQUEST", "部件检索上下文无效。")
    context = {"equipment_id": equipment}
    if asset:
        context["asset_id"] = asset
    if component:
        context["component_id"] = component
    return context


@frappe.whitelist(methods=["POST"])
def search(
    query: str,
    limit: int | str | None = None,
    equipment_id: str | None = None,
    asset_id: str | None = None,
    component_id: str | None = None,
) -> dict[str, object]:
    def _search() -> dict[str, object]:
        policy = load_current_policy()
        policy.require_search()
        normalized_query = str(query or "").strip()
        if not normalized_query or len(normalized_query) > 500:
            raise KnowledgeError("INVALID_REQUEST", "请输入 1–500 字的检索内容。")
        try:
            requested_limit = int(limit or policy.max_results)
        except (TypeError, ValueError) as exc:
            raise KnowledgeError("INVALID_REQUEST", "检索数量配置无效。") from exc
        normalized_limit = min(MAX_RESULTS_HARD_LIMIT, policy.max_results, max(1, requested_limit))
        context = _search_context(equipment_id, asset_id, component_id)

        consume_request_budget(frappe.cache, policy)
        request_id = secrets.token_hex(12)
        records = load_gateway_client().search(
            query=normalized_query,
            policy=policy,
            limit=normalized_limit,
            request_id=request_id,
            context=context,
        )
        consume_excerpt_budget(
            frappe.cache,
            policy,
            sum(len(record.excerpt) for record in records),
        )

        results = []
        for record in records:
            evidence_id = issue_evidence(frappe.cache, policy, record)
            results.append(
                {
                    "document_id": record.document_id,
                    "title": record.title,
                    "version": record.version,
                    "status_note": record.status_note,
                    "section": record.section,
                    "page_number": record.page_number,
                    "excerpt": record.excerpt,
                    "evidence_id": evidence_id,
                }
            )

        frappe.logger("hbos_knowledge").info(
            {
                "request_id": request_id,
                "subject_key": _subject_fingerprint(policy.subject),
                "operation": "search",
                "policy_revision": policy.policy_revision,
                "result_count": len(results),
                "equipment_id": context.get("equipment_id"),
                # Query and excerpts are intentionally excluded.
            }
        )
        return {
            "request_id": request_id,
            "mode": "retrieval",
            "context": context,
            "results": results,
        }

    return _run(_search)


@frappe.whitelist(methods=["POST"])
def resolve_evidence(evidence_id: str) -> dict[str, object]:
    def _resolve() -> dict[str, object]:
        policy = load_current_policy()
        policy.require_search()
        record = resolve_cached_evidence(frappe.cache, policy, str(evidence_id or ""))
        consume_excerpt_budget(frappe.cache, policy, len(record.excerpt))
        data = asdict(record)
        data.pop("chunk_id", None)
        data.pop("dataset_id", None)
        data["evidence_id"] = evidence_id
        return data

    return _run(_resolve)
