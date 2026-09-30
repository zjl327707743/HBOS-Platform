"""Allowlist package: source and production assets, never runtime or data."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
stage = Path(sys.argv[1]).resolve()
sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True).strip())
import os
if dirty and os.environ.get("HBOS_ALLOW_DIRTY_TEST_BUNDLE") != "1":
    raise SystemExit("正式制品必须从已审查提交的 clean 工作树构建；受控测试须显式标记")
allowed = ["apps/hb_attendance_app", "apps/hb_inventory_app", "apps/hb_lims_app", "apps/hbos_portal", "apps/hb_knowledge_app", "apps/hb_twin_app", "services/hbos_gateway", "scripts/release"]
for directory in allowed:
    shutil.copytree(root / directory, stage / directory, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".env", "*.local", "node_modules", "dist", "runtime", ".pytest_cache"))
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
