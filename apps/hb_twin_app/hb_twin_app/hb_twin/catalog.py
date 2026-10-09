"""Twin-only, content-bound bundles; existing policy remains the authority.

Private review approval is an asset gate in addition to policy. It never grants
a capability, equipment scope, role or access to knowledge sources.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlencode

from hb_twin_app.hb_twin.assets import _read_json, _safe_child, sha256_file, validate_equipment_id
from hb_twin_app.hb_twin.errors import TwinError
from hb_twin_app.hb_twin.policy import TwinPolicy, VIEW_CAPABILITY
from hb_twin_app.hb_twin.model_members import inspect_model


def private_root(value: str | Path) -> Path:
    root = Path(value).expanduser()
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        raise TwinError("CONFIG_REQUIRED", "私有设备资产目录尚未配置。")
    return root.resolve(strict=True)


def enabled(value: str | Path) -> bool:
    return (private_root(value) / "catalog.json").is_file()


def _require_enter(policy: TwinPolicy) -> None:
    if not policy.can_enter or VIEW_CAPABILITY not in policy.capabilities:
        raise TwinError("FORBIDDEN", "你没有权限访问设备模块。")


def _entries(root: Path) -> Mapping[str, Any]:
    doc = _read_json(_safe_child(root, "catalog.json"))
    if doc.get("schema") != "twin.catalog.v1" or not isinstance(doc.get("entries"), list):
        raise TwinError("ASSET_INVALID", "设备目录版本不受支持。")
    return doc


def _entry(root: Path, entry_id: str) -> Mapping[str, Any]:
    validate_equipment_id(entry_id)
    matches = [e for e in _entries(root)["entries"] if e.get("entry_id") == entry_id]
    if len(matches) != 1:
        raise TwinError("FORBIDDEN", "无法访问此设备或场景。")
    return matches[0]


def _required(entry: Mapping[str, Any], policy: TwinPolicy) -> None:
    _require_enter(policy)
    scopes = entry.get("required_equipment_ids")
    if not isinstance(scopes, list) or not scopes:
        raise TwinError("ASSET_INVALID", "资产成员范围未配置。")
    for equipment in scopes:
        policy.require_equipment(str(equipment))


def _hashed(root: Path, specification: Mapping[str, Any]) -> Path:
    path = _safe_child(root, str(specification.get("filename") or ""))
    if path.stat().st_size != specification.get("size_bytes") or sha256_file(path) != specification.get("sha256"):
        raise TwinError("ASSET_INTEGRITY_FAILED", "设备资源完整性校验失败。")
    return path


def _version(actual: str, expected: str | None) -> None:
    if expected is not None and expected != actual:
        raise TwinError("ASSET_REVISION_MISMATCH", "设备资源版本已变更，请重新打开。")


def _review_approval(folder: Path, manifest: Mapping[str, Any], subject: str) -> None:
    approval_path = folder / "approval.json"
    if not approval_path.exists():
        raise TwinError("MEMBERS_PENDING", "资产成员范围等待 Owner 确认。")
    approval = _read_json(_safe_child(folder, "approval.json"))
    # This candidate has no public/company release mode. The only supported
    # approval names exact synthetic review subjects in the private config.
    if (approval.get("status") != "OWNER_PRIVATE_REVIEW_APPROVED"
            or not approval.get("approval_reference")
            or subject not in approval.get("subjects", [])
            or approval.get("model_sha256") != manifest["model"]["sha256"]
            or approval.get("members_sha256") != manifest["members"]["sha256"]):
        raise TwinError("MEMBERS_PENDING", "当前会话不在已确认的私有评审范围。")


def catalog(value: str | Path, policy: TwinPolicy) -> dict[str, Any]:
    _require_enter(policy)
    root = private_root(value)
    doc = _entries(root)
    result = []
    for entry in doc["entries"]:
        equipment = entry.get("equipment_ids", [])
        # No unprivileged enumeration of scenes, equipment or accessory topics.
        if not equipment or any(e not in policy.equipment_ids for e in equipment):
            continue
        try:
            _required(entry, policy)
        except TwinError:
            if entry.get("entity_type") != "device":
                continue
            result.append({"entry_id":entry["entry_id"], "entity_type":"device", "equipment_ids":equipment,
                           "label":entry["label"], "availability":"SCOPE_NOT_READY"})
            continue
        folder = _safe_child(root, entry["entry_id"])
        try:
            manifest = _read_json(_safe_child(folder, "bundle.json"))
            _review_approval(folder, manifest, policy.subject)
            availability = "READY"
        except TwinError as exc:
            if exc.code in {"MEMBERS_PENDING", "ASSET_UNAVAILABLE"}:
                availability = exc.code
            else:
                raise
        result.append({"entry_id":entry["entry_id"], "entity_type":entry["entity_type"], "equipment_ids":equipment,
                       "label":entry["label"], "availability":availability})
    return {"schema":"twin.catalog.v1", "catalog_revision":doc["revision"], "entries":result}


@dataclass(frozen=True)
class Bundle:
    folder: Path
    definition: Mapping[str, Any]
    manifest: Mapping[str, Any]
    members: frozenset[str]
    model_path: Path
    member_scopes: Mapping[str, frozenset[str]]

    def browser_manifest(self) -> dict[str, Any]:
        m = self.manifest
        query = urlencode({"entry_id":m["entry_id"], "expected_model_sha256":m["model"]["sha256"], "expected_mapping_revision":m["mapping_revision"]})
        return {
            "entry_id":m["entry_id"], "entity_type":self.definition["entity_type"],
            "equipment_ids":self.definition["equipment_ids"], "label":self.definition["label"],
            "model_sha256":m["model"]["sha256"], "model_size_bytes":m["model"]["size_bytes"],
            "model_revision":m["model_revision"], "mapping_revision":m["mapping_revision"],
            "mapping_sha256":m["parts"]["sha256"], "process_revision":m["process_revision"],
            "process_sha256":m["process"]["sha256"], "binding_revision":m["binding_revision"],
            "camera_revision":m["camera_revision"], "demo_revision":m["demo_revision"], "demo_seed":m["demo_seed"],
            "truth":{"identity":"owner_confirmed", "geometry":"site_applicability_pending", "internals":"schematic_only", "visual_review":"pending", "data":"not_connected"},
            "model_url":"/api/method/hb_twin_app.hb_twin.api.get_entry_model?"+query,
            "review_only":True,
        }

    def resource(self, kind: str) -> Mapping[str, Any]:
        specification = self.manifest[kind]
        doc = _read_json(_hashed(self.folder, specification))
        if doc.get("entry_id") != self.manifest["entry_id"] or doc.get("model_sha256") != self.manifest["model"]["sha256"]:
            raise TwinError("ASSET_REVISION_MISMATCH", "资源与当前模型不兼容。")
        if doc.get("mapping_revision") != self.manifest["mapping_revision"]:
            raise TwinError("MAPPING_INVALID", "部件映射与当前模型不兼容。")
        return doc


def load_bundle(value: str | Path, entry_id: str, policy: TwinPolicy, *,
                expected_model_sha256: str | None = None,
                expected_mapping_revision: str | None = None,
                expected_process_revision: str | None = None) -> Bundle:
    root = private_root(value)
    entry = _entry(root, entry_id)
    _required(entry, policy)  # Always before reading model/configuration bytes.
    folder = _safe_child(root, entry_id)
    manifest = _read_json(_safe_child(folder, "bundle.json"))
    if manifest.get("schema") != "twin.bundle.v1" or manifest.get("entry_id") != entry_id:
        raise TwinError("ASSET_INVALID", "设备资源清单无效。")
    _review_approval(folder, manifest, policy.subject)
    if manifest.get("required_equipment_ids") != entry["required_equipment_ids"]:
        raise TwinError("ASSET_INVALID", "资产成员范围与目录不匹配。")
    _version(manifest["model"]["sha256"], expected_model_sha256)
    _version(manifest["mapping_revision"], expected_mapping_revision)
    _version(manifest["process_revision"], expected_process_revision)
    membership = _read_json(_hashed(folder, manifest["members"]))
    if membership.get("model_sha256") != manifest["model"]["sha256"]:
        raise TwinError("ASSET_INVALID", "资产成员与模型版本不匹配。")
    member_rows = membership.get("members", [])
    members = frozenset(row["asset_id"] for row in member_rows)
    if not members or len(members) != len(member_rows):
        raise TwinError("ASSET_INVALID", "资产成员清单无效。")
    for row in member_rows:
        required = row.get("proposed_required_equipment_ids")
        if not required or any(e not in entry["required_equipment_ids"] for e in required):
            raise TwinError("ASSET_INVALID", "资产成员范围不完整。")
    model = _hashed(folder, manifest["model"])
    inspection = inspect_model(model)
    node_ids = inspection["node_ids"]
    if len(node_ids) != len(members) or frozenset(node_ids) != members:
        raise TwinError("ASSET_INVALID", "模型实际成员与批准范围不匹配。")
    if membership.get("closure_sha256") != inspection["closure_sha256"]:
        raise TwinError("ASSET_INVALID", "模型资源范围与成员清单不匹配。")
    resources = membership.get("unreferenced_meshes", [])
    actual = {r["mesh_index"]: r for r in inspection["unreferenced_meshes"]}
    if len(resources) != len(actual) or {r.get("mesh_index") for r in resources} != set(actual):
        raise TwinError("ASSET_INVALID", "未引用几何没有完整登记。")
    for row in resources:
        if any(row.get(k) != actual[row["mesh_index"]][k] for k in ("geometry_sha256", "descriptor_sha256")):
            raise TwinError("ASSET_INVALID", "未引用几何指纹不匹配。")
        required = row.get("proposed_required_equipment_ids", [])
        if not required or not set(required) <= set(entry["required_equipment_ids"]):
            raise TwinError("ASSET_INVALID", "未引用几何范围不完整。")
    member_scopes = {row["asset_id"]: frozenset(row["proposed_required_equipment_ids"]) for row in member_rows}
    bundle = Bundle(folder, entry, manifest, members, model, member_scopes)
    parts = bundle.resource("parts")
    if any(a not in members for g in parts.get("groups", []) for a in g.get("asset_ids", [])):
        raise TwinError("MAPPING_INVALID", "候选目录包含非当前模型成员。")
    if any(a not in members for a in parts.get("items", {})):
        raise TwinError("MAPPING_INVALID", "映射包含非当前模型成员。")
    if any(g.get("equipment_id") is not None and g["equipment_id"] not in entry["equipment_ids"] for g in parts.get("groups", [])):
        raise TwinError("MAPPING_INVALID", "候选目录包含非当前设备。")
    if any(g.get("equipment_id") and any(g["equipment_id"] not in member_scopes[a] for a in g.get("asset_ids", [])) for g in parts.get("groups", [])):
        raise TwinError("MAPPING_INVALID", "候选目录成员与设备不匹配。")
    return bundle


def component_mapping(bundle: Bundle, asset_id: str, equipment_id: str) -> dict[str, Any]:
    if equipment_id not in bundle.definition["equipment_ids"] or asset_id not in bundle.members or equipment_id not in bundle.member_scopes[asset_id]:
        raise TwinError("MAPPING_INVALID", "当前设备中没有可定位的此部件。")
    parts = bundle.resource("parts")
    raw = parts.get("items", {}).get(asset_id, {})
    if raw and raw.get("equipment_id") != equipment_id:
        raise TwinError("MAPPING_INVALID", "部件不属于当前设备。")
    verified = raw.get("status") == "verified" and bool(raw.get("component_id"))
    return {"entry_id":bundle.manifest["entry_id"], "equipment_id":equipment_id, "asset_id":asset_id,
            "model_sha256":bundle.manifest["model"]["sha256"], "mapping_revision":bundle.manifest["mapping_revision"],
            "status":"verified" if verified else "unverified", "display_name":raw.get("display_name") or "待核节点",
            "component_id":raw.get("component_id") if verified else None,
            "knowledge_link_available":bool(verified and raw.get("knowledge_link_available"))}


def process_config(bundle: Bundle) -> Mapping[str, Any]:
    doc = bundle.resource("process")
    _version(bundle.manifest["process_revision"], doc.get("process_revision"))
    if doc.get("binding_revision") != bundle.manifest["binding_revision"]:
        raise TwinError("PROCESS_INCOMPATIBLE", "示教绑定版本不兼容。")
    if bundle.manifest.get("demo_seed") != 102:
        raise TwinError("PROCESS_INCOMPATIBLE", "示教种子与当前运行版本不兼容。")
    # Optional increment fields preserve the sealed A2 production combination.
    for key in ("camera_revision", "demo_revision"):
        if key in doc and doc[key] != bundle.manifest[key]:
            raise TwinError("PROCESS_INCOMPATIBLE", "示教镜头或演示版本不兼容。")
    if not set(doc.get("modes", [])) <= {"production", "filtration", "cip", "sip", "jacket", "attachment"}:
        raise TwinError("PROCESS_INCOMPATIBLE", "示教专题版本不兼容。")
    for equipment, config in doc.get("bindings", {}).items():
        targets = config.get("ids", [])
        if equipment not in bundle.definition["equipment_ids"] or len(set(targets)) != 5 or len(targets) != 5 or not set(targets) <= bundle.members or config.get("anchor") not in targets:
            raise TwinError("PROCESS_INCOMPATIBLE", "示教目标不在当前设备模型中。")
        if any(equipment not in bundle.member_scopes[a] for a in targets):
            raise TwinError("PROCESS_INCOMPATIBLE", "示教目标不属于当前讲解设备。")
    groups = {g.get("group_id"): g for g in bundle.resource("parts").get("groups", [])}
    for equipment, camera in doc.get("camera_targets", {}).items():
        ids = camera.get("overview_ids", [])
        source_groups = [groups.get(g) for g in camera.get("source_group_ids", [])]
        if (equipment not in bundle.definition["equipment_ids"] or not ids or len(set(ids)) != len(ids)
                or not set(ids) <= bundle.members or not source_groups
                or any(g is None or g.get("equipment_id") != equipment for g in source_groups)):
            raise TwinError("PROCESS_INCOMPATIBLE", "总览镜头缺少当前设备的登记分组依据。")
        registered = {a for g in source_groups for a in g.get("asset_ids", [])}
        if not set(ids) <= registered or any(equipment not in bundle.member_scopes[a] for a in ids):
            raise TwinError("PROCESS_INCOMPATIBLE", "总览镜头目标不属于当前登记设备组。")
    lessons = doc.get("lessons", {})
    if not set(lessons) <= {"jacket", "attachment"}:
        raise TwinError("PROCESS_INCOMPATIBLE", "几何讲解配置不受支持。")
    for kind, lesson in lessons.items():
        if kind not in doc.get("modes", []) or "M607B" not in doc.get("bindings", {}):
            raise TwinError("PROCESS_INCOMPATIBLE", "几何讲解没有对应的设备绑定。")
        rows = [lesson.get("supply", {}), lesson.get("return", {})] if kind == "jacket" else [lesson]
        for row in rows:
            ids = row.get("ids", [])
            scope = "M607B" if kind == "jacket" else "M660B"
            if (not ids or len(set(ids)) != len(ids) or not set(ids) <= bundle.members
                    or any(scope not in bundle.member_scopes[a] for a in ids)):
                raise TwinError("PROCESS_INCOMPATIBLE", "几何讲解目标超出已登记成员范围。")
            if kind == "jacket" and (len(ids) != 7 or row.get("parent_id") not in bundle.members):
                raise TwinError("PROCESS_INCOMPATIBLE", "夹套供回名称候选与原讲解不兼容。")
    if any(mode in doc.get("modes", []) and mode not in lessons for mode in ("jacket", "attachment")):
        raise TwinError("PROCESS_INCOMPATIBLE", "几何讲解缺少登记目标。")
    return doc
