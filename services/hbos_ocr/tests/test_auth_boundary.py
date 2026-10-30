"""识别服务的内部认证边界 —— 三种失败态必须能分开。

这类问题**线上极难排查**，因为三种情况在页面上都显示「识别服务当前不可用」：

    1. 服务没起            → 连不上（ConnectionError）
    2. 服务起了但没配令牌   → /health 200，但 recognize 503
    3. 令牌不匹配          → /health 200，recognize 401

第 2 种最容易漏：`/health` 是 200、`get_intake_context` 报 `available: true`，
看起来一切正常，只有真正识别时才 503。本文件把三种状态钉住。

不启动真实服务、不加载 ML 后端 —— 用 TestClient + stub 后端。
"""

from __future__ import annotations

import importlib
import io
import os
import sys

import pytest
from fastapi.testclient import TestClient

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

# 1x1 PNG
_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\xda\x63\xf8\xcf"
    b"\xc0\x50\x0f\x00\x04\x85\x01\x80\x84\xa9\x8c\x21\x00\x00\x00\x00IEND"
    b"\xaeB`\x82"
)


def _client(monkeypatch, token: str) -> TestClient:
    monkeypatch.setenv("HBOS_OCR_BACKEND", "stub")
    monkeypatch.setenv("HBOS_OCR_SHARED_TOKEN", token)
    import app.config as cfg

    importlib.reload(cfg)
    import app.main as main

    importlib.reload(main)
    return TestClient(main.app)


def _recognize(client: TestClient, headers: dict | None = None):
    return client.post(
        "/api/v1/recognize",
        files={"image": ("t.png", io.BytesIO(_PNG), "image/png")},
        data={"source_type": "自产"},
        headers=headers or {},
    )


def test_health_is_ok_even_without_token(monkeypatch):
    """/health 不要求令牌 —— 它**不能**用来证明识别链路可用。"""
    c = _client(monkeypatch, token="")
    assert c.get("/health").status_code == 200


def test_missing_token_returns_503(monkeypatch):
    """服务端没配令牌 → 503，不是 401、更不是放行。"""
    c = _client(monkeypatch, token="")
    r = _recognize(c, {"Authorization": "Bearer anything"})
    assert r.status_code == 503
    assert "认证未配置" in r.json()["detail"]


def test_wrong_token_returns_401(monkeypatch):
    c = _client(monkeypatch, token="right-token")
    r = _recognize(c, {"Authorization": "Bearer wrong-token"})
    assert r.status_code == 401


def test_no_authorization_header_returns_401(monkeypatch):
    c = _client(monkeypatch, token="right-token")
    assert _recognize(c).status_code == 401


def test_correct_token_passes(monkeypatch):
    c = _client(monkeypatch, token="right-token")
    r = _recognize(c, {"Authorization": "Bearer right-token"})
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_bearer_prefix_is_case_sensitive_on_scheme(monkeypatch):
    """`Bearer` 前缀必须原样 —— 别的写法一律当没带令牌。"""
    c = _client(monkeypatch, token="right-token")
    assert _recognize(c, {"Authorization": "right-token"}).status_code == 401
    assert _recognize(c, {"Authorization": "bearer right-token"}).status_code == 401
