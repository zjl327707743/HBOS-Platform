#!/usr/bin/env python3
"""Fail closed if an isolated Preview Compose stack can reuse foreign volumes.

Frappe v16's entrypoint replaces sites/assets with a symlink.  Binding a
separate volume at that nested path makes the entrypoint fail with EBUSY.
Use the already-namespaced sites and bench/assets volumes instead.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

BENCH = "/home/frappe/frappe-bench"
SITES = f"{BENCH}/sites"
BAD_ASSETS = f"{SITES}/assets"
BENCH_ASSETS = f"{BENCH}/assets"
FRAPPE_SERVICES = (
    "backend",
    "configurator",
    "create-site",
    "frontend",
    "queue-long",
    "queue-short",
    "scheduler",
    "websocket",
)
ASSET_USERS = ("backend", "frontend")


def validate_compose(config: dict[str, Any], project: str) -> None:
    """Validate resolved `docker compose -p PROJECT config --format json`."""
    if not project or project in {"default", "frappe", "hbos-m0-r3a"}:
        raise ValueError("Preview Docker project must be a distinct named project")
    if not isinstance(config, dict):
        raise ValueError("Compose config must be a mapping")
    if config.get("name") != project:
        raise ValueError("Resolved Compose project name differs from the Preview project")

    declared = config.get("volumes") or {}
    if not isinstance(declared, dict):
        raise ValueError("Compose volumes must be a mapping")
    safe_names: set[str] = set()
    for key, volume in declared.items():
        if not isinstance(key, str) or not isinstance(volume, dict):
            raise ValueError("Invalid named-volume declaration")
        expected = f"{project}_{key}"
        if volume.get("name") != expected:
            raise ValueError(f"Named volume {key} must resolve to {expected}")
        if volume.get("external"):
            raise ValueError(f"{key}: external volume reuse is forbidden in Preview")
        # A local driver can conceal a host data bind behind a safe-looking name.
        if volume.get("driver_opts") or volume.get("driver") not in (None, "local"):
            raise ValueError(f"{key}: non-default volume storage needs separate review")
        safe_names.add(expected)
    for key in ("sites", "assets-data"):
        if key not in declared:
            raise ValueError(f"Required named volume is missing: {key}")

    services = config.get("services") or {}
    if not isinstance(services, dict):
        raise ValueError("Compose services must be a mapping")
    for name, service in services.items():
        if not isinstance(service, dict):
            raise ValueError(f"{name}: service must be a mapping")
        volumes = service.get("volumes") or []
        if not isinstance(volumes, list) or any(not isinstance(v, dict) for v in volumes):
            raise ValueError(f"{name}: expected resolved mount objects")
        if any(volume.get("target") == BAD_ASSETS for volume in volumes):
            raise ValueError(
                f"{name}: nested sites/assets mount blocks Frappe entrypoint (EBUSY)"
            )
        for volume in volumes:
            if volume.get("type") != "volume":
                continue  # Source/font binds remain allowed; critical data targets are checked below.
            source = volume.get("source")
            if not isinstance(source, str) or not source:
                raise ValueError(f"{name}: anonymous volumes are forbidden in Preview")
            if source in declared:
                resolved_name = declared[source].get("name")
            else:
                resolved_name = source
            if resolved_name not in safe_names:
                raise ValueError(f"{name}: volume is not Preview-namespaced")

    # MariaDB data cannot be replaced with a host bind or another logical volume.
    if "db" in services:
        mounts = services["db"].get("volumes") or []
        data_mounts = [v for v in mounts if v.get("target") == "/var/lib/mysql"]
        if (len(data_mounts) != 1 or data_mounts[0].get("type") != "volume"
                or data_mounts[0].get("source") not in {"db-data", f"{project}_db-data"}
                or "db-data" not in declared):
            raise ValueError("db: MariaDB data must use the dedicated db-data named volume")

    for name in FRAPPE_SERVICES:
        if name not in services:
            raise ValueError(f"Required Frappe Preview service is missing: {name}")
        volumes = services[name].get("volumes") or []
        matches = [v for v in volumes if v.get("target") == SITES]
        if len(matches) != 1 or matches[0].get("type") != "volume":
            raise ValueError(f"{name}: sites must be exactly one named volume")
        # Docker Compose config may retain the logical source key "sites"
        # even though the top-level volume's resolved name is project_sites.
        # The declaration above has already proved that exact mapping.
        if matches[0].get("source") not in {"sites", f"{project}_sites"}:
            raise ValueError(f"{name}: sites volume is not Preview-namespaced")

    for name in ASSET_USERS:
        volumes = services[name].get("volumes") or []
        matches = [v for v in volumes if v.get("target") == BENCH_ASSETS]
        if len(matches) != 1 or matches[0].get("type") != "volume":
            raise ValueError(f"{name}: bench/assets must be exactly one named volume")
        if matches[0].get("source") not in {"assets-data", f"{project}_assets-data"}:
            raise ValueError(f"{name}: bench/assets volume is not Preview-namespaced")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    args = parser.parse_args()
    try:
        config = json.load(sys.stdin)
        validate_compose(config, args.project)
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        print(f"HBOS Preview Compose guard failed: {exc}", file=sys.stderr)
        return 1
    print("HBOS Preview Compose: named site/assets volumes isolated; no EBUSY mount")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
