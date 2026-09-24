from __future__ import annotations

from hbos_portal.contracts.errors import PortalException
from hbos_portal.services.access import require_app_access, require_authenticated_user
from hbos_portal.services.dispatcher import get_entry


def resolve_stable_route(app_id: str, stable_path: str) -> dict[str, str]:
    require_authenticated_user()
    entry = get_entry(app_id)
    require_app_access(entry)

    prefix = f"/hbos/{app_id}"
    path = str(stable_path or "").strip()
    if not path.startswith(prefix):
        raise PortalException(
            "INVALID_REQUEST",
            "稳定路由与应用不匹配。",
        )

    # P2 keeps the stable route unchanged. Legacy / hybrid implementation
    # mapping is introduced when concrete business providers are registered.
    return {
        "app_id": app_id,
        "stable_path": path,
        "resolved_path": path,
        "migration_mode": entry.manifest.migration_mode,
    }
