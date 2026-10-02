from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TwinError(Exception):
    code: str
    public_message: str
    retryable: bool = False

    def __str__(self) -> str:
        return self.public_message


def error_payload(error: TwinError) -> dict[str, object]:
    return {
        "ok": False,
        "error": {
            "code": error.code,
            "message": error.public_message,
            "retryable": error.retryable,
        },
    }
