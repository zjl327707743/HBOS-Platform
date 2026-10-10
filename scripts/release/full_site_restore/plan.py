"""Fixed, non-executable proposal. No Docker, sockets, Frappe or file writes.

Service commands are review templates, not admitted ResourceRecord specs. Binary
paths, source snapshots and numeric service UID/GID must be verified before an
execution tool can be implemented. The ownership guard currently admits only
the constrained namespace-precheck/volume-initialize sleep command, never these
service commands. The two batches require removal and new container identities;
this proposal cannot switch immutable create settings or run either batch.
"""
from __future__ import annotations

from .common import (
    APP_NAMES, BENCH, DB_IMAGE, DOCKER, FRAPPE_IMAGE, HOST, ORIGIN, OWNER,
    OWNER_LABEL, REDIS_IMAGE, ROOT, ROLES, VOLUME_NAMES,
)

PENDING_GATES = (
    "SOURCE_SNAPSHOT_CAPTURE_AND_HASH_NOT_RUN",
    "SOURCE_LINK_AND_RUNTIME_DEPENDENCY_CLOSURE_NOT_VERIFIED",
    "SERVICE_UID_GID_BINARY_AND_ENTRYPOINT_COMPATIBILITY_NOT_VERIFIED",
    "EXPLICIT_IMAGE_VOLUME_COVERAGE_NOT_VERIFIED",
    "PRIVATE_HOST_LANDING_OFFLINE_VALIDATED_CONTAINER_BIND_ADMISSION_NOT_IMPLEMENTED",
    "REGISTRY_AND_JOURNAL_OFFLINE_VALIDATED_TRUSTED_CAPTURE_NOT_IMPLEMENTED",
    "VOLUME_INITIALIZATION_OFFLINE_VALIDATED_DAEMON_UID_MODE_AND_NO_COPY_NOT_RUN",
    "NESTED_MOUNT_EMPTY_VOLUME_CAPTURE_NOT_VERIFIED",
    "TWO_BATCH_REPLACEMENT_FRESH_ABSENCE_RECEIPTS_AND_GENERATIONS_NOT_IMPLEMENTED",
    "CONTAINER_VOLUME_LANDING_SQL_IMPORT_AND_FINGERPRINT_NOT_IMPLEMENTED",
    "ACTUAL_ENCRYPTED_AUTH_APPLICABILITY_AND_DECRYPT_NOT_RUN",
    "CLONE_SESSION_INVALIDATION_AND_OLD_SID_REJECTION_NOT_RUN",
    "NATIVE_PASSWORD_LOGIN_FINITE_WRITE_SET_NOT_VERIFIED",
    "COMPLETE_PAGE_AND_BUSINESS_REQUEST_ALLOWLIST_NOT_VERIFIED",
    "NETWORK_NAMESPACE_ROUTES_AND_EGRESS_REJECTION_NOT_RUN",
    "STDIO_COMPONENTS_OFFLINE_VALIDATED_LISTENER_AND_EXEC_EXIT_CAPTURE_NOT_IMPLEMENTED",
    "DEADLINE_AND_OWNED_CLEANUP_OFFLINE_VALIDATED_COMPLETE_RUNTIME_ABSENCE_NOT_IMPLEMENTED",
    "OWNER_EXACT_RESOURCE_AND_CLONE_WRITE_AUTHORIZATION_PENDING",
    "OWNER_ORIGINAL_ACCOUNT_LOGIN_AND_BUSINESS_ACCEPTANCE_NOT_RUN",
)

FORWARD_PACKAGE_FILES = ("__init__.py", "common.py", "relay.py", "wire.py", "forward.py")
SOURCE_PID1_UID_GID = {"db": "999:999", "redis-cache": "999:1000", "redis-queue": "999:1000",
                      "backend": "1000:1000", "frontend": "1000:1000"}


