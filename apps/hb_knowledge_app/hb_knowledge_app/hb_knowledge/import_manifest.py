from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable


ALLOWED_EXTENSIONS = {
    ".doc",
    ".docx",
    ".md",
    ".pdf",
    ".ppt",
    ".pptx",
    ".txt",
    ".xls",
    ".xlsx",
}
BLOCKED_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    "id_rsa",
    "id_ed25519",
}
BLOCKED_SUFFIXES = {".bak", ".key", ".pem", ".p12", ".pfx", ".sqlite", ".tmp"}


class ManifestError(ValueError):
    pass


@dataclass(frozen=True)
class ManifestItem:
    source_ref: str
    relative_path: str
    media_type: str | None
    extension: str
    size_bytes: int
    sha256: str
    source_version: None = None
    approval_status: None = None
    knowledge_owner: None = None
    proposed_dataset: None = None
    ingestion_status: str = "pending_owner_approval"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _source_ref(root: Path, relative_path: str) -> str:
    # The manifest intentionally uses an opaque root reference rather than an
    # absolute filesystem path that could leak through later APIs.
    root_id = hashlib.sha256(str(root).encode("utf-8")).hexdigest()[:16]
    return f"local-root:{root_id}:{relative_path}"


def _media_type(extension: str) -> str | None:
    return {
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".ppt": "application/vnd.ms-powerpoint",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".xls": "application/vnd.ms-excel",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }.get(extension)


def _validate_relative_selection(value: str) -> PurePosixPath:
    candidate = PurePosixPath(value)
    if candidate.is_absolute() or not candidate.parts:
        raise ManifestError("selection must be a non-empty relative path")
    if any(part in {"", ".", ".."} for part in candidate.parts):
        raise ManifestError("selection contains an unsafe path segment")
    if any(part.startswith(".") for part in candidate.parts):
        raise ManifestError("hidden files and directories are not eligible")
    return candidate


def build_manifest(root: str | os.PathLike[str], selections: Iterable[str]) -> dict[str, object]:
    root_path = Path(root).expanduser()
    if not root_path.is_absolute() or not root_path.is_dir() or root_path.is_symlink():
        raise ManifestError("approved root must be an existing non-symlink absolute directory")
    root_resolved = root_path.resolve(strict=True)
    selected_values = [str(item).strip() for item in selections if str(item).strip()]
    if not selected_values:
        raise ManifestError("at least one Owner-selected relative file is required")

    items: list[ManifestItem] = []
    for raw in selected_values:
        relative = _validate_relative_selection(raw)
        candidate = root_resolved.joinpath(*relative.parts)
        if candidate.is_symlink():
            raise ManifestError(f"symlink selections are not eligible: {relative.as_posix()}")
        try:
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(root_resolved)
        except (FileNotFoundError, ValueError) as exc:
            raise ManifestError(f"selection is missing or outside the approved root: {relative.as_posix()}") from exc
        if not resolved.is_file():
            raise ManifestError(f"selection must identify a file: {relative.as_posix()}")
        if any(parent.is_symlink() for parent in candidate.parents if parent != root_resolved.parent):
            raise ManifestError(f"symlink path components are not eligible: {relative.as_posix()}")

        name_lower = resolved.name.lower()
        extension = resolved.suffix.lower()
        if name_lower in BLOCKED_NAMES or extension in BLOCKED_SUFFIXES:
            raise ManifestError(f"blocked sensitive or backup file: {relative.as_posix()}")
        if extension not in ALLOWED_EXTENSIONS:
            raise ManifestError(f"unsupported document type: {relative.as_posix()}")

        stat = resolved.stat()
        items.append(
            ManifestItem(
                source_ref=_source_ref(root_resolved, relative.as_posix()),
                relative_path=relative.as_posix(),
                media_type=_media_type(extension),
                extension=extension,
                size_bytes=stat.st_size,
                sha256=_sha256(resolved),
            )
        )

    hash_counts: dict[str, int] = {}
    for item in items:
        hash_counts[item.sha256] = hash_counts.get(item.sha256, 0) + 1

    serialized_items = []
    for item in items:
        value = asdict(item)
        value["duplicate_in_selection"] = hash_counts[item.sha256] > 1
        serialized_items.append(value)

    return {
        "schema_version": 1,
        "mode": "dry_run_only",
        "status": "pending_owner_approval",
        "root_ref": hashlib.sha256(str(root_resolved).encode("utf-8")).hexdigest()[:16],
        "item_count": len(serialized_items),
        "items": serialized_items,
        "next_action": "owner_approve_manifest_and_processing_boundary",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create an HBOS knowledge dry-run manifest for explicitly selected files.",
    )
    parser.add_argument("--root", required=True, help="Owner-approved absolute source root")
    parser.add_argument(
        "--select",
        action="append",
        default=[],
        help="Owner-selected relative file path; repeat for each file",
    )
    parser.add_argument("--output", required=True, help="Private manifest output path")
    args = parser.parse_args(argv)

    manifest = build_manifest(args.root, args.select)
    output = Path(args.output).expanduser()
    if output.is_symlink():
        raise ManifestError("output must not be a symbolic link")
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(output, flags, 0o600)
    os.fchmod(descriptor, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
