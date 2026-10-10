from __future__ import annotations

from hb_twin_app.hb_twin.policy import TwinPolicy, policy_for_subject


APP_ID = "twin"


def build_access_context(policy: TwinPolicy) -> dict[str, object]:
    return {
        "app_id": APP_ID,
        "can_enter": policy.can_enter,
        "capabilities": list(policy.capabilities) if policy.can_enter else [],
        "scopes": {},
    }


def build_access_from_config(
    config: object,
    subject: str | None,
    *,
    internal_user: bool = False,
) -> dict[str, object]:
    return build_access_context(
        policy_for_subject(config, subject, internal_user=internal_user)
    )
