"""飞书客户端 —— 本服务**既读又写**（与取数服务不同）。

读：11 张工艺描述 + 各产品生产台账
写：AI 工艺分析结果表（`Dl45bIEE…/tblXD7oAwbU8U040`）

写入必须幂等（见 `writer.py`）—— 既有 openclaw 项目在这一步出过缺陷：
同一格被追加 64 次（根因是写入前不清空、也不判重）。
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from . import config

log = logging.getLogger("hbos_production_ai.feishu")

_TOKEN: dict[str, Any] = {"value": "", "expires_at": 0.0}


class FeishuError(RuntimeError):
    def __init__(self, code: int, msg: str):
        super().__init__(f"feishu error {code}: {msg}")
        self.code = code
        self.msg = msg


def _token() -> str:
    now = time.time()
    if _TOKEN["value"] and now < _TOKEN["expires_at"]:
        return _TOKEN["value"]
    url = f"{config.FEISHU_BASE}/open-apis/auth/v3/tenant_access_token/internal"
    with httpx.Client(timeout=config.FEISHU_TIMEOUT) as c:
        r = c.post(url, json={"app_id": config.FEISHU_APP_ID, "app_secret": config.FEISHU_APP_SECRET})
    body = r.json()
    if body.get("code") != 0:
        raise FeishuError(int(body.get("code", -1)), "tenant_access_token 获取失败")
    _TOKEN["value"] = body["tenant_access_token"]
    _TOKEN["expires_at"] = now + int(body.get("expire", 7200)) - 60
    return _TOKEN["value"]


# ---------------------------------------------------------------------------
# 读
# ---------------------------------------------------------------------------

def list_records(base_token: str, table_id: str, page_size: int = 500) -> list[dict]:
    out: list[dict] = []
    page_token = ""
    with httpx.Client(timeout=config.FEISHU_TIMEOUT) as c:
        while True:
            params: dict[str, Any] = {"page_size": page_size}
            if page_token:
                params["page_token"] = page_token
            url = f"{config.FEISHU_BASE}/open-apis/bitable/v1/apps/{base_token}/tables/{table_id}/records"
            r = c.get(url, params=params, headers={"Authorization": f"Bearer {_token()}"})
            body = r.json()
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


# ---------------------------------------------------------------------------
# 写（**唯一会写飞书的地方，务必幂等**）
# ---------------------------------------------------------------------------

def create_record(base_token: str, table_id: str, fields: dict) -> str:
    url = f"{config.FEISHU_BASE}/open-apis/bitable/v1/apps/{base_token}/tables/{table_id}/records"
    with httpx.Client(timeout=config.FEISHU_TIMEOUT) as c:
        r = c.post(url, json={"fields": fields}, headers={"Authorization": f"Bearer {_token()}"})
    body = r.json()
    if body.get("code") != 0:
        raise FeishuError(int(body.get("code", -1)), str(body.get("msg", ""))[:200])
    return (body.get("data") or {}).get("record", {}).get("record_id", "")


def update_record(base_token: str, table_id: str, record_id: str, fields: dict) -> None:
    url = f"{config.FEISHU_BASE}/open-apis/bitable/v1/apps/{base_token}/tables/{table_id}/records/{record_id}"
    with httpx.Client(timeout=config.FEISHU_TIMEOUT) as c:
        r = c.put(url, json={"fields": fields}, headers={"Authorization": f"Bearer {_token()}"})
    body = r.json()
    if body.get("code") != 0:
        raise FeishuError(int(body.get("code", -1)), str(body.get("msg", ""))[:200])


def health() -> dict:
    """探活：不写任何东西，只确认凭据能换到 token。"""
    try:
        _token()
        return {"ok": True}
    except FeishuError as exc:
        return {"ok": False, "code": exc.code}
