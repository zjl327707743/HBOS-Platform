from __future__ import annotations

from collections.abc import Callable
from typing import Any

from hbos_portal.contracts.errors import (
    PortalException,
    error_response,
    new_trace_id,
    success_response,
)


def call_safely(func: Callable[[], Any]) -> dict[str, object]:
    try:
        return success_response(func())
    except PortalException as exc:
        return error_response(exc)
    except Exception:
        import frappe

        trace_id = new_trace_id()
        frappe.log_error(
            title=f"HBOS Portal unhandled API error [{trace_id}]",
            message=frappe.get_traceback(),
        )
        return error_response(
            PortalException(
                "PROVIDER_ERROR",
                "HBOS 服务暂时不可用。",
                retryable=True,
                trace_id=trace_id,
            )
        )


def normalize_limit(value: int | str | None, *, default: int = 20) -> int:
    if value in (None, ""):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise PortalException(
            "INVALID_REQUEST",
            "limit 必须是整数。",
        ) from exc

    if parsed < 1 or parsed > 50:
        raise PortalException(
            "INVALID_REQUEST",
            "limit 必须在 1 到 50 之间。",
        )
    return parsed
