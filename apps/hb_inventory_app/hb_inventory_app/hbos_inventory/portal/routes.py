from __future__ import annotations

from urllib.parse import unquote, urlsplit, urlunsplit

STABLE_PREFIX = "/hbos/inventory"

# 已前端化、留在 Portal SPA 内的**固定**路由（返回自身，前端据此不跳走）。
NATIVE_PATHS = {
    STABLE_PREFIX: STABLE_PREFIX,
    STABLE_PREFIX + "/intake": STABLE_PREFIX + "/intake",
    # 待检批次（只读工作台）。放行由 LIMS 投影写入，本 App 无权改。
    STABLE_PREFIX + "/pending": STABLE_PREFIX + "/pending",
    # 库存单据列表（新建入口）。单据详情走 `/entry/<单号>` 前缀路由。
    STABLE_PREFIX + "/entry": STABLE_PREFIX + "/entry",
    # 拣货单 / 库存对账的列表（新建入口），详情各走自己的前缀路由。
    STABLE_PREFIX + "/pick": STABLE_PREFIX + "/pick",
    STABLE_PREFIX + "/reconcile": STABLE_PREFIX + "/reconcile",
}

# 已前端化、带单据号后缀的**前缀**路由。
# 形如 `/hbos/inventory/draft/MAT-STE-2026-00042`，前端据此读单据号。
NATIVE_PREFIXES = (
    STABLE_PREFIX + "/draft/",
    STABLE_PREFIX + "/batch/",
    # 四张报表：`/hbos/inventory/report/<report-id>`。
    # 「一个视图 + 四条路由」—— Deep Link 归前端，路由本身不携带报表语义。
    STABLE_PREFIX + "/report/",
    # 库存单据详情：`/hbos/inventory/entry/<单号>`（列表是固定路径，见上）
    STABLE_PREFIX + "/entry/",
    # 拣货单 / 库存对账的详情（列表是固定路径，见上）
    STABLE_PREFIX + "/pick/",
    STABLE_PREFIX + "/reconcile/",
    # 主数据浏览（只读）：`/hbos/inventory/item/<物料代码>`、
    # `/hbos/inventory/warehouse/<货位名>`。物料代码与货位名都可带空格 / 连字符，
    # 由前端 encodeURIComponent 后拼入。
    STABLE_PREFIX + "/item/",
    STABLE_PREFIX + "/warehouse/",
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
