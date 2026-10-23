from __future__ import annotations


def get_manifest() -> dict[str, object]:
    return {
        "contract_version": 1,
        "id": "twin",
        "title": "设备与工艺",
        "short_title": "Twin",
        "description": "私有设备模型、部件上下文与受控知识联动",
        "icon": "DeploymentUnitOutlined",
        "accent": "equipment",
        "order": 55,
        "migration_mode": "native",
        "route": "/hbos/twin",
        "capabilities": [],
    }
