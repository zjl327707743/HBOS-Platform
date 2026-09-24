from __future__ import annotations

from hb_lims_app.hbos_lims.portal.access import build_access_context
from hb_lims_app.hbos_lims.portal.manifest import get_manifest
from hb_lims_app.hbos_lims.portal.routes import resolve_stable_route
from hb_lims_app.hbos_lims.portal.summary import get_summary_projection
from hb_lims_app.hbos_lims.portal.tasks import get_task_projection


class LimsPortalProvider:
    """Thin experience adapter; business authorization remains in LIMS."""

    def manifest(self) -> dict[str, object]:
        return get_manifest()

    def access_context(self) -> dict[str, object]:
        import frappe

        user = frappe.session.user
        roles = frappe.get_roles(user) if user and user != "Guest" else []
        return build_access_context(user, roles)

    def summary(self) -> dict[str, object]:
        return get_summary_projection()

    def my_tasks(
        self,
        *,
        limit: int = 20,
        cursor: str | None = None,
    ) -> dict[str, object]:
        return get_task_projection(limit=limit, cursor=cursor)

    def resolve_route(self, stable_path: str) -> str:
        return resolve_stable_route(stable_path)


def get_provider() -> LimsPortalProvider:
    return LimsPortalProvider()
