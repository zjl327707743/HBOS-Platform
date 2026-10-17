from __future__ import annotations

from time import perf_counter
from typing import Any

from hbos_portal.contracts.errors import PortalException, new_trace_id
from hbos_portal.portal.constants import CAPABILITY_METHODS
from hbos_portal.services.access import require_app_access, require_authenticated_user
from hbos_portal.services.registry import RegistryEntry, build_registry


def get_entry(app_id: str) -> RegistryEntry:
    registry = build_registry()
    entry = registry.entries.get(app_id)
    if not entry:
        raise PortalException(
            "APP_UNAVAILABLE",
            "应用暂时不可用。",
            retryable=True,
        )
    return entry


def dispatch_provider(
    app_id: str,
    capability: str,
    **kwargs: Any,
) -> dict[str, object]:
    import frappe

    require_authenticated_user()

    if capability not in CAPABILITY_METHODS:
        raise PortalException(
            "INVALID_REQUEST",
            "不支持的 Portal capability。",
        )

    entry = get_entry(app_id)
    require_app_access(entry)

    if capability not in entry.manifest.capabilities:
        raise PortalException(
            "APP_DISABLED",
            "该应用当前未提供此能力。",
        )

    method_name = CAPABILITY_METHODS[capability]
    method = getattr(entry.provider, method_name, None)
    if not callable(method):
        raise PortalException(
            "CONTRACT_MISMATCH",
            "应用契约与实现不一致。",
        )

    trace_id = new_trace_id()
    started = perf_counter()

    try:
        data = method(**kwargs)
        duration_ms = round((perf_counter() - started) * 1000, 2)
        frappe.logger("hbos_portal").info(
            {
                "trace_id": trace_id,
                "app_id": app_id,
                "capability": capability,
                "duration_ms": duration_ms,
                "result": "success",
            }
        )
        return {
            "trace_id": trace_id,
            "generated_at": frappe.utils.now_datetime().isoformat(),
            "data": data,
        }
    except PortalException:
        raise
    except Exception:
        duration_ms = round((perf_counter() - started) * 1000, 2)
        frappe.log_error(
            title=f"HBOS Portal provider failed: {app_id}:{capability}",
            message=frappe.get_traceback(),
        )
        frappe.logger("hbos_portal").error(
            {
                "trace_id": trace_id,
                "app_id": app_id,
                "capability": capability,
                "duration_ms": duration_ms,
                "result": "failure",
            }
        )
        raise PortalException(
            "PROVIDER_ERROR",
            "应用数据暂时不可用。",
            retryable=True,
            trace_id=trace_id,
        )
