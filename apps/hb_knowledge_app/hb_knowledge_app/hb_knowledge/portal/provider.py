from __future__ import annotations

from hb_knowledge_app.hb_knowledge.portal.access import build_access_context
from hb_knowledge_app.hb_knowledge.portal.manifest import get_manifest
from hb_knowledge_app.hb_knowledge.policy import load_current_policy


class KnowledgePortalProvider:
    def manifest(self) -> dict[str, object]:
        return get_manifest()

    def access_context(self) -> dict[str, object]:
        return build_access_context(load_current_policy())

    def resolve_route(self, stable_path: str) -> str:
        if stable_path == "/hbos/knowledge" or stable_path.startswith("/hbos/knowledge?"):
            return stable_path
        raise ValueError("unregistered knowledge route")


def get_provider() -> KnowledgePortalProvider:
    return KnowledgePortalProvider()
