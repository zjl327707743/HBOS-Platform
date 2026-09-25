from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from hbos_portal.portal.constants import (
    CONTRACT_VERSION,
    SUPPORTED_MIGRATION_MODES,
    SUPPORTED_PROVIDER_CAPABILITIES,
)


class ManifestValidationError(ValueError):
    pass


@dataclass(frozen=True)
class AppManifest:
    contract_version: int
    id: str
    title: str
    short_title: str
    description: str
    icon: str
    accent: str
    order: int
    migration_mode: str
    route: str
    capabilities: tuple[str, ...]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "AppManifest":
        required = (
            "contract_version",
            "id",
            "title",
            "short_title",
            "description",
            "icon",
            "accent",
            "order",
            "migration_mode",
            "route",
            "capabilities",
        )
        missing = [field for field in required if field not in value]
        if missing:
            raise ManifestValidationError(
                f"manifest missing fields: {', '.join(missing)}"
            )

        contract_version = int(value["contract_version"])
        if contract_version != CONTRACT_VERSION:
            raise ManifestValidationError(
                f"unsupported contract version: {contract_version}"
            )

        app_id = str(value["id"]).strip()
        if not app_id:
            raise ManifestValidationError("manifest id must not be empty")

        migration_mode = str(value["migration_mode"])
        if migration_mode not in SUPPORTED_MIGRATION_MODES:
            raise ManifestValidationError(
                f"unsupported migration mode: {migration_mode}"
            )

        capabilities = tuple(dict.fromkeys(str(x) for x in value["capabilities"]))
        unknown = sorted(set(capabilities) - SUPPORTED_PROVIDER_CAPABILITIES)
        if unknown:
            raise ManifestValidationError(
                f"unsupported capabilities: {', '.join(unknown)}"
            )

        route = str(value["route"]).strip()
        if not route.startswith("/hbos/"):
            raise ManifestValidationError("manifest route must use /hbos/<app>")

        return cls(
            contract_version=contract_version,
            id=app_id,
            title=str(value["title"]),
            short_title=str(value["short_title"]),
            description=str(value["description"]),
            icon=str(value["icon"]),
            accent=str(value["accent"]),
            order=int(value["order"]),
            migration_mode=migration_mode,
            route=route,
            capabilities=capabilities,
        )

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["capabilities"] = list(self.capabilities)
        return result
