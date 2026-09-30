"""Restore a backup into an owned, network-isolated throwaway MariaDB.

The source database is never a restore destination. Credentials are mounted
0600 files, and dumps/results remain outside Git. Files archives are verified
separately; this checks a complete SQL import and mandatory account tables.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import secrets
import subprocess
import tarfile
import tempfile
import time
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--database", required=True)
parser.add_argument("--site-config", required=True)
parser.add_argument("--public-files", required=True)
parser.add_argument("--private-files", required=True)
parser.add_argument("--before", required=True, help="准备备份时的受保护 before.json")
parser.add_argument("--auth-files", required=True, help="原生文件备份之外的集成凭据归档")
parser.add_argument("--image", default="mariadb:11.8")
args = parser.parse_args()
config = json.loads(Path(args.site_config).read_text())
if not config.get("encryption_key"):
    raise SystemExit("Encryption recovery key is missing; do not proceed")
for value in [args.public_files, args.private_files, args.auth_files]:
    with tarfile.open(value) as archive:
        for entry in archive.getmembers():
            if entry.name.startswith("/") or ".." in Path(entry.name).parts or entry.issym() or entry.islnk() or not (entry.isfile() or entry.isdir()):
                raise SystemExit("Files backup has unsafe archive paths")
            if entry.isfile():
                with archive.extractfile(entry) as source:
                    while source.read(1024 * 1024):
                        pass
name = "hbos-owned-restore-check-" + secrets.token_hex(6)
with tempfile.TemporaryDirectory(prefix="hbos-restore-check-") as temporary:
    directory = Path(temporary)
    password = secrets.token_urlsafe(40)
    (directory / "root-password").write_text(password)
    (directory / "client.cnf").write_text("[client]\nuser=root\npassword=" + password + "\n")
    for path in directory.iterdir():
        path.chmod(0o600)
    started = False
    try:
        subprocess.run(["docker", "run", "-d", "--rm", "--name", name, "--network", "none", "--mount", f"type=bind,src={directory},dst=/run/hbos-check,readonly", "-e", "MARIADB_ROOT_PASSWORD_FILE=/run/hbos-check/root-password", args.image], check=True, stdout=subprocess.DEVNULL)
        started = True
        for attempt in range(60):
            ready = subprocess.run(["docker", "exec", name, "mariadb-admin", "--defaults-extra-file=/run/hbos-check/client.cnf", "ping", "--silent"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if ready.returncode == 0:
                break
            time.sleep(1)
        else:
            raise RuntimeError("Isolated restore database did not become ready")
        subprocess.run(["docker", "exec", name, "mariadb", "--defaults-extra-file=/run/hbos-check/client.cnf", "-e", "CREATE DATABASE hbos_restore_check CHARACTER SET utf8mb4"], check=True)
        process = subprocess.Popen(["docker", "exec", "-i", name, "mariadb", "--defaults-extra-file=/run/hbos-check/client.cnf", "hbos_restore_check"], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        with gzip.open(args.database, "rb") as source:
            while chunk := source.read(1024 * 1024):
                process.stdin.write(chunk)
        process.stdin.close()
        error = process.stderr.read()
        if process.wait() != 0:
            raise RuntimeError("Full backup import failed; dump details intentionally omitted")
        query = "SELECT COUNT(*) FROM `tabUser`; SELECT COUNT(*) FROM `__Auth` WHERE doctype='User'; SELECT COUNT(*) FROM `tabHas Role` WHERE parenttype='User';"
        output = subprocess.check_output(["docker", "exec", name, "mariadb", "--defaults-extra-file=/run/hbos-check/client.cnf", "--batch", "--skip-column-names", "hbos_restore_check", "-e", query], text=True)
        counts = [int(row) for row in output.splitlines()]
        if counts[0] < 2 or counts[1] < 1:
            raise RuntimeError("Restored backup has no standard account/password records")
        before = json.loads(Path(args.before).read_text())
        queries = {
            "user_fingerprint": "SELECT JSON_ARRAY(name,enabled,user_type,username) FROM `tabUser`",
            "credential_fingerprint": "SELECT JSON_ARRAY(name,fieldname,password,encrypted) FROM `__Auth` WHERE doctype='User'",
            "role_fingerprint": "SELECT JSON_ARRAY(parent,role) FROM `tabHas Role` WHERE parenttype='User'",
            "permission_fingerprint": "SELECT JSON_ARRAY(user,allow,for_value,apply_to_all_doctypes,applicable_for) FROM `tabUser Permission`",
        }
        if before.get("identity_table_present"):
            queries["identity_fingerprint"] = "SELECT JSON_ARRAY(provider,tenant_key,app_id,id_type,external_id,user,enabled) FROM `tabHBOS External Identity`"
        for key, sql in queries.items():
            raw = subprocess.check_output(["docker", "exec", name, "mariadb", "--defaults-extra-file=/run/hbos-check/client.cnf", "--raw", "--batch", "--skip-column-names", "hbos_restore_check", "-e", sql], text=True)
            rows = [json.loads(row) for row in raw.splitlines()]
            canonical = json.dumps(sorted(rows, key=lambda row: str(row)), default=str, sort_keys=True, ensure_ascii=False)
            if hashlib.sha256(canonical.encode()).hexdigest() != before[key]:
                raise RuntimeError("Restored account preservation failed: " + key)
        associations = []
        for table, field in [("Employee", "user_id"), ("Employee Checkin", "employee"), ("Attendance", "employee")]:
            if table in before["business_counts"]:
                sql = f"SELECT JSON_ARRAY('{table}',name,`{field}`) FROM `tab{table}`"
                raw = subprocess.check_output(["docker", "exec", name, "mariadb", "--defaults-extra-file=/run/hbos-check/client.cnf", "--raw", "--batch", "--skip-column-names", "hbos_restore_check", "-e", sql], text=True)
                associations.extend(json.loads(row) for row in raw.splitlines())
        canonical = json.dumps(sorted(associations, key=lambda row: str(row)), default=str, sort_keys=True, ensure_ascii=False)
        if hashlib.sha256(canonical.encode()).hexdigest() != before["business_association_fingerprint"]:
            raise RuntimeError("Restored business association preservation failed")
        print(json.dumps({"database_restore": "PASS", "account_fingerprints_match": "PASS", "database_backup_sha256": hashlib.sha256(Path(args.database).read_bytes()).hexdigest(), "database_fingerprint": hashlib.sha256(str(config["db_name"]).encode()).hexdigest(), "restored_user_count": counts[0], "restored_credential_count": counts[1], "restored_user_role_count": counts[2], "files_archive_read": "PASS", "encryption_key_present": True, "source_database_modified": False}))
    finally:
        if started:
            subprocess.run(["docker", "stop", "--time", "5", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