def forward_entrypoint_template() -> str:
    """Fixed unmaterialized wrapper; the package must be mounted alongside it."""
    return ('from full_site_restore.forward import main\n'
            'if __name__ == "__main__":\n'
            '    raise SystemExit(main())\n')


def _volume(suffix: str, destination: str, read_only: bool) -> dict:
    return {"kind": "volume", "source": OWNER + "-" + suffix,
            "destination": destination, "read_only": read_only, "no_copy": True}


def _bind(relative: str, destination: str) -> dict:
    return {"kind": "bind", "source": str(ROOT / relative),
            "destination": destination, "read_only": True}


def _mounts(role: str) -> list[dict]:
    if role == "db":
        return [_volume("db-data", "/var/lib/mysql", False),
                _bind("runtime/db.cnf", "/run/hbos-restore/db.cnf")]
    if role.startswith("redis-"):
        return [_volume(role + "-data", "/data", False)]
    mounts = [
        _volume("sites", BENCH + "/sites", role == "frontend"),
        _volume("logs", BENCH + "/logs", False),
        _volume("assets-data", BENCH + "/sites/assets", True),
        _volume("assets-data", BENCH + "/assets", True),
        _bind("snapshot/env", BENCH + "/env"),
        _bind("snapshot/fonts", BENCH + "/fonts"),
    ]
    mounts.extend(_bind("snapshot/apps/" + app, BENCH + "/apps/" + app)
                  for app in APP_NAMES)
    mounts.extend([
        _volume("frappe-dist", BENCH + "/apps/frappe/frappe/public/dist", True),
        _volume("erpnext-dist", BENCH + "/apps/erpnext/erpnext/public/dist", True),
        _volume("hbos-lims-dist", BENCH + "/apps/hb_lims_app/hb_lims_app/public/hbos-lims", True),
    ])
    if role == "frontend":
        mounts.append(_bind("runtime/nginx.conf", "/run/hbos-restore/nginx.conf"))
    else:
        mounts.append(_bind("runtime/forward.py", "/run/hbos-restore/forward.py"))
        mounts.append(_bind("runtime/full_site_restore", "/run/hbos-restore/full_site_restore"))
    return mounts


def _service_command(role: str) -> list[str]:
    if role == "db":
        return ["/usr/sbin/mariadbd", "--defaults-file=/run/hbos-restore/db.cnf"]
    if role.startswith("redis-"):
        port = "6379" if role == "redis-cache" else "6380"
        return ["/usr/local/bin/redis-server", "--bind", "127.0.0.1", "--port", port,
                "--protected-mode", "yes", "--save", "", "--appendonly", "no"]
    if role == "frontend":
        return ["/usr/sbin/nginx", "-c", "/run/hbos-restore/nginx.conf", "-g", "daemon off;"]
    return [BENCH + "/env/bin/gunicorn", "--bind", "127.0.0.1:8000", "--workers", "2",
            "--threads", "4", "--timeout", "60", "frappe.app:application"]


def _initialization_mounts(role: str) -> list[dict]:
    """Owned volumes only; source/private/runtime binds are not initial inputs."""
    if role == "db":
        return [_volume("db-data", "/var/lib/mysql", False)]
    if role.startswith("redis-"):
        return [_volume(role + "-data", "/data", False)]
    mounts = [_volume("sites", BENCH + "/sites", role == "frontend"),
              _volume("logs", BENCH + "/logs", False),
              _volume("assets-data", BENCH + "/sites/assets", role == "frontend")]
    if role == "frontend":
        mounts.append(_volume("assets-data", BENCH + "/assets", True))
    mounts.extend([
        _volume("frappe-dist", BENCH + "/apps/frappe/frappe/public/dist", role == "frontend"),
        _volume("erpnext-dist", BENCH + "/apps/erpnext/erpnext/public/dist", role == "frontend"),
        _volume("hbos-lims-dist", BENCH + "/apps/hb_lims_app/hb_lims_app/public/hbos-lims", role == "frontend"),
    ])
    return mounts


