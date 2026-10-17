from __future__ import annotations

import secrets
import time
from dataclasses import asdict
from typing import Any

from hb_knowledge_app.hb_knowledge.errors import KnowledgeError
from hb_knowledge_app.hb_knowledge.gateway import EvidenceRecord
from hb_knowledge_app.hb_knowledge.policy import SubjectPolicy


EVIDENCE_TTL_SECONDS = 5 * 60
REQUESTS_PER_MINUTE = 12
EXCERPT_CODEPOINTS_PER_MINUTE = 5_000


def _evidence_key(evidence_id: str) -> str:
    return f"hbos:p1:knowledge:evidence:{evidence_id}"


def issue_evidence(cache: Any, policy: SubjectPolicy, record: EvidenceRecord) -> str:
    evidence_id = secrets.token_urlsafe(24)
    payload = {
        "subject": policy.subject,
        "policy_revision": policy.policy_revision,
        "expires_at": int(time.time()) + EVIDENCE_TTL_SECONDS,
        "record": asdict(record),
    }
    cache.set_value(
        _evidence_key(evidence_id),
        payload,
        expires_in_sec=EVIDENCE_TTL_SECONDS,
    )
    return evidence_id


def resolve_evidence(cache: Any, policy: SubjectPolicy, evidence_id: str) -> EvidenceRecord:
    if not evidence_id or len(evidence_id) > 128:
        raise KnowledgeError("EVIDENCE_INVALID", "该证据不可用或已过期。")
    payload = cache.get_value(_evidence_key(evidence_id), expires=True)
    if not isinstance(payload, dict):
        raise KnowledgeError("EVIDENCE_INVALID", "该证据不可用或已过期。")
    if payload.get("subject") != policy.subject:
        raise KnowledgeError("FORBIDDEN", "你没有权限查看该证据。")
    if payload.get("policy_revision") != policy.policy_revision:
        raise KnowledgeError("EVIDENCE_REVOKED", "权限已变更，请重新检索。")
    if int(payload.get("expires_at") or 0) < int(time.time()):
        raise KnowledgeError("EVIDENCE_INVALID", "该证据不可用或已过期。")
    raw_record = payload.get("record")
    if not isinstance(raw_record, dict):
        raise KnowledgeError("EVIDENCE_INVALID", "该证据不可用或已过期。")
    if raw_record.get("document_id") not in set(policy.document_ids):
        raise KnowledgeError("EVIDENCE_REVOKED", "权限已变更，请重新检索。")
    return EvidenceRecord(**raw_record)


def _consume_counter(cache: Any, key: str, amount: int, *, ttl: int = 70) -> int:
    # RedisWrapper inherits redis.Redis. Atomic INCRBY prevents multi-worker races.
    namespaced = cache.make_key(key)
    value = int(cache.incrby(namespaced, amount))
    if value == amount:
        cache.expire(namespaced, ttl)
    return value


def consume_request_budget(cache: Any, policy: SubjectPolicy) -> None:
    minute = int(time.time() // 60)
    value = _consume_counter(
        cache,
        f"hbos:p1:knowledge:requests:{policy.subject}:{minute}",
        1,
    )
    if value > REQUESTS_PER_MINUTE:
        raise KnowledgeError(
            "RATE_LIMITED",
            "检索过于频繁，请稍后重试。",
            retryable=True,
        )


def consume_excerpt_budget(cache: Any, policy: SubjectPolicy, codepoints: int) -> None:
    minute = int(time.time() // 60)
    value = _consume_counter(
        cache,
        f"hbos:p1:knowledge:excerpt:{policy.subject}:{minute}",
        max(0, int(codepoints)),
    )
    if value > EXCERPT_CODEPOINTS_PER_MINUTE:
        raise KnowledgeError(
            "EXTRACTION_LIMITED",
            "本时段可展示的证据摘录已达上限。",
            retryable=True,
        )
