"""R1.1 shared public/transport structure. Structure is never authority."""
from __future__ import annotations
import json
import re
import html
from urllib.parse import unquote
from pathlib import Path
from dataclasses import dataclass
from jsonschema import Draft202012Validator, FormatChecker
from .errors import KnowledgeError

SCHEMA_ROOT = Path(__file__).parent / "schemas"
CONTRACT_VERSION = "k1c1-r1.1"
INSUFFICIENT_TEXT = "当前授权资料不足以形成回答。"
REFERENCE_TEXT = "仅供参考，请核对获准依据。"
SYNTHETIC_TEXT = "SYNTHETIC_ONLY：仅供隔离测试。"
CONTEXT_KEYS = ("equipment_id", "asset_id", "component_id")

def validate_structure(name: str, value, *, plan: bool = False):
    file = "execution_plan.schema.json" if plan else "api.schema.json"
    schema = json.loads((SCHEMA_ROOT / file).read_text())
    if not plan:
        schema = {**schema, "$ref": "#/$defs/" + name}
        schema.pop("oneOf", None)
    if next(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(value), None):
        raise KnowledgeError("INVALID_REQUEST")
    return value

@dataclass(frozen=True)
class SearchRequest:
    query: str
    limit: int = 5
    space_ids: tuple[str, ...] | None = None
    context: tuple[tuple[str, str], ...] = ()

    def to_wire(self):
        value = {"query": self.query, "limit": self.limit}
        if self.space_ids is not None:
            value["space_ids"] = list(self.space_ids)
        if self.context:
            value["context"] = dict(self.context)
        return value

def normalize_search(raw: dict, *, legacy: bool = False) -> SearchRequest:
    if not isinstance(raw, dict):
        raise KnowledgeError("INVALID_REQUEST")
    allowed = {"query", "limit", "space_ids", "context"} | (set(CONTEXT_KEYS) if legacy else set())
    if set(raw) - allowed:
        raise KnowledgeError("INVALID_REQUEST")
    raw = dict(raw)
    flat = {key: raw.pop(key) for key in CONTEXT_KEYS if key in raw}
    if flat and "context" in raw:
        raise KnowledgeError("INVALID_REQUEST")
    if flat:
        raw["context"] = flat
    if not isinstance(raw.get("query"), str):
        raise KnowledgeError("INVALID_REQUEST")
    raw["query"] = raw["query"].strip()
    if raw.get("space_ids") == []:
        raise KnowledgeError("EMPTY_SCOPE")
    if legacy and isinstance(raw.get("limit"), str) and re.fullmatch(r"[1-5]", raw["limit"]):
        raw["limit"] = int(raw["limit"])
    if type(raw.get("limit", 5)) is not int:
        raise KnowledgeError("INVALID_REQUEST")
    if "context" in raw:
        context = raw["context"]
        if not isinstance(context, dict) or any(not isinstance(v, str) for v in context.values()):
            raise KnowledgeError("INVALID_REQUEST")
        raw["context"] = {k: v.strip() for k, v in context.items()}
        for value in raw["context"].values():
            decoded=html.unescape(unquote(value))
            if re.search(r"(?i)(?:[a-z][a-z0-9+.-]*://|^[\\/]|[<>]|\.\.[\\/])",decoded):
                raise KnowledgeError("INVALID_REQUEST")
    if "space_ids" in raw:
        ids = raw["space_ids"]
        if not isinstance(ids, list) or any(not isinstance(v, str) or not v.strip() or v != v.strip() for v in ids):
            raise KnowledgeError("INVALID_REQUEST")
    validate_structure("SearchRequest", raw)
    return SearchRequest(raw["query"], raw.get("limit", 5),
                         tuple(raw["space_ids"]) if "space_ids" in raw else None,
                         tuple(sorted(raw.get("context", {}).items())))

def normalize_evidence(raw: dict):
    validate_structure("EvidenceRequest", raw)
    if not raw["evidence_id"].strip():
        raise KnowledgeError("INVALID_REQUEST")
    return raw["evidence_id"]

def validate_ask_data(value: dict, *, environment: str):
    validate_structure("AskData", value)
    triple = (value["mode"], value["answer_status"], value["answerable"])
    admitted = {
        ("authorized_generation", "ANSWERED", True),
        ("authorized_generation", "INSUFFICIENT_EVIDENCE", False),
        ("reference_only", "REFERENCE_ONLY", False),
        ("synthetic_test", "SYNTHETIC_TEST", False),
    }
    if triple not in admitted or environment not in {"production", "synthetic"}:
        raise KnowledgeError("INVALID_REQUEST")
    citations = value["citations"]
    if len({c["citation_label"] for c in citations}) != len(citations):
        raise KnowledgeError("INVALID_REQUEST")
    if triple[1] == "REFERENCE_ONLY" and (value["answer"] != REFERENCE_TEXT or not citations):
        raise KnowledgeError("INVALID_REQUEST")
    if triple[1] == "SYNTHETIC_TEST" and (environment != "synthetic" or value["answer"] != SYNTHETIC_TEXT or citations):
        raise KnowledgeError("INVALID_REQUEST")
    if environment == "production" and any(c["source_type"] == "SYNTHETIC_TEST" for c in citations):
        raise KnowledgeError("INVALID_REQUEST")
    return value