def _append_mount_arguments(argv: list[str], mounts: list[dict]) -> None:
    for mount in mounts:
        value = ("type=" + mount["kind"] + ",source=" + mount["source"]
                 + ",destination=" + mount["destination"])
        if mount["read_only"]:
            value += ",readonly"
        if mount["kind"] == "volume":
            value += ",volume-nocopy"
        argv.extend(["--mount", value])


def _initialization_containers() -> list[dict]:
    containers = []
    for role in ROLES:
        image = DB_IMAGE if role == "db" else REDIS_IMAGE if role.startswith("redis-") else FRAPPE_IMAGE
        network = "none" if role == "db" else "container:<VERIFIED_NEW_INITIALIZATION_DB_ID>"
        phase = "namespace-precheck" if role == "frontend" else "volume-initialize"
        mounts = _initialization_mounts(role)
        argv = [DOCKER, "create", "--name", OWNER + "-" + role,
                "--label", OWNER_LABEL + "=" + OWNER, "--label", "hbos.restore.phase=" + phase,
                "--network", network, "--user", "1000:1000", "--read-only",
                "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                "--no-healthcheck", "--log-driver", "none", "--restart", "no", "--entrypoint", ""]
        if role in ("backend", "frontend"):
            argv.extend(["--workdir", BENCH, "--env", "PYTHONDONTWRITEBYTECODE=1"])
        _append_mount_arguments(argv, mounts)
        argv.extend([image, "/bin/sleep", "2700"])
        containers.append({"role": role, "name": OWNER + "-" + role, "image": image,
            "network": network, "published_ports": [], "phase": phase, "uid_gid": "1000:1000",
            "read_only_rootfs": True, "cap_drop": ["ALL"], "security_opt": ["no-new-privileges"],
            "healthcheck": "DISABLED", "log_driver": "none", "restart_policy": "no",
            "mounts": mounts, "command": ["/bin/sleep", "2700"], "entrypoint": [],
            "argv_template": argv, "executable": False,
            "ownership_admission": "OFFLINE_METADATA_ONLY_RUNTIME_NOT_RUN",
            "new_volume_initialization": "OFFLINE_COMPONENTS_ONLY_DAEMON_NOT_RUN"})
    return containers


def build_proposal() -> dict:
    """Return a fresh sanitized review document, with unresolved argv placeholders."""
    containers = []
    for role in ROLES:
        image = DB_IMAGE if role == "db" else REDIS_IMAGE if role.startswith("redis-") else FRAPPE_IMAGE
        network = "none" if role == "db" else "container:<VERIFIED_NEW_SERVICE_DB_ID>"
        mounts = _mounts(role)
        argv = [DOCKER, "create", "--name", OWNER + "-" + role,
                "--label", OWNER_LABEL + "=" + OWNER, "--network", network,
                "--user", "<VERIFIED_SERVICE_UID_GID>", "--read-only",
                "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                "--no-healthcheck", "--log-driver", "none", "--restart", "no",
                "--entrypoint", _service_command(role)[0]]
        if role in ("backend", "frontend"):
            argv.extend(["--workdir", BENCH, "--env", "PYTHONDONTWRITEBYTECODE=1"])
        _append_mount_arguments(argv, mounts)
        argv.extend([image, *_service_command(role)[1:]])
        containers.append({"role": role, "name": OWNER + "-" + role,
                           "image": image, "network": network, "published_ports": [],
                           "uid_gid": "NOT_VERIFIED", "source_pid1_uid_gid_observed": SOURCE_PID1_UID_GID[role],
                           "new_volume_initialization": "OFFLINE_COMPONENTS_ONLY_DAEMON_NOT_RUN", "read_only_rootfs": True,
                           "phase": "service",
                           "cap_drop": ["ALL"], "security_opt": ["no-new-privileges"],
                           "healthcheck": "DISABLED", "log_driver": "none", "restart_policy": "no",
                           "mounts": mounts, "service_command_template": _service_command(role),
                           "argv_template": argv, "executable": False,
                           "ownership_admission": "SERVICE_COMMAND_NOT_ADMITTED"})
    return {
        "schema_version": 1, "status": "OFFLINE_PROPOSAL_ONLY",
        "execution": "NOT_IMPLEMENTED", "runtime_ready": False,
        "owner": OWNER, "private_root": str(ROOT), "custom_networks": [],
        "containers": containers,
        "initialization_containers": _initialization_containers(),
        "phases": ["namespace-volume-initialize", "service"],
        "resource_limits": {"container_incarnations": 10, "max_simultaneous_containers": 5,
                            "named_volumes": 9, "custom_networks": 0, "host_relays": 1},
        "replacement": {"execution": "HARD_BLOCKED", "in_place_command_or_mount_switch": False,
                        "same_names_new_container_ids": True, "reuse_previous_container_ids": False,
                        "remove_initialization_db_last": True, "create_service_db_first": True,
                        "requires_fresh_all_initialization_absent_receipts": True,
                        "requires_registered_new_generation_receipts": True,
                        "generation_registration": "NOT_IMPLEMENTED"},
        "volumes": [{"name": name, "labels": {OWNER_LABEL: OWNER}} for name in VOLUME_NAMES],
        "host_relay": {"name": OWNER + "-http-relay", "listen": "127.0.0.1:18092",
                       "host": HOST, "origin": ORIGIN, "implementation": "COMPONENTS_ONLY_LISTENER_NOT_IMPLEMENTED",
                       "stdio": "OFFLINE_COMPONENTS_IMPLEMENTED", "production_admission": "HARD_BLOCKED"},
        "forward_deployment": {"wrapper": "runtime/forward.py", "package": "runtime/full_site_restore",
                               "package_files": list(FORWARD_PACKAGE_FILES),
                               "fixed_exec_switch": "--owned-runtime-enabled", "materialized": False},
        "internal_loopback": {"db": 3306, "redis_cache": 6379, "redis_queue": 6380,
                              "backend": 8000, "frontend": 8080},
        "guard_scope": "OFFLINE_COMPONENTS_AND_NAMESPACE_VOLUME_INITIALIZATION_METADATA_ONLY",
        "pending_gates": list(PENDING_GATES),
        "budget_proposal_seconds": {"restore": 1800, "owner_acceptance": 900, "cleanup": 600},
    }


def frontend_config_template() -> str:
    """Unexecuted nginx configuration; compatibility is still a runtime gate."""
    return f"""worker_processes 1;
pid {BENCH}/logs/restore-nginx.pid;
error_log {BENCH}/logs/restore-nginx-error.log warn;
events {{ worker_connections 32; }}
http {{
    gzip off;
    access_log off;
    client_body_temp_path {BENCH}/logs/restore-body;
    proxy_temp_path {BENCH}/logs/restore-proxy;
    client_max_body_size 64k;
    server {{ listen 127.0.0.1:8080 default_server; server_name _; return 444; }}
    server {{
        listen 127.0.0.1:8080;
        server_name hbos-restore.localhost;
        location /socket.io {{ return 403; }}
        location /private {{ return 403; }}
        location /assets/ {{ alias {BENCH}/sites/assets/; }}
        location /files/ {{ alias {BENCH}/sites/frontend/public/files/; }}
        location / {{
            proxy_pass http://127.0.0.1:8000;
            proxy_set_header Host {HOST};
            proxy_set_header X-Frappe-Site-Name frontend;
            proxy_set_header X-Forwarded-For "";
            proxy_set_header X-Forwarded-Host "";
            proxy_set_header X-Forwarded-Proto "";
            proxy_connect_timeout 2s;
            proxy_read_timeout 10s;
            proxy_http_version 1.1;
            proxy_set_header Connection close;
            proxy_set_header Accept-Encoding identity;
        }}
    }}
}}
"""
