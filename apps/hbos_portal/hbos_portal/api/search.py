from __future__ import annotations

import frappe

from hbos_portal.api._utils import call_safely, normalize_limit
from hbos_portal.contracts.errors import PortalException
from hbos_portal.services.access import evaluate_access, require_authenticated_user
from hbos_portal.services.dispatcher import dispatch_provider
from hbos_portal.services.registry import build_registry


@frappe.whitelist()
def search(
    query: str,
    limit: int | str | None = 20,
) -> dict[str, object]:
    def _load() -> dict[str, object]:
        require_authenticated_user()
        q = str(query or "").strip()
        if not q:
            raise PortalException(
                "INVALID_REQUEST",
                "请输入搜索内容。",
            )

        normalized_limit = normalize_limit(limit)
        registry = build_registry()
        results: list[object] = []
        provider_errors: list[dict[str, str]] = []

        for entry in registry.ordered_entries():
            if "search" not in entry.manifest.capabilities:
                continue

            try:
                access = evaluate_access(entry)
                if not access.can_enter:
                    continue
                payload = dispatch_provider(
                    entry.manifest.id,
                    "search",
                    query=q,
                    limit=normalized_limit,
                )
                data = payload.get("data")
                if isinstance(data, dict):
                    provider_results = data.get("results") or []
                elif isinstance(data, list):
                    provider_results = data
                else:
                    provider_results = []
                results.extend(provider_results)
            except PortalException as exc:
                provider_errors.append(
                    {
                        "app_id": entry.manifest.id,
                        "code": exc.error.code,
                    }
                )

        return {
            "query": q,
            "results": results[:normalized_limit],
            "provider_errors": provider_errors,
        }

    return call_safely(_load)
