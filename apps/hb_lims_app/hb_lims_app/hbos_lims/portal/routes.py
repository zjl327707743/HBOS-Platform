from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, unquote, urlsplit, urlunsplit

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


def build_stable_deep_link(
    route: str,
    route_params: dict[str, object] | None = None,
) -> str:
    """Project an app-internal LIMS route into the stable HBOS namespace."""

    value = str(route or "").strip()
    parsed = urlsplit(value)

    if parsed.scheme or parsed.netloc or parsed.fragment:
        raise ValueError("LIMS internal route must be a local path without fragment")

    decoded_path = unquote(parsed.path)
    if not decoded_path.startswith("/") or decoded_path.startswith("//"):
        raise ValueError("LIMS internal route must be an absolute local path")
    if "\\" in decoded_path:
        raise ValueError("LIMS internal route must not contain backslashes")

    segments = [segment for segment in decoded_path.split("/") if segment]
    if any(segment in {".", ".."} for segment in segments):
        raise ValueError("LIMS internal route must not contain traversal segments")

    suffix = parsed.path if parsed.path != "/" else ""
    stable_path = STABLE_PREFIX + suffix

    query_items = list(parse_qsl(parsed.query, keep_blank_values=True))
    for key, raw_value in (route_params or {}).items():
        if raw_value is None:
            continue
        if isinstance(raw_value, (list, tuple)):
            query_items.extend((str(key), str(item)) for item in raw_value)
        else:
            query_items.append((str(key), str(raw_value)))

    return urlunsplit(("", "", stable_path, urlencode(query_items, doseq=True), ""))


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
