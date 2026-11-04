from __future__ import annotations

from typing import Any


def _count(value: object) -> int:
    try:
        return max(int(value or 0), 0)
    except (TypeError, ValueError):
        return 0


def project_dashboard_summary(payload: dict[str, Any]) -> dict[str, object]:
    """Project Attendance-owned HR dashboard facts into Portal semantics."""

    anomaly_people = _count(payload.get("anomaly_people"))
    late = _count(payload.get("total_late"))
    early = _count(payload.get("total_early"))
    absent = _count(payload.get("total_absent"))

    dashboard_link = "/hbos/attendance/dashboard"

    return {
        "app_id": "attendance",
        "generated_at": "",
        "status": "attention" if (anomaly_people or absent) else "normal",
        "metrics": [
            {
                "id": "attendance_anomaly_people",
                "label": "异常人员",
                "value": anomaly_people,
                "tone": "warning" if anomaly_people else "success",
                "deep_link": dashboard_link,
            },
            {
                "id": "attendance_late",
                "label": "本周迟到",
                "value": late,
                "tone": "warning" if late else "neutral",
                "deep_link": dashboard_link,
            },
            {
                "id": "attendance_early",
                "label": "本周早退",
                "value": early,
                "tone": "warning" if early else "neutral",
                "deep_link": dashboard_link,
            },
            {
                "id": "attendance_absent",
                "label": "本周缺勤",
                "value": absent,
                "tone": "critical" if absent else "success",
                "deep_link": dashboard_link,
            },
        ],
    }


def get_summary_projection() -> dict[str, object]:
    from hb_attendance_app.hbos_attendance.page.hbos_attendance_dashboard.dashboard_data import (
        get_data,
    )

    return project_dashboard_summary(get_data())
