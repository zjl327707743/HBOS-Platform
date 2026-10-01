from __future__ import annotations

from collections.abc import Sequence

from hb_lims_app.hbos_lims import workflow_contract as wf
from hb_lims_app.hbos_lims.todo_contract import LIMS_BUSINESS_ROLES

APP_ID = "lims"
READ_CAPABILITY = "lims.read"
AUDIT_READ_CAPABILITY = "lims.audit.read"
RESULTS_READ_CAPABILITY = "lims.results.read"
LEDGER_READ_CAPABILITY = "lims.ledger.read"
RETENTION_READ_CAPABILITY = "lims.retention.read"
RESULTS_SUBMIT_CAPABILITY = "lims.results.submit"
RESULTS_REVIEW_CAPABILITY = "lims.results.review"
RESULTS_APPROVE_CAPABILITY = "lims.results.approve"


def build_access_context(user: str | None, roles: Sequence[str] | None) -> dict[str, object]:
    """Translate LIMS-owned role authority into the Portal access contract.

    Raw role names remain inside LIMS. Portal receives only semantic access.
    """

    normalized_user = str(user or "").strip()
    role_set = {str(role) for role in (roles or ())}

    if not normalized_user or normalized_user == "Guest":
        can_enter = False
    else:
        has_business_role = bool(role_set.intersection(LIMS_BUSINESS_ROLES))
        has_system_read_role = wf.ROLE_SYSTEM in role_set
        # Built-in Administrator is LIMS' audited break-glass identity.
        can_enter = (
            normalized_user == "Administrator"
            or has_business_role
            or has_system_read_role
        )

    is_break_glass = normalized_user == "Administrator"
    capabilities = [READ_CAPABILITY]
    if is_break_glass or role_set.intersection({wf.ROLE_ANALYST, wf.ROLE_REVIEWER, wf.ROLE_MANAGER, wf.ROLE_SYSTEM}):
        capabilities.extend((RESULTS_READ_CAPABILITY, LEDGER_READ_CAPABILITY))
    if is_break_glass or role_set.intersection({wf.ROLE_ANALYST, wf.ROLE_REVIEWER, wf.ROLE_LIMS_QA, wf.ROLE_MANAGER, wf.ROLE_SYSTEM}):
        capabilities.append(RETENTION_READ_CAPABILITY)
    if is_break_glass or role_set.intersection({wf.ROLE_ANALYST, wf.ROLE_MANAGER}):
        capabilities.append(RESULTS_SUBMIT_CAPABILITY)
    if is_break_glass or role_set.intersection({wf.ROLE_REVIEWER, wf.ROLE_MANAGER}):
        capabilities.extend((RESULTS_REVIEW_CAPABILITY, RESULTS_APPROVE_CAPABILITY))
    if (
        is_break_glass
        or role_set.intersection({wf.ROLE_REVIEWER, wf.ROLE_MANAGER, wf.ROLE_SYSTEM})
    ):
        capabilities.append(AUDIT_READ_CAPABILITY)

    return {
        "app_id": APP_ID,
        "can_enter": can_enter,
        "capabilities": capabilities if can_enter else [],
        "scopes": {},
    }
