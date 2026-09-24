from __future__ import annotations

from urllib.parse import unquote, urlsplit, urlunsplit

STABLE_PREFIX = "/hbos/attendance"
CURRENT_DASHBOARD = "/app/hbos-attendance-dashboard"


def resolve_stable_route(stable_path: str) -> str:
    """Map stable HBOS Attendance routes to the current Desk implementation."""

    value = str(stable_path or "").strip()
    parsed = urlsplit(value)

    if parsed.scheme or parsed.netloc or parsed.fragment:
        raise ValueError("Attendance Portal route must be a local path without fragment")

    decoded_path = unquote(parsed.path)
    if "\" in decoded_path:
        raise ValueError("Attendance Portal route must not contain backslashes")

    segments = [segment for segment in decoded_path.split("/") if segment]
    if any(segment in {".", ".."} for segment in segments):
        raise ValueError("Attendance Portal route must not contain traversal segments")

    if decoded_path not in {STABLE_PREFIX, STABLE_PREFIX + "/", STABLE_PREFIX + "/dashboard"}:
        raise ValueError("Attendance stable route is not registered yet")

    return urlunsplit(("", "", CURRENT_DASHBOARD, parsed.query, ""))
