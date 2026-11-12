from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
import tempfile
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


class LocalIndexError(RuntimeError):
    pass


ASCII_TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9._/-]{1,63}", re.IGNORECASE)
CJK_SEQUENCE_PATTERN = re.compile(r"[\u3400-\u9fff]+")
WHITESPACE_PATTERN = re.compile(r"[\t\r\f\v ]+")


def _secure_regular_file(path: Path, *, owner_only: bool = False) -> os.stat_result:
    try:
        metadata = path.lstat()
    except FileNotFoundError as exc:
        raise LocalIndexError(f"Required file is missing: {path.name}") from exc
    if not stat.S_ISREG(metadata.st_mode) or path.is_symlink():
        raise LocalIndexError(f"Unsafe file type: {path.name}")
    if owner_only and metadata.st_mode & 0o077:
        raise LocalIndexError(f"Private file permissions are too broad: {path.name}")
    if hasattr(os, "geteuid") and metadata.st_uid != os.geteuid():
        raise LocalIndexError(f"Unexpected file owner: {path.name}")
    return metadata


def _atomic_private_write(path: Path, payload: str) -> None:
    if path.exists() and path.is_symlink():
        raise LocalIndexError(f"Refusing symlink output: {path.name}")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        dir=str(path.parent),
        text=True,
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        path.chmod(0o600)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _normalize_page_text(value: str) -> str:
    lines = []
    for raw_line in value.replace("\u00a0", " ").splitlines():
        line = WHITESPACE_PATTERN.sub(" ", raw_line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def _chunks(value: str, *, maximum: int = 900, overlap: int = 100) -> Iterable[str]:
    if maximum < 200 or overlap < 0 or overlap >= maximum:
        raise LocalIndexError("Invalid chunk settings")
    paragraphs = [item.strip() for item in value.split("\n") if item.strip()]
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > maximum:
            if current:
                yield current
                current = ""
            start = 0
            while start < len(paragraph):
                chunk = paragraph[start : start + maximum].strip()
                if chunk:
                    yield chunk
                start += maximum - overlap
            continue
        candidate = paragraph if not current else f"{current}\n{paragraph}"
        if len(candidate) <= maximum:
            current = candidate
            continue
        yield current
        tail = current[-overlap:].strip() if overlap else ""
        current = f"{tail}\n{paragraph}".strip() if tail else paragraph
    if current:
        yield current


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_private_manifest(path: Path) -> Mapping[str, Any]:
    _secure_regular_file(path, owner_only=True)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LocalIndexError("Approved import manifest is invalid") from exc
    if not isinstance(value, Mapping) or value.get("schema_version") != 1:
        raise LocalIndexError("Approved import manifest schema is invalid")
    return value


def build_private_index(manifest_path: str | Path, output_root: str | Path) -> dict[str, Any]:
    """Extract only explicitly approved PDFs into an owner-only lexical index."""

    from pypdf import PdfReader

    manifest = _load_private_manifest(Path(manifest_path).expanduser().resolve())
    dataset_id = str(manifest.get("dataset_id") or "").strip()
    documents = manifest.get("documents")
    if not dataset_id or not isinstance(documents, list) or not documents:
        raise LocalIndexError("Approved import manifest has no dataset or documents")

    output = Path(output_root).expanduser().resolve()
    if output.exists() and output.is_symlink():
        raise LocalIndexError("Private output root cannot be a symlink")
    output.mkdir(mode=0o700, parents=True, exist_ok=True)
    output.chmod(0o700)

    seen_ids: set[str] = set()
    index_rows: list[dict[str, Any]] = []
    record_items: list[dict[str, Any]] = []
    for raw in documents:
        if not isinstance(raw, Mapping):
            raise LocalIndexError("Document entry is invalid")
        document_id = str(raw.get("document_id") or "").strip()
        source = Path(str(raw.get("source_path") or "")).expanduser()
        title = str(raw.get("title") or "").strip()
        version = str(raw.get("version") or "").strip() or None
        status_note = str(raw.get("status_note") or "").strip()
        equipment_ids = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in (raw.get("equipment_ids") or [])
                if str(item).strip()
            )
        )
        if not document_id or document_id in seen_ids or not title or not status_note:
            raise LocalIndexError("Document metadata is incomplete or duplicated")
        seen_ids.add(document_id)
        if source.suffix.lower() != ".pdf":
            raise LocalIndexError(f"Only PDF sources are accepted: {document_id}")
        _secure_regular_file(source)

        reader = PdfReader(str(source), strict=False)
        document_rows: list[dict[str, Any]] = []
        extracted_characters = 0
        for page_number, page in enumerate(reader.pages, start=1):
            text = _normalize_page_text(page.extract_text() or "")
            extracted_characters += len(text)
            if not text:
                raise LocalIndexError(
                    f"Native text extraction is empty for {document_id} page {page_number}; OCR approval is required"
                )
            for chunk_number, excerpt in enumerate(_chunks(text), start=1):
                chunk_id = hashlib.sha256(
                    f"{document_id}\x1f{page_number}\x1f{chunk_number}\x1f{excerpt}".encode("utf-8")
                ).hexdigest()[:32]
                document_rows.append(
                    {
                        "dataset_id": dataset_id,
                        "document_id": document_id,
                        "title": title,
                        "version": version,
                        "status_note": status_note,
                        "section": f"第 {page_number} 页 · 文本块 {chunk_number}",
                        "page_number": page_number,
                        "chunk_id": chunk_id,
                        "excerpt": excerpt,
                        "equipment_ids": list(equipment_ids),
                    }
                )
        if not document_rows:
            raise LocalIndexError(f"No searchable content extracted: {document_id}")
        index_rows.extend(document_rows)
        record_items.append(
            {
                "document_id": document_id,
                "source_filename": source.name,
                "source_sha256": _sha256(source),
                "source_size_bytes": source.stat().st_size,
                "page_count": len(reader.pages),
                "extracted_characters": extracted_characters,
                "chunk_count": len(document_rows),
                "extraction_method": "pypdf-native-text",
                "ocr_used": False,
                "version": version,
                "status_note": status_note,
                "equipment_ids": list(equipment_ids),
            }
        )

    serialized_index = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in index_rows
    )
    index_path = output / "index.jsonl"
    record_path = output / "import_record.json"
    _atomic_private_write(index_path, serialized_index)
    record = {
        "schema_version": 1,
        "dataset_id": dataset_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "item_count": len(record_items),
        "chunk_count": len(index_rows),
        "publication": "enterprise_internal_reference_retrieval_only",
        "source_download_enabled": False,
        "external_processing_used": False,
        "generative_answer_enabled": False,
        "items": record_items,
    }
    _atomic_private_write(
        record_path,
        json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    return {**record, "index_path": str(index_path), "record_path": str(record_path)}


def tokenize(value: str) -> tuple[str, ...]:
    normalized = value.casefold()
    tokens: list[str] = [match.group(0) for match in ASCII_TOKEN_PATTERN.finditer(normalized)]
    for sequence in CJK_SEQUENCE_PATTERN.findall(normalized):
        tokens.extend(sequence)
        tokens.extend(sequence[index : index + 2] for index in range(len(sequence) - 1))
    return tuple(dict.fromkeys(token for token in tokens if token))


@dataclass(frozen=True)
class LocalIndex:
    rows: tuple[Mapping[str, Any], ...]

    @classmethod
    def from_file(cls, path: str | Path) -> "LocalIndex":
        source = Path(path).expanduser().resolve()
        metadata = _secure_regular_file(source, owner_only=True)
        if metadata.st_size <= 0 or metadata.st_size > 100 * 1024 * 1024:
            raise LocalIndexError("Private index size is invalid")
        rows: list[Mapping[str, Any]] = []
        for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise LocalIndexError(f"Private index row {line_number} is invalid") from exc
            if not isinstance(row, Mapping):
                raise LocalIndexError(f"Private index row {line_number} is invalid")
            required = ("dataset_id", "document_id", "chunk_id", "excerpt")
            if any(not str(row.get(field) or "").strip() for field in required):
                raise LocalIndexError(f"Private index row {line_number} is incomplete")
            rows.append(row)
        if not rows:
            raise LocalIndexError("Private index is empty")
        return cls(tuple(rows))

    def search(
        self,
        *,
        query: str,
        dataset_ids: Sequence[str],
        document_ids: Sequence[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        query_tokens = tokenize(query)
        if not query_tokens:
            return []
        allowed_datasets = set(dataset_ids)
        allowed_documents = set(document_ids)
        candidates = [
            row
            for row in self.rows
            if row.get("dataset_id") in allowed_datasets
            and row.get("document_id") in allowed_documents
        ]
        if not candidates:
            return []

        document_frequency: Counter[str] = Counter()
        row_tokens: list[tuple[Mapping[str, Any], Counter[str], set[str]]] = []
        for row in candidates:
            title = str(row.get("title") or "")
            excerpt = str(row.get("excerpt") or "")
            counter = Counter(tokenize(f"{title}\n{excerpt}"))
            present = set(counter)
            row_tokens.append((row, counter, present))
            document_frequency.update(present)

        total = len(row_tokens)
        normalized_query = "".join(query.casefold().split())
        scored: list[tuple[float, Mapping[str, Any]]] = []
        for row, counter, present in row_tokens:
            score = 0.0
            for token in query_tokens:
                if token not in present:
                    continue
                inverse_frequency = math.log((total + 1) / (document_frequency[token] + 0.5)) + 1
                token_weight = 1.8 if len(token) > 1 else 0.45
                score += inverse_frequency * token_weight * (1 + math.log(counter[token]))
            haystack = "".join(
                f"{row.get('title') or ''}{row.get('excerpt') or ''}".casefold().split()
            )
            if normalized_query and normalized_query in haystack:
                score += 8.0
            if score > 0:
                scored.append((score, row))
        scored.sort(key=lambda item: (-item[0], str(item[1].get("chunk_id") or "")))

        results = []
        for score, row in scored[: max(1, min(5, int(limit)))]:
            results.append(
                {
                    "document_id": row.get("document_id"),
                    "dataset_id": row.get("dataset_id"),
                    "title": row.get("title"),
                    "version": row.get("version"),
                    "status_note": row.get("status_note"),
                    "section": row.get("section"),
                    "page_number": row.get("page_number"),
                    "chunk_id": row.get("chunk_id"),
                    "excerpt": row.get("excerpt"),
                    "score": round(score, 6),
                }
            )
        return results
