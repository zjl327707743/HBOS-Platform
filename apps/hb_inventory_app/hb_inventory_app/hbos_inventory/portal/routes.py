from __future__ import annotations

from urllib.parse import unquote, urlsplit, urlunsplit

STABLE_PREFIX = "/hbos/inventory"
CURRENT_ENTRY = "/app/hbos-photo-intake"


def resolve_stable_route(stable_path: str) -> str:
    """Map stable Inventory routes to the current controlled Desk entry."""

    value = str(stable_path or "").strip()
    parsed = urlsplit(value)

    if parsed.scheme or parsed.netloc or parsed.fragment:
        raise ValueError("Inventory Portal route must be a local path without fragment")

    decoded_path = unquote(parsed.path)
    if "\\" in decoded_path:
        raise ValueError("Inventory Portal route must not contain backslashes")

    segments = [segment for segment in decoded_path.split("/") if segment]
    if any(segment in {".", ".."} for segment in segments):
        raise ValueError("Inventory Portal route must not contain traversal segments")

    if decoded_path not in {STABLE_PREFIX, STABLE_PREFIX + "/", STABLE_PREFIX + "/intake"}:
        raise ValueError("Inventory stable route is not registered yet")

    return urlunsplit(("", "", CURRENT_ENTRY, parsed.query, ""))
