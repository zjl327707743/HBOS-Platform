"""Shared public string projection. Validation cannot confer authorization."""
from __future__ import annotations
import html
import re
import unicodedata
from urllib.parse import unquote
from .errors import KnowledgeError

DANGER=re.compile(r"(?i)(?:[a-z][a-z0-9+.-]*://|www\.|(?:javascript|data|mailto):|"
    r"(?:^|[\s\"'(])/(?:[^\s<>]+)|[a-z]:[\\/]|(?:\.\.[\\/])|"
    r"%2f|%5c|\\u[0-9a-f]{4}|<\s*(?:/?[a-z!])[^>]*>|(?:api.?key|token|password|secret)\s*[:=]\s*\S+)")

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

