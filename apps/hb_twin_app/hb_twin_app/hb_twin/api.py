from __future__ import annotations

import hashlib
import secrets
import time
from typing import Callable

import frappe

from hb_twin_app.hb_twin.assets import load_asset, load_component_mapping
from hb_twin_app.hb_twin.errors import TwinError, error_payload
from hb_twin_app.hb_twin.policy import VIEW_CAPABILITY, load_current_policy
from hb_twin_app.hb_twin import catalog as bundles


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
    if code in {"FORBIDDEN", "MEMBERS_PENDING"}:
        return 403
    if code in {"ASSET_REVISION_MISMATCH", "ASSET_INTEGRITY_FAILED", "PROCESS_INCOMPATIBLE"}:
        return 409
    if code in {"ASSET_UNAVAILABLE"}:
        return 404
    if code in {"INVALID_REQUEST", "ASSET_INVALID", "MAPPING_INVALID"}:
        return 400
    return 503


def _bundle(entry_id: str, expected_model_sha256: str | None = None,
            expected_mapping_revision: str | None = None,
            expected_process_revision: str | None = None) -> bundles.Bundle:
    started = time.perf_counter()
    bundle = bundles.load_bundle(
        _asset_root(), entry_id, load_current_policy(),
        expected_model_sha256=expected_model_sha256,
        expected_mapping_revision=expected_mapping_revision,
        expected_process_revision=expected_process_revision,
    )
    frappe.local.response_headers["Server-Timing"] = f"twin_integrity;dur={(time.perf_counter()-started)*1000:.2f}"
    return bundle


def _run_v1(action: Callable[[], dict[str, object]]) -> dict[str, object]:
    result = _run(action)
    # Preserve the existing JSON RPC error envelope so the shared Portal client
    # retains domain codes. Binary responses use HTTP status codes separately.
    if not result["ok"] and result["error"]["code"] in {"FORBIDDEN", "MEMBERS_PENDING"}:
        frappe.local.response["http_status_code"] = 403
    return result


@frappe.whitelist(methods=["GET"])
def get_catalog() -> dict[str, object]:
    return _run_v1(lambda: bundles.catalog(_asset_root(), load_current_policy()))


@frappe.whitelist(methods=["GET"])
def get_entry_manifest(entry_id: str, expected_model_sha256: str | None = None) -> dict[str, object]:
    return _run_v1(lambda: _bundle(entry_id, expected_model_sha256).browser_manifest())


@frappe.whitelist(methods=["GET"])
def get_entry_parts(entry_id: str, expected_model_sha256: str, expected_mapping_revision: str) -> dict[str, object]:
    return _run_v1(lambda: dict(_bundle(entry_id, expected_model_sha256, expected_mapping_revision).resource("parts")))


@frappe.whitelist(methods=["GET"])
def get_entry_mapping(entry_id: str, equipment_id: str, asset_id: str,
                      expected_model_sha256: str, expected_mapping_revision: str) -> dict[str, object]:
    return _run_v1(lambda: bundles.component_mapping(
        _bundle(entry_id, expected_model_sha256, expected_mapping_revision), asset_id, equipment_id))


@frappe.whitelist(methods=["GET"])
def get_entry_process(entry_id: str, expected_model_sha256: str, expected_mapping_revision: str,
                      expected_process_revision: str) -> dict[str, object]:
    return _run_v1(lambda: dict(bundles.process_config(_bundle(
        entry_id, expected_model_sha256, expected_mapping_revision, expected_process_revision))))


@frappe.whitelist(methods=["GET"])
def get_entry_model(entry_id: str, expected_model_sha256: str, expected_mapping_revision: str) -> None:
    _private_no_store()
    try:
        bundle = _bundle(entry_id, expected_model_sha256, expected_mapping_revision)
        # Recheck the bytes being sent to close the hash/read window. Private
        # development bundles are immutable, but a changed file still fails shut.
        content = bundle.model_path.read_bytes()
        if hashlib.sha256(content).hexdigest() != expected_model_sha256:
            raise TwinError("ASSET_INTEGRITY_FAILED", "设备模型完整性校验失败。")
        frappe.local.response.update({"filename":f"{entry_id}.glb", "filecontent":content,
                                      "type":"download", "display_content_as":"inline"})
        frappe.local.response_headers.update({"Content-Type":"model/gltf-binary", "Content-Length":str(len(content)),
                                              "Content-Security-Policy":"default-src 'none'; sandbox"})
    except TwinError as exc:
        frappe.local.response.update({"http_status_code":_model_error_status(exc.code), "type":"json", **error_payload(exc)})
    except Exception:
        frappe.local.response.update({"http_status_code":503, "type":"json",
            **error_payload(TwinError("SERVICE_ERROR", "设备服务暂时不可用。", retryable=True))})


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
            message="Unexpected Twin service failure. Private resource paths and request details are withheld.",
        )
        return error_payload(
            TwinError("SERVICE_ERROR", "设备服务暂时不可用。", retryable=True)
        )


@frappe.whitelist(methods=["GET"])
def get_status() -> dict[str, object]:
    def _load() -> dict[str, object]:
        policy = load_current_policy()
        can_enter = policy.can_enter and VIEW_CAPABILITY in policy.capabilities
        return {
            "can_enter": can_enter,
            "equipment_ids": list(policy.equipment_ids) if can_enter else [],
            "policy_revision": policy.policy_revision if can_enter else None,
            "asset_root_configured": bool(str(frappe.conf.get("hbos_twin_asset_root") or "").strip()),
        }

    return _run(_load)


@frappe.whitelist(methods=["GET"])
def get_manifest(equipment_id: str = "M607B") -> dict[str, object]:
    def _load() -> dict[str, object]:
        normalized = str(equipment_id or "").strip()
        if bundles.enabled(_asset_root()):
            manifest = _bundle(normalized).browser_manifest()
            return {**manifest, "equipment_id":normalized, "site_identity":normalized,
                    "viewer_revision":"twin-v1-a1", "fit_disclaimer":"展示拟合·非实测", "connection_state":"not_connected"}
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
        if bundles.enabled(_asset_root()):
            return bundles.component_mapping(_bundle(normalized_equipment), normalized_asset, normalized_equipment)
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
        if bundles.enabled(_asset_root()):
            bundle = _bundle(normalized)
            if revision and revision not in {bundle.manifest["model"]["sha256"], bundle.manifest["model"]["sha256"][:16]}:
                raise TwinError("ASSET_REVISION_MISMATCH", "设备模型版本已变更，请刷新页面。")
            return get_entry_model(normalized, bundle.manifest["model"]["sha256"], bundle.manifest["mapping_revision"])
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
            message="Unexpected Twin model failure. Private resource paths and request details are withheld.",
        )
        frappe.local.response["http_status_code"] = 503
        frappe.local.response["type"] = "json"
        frappe.local.response.update(
            error_payload(TwinError("SERVICE_ERROR", "设备服务暂时不可用。", retryable=True))
        )
        return None
