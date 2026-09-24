from __future__ import annotations

from urllib.parse import unquote, urlsplit, urlunsplit

STABLE_PREFIX = "/hbos/lims"
IMPLEMENTATION_PREFIX = "/hbos-lims"


def _validated_path(raw_path: str) -> tuple[str, str]:
    value = str(raw_path or "").strip()
    parsed = urlsplit(value)

    if parsed.scheme or parsed.netloc or parsed.fragment:
        raise ValueError("LIMS Portal route must be a local path without fragment")

    decoded_path = unquote(parsed.path)
    if "\\" in decoded_path:
        raise ValueError("LIMS Portal route must not contain backslashes")

    segments = [segment for segment in decoded_path.split("/") if segment]
    if any(segment in {".", ".."} for segment in segments):
        raise ValueError("LIMS Portal route must not contain traversal segments")

    if decoded_path != STABLE_PREFIX and not decoded_path.startswith(STABLE_PREFIX + "/"):
        raise ValueError("LIMS stable route must stay under /hbos/lims")

    return parsed.path, parsed.query


def resolve_stable_route(stable_path: str) -> str:
    """Map stable HBOS product paths to the current LIMS implementation.

    The public contract remains /hbos/lims/... while the current native Vue
    build is served from /hbos-lims/....
    """

    path, query = _validated_path(stable_path)
    suffix = path[len(STABLE_PREFIX):]

    if suffix in {"", "/"}:
        implementation_path = IMPLEMENTATION_PREFIX + "/dashboard"
    else:
        implementation_path = IMPLEMENTATION_PREFIX + suffix

    return urlunsplit(("", "", implementation_path, query, ""))
