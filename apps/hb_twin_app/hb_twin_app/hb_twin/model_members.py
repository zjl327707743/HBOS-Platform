"""Inspect the entire supported GLB, including resources outside its scenes.

This is a deliberately narrow candidate format: one internal BIN, uncompressed
static triangle meshes, no external references or opaque extensions. A format
change requires a new inspection and membership proposal, never a silent pass.
"""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

from hb_twin_app.hb_twin.errors import TwinError

_WIDTH = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}
_COUNT = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def inspect_model(path: Path) -> dict:
    try:
        return _inspect(path.read_bytes())
    except (KeyError, IndexError, TypeError, ValueError, struct.error) as exc:
        raise TwinError("ASSET_INVALID", "模型完整成员检查失败。") from exc


def _inspect(data: bytes) -> dict:
    magic, version, size, json_size, kind = struct.unpack_from("<4sIII4s", data)
    if magic != b"glTF" or version != 2 or size != len(data) or kind != b"JSON":
        raise ValueError("header")
    doc = json.loads(data[20:20 + json_size])
    bin_size, bin_kind = struct.unpack_from("<I4s", data, 20 + json_size)
    body = data[28 + json_size:]
    if bin_kind != b"BIN\0" or len(body) != bin_size or len(doc["buffers"]) != 1:
        raise ValueError("BIN")
    if doc["buffers"][0].get("uri") or doc["buffers"][0]["byteLength"] != bin_size:
        raise ValueError("external buffer")
    if any(doc.get(key) for key in ("textures", "images", "animations", "skins", "extensionsUsed", "extensionsRequired")):
        raise ValueError("unsupported resource")

    def no_opaque(value: object) -> None:
        if isinstance(value, dict):
            if value.get("extensions") or "uri" in value:
                raise ValueError("opaque or external data")
            for child in value.values():
                no_opaque(child)
        elif isinstance(value, list):
            for child in value:
                no_opaque(child)
    no_opaque(doc)

    nodes = doc["nodes"]
    node_ids = [n["extras"]["asset_id"] for n in nodes]
    if any(not isinstance(a, str) or not a for a in node_ids) or len(set(node_ids)) != len(node_ids):
        raise ValueError("node identity")
    reached: set[int] = set()

    def visit(index: int) -> None:
        if index in reached or index < 0 or index >= len(nodes):
            raise ValueError("node graph")
        reached.add(index)
        for child in nodes[index].get("children", []):
            visit(child)
    for scene in doc["scenes"]:
        for index in scene.get("nodes", []):
            visit(index)
    if len(reached) != len(nodes):
        raise ValueError("unreachable nodes")
    # Asset references in source metadata must also stay within this package.
    for node in nodes:
        for key, values in node.get("extras", {}).items():
            if key.endswith("asset_ids") and isinstance(values, list) and not set(values) <= set(node_ids):
                raise ValueError("external asset reference")

    accessors: set[int] = set()
    views: set[int] = set()
    materials: set[int] = set()

    def accessor(index: int) -> dict:
        accessors.add(index)
        a = doc["accessors"][index]
        if a.get("sparse"):
            raise ValueError("sparse accessor")
        views.add(a["bufferView"])
        v = doc["bufferViews"][a["bufferView"]]
        width = _WIDTH[a["componentType"]] * _COUNT[a["type"]]
        # All current candidates are tightly packed; stride gaps could contain
        # unlisted data and are deliberately unsupported at this gate.
        if v.get("buffer", 0) != 0 or v.get("byteStride", width) != width:
            raise ValueError("buffer layout")
        start = v.get("byteOffset", 0) + a.get("byteOffset", 0)
        end = start + a["count"] * width
        if start < v.get("byteOffset", 0) or end > v.get("byteOffset", 0) + v["byteLength"] or end > len(body):
            raise ValueError("accessor bounds")
        return {"count": a["count"], "type": a["type"], "componentType": a["componentType"],
                "normalized": a.get("normalized", False), "payload_sha256": hashlib.sha256(body[start:end]).hexdigest()}

    used_meshes = {n["mesh"] for n in nodes if "mesh" in n}
    if any(i < 0 or i >= len(doc["meshes"]) for i in used_meshes):
        raise ValueError("mesh reference")
    meshes = []
    for index, mesh in enumerate(doc["meshes"]):
        primitives = []
        for p in mesh["primitives"]:
            if p.get("targets") or p.get("mode", 4) != 4:
                raise ValueError("mesh format")
            if "material" in p:
                materials.add(p["material"])
            primitives.append({"mode": p.get("mode", 4), "indices": accessor(p["indices"]) if "indices" in p else None,
                               "attributes": {key: accessor(a) for key, a in p["attributes"].items()}})
        meshes.append({"mesh_index": index, "geometry_sha256": _digest(primitives),
                       "descriptor_sha256": _digest(mesh), "referenced": index in used_meshes})
    if accessors != set(range(len(doc["accessors"]))) or views != set(range(len(doc["bufferViews"]))) or materials != set(range(len(doc.get("materials", [])))):
        raise ValueError("unlisted resource")
    # Account for every byte, including padding. No opaque unused BIN is sent.
    cursor = 0
    padding = 0
    for start, end in sorted((v.get("byteOffset", 0), v.get("byteOffset", 0) + v["byteLength"]) for v in doc["bufferViews"]):
        if start < cursor or end > len(body) or end < start:
            raise ValueError("buffer view overlap or bounds")
        gap = body[cursor:start]
        if len(gap) > 3 or any(gap):
            raise ValueError("opaque BIN data")
        padding += len(gap)
        cursor = end
    gap = body[cursor:]
    if len(gap) > 3 or any(gap):
        raise ValueError("opaque BIN tail")
    padding += len(gap)
    # Each view must be fully covered by tightly packed accessors. Checking the
    # view range alone would miss hidden bytes inside an oversized bufferView.
    for index, view in enumerate(doc["bufferViews"]):
        intervals = sorted((a.get("byteOffset", 0), a.get("byteOffset", 0) + a["count"] * _WIDTH[a["componentType"]] * _COUNT[a["type"]])
                           for a in doc["accessors"] if a["bufferView"] == index)
        covered = 0
        for start, end in intervals:
            if start > covered:
                raise ValueError("unused view bytes")
            covered = max(covered, end)
        if covered != view["byteLength"]:
            raise ValueError("unused view tail")
    closure = {"meshes": meshes, "accessors": len(accessors), "buffer_views": len(views), "materials": len(materials),
               "bin_bytes": len(body), "zero_alignment_bytes": padding, "unreachable_nodes": 0,
               "external_references": 0, "textures": 0, "animations": 0}
    return {"node_ids": node_ids, "node_meshes": {node_ids[i]: n["mesh"] for i, n in enumerate(nodes) if "mesh" in n},
            "meshes": meshes, "unreferenced_meshes": [m for m in meshes if not m["referenced"]],
            "closure_sha256": _digest(closure), "closure": closure}
