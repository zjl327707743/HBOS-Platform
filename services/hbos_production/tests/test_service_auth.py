"""服务间鉴权 —— **默认拒绝**。

本服务不再由浏览器直连（改为 `Portal → HBOS 受控后端 → 本服务`）。
所以每个数据端点都必须带 `X-HBOS-Service-Token`，且令牌未配置时直接 503 ——
不允许「没配令牌就跑匿名」，那等于把生产数据裸奔。
"""

from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient

TOKEN = "test-service-token-abc"


def _client(monkeypatch, *, token: str | None):
    monkeypatch.setenv("HBOS_FEISHU_APP_ID", "cli_fake")
    monkeypatch.setenv("HBOS_FEISHU_APP_SECRET", "fake-secret")
    if token is None:
        monkeypatch.delenv("HBOS_PRODUCTION_SERVICE_TOKEN", raising=False)
    else:
        monkeypatch.setenv("HBOS_PRODUCTION_SERVICE_TOKEN", token)

    import app.config as cfg

    importlib.reload(cfg)
    import app.main as main

    importlib.reload(main)
    return main, TestClient(main.app)


DATA_ENDPOINTS = ("/production/monthly", "/production/yesterday", "/production/ai-analysis")


def test_data_endpoints_reject_without_token(monkeypatch):
    """配置了令牌但请求没带 → 401，**且响应体里没有生产数据**。"""
    _, client = _client(monkeypatch, token=TOKEN)
    for path in DATA_ENDPOINTS:
        response = client.get(path)
        assert response.status_code == 401, path
        assert "rows" not in response.text


def test_data_endpoints_reject_wrong_token(monkeypatch):
    _, client = _client(monkeypatch, token=TOKEN)
    for path in DATA_ENDPOINTS:
        response = client.get(path, headers={"X-HBOS-Service-Token": "wrong"})
        assert response.status_code == 401, path


def test_data_endpoints_refuse_when_token_not_configured(monkeypatch):
    """**未配置令牌 = 拒绝所有数据请求**（默认拒绝）。

    这是防「部署时忘了配，服务就这么裸着对外」的那道闸。
    """
    _, client = _client(monkeypatch, token=None)
    for path in DATA_ENDPOINTS:
        response = client.get(path, headers={"X-HBOS-Service-Token": TOKEN})
        assert response.status_code == 503, path


def test_health_stays_open_but_leaks_nothing(monkeypatch):
    """健康检查要能探活，所以不要求令牌；但它**不含任何业务数据**。"""
    _, client = _client(monkeypatch, token=TOKEN)
    body = client.get("/health").json()
    assert body["ok"] is True
    assert body["serviceTokenConfigured"] is True
    assert "rows" not in body
    assert TOKEN not in str(body)


def test_correct_token_reaches_the_data_layer(monkeypatch):
    """带对令牌 → 过了闸门，进到取数逻辑（这里打桩，不真打飞书）。"""
    main, client = _client(monkeypatch, token=TOKEN)

    monkeypatch.setattr(
        main,
        "_board_data",
        lambda today: {"rows": [], "anomaly": {}},
    )
    response = client.get(
        "/production/monthly",
        headers={"X-HBOS-Service-Token": TOKEN},
    )
    assert response.status_code == 200
    body = response.json()
    assert "daysElapsed" in body and "rows" in body
