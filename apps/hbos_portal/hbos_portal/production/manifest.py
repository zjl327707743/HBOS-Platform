"""生产看板 —— Portal 侧的应用清单。

**为什么这个 provider 放在 `hbos_portal` 而不是独立 App**：
生产看板没有自己的 Frappe App（它的事实来源是独立 FastAPI + 飞书多维表格），
而新建 Frappe App 需要 Owner 单独授权。所以这里只放一个**适配器（BFF）**，
它不持有任何生产业务状态 —— 业务事实仍在外部服务。

注册后，`bootstrap` 才能把「生产看板」这个入口发给**有权限的**员工。
"""

from __future__ import annotations

APP_ID = "production"


def get_manifest() -> dict[str, object]:
    """稳定的应用元数据（Portal 契约）。"""

    return {
        "contract_version": 1,
        "id": APP_ID,
        "title": "生产看板",
        "short_title": "生产看板",
        "description": "产量达成、收率跟踪与工艺分析",
        "icon": "ThunderboltOutlined",
        "accent": "production",
        # 排序在 LIMS(30) 之后 —— 生产看板面向生产管理岗，不是全员首页项
        "order": 40,
        # 页面由 Portal SPA 自身渲染（原生 Vue 页），所以是 native；
        # 数据从受控后端 API 取得，不走 Desk。
        "migration_mode": "native",
        "route": "/hbos/production",
        # 本轮不提供 summary / tasks / search：
        # 生产看板尚无跨应用待办与搜索聚合，显式不给（不支持的能力显式关闭）。
        "capabilities": [],
    }
