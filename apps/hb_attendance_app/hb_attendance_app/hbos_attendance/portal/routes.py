from __future__ import annotations

from urllib.parse import unquote, urlsplit, urlunsplit

STABLE_PREFIX = "/hbos/attendance"
# 仪表盘/人员管理已原生进 Portal SPA（AttendanceDashboardView.vue、
# AttendanceEmployeesView.vue）。解析回自身 → 前端按「以 /hbos/ 开头即
# SPA 路由」处理，不再进 iframe。
CURRENT_IMPLEMENTATION = STABLE_PREFIX

# 已注册的稳定路由白名单（含子路由）。
REGISTERED_PATHS = frozenset({
    STABLE_PREFIX,
    STABLE_PREFIX + "/",
    STABLE_PREFIX + "/dashboard",
    STABLE_PREFIX + "/employees",
    STABLE_PREFIX + "/board",
})


def resolve_stable_route(stable_path: str) -> str:
    """Map stable HBOS Attendance routes to the current native implementation."""

    value = str(stable_path or "").strip()
    parsed = urlsplit(value)

    if parsed.scheme or parsed.netloc or parsed.fragment:
        raise ValueError("Attendance Portal route must be a local path without fragment")

    decoded_path = unquote(parsed.path)
    if "\\" in decoded_path:
        raise ValueError("Attendance Portal route must not contain backslashes")

    segments = [segment for segment in decoded_path.split("/") if segment]
    if any(segment in {".", ".."} for segment in segments):
        raise ValueError("Attendance Portal route must not contain traversal segments")

    # 已注册的稳定子路由。新增 Portal 页面时必须在此登记，否则后端拒绝解析
    # （前端会落到 403）。保留精确白名单而非前缀放行，是为了让未注册路径
    # 在路由解析阶段就失败，而不是悄悄透传到后端。
    if decoded_path not in REGISTERED_PATHS:
        raise ValueError("Attendance stable route is not registered yet")

    # 子路由解析回自身时保留其子路径（/hbos/attendance/employees → 同一路径），
    # 前端据此命中对应的 Vue 路由。
    return urlunsplit(("", "", decoded_path, parsed.query, ""))
