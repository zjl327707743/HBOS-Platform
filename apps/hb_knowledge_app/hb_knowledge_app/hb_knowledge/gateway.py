from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from hb_knowledge_app.hb_knowledge.errors import KnowledgeError
from hb_knowledge_app.hb_knowledge.policy import SubjectPolicy


MAX_EXCERPT_CODEPOINTS = 500


@dataclass(frozen=True)
class EvidenceRecord:
    document_id: str
    title: str | None
    version: str | None
    status_note: str | None
    section: str | None
    page_number: int | None
    excerpt: str
    chunk_id: str | None
    dataset_id: str | None


def _trim_excerpt(value: object) -> str:
    text = str(value or "").strip()
    return text[:MAX_EXCERPT_CODEPOINTS]


def _trim_metadata(value: object, maximum: int = 240) -> str | None:
    text = " ".join(str(value or "").split()).strip()
    return text[:maximum] or None


def _page_number(value: object) -> int | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if 1 <= number <= 100_000 else None


def _normalize_results(payload: object) -> list[Mapping[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, Mapping)]
    if not isinstance(payload, Mapping):
        raise KnowledgeError(
            "UPSTREAM_INVALID",
            "知识服务返回了无效响应。",
            retryable=True,
        )
    value = payload.get("results")
    if value is None and isinstance(payload.get("data"), Mapping):
        value = payload["data"].get("results")
    if not isinstance(value, list):
        raise KnowledgeError(
            "UPSTREAM_INVALID",
            "知识服务返回了无效响应。",
            retryable=True,
        )
    return [item for item in value if isinstance(item, Mapping)]


def filter_authorized_results(
    payload: object,
    policy: SubjectPolicy,
    *,
    limit: int,
) -> list[EvidenceRecord]:
    allowed_documents = set(policy.document_ids)
    allowed_datasets = set(policy.dataset_ids)
    output: list[EvidenceRecord] = []

    for item in _normalize_results(payload):
        document_id = str(item.get("document_id") or "").strip()
        dataset_id = str(item.get("dataset_id") or "").strip() or None
        if not document_id:
            continue
        if document_id not in allowed_documents:
            raise KnowledgeError(
                "UPSTREAM_SCOPE_VIOLATION",
                "知识服务权限校验失败。",
            )
        if not dataset_id or dataset_id not in allowed_datasets:
            raise KnowledgeError(
                "UPSTREAM_SCOPE_VIOLATION",
                "知识服务权限校验失败。",
            )
        excerpt = _trim_excerpt(item.get("excerpt") or item.get("content"))
        if not excerpt:
            continue
        output.append(
            EvidenceRecord(
                document_id=document_id,
                title=_trim_metadata(item.get("title")),
                version=str(item.get("version") or "").strip() or None,
                status_note=_trim_metadata(item.get("status_note"), maximum=320),
                section=str(item.get("section") or item.get("section_label") or "").strip() or None,
                page_number=_page_number(item.get("page_number")),
                excerpt=excerpt,
                chunk_id=str(item.get("chunk_id") or "").strip() or None,
                dataset_id=dataset_id,
            )
        )
        if len(output) >= limit:
            break

    return output


class GatewayClient:
    def __init__(
        self,
        *,
        endpoint: str,
        token: str,
        client_id: str,
        post: Callable[..., Any] | None = None,
        timeout_seconds: float = 12.0,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.token = token
        self.client_id = client_id
        self.timeout_seconds = timeout_seconds
        self._post = post

    @property
    def configured(self) -> bool:
        return bool(self.endpoint.startswith(("http://", "https://")) and self.token and self.client_id)

    def search(
        self,
        *,
        query: str,
        policy: SubjectPolicy,
        limit: int,
        request_id: str,
        context: Mapping[str, str] | None = None,
    ) -> list[EvidenceRecord]:
        policy.require_search()
        if not self.configured:
            raise KnowledgeError(
                "CONFIG_REQUIRED",
                "知识服务尚未完成本地安全配置。",
            )

        # Only this trusted backend constructs subject and retrieval filters.
        body = {
            "query": query,
            "client_id": self.client_id,
            "subject": policy.subject,
            "policy_revision": policy.policy_revision,
            "dataset_ids": list(policy.dataset_ids),
            "document_ids": list(policy.document_ids),
            "limit": limit,
            "request_id": request_id,
        }
        if context:
            body["context"] = dict(context)
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "X-HBOS-Policy-Revision": policy.policy_revision,
            "X-Request-ID": request_id,
        }

        try:
            if self._post is None:
                import requests

                response = requests.post(
                    f"{self.endpoint}/v1/knowledge/search",
                    json=body,
                    headers=headers,
                    timeout=self.timeout_seconds,
                )
            else:
                response = self._post(
                    f"{self.endpoint}/v1/knowledge/search",
                    json=body,
                    headers=headers,
                    timeout=self.timeout_seconds,
                )
            response.raise_for_status()
            payload = response.json()
        except KnowledgeError:
            raise
        except Exception as exc:
            raise KnowledgeError(
                "UPSTREAM_UNAVAILABLE",
                "知识服务暂时不可用，请稍后重试。",
                retryable=True,
            ) from exc

        return filter_authorized_results(payload, policy, limit=limit)


def load_gateway_client() -> GatewayClient:
    import frappe

    token_path = Path(str(frappe.get_site_path("private", "hbos_knowledge_gateway_token")))
    token = ""
    try:
        metadata = token_path.lstat()
        if (
            stat.S_ISREG(metadata.st_mode)
            and not metadata.st_mode & 0o077
            and (not hasattr(os, "geteuid") or metadata.st_uid == os.geteuid())
            and 0 < metadata.st_size <= 1024
        ):
            candidate = token_path.read_text(encoding="utf-8").strip()
            if candidate and not any(character.isspace() for character in candidate):
                token = candidate
    except FileNotFoundError:
        pass
    if not token and str(frappe.conf.get("hbos_knowledge_allow_config_token") or "").lower() in {
        "1",
        "true",
        "yes",
    }:
        token = str(frappe.conf.get("hbos_knowledge_gateway_token") or "")
    return GatewayClient(
        endpoint=str(frappe.conf.get("hbos_knowledge_gateway_url") or ""),
        token=token,
        client_id=str(frappe.conf.get("hbos_knowledge_gateway_client_id") or ""),
        timeout_seconds=float(frappe.conf.get("hbos_knowledge_gateway_timeout") or 12),
    )
