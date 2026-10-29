from __future__ import annotations

from hb_twin_app.hb_twin.portal.access import build_access_context
from hb_twin_app.hb_twin.portal.manifest import get_manifest
from hb_twin_app.hb_twin.policy import load_current_policy


class TwinPortalProvider:
    def manifest(self) -> dict[str, object]:
        return get_manifest()

    def access_context(self) -> dict[str, object]:
        return build_access_context(load_current_policy())

    def resolve_route(self, stable_path: str) -> str:
        if stable_path == "/hbos/twin" or stable_path.startswith("/hbos/twin?"):
            return stable_path
        raise ValueError("unregistered twin route")


def get_provider() -> TwinPortalProvider:
    return TwinPortalProvider()
