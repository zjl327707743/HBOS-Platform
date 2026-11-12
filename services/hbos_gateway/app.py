"""Portable HBOS retrieval contract; configuration and index remain private.

This independent adapter does not copy or alter an Owner's private service.
It runs the existing approved local index without importing or rebuilding it.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import stat
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from hb_knowledge_app.hb_knowledge.local_index import LocalIndex

VERSION = "1.2.0"
app = FastAPI(title="HBOS Portable Gateway", version=VERSION, docs_url=None, redoc_url=None)


def protected_file(name: str, maximum: int) -> str:
    path = Path(os.environ.get(name, ""))
    metadata = path.lstat()
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_mode & 0o077 or metadata.st_uid != os.geteuid() or not 0 < metadata.st_size <= maximum:
        raise ValueError("protected file permissions invalid")
    return path.read_text(encoding="utf-8").strip()


class Context(BaseModel):
    equipment_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    asset_id: Optional[str] = Field(default=None, max_length=200)
    component_id: Optional[str] = Field(default=None, max_length=200)


class Search(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    client_id: str = Field(min_length=1, max_length=120)
    subject: str = Field(min_length=1, max_length=320)
    policy_revision: str = Field(min_length=1, max_length=120)
    dataset_ids: list[str] = Field(max_length=200)
    document_ids: list[str] = Field(max_length=200)
    limit: int = Field(default=5, ge=1, le=5)
    request_id: str = Field(min_length=1, max_length=128)
    context: Optional[Context] = None


def search_local(payload: Search, policy: dict, index: LocalIndex) -> dict:
    subject = payload.subject.strip()
    if subject.casefold() in {str(s).casefold() for s in policy.get("denied_subjects", [])} or subject.casefold() == "guest":
        raise HTTPException(403, detail={"code": "FORBIDDEN_SUBJECT"})
    grant = policy.get("subjects", {}).get(subject)
    if grant is None and subject.casefold() != "administrator":
        grant = policy.get("default_internal")
    if not isinstance(grant, dict) or not grant.get("enabled") or "knowledge.search" not in grant.get("capabilities", []):
        raise HTTPException(403, detail={"code": "FORBIDDEN_SUBJECT"})
    if payload.policy_revision != grant.get("policy_revision"):
        raise HTTPException(409, detail={"code": "POLICY_STALE"})
    datasets, documents = set(payload.dataset_ids), set(payload.document_ids)
    if not datasets or not documents or not datasets <= set(grant.get("dataset_ids", [])) or not documents <= set(grant.get("document_ids", [])):
        raise HTTPException(403, detail={"code": "FORBIDDEN_SCOPE"})
    if payload.context:
        equipment_docs = set(grant.get("equipment_document_ids", {}).get(payload.context.equipment_id, []))
        if not equipment_docs or not equipment_docs <= set(grant.get("document_ids", [])):
            raise HTTPException(403, detail={"code": "FORBIDDEN_EQUIPMENT"})
        documents &= equipment_docs
        if not documents:
            raise HTTPException(403, detail={"code": "FORBIDDEN_SCOPE"})
    results = index.search(query=payload.query, dataset_ids=tuple(datasets), document_ids=tuple(documents), limit=min(payload.limit, int(grant.get("max_results", 5))))
    safe = []
    for result in results:
        if result.get("document_id") not in documents or result.get("dataset_id") not in datasets:
            raise HTTPException(502, detail={"code": "UPSTREAM_SCOPE_VIOLATION"})
        safe.append({**{k: result.get(k) for k in ["document_id", "dataset_id", "title", "version", "status_note", "section", "page_number", "chunk_id"]}, "excerpt": str(result.get("excerpt") or "")[:500]})
    return {"request_id": payload.request_id, "status": "SUCCESS", "results": safe}


@app.get("/health")
def health():
    try:
        protected_file("HBOS_GATEWAY_TOKEN_FILE", 1024)
        json.loads(protected_file("HBOS_GATEWAY_POLICY_PATH", 128 * 1024))
        LocalIndex.from_file(os.environ.get("HBOS_GATEWAY_LOCAL_INDEX_PATH", ""))
        ready = bool(os.environ.get("HBOS_GATEWAY_CLIENT_ID"))
    except Exception:
        ready = False
    return {"status": "healthy", "service": "hbos-portable-gateway", "version": VERSION, "configured": ready, "retrieval_mode": "local_private_index" if ready else "unconfigured"}


@app.post("/v1/knowledge/search")
def search(payload: Search, authorization: str = Header(default="")):
    try:
        expected = protected_file("HBOS_GATEWAY_TOKEN_FILE", 1024)
        client = os.environ.get("HBOS_GATEWAY_CLIENT_ID", "")
    except Exception:
        raise HTTPException(503, detail={"code": "CONFIG_REQUIRED"}) from None
    scheme, _, token = authorization.partition(" ")
    if not expected or not client or scheme.lower() != "bearer" or not secrets.compare_digest(token, expected) or not secrets.compare_digest(payload.client_id, client):
        raise HTTPException(401, detail={"code": "AUTHENTICATION_FAILED"})
    try:
        policy = json.loads(protected_file("HBOS_GATEWAY_POLICY_PATH", 128 * 1024))
        index = LocalIndex.from_file(os.environ.get("HBOS_GATEWAY_LOCAL_INDEX_PATH", ""))
        return search_local(payload, policy, index)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503, detail={"code": "CONFIG_REQUIRED"}) from None
