from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


class AccessValidationError(ValueError):
    pass


@dataclass(frozen=True)
class AccessContext:
    app_id: str
    can_enter: bool
    capabilities: tuple[str, ...] = ()
    scopes: Mapping[str, tuple[str, ...]] = field(default_factory=dict)

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
        *,
        expected_app_id: str,
    ) -> "AccessContext":
        app_id = str(value.get("app_id", "")).strip()
        if app_id != expected_app_id:
            raise AccessValidationError(
                f"access app_id mismatch: expected {expected_app_id}"
            )

        raw_scopes = value.get("scopes") or {}
        if not isinstance(raw_scopes, Mapping):
            raise AccessValidationError("access scopes must be a mapping")

        scopes = {
            str(key): tuple(str(item) for item in (items or []))
            for key, items in raw_scopes.items()
        }

        return cls(
            app_id=app_id,
            can_enter=bool(value.get("can_enter", False)),
            capabilities=tuple(
                dict.fromkeys(str(x) for x in (value.get("capabilities") or []))
            ),
            scopes=scopes,
        )

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["capabilities"] = list(self.capabilities)
        result["scopes"] = {
            key: list(items) for key, items in self.scopes.items()
        }
        return result
