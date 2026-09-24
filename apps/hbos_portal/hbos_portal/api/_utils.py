from __future__ import annotations

from collections.abc import Callable
from typing import Any

from hbos_portal.contracts.errors import (
    PortalException,
    error_response,
    success_response,
)


def call_safely(func: Callable[[], Any]) -> dict[str, object]:
    try:
        return success_response(func())
    except PortalException as exc:
        return error_response(exc)


def normalize_limit(value: int | str | None, *, default: int = 20) -> int:
    if value in (None, ""):
        return default
    parsed = int(value)
    if parsed < 1 or parsed > 50:
        raise PortalException(
            "INVALID_REQUEST",
            "limit 必须在 1 到 50 之间。",
        )
    return parsed
