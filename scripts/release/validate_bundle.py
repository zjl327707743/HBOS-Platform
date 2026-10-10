"""Check the deployable archive and every versioned payload checksum."""
from __future__ import annotations

import argparse
import hashlib
import json
import tarfile
from pathlib import PurePosixPath

parser = argparse.ArgumentParser()
parser.add_argument("archive")
parser.add_argument("--source-commit", required=True)
args = parser.parse_args()
with tarfile.open(args.archive) as archive:
    files = {}
    for entry in archive.getmembers():
        path = PurePosixPath(entry.name)
        if path.is_absolute() or ".." in path.parts or entry.issym() or entry.islnk() or not (entry.isfile() or entry.isdir()):
            raise SystemExit("发布包包含不安全路径或文件类型")
        if any(part.startswith("._") or part in {"__pycache__", "node_modules", "runtime", "backups", ".DS_Store"} for part in path.parts):
            raise SystemExit("发布包包含运行数据、缓存或本机元数据")
        if entry.isfile():
            if entry.name in files:
                raise SystemExit("发布包包含重复文件")
            if path.suffix in {".sql", ".glb", ".pdf", ".xlsx", ".xls", ".pyc"} or path.name == ".env":
                raise SystemExit("发布包包含禁止交付的数据文件")
            files[entry.name] = archive.extractfile(entry).read()
    info = json.loads(files["release.json"])
    if info["source_commit"] != args.source_commit or info["source_dirty"] or info["portal_data_mode"] != "frappe":
        raise SystemExit("制品来源或数据模式未通过正式发布门禁")
    for path, digest in info["files"].items():
        if hashlib.sha256(files[path]).hexdigest() != digest:
            raise SystemExit("发布文件校验失败")
    build_info = "apps/hbos_portal/hbos_portal/public/portal/build-info.json"
    if set(files) != set(info["files"]) | {"release.json", build_info}:
        raise SystemExit("发布包存在未登记文件")
    actual = json.loads(files[build_info])
    if any(actual[key] != info[key] for key in actual):
        raise SystemExit("Portal 编译版本与部署清单不一致")
    for required in ["apps/hbos_portal/hbos_portal/public/portal/index.html", "apps/hb_lims_app/hb_lims_app/public/hbos-lims/index.html", "services/hbos_gateway/requirements.txt"]:
        if required not in files:
            raise SystemExit("发布包缺少必要编译制品或依赖")
print(json.dumps({"status": "PASS", "source_commit": info["source_commit"], "build_id": info["build_id"], "verified_files": len(info["files"])}, ensure_ascii=False))
