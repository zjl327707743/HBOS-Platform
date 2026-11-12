from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

from hb_twin_app.hb_twin.errors import TwinError


VIEW_CAPABILITY = "twin.view"


def _parse(value: object) -> Mapping[str, Any]:
    if value in (None, ""):
        return {}
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise TwinError("POLICY_INVALID", "设备权限策略配置无效。") from exc
    if not isinstance(value, Mapping):
        raise TwinError("POLICY_INVALID", "设备权限策略配置无效。")
    return value


def _strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(dict.fromkeys(str(item).strip() for item in value if str(item).strip()))


@dataclass(frozen=True)
class TwinPolicy:
    subject: str
    enabled: bool
    capabilities: tuple[str, ...]
    equipment_ids: tuple[str, ...]
    policy_revision: str

    @property
    def can_enter(self) -> bool:
        return bool(self.enabled and self.subject and self.subject != "Guest")

    def require_equipment(self, equipment_id: str) -> None:
        if not self.can_enter or VIEW_CAPABILITY not in self.capabilities:
            raise TwinError("FORBIDDEN", "你没有权限访问设备模块。")
        if equipment_id not in self.equipment_ids:
            raise TwinError("FORBIDDEN", "你没有权限查看该设备。")


def policy_for_subject(
    config: object,
    subject: str | None,
    *,
    internal_user: bool = False,
) -> TwinPolicy:
    normalized_subject = str(subject or "").strip()
    raw = _parse(config)
    subjects = raw.get("subjects") or {}
    if not isinstance(subjects, Mapping):
        raise TwinError("POLICY_INVALID", "设备权限策略配置无效。")
    item = subjects.get(normalized_subject)
    if item is None and internal_user and normalized_subject != "Guest":
        item = raw.get("default_internal")
    item = item or {}
    if not isinstance(item, Mapping):
        item = {}
    return TwinPolicy(
        subject=normalized_subject,
        enabled=bool(item.get("enabled", False)),
        capabilities=_strings(item.get("capabilities")),
        equipment_ids=_strings(item.get("equipment_ids")),
        policy_revision=str(item.get("policy_revision") or "unconfigured"),
    )


def load_current_policy() -> TwinPolicy:
    import frappe
    from hbos_portal.services.internal_users import load_internal_user_decision

    decision = load_internal_user_decision(frappe.session.user)
    return policy_for_subject(
        frappe.conf.get("hbos_twin_policy"),
        frappe.session.user,
        internal_user=decision.allowed,
    )
