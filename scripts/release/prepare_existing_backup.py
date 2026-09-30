from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import stat
import tarfile
from pathlib import Path

import frappe

parser = argparse.ArgumentParser()
parser.add_argument("--site", required=True)
parser.add_argument("--bench", required=True)
parser.add_argument("--expected-database", required=True)
parser.add_argument("--audit-dir", required=True)
args = parser.parse_args()
bench = Path(args.bench).resolve()
audit = Path(args.audit_dir).resolve()
if not (bench / "sites" / args.site / "site_config.json").is_file():
    raise SystemExit("Existing Site was not found; no new Site created")
audit.mkdir(mode=0o700, parents=True, exist_ok=True); audit.chmod(0o700)
os.umask(0o077)
os.chdir(bench / "sites"); frappe.init(site=args.site); frappe.connect()
try:
    from hbos_portal.auth.site_inventory import inspect
    before = inspect()
    if before["database_fingerprint"] != args.expected_database:
        raise SystemExit("Confirmed target database does not match")
    if not before["csrf_enabled"] or before["legacy_feishu_social_keys"]:
        raise SystemExit("Authentication bypass gate failed; correct the actual configuration first")
    (audit / "before.json").write_text(json.dumps(before))
    from hbos_portal.auth.feishu import SECRET_FILENAME, TENANT_FILENAME
    # These protected integration files are outside native private/files.
    with tarfile.open(audit / "auth-private.tar.gz", "w:gz") as archive:
        for filename in (SECRET_FILENAME, TENANT_FILENAME, "hbos_knowledge_gateway_token"):
            source = Path(frappe.get_site_path("private", filename))
            if source.exists():
                metadata = source.lstat()
                if not stat.S_ISREG(metadata.st_mode) or metadata.st_mode & 0o077 or metadata.st_uid != os.geteuid():
                    raise RuntimeError("Protected authentication file permissions invalid")
                archive.add(source, arcname=filename)
finally:
    frappe.destroy()
with (audit / "backup.log").open("w") as log:
    subprocess.run(["bench", "--site", args.site, "backup", "--with-files"], cwd=bench, stdout=log, stderr=log, check=True)
backups = bench / "sites" / args.site / "private" / "backups"
database = max(backups.glob("*-database.sql.gz"), key=lambda path: path.stat().st_mtime)
prefix = database.name.removesuffix("-database.sql.gz")
types = {"database": "-database.sql.gz", "site_config": "-site_config_backup.json", "public_files": "-files.tar", "private_files": "-private-files.tar"}
prepared = {"auth_files": str(audit / "auth-private.tar.gz")}
for key, suffix in types.items():
    source = backups / (prefix + suffix)
    if not source.is_file():
        raise SystemExit("Backup component missing: " + key)
    target = audit / source.name
    shutil.copy2(source, target); target.chmod(0o600)
    prepared[key] = str(target)
(audit / "backup-prepared.json").write_text(json.dumps(prepared, indent=2))
print("Protected backup ready; verify an isolated restore before applying the release.")
