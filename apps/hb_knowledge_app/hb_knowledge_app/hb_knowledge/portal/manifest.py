from __future__ import annotations


def get_manifest() -> dict[str, object]:
    return {
        "contract_version": 1,
        "id": "knowledge",
        "title": "知识助理",
        "short_title": "Knowledge",
        "description": "受控检索、来源证据与资料权限",
        "icon": "BulbOutlined",
        "accent": "knowledge",
        "order": 50,
        "migration_mode": "native",
        "route": "/hbos/knowledge",
        # Domain search stays off the public Portal search dispatcher until its
        # complete permission regression suite and corpus publication gate pass.
        "capabilities": [],
    }
