"""Allowlist package: source and production assets, never runtime or data."""
from __future__ import annotations

import hashlib
import gzip
import json
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(sys.argv[1]).resolve()
sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True).strip())
import os
if dirty and os.environ.get("HBOS_ALLOW_DIRTY_TEST_BUNDLE") != "1":
    raise SystemExit("正式制品必须从已审查提交的 clean 工作树构建；受控测试须显式标记")
allowed = ["apps/hb_attendance_app", "apps/hb_inventory_app", "apps/hb_lims_app", "apps/hbos_portal", "apps/hb_knowledge_app", "apps/hb_twin_app", "services/hbos_gateway", "scripts/release", "scripts/local"]
for directory in allowed:
    shutil.copytree(root / directory, stage / directory, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".env", "*.local", "node_modules", "dist", "runtime", ".pytest_cache", "._*", ".DS_Store"))
target = stage / "apps/hbos_portal/hbos_portal/public/portal"
if target.exists():
    shutil.rmtree(target)
shutil.copytree(root / "frontend/hbos-portal-web/dist", target)
lims_target = stage / "apps/hb_lims_app/hb_lims_app/public/hbos-lims"
if lims_target.exists():
    shutil.rmtree(lims_target)
shutil.copytree(root / "frontend/hbos-lims-web/dist", lims_target)
files = {str(path.relative_to(stage)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(stage.rglob("*")) if path.is_file()}
build_id = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()[:20]
info = {"schema": 1, "source_commit": sha, "source_dirty": dirty, "build_id": build_id, "portal_data_mode": "frappe", "gateway_version": "1.2.0", "requires": {"frappe_major": 16, "node_major": 22}, "files": files}
(stage / "release.json").write_text(json.dumps(info, indent=2) + "\n")
(target / "build-info.json").write_text(json.dumps({k: info[k] for k in ["source_commit", "source_dirty", "build_id", "portal_data_mode", "gateway_version"]}, indent=2) + "\n")
print(json.dumps({k: info[k] for k in ["source_commit", "source_dirty", "build_id"]}))

# Python tarfile avoids macOS resource-fork/AppleDouble records. Normalize
# ownership and time so the same reviewed source/assets produce the same bytes.
if len(sys.argv) > 2:
    with Path(sys.argv[2]).open("wb") as output:
        with gzip.GzipFile(filename="", mode="wb", fileobj=output, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
                for path in sorted(stage.rglob("*")):
                    if path.is_symlink():
                        raise SystemExit("发布包不允许软链")
                    entry = archive.gettarinfo(str(path), arcname=str(path.relative_to(stage)))
                    entry.uid = entry.gid = entry.mtime = 0
                    entry.uname = entry.gname = ""
                    entry.mode = 0o755 if path.is_dir() or path.stat().st_mode & 0o111 else 0o644
                    entry.pax_headers = {}
                    if entry.isfile():
                        with path.open("rb") as source:
                            archive.addfile(entry, source)
                    else:
                        archive.addfile(entry)
