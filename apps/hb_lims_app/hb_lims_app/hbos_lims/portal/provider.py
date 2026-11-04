from __future__ import annotations

from hb_lims_app.hbos_lims.portal.access import build_access_context
from hb_lims_app.hbos_lims.portal.audit import get_audit_projection
from hb_lims_app.hbos_lims.portal.coa import get_coa_projection
from hb_lims_app.hbos_lims.portal.ledger import get_ledger_projection
from hb_lims_app.hbos_lims.portal.manifest import get_manifest
from hb_lims_app.hbos_lims.portal.routes import resolve_stable_route
from hb_lims_app.hbos_lims.portal.search import search_results
from hb_lims_app.hbos_lims.portal.results import get_result_projection
from hb_lims_app.hbos_lims.portal.summary import get_summary_projection
from hb_lims_app.hbos_lims.portal.specifications import get_specification_projection
from hb_lims_app.hbos_lims.portal.retention import get_retention_projection
from hb_lims_app.hbos_lims.portal.stability import get_stability_projection
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

    def search(
        self,
        *,
        query: str,
        limit: int = 20,
    ) -> dict[str, object]:
        return search_results(query=query, limit=limit)

    def results(
        self,
        *,
        result_id: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
        keyword: str | None = None,
        status: str | None = None,
        verdict: str | None = None,
    ) -> dict[str, object]:
        return get_result_projection(
            result_id=result_id,
            limit=limit,
            cursor=cursor,
            keyword=keyword,
            status=status,
            verdict=verdict,
        )

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
    ) -> dict[str, object]:
        return get_ledger_projection(
            sample_type=sample_type,
            material=material,
            keyword=keyword,
            status=status,
            verdict=verdict,
            limit=limit,
            cursor=cursor,
        )

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
    ) -> dict[str, object]:
        return get_audit_projection(
            log_type=log_type,
            doctype_target=doctype_target,
            user=user,
            keyword=keyword,
            from_date=from_date,
            to_date=to_date,
            limit=limit,
            cursor=cursor,
        )

    def coa(
        self,
        *,
        coa_id: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
        keyword: str | None = None,
        status: str | None = None,
    ) -> dict[str, object]:
        return get_coa_projection(
            coa_id=coa_id,
            limit=limit,
            cursor=cursor,
            keyword=keyword,
            status=status,
        )

    def specifications(
        self,
        *,
        specification_id: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
        keyword: str | None = None,
        status: str | None = None,
    ) -> dict[str, object]:
        return get_specification_projection(
            specification_id=specification_id,
            limit=limit,
            cursor=cursor,
            keyword=keyword,
            status=status,
        )

    def retains(
        self,
        *,
        section: str | None = None,
        keyword: str | None = None,
        status: str | None = None,
        active: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> dict[str, object]:
        return get_retention_projection(
            section=section,
            keyword=keyword,
            status=status,
            active=active,
            limit=limit,
            cursor=cursor,
        )

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
    ) -> dict[str, object]:
        return get_stability_projection(
            section=section,
            keyword=keyword,
            status=status,
            month=month,
            condition=condition,
            exec_status=exec_status,
            stability_product=stability_product,
            stability_test_item=stability_test_item,
            condition_type=condition_type,
            limit=limit,
            offset=offset,
        )

    def my_tasks(
        self,
        *,
        limit: int = 20,
        cursor: str | None = None,
        view: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        keyword: str | None = None,
    ) -> dict[str, object]:
        return get_task_projection(
            limit=limit,
            cursor=cursor,
            view=view,
            status=status,
            priority=priority,
            keyword=keyword,
        )

    def resolve_route(self, stable_path: str) -> str:
        return resolve_stable_route(stable_path)


def get_provider() -> LimsPortalProvider:
    return LimsPortalProvider()
