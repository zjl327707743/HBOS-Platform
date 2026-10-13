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
    if config.get("name") != project:
        raise ValueError("Resolved Compose project name differs from the Preview project")

    declared = config.get("volumes") or {}
    for key in ("sites", "assets-data"):
        actual = (declared.get(key) or {}).get("name")
        expected = f"{project}_{key}"
        if actual != expected:
            raise ValueError(f"Named volume {key} must resolve to {expected}")

    services = config.get("services") or {}
    for name, service in services.items():
        volumes = service.get("volumes") or []
        if any(volume.get("target") == BAD_ASSETS for volume in volumes):
            raise ValueError(
                f"{name}: nested sites/assets mount blocks Frappe entrypoint (EBUSY)"
            )

    for name in FRAPPE_SERVICES:
        if name not in services:
            raise ValueError(f"Required Frappe Preview service is missing: {name}")
        volumes = services[name].get("volumes") or []
        matches = [v for v in volumes if v.get("target") == SITES]
        if len(matches) != 1 or matches[0].get("type") != "volume":
            raise ValueError(f"{name}: sites must be exactly one named volume")
        if matches[0].get("source") != f"{project}_sites":
            raise ValueError(f"{name}: sites volume is not Preview-namespaced")

    for name in ASSET_USERS:
        volumes = services[name].get("volumes") or []
        matches = [v for v in volumes if v.get("target") == BENCH_ASSETS]
        if len(matches) != 1 or matches[0].get("type") != "volume":
            raise ValueError(f"{name}: bench/assets must be exactly one named volume")
        if matches[0].get("source") != f"{project}_assets-data":
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
