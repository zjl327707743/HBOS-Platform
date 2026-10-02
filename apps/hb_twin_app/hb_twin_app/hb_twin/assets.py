from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from hb_twin_app.hb_twin.errors import TwinError


MANIFEST_FILENAME = "model_manifest.json"
MAPPING_FILENAME = "component_mappings.json"
SUPPORTED_MANIFEST_SCHEMA = 1
EQUIPMENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


def validate_equipment_id(value: str) -> str:
    normalized = str(value or "").strip()
    if not EQUIPMENT_ID_PATTERN.fullmatch(normalized):
        raise TwinError("INVALID_REQUEST", "设备标识无效。")
    return normalized


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TwinError("ASSET_INVALID", "设备资产清单不可用。") from exc
    if not isinstance(value, Mapping):
        raise TwinError("ASSET_INVALID", "设备资产清单不可用。")
    return value


def _safe_child(root: Path, filename: str) -> Path:
    if not filename or filename != Path(filename).name:
        raise TwinError("ASSET_INVALID", "设备资产路径无效。")
    candidate = root / filename
    if candidate.is_symlink():
        raise TwinError("ASSET_INVALID", "设备资产不允许符号链接。")
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (FileNotFoundError, ValueError) as exc:
        raise TwinError("ASSET_UNAVAILABLE", "设备模型文件不可用。", retryable=True) from exc
    return resolved


@dataclass(frozen=True)
class ModelAsset:
    equipment_id: str
    label: str
    site_identity: str
    model_path: Path
    sha256: str
    size_bytes: int
    viewer_revision: str
    mapping_revision: str
    fit_disclaimer: str
    connection_state: str
    model_revision: str

    def browser_manifest(self) -> dict[str, object]:
        return {
            "equipment_id": self.equipment_id,
            "label": self.label,
            "site_identity": self.site_identity,
            "model_sha256": self.sha256,
            "model_size_bytes": self.size_bytes,
            "model_revision": self.model_revision,
            "viewer_revision": self.viewer_revision,
            "mapping_revision": self.mapping_revision,
            "fit_disclaimer": self.fit_disclaimer,
            "connection_state": self.connection_state,
            "model_url": (
                "/api/method/hb_twin_app.hb_twin.api.get_model"
                f"?equipment_id={self.equipment_id}&revision={self.sha256[:16]}"
            ),
        }


def load_asset(asset_root: str | Path, equipment_id: str) -> ModelAsset:
    equipment_id = validate_equipment_id(equipment_id)
    root = Path(asset_root).expanduser()
    if not root.is_absolute() or not root.is_dir() or root.is_symlink():
        raise TwinError("CONFIG_REQUIRED", "私有设备资产目录尚未配置。")
    root = root.resolve(strict=True)
    equipment_root = _safe_child(root, equipment_id)
    if not equipment_root.is_dir():
        raise TwinError("ASSET_UNAVAILABLE", "设备模型文件不可用。")
    manifest = _read_json(_safe_child(equipment_root, MANIFEST_FILENAME))
    if int(manifest.get("schema_version") or 0) != SUPPORTED_MANIFEST_SCHEMA:
        raise TwinError("ASSET_INVALID", "设备资产清单版本不受支持。")
    if str(manifest.get("equipment_id") or "") != equipment_id:
        raise TwinError("ASSET_INVALID", "设备资产身份不匹配。")
    raw_model = manifest.get("model") or {}
    if not isinstance(raw_model, Mapping):
        raise TwinError("ASSET_INVALID", "设备资产清单不可用。")
    model_path = _safe_child(equipment_root, str(raw_model.get("filename") or ""))
    if model_path.suffix.lower() != ".glb":
        raise TwinError("ASSET_INVALID", "设备模型格式无效。")

    expected_sha = str(raw_model.get("sha256") or "").lower()
    expected_size = int(raw_model.get("size_bytes") or -1)
    actual_size = model_path.stat().st_size
    actual_sha = sha256_file(model_path)
    if actual_size != expected_size or actual_sha != expected_sha:
        raise TwinError("ASSET_INTEGRITY_FAILED", "设备模型完整性校验失败。")

    return ModelAsset(
        equipment_id=equipment_id,
        label=str(manifest.get("label") or equipment_id),
        site_identity=str(manifest.get("site_identity") or equipment_id),
        model_path=model_path,
        sha256=actual_sha,
        size_bytes=actual_size,
        viewer_revision=str(manifest.get("viewer_revision") or "unversioned"),
        mapping_revision=str(manifest.get("mapping_revision") or "unconfigured"),
        fit_disclaimer=str(manifest.get("fit_disclaimer") or "展示拟合·非实测"),
        connection_state=str(manifest.get("connection_state") or "not_connected"),
        model_revision=str(manifest.get("model_revision") or actual_sha[:16]),
    )


def load_component_mapping(
    asset_root: str | Path,
    equipment_id: str,
    asset_id: str,
    expected_revision: str,
) -> dict[str, object]:
    equipment_id = validate_equipment_id(equipment_id)
    root = Path(asset_root).expanduser().resolve(strict=True)
    equipment_root = _safe_child(root, equipment_id)
    mapping = _read_json(_safe_child(equipment_root, MAPPING_FILENAME))
    if str(mapping.get("mapping_revision") or "") != expected_revision:
        raise TwinError("MAPPING_INVALID", "部件映射版本与模型不匹配。")
    items = mapping.get("items") or {}
    if not isinstance(items, Mapping):
        raise TwinError("MAPPING_INVALID", "部件映射配置无效。")
    raw = items.get(asset_id)
    if not isinstance(raw, Mapping):
        return {
            "equipment_id": equipment_id,
            "asset_id": asset_id,
            "mapping_revision": expected_revision,
            "status": "unverified",
            "display_name": "待核部件",
            "component_id": None,
            "process_step_id": None,
            "knowledge_link_available": False,
        }
    return {
        "equipment_id": equipment_id,
        "asset_id": asset_id,
        "mapping_revision": expected_revision,
        "status": str(raw.get("status") or "unverified"),
        "display_name": str(raw.get("display_name") or "待核部件"),
        "component_id": str(raw.get("component_id") or "").strip() or None,
        "process_step_id": str(raw.get("process_step_id") or "").strip() or None,
        # The knowledge app independently authorizes actual sources. This flag
        # only becomes true in a private mapping after a published-corpus gate.
        "knowledge_link_available": bool(raw.get("knowledge_link_available", False)),
    }
