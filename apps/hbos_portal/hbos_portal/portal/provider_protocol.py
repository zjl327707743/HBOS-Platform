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
        view: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        keyword: str | None = None,
    ) -> Mapping[str, Any]:
        ...

    def search(
        self,
        *,
        query: str,
        limit: int = 20,
    ) -> Mapping[str, Any]:
        ...

    def results(
        self,
        *,
        result_id: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
        keyword: str | None = None,
        status: str | None = None,
        verdict: str | None = None,
    ) -> Mapping[str, Any]:
        ...

    def ledger(
        self,
        *,
        sample_type: str | None = None,
        material: str | None = None,
        keyword: str | None = None,
        status: str | None = None,
        verdict: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> Mapping[str, Any]:
        ...

    def audit(
        self,
        *,
        log_type: str | None = None,
        doctype_target: str | None = None,
        user: str | None = None,
        keyword: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> Mapping[str, Any]:
        ...

    def coa(
        self,
        *,
        coa_id: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
        keyword: str | None = None,
        status: str | None = None,
    ) -> Mapping[str, Any]:
        ...

    def specifications(
        self,
        *,
        specification_id: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
        keyword: str | None = None,
        status: str | None = None,
    ) -> Mapping[str, Any]:
        ...

    def retains(
        self,
        *,
        section: str | None = None,
        keyword: str | None = None,
        status: str | None = None,
        active: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> Mapping[str, Any]:
        ...

    def stability(
        self,
        *,
        section: str | None = None,
        keyword: str | None = None,
        status: str | None = None,
        month: str | None = None,
        condition: str | None = None,
        exec_status: str | None = None,
        stability_product: str | None = None,
        stability_test_item: str | None = None,
        condition_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Mapping[str, Any]:
        ...
