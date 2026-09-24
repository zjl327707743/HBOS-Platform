from __future__ import annotations

import os

import frappe

from hbos_portal.services.access import evaluate_access
from hbos_portal.services.bootstrap import build_bootstrap
from hbos_portal.services.registry import build_registry


def _require_ci_authority() -> None:
    if os.environ.get("HBOS_PORTAL_INTEGRATION_CHECKS") != "1":
        raise RuntimeError(
            "HBOS Portal integration checks require HBOS_PORTAL_INTEGRATION_CHECKS=1"
        )


def run() -> dict[str, object]:
    """Verify real Frappe Hook -> Registry -> Access -> Bootstrap integration.

    This function is intentionally not whitelisted and is guarded by an
    explicit CI environment variable.
    """

    _require_ci_authority()

    frappe.set_user("Administrator")

    registry = build_registry()
    if registry.failures:
        raise AssertionError(
            "Portal Registry failures: "
            + "; ".join(
                f"{item.provider_path}:{item.code}:{item.detail}"
                for item in registry.failures
            )
        )

    if "lims" not in registry.entries:
        raise AssertionError("LIMS provider was not discovered by Frappe hooks")

    entry = registry.entries["lims"]
    manifest = entry.manifest.to_dict()

    if manifest["route"] != "/hbos/lims":
        raise AssertionError("LIMS stable route mismatch")
    if manifest["capabilities"]:
        raise AssertionError(
            "P3-LIMS-1 must not enable summary/tasks/search before their gates"
        )

    access = evaluate_access(entry)
    if not access.can_enter:
        raise AssertionError("Administrator must receive LIMS break-glass entry access")

    bootstrap = build_bootstrap()
    app_ids = [
        app["manifest"]["id"]
        for app in bootstrap["apps"]
    ]
    if "lims" not in app_ids:
        raise AssertionError("Authenticated Portal bootstrap did not expose LIMS")

    return {
        "registry_entries": sorted(registry.entries),
        "registry_failures": len(registry.failures),
        "lims_route": manifest["route"],
        "lims_manifest_capabilities": manifest["capabilities"],
        "lims_access": access.can_enter,
        "bootstrap_apps": app_ids,
        "user": bootstrap["user"]["id"],
    }
