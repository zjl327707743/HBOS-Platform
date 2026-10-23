from __future__ import annotations

from urllib.parse import unquote, urlsplit, urlunsplit

STABLE_PREFIX = "/hbos/attendance"

# ── 原生 SPA 路由 ──
# 仪表盘 / 人员管理 / 部门看板已原生进 Portal SPA
# （AttendanceDashboardView.vue、AttendanceEmployeesView.vue、AttendanceBoardView.vue）。
# 解析回自身 → 前端按「以 /hbos/ 开头即 SPA 路由」处理，不进 iframe。
NATIVE_PATHS = frozenset({
    STABLE_PREFIX,
    STABLE_PREFIX + "/",
    STABLE_PREFIX + "/dashboard",
    STABLE_PREFIX + "/employees",
    STABLE_PREFIX + "/board",
})

# ── 仍由同域 iframe 承载的后台面 ──
#
# 2026-10-08 起，报表（4）、列表（4）与两个上传页已改为**门户原生渲染**，
# 走 `report_data.py` / `list_data.py` / 既有上传端点，**不再经过这里**。
# 保留在表内会让下一个人以为它们还走 iframe，故只留实际在用的那一条。
#
# 班次管理仍是例外：它是编辑器型页面、13 个写接口中两个会改判定口径、
# 低频，Owner 2026-10-08 裁定保留 Desk 实现（见 M3_考勤面板全面化与分组导航.md §7）。
#
# 稳定路径保持**纯 ASCII**：中文只出现在映射目标里（会经 axios 查询参数与
# urlsplit/urlunsplit 往返，ASCII 可完全绕开编码歧义）。
EMBEDDED_ROUTES = {
    STABLE_PREFIX + "/shifts": "/app/hbos-shift-management",
}

# 已注册的稳定路由白名单（原生 + 内嵌）。
REGISTERED_PATHS = NATIVE_PATHS | frozenset(EMBEDDED_ROUTES)


def resolve_stable_route(stable_path: str) -> str:
    """把稳定路由解析为当前实现路径（原生 SPA 路由，或 Desk 实现路径）。

    输出路径的安全性由调用方 hbos_portal.services.routes.validate_resolved_path
    再校验一次（拒 scheme / netloc / fragment / `//` / 反斜杠 / 穿越段）。
    """

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

    # 已注册的稳定路由。新增门户入口时必须在此登记，否则后端拒绝解析
    # （前端会落到 403）。保留精确白名单而非前缀放行，是为了让未注册路径
    # 在路由解析阶段就失败，而不是悄悄透传到后端。
    if decoded_path not in REGISTERED_PATHS:
        raise ValueError("Attendance stable route is not registered yet")

    # 原生路由解析回自身：保留子路径（/hbos/attendance/employees → 同一路径），
    # 前端据此命中对应的 Vue 路由。
    if decoded_path in NATIVE_PATHS:
        return urlunsplit(("", "", decoded_path, parsed.query, ""))

    # 内嵌路由解析到 Desk 实现路径；查询串透传，供报表筛选使用。
    return urlunsplit(("", "", EMBEDDED_ROUTES[decoded_path], parsed.query, ""))
