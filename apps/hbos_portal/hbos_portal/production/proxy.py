"""受控代理：HBOS 后端 → 生产 FastAPI。

## 为什么必须有这一层

原来前端**直连** FastAPI（`VITE_PRODUCTION_SERVICE_ORIGIN`），意味着：

- 浏览器拿到服务地址后可以绕开 Portal 直接请求它；
- FastAPI 只靠 CORS 判断来源 —— CORS 是浏览器行为，不是鉴权；
- 权限与数据范围无从谈起。

现在改成：`Portal → HBOS 受控后端 API → 生产 FastAPI → 飞书`。
浏览器不再知道 FastAPI 的地址，也不再持有它的凭据。

## 服务间凭据

`hbos_production_service_token` 与 `hbos_production_service_url` 放在 **site config**
（`frappe.conf`，不进仓库）。**未配置即拒**（`SERVICE_NOT_CONFIGURED`）——
不允许「没配就跑匿名」。

> 说明：这里用静态共享令牌是最小可用形态（受信服务间凭证）。
> 签名 / 重放保护 / 轮换策略按 IAM 边界提案 §4 在后续设计中落地。
"""

from __future__ import annotations

from typing import Any, Mapping

from hbos_portal.contracts.errors import PortalException, new_trace_id

#: 读超时（秒）。冷取要并发拉 13 张飞书表，实测约 15 秒，给足余量。
DEFAULT_TIMEOUT = 60


def _conf(key: str) -> str:
    import frappe

    return str(frappe.conf.get(key) or "").strip()


def service_url() -> str:
    return _conf("hbos_production_service_url").rstrip("/")


def _service_token() -> str:
    return _conf("hbos_production_service_token")


def _require_configured() -> tuple[str, str]:
    url = service_url()
    token = _service_token()
    if not url or not token:
        # 明确报「未接入」，而不是编造数据或静默放行
        raise PortalException(
            "SERVICE_NOT_CONFIGURED",
            "生产数据服务尚未接入，请联系管理员。",
            retryable=False,
        )
    return url, token


def fetch_json(
    path: str,
    *,
    params: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """带服务令牌请求生产 FastAPI 的一个只读端点。

    - 只允许相对路径（防 SSRF：不允许 `http://` 或 `//host`）；
    - 超时与网络错误统一转成 Portal 语义的错误，不把底层细节透给前端。
    """

    import requests

    if not str(path).startswith("/") or str(path).startswith("//"):
        raise PortalException("INVALID_REQUEST", "生产服务路径非法。")

    base, token = _require_configured()

    try:
        response = requests.get(
            f"{base}{path}",
            params=dict(params or {}),
            headers={
                "X-HBOS-Service-Token": token,
                "Accept": "application/json",
            },
            timeout=DEFAULT_TIMEOUT,
        )
    except requests.RequestException:
        trace_id = new_trace_id()
        raise PortalException(
            "PROVIDER_ERROR",
            "生产数据服务暂时不可用，请稍后重试。",
            retryable=True,
            trace_id=trace_id,
        ) from None

    if response.status_code == 401 or response.status_code == 403:
        # 服务端令牌不对 / 被拒 —— 这是配置问题，不是用户问题
        raise PortalException(
            "PROVIDER_ERROR",
            "生产数据服务拒绝了本次调用，请联系管理员。",
            retryable=False,
        )
    if response.status_code != 200:
        raise PortalException(
            "PROVIDER_ERROR",
            "生产数据服务暂时不可用，请稍后重试。",
            retryable=True,
        )

    try:
        payload = response.json()
    except ValueError:
        raise PortalException(
            "PROVIDER_ERROR",
            "生产数据服务返回了无效响应。",
            retryable=True,
        ) from None

    if not isinstance(payload, dict):
        raise PortalException(
            "PROVIDER_ERROR",
            "生产数据服务返回了无效响应。",
            retryable=True,
        )
    return payload
