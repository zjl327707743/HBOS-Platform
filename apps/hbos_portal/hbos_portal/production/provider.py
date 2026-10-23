"""生产看板的 Portal Provider（适配器）。

它**不持有生产业务状态** —— 业务事实在独立 FastAPI + 飞书多维表格。
这里只做三件事：报清单、判权限、把受控请求转给 FastAPI。
"""

from __future__ import annotations

from hbos_portal.contracts.errors import PortalException, new_trace_id
from hbos_portal.production.access import build_access_context
from hbos_portal.production.manifest import get_manifest
from hbos_portal.production.proxy import fetch_json


class ProductionPortalProvider:
    """Portal 体验适配器；业务授权真相在 HBOS 侧（见 access.py）。"""

    def manifest(self) -> dict[str, object]:
        return get_manifest()

    def access_context(self) -> dict[str, object]:
        import frappe

        user = frappe.session.user
        roles = frappe.get_roles(user) if user and user != "Guest" else []
        return build_access_context(user, roles)

    # --- 数据端点（由 api/production.py 在权限闸门之后调用）--------------

    def board(self, *, refresh: bool = False) -> dict[str, object]:
        """当月看板行（含异常闭环）。"""
        try:
            return fetch_json(
                "/production/monthly",
                params={"refresh": "1"} if refresh else None,
            )
        except PortalException:
            raise
        except Exception:
            trace_id = new_trace_id()
            import frappe

            frappe.log_error(
                title=f"HBOS production board error [{trace_id}]",
                message=frappe.get_traceback(),
            )
            raise PortalException(
                "PROVIDER_ERROR",
                "生产看板数据暂时不可用，请稍后重试。",
                retryable=True,
                trace_id=trace_id,
            ) from None

    def ai_analysis(self) -> dict[str, object]:
        """AI 工艺分析结论（读结果表，不触发分析）。"""
        try:
            return fetch_json("/production/ai-analysis")
        except PortalException:
            raise
        except Exception:
            trace_id = new_trace_id()
            import frappe

            frappe.log_error(
                title=f"HBOS production ai-analysis error [{trace_id}]",
                message=frappe.get_traceback(),
            )
            raise PortalException(
                "PROVIDER_ERROR",
                "AI 工艺分析结果暂时不可用。",
                retryable=True,
                trace_id=trace_id,
            ) from None


def get_provider() -> ProductionPortalProvider:
    return ProductionPortalProvider()
