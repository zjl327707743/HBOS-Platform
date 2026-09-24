from __future__ import annotations

from hb_lims_app.hbos_lims.portal.access import build_access_context
from hb_lims_app.hbos_lims.portal.manifest import get_manifest


class LimsPortalProvider:
    """Thin experience adapter; business authorization remains in LIMS."""

    def manifest(self) -> dict[str, object]:
        return get_manifest()

    def access_context(self) -> dict[str, object]:
        import frappe

        user = frappe.session.user
        roles = frappe.get_roles(user) if user and user != "Guest" else []
        return build_access_context(user, roles)


def get_provider() -> LimsPortalProvider:
    return LimsPortalProvider()
