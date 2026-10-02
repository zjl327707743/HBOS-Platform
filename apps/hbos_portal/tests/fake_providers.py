def manifest_for(
    app_id: str,
    *,
    contract_version: int = 1,
    capabilities: list[str] | None = None,
) -> dict[str, object]:
    return {
        "contract_version": contract_version,
        "id": app_id,
        "title": app_id.title(),
        "short_title": app_id.upper(),
        "description": f"{app_id} test provider",
        "icon": "test",
        "accent": "test",
        "order": 10,
        "migration_mode": "native",
        "route": f"/hbos/{app_id}",
        "capabilities": capabilities or [],
    }


class VisibleProvider:
    def manifest(self):
        return manifest_for("visible", capabilities=["summary", "tasks", "search"])

    def access_context(self):
        return {
            "app_id": "visible",
            "can_enter": True,
            "capabilities": ["read"],
            "scopes": {},
        }

    def summary(self):
        return {"metrics": []}

    def my_tasks(self, *, limit=20, cursor=None):
        return {"tasks": [], "next_cursor": None}

    def search(self, *, query, limit=20):
        return {"results": []}


class DuplicateProvider(VisibleProvider):
    pass


class UnsupportedProvider(VisibleProvider):
    def manifest(self):
        return manifest_for("unsupported", contract_version=99)


class BrokenCapabilityProvider(VisibleProvider):
    def manifest(self):
        return manifest_for("broken", capabilities=["summary"])

    summary = None
