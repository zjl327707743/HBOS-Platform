"""生产看板的访问判定 —— **默认拒绝**。

## 为什么默认拒绝

Owner 尚未批准生产看板的正式角色与车间范围（见交付物的「待 Owner IAM 决定」清单）。
在授权矩阵落地之前，**任何人都不该因为「页面需要能打开」而被放行**。
所以：

- 角色白名单**默认为空**；
- 只有内置 `Administrator`（本仓库既有的审计 break-glass 身份）可进入；
- 其余用户 `can_enter = False`，`bootstrap` 里不会出现生产看板入口，
  直接调后端 API 也会被 `FORBIDDEN` 拒掉。

未来启用普通业务角色时，必须同时落实 Owner 批准的角色与服务端数据范围契约；
仅向 `PRODUCTION_ROLES` 增加角色名不足以安全启用。前端不得自行拼接权限或绕过判定。

> 与 `HBOS_BACKEND_AND_IAM_BOUNDARY_V2_PROPOSAL.md` 一致：独立 FastAPI
> 不另建员工账号；授权真相在 HBOS 侧，前端 CORS 不是鉴权。
"""

from __future__ import annotations

from collections.abc import Sequence

APP_ID = "production"
READ_CAPABILITY = "production.board.read"

#: 允许进入生产看板的角色。
#:
#: **默认为空 = 默认拒绝**，等 Owner 按 IAM 规范批准后填入。
#: 不建议在此处塞原生 `System Manager` 等平台角色 —— 平台管理角色不等于
#: 生产业务角色（见 IAM 边界提案 §3「不要使用后台管理员即所有业务管理员」）。
PRODUCTION_ROLES: tuple[str, ...] = ()


def build_access_context(
    user: str | None,
    roles: Sequence[str] | None,
) -> dict[str, object]:
    """把 HBOS 会话身份翻译成 Portal 的 access 契约。

    只返回**语义化**结果（能否进入 / 能力 / 范围），不把原始角色名传给前端。
    """

    normalized_user = str(user or "").strip()
    role_set = {str(role) for role in (roles or ())}

    if not normalized_user or normalized_user == "Guest":
        can_enter = False
    else:
        can_enter = (
            normalized_user == "Administrator"
            or bool(role_set.intersection(PRODUCTION_ROLES))
        )

    return {
        "app_id": APP_ID,
        "can_enter": can_enter,
        "capabilities": [READ_CAPABILITY] if can_enter else [],
        # 车间 / 部门范围由服务端确定；暂时没有范围能力，留空（空 ≠ ALL）。
        "scopes": {},
    }
