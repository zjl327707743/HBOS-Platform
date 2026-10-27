"""Server-owned immutable source mappings. No client paths or remote fetches."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import unicodedata
from urllib.parse import quote

from .errors import KnowledgeError

MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_RANGE_BYTES = 8 * 1024 * 1024
MAX_MANIFEST_BYTES = 16 * 1024 * 1024
HEX64 = re.compile(r'[a-f0-9]{64}')
_RANGE = re.compile(r'bytes=(\d*)-(\d*)')


def unavailable(reason):
    return KnowledgeError('DOCUMENT_DELIVERY_UNAVAILABLE', state=reason)


def safe_filename(value):
    if not isinstance(value, str):
        raise unavailable('ASSET_UNAVAILABLE')
    value = unicodedata.normalize('NFC', value)
    value = ''.join(c for c in value if not unicodedata.category(c).startswith('C'))
    value = value.replace('/', '_').replace('\\', '_').strip(' .')[:180]
    if not value or value in {'.', '..'}:
        return 'document.bin'
    return value


def disposition(filename, inline=False):
    # The ASCII fallback is deliberately fixed; UTF-8 names use RFC 5987.
    return ('inline' if inline else 'attachment') + "; filename=\"document\"; filename*=UTF-8''" + quote(safe_filename(filename), safe='')


def byte_range(value, size):
    if value is None:
        return 0, size - 1, 200
    if not isinstance(value, str) or len(value) > 100:
        raise KnowledgeError('DOCUMENT_RANGE_NOT_SATISFIABLE')
    match = _RANGE.fullmatch(value)
    if not match or not any(match.groups()):
        raise KnowledgeError('DOCUMENT_RANGE_NOT_SATISFIABLE')
    first, last = match.groups()
    if first:
        start = int(first)
        end = min(int(last) if last else size - 1, size - 1)
    else:
        suffix = int(last)
        if suffix < 1:
            raise KnowledgeError('DOCUMENT_RANGE_NOT_SATISFIABLE')
        start, end = max(0, size - suffix), size - 1
    if (size < 1 or start >= size or end < start
            or end - start + 1 > MAX_RANGE_BYTES):
        raise KnowledgeError('DOCUMENT_RANGE_NOT_SATISFIABLE')
    return start, end, 206


@dataclass(frozen=True)
class Asset:
    path: Path
    sha256: str
    filename: str
    content_type: str
    kind: str
    source_sha256: str

    def read(self, range_header=None):
        """One O_NOFOLLOW handle, bounded bytes, full hash before any response.

        A range does not skip source verification. File replacement during the
        read is refused, and no bytes are returned until the entire digest and
        stable file metadata have been checked.
        """
        try:
            fd = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(fd, 'rb') as stream:
                before = os.fstat(stream.fileno())
                if not stat.S_ISREG(before.st_mode) or before.st_size < 1:
                    raise unavailable('ASSET_UNAVAILABLE')
                if before.st_size > MAX_FILE_BYTES:
                    raise unavailable('ASSET_TOO_LARGE')
                start, end, status = byte_range(range_header, before.st_size)
                hasher, output, offset = hashlib.sha256(), bytearray(), 0
                first = b''
                while True:
                    block = stream.read(1024 * 1024)
                    if not block:
                        break
                    if offset == 0:
                        first = block[:8]
                    if offset + len(block) > MAX_FILE_BYTES:
                        raise unavailable('ASSET_TOO_LARGE')
                    hasher.update(block)
                    left, right = max(start - offset, 0), min(end + 1 - offset, len(block))
                    if left < right:
                        output.extend(block[left:right])
                    offset += len(block)
                after = os.fstat(stream.fileno())
                identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
                if (identity(before) != identity(after) or offset != before.st_size
                        or hasher.hexdigest() != self.sha256):
                    raise unavailable('ASSET_HASH_MISMATCH')
                if self.content_type == 'application/pdf' and not first.startswith(b'%PDF-'):
                    raise unavailable('ASSET_HASH_MISMATCH')
                return bytes(output), status, start, end, before.st_size
        except KnowledgeError:
            raise
        except (OSError, ValueError):
            raise unavailable('ASSET_UNAVAILABLE') from None


class LocalDocumentAssets:
    """Mapping metadata is trusted configuration, never an authorization allow."""
    def __init__(self, manifest_path, roots, source_hash):
        self.manifest_path = Path(manifest_path) if manifest_path else None
        self.roots = {key: Path(path) for key, path in (roots or {}).items()}
        self.source_hash = source_hash

    def _entry(self, binding):
        try:
            if not self.manifest_path or self.manifest_path.stat().st_size > MAX_MANIFEST_BYTES:
                raise unavailable('ASSET_UNAVAILABLE')
            value = json.loads(self.manifest_path.read_text())
            if value.get('schema') != 'hbos-document-assets-v1':
                raise unavailable('ASSET_UNAVAILABLE')
            entry = value['by_version'][binding.version_id]
            expected = self.source_hash(binding)
            if (not isinstance(expected, str) or not HEX64.fullmatch(expected)
                    or entry['document_id'] != binding.canonical_document_id
                    or entry['source_sha256'] != expected):
                raise unavailable('ASSET_HASH_MISMATCH')
            return entry, expected
        except KnowledgeError:
            raise
        except (OSError, ValueError, KeyError, TypeError):
            raise unavailable('ASSET_UNAVAILABLE') from None

    def _path(self, record):
        try:
            raw = record['relative_path']
            if not isinstance(raw, str) or not raw or '\\' in raw or '\x00' in raw:
                raise ValueError()
            rel = PurePosixPath(raw)
            if rel.is_absolute() or any(p in {'.', '..'} for p in raw.split('/')):
                raise ValueError()
            root = self.roots[record['root_id']].resolve(strict=True)
            path = root.joinpath(*rel.parts)
            resolved = path.resolve(strict=True)
            # No symlink at any level, no external roots, no URLs or devices.
            if resolved != path or not resolved.is_relative_to(root):
                raise ValueError()
            return path
        except (KeyError, TypeError, ValueError, OSError):
            raise unavailable('ASSET_UNAVAILABLE') from None

    def resolve(self, binding, purpose):
        entry, expected = self._entry(binding)
        # The original mapping is required even for a derived preview. Source
        # verification cannot be replaced by a digest asserted by a converter.
        source = entry['original']
        original = Asset(self._path(source), expected, safe_filename(source['filename']),
                         'application/octet-stream', 'ORIGINAL_FILE', expected)
        if purpose == 'download':
            return original, original
        preview = entry.get('preview')
        if not isinstance(preview, dict) or preview.get('kind') not in {'ORIGINAL_PDF', 'DERIVED_PDF'}:
            raise unavailable('PREVIEW_UNAVAILABLE')
        sha = preview.get('sha256')
        if not isinstance(sha, str) or not HEX64.fullmatch(sha):
            raise unavailable('ASSET_UNAVAILABLE')
        if preview['kind'] == 'ORIGINAL_PDF' and (sha != expected or self._path(preview) != original.path):
            raise unavailable('ASSET_HASH_MISMATCH')
        asset = Asset(self._path(preview), sha, safe_filename(preview['filename']),
                      'application/pdf', preview['kind'], expected)
        return asset, original


def current_source_hash(binding):
    """Fresh committed HBOS version metadata, independent of the asset map."""
    from .frappe_authority import committed_view, rows
    with committed_view() as cur:
        found = rows(cur, 'SELECT v.version_json FROM `tabHBOS Knowledge Version` v '
                     'JOIN `tabHBOS Knowledge Document` d ON d.name=v.canonical_document_id '
                     'WHERE v.name=%s AND d.name=%s AND d.current_version=v.name '
                     'AND d.withdrawn=0 AND d.ingestion_status=%s',
                     (binding.version_id, binding.canonical_document_id, 'published'))
    try:
        if len(found) != 1:
            raise ValueError()
        return json.loads(found[0]['version_json'])['sha256']
    except (ValueError, KeyError, TypeError):
        raise unavailable('ASSET_UNAVAILABLE') from None
