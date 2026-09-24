from __future__ import annotations

from typing import Any, Mapping, Protocol


class PortalProvider(Protocol):
    """Experience adapter implemented by an HBOS business application."""

    def manifest(self) -> Mapping[str, Any]:
        ...

    def access_context(self) -> Mapping[str, Any]:
        ...

    # Optional methods are invoked only when declared by the manifest.
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
