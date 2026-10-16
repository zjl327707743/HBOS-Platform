from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

from hb_knowledge_app.hb_knowledge.errors import KnowledgeError


SEARCH_CAPABILITY = "knowledge.search"
MAX_RESULTS_HARD_LIMIT = 5


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(dict.fromkeys(str(item).strip() for item in value if str(item).strip()))


def parse_policy_config(value: object) -> Mapping[str, Any]:
    if value in (None, ""):
        return {}
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise KnowledgeError(
                "POLICY_INVALID",
                "知识权限策略配置无效。",
            ) from exc
    if not isinstance(value, Mapping):
        raise KnowledgeError("POLICY_INVALID", "知识权限策略配置无效。")
    return value


@dataclass(frozen=True)
class SubjectPolicy:
    subject: str
    enabled: bool
    capabilities: tuple[str, ...]
    dataset_ids: tuple[str, ...]
    document_ids: tuple[str, ...]
    policy_revision: str
    max_results: int = MAX_RESULTS_HARD_LIMIT

    @property
    def can_enter(self) -> bool:
        return bool(self.enabled and self.subject and self.subject != "Guest")

    @property
    def can_search(self) -> bool:
        return bool(
            self.can_enter
            and SEARCH_CAPABILITY in self.capabilities
            and self.dataset_ids
            and self.document_ids
        )

    def require_search(self) -> None:
        if not self.can_enter:
            raise KnowledgeError("FORBIDDEN", "你没有权限访问知识助理。")
        if SEARCH_CAPABILITY not in self.capabilities:
            raise KnowledgeError("FORBIDDEN", "你没有知识检索权限。")
        if not self.dataset_ids or not self.document_ids:
            raise KnowledgeError(
                "EMPTY_SCOPE",
                "当前没有已发布且可检索的资料范围。",
            )


def policy_for_subject(
    config: object,
    subject: str | None,
    *,
    internal_user: bool = False,
) -> SubjectPolicy:
    normalized_subject = str(subject or "").strip()
    raw_config = parse_policy_config(config)
    raw_subjects = raw_config.get("subjects") or {}
    if not isinstance(raw_subjects, Mapping):
        raise KnowledgeError("POLICY_INVALID", "知识权限策略配置无效。")

    raw_policy = raw_subjects.get(normalized_subject)
    if raw_policy is None and internal_user and normalized_subject != "Guest":
        raw_policy = raw_config.get("default_internal")
    raw_policy = raw_policy or {}
    if not isinstance(raw_policy, Mapping):
        raw_policy = {}

    try:
        max_results = min(
            MAX_RESULTS_HARD_LIMIT,
            max(1, int(raw_policy.get("max_results") or MAX_RESULTS_HARD_LIMIT)),
        )
    except (TypeError, ValueError):
        max_results = MAX_RESULTS_HARD_LIMIT

    return SubjectPolicy(
        subject=normalized_subject,
        enabled=bool(raw_policy.get("enabled", False)),
        capabilities=_string_tuple(raw_policy.get("capabilities")),
        dataset_ids=_string_tuple(raw_policy.get("dataset_ids")),
        document_ids=_string_tuple(raw_policy.get("document_ids")),
        policy_revision=str(raw_policy.get("policy_revision") or "unconfigured"),
        max_results=max_results,
    )


def load_current_policy() -> SubjectPolicy:
    import frappe
    from hbos_portal.services.internal_users import load_internal_user_decision

    decision = load_internal_user_decision(frappe.session.user)
    import os
    if os.environ.get('HBOS_KNOWLEDGE_REFERENCE_CONFIG'):
        from .shared_reference import configuration
        cfg=configuration()
        eligible=decision.allowed and cfg['reader_role'] in frappe.get_roles(frappe.session.user)
        return SubjectPolicy(frappe.session.user,eligible,(SEARCH_CAPABILITY,) if eligible else (),
            tuple(cfg['dataset_aliases']),tuple(cfg['approved_document_ids']),cfg['policy_revision'])
    return policy_for_subject(
        frappe.conf.get("hbos_knowledge_policy"),
        frappe.session.user,
        internal_user=decision.allowed,
    )
