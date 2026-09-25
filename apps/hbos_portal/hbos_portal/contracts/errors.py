from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4


@dataclass(frozen=True)
class PortalError:
    code: str
    message: str
    retryable: bool = False
    trace_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
            "trace_id": self.trace_id,
        }


class PortalException(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        trace_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.error = PortalError(
            code=code,
            message=message,
            retryable=retryable,
            trace_id=trace_id,
        )


def new_trace_id() -> str:
    return uuid4().hex


def error_response(exc: PortalException) -> dict[str, object]:
    return {
        "ok": False,
        "error": exc.error.to_dict(),
    }


def success_response(data: object) -> dict[str, object]:
    return {
        "ok": True,
        "data": data,
    }
