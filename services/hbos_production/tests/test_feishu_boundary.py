"""飞书客户端边界 —— 网络/解析异常必须变成 `FeishuError`。

端点层（`monthly` / `ai_analysis`）只捕获 `FeishuError`。客户端里任何
别的异常都会穿透成 FastAPI 500 —— 实测把取数函数换成抛 `ReadTimeout`
后，接口直接 500 而不是可解释的 502。

这一组钉的就是这道边界。
"""

from __future__ import annotations

import httpx
import pytest

from app import feishu


def _clear_token():
    feishu._clear_token()


def test_read_timeout_becomes_feishu_error(monkeypatch):
    _clear_token()

    class Client:
        def __init__(self, **kw):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, *a, **kw):
            raise httpx.ReadTimeout("slow", request=httpx.Request("GET", "http://x"))

    monkeypatch.setattr(feishu.httpx, "Client", Client)
    monkeypatch.setattr(feishu, "_token", lambda: "tok")
    with pytest.raises(feishu.FeishuError):
        feishu.list_records("base", "tbl")


def test_connect_error_becomes_feishu_error(monkeypatch):
    _clear_token()

    class Client:
        def __init__(self, **kw):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, *a, **kw):
            raise httpx.ConnectError("refused")

    monkeypatch.setattr(feishu.httpx, "Client", Client)
    monkeypatch.setattr(feishu, "_token", lambda: "tok")
    with pytest.raises(feishu.FeishuError):
        feishu.list_records("base", "tbl")


def test_non_json_response_becomes_feishu_error(monkeypatch):
    _clear_token()

    class Resp:
        status_code = 200
        text = "<html>gateway</html>"

        def json(self):
            raise ValueError("not json")

    class Client:
        def __init__(self, **kw):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, *a, **kw):
            return Resp()

    monkeypatch.setattr(feishu.httpx, "Client", Client)
    monkeypatch.setattr(feishu, "_token", lambda: "tok")
    with pytest.raises(feishu.FeishuError):
        feishu.list_records("base", "tbl")


def test_token_missing_field_becomes_feishu_error(monkeypatch):
    _clear_token()

    class Resp:
        status_code = 200

        def json(self):
            return {"code": 0}          # 缺 tenant_access_token

    class Client:
        def __init__(self, **kw):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, *a, **kw):
            return Resp()

    monkeypatch.setattr(feishu.httpx, "Client", Client)
    with pytest.raises(feishu.FeishuError, match="缺字段"):
        feishu._token()


def test_token_network_error_becomes_feishu_error(monkeypatch):
    _clear_token()

    class Client:
        def __init__(self, **kw):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, *a, **kw):
            raise httpx.ConnectError("refused")

    monkeypatch.setattr(feishu.httpx, "Client", Client)
    with pytest.raises(feishu.FeishuError):
        feishu._token()
