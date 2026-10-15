"""Server-only, transaction-bound native current reads. No endpoint or grant.

This initial loader locks full source ranges under MariaDB REPEATABLE READ.
Its coarse lock cost requires validation before production enablement.
"""
import hashlib
import re
from datetime import datetime, timezone

from hbos_portal.authorization.errors import ContractError
from .source_adapter import _SCHEMAS, build_source_snapshot


class FrappeLockedSourceLoader:
    def __init__(self, repository, *, expected_site=None, expected_database_sha256=None, enabled=False):
        self.repository = repository
        self.expected_site = expected_site
        self.expected_database_sha256 = expected_database_sha256
        self.enabled = enabled is True

    def __call__(self):
        if not self.enabled:
            raise ContractError("SOURCE_READS_DISABLED", "source")
        if (not isinstance(self.expected_site, str) or not self.expected_site.strip()
                or self.expected_site != self.expected_site.strip()
                or not isinstance(self.expected_database_sha256, str)
                or not re.fullmatch(r"[0-9a-f]{64}", self.expected_database_sha256)):
            raise ContractError("SOURCE_BINDING_REQUIRED", "source.context")
        native = self.repository.require_locked_source_context()
        if native.local.site != self.expected_site:
            raise ContractError("SOURCE_SITE_MISMATCH", "source.context")
        if native.conf.get("db_type", "mariadb") != "mariadb":
            raise ContractError("UNSUPPORTED_SOURCE_DATABASE", "source.context")
        database, isolation = native.db.sql("SELECT DATABASE(), @@tx_isolation")[0]
        if hashlib.sha256(database.encode()).hexdigest() != self.expected_database_sha256:
            raise ContractError("SOURCE_DATABASE_MISMATCH", "source.context")
        if isolation != "REPEATABLE-READ":
            # READ COMMITTED does not provide the full-range phantom protection
            # relied on by this first implementation. Never silently downgrade.
            raise ContractError("UNSUPPORTED_SOURCE_ISOLATION", "source.context")
        tables = tuple("tab" + kind for kind in _SCHEMAS)
        engines = native.db.sql(
            "SELECT table_name,engine FROM information_schema.tables WHERE table_schema=DATABASE() "
            "AND table_name IN (" + ",".join(["%s"] * len(tables)) + ")", tables)
        if dict(engines) != {table: "InnoDB" for table in tables}:
            raise ContractError("UNSUPPORTED_SOURCE_ENGINE", "source.context")
        selected = {}
        for kind, fields in _SCHEMAS.items():
            # Fixed schema/order, all rows, current locking reads (no caches or
            # pages). Full Employee range also protects absent/duplicate links.
            rows = native.db.sql("SELECT " + ",".join("`" + field + "`" for field in fields)
                                 + f" FROM `tab{kind}` ORDER BY name FOR UPDATE", as_dict=True)
            converted = []
            for row in rows:
                data = dict(row)
                if data.get("modified") is None:
                    raise ContractError("INVALID_SOURCE_MODIFIED", "source." + kind + ".modified")
                data["modified"] = str(data["modified"])
                converted.append(data)
            selected[kind] = converted
        return build_source_snapshot(site_id=native.local.site, provider_id="hbos_portal.native_locked.v1",
            captured_at=datetime.now(timezone.utc).isoformat(), rows_by_type=selected, employee_links_complete=True)
