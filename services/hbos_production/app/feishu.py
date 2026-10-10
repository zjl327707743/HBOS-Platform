"""飞书 OpenAPI 客户端 —— **凭据只在本服务**。

只做两件事：拿 tenant_access_token、分页拉表记录。
不做业务判断（口径在 `contract.py`）。

同 `hbos_ocr` 的做法：凭据来自环境变量，日志不记凭据。
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from . import config

log = logging.getLogger("hbos_production.feishu")

_TOKEN: dict[str, Any] = {"value": "", "expires_at": 0.0}


class FeishuError(RuntimeError):
    """飞书调用失败。带上游 code/msg，便于定位（与 hbos_ocr 的错误处理一致）。"""

    def __init__(self, code: int, msg: str):
        super().__init__(f"feishu error {code}: {msg}")
        self.code = code
        self.msg = msg


def _token() -> str:
    """取 tenant_access_token（进程内缓存，提前 60 秒过期）。"""
    now = time.time()
    if _TOKEN["value"] and now < _TOKEN["expires_at"]:
        return _TOKEN["value"]

    url = f"{config.FEISHU_BASE}/open-apis/auth/v3/tenant_access_token/internal"
    with httpx.Client(timeout=config.TIMEOUT_SECONDS) as c:
        r = c.post(url, json={"app_id": config.FEISHU_APP_ID, "app_secret": config.FEISHU_APP_SECRET})
    body = r.json()
    if body.get("code") != 0:
        # 错误信息里可能带凭据相关提示，因此只记 code 不记 msg 全文
        raise FeishuError(int(body.get("code", -1)), "tenant_access_token 获取失败")
    _TOKEN["value"] = body["tenant_access_token"]
    _TOKEN["expires_at"] = now + int(body.get("expire", 7200)) - 60
    return _TOKEN["value"]


#: 值得重试的飞书错误码。
#:
#: `1254607` = 「Data not ready, please try again later」—— 实测并发拉表时随机出现，
#: 重试即好。**不重试的话，任意一张表碰上一次整个看板就 502**，
#: 前端显示「未接入」，看起来像服务没通。
RETRYABLE_CODES = frozenset({1254607, 1254291, 99991400})
#: 5xx 一律可重试（飞书侧瞬时故障）。
RETRYABLE_HTTP = frozenset({500, 502, 503, 504})

#: 重试次数与退避基数（秒）。退避 = base * 2^n。
RETRY_ATTEMPTS = 3
RETRY_BACKOFF = 0.8


def _get_with_retry(c: httpx.Client, url: str, params: dict) -> dict:
    """带退避重试的 GET。返回飞书响应的 JSON body。

    重试的三种情况：
      - HTTP 5xx
      - 读超时（飞书偶尔很慢 —— 实测单张 400 行的表要 5~7 秒，
        大表翻页时更容易超）
      - `RETRYABLE_CODES` 里的业务码
    """
    last: Exception | None = None
    for attempt in range(RETRY_ATTEMPTS):
        if attempt:
            time.sleep(RETRY_BACKOFF * (2 ** (attempt - 1)))
        try:
            r = c.get(url, params=params, headers={"Authorization": f"Bearer {_token()}"})
        except httpx.TimeoutException as exc:
            last = exc
            log.warning("读超时，第 %d 次重试", attempt + 1)
            continue

        if r.status_code in RETRYABLE_HTTP:
            last = FeishuError(r.status_code, f"HTTP {r.status_code}")
            log.warning("HTTP %s，第 %d 次重试", r.status_code, attempt + 1)
            continue

        body = r.json()
        code = int(body.get("code", -1))
        if code != 0 and code in RETRYABLE_CODES:
            last = FeishuError(code, str(body.get("msg", ""))[:120])
            log.warning("飞书业务码 %s，第 %d 次重试", code, attempt + 1)
            continue
        return body

    assert last is not None
    raise last


def list_records(base_token: str, table_id: str, page_size: int = 500) -> list[dict]:
    """分页拉全表记录。

    `page_size` 上限 500（飞书限制）。翻页用 `page_token`。
    GET 走 `_get_with_retry` —— 见那里的说明（不重试会导致整块 502）。
    """
    out: list[dict] = []
    page_token = ""
    # 读超时给足：实测单张 400 行的表要 5~7 秒，大表翻页更慢。
    with httpx.Client(timeout=httpx.Timeout(config.TIMEOUT_SECONDS, read=90.0)) as c:
        while True:
            params = {"page_size": page_size}
            if page_token:
                params["page_token"] = page_token
            url = f"{config.FEISHU_BASE}/open-apis/bitable/v1/apps/{base_token}/tables/{table_id}/records"
            body = _get_with_retry(c, url, params)
            if body.get("code") != 0:
                raise FeishuError(int(body.get("code", -1)), str(body.get("msg", ""))[:200])
            data = body.get("data") or {}
            out.extend(data.get("items") or [])
            if not data.get("has_more"):
                break
            page_token = data.get("page_token") or ""
            if not page_token:
                break
    return out
