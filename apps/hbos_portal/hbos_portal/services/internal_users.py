from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping


DEFAULT_EXTERNAL_ROLES = frozenset({"Customer", "Supplier"})
DEFAULT_SERVICE_ROLES = frozenset({"HBOS Service Account", "Integration User"})
PRIVILEGED_ROLES = frozenset({"System Manager"})


def _configured_values(value: object) -> set[str]:
    if value in (None, ""):
        return set()
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return set()
        if stripped.startswith("["):
            try:
                value = json.loads(stripped)
            except json.JSONDecodeError:
                return {item.strip() for item in stripped.split(",") if item.strip()}
        else:
            return {item.strip() for item in stripped.split(",") if item.strip()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return {str(item).strip() for item in value if str(item).strip()}
    return set()


@dataclass(frozen=True)
class InternalUserDecision:
    user: str
    allowed: bool
    reason: str
    user_type: str | None = None


def classify_internal_user(
    user: str | None,
    *,
    account: Mapping[str, Any] | None,
    roles: set[str] | frozenset[str] | tuple[str, ...] | list[str],
    config: Mapping[str, Any] | None = None,
) -> InternalUserDecision:
    """Classify a Frappe account for basic internal Portal access.

    This does not grant roles. Enabled ordinary accounts can access the basic
    Portal while retaining explicit denials for visitors,
    service accounts, privileged accounts and locally configured exceptions.
    """

    normalized = str(user or "").strip()
    if not normalized or normalized.casefold() in {"guest", "administrator"}:
        return InternalUserDecision(normalized, False, "reserved_account")
    if not account or not bool(account.get("enabled")):
        return InternalUserDecision(normalized, False, "disabled_or_missing")

    user_type = str(account.get("user_type") or "").strip()
    if user_type not in {"Website User", "System User"}:
        return InternalUserDecision(normalized, False, "unsupported_user_type", user_type)

    settings = config or {}
    denied_accounts = {
        item.casefold()
        for item in (
            _configured_values(settings.get("hbos_portal_external_accounts"))
            | _configured_values(settings.get("hbos_portal_service_accounts"))
            | _configured_values(settings.get("hbos_portal_denied_accounts"))
        )
    }
    if normalized.casefold() in denied_accounts:
        return InternalUserDecision(normalized, False, "configured_account_denial", user_type)

    normalized_roles = {str(role).strip() for role in roles if str(role).strip()}
    denied_roles = (
        DEFAULT_EXTERNAL_ROLES
        | DEFAULT_SERVICE_ROLES
        | PRIVILEGED_ROLES
        | _configured_values(settings.get("hbos_portal_external_roles"))
        | _configured_values(settings.get("hbos_portal_service_roles"))
        | _configured_values(settings.get("hbos_portal_denied_roles"))
    )
    if normalized_roles & denied_roles:
        return InternalUserDecision(normalized, False, "denied_role", user_type)

    return InternalUserDecision(normalized, True, "enabled_internal_account", user_type)


def load_internal_user_decision(user: str | None = None) -> InternalUserDecision:
    import frappe

    subject = str(user or frappe.session.user or "").strip()
    account = frappe.db.get_value(
        "User",
        subject,
        ["enabled", "user_type"],
        as_dict=True,
    )
    roles = set(frappe.get_roles(subject)) if account else set()
    if account and 'System Manager' in roles and frappe.db.exists('DocType', 'HBOS Account Security'):
        operation = frappe.db.get_value('HBOS Account Security', subject, 'management_operation')
        if operation and frappe.db.exists('HBOS Account Operation', {
            'name': operation, 'kind': 'roles', 'state': 'Completed', 'source_user': subject}):
            # Only this named, explicitly approved recipient is eligible.
            # Other service/external/account denials remain authoritative.
            decision = classify_internal_user(subject, account=account, roles=roles - {'System Manager'}, config=frappe.conf)
            if decision.allowed:
                return InternalUserDecision(subject, True, 'explicit_management_handover', decision.user_type)
    return classify_internal_user(
        subject,
        account=account,
        roles=roles,
        config=frappe.conf,
    )
