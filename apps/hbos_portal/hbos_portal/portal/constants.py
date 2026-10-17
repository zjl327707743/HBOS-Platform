CONTRACT_VERSION = 1
PROVIDER_HOOK = "hbos_portal_provider"

CAPABILITY_SUMMARY = "summary"
CAPABILITY_TASKS = "tasks"
CAPABILITY_SEARCH = "search"

SUPPORTED_PROVIDER_CAPABILITIES = frozenset(
    {
        CAPABILITY_SUMMARY,
        CAPABILITY_TASKS,
        CAPABILITY_SEARCH,
    }
)

CAPABILITY_METHODS = {
    CAPABILITY_SUMMARY: "summary",
    CAPABILITY_TASKS: "my_tasks",
    CAPABILITY_SEARCH: "search",
}

SUPPORTED_MIGRATION_MODES = frozenset({"legacy", "hybrid", "native"})
