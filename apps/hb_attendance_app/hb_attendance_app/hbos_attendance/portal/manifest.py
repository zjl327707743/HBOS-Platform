from __future__ import annotations


def get_manifest() -> dict[str, object]:
    return {
        "contract_version": 1,
        "id": "attendance",
        "title": "考勤管理",
        "short_title": "Attendance",
        "description": "考勤、排班、异常、月度汇总与 HR 运营",
        "icon": "ClockCircleOutlined",
        "accent": "attendance",
        "order": 10,
        "migration_mode": "legacy",
        "route": "/hbos/attendance",
        # P3-ATT-1 registers entry/access only.
        "capabilities": [],
    }
