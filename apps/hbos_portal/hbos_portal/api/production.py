"""生产看板的受控数据入口。

**浏览器只能到这里**，不再直连 FastAPI。每个端点都走同一道闸门：

    require_authenticated_user()   → 必须有有效 HBOS 会话
    get_entry("production")        → 应用必须已注册
    require_app_access(entry)      → 必须有生产看板权限（默认拒绝）

任何一步不过就拒绝，且**不返回任何生产数据**。
"""

from __future__ import annotations

import frappe

from hbos_portal.api._utils import call_safely
from hbos_portal.services.access import require_app_access, require_authenticated_user
from hbos_portal.services.dispatcher import get_entry

APP_ID = "production"


def _guarded_provider():
    """过一遍会话与授权闸门，返回 provider。"""

    require_authenticated_user()
    entry = get_entry(APP_ID)
    require_app_access(entry)
    return entry.provider


@frappe.whitelist()
def get_board(refresh: int | str | None = 0) -> dict[str, object]:
    """当月看板行。`refresh=1` 表示同步重取（前端「刷新」按钮）。"""

    def _load() -> dict[str, object]:
        provider = _guarded_provider()
        return provider.board(refresh=str(refresh or "0") not in {"0", "", "false", "False"})

    return call_safely(_load)


@frappe.whitelist()
def get_ai_analysis() -> dict[str, object]:
    """AI 工艺分析结论（只读结果表，**不触发分析、不写飞书**）。"""

    def _load() -> dict[str, object]:
        provider = _guarded_provider()
        return provider.ai_analysis()

    return call_safely(_load)
