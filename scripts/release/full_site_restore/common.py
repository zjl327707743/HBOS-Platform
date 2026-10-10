"""Fixed original target and owned proposal; no secrets or environment fallback."""
from __future__ import annotations

from pathlib import Path
import re
from types import MappingProxyType

OWNER = "hbos-owned-site-restore-20261010-a7d3"
ROOT = Path("/private/tmp") / OWNER
SITE = "frontend"
BENCH = "/home/frappe/frappe-bench"
DOCKER = "/Applications/Docker.app/Contents/Resources/bin/docker"
HOST = "hbos-restore.localhost:18092"
ORIGIN = "http://" + HOST
DATABASE_SHA256 = "98d2b2166d96e1969c24b420238b40e82a7572a59105b5e31d4f6f215b6aa4cb"
OWNER_LABEL = "hbos.restore.owner"
FRAPPE_IMAGE = "frappe/erpnext@sha256:d349cceb89693d54525ef9696c29af772c05ad4f42af723742cbee4e62420583"
DB_IMAGE = "mariadb@sha256:efb4959ef2c835cd735dbc388eb9ad6aab0c78dd64febcd51bc17481111890c4"
REDIS_IMAGE = "redis@sha256:ec5e187c913d422cdf60f4216a5fdfb95246792c6de6fe21ff5bed75cbfc8c23"
APP_NAMES = ("frappe", "erpnext", "hrms", "hb_attendance_app", "hb_inventory_app",
             "hb_lims_app", "hbos_portal", "hb_knowledge_app", "hb_twin_app")
ROLES = ("db", "redis-cache", "redis-queue", "backend", "frontend")
VOLUME_SUFFIXES = ("db-data", "redis-cache-data", "redis-queue-data", "sites", "logs",
                   "assets-data", "frappe-dist", "erpnext-dist", "hbos-lims-dist")
VOLUME_NAMES = tuple(OWNER + "-" + suffix for suffix in VOLUME_SUFFIXES)
BEFORE_SHA256 = "e225e34a6f659e638c8ee597f22342e2aa12303d9d65ead731dc64734f825748"
# Same complete backup already independently checked; the CLI cannot override pins.
BACKUP_EXPECTED = MappingProxyType({
    "database": MappingProxyType({"bytes": 2645386, "sha256": "c2f3c190095224ae075867582cedb5bd831a7fd7c9c7481d8f3df27ecccceac9"}),
    "site_config": MappingProxyType({"bytes": 1259, "sha256": "533a2b31faf6265df003d6fa2fc1bc42fa9fa70778a4fa5c5d08c8c8ec37b89a"}),
    "public_files": MappingProxyType({"bytes": 10240, "sha256": "ec494d1950ae0bfe001150421a8218b5e9a3fb99cdf2e7b34e54769db87e00ed"}),
    "private_files": MappingProxyType({"bytes": 174080, "sha256": "cc581cc045fd49b226d536816e5631a43f84b02ef3a74f0751e81c2c7675f3f5"}),
    "auth_files": MappingProxyType({"bytes": 293, "sha256": "56043bd376e2366ec8dff632feea3184f798558dac2a2772404928ab3d3aab20"}),
})


class RestoreError(ValueError):
    """Only a fixed diagnostic code may escape to public CLI output."""

    def __init__(self, code: str = "RESTORE_INVALID"):
        self.code = code if type(code) is str and re.fullmatch(r"[A-Z][A-Z0-9_]{2,80}", code) else "RESTORE_INVALID"
        super().__init__(self.code)
