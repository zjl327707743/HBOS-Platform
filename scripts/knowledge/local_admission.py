"""Offline, fail-closed material discovery and immutable admission planning.

This module reads only caller-supplied local roots. It has no network client,
model call, database writer, archive expander, or document renderer. Content
reviews are separate private evidence; absence of a review never admits a file.
Plans do not authorize ingestion or publication and do not modify old registries.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping


class AdmissionError(ValueError):
    pass


def _digest(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _safe_absolute_directory(value: str | os.PathLike[str]) -> Path:
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts:
        raise AdmissionError("root must be an absolute directory without parent traversal")
    for parent in reversed((path, *path.parents)):
        try:
            metadata = parent.lstat()
        except OSError as exc:
            raise AdmissionError("root or an ancestor is unavailable") from exc
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise AdmissionError("root and every ancestor must be non-symlink directories")
    if path.resolve(strict=True) != path:
        raise AdmissionError("root resolves to a different path")
    return path


def _open_directory_safely(path: Path) -> int:
    """Open each ancestor through a held descriptor, rejecting link races."""
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path.anchor, flags)
    try:
        for component in path.parts[1:]:
            child = os.open(component, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _hash_regular_file(name: str, expected: os.stat_result, directory_fd: int) -> str:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(name, flags, dir_fd=directory_fd)
    with os.fdopen(descriptor, "rb") as handle:
        actual = os.fstat(handle.fileno())
        identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
        if not stat.S_ISREG(actual.st_mode) or identity(actual) != identity(expected):
            raise AdmissionError("source changed before hashing")
        digest = hashlib.sha256()
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
        if identity(os.fstat(handle.fileno())) != identity(actual):
            raise AdmissionError("source changed while hashing")
        after = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        if stat.S_ISLNK(after.st_mode) or identity(after) != identity(actual):
            raise AdmissionError("source path changed while hashing")
    return digest.hexdigest()


def discover(roots: Mapping[str, str | os.PathLike[str]]) -> dict[str, Any]:
    """Hash ordinary files without following links or executing their contents.

    Root names are caller-defined aliases. Private paths remain in the private
    inventory only; callers must not expose inventories as employee directories.
    """
    if not roots or any(not isinstance(k, str) or not k.strip() for k in roots):
        raise AdmissionError("at least one named root is required")
    records: list[dict[str, Any]] = []
    exclusions: list[dict[str, str]] = []
    approved_roots: list[dict[str, str]] = []
    resolved_roots: list[Path] = []
    for alias, raw_root in sorted(roots.items()):
        root = _safe_absolute_directory(raw_root)
        if any(root == other or root in other.parents or other in root.parents for other in resolved_roots):
            raise AdmissionError("approved roots must be distinct and non-overlapping")
        resolved_roots.append(root)
        approved_roots.append({"root_alias": alias, "source_root": str(root)})

        def visit(directory_fd: int, relative_directory: PurePosixPath) -> None:
            # All children open relative to held non-symlink descriptors. A
            # renamed/swapped directory cannot redirect reads outside the root.
            with os.scandir(directory_fd) as stream:
                names = sorted(entry.name for entry in stream)
            for name in names:
                relative = (relative_directory / name).as_posix()
                metadata = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                base = {"root_alias": alias, "relative_path": relative}
                if stat.S_ISLNK(metadata.st_mode):
                    exclusions.append({**base, "reason": "SYMLINK_NOT_FOLLOWED"})
                elif stat.S_ISDIR(metadata.st_mode):
                    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
                    child_fd = os.open(name, flags, dir_fd=directory_fd)
                    try:
                        actual = os.fstat(child_fd)
                        if (actual.st_dev, actual.st_ino) != (metadata.st_dev, metadata.st_ino):
                            exclusions.append({**base, "reason": "DIRECTORY_CHANGED"})
                        else:
                            visit(child_fd, PurePosixPath(relative))
                    finally:
                        os.close(child_fd)
                elif not stat.S_ISREG(metadata.st_mode):
                    exclusions.append({**base, "reason": "NONREGULAR_NOT_READ"})
                else:
                    try:
                        source_hash = _hash_regular_file(name, metadata, directory_fd)
                    except (AdmissionError, OSError):
                        exclusions.append({**base, "reason": "SOURCE_CHANGED_OR_UNREADABLE"})
                        continue
                    records.append({
                        **base,
                        "source_sha256": source_hash,
                        "size_bytes": metadata.st_size,
                        "extension": PurePosixPath(name).suffix.lower(),
                        "source_ref": f"local-root:{_digest(alias)[:16]}:{relative}",
                        "discovery_status": "DISCOVERED_READONLY",
                    })

        root_fd = _open_directory_safely(root)
        try:
            visit(root_fd, PurePosixPath())
        finally:
            os.close(root_fd)
    return {
        "schema_version": 1,
        "mode": "OFFLINE_ONLY",
        "roots": approved_roots,
        "files": records,
        "excluded_entries": exclusions,
        "inventory_sha256": _digest(records),
    }


def _sha(value: Any) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise AdmissionError("source SHA-256 must be lowercase hexadecimal")
    return value


def _review_decision(review: Mapping[str, Any] | None, source_hash: str) -> tuple[str, str]:
    if not review:
        return "QUARANTINE", "CONTENT_REVIEW_MISSING"
    if review.get("source_sha256") != source_hash:
        return "QUARANTINE", "CONTENT_REVIEW_HASH_MISMATCH"
    if review.get("decision") != "ADMIT_INTERNAL_REFERENCE":
        return "QUARANTINE", str(review.get("reason_code") or "LOCAL_REVIEW_QUARANTINED")
    if review.get("sensitive_flags"):
        return "QUARANTINE", "SENSITIVE_CONTENT_FLAGGED"
    if not all(review.get(k) is True for k in (
        "actual_content_checked", "extraction_complete", "internal_sharing_applicable", "external_processing_applicable"
    )):
        return "QUARANTINE", "CONTENT_OR_SHARING_SCOPE_UNPROVEN"
    try:
        _sha(review.get("review_evidence_sha256"))
    except AdmissionError:
        return "QUARANTINE", "REVIEW_EVIDENCE_MISSING"
    return "ADMIT_INTERNAL_REFERENCE", str(review.get("reason_code") or "ORDINARY_REFERENCE_CONTENT_CHECKED")


def build_plan(
    inventory: Mapping[str, Any],
    reviews: Mapping[str, Mapping[str, Any]],
    registry_rows: Iterable[Mapping[str, Any]],
    department_keys: Mapping[str, str],
    datasets: Iterable[Mapping[str, Any]],
    *,
    batch_name: str,
    version_relations: Mapping[str, Mapping[str, str]] | None = None,
) -> dict[str, Any]:
    """Create a dry-run plan using a shared exported identity registry.

    Same content reuses identity regardless of filename or department. Same
    path/title with changed bytes requires an explicit immutable version link.
    Existing withdrawn/published state is recorded, never changed by this tool.
    """
    by_hash: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    by_identity: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    by_name: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    rows = list(registry_rows)
    for row in rows:
        source_hash = row.get("sha256") or row.get("source_sha256")
        if source_hash:
            by_hash[_sha(source_hash)].append(row)
        if row.get("canonical_document_id"):
            by_identity[str(row["canonical_document_id"])].append(row)
        if row.get("department_key") and row.get("relative_path"):
            by_name[(str(row["department_key"]), PurePosixPath(str(row["relative_path"])).name)].append(row)
    dataset_by_department: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for dataset in datasets:
        if dataset.get("department_key"):
            dataset_by_department[str(dataset["department_key"])].append(dataset)

    items: list[dict[str, Any]] = []
    first_content: dict[str, dict[str, Any]] = {}
    content_identity_conflicts: set[str] = set()
    seen_inputs: set[tuple[str, str]] = set()
    for source in inventory.get("files", []):
        alias, relative = str(source["root_alias"]), str(source["relative_path"])
        input_key = (alias, relative)
        if input_key in seen_inputs:
            raise AdmissionError("inventory repeats an input path")
        seen_inputs.add(input_key)
        path = PurePosixPath(relative)
        if path.is_absolute() or ".." in path.parts or not relative:
            raise AdmissionError("inventory contains an unsafe relative path")
        source_hash = _sha(source["source_sha256"])
        if alias not in department_keys:
            raise AdmissionError("inventory root has no explicit department mapping")
        department = department_keys[alias]
        decision, reason = _review_decision(reviews.get(source_hash), source_hash)
        matches = by_hash[source_hash]
        identities = {(r.get("canonical_document_id"), r.get("version_id")) for r in matches}
        item = dict(source)
        item.update({
            "department_key": department,
            "admission_decision": decision,
            "reason_code": reason,
            "review_evidence_sha256": (reviews.get(source_hash) or {}).get("review_evidence_sha256"),
            "reference_status": "INTERNAL_REFERENCE_EFFECTIVENESS_UNVERIFIED",
            "processing_status": "QUARANTINED_LOCAL_ONLY" if decision == "QUARANTINE" else "PREPARED_NOT_INGESTED",
            "publication_status": "NOT_PUBLISHED_BY_PLAN",
            "canonical_document_id": None,
            "version_id": None,
            "target_dataset_id": None,
            "online_gate": "COORDINATOR_GATES_REQUIRED",
        })
        department_datasets = dataset_by_department[department]
        dataset_ids = {d.get("dataset_id") for d in department_datasets}
        if len(dataset_ids) > 1 or (department_datasets and None in dataset_ids):
            item.update(admission_decision="QUARANTINE", reason_code="DATASET_MAPPING_AMBIGUOUS", processing_status="QUARANTINED_LOCAL_ONLY")
        elif department_datasets:
            item["target_dataset_id"] = next(iter(dataset_ids))
            item["dataset_action"] = "REUSE_EXACT_REGISTERED_ID_AFTER_BINDING_CHECK"
            item["registered_embedding_model"] = department_datasets[0].get("embedding_model")
        else:
            item["dataset_action"] = "CREATE_ONCE_AND_REGISTER_AFTER_ONLINE_GATES"

        if identities:
            if len(identities) != 1 or any(not a or not b for a, b in identities):
                item.update(admission_decision="QUARANTINE", reason_code="EXISTING_CONTENT_IDENTITY_CONFLICT", processing_status="QUARANTINED_LOCAL_ONLY")
            else:
                item["canonical_document_id"], item["version_id"] = next(iter(identities))
                item["identity_relation"] = "SAME_CONTENT_REUSE_OR_ALIAS"
                item["upload_action"] = "SKIP_EXISTING_CONTENT"
                item["existing_states"] = sorted({str(r.get("status") or r.get("ingestion_status") or "UNKNOWN") for r in matches})
                item["existing_dataset_ids"] = sorted({str(r["dataset_id"]) for r in matches if r.get("dataset_id")})
        else:
            relation_key = f"{alias}:{relative}"
            relation = (version_relations or {}).get(relation_key)
            prior_named = by_name[(department, path.name)]
            if relation:
                canonical = relation.get("canonical_document_id")
                expected_version = relation.get("expected_current_version")
                prior = by_identity.get(str(canonical), [])
                explicit_current = {r.get("current_version_id") for r in prior if r.get("current_version_id")}
                prior_versions = explicit_current or {r.get("version_id") for r in prior}
                if not prior or prior_versions != {expected_version} or relation.get("source_sha256") != source_hash:
                    item.update(admission_decision="QUARANTINE", reason_code="EXPLICIT_VERSION_RELATION_INVALID", processing_status="QUARANTINED_LOCAL_ONLY")
                else:
                    item.update(canonical_document_id=canonical, version_id=f"N1VER-{source_hash[:24]}", identity_relation="EXPLICIT_IMMUTABLE_NEW_VERSION", expected_current_version=expected_version, upload_action="NEW_VERSION_AFTER_GATES")
            elif prior_named:
                item.update(admission_decision="QUARANTINE", reason_code="CHANGED_CONTENT_REQUIRES_VERSION_RELATION", processing_status="QUARANTINED_LOCAL_ONLY", identity_relation="UNRESOLVED_CHANGED_CONTENT")
            else:
                item.update(canonical_document_id=f"N1DOC-{source_hash[:24]}", version_id=f"N1VER-{source_hash[:24]}", identity_relation="NEW_CONTENT", upload_action="UPLOAD_ONCE_AFTER_GATES")

        # A quarantined occurrence cannot become an ingestion representative.
        # Equal bytes do not authorize replacing an explicit immutable identity
        # or its compare-and-set predecessor. Quarantine every admitted member
        # of a conflicting content group, including an earlier representative.
        if source_hash in content_identity_conflicts and item["admission_decision"] != "QUARANTINE":
            item.update(admission_decision="QUARANTINE", reason_code="BATCH_CONTENT_VERSION_IDENTITY_CONFLICT", processing_status="QUARANTINED_LOCAL_ONLY")
        elif source_hash in first_content and item["admission_decision"] != "QUARANTINE":
            prior = first_content[source_hash]
            identity_keys = ("canonical_document_id", "version_id", "expected_current_version")
            if any(item.get(key) != prior.get(key) for key in identity_keys):
                content_identity_conflicts.add(source_hash)
                for member in (*items, item):
                    if member["source_sha256"] == source_hash and member["admission_decision"] != "QUARANTINE":
                        member.update(admission_decision="QUARANTINE", reason_code="BATCH_CONTENT_VERSION_IDENTITY_CONFLICT", processing_status="QUARANTINED_LOCAL_ONLY", upload_action="PROHIBITED_LOCAL_QUARANTINE")
                        member.pop("classification_alias_of", None)
            else:
                item.update(identity_relation="SAME_CONTENT_CLASSIFICATION_ALIAS", upload_action="SKIP_DUPLICATE_IN_PLAN", classification_alias_of={"root_alias": prior["root_alias"], "relative_path": prior["relative_path"]})
        elif item["admission_decision"] != "QUARANTINE":
            first_content[source_hash] = item
        if item["admission_decision"] == "QUARANTINE":
            item["upload_action"] = "PROHIBITED_LOCAL_QUARANTINE"
        items.append(item)

    summary = {
        "discovered": len(items),
        "unique_source_contents": len({i["source_sha256"] for i in items}),
        "admitted_paths": sum(i["admission_decision"] == "ADMIT_INTERNAL_REFERENCE" for i in items),
        "quarantined_paths": sum(i["admission_decision"] == "QUARANTINE" for i in items),
        "new_unique_admitted": sum(i["upload_action"] in {"UPLOAD_ONCE_AFTER_GATES", "NEW_VERSION_AFTER_GATES"} for i in items),
        "duplicate_or_existing_skips": sum(i["upload_action"] in {"SKIP_EXISTING_CONTENT", "SKIP_DUPLICATE_IN_PLAN"} for i in items),
        "uploaded": 0,
        "indexed": 0,
        "quality_approved": 0,
        "published": 0,
        "reasons": dict(Counter(i["reason_code"] for i in items)),
    }
    plan = {
        "schema_version": 1,
        "batch_name": batch_name,
        "mode": "OFFLINE_IMMUTABLE_PLAN_ONLY",
        "inventory_sha256": inventory.get("inventory_sha256"),
        "registry_export_sha256": _digest(rows),
        "scope": "INTERNAL_SHARED_REFERENCE_CANDIDATE",
        "business_effectiveness": "NOT_APPROVED_BY_TECHNICAL_SCREENING",
        "summary": summary,
        "items": items,
        "excluded_entries": inventory.get("excluded_entries", []),
    }
    plan["batch_sha256"] = _digest(plan)
    return plan


def write_private_frozen_json(path: str | os.PathLike[str], value: Any) -> str:
    """Write mode 0600 once; identical replay is a NOOP, changed replay fails."""
    output = Path(path)
    _safe_absolute_directory(output.parent)
    if stat.S_IMODE(output.parent.stat().st_mode) & 0o077:
        raise AdmissionError("private output directory must have mode 0700")
    encoded = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    directory_fd = _open_directory_safely(output.parent)
    try:
        if stat.S_IMODE(os.fstat(directory_fd).st_mode) & 0o077:
            raise AdmissionError("private output directory must have mode 0700")
        try:
            metadata = os.stat(output.name, dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            metadata = None
        if metadata is not None:
            if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) & 0o077:
                raise AdmissionError("existing private output is unsafe")
            descriptor = os.open(output.name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=directory_fd)
            with os.fdopen(descriptor, "rb") as handle:
                actual = os.fstat(handle.fileno())
                if (actual.st_dev, actual.st_ino) != (metadata.st_dev, metadata.st_ino) or handle.read() != encoded:
                    raise AdmissionError("frozen output already exists with different contents")
            return "NOOP"
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(output.name, flags, 0o600, dir_fd=directory_fd)
        with os.fdopen(descriptor, "wb") as handle:
            os.fchmod(handle.fileno(), 0o600)
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        return "CREATED"
    finally:
        os.close(directory_fd)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", action="append", required=True, metavar="ALIAS=ABSOLUTE_PATH")
    parser.add_argument("--output", required=True, help="Existing mode-0700 private output directory/file")
    args = parser.parse_args(argv)
    roots: dict[str, str] = {}
    for raw in args.root:
        alias, separator, path = raw.partition("=")
        if not separator or alias in roots:
            parser.error("each root must be a distinct ALIAS=ABSOLUTE_PATH")
        roots[alias] = path
    inventory = discover(roots)
    result = write_private_frozen_json(args.output, inventory)
    print(json.dumps({"write": result, "discovered": len(inventory["files"]), "excluded": len(inventory["excluded_entries"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
