from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable

from hbos_portal.contracts.manifest import AppManifest, ManifestValidationError
from hbos_portal.portal.constants import CAPABILITY_METHODS, PROVIDER_HOOK


@dataclass(frozen=True)
class RegistryEntry:
    manifest: AppManifest
    provider: Any


@dataclass(frozen=True)
class RegistryFailure:
    provider_path: str
    code: str
    detail: str


@dataclass
class RegistrySnapshot:
    entries: dict[str, RegistryEntry]
    failures: list[RegistryFailure]

    def ordered_entries(self) -> list[RegistryEntry]:
        return sorted(
            self.entries.values(),
            key=lambda item: (item.manifest.order, item.manifest.id),
        )


def _default_sources() -> tuple[Iterable[str], Callable[[str], Any]]:
    import frappe

    paths = frappe.get_hooks(PROVIDER_HOOK) or []
    return paths, frappe.get_attr


def build_registry(
    provider_paths: Iterable[str] | None = None,
    *,
    resolver: Callable[[str], Any] | None = None,
) -> RegistrySnapshot:
    if provider_paths is None or resolver is None:
        default_paths, default_resolver = _default_sources()
        if provider_paths is None:
            provider_paths = default_paths
        if resolver is None:
            resolver = default_resolver

    entries: dict[str, RegistryEntry] = {}
    failures: list[RegistryFailure] = []
    blocked_ids: set[str] = set()

    for raw_path in provider_paths:
        path = str(raw_path)
        try:
            factory = resolver(path)
            provider = factory()
            manifest = AppManifest.from_mapping(provider.manifest())

            if manifest.id in blocked_ids:
                failures.append(
                    RegistryFailure(
                        path,
                        "DUPLICATE_APP_ID",
                        f"duplicate app id: {manifest.id}",
                    )
                )
                continue

            if manifest.id in entries:
                entries.pop(manifest.id, None)
                blocked_ids.add(manifest.id)
                failures.append(
                    RegistryFailure(
                        path,
                        "DUPLICATE_APP_ID",
                        f"duplicate app id: {manifest.id}",
                    )
                )
                continue

            for capability in manifest.capabilities:
                method_name = CAPABILITY_METHODS[capability]
                if not callable(getattr(provider, method_name, None)):
                    raise ManifestValidationError(
                        f"capability {capability} requires method {method_name}"
                    )

            entries[manifest.id] = RegistryEntry(manifest=manifest, provider=provider)
        except Exception as exc:
            failures.append(
                RegistryFailure(
                    provider_path=path,
                    code="PROVIDER_REGISTRATION_ERROR",
                    detail=str(exc),
                )
            )

    return RegistrySnapshot(entries=entries, failures=failures)
