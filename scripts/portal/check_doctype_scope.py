#!/usr/bin/env python3
"""Check the candidate Portal DocType scope without Frappe or a live Site.

The organization/IAM entries are a source-review boundary only. Their presence
does not approve product policy, runtime enablement, or database migration.
"""
import argparse
import json
from pathlib import Path
import sys


PORTAL_APP = Path("apps/hbos_portal")

# Full repository paths and identities read from the existing JSON definitions.
# Keep the four account models and the eight explicitly scoped IAM candidates.
APPROVED_DOCTYPES = {
    "apps/hbos_portal/hbos_portal/hbos_portal/doctype/hbos_external_identity/hbos_external_identity.json":
        ("DocType", "HBOS External Identity", "HBOS Portal"),
    "apps/hbos_portal/hbos_portal/hbos_portal/doctype/hbos_account_operation/hbos_account_operation.json":
        ("DocType", "HBOS Account Operation", "HBOS Portal"),
    "apps/hbos_portal/hbos_portal/hbos_portal/doctype/hbos_account_change_event/hbos_account_change_event.json":
        ("DocType", "HBOS Account Change Event", "HBOS Portal"),
    "apps/hbos_portal/hbos_portal/hbos_portal/doctype/hbos_account_security/hbos_account_security.json":
        ("DocType", "HBOS Account Security", "HBOS Portal"),
    "apps/hbos_portal/hbos_portal/hbos_portal/doctype/hbos_position/hbos_position.json":
        ("DocType", "HBOS Position", "HBOS Portal"),
    "apps/hbos_portal/hbos_portal/hbos_portal/doctype/hbos_position_revision/hbos_position_revision.json":
        ("DocType", "HBOS Position Revision", "HBOS Portal"),
    "apps/hbos_portal/hbos_portal/hbos_portal/doctype/hbos_personnel_assignment/hbos_personnel_assignment.json":
        ("DocType", "HBOS Personnel Assignment", "HBOS Portal"),
    "apps/hbos_portal/hbos_portal/hbos_portal/doctype/hbos_personnel_assignment_revision/hbos_personnel_assignment_revision.json":
        ("DocType", "HBOS Personnel Assignment Revision", "HBOS Portal"),
    "apps/hbos_portal/hbos_portal/hbos_portal/doctype/hbos_organization_command_receipt/hbos_organization_command_receipt.json":
        ("DocType", "HBOS Organization Command Receipt", "HBOS Portal"),
    "apps/hbos_portal/hbos_portal/hbos_portal/doctype/hbos_organization_write_lock/hbos_organization_write_lock.json":
        ("DocType", "HBOS Organization Write Lock", "HBOS Portal"),
    "apps/hbos_portal/hbos_portal/hbos_portal/doctype/hbos_organization_management_policy/hbos_organization_management_policy.json":
        ("DocType", "HBOS Organization Management Policy", "HBOS Portal"),
    "apps/hbos_portal/hbos_portal/hbos_portal/doctype/hbos_organization_management_policy_revision/hbos_organization_management_policy_revision.json":
        ("DocType", "HBOS Organization Management Policy Revision", "HBOS Portal"),
}


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _declared_models(value):
    if isinstance(value, dict):
        if value.get("doctype") == "DocType":
            yield value
        for child in value.values():
            yield from _declared_models(child)
    elif isinstance(value, list):
        for child in value:
            yield from _declared_models(child)


def check_doctype_scope(repository_root: Path) -> list[str]:
    """Return every refusal with its repository-relative file and reason."""
    repository_root = Path(repository_root)
    app_root = repository_root / PORTAL_APP
    if not app_root.is_dir() or app_root.is_symlink():
        return [f"{PORTAL_APP.as_posix()}: missing Portal App directory or symbolic link"]

    failures = []
    found_paths = set()
    seen_names = {}
    approved_filenames = {Path(path).name for path in APPROVED_DOCTYPES}
    for path in sorted(app_root.rglob("*")):
        relative = path.relative_to(repository_root).as_posix()
        if path.is_symlink():
            # rglob does not descend directory links. Reject them so additional
            # models cannot be hidden there, or an approved path redirected.
            failures.append(f"{relative}: symbolic links are not allowed in the Portal JSON scope")
            continue
        if not path.is_file() or path.suffix.lower() != ".json":
            continue
        if relative in APPROVED_DOCTYPES:
            found_paths.add(relative)
        try:
            metadata = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_keys)
            declarations = list(_declared_models(metadata))
        except json.JSONDecodeError as error:
            failures.append(f"{relative}: invalid JSON at line {error.lineno}, column {error.colno}: {error.msg}")
            continue
        except (OSError, UnicodeError, ValueError, RecursionError) as error:
            failures.append(f"{relative}: cannot read unambiguous JSON: {error}")
            continue

        # Inspect the whole App: approved basenames and DocType declarations
        # outside a doctype tree must not silently escape the scope check.
        if "doctype" not in path.relative_to(app_root).parts and path.name not in approved_filenames and not declarations:
            continue
        if declarations and (len(declarations) != 1 or declarations[0] is not metadata):
            failures.append(f"{relative}: embedded DocType declarations are not allowed; use each model's exact registered file")
        for model in declarations:
            name = model.get("name")
            if not isinstance(name, str):
                continue
            if name in seen_names:
                failures.append(f"{relative}: duplicate model identity {name!r}; first declared in {seen_names[name]}")
            else:
                seen_names[name] = relative
        expected = APPROVED_DOCTYPES.get(relative)
        if expected is None:
            failures.append(f"{relative}: unapproved DocType path or filename")
            continue
        if not isinstance(metadata, dict):
            failures.append(f"{relative}: DocType JSON must be an object")
            continue
        for field, value in zip(("doctype", "name", "module"), expected):
            if metadata.get(field) != value:
                failures.append(f"{relative}: identity mismatch for {field}: expected {value!r}, got {metadata.get(field)!r}")

    for relative in sorted(set(APPROVED_DOCTYPES) - found_paths):
        failures.append(f"{relative}: required registered DocType file is missing")
    return failures


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2],
                        help="repository root (defaults to this script's repository)")
    args = parser.parse_args(argv)
    failures = check_doctype_scope(args.root)
    if failures:
        print("Portal DocType scope FAIL", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 1
    print(f"Portal DocType scope PASS: {len(APPROVED_DOCTYPES)} exact model paths and JSON identities")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
