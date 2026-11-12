"""Controlled document-body reader contract. Not a download or enumeration port.

The only identity this contract carries is the *logical* document id (and,
optionally, the immutable technical version id the client was already shown).
Physical RAGFlow dataset/document ids, native chunk ids, paths, tokens and
upstream addresses are never accepted here and never returned.

``version_id`` is optional because the existing citation/search/catalog DTOs
only carry ``document_id`` plus the business version. When it is omitted the
server resolves the one current published binding of that logical document in
the same authorization snapshot. When it is supplied it must equal that current
version exactly; an older version is refused, never silently upgraded.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from .errors import KnowledgeError

# Fixed page/search bounds (blocks, codepoints, pages, matches).
PAGE_SIZE = 8
MAX_PAGE = 1024
MAX_BLOCK_CODEPOINTS = 4000
MAX_PAGE_CODEPOINTS = 20000
MAX_TOC_ENTRIES = 40
TOC_SCAN_PAGES = 16
MAX_SEARCH_QUERY_CODEPOINTS = 120
MAX_SEARCH_LIMIT = 20
MAX_SEARCH_PAGES = 16
MAX_SEARCH_BLOCKS = MAX_SEARCH_PAGES * PAGE_SIZE

BODY_ORIGIN = "INDEXED_CHUNKS"
PAGE_NUMBERING = "UNAVAILABLE"
TOC_SOURCE = "ORIGINAL_HEADING_LINES"
DISCLOSURE = "正文来自已授权当前版本的索引文本（安全净化派生），不是原件下载；页码未核验。"
BODY_READ_SENTINEL = "CATALOG_BODY_READ"

# Enumerated, non-sensitive failure reasons the client may translate.
READ_STATES = ("NOT_AUTHORIZED", "WITHDRAWN", "NOT_PUBLISHED", "VERSION_STALE",
               "VERSION_AMBIGUOUS")

_DOCUMENT_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,119}")
_VERSION_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


@dataclass(frozen=True)
class DocumentReadRequest:
    document_id: str
    version_id: str | None = None

    def to_wire(self):
        value = {"document_id": self.document_id}
        if self.version_id is not None:
            value["version_id"] = self.version_id
        return value


def normalize_document_read(raw) -> DocumentReadRequest:
    if not isinstance(raw, dict) or set(raw) not in (
            {"document_id"}, {"document_id", "version_id"}):
        raise KnowledgeError("INVALID_REQUEST")
    document = raw["document_id"]
    version = raw.get("version_id")
    if not isinstance(document, str) or not _DOCUMENT_ID.fullmatch(document):
        raise KnowledgeError("INVALID_REQUEST")
    if "version_id" in raw and (not isinstance(version, str)
                                or not _VERSION_ID.fullmatch(version)):
        raise KnowledgeError("INVALID_REQUEST")
    return DocumentReadRequest(document, version)


def document_read_request_from_wire(value) -> DocumentReadRequest:
    return normalize_document_read(value)


def normalize_page(value) -> int:
    if type(value) is not int or not 1 <= value <= MAX_PAGE:
        raise KnowledgeError("INVALID_REQUEST")
    return value


def normalize_search_query(value) -> str:
    if not isinstance(value, str):
        raise KnowledgeError("INVALID_REQUEST")
    value = value.strip()
    if (not value or len(value) > MAX_SEARCH_QUERY_CODEPOINTS
            or _CONTROL.search(value) or "\r" in value or "\n" in value):
        raise KnowledgeError("INVALID_REQUEST")
    # Search text is employee input, not document text: reject hidden channels
    # (URLs, markup, encoded traversal) exactly like the other public strings.
    from .public_strings import safe_string
    try:
        safe_string(value, MAX_SEARCH_QUERY_CODEPOINTS)
    except KnowledgeError:
        raise KnowledgeError("INVALID_REQUEST") from None
    return unicodedata.normalize("NFKC", value)


def normalize_search_limit(value) -> int:
    if type(value) is not int or not 1 <= value <= MAX_SEARCH_LIMIT:
        raise KnowledgeError("INVALID_REQUEST")
    return value
