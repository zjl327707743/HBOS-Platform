"""飞书 OpenAPI 客户端 —— **凭据只在本服务**。

只做两件事：拿 tenant_access_token、分页拉表记录。
不做业务判断（口径在 `contract.py`）。

同 `hbos_ocr` 的做法：凭据来自环境变量，日志不记凭据。
"""

from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import httpx

from . import config

log = logging.getLogger("hbos_production.feishu")

_TOKEN: dict[str, Any] = {"value": "", "expires_at": 0.0}
#: `_TOKEN` 是进程级共享状态，而 `list_records_many` 会并发调用 ——
#: 不加锁的话冷启动时几个线程会同时去换 token（幂等但浪费，且更容易撞节流）。
_TOKEN_LOCK = threading.Lock()


class FeishuError(RuntimeError):
    """飞书调用失败。带上游 code/msg，便于定位（与 hbos_ocr 的错误处理一致）。"""

    def __init__(self, code: int, msg: str):
        super().__init__(f"feishu error {code}: {msg}")
        self.code = code
        self.msg = msg


#: 飞书「token 失效/无效」类业务码。
#:
#: 早先只在本地按 `expires_at` 判过期；飞书侧提前撤销、或换了应用凭据时，
#: 本地缓存仍有效 → 后续请求一路 401/403，**持续 502 直到进程重启**。
#: 命中这些码时清掉本地 token 并**只重试一次**（真权限问题不该无限重试）。
AUTH_ERROR_CODES = frozenset({99991661, 99991663, 99991664, 99991668, 99991677})


def _json_body(r: httpx.Response, what: str):
    """把 HTTP 响应解析成 JSON；网络/解析错误统一转成 `FeishuError`。

    **为什么必须在客户端边界做**：端点层只捕获 `FeishuError`。
    `httpx.ReadTimeout`、`JSONDecodeError`、token 响应缺字段的 `KeyError`
    都会一路穿透成 FastAPI 500 —— 实测把取数函数换成抛 `ReadTimeout`
    后，接口直接 500，而不是可解释的 502。
    """
    try:
        return r.json()
    except ValueError as exc:
        raise FeishuError(-1, f"{what} 返回了非 JSON 响应（HTTP {r.status_code}）") from exc


def _token() -> str:
    """取 tenant_access_token（进程内缓存，提前 60 秒过期）。"""
    now = time.time()
    if _TOKEN["value"] and now < _TOKEN["expires_at"]:
        return _TOKEN["value"]

    with _TOKEN_LOCK:
        # 双检：等锁期间可能已经有别的线程换好了
        now = time.time()
        if _TOKEN["value"] and now < _TOKEN["expires_at"]:
            return _TOKEN["value"]

        url = f"{config.FEISHU_BASE}/open-apis/auth/v3/tenant_access_token/internal"
        try:
            with httpx.Client(timeout=config.TIMEOUT_SECONDS) as c:
                r = c.post(
                    url,
                    json={"app_id": config.FEISHU_APP_ID, "app_secret": config.FEISHU_APP_SECRET},
                )
        except httpx.HTTPError as exc:
            raise FeishuError(-1, f"取 tenant_access_token 网络失败：{type(exc).__name__}") from exc
        body = _json_body(r, "tenant_access_token")
        if not isinstance(body, dict):
            raise FeishuError(-1, "tenant_access_token 响应不是对象")
        if body.get("code") != 0:
            # 错误信息里可能带凭据相关提示，因此只记 code 不记 msg 全文
            raise FeishuError(int(body.get("code", -1)), "tenant_access_token 获取失败")
        token = body.get("tenant_access_token")
        if not token:
            # 缺字段 → KeyError 会穿透成 500，这里明确转成业务错误
            raise FeishuError(-1, "tenant_access_token 响应缺字段")
        _TOKEN["value"] = token
        _TOKEN["expires_at"] = now + int(body.get("expire", 7200)) - 60
        return _TOKEN["value"]


def _clear_token() -> None:
    """作废本地 token —— 上游判定它无效时调用，下一次 `_token()` 会重新换。"""
    with _TOKEN_LOCK:
        _TOKEN["value"] = ""
        _TOKEN["expires_at"] = 0.0


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

    另有一种**每次调用最多一次**的补救：上游判定 token 失效（`AUTH_ERROR_CODES`）
    时清空本地缓存并立刻重试 —— 否则 token 被提前撤销后，服务会一路 502
    直到进程重启（本地 `expires_at` 还没到）。
    """
    last: Exception | None = None
    token_refreshed = False
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

        body = _json_body(r, "bitable 查询")
        if not isinstance(body, dict):
            raise FeishuError(-1, "bitable 响应不是对象")
        code = int(body.get("code", -1))
        if code in AUTH_ERROR_CODES:
            if token_refreshed:
                # 换过 token 仍然不行 → 凭据/权限问题，立刻失败
                raise FeishuError(code, str(body.get("msg", ""))[:120])
            token_refreshed = True
            log.warning("飞书 token 失效（code=%s），作废本地缓存并重试一次", code)
            _clear_token()
            last = FeishuError(code, str(body.get("msg", ""))[:120])
            continue
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
    # 读超时给足：实测单张 400 行的表要 5~7 秒，大表翻页更慢。
    #
    # 整个分页过程包在 try 里：`httpx.Client` 构造、连接、读超时都可能抛
    # `httpx.HTTPError`，端点层只捕获 `FeishuError` —— 不包就会变成 500。
    try:
        return _list_records_paged(base_token, table_id, page_size)
    except httpx.HTTPError as exc:
        raise FeishuError(-1, f"拉表网络失败：{type(exc).__name__}") from exc


def _list_records_paged(base_token: str, table_id: str, page_size: int) -> list[dict]:
    out: list[dict] = []
    page_token = ""
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


def list_records_many(specs: list[tuple[str, str]]) -> dict[tuple[str, str], list[dict]]:
    """并发拉多张表 → `{(base_token, table_id): rows}`。

    **为什么要并发**：看板要 13 张表，其中 7 张明细表各 1500~2000 行（翻 3~4 页），
    串行实测 **57 秒** —— 点一次刷新要等近一分钟，体验很差。并发后 ~19 秒。

    两个不变量：

    - **同一张表只拉一次**：调用方可能重复引用（去重后再分发）。
    - **异常照抛**：任一张表最终失败就让整次取数失败（调用方转 502），
      不静默少算几行 —— 看板的数字宁可没有，也不能是「少拉了两张表」的结果。

    `workers <= 1` 时退回串行（保留开关，便于排查是不是并发引起的问题）。
    """
    uniq = list(dict.fromkeys(specs))
    if not uniq:
        return {}
    if config.FETCH_WORKERS <= 1 or len(uniq) == 1:
        return {s: list_records(*s) for s in uniq}

    out: dict[tuple[str, str], list[dict]] = {}
    with ThreadPoolExecutor(max_workers=min(config.FETCH_WORKERS, len(uniq))) as pool:
        futures = {pool.submit(list_records, b, t): (b, t) for b, t in uniq}
        for fut in as_completed(futures):
            out[futures[fut]] = fut.result()
    return out
