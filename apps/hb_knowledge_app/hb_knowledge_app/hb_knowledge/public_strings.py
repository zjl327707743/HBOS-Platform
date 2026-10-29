"""Shared public string projection. Validation cannot confer authorization."""
from __future__ import annotations
import html
import re
import unicodedata
from urllib.parse import unquote
from .errors import KnowledgeError

DANGER=re.compile(r"(?i)(?:[a-z][a-z0-9+.-]*://|www\.|(?:javascript|data|mailto):|"
    r"(?:^|[\s\"'(])/(?=[^\s<>，。；、（）？！“”]*(?:[A-Za-z0-9._~%-]|/))(?:[^\s<>]+)|[a-z]:[\\/]|(?:\.\.[\\/])|"
    r"%2f|%5c|\\u[0-9a-f]{4}|<\s*(?:/?[a-z!])[^>]*>|(?:api.?key|token|password|secret)\s*[:=]\s*\S+)")

# Source text is the document's own content, not model output. A regulation that
# cites a standard's URL, or a table that spells a path, is still the document.
# The injection defence below targets what a MODEL writes into an answer, so for
# source excerpts the link/path clauses are dropped while the clauses that catch
# credentials, markup and encoded traversal are kept.
DANGER_SOURCE=re.compile(r"(?i)(?:javascript:|data:|mailto:|\.\.[\\/]|\\\\u[0-9a-f]{4}|"
    r"%2f|%5c|<\s*(?:/?[a-z!])[^>]*>|(?:api.?key|token|password|secret)\s*[:=]\s*\S+)")

PUA=re.compile(r"[\ue000-\uf8ff]")
CONTROL=re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
CID_GLYPH=re.compile(r"/G\d{2,3}\b")


def source_string(value, maximum=None, *, physical_ids=(), nullable=False, strict_glyphs=False):
    """Validate a *source* string.

    ``strict_glyphs=False`` (display): allows the document's own URLs and paths,
    which are rendered as inert text. Identical to ``safe_string`` apart from
    those two clauses, so nothing that could be displayed before is rejected now.

    ``strict_glyphs=True`` (index adapter): additionally refuses private-use /
    CID glyph residue and control characters. That is the signal that the text
    was never really decoded, and it belongs to accepting an index, not to
    rendering an excerpt of it.
    """
    if value is None and nullable:
        return None
    if not isinstance(value,str):
        raise KnowledgeError("UPSTREAM_INVALID_RESULT")
    normalized=unicodedata.normalize("NFKC",value)
    for _ in range(3):
        normalized=html.unescape(unquote(normalized))
    if DANGER_SOURCE.search(normalized) or any(identity and identity in value for identity in physical_ids):
        raise KnowledgeError("UPSTREAM_INVALID_RESULT")
    if strict_glyphs and (PUA.search(value) or CONTROL.search(value) or CID_GLYPH.search(value)):
        raise KnowledgeError("UPSTREAM_INVALID_RESULT")
    if maximum is not None and len(value)>maximum:
        raise KnowledgeError("UPSTREAM_INVALID_RESULT")
    return value


def safe_string(value, maximum=None, *, physical_ids=(), nullable=False):
    if value is None and nullable:
        return None
    if not isinstance(value,str):
        raise KnowledgeError("UPSTREAM_INVALID_RESULT")
    normalized=unicodedata.normalize("NFKC",value)
    for _ in range(3):
        normalized=html.unescape(unquote(normalized))
    if DANGER.search(normalized) or any(identity and identity in value for identity in physical_ids):
        raise KnowledgeError("UPSTREAM_INVALID_RESULT")
    if maximum is not None and len(value)>maximum:
        raise KnowledgeError("UPSTREAM_INVALID_RESULT")
    return value


def source_display_string(value, maximum=None, *, physical_ids=(), nullable=False):
    """Hygiene gate for already-sanitized document *display* text.

    Reader blocks are made inert before they reach this gate: accepted native
    table text is flattened by ``native_text`` and anything rejected there is
    HTML-entity-escaped (``&``/``<``/``>`` only) and returned as ordinary text.
    That escaped text must stay inert, so unlike ``safe_string`` this gate does
    NOT unescape entities in its check - unescaping ``&lt;product&gt;`` would
    turn inert display text back into markup and reject exactly the block the
    controlled fallback exists for. It keeps the same credential, encoded
    traversal and markup gate on the text as it will be displayed.
    """
    if value is None and nullable:
        return None
    if not isinstance(value,str):
        raise KnowledgeError("UPSTREAM_INVALID_RESULT")
    normalized=unicodedata.normalize("NFKC",value)
    if DANGER_SOURCE.search(normalized) or any(identity and identity in value for identity in physical_ids):
        raise KnowledgeError("UPSTREAM_INVALID_RESULT")
    if CONTROL.search(normalized):
        raise KnowledgeError("UPSTREAM_INVALID_RESULT")
    if maximum is not None and len(value)>maximum:
        raise KnowledgeError("UPSTREAM_INVALID_RESULT")
    return value
