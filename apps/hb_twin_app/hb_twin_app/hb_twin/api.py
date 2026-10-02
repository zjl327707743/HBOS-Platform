from __future__ import annotations

import hashlib
import secrets
from typing import Callable

import frappe

from hb_twin_app.hb_twin.assets import load_asset, load_component_mapping
from hb_twin_app.hb_twin.errors import TwinError, error_payload
from hb_twin_app.hb_twin.policy import load_current_policy


def _private_no_store() -> None:
    frappe.local.response_headers["Cache-Control"] = "private, no-store, max-age=0"
    frappe.local.response_headers["Pragma"] = "no-cache"
    frappe.local.response_headers["X-Content-Type-Options"] = "nosniff"


def _asset_root() -> str:
    value = str(frappe.conf.get("hbos_twin_asset_root") or "").strip()
    if not value:
        raise TwinError("CONFIG_REQUIRED", "私有设备资产目录尚未配置。")
    return value


def _subject_fingerprint(subject: str) -> str:
    """Return a stable audit key without writing the account identifier to logs."""
    return hashlib.sha256(subject.encode("utf-8")).hexdigest()[:16]


def _model_error_status(code: str) -> int:
    if code == "FORBIDDEN":
        return 403
    if code in {"ASSET_REVISION_MISMATCH", "ASSET_INTEGRITY_FAILED"}:
        return 409
    if code in {"ASSET_UNAVAILABLE"}:
        return 404
    if code in {"INVALID_REQUEST", "ASSET_INVALID", "MAPPING_INVALID"}:
        return 400
    return 503


def _run(action: Callable[[], dict[str, object]]) -> dict[str, object]:
    _private_no_store()
    try:
        return {"ok": True, "data": action()}
    except TwinError as exc:
        return error_payload(exc)
    except Exception:
        request_id = secrets.token_hex(8)
        frappe.log_error(
            title=f"HBOS Twin API error [{request_id}]",
            message=frappe.get_traceback(),
        )
        return error_payload(
            TwinError("SERVICE_ERROR", "设备服务暂时不可用。", retryable=True)
        )


@frappe.whitelist(methods=["GET"])
def get_status() -> dict[str, object]:
    def _load() -> dict[str, object]:
        policy = load_current_policy()
        return {
            "can_enter": policy.can_enter,
            "equipment_ids": list(policy.equipment_ids) if policy.can_enter else [],
            "policy_revision": policy.policy_revision if policy.can_enter else None,
            "asset_root_configured": bool(str(frappe.conf.get("hbos_twin_asset_root") or "").strip()),
        }

    return _run(_load)


@frappe.whitelist(methods=["GET"])
def get_manifest(equipment_id: str = "M607B") -> dict[str, object]:
    def _load() -> dict[str, object]:
        normalized = str(equipment_id or "").strip()
        policy = load_current_policy()
        policy.require_equipment(normalized)
        asset = load_asset(_asset_root(), normalized)
        return asset.browser_manifest()

    return _run(_load)


@frappe.whitelist(methods=["GET"])
def get_component_mapping(equipment_id: str, asset_id: str) -> dict[str, object]:
    def _load() -> dict[str, object]:
        normalized_equipment = str(equipment_id or "").strip()
        normalized_asset = str(asset_id or "").strip()
        if not normalized_asset or len(normalized_asset) > 200:
            raise TwinError("INVALID_REQUEST", "部件标识无效。")
        policy = load_current_policy()
        policy.require_equipment(normalized_equipment)
        asset = load_asset(_asset_root(), normalized_equipment)
        return load_component_mapping(
            _asset_root(),
            normalized_equipment,
            normalized_asset,
            asset.mapping_revision,
        )

    return _run(_load)


@frappe.whitelist(methods=["GET"])
def get_model(equipment_id: str = "M607B", revision: str | None = None) -> None:
    _private_no_store()
    try:
        normalized = str(equipment_id or "").strip()
        policy = load_current_policy()
        policy.require_equipment(normalized)
        asset = load_asset(_asset_root(), normalized)
        if revision and str(revision) != asset.sha256[:16]:
            raise TwinError("ASSET_REVISION_MISMATCH", "设备模型版本已变更，请刷新页面。")

        frappe.local.response["filename"] = f"{normalized}-{asset.model_revision}.glb"
        frappe.local.response["filecontent"] = asset.model_path.read_bytes()
        frappe.local.response["type"] = "download"
        frappe.local.response["display_content_as"] = "inline"
        frappe.local.response_headers["Content-Type"] = "model/gltf-binary"
        frappe.local.response_headers["Content-Length"] = str(asset.size_bytes)
        frappe.local.response_headers["Content-Security-Policy"] = "default-src 'none'; sandbox"
        frappe.logger("hbos_twin").info(
            {
                "subject_key": _subject_fingerprint(policy.subject),
                "operation": "model_read",
                "equipment_id": normalized,
                "model_revision": asset.model_revision,
                "policy_revision": policy.policy_revision,
            }
        )
        return None
    except TwinError as exc:
        frappe.local.response["http_status_code"] = _model_error_status(exc.code)
        frappe.local.response["type"] = "json"
        frappe.local.response.update(error_payload(exc))
        return None
    except Exception:
        request_id = secrets.token_hex(8)
        frappe.log_error(
            title=f"HBOS Twin model error [{request_id}]",
            message=frappe.get_traceback(),
        )
        frappe.local.response["http_status_code"] = 503
        frappe.local.response["type"] = "json"
        frappe.local.response.update(
            error_payload(TwinError("SERVICE_ERROR", "设备服务暂时不可用。", retryable=True))
        )
        return None
