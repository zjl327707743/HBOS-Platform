from __future__ import annotations

from typing import Any, Mapping, Protocol


class PortalProvider(Protocol):
    """Experience adapter implemented by an HBOS business application."""

    def manifest(self) -> Mapping[str, Any]:
        ...

    def access_context(self) -> Mapping[str, Any]:
        ...

    # Optional implementation-route adapter. This is not a data capability.
    # Portal stable URLs remain /hbos/<app>/... even when the current
    # implementation is mounted elsewhere.
    def resolve_route(self, stable_path: str) -> str:
        ...

    # Optional data methods are invoked only when declared by the manifest.
    def summary(self) -> Mapping[str, Any]:
        ...

    def my_tasks(
        self,
        *,
        limit: int = 20,
        cursor: str | None = None,
    ) -> Mapping[str, Any]:
        ...

    def search(
        self,
        *,
        query: str,
        limit: int = 20,
    ) -> Mapping[str, Any]:
        ...
