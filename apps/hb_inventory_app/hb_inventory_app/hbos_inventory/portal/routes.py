from __future__ import annotations

from urllib.parse import unquote, urlsplit, urlunsplit

STABLE_PREFIX = "/hbos/inventory"

# 已前端化、留在 Portal SPA 内的**固定**路由（返回自身，前端据此不跳走）。
NATIVE_PATHS = {
    STABLE_PREFIX: STABLE_PREFIX,
    STABLE_PREFIX + "/intake": STABLE_PREFIX + "/intake",
}

# 已前端化、带单据号后缀的**前缀**路由。
# 形如 `/hbos/inventory/draft/MAT-STE-2026-00042`，前端据此读单据号。
NATIVE_PREFIXES = (
    STABLE_PREFIX + "/draft/",
    STABLE_PREFIX + "/batch/",
    # 四张报表：`/hbos/inventory/report/<report-id>`。
    # 「一个视图 + 四条路由」—— Deep Link 归前端，路由本身不携带报表语义。
    STABLE_PREFIX + "/report/",
)


def resolve_stable_route(stable_path: str) -> str:
    """Map stable Inventory routes to their current implementation.

    这些路由都已原生；但 ``migration_mode`` 仍是 ``hybrid`` —— 概览页、拍照识别页、
    草稿复核页、批次页在前端，而**通用 Stock Entry / 其他 ERPNext 单据**仍走原生表单。
    所以不会是「全部原生」的 ``native`` 语义。
    """

    value = str(stable_path or "").strip()
    parsed = urlsplit(value)

    if parsed.scheme or parsed.netloc or parsed.fragment:
        raise ValueError("Inventory Portal route must be a local path without fragment")

    decoded_path = unquote(parsed.path)
    if "\\" in decoded_path:
        raise ValueError("Inventory Portal route must not contain backslashes")

    segments = [segment for segment in decoded_path.split("/") if segment]
    if any(segment in {".", ".."} for segment in segments):
        raise ValueError("Inventory Portal route must not contain traversal segments")

    # 末尾斜杠与基础路由等价
    if decoded_path == STABLE_PREFIX + "/":
        decoded_path = STABLE_PREFIX

    if decoded_path in NATIVE_PATHS:
        return urlunsplit(("", "", NATIVE_PATHS[decoded_path], parsed.query, ""))

    for prefix in NATIVE_PREFIXES:
        # 前缀之后必须还有内容（单据号），否则是 `/draft/` 这种半截路径
        if decoded_path.startswith(prefix) and len(decoded_path) > len(prefix):
            return urlunsplit(("", "", decoded_path, parsed.query, ""))

    raise ValueError("Inventory stable route is not registered yet")
