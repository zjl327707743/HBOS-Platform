"""Repack a static, uncompressed GLB from explicit, privately supplied root IDs.

Fail closed on features this exporter cannot prove safe. Never copies the source
BIN wholesale. Each retained accessor is packed separately without stride gaps.
The source is read only; output and evidence must be outside the repository.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import itertools
import json
import math
import struct
from pathlib import Path


def read_glb(path):
    data = Path(path).read_bytes()
    magic, version, length = struct.unpack_from("<4sII", data)
    assert (magic, version, length) == (b"glTF", 2, len(data)), "Invalid GLB header"
    chunks = []
    cursor = 12
    while cursor < len(data):
        size, kind = struct.unpack_from("<I4s", data, cursor)
        assert size % 4 == 0 and cursor + 8 + size <= len(data)
        chunks.append((kind, data[cursor + 8:cursor + 8 + size]))
        cursor += 8 + size
    assert len(chunks) == 2 and [c[0] for c in chunks] == [b"JSON", b"BIN\0"]
    return json.loads(chunks[0][1]), chunks[1][1]


def matrix(node):
    if "matrix" in node:
        a = node["matrix"]
        return [[a[c * 4 + r] for c in range(4)] for r in range(4)]
    x, y, z, w = node.get("rotation", [0, 0, 0, 1])
    sx, sy, sz = node.get("scale", [1, 1, 1])
    px, py, pz = node.get("translation", [0, 0, 0])
    return [
        [(1-2*y*y-2*z*z)*sx, (2*x*y-2*z*w)*sy, (2*x*z+2*y*w)*sz, px],
        [(2*x*y+2*z*w)*sx, (1-2*x*x-2*z*z)*sy, (2*y*z-2*x*w)*sz, py],
        [(2*x*z-2*y*w)*sx, (2*y*z+2*x*w)*sy, (1-2*x*x-2*y*y)*sz, pz],
        [0, 0, 0, 1],
    ]


def mul(a, b):
    return [[sum(a[r][k]*b[k][c] for k in range(4)) for c in range(4)] for r in range(4)]


def world_matrices(doc):
    result = {}
    identity = [[int(r == c) for c in range(4)] for r in range(4)]
    def visit(index, parent):
        assert index not in result, "Repeated/cyclic node"
        result[index] = mul(parent, matrix(doc["nodes"][index]))
        for child in doc["nodes"][index].get("children", []):
            visit(child, result[index])
    for scene in doc["scenes"]:
        for root in scene.get("nodes", []):
            if root not in result:
                visit(root, identity)
    return result


def accessor_bytes(doc, binary, index):
    accessor = doc["accessors"][index]
    assert "sparse" not in accessor and "extensions" not in accessor
    width = {5120:1, 5121:1, 5122:2, 5123:2, 5125:4, 5126:4}[accessor["componentType"]]
    components = {"SCALAR":1, "VEC2":2, "VEC3":3, "VEC4":4}[accessor["type"]]
    view = doc["bufferViews"][accessor["bufferView"]]
    assert view.get("buffer", 0) == 0 and "extensions" not in view
    item_size = width * components
    stride = view.get("byteStride", item_size)
    offset = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    assert stride >= item_size and offset + (accessor["count"]-1)*stride + item_size <= view.get("byteOffset", 0) + view["byteLength"]
    return b"".join(binary[offset+i*stride:offset+i*stride+item_size] for i in range(accessor["count"]))


def bounds(doc, worlds):
    points = []
    for index, node in enumerate(doc["nodes"]):
        if "mesh" not in node:
            continue
        for primitive in doc["meshes"][node["mesh"]]["primitives"]:
            a = doc["accessors"][primitive["attributes"]["POSITION"]]
            assert "min" in a and "max" in a
            for xyz in itertools.product(*zip(a["min"], a["max"])):
                points.append([sum(worlds[index][r][k]*(*xyz, 1)[k] for k in range(4)) for r in range(3)])
    return [[min(p[k] for p in points) for k in range(3)], [max(p[k] for p in points) for k in range(3)]]


def subset(source, root_ids, destination, evidence_path):
    if not __debug__:
        raise RuntimeError("Run without -O; export verification is mandatory")
    if not isinstance(root_ids, list) or not root_ids or len(set(root_ids)) != len(root_ids):
        raise ValueError("Supply distinct, explicit source root IDs")
    source = Path(source).resolve(strict=True)
    destination, evidence_path = Path(destination).resolve(), Path(evidence_path).resolve()
    if destination == evidence_path:
        raise ValueError("Candidate and evidence paths must differ")
    for output in (destination, evidence_path):
        if output.exists() or output == source:
            raise ValueError("Refuse to overwrite any source or existing output")
        if any((parent / ".git").exists() for parent in output.parents):
            raise ValueError("Private candidate and evidence must remain outside Git")
    src, binary = read_glb(source)
    assert not any(src.get(k) for k in ["extensionsUsed", "extensionsRequired", "animations", "skins", "textures", "images", "cameras"]), "Unsupported feature; review required"
    assert len(src["buffers"]) == 1 and "uri" not in src["buffers"][0]
    ids = {n.get("extras", {}).get("asset_id"): i for i, n in enumerate(src["nodes"])}
    assert len(ids) == len(src["nodes"]) and None not in ids
    source_roots = {i for s in src["scenes"] for i in s.get("nodes", [])}
    roots = [ids[r] for r in root_ids]
    assert set(roots) <= source_roots, "Only complete source roots are supported"
    kept = set()
    def collect(index):
        assert index not in kept
        kept.add(index)
        for child in src["nodes"][index].get("children", []):
            collect(child)
    for r in roots:
        collect(r)
    node_map = {old: new for new, old in enumerate(sorted(kept))}
    mesh_map = {old: new for new, old in enumerate(sorted({src["nodes"][i]["mesh"] for i in kept if "mesh" in src["nodes"][i]}))}
    out = {"asset":{"version":"2.0", "generator":"HBOS Twin static subset v1"}, "scene":0,
           "scenes":[{"nodes":[node_map[r] for r in roots]}], "nodes":[], "meshes":[], "accessors":[], "bufferViews":[], "materials":[]}
    kept_ids = {src["nodes"][i]["extras"]["asset_id"] for i in kept}
    for i in sorted(kept):
        n = copy.deepcopy(src["nodes"][i])
        assert not any(k in n for k in ["skin", "camera", "extensions"])
        # Retain only local provenance, never references to removed objects.
        extras = n.get("extras", {})
        for key, value in extras.items():
            if key.endswith("asset_ids") and isinstance(value, list):
                assert set(value) <= kept_ids, "Metadata references removed content"
        if "children" in n:
            n["children"] = [node_map[c] for c in n["children"]]
        if "mesh" in n:
            n["mesh"] = mesh_map[n["mesh"]]
        out["nodes"].append(n)
    packed = bytearray()
    accessor_map, material_map = {}, {}
    def pack_accessor(old):
        if old in accessor_map:
            return accessor_map[old]
        data = accessor_bytes(src, binary, old)
        while len(packed) % 4:
            packed.append(0)
        view_index = len(out["bufferViews"])
        out["bufferViews"].append({"buffer":0, "byteOffset":len(packed), "byteLength":len(data)})
        packed.extend(data)
        a = copy.deepcopy(src["accessors"][old])
        a.pop("name", None); a.pop("extras", None); a.pop("byteOffset", None)
        a["bufferView"] = view_index
        accessor_map[old] = len(out["accessors"])
        out["accessors"].append(a)
        return accessor_map[old]
    for old in mesh_map:
        mesh = copy.deepcopy(src["meshes"][old])
        mesh.pop("name", None); mesh.pop("extras", None)
        for p in mesh["primitives"]:
            assert not p.get("extensions") and not p.get("targets")
            p["attributes"] = {k:pack_accessor(a) for k,a in p["attributes"].items()}
            if "indices" in p:
                p["indices"] = pack_accessor(p["indices"])
            if "material" in p:
                m = p["material"]
                if m not in material_map:
                    material = copy.deepcopy(src["materials"][m])
                    assert not material.get("extensions")
                    material.pop("name", None); material.pop("extras", None)
                    material_map[m] = len(out["materials"])
                    out["materials"].append(material)
                p["material"] = material_map[m]
        out["meshes"].append(mesh)
    out["buffers"] = [{"byteLength":len(packed)}]
    body = json.dumps(out, ensure_ascii=False, separators=(",", ":")).encode()
    body += b" " * (-len(body) % 4)
    packed.extend(b"\0" * (-len(packed) % 4))
    result = struct.pack("<4sII", b"glTF", 2, 28+len(body)+len(packed)) + struct.pack("<I4s",len(body),b"JSON") + body + struct.pack("<I4s",len(packed),b"BIN\0") + packed
    Path(destination).parent.mkdir(parents=True, exist_ok=True)
    Path(destination).write_bytes(result)
    check, check_bin = read_glb(destination)
    source_world, candidate_world = world_matrices(src), world_matrices(check)
    records = []
    for old, new in node_map.items():
        error = max(abs(source_world[old][r][c]-candidate_world[new][r][c]) for r in range(4) for c in range(4))
        assert math.isfinite(error) and error <= 1e-10
        records.append({"asset_id":src["nodes"][old]["extras"]["asset_id"], "source_node":old,"candidate_node":new,"source_world_matrix":source_world[old],"candidate_world_matrix":candidate_world[new],"max_error":error})
    for old, new in accessor_map.items():
        assert accessor_bytes(src,binary,old) == accessor_bytes(check,check_bin,new)
    assert len(candidate_world) == len(check["nodes"]), "Unreachable nodes"
    assert len(mesh_map) == len(check["meshes"]) and len(accessor_map) == len(check["accessors"])
    # Prove the entire BIN consists of retained accessor bytes and zero alignment.
    cursor = 0
    for view in check["bufferViews"]:
        assert not any(check_bin[cursor:view["byteOffset"]])
        cursor = view["byteOffset"] + view["byteLength"]
    assert not any(check_bin[cursor:])
    evidence = {"schema":"twin.subset-evidence.v1", "source_sha256":hashlib.sha256(Path(source).read_bytes()).hexdigest(),"candidate_sha256":hashlib.sha256(result).hexdigest(),"size_bytes":len(result),"root_asset_ids":root_ids,"retained_nodes":len(kept),"retained_mesh_instances":sum("mesh" in n for n in check["nodes"]),"unique_meshes":len(mesh_map),"accessors":len(accessor_map),"buffer_views":len(check["bufferViews"]),"materials":len(material_map),"scenes":1,"textures":0,"unreachable_nodes":0,"unused_bin_payload":0,"matrix_tolerance_gltf_units":1e-10,"source_subtree_bbox":bounds({**src,"nodes":[src["nodes"][i] for i in sorted(kept)]},{n:source_world[old] for n,old in enumerate(sorted(kept))}),"candidate_bbox":bounds(check,candidate_world),"id_matrix_comparison":records,"removed_asset_ids":[n["extras"]["asset_id"] for i,n in enumerate(src["nodes"]) if i not in kept],"distribution_approval":"PENDING_OWNER","precision":"Numerical transform retention only; not site measurement precision"}
    assert evidence["source_subtree_bbox"] == evidence["candidate_bbox"]
    Path(evidence_path).write_text(json.dumps(evidence,ensure_ascii=False,indent=2))
    return {k:v for k,v in evidence.items() if k not in ["id_matrix_comparison","removed_asset_ids"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for key in ["source", "roots_file", "output", "evidence"]:
        parser.add_argument("--"+key.replace("_","-"), required=True)
    args = parser.parse_args()
    print(json.dumps(subset(args.source,json.loads(Path(args.roots_file).read_text()),args.output,args.evidence),ensure_ascii=False,indent=2))
