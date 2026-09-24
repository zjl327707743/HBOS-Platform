from __future__ import annotations

from urllib.parse import unquote, urlsplit, urlunsplit

from hbos_portal.contracts.errors import PortalException
from hbos_portal.services.access import require_app_access, require_authenticated_user
from hbos_portal.services.dispatcher import get_entry


def _reject_unsafe_url(value: str, *, label: str) -> tuple[str, str]:
    parsed = urlsplit(value)

    if parsed.scheme or parsed.netloc or parsed.fragment:
        raise PortalException(
            "INVALID_REQUEST",
            f"{label}必须是同源本地路径。",
        )

    decoded_path = unquote(parsed.path)
    if not decoded_path.startswith("/") or decoded_path.startswith("//"):
        raise PortalException(
            "INVALID_REQUEST",
            f"{label}必须是绝对本地路径。",
        )
    if "\\" in decoded_path:
        raise PortalException(
            "INVALID_REQUEST",
            f"{label}包含非法路径字符。",
        )

    segments = [segment for segment in decoded_path.split("/") if segment]
    if any(segment in {".", ".."} for segment in segments):
        raise PortalException(
            "INVALID_REQUEST",
            f"{label}包含非法路径段。",
        )

    return parsed.path, parsed.query


def validate_stable_path(app_id: str, stable_path: str) -> str:
    value = str(stable_path or "").strip()
    path, query = _reject_unsafe_url(value, label="稳定路由")

    prefix = f"/hbos/{app_id}"
    if path != prefix and not path.startswith(prefix + "/"):
        raise PortalException(
            "INVALID_REQUEST",
            "稳定路由与应用不匹配。",
        )

    return urlunsplit(("", "", path, query, ""))


def validate_resolved_path(resolved_path: str) -> str:
    value = str(resolved_path or "").strip()
    path, query = _reject_unsafe_url(value, label="实现路由")
    return urlunsplit(("", "", path, query, ""))


def resolve_stable_route(app_id: str, stable_path: str) -> dict[str, str]:
    require_authenticated_user()
    entry = get_entry(app_id)
    require_app_access(entry)

    path = validate_stable_path(app_id, stable_path)

    resolver = getattr(entry.provider, "resolve_route", None)
    if callable(resolver):
        try:
            resolved_path = resolver(path)
        except PortalException:
            raise
        except Exception as exc:
            raise PortalException(
                "CONTRACT_MISMATCH",
                "应用路由适配器返回失败。",
            ) from exc
    else:
        resolved_path = path

    resolved_path = validate_resolved_path(str(resolved_path))

    return {
        "app_id": app_id,
        "stable_path": path,
        "resolved_path": resolved_path,
        "migration_mode": entry.manifest.migration_mode,
    }
