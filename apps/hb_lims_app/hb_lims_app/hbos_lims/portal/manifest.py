from __future__ import annotations


def get_manifest() -> dict[str, object]:
    """Stable HBOS application metadata owned by LIMS."""

    return {
        "contract_version": 1,
        "id": "lims",
        "title": "实验室质量管理",
        "short_title": "LIMS",
        "description": "检验、质量、留样与稳定性管理",
        "icon": "ExperimentOutlined",
        "accent": "lims",
        "order": 30,
        "migration_mode": "native",
        "route": "/hbos/lims",
        # P3-LIMS-3 enables only the existing LIMS todo projection.
        # Summary and search remain behind later gates.
        "capabilities": ["tasks"],
    }
