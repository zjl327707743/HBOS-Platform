#!/usr/bin/env python3
"""IAM-0 bounded, read-only Python source inventory; NOT an authorization audit.

Never imports application code, connects to a Site, follows symlinks, or writes
files. JSON goes to stdout. No source lines, SQL text, defaults or literals are
included. Run only against the six application source roots declared below.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

APPS = ("hbos_portal", "hb_attendance_app", "hb_inventory_app", "hb_lims_app",
        "hb_knowledge_app", "hb_twin_app")
SKIP_DIRS = {"tests", "test", "fixtures", "node_modules", "__pycache__", ".git"}
MAX_FILES = 5000
MAX_BYTES = 2 * 1024 * 1024
GUARD_NAMES = {"only_for", "has_permission", "check_permission", "action_allowed",
               "require_app_access", "require_authenticated_user", "require_search",
               "_check_action", "_require_hr_write"}


def dotted(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        left = dotted(node.value)
        return left + "." + node.attr if left else node.attr
    return ""


def own_nodes(function: ast.AST):
    """Exclude nested function/class bodies; their checks do not guard the caller."""
    stack = list(reversed(getattr(function, "body", [])))
    while stack:
        node = stack.pop()
        yield node
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            stack.extend(reversed(list(ast.iter_child_nodes(node))))


def inspect_source(source: str, path: str) -> list[dict[str, Any]]:
    tree = ast.parse(source, filename=path)
    result = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        decorators = [d for d in node.decorator_list
                      if dotted(d.func if isinstance(d, ast.Call) else d).split(".")[-1] == "whitelist"]
        if not decorators:
            continue
        guest: bool | str = False
        for decorator in decorators:
            if isinstance(decorator, ast.Call):
                if any(k.arg is None for k in decorator.keywords):
                    guest = "UNKNOWN"
                for keyword in decorator.keywords:
                    if keyword.arg == "allow_guest":
                        guest = (keyword.value.value if isinstance(keyword.value, ast.Constant)
                                 and isinstance(keyword.value.value, bool) else "UNKNOWN")
        calls = [n for n in own_nodes(node) if isinstance(n, ast.Call)]
        names = {dotted(n.func) for n in calls}
        guards = sorted(n for n in names if n.split(".")[-1] in GUARD_NAMES)
        # These are review markers, not proof that a function is unsafe.
        markers = set()
        for call in calls:
            name = dotted(call.func)
            if name in {"frappe.get_all", "frappe.db.get_all"}:
                markers.add("GET_ALL")
            if name == "frappe.db.sql":
                markers.add("RAW_SQL")
            if name in {"frappe.db.set_value", "frappe.db.delete", "frappe.db.truncate"}:
                markers.add("DIRECT_DB_MUTATION")
            for keyword in call.keywords:
                if keyword.arg == "ignore_permissions":
                    markers.add("IGNORE_PERMISSIONS_ARGUMENT")
        result.append({"path": path, "line": node.lineno, "function": node.name,
                       "decorator_allow_guest": guest, "guard_calls_observed": guards,
                       "review_markers": sorted(markers),
                       "authorization_verdict": "NOT_EVALUATED"})
    return sorted(result, key=lambda row: (row["path"], row["line"]))


def scan_repository(root: Path, declared_commit: str) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{40}", declared_commit):
        raise ValueError("source commit must be a lowercase full SHA")
    root = root.resolve(strict=True)
    report: dict[str, Any] = {
        "schema_version": "hbos.iam0.source-inventory.v1",
        "declared_source_commit": declared_commit,
        "commit_verification": "EXTERNAL_REQUIRED",
        "mode": "SOURCE_ONLY_NO_SITE_ACCESS",
        "authorization_verdict": "NOT_EVALUATED",
        "runtime_inventory": "NOT_RUN", "files": [], "endpoints": [], "gaps": [],
        "limitations": ["Python whitelist-name matching only; aliases/dynamic registration may be missed",
                        "Guard markers are lexical, not control-flow or delegated-call analysis",
                        "No JS/TS routes, hooks, DocType JSON, reports or effective Site grants evaluated",
                        "No data values or current user permissions read"],
    }
    for app in APPS:
        source_root = root / "apps" / app / app
        relative_root = f"apps/{app}/{app}"
        # Reject a symlink at any component below the requested root.
        parts = [root / "apps", root / "apps" / app, source_root]
        if any(part.is_symlink() for part in parts) or not source_root.is_dir():
            report["gaps"].append({"path": relative_root, "reason": "MISSING_OR_SYMLINK_ROOT"})
            continue
        for directory, dirs, files in os.walk(source_root, followlinks=False):
            for d in list(dirs):
                if d in SKIP_DIRS:
                    dirs.remove(d)
                elif (Path(directory) / d).is_symlink():
                    report["gaps"].append({"path": (Path(directory) / d).relative_to(root).as_posix(),
                                           "reason": "SYMLINK_DIRECTORY"})
                    dirs.remove(d)
            dirs.sort()
            for filename in sorted(files):
                if not filename.endswith(".py") or filename.startswith("test_"):
                    continue
                path = Path(directory) / filename
                rel = path.relative_to(root).as_posix()
                if len(report["files"]) + len(report["gaps"]) >= MAX_FILES:
                    report["gaps"].append({"path": relative_root, "reason": "FILE_LIMIT"})
                    report["coverage_status"] = "PARTIAL"
                    return report
                try:
                    if path.is_symlink():
                        report["gaps"].append({"path": rel, "reason": "SYMLINK_FILE"})
                        continue
                    with path.open("rb") as handle:
                        raw = handle.read(MAX_BYTES + 1)
                    if len(raw) > MAX_BYTES:
                        report["gaps"].append({"path": rel, "reason": "FILE_SIZE_LIMIT"})
                        continue
                    entries = inspect_source(raw.decode("utf-8-sig"), rel)
                    report["files"].append({"path": rel, "sha256": hashlib.sha256(raw).hexdigest()})
                    report["endpoints"].extend(entries)
                except (OSError, UnicodeError, SyntaxError):
                    report["gaps"].append({"path": rel, "reason": "READ_OR_PARSE_ERROR"})
    report["files"].sort(key=lambda row: row["path"])
    report["endpoints"].sort(key=lambda row: (row["path"], row["line"]))
    report["coverage_status"] = "PARTIAL" if report["gaps"] else "DECLARED_PYTHON_ROOTS_SCANNED"
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--source-commit", required=True,
                        help="Declared full SHA; independently verify HEAD and source cleanliness")
    args = parser.parse_args()
    try:
        report = scan_repository(args.repo, args.source_commit)
    except (OSError, ValueError):
        print(json.dumps({"error": "INVALID_SOURCE_INPUT", "runtime_inventory": "NOT_RUN"}))
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 2 if report["gaps"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
