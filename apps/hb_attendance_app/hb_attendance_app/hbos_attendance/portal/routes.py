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

# ── 后台面（进 iframe）──
# 报表 / 列表 / 配置页按项目规范不重写成原生前端
# （docs/frontend/FRONTEND_IMPLEMENTATION_GUIDE.md §1.2），而是解析到 Desk 路径，
# 由门户内的同域 iframe 承载。
#
# 稳定路径一律**纯 ASCII**：中文只出现在映射目标里。稳定路径会经 axios 查询参数
# 与 urlsplit/urlunsplit 往返，保持 ASCII 可以完全绕开编码歧义。
EMBEDDED_ROUTES = {
    STABLE_PREFIX + "/report/monthly": "/app/query-report/月度考勤汇总",
    STABLE_PREFIX + "/report/checkins": "/app/query-report/打卡流水",
    STABLE_PREFIX + "/report/results": "/app/query-report/考勤结果",
    STABLE_PREFIX + "/report/staging": "/app/query-report/HBOS 月度汇总暂存（对账）",
    STABLE_PREFIX + "/import": "/app/hbos-attendance-import",
    STABLE_PREFIX + "/import-log": "/app/hbos-attendance-import-log",
    STABLE_PREFIX + "/monthly-upload": "/app/hbos-monthly-upload",
    STABLE_PREFIX + "/shifts": "/app/hbos-shift-management",
    STABLE_PREFIX + "/feishu/leave": "/app/hbos-leave-record",
    STABLE_PREFIX + "/feishu/overtime": "/app/hbos-overtime-record",
    STABLE_PREFIX + "/feishu/rest-leave": "/app/hbos-rest-leave-record",
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
