from __future__ import annotations

from hb_knowledge_app.hb_knowledge.policy import SubjectPolicy, policy_for_subject


APP_ID = "knowledge"


def build_access_context(policy: SubjectPolicy) -> dict[str, object]:
    return {
        "app_id": APP_ID,
        "can_enter": policy.can_enter,
        "capabilities": list(policy.capabilities) if policy.can_enter else [],
        "scopes": {},
    }


def build_access_from_config(config: object, subject: str | None) -> dict[str, object]:
    return build_access_context(policy_for_subject(config, subject))
