from __future__ import annotations


def get_manifest() -> dict[str, object]:
    return {
        "contract_version": 1,
        "id": "inventory",
        "title": "仓储库存",
        "short_title": "Inventory",
        "description": "入库、出库、批次、货位、盘点与效期管理",
        "icon": "InboxOutlined",
        "accent": "inventory",
        "order": 20,
        "migration_mode": "legacy",
        "route": "/hbos/inventory",
        # P3-INV-2 exposes only a permission-aware count projection.
        "capabilities": ["summary"],
    }
